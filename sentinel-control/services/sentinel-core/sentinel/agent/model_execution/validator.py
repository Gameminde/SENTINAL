from __future__ import annotations

from typing import Any

from sentinel.agent.model_execution.models import LLMDecisionResult, ModelExecutionOutcomeClass, ProviderModelResponse
from sentinel.agent.model_execution.redaction import stable_hash


_AUTHORITY_EXPANSION_FIELDS = {
    "grant_tools",
    "allowed_tools",
    "tool_calls",
    "execute_tool",
    "organ_execution",
    "allowed_domains",
    "allowed_paths",
    "budget_override",
    "credential_access",
}


class LLMDecisionResultValidator:
    @staticmethod
    def validate(response: ProviderModelResponse) -> LLMDecisionResult:
        content = response.content
        response_hash = stable_hash(content)
        tool_requested = "tool_calls" in content or "execute_tool" in content
        organ_requested = "organ_execution" in content
        authority_expansion = any(field in content for field in _AUTHORITY_EXPANSION_FIELDS)

        if authority_expansion:
            return _result(
                response,
                outcome_class=ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED,
                success=False,
                authority_expansion=True,
                tool_execution_requested=tool_requested,
                organ_execution_requested=organ_requested,
                response_hash=response_hash,
            )
        if response.refusal:
            return _result(
                response,
                outcome_class=ModelExecutionOutcomeClass.PROVIDER_REFUSAL,
                success=False,
                refusal=True,
                response_hash=response_hash,
            )
        if response.error_class:
            return _result(
                response,
                outcome_class=ModelExecutionOutcomeClass.PROVIDER_ERROR,
                success=False,
                error_class=response.error_class,
                response_hash=response_hash,
            )
        if not _has_valid_schema(content):
            return _result(
                response,
                outcome_class=ModelExecutionOutcomeClass.INVALID_RESPONSE_SCHEMA,
                success=False,
                response_hash=response_hash,
            )
        return _result(
            response,
            outcome_class=ModelExecutionOutcomeClass.SUCCESS_VALIDATED,
            success=True,
            response_hash=response_hash,
        )


def _has_valid_schema(content: dict[str, Any]) -> bool:
    return isinstance(content.get("decision"), str) and isinstance(content.get("rationale"), str) and isinstance(
        content.get("evidence_refs"), list
    )


def _result(
    response: ProviderModelResponse,
    *,
    outcome_class: ModelExecutionOutcomeClass,
    success: bool,
    response_hash: str,
    refusal: bool = False,
    error_class: str | None = None,
    authority_expansion: bool = False,
    tool_execution_requested: bool = False,
    organ_execution_requested: bool = False,
) -> LLMDecisionResult:
    content = response.content
    evidence_refs = content.get("evidence_refs") if isinstance(content.get("evidence_refs"), list) else []
    confidence = content.get("confidence")
    return LLMDecisionResult(
        provider_id=response.provider_id,
        model_id=response.model_id,
        decision=content.get("decision") if isinstance(content.get("decision"), str) else None,
        rationale_summary=content.get("rationale") if isinstance(content.get("rationale"), str) else None,
        evidence_refs=[str(ref) for ref in evidence_refs],
        confidence=confidence if isinstance(confidence, int | float) else None,
        outcome_class=outcome_class,
        success=success,
        refusal=refusal,
        error_class=error_class,
        authority_expansion=authority_expansion,
        tool_execution_requested=tool_execution_requested,
        organ_execution_requested=organ_execution_requested,
        sanitized_response_hash=response_hash,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=response.cost_usd,
    )
