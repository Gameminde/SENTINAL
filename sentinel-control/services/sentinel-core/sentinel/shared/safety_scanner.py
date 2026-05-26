from __future__ import annotations

import re
from enum import StrEnum
from typing import Any


class OrganSafetyScanCategory(StrEnum):
    ALL = "all"
    UNSAFE_PAYLOAD = "unsafe_payload"
    SECRET = "secret"
    PROVIDER_OVERRIDE = "provider_override"
    AUTHORITY_EXPANSION = "authority_expansion"
    EXTERNAL_ACTION = "external_action"
    BROWSER_DANGEROUS = "browser_dangerous"
    CREDENTIAL_DANGEROUS = "credential_dangerous"
    FORBIDDEN_SURFACE = "forbidden_surface"


OrganSafetyScanResult = dict[str, list[str]]


SHARED_SECRET_LIKE_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9_\-]{12,}|gsk_[A-Za-z0-9]+|nvapi-[A-Za-z0-9]+|sk-or-v1-[A-Za-z0-9]+|sk-[A-Za-z0-9_\-]{16,})",
    re.IGNORECASE,
)

SHARED_FORBIDDEN_SECRET_KEYS = {
    "api_key",
    "authorization",
    "bearer",
    "credential",
    "credential_value",
    "password",
    "secret",
    "secret_value",
    "token",
}

SHARED_PROVIDER_OVERRIDE_KEYS = {
    "backend_override",
    "model_override",
    "provider_override",
}

SHARED_AUTHORITY_EXPANSION_KEYS = {
    "authority_expansion",
    "delegated_lane_creation",
    "mission_envelope_expansion",
}

SHARED_EXTERNAL_ACTION_KEYS = {
    "api_call",
    "api_mutation",
    "channel_send",
    "desktop_action",
    "direct_action",
    "external_network",
    "external_send",
    "network_call",
    "payment",
    "process",
    "revert_files",
    "send_email",
    "send_now",
    "shell",
    "spend",
    "terminal",
    "trade",
}

SHARED_BROWSER_DANGEROUS_KEYS = {
    "browser_download",
    "browser_login",
    "browser_private_session",
    "browser_submit",
    "browser_upload",
    "browser_js_execution",
    "download",
    "download_file",
    "execute_javascript",
    "javascript",
    "js_execution",
    "login",
    "private_session",
    "submit",
    "upload",
    "upload_file",
}

SHARED_CREDENTIAL_DANGEROUS_KEYS = {
    "cookie",
    "credential_access",
    "credential_use",
    "har_body",
    "raw_auth_headers",
    "session",
    "storage",
}

SHARED_RUNTIME_FORBIDDEN_KEYS = {
    "chain_of_thought",
    "execute_checkpoint",
    "execute_now",
    "organ_execution",
    "prompt",
    "provider_response",
    "raw_prompt",
    "raw_response",
    "reasoning",
    "restore_now",
    "rollback_now",
    "thinking",
    "tool_calls",
}

SHARED_RUNTIME_FORBIDDEN_TEXT = {
    "authority_expansion",
    "chain_of_thought",
    "delegated_lane_creation",
    "execute_checkpoint",
    "execute_now",
    "mission_envelope_expansion",
    "organ_execution",
    "provider_response",
    "raw_prompt",
    "raw_response",
    "restore_now",
    "rollback_now",
    "tool_calls",
}

SHARED_NEGATIVE_CONTROL_SAFE_KEYS = {
    "allowed_preparation_classes",
    "blocked_action_classes",
    "forbidden_actions",
    "forbidden_action_classes",
    "forbidden_inputs",
    "forbidden_organs",
    "forbidden_substeps",
}

DOWNSTREAM_DANGEROUS_FORBIDDEN_KEYS = frozenset(
    SHARED_PROVIDER_OVERRIDE_KEYS
    | SHARED_AUTHORITY_EXPANSION_KEYS
    | SHARED_EXTERNAL_ACTION_KEYS
    | SHARED_BROWSER_DANGEROUS_KEYS
    | SHARED_CREDENTIAL_DANGEROUS_KEYS
    | SHARED_FORBIDDEN_SECRET_KEYS
    | SHARED_RUNTIME_FORBIDDEN_KEYS
)

_FORBIDDEN_TEXT_BY_CATEGORY: dict[OrganSafetyScanCategory, set[str]] = {
    OrganSafetyScanCategory.PROVIDER_OVERRIDE: SHARED_PROVIDER_OVERRIDE_KEYS,
    OrganSafetyScanCategory.AUTHORITY_EXPANSION: SHARED_AUTHORITY_EXPANSION_KEYS,
    OrganSafetyScanCategory.EXTERNAL_ACTION: SHARED_EXTERNAL_ACTION_KEYS,
    OrganSafetyScanCategory.BROWSER_DANGEROUS: {
        "browser_download",
        "browser_login",
        "browser_private_session",
        "browser_submit",
        "browser_upload",
        "browser_js_execution",
        "download_file",
        "execute_javascript",
        "upload_file",
    },
    OrganSafetyScanCategory.CREDENTIAL_DANGEROUS: SHARED_CREDENTIAL_DANGEROUS_KEYS,
}


def scan_forbidden_payload_flat(payload: Any, path: str = "$") -> list[str]:
    return scan_forbidden_payload_categorized(payload, path)[OrganSafetyScanCategory.ALL.value]


def scan_forbidden_payload_categorized(payload: Any, path: str = "$") -> OrganSafetyScanResult:
    result = _empty_result()
    _scan_value(payload, path, result, negative_control=False)
    return _dedupe_result(result)


def scan_secret_like_text(value: str, path: str = "$") -> list[str]:
    return [path] if SHARED_SECRET_LIKE_PATTERN.search(value) else []


def scan_provider_override(payload: Any, path: str = "$") -> list[str]:
    return scan_forbidden_payload_categorized(payload, path)[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]


def scan_forbidden_external_surfaces(payload: Any, path: str = "$") -> list[str]:
    scan = scan_forbidden_payload_categorized(payload, path)
    return dedupe_scan_findings(
        scan[OrganSafetyScanCategory.EXTERNAL_ACTION.value]
        + scan[OrganSafetyScanCategory.BROWSER_DANGEROUS.value]
        + scan[OrganSafetyScanCategory.CREDENTIAL_DANGEROUS.value]
    )


def merge_scan_results(*results: OrganSafetyScanResult) -> OrganSafetyScanResult:
    merged = _empty_result()
    for result in results:
        for category in merged:
            merged[category].extend(result.get(category, []))
    return _dedupe_result(merged)


def dedupe_scan_findings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _scan_value(value: Any, path: str, result: OrganSafetyScanResult, *, negative_control: bool) -> None:
    dumped = _model_dump(value)
    if dumped is not value:
        _scan_value(dumped, path, result, negative_control=negative_control)
        return

    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            child_path = f"{path}.{key}" if path else str(key)
            child_negative = negative_control or normalized_key in SHARED_NEGATIVE_CONTROL_SAFE_KEYS
            if child_negative:
                _scan_negative_control_value(item, child_path, result)
                continue
            _scan_key(normalized_key, child_path, item, result)
            _scan_value(item, child_path, result, negative_control=False)
        return

    if isinstance(value, list | tuple | set):
        for index, item in enumerate(value):
            _scan_value(item, f"{path}[{index}]", result, negative_control=negative_control)
        return

    if isinstance(value, str):
        _scan_string(value, path, result, include_text_markers=not negative_control)


def _scan_negative_control_value(value: Any, path: str, result: OrganSafetyScanResult) -> None:
    dumped = _model_dump(value)
    if dumped is not value:
        _scan_negative_control_value(dumped, path, result)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            child_path = f"{path}.{key}" if path else str(key)
            if normalized_key in SHARED_FORBIDDEN_SECRET_KEYS and _truthy_payload(item):
                _add(result, OrganSafetyScanCategory.SECRET, child_path)
            _scan_negative_control_value(item, child_path, result)
        return
    if isinstance(value, list | tuple | set):
        for index, item in enumerate(value):
            _scan_negative_control_value(item, f"{path}[{index}]", result)
        return
    if isinstance(value, str):
        _scan_string(value, path, result, include_text_markers=False)


def _scan_key(normalized_key: str, path: str, value: Any, result: OrganSafetyScanResult) -> None:
    if not _truthy_payload(value):
        return
    if normalized_key in SHARED_FORBIDDEN_SECRET_KEYS:
        _add(result, OrganSafetyScanCategory.SECRET, path)
    if normalized_key in SHARED_PROVIDER_OVERRIDE_KEYS:
        _add(result, OrganSafetyScanCategory.PROVIDER_OVERRIDE, path)
    if normalized_key in SHARED_AUTHORITY_EXPANSION_KEYS:
        _add(result, OrganSafetyScanCategory.AUTHORITY_EXPANSION, path)
    if normalized_key in SHARED_EXTERNAL_ACTION_KEYS:
        _add(result, OrganSafetyScanCategory.EXTERNAL_ACTION, path)
    if normalized_key in SHARED_BROWSER_DANGEROUS_KEYS:
        _add(result, OrganSafetyScanCategory.BROWSER_DANGEROUS, path)
    if normalized_key in SHARED_CREDENTIAL_DANGEROUS_KEYS:
        _add(result, OrganSafetyScanCategory.CREDENTIAL_DANGEROUS, path)
    if normalized_key in SHARED_RUNTIME_FORBIDDEN_KEYS:
        _add(result, OrganSafetyScanCategory.UNSAFE_PAYLOAD, path)


def _scan_string(value: str, path: str, result: OrganSafetyScanResult, *, include_text_markers: bool) -> None:
    if SHARED_SECRET_LIKE_PATTERN.search(value):
        _add(result, OrganSafetyScanCategory.SECRET, path)
    if not include_text_markers:
        return
    lowered = value.lower()
    for category, markers in _FORBIDDEN_TEXT_BY_CATEGORY.items():
        if any(marker in lowered for marker in markers):
            _add(result, category, path)
            return
    if any(marker in lowered for marker in SHARED_RUNTIME_FORBIDDEN_TEXT):
        _add(result, OrganSafetyScanCategory.UNSAFE_PAYLOAD, path)


def _add(result: OrganSafetyScanResult, category: OrganSafetyScanCategory, path: str) -> None:
    result[category.value].append(path)
    result[OrganSafetyScanCategory.ALL.value].append(path)
    if category in {
        OrganSafetyScanCategory.EXTERNAL_ACTION,
        OrganSafetyScanCategory.BROWSER_DANGEROUS,
        OrganSafetyScanCategory.CREDENTIAL_DANGEROUS,
    }:
        result[OrganSafetyScanCategory.FORBIDDEN_SURFACE.value].append(path)


def _empty_result() -> OrganSafetyScanResult:
    return {category.value: [] for category in OrganSafetyScanCategory}


def _dedupe_result(result: OrganSafetyScanResult) -> OrganSafetyScanResult:
    return {category.value: dedupe_scan_findings(result.get(category.value, [])) for category in OrganSafetyScanCategory}


def _normalize_key(key: Any) -> str:
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")


def _truthy_payload(value: Any) -> bool:
    return value not in (None, False, "", [], {})


def _model_dump(value: Any) -> Any:
    if isinstance(value, (str, bytes, bytearray, int, float, bool, type(None))):
        return value
    dumper = getattr(value, "model_dump", None)
    if not callable(dumper):
        return value
    try:
        return dumper(mode="python")
    except TypeError:
        return dumper()
