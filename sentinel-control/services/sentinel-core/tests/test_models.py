import pytest
from pydantic import ValidationError

from sentinel.shared.enums import EvidenceType, RiskLevel, TraceEventType, Verdict
from sentinel.shared.models import DecisionPlan, EvidenceItem


def test_enum_values_are_locked():
    assert RiskLevel.LOW.value == "low"
    assert Verdict.NICHE_DOWN.value == "niche_down"
    assert EvidenceType.WTP.value == "wtp"
    assert TraceEventType.ACTION_PROPOSED.value == "action_proposed"


def test_invalid_risk_verdict_and_evidence_type_are_rejected():
    with pytest.raises(ValidationError):
        EvidenceItem(
            source="reddit",
            summary="Pain signal",
            confidence=0.8,
            freshness_score=0.8,
            relevance_score=0.8,
            evidence_type="invalid",
        )

    evidence = EvidenceItem(
        source="reddit",
        summary="Pain signal",
        confidence=0.8,
        freshness_score=0.8,
        relevance_score=0.8,
        evidence_type=EvidenceType.PAIN,
    )
    with pytest.raises(ValidationError):
        DecisionPlan(
            goal="Validate idea",
            evidence=[evidence],
            reasoning_summary="Evidence is not enough yet.",
            proposed_actions=[],
            confidence=0.5,
            risk_score=20,
            verdict="invalid",
        )


def test_confidence_and_risk_score_are_constrained():
    with pytest.raises(ValidationError):
        EvidenceItem(
            source="reddit",
            summary="Pain signal",
            confidence=1.5,
            freshness_score=0.8,
            relevance_score=0.8,
            evidence_type=EvidenceType.PAIN,
        )

    with pytest.raises(ValidationError):
        DecisionPlan(
            goal="Validate idea",
            evidence=[],
            reasoning_summary="Too risky.",
            proposed_actions=[],
            confidence=0.6,
            risk_score=120,
            verdict=Verdict.RESEARCH_MORE,
        )

