from __future__ import annotations

from typing import Any

from sentinel.agent.llm import (
    LLMRoleContract,
    LLMRoleId,
    LLMRoleLoopOrchestrator,
    LLMRoleLoopPlan,
    LLMRoleOutput,
    RoleLoopStatus,
    build_default_llm_role_contracts,
)
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution import ModelExecutionBudgetLedger


SECRET_VALUE = "unit-test-role-loop-token-not-real"
RAW_PROMPT_FRAGMENT = "raw role prompt " + SECRET_VALUE


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
            content=payload.get("content", _safe_content(frame.role_id)),
            evidence_refs=payload.get("evidence_refs", ["ev_direct"]),
            proposal_artifacts=payload.get("proposal_artifacts", []),
            action_candidates=payload.get("action_candidates", []),
            uncertainty=payload.get("uncertainty", []),
            objections=payload.get("objections", []),
            input_tokens=payload.get("input_tokens", 12),
            output_tokens=payload.get("output_tokens", 8),
        )


def _safe_content(role_id: LLMRoleId) -> dict[str, Any]:
    if role_id is LLMRoleId.VISIONARY:
        return {"strategies": ["community wedge", "agent ops wedge", "evidence product wedge"]}
    if role_id is LLMRoleId.CRITIC:
        return {"objections": ["evidence may be thin"], "blocking_weakness": False}
    if role_id is LLMRoleId.VERIFIER:
        return {"uncertainty": ["market proof still partial"], "evidence_refs": ["ev_direct"]}
    if role_id is LLMRoleId.OPERATOR_PLANNER:
        return {"proposal_only": True, "candidate_count": 1}
    if role_id is LLMRoleId.CODER_ADVISOR:
        return {"patch_plan": ["add tests", "implement bounded loop"], "file_mutation": False}
    return {"summary": f"{role_id.value} completed safely"}


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
            expected_quality="strict_single_model_role_loop",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _plan(**updates: Any) -> LLMRoleLoopPlan:
    base = {
        "mission_id": "mission_role_loop",
        "mission_goal": "Design Sentinel's first strict single-model role loop.",
        "user_model_contract": _model_contract(),
        "available_evidence_refs": ["ev_direct", "receipt_1"],
        "mission_memory_refs": ["receipt_1"],
        "per_role_input_token_estimate": 120,
        "per_role_output_token_estimate": 80,
        "raw_prompt_in_memory_only": RAW_PROMPT_FRAGMENT,
    }
    base.update(updates)
    return LLMRoleLoopPlan(**base)


def test_strict_role_loop_uses_same_provider_backend_model_for_all_roles() -> None:
    client = RecordingRoleModelClient()
    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.status is RoleLoopStatus.COMPLETED
    assert [call.selected_provider_id for call in client.calls] == ["groq"] * len(client.calls)
    assert [call.selected_backend_id for call in client.calls] == ["groq_openai_compatible_chat"] * len(client.calls)
    assert [call.selected_model for call in client.calls] == ["openai/gpt-oss-20b"] * len(client.calls)
    assert {output.provider_id for output in result.role_outputs} == {"groq"}
    assert {output.backend_id for output in result.role_outputs} == {"groq_openai_compatible_chat"}
    assert {output.model_id for output in result.role_outputs} == {"openai/gpt-oss-20b"}


def test_role_loop_rejects_role_provider_override() -> None:
    client = RecordingRoleModelClient()
    contracts = build_default_llm_role_contracts()
    contracts[LLMRoleId.STRATEGIST] = contracts[LLMRoleId.STRATEGIST].model_copy(update={"provider_id": "openrouter"})

    result = LLMRoleLoopOrchestrator(role_model_client=client, role_contracts=contracts).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.STRATEGIST
    assert len(client.calls) == 1
    assert result.blocked_reason == "role_provider_override_rejected"


def test_role_loop_rejects_role_backend_override() -> None:
    client = RecordingRoleModelClient()
    contracts = build_default_llm_role_contracts()
    contracts[LLMRoleId.RESEARCHER] = contracts[LLMRoleId.RESEARCHER].model_copy(update={"backend_id": "other_backend"})

    result = LLMRoleLoopOrchestrator(role_model_client=client, role_contracts=contracts).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.RESEARCHER
    assert result.blocked_reason == "role_backend_override_rejected"


def test_role_loop_rejects_role_model_override() -> None:
    client = RecordingRoleModelClient()
    contracts = build_default_llm_role_contracts()
    contracts[LLMRoleId.PLANNER] = contracts[LLMRoleId.PLANNER].model_copy(update={"model_id": "other/model"})

    result = LLMRoleLoopOrchestrator(role_model_client=client, role_contracts=contracts).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.PLANNER
    assert result.blocked_reason == "role_model_override_rejected"


def test_role_loop_stops_when_budget_exhausted() -> None:
    ledger = ModelExecutionBudgetLedger(mission_id="mission_role_loop", max_mission_total_tokens=150)

    result = LLMRoleLoopOrchestrator(
        role_model_client=RecordingRoleModelClient(),
        budget_ledger=ledger,
    ).run(_plan())

    assert result.status is RoleLoopStatus.LOOP_BUDGET_EXHAUSTED
    assert result.blocked_reason == "mission_total_tokens_exhausted"
    assert result.budget_summary.compliant is False


def test_role_loop_receipts_do_not_store_raw_prompt_response_reasoning_or_key() -> None:
    result = LLMRoleLoopOrchestrator(role_model_client=RecordingRoleModelClient()).run(_plan())

    dumped = result.model_dump_json()
    assert RAW_PROMPT_FRAGMENT not in dumped
    assert SECRET_VALUE not in dumped
    assert "raw_prompt" not in dumped
    assert "raw_response" not in dumped
    assert "reasoning_details" not in dumped
    assert "hidden_action_payload" not in dumped


def test_role_loop_rejects_nested_tool_or_organ_intent() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.PLANNER: {
                "content": {"nested": {"tool_calls": [{"name": "browser_submit"}]}},
            }
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.PLANNER
    assert result.blocked_reason == "forbidden_model_output_intent"


def test_role_consensus_cannot_create_authority() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.SYNTHESIZER: {
                "content": {"role_consensus": "approved", "authority_grant": {"allow_send": True}},
            }
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.SYNTHESIZER
    assert result.blocked_reason == "forbidden_model_output_intent"


def test_critic_output_cannot_approve_execution() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.CRITIC: {
                "content": {"approve_execution": True, "objections": []},
            }
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.CRITIC
    assert result.blocked_reason == "role_cannot_approve_execution"


def test_verifier_pass_cannot_execute_action() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.VERIFIER: {
                "content": {"verified": True, "execute_action": {"send": "now"}},
            }
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(_plan())

    assert result.status is RoleLoopStatus.ROLE_REJECTED
    assert result.blocked_role_id is LLMRoleId.VERIFIER
    assert result.blocked_reason == "forbidden_model_output_intent"


def test_operator_planner_outputs_proposal_only() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.OPERATOR_PLANNER: {
                "action_candidates": [
                    {
                        "organ": "browser",
                        "action": "click",
                        "execution_effect": "proposal_only",
                        "creates_delegated_lane": False,
                    }
                ]
            }
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(
        _plan(role_sequence=[LLMRoleId.OPERATOR_PLANNER])
    )

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.proposal_artifacts == []
    assert result.action_candidates[0]["execution_effect"] == "proposal_only"


def test_coder_advisor_outputs_patch_plan_not_file_mutation() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.CODER_ADVISOR: {
                "content": {"patch_plan": ["edit safely"], "file_mutation": False},
                "proposal_artifacts": [{"kind": "patch_plan", "files": ["sentinel/agent/llm/role_loop.py"]}],
            }
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(
        _plan(role_sequence=[LLMRoleId.CODER_ADVISOR])
    )

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.proposal_artifacts[0]["kind"] == "patch_plan"
    assert result.action_candidates == []


def test_visionary_can_generate_multiple_strategies_within_budget() -> None:
    result = LLMRoleLoopOrchestrator(role_model_client=RecordingRoleModelClient()).run(
        _plan(role_sequence=[LLMRoleId.VISIONARY])
    )

    assert result.status is RoleLoopStatus.COMPLETED
    assert len(result.role_outputs[0].content["strategies"]) == 3
    assert result.budget_summary.compliant is True


def test_role_loop_final_packet_preserves_uncertainty_and_objections() -> None:
    client = RecordingRoleModelClient(
        {
            LLMRoleId.CRITIC: {"content": {"objections": ["weak proof"]}, "objections": ["weak proof"]},
            LLMRoleId.VERIFIER: {"content": {"uncertainty": ["needs live evidence"]}, "uncertainty": ["needs live evidence"]},
            LLMRoleId.SYNTHESIZER: {"content": {"summary": "safe packet"}},
        }
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(
        _plan(role_sequence=[LLMRoleId.CRITIC, LLMRoleId.VERIFIER, LLMRoleId.SYNTHESIZER])
    )

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.final_packet["objections"] == ["weak proof"]
    assert result.final_packet["uncertainty"] == ["needs live evidence"]

