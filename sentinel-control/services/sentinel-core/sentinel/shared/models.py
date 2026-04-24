from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from sentinel.shared.enums import ApprovalStatus, EvidenceType, RiskLevel, TraceEventType, Verdict


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class SentinelModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class EvidenceItem(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("ev"))
    source: str
    url: str | None = None
    quote: str | None = None
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    evidence_type: EvidenceType
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentAction(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("act"))
    tool: str
    intent: str
    input: dict[str, Any] = Field(default_factory=dict)
    expected_output: str
    risk_level: RiskLevel
    requires_approval: bool
    evidence_refs: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING


class DecisionPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("plan"))
    goal: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    reasoning_summary: str
    proposed_actions: list[AgentAction] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=100.0)
    verdict: Verdict


class TraceRecord(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("trace"))
    user_id: str
    run_id: str
    event_type: TraceEventType
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    decision_snapshot: dict[str, Any] | None = None
    action_snapshot: dict[str, Any] | None = None
    output_snapshot: dict[str, Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DryRunPreview(SentinelModel):
    action: str
    risk: RiskLevel
    why_needed: str
    evidence_used: list[str] = Field(default_factory=list)
    preview: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool


class FirewallReview(SentinelModel):
    action_id: str
    tool: str
    risk_level: RiskLevel
    risk_score: float = Field(ge=0.0, le=100.0)
    requires_approval: bool
    approval_status: ApprovalStatus
    allowed: bool
    blocked: bool
    reasons: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)
    dry_run: DryRunPreview | None = None


class AgentRun(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    user_id: str
    input_idea: str
    status: str = "created"
    verdict: Verdict | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_score: float | None = Field(default=None, ge=0.0, le=100.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GeneratedAsset(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("asset"))
    run_id: str
    asset_type: str
    title: str
    content: str
    file_path: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FirewallPolicy(SentinelModel):
    tool_name: str
    risk_level: RiskLevel
    auto_allowed: bool
    requires_user_approval: bool = False
    v1_disabled: bool = False
    allowed_paths: list[str] = Field(default_factory=list)
    policy_json: dict[str, Any] = Field(default_factory=dict)

