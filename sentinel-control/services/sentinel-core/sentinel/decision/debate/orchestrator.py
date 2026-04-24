from __future__ import annotations

from sentinel.decision.debate.agents import count_type, evidence_refs, strongest_summary
from sentinel.decision.debate.verdict import AgentOpinion, DebateResult
from sentinel.shared.enums import EvidenceType, Verdict
from sentinel.shared.models import EvidenceItem


class DebateOrchestrator:
    def debate(self, idea: str, evidence: list[EvidenceItem]) -> DebateResult:
        refs = evidence_refs(evidence, limit=8)
        pain_count = count_type(evidence, EvidenceType.PAIN, EvidenceType.DIRECT_PROOF)
        wtp_count = count_type(evidence, EvidenceType.WTP, EvidenceType.PRICING)
        competitor_count = count_type(evidence, EvidenceType.COMPETITOR_COMPLAINT)
        community_count = count_type(evidence, EvidenceType.COMMUNITY_SIGNAL)
        direct_count = sum(1 for item in evidence if item.metadata.get("proof_tier") == "direct")

        wedge = strongest_summary(evidence, f"Narrow {idea} to the buyer segment with the strongest direct pain.")
        has_wedge = bool(wedge and len(wedge) > 20)

        if pain_count >= 2 and wtp_count >= 1 and (competitor_count == 0 or has_wedge):
            decision = Verdict.BUILD
            market_verdict = "promising"
        elif pain_count >= 1 and (wtp_count >= 1 or community_count >= 1):
            decision = Verdict.NICHE_DOWN
            market_verdict = "needs_niche"
        elif pain_count == 0 and wtp_count == 0:
            decision = Verdict.RESEARCH_MORE
            market_verdict = "weak"
        elif competitor_count >= 2 and not has_wedge:
            decision = Verdict.PIVOT
            market_verdict = "saturated"
        else:
            decision = Verdict.RESEARCH_MORE
            market_verdict = "needs_more_proof"

        if wtp_count == 0 and decision == Verdict.BUILD:
            decision = Verdict.NICHE_DOWN
            market_verdict = "needs_niche"

        risks = []
        if wtp_count == 0:
            risks.append("WTP evidence is weak; do not commit to build until pricing intent is proven.")
        if direct_count == 0:
            risks.append("Direct proof is missing; current recommendation relies on adjacent or supporting evidence.")
        if competitor_count >= 2:
            risks.append("Competitor pressure exists; the wedge must be narrower than the category.")

        confidence = min(
            0.95,
            0.25
            + min(pain_count, 4) * 0.10
            + min(wtp_count, 3) * 0.14
            + min(direct_count, 4) * 0.08
            + min(community_count, 3) * 0.04,
        )

        skeptical_challenge = (
            "The current evidence may describe interest rather than paid urgency; validate WTP and buyer reachability before execution."
        )
        opinions = [
            AgentOpinion(
                agent_name="SIGNAL_AGENT",
                role="trend, timing, market forces",
                opinion=f"Market signal is {market_verdict} with {pain_count} pain signals and {community_count} community signals.",
                confidence=confidence,
                evidence_refs=refs,
            ),
            AgentOpinion(
                agent_name="AXIOM_AGENT",
                role="scoring, risk, expected value, invalidation",
                opinion=f"Decision should be {decision.value}; WTP count is {wtp_count}.",
                confidence=confidence,
                evidence_refs=refs,
            ),
            AgentOpinion(
                agent_name="SKEPTIC_AGENT",
                role="attacks weak assumptions",
                opinion="The plan is not allowed to become build-first without paid-intent proof.",
                confidence=0.9,
                evidence_refs=refs,
                skeptical_challenge=skeptical_challenge,
            ),
        ]

        return DebateResult(
            idea=idea,
            market_verdict=market_verdict,
            recommended_wedge=wedge,
            primary_icp="Start with the narrowest reachable buyer segment represented in the strongest evidence.",
            business_model="Concierge validation first, then subscription or service-assisted SaaS if WTP is proven.",
            pricing_test="$19-$99/mo or paid pilot; exact price must be validated with WTP evidence.",
            risks=risks,
            decision=decision,
            confidence=confidence,
            evidence_refs=refs,
            opinions=opinions,
            skeptical_challenge=skeptical_challenge,
        )

