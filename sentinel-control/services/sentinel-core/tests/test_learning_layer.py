from __future__ import annotations

from sentinel.learning.feedback import FeedbackRecord, summarize_feedback
from sentinel.learning.memory import InMemoryMemoryStore, derive_memory_entries
from sentinel.learning.prompt_versions import PromptVersion, PromptVersionRegistry
from sentinel.learning.self_improvement import propose_improvements
from sentinel.shared.enums import RiskLevel


def test_feedback_summary_counts_ratings_and_targets() -> None:
    records = [
        FeedbackRecord(run_id="run_1", target_type="asset", target_id="asset_1", rating="useful"),
        FeedbackRecord(run_id="run_1", target_type="asset", target_id="asset_2", rating="weak"),
        FeedbackRecord(run_id="run_1", target_type="action", target_id="A-101", rating="approved"),
    ]

    summary = summarize_feedback(records)

    assert summary.total == 3
    assert summary.useful == 1
    assert summary.weak == 1
    assert summary.approved == 1
    assert summary.weak_targets == ["asset_2"]
    assert "asset_1" in summary.useful_targets


def test_memory_entries_are_derived_from_user_feedback() -> None:
    records = [
        FeedbackRecord(run_id="run_1", target_type="asset", target_id="asset_1", rating="useful"),
        FeedbackRecord(run_id="run_1", target_type="asset", target_id="asset_2", rating="weak"),
    ]
    store = InMemoryMemoryStore()

    for entry in derive_memory_entries(records):
        store.add(entry)

    entries = store.list()
    assert {entry.subject for entry in entries} == {"useful_outputs", "weak_outputs"}
    assert all(entry.confidence > 0 for entry in entries)


def test_prompt_registry_keeps_one_active_version_per_name() -> None:
    registry = PromptVersionRegistry()
    registry.register(PromptVersion(name="gtm_pack", version="1.0.0", purpose="pack", content="old"))
    latest = registry.register(PromptVersion(name="gtm_pack", version="1.1.0", purpose="pack", content="new"))

    assert registry.active("gtm_pack") == latest
    assert len([prompt for prompt in registry.list() if prompt.name == "gtm_pack" and prompt.active]) == 1


def test_self_improvement_proposals_are_draft_and_non_mutating() -> None:
    records = [
        FeedbackRecord(run_id="run_1", target_type="asset", target_id="asset_weak", rating="weak"),
        FeedbackRecord(run_id="run_1", target_type="action", target_id="A-101", rating="rejected"),
    ]

    proposals = propose_improvements(records)

    assert len(proposals) == 2
    assert all(proposal.status == "needs_user_approval" for proposal in proposals)
    assert all(proposal.risk == RiskLevel.MEDIUM for proposal in proposals)
    assert all(proposal.tests_needed for proposal in proposals)
