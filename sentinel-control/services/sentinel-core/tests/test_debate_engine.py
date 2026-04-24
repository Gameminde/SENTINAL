from sentinel.decision.debate import DebateOrchestrator
from sentinel.shared.enums import EvidenceType, Verdict
from sentinel.shared.models import EvidenceItem


def item(evidence_type: EvidenceType, summary: str, proof_tier: str = "direct") -> EvidenceItem:
    return EvidenceItem(
        source="test",
        summary=summary,
        confidence=0.85,
        freshness_score=0.8,
        relevance_score=0.9,
        evidence_type=evidence_type,
        metadata={"proof_tier": proof_tier},
    )


def test_debate_never_builds_without_wtp_evidence():
    result = DebateOrchestrator().debate("AI invoice chasing", [
        item(EvidenceType.PAIN, "Freelancers struggle with unpaid invoice reminders."),
        item(EvidenceType.PAIN, "Manual follow-up is awkward and time-consuming."),
    ])

    assert result.decision != Verdict.BUILD
    assert "WTP evidence is weak" in result.risks[0]
    assert result.skeptical_challenge
    assert result.evidence_refs


def test_debate_can_build_when_pain_wtp_and_wedge_exist():
    result = DebateOrchestrator().debate("AI invoice chasing", [
        item(EvidenceType.PAIN, "Freelancers repeatedly complain about chasing invoices."),
        item(EvidenceType.PAIN, "Agencies have recurring late-payment operations pain."),
        item(EvidenceType.WTP, "A freelancer says they would pay for automatic reminders."),
        item(EvidenceType.COMMUNITY_SIGNAL, "Freelance communities discuss this workflow weekly.", "adjacent"),
    ])

    assert result.decision == Verdict.BUILD
    assert any(opinion.agent_name == "SKEPTIC_AGENT" for opinion in result.opinions)

