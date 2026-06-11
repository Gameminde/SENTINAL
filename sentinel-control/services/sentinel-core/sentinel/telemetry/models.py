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
    MISSION_DAEMON = "mission_daemon"
    PROACTIVE_SCHEDULER = "proactive_scheduler"
    MODEL_AMPLIFICATION_HARNESS = "model_amplification_harness"
    SKILL_FABRIC = "skill_fabric"
    WORKFLOW_STORE = "workflow_store"
    POWER_RUNTIME = "power_runtime"
    AGENT_RUNTIME = "agentruntime"
    LLM_OPERATOR = "llm_operator"
    MODEL_ROUTER = "model_router"
    CHANNEL_ADAPTER = "channel_adapter"
    DESKTOP_SIDECAR = "desktop_sidecar"
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
    WORKER_SPAWN_REQUESTED = "worker_spawn_requested"
    WORKER_SPAWN_BLOCKED = "worker_spawn_blocked"
    WORKER_STARTED = "worker_started"
    WORKER_COMPLETED = "worker_completed"
    WORKER_FAILED = "worker_failed"
    WORKER_KILLED = "worker_killed"
    WORKER_TIMEOUT = "worker_timeout"
    WORKER_BUDGET_EXHAUSTED = "worker_budget_exhausted"
    WORKER_AUTHORITY_DERIVED = "worker_authority_derived"
    WORKER_AUTHORITY_REJECTED = "worker_authority_rejected"
    WORKER_RESULT_SUBMITTED = "worker_result_submitted"
    WORKER_RESULT_MERGED = "worker_result_merged"
    WORKER_RESULT_REJECTED = "worker_result_rejected"
    WORKER_CONFLICT_DETECTED = "worker_conflict_detected"
    DAEMON_STARTED = "daemon_started"
    DAEMON_STOPPED = "daemon_stopped"
    DAEMON_TICK_STARTED = "daemon_tick_started"
    DAEMON_TICK_COMPLETED = "daemon_tick_completed"
    DAEMON_TICK_FAILED = "daemon_tick_failed"
    DAEMON_LEASE_CLAIMED = "daemon_lease_claimed"
    DAEMON_LEASE_REJECTED = "daemon_lease_rejected"
    DAEMON_LEASE_RENEWED = "daemon_lease_renewed"
    DAEMON_LEASE_EXPIRED = "daemon_lease_expired"
    DAEMON_LEASE_RELEASED = "daemon_lease_released"
    DAEMON_HEARTBEAT_EMITTED = "daemon_heartbeat_emitted"
    DAEMON_HEARTBEAT_MISSED = "daemon_heartbeat_missed"
    DAEMON_RECOVERY_STARTED = "daemon_recovery_started"
    DAEMON_RECOVERY_COMPLETED = "daemon_recovery_completed"
    DAEMON_RECOVERY_FAILED = "daemon_recovery_failed"
    DAEMON_DEAD_LETTER_CREATED = "daemon_dead_letter_created"
    SCHEDULER_TRIGGER_EVALUATED = "scheduler_trigger_evaluated"
    SCHEDULER_PROPOSAL_CREATED = "scheduler_proposal_created"
    SCHEDULER_PROPOSAL_REJECTED = "scheduler_proposal_rejected"
    OPERATOR_HANDOFF_CREATED = "operator_handoff_created"
    OPERATOR_NOTIFICATION_CREATED = "operator_notification_created"
    HARNESS_SESSION_STARTED = "harness_session_started"
    HARNESS_SESSION_COMPLETED = "harness_session_completed"
    HARNESS_SESSION_FAILED = "harness_session_failed"
    HARNESS_CONTEXT_PACK_CREATED = "harness_context_pack_created"
    HARNESS_CONTEXT_PACK_REJECTED = "harness_context_pack_rejected"
    HARNESS_ARTIFACT_READ = "harness_artifact_read"
    HARNESS_EDIT_PROPOSED = "harness_edit_proposed"
    HARNESS_EDIT_VERIFIED = "harness_edit_verified"
    HARNESS_EDIT_REJECTED = "harness_edit_rejected"
    HARNESS_KERNEL_STARTED = "harness_kernel_started"
    HARNESS_KERNEL_COMPLETED = "harness_kernel_completed"
    HARNESS_KERNEL_FAILED = "harness_kernel_failed"
    HARNESS_TOOL_OUTPUT_MINIMIZED = "harness_tool_output_minimized"
    HARNESS_WORKER_REQUESTED = "harness_worker_requested"
    HARNESS_WORKER_COMPLETED = "harness_worker_completed"
    HARNESS_WORKER_REJECTED = "harness_worker_rejected"
    HARNESS_CONFLICT_DETECTED = "harness_conflict_detected"
    HARNESS_MERGE_COMPLETED = "harness_merge_completed"
    HARNESS_MERGE_REJECTED = "harness_merge_rejected"
    SKILL_MANIFEST_REGISTERED = "skill_manifest_registered"
    SKILL_MANIFEST_REJECTED = "skill_manifest_rejected"
    SKILL_SCAN_STARTED = "skill_scan_started"
    SKILL_SCAN_COMPLETED = "skill_scan_completed"
    SKILL_QUARANTINED = "skill_quarantined"
    SKILL_EVALUATION_STARTED = "skill_evaluation_started"
    SKILL_EVALUATION_COMPLETED = "skill_evaluation_completed"
    SKILL_APPROVED = "skill_approved"
    SKILL_PROMOTED = "skill_promoted"
    SKILL_REVOKED = "skill_revoked"
    SKILL_EXECUTION_REQUESTED = "skill_execution_requested"
    SKILL_EXECUTION_BLOCKED = "skill_execution_blocked"
    SKILL_EXECUTION_STARTED = "skill_execution_started"
    SKILL_EXECUTION_COMPLETED = "skill_execution_completed"
    SKILL_EXECUTION_FAILED = "skill_execution_failed"
    PROCEDURE_STEP_STARTED = "procedure_step_started"
    PROCEDURE_STEP_COMPLETED = "procedure_step_completed"
    PROCEDURE_STEP_FAILED = "procedure_step_failed"
    PROCEDURE_ROLLBACK_REQUIRED = "procedure_rollback_required"
    PROCEDURE_REPLAY_BUILT = "procedure_replay_built"
    MODEL_ROUTER_CANDIDATE_REGISTERED = "model_router_candidate_registered"
    MODEL_ROUTER_CANDIDATE_REJECTED = "model_router_candidate_rejected"
    MODEL_ROUTER_HARDWARE_SNAPSHOT_CREATED = "model_router_hardware_snapshot_created"
    MODEL_ROUTER_RUNTIME_PROBE_STARTED = "model_router_runtime_probe_started"
    MODEL_ROUTER_RUNTIME_PROBE_COMPLETED = "model_router_runtime_probe_completed"
    MODEL_ROUTER_SIMULATION_STARTED = "model_router_simulation_started"
    MODEL_ROUTER_SIMULATION_COMPLETED = "model_router_simulation_completed"
    MODEL_ROUTER_DECISION_CREATED = "model_router_decision_created"
    MODEL_ROUTER_DECISION_REJECTED = "model_router_decision_rejected"
    MODEL_ROUTER_APPROVAL_RECORDED = "model_router_approval_recorded"
    MODEL_ROUTER_BINDING_CREATED = "model_router_binding_created"
    MODEL_ROUTER_BINDING_REJECTED = "model_router_binding_rejected"
    MODEL_ROUTER_FALLBACK_BLOCKED = "model_router_fallback_blocked"
    MODEL_ROUTER_POLICY_REJECTED = "model_router_policy_rejected"
    CHANNEL_ADAPTER_REGISTERED = "channel_adapter_registered"
    CHANNEL_ADAPTER_REJECTED = "channel_adapter_rejected"
    CHANNEL_INBOUND_RECEIVED = "channel_inbound_received"
    CHANNEL_INBOUND_QUARANTINED = "channel_inbound_quarantined"
    CHANNEL_IDENTITY_BOUND = "channel_identity_bound"
    CHANNEL_OUTBOUND_DRAFT_CREATED = "channel_outbound_draft_created"
    CHANNEL_OUTBOUND_APPROVAL_RECORDED = "channel_outbound_approval_recorded"
    CHANNEL_OUTBOUND_SEND_REQUESTED = "channel_outbound_send_requested"
    CHANNEL_OUTBOUND_SEND_BLOCKED = "channel_outbound_send_blocked"
    CHANNEL_OUTBOUND_SENT = "channel_outbound_sent"
    CHANNEL_OUTBOUND_FAILED = "channel_outbound_failed"
    CHANNEL_DUPLICATE_SEND_BLOCKED = "channel_duplicate_send_blocked"
    CHANNEL_REVOCATION_DETECTED = "channel_revocation_detected"
    CHANNEL_KILL_SWITCH_TRIGGERED = "channel_kill_switch_triggered"
    CHANNEL_REPLAY_BUILT = "channel_replay_built"
    DESKTOP_SIDECAR_REGISTERED = "desktop_sidecar_registered"
    DESKTOP_SIDECAR_REJECTED = "desktop_sidecar_rejected"
    DESKTOP_OBSERVATION_REQUESTED = "desktop_observation_requested"
    DESKTOP_OBSERVATION_BLOCKED = "desktop_observation_blocked"
    DESKTOP_OBSERVATION_COMPLETED = "desktop_observation_completed"
    DESKTOP_SCREENSHOT_CAPTURED = "desktop_screenshot_captured"
    DESKTOP_SCREENSHOT_REDACTED = "desktop_screenshot_redacted"
    DESKTOP_SENSITIVE_REGION_DETECTED = "desktop_sensitive_region_detected"
    DESKTOP_GROUNDING_REQUESTED = "desktop_grounding_requested"
    DESKTOP_GROUNDING_COMPLETED = "desktop_grounding_completed"
    DESKTOP_GROUNDING_FAILED = "desktop_grounding_failed"
    DESKTOP_ACTION_PROPOSED = "desktop_action_proposed"
    DESKTOP_ACTION_PREVIEW_CREATED = "desktop_action_preview_created"
    DESKTOP_ACTION_APPROVAL_REQUIRED = "desktop_action_approval_required"
    DESKTOP_ACTION_APPROVED = "desktop_action_approved"
    DESKTOP_ACTION_BLOCKED = "desktop_action_blocked"
    DESKTOP_ACTION_STARTED = "desktop_action_started"
    DESKTOP_ACTION_COMPLETED = "desktop_action_completed"
    DESKTOP_ACTION_FAILED = "desktop_action_failed"
    DESKTOP_KILL_SWITCH_TRIGGERED = "desktop_kill_switch_triggered"
    DESKTOP_REVOCATION_DETECTED = "desktop_revocation_detected"
    DESKTOP_REPLAY_BUILT = "desktop_replay_built"


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
    WORKER_PARALLEL_EFFICIENCY = "worker_parallel_efficiency"
    WORKER_CONFLICT_RATE = "worker_conflict_rate"
    WORKER_COMPLETION_RATE = "worker_completion_rate"
    WORKER_USEFUL_MINUTES = "worker_useful_minutes"
    WORKER_COST = "worker_cost"
    WORKER_RETRY_RATE = "worker_retry_rate"
    WORKER_MERGE_SUCCESS_RATE = "worker_merge_success_rate"
    FUTURE_WORKER_PARALLEL_EFFICIENCY = "future_worker_parallel_efficiency"
    FUTURE_WORKER_CONFLICT_RATE = "future_worker_conflict_rate"
    DAEMON_UPTIME = "daemon_uptime"
    DAEMON_TICK_LATENCY = "daemon_tick_latency"
    LEASE_CLAIM_LATENCY = "lease_claim_latency"
    HEARTBEAT_INTERVAL = "heartbeat_interval"
    STALE_LEASE_COUNT = "stale_lease_count"
    CRASH_RECOVERY_SUCCESS_RATE = "crash_recovery_success_rate"
    DEAD_LETTER_RATE = "dead_letter_rate"
    SCHEDULER_PROPOSAL_COUNT = "scheduler_proposal_count"
    SCHEDULER_PROPOSAL_ACCEPTANCE_RATE = "scheduler_proposal_acceptance_rate"
    OPERATOR_HANDOFF_COUNT = "operator_handoff_count"
    MISSION_BACKGROUND_USEFUL_MINUTES = "mission_background_useful_minutes"
    HARNESS_CONTEXT_TOKENS_SAVED = "harness_context_tokens_saved"
    HARNESS_TOOL_OUTPUT_BYTES_INPUT = "harness_tool_output_bytes_input"
    HARNESS_TOOL_OUTPUT_BYTES_PERSISTED = "harness_tool_output_bytes_persisted"
    HARNESS_SCHEMA_VALID_RATE = "harness_schema_valid_rate"
    HARNESS_CONFLICT_COUNT = "harness_conflict_count"
    HARNESS_MERGE_SUCCESS_RATE = "harness_merge_success_rate"
    HARNESS_RETRY_REDUCTION_ESTIMATE = "harness_retry_reduction_estimate"
    HARNESS_COMPLETION_DELTA_SAMPLE = "harness_completion_delta_sample"
    HARNESS_COST_DELTA_SAMPLE = "harness_cost_delta_sample"
    SKILL_SCAN_PASS_RATE = "skill_scan_pass_rate"
    SKILL_QUARANTINE_RATE = "skill_quarantine_rate"
    SKILL_EVAL_SUCCESS_RATE = "skill_eval_success_rate"
    SKILL_EXECUTION_SUCCESS_RATE = "skill_execution_success_rate"
    PROCEDURE_REUSE_COUNT = "procedure_reuse_count"
    PROCEDURE_COMPLETION_DELTA_SAMPLE = "procedure_completion_delta_sample"
    PROCEDURE_COST_DELTA_SAMPLE = "procedure_cost_delta_sample"
    PROCEDURE_ROLLBACK_COUNT = "procedure_rollback_count"
    SKILL_REVOCATION_COUNT = "skill_revocation_count"
    SKILL_AUTHORITY_REJECT_COUNT = "skill_authority_reject_count"
    MODEL_ROUTER_CANDIDATE_COUNT = "model_router_candidate_count"
    MODEL_ROUTER_CANDIDATE_REJECTION_COUNT = "model_router_candidate_rejection_count"
    MODEL_ROUTER_ESTIMATED_COST_DELTA = "model_router_estimated_cost_delta"
    MODEL_ROUTER_ESTIMATED_LATENCY_DELTA = "model_router_estimated_latency_delta"
    MODEL_ROUTER_CONTEXT_FIT_SCORE = "model_router_context_fit_score"
    MODEL_ROUTER_HARDWARE_FIT_SCORE = "model_router_hardware_fit_score"
    MODEL_ROUTER_PRIVACY_SCORE = "model_router_privacy_score"
    MODEL_ROUTER_QUALITY_SCORE = "model_router_quality_score"
    MODEL_ROUTER_ROUTE_APPROVAL_RATE = "model_router_route_approval_rate"
    MODEL_ROUTER_FALLBACK_BLOCK_COUNT = "model_router_fallback_block_count"
    MODEL_ROUTER_POLICY_REJECT_COUNT = "model_router_policy_reject_count"
    CHANNEL_INBOUND_MESSAGE_COUNT = "channel_inbound_message_count"
    CHANNEL_OUTBOUND_DRAFT_COUNT = "channel_outbound_draft_count"
    CHANNEL_OUTBOUND_SEND_COUNT = "channel_outbound_send_count"
    CHANNEL_OUTBOUND_BLOCK_COUNT = "channel_outbound_block_count"
    CHANNEL_APPROVAL_REQUIRED_COUNT = "channel_approval_required_count"
    CHANNEL_RATE_LIMIT_BLOCK_COUNT = "channel_rate_limit_block_count"
    CHANNEL_DUPLICATE_SEND_BLOCK_COUNT = "channel_duplicate_send_block_count"
    CHANNEL_RECEIPT_COMPLETENESS = "channel_receipt_completeness"
    CHANNEL_DELIVERY_SUCCESS_RATE = "channel_delivery_success_rate"
    CHANNEL_REPLAY_COMPLETENESS = "channel_replay_completeness"
    DESKTOP_OBSERVATION_COUNT = "desktop_observation_count"
    DESKTOP_OBSERVATION_BLOCK_COUNT = "desktop_observation_block_count"
    DESKTOP_GROUNDING_SUCCESS_RATE = "desktop_grounding_success_rate"
    DESKTOP_GROUNDING_AMBIGUITY_RATE = "desktop_grounding_ambiguity_rate"
    DESKTOP_SENSITIVE_REGION_BLOCK_COUNT = "desktop_sensitive_region_block_count"
    DESKTOP_ACTION_PREVIEW_COUNT = "desktop_action_preview_count"
    DESKTOP_ACTION_BLOCK_COUNT = "desktop_action_block_count"
    DESKTOP_ACTION_SUCCESS_RATE = "desktop_action_success_rate"
    DESKTOP_RECEIPT_COMPLETENESS = "desktop_receipt_completeness"
    DESKTOP_REPLAY_COMPLETENESS = "desktop_replay_completeness"
    DESKTOP_KILL_LATENCY = "desktop_kill_latency"


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
