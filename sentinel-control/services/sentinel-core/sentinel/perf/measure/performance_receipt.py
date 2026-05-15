"""``PerformanceReceipt`` — append-only, sanitized, frozen receipt for a completed action.

This module defines the canonical receipt model emitted after every
instrumented action completes. The receipt embeds a ``PerformanceTrace``
(Task 2.1) and adds cost, budget, cache, scheduling, timeout, and safety
fields. It is immutable (``frozen=True``) and self-validating: construction
rejects authority expansion, raw-secret leakage, and hash mismatches.

The ``model_validator`` reuses the canonical ``sanitize_context_text``
sanitizer from ``sentinel.agent.evidence_ranker`` to reject any string
field (including embedded trace string fields) that would leak raw secrets.

Requirements covered: 1.2, 1.3, 8.6, 9.4, 10.9, 12.1, 12.8.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Iterator, Self

from pydantic import ConfigDict, Field, model_validator

from sentinel.agent.evidence_ranker import sanitize_context_text
from sentinel.perf.measure.performance_trace import PerformanceTrace
from sentinel.shared.models import SentinelModel, new_id


_VALID_CACHE_TYPES: set[str | None] = {"context", "prompt", "frame", None}


def _flat_string_fields(obj: SentinelModel) -> Iterator[tuple[str, str]]:
    """Yield ``(field_name, value)`` for all string-typed fields on *obj* and nested models.

    Skips ``None`` values. For the ``PerformanceReceipt`` this iterates both
    the receipt's own string fields and the embedded ``PerformanceTrace``
    string fields, ensuring the sanitizer covers the full surface.
    """
    for field_name, field_info in type(obj).model_fields.items():
        value = getattr(obj, field_name)
        if value is None:
            continue
        if isinstance(value, str):
            yield field_name, value
        elif isinstance(value, SentinelModel):
            for nested_name, nested_value in _flat_string_fields(value):
                yield f"{field_name}.{nested_name}", nested_value


class PerformanceReceipt(SentinelModel):
    """Append-only, sanitized, frozen receipt for a completed action.

    Requirements: 1.2, 1.3, 8.6, 9.4, 10.9, 12.1, 12.8
    """

    # --- Identity -----------------------------------------------------------
    id: str = Field(default_factory=lambda: new_id("pr"))
    mission_id: str
    action_id: str
    organ_id: str | None = None
    action: str

    # --- Embedded trace -----------------------------------------------------
    trace: PerformanceTrace

    # --- Cost ---------------------------------------------------------------
    estimated_cost_usd: Decimal = Field(default=Decimal("0"), max_digits=20, decimal_places=6)
    model_id: str | None = None

    # --- Budget -------------------------------------------------------------
    budget_remaining: int = Field(ge=0)
    budget_limit: int = Field(ge=0)

    # --- Cache/scheduling context (optional) --------------------------------
    cache_type: str | None = None  # "context" | "prompt" | "frame" | None
    backpressure_reason: str | None = None
    queue_depth_at_receipt: int | None = None

    # --- Timeout / cancel ---------------------------------------------------
    deadline_ms: int | None = None
    elapsed_ms: int | None = None

    # --- Safety invariants (never True for a valid receipt) -----------------
    authority_expansion: bool = False
    raw_secret_leakage: bool = False

    # --- Integrity ----------------------------------------------------------
    receipt_hash: str = ""
    created_at: datetime

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Enforce safety invariants, sanitize strings, validate cache_type, and seal hash."""
        # 1. Reject authority expansion
        if self.authority_expansion:
            raise ValueError("PerformanceReceipt cannot expand authority.")

        # 2. Sanitize all string fields (including embedded trace)
        for field_name, value in _flat_string_fields(self):
            if sanitize_context_text(value) != value:
                raise ValueError(
                    f"PerformanceReceipt contains raw secret in {field_name}"
                )

        # 3. Validate cache_type constraint
        if self.cache_type not in _VALID_CACHE_TYPES:
            raise ValueError(
                f"cache_type must be one of {{'context', 'prompt', 'frame', None}}, "
                f"got {self.cache_type!r}"
            )

        # 4. Compute and verify receipt hash
        expected = self._compute_receipt_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("PerformanceReceipt hash mismatch.")
        object.__setattr__(self, "receipt_hash", expected)

        return self

    def _compute_receipt_hash(self) -> str:
        """Compute a deterministic SHA-256 hash of the receipt (excluding ``receipt_hash``)."""
        payload = self.model_dump(mode="json", exclude={"receipt_hash"})
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
            ensure_ascii=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["PerformanceReceipt"]
