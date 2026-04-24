from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sentinel.decision.source_ranker import rank_sources
from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


class ResearchBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idea: str
    questions: list[str]
    ranked_evidence: list[EvidenceItem] = Field(default_factory=list)
    pain_signal_count: int = 0
    wtp_signal_count: int = 0
    competitor_signal_count: int = 0
    community_signal_count: int = 0
    summary: str


class ResearchAgent:
    def generate_questions(self, idea: str) -> list[str]:
        return [
            f"Who has the strongest repeated pain for {idea}?",
            f"What alternatives do people use today instead of {idea}?",
            f"Who pays today to solve the problem behind {idea}?",
            f"What competitor complaints repeat around {idea}?",
            f"What keywords show buying intent for {idea}?",
            f"Which communities concentrate reachable first customers for {idea}?",
        ]

    def build_brief(self, idea: str, evidence: list[EvidenceItem]) -> ResearchBrief:
        ranked = rank_sources(evidence)
        pain_count = sum(1 for item in ranked if item.evidence_type == EvidenceType.PAIN)
        wtp_count = sum(1 for item in ranked if item.evidence_type in {EvidenceType.WTP, EvidenceType.PRICING})
        competitor_count = sum(1 for item in ranked if item.evidence_type == EvidenceType.COMPETITOR_COMPLAINT)
        community_count = sum(1 for item in ranked if item.evidence_type == EvidenceType.COMMUNITY_SIGNAL)
        summary = (
            f"{idea} research brief: {len(ranked)} evidence items, "
            f"{pain_count} pain signals, {wtp_count} WTP/pricing signals, "
            f"{competitor_count} competitor signals, {community_count} community signals."
        )

        return ResearchBrief(
            idea=idea,
            questions=self.generate_questions(idea),
            ranked_evidence=ranked,
            pain_signal_count=pain_count,
            wtp_signal_count=wtp_count,
            competitor_signal_count=competitor_count,
            community_signal_count=community_count,
            summary=summary,
        )

