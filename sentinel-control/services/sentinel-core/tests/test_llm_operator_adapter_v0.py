from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.operator.llm_adapter import OperatorLLMConversationAdapter, OperatorLLMModeError
from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.models import OperatorMessage, OperatorMessageRole, OperatorMode


def _contract(
    *,
    provider_id: str = "local_openai",
    backend_id: str = "ollama_openai_compatible",
    model: str = "qwen3.5:9b",
) -> UserModelContract:
    return UserModelContract(
        selected_provider_id=provider_id,
        selected_backend_id=backend_id,
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name=model,
            context_window_tokens=32_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="operator_v0",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _frame() -> OperatorConversationFrame:
    return OperatorConversationFrame.build(
        session_id="session_adapter",
        user_message=OperatorMessage(
            session_id="session_adapter",
            role=OperatorMessageRole.USER,
            content="Je veux lancer un business de formation IA.",
        ),
    )


class RecordingOperatorModelClient:
    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.requests: list[RealModelRequest] = []

    def complete(self, request: RealModelRequest) -> dict[str, object]:
        self.requests.append(request)
        return self.output


def test_llm_mode_requires_explicit_user_model_contract() -> None:
    with pytest.raises(OperatorLLMModeError):
        OperatorLLMConversationAdapter(mode=OperatorMode.LLM_OPERATOR, model_client=RecordingOperatorModelClient({}))


def test_no_hidden_default_provider() -> None:
    contract = _contract(provider_id="user_selected_provider")
    client = RecordingOperatorModelClient(_valid_output())

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=client,
    ).complete(_frame())

    assert result.provider_id == "user_selected_provider"
    assert client.requests[0].provider_id == "user_selected_provider"
    assert client.requests[0].backend_id == contract.selected_backend_id
    assert client.requests[0].model_id == contract.selected_model


def test_no_provider_fallback_auto() -> None:
    contract = _contract(provider_id="explicit_provider")
    client = RecordingOperatorModelClient(_valid_output())

    OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=contract,
        model_client=client,
    ).complete(_frame())

    request_metadata = client.requests[0].serializable_metadata()
    rendered = json.dumps(request_metadata, sort_keys=True)
    assert "fallback" not in rendered.lower()
    assert "auto" not in rendered.lower()


def test_provider_backend_model_override_rejected() -> None:
    contract = _contract()
    client = RecordingOperatorModelClient(
        {
            **_valid_output(),
            "metadata": {"provider_override": "other_provider"},
        }
    )

    with pytest.raises(ValidationError):
        OperatorLLMConversationAdapter(
            mode=OperatorMode.LLM_OPERATOR,
            user_model_contract=contract,
            model_client=client,
        ).complete(_frame())


def test_valid_llm_output_creates_mission_draft_schema() -> None:
    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=RecordingOperatorModelClient(_valid_output()),
    ).complete(_frame())

    assert result.mode is OperatorMode.LLM_OPERATOR
    assert result.mission_draft is not None
    assert result.mission_draft.title == "AI training business launch"
    assert result.mission_draft.executable is False
    assert result.authority_summary is not None
    assert result.authority_summary.can_grant_authority is False


def test_invalid_llm_output_fails_closed() -> None:
    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=RecordingOperatorModelClient({"reply": 123}),
    ).complete(_frame())

    assert result.reply.startswith("I could not validate")
    assert result.mission_draft is None
    assert result.metadata["blocked_reason"] == "invalid_structured_output"


def test_llm_output_direct_organ_call_rejected() -> None:
    client = RecordingOperatorModelClient(
        {
            **_valid_output(),
            "metadata": {"organ_execution": {"organ_kind": "browser_readonly"}},
        }
    )

    with pytest.raises(ValidationError):
        OperatorLLMConversationAdapter(
            mode=OperatorMode.LLM_OPERATOR,
            user_model_contract=_contract(),
            model_client=client,
        ).complete(_frame())


def test_llm_output_authority_grant_rejected() -> None:
    client = RecordingOperatorModelClient(
        {
            **_valid_output(),
            "authority_summary": {
                "mission_id": "mission_llm",
                "allowed_actions": ["research"],
                "forbidden_actions": [],
                "summary": "I grant authority.",
                "can_grant_authority": True,
            },
        }
    )

    with pytest.raises(ValidationError):
        OperatorLLMConversationAdapter(
            mode=OperatorMode.LLM_OPERATOR,
            user_model_contract=_contract(),
            model_client=client,
        ).complete(_frame())


def test_raw_provider_response_not_persisted() -> None:
    client = RecordingOperatorModelClient(
        {
            **_valid_output(),
            "raw_provider_response": "raw text that must not persist",
        }
    )

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=client,
    ).complete(_frame())

    rendered = json.dumps(result.safe_model_dump(), sort_keys=True)
    assert "raw text that must not persist" not in rendered
    assert result.provider_response_hash


def test_raw_reasoning_not_persisted() -> None:
    client = RecordingOperatorModelClient(
        {
            **_valid_output(),
            "reasoning": "hidden chain of thought should not persist",
        }
    )

    result = OperatorLLMConversationAdapter(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=client,
    ).complete(_frame())

    rendered = json.dumps(result.safe_model_dump(), sort_keys=True)
    assert "hidden chain of thought" not in rendered
    assert result.reasoning_hash


def _valid_output() -> dict[str, object]:
    return {
        "reply": "Tres bien. Je vais clarifier la mission avant de commencer.",
        "intent": {"kind": "draft_mission", "text": "launch AI training business"},
        "mission_draft": {
            "title": "AI training business launch",
            "objective": "Research the target market and prepare launch artifacts.",
            "constraints": ["no payment", "no real outbound send"],
            "expected_artifacts": ["market summary", "launch plan"],
        },
        "authority_summary": {
            "mission_id": "mission_llm",
            "allowed_actions": ["research", "draft", "create_report"],
            "forbidden_actions": ["payment", "send_email"],
            "summary": "Research and drafting only; no external send or payment.",
        },
    }
