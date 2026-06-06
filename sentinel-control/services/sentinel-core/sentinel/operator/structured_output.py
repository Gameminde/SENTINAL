from __future__ import annotations

from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionClarificationQuestion,
    MissionDraft,
    MissionStartProposal,
    OperatorIntent,
    OperatorLLMDecisionResult,
    OperatorMode,
)


class OperatorStructuredOutputError(ValueError):
    """Raised for malformed but non-dangerous LLM structured output."""


def validate_operator_structured_output(
    raw_output: dict[str, Any],
    *,
    mode: OperatorMode,
    provider_id: str,
    backend_id: str,
    model_id: str,
) -> OperatorLLMDecisionResult:
    if not isinstance(raw_output, dict):
        raise OperatorStructuredOutputError("operator LLM output must be an object")
    reply = raw_output.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        raise OperatorStructuredOutputError("operator LLM output requires a reply string")

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


def _coerce_optional(model_type: Any, value: Any) -> Any:
    if value is None:
        return None
    return model_type.model_validate(value)
