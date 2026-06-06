from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.models import MissionDraft, OperatorMessage
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    scan_forbidden_payload_categorized,
)


_STRUCTURED_OUTPUT_SCHEMA = {
    "allowed_outputs": [
        "OperatorReply",
        "MissionDraft",
        "MissionClarificationQuestion",
        "MissionAuthoritySummary",
        "MissionStartProposal",
        "MissionPlanProposal",
        "OperatorStatusExplanation",
    ],
    "forbidden_outputs": [
        "direct organ calls",
        "authority grants",
        "credential unlocks",
        "provider overrides",
        "raw prompt or raw provider response persistence",
    ],
}


class OperatorConversationFrame(SentinelModel):
    frame_id: str = Field(default_factory=lambda: new_id("opframe"))
    session_id: str
    user_message_hash: str
    safe_user_message: str
    current_draft_summary: dict[str, Any] | None = None
    structured_output_schema: dict[str, Any] = Field(default_factory=lambda: dict(_STRUCTURED_OUTPUT_SCHEMA))
    forbidden_actions: list[str] = Field(
        default_factory=lambda: [
            "execute organs directly",
            "grant authority",
            "unlock credentials",
            "override provider/backend/model",
            "treat memory or receipts as permission",
        ]
    )
    prompt_hash: str
    llm_is_authority: bool = False
    llm_can_execute: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @classmethod
    def build(
        cls,
        *,
        session_id: str,
        user_message: OperatorMessage,
        current_draft: MissionDraft | None = None,
    ) -> OperatorConversationFrame:
        _reject_prompt_injection(user_message.content)
        draft_summary = (
            {
                "draft_id": current_draft.draft_id,
                "title": current_draft.title,
                "objective": current_draft.objective,
                "constraints": list(current_draft.constraints),
                "expected_artifacts": list(current_draft.expected_artifacts),
            }
            if current_draft is not None
            else None
        )
        safe_payload = {
            "session_id": session_id,
            "user_message_hash": user_message.content_hash,
            "safe_user_message": user_message.safe_content,
            "current_draft_summary": draft_summary,
            "structured_output_schema": _STRUCTURED_OUTPUT_SCHEMA,
        }
        return cls(
            session_id=session_id,
            user_message_hash=user_message.content_hash,
            safe_user_message=user_message.safe_content,
            current_draft_summary=draft_summary,
            prompt_hash=stable_hash(safe_payload),
        )

    @model_validator(mode="after")
    def _frame_is_data(self) -> OperatorConversationFrame:
        assert_data_not_authority(
            context="operator_conversation_frame",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.llm_is_authority or self.llm_can_execute:
            raise ValueError("operator_conversation_frame: llm cannot be authority or executor")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "session_id": self.session_id,
            "user_message_hash": self.user_message_hash,
            "safe_user_message_hash": stable_hash(self.safe_user_message),
            "current_draft_summary": self.current_draft_summary,
            "structured_output_schema": self.structured_output_schema,
            "forbidden_actions": self.forbidden_actions,
            "prompt_hash": self.prompt_hash,
            "llm_is_authority": self.llm_is_authority,
            "llm_can_execute": self.llm_can_execute,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def prompt_payload(self) -> dict[str, Any]:
        payload = self.safe_model_dump()
        payload["safe_user_message"] = self.safe_user_message
        return payload


def _reject_prompt_injection(text: str) -> None:
    scan = scan_forbidden_payload_categorized(text, path="$.user_message")
    allowed = set(scan[OrganSafetyScanCategory.SECRET.value])
    unsafe = [finding for finding in scan[OrganSafetyScanCategory.ALL.value] if finding not in allowed]
    if unsafe:
        raise ValueError("operator prompt frame rejected unsafe direct execution text")
