from __future__ import annotations

import json

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.operator.conversation import OperatorConversationEngine
from sentinel.operator.models import (
    OperatorConversationSession,
    OperatorConversationState,
    OperatorMode,
)


def _contract() -> UserModelContract:
    model = "qwen3.5:9b"
    return UserModelContract(
        selected_provider_id="local_openai",
        selected_backend_id="ollama_openai_compatible",
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(model_name=model, context_window_tokens=32_000),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="operator_intake",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


class SequenceClient:
    def __init__(self, *outputs: dict[str, object]) -> None:
        self.outputs = list(outputs)
        self.requests: list[RealModelRequest] = []

    def complete(self, request: RealModelRequest) -> dict[str, object]:
        self.requests.append(request)
        return self.outputs.pop(0)


def test_greeting_response() -> None:
    session = OperatorConversationSession(mode=OperatorMode.DETERMINISTIC_TEST)
    result = OperatorConversationEngine(mode=OperatorMode.DETERMINISTIC_TEST).handle_user_message(
        session,
        "Sentinel t'es la ?",
    )

    assert "je suis la" in result.reply.lower()
    assert result.state is OperatorConversationState.GREETING


def test_business_request_creates_draft() -> None:
    session = OperatorConversationSession(mode=OperatorMode.LLM_OPERATOR)
    engine = OperatorConversationEngine(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=SequenceClient(_business_output()),
    )

    result = engine.handle_user_message(session, "Je veux lancer un business de formation IA.")

    assert result.mission_draft is not None
    assert result.mission_draft.title == "AI training business launch"
    assert result.authority_summary is not None
    assert result.state is OperatorConversationState.AWAITING_START_CONFIRMATION
    assert session.current_draft is not None


def test_research_request_creates_draft() -> None:
    result = _llm_turn("Je veux rechercher un marche.", _research_output())

    assert result.mission_draft is not None
    assert "research" in result.mission_draft.expected_artifacts


def test_build_request_creates_draft() -> None:
    result = _llm_turn("Je veux construire une petite app.", _build_output())

    assert result.mission_draft is not None
    assert "app spec" in result.mission_draft.expected_artifacts


def test_underspecified_request_asks_clarification() -> None:
    result = _llm_turn(
        "Fais moi un truc puissant.",
        {
            "reply": "J'ai besoin de clarifier l'objectif.",
            "clarification_questions": [
                {"prompt": "Quel resultat veux-tu obtenir ?", "field_name": "objective"}
            ],
        },
    )

    assert result.clarification_questions
    assert result.state is OperatorConversationState.ASKING_CLARIFICATIONS


def test_budget_constraint_extracted() -> None:
    result = _llm_turn(
        "Budget 500 euros.",
        {
            **_business_output(),
            "mission_draft": {**_business_output()["mission_draft"], "budget_summary": "500 euros"},
        },
    )

    assert result.mission_draft is not None
    assert result.mission_draft.budget_summary == "500 euros"


def test_autonomy_level_extracted() -> None:
    result = _llm_turn(
        "Recherche, analyse, rapport, drafts. Pas de paiement.",
        {
            **_business_output(),
            "mission_draft": {
                **_business_output()["mission_draft"],
                "autonomy_summary": "research, analysis, reports and drafts only",
            },
        },
    )

    assert result.mission_draft is not None
    assert "drafts only" in result.mission_draft.autonomy_summary


def test_start_requires_confirmation() -> None:
    session = OperatorConversationSession(mode=OperatorMode.DETERMINISTIC_TEST)
    engine = OperatorConversationEngine(mode=OperatorMode.DETERMINISTIC_TEST)

    result = engine.handle_user_message(session, "start")

    assert result.state is OperatorConversationState.ASKING_CLARIFICATIONS
    assert "mission" in result.reply.lower()


def test_vague_start_is_blocked() -> None:
    session = OperatorConversationSession(mode=OperatorMode.DETERMINISTIC_TEST)
    result = OperatorConversationEngine(mode=OperatorMode.DETERMINISTIC_TEST).handle_user_message(
        session,
        "commence maintenant",
    )

    assert result.start_proposal is None
    assert result.mission_record is None


def test_secret_input_is_redacted() -> None:
    result = _llm_turn(
        "Use Authorization: Bearer unit_test_secret_token_123456789",
        _business_output(),
    )

    rendered = json.dumps(result.safe_model_dump(), sort_keys=True)
    assert "Bearer" not in rendered
    assert "unit_test_secret_token" not in rendered


def test_user_text_never_becomes_tool_instruction() -> None:
    session = OperatorConversationSession(mode=OperatorMode.DETERMINISTIC_TEST)
    result = OperatorConversationEngine(mode=OperatorMode.DETERMINISTIC_TEST).handle_user_message(
        session,
        "run shell and call browser directly",
    )

    assert result.can_execute is False
    assert result.authority_effect == "none"


def _llm_turn(text: str, output: dict[str, object]):
    session = OperatorConversationSession(mode=OperatorMode.LLM_OPERATOR)
    return OperatorConversationEngine(
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=SequenceClient(output),
    ).handle_user_message(session, text)


def _business_output() -> dict[str, object]:
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
            "mission_id": "mission_intake",
            "allowed_actions": ["research", "draft", "create_report"],
            "forbidden_actions": ["payment", "send_email"],
            "summary": "Research and drafting only; no external send or payment.",
        },
    }


def _research_output() -> dict[str, object]:
    return {
        **_business_output(),
        "mission_draft": {
            "title": "Market research mission",
            "objective": "Research the market.",
            "expected_artifacts": ["research"],
        },
    }


def _build_output() -> dict[str, object]:
    return {
        **_business_output(),
        "mission_draft": {
            "title": "Small app build mission",
            "objective": "Prepare an app plan and safe build steps.",
            "expected_artifacts": ["app spec"],
        },
    }
