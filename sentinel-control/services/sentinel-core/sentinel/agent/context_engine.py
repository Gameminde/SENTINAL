from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from sentinel.agent.token_ledger import estimate_tokens
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    from sentinel.agent.decision_frame import LLMDecisionFrame


class ContextNeed(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("ctxneed"))
    mission_id: str
    objective: str
    blockers: list[str] = Field(default_factory=list)
    required_evidence_refs: list[str] = Field(default_factory=list)
    candidate_tools: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ContextNeedEstimator:
    """Builds a deterministic statement of what the next LLM decision needs."""

    STOPWORDS = {
        "and",
        "the",
        "for",
        "with",
        "need",
        "needs",
        "next",
        "step",
        "choose",
        "current",
        "source",
        "evidence",
    }

    def estimate(
        self,
        *,
        mission_id: str,
        objective: str,
        blockers: list[str] | None = None,
        required_evidence_refs: list[str] | None = None,
        candidate_tools: list[str] | None = None,
    ) -> ContextNeed:
        text = " ".join([objective, " ".join(blockers or []), " ".join(candidate_tools or [])]).lower()
        keywords = sorted(
            {
                token.strip(".,:;!?()[]{}")
                for token in text.split()
                if len(token.strip(".,:;!?()[]{}")) >= 3 and token.strip(".,:;!?()[]{}") not in self.STOPWORDS
            }
        )
        return ContextNeed(
            mission_id=mission_id,
            objective=objective,
            blockers=blockers or [],
            required_evidence_refs=required_evidence_refs or [],
            candidate_tools=candidate_tools or [],
            keywords=keywords,
        )


class ContextCompressionResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("ctxcompress"))
    raw_context_tokens: int = Field(ge=0)
    decision_frame_tokens: int = Field(ge=0)
    compression_ratio: float = Field(ge=0.0)
    authority_preserved: bool
    critical_evidence_preserved: bool
    prompt_budget_respected: bool

    @classmethod
    def from_frame(cls, *, raw_context: str, frame: LLMDecisionFrame) -> ContextCompressionResult:
        raw_tokens = estimate_tokens(raw_context)
        ratio = (frame.token_count / raw_tokens) if raw_tokens else 0.0
        return cls(
            raw_context_tokens=raw_tokens,
            decision_frame_tokens=frame.token_count,
            compression_ratio=round(ratio, 6),
            authority_preserved=bool(frame.authority_card),
            critical_evidence_preserved=bool(frame.top_k_evidence),
            prompt_budget_respected=frame.prompt_budget_respected,
        )
