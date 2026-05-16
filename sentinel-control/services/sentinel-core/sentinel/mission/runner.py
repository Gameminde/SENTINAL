from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from sentinel.mission.artifacts import MissionArtifactIndex
from sentinel.mission.autonomy import AutonomyEngine
from sentinel.mission.budget import MissionBudgetController
from sentinel.mission.cancellation import CancellationToken
from sentinel.mission.escalation import EscalationGateway
from sentinel.mission.exceptions import BrowserOperatorRouteRejected
from sentinel.mission.exceptions import MissionRevokedException
from sentinel.mission.models import MissionAuthorityEnvelope, MissionPlan, MissionRunResult, MissionState, ReviewResult, utc_now
from sentinel.mission.posture import MissionExecutionPosturePolicy
from sentinel.mission.registry import MissionRegistry, default_mission_registry
from sentinel.mission.safe_executors import SafeMissionExecutors, mission_slug
from sentinel.mission.trace_timeline import MissionTraceTimeline
from sentinel.shared.enums import MissionActionRoute, MissionStatus, MissionTraceEventType


if TYPE_CHECKING:
    from sentinel.perf.hot_cold.cold_receipt_store import ColdReceiptStore
    from sentinel.perf.hot_cold.hot_mission_cache import HotMissionCache
    from sentinel.perf.hot_cold.receipt_index import ReceiptIndex
    from sentinel.perf.measure.latency_profiler import LatencyProfiler


class BrowserOperatorMissionRouteProtocol(Protocol):
    def run_mission_action(
        self,
        action: Any,
        envelope: MissionAuthorityEnvelope,
        *,
        capture_root: str | Path | None = None,
    ) -> dict[str, Any]:
        ...


class MissionRunner:
    def __init__(
        self,
        project_root: str | Path | None = None,
        registry: MissionRegistry | None = None,
        browser_operator_route: BrowserOperatorMissionRouteProtocol | None = None,
    ) -> None:
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.executors = SafeMissionExecutors(self.project_root)
        self.autonomy = AutonomyEngine(self.project_root)
        self.budget = MissionBudgetController()
        self.escalations = EscalationGateway()
        self.registry = registry or default_mission_registry(str(self.project_root))
        self.posture_policy = MissionExecutionPosturePolicy()
        self.browser_operator_route = browser_operator_route
        self._latency_profiler = latency_profiler
        self._hot_cache = hot_cache
        self._cold_store = cold_store
        self._receipt_index = receipt_index

    def run_gtm_mission(
        self,
        envelope: MissionAuthorityEnvelope,
        *,
        idea: str | None = None,
        evidence_refs: list[str] | None = None,
        plan: MissionPlan | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> MissionRunResult:
        return self.run_mission(
            envelope,
            idea=idea,
            evidence_refs=evidence_refs,
            plan=plan,
            cancellation_token=cancellation_token,
        )

    def run_mission(
        self,
        envelope: MissionAuthorityEnvelope,
        *,
        idea: str | None = None,
        evidence_refs: list[str] | None = None,
        plan: MissionPlan | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> MissionRunResult:
        # Emit mission-start trace if profiler is injected
        trace_id = None
        if self._latency_profiler is not None:
            trace_id = self._latency_profiler.start_trace(
                mission_id=envelope.id,
                action_id=f"{envelope.id}:mission_run",
                action_type="mission_run",
                metadata={"phase": "mission_runner"},
            )

        try:
            result = self._do_run_mission(
                envelope,
                idea=idea,
                evidence_refs=evidence_refs,
                plan=plan,
                cancellation_token=cancellation_token,
            )

            if self._hot_cache is not None:
                self._hot_cache.set(envelope.id, result)

            return result
        finally:
            if self._hot_cache is not None:
                self._hot_cache.evict(envelope.id)
            if self._latency_profiler is not None and trace_id is not None:
                self._latency_profiler.stop_trace(trace_id)

    def _do_run_mission(
        self,
        envelope: MissionAuthorityEnvelope,
        *,
        idea: str | None = None,
        evidence_refs: list[str] | None = None,
        plan: MissionPlan | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> MissionRunResult:
        definition = self.registry.get(envelope.mission_type)
        project_dir = self.executors.project_dir_for(envelope.mission_title)
        timeline = MissionTraceTimeline(envelope.id)
        timeline.emit(MissionTraceEventType.MISSION_CREATED, "Mission authority envelope accepted.")
        timeline.bind_project_dir(project_dir)

        state = MissionState(
            mission_id=envelope.id,
            status=MissionStatus.RUNNING,
            started_at=utc_now(),
            updated_at=utc_now(),
        )
        timeline.emit(MissionTraceEventType.MISSION_STARTED, "Mission started inside authorized scope.")
        posture = self.posture_policy.select(envelope)

        artifact_index = MissionArtifactIndex(project_dir, mission_id=envelope.id)
        if plan is not None and plan.mission_id != envelope.id:
            raise ValueError("Supplied mission plan must match the mission authority envelope.")
        plan = plan or definition.planner.create_plan(envelope, idea=idea, evidence_refs=evidence_refs)
        escalations = []
        blocked_actions = []
        completed_steps: set[str] = set()
        revoked = False

        for step in plan.steps:
            # Task 4 / Requirement 4 (F-A3.10) - reactive revocation check.
            # Poll ``envelope.revoked_at`` and the optional cancellation
            # token BEFORE each plan step so the kill-switch takes effect
            # within one phase boundary. If revoked, abort the remaining
            # steps; they must not execute.
            try:
                self._check_revocation(envelope, cancellation_token)
            except MissionRevokedException:
                revoked = True
                timeline.emit(
                    MissionTraceEventType.MISSION_REVOKED,
                    "Mission authority revoked mid-run; remaining plan steps suppressed.",
                    action_id=step.action.id,
                    result={"step_id": step.id, "reason": "mission_revoked"},
                )
                break

            missing_deps = [dep for dep in step.depends_on if dep not in completed_steps]
            if missing_deps:
                timeline.emit(
                    MissionTraceEventType.ACTION_BLOCKED,
                    "Plan step blocked because DAG dependencies are missing.",
                    action_id=step.action.id,
                    result={"step_id": step.id, "missing_dependencies": missing_deps},
                )
                blocked_actions.append(step.action)
                continue

            state = state.model_copy(update={"current_step": step.id, "updated_at": utc_now()})
            timeline.emit_action_planned(step.action.id, f"Planned step `{step.id}`.", target=step.expected_artifact)
            decision = self.autonomy.decide(envelope, state, step.action, timeline=timeline, posture=posture)
            routed_action = step.action.model_copy(update={"route": decision.route, "risk_score": decision.risk_score})

            if decision.route in {MissionActionRoute.AUTO_EXECUTE, MissionActionRoute.LOG_AND_CONTINUE}:
                try:
                    if routed_action.action_type == "browser_operator_route":
                        output = self._execute_browser_operator_route(envelope, routed_action)
                    else:
                        output = definition.executor.execute(routed_action, project_dir, artifact_index, timeline=timeline)
                except Exception as exc:
                    timeline.emit(
                        MissionTraceEventType.ACTION_BLOCKED,
                        "Action executor failed inside the mission boundary.",
                        action_id=routed_action.id,
                        result={
                            "step_id": step.id,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                    blocked_actions.append(routed_action)
                    continue
                timeline.emit_executed(routed_action.id, f"Executed `{routed_action.action_type}`.", output, routed_action.reversibility)
                state = self.budget.record_usage(state, routed_action)
                completed_steps.add(step.id)
                # Also poll AFTER the step so the next step does not start
                # when revocation arrived mid-step. This does not roll back
                # the completed step; it only guarantees no subsequent step
                # begins after revocation is observed.
                try:
                    self._check_revocation(envelope, cancellation_token)
                except MissionRevokedException:
                    revoked = True
                    timeline.emit(
                        MissionTraceEventType.MISSION_REVOKED,
                        "Mission authority revoked between steps; remaining plan steps suppressed.",
                        action_id=routed_action.id,
                        result={"step_id": step.id, "reason": "mission_revoked"},
                    )
                    break
                continue

            if decision.route == MissionActionRoute.ESCALATE:
                request = self.escalations.create_request(envelope, routed_action, "; ".join(decision.reasons), timeline=timeline)
                escalations.append(request)
                state = state.model_copy(update={"status": MissionStatus.ESCALATED, "updated_at": utc_now()})
                continue

            blocked_actions.append(routed_action)

        artifact_index.write(timeline=timeline)
        timeline.persist()

        review = definition.reviewer.review(
            envelope,
            project_dir,
            artifact_index.artifacts,
            unresolved_critical_escalations=len(escalations),
        )
        timeline.emit(
            MissionTraceEventType.REVIEW_EXECUTED,
            "ReviewerLite checked mission artifacts before completion.",
            result=review.model_dump(mode="json"),
        )
        timeline.persist()

        success, failures = definition.success_evaluator.evaluate(project_dir, review, unresolved_critical_escalations=len(escalations))
        if revoked:
            state = state.model_copy(
                update={"status": MissionStatus.REVOKED, "updated_at": utc_now(), "ended_at": utc_now()}
            )
            review = ReviewResult(
                mission_id=envelope.id,
                ready=False,
                issues=review.issues,
            )
            success = False
        elif success and not blocked_actions and not escalations:
            state = state.model_copy(update={"status": MissionStatus.COMPLETED, "current_step": "mission_completed", "updated_at": utc_now(), "ended_at": utc_now()})
            timeline.emit(MissionTraceEventType.MISSION_COMPLETED, "Mission completed after ReviewerLite and success evaluation.")
        else:
            state = state.model_copy(update={"status": MissionStatus.FAILED, "updated_at": utc_now(), "ended_at": utc_now()})
            timeline.emit(
                MissionTraceEventType.MISSION_FAILED,
                "Mission failed success evaluation or encountered unresolved boundary events.",
                result={"failures": failures, "blocked_actions": [action.id for action in blocked_actions], "escalations": [item.id for item in escalations]},
            )
            review = ReviewResult(
                mission_id=envelope.id,
                ready=False,
                issues=review.issues,
            )
        timeline.persist()

        return MissionRunResult(
            mission=envelope,
            state=state,
            project_path=str(project_dir),
            artifacts=artifact_index.artifacts,
            artifact_receipts=artifact_index.artifact_receipts,
            review=review,
            success=success and not blocked_actions and not escalations and not revoked,
            trace_events=timeline.events,
            escalations=escalations,
            blocked_actions=blocked_actions,
        )

    @staticmethod
    def _check_revocation(
        envelope: MissionAuthorityEnvelope,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Raise :class:`MissionRevokedException` if the run is revoked."""
        if envelope.revoked_at is not None:
            raise MissionRevokedException(
                "mission_revoked: envelope.revoked_at is set; "
                "remaining plan steps must not execute."
            )
        if cancellation_token is not None and cancellation_token.is_cancelled:
            raise MissionRevokedException(
                "mission_revoked: cancellation token fired; "
                "remaining plan steps must not execute."
            )

    def _execute_browser_operator_route(self, envelope: MissionAuthorityEnvelope, action) -> dict[str, Any]:
        if self.browser_operator_route is None:
            raise BrowserOperatorRouteRejected(
                reason="browser_operator_route_not_configured",
                context={
                    "mission_id": envelope.id,
                    "action_id": getattr(action, "id", None),
                    "action_type": getattr(action, "action_type", None),
                },
            )
        capture_root = self.project_root / "browser_operator_captures" / mission_slug(envelope.mission_title)
        try:
            result = self.browser_operator_route.run_mission_action(
                action, envelope, capture_root=capture_root
            )
        except BrowserOperatorRouteRejected:
            raise
        except Exception as original_exc:
            raise BrowserOperatorRouteRejected(
                reason="browser_operator_route_adapter_failed",
                context={
                    "mission_id": envelope.id,
                    "action_id": getattr(action, "id", None),
                    "action_type": getattr(action, "action_type", None),
                    "capture_root": str(capture_root),
                    "error_type": type(original_exc).__name__,
                },
                original_exception=original_exc,
            ) from original_exc
        if result.get("accepted") is not True:
            raise BrowserOperatorRouteRejected(
                reason=str(result.get("reason") or "unspecified"),
                context={
                    "mission_id": envelope.id,
                    "action_id": getattr(action, "id", None),
                    "action_type": getattr(action, "action_type", None),
                    "capture_root": str(capture_root),
                    "adapter_result": {
                        k: v
                        for k, v in result.items()
                        if k not in {"accepted", "reason"}
                    },
                },
            )
        return {
            "status": "executed",
            "type": "browser_operator_route",
            **result,
        }
