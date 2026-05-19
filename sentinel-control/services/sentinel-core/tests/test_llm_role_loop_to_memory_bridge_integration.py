from __future__ import annotations

from inspect import signature
from typing import Any

from sentinel.agent.llm import (
    DelegatedActionLevel,
    FeedbackSignalKind,
    LLMRoleId,
    LLMRoleLoopOrchestrator,
    LLMRoleLoopPlan,
    LLMRoleOutput,
    ProposalArtifactKind,
    RoleLoopMemoryBridge,
    RoleLoopStatus,
)
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution import ModelExecutionBudgetLedger
from sentinel.agent.runtime import AgentRuntime


SECRET_FRAGMENT = "unit-test-role-memory-secret-not-real"
RAW_PROMPT_FRAGMENT = "raw role-memory prompt " + SECRET_FRAGMENT


class RecordingRoleModelClient:
    def __init__(self, outputs: dict[LLMRoleId, dict[str, Any]] | None = None) -> None:
        self.outputs = outputs or {}
        self.calls: list[Any] = []

    def complete_role(self, frame) -> LLMRoleOutput:
        self.calls.append(frame)
        payload = self.outputs.get(frame.role_id, {})
        return LLMRoleOutput(
            role_id=frame.role_id,
            provider_id=frame.selected_provider_id,
            backend_id=frame.selected_backend_id,
            model_id=frame.selected_model,
            content=payload.get("content", {"summary": f"{frame.role_id.value} safe output"}),
            evidence_refs=payload.get("evidence_refs", ["ev_direct"]),
            proposal_artifacts=payload.get("proposal_artifacts", []),
            action_candidates=payload.get("action_candidates", []),
            uncertainty=payload.get("uncertainty", []),
            objections=payload.get("objections", []),
            input_tokens=payload.get("input_tokens", 8),
            output_tokens=payload.get("output_tokens", 6),
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
            expected_quality="role_loop_memory_bridge",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _plan(**updates: Any) -> LLMRoleLoopPlan:
    base = {
        "mission_id": "mission_role_loop_memory",
        "mission_goal": "Connect role-loop safe receipts to the memory bridge.",
        "user_model_contract": _model_contract(),
        "available_evidence_refs": ["ev_direct", "receipt_1", "ev_contra"],
        "mission_memory_refs": ["pre_existing_memory_ref"],
        "role_sequence": [LLMRoleId.VISIONARY, LLMRoleId.PLANNER, LLMRoleId.SYNTHESIZER],
        "per_role_input_token_estimate": 80,
        "per_role_output_token_estimate": 60,
        "raw_prompt_in_memory_only": RAW_PROMPT_FRAGMENT,
    }
    base.update(updates)
    return LLMRoleLoopPlan(**base)


def _proposal(**updates: Any) -> dict[str, Any]:
    base = {
        "proposal_id": "proposal_memory_1",
        "source_role_id": LLMRoleId.PLANNER.value,
        "mission_id": "mission_role_loop_memory",
        "objective_summary": "Create a safe proposal artifact.",
        "artifact_kind": ProposalArtifactKind.MISSION_PLAN.value,
        "action_level_candidate": DelegatedActionLevel.L1.value,
        "authority_class": "proposal_only",
        "risk_class": "low",
        "budget_estimate": {"model_tokens": 80},
        "evidence_refs": ["ev_direct"],
        "receipt_refs": ["receipt_1"],
        "expected_outcome": "A non-executing proposal.",
        "rollback_posture": "reject_proposal",
        "user_review_required": False,
        "uncertainty": [],
        "safe_summary": "Safe role-loop proposal.",
    }
    base.update(updates)
    return base


def _run_with_memory(
    outputs: dict[LLMRoleId, dict[str, Any]] | None = None,
    **plan_updates: Any,
):
    client = RecordingRoleModelClient(outputs)
    result = LLMRoleLoopOrchestrator(
        role_model_client=client,
        memory_bridge=RoleLoopMemoryBridge(),
    ).run(_plan(**plan_updates))
    return result, client


def _signal_kinds(result) -> set[FeedbackSignalKind]:
    return {signal.kind for signal in result.feedback_signals}


def test_role_loop_memory_bridge_default_off_preserves_existing_behavior() -> None:
    client = RecordingRoleModelClient()
    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.memory_bridge_result is None
    assert result.living_memory_snapshot is None
    assert result.feedback_signals == []
    assert result.memory_entry_refs == []


def test_role_loop_memory_bridge_explicitly_enabled_outputs_snapshot() -> None:
    result, _ = _run_with_memory()

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.memory_bridge_result is not None
    assert result.living_memory_snapshot is not None
    assert result.living_memory_snapshot.mission_id == "mission_role_loop_memory"
    assert result.memory_entry_refs


def test_role_loop_memory_bridge_ingests_role_receipts_safely() -> None:
    result, _ = _run_with_memory()

    assert result.memory_bridge_result is not None
    assert any(entry.source_class.value == "receipt" for entry in result.memory_bridge_result.memory_entries)
    dumped = result.memory_bridge_result.model_dump_json()
    assert RAW_PROMPT_FRAGMENT not in dumped
    assert SECRET_FRAGMENT not in dumped


def test_role_loop_memory_bridge_ingests_proposal_receipts_safely() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"proposal_artifacts": [_proposal()]}})

    assert result.memory_bridge_result is not None
    assert any(entry.source_class.value == "proposal_artifact" for entry in result.memory_bridge_result.memory_entries)


def test_role_loop_memory_bridge_ingests_evidence_verifier_results() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"proposal_artifacts": [_proposal()]}})

    assert result.final_packet["evidence_verification_summary"]["verdict"] == "SUPPORTED"
    assert result.memory_bridge_result is not None
    assert result.memory_bridge_result.safety_validation.valid is True


def test_role_loop_memory_bridge_rejects_raw_prompt_response_reasoning_or_key() -> None:
    result, _ = _run_with_memory(
        {
            LLMRoleId.PLANNER: {
                "content": {
                    "raw_prompt": "never store",
                    "raw_response": "provider body",
                    "reasoning": "private",
                    "api_key": "not-real",
                }
            }
        }
    )

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert FeedbackSignalKind.BLOCKED_INTENT in _signal_kinds(result)
    assert result.memory_bridge_result is not None
    assert result.memory_bridge_result.memory_entries == []


def test_role_loop_memory_bridge_rejects_hidden_tool_or_organ_payload() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"content": {"tool_calls": [{"name": "browser_submit"}]}}})

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert FeedbackSignalKind.BLOCKED_INTENT in _signal_kinds(result)


def test_role_loop_memory_bridge_cannot_grant_authority() -> None:
    result, _ = _run_with_memory()

    assert result.can_grant_authority is False
    assert result.memory_bridge_result is not None
    assert result.memory_bridge_result.can_grant_authority is False


def test_role_loop_memory_bridge_cannot_approve_execution() -> None:
    result, _ = _run_with_memory()

    assert result.can_approve_execution is False
    assert result.memory_bridge_result is not None
    assert result.memory_bridge_result.can_approve_execution is False


def test_role_loop_memory_bridge_cannot_create_delegated_lane() -> None:
    result, _ = _run_with_memory()

    assert result.can_create_delegated_lane is False
    assert result.memory_bridge_result is not None
    assert result.memory_bridge_result.can_create_delegated_lane is False


def test_role_loop_memory_bridge_cannot_override_provider_backend_model() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"content": {"provider_override": "other"}}})

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.can_override_provider_model is False
    assert FeedbackSignalKind.BLOCKED_INTENT in _signal_kinds(result)


def test_role_loop_memory_bridge_preserves_selected_model_contract() -> None:
    result, client = _run_with_memory()

    assert {call.selected_provider_id for call in client.calls} == {"groq"}
    assert {call.selected_backend_id for call in client.calls} == {"groq_openai_compatible_chat"}
    assert {call.selected_model for call in client.calls} == {"openai/gpt-oss-20b"}
    assert result.role_outputs[0].provider_id == "groq"
    assert result.role_outputs[0].backend_id == "groq_openai_compatible_chat"
    assert result.role_outputs[0].model_id == "openai/gpt-oss-20b"


def test_role_loop_memory_bridge_missing_evidence_creates_feedback_signal() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"proposal_artifacts": [_proposal(evidence_refs=[])]}})

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert FeedbackSignalKind.MISSING_EVIDENCE in _signal_kinds(result)


def test_role_loop_memory_bridge_contradiction_creates_feedback_signal() -> None:
    result, _ = _run_with_memory(
        {LLMRoleId.PLANNER: {"content": {"contradictions": [{"claim_id": "claim_1", "evidence_refs": ["ev_contra"]}]}}}
    )

    assert FeedbackSignalKind.CONTRADICTION in _signal_kinds(result)
    assert result.living_memory_snapshot is not None
    assert result.living_memory_snapshot.contradiction_count == 1


def test_role_loop_memory_bridge_budget_issue_creates_feedback_signal() -> None:
    ledger = ModelExecutionBudgetLedger(mission_id="mission_role_loop_memory", max_mission_total_tokens=100)
    result = LLMRoleLoopOrchestrator(
        role_model_client=RecordingRoleModelClient(),
        budget_ledger=ledger,
        memory_bridge=RoleLoopMemoryBridge(),
    ).run(_plan())

    assert result.status is RoleLoopStatus.LOOP_BUDGET_EXHAUSTED
    assert FeedbackSignalKind.BUDGET_EXHAUSTED in _signal_kinds(result)


def test_role_loop_memory_bridge_blocked_intent_creates_feedback_signal() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"content": {"execute_action": {"send": "now"}}}})

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert FeedbackSignalKind.BLOCKED_INTENT in _signal_kinds(result)


def test_role_loop_memory_bridge_self_generated_evidence_is_quarantined() -> None:
    result, _ = _run_with_memory({LLMRoleId.PLANNER: {"evidence_refs": []}})

    assert FeedbackSignalKind.SELF_GENERATED_EVIDENCE_QUARANTINED in _signal_kinds(result)


def test_role_loop_memory_bridge_duplicate_source_is_suppressed() -> None:
    result, _ = _run_with_memory(role_sequence=[LLMRoleId.VISIONARY, LLMRoleId.VISIONARY])

    assert FeedbackSignalKind.DUPLICATE_SOURCE_SUPPRESSED in _signal_kinds(result)


def test_role_loop_memory_bridge_snapshot_has_authority_effect_none() -> None:
    result, _ = _run_with_memory()

    assert result.living_memory_snapshot is not None
    assert result.living_memory_snapshot.authority_effect == "none"


def test_role_loop_memory_bridge_snapshot_has_execution_effect_none() -> None:
    result, _ = _run_with_memory()

    assert result.living_memory_snapshot is not None
    assert result.living_memory_snapshot.execution_effect == "none"


def test_role_loop_memory_bridge_does_not_inject_memory_into_prompts() -> None:
    _, client = _run_with_memory(role_sequence=[LLMRoleId.VISIONARY, LLMRoleId.STRATEGIST])

    assert [call.mission_memory_refs for call in client.calls] == [
        ["pre_existing_memory_ref"],
        ["pre_existing_memory_ref"],
    ]


def test_role_loop_memory_bridge_does_not_change_agent_runtime_default_behavior() -> None:
    runtime_params = signature(AgentRuntime.__init__).parameters

    assert "memory_bridge" not in runtime_params
