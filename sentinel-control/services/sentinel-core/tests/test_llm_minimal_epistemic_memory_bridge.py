from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.llm import (
    FeedbackSignalKind,
    LivingMissionMemoryEntry,
    MemoryBridgeInput,
    MemoryClaimStatus,
    MemorySourceClass,
    RoleLoopMemoryBridge,
)


NOW = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)


def _item(**updates: Any) -> dict[str, Any]:
    base = {
        "source_class": MemorySourceClass.evidence,
        "source_id": "ev_1",
        "source_lineage_id": "lineage_1",
        "source_scope": "mission_scope",
        "validity_scope": "mission_scope",
        "claim_status": MemoryClaimStatus.SUPPORTED,
        "confidence": 0.72,
        "variance": 0.12,
        "evidence_refs": ["ev_1"],
        "receipt_refs": ["receipt_1"],
        "safe_summary": "Evidence-supported scoped memory.",
        "uncertainty": ["current scope only"],
    }
    base.update(updates)
    return base


def _input(**updates: Any) -> MemoryBridgeInput:
    base = {
        "mission_id": "mission_memory",
        "loop_id": "role_loop_1",
        "memory_items": [_item()],
        "current_time": NOW,
    }
    base.update(updates)
    return MemoryBridgeInput(**base)


def _bridge_result(**updates: Any):
    return RoleLoopMemoryBridge().build(_input(**updates))


def _signal_kinds(result) -> set[FeedbackSignalKind]:
    return {signal.kind for signal in result.feedback_signals}


def test_memory_cannot_grant_root_authority() -> None:
    with pytest.raises(ValidationError):
        LivingMissionMemoryEntry(
            memory_id="mem_bad",
            mission_id="mission_memory",
            source_class=MemorySourceClass.evidence,
            source_id="ev_1",
            source_lineage_id="lineage_1",
            source_scope="mission_scope",
            validity_scope="mission_scope",
            created_at=NOW,
            observed_at=NOW,
            claim_status=MemoryClaimStatus.SUPPORTED,
            confidence=0.9,
            variance=0.1,
            evidence_refs=["ev_1"],
            receipt_refs=["receipt_1"],
            uncertainty=[],
            safe_summary="Bad authority memory.",
            can_grant_authority=True,
        )


def test_memory_cannot_approve_execution() -> None:
    with pytest.raises(ValidationError):
        LivingMissionMemoryEntry(
            memory_id="mem_bad",
            mission_id="mission_memory",
            source_class=MemorySourceClass.evidence,
            source_id="ev_1",
            source_lineage_id="lineage_1",
            source_scope="mission_scope",
            validity_scope="mission_scope",
            created_at=NOW,
            observed_at=NOW,
            claim_status=MemoryClaimStatus.SUPPORTED,
            confidence=0.9,
            variance=0.1,
            safe_summary="Bad execution memory.",
            can_approve_execution=True,
        )


def test_memory_cannot_create_delegated_lane() -> None:
    with pytest.raises(ValidationError):
        LivingMissionMemoryEntry(
            memory_id="mem_bad",
            mission_id="mission_memory",
            source_class=MemorySourceClass.evidence,
            source_id="ev_1",
            source_lineage_id="lineage_1",
            source_scope="mission_scope",
            validity_scope="mission_scope",
            created_at=NOW,
            observed_at=NOW,
            claim_status=MemoryClaimStatus.SUPPORTED,
            confidence=0.9,
            variance=0.1,
            safe_summary="Bad lane memory.",
            can_create_delegated_lane=True,
        )


def test_memory_cannot_override_provider_backend_model() -> None:
    result = _bridge_result(memory_items=[_item(provider_override="other", backend_override="x", model_override="y")])

    assert result.safety_validation.valid is False
    assert result.memory_entries == []


def test_memory_snapshot_has_authority_effect_none() -> None:
    result = _bridge_result()

    assert result.snapshot.authority_effect == "none"


def test_memory_snapshot_has_execution_effect_none() -> None:
    result = _bridge_result()

    assert result.snapshot.execution_effect == "none"


def test_raw_prompt_response_reasoning_key_rejected() -> None:
    result = _bridge_result(
        final_packet={
            "raw_prompt": "do not persist me",
            "raw_response": "provider body",
            "reasoning": "private chain",
            "api_key": "not-a-real-key",
        }
    )

    assert result.safety_validation.valid is False
    assert result.memory_entries == []
    assert "forbidden_memory_payload" in result.safety_validation.reasons


def test_hidden_tool_or_organ_payload_rejected() -> None:
    result = _bridge_result(final_packet={"nested": {"tool_calls": [{"name": "browser_submit"}]}})

    assert result.safety_validation.valid is False
    assert FeedbackSignalKind.BLOCKED_INTENT in _signal_kinds(result)


def test_bearer_token_or_secret_rejected() -> None:
    fake_bearer = "Bearer " + "abcdefghijklmnop123456"
    result = _bridge_result(final_packet={"diagnostic": fake_bearer})

    assert result.safety_validation.valid is False
    assert result.memory_entries == []


def test_self_generated_receipts_do_not_satisfy_evidence_requirement() -> None:
    result = _bridge_result(
        memory_items=[
            _item(
                source_class=MemorySourceClass.role_output,
                source_id="role_output_1",
                source_lineage_id="role_lineage_1",
                claim_status=MemoryClaimStatus.SUPPORTED,
                evidence_refs=[],
                receipt_refs=["role_receipt_1"],
                confidence=0.88,
            )
        ]
    )

    assert result.memory_entries[0].claim_status is not MemoryClaimStatus.SUPPORTED
    assert FeedbackSignalKind.SELF_GENERATED_EVIDENCE_QUARANTINED in _signal_kinds(result)
    assert result.snapshot.self_generated_evidence_quarantine_count == 1


def test_duplicate_same_source_does_not_increase_confidence() -> None:
    result = _bridge_result(
        memory_items=[
            _item(source_lineage_id="same_lineage", confidence=0.4),
            _item(source_id="ev_2", source_lineage_id="same_lineage", confidence=0.9),
        ]
    )

    assert len(result.memory_entries) == 1
    assert result.memory_entries[0].confidence == 0.4


def test_duplicate_source_creates_feedback_signal() -> None:
    result = _bridge_result(
        memory_items=[
            _item(source_lineage_id="same_lineage"),
            _item(source_id="ev_2", source_lineage_id="same_lineage"),
        ]
    )

    assert FeedbackSignalKind.DUPLICATE_SOURCE_SUPPRESSED in _signal_kinds(result)
    assert result.snapshot.duplicate_source_suppression_count == 1


def test_user_correction_supersedes_inferred_memory() -> None:
    result = _bridge_result(
        memory_items=[
            _item(
                source_class=MemorySourceClass.role_output,
                source_id="role_output_1",
                source_lineage_id="role_lineage_1",
                claim_status=MemoryClaimStatus.INFERRED,
                validity_scope="preference_scope",
                safe_summary="Use the old preference.",
            ),
            _item(
                source_class=MemorySourceClass.user_correction,
                source_id="user_correction_1",
                source_lineage_id="user_lineage_1",
                claim_status=MemoryClaimStatus.OBSERVED,
                validity_scope="preference_scope",
                safe_summary="Use the corrected preference.",
            ),
        ]
    )

    by_source = {entry.source_id: entry for entry in result.memory_entries}
    assert by_source["role_output_1"].claim_status is MemoryClaimStatus.SUPERSEDED
    assert by_source["user_correction_1"].source_class is MemorySourceClass.user_correction
    assert FeedbackSignalKind.USER_CORRECTION in _signal_kinds(result)


def test_contradictions_survive_snapshot() -> None:
    result = _bridge_result(
        memory_items=[_item(contradiction_refs=["ev_contra"], claim_status=MemoryClaimStatus.WEAK_SUPPORT)]
    )

    assert result.memory_entries[0].contradiction_refs == ["ev_contra"]
    assert result.snapshot.contradiction_count == 1


def test_expired_memory_returns_historical_only() -> None:
    result = _bridge_result(memory_items=[_item(expires_at=NOW - timedelta(days=1))])

    assert result.memory_entries[0].claim_status is MemoryClaimStatus.EXPIRED
    assert result.memory_entries[0].historical_only is True
    assert FeedbackSignalKind.STALE_MEMORY in _signal_kinds(result)


def test_missing_evidence_creates_feedback_signal() -> None:
    result = _bridge_result(missing_evidence=["claim_missing"])

    assert FeedbackSignalKind.MISSING_EVIDENCE in _signal_kinds(result)
    assert result.snapshot.evidence_gap_count == 1


def test_invented_evidence_ref_creates_feedback_signal() -> None:
    result = _bridge_result(invented_evidence_refs=["ev_fake"])

    assert FeedbackSignalKind.INVENTED_EVIDENCE_REF in _signal_kinds(result)
    assert result.snapshot.evidence_gap_count == 1


def test_contradiction_creates_feedback_signal() -> None:
    result = _bridge_result(contradictions=[{"claim_id": "claim_1", "evidence_refs": ["ev_contra"]}])

    assert FeedbackSignalKind.CONTRADICTION in _signal_kinds(result)
    assert result.snapshot.contradiction_count == 1


def test_budget_issue_creates_feedback_signal() -> None:
    result = _bridge_result(budget_summaries=[{"compliant": False, "decision": "mission_budget_exhausted"}])

    assert FeedbackSignalKind.BUDGET_EXHAUSTED in _signal_kinds(result)
    assert result.snapshot.budget_issue_count == 1


def test_blocked_intent_creates_feedback_signal() -> None:
    result = _bridge_result(blocked_intents=["forbidden_model_output_intent"])

    assert FeedbackSignalKind.BLOCKED_INTENT in _signal_kinds(result)
    assert result.snapshot.blocked_action_count == 1


def test_self_improvement_candidate_is_proposal_only() -> None:
    result = _bridge_result(self_improvement_candidates=[{"safe_summary": "Improve evidence prompts."}])

    assert FeedbackSignalKind.SELF_IMPROVEMENT_CANDIDATE in _signal_kinds(result)
    assert result.authority_effect == "none"
    assert result.execution_effect == "none"


def test_identical_sanitized_inputs_produce_deterministic_memory_ids() -> None:
    first = _bridge_result()
    second = _bridge_result()

    assert first.memory_entries[0].memory_id == second.memory_entries[0].memory_id


def test_memory_bridge_result_is_non_executing() -> None:
    result = _bridge_result()

    assert result.can_grant_authority is False
    assert result.can_approve_execution is False
    assert result.can_create_delegated_lane is False
    assert result.can_override_provider_model is False
    assert result.authority_effect == "none"
    assert result.execution_effect == "none"


def test_memory_retrieval_is_data_not_instruction_contract_placeholder() -> None:
    result = _bridge_result()

    assert result.retrieval_contract == "data_not_instruction"
