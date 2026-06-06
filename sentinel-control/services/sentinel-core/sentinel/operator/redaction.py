from __future__ import annotations

import re
from typing import Any

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
