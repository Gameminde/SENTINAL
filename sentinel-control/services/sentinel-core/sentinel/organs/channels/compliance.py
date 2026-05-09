from __future__ import annotations

from pydantic import Field

from sentinel.organs.channels.draft import ChannelMessageDraft
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class ChannelComplianceDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chcomp"))
    blocked: bool
    lane: AutonomyRiskLane
    matched_terms: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    authority_expansion: bool = False


class ChannelComplianceClassifier:
    TERM_MAP = {
        "spam": {"spam", "mass_spam", "illegal_spam"},
        "deceptive_outreach": {"deceptive", "deception", "misleading"},
        "hidden_identity": {"hide_identity", "hidden_identity", "anonymous_sender"},
        "credential_capture": {"credential_capture", "capture_credentials", "phishing", "api_key"},
    }

    def classify(self, draft: ChannelMessageDraft) -> ChannelComplianceDecision:
        haystack = " ".join([draft.subject or "", draft.body, *draft.objective_tags]).lower().replace(" ", "_")
        matched = []
        for label, terms in self.TERM_MAP.items():
            if any(term in haystack for term in terms):
                matched.append(label)
        blocked = bool(matched)
        return ChannelComplianceDecision(
            blocked=blocked,
            lane=AutonomyRiskLane.BLACK if blocked else draft.lane,
            matched_terms=sorted(matched),
            reasons=["channel_misuse_blocked"] if blocked else ["channel_draft_compliance_clear"],
        )
