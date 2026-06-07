from __future__ import annotations

import re
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.safety_scanner import SHARED_SECRET_LIKE_PATTERN


_ENV_LIKE_PATTERN = re.compile(
    r"\b[A-Z][A-Z0-9_]{2,}\s*=\s*[A-Za-z0-9_\-./+=]{8,}",
    re.IGNORECASE,
)

_COOKIE_PATTERN = re.compile(
    r"\b(cookie|session[_-]?token|sessionid)\s*[:=]\s*[^;\s]{8,}",
    re.IGNORECASE,
)


def redact_operator_text(value: str) -> str:
    redacted = SHARED_SECRET_LIKE_PATTERN.sub("[REDACTED_SECRET]", value)
    redacted = _ENV_LIKE_PATTERN.sub("[REDACTED_SECRET]", redacted)
    return _COOKIE_PATTERN.sub("[REDACTED_SECRET]", redacted)


def redact_operator_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_operator_text(value)
    if isinstance(value, dict):
        return {
            redact_operator_text(str(key)): redact_operator_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_operator_value(item) for item in value]
    if isinstance(value, set):
        redacted_items = [redact_operator_value(item) for item in value]
        return sorted(redacted_items, key=lambda item: repr(item))
    return value


def sanitize_operator_ref(value: Any) -> str:
    text = str(value)
    redacted = redact_operator_text(text)
    if redacted != text:
        return f"redacted_ref:{stable_hash(text)}"
    return redacted


def sanitize_operator_refs(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    return list(dict.fromkeys(sanitize_operator_ref(value) for value in values if str(value)))
