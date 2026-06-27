from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.policy import ModelExecutionBudgetPolicy, ModelRetryPolicy, ModelTimeoutPolicy
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.llm_adapter import OperatorModelClient
from sentinel.operator.model_decision_extractor import (
    ModelDecisionExtractionError,
    extract_read_only_decision_payload,
)
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
        "reasoning_char_count",
        "reasoning_token_count",
        "reasoning_character_count",
        "visible_content_length",
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
_FILTERED_SAFE_METADATA_KEYS = _SAFE_PROVIDER_METADATA_KEYS - {"provider_response_hash"}

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
    {"missing_choices_or_message", "message_not_object", "content_not_string", "model_client_exception"}
)
_DECISION_ENVELOPE_KEYS = ("reply", "message", "content", "output", "result", "response")
_UNSAFE_ENVELOPE_FIELD_NAMES = frozenset(
    {
        "shell",
        "write_file",
        "delete_file",
        "modify_file",
        "credential_access",
        "payment",
        "send_email",
        "browser_click",
        "network_request",
        "authority",
        "authority_scope",
        "approval_scope",
        "can_execute",
        "can_grant_authority",
        "workspace_ref",
        "model_contract_ref",
        "budget",
        "credentials",
        "authorization",
        "raw_prompt",
        "raw_response",
        "raw_reasoning",
        "reasoning",
        "reasoning_content",
        "provider_wrapper",
    }
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
        try:
            raw = self._model_client.complete(request)
        except Exception as exc:  # noqa: BLE001
            diagnostics = _build_exception_diagnostics(
                parse_stage="read_only_decision_validation",
                allowed_fields=_DECISION_FIELDS,
                exception_class=exc.__class__.__name__,
            )
            _record_model_completed(
                self._telemetry_sink,
                request,
                context,
                schema_invalid=True,
                diagnostics=diagnostics,
            )
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                phase="model_decision",
                exception_class=exc.__class__.__name__,
                legacy_reason="read_only_decision_schema_invalid",
                diagnostics=diagnostics,
            ) from exc
        _raise_if_blocked(raw, phase="model_decision", telemetry_sink=self._telemetry_sink, request=request, context=context)
        try:
            decision, success_diagnostics = _validate_decision(raw)
        except Exception as exc:  # noqa: BLE001
            diagnostics = _build_read_only_diagnostics(
                raw,
                parse_stage="read_only_decision_validation",
                allowed_fields=_DECISION_FIELDS,
                required_fields={"action"},
                validation_error=exc if isinstance(exc, ValidationError) else None,
                extra_error_codes=["unknown_field"] if _unknown_field_names(raw, _DECISION_FIELDS) else [],
            )
            if isinstance(exc, ModelDecisionExtractionError):
                diagnostics = _merge_extraction_diagnostics(diagnostics, exc.diagnostics)
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
            diagnostics=_merge_optional_diagnostics(
                success_diagnostics,
                _success_diagnostics_if_metadata_filtered(
                    raw,
                    parse_stage="read_only_decision_validation",
                    allowed_fields=_DECISION_FIELDS,
                    required_fields={"action"},
                ),
            ),
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
        try:
            raw = self._model_client.complete(request)
        except Exception as exc:  # noqa: BLE001
            diagnostics = _build_exception_diagnostics(
                parse_stage="read_only_report_validation",
                allowed_fields=_REPORT_FIELDS,
                exception_class=exc.__class__.__name__,
            )
            _record_model_completed(
                self._telemetry_sink,
                request,
                context,
                schema_invalid=True,
                diagnostics=diagnostics,
            )
            raise ReadOnlySpineError(
                ReadOnlyFailureCode.READ_MODEL_DECISION_ERROR,
                phase="final_report",
                exception_class=exc.__class__.__name__,
                legacy_reason="read_only_report_schema_invalid",
                diagnostics=diagnostics,
            ) from exc
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
            "Allowed top-level keys are exactly: action, arguments, evidence_refs, operator_message.",
            "Do not include reasoning_char_count or any diagnostic/metadata fields.",
            "Do not include workspace/model/authority fields such as workspace_ref, model_contract_ref, authority, can_execute.",
            "Do not include shell/write/credential/payment/email/browser-click actions.",
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


def _validate_decision(raw: dict[str, Any]) -> tuple[ReadOnlyDecision, dict[str, Any] | None]:
    validation_payload = raw
    envelope_diagnostics: dict[str, Any] | None = None
    envelope = _extract_decision_envelope(raw)
    if envelope is not None:
        validation_payload, envelope_diagnostics = envelope
    try:
        extraction = extract_read_only_decision_payload(validation_payload)
    except ModelDecisionExtractionError as exc:
        if envelope_diagnostics is not None:
            raise ModelDecisionExtractionError(
                _merge_envelope_extraction_diagnostics(envelope_diagnostics, exc.diagnostics)
            ) from exc
        raise
    decision = ReadOnlyDecision.model_validate(extraction.payload)
    if envelope_diagnostics is None:
        return decision, None
    return decision, _merge_envelope_extraction_diagnostics(envelope_diagnostics, extraction.diagnostics)


def _extract_decision_envelope(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    present_keys = [key for key in _DECISION_ENVELOPE_KEYS if key in raw]
    metadata_key_present = "metadata" in raw
    if not present_keys and not metadata_key_present:
        return None

    safe_metadata_ignored = False
    if metadata_key_present:
        metadata_value = raw.get("metadata")
        if isinstance(metadata_value, dict) and metadata_value.get("blocked_reason"):
            return None
        if not _is_safe_scalar_metadata(metadata_value):
            diagnostics = _envelope_diagnostics(
                raw,
                envelope_key=present_keys[0] if present_keys else None,
                envelope_value=raw.get(present_keys[0]) if present_keys else None,
                envelope_parse_status="failed",
                validation_error_codes=["extraction_failed", "unsafe_envelope_metadata"],
            )
            diagnostics["unsafe_field_name_hashes"] = sorted(
                dict.fromkeys([*diagnostics["unsafe_field_name_hashes"], _hash_field_name("metadata")])
            )
            raise ModelDecisionExtractionError(diagnostics)
        safe_metadata_ignored = True

    unsafe_wrapper_hashes = _unsafe_wrapper_field_hashes(raw)
    if unsafe_wrapper_hashes:
        diagnostics = _envelope_diagnostics(
            raw,
            envelope_key=present_keys[0] if present_keys else None,
            envelope_value=raw.get(present_keys[0]) if present_keys else None,
            envelope_parse_status="failed",
            validation_error_codes=["extraction_failed", "unsafe_envelope_wrapper"],
            safe_metadata_ignored=safe_metadata_ignored,
        )
        diagnostics["unsafe_field_name_hashes"] = sorted(
            dict.fromkeys([*diagnostics["unsafe_field_name_hashes"], *unsafe_wrapper_hashes])
        )
        raise ModelDecisionExtractionError(diagnostics)

    if len(present_keys) != 1:
        diagnostics = _envelope_diagnostics(
            raw,
            envelope_key=present_keys[0] if present_keys else None,
            envelope_value=raw.get(present_keys[0]) if present_keys else None,
            envelope_parse_status="failed",
            validation_error_codes=["extraction_failed", "ambiguous_or_missing_envelope_reply"],
            safe_metadata_ignored=safe_metadata_ignored,
        )
        diagnostics["missing_required_canonical_fields"] = ["action"]
        raise ModelDecisionExtractionError(diagnostics)

    envelope_key = present_keys[0]
    envelope_value = raw.get(envelope_key)
    payload, parse_status, json_detected = _parse_envelope_value(envelope_value)
    if payload is None:
        diagnostics = _envelope_diagnostics(
            raw,
            envelope_key=envelope_key,
            envelope_value=envelope_value,
            envelope_parse_status=parse_status,
            envelope_json_detected=json_detected,
            validation_error_codes=["extraction_failed", "envelope_reply_not_json"],
            safe_metadata_ignored=safe_metadata_ignored,
        )
        diagnostics["missing_required_canonical_fields"] = ["action"]
        raise ModelDecisionExtractionError(diagnostics)

    unsafe_payload_hashes = _unsafe_envelope_field_hashes(payload)
    if unsafe_payload_hashes:
        diagnostics = _envelope_diagnostics(
            raw,
            envelope_key=envelope_key,
            envelope_value=envelope_value,
            envelope_parse_status=parse_status,
            envelope_json_detected=json_detected,
            validation_error_codes=["extraction_failed", "unsafe_envelope_reply"],
            safe_metadata_ignored=safe_metadata_ignored,
        )
        diagnostics["unsafe_field_name_hashes"] = unsafe_payload_hashes
        raise ModelDecisionExtractionError(diagnostics)

    diagnostics = _envelope_diagnostics(
        raw,
        envelope_key=envelope_key,
        envelope_value=envelope_value,
        envelope_parse_status=parse_status,
        envelope_json_detected=json_detected,
        safe_metadata_ignored=safe_metadata_ignored,
    )
    return payload, diagnostics


def _parse_envelope_value(value: Any) -> tuple[dict[str, Any] | None, str, bool]:
    if isinstance(value, dict):
        return value, "parsed", True
    if not isinstance(value, str):
        return None, "failed", False
    candidate = value.strip()
    if not candidate:
        return None, "not_json", False
    parse_status = "parsed"
    if candidate.startswith("```"):
        first_break = candidate.find("\n")
        last_fence = candidate.rfind("```")
        if first_break < 0 or last_fence <= first_break:
            return None, "failed", False
        if candidate[last_fence + 3 :].strip():
            return None, "failed", False
        candidate = candidate[first_break + 1 : last_fence].strip()
        parse_status = "fenced_json"
    if not candidate.startswith("{"):
        return None, "not_json", False
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None, "failed", False
    if not isinstance(parsed, dict):
        return None, "failed", True
    return parsed, parse_status, True


def _envelope_diagnostics(
    raw: dict[str, Any],
    *,
    envelope_key: str | None,
    envelope_value: Any,
    envelope_parse_status: str,
    envelope_json_detected: bool | None = None,
    validation_error_codes: list[str] | None = None,
    safe_metadata_ignored: bool = False,
) -> dict[str, Any]:
    return {
        "envelope_detected": True,
        "envelope_key": envelope_key,
        "envelope_value_type": _envelope_value_type(envelope_value),
        "envelope_json_detected": envelope_json_detected
        if isinstance(envelope_json_detected, bool)
        else isinstance(envelope_value, dict),
        "envelope_parse_status": envelope_parse_status,
        "model_top_level_key_names": _safe_key_names(raw),
        "metadata_key_present": "metadata" in raw,
        "safe_metadata_ignored": safe_metadata_ignored,
        "detected_action_field_names": [],
        "detected_argument_field_names": [],
        "missing_required_canonical_fields": [],
        "unsafe_field_name_hashes": _unsafe_envelope_field_hashes(raw),
        "provider_response_hash": _provider_response_hash(raw),
        "diagnostic_retention_status": "retained",
        "validation_error_codes": list(validation_error_codes or []),
        "unknown_field_names": [],
        "unsafe_unknown_field_names": [],
    }


def _merge_envelope_extraction_diagnostics(
    envelope: dict[str, Any],
    extraction: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(extraction)
    for key, value in envelope.items():
        if key in {
            "detected_action_field_names",
            "detected_argument_field_names",
            "missing_required_canonical_fields",
            "validation_error_codes",
        }:
            continue
        merged[key] = value
    merged["provider_response_hash"] = envelope["provider_response_hash"]
    merged["validation_error_codes"] = sorted(
        dict.fromkeys(
            [
                *envelope.get("validation_error_codes", []),
                *extraction.get("validation_error_codes", []),
            ]
        )
    )
    if not extraction.get("missing_required_canonical_fields"):
        merged["missing_required_canonical_fields"] = envelope.get("missing_required_canonical_fields", [])
    merged["unsafe_field_name_hashes"] = sorted(
        dict.fromkeys(
            [
                *envelope.get("unsafe_field_name_hashes", []),
                *extraction.get("unsafe_field_names", []),
            ]
        )
    )
    merged.setdefault("unknown_field_names", [])
    merged.setdefault("unsafe_unknown_field_names", [])
    return merged


def _envelope_value_type(value: Any) -> str:
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, str):
        return "string"
    return "other"


def _safe_key_names(payload: dict[str, Any]) -> list[str]:
    return sorted(_safe_envelope_key_name(str(key)) for key in payload if str(key) != "provider_response_hash")


def _safe_envelope_key_name(key: str) -> str:
    lowered = key.lower()
    if lowered in _UNSAFE_ENVELOPE_FIELD_NAMES or key in _PROVIDER_MATERIAL_KEYS:
        return f"diagnostic_label_hash:{text_hash(key)}"
    return key


def _unsafe_envelope_field_hashes(value: Any) -> list[str]:
    hashes: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                key_name = str(key)
                if key_name.lower() in _UNSAFE_ENVELOPE_FIELD_NAMES or key_name in _PROVIDER_MATERIAL_KEYS:
                    hashes.append(_hash_field_name(key_name))
                visit(nested)
        elif isinstance(item, list | tuple | set):
            for nested in item:
                visit(nested)

    visit(value)
    return sorted(dict.fromkeys(hashes))


def _unsafe_wrapper_field_hashes(raw: dict[str, Any]) -> list[str]:
    hashes: list[str] = []
    for key, value in raw.items():
        if key in _DECISION_ENVELOPE_KEYS or key == "metadata":
            continue
        if key in _SAFE_PROVIDER_METADATA_KEYS and _is_safe_scalar_metadata(value):
            continue
        hashes.append(_hash_field_name(str(key)))
    return sorted(dict.fromkeys(hashes))


def _hash_field_name(key: str) -> str:
    return f"diagnostic_label_hash:{text_hash(key)}"


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
    return _unsafe_unknown_field_names(raw, allowed_fields)


def _unsafe_unknown_field_names(raw: dict[str, Any], allowed_fields: frozenset[str]) -> list[str]:
    unknown: list[str] = []
    for key, value in raw.items():
        key_name = str(key)
        if key in allowed_fields:
            continue
        if key in _SAFE_PROVIDER_METADATA_KEYS and _is_safe_scalar_metadata(value):
            continue
        if key in _SAFE_PROVIDER_METADATA_KEYS:
            unknown.append(key_name)
            continue
        if key in _PROVIDER_MATERIAL_KEYS or key in _FORBIDDEN_CONTROL_FIELDS:
            unknown.append(key_name)
            continue
        unknown.append(key_name)
    return sorted(dict.fromkeys(unknown))


def _filtered_safe_metadata_keys(raw: dict[str, Any]) -> list[str]:
    if not isinstance(raw, dict):
        return []
    return sorted(
        str(key)
        for key, value in raw.items()
        if key in _FILTERED_SAFE_METADATA_KEYS and _is_safe_scalar_metadata(value)
    )


def _is_safe_scalar_metadata(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _validation_payload_key_names(payload: dict[str, Any], *, allowed_fields: frozenset[str]) -> list[str]:
    return sorted(str(key) for key in _typed_visible_content(payload, allowed_fields=allowed_fields))


def _success_diagnostics_if_metadata_filtered(
    raw_output: dict[str, Any],
    *,
    parse_stage: str,
    allowed_fields: frozenset[str],
    required_fields: set[str],
) -> dict[str, Any] | None:
    if not _filtered_safe_metadata_keys(raw_output):
        return None
    return _build_read_only_diagnostics(
        raw_output,
        parse_stage=parse_stage,
        allowed_fields=allowed_fields,
        required_fields=required_fields,
    )


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
    filtered_safe_metadata = _filtered_safe_metadata_keys(payload)
    validation_payload_key_names = _validation_payload_key_names(payload, allowed_fields=allowed_fields)
    unsafe_unknown_fields = _unsafe_unknown_field_names(payload, allowed_fields)
    top_level_keys = [
        str(key)
        for key in sorted(payload)
        if key not in _SAFE_PROVIDER_METADATA_KEYS and key not in _PROVIDER_MATERIAL_KEYS
    ]
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
        "original_top_level_key_names": sorted(str(key) for key in payload if key != "provider_response_hash"),
        "top_level_key_names": top_level_keys,
        "missing_required_field_names": sorted(required_missing),
        "unknown_field_names": unsafe_unknown_fields,
        "unsafe_unknown_field_names": unsafe_unknown_fields,
        "safe_metadata_filtered": bool(filtered_safe_metadata),
        "filtered_safe_metadata_keys": filtered_safe_metadata,
        "validation_payload_key_names": validation_payload_key_names,
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
        "conversation_or_phase": _conversation_or_phase(parse_stage),
        "diagnostic_retention_status": "retained",
        "diagnostic_missing_fields": [],
        "diagnostic_missing_reason": [],
    }


def _merge_extraction_diagnostics(base: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key in (
        "extraction_failed",
        "model_top_level_type",
        "model_top_level_key_names",
        "detected_action_field_names",
        "detected_argument_field_names",
        "detected_evidence_field_names",
        "detected_operator_message_field_names",
        "unsafe_field_names",
        "unsafe_action_names",
        "missing_required_canonical_fields",
        "envelope_detected",
        "envelope_key",
        "envelope_value_type",
        "envelope_json_detected",
        "envelope_parse_status",
        "metadata_key_present",
        "safe_metadata_ignored",
        "unsafe_field_name_hashes",
    ):
        if key in extraction:
            merged[key] = extraction[key]
    extraction_codes = [
        str(code)
        for code in extraction.get("validation_error_codes", [])
        if isinstance(code, str) and code
    ]
    merged["validation_error_codes"] = sorted(
        dict.fromkeys([*merged.get("validation_error_codes", []), *extraction_codes])
    )
    provider_hash = extraction.get("provider_response_hash")
    if isinstance(provider_hash, str) and provider_hash:
        merged["provider_response_hash"] = provider_hash
    return merged


def _merge_optional_diagnostics(*diagnostics: dict[str, Any] | None) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    for item in diagnostics:
        if isinstance(item, dict):
            merged.update(item)
    return merged or None


def _build_exception_diagnostics(
    *,
    parse_stage: str,
    allowed_fields: frozenset[str],
    exception_class: str,
) -> dict[str, Any]:
    missing_fields = {
        "provider_response_hash",
        "json_object_detected",
        "top_level_type",
        "original_top_level_key_names",
        "validation_payload_key_names",
        "finish_reason",
        "output_truncated",
        "normalization_strategy",
        "content_extraction_source",
    }
    return {
        "protocol_version": READ_ONLY_REPORT_PROTOCOL_VERSION
        if allowed_fields == _REPORT_FIELDS
        else READ_ONLY_DECISION_PROTOCOL_VERSION,
        "parse_stage": parse_stage,
        "provider_response_hash": None,
        "visible_content_length": None,
        "finish_reason": None,
        "output_truncated": None,
        "json_object_detected": None,
        "top_level_type": None,
        "original_top_level_key_names": [],
        "top_level_key_names": [],
        "missing_required_field_names": [],
        "unknown_field_names": [],
        "unsafe_unknown_field_names": [],
        "safe_metadata_filtered": False,
        "filtered_safe_metadata_keys": [],
        "validation_payload_key_names": [],
        "validation_error_codes": sorted({"model_client_exception", exception_class}),
        "validation_error_paths": [],
        "markdown_fence_detected": None,
        "multiple_json_objects_detected": None,
        "normalization_strategy": None,
        "content_extraction_source": None,
        "content_extraction_error": "model_client_exception",
        "conversation_or_phase": _conversation_or_phase(parse_stage),
        "diagnostic_retention_status": "partial",
        "diagnostic_missing_fields": {field: True for field in sorted(missing_fields)},
        "diagnostic_missing_reason": {"model_client_exception_before_visible_payload": True},
    }


def _conversation_or_phase(parse_stage: str) -> str:
    if "report" in parse_stage:
        return "read_only_final_report"
    return "read_only_exploration_decision"


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
    try:
        recorder(
            request,
            provider_response_hash=provider_response_hash if isinstance(provider_response_hash, str) else None,
            reasoning_hash=None,
            session_id=_safe_session_id(context),
            blocked_reason=blocked_reason,
            schema_invalid=schema_invalid,
            diagnostics=diagnostics,
        )
    except Exception:  # noqa: BLE001
        return


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
