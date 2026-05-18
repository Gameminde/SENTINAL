from __future__ import annotations

import re
from typing import Any

from sentinel.agent.model_execution.models import LLMDecisionResult, ModelExecutionOutcomeClass, ProviderModelResponse
from sentinel.agent.model_execution.redaction import stable_hash, text_hash


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
_TOOL_INTENT_KEYS = {"tool_calls", "execute_tool", "function_call", "function_calls", "tool_execution"}
_ORGAN_INTENT_KEYS = {"organ_execution", "execute_organ", "organ_calls"}
_AUTHORITY_INTENT_KEYS = {
    *_AUTHORITY_EXPANSION_FIELDS,
    "authority_grant",
    "grant_authority",
    "scope_expansion",
    "expand_scope",
    "provider_override",
    "model_override",
    "selected_provider_id",
    "selected_backend_id",
    "selected_model",
    "credential_access",
}
_ACTION_INTENT_KEYS = {
    "action_execution",
    "execute_action",
    "browser_submit",
    "browser_login",
    "browser_upload",
    "browser_download",
    "browser_send",
    "spend",
    "payment",
    "trading",
    "shell",
    "desktop_host_control",
}
_SECRET_OR_RAW_PATTERNS = (
    "sk-or-v1",
    "gsk_",
    "nvapi-",
    "authorization: bearer",
    "reasoning_details",
    "reasoning_content",
    "raw provider",
    "raw_response",
    "raw prompt",
)
_SECRET_REGEXES = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}", re.IGNORECASE),
)


class LLMDecisionResultValidator:
    @staticmethod
    def validate(
        response: ProviderModelResponse,
        *,
        allowed_evidence_refs: set[str] | frozenset[str] | None = None,
    ) -> LLMDecisionResult:
        content = response.content
        response_hash = stable_hash(content)
        scan = _scan_for_forbidden_intent(content)
        tool_requested = scan["tool"]
        organ_requested = scan["organ"]
        authority_expansion = scan["authority"]

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
            outcome_class = _outcome_from_error_class(response.error_class)
            return _result(
                response,
                outcome_class=outcome_class,
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
        if allowed_evidence_refs is not None and not _evidence_refs_bind(content, allowed_evidence_refs):
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


def _evidence_refs_bind(content: dict[str, Any], allowed_evidence_refs: set[str] | frozenset[str]) -> bool:
    evidence_refs = content.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        return False
    return all(str(ref) in allowed_evidence_refs for ref in evidence_refs)


def _outcome_from_error_class(error_class: str) -> ModelExecutionOutcomeClass:
    try:
        return ModelExecutionOutcomeClass(error_class)
    except ValueError:
        return ModelExecutionOutcomeClass.PROVIDER_ERROR


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
    rationale = content.get("rationale") if isinstance(content.get("rationale"), str) else None
    return LLMDecisionResult(
        provider_id=response.provider_id,
        model_id=response.model_id,
        decision=content.get("decision") if isinstance(content.get("decision"), str) else None,
        rationale_summary=_durable_text(rationale),
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


def _scan_for_forbidden_intent(payload: Any) -> dict[str, bool]:
    result = {"tool": False, "organ": False, "authority": False}

    def visit(value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized_key = _normalize(str(key))
                next_path = (*path, normalized_key)
                path_tokens = set(next_path)
                if normalized_key in _TOOL_INTENT_KEYS:
                    result["tool"] = True
                    result["authority"] = True
                if normalized_key in _ORGAN_INTENT_KEYS:
                    result["organ"] = True
                    result["authority"] = True
                if normalized_key in _AUTHORITY_INTENT_KEYS or normalized_key in _ACTION_INTENT_KEYS:
                    result["authority"] = True
                if "browser" in path_tokens and normalized_key in {"submit", "login", "upload", "download", "send"}:
                    result["authority"] = True
                if normalized_key in {"spend", "payment", "trading", "shell"}:
                    result["authority"] = True
                if "desktop" in path_tokens and normalized_key in {"host_control", "control", "execute"}:
                    result["authority"] = True
                visit(child, next_path)
        elif isinstance(value, list | tuple | set):
            for item in value:
                visit(item, path)

    visit(payload)
    return result


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _durable_text(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.lower()
    if any(pattern in lowered for pattern in _SECRET_OR_RAW_PATTERNS) or any(
        pattern.search(value) for pattern in _SECRET_REGEXES
    ):
        return f"redacted:{text_hash(value)}"
    return value
