from sentinel.decision import ResearchAgent
from sentinel.decision.source_ranker import rank_sources
from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


def evidence(summary: str, evidence_type: EvidenceType, relevance: float, confidence: float = 0.7) -> EvidenceItem:
    return EvidenceItem(
        source="test",
        summary=summary,
        confidence=confidence,
        freshness_score=0.8,
        relevance_score=relevance,
        evidence_type=evidence_type,
    )


def test_source_ranker_prioritizes_relevance_confidence_and_freshness():
    low = evidence("weak adjacent signal", EvidenceType.ADJACENT_PROOF, relevance=0.3, confidence=0.5)
    high = evidence("strong direct pain", EvidenceType.PAIN, relevance=0.95, confidence=0.9)

    ranked = rank_sources([low, high])

    assert ranked[0].summary == "strong direct pain"


def test_research_agent_builds_brief_with_required_questions_and_counts():
    agent = ResearchAgent()
    items = [
        evidence("people struggle with invoice chasing", EvidenceType.PAIN, relevance=0.9),
        evidence("would pay for reminders", EvidenceType.WTP, relevance=0.85),
        evidence("competitor lacks relationship-aware reminders", EvidenceType.COMPETITOR_COMPLAINT, relevance=0.8),
        evidence("freelance community signal", EvidenceType.COMMUNITY_SIGNAL, relevance=0.7),
    ]

    brief = agent.build_brief("AI invoice chasing", items)

    assert len(brief.questions) == 6
    assert brief.pain_signal_count == 1
    assert brief.wtp_signal_count == 1
    assert brief.competitor_signal_count == 1
    assert brief.community_signal_count == 1
    assert brief.ranked_evidence[0].relevance_score >= brief.ranked_evidence[-1].relevance_score

