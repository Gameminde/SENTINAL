from __future__ import annotations

from datetime import UTC, datetime, timedelta
from inspect import signature
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.llm import (
    FeedbackSignalKind,
    HotContextSlotBuilder,
    LLMRoleId,
    LLMRoleLoopOrchestrator,
    LLMRoleLoopPlan,
    LLMRoleOutput,
    LivingMissionMemoryEntry,
    LivingMissionMemorySnapshot,
    MemoryClaimStatus,
    MemoryReplayBuilder,
    MemoryReplayBuildInput,
    MemoryReplayEvent,
    MemoryReplayEventKind,
    MemoryReplayEventStatus,
    MemorySourceClass,
    MissionCheckpoint,
    MissionCheckpointBuilder,
    MissionCheckpointBuildInput,
    MissionCheckpointKind,
    MissionCheckpointStatus,
    SafeFeedbackSignal,
    SafeMemoryRetriever,
    MemoryRetrievalQuery,
    render_checkpoint_as_untrusted_context,
    render_replay_as_untrusted_context,
)
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.runtime import AgentRuntime


NOW = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
SECRET_FRAGMENT = "replay-secret-not-real"
RAW_PROMPT_FRAGMENT = "raw replay prompt " + SECRET_FRAGMENT


class RecordingRoleModelClient:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def complete_role(self, frame) -> LLMRoleOutput:
        self.calls.append(frame)
        return LLMRoleOutput(
            role_id=frame.role_id,
            provider_id=frame.selected_provider_id,
            backend_id=frame.selected_backend_id,
            model_id=frame.selected_model,
            content={"summary": f"{frame.role_id.value} safe output"},
            evidence_refs=["ev_direct"],
            input_tokens=8,
            output_tokens=6,
        )


def _model_contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id="groq",
        selected_backend_id="groq_openai_compatible_chat",
        selected_model="openai/gpt-oss-20b",
        cost_profile=ModelCostProfile(
            model_name="openai/gpt-oss-20b",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="openai/gpt-oss-20b",
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=250,
            max_evidence_tokens=1_000,
            reserve_output_tokens=200,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="memory_replay",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _plan(**updates: Any) -> LLMRoleLoopPlan:
    base = {
        "mission_id": "mission_replay",
        "mission_goal": "Replay memory as historical data only.",
        "user_model_contract": _model_contract(),
        "available_evidence_refs": ["ev_direct"],
        "mission_memory_refs": ["pre_existing_memory_ref"],
        "role_sequence": [LLMRoleId.VISIONARY, LLMRoleId.STRATEGIST],
        "raw_prompt_in_memory_only": RAW_PROMPT_FRAGMENT,
    }
    base.update(updates)
    return LLMRoleLoopPlan(**base)


def _entry(**updates: Any) -> LivingMissionMemoryEntry:
    base = {
        "memory_id": "memory_alpha",
        "mission_id": "mission_replay",
        "source_class": MemorySourceClass.evidence,
        "source_id": "ev_alpha",
        "source_lineage_id": "lineage_alpha",
        "source_scope": "mission_replay",
        "validity_scope": "mission_replay",
        "created_at": NOW,
        "observed_at": NOW,
        "expires_at": NOW + timedelta(hours=1),
        "claim_status": MemoryClaimStatus.CLAIMED,
        "confidence": 0.42,
        "variance": 0.38,
        "contradiction_refs": ["contra_alpha"],
        "evidence_refs": ["ev_alpha"],
        "receipt_refs": ["receipt_alpha"],
        "uncertainty": ["needs replay verification"],
        "safe_summary": "Alpha mission memory should remain historical data.",
    }
    base.update(updates)
    return LivingMissionMemoryEntry(**base)


def _snapshot(**updates: Any) -> LivingMissionMemorySnapshot:
    base = {
        "mission_id": "mission_replay",
        "loop_id": "role_loop_replay",
        "memory_entry_ids": ["memory_alpha"],
        "feedback_signal_count": 2,
        "evidence_gap_count": 1,
        "contradiction_count": 1,
        "risk_flag_count": 1,
        "blocked_action_count": 1,
        "budget_issue_count": 1,
        "learned_pattern_count": 0,
        "expired_memory_count": 0,
        "duplicate_source_suppression_count": 0,
        "self_generated_evidence_quarantine_count": 0,
        "safe_summary": "Replay snapshot safe summary.",
    }
    base.update(updates)
    return LivingMissionMemorySnapshot(**base)


def _feedback(kind: FeedbackSignalKind = FeedbackSignalKind.MISSING_EVIDENCE) -> SafeFeedbackSignal:
    return SafeFeedbackSignal.build(
        mission_id="mission_replay",
        loop_id="role_loop_replay",
        kind=kind,
        safe_summary=f"{kind.value} feedback for replay.",
        source_id=kind.value.lower(),
        evidence_refs=["ev_alpha"] if kind is not FeedbackSignalKind.BLOCKED_INTENT else [],
        receipt_refs=["receipt_alpha"],
    )


def _slot_set():
    return HotContextSlotBuilder().build(
        {
            "mission_id": "mission_replay",
            "mission_goal": "Replay memory as historical data only.",
            "memory_snapshot": _snapshot(),
            "memory_entries": [_entry()],
            "feedback_signals": [
                _feedback(FeedbackSignalKind.MISSING_EVIDENCE),
                _feedback(FeedbackSignalKind.CONTRADICTION),
            ],
            "evidence_refs": ["ev_alpha"],
            "receipt_refs": ["receipt_alpha"],
            "final_packet": {"safe_summary": "Final packet safe summary.", "risk_flags": ["medium"]},
            "root_authority_summary": "Root authority remains unchanged.",
            "delegated_lane_summary": "No delegated lane active.",
            "risk_flags": ["medium"],
            "open_questions": ["Which evidence is current?"],
            "current_time": NOW,
        }
    ).slot_set


def _retrieval_result():
    return SafeMemoryRetriever().retrieve(
        query=MemoryRetrievalQuery(
            mission_id="mission_replay",
            validity_scope="mission_replay",
            query_text="alpha mission",
            current_time=NOW,
        ),
        memory_entries=[_entry()],
        memory_snapshot=_snapshot(),
        hot_context_slot_set=_slot_set(),
        feedback_signals=[_feedback()],
        evidence_refs=["ev_alpha"],
        receipt_refs=["receipt_alpha"],
    )


def _replay_input(**updates: Any) -> MemoryReplayBuildInput:
    base = {
        "mission_id": "mission_replay",
        "loop_id": "role_loop_replay",
        "role_loop_receipts": [
            {
                "role_id": "visionary",
                "receipt_hash": "role_receipt_hash",
                "evidence_refs": ["ev_alpha"],
                "safe_summary": "Visionary receipt recorded safely.",
            }
        ],
        "proposal_receipts": [
            {
                "proposal_id": "proposal_alpha",
                "proposal_hash": "proposal_hash",
                "evidence_refs": ["ev_alpha"],
                "receipt_refs": ["proposal_receipt_alpha"],
                "risk_class": "medium",
                "safe_summary": "Proposal receipt recorded safely.",
            }
        ],
        "proposal_artifacts": [
            {
                "proposal_id": "proposal_alpha",
                "artifact_kind": "mission_plan",
                "evidence_refs": ["ev_alpha"],
                "safe_summary": "Mission plan proposal remains non-executing.",
            }
        ],
        "evidence_verification_results": [
            {
                "verdict": "MISSING_EVIDENCE",
                "evidence_refs": ["ev_alpha"],
                "missing_evidence": ["ev_missing"],
                "contradiction_refs": ["contra_alpha"],
                "safe_summary": "Verifier preserved missing evidence.",
            }
        ],
        "memory_entries": [_entry()],
        "memory_snapshot": _snapshot(),
        "feedback_signals": [
            _feedback(FeedbackSignalKind.MISSING_EVIDENCE),
            _feedback(FeedbackSignalKind.CONTRADICTION),
            _feedback(FeedbackSignalKind.BLOCKED_INTENT),
        ],
        "hot_context_slot_set": _slot_set(),
        "memory_retrieval_result": _retrieval_result(),
        "budget_summaries": [{"budget_id": "budget_alpha", "compliant": False, "decision": "budget_exhausted"}],
        "risk_flags": ["medium"],
        "unresolved_objections": ["Critic objection remains open."],
        "missing_evidence": ["ev_missing"],
        "future_gate_decision_refs": ["gate_future_1"],
        "future_finalgate_refs": ["finalgate_future_1"],
        "current_time": NOW,
    }
    base.update(updates)
    return MemoryReplayBuildInput(**base)


def _build_replay(**updates: Any):
    return MemoryReplayBuilder().build(_replay_input(**updates))


def _checkpoint(**updates: Any) -> MissionCheckpoint:
    base = {
        "checkpoint_id": "checkpoint_alpha",
        "mission_id": "mission_replay",
        "checkpoint_kind": MissionCheckpointKind.MEMORY_SNAPSHOT,
        "checkpoint_status": MissionCheckpointStatus.ACTIVE,
        "created_at": NOW,
        "expires_at": NOW + timedelta(hours=1),
        "source_refs": ["memory_snapshot"],
        "evidence_refs": ["ev_alpha"],
        "receipt_refs": ["receipt_alpha"],
        "memory_snapshot_ref": "snapshot_alpha",
        "replay_event_refs": ["event_alpha"],
        "proposal_refs": ["proposal_alpha"],
        "contradiction_refs": ["contra_alpha"],
        "budget_summary_ref": "budget_alpha",
        "risk_flags": ["medium"],
        "safe_summary": "Checkpoint is a historical marker only.",
        "rollback_posture_summary": "Rollback posture is descriptive only.",
    }
    base.update(updates)
    return MissionCheckpoint(**base)


def _checkpoint_input(**updates: Any) -> MissionCheckpointBuildInput:
    base = {
        "mission_id": "mission_replay",
        "checkpoints": [_checkpoint()],
        "current_time": NOW,
    }
    base.update(updates)
    return MissionCheckpointBuildInput(**base)


def _build_checkpoints(**updates: Any):
    return MissionCheckpointBuilder().build(_checkpoint_input(**updates))


def _event_kinds(result) -> list[MemoryReplayEventKind]:
    return [event.event_kind for event in result.timeline.events]


def test_memory_replay_builds_timeline_from_safe_memory_outputs() -> None:
    result = _build_replay()

    assert result.safety_validation.valid is True
    assert result.timeline.events
    assert MemoryReplayEventKind.MEMORY_ENTRY_CREATED in _event_kinds(result)
    assert MemoryReplayEventKind.MEMORY_RETRIEVAL_RESULT_RECORDED in _event_kinds(result)


def test_memory_replay_orders_events_deterministically() -> None:
    first = _build_replay()
    second = _build_replay()

    assert [event.event_id for event in first.timeline.events] == [
        event.event_id for event in second.timeline.events
    ]
    assert [event.sequence_index for event in first.timeline.events] == list(range(len(first.timeline.events)))


def test_memory_replay_preserves_receipt_refs() -> None:
    result = _build_replay()

    all_receipts = {ref for event in result.timeline.events for ref in event.receipt_refs}
    assert {"receipt_alpha", "proposal_receipt_alpha"} <= all_receipts


def test_memory_replay_preserves_evidence_refs() -> None:
    result = _build_replay()

    all_evidence = {ref for event in result.timeline.events for ref in event.evidence_refs}
    assert "ev_alpha" in all_evidence


def test_memory_replay_preserves_contradictions() -> None:
    result = _build_replay()

    assert "contra_alpha" in result.timeline.contradiction_refs
    assert result.timeline.contradiction_count >= 1


def test_memory_replay_preserves_missing_evidence() -> None:
    result = _build_replay()

    assert result.timeline.missing_evidence_count >= 1
    assert MemoryReplayEventKind.MISSING_EVIDENCE_RECORDED in _event_kinds(result)


def test_memory_replay_timeline_hash_is_deterministic() -> None:
    assert _build_replay().timeline.timeline_hash == _build_replay().timeline.timeline_hash


def test_memory_replay_rejects_raw_prompt_response_reasoning_or_key() -> None:
    result = _build_replay(
        risk_flags=["medium"],
        unresolved_objections=[
            {"raw_prompt": "do not store", "raw_response": "provider body", "reasoning": "private", "api_key": "not-real"}
        ],
    )

    assert result.safety_validation.valid is False
    assert result.timeline.events == []


def test_memory_replay_rejects_hidden_tool_or_organ_payload() -> None:
    result = _build_replay(risk_flags=[{"nested": {"tool_calls": [{"name": "browser_submit"}]}}])

    assert result.safety_validation.valid is False
    assert result.timeline.events == []


def test_memory_replay_rejects_secret_or_bearer_payload() -> None:
    fake_bearer = "Bearer " + "abcdefghijklmnop123456"
    result = _build_replay(unresolved_objections=[{"diagnostic": fake_bearer}])

    assert result.safety_validation.valid is False
    assert result.timeline.events == []


def test_memory_replay_rejects_authority_expansion_payload() -> None:
    result = _build_replay(unresolved_objections=[{"authority_expansion": "expand"}])

    assert result.safety_validation.valid is False
    assert "forbidden_replay_payload" in result.safety_validation.reasons


def test_memory_replay_rejects_restore_or_rollback_execution_payload() -> None:
    result = _build_replay(unresolved_objections=[{"restore_now": True, "rollback_now": True, "revert_files": True}])

    assert result.safety_validation.valid is False
    assert result.timeline.events == []


def test_memory_replay_cannot_grant_authority() -> None:
    payload = _build_replay().timeline.events[0].model_dump(mode="python")
    payload["can_grant_authority"] = True
    with pytest.raises(ValidationError):
        MemoryReplayEvent(**payload)


def test_memory_replay_cannot_approve_execution() -> None:
    payload = _build_replay().timeline.events[0].model_dump(mode="python")
    payload["can_approve_execution"] = True
    with pytest.raises(ValidationError):
        MemoryReplayEvent(**payload)


def test_memory_replay_cannot_create_delegated_lane() -> None:
    payload = _build_replay().timeline.events[0].model_dump(mode="python")
    payload["can_create_delegated_lane"] = True
    with pytest.raises(ValidationError):
        MemoryReplayEvent(**payload)


def test_memory_replay_cannot_override_provider_backend_model() -> None:
    payload = _build_replay().timeline.events[0].model_dump(mode="python")
    payload["can_override_provider_model"] = True
    with pytest.raises(ValidationError):
        MemoryReplayEvent(**payload)


def test_checkpoint_is_authority_neutral() -> None:
    checkpoint = _build_checkpoints().checkpoint_set.checkpoints[0]

    assert checkpoint.authority_effect == "none"
    assert checkpoint.execution_effect == "none"
    assert checkpoint.data_not_instruction is True


def test_checkpoint_cannot_approve_execution() -> None:
    payload = _checkpoint().model_dump(mode="python")
    payload["can_approve_execution"] = True
    with pytest.raises(ValidationError):
        MissionCheckpoint(**payload)


def test_checkpoint_cannot_restore_or_revert_workspace() -> None:
    result = _build_checkpoints(checkpoints=[_checkpoint().model_dump(mode="python") | {"restore_now": True}])

    assert result.safety_validation.valid is False
    assert result.checkpoint_set.checkpoints == []


def test_checkpoint_cannot_create_delegated_lane() -> None:
    payload = _checkpoint().model_dump(mode="python")
    payload["can_create_delegated_lane"] = True
    with pytest.raises(ValidationError):
        MissionCheckpoint(**payload)


def test_checkpoint_ttl_expired_becomes_historical_only() -> None:
    expired = _checkpoint(
        checkpoint_id="checkpoint_expired",
        expires_at=NOW - timedelta(seconds=1),
        checkpoint_status=MissionCheckpointStatus.ACTIVE,
    )
    result = _build_checkpoints(checkpoints=[expired])

    checkpoint = result.checkpoint_set.checkpoints[0]
    assert checkpoint.checkpoint_status is MissionCheckpointStatus.HISTORICAL_ONLY
    assert checkpoint.is_expired is True
    assert checkpoint.is_historical_only is True


def test_checkpoint_supersession_preserves_audit_trail() -> None:
    superseded = _checkpoint(
        checkpoint_id="checkpoint_old",
        checkpoint_status=MissionCheckpointStatus.SUPERSEDED,
        superseded_by_checkpoint_ref="checkpoint_new",
        supersession_refs=["checkpoint_new"],
    )
    result = _build_checkpoints(checkpoints=[superseded])

    checkpoint = result.checkpoint_set.checkpoints[0]
    assert checkpoint.checkpoint_status is MissionCheckpointStatus.SUPERSEDED
    assert checkpoint.supersession_refs == ["checkpoint_new"]


def test_replay_rendering_is_data_not_instruction() -> None:
    rendered = render_replay_as_untrusted_context(_build_replay().timeline)

    assert "not instructions, not authority, not proof, and not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_checkpoint_rendering_is_data_not_instruction() -> None:
    rendered = render_checkpoint_as_untrusted_context(_build_checkpoints().checkpoint_set)

    assert "not instructions, not authority, not proof, and not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_replay_does_not_inject_memory_into_role_prompts() -> None:
    client = RecordingRoleModelClient()
    LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert [call.mission_memory_refs for call in client.calls] == [
        ["pre_existing_memory_ref"],
        ["pre_existing_memory_ref"],
    ]


def test_replay_does_not_change_selected_model_contract() -> None:
    client = RecordingRoleModelClient()
    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.role_outputs
    assert {(output.provider_id, output.backend_id, output.model_id) for output in result.role_outputs} == {
        ("groq", "groq_openai_compatible_chat", "openai/gpt-oss-20b")
    }


def test_replay_does_not_change_agent_runtime_default_behavior() -> None:
    assert "memory_replay" not in signature(AgentRuntime.__init__).parameters
    assert "checkpoint" not in signature(AgentRuntime.__init__).parameters
