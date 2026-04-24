from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from sentinel.shared.models import EvidenceItem


class BridgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Competitor(BridgeModel):
    name: str
    url: str | None = None
    gap: str | None = None
    threat_level: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class TrendSignal(BridgeModel):
    keyword: str
    direction: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class Watchlist(BridgeModel):
    id: str | None = None
    idea: str
    competitors: list[str] = Field(default_factory=list)
    status: str = "created"
    raw: dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BridgeModel):
    idea: str
    validation_id: str | None = None
    verdict: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    trends: list[TrendSignal] = Field(default_factory=list)
    direct_evidence_count: int = 0
    adjacent_evidence_count: int = 0
    wtp_signal_count: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)

