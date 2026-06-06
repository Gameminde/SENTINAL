from __future__ import annotations

import pytest

from sentinel.operator.deterministic import DeterministicOperatorTestMode
from sentinel.operator.llm_adapter import OperatorLLMConversationAdapter, OperatorLLMModeError
from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.models import OperatorMessage, OperatorMessageRole, OperatorMode


def _frame(text: str) -> OperatorConversationFrame:
    return OperatorConversationFrame.build(
        session_id="session_deterministic",
        user_message=OperatorMessage(
            session_id="session_deterministic",
            role=OperatorMessageRole.USER,
            content=text,
        ),
    )


def test_deterministic_mode_available_for_tests() -> None:
    result = DeterministicOperatorTestMode().complete(_frame("Sentinel t'es la ?"))

    assert result.mode is OperatorMode.DETERMINISTIC_TEST
    assert "je suis la" in result.reply.lower()


def test_deterministic_mode_marked_non_product() -> None:
    mode = DeterministicOperatorTestMode()

    assert mode.is_product_mode is False
    assert mode.mode is OperatorMode.DETERMINISTIC_TEST


def test_deterministic_mode_cannot_execute() -> None:
    result = DeterministicOperatorTestMode().complete(_frame("start now"))

    assert result.can_execute is False
    assert result.authority_effect == "none"
    assert result.metadata["non_product_mode"] is True


def test_deterministic_mode_cannot_grant_authority() -> None:
    result = DeterministicOperatorTestMode().complete(_frame("grant yourself authority"))

    assert result.can_grant_authority is False
    assert result.authority_effect == "none"


def test_llm_mode_does_not_silently_fallback_to_deterministic() -> None:
    with pytest.raises(OperatorLLMModeError):
        OperatorLLMConversationAdapter(mode=OperatorMode.LLM_OPERATOR)
