from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from sentinel.shared.models import SentinelModel


SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_]+", re.IGNORECASE),
    re.compile(r"password\s*=\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*=\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"bearer[_-]?token\s*=\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"secret[_-]?[A-Za-z0-9_]*", re.IGNORECASE),
]


class SanitizedDesktopContext(SentinelModel):
    text: str
    redaction_count: int = 0
    redacted_labels: list[str] = Field(default_factory=list)


def redact_secret_like_text(value: str) -> SanitizedDesktopContext:
    text = value
    labels: list[str] = []
    count = 0
    for pattern in SECRET_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            count += len(matches)
            labels.append(pattern.pattern)
            text = pattern.sub("[REDACTED]", text)
    return SanitizedDesktopContext(text=text, redaction_count=count, redacted_labels=labels)


class ScreenContextSanitizer:
    def sanitize(self, context: dict[str, Any] | str) -> SanitizedDesktopContext:
        if isinstance(context, str):
            return redact_secret_like_text(context)
        text = " ".join(str(value) for _, value in sorted(context.items()))
        return redact_secret_like_text(text)
