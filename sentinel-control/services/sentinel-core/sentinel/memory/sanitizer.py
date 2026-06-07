from __future__ import annotations

import re
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.shared.safety_scanner import scan_forbidden_payload_flat


_INSTRUCTION_SHAPED_MEMORY = re.compile(
    r"\b(ignore|disregard|override)\b.{0,80}\b(instruction|policy|authority|permission)\b"
    r"|\b(execute|run|call|submit|send|unlock|grant)\s+(now|tool|organ|authority|credential)\b"
    r"|\b(prior|previous|standing)\s+(approval|permission|authorization)\s+(exists|is|was|has)\b"
    r"|\b(place|put|add|include|mark|state|claim|assert)\b.{0,100}"
    r"\b(allowed\s+list|approved|authorized|prior\s+approval|permission)\b"
    r"|\b(treat|consider)\b.{0,80}\b(approved|authorized|permitted)\b"
    r"|\bsystem\s+prompt\b",
    re.IGNORECASE | re.DOTALL,
)


def sanitize_memory_payload(payload: Any) -> tuple[Any, list[str], str]:
    redacted = redact_operator_value(payload)
    rejected_paths = scan_forbidden_payload_flat(redacted)
    return redacted, rejected_paths, stable_hash(redacted)


def sanitize_memory_text(value: str) -> str:
    return redact_operator_text(value)


def memory_text_rejection_reasons(value: str) -> list[str]:
    if _INSTRUCTION_SHAPED_MEMORY.search(value):
        return ["instruction_shaped_memory"]
    return []
