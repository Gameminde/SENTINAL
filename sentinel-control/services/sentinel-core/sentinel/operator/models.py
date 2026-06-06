from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import text_hash
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id


class OperatorMode(StrEnum):
    LLM_OPERATOR = "llm_operator_mode"
    DETERMINISTIC_TEST = "deterministic_test_mode"


class OperatorMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class OperatorIntentKind(StrEnum):
    GREETING = "greeting"
    DRAFT_MISSION = "draft_mission"
    ASK_CLARIFICATION = "ask_clarification"
    START_MISSION = "start_mission"
    PAUSE_MISSION = "pause_mission"
    RESUME_MISSION = "resume_mission"
    KILL_MISSION = "kill_mission"
    STATUS = "status"
    TIMELINE = "timeline"
    REPLAY = "replay"
    UNKNOWN = "unknown"


class OperatorConversationState(StrEnum):
    IDLE = "idle"
    GREETING = "greeting"
    UNDERSTANDING_REQUEST = "understanding_request"
    ASKING_CLARIFICATIONS = "asking_clarifications"
    DRAFTING_MISSION = "drafting_mission"
    AWAITING_START_CONFIRMATION = "awaiting_start_confirmation"
    MISSION_QUEUED = "mission_queued"
    MISSION_RUNNING = "mission_running"
    MISSION_PAUSED = "mission_paused"
    MISSION_KILLED = "mission_killed"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_BLOCKED = "mission_blocked"


class OperatorMissionStatus(StrEnum):
    DRAFT = "draft"
    READY_TO_START = "ready_to_start"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    CANCEL_REQUESTED = "cancel_requested"
    KILLED = "killed"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    REVOKED = "revoked"


def utc_now() -> datetime:
    return datetime.now(UTC)


class OperatorMessage(SentinelModel):
    message_id: str = Field(default_factory=lambda: new_id("opmsg"))
    session_id: str
    role: OperatorMessageRole
    content: str = Field(exclude=True, repr=False)
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _message_is_data(self) -> OperatorMessage:
        assert_data_not_authority(
            context="operator_message",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    @property
    def content_hash(self) -> str:
        return text_hash(self.content)

    @property
    def safe_content(self) -> str:
        return redact_operator_text(self.content)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role.value,
            "safe_content": self.safe_content,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class OperatorIntent(SentinelModel):
    kind: OperatorIntentKind
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _intent_is_safe_data(self) -> OperatorIntent:
        assert_data_not_authority(
            context="operator_intent",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.metadata, context="operator_intent")
        return self


class MissionDraft(SentinelModel):
    draft_id: str = Field(default_factory=lambda: new_id("mission_draft"))
    title: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    target_audience: str | None = None
    budget_summary: str | None = None
    autonomy_summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    executable: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _draft_is_not_executable(self) -> MissionDraft:
        assert_data_not_authority(
            context="mission_draft",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.executable is not False:
            raise ValueError("mission_draft: executable must remain false")
        reject_operator_control_payload(self.metadata, context="mission_draft")
        return self


class MissionClarificationQuestion(SentinelModel):
    question_id: str = Field(default_factory=lambda: new_id("clarify"))
    prompt: str
    field_name: str
    required: bool = True
    data_not_authority: bool = True


class MissionAuthoritySummary(SentinelModel):
    mission_id: str
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    summary: str
    user_confirmation_required: bool = True
    finalgate_required: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _authority_summary_is_not_authority(self) -> MissionAuthoritySummary:
        assert_data_not_authority(
            context="mission_authority_summary",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.metadata, context="mission_authority_summary")
        return self


class MissionStartProposal(SentinelModel):
    proposal_id: str = Field(default_factory=lambda: new_id("start_proposal"))
    mission_draft_id: str
    authority_summary: MissionAuthoritySummary
    requires_explicit_confirmation: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _start_proposal_cannot_execute(self) -> MissionStartProposal:
        assert_data_not_authority(
            context="mission_start_proposal",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if self.requires_explicit_confirmation is not True:
            raise ValueError("mission_start_proposal: explicit confirmation is required")
        reject_operator_control_payload(self.metadata, context="mission_start_proposal")
        return self


class OperatorLLMDecisionResult(SentinelModel):
    result_id: str = Field(default_factory=lambda: new_id("opllm"))
    mode: OperatorMode
    reply: str
    intent: OperatorIntent | None = None
    mission_draft: MissionDraft | None = None
    clarification_questions: list[MissionClarificationQuestion] = Field(default_factory=list)
    authority_summary: MissionAuthoritySummary | None = None
    start_proposal: MissionStartProposal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None
    provider_response_hash: str | None = None
    reasoning_hash: str | None = None
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _llm_result_is_advisory(self) -> OperatorLLMDecisionResult:
        assert_data_not_authority(
            context="operator_llm_decision_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.metadata, context="operator_llm_decision_result")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "mode": self.mode.value,
            "reply": redact_operator_text(self.reply),
            "intent": self.intent.model_dump(mode="json") if self.intent else None,
            "mission_draft": self.mission_draft.model_dump(mode="json") if self.mission_draft else None,
            "clarification_questions": [
                question.model_dump(mode="json") for question in self.clarification_questions
            ],
            "authority_summary": self.authority_summary.model_dump(mode="json") if self.authority_summary else None,
            "start_proposal": self.start_proposal.model_dump(mode="json") if self.start_proposal else None,
            "metadata": self.metadata,
            "provider_id": self.provider_id,
            "backend_id": self.backend_id,
            "model_id": self.model_id,
            "provider_response_hash": self.provider_response_hash,
            "reasoning_hash": self.reasoning_hash,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class OperatorConversationSession(SentinelModel):
    session_id: str = Field(default_factory=lambda: new_id("opsession"))
    mode: OperatorMode
    state: OperatorConversationState = OperatorConversationState.IDLE
    current_draft: MissionDraft | None = None
    current_authority_summary: MissionAuthoritySummary | None = None
    active_mission_id: str | None = None
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _session_is_state_only(self) -> OperatorConversationSession:
        assert_data_not_authority(
            context="operator_conversation_session",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class OperatorTurnResult(SentinelModel):
    session_id: str
    state: OperatorConversationState
    reply: str
    intent: OperatorIntent | None = None
    mission_draft: MissionDraft | None = None
    clarification_questions: list[MissionClarificationQuestion] = Field(default_factory=list)
    authority_summary: MissionAuthoritySummary | None = None
    start_proposal: MissionStartProposal | None = None
    mission_record: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _turn_result_is_data(self) -> OperatorTurnResult:
        assert_data_not_authority(
            context="operator_turn_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.metadata, context="operator_turn_result")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "reply": redact_operator_text(self.reply),
            "intent": self.intent.model_dump(mode="json") if self.intent else None,
            "mission_draft": self.mission_draft.model_dump(mode="json") if self.mission_draft else None,
            "clarification_questions": [
                question.model_dump(mode="json") for question in self.clarification_questions
            ],
            "authority_summary": self.authority_summary.model_dump(mode="json") if self.authority_summary else None,
            "start_proposal": self.start_proposal.model_dump(mode="json") if self.start_proposal else None,
            "mission_record": self.mission_record,
            "metadata": self.metadata,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class MissionRecord(SentinelModel):
    mission_id: str = Field(default_factory=lambda: new_id("mission"))
    session_id: str
    draft: MissionDraft
    authority_summary: MissionAuthoritySummary | None = None
    status: OperatorMissionStatus = OperatorMissionStatus.DRAFT
    run_dir: str
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _record_is_kernel_state_only(self) -> MissionRecord:
        assert_data_not_authority(
            context="mission_record",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        draft = self.draft.model_dump(mode="json")
        draft["title"] = redact_operator_text(str(draft.get("title", "")))
        draft["objective"] = redact_operator_text(str(draft.get("objective", "")))
        draft["constraints"] = [redact_operator_text(str(item)) for item in draft.get("constraints", [])]
        authority = self.authority_summary.model_dump(mode="json") if self.authority_summary else None
        return {
            "mission_id": self.mission_id,
            "session_id": self.session_id,
            "draft": draft,
            "authority_summary": authority,
            "status": self.status.value,
            "run_dir": self.run_dir,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class MissionEvent(SentinelModel):
    event_id: str = Field(default_factory=lambda: new_id("mission_event"))
    mission_id: str
    sequence: int = Field(ge=0)
    event_type: str
    safe_summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    previous_hash: str | None = None
    event_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _event_is_kernel_data(self) -> MissionEvent:
        assert_data_not_authority(
            context="mission_event",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        reject_operator_control_payload(self.metadata, context="mission_event")
        return self
