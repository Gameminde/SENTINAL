from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import Field

from sentinel.agent.audit import RuntimeCertificationGate
from sentinel.agent.browser.interaction_dry_run import (
    P3G_FORBIDDEN_INTERACTION_NAMES,
    verify_browser_interaction_plan_hash,
)
from sentinel.agent.browser.interaction_execution import P3H_ALLOWED_EXECUTION_INTENTS
from sentinel.agent.browser.observability import verify_browser_network_ledger_hash
from sentinel.agent.browser.cdp_ax import verify_cdp_ax_tree_hash
from sentinel.agent.browser.dom_snapshot import verify_dom_snapshot_hash
from sentinel.agent.browser.ui_observation import verify_ui_observation_hash
from sentinel.agent.browser.visual_observation import verify_visual_observation_hash
from sentinel.agent.events import AgentEventType
from sentinel.agent.evidence import EvidenceDecisionType
from sentinel.agent.final_gate_registry import FinalGateRegistry
from sentinel.agent.models import AgentRunResult, ToolSelectionStatus
from sentinel.agent.phases import AgentPhase
from sentinel.agent.replay import AgentTraceReplayer
from sentinel.mission.models import MissionPlan, MissionRunResult
from sentinel.mission.trace_timeline import MissionTraceTimeline
from sentinel.shared.enums import MissionActionRoute, MissionTraceEventType
from sentinel.shared.models import SentinelModel


class CoreGateCheckKind(StrEnum):
    TRACE = "trace"
    CERTIFICATION = "certification"
    REPLAY = "replay"
    PHASE = "phase"
    TOOL_POLICY = "tool_policy"
    LEARNING = "learning"
    EVIDENCE = "evidence"
    ARTIFACT = "artifact"
    SCOPE = "scope"
    RISK = "risk"
    MISSION = "mission"
    BUDGET = "budget"
    PERFORMANCE = "performance"


class CoreGateCheck(SentinelModel):
    name: str
    kind: CoreGateCheckKind
    passed: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class CoreFinalGateResult(SentinelModel):
    accepted: bool
    checks: list[CoreGateCheck] = Field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        return [check.name for check in self.checks if not check.passed]


class CoreFinalGate:
    """Final P1 brain gate before any P2 capability expansion.

    Task 11 / Requirement 11 — CoreFinalGate Decomposition.
    Checks are split across :class:`FinalGateCheckModule` instances held in
    a :class:`FinalGateRegistry`. The default registry (core + browser +
    conditional project-scope tail) reproduces the pre-Task-11 check order
    and count exactly, so behavior is unchanged. Organ-side adapters can
    be appended via ``registry.register(module)`` without modifying this
    class.
    """

    SUCCESS_REQUIRED_EVENTS = (
        AgentEventType.CONTEXT_BUILT,
        AgentEventType.CONTEXT_COMPRESSED,
        AgentEventType.ORIENTATION_COMPLETED,
        AgentEventType.METHODS_SELECTED,
        AgentEventType.CAPABILITIES_SELECTED,
        AgentEventType.TOOLS_SELECTED,
        AgentEventType.HYPOTHESES_REVIEWED,
        AgentEventType.WORLD_MODEL_SIMULATED,
        AgentEventType.OBJECTIVE_SCORED,
        AgentEventType.EFFORT_ROUTED,
        AgentEventType.PLAN_CREATED,
        AgentEventType.EXECUTION_POSTURE_SELECTED,
        AgentEventType.PLAN_REVIEWED,
        AgentEventType.WORKER_STARTED,
        AgentEventType.WORKER_COMPLETED,
        AgentEventType.ARTIFACTS_REVIEWED,
        AgentEventType.REPAIR_DECIDED,
        AgentEventType.SUCCESS_EVALUATED,
        AgentEventType.LEARNING_PROPOSED,
        AgentEventType.AGENT_COMPLETED,
    )

    SUCCESS_REQUIRED_EVIDENCE = (
        EvidenceDecisionType.TOOL_SELECTION,
        EvidenceDecisionType.HYPOTHESIS_VERDICT,
        EvidenceDecisionType.PLAN_CREATION,
        EvidenceDecisionType.REPAIR_DECISION,
        EvidenceDecisionType.SUCCESS_EVALUATION,
        EvidenceDecisionType.LEARNING_PROPOSAL,
    )

    def __init__(self, registry: "FinalGateRegistry | None" = None) -> None:
        # Local import to avoid circular dependency at module-load time —
        # ``final_gate_registry`` imports ``CoreFinalGate`` to delegate
        # its check methods.
        from sentinel.agent.final_gate_registry import default_registry as _default

        self._registry = registry if registry is not None else _default()

    @property
    def registry(self) -> "FinalGateRegistry":
        return self._registry

    def evaluate(
        self,
        result: AgentRunResult,
        *,
        allowed_project_root: str | Path | None = None,
    ) -> CoreFinalGateResult:
        verdict = self._registry.evaluate_all(
            result,
            allowed_project_root=Path(allowed_project_root).resolve()
            if allowed_project_root is not None
            else None,
        )
        performance_receipts = tuple(getattr(result, "performance_receipts", ()) or ())
        if not performance_receipts:
            return verdict

        performance_check = self._performance_receipt_invariants(performance_receipts)
        return CoreFinalGateResult(
            accepted=verdict.accepted and performance_check.passed,
            checks=[*verdict.checks, performance_check],
        )

    def verify_performance_receipts(
        self,
        receipts: Sequence["PerformanceReceipt"],
    ) -> CoreFinalGateResult:
        """Verify only cross-cutting PerformanceReceipt safety invariants.

        Phase F keeps latency and benchmark-budget decisions in
        ``BenchmarkHarness``. This helper intentionally checks only:
        authority expansion, raw-secret-leakage marker, and receipt hash
        integrity for receipts supplied at mission-close boundaries.
        """

        check = self._performance_receipt_invariants(receipts)
        return CoreFinalGateResult(accepted=check.passed, checks=[check])

    @staticmethod
    def _performance_receipt_invariants(
        receipts: Sequence["PerformanceReceipt"],
    ) -> CoreGateCheck:
        errors: list[str] = []

        for receipt in receipts:
            if getattr(receipt, "authority_expansion", False):
                errors.append("performance_receipt_authority_expansion")
            if getattr(receipt, "raw_secret_leakage", False):
                errors.append("performance_receipt_raw_secret_leakage")
            try:
                expected_hash = receipt._compute_receipt_hash()
                if getattr(receipt, "receipt_hash", "") != expected_hash:
                    errors.append("performance_receipt_hash_mismatch")
            except Exception:
                errors.append("performance_receipt_hash_unverifiable")

        return CoreGateCheck(
            name="performance_receipt_invariants",
            kind=CoreGateCheckKind.PERFORMANCE,
            passed=not errors,
            message="PerformanceReceipt safety invariants hold."
            if not errors
            else "PerformanceReceipt safety invariant check failed.",
            details={"errors": errors, "receipt_count": len(receipts)},
        )

    @staticmethod
    def _trace_present(result: AgentRunResult) -> CoreGateCheck:
        return CoreGateCheck(
            name="trace_present",
            kind=CoreGateCheckKind.TRACE,
            passed=bool(result.trace),
            message="Run includes an EventBus trace." if result.trace else "Run has no trace.",
        )

    @staticmethod
    def _trace_mission_consistency(result: AgentRunResult) -> CoreGateCheck:
        mission_ids = {event.mission_id for event in result.trace}
        passed = mission_ids == {result.mission_id}
        return CoreGateCheck(
            name="trace_mission_consistency",
            kind=CoreGateCheckKind.TRACE,
            passed=passed,
            message="Trace mission ids match the run result." if passed else "Trace mission ids diverge from the run result.",
            details={"trace_mission_ids": sorted(mission_ids), "result_mission_id": result.mission_id},
        )

    @staticmethod
    def _runtime_certification(result: AgentRunResult) -> CoreGateCheck:
        certification = RuntimeCertificationGate().certify(result.trace)
        errors = list(certification.errors)
        if result.runtime_certification is None:
            errors.append("result_runtime_certification_missing")
        else:
            if result.runtime_certification.certified != certification.certified:
                errors.append("result_runtime_certification_certified_mismatch")
            if result.runtime_certification.event_count != certification.event_count:
                errors.append("result_runtime_certification_event_count_mismatch")
            if result.runtime_certification.mission_id != certification.mission_id:
                errors.append("result_runtime_certification_mission_mismatch")
            if list(result.runtime_certification.errors) != list(certification.errors):
                errors.append("result_runtime_certification_errors_mismatch")
        return CoreGateCheck(
            name="runtime_certification",
            kind=CoreGateCheckKind.CERTIFICATION,
            passed=certification.certified and not errors,
            message="Runtime certification accepts the trace and matches the run result." if certification.certified and not errors else "Runtime certification contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _state_replay(result: AgentRunResult) -> CoreGateCheck:
        replay = AgentTraceReplayer().replay(result.trace)
        errors = list(replay.errors)
        if result.state_snapshot is None:
            errors.append("result_state_snapshot_missing")
        else:
            snapshot = replay.snapshot
            if result.state_snapshot.errors:
                errors.append("result_state_snapshot_has_errors")
            comparisons = {
                "trace_hash": (result.state_snapshot.trace_hash, snapshot.trace_hash),
                "final_phase": (result.state_snapshot.final_phase, snapshot.final_phase),
                "selected_tools": (result.state_snapshot.selected_tools, snapshot.selected_tools),
                "selected_action_id": (result.state_snapshot.selected_action_id, snapshot.selected_action_id),
                "selected_action_name": (result.state_snapshot.selected_action_name, snapshot.selected_action_name),
                "effort_level": (result.state_snapshot.effort_level, snapshot.effort_level),
                "project_path": (result.state_snapshot.project_path, snapshot.project_path),
                "direct_tool_call_budget": (result.state_snapshot.direct_tool_call_budget, snapshot.direct_tool_call_budget),
                "controlled_capability_executed_count": (
                    result.state_snapshot.controlled_capability_executed_count,
                    snapshot.controlled_capability_executed_count,
                ),
                "controlled_capability_rejected_count": (
                    result.state_snapshot.controlled_capability_rejected_count,
                    snapshot.controlled_capability_rejected_count,
                ),
            }
            if snapshot.success is not None:
                comparisons["success"] = (result.state_snapshot.success, snapshot.success)
            for field_name, (observed, expected) in comparisons.items():
                if observed != expected:
                    errors.append(f"result_state_snapshot_{field_name}_mismatch")
        return CoreGateCheck(
            name="state_replay",
            kind=CoreGateCheckKind.REPLAY,
            passed=replay.accepted and not errors,
            message="Trace replay reconstructs an accepted state and matches the run result." if replay.accepted and not errors else "Trace replay contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _phase_contract(result: AgentRunResult) -> CoreGateCheck:
        success_contract = result.success is (result.final_phase == AgentPhase.COMPLETED)
        terminal_match = bool(result.trace and result.trace[-1].phase_after == result.final_phase)
        passed = success_contract and terminal_match
        return CoreGateCheck(
            name="phase_contract",
            kind=CoreGateCheckKind.PHASE,
            passed=passed,
            message="Success flag, final phase, and terminal trace agree." if passed else "Success flag, final phase, or terminal trace disagree.",
            details={
                "success": result.success,
                "final_phase": result.final_phase,
                "terminal_phase": result.trace[-1].phase_after if result.trace else None,
            },
        )

    @staticmethod
    def _tool_policy_decisions_trace_bound(result: AgentRunResult) -> CoreGateCheck:
        policy_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.TOOL_POLICY_DECIDED
        }
        errors: list[str] = []
        for index, decision in enumerate(result.tool_selection_decisions):
            if decision.candidate_tool_id and not decision.trace_id:
                errors.append(f"tool_decision_missing_trace_id_{index}")
                continue
            if not decision.trace_id:
                continue
            event = policy_events.get(decision.trace_id)
            if event is None:
                errors.append(f"tool_decision_trace_event_missing_{index}")
                continue
            payload = event.payload
            expected = {
                "tool_id": decision.candidate_tool_id,
                "action": decision.requested_action,
                "status": _enum_value(decision.registry_policy_result),
                "allowed": decision.authority_allowed,
                "reason": decision.reason,
                "risk_class": _enum_value(decision.risk_class),
                "manifest_status": _enum_value(decision.manifest_status),
            }
            for key, expected_value in expected.items():
                if expected_value is not None and payload.get(key) != expected_value:
                    errors.append(f"tool_decision_trace_payload_mismatch_{index}_{key}")
            requested_side_effects = [_enum_value(item) for item in decision.side_effects]
            payload_side_effects = [_enum_value(item) for item in payload.get("requested_side_effects", [])]
            if sorted(payload_side_effects) != sorted(requested_side_effects):
                errors.append(f"tool_decision_trace_payload_mismatch_{index}_requested_side_effects")
        return CoreGateCheck(
            name="tool_policy_decisions_trace_bound",
            kind=CoreGateCheckKind.TOOL_POLICY,
            passed=not errors,
            message="Tool selection decisions are bound to policy trace events." if not errors else "Tool policy decision trace binding failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _selected_tools_are_policy_eligible(result: AgentRunResult) -> CoreGateCheck:
        eligible = {
            decision.candidate_tool_id
            for decision in result.tool_selection_decisions
            if decision.candidate_tool_id
            and decision.decision in {ToolSelectionStatus.ELIGIBLE_FOR_SAFE_WORKER, ToolSelectionStatus.ELIGIBLE_FOR_DRY_RUN}
            and decision.authority_allowed
            and decision.trace_id
        }
        unproven = sorted(tool for tool in result.selected_tools if tool not in eligible)
        return CoreGateCheck(
            name="selected_tools_are_policy_eligible",
            kind=CoreGateCheckKind.TOOL_POLICY,
            passed=not unproven,
            message="Every selected tool has an eligible policy decision." if not unproven else "Selected tools lack eligible policy decisions.",
            details={"unproven_selected_tools": unproven},
        )

    @staticmethod
    def _non_selected_tools_stay_out(result: AgentRunResult) -> CoreGateCheck:
        selected = set(result.selected_tools)
        forbidden_overlap = sorted(selected & (set(result.blocked_tools) | set(result.candidate_tools)))
        return CoreGateCheck(
            name="blocked_and_candidate_tools_not_selected",
            kind=CoreGateCheckKind.TOOL_POLICY,
            passed=not forbidden_overlap,
            message="Blocked and candidate tools are not selected." if not forbidden_overlap else "Blocked or candidate tools were selected.",
            details={"overlap": forbidden_overlap},
        )

    @staticmethod
    def _learning_is_human_approved(result: AgentRunResult) -> CoreGateCheck:
        unsafe = [proposal.id for proposal in result.learning_proposals if not proposal.requires_human_approval]
        errors = [f"learning_proposal_without_human_approval_{proposal_id}" for proposal_id in unsafe]
        proposal_events = [
            event
            for event in result.trace
            if event.event_type == AgentEventType.LEARNING_PROPOSED
        ]
        traced_count = 0
        for index, event in enumerate(proposal_events):
            proposal_count = event.payload.get("proposal_count")
            if not isinstance(proposal_count, int) or proposal_count < 0:
                errors.append(f"learning_event_invalid_proposal_count_{index}")
                continue
            traced_count += proposal_count
        if result.learning_proposals and not proposal_events:
            errors.append("learning_proposals_without_trace_event")
        if traced_count != len(result.learning_proposals):
            errors.append("learning_proposal_count_trace_mismatch")
        return CoreGateCheck(
            name="learning_requires_human_approval",
            kind=CoreGateCheckKind.LEARNING,
            passed=not errors,
            message="All learning proposals require human approval and match trace counts." if not errors else "Learning proposal contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _mission_result_consistency(result: AgentRunResult) -> CoreGateCheck:
        if result.mission_result is None:
            errors = []
            if result.success:
                errors.append("successful_run_missing_mission_result")
            if result.project_path is not None:
                errors.append("project_path_without_mission_result")
            if result.artifacts:
                errors.append("artifacts_without_mission_result")
            passed = not errors
            return CoreGateCheck(
                name="mission_result_consistency",
                kind=CoreGateCheckKind.MISSION,
                passed=passed,
                message="Run without MissionRunResult exposes no mission artifacts." if passed else "Run exposes mission outputs without MissionRunResult.",
                details={"errors": errors},
            )
        mission_result = result.mission_result
        result_artifacts = [CoreFinalGate._artifact_signature(artifact) for artifact in result.artifacts]
        mission_artifacts = [CoreFinalGate._artifact_signature(artifact) for artifact in mission_result.artifacts]
        errors: list[str] = []
        if mission_result.mission.id != result.mission_id:
            errors.append("mission_envelope_id_mismatch")
        if mission_result.state.mission_id != result.mission_id:
            errors.append("mission_state_id_mismatch")
        # A run can legitimately downgrade to success=False when critical
        # review findings fire post-execution, even if the inner mission
        # worker succeeded. The dangerous inverse — claiming overall run
        # success while the inner mission failed — is still rejected.
        if result.success and not mission_result.success:
            errors.append("mission_success_mismatch")
        if mission_result.project_path != result.project_path:
            errors.append("mission_project_path_mismatch")
        if mission_artifacts != result_artifacts:
            errors.append("mission_artifact_list_mismatch")
        return CoreGateCheck(
            name="mission_result_consistency",
            kind=CoreGateCheckKind.MISSION,
            passed=not errors,
            message="Agent result and MissionRunResult agree." if not errors else "Agent result diverges from MissionRunResult.",
            details={"errors": errors},
        )

    @staticmethod
    def _artifact_signature(artifact) -> dict[str, Any]:
        return {
            "id": artifact.id,
            "type": artifact.type,
            "path": artifact.path,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "receipt_id": artifact.receipt_id,
            "rollback_strategy": artifact.rollback_strategy,
            "trace_refs": list(artifact.trace_refs),
        }

    @staticmethod
    def _mission_trace_integrity(result: AgentRunResult) -> CoreGateCheck:
        if result.mission_result is None:
            return CoreGateCheck(
                name="mission_trace_integrity",
                kind=CoreGateCheckKind.TRACE,
                passed=True,
                message="Run has no mission result requiring mission trace integrity certification.",
            )
        errors = CoreFinalGate._mission_trace_errors_for_result(result.mission_result, result.mission_id)
        return CoreGateCheck(
            name="mission_trace_integrity",
            kind=CoreGateCheckKind.TRACE,
            passed=not errors,
            message="Mission timeline is mono-mission, terminal, and hash-chain valid." if not errors else "Mission timeline integrity contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _mission_results_archive(result: AgentRunResult) -> CoreGateCheck:
        errors: list[str] = []
        if result.mission_result is None:
            if result.mission_results:
                errors.append("archived_mission_results_without_final_mission_result")
        else:
            if not result.mission_results:
                errors.append("mission_results_archive_empty")
            elif CoreFinalGate._mission_result_signature(result.mission_results[-1]) != CoreFinalGate._mission_result_signature(result.mission_result):
                errors.append("final_mission_result_not_last_archived_result")

        for index, mission_result in enumerate(result.mission_results):
            archive_errors = CoreFinalGate._mission_trace_errors_for_result(mission_result, result.mission_id)
            if result.active_plan is not None:
                archive_errors.extend(
                    CoreFinalGate._mission_plan_binding_errors(mission_result, result.active_plan, result.mission_id)
                )
            archive_errors.extend(CoreFinalGate._mission_risk_route_errors(mission_result))
            archive_errors.extend(CoreFinalGate._mission_artifact_receipt_errors(mission_result, result.mission_id))
            errors.extend(f"archive_{index}:{error}" for error in archive_errors)

        return CoreGateCheck(
            name="mission_results_archive",
            kind=CoreGateCheckKind.MISSION,
            passed=not errors,
            message="MissionRunResult archive preserves every worker run trace." if not errors else "MissionRunResult archive contract failed.",
            details={"errors": errors, "archive_count": len(result.mission_results)},
        )

    @staticmethod
    def _mission_trace_errors_for_result(mission_result: MissionRunResult, expected_mission_id: str) -> list[str]:
        trace = mission_result.trace_events
        errors: list[str] = []
        if not trace:
            errors.append("mission_trace_empty")
        mission_ids = {event.mission_id for event in trace}
        if mission_ids != {expected_mission_id}:
            errors.append("mission_trace_mission_mismatch")
        if mission_result.mission.id != expected_mission_id:
            errors.append("mission_envelope_id_mismatch")
        if mission_result.state.mission_id != expected_mission_id:
            errors.append("mission_state_id_mismatch")
        if not MissionTraceTimeline.verify_events(trace):
            errors.append("mission_trace_hash_chain_invalid")
        if trace:
            final_type = trace[-1].event_type
            terminal_types = {
                MissionTraceEventType.MISSION_COMPLETED,
                MissionTraceEventType.MISSION_FAILED,
                MissionTraceEventType.MISSION_STOPPED,
                MissionTraceEventType.MISSION_REVOKED,
            }
            if final_type not in terminal_types:
                errors.append("mission_trace_not_terminal")
            elif mission_result.success and final_type != MissionTraceEventType.MISSION_COMPLETED:
                errors.append("successful_mission_trace_not_completed")
            elif not mission_result.success and final_type == MissionTraceEventType.MISSION_COMPLETED:
                errors.append("failed_mission_trace_marked_completed")
            review_indices = [
                index
                for index, event in enumerate(trace)
                if event.event_type == MissionTraceEventType.REVIEW_EXECUTED
            ]
            if final_type in {MissionTraceEventType.MISSION_COMPLETED, MissionTraceEventType.MISSION_FAILED} and not review_indices:
                errors.append("mission_trace_missing_review_before_terminal")
        return errors

    @staticmethod
    def _mission_result_signature(mission_result: MissionRunResult) -> dict[str, Any]:
        return {
            "mission_id": mission_result.mission.id,
            "state_mission_id": mission_result.state.mission_id,
            "project_path": mission_result.project_path,
            "success": mission_result.success,
            "artifact_ids": [artifact.id for artifact in mission_result.artifacts],
            "trace_event_count": len(mission_result.trace_events),
            "last_trace_hash": mission_result.trace_events[-1].event_hash if mission_result.trace_events else None,
        }

    @staticmethod
    def _global_action_budget(result: AgentRunResult) -> CoreGateCheck:
        if result.mission_result is None:
            return CoreGateCheck(
                name="global_action_budget",
                kind=CoreGateCheckKind.BUDGET,
                passed=True,
                message="Run has no mission result requiring global action budget certification.",
            )
        errors: list[str] = []
        controlled_executed = sum(
            1
            for event in result.trace
            if event.event_type == AgentEventType.CONTROLLED_CAPABILITY_EXECUTED
        )
        worker_action_total = 0
        worker_payloads = [
            event.payload
            for event in result.trace
            if event.event_type == AgentEventType.WORKER_COMPLETED
        ]
        if result.success and not worker_payloads:
            errors.append("successful_run_missing_worker_action_budget_trace")
        if len(worker_payloads) != len(result.mission_results):
            errors.append("worker_completed_archive_count_mismatch")
        for index, payload in enumerate(worker_payloads):
            action_count = payload.get("action_count")
            if not isinstance(action_count, int) or action_count < 0:
                errors.append(f"worker_action_count_missing_or_invalid_{index}")
                continue
            archived_action_count = result.mission_results[index].state.action_count if index < len(result.mission_results) else action_count
            if action_count != archived_action_count:
                errors.append(f"worker_action_count_archive_mismatch_{index}")
            worker_action_total += archived_action_count
        total_actions = controlled_executed + worker_action_total
        max_actions = result.mission_result.mission.max_actions
        if total_actions > max_actions:
            errors.append("global_action_budget_exceeded")
        return CoreGateCheck(
            name="global_action_budget",
            kind=CoreGateCheckKind.BUDGET,
            passed=not errors,
            message="Agent-level and mission-level executed actions stay within max_actions." if not errors else "Global action budget contract failed.",
            details={
                "errors": errors,
                "controlled_executed": controlled_executed,
                "worker_action_total": worker_action_total,
                "total_actions": total_actions,
                "max_actions": max_actions,
            },
        )

    @staticmethod
    def _model_execution_budget_contract(result: AgentRunResult) -> CoreGateCheck:
        cycle = result.llm_decision_cycle
        if not isinstance(cycle, dict):
            return CoreGateCheck(
                name="model_execution_budget_contract",
                kind=CoreGateCheckKind.BUDGET,
                passed=True,
                message="Run has no model execution budget metadata.",
            )
        model_execution = cycle.get("model_execution")
        if not isinstance(model_execution, dict):
            return CoreGateCheck(
                name="model_execution_budget_contract",
                kind=CoreGateCheckKind.BUDGET,
                passed=False,
                message="Model execution metadata is malformed.",
                details={"errors": ["model_execution_metadata_missing_or_invalid"]},
            )
        summary = model_execution.get("budget_summary")
        if summary is None:
            return CoreGateCheck(
                name="model_execution_budget_contract",
                kind=CoreGateCheckKind.BUDGET,
                passed=True,
                message="Model execution budget summary is not present for this run.",
            )
        errors: list[str] = []
        if not isinstance(summary, dict):
            errors.append("model_execution_budget_summary_invalid")
        else:
            rendered = str(summary).lower()
            for forbidden in (
                "prompt_text_in_memory_only",
                "raw_prompt",
                "raw_response",
                "reasoning_details",
                "authorization: bearer",
                "gsk_",
                "nvapi-",
                "sk-or-v1",
            ):
                if forbidden in rendered:
                    errors.append(f"model_execution_budget_summary_leaks_{forbidden}")
            if summary.get("compliant") is False and model_execution.get("success") is True:
                errors.append("model_execution_budget_noncompliant_success")
        if model_execution.get("outcome_class") == "BUDGET_REJECTED":
            if model_execution.get("success") is True:
                errors.append("budget_rejected_marked_success")
            decision = summary.get("decision") if isinstance(summary, dict) else None
            if model_execution.get("provider_called") is True and not str(decision or "").startswith("actual_"):
                errors.append("budget_rejected_after_provider_call")
            if isinstance(summary, dict) and summary.get("compliant") is not False:
                errors.append("budget_rejected_missing_noncompliant_summary")
        return CoreGateCheck(
            name="model_execution_budget_contract",
            kind=CoreGateCheckKind.BUDGET,
            passed=not errors,
            message="Model execution budget metadata is safe and internally consistent."
            if not errors
            else "Model execution budget contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _active_plan_matches_mission_trace(result: AgentRunResult) -> CoreGateCheck:
        if result.active_plan is None or result.mission_result is None:
            passed = not result.success
            return CoreGateCheck(
                name="active_plan_matches_mission_trace",
                kind=CoreGateCheckKind.MISSION,
                passed=passed,
                message="Non-successful run has no required active plan binding." if passed else "Successful run is missing active plan or mission result.",
            )
        errors = CoreFinalGate._mission_plan_binding_errors(result.mission_result, result.active_plan, result.mission_id)
        return CoreGateCheck(
            name="active_plan_matches_mission_trace",
            kind=CoreGateCheckKind.MISSION,
            passed=not errors,
            message="Reviewed active plan is the plan observed in mission trace." if not errors else "Mission trace diverges from the reviewed active plan.",
            details={"errors": errors},
        )

    @staticmethod
    def _mission_plan_binding_errors(
        mission_result: MissionRunResult,
        active_plan: MissionPlan,
        expected_mission_id: str,
    ) -> list[str]:
        planned_action_ids = [step.action.id for step in active_plan.steps]
        trace_planned_action_ids = [
            event.action_id
            for event in mission_result.trace_events
            if event.event_type == MissionTraceEventType.ACTION_PLANNED and event.action_id
        ]
        executed_action_ids = [
            event.action_id
            for event in mission_result.trace_events
            if event.event_type == MissionTraceEventType.ACTION_EXECUTED and event.action_id
        ]
        errors: list[str] = []
        if active_plan.mission_id != expected_mission_id:
            errors.append("active_plan_mission_mismatch")
        if mission_result.mission.id != expected_mission_id:
            errors.append("mission_result_mission_mismatch")
        if any(step.action.mission_id != expected_mission_id for step in active_plan.steps):
            errors.append("active_plan_action_mission_mismatch")
        duplicate_plan_action_ids = sorted(
            action_id
            for action_id in set(planned_action_ids)
            if planned_action_ids.count(action_id) > 1
        )
        if duplicate_plan_action_ids:
            errors.append("active_plan_duplicate_action_ids")
        if mission_result.success and trace_planned_action_ids != planned_action_ids:
            errors.append("active_plan_trace_action_mismatch")
        if not mission_result.success:
            planned_without_active_step = sorted(set(trace_planned_action_ids) - set(planned_action_ids))
            if planned_without_active_step:
                errors.append("mission_planned_action_not_in_active_plan")
        executed_without_plan = sorted(set(executed_action_ids) - set(planned_action_ids))
        if executed_without_plan:
            errors.append("mission_executed_action_not_in_active_plan")
        return errors

    def _success_event_contract(self, result: AgentRunResult) -> CoreGateCheck:
        if not result.success:
            return CoreGateCheck(
                name="success_event_contract",
                kind=CoreGateCheckKind.TRACE,
                passed=True,
                message="Non-successful run is not required to include the full success event path.",
            )
        event_types = {event.event_type for event in result.trace}
        missing = [event.value for event in self.SUCCESS_REQUIRED_EVENTS if event not in event_types]
        return CoreGateCheck(
            name="success_event_contract",
            kind=CoreGateCheckKind.TRACE,
            passed=not missing,
            message="Successful run includes every mandatory P1 event." if not missing else "Successful run is missing mandatory P1 events.",
            details={"missing_events": missing},
        )

    @staticmethod
    def _evidence_chains_trace_bound(result: AgentRunResult) -> CoreGateCheck:
        evidence_events = [
            event
            for event in result.trace
            if event.event_type == AgentEventType.EVIDENCE_CHAIN_BUILT
        ]
        event_chain_ids = [str(event.payload.get("chain_id")) for event in evidence_events if event.payload.get("chain_id")]
        result_chain_ids = [chain.id for chain in result.evidence_chains]
        event_by_chain_id = {
            str(event.payload.get("chain_id")): event
            for event in evidence_events
            if event.payload.get("chain_id")
        }
        errors: list[str] = []

        for chain_id in sorted(chain_id for chain_id in set(event_chain_ids) if event_chain_ids.count(chain_id) > 1):
            errors.append(f"duplicate_evidence_chain_event_{chain_id}")
        for chain_id in sorted(chain_id for chain_id in set(result_chain_ids) if result_chain_ids.count(chain_id) > 1):
            errors.append(f"duplicate_result_evidence_chain_{chain_id}")

        missing_events = sorted(set(result_chain_ids) - set(event_chain_ids))
        for chain_id in missing_events:
            errors.append(f"evidence_chain_without_trace_event_{chain_id}")
        missing_results = sorted(set(event_chain_ids) - set(result_chain_ids))
        for chain_id in missing_results:
            errors.append(f"evidence_event_without_result_chain_{chain_id}")

        for chain in result.evidence_chains:
            event = event_by_chain_id.get(chain.id)
            if event is None:
                continue
            payload = event.payload
            if _enum_value(payload.get("decision_type")) != chain.decision_type.value:
                errors.append(f"evidence_chain_decision_type_mismatch_{chain.id}")
            if payload.get("claim_id") != chain.claim.id:
                errors.append(f"evidence_chain_claim_mismatch_{chain.id}")
            if _enum_value(payload.get("verdict")) != chain.verdict.value:
                errors.append(f"evidence_chain_verdict_mismatch_{chain.id}")
            if payload.get("confidence") != chain.confidence:
                errors.append(f"evidence_chain_confidence_mismatch_{chain.id}")

        return CoreGateCheck(
            name="evidence_chains_trace_bound",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not errors,
            message="Evidence chains returned by the run match EventBus evidence events." if not errors else "Evidence chain trace binding failed.",
            details={"errors": errors},
        )

    def _success_evidence_contract(self, result: AgentRunResult) -> CoreGateCheck:
        if not result.success:
            return CoreGateCheck(
                name="success_evidence_contract",
                kind=CoreGateCheckKind.EVIDENCE,
                passed=True,
                message="Non-successful run is not required to include all success evidence chains.",
            )
        present = {chain.decision_type for chain in result.evidence_chains}
        missing = [decision_type.value for decision_type in self.SUCCESS_REQUIRED_EVIDENCE if decision_type not in present]
        return CoreGateCheck(
            name="success_evidence_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not missing,
            message="Successful run includes mandatory evidence chains." if not missing else "Successful run is missing evidence chains.",
            details={"missing_evidence_chains": missing},
        )

    @staticmethod
    def _success_artifact_contract(result: AgentRunResult) -> CoreGateCheck:
        if not result.success:
            return CoreGateCheck(
                name="success_artifact_contract",
                kind=CoreGateCheckKind.ARTIFACT,
                passed=True,
                message="Non-successful run is not required to produce artifacts.",
            )
        passed = bool(result.project_path and result.artifacts)
        return CoreGateCheck(
            name="success_artifact_contract",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=passed,
            message="Successful run produced a project path and artifacts." if passed else "Successful run lacks project path or artifacts.",
            details={"project_path": result.project_path, "artifact_count": len(result.artifacts)},
        )

    @staticmethod
    def _artifact_paths_are_relative(result: AgentRunResult) -> CoreGateCheck:
        bad_paths: list[str] = []
        for artifact in result.artifacts:
            path = PurePosixPath(artifact.path.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                bad_paths.append(artifact.path)
        return CoreGateCheck(
            name="artifact_paths_are_relative",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not bad_paths,
            message="Artifact paths are relative and scoped." if not bad_paths else "Artifact paths include absolute paths or path escapes.",
            details={"bad_paths": bad_paths},
        )

    @staticmethod
    def _execution_posture_matches_authority(result: AgentRunResult) -> CoreGateCheck:
        if result.execution_posture is None:
            passed = not result.success
            return CoreGateCheck(
                name="execution_posture_matches_authority",
                kind=CoreGateCheckKind.RISK,
                passed=passed,
                message="Non-successful run has no required execution posture." if passed else "Successful run lacks execution posture.",
            )
        expected_mode = result.mission_result.mission.mode if result.mission_result is not None else result.execution_posture.mode
        errors: list[str] = []
        if result.execution_posture.mission_id != result.mission_id:
            errors.append("posture_mission_mismatch")
        if result.execution_posture.mode != expected_mode:
            errors.append("posture_mode_mismatch")
        return CoreGateCheck(
            name="execution_posture_matches_authority",
            kind=CoreGateCheckKind.RISK,
            passed=not errors,
            message="Execution posture matches mission authority." if not errors else "Execution posture diverges from mission authority.",
            details={
                "errors": errors,
                "posture_mode": result.execution_posture.mode.value,
                "expected_mode": expected_mode.value,
            },
        )

    @staticmethod
    def _mission_risk_route_decisions(result: AgentRunResult) -> CoreGateCheck:
        if result.mission_result is None:
            return CoreGateCheck(
                name="mission_risk_route_decisions",
                kind=CoreGateCheckKind.RISK,
                passed=True,
                message="Run has no mission result requiring mission risk-route decisions.",
            )
        errors = CoreFinalGate._mission_risk_route_errors(result.mission_result)
        return CoreGateCheck(
            name="mission_risk_route_decisions",
            kind=CoreGateCheckKind.RISK,
            passed=not errors,
            message="Mission actions include posture-aware risk-route decisions." if not errors else "Mission risk-route decision contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _mission_risk_route_errors(mission_result: MissionRunResult) -> list[str]:
        events = mission_result.trace_events
        expected_posture = mission_result.mission.mode.value
        routed_indices = {
            event.action_id: index
            for index, event in enumerate(events)
            if event.event_type == MissionTraceEventType.ACTION_ROUTED and event.action_id
        }
        executed_indices = {
            event.action_id: index
            for index, event in enumerate(events)
            if event.event_type == MissionTraceEventType.ACTION_EXECUTED and event.action_id
        }
        decisions_by_action: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        errors: list[str] = []

        for index, event in enumerate(events):
            if event.event_type != MissionTraceEventType.RISK_ROUTE_DECIDED:
                continue
            if not event.action_id:
                errors.append(f"risk_route_missing_action_id_{index}")
                continue
            decisions_by_action.setdefault(event.action_id, []).append((index, event.result))
            result_payload = event.result
            route = result_payload.get("route")
            posture = result_payload.get("posture")
            risk_score = result_payload.get("risk_score")
            applied_threshold = result_payload.get("applied_threshold")
            blocking_rule = result_payload.get("blocking_rule")
            if route not in {item.value for item in MissionActionRoute}:
                errors.append(f"risk_route_invalid_route_{index}")
            if posture != expected_posture:
                errors.append(f"risk_route_posture_mismatch_{event.action_id}")
            if not isinstance(risk_score, (int, float)):
                errors.append(f"risk_route_missing_score_{event.action_id}")
            if route in {MissionActionRoute.AUTO_EXECUTE.value, MissionActionRoute.LOG_AND_CONTINUE.value}:
                if blocking_rule:
                    errors.append(f"continuation_route_has_blocking_rule_{event.action_id}")
                if not isinstance(applied_threshold, (int, float)):
                    errors.append(f"continuation_route_missing_threshold_{event.action_id}")
                elif isinstance(risk_score, (int, float)) and risk_score > applied_threshold:
                    errors.append(f"continuation_route_exceeds_threshold_{event.action_id}")

        if mission_result.success and not decisions_by_action:
            errors.append("successful_mission_missing_risk_route_decisions")
        for action_id, route_index in routed_indices.items():
            if action_id not in decisions_by_action:
                errors.append(f"routed_action_missing_risk_decision_{action_id}")
                continue
            if len(decisions_by_action[action_id]) != 1:
                errors.append(f"duplicate_risk_decision_{action_id}")
            if decisions_by_action[action_id][0][0] < route_index:
                errors.append(f"risk_decision_before_action_routed_{action_id}")
        for action_id, decisions in decisions_by_action.items():
            if action_id not in routed_indices:
                errors.append(f"risk_decision_without_action_routed_{action_id}")
            executed_index = executed_indices.get(action_id)
            if executed_index is not None and any(decision_index > executed_index for decision_index, _ in decisions):
                errors.append(f"risk_decision_after_action_executed_{action_id}")
        for action_id, executed_index in executed_indices.items():
            route_index = routed_indices.get(action_id)
            if route_index is None:
                errors.append(f"executed_action_missing_action_routed_{action_id}")
            elif route_index > executed_index:
                errors.append(f"executed_action_before_action_routed_{action_id}")
            decisions = decisions_by_action.get(action_id, [])
            if not decisions:
                errors.append(f"executed_action_missing_risk_decision_{action_id}")
                continue
            decision_index, decision_payload = decisions[0]
            if decision_index > executed_index:
                errors.append(f"executed_action_before_risk_decision_{action_id}")
            if decision_payload.get("route") not in {MissionActionRoute.AUTO_EXECUTE.value, MissionActionRoute.LOG_AND_CONTINUE.value}:
                errors.append(f"executed_action_without_continuation_route_{action_id}")
        return errors

    @staticmethod
    def _controlled_capability_receipts(result: AgentRunResult) -> CoreGateCheck:
        execution_events = {
            str(event.payload.get("receipt_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.CONTROLLED_CAPABILITY_EXECUTED and event.payload.get("receipt_id")
        }
        rejected_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.CONTROLLED_CAPABILITY_REJECTED
        }
        errors: list[str] = []
        execution_receipt_ids = [
            str(event.payload.get("receipt_id"))
            for event in result.trace
            if event.event_type == AgentEventType.CONTROLLED_CAPABILITY_EXECUTED and event.payload.get("receipt_id")
        ]
        duplicate_execution_receipts = sorted(
            receipt_id
            for receipt_id in set(execution_receipt_ids)
            if execution_receipt_ids.count(receipt_id) > 1
        )
        for receipt_id in duplicate_execution_receipts:
            errors.append(f"duplicate_controlled_execution_receipt_event_{receipt_id}")
        result_receipt_id_list = [
            str(item.get("receipt", {}).get("id"))
            for item in result.controlled_capability_results
            if item.get("accepted") and isinstance(item.get("receipt"), dict)
        ]
        duplicate_result_receipts = sorted(
            receipt_id
            for receipt_id in set(result_receipt_id_list)
            if result_receipt_id_list.count(receipt_id) > 1
        )
        for receipt_id in duplicate_result_receipts:
            errors.append(f"duplicate_controlled_result_receipt_{receipt_id}")
        for index, item in enumerate(result.controlled_capability_results):
            if item.get("accepted") and item.get("browser_trace_event_id"):
                continue
            if not item.get("accepted"):
                trace_id = str(item.get("trace_event_id") or "")
                if not trace_id:
                    errors.append(f"rejected_controlled_result_missing_trace_{index}")
                    continue
                event = rejected_events.get(trace_id)
                if event is None:
                    errors.append(f"rejected_controlled_result_trace_missing_{index}")
                    continue
                if event.payload.get("reason") != item.get("reason"):
                    errors.append(f"rejected_controlled_result_reason_mismatch_{index}")
                continue
            receipt = item.get("receipt")
            if not isinstance(receipt, dict):
                errors.append(f"missing_receipt_{index}")
                continue
            receipt_id = str(receipt.get("id") or "")
            artifact_path = str(receipt.get("artifact_path") or "")
            path = PurePosixPath(artifact_path.replace("\\", "/"))
            required = (
                "mission_id",
                "tool_call_id",
                "canonical_call_hash",
                "tool_id",
                "action",
                "policy_trace_id",
                "capture_trace_id",
                "artifact_id",
                "artifact_path",
                "artifact_sha256",
                "rollback_strategy",
            )
            missing = [key for key in required if not receipt.get(key)]
            if missing:
                errors.append(f"incomplete_receipt_{index}:{','.join(missing)}")
            if receipt.get("mission_id") != result.mission_id:
                errors.append(f"receipt_mission_mismatch_{index}")
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"receipt_path_out_of_scope_{index}")
            if receipt.get("reversible") is not True:
                errors.append(f"receipt_not_reversible_{index}")
            if receipt.get("rollback_strategy") != "delete_captured_artifact_if_hash_matches":
                errors.append(f"receipt_unrecognized_rollback_strategy_{index}")
            event = execution_events.get(receipt_id)
            if event is None:
                errors.append(f"receipt_without_execution_event_{index}")
                continue
            if event.payload.get("artifact_sha256") != receipt.get("artifact_sha256"):
                errors.append(f"receipt_hash_event_mismatch_{index}")
            if event.payload.get("policy_trace_id") != receipt.get("policy_trace_id"):
                errors.append(f"receipt_policy_trace_event_mismatch_{index}")
            if receipt.get("policy_trace_id") not in event.trace_refs:
                errors.append(f"receipt_policy_trace_ref_missing_{index}")
            if receipt.get("capture_trace_id") not in event.trace_refs:
                errors.append(f"receipt_capture_trace_ref_missing_{index}")
            if event.payload.get("tool_call_id") != receipt.get("tool_call_id"):
                errors.append(f"receipt_tool_call_event_mismatch_{index}")
            if event.payload.get("canonical_call_hash") != receipt.get("canonical_call_hash"):
                errors.append(f"receipt_canonical_hash_event_mismatch_{index}")
            if event.payload.get("artifact_id") != receipt.get("artifact_id"):
                errors.append(f"receipt_artifact_event_mismatch_{index}")
        result_receipt_ids = set(result_receipt_id_list)
        missing_result_receipts = sorted(set(execution_events) - result_receipt_ids)
        for receipt_id in missing_result_receipts:
            errors.append(f"execution_event_without_result_receipt_{receipt_id}")
        result_rejection_event_ids = {
            str(item.get("trace_event_id"))
            for item in result.controlled_capability_results
            if item.get("accepted") is not True and item.get("trace_event_id")
        }
        missing_result_rejections = sorted(set(rejected_events) - result_rejection_event_ids)
        for event_id in missing_result_rejections:
            errors.append(f"rejection_event_without_result_{event_id}")
        return CoreGateCheck(
            name="controlled_capability_receipts",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Controlled capability executions include scoped receipts." if not errors else "Controlled capability receipt contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_capability_receipts(result: AgentRunResult) -> CoreGateCheck:
        url_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_URL_CLASSIFIED
        }
        policy_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.TOOL_POLICY_DECIDED
        }
        capture_events = {
            event.id: event
            for event in result.trace
            if event.event_type
            in {
                AgentEventType.BROWSER_EVIDENCE_COLLECTED,
                AgentEventType.BROWSER_SNAPSHOT_CAPTURED,
                AgentEventType.BROWSER_INTERACTION_EXECUTED,
                AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED,
                AgentEventType.BROWSER_DOWNLOAD_QUARANTINED,
                AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED,
                AgentEventType.BROWSER_PRIVATE_SESSION_STARTED,
                AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED,
                AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED,
                AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED,
                AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED,
                AgentEventType.BROWSER_HAR_BODY_CAPTURED,
            }
        }
        artifact_events = {
            str(event.payload.get("artifact_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
        }
        errors: list[str] = []

        for event_id, event in capture_events.items():
            payload = event.payload
            receipt_id = payload.get("receipt_id")
            url_trace_id = payload.get("url_policy_trace_id")
            if not receipt_id:
                errors.append(f"browser_event_missing_receipt_{event_id}")
            no_url_policy_required = {
                AgentEventType.BROWSER_INTERACTION_EXECUTED,
                AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED,
                AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED,
                AgentEventType.BROWSER_PRIVATE_SESSION_STARTED,
                AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED,
                AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED,
                AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED,
                AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED,
                AgentEventType.BROWSER_HAR_BODY_CAPTURED,
            }
            if event.event_type in no_url_policy_required:
                url_trace_id = None
            elif not url_trace_id or url_trace_id not in url_events:
                errors.append(f"browser_event_missing_url_policy_{event_id}")
            elif url_trace_id:
                url_event = url_events[url_trace_id]
                if url_trace_id not in event.trace_refs:
                    errors.append(f"browser_event_missing_url_trace_ref_{event_id}")
                if url_event.sequence >= event.sequence:
                    errors.append(f"browser_event_url_policy_order_invalid_{event_id}")

            artifact_pairs: list[tuple[str, str | None]] = []
            if event.event_type == AgentEventType.BROWSER_EVIDENCE_COLLECTED:
                artifact_pairs.append((str(payload.get("artifact_id") or ""), payload.get("artifact_sha256")))
            elif event.event_type == AgentEventType.BROWSER_SNAPSHOT_CAPTURED:
                artifact_pairs.append((str(payload.get("snapshot_artifact_id") or ""), payload.get("snapshot_artifact_sha256")))
                if payload.get("screenshot_artifact_id"):
                    artifact_pairs.append((str(payload.get("screenshot_artifact_id") or ""), payload.get("screenshot_artifact_sha256")))
                if payload.get("pdf_artifact_id"):
                    artifact_pairs.append((str(payload.get("pdf_artifact_id") or ""), payload.get("pdf_artifact_sha256")))
                if not payload.get("accessibility_snapshot_sha256"):
                    errors.append(f"browser_snapshot_missing_accessibility_hash_{event_id}")
                if not payload.get("accessibility_page_sha256"):
                    errors.append(f"browser_snapshot_missing_accessibility_page_hash_{event_id}")
                if not isinstance(payload.get("accessibility_ref_count"), int):
                    errors.append(f"browser_snapshot_invalid_accessibility_ref_count_{event_id}")
                if not isinstance(payload.get("accessibility_interactive_count"), int):
                    errors.append(f"browser_snapshot_invalid_accessibility_interactive_count_{event_id}")
                if not isinstance(payload.get("accessibility_ref_ids"), list):
                    errors.append(f"browser_snapshot_invalid_accessibility_ref_ids_{event_id}")
                screenshot_metadata = payload.get("screenshot_metadata")
                if payload.get("screenshot_artifact_id") and not isinstance(screenshot_metadata, dict):
                    errors.append(f"browser_snapshot_invalid_screenshot_metadata_{event_id}")
                elif payload.get("screenshot_artifact_id"):
                    if not isinstance(screenshot_metadata.get("normalized"), bool):
                        errors.append(f"browser_snapshot_invalid_screenshot_normalized_{event_id}")
                    if not isinstance(screenshot_metadata.get("bytes"), int):
                        errors.append(f"browser_snapshot_invalid_screenshot_bytes_{event_id}")
                    if not screenshot_metadata.get("content_type"):
                        errors.append(f"browser_snapshot_missing_screenshot_content_type_{event_id}")
                pdf_metadata = payload.get("pdf_metadata")
                if payload.get("pdf_artifact_id"):
                    if not isinstance(pdf_metadata, dict):
                        errors.append(f"browser_snapshot_invalid_pdf_metadata_{event_id}")
                    else:
                        if pdf_metadata.get("content_type") != "application/pdf":
                            errors.append(f"browser_snapshot_pdf_content_type_invalid_{event_id}")
                        if not isinstance(pdf_metadata.get("bytes"), int):
                            errors.append(f"browser_snapshot_pdf_bytes_invalid_{event_id}")
                element_screenshots = payload.get("element_screenshot_artifacts")
                if element_screenshots is None:
                    element_screenshots = []
                if not isinstance(element_screenshots, list):
                    errors.append(f"browser_snapshot_element_screenshots_invalid_{event_id}")
                    element_screenshots = []
                for item_index, item in enumerate(element_screenshots):
                    if not isinstance(item, dict):
                        errors.append(f"browser_snapshot_element_screenshot_invalid_{event_id}_{item_index}")
                        continue
                    artifact_pairs.append((str(item.get("artifact_id") or ""), item.get("artifact_sha256")))
                    if not item.get("ref_id"):
                        errors.append(f"browser_snapshot_element_screenshot_missing_ref_{event_id}_{item_index}")
                    item_meta = item.get("screenshot_metadata")
                    if not isinstance(item_meta, dict):
                        errors.append(f"browser_snapshot_element_screenshot_metadata_invalid_{event_id}_{item_index}")
                    elif not isinstance(item_meta.get("normalized"), bool):
                        errors.append(f"browser_snapshot_element_screenshot_normalized_invalid_{event_id}_{item_index}")
                network_ledger = payload.get("network_ledger")
                network_ledger_sha256 = payload.get("network_ledger_sha256")
                if not network_ledger_sha256:
                    errors.append(f"browser_snapshot_missing_network_ledger_hash_{event_id}")
                if not isinstance(network_ledger, dict):
                    errors.append(f"browser_snapshot_missing_network_ledger_{event_id}")
                elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                    errors.append(f"browser_snapshot_network_ledger_hash_mismatch_{event_id}")
                elif (
                    payload.get("network_request_count") != _list_len(network_ledger.get("requests", []))
                    or payload.get("network_response_count") != _list_len(network_ledger.get("responses", []))
                    or payload.get("network_failure_count") != _list_len(network_ledger.get("failures", []))
                    or payload.get("console_message_count") != _list_len(network_ledger.get("console", []))
                    or payload.get("page_error_count") != _list_len(network_ledger.get("page_errors", []))
                ):
                    errors.append(f"browser_snapshot_network_ledger_count_mismatch_{event_id}")
                for field_name in (
                    "network_request_count",
                    "network_response_count",
                    "network_failure_count",
                    "console_message_count",
                    "page_error_count",
                ):
                    if not isinstance(payload.get(field_name), int):
                        errors.append(f"browser_snapshot_invalid_{field_name}_{event_id}")
                if not isinstance(payload.get("network_ledger_truncated"), bool):
                    errors.append(f"browser_snapshot_invalid_network_ledger_truncated_{event_id}")
                if not isinstance(payload.get("browser_health"), dict):
                    errors.append(f"browser_snapshot_invalid_browser_health_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_INTERACTION_EXECUTED:
                artifact_pairs.append((str(payload.get("after_snapshot_artifact_id") or ""), payload.get("after_snapshot_artifact_sha256")))
                artifact_pairs.append((str(payload.get("after_screenshot_artifact_id") or ""), payload.get("after_screenshot_artifact_sha256")))
                if not payload.get("plan_trace_event_id"):
                    errors.append(f"browser_interaction_missing_plan_trace_{event_id}")
                if not payload.get("before_snapshot_trace_event_id"):
                    errors.append(f"browser_interaction_missing_before_snapshot_trace_{event_id}")
                if payload.get("same_origin") is not True:
                    errors.append(f"browser_interaction_not_same_origin_{event_id}")
                network_ledger = payload.get("network_ledger")
                network_ledger_sha256 = payload.get("network_ledger_sha256")
                if not network_ledger_sha256:
                    errors.append(f"browser_interaction_missing_network_ledger_hash_{event_id}")
                if not isinstance(network_ledger, dict):
                    errors.append(f"browser_interaction_missing_network_ledger_{event_id}")
                elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                    errors.append(f"browser_interaction_network_ledger_hash_mismatch_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED:
                artifact_pairs.append((str(payload.get("post_submit_snapshot_artifact_id") or ""), payload.get("post_submit_snapshot_artifact_sha256")))
                if payload.get("post_submit_screenshot_artifact_id"):
                    artifact_pairs.append((str(payload.get("post_submit_screenshot_artifact_id") or ""), payload.get("post_submit_screenshot_artifact_sha256")))
                if payload.get("authority_class") != "browser_form_submit":
                    errors.append(f"browser_form_submit_authority_class_invalid_{event_id}")
                if not payload.get("authority_grant_id"):
                    errors.append(f"browser_form_submit_missing_authority_grant_{event_id}")
                if not payload.get("compiled_intent_trace_id"):
                    errors.append(f"browser_form_submit_missing_compiled_intent_{event_id}")
                if not payload.get("context_pack_id"):
                    errors.append(f"browser_form_submit_missing_context_pack_{event_id}")
                if not payload.get("plan_trace_event_id"):
                    errors.append(f"browser_form_submit_missing_plan_trace_{event_id}")
                if not payload.get("before_snapshot_trace_event_id"):
                    errors.append(f"browser_form_submit_missing_before_snapshot_trace_{event_id}")
                if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
                    errors.append(f"browser_form_submit_cross_origin_not_authorized_{event_id}")
                network_ledger = payload.get("network_ledger")
                network_ledger_sha256 = payload.get("network_ledger_sha256")
                if not network_ledger_sha256:
                    errors.append(f"browser_form_submit_missing_network_ledger_hash_{event_id}")
                if not isinstance(network_ledger, dict):
                    errors.append(f"browser_form_submit_missing_network_ledger_{event_id}")
                elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                    errors.append(f"browser_form_submit_network_ledger_hash_mismatch_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_DOWNLOAD_QUARANTINED:
                artifact_pairs.append((str(payload.get("artifact_id") or ""), payload.get("artifact_sha256")))
                if payload.get("authority_class") != "browser_download_quarantine":
                    errors.append(f"browser_download_authority_class_invalid_{event_id}")
                if not payload.get("authority_grant_id"):
                    errors.append(f"browser_download_missing_authority_grant_{event_id}")
                if not payload.get("compiled_intent_trace_id"):
                    errors.append(f"browser_download_missing_compiled_intent_{event_id}")
                if not payload.get("context_pack_id"):
                    errors.append(f"browser_download_missing_context_pack_{event_id}")
                if payload.get("promoted") is not False:
                    errors.append(f"browser_download_promoted_in_quarantine_event_{event_id}")
                if payload.get("mime_type_allowed") is not True:
                    errors.append(f"browser_download_mime_not_allowed_{event_id}")
                if not isinstance(payload.get("size_bytes"), int) or not isinstance(payload.get("max_bytes"), int):
                    errors.append(f"browser_download_invalid_size_metadata_{event_id}")
                elif payload.get("size_bytes") > payload.get("max_bytes"):
                    errors.append(f"browser_download_size_exceeds_max_{event_id}")
                if not str(payload.get("quarantine_relative_path") or "").startswith("browser/download_quarantine/"):
                    errors.append(f"browser_download_quarantine_path_invalid_{event_id}")
                if not payload.get("download_sha256"):
                    errors.append(f"browser_download_missing_download_hash_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED:
                artifact_pairs.append((str(payload.get("source_artifact_id") or ""), payload.get("source_artifact_sha256")))
                artifact_pairs.append((str(payload.get("post_upload_snapshot_artifact_id") or ""), payload.get("post_upload_snapshot_artifact_sha256")))
                if payload.get("post_upload_screenshot_artifact_id"):
                    artifact_pairs.append((str(payload.get("post_upload_screenshot_artifact_id") or ""), payload.get("post_upload_screenshot_artifact_sha256")))
                if payload.get("authority_class") != "browser_upload_authorized":
                    errors.append(f"browser_upload_authority_class_invalid_{event_id}")
                if not payload.get("authority_grant_id"):
                    errors.append(f"browser_upload_missing_authority_grant_{event_id}")
                if not payload.get("compiled_intent_trace_id"):
                    errors.append(f"browser_upload_missing_compiled_intent_{event_id}")
                if not payload.get("context_pack_id"):
                    errors.append(f"browser_upload_missing_context_pack_{event_id}")
                if not payload.get("plan_trace_event_id"):
                    errors.append(f"browser_upload_missing_plan_trace_{event_id}")
                if not payload.get("before_snapshot_trace_event_id"):
                    errors.append(f"browser_upload_missing_before_snapshot_trace_{event_id}")
                if not payload.get("source_artifact_id") or not payload.get("source_artifact_sha256"):
                    errors.append(f"browser_upload_missing_source_artifact_{event_id}")
                if not payload.get("upload_ref_id"):
                    errors.append(f"browser_upload_missing_ref_{event_id}")
                if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
                    errors.append(f"browser_upload_cross_origin_not_authorized_{event_id}")
                network_ledger = payload.get("network_ledger")
                network_ledger_sha256 = payload.get("network_ledger_sha256")
                if not network_ledger_sha256:
                    errors.append(f"browser_upload_missing_network_ledger_hash_{event_id}")
                if not isinstance(network_ledger, dict):
                    errors.append(f"browser_upload_missing_network_ledger_{event_id}")
                elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                    errors.append(f"browser_upload_network_ledger_hash_mismatch_{event_id}")
            elif event.event_type in {AgentEventType.BROWSER_PRIVATE_SESSION_STARTED, AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED}:
                artifact_pairs.append((str(payload.get("receipt_artifact_id") or ""), payload.get("receipt_artifact_sha256")))
                if payload.get("authority_class") != "browser_private_session":
                    errors.append(f"browser_private_session_authority_class_invalid_{event_id}")
                if not payload.get("session_id") or not payload.get("profile_id"):
                    errors.append(f"browser_private_session_missing_session_ids_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED:
                artifact_pairs.append((str(payload.get("post_login_snapshot_artifact_id") or ""), payload.get("post_login_snapshot_artifact_sha256")))
                if payload.get("authority_class") != "browser_login_authority":
                    errors.append(f"browser_login_authority_class_invalid_{event_id}")
                if payload.get("login_success") is not True:
                    errors.append(f"browser_login_not_successful_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED:
                artifact_pairs.append((str(payload.get("summary_artifact_id") or ""), payload.get("summary_artifact_sha256")))
                if payload.get("authority_class") != "browser_cookie_storage_contract":
                    errors.append(f"browser_cookie_storage_authority_class_invalid_{event_id}")
                if payload.get("redaction_applied") is not True or payload.get("raw_value_exposed") is True:
                    errors.append(f"browser_cookie_storage_redaction_invalid_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED:
                artifact_pairs.append((str(payload.get("result_artifact_id") or ""), payload.get("result_artifact_sha256")))
                if payload.get("authority_class") != "browser_js_evaluate_sandboxed":
                    errors.append(f"browser_js_authority_class_invalid_{event_id}")
                if payload.get("script_hash_allowed") is not True or payload.get("network_calls_blocked") is not True:
                    errors.append(f"browser_js_contract_flags_invalid_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_HAR_BODY_CAPTURED:
                artifact_pairs.append((str(payload.get("har_artifact_id") or ""), payload.get("har_artifact_sha256")))
                if payload.get("authority_class") != "browser_har_body_capture":
                    errors.append(f"browser_har_authority_class_invalid_{event_id}")
                if payload.get("redaction_applied") is not True:
                    errors.append(f"browser_har_redaction_missing_{event_id}")
            for artifact_id, expected_hash in artifact_pairs:
                if not artifact_id:
                    errors.append(f"browser_event_missing_artifact_{event_id}")
                    continue
                artifact_event = artifact_events.get(artifact_id)
                if artifact_event is None:
                    errors.append(f"browser_event_artifact_trace_missing_{event_id}_{artifact_id}")
                    continue
                if expected_hash and artifact_event.payload.get("sha256") != expected_hash:
                    errors.append(f"browser_event_artifact_hash_mismatch_{event_id}_{artifact_id}")
                if artifact_event.sequence >= event.sequence:
                    errors.append(f"browser_event_artifact_order_invalid_{event_id}_{artifact_id}")

        for index, item in enumerate(result.controlled_capability_results):
            if not item.get("accepted") or not item.get("browser_trace_event_id"):
                continue
            browser_trace_event_id = str(item.get("browser_trace_event_id"))
            event = capture_events.get(browser_trace_event_id)
            if event is None:
                errors.append(f"browser_result_trace_missing_{index}")
                continue
            if item.get("trace_event_id") != browser_trace_event_id:
                errors.append(f"browser_result_trace_alias_mismatch_{index}")
            policy_trace_id = str(item.get("policy_trace_id") or "")
            policy_event = policy_events.get(policy_trace_id)
            if policy_event is None:
                errors.append(f"browser_result_policy_trace_missing_{index}")
            else:
                if policy_event.sequence >= event.sequence:
                    errors.append(f"browser_result_policy_order_invalid_{index}")
                policy_payload = policy_event.payload
                if policy_payload.get("tool_id") != item.get("tool_id"):
                    errors.append(f"browser_result_policy_tool_mismatch_{index}")
                if policy_payload.get("action") != item.get("action"):
                    errors.append(f"browser_result_policy_action_mismatch_{index}")
                if policy_payload.get("allowed") is not True:
                    errors.append(f"browser_result_policy_not_allowed_{index}")
            if event.payload.get("receipt_id") != item.get("receipt_id"):
                errors.append(f"browser_result_receipt_mismatch_{index}")
            event_artifact_ids = {
                str(value)
                for value in (
                    event.payload.get("artifact_id"),
                    event.payload.get("snapshot_artifact_id"),
                    event.payload.get("screenshot_artifact_id"),
                    event.payload.get("pdf_artifact_id"),
                    event.payload.get("after_snapshot_artifact_id"),
                    event.payload.get("after_screenshot_artifact_id"),
                    event.payload.get("post_submit_snapshot_artifact_id"),
                    event.payload.get("post_submit_screenshot_artifact_id"),
                    event.payload.get("post_upload_snapshot_artifact_id"),
                    event.payload.get("post_upload_screenshot_artifact_id"),
                    event.payload.get("receipt_artifact_id"),
                    event.payload.get("post_login_snapshot_artifact_id"),
                    event.payload.get("summary_artifact_id"),
                    event.payload.get("result_artifact_id"),
                    event.payload.get("har_artifact_id"),
                    event.payload.get("source_artifact_id"),
                )
                if value
            }
            for element_item in event.payload.get("element_screenshot_artifacts") or []:
                if isinstance(element_item, dict) and element_item.get("artifact_id"):
                    event_artifact_ids.add(str(element_item.get("artifact_id")))
            if not set(item.get("artifact_ids") or []).issubset(event_artifact_ids):
                errors.append(f"browser_result_artifact_mismatch_{index}")
            if not item.get("receipt_id"):
                errors.append(f"browser_result_missing_receipt_{index}")
            if not item.get("artifact_ids"):
                errors.append(f"browser_result_missing_artifacts_{index}")

        return CoreGateCheck(
            name="browser_capability_receipts",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Browser capability events are bound to URL policy, artifacts, and receipts." if not errors else "Browser capability receipt contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_interaction_dry_run_contract(result: AgentRunResult) -> CoreGateCheck:
        snapshot_events = [
            event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_SNAPSHOT_CAPTURED
        ]
        snapshots_by_hash = {
            str(event.payload.get("accessibility_snapshot_sha256")): event
            for event in snapshot_events
            if event.payload.get("accessibility_snapshot_sha256")
        }
        plan_events = [
            event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_INTERACTION_PLAN_CREATED
        ]
        errors: list[str] = []

        for event in result.trace:
            if event.event_type != AgentEventType.CONTROLLED_CAPABILITY_EXECUTED:
                continue
            action = str(event.payload.get("action") or "").lower()
            if action in {
                "browser_click",
                "browser_type",
                "browser_fill",
                "browser_select",
                "browser_press",
                "browser_hover",
                "browser_submit",
                "browser_upload",
                "browser_download",
                "browser_interaction_execute",
            }:
                errors.append(f"browser_real_interaction_event_in_p3g_{event.id}")

        for event in plan_events:
            payload = event.payload
            event_id = event.id
            plan = payload.get("plan")
            plan_sha256 = payload.get("plan_sha256")
            if not payload.get("dry_run_only"):
                errors.append(f"browser_interaction_plan_not_dry_run_{event_id}")
            if not isinstance(plan, dict):
                errors.append(f"browser_interaction_plan_missing_payload_{event_id}")
                continue
            if plan.get("dry_run_only") is not True:
                errors.append(f"browser_interaction_plan_payload_not_dry_run_{event_id}")
            if plan.get("plan_sha256") != plan_sha256:
                errors.append(f"browser_interaction_plan_hash_payload_mismatch_{event_id}")
            if not verify_browser_interaction_plan_hash(plan, str(plan_sha256 or "")):
                errors.append(f"browser_interaction_plan_hash_invalid_{event_id}")

            snapshot_hash = str(plan.get("snapshot_sha256") or "")
            page_hash = str(plan.get("page_sha256") or "")
            snapshot_event = snapshots_by_hash.get(snapshot_hash)
            if snapshot_event is None:
                errors.append(f"browser_interaction_plan_snapshot_missing_{event_id}")
                continue
            if snapshot_event.sequence >= event.sequence:
                errors.append(f"browser_interaction_plan_snapshot_order_invalid_{event_id}")
            if snapshot_event.id not in event.trace_refs:
                errors.append(f"browser_interaction_plan_missing_snapshot_trace_ref_{event_id}")
            if snapshot_event.payload.get("accessibility_page_sha256") != page_hash:
                errors.append(f"browser_interaction_plan_page_hash_mismatch_{event_id}")

            ref_ids = snapshot_event.payload.get("accessibility_ref_ids")
            if not isinstance(ref_ids, list):
                errors.append(f"browser_interaction_plan_snapshot_refs_unavailable_{event_id}")
            else:
                allowed_refs = {str(ref_id) for ref_id in ref_ids}
                for ref_id in plan.get("required_ref_ids", []):
                    if str(ref_id) not in allowed_refs:
                        errors.append(f"browser_interaction_plan_unknown_ref_{event_id}_{ref_id}")

            intents = [str(intent).lower() for intent in payload.get("intents", [])]
            plan_steps = plan.get("steps", [])
            if not isinstance(plan_steps, list):
                errors.append(f"browser_interaction_plan_steps_invalid_{event_id}")
                plan_steps = []
            step_intents = [str(step.get("intent", "")).lower() for step in plan_steps if isinstance(step, dict)]
            for intent in [*intents, *step_intents]:
                if intent in P3G_FORBIDDEN_INTERACTION_NAMES:
                    errors.append(f"browser_interaction_plan_forbidden_intent_{event_id}_{intent}")
                if any(token in intent for token in P3G_FORBIDDEN_INTERACTION_NAMES):
                    errors.append(f"browser_interaction_plan_forbidden_intent_token_{event_id}_{intent}")

        return CoreGateCheck(
            name="browser_interaction_dry_run_contract",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Browser interaction plans are dry-run, snapshot-bound, and ref-verified." if not errors else "Browser interaction dry-run contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_interaction_execution_contract(result: AgentRunResult) -> CoreGateCheck:
        plan_events = {
            str(event.payload.get("plan_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_INTERACTION_PLAN_CREATED and event.payload.get("plan_id")
        }
        snapshot_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_SNAPSHOT_CAPTURED
        }
        artifact_events = {
            str(event.payload.get("artifact_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
        }
        allowed_intents = {intent.value for intent in P3H_ALLOWED_EXECUTION_INTENTS}
        errors: list[str] = []

        for event in result.trace:
            if event.event_type != AgentEventType.BROWSER_INTERACTION_EXECUTED:
                continue
            event_id = event.id
            payload = event.payload
            plan_id = str(payload.get("plan_id") or "")
            plan_sha256 = str(payload.get("plan_sha256") or "")
            plan = payload.get("plan")
            plan_event = plan_events.get(plan_id)
            if plan_event is None:
                errors.append(f"browser_interaction_execution_plan_missing_{event_id}")
            elif plan_event.sequence >= event.sequence:
                errors.append(f"browser_interaction_execution_plan_order_invalid_{event_id}")
            elif plan_event.id not in event.trace_refs:
                errors.append(f"browser_interaction_execution_missing_plan_trace_ref_{event_id}")
            if not isinstance(plan, dict):
                errors.append(f"browser_interaction_execution_plan_payload_missing_{event_id}")
            elif not verify_browser_interaction_plan_hash(plan, plan_sha256):
                errors.append(f"browser_interaction_execution_plan_hash_invalid_{event_id}")
            elif plan_event is not None and plan_event.payload.get("plan_sha256") != plan_sha256:
                errors.append(f"browser_interaction_execution_plan_hash_mismatch_{event_id}")

            before_snapshot_trace = str(payload.get("before_snapshot_trace_event_id") or "")
            before_snapshot_event = snapshot_events.get(before_snapshot_trace)
            if before_snapshot_event is None:
                errors.append(f"browser_interaction_execution_before_snapshot_missing_{event_id}")
            else:
                if before_snapshot_event.sequence >= event.sequence:
                    errors.append(f"browser_interaction_execution_before_snapshot_order_invalid_{event_id}")
                if before_snapshot_trace not in event.trace_refs:
                    errors.append(f"browser_interaction_execution_missing_before_snapshot_trace_ref_{event_id}")
                if before_snapshot_event.payload.get("accessibility_snapshot_sha256") != payload.get("before_snapshot_sha256"):
                    errors.append(f"browser_interaction_execution_before_snapshot_hash_mismatch_{event_id}")
                if before_snapshot_event.payload.get("accessibility_page_sha256") != payload.get("before_page_sha256"):
                    errors.append(f"browser_interaction_execution_before_page_hash_mismatch_{event_id}")

            if payload.get("same_origin") is not True:
                errors.append(f"browser_interaction_execution_same_origin_missing_{event_id}")
            if not payload.get("receipt_id"):
                errors.append(f"browser_interaction_execution_receipt_missing_{event_id}")
            if not payload.get("after_snapshot_sha256") or not payload.get("after_page_sha256"):
                errors.append(f"browser_interaction_execution_after_hash_missing_{event_id}")

            intents = [str(intent).lower() for intent in payload.get("executed_intents", [])]
            if not intents:
                errors.append(f"browser_interaction_execution_intents_missing_{event_id}")
            for intent in intents:
                if intent not in allowed_intents:
                    errors.append(f"browser_interaction_execution_intent_not_delegated_{event_id}_{intent}")
                if any(token in intent for token in P3G_FORBIDDEN_INTERACTION_NAMES):
                    errors.append(f"browser_interaction_execution_forbidden_intent_token_{event_id}_{intent}")

            snapshot_artifact_id = str(payload.get("after_snapshot_artifact_id") or "")
            snapshot_artifact = artifact_events.get(snapshot_artifact_id)
            if snapshot_artifact is None:
                errors.append(f"browser_interaction_execution_after_artifact_missing_{event_id}")
            else:
                if snapshot_artifact.sequence >= event.sequence:
                    errors.append(f"browser_interaction_execution_after_artifact_order_invalid_{event_id}")
                if payload.get("after_snapshot_artifact_sha256") != snapshot_artifact.payload.get("sha256"):
                    errors.append(f"browser_interaction_execution_after_artifact_hash_mismatch_{event_id}")

            screenshot_artifact_id = str(payload.get("after_screenshot_artifact_id") or "")
            if screenshot_artifact_id:
                screenshot_artifact = artifact_events.get(screenshot_artifact_id)
                if screenshot_artifact is None:
                    errors.append(f"browser_interaction_execution_after_screenshot_missing_{event_id}")
                elif payload.get("after_screenshot_artifact_sha256") != screenshot_artifact.payload.get("sha256"):
                    errors.append(f"browser_interaction_execution_after_screenshot_hash_mismatch_{event_id}")

            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = str(payload.get("network_ledger_sha256") or "")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_interaction_execution_network_ledger_missing_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, network_ledger_sha256):
                errors.append(f"browser_interaction_execution_network_ledger_hash_invalid_{event_id}")

        return CoreGateCheck(
            name="browser_interaction_execution_contract",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Limited browser interactions are plan-bound, authority-traced, and recaptured." if not errors else "Browser interaction execution contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_public_lifecycle_contract(result: AgentRunResult) -> CoreGateCheck:
        url_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_URL_CLASSIFIED
        }
        sessions: dict[str, dict[str, Any]] = {}
        tabs: dict[str, dict[str, Any]] = {}
        errors: list[str] = []

        lifecycle_events = {
            AgentEventType.BROWSER_PUBLIC_SESSION_STARTED,
            AgentEventType.BROWSER_PUBLIC_TAB_OPENED,
            AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED,
            AgentEventType.BROWSER_PUBLIC_TAB_CLOSED,
            AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED,
            AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED,
        }
        expected_status = {
            AgentEventType.BROWSER_PUBLIC_SESSION_STARTED: "active",
            AgentEventType.BROWSER_PUBLIC_TAB_OPENED: "active",
            AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED: "active",
            AgentEventType.BROWSER_PUBLIC_TAB_CLOSED: "closed",
            AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED: "closed",
            AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED: "rejected",
        }

        for event in result.trace:
            if event.event_type not in lifecycle_events:
                continue
            payload = event.payload
            event_id = event.id
            if str(_enum_value(payload.get("status")) or "").lower() != expected_status[event.event_type]:
                errors.append(f"browser_public_lifecycle_status_invalid_{event_id}")
            if payload.get("stateless_public") is not True:
                errors.append(f"browser_public_lifecycle_not_stateless_{event_id}")
            if payload.get("cookies_enabled") is not False:
                errors.append(f"browser_public_lifecycle_cookies_enabled_{event_id}")
            if payload.get("storage_enabled") is not False:
                errors.append(f"browser_public_lifecycle_storage_enabled_{event_id}")

            if event.event_type == AgentEventType.BROWSER_PUBLIC_LIFECYCLE_REJECTED:
                if not payload.get("action"):
                    errors.append(f"browser_public_lifecycle_rejection_missing_action_{event_id}")
                if not payload.get("reason"):
                    errors.append(f"browser_public_lifecycle_rejection_missing_reason_{event_id}")
                url_trace_id = str(payload.get("url_policy_trace_id") or "")
                if url_trace_id:
                    CoreFinalGate._browser_lifecycle_check_url_policy(
                        event=event,
                        url_events=url_events,
                        url_trace_id=url_trace_id,
                        expected_final_url=None,
                        errors=errors,
                        prefix="browser_public_lifecycle_rejection",
                        require_allowed=False,
                    )
                continue

            if not payload.get("receipt_id"):
                errors.append(f"browser_public_lifecycle_missing_receipt_{event_id}")

            if event.event_type == AgentEventType.BROWSER_PUBLIC_SESSION_STARTED:
                session_id = str(payload.get("session_id") or "")
                if not session_id:
                    errors.append(f"browser_public_session_missing_id_{event_id}")
                    continue
                if session_id in sessions:
                    errors.append(f"browser_public_session_duplicate_{event_id}_{session_id}")
                    continue
                max_tabs = payload.get("max_tabs")
                if not isinstance(max_tabs, int) or max_tabs < 1:
                    errors.append(f"browser_public_session_invalid_max_tabs_{event_id}")
                    max_tabs = 0
                sessions[session_id] = {
                    "status": "active",
                    "max_tabs": max_tabs,
                    "active_tabs": set(),
                    "sequence": event.sequence,
                }

            elif event.event_type == AgentEventType.BROWSER_PUBLIC_TAB_OPENED:
                session_id = str(payload.get("session_id") or "")
                tab_id = str(payload.get("tab_id") or "")
                session = sessions.get(session_id)
                if session is None:
                    errors.append(f"browser_public_tab_open_session_missing_{event_id}")
                    continue
                if session["status"] != "active":
                    errors.append(f"browser_public_tab_open_session_closed_{event_id}")
                active_tabs = session["active_tabs"]
                if len(active_tabs) >= int(session["max_tabs"]):
                    errors.append(f"browser_public_tab_open_limit_exceeded_{event_id}")
                if not tab_id:
                    errors.append(f"browser_public_tab_open_missing_tab_id_{event_id}")
                    continue
                if tab_id in tabs:
                    errors.append(f"browser_public_tab_duplicate_{event_id}_{tab_id}")
                    continue
                final_url = str(payload.get("final_url") or "")
                url_trace_id = str(payload.get("url_policy_trace_id") or "")
                CoreFinalGate._browser_lifecycle_check_url_policy(
                    event=event,
                    url_events=url_events,
                    url_trace_id=url_trace_id,
                    expected_final_url=final_url,
                    errors=errors,
                    prefix="browser_public_tab_open",
                )
                tabs[tab_id] = {
                    "session_id": session_id,
                    "status": "active",
                    "current_url": final_url,
                    "navigation_count": int(payload.get("navigation_count") or 0),
                    "sequence": event.sequence,
                }
                active_tabs.add(tab_id)

            elif event.event_type == AgentEventType.BROWSER_PUBLIC_TAB_NAVIGATED:
                session_id = str(payload.get("session_id") or "")
                tab_id = str(payload.get("tab_id") or "")
                session = sessions.get(session_id)
                tab = tabs.get(tab_id)
                if session is None:
                    errors.append(f"browser_public_tab_nav_session_missing_{event_id}")
                    continue
                if session["status"] != "active":
                    errors.append(f"browser_public_tab_nav_session_closed_{event_id}")
                if tab is None:
                    errors.append(f"browser_public_tab_nav_tab_missing_{event_id}")
                    continue
                if tab["session_id"] != session_id:
                    errors.append(f"browser_public_tab_nav_session_mismatch_{event_id}")
                if tab["status"] != "active":
                    errors.append(f"browser_public_tab_nav_tab_closed_{event_id}")
                if payload.get("previous_url") != tab["current_url"]:
                    errors.append(f"browser_public_tab_nav_previous_url_mismatch_{event_id}")
                navigation_count = payload.get("navigation_count")
                if not isinstance(navigation_count, int) or navigation_count != int(tab["navigation_count"]) + 1:
                    errors.append(f"browser_public_tab_nav_count_invalid_{event_id}")
                    navigation_count = int(tab["navigation_count"])
                final_url = str(payload.get("final_url") or "")
                url_trace_id = str(payload.get("url_policy_trace_id") or "")
                CoreFinalGate._browser_lifecycle_check_url_policy(
                    event=event,
                    url_events=url_events,
                    url_trace_id=url_trace_id,
                    expected_final_url=final_url,
                    errors=errors,
                    prefix="browser_public_tab_nav",
                )
                tab["current_url"] = final_url
                tab["navigation_count"] = navigation_count

            elif event.event_type == AgentEventType.BROWSER_PUBLIC_TAB_CLOSED:
                session_id = str(payload.get("session_id") or "")
                tab_id = str(payload.get("tab_id") or "")
                session = sessions.get(session_id)
                tab = tabs.get(tab_id)
                if session is None:
                    errors.append(f"browser_public_tab_close_session_missing_{event_id}")
                    continue
                if tab is None:
                    errors.append(f"browser_public_tab_close_tab_missing_{event_id}")
                    continue
                if tab["session_id"] != session_id:
                    errors.append(f"browser_public_tab_close_session_mismatch_{event_id}")
                if tab["status"] != "active":
                    errors.append(f"browser_public_tab_close_tab_not_active_{event_id}")
                if payload.get("final_url") != tab["current_url"]:
                    errors.append(f"browser_public_tab_close_url_mismatch_{event_id}")
                tab["status"] = "closed"
                session["active_tabs"].discard(tab_id)

            elif event.event_type == AgentEventType.BROWSER_PUBLIC_SESSION_CLOSED:
                session_id = str(payload.get("session_id") or "")
                session = sessions.get(session_id)
                if session is None:
                    errors.append(f"browser_public_session_close_missing_{event_id}")
                    continue
                if session["status"] != "active":
                    errors.append(f"browser_public_session_close_not_active_{event_id}")
                closed_tab_ids = payload.get("closed_tab_ids")
                if not isinstance(closed_tab_ids, list):
                    errors.append(f"browser_public_session_close_invalid_tab_ids_{event_id}")
                    closed_tab_ids = []
                active_tabs = set(session["active_tabs"])
                missing_closed = sorted(active_tabs - {str(tab_id) for tab_id in closed_tab_ids})
                if missing_closed:
                    errors.append(f"browser_public_session_close_missing_active_tabs_{event_id}:{','.join(missing_closed)}")
                for tab_id in closed_tab_ids:
                    tab = tabs.get(str(tab_id))
                    if tab is None:
                        errors.append(f"browser_public_session_close_unknown_tab_{event_id}_{tab_id}")
                        continue
                    if tab["session_id"] != session_id:
                        errors.append(f"browser_public_session_close_tab_session_mismatch_{event_id}_{tab_id}")
                    tab["status"] = "closed"
                session["active_tabs"].clear()
                session["status"] = "closed"

        return CoreGateCheck(
            name="browser_public_lifecycle_contract",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Public browser lifecycle events are stateless, URL-policy-bound, and ordered." if not errors else "Public browser lifecycle contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_reliability_supervisor_contract(result: AgentRunResult) -> CoreGateCheck:
        leases: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        supervisor_events = {
            AgentEventType.BROWSER_POOL_LEASED,
            AgentEventType.BROWSER_POOL_RELEASED,
            AgentEventType.BROWSER_HEALTH_CHECKED,
            AgentEventType.BROWSER_OPERATION_RETRIED,
            AgentEventType.BROWSER_SUPERVISOR_REJECTED,
        }
        valid_health_statuses = {"healthy", "degraded", "unavailable"}

        for event in result.trace:
            if event.event_type not in supervisor_events:
                continue
            payload = event.payload
            event_id = event.id

            if payload.get("stateless_public") is not True:
                errors.append(f"browser_supervisor_not_stateless_{event_id}")
            if payload.get("cookies_enabled") is not False:
                errors.append(f"browser_supervisor_cookies_enabled_{event_id}")
            if payload.get("storage_enabled") is not False:
                errors.append(f"browser_supervisor_storage_enabled_{event_id}")
            if payload.get("js_enabled") is not False:
                errors.append(f"browser_supervisor_js_enabled_{event_id}")
            if payload.get("downloads_enabled") is not False:
                errors.append(f"browser_supervisor_downloads_enabled_{event_id}")

            if event.event_type == AgentEventType.BROWSER_POOL_LEASED:
                if str(_enum_value(payload.get("status")) or "").lower() != "leased":
                    errors.append(f"browser_pool_lease_status_invalid_{event_id}")
                if not payload.get("receipt_id"):
                    errors.append(f"browser_pool_lease_missing_receipt_{event_id}")
                lease_id = str(payload.get("lease_id") or "")
                if not lease_id:
                    errors.append(f"browser_pool_lease_missing_id_{event_id}")
                    continue
                if lease_id in leases:
                    errors.append(f"browser_pool_lease_duplicate_{event_id}_{lease_id}")
                    continue
                max_operations = payload.get("max_operations")
                operation_count = payload.get("operation_count")
                if not isinstance(max_operations, int) or max_operations < 1:
                    errors.append(f"browser_pool_lease_invalid_max_operations_{event_id}")
                    max_operations = 0
                if not isinstance(operation_count, int) or operation_count != 0:
                    errors.append(f"browser_pool_lease_invalid_operation_count_{event_id}")
                    operation_count = 0
                leases[lease_id] = {
                    "status": "leased",
                    "sequence": event.sequence,
                    "max_operations": max_operations,
                    "operation_count": operation_count,
                    "lease_event_id": event.id,
                }

            elif event.event_type == AgentEventType.BROWSER_POOL_RELEASED:
                if str(_enum_value(payload.get("status")) or "").lower() != "released":
                    errors.append(f"browser_pool_release_status_invalid_{event_id}")
                if not payload.get("receipt_id"):
                    errors.append(f"browser_pool_release_missing_receipt_{event_id}")
                lease_id = str(payload.get("lease_id") or "")
                lease = leases.get(lease_id)
                if lease is None:
                    errors.append(f"browser_pool_release_unknown_lease_{event_id}")
                    continue
                if lease["status"] != "leased":
                    errors.append(f"browser_pool_release_lease_not_active_{event_id}")
                if lease["lease_event_id"] not in event.trace_refs:
                    errors.append(f"browser_pool_release_missing_lease_trace_ref_{event_id}")
                operation_count = payload.get("operation_count")
                if not isinstance(operation_count, int) or operation_count < 0:
                    errors.append(f"browser_pool_release_invalid_operation_count_{event_id}")
                elif operation_count > int(lease["max_operations"]):
                    errors.append(f"browser_pool_release_operation_count_exceeds_max_{event_id}")
                lease["status"] = "released"

            elif event.event_type == AgentEventType.BROWSER_HEALTH_CHECKED:
                status = str(_enum_value(payload.get("status")) or "").lower()
                if status not in valid_health_statuses:
                    errors.append(f"browser_health_status_invalid_{event_id}")
                if not payload.get("health_check_id"):
                    errors.append(f"browser_health_missing_check_id_{event_id}")
                if not isinstance(payload.get("latency_ms"), int):
                    errors.append(f"browser_health_invalid_latency_{event_id}")
                if not isinstance(payload.get("consecutive_failures"), int):
                    errors.append(f"browser_health_invalid_consecutive_failures_{event_id}")
                lease_id = str(payload.get("lease_id") or "")
                if lease_id:
                    lease = leases.get(lease_id)
                    if lease is None:
                        errors.append(f"browser_health_unknown_lease_{event_id}")
                    else:
                        if lease["status"] != "leased":
                            errors.append(f"browser_health_lease_not_active_{event_id}")
                        if lease["lease_event_id"] not in event.trace_refs:
                            errors.append(f"browser_health_missing_lease_trace_ref_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_OPERATION_RETRIED:
                if str(_enum_value(payload.get("status")) or "").lower() != "retrying":
                    errors.append(f"browser_retry_status_invalid_{event_id}")
                if not payload.get("operation_name"):
                    errors.append(f"browser_retry_missing_operation_name_{event_id}")
                if not payload.get("reason"):
                    errors.append(f"browser_retry_missing_reason_{event_id}")
                if payload.get("retryable") is not True:
                    errors.append(f"browser_retry_not_marked_retryable_{event_id}")
                attempt_number = payload.get("attempt_number")
                max_attempts = payload.get("max_attempts")
                if not isinstance(attempt_number, int) or attempt_number < 1:
                    errors.append(f"browser_retry_invalid_attempt_number_{event_id}")
                    attempt_number = 0
                if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 5:
                    errors.append(f"browser_retry_invalid_max_attempts_{event_id}")
                    max_attempts = 0
                if attempt_number >= max_attempts:
                    errors.append(f"browser_retry_attempt_not_bounded_{event_id}")
                lease_id = str(payload.get("lease_id") or "")
                if lease_id:
                    lease = leases.get(lease_id)
                    if lease is None:
                        errors.append(f"browser_retry_unknown_lease_{event_id}")
                    else:
                        if lease["status"] != "leased":
                            errors.append(f"browser_retry_lease_not_active_{event_id}")
                        if lease["lease_event_id"] not in event.trace_refs:
                            errors.append(f"browser_retry_missing_lease_trace_ref_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_SUPERVISOR_REJECTED:
                if str(_enum_value(payload.get("status")) or "").lower() != "rejected":
                    errors.append(f"browser_supervisor_rejection_status_invalid_{event_id}")
                if not payload.get("operation_name") and not payload.get("action"):
                    errors.append(f"browser_supervisor_rejection_missing_operation_{event_id}")
                if not payload.get("reason"):
                    errors.append(f"browser_supervisor_rejection_missing_reason_{event_id}")

        return CoreGateCheck(
            name="browser_reliability_supervisor_contract",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Browser reliability supervisor events are bounded, stateless, and ordered." if not errors else "Browser reliability supervisor contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_v25_observation_and_operator_contract(result: AgentRunResult) -> CoreGateCheck:
        v25_event_types = {
            AgentEventType.BROWSER_UI_OBSERVATION_CAPTURED,
            AgentEventType.BROWSER_UI_OBSERVATION_REJECTED,
            AgentEventType.BROWSER_CDP_AX_TREE_CAPTURED,
            AgentEventType.BROWSER_DOM_SNAPSHOT_CAPTURED,
            AgentEventType.BROWSER_VISUAL_OBSERVATION_CAPTURED,
            AgentEventType.BROWSER_ADVANCED_POOL_STARTED,
            AgentEventType.BROWSER_ADVANCED_POOL_LEASED,
            AgentEventType.BROWSER_ADVANCED_POOL_RELEASED,
            AgentEventType.BROWSER_MULTITAB_STRATEGY_EXECUTED,
            AgentEventType.BROWSER_VERIFICATION_COMPLETED,
            AgentEventType.BROWSER_LOOP_DETECTED,
        }
        v25_events = [event for event in result.trace if event.event_type in v25_event_types]
        if not v25_events:
            return CoreGateCheck(
                name="browser_v25_observation_and_operator_contract",
                kind=CoreGateCheckKind.EVIDENCE,
                passed=True,
                message="No Browser V2.5 observation/operator events were emitted.",
            )

        errors: list[str] = []
        advanced_leases: dict[str, dict[str, Any]] = {}
        valid_verdicts = {"accepted", "needs_repair", "inconclusive"}

        for event in v25_events:
            payload = event.payload
            event_id = event.id
            CoreFinalGate._browser_v25_boundary_errors(payload, event_id, errors)

            if event.event_type == AgentEventType.BROWSER_CDP_AX_TREE_CAPTURED:
                tree = payload.get("tree")
                expected_hash = payload.get("tree_sha256")
                if not isinstance(tree, dict):
                    errors.append(f"browser_v25_ax_tree_missing_{event_id}")
                    continue
                if not verify_cdp_ax_tree_hash(tree, str(expected_hash or "")):
                    errors.append(f"browser_v25_ax_tree_hash_mismatch_{event_id}")
                if payload.get("node_count") != tree.get("node_count"):
                    errors.append(f"browser_v25_ax_tree_node_count_mismatch_{event_id}")
                if not isinstance(payload.get("backend_node_count"), int):
                    errors.append(f"browser_v25_ax_tree_backend_count_invalid_{event_id}")
                if not payload.get("root_id"):
                    errors.append(f"browser_v25_ax_tree_missing_root_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_DOM_SNAPSHOT_CAPTURED:
                snapshot = payload.get("snapshot")
                expected_hash = payload.get("snapshot_sha256")
                if not isinstance(snapshot, dict):
                    errors.append(f"browser_v25_dom_snapshot_missing_{event_id}")
                    continue
                if not verify_dom_snapshot_hash(snapshot, str(expected_hash or "")):
                    errors.append(f"browser_v25_dom_snapshot_hash_mismatch_{event_id}")
                if payload.get("node_count") != snapshot.get("node_count"):
                    errors.append(f"browser_v25_dom_snapshot_node_count_mismatch_{event_id}")
                if payload.get("layout_count") != snapshot.get("layout_count"):
                    errors.append(f"browser_v25_dom_snapshot_layout_count_mismatch_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_UI_OBSERVATION_CAPTURED:
                observation_set = payload.get("observation_set")
                expected_hash = payload.get("observation_sha256")
                if not isinstance(observation_set, dict):
                    errors.append(f"browser_v25_ui_observation_missing_{event_id}")
                    continue
                if not verify_ui_observation_hash(observation_set, str(expected_hash or "")):
                    errors.append(f"browser_v25_ui_observation_hash_mismatch_{event_id}")
                observations = observation_set.get("observations")
                if not isinstance(observations, list):
                    errors.append(f"browser_v25_ui_observation_items_invalid_{event_id}")
                elif payload.get("observation_count") != len(observations):
                    errors.append(f"browser_v25_ui_observation_count_mismatch_{event_id}")
                if not isinstance(payload.get("source_count"), int) or payload.get("source_count") < 1:
                    errors.append(f"browser_v25_ui_observation_source_count_invalid_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_VISUAL_OBSERVATION_CAPTURED:
                observation = payload.get("observation")
                expected_hash = payload.get("observation_sha256")
                if not isinstance(observation, dict):
                    errors.append(f"browser_v25_visual_observation_missing_{event_id}")
                    continue
                if not verify_visual_observation_hash(observation, str(expected_hash or "")):
                    errors.append(f"browser_v25_visual_observation_hash_mismatch_{event_id}")
                if not payload.get("source_screenshot_sha256"):
                    errors.append(f"browser_v25_visual_observation_missing_source_hash_{event_id}")
                bytes_observed = payload.get("bytes_observed")
                max_bytes = payload.get("max_bytes")
                if not isinstance(bytes_observed, int) or not isinstance(max_bytes, int) or bytes_observed > max_bytes:
                    errors.append(f"browser_v25_visual_observation_bytes_invalid_{event_id}")
                if payload.get("ocr_dependency") != "stub":
                    errors.append(f"browser_v25_visual_observation_ocr_dependency_invalid_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_ADVANCED_POOL_STARTED:
                capacity = payload.get("capacity")
                instance_ids = payload.get("instance_ids")
                if not isinstance(capacity, int) or capacity < 1:
                    errors.append(f"browser_v25_pool_capacity_invalid_{event_id}")
                if not isinstance(instance_ids, list) or len(instance_ids) != capacity:
                    errors.append(f"browser_v25_pool_instance_count_mismatch_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_ADVANCED_POOL_LEASED:
                if str(_enum_value(payload.get("status")) or "").lower() != "leased":
                    errors.append(f"browser_v25_pool_lease_status_invalid_{event_id}")
                lease_id = str(payload.get("lease_id") or "")
                instance_id = str(payload.get("instance_id") or "")
                if not lease_id or not instance_id:
                    errors.append(f"browser_v25_pool_lease_missing_identity_{event_id}")
                    continue
                if lease_id in advanced_leases:
                    errors.append(f"browser_v25_pool_lease_duplicate_{event_id}_{lease_id}")
                    continue
                advanced_leases[lease_id] = {"instance_id": instance_id, "status": "leased", "event_id": event.id}

            elif event.event_type == AgentEventType.BROWSER_ADVANCED_POOL_RELEASED:
                if str(_enum_value(payload.get("status")) or "").lower() != "released":
                    errors.append(f"browser_v25_pool_release_status_invalid_{event_id}")
                lease_id = str(payload.get("lease_id") or "")
                lease = advanced_leases.get(lease_id)
                if lease is None:
                    errors.append(f"browser_v25_pool_release_unknown_lease_{event_id}")
                    continue
                if lease["status"] != "leased":
                    errors.append(f"browser_v25_pool_release_not_active_{event_id}")
                if lease["event_id"] not in event.trace_refs:
                    errors.append(f"browser_v25_pool_release_missing_lease_trace_ref_{event_id}")
                if payload.get("instance_id") != lease["instance_id"]:
                    errors.append(f"browser_v25_pool_release_instance_mismatch_{event_id}")
                lease["status"] = "released"

            elif event.event_type == AgentEventType.BROWSER_MULTITAB_STRATEGY_EXECUTED:
                tab_ids = payload.get("tab_ids")
                final_urls = payload.get("final_urls")
                tab_count = payload.get("tab_count")
                max_tabs = payload.get("max_tabs")
                if not isinstance(tab_count, int) or not isinstance(max_tabs, int) or tab_count < 1 or tab_count > max_tabs:
                    errors.append(f"browser_v25_multitab_count_invalid_{event_id}")
                if not isinstance(tab_ids, list) or len(tab_ids) != tab_count:
                    errors.append(f"browser_v25_multitab_ids_mismatch_{event_id}")
                if not isinstance(final_urls, list) or len(final_urls) != tab_count:
                    errors.append(f"browser_v25_multitab_urls_mismatch_{event_id}")
                if not event.trace_refs:
                    errors.append(f"browser_v25_multitab_missing_lifecycle_trace_refs_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_VERIFICATION_COMPLETED:
                verdict = str(_enum_value(payload.get("verdict")) or "").lower()
                if verdict not in valid_verdicts:
                    errors.append(f"browser_v25_verifier_verdict_invalid_{event_id}")
                if not payload.get("checked_receipt_id"):
                    errors.append(f"browser_v25_verifier_missing_receipt_{event_id}")
                if not payload.get("before_snapshot_sha256") or not payload.get("after_snapshot_sha256"):
                    errors.append(f"browser_v25_verifier_missing_snapshot_hash_{event_id}")
                findings = payload.get("findings")
                if not isinstance(findings, list):
                    errors.append(f"browser_v25_verifier_findings_invalid_{event_id}")
                elif verdict == "accepted" and findings:
                    errors.append(f"browser_v25_verifier_accepted_with_findings_{event_id}")
                trace_ref_count = payload.get("trace_ref_count")
                if not isinstance(trace_ref_count, int) or trace_ref_count < 1:
                    errors.append(f"browser_v25_verifier_missing_trace_refs_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_LOOP_DETECTED:
                repeated_count = payload.get("repeated_count")
                threshold = payload.get("threshold")
                if not isinstance(repeated_count, int) or not isinstance(threshold, int) or repeated_count < threshold:
                    errors.append(f"browser_v25_loop_count_invalid_{event_id}")
                if not payload.get("loop_key"):
                    errors.append(f"browser_v25_loop_missing_key_{event_id}")

            elif event.event_type == AgentEventType.BROWSER_UI_OBSERVATION_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v25_ui_observation_rejection_missing_reason_{event_id}")

        return CoreGateCheck(
            name="browser_v25_observation_and_operator_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not errors,
            message="Browser V2.5 observation/operator events are proof-bound and public/stateless." if not errors else "Browser V2.5 observation/operator contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_v25_boundary_errors(payload: dict[str, Any], event_id: str, errors: list[str]) -> None:
        if payload.get("stateless_public") is not True:
            errors.append(f"browser_v25_not_stateless_{event_id}")
        if payload.get("cookies_enabled") is not False:
            errors.append(f"browser_v25_cookies_enabled_{event_id}")
        if payload.get("storage_enabled") is not False:
            errors.append(f"browser_v25_storage_enabled_{event_id}")
        if payload.get("js_enabled") is not False:
            errors.append(f"browser_v25_js_enabled_{event_id}")
        if payload.get("downloads_enabled") is not False:
            errors.append(f"browser_v25_downloads_enabled_{event_id}")

    @staticmethod
    def _browser_v3_form_submit_contract(result: AgentRunResult) -> CoreGateCheck:
        form_events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED, AgentEventType.BROWSER_FORM_SUBMIT_REJECTED}
        ]
        if not form_events:
            return CoreGateCheck(
                name="browser_v3_form_submit_contract",
                kind=CoreGateCheckKind.EVIDENCE,
                passed=True,
                message="No Browser V3 form-submit events were emitted.",
            )

        errors: list[str] = []
        compiled_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
        }
        artifact_events = {
            str(event.payload.get("artifact_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
        }

        for event in form_events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_form_submit":
                errors.append(f"browser_v3_form_submit_authority_class_invalid_{event_id}")
            if not payload.get("authority_grant_id"):
                errors.append(f"browser_v3_form_submit_missing_grant_{event_id}")
            if not payload.get("context_pack_id"):
                errors.append(f"browser_v3_form_submit_missing_context_pack_{event_id}")
            compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
            if not compiled_trace_id:
                errors.append(f"browser_v3_form_submit_missing_compiled_intent_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_FORM_SUBMIT_EXECUTED:
                compiled_event = compiled_events.get(compiled_trace_id)
                if compiled_event is None:
                    errors.append(f"browser_v3_form_submit_compiled_intent_missing_{event_id}")
                elif compiled_trace_id not in event.trace_refs:
                    errors.append(f"browser_v3_form_submit_missing_compiled_trace_ref_{event_id}")
            if event.event_type == AgentEventType.BROWSER_FORM_SUBMIT_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_form_submit_rejection_missing_reason_{event_id}")
                continue

            if not payload.get("receipt_id"):
                errors.append(f"browser_v3_form_submit_missing_receipt_{event_id}")
            plan = payload.get("plan")
            plan_sha256 = payload.get("plan_sha256")
            if not isinstance(plan, dict):
                errors.append(f"browser_v3_form_submit_missing_plan_{event_id}")
            elif not verify_browser_interaction_plan_hash(plan, str(plan_sha256 or "")):
                errors.append(f"browser_v3_form_submit_plan_hash_mismatch_{event_id}")
            if not payload.get("plan_trace_event_id"):
                errors.append(f"browser_v3_form_submit_missing_plan_trace_{event_id}")
            if not payload.get("before_snapshot_trace_event_id"):
                errors.append(f"browser_v3_form_submit_missing_before_snapshot_trace_{event_id}")
            if not payload.get("before_snapshot_sha256") or not payload.get("after_snapshot_sha256"):
                errors.append(f"browser_v3_form_submit_missing_snapshot_hash_{event_id}")
            if not payload.get("form_ref_id") or not payload.get("submit_ref_id"):
                errors.append(f"browser_v3_form_submit_missing_refs_{event_id}")
            if str(payload.get("submit_kind") or "").lower() not in {"submit", "post", "send", "publish"}:
                errors.append(f"browser_v3_form_submit_kind_invalid_{event_id}")
            if not payload.get("expected_effect"):
                errors.append(f"browser_v3_form_submit_missing_expected_effect_{event_id}")
            if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
                errors.append(f"browser_v3_form_submit_cross_origin_not_authorized_{event_id}")

            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = payload.get("network_ledger_sha256")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_v3_form_submit_missing_network_ledger_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                errors.append(f"browser_v3_form_submit_network_ledger_hash_mismatch_{event_id}")

            artifact_id = str(payload.get("post_submit_snapshot_artifact_id") or "")
            artifact_hash = payload.get("post_submit_snapshot_artifact_sha256")
            artifact_event = artifact_events.get(artifact_id)
            if not artifact_id:
                errors.append(f"browser_v3_form_submit_missing_post_snapshot_artifact_{event_id}")
            elif artifact_event is None:
                errors.append(f"browser_v3_form_submit_post_snapshot_artifact_missing_{event_id}")
            else:
                if artifact_event.sequence >= event.sequence:
                    errors.append(f"browser_v3_form_submit_post_snapshot_artifact_order_invalid_{event_id}")
                if artifact_hash and artifact_event.payload.get("sha256") != artifact_hash:
                    errors.append(f"browser_v3_form_submit_post_snapshot_artifact_hash_mismatch_{event_id}")

        return CoreGateCheck(
            name="browser_v3_form_submit_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not errors,
            message="Browser V3 form-submit events are authority-bound and proof-certified." if not errors else "Browser V3 form-submit contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_v3_download_quarantine_contract(result: AgentRunResult) -> CoreGateCheck:
        download_events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_DOWNLOAD_QUARANTINED, AgentEventType.BROWSER_DOWNLOAD_REJECTED}
        ]
        if not download_events:
            return CoreGateCheck(
                name="browser_v3_download_quarantine_contract",
                kind=CoreGateCheckKind.EVIDENCE,
                passed=True,
                message="No Browser V3 download-quarantine events were emitted.",
            )

        errors: list[str] = []
        compiled_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
        }
        url_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.BROWSER_URL_CLASSIFIED
        }
        artifact_events = {
            str(event.payload.get("artifact_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
        }

        for event in download_events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_download_quarantine":
                errors.append(f"browser_v3_download_authority_class_invalid_{event_id}")
            if not payload.get("authority_grant_id"):
                errors.append(f"browser_v3_download_missing_grant_{event_id}")
            if not payload.get("context_pack_id"):
                errors.append(f"browser_v3_download_missing_context_pack_{event_id}")
            compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
            if not compiled_trace_id:
                errors.append(f"browser_v3_download_missing_compiled_intent_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_DOWNLOAD_QUARANTINED:
                compiled_event = compiled_events.get(compiled_trace_id)
                if compiled_event is None:
                    errors.append(f"browser_v3_download_compiled_intent_missing_{event_id}")
                elif compiled_trace_id not in event.trace_refs:
                    errors.append(f"browser_v3_download_missing_compiled_trace_ref_{event_id}")

            url_trace_id = str(payload.get("url_policy_trace_id") or "")
            if not url_trace_id:
                errors.append(f"browser_v3_download_missing_url_policy_{event_id}")
            else:
                url_event = url_events.get(url_trace_id)
                if url_event is None:
                    errors.append(f"browser_v3_download_url_policy_missing_{event_id}")
                else:
                    if url_event.sequence >= event.sequence:
                        errors.append(f"browser_v3_download_url_policy_order_invalid_{event_id}")
                    if url_trace_id not in event.trace_refs:
                        errors.append(f"browser_v3_download_missing_url_trace_ref_{event_id}")
                    if event.event_type == AgentEventType.BROWSER_DOWNLOAD_QUARANTINED and str(url_event.payload.get("status")) != "allowed":
                        errors.append(f"browser_v3_download_url_policy_not_allowed_{event_id}")

            if event.event_type == AgentEventType.BROWSER_DOWNLOAD_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_download_rejection_missing_reason_{event_id}")
                continue

            if not payload.get("receipt_id"):
                errors.append(f"browser_v3_download_missing_receipt_{event_id}")
            if payload.get("promoted") is not False:
                errors.append(f"browser_v3_download_promoted_{event_id}")
            if payload.get("mime_type_allowed") is not True:
                errors.append(f"browser_v3_download_mime_not_allowed_{event_id}")
            if str(payload.get("quarantine_relative_path") or "").startswith("browser/download_quarantine/") is not True:
                errors.append(f"browser_v3_download_quarantine_path_invalid_{event_id}")
            if not payload.get("filename_hash"):
                errors.append(f"browser_v3_download_missing_filename_hash_{event_id}")
            size_bytes = payload.get("size_bytes")
            max_bytes = payload.get("max_bytes")
            if not isinstance(size_bytes, int) or not isinstance(max_bytes, int):
                errors.append(f"browser_v3_download_invalid_size_metadata_{event_id}")
            elif size_bytes > max_bytes:
                errors.append(f"browser_v3_download_size_exceeds_max_{event_id}")

            artifact_id = str(payload.get("artifact_id") or "")
            artifact_hash = payload.get("artifact_sha256")
            download_hash = payload.get("download_sha256")
            artifact_event = artifact_events.get(artifact_id)
            if not artifact_id:
                errors.append(f"browser_v3_download_missing_artifact_{event_id}")
            elif artifact_event is None:
                errors.append(f"browser_v3_download_artifact_missing_{event_id}")
            else:
                if artifact_event.sequence >= event.sequence:
                    errors.append(f"browser_v3_download_artifact_order_invalid_{event_id}")
                if artifact_hash and artifact_event.payload.get("sha256") != artifact_hash:
                    errors.append(f"browser_v3_download_artifact_hash_mismatch_{event_id}")
                if download_hash and artifact_event.payload.get("sha256") != download_hash:
                    errors.append(f"browser_v3_download_hash_mismatch_{event_id}")
                if artifact_event.payload.get("artifact_type") != "browser_download_quarantine":
                    errors.append(f"browser_v3_download_artifact_type_invalid_{event_id}")

        return CoreGateCheck(
            name="browser_v3_download_quarantine_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not errors,
            message="Browser V3 download-quarantine events are authority-bound and quarantine-certified." if not errors else "Browser V3 download-quarantine contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_v3_upload_authorized_contract(result: AgentRunResult) -> CoreGateCheck:
        upload_events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED, AgentEventType.BROWSER_UPLOAD_AUTHORIZED_REJECTED}
        ]
        if not upload_events:
            return CoreGateCheck(
                name="browser_v3_upload_authorized_contract",
                kind=CoreGateCheckKind.EVIDENCE,
                passed=True,
                message="No Browser V3 authorized-upload events were emitted.",
            )

        errors: list[str] = []
        compiled_events = {
            event.id: event
            for event in result.trace
            if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
        }
        artifact_events = {
            str(event.payload.get("artifact_id")): event
            for event in result.trace
            if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
        }

        for event in upload_events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_upload_authorized":
                errors.append(f"browser_v3_upload_authority_class_invalid_{event_id}")
            if not payload.get("authority_grant_id"):
                errors.append(f"browser_v3_upload_missing_grant_{event_id}")
            if not payload.get("context_pack_id"):
                errors.append(f"browser_v3_upload_missing_context_pack_{event_id}")
            compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
            if not compiled_trace_id:
                errors.append(f"browser_v3_upload_missing_compiled_intent_{event_id}")
            elif event.event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_EXECUTED:
                compiled_event = compiled_events.get(compiled_trace_id)
                if compiled_event is None:
                    errors.append(f"browser_v3_upload_compiled_intent_missing_{event_id}")
                elif compiled_trace_id not in event.trace_refs:
                    errors.append(f"browser_v3_upload_missing_compiled_trace_ref_{event_id}")

            if event.event_type == AgentEventType.BROWSER_UPLOAD_AUTHORIZED_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_upload_rejection_missing_reason_{event_id}")
                continue

            if not payload.get("receipt_id"):
                errors.append(f"browser_v3_upload_missing_receipt_{event_id}")
            plan = payload.get("plan")
            plan_sha256 = payload.get("plan_sha256")
            if not isinstance(plan, dict):
                errors.append(f"browser_v3_upload_missing_plan_{event_id}")
            elif not verify_browser_interaction_plan_hash(plan, str(plan_sha256 or "")):
                errors.append(f"browser_v3_upload_plan_hash_mismatch_{event_id}")
            if not payload.get("plan_trace_event_id"):
                errors.append(f"browser_v3_upload_missing_plan_trace_{event_id}")
            if not payload.get("before_snapshot_trace_event_id"):
                errors.append(f"browser_v3_upload_missing_before_snapshot_trace_{event_id}")
            if not payload.get("before_snapshot_sha256") or not payload.get("after_snapshot_sha256"):
                errors.append(f"browser_v3_upload_missing_snapshot_hash_{event_id}")
            if not payload.get("upload_ref_id"):
                errors.append(f"browser_v3_upload_missing_upload_ref_{event_id}")
            if not payload.get("expected_effect"):
                errors.append(f"browser_v3_upload_missing_expected_effect_{event_id}")
            if payload.get("same_origin") is not True and payload.get("cross_origin_authorized") is not True:
                errors.append(f"browser_v3_upload_cross_origin_not_authorized_{event_id}")

            network_ledger = payload.get("network_ledger")
            network_ledger_sha256 = payload.get("network_ledger_sha256")
            if not isinstance(network_ledger, dict):
                errors.append(f"browser_v3_upload_missing_network_ledger_{event_id}")
            elif not verify_browser_network_ledger_hash(network_ledger, str(network_ledger_sha256 or "")):
                errors.append(f"browser_v3_upload_network_ledger_hash_mismatch_{event_id}")

            source_artifact_id = str(payload.get("source_artifact_id") or "")
            source_artifact_hash = payload.get("source_artifact_sha256")
            source_artifact_event = artifact_events.get(source_artifact_id)
            if not source_artifact_id:
                errors.append(f"browser_v3_upload_missing_source_artifact_{event_id}")
            elif source_artifact_event is None:
                errors.append(f"browser_v3_upload_source_artifact_missing_{event_id}")
            else:
                if source_artifact_event.sequence >= event.sequence:
                    errors.append(f"browser_v3_upload_source_artifact_order_invalid_{event_id}")
                if source_artifact_hash and source_artifact_event.payload.get("sha256") != source_artifact_hash:
                    errors.append(f"browser_v3_upload_source_artifact_hash_mismatch_{event_id}")

            snapshot_artifact_id = str(payload.get("post_upload_snapshot_artifact_id") or "")
            snapshot_artifact_hash = payload.get("post_upload_snapshot_artifact_sha256")
            snapshot_artifact_event = artifact_events.get(snapshot_artifact_id)
            if not snapshot_artifact_id:
                errors.append(f"browser_v3_upload_missing_post_snapshot_artifact_{event_id}")
            elif snapshot_artifact_event is None:
                errors.append(f"browser_v3_upload_post_snapshot_artifact_missing_{event_id}")
            else:
                if snapshot_artifact_event.sequence >= event.sequence:
                    errors.append(f"browser_v3_upload_post_snapshot_artifact_order_invalid_{event_id}")
                if snapshot_artifact_hash and snapshot_artifact_event.payload.get("sha256") != snapshot_artifact_hash:
                    errors.append(f"browser_v3_upload_post_snapshot_artifact_hash_mismatch_{event_id}")

        return CoreGateCheck(
            name="browser_v3_upload_authorized_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not errors,
            message="Browser V3 authorized-upload events are authority-bound and artifact-certified." if not errors else "Browser V3 authorized-upload contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_v3_private_session_contract(result: AgentRunResult) -> CoreGateCheck:
        events = [
            event
            for event in result.trace
            if event.event_type
            in {
                AgentEventType.BROWSER_PRIVATE_SESSION_STARTED,
                AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED,
                AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED,
            }
        ]
        if not events:
            return CoreGateCheck(name="browser_v3_private_session_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 private-session events were emitted.")
        errors: list[str] = []
        starts: dict[str, Any] = {}
        closes: dict[str, Any] = {}
        compiled = _accepted_compiled_event_ids(result)
        artifacts = _artifact_events_by_id(result)
        for event in events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_private_session":
                errors.append(f"browser_v3_private_session_class_invalid_{event_id}")
            _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_private_session")
            if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_private_session_rejection_missing_reason_{event_id}")
                continue
            session_id = str(payload.get("session_id") or "")
            if not session_id or not payload.get("profile_id"):
                errors.append(f"browser_v3_private_session_missing_ids_{event_id}")
            if payload.get("session_scope") != "per_mission":
                errors.append(f"browser_v3_private_session_scope_invalid_{event_id}")
            if not payload.get("storage_state_sha256"):
                errors.append(f"browser_v3_private_session_missing_storage_hash_{event_id}")
            _check_artifact_pair(payload.get("receipt_artifact_id"), payload.get("receipt_artifact_sha256"), event, artifacts, errors, "browser_v3_private_session_receipt")
            if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_STARTED:
                if payload.get("created") is not True:
                    errors.append(f"browser_v3_private_session_not_created_{event_id}")
                starts[session_id] = event
            if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_CLOSED:
                if payload.get("destroyed") is not True or payload.get("profile_destroyed") is not True:
                    errors.append(f"browser_v3_private_session_not_destroyed_{event_id}")
                closes[session_id] = event
        for session_id, start_event in starts.items():
            close_event = closes.get(session_id)
            if close_event is None:
                errors.append(f"browser_v3_private_session_missing_close_{session_id}")
            elif close_event.sequence <= start_event.sequence:
                errors.append(f"browser_v3_private_session_close_order_invalid_{session_id}")
        return CoreGateCheck(name="browser_v3_private_session_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 private sessions are opened and destroyed with proof." if not errors else "Browser V3 private-session contract failed.", details={"errors": errors})

    @staticmethod
    def _browser_v3_login_authority_contract(result: AgentRunResult) -> CoreGateCheck:
        events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_LOGIN_AUTHORITY_EXECUTED, AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED}
        ]
        if not events:
            return CoreGateCheck(name="browser_v3_login_authority_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 login-authority events were emitted.")
        errors: list[str] = []
        compiled = _accepted_compiled_event_ids(result)
        artifacts = _artifact_events_by_id(result)
        private_events = {event.id: event for event in result.trace if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_STARTED}
        for event in events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_login_authority":
                errors.append(f"browser_v3_login_class_invalid_{event_id}")
            _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_login")
            _check_no_credential_payload(payload, errors, f"browser_v3_login_credential_leak_{event_id}")
            if event.event_type == AgentEventType.BROWSER_LOGIN_AUTHORITY_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_login_rejection_missing_reason_{event_id}")
                continue
            session_trace_id = str(payload.get("private_session_trace_event_id") or "")
            session_event = private_events.get(session_trace_id)
            if session_event is None:
                errors.append(f"browser_v3_login_missing_private_session_{event_id}")
            elif session_event.sequence >= event.sequence:
                errors.append(f"browser_v3_login_private_session_order_invalid_{event_id}")
            if payload.get("login_success") is not True:
                errors.append(f"browser_v3_login_not_successful_{event_id}")
            if not payload.get("account_id") or not payload.get("login_url_hash"):
                errors.append(f"browser_v3_login_missing_account_or_url_hash_{event_id}")
            if not payload.get("plan_sha256") or not payload.get("plan_trace_event_id"):
                errors.append(f"browser_v3_login_missing_plan_{event_id}")
            _check_artifact_pair(payload.get("post_login_snapshot_artifact_id"), payload.get("post_login_snapshot_artifact_sha256"), event, artifacts, errors, "browser_v3_login_post_snapshot")
        return CoreGateCheck(name="browser_v3_login_authority_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 login events are session-bound and credential-redacted." if not errors else "Browser V3 login contract failed.", details={"errors": errors})

    @staticmethod
    def _browser_v3_cookie_storage_contract(result: AgentRunResult) -> CoreGateCheck:
        events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_APPLIED, AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED}
        ]
        if not events:
            return CoreGateCheck(name="browser_v3_cookie_storage_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 cookie/storage events were emitted.")
        errors: list[str] = []
        compiled = _accepted_compiled_event_ids(result)
        artifacts = _artifact_events_by_id(result)
        private_events = {event.id: event for event in result.trace if event.event_type == AgentEventType.BROWSER_PRIVATE_SESSION_STARTED}
        for event in events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_cookie_storage_contract":
                errors.append(f"browser_v3_cookie_storage_class_invalid_{event_id}")
            _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_cookie_storage")
            if event.event_type == AgentEventType.BROWSER_COOKIE_STORAGE_CONTRACT_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_cookie_storage_rejection_missing_reason_{event_id}")
                continue
            session_trace_id = str(payload.get("private_session_trace_event_id") or "")
            if session_trace_id not in private_events:
                errors.append(f"browser_v3_cookie_storage_missing_private_session_{event_id}")
            if payload.get("redaction_applied") is not True or payload.get("raw_value_exposed") is True:
                errors.append(f"browser_v3_cookie_storage_redaction_invalid_{event_id}")
            if payload.get("operation") not in {"redacted_summary", "clear_scoped_storage"}:
                errors.append(f"browser_v3_cookie_storage_operation_invalid_{event_id}")
            _check_artifact_pair(payload.get("summary_artifact_id"), payload.get("summary_artifact_sha256"), event, artifacts, errors, "browser_v3_cookie_storage_summary")
        return CoreGateCheck(name="browser_v3_cookie_storage_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 cookie/storage contracts are redacted and session-bound." if not errors else "Browser V3 cookie/storage contract failed.", details={"errors": errors})

    @staticmethod
    def _browser_v3_js_evaluate_sandboxed_contract(result: AgentRunResult) -> CoreGateCheck:
        events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_EXECUTED, AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED}
        ]
        if not events:
            return CoreGateCheck(name="browser_v3_js_evaluate_sandboxed_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 sandboxed-JS events were emitted.")
        errors: list[str] = []
        compiled = _accepted_compiled_event_ids(result)
        artifacts = _artifact_events_by_id(result)
        for event in events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_js_evaluate_sandboxed":
                errors.append(f"browser_v3_js_class_invalid_{event_id}")
            _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_js")
            if event.event_type == AgentEventType.BROWSER_JS_EVALUATE_SANDBOXED_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_js_rejection_missing_reason_{event_id}")
                continue
            if payload.get("script_hash_allowed") is not True:
                errors.append(f"browser_v3_js_script_hash_not_allowed_{event_id}")
            if payload.get("network_calls_blocked") is not True:
                errors.append(f"browser_v3_js_network_calls_not_blocked_{event_id}")
            if not isinstance(payload.get("result_size_bytes"), int) or not isinstance(payload.get("max_result_bytes"), int):
                errors.append(f"browser_v3_js_size_metadata_invalid_{event_id}")
            elif payload.get("result_size_bytes") > payload.get("max_result_bytes"):
                errors.append(f"browser_v3_js_result_too_large_{event_id}")
            _check_artifact_pair(payload.get("result_artifact_id"), payload.get("result_artifact_sha256"), event, artifacts, errors, "browser_v3_js_result")
        return CoreGateCheck(name="browser_v3_js_evaluate_sandboxed_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 sandboxed JS is hash-allowlisted and artifact-bound." if not errors else "Browser V3 sandboxed-JS contract failed.", details={"errors": errors})

    @staticmethod
    def _browser_v3_har_body_capture_contract(result: AgentRunResult) -> CoreGateCheck:
        events = [
            event
            for event in result.trace
            if event.event_type in {AgentEventType.BROWSER_HAR_BODY_CAPTURED, AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED}
        ]
        if not events:
            return CoreGateCheck(name="browser_v3_har_body_capture_contract", kind=CoreGateCheckKind.EVIDENCE, passed=True, message="No Browser V3 HAR/body events were emitted.")
        errors: list[str] = []
        compiled = _accepted_compiled_event_ids(result)
        artifacts = _artifact_events_by_id(result)
        for event in events:
            payload = event.payload
            event_id = event.id
            if payload.get("authority_class") != "browser_har_body_capture":
                errors.append(f"browser_v3_har_class_invalid_{event_id}")
            _check_basic_v3_event(payload, event, compiled, errors, "browser_v3_har")
            if event.event_type == AgentEventType.BROWSER_HAR_BODY_CAPTURE_REJECTED:
                if not payload.get("reason"):
                    errors.append(f"browser_v3_har_rejection_missing_reason_{event_id}")
                continue
            if payload.get("redaction_applied") is not True:
                errors.append(f"browser_v3_har_redaction_missing_{event_id}")
            if not isinstance(payload.get("record_count"), int) or not isinstance(payload.get("max_records"), int):
                errors.append(f"browser_v3_har_record_metadata_invalid_{event_id}")
            elif payload.get("record_count") > payload.get("max_records"):
                errors.append(f"browser_v3_har_record_limit_exceeded_{event_id}")
            if not isinstance(payload.get("total_bytes"), int) or not isinstance(payload.get("max_bytes"), int):
                errors.append(f"browser_v3_har_byte_metadata_invalid_{event_id}")
            elif payload.get("total_bytes") > payload.get("max_bytes"):
                errors.append(f"browser_v3_har_byte_limit_exceeded_{event_id}")
            _check_artifact_pair(payload.get("har_artifact_id"), payload.get("har_artifact_sha256"), event, artifacts, errors, "browser_v3_har_artifact")
        return CoreGateCheck(name="browser_v3_har_body_capture_contract", kind=CoreGateCheckKind.EVIDENCE, passed=not errors, message="Browser V3 HAR/body capture is bounded, redacted, and artifact-bound." if not errors else "Browser V3 HAR/body contract failed.", details={"errors": errors})

    @staticmethod
    def _llm_context_pack_and_tool_intent_contract(result: AgentRunResult) -> CoreGateCheck:
        p3y_events = [
            event
            for event in result.trace
            if event.event_type
            in {
                AgentEventType.CONTEXT_PACK_ASSEMBLED,
                AgentEventType.CONTEXT_PACK_VALIDATED,
                AgentEventType.CONTEXT_PACK_REJECTED,
                AgentEventType.CONTEXT_PACK_REHYDRATED,
                AgentEventType.LLM_REASONING_DRAFTED,
                AgentEventType.LLM_VERIFICATION_DRAFTED,
                AgentEventType.TOOL_INTENT_COMPILED,
                AgentEventType.TOOL_INTENT_COMPILATION_REJECTED,
            }
        ]
        if not p3y_events:
            return CoreGateCheck(
                name="llm_context_pack_and_tool_intent_contract",
                kind=CoreGateCheckKind.EVIDENCE,
                passed=True,
                message="No P3Y LLM context-pack events were emitted.",
            )

        errors: list[str] = []
        assembled = {
            event.payload.get("context_pack_id"): event
            for event in p3y_events
            if event.event_type == AgentEventType.CONTEXT_PACK_ASSEMBLED and event.payload.get("context_pack_id")
        }
        validated = {
            event.payload.get("context_pack_id"): event
            for event in p3y_events
            if event.event_type == AgentEventType.CONTEXT_PACK_VALIDATED
            and event.payload.get("accepted") is True
            and event.payload.get("context_pack_id")
        }
        rejected = {
            event.payload.get("context_pack_id")
            for event in p3y_events
            if event.event_type == AgentEventType.CONTEXT_PACK_REJECTED and event.payload.get("context_pack_id")
        }

        for context_pack_id, event in assembled.items():
            if not event.payload.get("context_pack_sha256"):
                errors.append(f"context_pack_assembled_missing_hash:{context_pack_id}")
        for context_pack_id, event in validated.items():
            if context_pack_id not in assembled:
                errors.append(f"context_pack_validated_without_assembly:{context_pack_id}")
            if event.payload.get("errors"):
                errors.append(f"context_pack_validated_with_errors:{context_pack_id}")
            if not event.payload.get("context_pack_sha256"):
                errors.append(f"context_pack_validated_missing_hash:{context_pack_id}")

        for event in p3y_events:
            if event.event_type == AgentEventType.LLM_REASONING_DRAFTED:
                context_pack_id = event.payload.get("context_pack_id")
                if context_pack_id not in validated:
                    errors.append(f"llm_reasoning_without_validated_context_pack:{event.id}")
            elif event.event_type == AgentEventType.TOOL_INTENT_COMPILED:
                context_pack_id = event.payload.get("context_pack_id")
                if event.payload.get("accepted") is not True:
                    errors.append(f"tool_intent_compiled_not_accepted:{event.id}")
                if context_pack_id not in validated:
                    errors.append(f"tool_intent_compiled_without_validated_context_pack:{event.id}")
                if context_pack_id in rejected:
                    errors.append(f"tool_intent_compiled_after_rejected_context_pack:{event.id}")
                if not event.payload.get("canonical_hash") or not event.payload.get("compilation_hash"):
                    errors.append(f"tool_intent_compiled_missing_hash:{event.id}")
            elif event.event_type == AgentEventType.TOOL_INTENT_COMPILATION_REJECTED:
                if event.payload.get("accepted") is True:
                    errors.append(f"tool_intent_rejected_event_marked_accepted:{event.id}")

        return CoreGateCheck(
            name="llm_context_pack_and_tool_intent_contract",
            kind=CoreGateCheckKind.EVIDENCE,
            passed=not errors,
            message="P3Y LLM context-pack and tool-intent events are trace-bound." if not errors else "P3Y LLM context-pack/tool-intent contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _browser_lifecycle_check_url_policy(
        *,
        event,
        url_events: dict[str, Any],
        url_trace_id: str,
        expected_final_url: str | None,
        errors: list[str],
        prefix: str,
        require_allowed: bool = True,
    ) -> None:
        event_id = event.id
        if not url_trace_id:
            errors.append(f"{prefix}_missing_url_policy_{event_id}")
            return
        url_event = url_events.get(url_trace_id)
        if url_event is None:
            errors.append(f"{prefix}_url_policy_missing_{event_id}")
            return
        if url_event.sequence >= event.sequence:
            errors.append(f"{prefix}_url_policy_order_invalid_{event_id}")
        if url_trace_id not in event.trace_refs:
            errors.append(f"{prefix}_missing_url_trace_ref_{event_id}")
        if require_allowed and str(_enum_value(url_event.payload.get("status")) or "").lower() != "allowed":
            errors.append(f"{prefix}_url_policy_not_allowed_{event_id}")
        if expected_final_url is not None and url_event.payload.get("final_url") != expected_final_url:
            errors.append(f"{prefix}_url_policy_final_url_mismatch_{event_id}")

    @staticmethod
    def _mission_artifact_receipts(result: AgentRunResult) -> CoreGateCheck:
        if result.mission_result is None:
            return CoreGateCheck(
                name="mission_artifact_receipts",
                kind=CoreGateCheckKind.ARTIFACT,
                passed=True,
                message="Run has no mission result requiring artifact receipts.",
            )
        errors = CoreFinalGate._mission_artifact_receipt_errors(result.mission_result, result.mission_id)
        return CoreGateCheck(
            name="mission_artifact_receipts",
            kind=CoreGateCheckKind.ARTIFACT,
            passed=not errors,
            message="Mission artifacts include scoped receipts." if not errors else "Mission artifact receipt contract failed.",
            details={"errors": errors},
        )

    @staticmethod
    def _mission_artifact_receipt_errors(mission_result: MissionRunResult, expected_mission_id: str) -> list[str]:
        receipt_ids = [receipt.id for receipt in mission_result.artifact_receipts]
        receipt_event_ids = [
            str(event.result.get("id"))
            for event in mission_result.trace_events
            if event.event_type == MissionTraceEventType.ACTION_RECEIPT_RECORDED and event.result.get("id")
        ]
        receipt_by_id = {receipt.id: receipt for receipt in mission_result.artifact_receipts}
        receipt_event_by_id = {
            str(event.result.get("id")): event
            for event in mission_result.trace_events
            if event.event_type == MissionTraceEventType.ACTION_RECEIPT_RECORDED and event.result.get("id")
        }
        errors: list[str] = []
        for receipt_id in sorted(receipt_id for receipt_id in set(receipt_ids) if receipt_ids.count(receipt_id) > 1):
            errors.append(f"duplicate_artifact_receipt_{receipt_id}")
        for receipt_id in sorted(receipt_id for receipt_id in set(receipt_event_ids) if receipt_event_ids.count(receipt_id) > 1):
            errors.append(f"duplicate_artifact_receipt_event_{receipt_id}")
        for index, artifact in enumerate(mission_result.artifacts):
            if not artifact.receipt_id:
                errors.append(f"missing_artifact_receipt_id_{index}")
                continue
            receipt = receipt_by_id.get(artifact.receipt_id)
            if receipt is None:
                errors.append(f"missing_artifact_receipt_{index}")
                continue
            path = PurePosixPath(receipt.artifact_path.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                errors.append(f"receipt_path_out_of_scope_{index}")
            if receipt.mission_id != expected_mission_id:
                errors.append(f"receipt_mission_mismatch_{index}")
            if receipt.artifact_id != artifact.id:
                errors.append(f"receipt_artifact_mismatch_{index}")
            if receipt.artifact_sha256 != artifact.sha256:
                errors.append(f"receipt_hash_mismatch_{index}")
            if not receipt.rollback_strategy:
                errors.append(f"receipt_missing_rollback_strategy_{index}")
            if not receipt.trace_refs:
                errors.append(f"receipt_missing_trace_refs_{index}")
            receipt_event = receipt_event_by_id.get(receipt.id)
            if receipt_event is None:
                errors.append(f"receipt_missing_trace_event_{index}")
                continue
            if receipt_event.action_id != receipt.action_id:
                errors.append(f"receipt_action_event_mismatch_{index}")
            if receipt_event.target != receipt.artifact_path:
                errors.append(f"receipt_target_event_mismatch_{index}")
            if receipt_event.result.get("artifact_sha256") != receipt.artifact_sha256:
                errors.append(f"receipt_hash_event_mismatch_{index}")
        return errors

    @staticmethod
    def _project_scope(result: AgentRunResult, allowed_project_root: Path) -> CoreGateCheck:
        if result.project_path is None:
            return CoreGateCheck(
                name="project_scope",
                kind=CoreGateCheckKind.SCOPE,
                passed=True,
                message="Run has no project path to scope.",
            )
        project_path = Path(result.project_path).resolve()
        try:
            project_path.relative_to(allowed_project_root)
            passed = True
        except ValueError:
            passed = False
        return CoreGateCheck(
            name="project_scope",
            kind=CoreGateCheckKind.SCOPE,
            passed=passed,
            message="Project path is inside the allowed root." if passed else "Project path escapes the allowed root.",
            details={"project_path": str(project_path), "allowed_project_root": str(allowed_project_root)},
        )


def certify_core_final_gate(
    result: AgentRunResult,
    *,
    allowed_project_root: str | Path | None = None,
) -> CoreFinalGateResult:
    return CoreFinalGate().evaluate(result, allowed_project_root=allowed_project_root)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else -1


def _accepted_compiled_event_ids(result: AgentRunResult) -> set[str]:
    return {
        event.id
        for event in result.trace
        if event.event_type == AgentEventType.TOOL_INTENT_COMPILED and event.payload.get("accepted") is True
    }


def _artifact_events_by_id(result: AgentRunResult) -> dict[str, Any]:
    return {
        str(event.payload.get("artifact_id")): event
        for event in result.trace
        if event.event_type == AgentEventType.ARTIFACT_CAPTURED and event.payload.get("artifact_id")
    }


def _check_basic_v3_event(payload: dict[str, Any], event: Any, compiled_events: set[str], errors: list[str], prefix: str) -> None:
    event_id = event.id
    if not payload.get("authority_grant_id"):
        errors.append(f"{prefix}_missing_grant_{event_id}")
    if not payload.get("context_pack_id"):
        errors.append(f"{prefix}_missing_context_pack_{event_id}")
    compiled_trace_id = str(payload.get("compiled_intent_trace_id") or "")
    if not compiled_trace_id:
        errors.append(f"{prefix}_missing_compiled_intent_{event_id}")
    elif event.event_type.name.endswith("REJECTED") or str(event.event_type).endswith("_rejected"):
        return
    elif compiled_trace_id not in compiled_events:
        errors.append(f"{prefix}_compiled_intent_missing_{event_id}")
    elif compiled_trace_id not in event.trace_refs:
        errors.append(f"{prefix}_compiled_trace_ref_missing_{event_id}")
    if not payload.get("receipt_id") and not (event.event_type.name.endswith("REJECTED") or str(event.event_type).endswith("_rejected")):
        errors.append(f"{prefix}_missing_receipt_{event_id}")


def _check_artifact_pair(
    artifact_id: Any,
    expected_hash: Any,
    event: Any,
    artifact_events: dict[str, Any],
    errors: list[str],
    prefix: str,
) -> None:
    event_id = event.id
    artifact_id = str(artifact_id or "")
    if not artifact_id:
        errors.append(f"{prefix}_missing_artifact_{event_id}")
        return
    artifact_event = artifact_events.get(artifact_id)
    if artifact_event is None:
        errors.append(f"{prefix}_artifact_event_missing_{event_id}")
        return
    if artifact_event.sequence >= event.sequence:
        errors.append(f"{prefix}_artifact_order_invalid_{event_id}")
    if expected_hash and artifact_event.payload.get("sha256") != expected_hash:
        errors.append(f"{prefix}_artifact_hash_mismatch_{event_id}")


def _check_no_credential_payload(payload: dict[str, Any], errors: list[str], code: str) -> None:
    forbidden = ("password", "secret", "token", "credential_value", "cookie_value")

    def visit(value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                if any(marker in str(key).lower() for marker in forbidden):
                    return True
                if visit(item):
                    return True
        elif isinstance(value, list):
            return any(visit(item) for item in value)
        elif isinstance(value, str):
            lowered = value.lower()
            return any(marker in lowered for marker in ("password=", "bearer ", "secret=", "cookie:"))
        return False

    if visit(payload):
        errors.append(code)


# Task 1.3 / Requirement 1 (FinalGate Runtime Integration):
# ``AgentRunResult.final_gate_certification`` is typed as a forward reference
# to ``CoreFinalGateResult`` to avoid a circular import (models.py is loaded
# before this module). Now that both classes are defined, resolve the forward
# reference so the field validates/serializes correctly at runtime.
from sentinel.perf.measure.performance_receipt import PerformanceReceipt as _PerformanceReceipt
from sentinel.agent.brain.cognition_loop import BrainCognitionResult as _BrainCognitionResult
from sentinel.agent.llm.memory_bridge import MemoryBridgeResult as _MemoryBridgeResult
from sentinel.agent.organs.organ_dispatch import OrganDispatchResult as _OrganDispatchResult

AgentRunResult.model_rebuild(
    _types_namespace={
        "CoreFinalGateResult": CoreFinalGateResult,
        "BrainCognitionResult": _BrainCognitionResult,
        "MemoryBridgeResult": _MemoryBridgeResult,
        "OrganDispatchResult": _OrganDispatchResult,
        "PerformanceReceipt": _PerformanceReceipt,
    }
)
