from sentinel.decision.debate import DebateOrchestrator
from sentinel.execution.gtm_pack import GTMPackGenerator
from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


def evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            source="reddit",
            summary="Freelancers repeatedly complain about chasing unpaid invoices.",
            confidence=0.9,
            freshness_score=0.8,
            relevance_score=0.9,
            evidence_type=EvidenceType.PAIN,
            metadata={"proof_tier": "direct"},
        ),
        EvidenceItem(
            source="reddit",
            summary="A freelancer says they would pay for automatic reminders.",
            confidence=0.8,
            freshness_score=0.8,
            relevance_score=0.85,
            evidence_type=EvidenceType.WTP,
            metadata={"proof_tier": "direct"},
        ),
    ]


def test_gtm_pack_sections_all_reference_evidence():
    items = evidence()
    debate = DebateOrchestrator().debate("AI invoice chasing", items)
    pack = GTMPackGenerator().generate("AI invoice chasing", debate, items)

    assert len(pack.sections) == 10
    assert all(section.evidence_refs for section in pack.sections)
    assert any(section.filename == "09_DECISION_RULES.md" and "Kill if" in section.content for section in pack.sections)


def test_gtm_pack_actions_are_draft_and_file_only():
    items = evidence()
    debate = DebateOrchestrator().debate("AI invoice chasing", items)
    pack = GTMPackGenerator().generate("AI invoice chasing", debate, items)
    actions = GTMPackGenerator().actions_for_pack(pack)

    assert actions[0].tool == "create_folder"
    assert any(action.tool == "prepare_email_draft" and action.requires_approval for action in actions)
    assert not any(action.tool == "send_email" for action in actions)

