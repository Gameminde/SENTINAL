from __future__ import annotations

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.operator.deterministic import DeterministicOperatorTestMode
from sentinel.operator.llm_adapter import OperatorLLMConversationAdapter, OperatorModelClient
from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.models import (
    OperatorConversationSession,
    OperatorConversationState,
    OperatorIntent,
    OperatorIntentKind,
    OperatorMessage,
    OperatorMessageRole,
    OperatorMode,
    OperatorTurnResult,
)


class OperatorConversationEngine:
    def __init__(
        self,
        *,
        mode: OperatorMode,
        user_model_contract: UserModelContract | None = None,
        model_client: OperatorModelClient | None = None,
    ) -> None:
        self._mode = mode
        self._deterministic = DeterministicOperatorTestMode()
        self._llm_adapter = (
            OperatorLLMConversationAdapter(
                mode=mode,
                user_model_contract=user_model_contract,
                model_client=model_client,
            )
            if mode is OperatorMode.LLM_OPERATOR
            else None
        )

    def handle_user_message(
        self,
        session: OperatorConversationSession,
        text: str,
        *,
        persistent_memory_context: str | None = None,
    ) -> OperatorTurnResult:
        if _is_start_command(text) and session.current_draft is None:
            return _turn(
                session=session,
                state=OperatorConversationState.ASKING_CLARIFICATIONS,
                reply="J'ai besoin d'une mission claire avant de commencer.",
                intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text=text),
            )

        message = OperatorMessage(session_id=session.session_id, role=OperatorMessageRole.USER, content=text)
        try:
            frame = OperatorConversationFrame.build(
                session_id=session.session_id,
                user_message=message,
                current_draft=session.current_draft,
                persistent_memory_context=persistent_memory_context,
            )
        except ValueError:
            return _turn(
                session=session,
                state=OperatorConversationState.ASKING_CLARIFICATIONS,
                reply="Je ne peux pas traiter ce texte comme une instruction outil. Reformule l'objectif de mission.",
                intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text=message.safe_content),
            )

        decision = (
            self._deterministic.complete(frame)
            if self._mode is OperatorMode.DETERMINISTIC_TEST
            else self._llm_adapter.complete(frame)  # type: ignore[union-attr]
        )
        state = _state_from_decision(decision.intent.kind if decision.intent else None, bool(decision.clarification_questions), decision.mission_draft is not None, decision.authority_summary is not None)
        if decision.mission_draft is not None:
            session.current_draft = decision.mission_draft
        if decision.authority_summary is not None:
            session.current_authority_summary = decision.authority_summary
        session.state = state
        return OperatorTurnResult(
            session_id=session.session_id,
            state=state,
            reply=decision.reply,
            intent=decision.intent,
            mission_draft=decision.mission_draft,
            clarification_questions=decision.clarification_questions,
            authority_summary=decision.authority_summary,
            start_proposal=decision.start_proposal,
            metadata=decision.metadata,
        )


def _state_from_decision(
    intent: OperatorIntentKind | None,
    has_clarifications: bool,
    has_draft: bool,
    has_authority_summary: bool,
) -> OperatorConversationState:
    if intent is OperatorIntentKind.GREETING:
        return OperatorConversationState.GREETING
    if has_clarifications or intent is OperatorIntentKind.ASK_CLARIFICATION:
        return OperatorConversationState.ASKING_CLARIFICATIONS
    if has_draft and has_authority_summary:
        return OperatorConversationState.AWAITING_START_CONFIRMATION
    if has_draft:
        return OperatorConversationState.DRAFTING_MISSION
    return OperatorConversationState.UNDERSTANDING_REQUEST


def _turn(
    *,
    session: OperatorConversationSession,
    state: OperatorConversationState,
    reply: str,
    intent: OperatorIntent | None = None,
) -> OperatorTurnResult:
    session.state = state
    return OperatorTurnResult(session_id=session.session_id, state=state, reply=reply, intent=intent)


def _is_start_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"start", "commence", "commence maintenant", "go", "oui commence"}
