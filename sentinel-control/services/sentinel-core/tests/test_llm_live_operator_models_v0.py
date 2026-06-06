from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionClarificationQuestion,
    MissionDraft,
    MissionStartProposal,
    OperatorIntent,
    OperatorIntentKind,
    OperatorLLMDecisionResult,
    OperatorMessage,
    OperatorMessageRole,
    OperatorMode,
    OperatorConversationState,
    OperatorTurnResult,
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


def test_turn_result_safe_dump_redacts_mission_draft_text() -> None:
    draft = MissionDraft(
        title="Bearer secret_token_123456789",
        objective="API_KEY=secretvalue123456789",
        constraints=["cookie=sessionid_secret_123456789"],
    )
    turn = OperatorTurnResult(
        session_id="session_models",
        state=OperatorConversationState.DRAFTING_MISSION,
        reply="Draft ready",
        mission_draft=draft,
    )

    rendered = json.dumps(turn.safe_model_dump(), sort_keys=True)
    assert "secret_token" not in rendered
    assert "secretvalue" not in rendered
    assert "sessionid_secret" not in rendered


def test_llm_decision_safe_dump_redacts_all_structured_text() -> None:
    authority = MissionAuthoritySummary(
        mission_id="mission_models",
        allowed_actions=["research"],
        forbidden_actions=["payment"],
        summary="Do not leak Authorization: Bearer authority_secret_123456789",
    )
    decision = OperatorLLMDecisionResult(
        mode=OperatorMode.LLM_OPERATOR,
        reply="I saw cookie=sessionid_reply_123456789",
        intent=OperatorIntent(
            kind=OperatorIntentKind.DRAFT_MISSION,
            text="Use Bearer intent_secret_123456789",
        ),
        mission_draft=MissionDraft(
            title="Bearer draft_secret_123456789",
            objective="API_KEY=draftvalue123456789",
        ),
        clarification_questions=[
            MissionClarificationQuestion(
                prompt="What about Bearer question_secret_123456789?",
                field_name="API_KEY=fieldvalue123456789",
            )
        ],
        authority_summary=authority,
        start_proposal=MissionStartProposal(
            mission_draft_id="draft_models",
            authority_summary=authority,
        ),
    )

    rendered = json.dumps(decision.safe_model_dump(), sort_keys=True)

    assert "Bearer" not in rendered
    assert "API_KEY" not in rendered
    assert "cookie=sessionid" not in rendered
    assert "authority_secret" not in rendered
    assert "intent_secret" not in rendered
    assert "draft_secret" not in rendered
    assert "question_secret" not in rendered


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
