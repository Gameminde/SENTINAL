from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sanitize_metadata(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {str(k): sanitize_metadata(v) for k, v in sorted(payload.items(), key=lambda item: str(item[0]))}
    if isinstance(payload, list | tuple | set):
        return [sanitize_metadata(v) for v in payload]
    return payload
