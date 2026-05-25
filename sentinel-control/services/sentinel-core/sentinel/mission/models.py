from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import Field

from sentinel.shared.enums import (
    ConfidenceLevel,
    EscalationOption,
    ExternalityLevel,
    MissionActionRoute,
    MissionMode,
    MissionStatus,
    MissionType,
    MissionTraceEventType,
    ReversibilityLevel,
    SensitivityLevel,
)
from sentinel.shared.models import SentinelModel, new_id


def utc_now() -> datetime:
    return datetime.now(UTC)


class MissionAuthorityEnvelope(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mission"))
    user_id: str
    mission_type: MissionType = MissionType.GTM
    mission_title: str
    mission_objective: str
    success_criteria: list[str] = Field(default_factory=list)
    mode: MissionMode = MissionMode.SAFE
    allowed_systems: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=lambda: ["data/generated_projects"])
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_accounts: list[str] = Field(default_factory=list)
    allowed_data_types: list[str] = Field(default_factory=list)
    browser_v3_authority_grants: list[dict[str, Any]] = Field(default_factory=list)
    credential_grants: list[Any] = Field(default_factory=list)
    max_duration_minutes: int = Field(default=60, ge=1)
    max_actions: int = Field(default=50, ge=1)
    max_cost_usd: float = Field(default=0.0, ge=0.0)
    max_recipients: int = Field(default=0, ge=0)
    risk_appetite_score: float = Field(default=25.0, ge=0.0, le=100.0)
    escalation_triggers: list[str] = Field(default_factory=list)
    rollback_preference: str = "metadata_only"
    trace_level: str = "standard"
    emergency_stop_enabled: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None

    def resolved_expires_at(self) -> datetime:
        return self.expires_at or self.created_at + timedelta(minutes=self.max_duration_minutes)


class MissionState(SentinelModel):
    mission_id: str
    status: MissionStatus = MissionStatus.PLANNED
    current_step: str | None = None
    action_count: int = 0
    cost_used: float = Field(default=0.0, ge=0.0)
    started_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None


class MissionAction(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mact"))
    mission_id: str
    action_type: str
    tool: str
    intent: str
    target: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    expected_output: str
    reversibility: ReversibilityLevel = ReversibilityLevel.LOCAL_WRITE_REVERSIBLE
    externality: ExternalityLevel = ExternalityLevel.INTERNAL_LOCAL
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL
    estimated_cost: float = Field(default=0.0, ge=0.0)
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    route: MissionActionRoute | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    trace_id: str | None = None


class EscalationRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("esc"))
    mission_id: str
    action_id: str
    reason: str
    user_question: str
    action_preview: dict[str, Any] = Field(default_factory=dict)
    impact_summary: str
    options: list[EscalationOption] = Field(
        default_factory=lambda: [
            EscalationOption.APPROVE_ONCE,
            EscalationOption.ALLOW_FOR_MISSION,
            EscalationOption.DENY,
            EscalationOption.TAKE_OVER,
        ]
    )
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None


class MissionTraceEvent(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mev"))
    mission_id: str
    sequence: int = Field(default=0, ge=0)
    logical_time: int = Field(default=0, ge=0)
    event_type: MissionTraceEventType
    actor: str = "sentinel"
    action_id: str | None = None
    summary: str
    target: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    impact: str | None = None
    reversible: bool = True
    cost: float = Field(default=0.0, ge=0.0)
    timestamp: datetime = Field(default_factory=utc_now)
    previous_hash: str | None = None
    event_hash: str = ""


class MissionPlanStep(SentinelModel):
    id: str
    depends_on: list[str] = Field(default_factory=list)
    action: MissionAction
    expected_artifact: str | None = None
    required_evidence_refs: list[str] = Field(default_factory=list)
    status: str = "planned"


class MissionPlan(SentinelModel):
    mission_id: str
    steps: list[MissionPlanStep]


class MissionArtifactReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mrec"))
    mission_id: str | None = None
    artifact_id: str
    artifact_type: str
    artifact_path: str
    artifact_sha256: str
    size_bytes: int = Field(ge=0)
    action_id: str | None = None
    reversible: bool = True
    rollback_strategy: str = "delete_created_artifact_after_user_confirmation_if_hash_matches"
    scope: str = "mission_project_folder"
    trace_refs: list[str] = Field(default_factory=list)


class MissionArtifact(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("mart"))
    type: str
    path: str
    evidence_refs: list[str] = Field(default_factory=list)
    status: str = "created"
    created_by_action_id: str | None = None
    can_rollback: bool = True
    sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    receipt_id: str | None = None
    rollback_strategy: str | None = None
    trace_refs: list[str] = Field(default_factory=list)


class MissionArtifactSchema(SentinelModel):
    mission_type: MissionType | str
    required_artifact_types: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    major_sections: list[str] = Field(default_factory=list)
    draft_only_files: list[str] = Field(default_factory=list)


class RollbackMetadata(SentinelModel):
    created_files: list[str] = Field(default_factory=list)
    created_folders: list[str] = Field(default_factory=list)
    artifact_receipts: list[MissionArtifactReceipt] = Field(default_factory=list)
    can_rollback: bool = True
    rollback_action: str = "delete_created_artifacts_after_user_confirmation"


class ReviewerIssue(SentinelModel):
    code: str
    severity: str
    message: str
    artifact_path: str | None = None


class ReviewResult(SentinelModel):
    mission_id: str
    ready: bool
    issues: list[ReviewerIssue] = Field(default_factory=list)


class MissionRunResult(SentinelModel):
    mission: MissionAuthorityEnvelope
    state: MissionState
    project_path: str
    artifacts: list[MissionArtifact] = Field(default_factory=list)
    artifact_receipts: list[MissionArtifactReceipt] = Field(default_factory=list)
    review: ReviewResult
    success: bool
    trace_events: list[MissionTraceEvent] = Field(default_factory=list)
    escalations: list[EscalationRequest] = Field(default_factory=list)
    blocked_actions: list[MissionAction] = Field(default_factory=list)
