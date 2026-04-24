from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sentinel.shared.enums import Verdict


class AgentOpinion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    role: str
    opinion: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    skeptical_challenge: str | None = None


class DebateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea: str
    market_verdict: str
    recommended_wedge: str
    primary_icp: str
    business_model: str
    pricing_test: str
    risks: list[str] = Field(default_factory=list)
    decision: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    opinions: list[AgentOpinion] = Field(default_factory=list)
    skeptical_challenge: str

