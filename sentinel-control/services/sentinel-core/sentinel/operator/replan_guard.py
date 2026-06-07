from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.workflow_models import (
    ReplanCandidate,
    ReplanDecision,
    ReplanDecisionKind,
    ReplanExecutionPolicy,
    ReplanExecutionTarget,
    WorkflowAuthoritySnapshot,
    authority_fingerprint_payload,
    step_contract_hashes_from_plan,
    target_scope_from_plan,
)
from sentinel.power.runtime import PowerActuatorCapabilityLevel


_CAPABILITY_RANK = {
    PowerActuatorCapabilityLevel.L2: 2,
    PowerActuatorCapabilityLevel.L3: 3,
    PowerActuatorCapabilityLevel.L4: 4,
    PowerActuatorCapabilityLevel.L5: 5,
    PowerActuatorCapabilityLevel.L6: 6,
    PowerActuatorCapabilityLevel.L7: 7,
}

_SPECIAL_AUTHORITY_MARKERS = {
    "account_creation",
    "browser_login",
    "captcha",
    "channel_send",
    "desktop_action",
    "desktop_sensitive",
    "kyc",
    "payment",
    "security_test",
    "send_email",
    "spend",
    "trade",
    "trading",
}

_IRREVERSIBLE_MARKERS = {
    "api_mutation",
    "delete",
    "irreversible",
    "publish",
    "send_now",
    "submit_payment",
    "transfer",
}


class ReplanExecutionGuard:
    def __init__(self, policy: ReplanExecutionPolicy | None = None) -> None:
        self.policy = policy or ReplanExecutionPolicy()

    def evaluate(
        self,
        *,
        snapshot: WorkflowAuthoritySnapshot,
        current_envelope: MissionAuthorityEnvelope,
        candidate: ReplanCandidate,
        completed_action_count: int,
        cost_used_usd: float,
        latest_checkpoint_id: str,
        reserved_action_count: int = 0,
        reserved_cost_usd: float = 0.0,
        current_time: datetime | None = None,
    ) -> ReplanDecision:
        now = current_time or datetime.now(UTC)
        failures: list[str] = []

        if current_envelope.revoked_at is not None:
            failures.append("mission_revoked")
        if now > current_envelope.resolved_expires_at():
            failures.append("mission_expired")
        if current_envelope.id != snapshot.envelope_id or candidate.mission_id != snapshot.envelope_id:
            failures.append("mission_identity_changed")
        if candidate.source_checkpoint_id != latest_checkpoint_id:
            failures.append("stale_replan_checkpoint")
        if stable_hash(current_envelope.mission_objective) != snapshot.mission_objective_hash:
            failures.append("mission_objective_changed")
        if candidate.mission_objective_hash != snapshot.mission_objective_hash:
            failures.append("candidate_objective_changed")
        if stable_hash(authority_fingerprint_payload(current_envelope)) != snapshot.authority_fingerprint:
            failures.append("authority_envelope_changed")

        self._check_runtime_contract(snapshot, candidate, failures)
        self._check_budget(
            snapshot,
            candidate,
            completed_action_count,
            reserved_action_count,
            cost_used_usd,
            reserved_cost_usd,
            failures,
        )
        self._check_candidate_plan(snapshot, current_envelope, candidate, failures)

        if self.policy.require_confirmation_for_every_replan:
            failures.append("operator_confirmation_policy")
        if not self.policy.automatic_inside_authority:
            failures.append("automatic_replan_disabled")

        failures = _dedupe(failures)
        if failures:
            return ReplanDecision(
                kind=ReplanDecisionKind.ESCALATE,
                candidate_id=candidate.candidate_id,
                guard_failures=failures,
                safe_summary="Replan requires an operator checkpoint because one or more authority guards failed.",
            )
        return ReplanDecision(
            kind=ReplanDecisionKind.AUTO_EXECUTE,
            candidate_id=candidate.candidate_id,
            safe_summary="Replan remains inside the existing mission authority envelope.",
        )

    @staticmethod
    def _check_runtime_contract(
        snapshot: WorkflowAuthoritySnapshot,
        candidate: ReplanCandidate,
        failures: list[str],
    ) -> None:
        if candidate.executor_contract_id != snapshot.executor_contract_id:
            failures.append("executor_contract_changed")
        if (
            candidate.provider_id != snapshot.provider_id
            or candidate.backend_id != snapshot.backend_id
            or candidate.model_id != snapshot.model_id
            or candidate.model_contract_hash != snapshot.model_contract_hash
        ):
            failures.append("provider_contract_changed")

    @staticmethod
    def _check_budget(
        snapshot: WorkflowAuthoritySnapshot,
        candidate: ReplanCandidate,
        completed_action_count: int,
        reserved_action_count: int,
        cost_used_usd: float,
        reserved_cost_usd: float,
        failures: list[str],
    ) -> None:
        candidate_actions = (
            sum(1 + step.retry_budget for step in candidate.power_plan.graph.steps)
            if candidate.power_plan is not None
            else 1
        )
        if completed_action_count + reserved_action_count + candidate_actions > snapshot.max_actions:
            failures.append("action_budget_expansion")
        plan_cost = (
            sum(
                step.estimated_cost_usd * (1 + step.retry_budget)
                for step in candidate.power_plan.graph.steps
            )
            if candidate.power_plan is not None
            else 0.0
        )
        candidate_cost = max(candidate.estimated_cost_usd, plan_cost)
        if cost_used_usd + reserved_cost_usd + candidate_cost > snapshot.max_cost_usd:
            failures.append("cost_budget_expansion")
        if candidate.estimated_cost_usd > plan_cost:
            failures.append("unproven_cost_estimate")
        recipient_count = (
            len(target_scope_from_plan(candidate.power_plan).recipient_hashes)
            if candidate.power_plan is not None
            else candidate.estimated_recipient_count
        )
        if max(recipient_count, candidate.estimated_recipient_count) > snapshot.max_recipients:
            failures.append("recipient_budget_expansion")

    @staticmethod
    def _check_candidate_plan(
        snapshot: WorkflowAuthoritySnapshot,
        current_envelope: MissionAuthorityEnvelope,
        candidate: ReplanCandidate,
        failures: list[str],
    ) -> None:
        if candidate.execution_target is ReplanExecutionTarget.AGENT_RUNTIME:
            failures.append("agent_runtime_replan_requires_typed_plan")
            return
        plan = candidate.power_plan
        if plan is None:
            failures.append("power_plan_missing")
            return
        if not plan.graph.steps:
            failures.append("empty_replan_plan")
            return
        if plan.mission_id != snapshot.envelope_id:
            failures.append("power_plan_mission_changed")
        action_kinds = {step.action_kind for step in plan.graph.steps}
        organ_kinds = {step.organ_kind for step in plan.graph.steps}
        actuator_families = {step.actuator_family.value for step in plan.graph.steps}
        if not action_kinds.issubset(set(snapshot.approved_action_kinds)):
            failures.append("action_class_expansion")
        if not action_kinds.issubset(set(current_envelope.allowed_actions)):
            failures.append("action_outside_envelope")
        if not organ_kinds.issubset(set(snapshot.approved_organ_kinds)):
            failures.append("organ_scope_expansion")
        if not actuator_families.issubset(set(snapshot.approved_actuator_families)):
            failures.append("actuator_family_expansion")
        if not _counter_is_subset(
            Counter(step_contract_hashes_from_plan(plan)),
            Counter(snapshot.approved_step_contract_hashes),
        ):
            failures.append("step_contract_expansion")
        if any(
            _CAPABILITY_RANK[step.capability_level] > _CAPABILITY_RANK[snapshot.max_capability_level]
            for step in plan.graph.steps
        ):
            failures.append("risk_lane_increased")
        if any(step.capability_level in {PowerActuatorCapabilityLevel.L6, PowerActuatorCapabilityLevel.L7} for step in plan.graph.steps):
            failures.append("special_authority_boundary")
        candidate_scope = target_scope_from_plan(plan)
        if not candidate_scope.is_subset_of(snapshot.target_scope):
            failures.append("target_scope_expansion")
        markers = _markers(plan.model_dump(mode="json"))
        if _matches_any_marker(markers, _SPECIAL_AUTHORITY_MARKERS):
            failures.append("special_authority_boundary")
        if _matches_any_marker(markers, _IRREVERSIBLE_MARKERS):
            failures.append("irreversible_action_boundary")
        if any("credential" in marker or "secret" in marker for marker in markers):
            failures.append("credential_scope_unproven")


def _markers(value: Any) -> set[str]:
    markers: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            markers.add(str(key).strip().lower())
            markers.update(_markers(item))
    elif isinstance(value, list | tuple | set):
        for item in value:
            markers.update(_markers(item))
    elif isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        markers.add(normalized)
    return markers


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _counter_is_subset(candidate: Counter[str], approved: Counter[str]) -> bool:
    return all(count <= approved[value] for value, count in candidate.items())


def _matches_any_marker(markers: set[str], denied: set[str]) -> bool:
    return any(
        marker == value
        or marker.startswith(f"{value}_")
        or marker.endswith(f"_{value}")
        or f"_{value}_" in marker
        for marker in markers
        for value in denied
    )
