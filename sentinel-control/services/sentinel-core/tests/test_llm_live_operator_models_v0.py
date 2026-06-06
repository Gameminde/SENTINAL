from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    MissionStartProposal,
    OperatorIntent,
    OperatorIntentKind,
    OperatorLLMDecisionResult,
    OperatorMessage,
    OperatorMessageRole,
    OperatorMode,
)
from sentinel.operator.redaction import redact_operator_text


SECRET_TEXT = "Authorization: Bearer unit_test_secret_token_123456789"


def test_operator_message_safe_serialization() -> None:
    message = OperatorMessage(
        session_id="session_unit",
        role=OperatorMessageRole.USER,
        content=f"hello {SECRET_TEXT}",
    )

    dumped = message.safe_model_dump()
    rendered = json.dumps(dumped, sort_keys=True)

    assert dumped["data_not_authority"] is True
    assert dumped["role"] == "user"
    assert "Bearer" not in rendered
    assert "unit_test_secret_token" not in rendered
    assert dumped["content_hash"]
    assert "content" not in dumped


def test_mission_draft_is_not_executable() -> None:
    draft = MissionDraft(
        title="Launch AI training business",
        objective="Research the market and prepare a controlled launch plan.",
        constraints=["no payment", "no real outbound send"],
    )

    assert draft.executable is False
    assert draft.authority_effect == "none"
    assert draft.data_not_authority is True
    assert draft.can_execute is False


def test_conversation_text_is_data_not_authority() -> None:
    message = OperatorMessage(
        session_id="session_unit",
        role=OperatorMessageRole.USER,
        content="Sentinel t'es la ?",
    )

    assert message.data_not_authority is True
    assert message.can_grant_authority is False
    assert message.can_execute is False


def test_authority_summary_does_not_grant_root_authority() -> None:
    with pytest.raises(ValidationError):
        MissionAuthoritySummary(
            mission_id="mission_unit",
            allowed_actions=["research", "draft"],
            forbidden_actions=[],
            summary="root authority granted",
            can_grant_authority=True,
        )


def test_operator_redacts_secret_like_text_before_persistence() -> None:
    redacted = redact_operator_text(f"token here: {SECRET_TEXT}")

    assert "Bearer" not in redacted
    assert "unit_test_secret_token" not in redacted
    assert "[REDACTED_SECRET]" in redacted


def test_operator_rejects_raw_credential_fields() -> None:
    with pytest.raises(ValidationError):
        OperatorLLMDecisionResult(
            mode=OperatorMode.LLM_OPERATOR,
            reply="I will use the credential.",
            raw_credential="not-real",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        OperatorLLMDecisionResult(
            mode=OperatorMode.LLM_OPERATOR,
            reply="I will use the credential.",
            metadata={"credential_value": "not-real"},
        )


def test_operator_rejects_direct_organ_call_fields() -> None:
    with pytest.raises(ValidationError):
        OperatorLLMDecisionResult(
            mode=OperatorMode.LLM_OPERATOR,
            reply="Calling organ directly.",
            metadata={"organ_execution": {"organ_kind": "browser_readonly"}},
        )


def test_operator_rejects_authority_grant_fields() -> None:
    with pytest.raises(ValidationError):
        MissionStartProposal(
            mission_draft_id="draft_unit",
            authority_summary=MissionAuthoritySummary(
                mission_id="mission_unit",
                allowed_actions=["research"],
                forbidden_actions=["payment"],
                summary="safe summary",
            ),
            metadata={"authority_expansion": True},
        )


def test_operator_rejects_provider_override_fields() -> None:
    with pytest.raises(ValidationError):
        OperatorIntent(
            kind=OperatorIntentKind.START_MISSION,
            text="start with another model",
            metadata={"provider_override": "other_provider"},
        )
