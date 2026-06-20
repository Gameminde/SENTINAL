from __future__ import annotations

from sentinel.operator.llm_frame import OperatorConversationFrame
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    OperatorIntent,
    OperatorIntentKind,
    OperatorLLMDecisionResult,
    OperatorMode,
)


class DeterministicOperatorTestMode:
    mode: OperatorMode = OperatorMode.DETERMINISTIC_TEST
    is_product_mode: bool = False

    def complete(self, frame: OperatorConversationFrame) -> OperatorLLMDecisionResult:
        text = frame.safe_user_message.lower()
        metadata = {"non_product_mode": True}

        if _is_greeting(text):
            return OperatorLLMDecisionResult(
                mode=self.mode,
                reply="Oui, je suis la. Qu'est-ce que tu veux faire ?",
                intent=OperatorIntent(kind=OperatorIntentKind.GREETING, text=frame.safe_user_message),
                metadata=metadata,
            )

        if "business" in text or "formation" in text or "launch" in text or "lancer" in text:
            draft = MissionDraft(
                title="Draft mission",
                objective="Clarify the user's goal and prepare a controlled mission draft.",
                constraints=["no payment", "no real outbound send"],
                expected_artifacts=["mission summary", "next steps"],
            )
            return OperatorLLMDecisionResult(
                mode=self.mode,
                reply="Mode test deterministe: j'ai prepare un brouillon de mission non executable.",
                intent=OperatorIntent(kind=OperatorIntentKind.DRAFT_MISSION, text=frame.safe_user_message),
                mission_draft=draft,
                authority_summary=MissionAuthoritySummary(
                    mission_id="mission_deterministic_test",
                    allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_exploration"],
                    forbidden_actions=["payment", "send_email", "credential_access", "shell", "write_file"],
                    summary="Test mode only; no execution authority.",
                ),
                metadata=metadata,
            )

        return OperatorLLMDecisionResult(
            mode=self.mode,
            reply="Mode test deterministe: j'ai besoin de clarifier la mission avant toute preparation.",
            intent=OperatorIntent(kind=OperatorIntentKind.ASK_CLARIFICATION, text=frame.safe_user_message),
            metadata=metadata,
        )


def _is_greeting(text: str) -> bool:
    return any(marker in text for marker in ("t'es la", "tu es la", "are you there", "bonjour", "hello"))
