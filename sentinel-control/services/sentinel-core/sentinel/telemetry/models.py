from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id
from sentinel.telemetry.redaction import sanitize_telemetry_text, sanitize_telemetry_value


class TelemetryDomain(StrEnum):
    OPERATIONAL = "operational"
    AUTHORITY = "authority"
    LLM = "llm"
    ORGAN = "organ"
    MEMORY = "memory"
    WORKFLOW = "workflow"
    REPLAN = "replan"
    WORKER = "worker"
    COST = "cost"
    SAFETY = "safety"
    PRODUCT_POWER = "product_power"


class TelemetrySourceSurface(StrEnum):
    MISSION_KERNEL = "mission_kernel"
    MISSION_STORE = "mission_store"
    WORKFLOW_STORE = "workflow_store"
    POWER_RUNTIME = "power_runtime"
    AGENT_RUNTIME = "agentruntime"
    LLM_OPERATOR = "llm_operator"
    COCKPIT = "cockpit"
    REPLAY = "replay"
    BROWSER_LEDGER = "browser_neural_ledger"
    MANUAL = "manual"


class TelemetryEventKind(StrEnum):
    MISSION_CREATED = "mission_created"
    MISSION_STARTED = "mission_started"
    MISSION_QUEUED = "mission_queued"
    MISSION_RUNNING = "mission_running"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_KILLED = "mission_killed"
    MISSION_PAUSED = "mission_paused"
    MISSION_RESUMED = "mission_resumed"
    MISSION_BLOCKED = "mission_blocked"
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_CHECKPOINT_CREATED = "workflow_checkpoint_created"
    WORKFLOW_CHECKPOINT_FAILED = "workflow_checkpoint_failed"
    WORKFLOW_RESUMED = "workflow_resumed"
    REPLAN_CANDIDATE_CREATED = "replan_candidate_created"
    REPLAN_EXECUTED = "replan_executed"
    REPLAN_ESCALATED = "replan_escalated"
    REPLAN_REJECTED = "replan_rejected"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    GATE_ALLOWED = "gate_allowed"
    GATE_BLOCKED = "gate_blocked"
    FINALGATE_PASSED = "finalgate_passed"
    FINALGATE_FAILED = "finalgate_failed"
    ORGAN_CALLED = "organ_called"
    ORGAN_FAILED = "organ_failed"
    MODEL_CALL_STARTED = "model_call_started"
    MODEL_CALL_COMPLETED = "model_call_completed"
    MODEL_SCHEMA_INVALID = "model_schema_invalid"
    MEMORY_RECALL_USED = "memory_recall_used"
    MEMORY_RECALL_REJECTED = "memory_recall_rejected"
    SECRET_REDACTION_HIT = "secret_redaction_hit"
    CREDENTIAL_ACCESS_DENIED = "credential_access_denied"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    REVOCATION_DETECTED = "revocation_detected"


class TelemetryMetricKind(StrEnum):
    MISSION_COMPLETION_RATE = "mission_completion_rate"
    AUTONOMOUS_USEFUL_MINUTES = "autonomous_useful_minutes"
    TIME_TO_USEFUL_RESULT = "time_to_useful_result"
    OPERATOR_INTERRUPTION_COUNT = "operator_interruption_count"
    ORGAN_LATENCY = "organ_latency"
    STEP_LATENCY = "step_latency"
    WORKFLOW_CHECKPOINT_LATENCY = "workflow_checkpoint_latency"
    REPLAN_SUCCESS_RATE = "replan_success_rate"
    RECOVERY_SUCCESS_RATE = "recovery_success_rate"
    GATE_REJECT_COUNT = "gate_reject_count"
    FINALGATE_REJECT_COUNT = "finalgate_reject_count"
    KILL_SWITCH_LATENCY = "kill_switch_latency"
    REVOCATION_LATENCY = "revocation_latency"
    MEMORY_RECALL_COUNT = "memory_recall_count"
    MEMORY_RECALL_UTILITY = "memory_recall_utility"
    LLM_SCHEMA_FAILURE_RATE = "llm_schema_failure_rate"
    PROVIDER_BACKEND_MODEL_SELECTED = "provider_backend_model_selected"
    TOKEN_USAGE = "token_usage"
    COST_PER_COMPLETED_MISSION = "cost_per_completed_mission"
    RECEIPT_COMPLETENESS = "receipt_completeness"
    TIMELINE_REPLAY_COMPLETENESS = "timeline_replay_completeness"
    FUTURE_WORKER_PARALLEL_EFFICIENCY = "future_worker_parallel_efficiency"
    FUTURE_WORKER_CONFLICT_RATE = "future_worker_conflict_rate"


class TelemetryEventRecord(SentinelModel):
    telemetry_event_id: str = Field(default_factory=lambda: new_id("telemetry_event"))
    mission_id: str | None = None
    workflow_id: str | None = None
    session_id: str | None = None
    source_surface: TelemetrySourceSurface = TelemetrySourceSurface.MANUAL
    domain: TelemetryDomain = TelemetryDomain.OPERATIONAL
    event_kind: TelemetryEventKind
    safe_summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    redaction_hit: bool = False
    redaction_paths: list[str] = Field(default_factory=list)
    previous_hash: str | None = None
    event_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _event_is_data_only(self) -> TelemetryEventRecord:
        assert_data_not_authority(
            context="telemetry_event_record",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary, summary_hit = sanitize_telemetry_text(self.safe_summary)
        self.metadata, metadata_hit, metadata_paths = sanitize_telemetry_value(self.metadata, path="$.metadata")
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        self.redaction_hit = self.redaction_hit or summary_hit or metadata_hit
        self.redaction_paths = list(dict.fromkeys([*self.redaction_paths, *metadata_paths]))
        reject_operator_control_payload(self.metadata, context="telemetry_event_record")
        return self

    def with_hash(self) -> TelemetryEventRecord:
        payload = self.safe_model_dump()
        payload["event_hash"] = ""
        return self.model_copy(update={"event_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["event_hash"]
        payload["event_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "telemetry_event_id": self.telemetry_event_id,
            "mission_id": self.mission_id,
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "source_surface": self.source_surface.value,
            "domain": self.domain.value,
            "event_kind": self.event_kind.value,
            "safe_summary": self.safe_summary,
            "metadata": self.metadata,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "redaction_hit": self.redaction_hit,
            "redaction_paths": self.redaction_paths,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class TelemetryMetricSample(SentinelModel):
    telemetry_metric_id: str = Field(default_factory=lambda: new_id("telemetry_metric"))
    mission_id: str | None = None
    workflow_id: str | None = None
    session_id: str | None = None
    source_surface: TelemetrySourceSurface = TelemetrySourceSurface.MANUAL
    domain: TelemetryDomain = TelemetryDomain.OPERATIONAL
    metric_kind: TelemetryMetricKind
    value: Any
    unit: str | None = None
    safe_summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    redaction_hit: bool = False
    redaction_paths: list[str] = Field(default_factory=list)
    previous_hash: str | None = None
    metric_hash: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _metric_is_data_only(self) -> TelemetryMetricSample:
        assert_data_not_authority(
            context="telemetry_metric_sample",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary, summary_hit = sanitize_telemetry_text(self.safe_summary)
        self.value, value_hit, value_paths = sanitize_telemetry_value(self.value, path="$.value")
        self.metadata, metadata_hit, metadata_paths = sanitize_telemetry_value(self.metadata, path="$.metadata")
        self.redaction_hit = self.redaction_hit or summary_hit or value_hit or metadata_hit
        self.redaction_paths = list(dict.fromkeys([*self.redaction_paths, *value_paths, *metadata_paths]))
        reject_operator_control_payload(self.metadata, context="telemetry_metric_sample")
        return self

    def with_hash(self) -> TelemetryMetricSample:
        payload = self.safe_model_dump()
        payload["metric_hash"] = ""
        return self.model_copy(update={"metric_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["metric_hash"]
        payload["metric_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "telemetry_metric_id": self.telemetry_metric_id,
            "mission_id": self.mission_id,
            "workflow_id": self.workflow_id,
            "session_id": self.session_id,
            "source_surface": self.source_surface.value,
            "domain": self.domain.value,
            "metric_kind": self.metric_kind.value,
            "value": self.value,
            "unit": self.unit,
            "safe_summary": self.safe_summary,
            "metadata": self.metadata,
            "redaction_hit": self.redaction_hit,
            "redaction_paths": self.redaction_paths,
            "previous_hash": self.previous_hash,
            "metric_hash": self.metric_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class TelemetrySnapshot(SentinelModel):
    root_path: str
    telemetry_available: bool = True
    event_chain_ok: bool = True
    metric_chain_ok: bool = True
    tampered: bool = False
    certified_mode: bool = True
    reasons: list[str] = Field(default_factory=list)
    event_count: int = 0
    metric_count: int = 0
    event_counts_by_kind: dict[str, int] = Field(default_factory=dict)
    metric_counts_by_kind: dict[str, int] = Field(default_factory=dict)
    domain_counts: dict[str, int] = Field(default_factory=dict)
    latest_event_hash: str | None = None
    latest_metric_hash: str | None = None
    latest_provider_backend_model: dict[str, str] | None = None
    product_power_score: float = 0.0
    operator_visible: bool = True
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _snapshot_is_data_only(self) -> TelemetrySnapshot:
        assert_data_not_authority(
            context="telemetry_snapshot",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.reasons, context="telemetry_snapshot")
        reject_operator_control_payload(self.event_counts_by_kind, context="telemetry_snapshot_events")
        reject_operator_control_payload(self.metric_counts_by_kind, context="telemetry_snapshot_metrics")
        reject_operator_control_payload(self.domain_counts, context="telemetry_snapshot_domains")
        return self
