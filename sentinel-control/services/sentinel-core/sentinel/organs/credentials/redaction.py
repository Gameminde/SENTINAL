from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]+", re.IGNORECASE),
    re.compile(r"bearer\s+[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"secret[_-]?[A-Za-z0-9_-]*", re.IGNORECASE),
]


class CredentialTraceRedactor:
    def redact(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {key: self.redact(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [self.redact(value) for value in payload]
        if isinstance(payload, str):
            redacted = payload
            for pattern in SECRET_PATTERNS:
                redacted = pattern.sub("[REDACTED_SECRET]", redacted)
            return redacted
        return payload
