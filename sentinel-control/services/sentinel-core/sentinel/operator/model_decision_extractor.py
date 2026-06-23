from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.redaction import redact_operator_value, sanitize_operator_refs


READ_ONLY_CANONICAL_DECISION_FIELDS = frozenset({"action", "arguments", "evidence_refs", "operator_message"})

_READ_ONLY_ACTIONS = frozenset({"list_directory", "search_text", "read_file_segment", "finish_exploration"})
_EMPTY_ARGUMENT_ACTIONS = frozenset({"list_directory", "finish_exploration"})

_ACTION_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("action",),
    ("tool",),
    ("tool_name",),
    ("name",),
    ("next_action",),
    ("chosen_action",),
    ("operation",),
    ("next_step", "name"),
    ("function", "name"),
)
_ARGUMENT_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("arguments",),
    ("args",),
    ("params",),
    ("parameters",),
    ("input",),
    ("tool_input",),
    ("next_step", "input"),
    ("function", "arguments"),
)
_EVIDENCE_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("evidence_refs",),
    ("evidence",),
    ("references",),
    ("source_refs",),
    ("receipt_refs",),
)
_OPERATOR_MESSAGE_FIELD_PATHS: tuple[tuple[str, ...], ...] = (
    ("operator_message",),
    ("message",),
    ("summary",),
    ("rationale_summary",),
    ("note",),
)

_SAFE_METADATA_FIELDS = frozenset(
    {
        "content_extraction_source",
        "finish_reason",
        "json_object_detected",
        "normalization_strategy",
        "output_truncated",
        "visible_content_char_count",
        "visible_content_length",
        "visible_content_estimated_tokens",
        "reasoning_char_count",
        "provider_response_hash",
        "markdown_fence_detected",
        "multiple_json_objects_detected",
        "content_extraction_error",
    }
)

_UNSAFE_FIELD_NAMES = frozenset(
    {
        "authorization",
        "authority",
        "authority_scope",
        "approval_scope",
        "budget",
        "can_execute",
        "can_grant_authority",
        "credential_access",
        "credentials",
        "metadata",
        "model_contract_ref",
        "provider_wrapper",
        "raw_prompt",
        "raw_reasoning",
        "raw_response",
        "reasoning",
        "reasoning_content",
        "workspace_ref",
    }
)
_UNSAFE_ACTION_NAMES = frozenset(
    {
        "browser_click",
        "credential_access",
        "delete_file",
        "modify_file",
        "network_request",
        "payment",
        "send_email",
        "shell",
        "write_file",
    }
)
_DIAGNOSTIC_LABEL_RE = re.compile(r"^diagnostic_label_hash:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ModelDecisionExtractionResult:
    payload: dict[str, Any]
    diagnostics: dict[str, Any]


class ModelDecisionExtractionError(ValueError):
    def __init__(self, diagnostics: dict[str, Any]) -> None:
        self.diagnostics = diagnostics
        super().__init__("read_only_decision_extraction_failed")


def extract_read_only_decision_payload(raw_output: Any) -> ModelDecisionExtractionResult:
    diagnostics = _base_diagnostics(raw_output)
    if not isinstance(raw_output, dict):
        diagnostics["missing_required_canonical_fields"] = ["action"]
        diagnostics["validation_error_codes"] = ["extraction_failed", "raw_top_level_not_object"]
        raise ModelDecisionExtractionError(diagnostics)

    unsafe_fields = _unsafe_field_names(raw_output)
    action_candidate = _first_field(raw_output, _ACTION_FIELD_PATHS)
    action = _safe_action_value(action_candidate.value)
    unsafe_actions = []
    if isinstance(action_candidate.value, str) and action_candidate.value.strip().lower() in _UNSAFE_ACTION_NAMES:
        unsafe_actions.append(action_candidate.value.strip().lower())
    if unsafe_fields or unsafe_actions:
        diagnostics["unsafe_field_names"] = unsafe_fields
        diagnostics["unsafe_action_names"] = sorted(dict.fromkeys(unsafe_actions))
        diagnostics["validation_error_codes"] = ["extraction_failed", "unsafe_model_decision"]
        raise ModelDecisionExtractionError(diagnostics)

    if action_candidate.path:
        diagnostics["detected_action_field_names"] = [_path_name(action_candidate.path)]
    if not action:
        diagnostics["missing_required_canonical_fields"] = ["action"]
        diagnostics["validation_error_codes"] = ["extraction_failed", "missing_action"]
        raise ModelDecisionExtractionError(diagnostics)
    if action not in _READ_ONLY_ACTIONS:
        diagnostics["unsafe_action_names"] = [action]
        diagnostics["validation_error_codes"] = ["extraction_failed", "unsupported_action"]
        raise ModelDecisionExtractionError(diagnostics)

    arguments_candidate = _first_field(raw_output, _ARGUMENT_FIELD_PATHS)
    arguments = arguments_candidate.value
    if arguments_candidate.path:
        diagnostics["detected_argument_field_names"] = [_path_name(arguments_candidate.path)]
    if arguments is None:
        if action not in _EMPTY_ARGUMENT_ACTIONS:
            diagnostics["missing_required_canonical_fields"] = ["arguments"]
            diagnostics["validation_error_codes"] = ["extraction_failed", "missing_arguments"]
            raise ModelDecisionExtractionError(diagnostics)
        arguments = {}
    if not isinstance(arguments, dict):
        diagnostics["validation_error_codes"] = ["extraction_failed", "arguments_not_object"]
        raise ModelDecisionExtractionError(diagnostics)

    evidence_candidate = _first_field(raw_output, _EVIDENCE_FIELD_PATHS)
    if evidence_candidate.path:
        diagnostics["detected_evidence_field_names"] = [_path_name(evidence_candidate.path)]
    evidence_refs = _safe_ref_list(evidence_candidate.value)

    message_candidate = _first_field(raw_output, _OPERATOR_MESSAGE_FIELD_PATHS)
    if message_candidate.path:
        diagnostics["detected_operator_message_field_names"] = [_path_name(message_candidate.path)]

    payload: dict[str, Any] = {
        "action": action,
        "arguments": redact_operator_value(arguments),
        "evidence_refs": evidence_refs,
    }
    if isinstance(message_candidate.value, str) and message_candidate.value.strip():
        payload["operator_message"] = message_candidate.value.strip()[:240]

    diagnostics["extraction_failed"] = False
    diagnostics["missing_required_canonical_fields"] = []
    diagnostics["validation_payload_key_names"] = sorted(payload)
    diagnostics["ignored_safe_metadata_field_names"] = _ignored_safe_metadata_field_names(raw_output)
    return ModelDecisionExtractionResult(payload=payload, diagnostics=diagnostics)


@dataclass(frozen=True)
class _FieldCandidate:
    path: tuple[str, ...] | None
    value: Any


def _base_diagnostics(raw_output: Any) -> dict[str, Any]:
    top_level_keys = (
        sorted(_safe_key_name(str(key)) for key in raw_output if str(key) != "provider_response_hash")
        if isinstance(raw_output, dict)
        else []
    )
    return {
        "extraction_failed": True,
        "model_top_level_type": "dict" if isinstance(raw_output, dict) else type(raw_output).__name__,
        "model_top_level_key_names": top_level_keys,
        "detected_action_field_names": [],
        "detected_argument_field_names": [],
        "detected_evidence_field_names": [],
        "detected_operator_message_field_names": [],
        "unsafe_field_names": [],
        "unsafe_action_names": [],
        "missing_required_canonical_fields": [],
        "provider_response_hash": _provider_response_hash(raw_output),
        "diagnostic_retention_status": "retained",
        "validation_error_codes": [],
    }


def _first_field(payload: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> _FieldCandidate:
    for path in paths:
        found, value = _get_path(payload, path)
        if found:
            return _FieldCandidate(path=path, value=value)
    return _FieldCandidate(path=None, value=None)


def _get_path(payload: dict[str, Any], path: tuple[str, ...]) -> tuple[bool, Any]:
    current: Any = payload
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _safe_action_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower()


def _safe_ref_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return sanitize_operator_refs([value])
    if isinstance(value, list | tuple):
        return sanitize_operator_refs([str(item) for item in value if isinstance(item, str)])
    return []


def _unsafe_field_names(value: Any) -> list[str]:
    names: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                key_name = str(key)
                lowered = key_name.lower()
                if lowered in _UNSAFE_FIELD_NAMES:
                    names.append(_safe_label(key_name))
                visit(nested)
        elif isinstance(item, list | tuple | set):
            for nested in item:
                visit(nested)

    visit(value)
    return sorted(dict.fromkeys(names))


def _ignored_safe_metadata_field_names(payload: dict[str, Any]) -> list[str]:
    output: list[str] = []
    for key, value in payload.items():
        key_name = str(key)
        if key_name in READ_ONLY_CANONICAL_DECISION_FIELDS:
            continue
        if key_name in _SAFE_METADATA_FIELDS and _is_safe_scalar(value):
            output.append(key_name)
            continue
        if _DIAGNOSTIC_LABEL_RE.match(key_name) and _is_safe_scalar(value):
            output.append(key_name)
    return sorted(dict.fromkeys(output))


def _is_safe_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _path_name(path: tuple[str, ...]) -> str:
    return ".".join(path)


def _safe_label(value: str) -> str:
    return f"diagnostic_label_hash:{text_hash(value)}"


def _safe_key_name(value: str) -> str:
    if value.lower() in _UNSAFE_FIELD_NAMES:
        return _safe_label(value)
    return value


def _provider_response_hash(raw_output: Any) -> str:
    if isinstance(raw_output, dict):
        value = raw_output.get("provider_response_hash")
        if isinstance(value, str) and value:
            return value
    return stable_hash(redact_operator_value(raw_output))


__all__ = [
    "ModelDecisionExtractionError",
    "ModelDecisionExtractionResult",
    "extract_read_only_decision_payload",
]
