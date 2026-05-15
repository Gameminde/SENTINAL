"""``ToolCallQueue`` — three-level priority queue for organ tool calls (Phase D).

This module is the bounded, in-memory work queue that backs
``AsyncOrganScheduler`` (Task 8.4). It is intentionally a *plain data
structure*: it owns the FIFO/priority ordering and three queryable metrics,
and nothing else. It does not emit EventBus events, does not enforce
authority, does not enforce kill-switch state, does not consult the
``MissionAuthorityEnvelope``, and does not run any organ. Those concerns
live one layer up:

* ``BackpressureController`` (Task 8.2) decides whether a submission is
  admissible and emits ``QUEUE_BACKPRESSURE_APPLIED`` /
  ``QUEUE_BACKPRESSURE_CLEARED``.
* ``AsyncOrganScheduler`` (Task 8.4) consults authority/kill-switch,
  emits success/failure/timeout/cancellation receipts and completion
  events, and calls ``note_completion`` on this queue when an action
  finishes (because only the scheduler knows when an action has actually
  finished — the queue itself only sees enqueue and dequeue).

Three priority levels (Requirement 7.6)
---------------------------------------
``Priority.CRITICAL = 0``, ``Priority.NORMAL = 1``, ``Priority.LOW = 2``.
Lower integer value means higher priority. ``dequeue`` always pops from
the highest-priority non-empty deque first (CRITICAL → NORMAL → LOW),
and items at the same priority are FIFO. This matches the design's
``IntEnum`` convention and Property 9's higher-priority-first invariant.

Three metrics (Requirement 7.7)
-------------------------------
``depth``, ``estimated_wait_ms``, and ``per_organ_concurrency`` are
recomputed (or maintained) on every enqueue and dequeue so callers always
read a fresh value:

* ``depth()`` — total queued items across all three priority deques.
* ``estimated_wait_ms()`` — sum of ``estimated_cost_ms`` across all
  enqueued items. The walk is in priority order (CRITICAL first) so the
  resulting integer matches an estimate of "how long until the queue
  fully drains under unloaded conditions". This is a documented
  heuristic, not a guarantee.
* ``per_organ_concurrency()`` — ``{organ_id: in_flight_count}`` for
  actions that have been dequeued but not yet reported complete via
  ``note_completion``. The queue only tracks in-flight; the caller is
  responsible for completion notification.

Bounded depth (Requirement 8.1)
-------------------------------
``max_depth`` (default 1000) is the total cap across all three priority
deques. ``enqueue`` rejects with ``EnqueueOutcome(accepted=False,
reason='queue_full', position=-1, ...)`` when the queue is full and
**does not append** the item. The corresponding
``QUEUE_BACKPRESSURE_APPLIED`` event is the responsibility of
``BackpressureController`` — see module docstring above for the layering
rationale.

Frozen items, by-reference sharing
----------------------------------
``QueuedAction`` is a frozen pydantic model, so it is safe to share by
reference between the queue, the scheduler, and any subscribers. The
queue does not deep-copy on enqueue or dequeue.

Mission cancellation
--------------------
``cancel_mission(mission_id)`` removes every queued item whose
``mission_id`` matches and returns the count removed. It does **not**
touch in-flight counts (those are still owned by the scheduler) and
does **not** emit cancellation receipts (those are emitted by
``AsyncOrganScheduler.cancel_mission``). The integer return value lets
the scheduler report how many queued actions were dropped.

Requirements covered: 7.6, 7.7, 8.1, 8.2.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from enum import IntEnum

from pydantic import ConfigDict, Field

from sentinel.shared.models import SentinelModel


class Priority(IntEnum):
    """Three discrete priority levels for queued organ actions.

    Lower integer value means higher priority — ``CRITICAL`` runs before
    ``NORMAL`` runs before ``LOW``. Mirrors ``AsyncOrganScheduler.Priority``
    in the design (Task 8.4) so callers can pass the same enum to both.

    Requirement 7.6.
    """

    CRITICAL = 0
    NORMAL = 1
    LOW = 2


class QueuedAction(SentinelModel):
    """Immutable record describing a single enqueued organ action.

    Carries only short identifier strings, the priority level, the
    deadline (absolute or relative — interpretation is the caller's
    contract; the queue does not consult it), the monotonic-clock
    enqueue timestamp, and a heuristic ``estimated_cost_ms`` used by
    ``ToolCallQueue.estimated_wait_ms``. The queue does not store
    payload bytes; full action context lives in the ``OrganAction``
    object the scheduler resolves on dequeue.

    The model is frozen so it is safe to share by reference between
    the queue, the scheduler, and any EventBus subscribers without
    defensive copies.
    """

    action_id: str
    mission_id: str
    organ_id: str
    action_type: str
    priority: Priority
    deadline_ms: int = Field(ge=0)
    enqueued_at_ns: int = Field(ge=0)
    estimated_cost_ms: int = Field(default=10, ge=0)

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class EnqueueOutcome(SentinelModel):
    """Result of a single ``ToolCallQueue.enqueue`` call.

    * ``accepted`` — ``True`` iff the item was appended to a priority deque.
    * ``reason`` — short tag string. Currently ``"queued"`` on success and
      ``"queue_full"`` on rejection. Additional rejection tags MAY be added
      by callers (e.g. ``BackpressureController``) layered on top of this
      queue.
    * ``position`` — 0-indexed depth at the moment of enqueue (i.e. the
      newly-appended item's position in the ordered drain sequence). Only
      meaningful when ``accepted=True``; rejection records ``-1``.
    * ``estimated_wait_ms`` — the queue's ``estimated_wait_ms`` snapshot
      taken at the moment ``enqueue`` returned. Heuristic; documented as
      approximate.
    """

    accepted: bool
    reason: str
    position: int
    estimated_wait_ms: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class ToolCallQueue:
    """Three-level priority queue with FIFO semantics inside each level.

    Internal storage is three ``collections.deque`` instances keyed by
    ``Priority``; this gives O(1) append on the right and O(1) popleft on
    the left, which is what the FIFO-within-priority contract requires.
    All metrics (``depth``, ``estimated_wait_ms``, ``per_organ_concurrency``)
    are computed from the live deques and the in-flight counter map, so
    they reflect the current state on every call (Requirement 7.7).

    The queue is single-threaded: Phase D runs on a single asyncio event
    loop, and ``enqueue``/``dequeue``/``note_completion``/``cancel_mission``
    must be called from that loop. No locks are introduced.

    No events are emitted from this layer — see module docstring for the
    reasoning. ``BackpressureController`` and ``AsyncOrganScheduler`` own
    all event emission for queue-related state changes.
    """

    def __init__(
        self,
        *,
        max_depth: int = 1000,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if max_depth <= 0:
            raise ValueError("ToolCallQueue.max_depth must be a positive integer.")
        self._max_depth: int = max_depth
        self._clock: Callable[[], int] = clock
        # One FIFO deque per priority level. Keyed by ``Priority`` itself
        # so iteration order matches enum order (CRITICAL → NORMAL → LOW).
        self._deques: dict[Priority, deque[QueuedAction]] = {
            Priority.CRITICAL: deque(),
            Priority.NORMAL: deque(),
            Priority.LOW: deque(),
        }
        # ``per_organ_concurrency`` ground truth. Incremented on dequeue,
        # decremented on ``note_completion``. Entries at zero are removed
        # so the returned dict only lists organs with active in-flight
        # actions.
        self._per_organ_in_flight: dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # Metrics — Requirement 7.7. Recomputed on every call so callers
    # always observe the current state.
    # ------------------------------------------------------------------ #

    def depth(self) -> int:
        """Total number of queued items across all three priority levels."""
        return sum(len(q) for q in self._deques.values())

    def estimated_wait_ms(self) -> int:
        """Sum of ``estimated_cost_ms`` across all enqueued items.

        Walks deques in priority order (CRITICAL → NORMAL → LOW). The
        resulting integer is a documented heuristic — under perfectly
        sequential drainage with no parallelism it equals the worst-case
        time to fully drain the queue. With parallel execution or
        variable per-action cost it is an upper-bound estimate only.
        """
        total = 0
        for priority in Priority:
            for item in self._deques[priority]:
                total += item.estimated_cost_ms
        return total

    def per_organ_concurrency(self) -> dict[str, int]:
        """Defensive copy of the in-flight count map.

        The returned dict is safe to mutate by the caller — internal state
        is unaffected. Only organs with at least one in-flight action are
        present; entries at zero are pruned by ``note_completion``.
        """
        return dict(self._per_organ_in_flight)

    # ------------------------------------------------------------------ #
    # Enqueue / dequeue — the two operations that update all three
    # metrics (Requirement 7.7).
    # ------------------------------------------------------------------ #

    def enqueue(self, item: QueuedAction) -> EnqueueOutcome:
        """Append ``item`` to its priority deque, or reject if the queue is full.

        Rejection (``depth() >= max_depth``) returns an
        ``EnqueueOutcome(accepted=False, reason='queue_full',
        position=-1, ...)`` and **does not append**. The
        ``QUEUE_BACKPRESSURE_APPLIED`` event for this rejection is
        emitted one layer up by ``BackpressureController``.

        Success returns an ``EnqueueOutcome`` whose ``position`` is the
        0-indexed total depth of the queue immediately after the append
        (so the just-enqueued item's drain-order index) and whose
        ``estimated_wait_ms`` is the post-append heuristic.
        """
        if self.depth() >= self._max_depth:
            return EnqueueOutcome(
                accepted=False,
                reason="queue_full",
                position=-1,
                estimated_wait_ms=self.estimated_wait_ms(),
            )
        self._deques[item.priority].append(item)
        new_depth = self.depth()
        return EnqueueOutcome(
            accepted=True,
            reason="queued",
            position=new_depth - 1,
            estimated_wait_ms=self.estimated_wait_ms(),
        )

    def dequeue(self) -> QueuedAction | None:
        """Pop the next item to run, or ``None`` if every deque is empty.

        Highest-priority non-empty deque first (CRITICAL → NORMAL → LOW),
        FIFO within each priority. Increments
        ``per_organ_concurrency[item.organ_id]`` because the action is
        now considered in-flight; the caller is responsible for invoking
        ``note_completion(item.organ_id)`` when the action eventually
        finishes (success, failure, timeout, or cancellation — all four
        outcomes release the in-flight slot).
        """
        for priority in Priority:
            q = self._deques[priority]
            if q:
                item = q.popleft()
                self._per_organ_in_flight[item.organ_id] = (
                    self._per_organ_in_flight.get(item.organ_id, 0) + 1
                )
                return item
        return None

    # ------------------------------------------------------------------ #
    # Completion + cancellation — owned by the scheduler, plumbed
    # through these two methods.
    # ------------------------------------------------------------------ #

    def note_completion(self, organ_id: str) -> None:
        """Record that an in-flight action for ``organ_id`` finished.

        Decrements the in-flight count; removes the entry when the count
        reaches zero so ``per_organ_concurrency`` only ever lists organs
        with active work. Idempotent on missing or already-zero entries —
        the count is clamped at zero and no exception is raised — so the
        scheduler can safely call this from cancellation paths without
        having to track whether the action was ever dequeued.
        """
        current = self._per_organ_in_flight.get(organ_id, 0)
        if current <= 1:
            # Either the entry was missing, was 0, or was 1 — drop it.
            self._per_organ_in_flight.pop(organ_id, None)
            return
        self._per_organ_in_flight[organ_id] = current - 1

    def cancel_mission(self, mission_id: str) -> int:
        """Remove every queued item whose ``mission_id`` matches; return count.

        Walks all three deques and rebuilds each one without the matching
        items. Does **not** touch ``per_organ_concurrency`` (those counts
        belong to in-flight actions; only the scheduler knows when an
        in-flight action has actually been cancelled — at that point it
        calls ``note_completion``). Does **not** emit cancellation
        ``PerformanceReceipt`` events; that is the scheduler's job in
        ``AsyncOrganScheduler.cancel_mission`` (Task 8.4).
        """
        removed = 0
        for priority, q in self._deques.items():
            kept: deque[QueuedAction] = deque()
            for item in q:
                if item.mission_id == mission_id:
                    removed += 1
                else:
                    kept.append(item)
            self._deques[priority] = kept
        return removed


__all__ = [
    "EnqueueOutcome",
    "Priority",
    "QueuedAction",
    "ToolCallQueue",
]
