from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.policy import ModelExecutionBudgetPolicy, ModelRetryPolicy, ModelTimeoutPolicy
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.llm_adapter import OperatorModelClient
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyDecision,
    ReadOnlyFailureCode,
    ReadOnlyReportResult,
    ReadOnlySpineError,
)
from sentinel.operator.redaction import redact_operator_value, sanitize_operator_refs


_PROVIDER_MATERIAL_KEYS = frozenset(
    {
        "raw_provider_response",
        "raw_response",
        "raw_text",
        "raw_text_in_memory_only",
        "provider_wrapper",
        "provider_payload",
        "reasoning",
        "reasoning_content",
        "raw_reasoning",
        "chain_of_thought",
    }
)

READ_ONLY_DECISION_PROTOCOL_VERSION = "read_only_research_decision_v1"
READ_ONLY_REPORT_PROTOCOL_VERSION = "read_only_research_report_v1"

_SAFE_PROVIDER_METADATA_KEYS = frozenset(
    {
        "provider_response_hash",
        "reasoning_present",
        "reasoning_hash",
        "reasoning_token_count",
        "reasoning_character_count",
        "visible_content_char_count",
        "visible_content_estimated_tokens",
        "finish_reason",
        "finish_reason_hash",
        "output_truncated",
        "raw_text_hash",
        "raw_text_transport",
        "content_extraction_source",
        "content_extraction_error",
        "normalization_strategy",
        "json_object_detected",
        "markdown_fence_detected",
        "multiple_json_objects_detected",
    }
)

_DECISION_FIELDS = frozenset({"action", "arguments", "evidence_refs", "operator_message"})
_REPORT_FIELDS = frozenset({"report_text", "evidence_refs"})
_FORBIDDEN_CONTROL_FIELDS = frozenset(
    {
        "workspace",
        "workspace_ref",
        "path",
        "allowed_paths",
        "model_contract_ref",
        "authority_scope",
        "approval_scope",
        "allowed_actions",
        "budget",
        "credentials",
        "credential",
        "authorization",
        "authority",
        "authority_envelope",
        "can_execute",
        "can_grant_authority",
        "authority_effect",
        "data_not_authority",
        "MissionStartProposal",
        "MissionDraft",
        "MissionAuthoritySummary",
        "OperatorIntent",
    }
)
_ALLOWED_NORMALIZATION_STRATEGIES = frozenset(
    {
        "empty_visible_content",
        "plain_json_object",
        "single_json_markdown_fence",
        "truncated_or_invalid_json",
        "no_json_object_detected",
        "strict_json_rejected",
        "json_value_not_object",
        "raw_text_transport",
    }
)
_ALLOWED_CONTENT_EXTRACTION_ERRORS = frozenset(
    {"missing_choices_or_message", "message_not_object", "content_not_string"}
)


class ReadOnlyProviderDecisionClient:
    """Provider-backed read-only exploration decisions using the explicit model contract."""

    def __init__(
        self,
        *,
        user_model_contract: UserModelContract,
        model_client: OperatorModelClient,
        telemetry_sink: object | None = None,
        max_output_tokens: int | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._contract = user_model_contract
        self._model_client = model_client
        self._telemetry_sink = telemetry_sink
        self._max_output_tokens = max_output_tokens or user_model_contract.context_budget_policy.reserve_output_tokens
        self._timeout_seconds = timeout_seconds
        self.call_count = 0

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        self.call_count += 1
        prompt = _decision_prompt(context)
        request = _request(
            contract=self._contract,
            lane="exploration_decision",
            prompt=prompt,
            max_output_tokens=self._max_output_tokens,
            timeout_seconds=self._timeout_seconds,
            metadata={
                "mission_id": context.get("mission_id"),
                "status": context.get("status"),
                "observation_count": len(context.get("observations", [])),
                "legal_actions": list(context.get("legal_actions", [])),
            },
        )
        _record_model_started(self._telemetry_sink, request, context)
        raw = self._model_client.complete(request)
        _raise_if_blocked(raw, phase="model_decision", telemetry_sink=self._telemetry_sink, request=request, context=context)
        try:
            decision = _validate_decision(raw)
        except Exception as exc:  # noqa: BLE001
            diagnostics = _build_read_only_diagnostics(
                raw,
                parse_stage="read_only_decision_validation",
                allowed_fields=_DECISION_FIELDS,
                required_fields={"action"},
                validation_error=exc if isinstance(exc, ValidationError) else None,
                extra_error_codes=["unknown_field"] if _unknown_field_names(raw, _DECISION_FIELDS) else [],
            )
            _record_model_completed(
                self._telemetry_sink,
                request,
                context,
                schema_invalid=True,
                diagnostics=diagnostics,
                provider_response_hash=diagnostics.get("provider_response_hash"),
            )
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                phase="model_decision",
                exception_class=exc.__class__.__name__,
                legacy_reason="read_only_decision_schema_invalid",
                diagnostics=diagnostics,
            ) from exc
        _record_model_completed(
            self._telemetry_sink,
            request,
            context,
            provider_response_hash=_provider_response_hash(raw),
        )
        return decision


class ReadOnlyProviderReportClient:
    """Separate provider-backed report lane for sanitized read-only reports."""

    def __init__(
        self,
        *,
        user_model_contract: UserModelContract,
        model_client: OperatorModelClient,
        telemetry_sink: object | None = None,
        max_output_tokens: int | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        self._contract = user_model_contract
        self._model_client = model_client
        self._telemetry_sink = telemetry_sink
        reserve = user_model_contract.context_budget_policy.reserve_output_tokens
        self._max_output_tokens = max_output_tokens or max(reserve * 4, reserve + 500)
        self._timeout_seconds = timeout_seconds
        self.call_count = 0

    def complete(self, context: dict[str, Any]) -> ReadOnlyReportResult:
        self.call_count += 1
        evidence_refs = _context_evidence_refs(context)
        prompt = _report_prompt(context, evidence_refs=evidence_refs)
        request = _request(
            contract=self._contract,
            lane="final_report",
            prompt=prompt,
            max_output_tokens=self._max_output_tokens,
            timeout_seconds=self._timeout_seconds,
            metadata={
                "mission_id": context.get("mission_id"),
                "observation_count": len(context.get("observations", [])),
                "receipt_ref_count": len(context.get("receipt_refs", [])),
                "evidence_refs": evidence_refs,
            },
        )
        _record_model_started(self._telemetry_sink, request, context)
        raw = self._model_client.complete(request)
        _raise_if_blocked(raw, phase="final_report", telemetry_sink=self._telemetry_sink, request=request, context=context)
        try:
            report = _validate_report(raw)
        except Exception as exc:  # noqa: BLE001
            diagnostics = _build_read_only_diagnostics(
                raw,
                parse_stage="read_only_report_validation",
                allowed_fields=_REPORT_FIELDS,
                required_fields={"report_text"},
                validation_error=exc if isinstance(exc, ValidationError) else None,
                extra_error_codes=["unknown_field"] if _unknown_field_names(raw, _REPORT_FIELDS) else [],
            )
            _record_model_completed(
                self._telemetry_sink,
                request,
                context,
                schema_invalid=True,
                diagnostics=diagnostics,
                provider_response_hash=diagnostics.get("provider_response_hash"),
            )
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                phase="final_report",
                exception_class=exc.__class__.__name__,
                legacy_reason="read_only_report_schema_invalid",
                diagnostics=diagnostics,
            ) from exc
        _record_model_completed(
            self._telemetry_sink,
            request,
            context,
            provider_response_hash=_provider_response_hash(raw),
        )
        return report


def _request(
    *,
    contract: UserModelContract,
    lane: str,
    prompt: str,
    max_output_tokens: int,
    timeout_seconds: float,
    metadata: dict[str, Any],
) -> RealModelRequest:
    timeout_policy = ModelTimeoutPolicy(
        connect_timeout_seconds=2.0,
        read_timeout_seconds=timeout_seconds,
        total_timeout_seconds=timeout_seconds + 2.0,
    )
    retry_policy = ModelRetryPolicy(max_attempts=1, retryable_outcomes=[])
    budget_policy = ModelExecutionBudgetPolicy(
        max_input_tokens=contract.context_budget_policy.max_decision_frame_tokens
        + contract.context_budget_policy.max_evidence_tokens,
        max_output_tokens=max_output_tokens,
        max_total_estimated_usd=max(contract.cost_profile.input_usd_per_1m, contract.cost_profile.output_usd_per_1m, 0.0),
    )
    safe_metadata = {
        "read_only_lane": lane,
        "selected_provider_id": contract.selected_provider_id,
        "selected_backend_id": contract.selected_backend_id,
        "selected_model": contract.selected_model,
        "routing_policy": "explicit_user_model_contract_only",
        **redact_operator_value(metadata),
    }
    payload = {
        "provider_id": contract.selected_provider_id,
        "backend_id": contract.selected_backend_id,
        "model_id": contract.selected_model,
        "lane": lane,
        "prompt_hash": text_hash(prompt),
        "user_model_contract_id": contract.id,
        "request_metadata": safe_metadata,
    }
    return RealModelRequest(
        provider_id=contract.selected_provider_id,
        model_id=contract.selected_model,
        backend_id=contract.selected_backend_id,
        backend=contract.selected_backend_id,
        runtime="read_only_research_product",
        prompt_hash=text_hash(prompt),
        frame_hash=stable_hash({"lane": lane, "metadata": safe_metadata}),
        user_model_contract_id=contract.id,
        estimated_input_tokens=max(1, len(prompt) // 4),
        estimated_output_tokens=max_output_tokens,
        prompt_text_in_memory_only=prompt,
        request_metadata=safe_metadata,
        timeout_policy_id=timeout_policy.id,
        retry_policy_id=retry_policy.id,
        budget_policy_id=budget_policy.id,
        request_hash=stable_hash(payload),
    )


def _decision_prompt(context: dict[str, Any]) -> str:
    payload = {
        "protocol_version": READ_ONLY_DECISION_PROTOCOL_VERSION,
        "task": "Return exactly one JSON object for a governed read-only exploration decision.",
        "rules": [
            "Return exactly one JSON object.",
            "Do not wrap in Markdown.",
            "Do not include explanations outside JSON.",
            "Do not include reasoning.",
            "Do not include legacy OperatorLLMDecisionResult.",
            "Do not include MissionStartProposal, OperatorIntent, MissionDraft, or MissionAuthoritySummary.",
            "Do not include workspace, workspace_ref, model_contract_ref, paths outside arguments, credentials, budget, approval scope, authority, allowed_actions, or can_execute.",
            "Choose exactly one action.",
            "If exploration has enough evidence, use finish_exploration.",
        ],
        "allowed_actions": ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        "schema": {
            "action": "enum",
            "arguments": "object",
            "evidence_refs": "list[str]",
            "operator_message": "optional short display text",
        },
        "examples": [
            {"action": "list_directory", "arguments": {"path": "."}, "evidence_refs": []},
            {"action": "search_text", "arguments": {"query": "register", "path": "."}, "evidence_refs": []},
            {
                "action": "read_file_segment",
                "arguments": {"path": "src/example.py", "start_line": 1, "line_count": 80},
                "evidence_refs": [],
            },
            {"action": "finish_exploration", "arguments": {}, "evidence_refs": ["evidence_ref_1"]},
        ],
        "context": _safe_context(context),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _report_prompt(context: dict[str, Any], *, evidence_refs: list[str]) -> str:
    payload = {
        "protocol_version": READ_ONLY_REPORT_PROTOCOL_VERSION,
        "task": "Return a sanitized evidence-linked read-only report JSON object.",
        "schema": {"report_text": "string", "evidence_refs": "list[str]"},
        "rules": [
            "Reference only provided evidence refs.",
            "Do not claim writes, external actions, credential access, or authority grants.",
        ],
        "evidence_refs": evidence_refs,
        "context": _safe_context(context),
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def _safe_context(context: dict[str, Any]) -> dict[str, Any]:
    return redact_operator_value(
        {
            "mission_id": context.get("mission_id"),
            "status": context.get("status"),
            "observations": context.get("observations", []),
            "receipt_refs": context.get("receipt_refs", []),
            "legal_actions": context.get("legal_actions", []),
        }
    )


def _context_evidence_refs(context: dict[str, Any]) -> list[str]:
    return sanitize_operator_refs(
        [
            str(item.get("evidence_ref"))
            for item in context.get("observations", [])
            if isinstance(item, dict) and item.get("evidence_ref")
        ]
    )


def _raise_if_blocked(
    raw: dict[str, Any],
    *,
    phase: str,
    telemetry_sink: object | None = None,
    request: RealModelRequest | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    blocked_reason = None
    if isinstance(raw.get("metadata"), dict):
        blocked_reason = raw["metadata"].get("blocked_reason")
    blocked_reason = blocked_reason or raw.get("blocked_reason")
    if blocked_reason:
        diagnostics = _build_read_only_diagnostics(
            raw,
            parse_stage="read_only_provider_blocked",
            allowed_fields=_DECISION_FIELDS if phase == "model_decision" else _REPORT_FIELDS,
            required_fields=set(),
        )
        if request is not None:
            _record_model_completed(
                telemetry_sink,
                request,
                context or {},
                schema_invalid=True,
                diagnostics=diagnostics,
                provider_response_hash=diagnostics.get("provider_response_hash"),
                blocked_reason=str(blocked_reason),
            )
        raise ReadOnlySpineError(
            ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
            phase=phase,
            legacy_reason=str(blocked_reason),
            diagnostics=diagnostics,
        )


def _validate_decision(raw: dict[str, Any]) -> ReadOnlyDecision:
    unknown = _unknown_field_names(raw, _DECISION_FIELDS)
    if unknown:
        raise ValueError("read_only_decision_unknown_field")
    return ReadOnlyDecision.model_validate(_typed_visible_content(raw, allowed_fields=_DECISION_FIELDS))


def _validate_report(raw: dict[str, Any]) -> ReadOnlyReportResult:
    unknown = _unknown_field_names(raw, _REPORT_FIELDS)
    if unknown:
        raise ValueError("read_only_report_unknown_field")
    return ReadOnlyReportResult.model_validate(_typed_visible_content(raw, allowed_fields=_REPORT_FIELDS))


def _typed_visible_content(raw: dict[str, Any], *, allowed_fields: frozenset[str]) -> dict[str, Any]:
    return {
        key: value
        for key, value in raw.items()
        if key in allowed_fields
        and key not in _PROVIDER_MATERIAL_KEYS
        and key not in _SAFE_PROVIDER_METADATA_KEYS
    }


def _unknown_field_names(raw: dict[str, Any], allowed_fields: frozenset[str]) -> list[str]:
    if not isinstance(raw, dict):
        return []
    known = allowed_fields | _SAFE_PROVIDER_METADATA_KEYS | _PROVIDER_MATERIAL_KEYS
    return sorted(str(key) for key in raw if key not in known or key in _FORBIDDEN_CONTROL_FIELDS)


def _build_read_only_diagnostics(
    raw_output: dict[str, Any],
    *,
    parse_stage: str,
    allowed_fields: frozenset[str],
    required_fields: set[str],
    validation_error: ValidationError | None = None,
    extra_error_codes: list[str] | None = None,
) -> dict[str, Any]:
    payload = raw_output if isinstance(raw_output, dict) else {}
    top_level_keys = [
        str(key)
        for key in sorted(payload)
        if key not in _SAFE_PROVIDER_METADATA_KEYS and key not in _PROVIDER_MATERIAL_KEYS
    ]
    unknown_fields = _unknown_field_names(payload, allowed_fields)
    validation_codes = list(extra_error_codes or [])
    validation_paths: list[str] = []
    required_missing = {field for field in required_fields if field not in payload}
    if validation_error is not None:
        for error in validation_error.errors(include_url=False, include_context=False, include_input=False):
            code = str(error.get("type", "validation_error"))
            path = ".".join(str(part) for part in error.get("loc", ()))
            validation_codes.append(code)
            if path:
                validation_paths.append(path)
            if code == "missing" and path:
                required_missing.add(path)
    return {
        "protocol_version": READ_ONLY_REPORT_PROTOCOL_VERSION
        if allowed_fields == _REPORT_FIELDS
        else READ_ONLY_DECISION_PROTOCOL_VERSION,
        "parse_stage": parse_stage,
        "provider_response_hash": _provider_response_hash(payload),
        "visible_content_length": _safe_int(payload.get("visible_content_char_count")),
        "finish_reason": _safe_finish_reason(payload),
        "output_truncated": payload.get("output_truncated") if isinstance(payload.get("output_truncated"), bool) else None,
        "json_object_detected": payload.get("json_object_detected")
        if isinstance(payload.get("json_object_detected"), bool)
        else isinstance(raw_output, dict),
        "top_level_type": "dict" if isinstance(raw_output, dict) else type(raw_output).__name__,
        "top_level_key_names": top_level_keys,
        "missing_required_field_names": sorted(required_missing),
        "unknown_field_names": unknown_fields,
        "validation_error_codes": sorted(dict.fromkeys(validation_codes)),
        "validation_error_paths": sorted(dict.fromkeys(validation_paths)),
        "markdown_fence_detected": payload.get("markdown_fence_detected")
        if isinstance(payload.get("markdown_fence_detected"), bool)
        else None,
        "multiple_json_objects_detected": payload.get("multiple_json_objects_detected")
        if isinstance(payload.get("multiple_json_objects_detected"), bool)
        else None,
        "normalization_strategy": _safe_normalization_strategy(payload),
        "content_extraction_source": _safe_content_extraction_source(payload),
        "content_extraction_error": _safe_content_extraction_error(payload),
    }


def _record_model_started(telemetry_sink: object | None, request: RealModelRequest, context: dict[str, Any]) -> None:
    recorder = getattr(telemetry_sink, "record_model_call_started", None)
    if not callable(recorder):
        return
    recorder(request, session_id=_safe_session_id(context))


def _record_model_completed(
    telemetry_sink: object | None,
    request: RealModelRequest,
    context: dict[str, Any],
    *,
    provider_response_hash: object | None = None,
    schema_invalid: bool = False,
    diagnostics: dict[str, Any] | None = None,
    blocked_reason: str | None = None,
) -> None:
    recorder = getattr(telemetry_sink, "record_model_call_completed", None)
    if not callable(recorder):
        return
    recorder(
        request,
        provider_response_hash=provider_response_hash if isinstance(provider_response_hash, str) else None,
        reasoning_hash=None,
        session_id=_safe_session_id(context),
        blocked_reason=blocked_reason,
        schema_invalid=schema_invalid,
        diagnostics=diagnostics,
    )


def _safe_session_id(context: dict[str, Any]) -> str | None:
    value = context.get("mission_id")
    return str(value) if value else None


def _provider_response_hash(payload: dict[str, Any]) -> str:
    value = payload.get("provider_response_hash")
    if isinstance(value, str) and value:
        return value
    return stable_hash(redact_operator_value(payload))


def _safe_int(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _safe_finish_reason(payload: dict[str, Any]) -> str | None:
    value = payload.get("finish_reason")
    allowed = {"stop", "length", "content_filter", "tool_calls", "function_call"}
    return value if isinstance(value, str) and value in allowed else None


def _safe_normalization_strategy(payload: dict[str, Any]) -> str | None:
    value = payload.get("normalization_strategy")
    return value if isinstance(value, str) and value in _ALLOWED_NORMALIZATION_STRATEGIES else None


def _safe_content_extraction_source(payload: dict[str, Any]) -> str | None:
    value = payload.get("content_extraction_source")
    return value if value == "choices[0].message.content" else None


def _safe_content_extraction_error(payload: dict[str, Any]) -> str | None:
    value = payload.get("content_extraction_error")
    return value if isinstance(value, str) and value in _ALLOWED_CONTENT_EXTRACTION_ERRORS else None


__all__ = [
    "ReadOnlyProviderDecisionClient",
    "ReadOnlyProviderReportClient",
]
