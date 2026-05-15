"""``PerformanceTrace`` — per-action timing/cost record (Phase A — Measurement Foundation).

This module defines the canonical measurement record emitted by
``LatencyProfiler`` for every instrumented action. The trace is an immutable
(``frozen=True``) pydantic model carrying only timing, byte, token, cache,
organ-latency, and prefill/decode counters — no payload bytes, no secrets.

The ``LatencyProfiler`` (Task 2.5) attaches every successfully constructed
``PerformanceTrace`` to the existing ``EventBus`` via the
``PERFORMANCE_TRACE_EMITTED`` event (registered in Task 1.2). The receipt
shape (Task 2.3) embeds this trace.

Property 1 of the spec — *PerformanceTrace shape is total and non-negative* —
is validated by Task 2.2's Hypothesis property test; the model itself is the
construction-time gate that makes that property reachable: every numeric
counter is constrained to ``ge=0`` at construction, ``error``/``error_category``
are enforced consistent by a ``model_validator``, and the whole record is
``frozen``.

Requirements covered: 1.1, 1.7, 10.9, 12.8.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import ConfigDict, Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class PerformanceSeverity(StrEnum):
    """Severity classification for a ``PerformanceTrace``.

    ``CRITICAL`` is reserved for safety-invariant violations (Requirement
    12.8): authority expansion attempts, raw-secret leakage detections,
    kill-switch bypass attempts, and similar. Routine successful actions
    SHALL be ``INFO``; soft-degradation events (e.g., cache miss above a
    warning threshold) MAY be ``WARNING``.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PerformanceTrace(SentinelModel):
    """Immutable per-action measurement record attached to the EventBus.

    All eleven numeric counters are non-negative integers (Requirement 1.1).
    Fields not applicable to the action type are recorded as ``0`` rather
    than omitted, so the trace shape is total — every instrumented action
    yields a record with all eleven counters populated.

    On exception or timeout (Requirement 1.7), the trace is still emitted
    with timing fields populated up to the point of failure, ``error=True``,
    and a non-empty ``error_category``. ``error=False`` requires
    ``error_category is None``; the two fields are kept consistent by a
    ``model_validator``.

    Token counters (``tokens_in``, ``tokens_out``) feed into per-receipt and
    per-mission budget bookkeeping (Requirement 10.9). Safety-invariant
    violations carry ``severity=PerformanceSeverity.CRITICAL`` and never
    contain raw secret substrings (Requirement 12.8) — secret-pattern
    rejection is enforced at ``PerformanceReceipt`` construction (Task 2.3),
    not here, because the trace itself only carries integer counters and
    short identifier strings.
    """

    # --- Identity -----------------------------------------------------------
    id: str = Field(default_factory=lambda: new_id("ptrace"))
    action_id: str
    mission_id: str
    organ_id: str | None = None
    action_type: str

    # --- Eleven non-negative numeric counters (Requirement 1.1) ------------
    queue_wait_ms: int = Field(ge=0)
    wall_ms: int = Field(ge=0)
    cpu_ms: int = Field(ge=0)
    bytes_in: int = Field(ge=0)
    bytes_out: int = Field(ge=0)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cache_hit: int = Field(ge=0)
    cache_miss: int = Field(ge=0)
    organ_latency_ms: int = Field(ge=0)
    model_prefill_decode_ms: int = Field(ge=0)

    # --- Error & severity (Requirements 1.7, 12.8) -------------------------
    error: bool = False
    error_category: str | None = None
    severity: PerformanceSeverity = PerformanceSeverity.INFO

    # ``extra='forbid'`` is inherited from ``SentinelModel`` and preserved
    # here; ``frozen=True`` makes the model immutable post-construction so
    # downstream consumers (EventBus subscribers, aggregators, receipts)
    # cannot mutate counters in flight.
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)

    @model_validator(mode="after")
    def _validate_error_consistency(self) -> Self:
        """Enforce that ``error`` and ``error_category`` are jointly consistent.

        - ``error=True``  → ``error_category`` MUST be a non-empty string.
        - ``error=False`` → ``error_category`` MUST be ``None``.

        This matches Property 1's "failing actions set ``error=True`` plus
        ``error_category``" clause; the model itself rejects inconsistent
        combinations at construction time so the property test can rely on
        the invariant rather than re-checking it.
        """
        if self.error:
            if not isinstance(self.error_category, str) or not self.error_category.strip():
                raise ValueError(
                    "PerformanceTrace.error=True requires a non-empty error_category."
                )
        else:
            if self.error_category is not None:
                raise ValueError(
                    "PerformanceTrace.error=False requires error_category to be None."
                )
        return self


__all__ = ["PerformanceSeverity", "PerformanceTrace"]
