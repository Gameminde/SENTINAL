from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id
from sentinel.telemetry.models import TelemetrySnapshot


def daemon_utc_now() -> datetime:
    return datetime.now(UTC)


class DaemonQueueStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    KILLED = "killed"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    DEAD_LETTER = "dead_letter"


class DeadLetterReason(StrEnum):
    AUTHORITY_REVOKED = "authority_revoked"
    AUTHORITY_EXPIRED = "authority_expired"
    TELEMETRY_UNCERTIFIED = "telemetry_uncertified"
    STALE_OR_MISSING_LEASE = "stale_or_missing_lease"
    UNRECOVERABLE_WORKFLOW = "unrecoverable_workflow"
    WORKER_FLEET_UNRECOVERABLE = "worker_fleet_unrecoverable"
    RUNTIME_FAILURE = "runtime_failure"


class SchedulerDecisionKind(StrEnum):
    PROPOSED = "proposed"
    REJECTED = "rejected"
    HANDOFF_REQUIRED = "handoff_required"


class MissionDaemonConfig(SentinelModel):
    owner_id: str = Field(default_factory=lambda: new_id("daemon_owner"))
    lease_ttl_seconds: int = Field(default=60, ge=5)
    heartbeat_interval_seconds: int = Field(default=10, ge=1)
    require_certified_telemetry: bool = True
    max_tick_steps: int = Field(default=1, ge=1, le=50)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _config_is_data_only(self) -> MissionDaemonConfig:
        assert_data_not_authority(
            context="mission_daemon_config",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class DaemonLeaseOwner(SentinelModel):
    owner_id: str
    host_hash: str | None = None
    process_hash: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _owner_is_data_only(self) -> DaemonLeaseOwner:
        assert_data_not_authority(
            context="daemon_lease_owner",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class DaemonLease(SentinelModel):
    lease_id: str = Field(default_factory=lambda: new_id("daemon_lease"))
    mission_id: str
    owner: DaemonLeaseOwner
    claimed_at: datetime = Field(default_factory=daemon_utc_now)
    expires_at: datetime
    heartbeat_deadline_at: datetime
    released_at: datetime | None = None
    takeover_of_owner_id: str | None = None
    stale_takeover_proof_hash: str | None = None
    lease_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @classmethod
    def create(
        cls,
        *,
        mission_id: str,
        owner: DaemonLeaseOwner,
        now: datetime,
        ttl_seconds: int,
        takeover_of_owner_id: str | None = None,
        stale_takeover_proof_hash: str | None = None,
    ) -> DaemonLease:
        expires_at = now + timedelta(seconds=ttl_seconds)
        return cls(
            mission_id=mission_id,
            owner=owner,
            claimed_at=now,
            expires_at=expires_at,
            heartbeat_deadline_at=expires_at,
            takeover_of_owner_id=takeover_of_owner_id,
            stale_takeover_proof_hash=stale_takeover_proof_hash,
        ).with_hash()

    @model_validator(mode="after")
    def _lease_is_not_authority(self) -> DaemonLease:
        assert_data_not_authority(
            context="daemon_lease",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def is_stale(self, now: datetime) -> bool:
        return self.released_at is not None or now >= self.expires_at or now >= self.heartbeat_deadline_at

    def with_hash(self) -> DaemonLease:
        payload = self.safe_model_dump()
        payload["lease_hash"] = ""
        return self.model_copy(update={"lease_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["lease_hash"]
        payload["lease_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "mission_id": self.mission_id,
            "owner": self.owner.model_dump(mode="json"),
            "claimed_at": self.claimed_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "heartbeat_deadline_at": self.heartbeat_deadline_at.isoformat(),
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "takeover_of_owner_id": self.takeover_of_owner_id,
            "stale_takeover_proof_hash": self.stale_takeover_proof_hash,
            "lease_hash": self.lease_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class DaemonHeartbeatRecord(SentinelModel):
    heartbeat_id: str = Field(default_factory=lambda: new_id("daemon_heartbeat"))
    lease_id: str
    mission_id: str
    owner_id: str
    emitted_at: datetime = Field(default_factory=daemon_utc_now)
    safe_summary: str = "Daemon heartbeat emitted."
    heartbeat_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _heartbeat_is_data_only(self) -> DaemonHeartbeatRecord:
        assert_data_not_authority(
            context="daemon_heartbeat",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> DaemonHeartbeatRecord:
        payload = self.safe_model_dump()
        payload["heartbeat_hash"] = ""
        return self.model_copy(update={"heartbeat_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["heartbeat_hash"]
        payload["heartbeat_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "heartbeat_id": self.heartbeat_id,
            "lease_id": self.lease_id,
            "mission_id": self.mission_id,
            "owner_id": self.owner_id,
            "emitted_at": self.emitted_at.isoformat(),
            "safe_summary": self.safe_summary,
            "heartbeat_hash": self.heartbeat_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class DaemonQueueRecord(SentinelModel):
    queue_id: str = Field(default_factory=lambda: new_id("daemon_queue"))
    mission_id: str
    workflow_id: str | None = None
    worker_fleet_run_id: str | None = None
    status: DaemonQueueStatus = DaemonQueueStatus.QUEUED
    priority: int = Field(default=0, ge=0, le=100)
    safe_reason: str = "Mission queued for daemon supervision."
    metadata: dict[str, Any] = Field(default_factory=dict)
    queued_at: datetime = Field(default_factory=daemon_utc_now)
    updated_at: datetime = Field(default_factory=daemon_utc_now)
    queue_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _queue_is_data_only(self) -> DaemonQueueRecord:
        assert_data_not_authority(
            context="daemon_queue_record",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_reason = redact_operator_text(self.safe_reason)
        self.metadata = sanitize_daemon_metadata(self.metadata)
        return self

    def with_hash(self) -> DaemonQueueRecord:
        payload = self.safe_model_dump()
        payload["queue_hash"] = ""
        return self.model_copy(update={"queue_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["queue_hash"]
        payload["queue_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "mission_id": self.mission_id,
            "workflow_id": self.workflow_id,
            "worker_fleet_run_id": self.worker_fleet_run_id,
            "status": self.status.value,
            "priority": self.priority,
            "safe_reason": self.safe_reason,
            "metadata": self.metadata,
            "queued_at": self.queued_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "queue_hash": self.queue_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class DaemonQueueCursor(SentinelModel):
    mission_id: str
    queue_id: str | None = None
    updated_at: datetime = Field(default_factory=daemon_utc_now)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _cursor_is_data_only(self) -> DaemonQueueCursor:
        assert_data_not_authority(
            context="daemon_queue_cursor",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class DeadLetterRecord(SentinelModel):
    dead_letter_id: str = Field(default_factory=lambda: new_id("daemon_deadletter"))
    mission_id: str
    reason: DeadLetterReason
    safe_summary: str
    workflow_id: str | None = None
    worker_fleet_run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=daemon_utc_now)
    dead_letter_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _dead_letter_is_data_only(self) -> DeadLetterRecord:
        assert_data_not_authority(
            context="daemon_dead_letter",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.metadata = sanitize_daemon_metadata(self.metadata)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self

    def with_hash(self) -> DeadLetterRecord:
        payload = self.safe_model_dump()
        payload["dead_letter_hash"] = ""
        return self.model_copy(update={"dead_letter_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["dead_letter_hash"]
        payload["dead_letter_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "dead_letter_id": self.dead_letter_id,
            "mission_id": self.mission_id,
            "reason": self.reason.value,
            "safe_summary": self.safe_summary,
            "workflow_id": self.workflow_id,
            "worker_fleet_run_id": self.worker_fleet_run_id,
            "metadata": self.metadata,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "created_at": self.created_at.isoformat(),
            "dead_letter_hash": self.dead_letter_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class DaemonRecoveryPlan(SentinelModel):
    mission_id: str
    workflow_id: str | None = None
    recovery_reason: str
    safe_steps: list[str] = Field(default_factory=list)
    checkpoint_id: str | None = None
    lease_id: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _recovery_plan_is_data_only(self) -> DaemonRecoveryPlan:
        assert_data_not_authority(
            context="daemon_recovery_plan",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.recovery_reason = redact_operator_text(self.recovery_reason)
        self.safe_steps = [redact_operator_text(step) for step in self.safe_steps]
        return self


class OperatorHandoffRequest(SentinelModel):
    handoff_id: str = Field(default_factory=lambda: new_id("daemon_handoff"))
    mission_id: str
    reason: str
    safe_summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _handoff_is_data_only(self) -> OperatorHandoffRequest:
        assert_data_not_authority(
            context="operator_handoff_request",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.reason = redact_operator_text(self.reason)
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.metadata = sanitize_daemon_metadata(self.metadata)
        return self


class OperatorNotification(SentinelModel):
    notification_id: str = Field(default_factory=lambda: new_id("daemon_notification"))
    mission_id: str
    title: str
    body: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _notification_is_data_only(self) -> OperatorNotification:
        assert_data_not_authority(
            context="operator_notification",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.title = redact_operator_text(self.title)
        self.body = redact_operator_text(self.body)
        self.metadata = sanitize_daemon_metadata(self.metadata)
        return self


class MissionDaemonState(SentinelModel):
    mission_id: str
    owner_id: str | None = None
    queue_status: DaemonQueueStatus = DaemonQueueStatus.QUEUED
    lease_id: str | None = None
    heartbeat_id: str | None = None
    dead_letter_id: str | None = None
    workflow_id: str | None = None
    worker_fleet_run_id: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _state_is_data_only(self) -> MissionDaemonState:
        assert_data_not_authority(
            context="mission_daemon_state",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class DaemonTickResult(SentinelModel):
    mission_id: str
    status: DaemonQueueStatus
    executed: bool = False
    workflow_id: str | None = None
    worker_fleet_run_id: str | None = None
    latest_checkpoint_id: str | None = None
    dead_letter_reason: DeadLetterReason | None = None
    safe_summary: str
    used_direct_organ_path: bool = False
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _tick_result_is_evidence_only(self) -> DaemonTickResult:
        assert_data_not_authority(
            context="daemon_tick_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self


class DaemonCertifiedModeSnapshot(SentinelModel):
    certified_mode: bool
    reasons: list[str] = Field(default_factory=list)
    telemetry_snapshot_hash: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @classmethod
    def from_telemetry(cls, snapshot: TelemetrySnapshot) -> DaemonCertifiedModeSnapshot:
        return cls(
            certified_mode=snapshot.certified_mode,
            reasons=list(snapshot.reasons),
            telemetry_snapshot_hash=stable_hash(snapshot.model_dump(mode="json")),
        )


class DaemonStatusView(SentinelModel):
    queue: list[DaemonQueueRecord] = Field(default_factory=list)
    leases: list[DaemonLease] = Field(default_factory=list)
    heartbeats: list[DaemonHeartbeatRecord] = Field(default_factory=list)
    dead_letters: list[DeadLetterRecord] = Field(default_factory=list)
    certified_mode: DaemonCertifiedModeSnapshot
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False


class DaemonReplayView(SentinelModel):
    mission_id: str
    queue: list[DaemonQueueRecord] = Field(default_factory=list)
    leases: list[DaemonLease] = Field(default_factory=list)
    heartbeats: list[DaemonHeartbeatRecord] = Field(default_factory=list)
    dead_letters: list[DeadLetterRecord] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    reexecuted_actions: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False


class ProactiveProposal(SentinelModel):
    proposal_id: str = Field(default_factory=lambda: new_id("scheduler_proposal"))
    mission_id: str
    trigger_type: str
    safe_summary: str
    suggested_action: str = "operator_checkpoint"
    metadata: dict[str, Any] = Field(default_factory=dict)
    can_execute: bool = False
    can_grant_authority: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True

    @model_validator(mode="after")
    def _proposal_is_data_only(self) -> ProactiveProposal:
        assert_data_not_authority(
            context="proactive_scheduler_proposal",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.metadata = sanitize_daemon_metadata(self.metadata)
        return self


class ProactiveSchedulerConfig(SentinelModel):
    require_certified_telemetry: bool = True
    proposal_only: bool = True
    max_proposals_per_mission: int = Field(default=8, ge=0)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _config_is_data_only(self) -> ProactiveSchedulerConfig:
        assert_data_not_authority(
            context="proactive_scheduler_config",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class SchedulerPolicy(SentinelModel):
    require_certified_telemetry: bool = True
    allow_operator_handoff: bool = True
    proposal_only: bool = True
    max_proposals_per_mission: int = Field(default=8, ge=0)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _policy_is_data_only(self) -> SchedulerPolicy:
        assert_data_not_authority(
            context="scheduler_policy",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class SchedulerDecision(SentinelModel):
    kind: SchedulerDecisionKind
    mission_id: str
    proposal: ProactiveProposal | None = None
    reasons: list[str] = Field(default_factory=list)
    safe_summary: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _decision_is_data_only(self) -> SchedulerDecision:
        assert_data_not_authority(
            context="proactive_scheduler_decision",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


_HASH_ONLY_KEYS = {
    "raw_prompt",
    "prompt",
    "provider_response",
    "raw_provider_response",
    "reasoning",
    "raw_reasoning",
    "transcript",
}


def sanitize_daemon_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = redact_operator_text(str(key))
            if safe_key.lower() in _HASH_ONLY_KEYS:
                sanitized[f"{safe_key}_hash"] = stable_hash(redact_operator_value(item))
                continue
            sanitized[safe_key] = sanitize_daemon_metadata(item)
        return sanitized
    if isinstance(value, (list, tuple, set)):
        return [sanitize_daemon_metadata(item) for item in value]
    return redact_operator_value(value)
