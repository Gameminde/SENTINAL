from __future__ import annotations

from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.shared.safety_scanner import (
    SHARED_BROWSER_DANGEROUS_KEYS,
    SHARED_CREDENTIAL_DANGEROUS_KEYS,
    SHARED_FORBIDDEN_SECRET_KEYS,
    SHARED_PROVIDER_OVERRIDE_KEYS,
    SHARED_RUNTIME_FORBIDDEN_KEYS,
)


_TELEMETRY_REDACTED_KEYS = {
    *SHARED_BROWSER_DANGEROUS_KEYS,
    *SHARED_CREDENTIAL_DANGEROUS_KEYS,
    *SHARED_FORBIDDEN_SECRET_KEYS,
    *SHARED_PROVIDER_OVERRIDE_KEYS,
    *SHARED_RUNTIME_FORBIDDEN_KEYS,
    "authorization",
    "chain_of_thought",
    "coT",
    "co_t",
    "credential_value",
    "hidden_tool_payload",
    "prompt",
    "prompt_text",
    "provider_response",
    "raw_prompt",
    "raw_response",
    "reasoning",
    "thinking",
    "tool_calls",
}


def sanitize_telemetry_text(value: str) -> tuple[str, bool]:
    redacted = redact_operator_text(value)
    return redacted, redacted != value


def sanitize_telemetry_value(value: Any, *, path: str = "$") -> tuple[Any, bool, list[str]]:
    redaction_paths: list[str] = []
    sanitized, hit = _sanitize_telemetry_value(value, path=path, redaction_paths=redaction_paths)
    return sanitized, hit, redaction_paths


def sanitize_telemetry_refs(values: Any) -> list[str]:
    return sanitize_operator_refs(values)


def _sanitize_telemetry_value(
    value: Any,
    *,
    path: str,
    redaction_paths: list[str],
) -> tuple[Any, bool]:
    if hasattr(value, "safe_model_dump"):
        value = value.safe_model_dump()
    elif hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")

    if isinstance(value, str):
        redacted, hit = sanitize_telemetry_text(value)
        if hit:
            redaction_paths.append(path)
        return redacted, hit

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        hit = False
        for key, item in value.items():
            normalized_key = _normalize_key(str(key))
            child_path = f"{path}.{key}" if path else str(key)
            if normalized_key in _TELEMETRY_REDACTED_KEYS:
                hit = True
                redaction_paths.append(child_path)
                sanitized[str(key)] = f"[REDACTED_HASH:{stable_hash(item)}]"
                continue
            child_value, child_hit = _sanitize_telemetry_value(
                item,
                path=child_path,
                redaction_paths=redaction_paths,
            )
            sanitized[str(key)] = child_value
            hit = hit or child_hit
        return sanitized, hit

    if isinstance(value, list | tuple | set):
        sanitized_list: list[Any] = []
        hit = False
        for index, item in enumerate(value):
            child_value, child_hit = _sanitize_telemetry_value(
                item,
                path=f"{path}[{index}]",
                redaction_paths=redaction_paths,
            )
            sanitized_list.append(child_value)
            hit = hit or child_hit
        return sanitized_list, hit

    return value, False


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")
