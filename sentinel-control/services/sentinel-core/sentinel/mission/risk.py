from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sentinel.mission.budget import MissionBudgetController
from sentinel.mission.gate_sequence import (
    GateSequence,
    GateVerdict,
    SequenceResult,
)
from sentinel.mission.models import MissionAction, MissionAuthorityEnvelope, MissionState
from sentinel.mission.posture import MissionExecutionPosture, MissionExecutionPosturePolicy
from sentinel.mission.scope_checker import MissionScopeChecker
from sentinel.mission.trace_timeline import MissionTraceTimeline
from sentinel.shared.enums import (
    ConfidenceLevel,
    ExternalityLevel,
    MissionActionRoute,
    MissionStatus,
    MissionTraceEventType,
    ReversibilityLevel,
    SensitivityLevel,
)


@dataclass(frozen=True)
class RouteDecision:
    route: MissionActionRoute
    risk_score: float
    reasons: list[str] = field(default_factory=list)
    posture: str = "safe"
    applied_threshold: float | None = None
    blocking_rule: str | None = None


class GateSequenceRoutingError(RuntimeError):
    """Raised when :meth:`RiskRouter.route_via_sequence` observes an
    inconsistency between the gate sequence's verdict and the
    router's :class:`RouteDecision`.

    Task 6.5-A — the sequence is the canonical 1→7 ordering enforcer;
    the router preserves the existing timeline/event contract. Under
    normal operation the two agree (sequence BLOCK ⇒ router BLOCK,
    etc.). A mismatch is either a bug in the router's mapping or
    tampering with one side — either way it MUST NOT be silently
    papered over. This exception surfaces the drift loudly at the
    call site where it can be investigated.
    """


class RiskRouter:
    def __init__(self, project_root: str | Path | None = None) -> None:
        self.scope_checker = MissionScopeChecker(project_root)
        self.budget = MissionBudgetController()
        self.posture_policy = MissionExecutionPosturePolicy()
        self._project_root = project_root
        # Lazily built — the gate sequence construction uses the same
        # scope_checker / budget as this router, so the two code paths
        # can never disagree on what "black_zone" or "over budget" mean.
        self._gate_sequence: GateSequence | None = None
        # Populated by :meth:`route_via_sequence` so tests and audit
        # tooling can inspect the ordered gate trace after a routing
        # decision. Not part of the public :class:`RouteDecision`
        # contract (adding fields there would break
        # ``RISK_ROUTE_DECIDED`` payload parity).
        self._last_sequence_result: SequenceResult | None = None

    @property
    def last_sequence_result(self) -> SequenceResult | None:
        """Most recent :class:`SequenceResult` produced by
        :meth:`route_via_sequence`, or ``None`` if the router has
        never been invoked via the sequence path."""
        return self._last_sequence_result

    def _build_gate_sequence(self) -> GateSequence:
        """Construct the canonical 7-gate sequence.

        Gate 6 (``unknown_tool_or_capability``) is a no-op in this
        construction because the router does not own a tool
        registry; the capability check lives in
        :class:`sentinel.agent.capability_selector.CapabilitySelector`
        upstream. Passing ``known_tools=None`` yields a PASS from
        gate 6, preserving the router's existing behavior.
        """
        return GateSequence.default(
            project_root=self._project_root,
            known_tools=None,
        )

    def route(
        self,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
        action: MissionAction,
        timeline: MissionTraceTimeline | None = None,
        posture: MissionExecutionPosture | None = None,
    ) -> RouteDecision:
        reasons: list[str] = []
        expected_posture = self.posture_policy.select(envelope)
        if posture is not None and (posture.mission_id != envelope.id or posture.mode != envelope.mode):
            return self._decision(
                action,
                MissionActionRoute.ESCALATE,
                75.0,
                ["Execution posture does not match the mission authority envelope."],
                timeline,
                expected_posture,
                applied_threshold=expected_posture.escalate_threshold,
                blocking_rule="posture_authority_mismatch",
            )
        posture = posture or expected_posture

        if state.mission_id != envelope.id or action.mission_id != envelope.id:
            return self._decision(
                action,
                MissionActionRoute.BLOCK,
                100.0,
                ["Mission state or action identity does not match the authority envelope."],
                timeline,
                posture,
                applied_threshold=posture.block_threshold,
                blocking_rule="mission_identity_mismatch",
            )

        if envelope.revoked_at is not None or state.status == MissionStatus.REVOKED:
            return self._decision(action, MissionActionRoute.BLOCK, 100.0, ["Mission authority is revoked."], timeline, posture, blocking_rule="mission_revoked")

        if state.status in {MissionStatus.STOPPED, MissionStatus.FAILED, MissionStatus.COMPLETED, MissionStatus.ESCALATED}:
            return self._decision(action, MissionActionRoute.BLOCK, 100.0, [f"Mission is {state.status.value}."], timeline, posture, blocking_rule=f"mission_{state.status.value}")

        if datetime.now(UTC) > envelope.resolved_expires_at():
            return self._decision(action, MissionActionRoute.BLOCK, 100.0, ["Mission authority has expired."], timeline, posture, blocking_rule="mission_expired")

        if self.scope_checker.is_forbidden(envelope, action):
            return self._decision(action, MissionActionRoute.BLOCK, 100.0, ["Action is forbidden or black-zone in G12B."], timeline, posture, blocking_rule="forbidden_or_black_zone")

        in_scope = self.scope_checker.is_in_scope(envelope, action)
        if not in_scope:
            reasons.append("Action is outside the mission authority envelope.")

        budget_decision = self.budget.evaluate(envelope, state, action, timeline=timeline)
        if not budget_decision.allowed:
            reasons.extend(budget_decision.reasons)
            return self._decision(action, MissionActionRoute.ESCALATE, 75.0, reasons, timeline, posture, applied_threshold=posture.escalate_threshold, blocking_rule="budget_boundary")
        reasons.extend(budget_decision.reasons)

        risk_score = self.score(envelope, action, out_of_scope=not in_scope)

        if not in_scope:
            return self._decision(action, MissionActionRoute.ESCALATE, max(risk_score, 65.0), reasons, timeline, posture, applied_threshold=posture.escalate_threshold, blocking_rule="outside_authority")

        uncertain = action.confidence in {ConfidenceLevel.LOW, ConfidenceLevel.UNKNOWN}
        local_recoverable = self._is_local_recoverable(action)
        if posture.uncertainty_escalates and uncertain:
            return self._decision(
                action,
                MissionActionRoute.ESCALATE,
                max(risk_score, posture.escalate_threshold),
                reasons or ["SAFE posture escalates uncertain action instead of guessing."],
                timeline,
                posture,
                applied_threshold=posture.escalate_threshold,
                blocking_rule="safe_uncertainty_boundary",
            )

        if risk_score >= posture.block_threshold:
            return self._decision(action, MissionActionRoute.BLOCK, risk_score, reasons or ["Action enters blocked risk band."], timeline, posture, applied_threshold=posture.block_threshold, blocking_rule="risk_block_threshold")
        if risk_score >= posture.escalate_threshold:
            return self._decision(action, MissionActionRoute.ESCALATE, risk_score, reasons or ["Action crosses mission escalation boundary."], timeline, posture, applied_threshold=posture.escalate_threshold, blocking_rule="risk_escalate_threshold")
        if not local_recoverable:
            return self._decision(action, MissionActionRoute.ESCALATE, risk_score, reasons or ["Action is not local and recoverable; posture cannot auto-continue it."], timeline, posture, applied_threshold=posture.escalate_threshold, blocking_rule="non_local_or_non_recoverable")
        if local_recoverable and risk_score <= posture.auto_execute_threshold:
            return self._decision(action, MissionActionRoute.AUTO_EXECUTE, risk_score, reasons or ["Action is local, recoverable, authorized, and inside posture threshold."], timeline, posture, applied_threshold=posture.auto_execute_threshold)
        if risk_score <= posture.log_and_continue_threshold:
            return self._decision(action, MissionActionRoute.LOG_AND_CONTINUE, risk_score, reasons or ["Action is in scope and routed through bounded continuation."], timeline, posture, applied_threshold=posture.log_and_continue_threshold)

        return self._decision(action, MissionActionRoute.ESCALATE, risk_score, reasons or ["Action is authorized but exceeds posture continuation threshold."], timeline, posture, applied_threshold=posture.escalate_threshold, blocking_rule="posture_continuation_threshold")

    def route_via_sequence(
        self,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
        action: MissionAction,
        timeline: MissionTraceTimeline | None = None,
        posture: MissionExecutionPosture | None = None,
    ) -> RouteDecision:
        """Route an action through :class:`GateSequence` then
        :meth:`route` (Task 6.5-A / F-A3.8 wiring).

        The gate sequence enforces the SPINE_01 §5 1→7 order with
        short-circuit on any non-PASS verdict. After the sequence
        records its :class:`SequenceResult` on
        :attr:`_last_sequence_result`, this method delegates to
        :meth:`route` for the legacy route-decision shape and
        ``RISK_ROUTE_DECIDED`` timeline emission. **Neither code path
        is altered**: the sequence is additive audit/ordering
        evidence; the router is the existing verdict producer.

        Consistency contract (enforced):

        * If the sequence returned ``BLOCK``, the router's
          :class:`RouteDecision` MUST also carry
          ``MissionActionRoute.BLOCK``. Any drift raises
          :class:`GateSequenceRoutingError` — a production invariant
          violation worth investigating, not silently papering over.
        * If the sequence returned ``ESCALATE``, the router's route
          MUST be either ``BLOCK`` (strictly stronger — the router
          caught an additional rule the sequence did not) or
          ``ESCALATE``. Auto-execute after sequence-escalate would
          indicate the router dropped a gate.
        * ``PASS`` / ``REPORT_MISSING`` sequence verdicts do not
          constrain the router's route — both are advisory signals
          without a hardened mapping to the :class:`MissionActionRoute`
          enum.

        The timeline payload emitted by :meth:`_decision` is
        unchanged. A new ``RISK_ROUTE_DECIDED`` event still carries
        ``posture``, ``posture_level``, ``risk_score``,
        ``applied_threshold``, ``blocking_rule``, and ``reasons``
        exactly as :meth:`route` has always emitted them. Tests
        asserting on those fields continue to pass.
        """
        if self._gate_sequence is None:
            self._gate_sequence = self._build_gate_sequence()
        sequence_result = self._gate_sequence.evaluate(action, envelope, state)
        self._last_sequence_result = sequence_result
        decision = self.route(envelope, state, action, timeline=timeline, posture=posture)
        self._assert_sequence_router_consistency(sequence_result, decision, action)
        return decision

    @staticmethod
    def _assert_sequence_router_consistency(
        sequence_result: SequenceResult,
        decision: RouteDecision,
        action: MissionAction,
    ) -> None:
        if sequence_result.terminal_verdict == GateVerdict.BLOCK:
            if decision.route != MissionActionRoute.BLOCK:
                raise GateSequenceRoutingError(
                    "GateSequence returned BLOCK but RiskRouter returned "
                    f"{decision.route.value!r} for action "
                    f"{action.action_type!r}/{action.tool!r}. The two "
                    "enforcers must agree on terminal denies; a "
                    "mismatch indicates a bug in the router's route "
                    "mapping or in the sequence's default gate "
                    "construction. Blocking gate: "
                    f"{sequence_result.blocking_gate.gate_name if sequence_result.blocking_gate else None!r}."
                )
        elif sequence_result.terminal_verdict == GateVerdict.ESCALATE:
            if decision.route not in {
                MissionActionRoute.BLOCK,
                MissionActionRoute.ESCALATE,
            }:
                raise GateSequenceRoutingError(
                    "GateSequence returned ESCALATE but RiskRouter "
                    f"auto-executed {action.action_type!r}/{action.tool!r}. "
                    "An escalation gate was dropped; refusing to "
                    "auto-execute. Blocking gate: "
                    f"{sequence_result.blocking_gate.gate_name if sequence_result.blocking_gate else None!r}."
                )

    def score(self, envelope: MissionAuthorityEnvelope, action: MissionAction, *, out_of_scope: bool = False) -> float:
        external = action.externality in {ExternalityLevel.EXTERNAL_PRIVATE, ExternalityLevel.EXTERNAL_PUBLIC}
        irreversible = action.reversibility == ReversibilityLevel.IRREVERSIBLE
        sensitive = action.sensitivity in {SensitivityLevel.PERSONAL, SensitivityLevel.SECRET, SensitivityLevel.FINANCIAL, SensitivityLevel.IDENTITY}
        costly = envelope.max_cost_usd > 0 and action.estimated_cost >= envelope.max_cost_usd * 0.5
        uncertain = action.confidence in {ConfidenceLevel.LOW, ConfidenceLevel.UNKNOWN}

        return min(
            100.0,
            (25.0 if out_of_scope else 0.0)
            + (20.0 if external else 0.0)
            + (20.0 if irreversible else 0.0)
            + (15.0 if sensitive else 0.0)
            + (10.0 if costly else 0.0)
            + (10.0 if uncertain else 0.0),
        )

    def _decision(
        self,
        action: MissionAction,
        route: MissionActionRoute,
        risk_score: float,
        reasons: list[str],
        timeline: MissionTraceTimeline | None,
        posture: MissionExecutionPosture,
        *,
        applied_threshold: float | None = None,
        blocking_rule: str | None = None,
    ) -> RouteDecision:
        if timeline:
            timeline.emit_route(action.id, route.value, risk_score, reasons)
            timeline.emit(
                MissionTraceEventType.RISK_ROUTE_DECIDED,
                f"Risk route decided under {posture.mode.value} posture.",
                action_id=action.id,
                result={
                    "route": route.value,
                    "posture": posture.mode.value,
                    "posture_level": posture.level.value,
                    "risk_score": risk_score,
                    "applied_threshold": applied_threshold,
                    "blocking_rule": blocking_rule,
                    "reasons": reasons,
                },
                impact="Posture-adjusted mission routing evaluated without changing authority.",
            )
            if route == MissionActionRoute.BLOCK:
                timeline.emit(
                    MissionTraceEventType.ACTION_BLOCKED,
                    "Action blocked by Mission Authority Kernel.",
                    action_id=action.id,
                    result={"risk_score": risk_score, "reasons": reasons},
                    reversible=True,
                )
            elif route == MissionActionRoute.ESCALATE:
                timeline.emit(
                    MissionTraceEventType.ACTION_ESCALATED,
                    "Action escalated at mission boundary.",
                    action_id=action.id,
                    result={"risk_score": risk_score, "reasons": reasons},
                    reversible=True,
                )
        return RouteDecision(
            route=route,
            risk_score=risk_score,
            reasons=reasons,
            posture=posture.mode.value,
            applied_threshold=applied_threshold,
            blocking_rule=blocking_rule,
        )

    @staticmethod
    def _is_local_recoverable(action: MissionAction) -> bool:
        return (
            action.externality == ExternalityLevel.INTERNAL_LOCAL
            and action.reversibility
            in {
                ReversibilityLevel.READ_ONLY,
                ReversibilityLevel.DRAFT,
                ReversibilityLevel.LOCAL_WRITE_REVERSIBLE,
                ReversibilityLevel.STATE_MUTATING_RECOVERABLE,
            }
            and action.sensitivity not in {SensitivityLevel.PERSONAL, SensitivityLevel.SECRET, SensitivityLevel.FINANCIAL, SensitivityLevel.IDENTITY}
        )
