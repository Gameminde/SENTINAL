from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.safety import assert_data_not_authority
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerMissionPlan,
    PowerStepStatus,
)
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized


class WorkflowStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    WAITING_REPLAN = "waiting_replan"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    KILLED = "killed"
    FAILED = "failed"


class WorkflowBranchStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ReplanExecutionTarget(StrEnum):
    POWER_RUNTIME = "power_runtime"
    AGENT_RUNTIME = "agent_runtime"


class ReplanDecisionKind(StrEnum):
    AUTO_EXECUTE = "auto_execute"
    ESCALATE = "escalate"
    BLOCK = "block"


class ReplanExecutionPolicy(SentinelModel):
    automatic_inside_authority: bool = True
    require_confirmation_for_every_replan: bool = False
    max_automatic_replans: int = Field(default=3, ge=0, le=50)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _policy_is_not_authority(self) -> ReplanExecutionPolicy:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("replan policy cannot grant authority")
        return self


class ReplanTargetScope(SentinelModel):
    domain_hashes: list[str] = Field(default_factory=list)
    endpoint_hashes: list[str] = Field(default_factory=list)
    path_hashes: list[str] = Field(default_factory=list)
    recipient_hashes: list[str] = Field(default_factory=list)
    merchant_hashes: list[str] = Field(default_factory=list)
    asset_hashes: list[str] = Field(default_factory=list)
    account_hashes: list[str] = Field(default_factory=list)
    data_not_authority: bool = True
    authority_effect: str = "none"

    @model_validator(mode="after")
    def _scope_is_data(self) -> ReplanTargetScope:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("replan target scope cannot grant authority")
        return self

    def is_subset_of(self, other: ReplanTargetScope) -> bool:
        for field_name in (
            "domain_hashes",
            "endpoint_hashes",
            "path_hashes",
            "recipient_hashes",
            "merchant_hashes",
            "asset_hashes",
            "account_hashes",
        ):
            if not set(getattr(self, field_name)).issubset(set(getattr(other, field_name))):
                return False
        return True


class WorkflowAuthoritySnapshot(SentinelModel):
    envelope_id: str
    mission_objective_hash: str
    authority_fingerprint: str
    allowed_action_classes: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_systems: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_accounts_hash: str
    allowed_data_types: list[str] = Field(default_factory=list)
    browser_grants_hash: str
    credential_grants_hash: str
    max_duration_minutes: int
    max_actions: int
    max_cost_usd: float
    max_recipients: int
    risk_appetite_score: float
    expires_at: datetime
    approved_organ_kinds: list[str] = Field(default_factory=list)
    approved_action_kinds: list[str] = Field(default_factory=list)
    approved_actuator_families: list[str] = Field(default_factory=list)
    approved_step_contract_hashes: list[str] = Field(default_factory=list)
    max_capability_level: PowerActuatorCapabilityLevel
    executor_contract_id: str
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    model_contract_hash: str | None = None
    target_scope: ReplanTargetScope = Field(default_factory=ReplanTargetScope)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _snapshot_is_not_authority(self) -> WorkflowAuthoritySnapshot:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("workflow authority snapshot is comparison data only")
        return self

    @classmethod
    def from_runtime(
        cls,
        *,
        envelope: MissionAuthorityEnvelope,
        plan: PowerMissionPlan,
        executor_contract_id: str,
        provider_id: str | None = None,
        backend_id: str | None = None,
        model_id: str | None = None,
        model_contract_hash: str | None = None,
    ) -> WorkflowAuthoritySnapshot:
        assert_workflow_plan_persistable(plan)
        authority_payload = authority_fingerprint_payload(envelope)
        return cls(
            envelope_id=envelope.id,
            mission_objective_hash=stable_hash(envelope.mission_objective),
            authority_fingerprint=stable_hash(authority_payload),
            allowed_action_classes=sorted(set(envelope.allowed_actions)),
            allowed_tools=sorted(set(envelope.allowed_tools)),
            allowed_systems=sorted(set(envelope.allowed_systems)),
            allowed_paths=sorted(set(envelope.allowed_paths)),
            allowed_domains=sorted({_normalize_domain(value) for value in envelope.allowed_domains if value}),
            allowed_accounts_hash=stable_hash(sorted(str(value) for value in envelope.allowed_accounts)),
            allowed_data_types=sorted(set(envelope.allowed_data_types)),
            browser_grants_hash=stable_hash(envelope.browser_v3_authority_grants),
            credential_grants_hash=stable_hash(
                [
                    item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                    for item in envelope.credential_grants
                ]
            ),
            max_duration_minutes=envelope.max_duration_minutes,
            max_actions=envelope.max_actions,
            max_cost_usd=envelope.max_cost_usd,
            max_recipients=envelope.max_recipients,
            risk_appetite_score=envelope.risk_appetite_score,
            expires_at=envelope.resolved_expires_at(),
            approved_organ_kinds=sorted({step.organ_kind for step in plan.graph.steps}),
            approved_action_kinds=sorted({step.action_kind for step in plan.graph.steps}),
            approved_actuator_families=sorted({step.actuator_family.value for step in plan.graph.steps}),
            approved_step_contract_hashes=step_contract_hashes_from_plan(plan),
            max_capability_level=_max_capability_level(plan),
            executor_contract_id=executor_contract_id,
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
            model_contract_hash=model_contract_hash,
            target_scope=target_scope_from_plan(plan),
        )


class WorkflowStepState(SentinelModel):
    step_id: str
    status: PowerStepStatus
    attempt_count: int = Field(default=0, ge=0)
    proof_id: str | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    safe_summary: str = ""
    result_hash: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _completed_step_requires_proof(self) -> WorkflowStepState:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("workflow step state cannot grant authority")
        if self.status is PowerStepStatus.SUCCEEDED:
            if not self.receipt_refs or not self.finalgate_certificate_refs or not self.proof_id or not self.result_hash:
                raise ValueError("successful durable workflow step requires receipt and FinalGate proof")
        return self


class WorkflowStepProof(SentinelModel):
    proof_id: str = Field(default_factory=lambda: new_id("workflow_step_proof"))
    workflow_id: str
    mission_id: str
    branch_id: str
    plan_hash: str
    step_id: str
    step_contract_hash: str
    status: PowerStepStatus
    attempt_count: int = Field(ge=0)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    safe_summary: str = ""
    result_hash: str
    proof_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _proof_is_evidence_only(self) -> WorkflowStepProof:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("workflow step proof cannot grant authority")
        if self.status is PowerStepStatus.SUCCEEDED and (
            not self.receipt_refs or not self.finalgate_certificate_refs
        ):
            raise ValueError("successful workflow step proof requires receipt and FinalGate refs")
        return self

    def with_hash(self) -> WorkflowStepProof:
        payload = self.model_dump(mode="json")
        payload.pop("proof_hash", None)
        return self.model_copy(update={"proof_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.model_dump(mode="json")
        stored = payload.pop("proof_hash")
        return bool(stored) and stored == stable_hash(payload)


class ResumeCursor(SentinelModel):
    workflow_id: str
    branch_id: str
    plan_hash: str
    checkpoint_id: str | None = None
    completed_step_ids: list[str] = Field(default_factory=list)
    pending_step_ids: list[str] = Field(default_factory=list)
    authority_fingerprint: str
    cursor_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _cursor_is_data(self) -> ResumeCursor:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("resume cursor cannot grant authority")
        return self

    def with_hash(self) -> ResumeCursor:
        payload = self.model_dump(mode="json")
        payload.pop("cursor_hash", None)
        return self.model_copy(update={"cursor_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.model_dump(mode="json")
        stored = payload.pop("cursor_hash")
        return bool(stored) and stored == stable_hash(payload)


class WorkflowBranch(SentinelModel):
    branch_id: str = Field(default_factory=lambda: new_id("workflow_branch"))
    parent_branch_id: str | None = None
    source_checkpoint_id: str | None = None
    plan_hash: str
    execution_target: ReplanExecutionTarget = ReplanExecutionTarget.POWER_RUNTIME
    status: WorkflowBranchStatus = WorkflowBranchStatus.ACTIVE
    safe_reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_effect: str = "none"
    data_not_authority: bool = True


class WorkflowCheckpoint(SentinelModel):
    checkpoint_id: str = Field(default_factory=lambda: new_id("workflow_checkpoint"))
    workflow_id: str
    mission_id: str
    branch_id: str
    plan_hash: str
    authority_fingerprint: str
    record_version: int = Field(ge=0)
    safe_reason: str
    step_states: list[WorkflowStepState] = Field(default_factory=list)
    resume_cursor: ResumeCursor
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    prepared_event_hash: str
    checkpoint_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _checkpoint_is_data(self) -> WorkflowCheckpoint:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("workflow checkpoint cannot grant authority")
        return self

    def with_hash(self) -> WorkflowCheckpoint:
        payload = self.model_dump(mode="json")
        payload.pop("checkpoint_hash", None)
        return self.model_copy(update={"checkpoint_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.model_dump(mode="json")
        stored = payload.pop("checkpoint_hash")
        return bool(stored) and stored == stable_hash(payload)


class ReplanCandidate(SentinelModel):
    candidate_id: str = Field(default_factory=lambda: new_id("replan_candidate"))
    workflow_id: str
    mission_id: str
    source_checkpoint_id: str
    mission_objective: str | None = Field(default=None, exclude=True, repr=False)
    mission_objective_hash: str | None = None
    execution_target: ReplanExecutionTarget = ReplanExecutionTarget.POWER_RUNTIME
    power_plan: PowerMissionPlan | None = None
    agent_user_input: dict[str, Any] | None = Field(default=None, exclude=True, repr=False)
    agent_input_hash: str | None = None
    executor_contract_id: str
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    model_contract_hash: str | None = None
    reason: str
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    estimated_recipient_count: int = Field(default=0, ge=0)
    source_replan_packet_ref: str | None = None
    memory_feedback_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_is_authority: bool = False
    receipt_approves_execution: bool = False
    finalgate_allows_future_execution: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_execute: bool = False

    @model_validator(mode="after")
    def _candidate_is_proposal_only(self) -> ReplanCandidate:
        assert_data_not_authority(
            context="replan_candidate",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=False,
            can_execute=self.can_execute,
        )
        if self.memory_is_authority or self.receipt_approves_execution or self.finalgate_allows_future_execution:
            raise ValueError("replan evidence cannot become permission")
        if self.mission_objective is not None:
            objective_hash = stable_hash(self.mission_objective)
            if self.mission_objective_hash is not None and self.mission_objective_hash != objective_hash:
                raise ValueError("replan mission objective hash mismatch")
            self.mission_objective_hash = objective_hash
        if not self.mission_objective_hash:
            raise ValueError("replan mission objective hash required")
        metadata_scan = scan_forbidden_payload_categorized(
            {
                "reason": self.reason,
                "executor_contract_id": self.executor_contract_id,
                "provider_id": self.provider_id,
                "backend_id": self.backend_id,
                "model_id": self.model_id,
                "model_contract_hash": self.model_contract_hash,
                "source_replan_packet_ref": self.source_replan_packet_ref,
            },
            path="$.replan_candidate.persisted_metadata",
        )
        if metadata_scan[OrganSafetyScanCategory.SECRET.value]:
            raise ValueError("replan candidate contains secret-like persisted metadata")
        if self.execution_target is ReplanExecutionTarget.POWER_RUNTIME:
            if self.power_plan is None or self.agent_user_input is not None:
                raise ValueError("power replan requires only a power plan")
            assert_workflow_plan_persistable(self.power_plan)
        else:
            if self.agent_user_input is None or self.power_plan is not None:
                raise ValueError("agent replan requires only safe agent input")
            scan = scan_forbidden_payload_categorized(self.agent_user_input, path="$.agent_user_input")
            if scan[OrganSafetyScanCategory.ALL.value]:
                raise ValueError("agent replan input contains forbidden control payload")
            expected_hash = stable_hash(self.agent_user_input)
            if self.agent_input_hash is not None and self.agent_input_hash != expected_hash:
                raise ValueError("agent replan input hash mismatch")
            self.agent_input_hash = expected_hash
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        payload = self.model_dump(mode="json")
        payload["agent_input_hash"] = self.agent_input_hash
        return payload


class ReplanDecision(SentinelModel):
    kind: ReplanDecisionKind
    candidate_id: str
    guard_failures: list[str] = Field(default_factory=list)
    safe_summary: str
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_execute: bool = False

    @model_validator(mode="after")
    def _decision_is_not_permission(self) -> ReplanDecision:
        assert_data_not_authority(
            context="replan_decision",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=False,
            can_execute=self.can_execute,
        )
        return self


class DurableWorkflowRecord(SentinelModel):
    workflow_id: str = Field(default_factory=lambda: new_id("workflow"))
    mission_id: str
    snapshot: WorkflowAuthoritySnapshot
    initial_plan_hash: str
    current_branch_id: str
    branches: list[WorkflowBranch] = Field(default_factory=list)
    latest_checkpoint_id: str | None = None
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    automatic_replan_count: int = Field(default=0, ge=0)
    completed_action_count: int = Field(default=0, ge=0)
    reserved_action_count: int = Field(default=0, ge=0)
    cost_used_usd: float = Field(default=0.0, ge=0.0)
    reserved_cost_usd: float = Field(default=0.0, ge=0.0)
    record_version: int = Field(default=0, ge=0)
    record_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    authority_effect: str = "none"
    data_not_authority: bool = True

    @classmethod
    def create(
        cls,
        *,
        mission_id: str,
        snapshot: WorkflowAuthoritySnapshot,
        initial_plan: PowerMissionPlan,
    ) -> DurableWorkflowRecord:
        if initial_plan.mission_id != mission_id or snapshot.envelope_id != mission_id:
            raise ValueError("workflow mission identity mismatch")
        plan_hash = stable_hash(initial_plan.model_dump(mode="json"))
        branch = WorkflowBranch(
            plan_hash=plan_hash,
            execution_target=ReplanExecutionTarget.POWER_RUNTIME,
            safe_reason="initial governed workflow branch",
        )
        return cls(
            mission_id=mission_id,
            snapshot=snapshot,
            initial_plan_hash=plan_hash,
            current_branch_id=branch.branch_id,
            branches=[branch],
        ).with_hash()

    def with_hash(self) -> DurableWorkflowRecord:
        payload = self.model_dump(mode="json")
        payload.pop("record_hash", None)
        return self.model_copy(update={"record_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.model_dump(mode="json")
        stored = payload.pop("record_hash")
        return bool(stored) and stored == stable_hash(payload)


class WorkflowReplayView(SentinelModel):
    workflow_id: str
    mission_id: str
    record: DurableWorkflowRecord | None = None
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)
    tampered: bool = False
    reexecuted_actions: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True


class WorkflowRunResult(SentinelModel):
    workflow_id: str
    mission_id: str
    status: WorkflowStatus
    decision: ReplanDecision | None = None
    latest_checkpoint_id: str | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    safe_summary: str
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _run_result_is_evidence_only(self) -> WorkflowRunResult:
        assert_data_not_authority(
            context="workflow_run_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


def authority_fingerprint_payload(envelope: MissionAuthorityEnvelope) -> dict[str, Any]:
    return {
        "id": envelope.id,
        "user_id": envelope.user_id,
        "mission_type": envelope.mission_type.value,
        "mission_title": envelope.mission_title,
        "mission_objective": envelope.mission_objective,
        "success_criteria": sorted(set(envelope.success_criteria)),
        "mode": envelope.mode.value,
        "allowed_systems": sorted(set(envelope.allowed_systems)),
        "allowed_tools": sorted(set(envelope.allowed_tools)),
        "allowed_actions": sorted(set(envelope.allowed_actions)),
        "forbidden_actions": sorted(set(envelope.forbidden_actions)),
        "allowed_paths": sorted(set(envelope.allowed_paths)),
        "allowed_domains": sorted({_normalize_domain(value) for value in envelope.allowed_domains if value}),
        "allowed_accounts_hash": stable_hash(sorted(str(value) for value in envelope.allowed_accounts)),
        "allowed_data_types": sorted(set(envelope.allowed_data_types)),
        "browser_grants_hash": stable_hash(envelope.browser_v3_authority_grants),
        "credential_grants_hash": stable_hash(
            [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in envelope.credential_grants
            ]
        ),
        "max_duration_minutes": envelope.max_duration_minutes,
        "max_actions": envelope.max_actions,
        "max_cost_usd": envelope.max_cost_usd,
        "max_recipients": envelope.max_recipients,
        "risk_appetite_score": envelope.risk_appetite_score,
        "escalation_triggers": sorted(set(envelope.escalation_triggers)),
        "expires_at": envelope.resolved_expires_at(),
        "rollback_preference": envelope.rollback_preference,
        "trace_level": envelope.trace_level,
        "emergency_stop_enabled": envelope.emergency_stop_enabled,
        "created_at": envelope.created_at,
        "revoked_at": envelope.revoked_at,
    }


def target_scope_from_plan(
    plan: PowerMissionPlan,
) -> ReplanTargetScope:
    buckets: dict[str, set[str]] = {
        "domain_hashes": set(),
        "endpoint_hashes": set(),
        "path_hashes": set(),
        "recipient_hashes": set(),
        "merchant_hashes": set(),
        "asset_hashes": set(),
        "account_hashes": set(),
    }
    for step in plan.graph.steps:
        _collect_target_scope(step.request, buckets)
    return ReplanTargetScope(**{key: sorted(value) for key, value in buckets.items()})


def _collect_target_scope(
    value: Any,
    buckets: dict[str, set[str]],
    *,
    key: str = "",
    method: str = "GET",
) -> None:
    normalized_key = key.strip().lower()
    if isinstance(value, dict):
        child_method = str(value.get("method") or method or "GET").upper()
        for child_key, child_value in value.items():
            _collect_target_scope(child_value, buckets, key=str(child_key), method=child_method)
        return
    if isinstance(value, list | tuple | set):
        for item in value:
            _collect_target_scope(item, buckets, key=normalized_key, method=method)
        return
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    if normalized_key in {"url", "uri", "page_url"}:
        domain = _normalize_domain(text)
        if domain:
            buckets["domain_hashes"].add(stable_hash(domain))
        endpoint = _canonical_endpoint(text, method=method)
        if endpoint:
            buckets["endpoint_hashes"].add(stable_hash(endpoint))
        return
    mapping = {
        "endpoint": "endpoint_hashes",
        "api_endpoint": "endpoint_hashes",
        "path": "path_hashes",
        "file_path": "path_hashes",
        "target_path": "path_hashes",
        "recipient": "recipient_hashes",
        "recipients": "recipient_hashes",
        "merchant": "merchant_hashes",
        "merchant_id": "merchant_hashes",
        "asset": "asset_hashes",
        "asset_id": "asset_hashes",
        "account": "account_hashes",
        "account_id": "account_hashes",
    }
    bucket = mapping.get(normalized_key)
    if bucket:
        buckets[bucket].add(stable_hash(text))


def _normalize_domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").strip().lower()


def _canonical_endpoint(value: str, *, method: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return ""
    scheme = (parsed.scheme or "https").lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    suffix = f"?{query}" if query else ""
    return f"{method.upper()} {scheme}://{host}:{port}{path}{suffix}"


_REQUEST_TARGET_KEYS = {
    "account",
    "account_id",
    "api_endpoint",
    "asset",
    "asset_id",
    "endpoint",
    "file_path",
    "merchant",
    "merchant_id",
    "page_url",
    "path",
    "recipient",
    "recipients",
    "target_path",
    "uri",
    "url",
}
_REQUEST_RUNTIME_VARIATION_KEYS = {
    "element_ref",
    "locator",
    "ref",
    "selector",
    "target_ref",
    "target_selector",
    "uid",
}


def step_contract_hashes_from_plan(plan: PowerMissionPlan) -> list[str]:
    return sorted(step_contract_hash_from_step(step) for step in plan.graph.steps)


def step_contract_hash_from_step(step: Any) -> str:
    return stable_hash(
        {
            "actuator_family": step.actuator_family.value,
            "capability_level": step.capability_level.value,
            "organ_kind": step.organ_kind,
            "action_kind": step.action_kind,
            "estimated_cost_usd": step.estimated_cost_usd,
            "request_contract": _request_contract_payload(step.request),
        }
    )


def assert_workflow_plan_persistable(plan: PowerMissionPlan) -> None:
    scan = scan_forbidden_payload_categorized(plan, path="$.workflow_plan")
    forbidden_categories = (
        OrganSafetyScanCategory.SECRET,
        OrganSafetyScanCategory.PROVIDER_OVERRIDE,
        OrganSafetyScanCategory.AUTHORITY_EXPANSION,
        OrganSafetyScanCategory.UNSAFE_PAYLOAD,
    )
    if any(scan[category.value] for category in forbidden_categories) or _contains_sensitive_url_query(
        plan.model_dump(mode="python")
    ):
        raise ValueError("workflow_plan_contains_forbidden_persisted_payload")


def _contains_sensitive_url_query(value: Any, *, key: str = "") -> bool:
    normalized_key = key.strip().lower()
    if isinstance(value, dict):
        return any(_contains_sensitive_url_query(item, key=str(child_key)) for child_key, item in value.items())
    if isinstance(value, list | tuple | set):
        return any(_contains_sensitive_url_query(item, key=normalized_key) for item in value)
    if not isinstance(value, str) or normalized_key not in {"url", "uri", "page_url"}:
        return False
    sensitive_keys = {"api_key", "authorization", "bearer", "credential", "password", "secret", "token"}
    return any(query_key.strip().lower() in sensitive_keys for query_key, _ in parse_qsl(urlparse(value).query))


def _request_contract_payload(value: Any, *, key: str = "") -> Any:
    normalized_key = key.strip().lower()
    if normalized_key in _REQUEST_TARGET_KEYS:
        return {"target_field": normalized_key}
    if normalized_key in _REQUEST_RUNTIME_VARIATION_KEYS:
        return {"runtime_variation_field": normalized_key}
    if isinstance(value, dict):
        return {
            str(child_key): _request_contract_payload(child_value, key=str(child_key))
            for child_key, child_value in sorted(value.items(), key=lambda item: str(item[0]))
            if str(child_key).strip().lower() not in _REQUEST_RUNTIME_VARIATION_KEYS
        }
    if isinstance(value, list | tuple | set):
        return [_request_contract_payload(item, key=normalized_key) for item in value]
    return value


def _max_capability_level(plan: PowerMissionPlan) -> PowerActuatorCapabilityLevel:
    ranks = {
        PowerActuatorCapabilityLevel.L2: 2,
        PowerActuatorCapabilityLevel.L3: 3,
        PowerActuatorCapabilityLevel.L4: 4,
        PowerActuatorCapabilityLevel.L5: 5,
        PowerActuatorCapabilityLevel.L6: 6,
        PowerActuatorCapabilityLevel.L7: 7,
    }
    if not plan.graph.steps:
        return PowerActuatorCapabilityLevel.L2
    return max((step.capability_level for step in plan.graph.steps), key=ranks.__getitem__)
