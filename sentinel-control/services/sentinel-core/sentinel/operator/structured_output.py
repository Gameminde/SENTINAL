from __future__ import annotations

from typing import Any

from pydantic import Field, ValidationError, field_validator, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionClarificationQuestion,
    MissionDraft,
    MissionStartProposal,
    OperatorIntent,
    OperatorIntentKind,
    OperatorLLMDecisionResult,
    OperatorMode,
)
from sentinel.shared.models import SentinelModel, new_id


COCKPIT_MISSION_UNDERSTANDING_V2 = "cockpit_mission_understanding_v2"
READ_ONLY_RESEARCH_CAPABILITY = "read_only_research"
READ_ONLY_RESEARCH_ACTIONS = (
    "list_directory",
    "read_file_segment",
    "search_text",
    "finish_exploration",
)
READ_ONLY_RESEARCH_FORBIDDEN_ACTIONS = (
    "write_file",
    "shell",
    "credential_access",
    "browser_click",
    "payment",
    "send_email",
)

_V2_ALLOWED_FIELDS = {
    "protocol_version",
    "kind",
    "reply",
    "title",
    "objective",
    "constraints",
    "expected_artifacts",
    "requested_capability",
    "clarification_questions",
}
_SAFE_PROVIDER_METADATA_FIELDS = {
    "raw_provider_response",
    "provider_response_hash",
    "reasoning_present",
    "reasoning_hash",
    "reasoning_char_count",
    "reasoning_token_count",
    "visible_content_char_count",
    "visible_content_estimated_tokens",
    "finish_reason",
    "finish_reason_hash",
    "output_truncated",
    "raw_text_hash",
    "raw_text_transport",
}
_LEGACY_ALLOWED_FIELDS = {
    "reply",
    "intent",
    "mission_draft",
    "authority_summary",
    "start_proposal",
    "clarification_questions",
    "metadata",
}


class OperatorStructuredOutputError(ValueError):
    """Raised for malformed but non-dangerous LLM structured output."""

    def __init__(self, message: str, *, diagnostics: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics or {}


class CockpitMissionUnderstandingV2(SentinelModel):
    protocol_version: str
    kind: str
    reply: str
    title: str | None = None
    objective: str | None = None
    constraints: list[str] = Field(default_factory=list)
    expected_artifacts: list[str] = Field(default_factory=list)
    requested_capability: str | None = None
    clarification_questions: list[str] = Field(default_factory=list)

    @field_validator("protocol_version")
    @classmethod
    def _protocol_is_v2(cls, value: str) -> str:
        if value != COCKPIT_MISSION_UNDERSTANDING_V2:
            raise ValueError("unsupported_protocol_version")
        return value

    @field_validator("kind")
    @classmethod
    def _kind_is_supported(cls, value: str) -> str:
        if value not in {"draft_mission", "ask_clarification", "greeting", "unknown"}:
            raise ValueError("unsupported_kind")
        return value

    @field_validator("reply", "title", "objective", mode="before")
    @classmethod
    def _bounded_optional_text(cls, value: Any) -> Any:
        if value is None:
            return value
        if not isinstance(value, str):
            raise ValueError("text_field_must_be_string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("text_field_empty")
        if len(stripped) > 1200:
            raise ValueError("text_field_too_long")
        return stripped

    @field_validator("constraints", "expected_artifacts", "clarification_questions")
    @classmethod
    def _bounded_string_list(cls, value: list[str]) -> list[str]:
        if len(value) > 8:
            raise ValueError("list_too_long")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("list_item_must_be_nonempty_string")
            stripped = item.strip()
            if len(stripped) > 500:
                raise ValueError("list_item_too_long")
            normalized.append(stripped)
        return normalized

    @model_validator(mode="after")
    def _draft_fields_are_present(self) -> "CockpitMissionUnderstandingV2":
        if self.kind == "draft_mission":
            if not self.title:
                raise ValueError("missing_required_title")
            if not self.objective:
                raise ValueError("missing_required_objective")
            if not self.requested_capability:
                raise ValueError("missing_required_requested_capability")
        return self


def validate_operator_structured_output(
    raw_output: dict[str, Any],
    *,
    mode: OperatorMode,
    provider_id: str,
    backend_id: str,
    model_id: str,
    required_protocol_version: str | None = None,
) -> OperatorLLMDecisionResult:
    if not isinstance(raw_output, dict):
        raise OperatorStructuredOutputError(
            "operator LLM output must be an object",
            diagnostics=build_structured_output_diagnostics(
                raw_output,
                parse_stage="top_level_type",
                expected_protocol_version=required_protocol_version,
            ),
        )
    if (
        required_protocol_version == COCKPIT_MISSION_UNDERSTANDING_V2
        or raw_output.get("protocol_version") == COCKPIT_MISSION_UNDERSTANDING_V2
    ):
        return _validate_mission_understanding_v2(
            raw_output,
            mode=mode,
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
        )
    reply = raw_output.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise OperatorStructuredOutputError(
            "operator LLM output requires a reply string",
            diagnostics=build_structured_output_diagnostics(
                raw_output,
                parse_stage="legacy_operator_decision_validation",
                missing_required_field_names=["reply"],
                expected_protocol_version=required_protocol_version,
            ),
        )

    raw_provider_response = raw_output.get("raw_provider_response")
    raw_reasoning = raw_output.get("reasoning")
    content = {
        key: value
        for key, value in raw_output.items()
        if key not in {"raw_provider_response", "reasoning"}
    }

    intent = _coerce_optional(OperatorIntent, content.get("intent"))
    mission_draft = _coerce_optional(MissionDraft, content.get("mission_draft"))
    authority_summary = _coerce_optional(MissionAuthoritySummary, content.get("authority_summary"))
    start_proposal = _coerce_optional(MissionStartProposal, content.get("start_proposal"))
    clarification_questions = [
        MissionClarificationQuestion.model_validate(item)
        for item in content.get("clarification_questions", [])
    ]

    return OperatorLLMDecisionResult(
        mode=mode,
        reply=reply,
        intent=intent,
        mission_draft=mission_draft,
        clarification_questions=clarification_questions,
        authority_summary=authority_summary,
        start_proposal=start_proposal,
        metadata=dict(content.get("metadata", {})),
        provider_id=provider_id,
        backend_id=backend_id,
        model_id=model_id,
        provider_response_hash=stable_hash(raw_provider_response)
        if raw_provider_response is not None
        else stable_hash(content),
        reasoning_hash=text_hash(str(raw_reasoning)) if raw_reasoning else None,
    )


def build_structured_output_diagnostics(
    raw_output: Any,
    *,
    parse_stage: str,
    validation_error: ValidationError | None = None,
    missing_required_field_names: list[str] | None = None,
    expected_protocol_version: str | None = None,
) -> dict[str, Any]:
    payload = raw_output if isinstance(raw_output, dict) else {}
    actual_protocol = payload.get("protocol_version")
    if actual_protocol == COCKPIT_MISSION_UNDERSTANDING_V2:
        protocol_version = COCKPIT_MISSION_UNDERSTANDING_V2
    elif expected_protocol_version == COCKPIT_MISSION_UNDERSTANDING_V2:
        protocol_version = COCKPIT_MISSION_UNDERSTANDING_V2
    else:
        protocol_version = "unknown"
    top_level_keys = sorted(str(key) for key in payload if str(key) not in _SAFE_PROVIDER_METADATA_FIELDS)
    allowed = (
        _V2_ALLOWED_FIELDS | _SAFE_PROVIDER_METADATA_FIELDS
        if protocol_version == COCKPIT_MISSION_UNDERSTANDING_V2
        else _LEGACY_ALLOWED_FIELDS | _SAFE_PROVIDER_METADATA_FIELDS
    )
    unknown_fields = sorted(key for key in top_level_keys if key not in allowed)
    required_missing = set(missing_required_field_names or [])
    validation_codes: list[str] = []
    validation_paths: list[str] = []
    if validation_error is not None:
        for error in validation_error.errors(include_url=False, include_context=False, include_input=False):
            code = str(error.get("type", "validation_error"))
            path = ".".join(str(part) for part in error.get("loc", ()))
            validation_codes.append(code)
            if path:
                validation_paths.append(path)
            if code == "missing" and path:
                required_missing.add(path)
            message = str(error.get("msg", ""))
            if "missing_required_title" in message:
                required_missing.add("title")
            if "missing_required_objective" in message:
                required_missing.add("objective")
            if "missing_required_requested_capability" in message:
                required_missing.add("requested_capability")
    return {
        "protocol_version": protocol_version,
        "parse_stage": parse_stage,
        "provider_response_hash": _safe_hash(payload),
        "visible_content_length": _safe_int(payload.get("visible_content_char_count")),
        "finish_reason": _safe_finish_reason(payload),
        "output_truncated": payload.get("output_truncated") if isinstance(payload.get("output_truncated"), bool) else None,
        "json_object_detected": isinstance(raw_output, dict),
        "top_level_type": type(raw_output).__name__,
        "top_level_key_names": top_level_keys,
        "missing_required_field_names": sorted(required_missing),
        "unknown_field_names": unknown_fields,
        "validation_error_codes": sorted(dict.fromkeys(validation_codes)),
        "validation_error_paths": sorted(dict.fromkeys(validation_paths)),
        "markdown_fence_detected": payload.get("markdown_fence_detected") if isinstance(payload.get("markdown_fence_detected"), bool) else None,
        "multiple_json_objects_detected": payload.get("multiple_json_objects_detected") if isinstance(payload.get("multiple_json_objects_detected"), bool) else None,
    }


def _validate_mission_understanding_v2(
    raw_output: dict[str, Any],
    *,
    mode: OperatorMode,
    provider_id: str,
    backend_id: str,
    model_id: str,
) -> OperatorLLMDecisionResult:
    if "reasoning" in raw_output:
        diagnostics = build_structured_output_diagnostics(
            raw_output,
            parse_stage="mission_understanding_v2_validation",
            missing_required_field_names=[],
            expected_protocol_version=COCKPIT_MISSION_UNDERSTANDING_V2,
        )
        diagnostics["unknown_field_names"] = sorted(dict.fromkeys([*diagnostics["unknown_field_names"], "reasoning"]))
        raise OperatorStructuredOutputError("operator LLM output contained raw reasoning", diagnostics=diagnostics)
    content = {
        key: value
        for key, value in raw_output.items()
        if key not in _SAFE_PROVIDER_METADATA_FIELDS
    }
    try:
        understanding = CockpitMissionUnderstandingV2.model_validate(content)
    except ValidationError as exc:
        raise OperatorStructuredOutputError(
            "mission understanding v2 validation failed",
            diagnostics=build_structured_output_diagnostics(
                raw_output,
                parse_stage="mission_understanding_v2_validation",
                validation_error=exc,
                expected_protocol_version=COCKPIT_MISSION_UNDERSTANDING_V2,
            ),
        ) from None
    if understanding.kind == "draft_mission" and understanding.requested_capability != READ_ONLY_RESEARCH_CAPABILITY:
        return OperatorLLMDecisionResult(
            mode=mode,
            reply=understanding.reply,
            intent=OperatorIntent(
                kind=OperatorIntentKind.ASK_CLARIFICATION,
                text="unsupported requested capability",
                metadata={"understanding_protocol": COCKPIT_MISSION_UNDERSTANDING_V2},
            ),
            clarification_questions=[
                MissionClarificationQuestion(
                    prompt="This cockpit route only supports read-only repository research in Pack 3.",
                    field_name="requested_capability",
                )
            ],
            metadata={
                "understanding_protocol": COCKPIT_MISSION_UNDERSTANDING_V2,
                "blocked_reason": "unsupported_requested_capability",
            },
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
            provider_response_hash=_safe_hash(raw_output),
            reasoning_hash=_safe_reasoning_hash(raw_output),
        )
    intent_kind = {
        "draft_mission": OperatorIntentKind.DRAFT_MISSION,
        "ask_clarification": OperatorIntentKind.ASK_CLARIFICATION,
        "greeting": OperatorIntentKind.GREETING,
        "unknown": OperatorIntentKind.UNKNOWN,
    }[understanding.kind]
    draft = None
    authority_summary = None
    clarifications: list[MissionClarificationQuestion] = []
    if understanding.kind == "draft_mission":
        draft = MissionDraft(
            title=understanding.title or "Mission draft",
            objective=understanding.objective or "",
            constraints=understanding.constraints,
            expected_artifacts=understanding.expected_artifacts,
            metadata={
                "understanding_protocol": COCKPIT_MISSION_UNDERSTANDING_V2,
                "requested_capability": READ_ONLY_RESEARCH_CAPABILITY,
            },
        )
        authority_summary = MissionAuthoritySummary(
            mission_id=new_id("mission_summary"),
            allowed_actions=list(READ_ONLY_RESEARCH_ACTIONS),
            forbidden_actions=list(READ_ONLY_RESEARCH_FORBIDDEN_ACTIONS),
            summary="Read-only repository research with bounded list, read, search, and final report actions.",
            metadata={
                "understanding_protocol": COCKPIT_MISSION_UNDERSTANDING_V2,
                "capability_id": READ_ONLY_RESEARCH_CAPABILITY,
                "operation": "inspect_repository",
            },
        )
    else:
        clarifications = [
            MissionClarificationQuestion(prompt=question, field_name="mission_request")
            for question in understanding.clarification_questions
        ]
    return OperatorLLMDecisionResult(
        mode=mode,
        reply=understanding.reply,
        intent=OperatorIntent(
            kind=intent_kind,
            text=understanding.reply,
            metadata={"understanding_protocol": COCKPIT_MISSION_UNDERSTANDING_V2},
        ),
        mission_draft=draft,
        clarification_questions=clarifications,
        authority_summary=authority_summary,
        metadata={"understanding_protocol": COCKPIT_MISSION_UNDERSTANDING_V2},
        provider_id=provider_id,
        backend_id=backend_id,
        model_id=model_id,
        provider_response_hash=_safe_hash(raw_output),
        reasoning_hash=_safe_reasoning_hash(raw_output),
    )


def _coerce_optional(model_type: Any, value: Any) -> Any:
    if value is None:
        return None
    return model_type.model_validate(value)


def _safe_hash(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("provider_response_hash"), str):
        return str(payload["provider_response_hash"])
    if payload.get("raw_provider_response") is not None:
        return stable_hash(payload.get("raw_provider_response"))
    return stable_hash({key: value for key, value in payload.items() if key != "raw_provider_response"})


def _safe_reasoning_hash(payload: dict[str, Any]) -> str | None:
    value = payload.get("reasoning_hash")
    return value if isinstance(value, str) else None


def _safe_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _safe_finish_reason(payload: dict[str, Any]) -> str | None:
    value = payload.get("finish_reason")
    if isinstance(value, str) and value in {"stop", "length", "content_filter", "tool_calls"}:
        return value
    value = payload.get("finish_reason_hash")
    return value if isinstance(value, str) else None
