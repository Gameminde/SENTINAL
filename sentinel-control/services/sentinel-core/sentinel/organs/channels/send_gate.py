from __future__ import annotations

from pydantic import Field

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.channels.compliance import ChannelComplianceDecision
from sentinel.organs.channels.draft import ChannelMessageDraft
from sentinel.organs.channels.outbound import RecipientProvenance
from sentinel.organs.channels.rate_limit import ChannelRateLimitDecision
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class ChannelSendGateDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chgate"))
    send_allowed: bool = False
    dry_run_only: bool = True
    lane: AutonomyRiskLane
    reasons: list[str]
    recipient_refs: list[str] = Field(default_factory=list)
    authority_expansion: bool = False


class ChannelSendGate:
    def evaluate(
        self,
        draft: ChannelMessageDraft,
        authority: OrganAuthorityEnvelope,
        *,
        recipients: list[RecipientProvenance],
        compliance: ChannelComplianceDecision,
        rate_limit: ChannelRateLimitDecision,
        finalgate_available: bool,
    ) -> ChannelSendGateDecision:
        reasons: list[str] = []
        if authority.errors:
            reasons.extend(f"authority_error:{error}" for error in authority.errors)
        if not recipients:
            reasons.append("missing_recipient_provenance")
        if compliance.blocked:
            reasons.extend(["compliance_blocked", *compliance.matched_terms])
        if not rate_limit.accepted:
            reasons.append("rate_limit_exceeded")
        if not finalgate_available:
            reasons.append("finalgate_unavailable")
        reasons.append("p6e_live_send_not_promoted")
        lane = AutonomyRiskLane.BLACK if compliance.blocked else AutonomyRiskLane.ORANGE
        return ChannelSendGateDecision(
            send_allowed=False,
            dry_run_only=True,
            lane=lane,
            reasons=reasons,
            recipient_refs=[recipient.id for recipient in recipients],
        )
