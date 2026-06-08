from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    scan_forbidden_payload_categorized,
)


class WorkerRole(StrEnum):
    ANALYST = "analysis_worker"
    RESEARCHER = "research_worker"
    PLANNER = "planning_worker"
    VERIFIER = "verification_worker"
    MEMORY_CURATOR = "memory_curator_worker"
    WORKFLOW_SUBTASK = "workflow_subtask_worker"
    POWER_OPERATOR = "power_runtime_worker"
    AGENT_OPERATOR = "agentruntime_worker"


class WorkerExecutionMode(StrEnum):
    ANALYSIS = "analysis_worker"
    RESEARCH = "research_worker"
    PLANNING = "planning_worker"
    VERIFICATION = "verification_worker"
    MEMORY_CURATION = "memory_curator_worker"
    WORKFLOW_SUBTASK = "workflow_subtask_worker"
    POWER_RUNTIME = "power_runtime_worker"
    AGENT_RUNTIME = "agentruntime_worker"


class WorkerTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    KILLED = "killed"
    TIMEOUT = "timeout"
    BUDGET_EXHAUSTED = "budget_exhausted"


class WorkerFleetRunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    KILLED = "killed"


class WorkerMergeOutcome(StrEnum):
    MERGED = "merged"
    REJECTED = "rejected"
    NEEDS_RETRY = "needs_retry"
    NEEDS_REPLAN = "needs_replan"
    NEEDS_OPERATOR_CHECKPOINT = "needs_operator_checkpoint"
    CONFLICT = "conflict"


class WorkerFleetConfig(SentinelModel):
    max_workers: int = Field(default=8, ge=1, le=64)
    require_certified_telemetry: bool = True
    allow_worker_spawn_from_worker: bool = False
    allow_agentruntime_workers: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _config_is_not_authority(self) -> WorkerFleetConfig:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker fleet config cannot grant authority")
        return self


class WorkerBudget(SentinelModel):
    max_actions: int = Field(default=1, ge=0)
    max_cost_usd: float = Field(default=0.0, ge=0.0)
    max_retries: int = Field(default=0, ge=0)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _budget_is_data(self) -> WorkerBudget:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker budget cannot grant authority")
        return self


class WorkerDeadline(SentinelModel):
    timeout_seconds: int = Field(default=60, ge=1)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _deadline_is_data(self) -> WorkerDeadline:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker deadline cannot grant authority")
        return self


class WorkerScope(SentinelModel):
    allowed_actions: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_systems: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_data_types: list[str] = Field(default_factory=list)
    credential_scope_hashes: list[str] = Field(default_factory=list)
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    allow_power_runtime: bool = False
    allow_agentruntime: bool = False
    allow_worker_spawning: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _scope_is_data(self) -> WorkerScope:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker scope cannot grant authority")
        _reject_worker_control_payload(self.model_dump(mode="json"), context="worker_scope")
        return self


class WorkerResultContract(SentinelModel):
    contract_id: str = Field(default_factory=lambda: new_id("worker_contract"))
    required_evidence_refs: int = Field(default=1, ge=0)
    require_receipt_refs_for_execution: bool = True
    require_finalgate_refs_for_execution: bool = True
    conflict_key: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _contract_is_data(self) -> WorkerResultContract:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker result contract cannot grant authority")
        return self


class WorkerTask(SentinelModel):
    task_id: str
    role: WorkerRole
    execution_mode: WorkerExecutionMode
    objective: str
    scope: WorkerScope
    budget: WorkerBudget
    deadline: WorkerDeadline
    result_contract: WorkerResultContract
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _task_is_data(self) -> WorkerTask:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker task cannot grant authority")
        self.objective = redact_operator_text(self.objective)
        self.metadata = redact_operator_value(self.metadata)
        _reject_worker_control_payload(self.metadata, context="worker_task")
        return self


class WorkerTaskGraph(SentinelModel):
    tasks: list[WorkerTask] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _graph_is_acyclic_enough_for_v1(self) -> WorkerTaskGraph:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker task graph cannot grant authority")
        seen: set[str] = set()
        for task in self.tasks:
            if task.task_id in seen:
                raise ValueError(f"duplicate worker task id: {task.task_id}")
            seen.add(task.task_id)
        for task in self.tasks:
            if any(dep not in seen for dep in task.depends_on):
                raise ValueError(f"worker task {task.task_id} has unknown dependency")
            if task.task_id in task.depends_on:
                raise ValueError("worker task cannot depend on itself")
        return self


class WorkerSpawnRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("worker_spawn"))
    mission_id: str
    requested_by: str
    tasks: list[WorkerTask]
    safe_reason: str
    config: WorkerFleetConfig = Field(default_factory=WorkerFleetConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _request_is_data(self) -> WorkerSpawnRequest:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker spawn request cannot grant authority")
        self.safe_reason = redact_operator_text(self.safe_reason)
        self.metadata = redact_operator_value(self.metadata)
        _reject_worker_control_payload(self.metadata, context="worker_spawn_request")
        WorkerTaskGraph(tasks=self.tasks)
        if len(self.tasks) > self.config.max_workers:
            raise ValueError("worker spawn request exceeds max_workers")
        return self


class ChildAuthorityEnvelope(SentinelModel):
    child_authority_id: str = Field(default_factory=lambda: new_id("child_authority"))
    parent_envelope_id: str
    mission_id: str
    worker_id: str
    task_id: str
    allowed_actions: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_systems: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_data_types: list[str] = Field(default_factory=list)
    credential_scope_hashes: list[str] = Field(default_factory=list)
    max_actions: int = Field(ge=0)
    max_cost_usd: float = Field(ge=0.0)
    timeout_seconds: int = Field(ge=1)
    risk_appetite_score: float = Field(ge=0.0, le=100.0)
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    allow_power_runtime: bool = False
    allow_agentruntime: bool = False
    allow_worker_spawning: bool = False
    strict_subset: bool = True
    authority_hash: str = ""
    authority_effect: str = "derived_child_authority_subset"
    can_grant_authority: bool = False

    @model_validator(mode="after")
    def _child_authority_is_derived_only(self) -> ChildAuthorityEnvelope:
        if self.can_grant_authority:
            raise ValueError("child authority cannot grant further authority")
        if self.allow_worker_spawning:
            raise ValueError("child worker spawning is not enabled in V1")
        if self.strict_subset is not True:
            raise ValueError("child authority must be a strict subset")
        return self

    def with_hash(self) -> ChildAuthorityEnvelope:
        payload = self.safe_model_dump()
        payload["authority_hash"] = ""
        return self.model_copy(update={"authority_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["authority_hash"]
        payload["authority_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "child_authority_id": self.child_authority_id,
            "parent_envelope_id": self.parent_envelope_id,
            "mission_id": self.mission_id,
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "allowed_actions": self.allowed_actions,
            "allowed_tools": self.allowed_tools,
            "allowed_systems": self.allowed_systems,
            "allowed_paths": self.allowed_paths,
            "allowed_domains": self.allowed_domains,
            "allowed_data_types": self.allowed_data_types,
            "credential_scope_hashes": self.credential_scope_hashes,
            "max_actions": self.max_actions,
            "max_cost_usd": self.max_cost_usd,
            "timeout_seconds": self.timeout_seconds,
            "risk_appetite_score": self.risk_appetite_score,
            "provider_id": self.provider_id,
            "backend_id": self.backend_id,
            "model_id": self.model_id,
            "allow_power_runtime": self.allow_power_runtime,
            "allow_agentruntime": self.allow_agentruntime,
            "allow_worker_spawning": self.allow_worker_spawning,
            "strict_subset": self.strict_subset,
            "authority_hash": self.authority_hash,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
        }


class WorkerExecutionContext(SentinelModel):
    worker_id: str
    task_id: str
    mission_id: str
    parent_envelope_id: str
    role: WorkerRole
    execution_mode: WorkerExecutionMode
    child_authority: ChildAuthorityEnvelope
    scope: WorkerScope
    budget: WorkerBudget
    deadline: WorkerDeadline
    result_contract: WorkerResultContract
    memory_context_refs: list[str] = Field(default_factory=list)
    telemetry_snapshot_hash: str
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _context_is_data(self) -> WorkerExecutionContext:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker execution context cannot grant authority")
        return self


class WorkerEvidencePacket(SentinelModel):
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _evidence_is_data(self) -> WorkerEvidencePacket:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker evidence packet cannot grant authority")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self


class WorkerResult(SentinelModel):
    worker_result_id: str = Field(default_factory=lambda: new_id("worker_result"))
    worker_id: str
    task_id: str
    status: WorkerTaskStatus
    result_contract_id: str
    safe_summary: str
    output: dict[str, Any] = Field(default_factory=dict)
    evidence_packet: WorkerEvidencePacket
    actions_used: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    result_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute_more: bool = False

    @model_validator(mode="after")
    def _result_is_data(self) -> WorkerResult:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker result cannot grant authority")
        if self.can_grant_authority or self.can_execute_more:
            raise ValueError("worker result cannot request authority")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.output = redact_operator_value(self.output)
        if _contains_authority_request(self.output):
            raise ValueError("worker result cannot request authority")
        _reject_worker_control_payload(self.output, context="worker_result")
        return self

    def with_hash(self) -> WorkerResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "worker_result_id": self.worker_result_id,
            "worker_id": self.worker_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "result_contract_id": self.result_contract_id,
            "safe_summary": redact_operator_text(self.safe_summary),
            "output": redact_operator_value(self.output),
            "evidence_packet": self.evidence_packet.model_dump(mode="json"),
            "actions_used": self.actions_used,
            "cost_usd": self.cost_usd,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "result_hash": self.result_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute_more": self.can_execute_more,
        }


class WorkerMergeDecision(SentinelModel):
    decision_id: str = Field(default_factory=lambda: new_id("worker_merge"))
    worker_id: str
    task_id: str
    outcome: WorkerMergeOutcome
    reasons: list[str] = Field(default_factory=list)
    result_hash: str | None = None
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _decision_is_data(self) -> WorkerMergeDecision:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker merge decision cannot grant authority")
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self


class WorkerConflictRecord(SentinelModel):
    conflict_id: str = Field(default_factory=lambda: new_id("worker_conflict"))
    conflict_key: str
    worker_ids: list[str]
    result_hashes: list[str]
    safe_summary: str
    authority_effect: str = "none"
    data_not_authority: bool = True


class WorkerFleetRun(SentinelModel):
    worker_fleet_run_id: str = Field(default_factory=lambda: new_id("worker_fleet_run"))
    mission_id: str
    spawn_request_id: str
    status: WorkerFleetRunStatus = WorkerFleetRunStatus.CREATED
    blocked_reason: str | None = None
    workers: list[WorkerExecutionContext] = Field(default_factory=list)
    child_authority_envelopes: list[ChildAuthorityEnvelope] = Field(default_factory=list)
    worker_results: list[WorkerResult] = Field(default_factory=list)
    merge_decisions: list[WorkerMergeDecision] = Field(default_factory=list)
    conflict_records: list[WorkerConflictRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    run_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _run_is_data(self) -> WorkerFleetRun:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker fleet run cannot grant authority")
        return self

    def with_hash(self) -> WorkerFleetRun:
        payload = self.safe_model_dump()
        payload["run_hash"] = ""
        return self.model_copy(update={"run_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["run_hash"]
        payload["run_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "worker_fleet_run_id": self.worker_fleet_run_id,
            "mission_id": self.mission_id,
            "spawn_request_id": self.spawn_request_id,
            "status": self.status.value,
            "blocked_reason": self.blocked_reason,
            "workers": [worker.model_dump(mode="json") for worker in self.workers],
            "child_authority_envelopes": [child.safe_model_dump() for child in self.child_authority_envelopes],
            "worker_results": [result.safe_model_dump() for result in self.worker_results],
            "merge_decisions": [decision.model_dump(mode="json") for decision in self.merge_decisions],
            "conflict_records": [conflict.model_dump(mode="json") for conflict in self.conflict_records],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "run_hash": self.run_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
        }


class WorkerFleetReplayView(SentinelModel):
    mission_id: str
    worker_fleet_run_id: str
    run: WorkerFleetRun
    child_authority_envelopes: list[ChildAuthorityEnvelope] = Field(default_factory=list)
    worker_results: list[WorkerResult] = Field(default_factory=list)
    merge_decisions: list[WorkerMergeDecision] = Field(default_factory=list)
    conflict_records: list[WorkerConflictRecord] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    reexecuted_actions: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _replay_is_data(self) -> WorkerFleetReplayView:
        if self.authority_effect != "none" or self.data_not_authority is not True:
            raise ValueError("worker replay cannot grant authority")
        return self


def _contains_authority_request(value: Any) -> bool:
    scan = scan_forbidden_payload_categorized(value, path="$.worker_result")
    return bool(
        scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value]
        or scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]
        or scan[OrganSafetyScanCategory.CREDENTIAL_DANGEROUS.value]
        or _contains_worker_control_key(value)
    )


def _reject_worker_control_payload(value: Any, *, context: str) -> None:
    try:
        reject_operator_control_payload(value, context=context)
    except ValueError as exc:
        raise ValueError(f"{context}: worker payload cannot contain control-plane execution fields") from exc


def _contains_worker_control_key(value: Any) -> bool:
    dangerous_tokens = {
        "authority",
        "authority_grant",
        "grant_authority",
        "permission",
        "credential",
        "credential_unlock",
        "provider_override",
        "backend_override",
        "model_override",
        "model_contract_override",
        "direct_organ",
        "organ_call",
        "dispatch",
        "dispatcher",
        "executor",
        "execute_more",
        "finalgate_as_permission",
        "receipt_as_permission",
        "memory_as_authority",
    }
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).lower()
            if any(token in key_text for token in dangerous_tokens):
                return True
            if _contains_worker_control_key(nested):
                return True
    if isinstance(value, list):
        return any(_contains_worker_control_key(item) for item in value)
    return False
