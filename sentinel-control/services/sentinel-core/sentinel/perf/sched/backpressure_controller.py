"""``BackpressureController`` — envelope-bounded admission controller (Phase D).

This module is the **safety chokepoint** for the async-organ scheduler:
every submission flows through :meth:`BackpressureController.check_submission`
before it is allowed to enqueue, and every returned :class:`BackpressureDecision`
SHALL have all bounds less-than-or-equal-to the corresponding fields of the
governing :class:`MissionAuthorityEnvelope`. This is **Requirement 12.6**
("backpressure never expands authority"); the design's Property 10
property-based test (Task 8.6) verifies the invariant exhaustively. The
controller never widens any envelope field, never returns a configured
bound that exceeds the envelope, and never emits an event that contains
action body, organ output, or secret material.

Three rejection reasons + one accept reason
-------------------------------------------
* ``"within_envelope"`` — admitted; the queue, per-organ concurrency,
  and 1 s sliding byte rate are all under their effective caps.
* ``"queue_depth_overflow"`` — the bounded queue is at or above
  ``min(max_queue_depth, envelope.max_actions)``.
* ``"organ_concurrency_exceeded"`` — the requesting organ already has
  ``min(max_organ_concurrency, envelope.max_actions)`` in-flight actions.
* ``"byte_rate_exceeded"`` — admitting this action's byte estimate would
  push the per-organ 1 s byte rate above ``max_byte_rate_per_s``.

Events
------
On every rejection, ``QUEUE_BACKPRESSURE_APPLIED`` is appended to the
``EventBus`` with payload ``{organ_type, queue_depth, estimated_wait_ms,
reason}`` — exactly those four keys. ``QUEUE_BACKPRESSURE_CLEARED`` is
appended on a transition from "under pressure" to "not under pressure",
which by spec requires both predicates:

1. The controller was under pressure prior to this submission (i.e.
   :attr:`_under_pressure` was ``True``); **and**
2. The current queue depth is **strictly less** than the configured
   ``max_queue_depth`` cap.

If only the second condition holds (queue is low but no prior rejection),
the cleared event is **not** emitted; emitting it on every accept would
make the event meaningless and would violate Property 10's "exactly once
per cleared transition" contract.

Per-organ sliding byte-rate window
----------------------------------
:meth:`note_enqueue` records ``(timestamp_ns, byte_estimate)`` into a
per-organ ``deque``. :meth:`sliding_byte_rate` prunes any entries whose
timestamp is older than ``now_ns - 1_000_000_000`` (strictly less, so
the boundary entry at exactly 1 s ago is retained until the next ns
ticks past it) and returns the sum of the surviving byte estimates.
The clock is injectable so tests can drive the window deterministically.

Layering
--------
This module sits one layer **above** :class:`ToolCallQueue` and one layer
**below** :class:`AsyncOrganScheduler` (Task 8.4): the queue owns FIFO
ordering and metrics, the scheduler owns organ execution, and the
controller owns admission decisions and the two backpressure events.
This module never modifies the queue and never executes any organ.

Requirements covered: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.6.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.sched.tool_call_queue import ToolCallQueue
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel

# 1 second expressed in nanoseconds; the byte-rate window length per
# Requirement 8.5. Constant rather than computed so the pruning code
# is unambiguously the same value used by the spec.
_ONE_SECOND_NS = 1_000_000_000


@runtime_checkable
class _OrganActionLike(Protocol):
    """Structural type for any action carrying an ``organ_id`` string.

    The controller consults nothing else from the action — not its body,
    not its parameters, not its expected output. Any object that exposes
    ``organ_id: str`` (including ``QueuedAction`` from :mod:`tool_call_queue`
    and the design's ``OrganAction``) is accepted. This deliberately keeps
    payload bytes out of the controller, which is part of why the emitted
    event payloads cannot accidentally contain action body or secrets.
    """

    @property
    def organ_id(self) -> str: ...  # pragma: no cover - structural marker


# Canonical reason tags. Centralized so callers (and the property test in
# Task 8.6) can compare against a single source of truth.
_REASON_WITHIN_ENVELOPE = "within_envelope"
_REASON_QUEUE_DEPTH_OVERFLOW = "queue_depth_overflow"
_REASON_ORGAN_CONCURRENCY_EXCEEDED = "organ_concurrency_exceeded"
_REASON_BYTE_RATE_EXCEEDED = "byte_rate_exceeded"


class BackpressureDecision(SentinelModel):
    """Result of a single :meth:`BackpressureController.check_submission` call.

    ``bounds_used`` is the **Requirement 12.6 enforcement chokepoint**.
    Every integer in this dict is the result of ``min(configured_bound,
    corresponding_envelope_field)``; downstream callers, audit tooling,
    and Property 10 (Task 8.6) all rely on the invariant that no value
    in ``bounds_used`` exceeds the matching envelope field. Any
    divergence is a safety regression and must fail tests, not be
    silently corrected.

    The model is frozen so a decision cannot be mutated after the
    controller releases it; this prevents downstream code from "patching
    up" a decision into a wider authorization than the controller granted.
    """

    accepted: bool
    reason: str
    organ_id: str | None = None
    queue_depth: int = Field(ge=0)
    estimated_wait_ms: int = Field(ge=0)
    # The effective bounds the controller applied for this decision. Keys
    # are stable identifiers; values are non-negative integers ≤ the
    # corresponding envelope field. See class docstring for the
    # Requirement 12.6 invariant.
    bounds_used: dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class BackpressureController:
    """Envelope-bounded admission controller for queued tool calls.

    See module docstring for the full event-emission and bound-clamping
    contract. The controller is single-threaded (Phase D runs on a single
    asyncio event loop) and holds no locks — all internal state mutations
    happen in the calling task's frame.

    Requirements covered: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.6.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        queue: ToolCallQueue,
        max_queue_depth: int = 1000,
        max_byte_rate_per_s: int = 100_000_000,
        max_organ_concurrency: int = 8,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if max_queue_depth <= 0:
            raise ValueError(
                "BackpressureController.max_queue_depth must be a positive integer."
            )
        if max_byte_rate_per_s < 0:
            raise ValueError(
                "BackpressureController.max_byte_rate_per_s must be non-negative."
            )
        if max_organ_concurrency <= 0:
            raise ValueError(
                "BackpressureController.max_organ_concurrency must be a positive integer."
            )
        self._event_bus: EventBus = event_bus
        self._queue: ToolCallQueue = queue
        self._max_queue_depth: int = max_queue_depth
        self._max_byte_rate_per_s: int = max_byte_rate_per_s
        self._max_organ_concurrency: int = max_organ_concurrency
        self._clock: Callable[[], int] = clock
        # Per-organ deque of (timestamp_ns, byte_estimate) tuples within the
        # 1s sliding window. Empty deques are pruned lazily on read.
        self._byte_window: dict[str, deque[tuple[int, int]]] = {}
        # Global "currently under pressure" flag. Set by any rejection,
        # cleared (and the CLEARED event emitted) on the next accept that
        # observes a queue depth below the configured cap. See module
        # docstring for the two-predicate CLEARED rule.
        self._under_pressure: bool = False

    # ------------------------------------------------------------------ #
    # Admission decision — the safety chokepoint.
    # ------------------------------------------------------------------ #

    def check_submission(
        self,
        action: _OrganActionLike,
        *,
        envelope: MissionAuthorityEnvelope,
        action_byte_estimate: int = 0,
    ) -> BackpressureDecision:
        """Decide whether ``action`` may be enqueued under ``envelope``.

        Never returns a decision whose ``bounds_used`` exceeds the
        corresponding envelope field — this is the Requirement 12.6
        enforcement point. Rejections emit ``QUEUE_BACKPRESSURE_APPLIED``
        with payload ``{organ_type, queue_depth, estimated_wait_ms,
        reason}`` and toggle ``_under_pressure`` to ``True``. Accepts
        emit ``QUEUE_BACKPRESSURE_CLEARED`` only when both predicates of
        the cleared-iff rule hold (see module docstring).
        """
        if action_byte_estimate < 0:
            raise ValueError("action_byte_estimate must be non-negative.")

        organ_id = action.organ_id

        # Requirement 12.6: clamp every bound to envelope.max_actions, the
        # envelope field most directly applicable to queue admission.
        # The envelope's max_actions is pydantic-validated >= 1, so the
        # effective caps are always >= 1 here.
        effective_queue_cap = min(self._max_queue_depth, envelope.max_actions)
        effective_concurrency_cap = min(
            self._max_organ_concurrency, envelope.max_actions
        )
        bounds_used: dict[str, int] = {
            "max_queue_depth": effective_queue_cap,
            "max_organ_concurrency": effective_concurrency_cap,
            "envelope_max_actions": envelope.max_actions,
        }

        queue_depth = self._queue.depth()
        estimated_wait_ms = self._queue.estimated_wait_ms()

        # 1) Queue-depth check (Requirement 8.1, 8.2).
        if queue_depth >= effective_queue_cap:
            return self._reject(
                organ_id=organ_id,
                reason=_REASON_QUEUE_DEPTH_OVERFLOW,
                queue_depth=queue_depth,
                estimated_wait_ms=estimated_wait_ms,
                bounds_used=bounds_used,
            )

        # 2) Per-organ concurrency check (Requirement 8.3).
        per_organ_in_flight = self._queue.per_organ_concurrency().get(organ_id, 0)
        if per_organ_in_flight >= effective_concurrency_cap:
            return self._reject(
                organ_id=organ_id,
                reason=_REASON_ORGAN_CONCURRENCY_EXCEEDED,
                queue_depth=queue_depth,
                estimated_wait_ms=estimated_wait_ms,
                bounds_used=bounds_used,
            )

        # 3) Byte-rate check (Requirement 8.5).
        projected_byte_rate = (
            self.sliding_byte_rate(organ_id) + action_byte_estimate
        )
        if projected_byte_rate > self._max_byte_rate_per_s:
            return self._reject(
                organ_id=organ_id,
                reason=_REASON_BYTE_RATE_EXCEEDED,
                queue_depth=queue_depth,
                estimated_wait_ms=estimated_wait_ms,
                bounds_used=bounds_used,
            )

        # Accept. Two-predicate CLEARED rule (Requirement 8.7): only emit
        # CLEARED if we were previously under pressure AND queue depth is
        # below the configured cap. The configured cap (not the
        # envelope-clamped effective cap) is intentional per task spec.
        if self._under_pressure and queue_depth < self._max_queue_depth:
            self._emit_cleared(organ_id=organ_id, queue_depth=queue_depth)
            self._under_pressure = False

        return BackpressureDecision(
            accepted=True,
            reason=_REASON_WITHIN_ENVELOPE,
            organ_id=organ_id,
            queue_depth=queue_depth,
            estimated_wait_ms=estimated_wait_ms,
            bounds_used=bounds_used,
        )

    # ------------------------------------------------------------------ #
    # Sliding byte-rate window — Requirement 8.5.
    # ------------------------------------------------------------------ #

    def note_enqueue(
        self, action: _OrganActionLike, byte_estimate: int
    ) -> None:
        """Record that ``byte_estimate`` bytes were just admitted for ``action``.

        Appends a ``(now_ns, byte_estimate)`` tuple to the per-organ
        deque, then prunes anything outside the 1 s window. Zero-byte
        estimates and negative inputs are rejected to avoid skewing the
        rate estimate. Callers SHOULD invoke this immediately after a
        successful :meth:`check_submission`+enqueue pair so the next
        admission decision sees an up-to-date rate.
        """
        if byte_estimate < 0:
            raise ValueError("byte_estimate must be non-negative.")
        if byte_estimate == 0:
            # Zero-byte entries don't change the rate; skipping them keeps
            # the deque small under high-frequency zero-byte traffic.
            return
        organ_id = action.organ_id
        window = self._byte_window.setdefault(organ_id, deque())
        now_ns = int(self._clock())
        window.append((now_ns, byte_estimate))
        self._prune(window, now_ns)

    def note_dequeue(self, action: _OrganActionLike) -> None:
        """Hook invoked when an action leaves the queue (no-op today).

        The byte-rate window represents bytes **admitted** in the last
        1 s, not bytes currently in flight, so dequeue does not change
        the window. Kept on the public surface to match the design's
        :class:`BackpressureController` shape and to leave a documented
        extension point if a future model needs in-flight tracking.
        """
        del action  # unused; documented contract
        return None

    def sliding_byte_rate(self, organ_id: str) -> int:
        """Return bytes admitted for ``organ_id`` within the last 1 s window.

        Prunes entries strictly older than ``now_ns - 1_000_000_000``
        before summing. The boundary entry at exactly 1 s ago is retained
        until the clock advances past it, which matches the "older than"
        wording in Requirement 8.5.
        """
        window = self._byte_window.get(organ_id)
        if not window:
            return 0
        now_ns = int(self._clock())
        self._prune(window, now_ns)
        if not window:
            # All entries fell out of the window during pruning.
            return 0
        return sum(byte_count for _, byte_count in window)

    # ------------------------------------------------------------------ #
    # Internal helpers.
    # ------------------------------------------------------------------ #

    def _reject(
        self,
        *,
        organ_id: str,
        reason: str,
        queue_depth: int,
        estimated_wait_ms: int,
        bounds_used: dict[str, int],
    ) -> BackpressureDecision:
        """Mark the controller as under pressure, emit APPLIED, return reject."""
        self._under_pressure = True
        # Event payload whitelist: exactly four keys, all primitives. No
        # action body, no organ output, no secrets. Keep this list in
        # lock-step with the module docstring; widening it is a safety
        # decision and must go through the design review.
        self._event_bus.append(
            AgentEventType.QUEUE_BACKPRESSURE_APPLIED,
            f"queue backpressure applied: {reason}",
            payload={
                "organ_type": organ_id,
                "queue_depth": queue_depth,
                "estimated_wait_ms": estimated_wait_ms,
                "reason": reason,
            },
        )
        return BackpressureDecision(
            accepted=False,
            reason=reason,
            organ_id=organ_id,
            queue_depth=queue_depth,
            estimated_wait_ms=estimated_wait_ms,
            bounds_used=bounds_used,
        )

    def _emit_cleared(self, *, organ_id: str, queue_depth: int) -> None:
        """Emit ``QUEUE_BACKPRESSURE_CLEARED`` with the two-key whitelist payload."""
        self._event_bus.append(
            AgentEventType.QUEUE_BACKPRESSURE_CLEARED,
            "queue backpressure cleared",
            payload={
                "organ_type": organ_id,
                "queue_depth": queue_depth,
            },
        )

    @staticmethod
    def _prune(window: deque[tuple[int, int]], now_ns: int) -> None:
        """Drop any entries with timestamp strictly older than 1 s ago."""
        cutoff_ns = now_ns - _ONE_SECOND_NS
        while window and window[0][0] < cutoff_ns:
            window.popleft()


__all__ = [
    "BackpressureController",
    "BackpressureDecision",
]
