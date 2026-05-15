"""``AsyncOrganScheduler`` — submit / completion / cancellation gateway (Task 8.4).

This module is the **central correctness chokepoint** for Phase D async organ
scheduling. Every organ action that the runtime wants to execute flows through
:meth:`AsyncOrganScheduler.submit`, which:

1. **Kill-switch gate** (Requirement 12.5) — rejects when ``kill_switch.triggered``
   or ``kill_switch.execution_allowed`` is False. Emits ``KILL_SWITCH_BLOCKED``
   plus a critical-severity rejection :class:`PerformanceReceipt`. Returns a
   :class:`SubmissionAck` with ``reason="kill_switch_blocked"``.
2. **Authority gate** (Requirement 12.5) — rejects when
   ``authority.execution_authorized`` is False or ``authority.dry_run_only`` is
   True. Emits ``AUTHORITY_VIOLATION`` plus a critical-severity rejection
   receipt. Returns a :class:`SubmissionAck` with ``reason="authority_denied"``.
3. **Backpressure gate** — delegates to the injected
   :class:`BackpressureController` and rejects with ``reason="backpressure_rejected"``
   when the envelope-bounded admission decision is not accepted. The
   ``QUEUE_BACKPRESSURE_APPLIED`` event is emitted by the controller, not here.
4. **Enqueue** — appends a :class:`QueuedAction` to the bounded
   :class:`ToolCallQueue`. A queue-full rejection (which is rare given the
   backpressure pre-check) is reported back as ``reason="queue_full"``.
5. **Schedule** — creates a per-action :class:`asyncio.Task` running
   :meth:`_run_action_wrapper`. ``submit`` then returns a queued
   :class:`SubmissionAck` *without awaiting organ execution*. This is the
   non-blocking contract of Requirement 7.1.

The wrapper task ultimately produces exactly one outcome event from the set
{success, failure, timeout, cancellation} and exactly one
:class:`PerformanceReceipt`. The wrapper is the **single source** of those
events — :meth:`cancel_mission` never emits cancellation events directly; it
only cancels the wrapper tasks and lets each wrapper's ``CancelledError``
handler fire. This guarantees no double-emit on cancellation, satisfying
Requirements 7.4, 7.5, 7.8.

Event payload whitelist
-----------------------
Every event emitted by this module carries **only** these keys:
``{action_id, mission_id, organ_id, reason, deadline_ms, elapsed_ms,
error_category}``. Action body, organ output bytes, payload arguments, and
secret material are never included. The :class:`PerformanceReceipt` model's
``model_validator`` applies the canonical ``sanitize_context_text`` to every
string field, so even short identifier strings that incidentally contain a
secret pattern are rejected at receipt construction.

Non-blocking contract
---------------------
``submit`` SHALL NOT ``await`` any organ I/O. The only awaitable step inside
``submit`` is the bounded enqueue → ``create_task`` sequence, both of which
return promptly. Property 9 (Task 8.5) verifies this with a Hypothesis FSM.

Requirements covered: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 12.5.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.dry_run import OrganDryRunReceipt
from sentinel.organs.kill_switch import OrganKillSwitch
from sentinel.perf.measure.latency_profiler import LatencyProfiler
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.perf.sched.backpressure_controller import BackpressureController
from sentinel.perf.sched.tool_call_queue import (
    Priority,
    QueuedAction,
    ToolCallQueue,
)
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


# ----- Reason tags ------------------------------------------------------------
# Centralized constants so callers and tests compare against a single source
# of truth. Keep these stable — they are part of the SubmissionAck contract.

_REASON_QUEUED = "queued"
_REASON_KILL_SWITCH_BLOCKED = "kill_switch_blocked"
_REASON_AUTHORITY_DENIED = "authority_denied"
_REASON_BACKPRESSURE_REJECTED = "backpressure_rejected"
_REASON_QUEUE_FULL = "queue_full"

_ERROR_CATEGORY_KILL_SWITCH = "kill_switch_blocked"
_ERROR_CATEGORY_AUTHORITY = "authority_denied"
_ERROR_CATEGORY_TIMEOUT = "deadline_exceeded"
_ERROR_CATEGORY_CANCELLED = "mission_cancelled"
_ERROR_CATEGORY_BACKPRESSURE = "backpressure_rejected"


# ----- Structural types -------------------------------------------------------


@runtime_checkable
class _OrganActionLike(Protocol):
    """Structural type for any organ action accepted by the scheduler.

    The scheduler reads only short identifier strings from the action object —
    never payload bytes, never organ output. Any object exposing the four
    required string properties is accepted, including the design's
    ``OrganAction`` and any test stub.
    """

    @property
    def action_id(self) -> str: ...  # pragma: no cover - structural marker

    @property
    def mission_id(self) -> str: ...  # pragma: no cover - structural marker

    @property
    def organ_id(self) -> str: ...  # pragma: no cover - structural marker

    @property
    def action_type(self) -> str: ...  # pragma: no cover - structural marker


# ----- SubmissionAck ----------------------------------------------------------


class SubmissionAck(SentinelModel):
    """Result of a single :meth:`AsyncOrganScheduler.submit` call.

    Frozen pydantic model — once produced by the scheduler, the caller cannot
    "patch up" an ack into a wider acceptance than the gates granted.

    * ``accepted`` — True iff the submission cleared all four gates
      (kill-switch, authority, backpressure, queue depth).
    * ``reason`` — short tag from a fixed set: ``"queued"``,
      ``"kill_switch_blocked"``, ``"authority_denied"``,
      ``"backpressure_rejected"``, or ``"queue_full"``.
    * ``position`` — 0-indexed queue position when accepted, ``-1`` on rejection.
    """

    accepted: bool
    reason: str
    action_id: str
    mission_id: str
    organ_id: str
    position: int = Field(default=-1)

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


# ----- AsyncOrganScheduler ----------------------------------------------------


async def _noop_organ_runner(action: _OrganActionLike) -> Any:
    """Default runner: succeeds immediately with an empty result.

    Used as a safe default when no ``organ_runner`` is injected (test paths,
    smoke checks). A production runtime SHALL inject the real organ
    dispatcher; the default is intentionally inert and never reaches into
    organ-specific logic.
    """
    del action  # explicit: we deliberately ignore the action body
    return None


class AsyncOrganScheduler:
    """Event-loop-based submission/completion scheduler with safety gates.

    Single-task-per-action model: each :meth:`submit` enqueues a
    :class:`QueuedAction` for depth/position metrics and creates one
    :class:`asyncio.Task` running :meth:`_run_action_wrapper`. The wrapper
    is the **single source of outcome events** for that action, ensuring no
    double-emit across the success / failure / timeout / cancellation
    branches.

    The scheduler is single-threaded (Phase D runs on a single asyncio event
    loop) and holds no locks — all internal mutations happen inside coroutine
    bodies on that loop.

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 12.5.
    """

    Priority = Priority  # re-export for callers passing the enum

    def __init__(
        self,
        *,
        event_bus: EventBus,
        queue: ToolCallQueue,
        backpressure: BackpressureController,
        latency_profiler: LatencyProfiler | None = None,
        cold_store: Any | None = None,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._event_bus: EventBus = event_bus
        self._queue: ToolCallQueue = queue
        self._backpressure: BackpressureController = backpressure
        self._latency_profiler: LatencyProfiler | None = latency_profiler
        self._cold_store: Any | None = cold_store
        self._clock: Callable[[], int] = clock
        # action_id -> asyncio.Task. Populated on submit, removed in the
        # wrapper's finally block. Used by cancel_mission to cancel both
        # queued (drainer not yet started organ_runner) and in-flight
        # (organ_runner running) actions uniformly.
        self._in_flight: dict[str, asyncio.Task[None]] = {}
        # mission_id -> set of action_ids submitted under that mission.
        # cancel_mission walks this set to cancel every still-active task.
        self._mission_to_actions: dict[str, set[str]] = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def submit(
        self,
        action: _OrganActionLike,
        *,
        authority: OrganAuthorityEnvelope,
        kill_switch: OrganKillSwitch,
        dry_run: OrganDryRunReceipt,
        deadline_ms: int,
        priority: Priority = Priority.NORMAL,
        organ_runner: Callable[[_OrganActionLike], Awaitable[Any]] | None = None,
        action_byte_estimate: int = 0,
        estimated_cost_ms: int = 10,
    ) -> SubmissionAck:
        """Run safety gates and schedule ``action`` for asynchronous execution.

        Non-blocking contract: this coroutine SHALL NOT ``await`` any organ
        I/O. The only awaitable touched here is :func:`asyncio.create_task`
        wrapping the per-action wrapper, which schedules without awaiting
        completion. The caller therefore observes a prompt return regardless
        of organ runtime cost.

        Returns a :class:`SubmissionAck` describing the outcome. On
        rejection, a critical-severity :class:`PerformanceReceipt` is built
        and emitted via ``PERFORMANCE_RECEIPT_RECORDED`` and the
        outcome-specific event (``KILL_SWITCH_BLOCKED`` or
        ``AUTHORITY_VIOLATION``) is appended.
        """
        if deadline_ms <= 0:
            raise ValueError("AsyncOrganScheduler.submit: deadline_ms must be positive.")

        action_id = action.action_id
        mission_id = action.mission_id
        organ_id = action.organ_id
        action_type = action.action_type

        # 1) Kill-switch gate (Requirement 12.5).
        # Reject before consulting authority so a triggered kill-switch is
        # always reported with that specific reason, even when authority
        # would also have failed. The kill-switch is the more severe
        # invariant; reporting it preserves operator clarity.
        if kill_switch.triggered or not kill_switch.execution_allowed:
            self._emit_rejection(
                event_type=AgentEventType.KILL_SWITCH_BLOCKED,
                summary="organ submission blocked by triggered kill switch",
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                reason=_REASON_KILL_SWITCH_BLOCKED,
                error_category=_ERROR_CATEGORY_KILL_SWITCH,
            )
            return SubmissionAck(
                accepted=False,
                reason=_REASON_KILL_SWITCH_BLOCKED,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                position=-1,
            )

        # 2) Authority gate (Requirement 12.5).
        # ``execution_authorized`` AND not ``dry_run_only`` are both required
        # for live execution; either failing is an authority denial.
        if not authority.execution_authorized or authority.dry_run_only:
            self._emit_rejection(
                event_type=AgentEventType.AUTHORITY_VIOLATION,
                summary="organ submission blocked: execution not authorized",
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                reason=_REASON_AUTHORITY_DENIED,
                error_category=_ERROR_CATEGORY_AUTHORITY,
            )
            return SubmissionAck(
                accepted=False,
                reason=_REASON_AUTHORITY_DENIED,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                position=-1,
            )

        # 3) Backpressure gate. The controller emits its own
        #    QUEUE_BACKPRESSURE_APPLIED event on rejection — we do not
        #    duplicate it here, but we still build a rejection receipt so
        #    the audit trail records the rejected submission.
        #    The controller's signature requires a MissionAuthorityEnvelope;
        #    we pass the OrganAuthorityEnvelope directly because the
        #    controller only consults ``envelope.max_actions``, which is
        #    present on both envelope shapes (Task 8.4 wiring note).
        decision = self._backpressure.check_submission(
            action,
            envelope=authority,  # type: ignore[arg-type]
            action_byte_estimate=action_byte_estimate,
        )
        if not decision.accepted:
            self._build_rejection_receipt(
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                error_category=_ERROR_CATEGORY_BACKPRESSURE,
                reason=decision.reason,
            )
            return SubmissionAck(
                accepted=False,
                reason=_REASON_BACKPRESSURE_REJECTED,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                position=-1,
            )

        # 4) Enqueue. Backpressure has already cleared us, so a queue-full
        #    rejection here is rare (concurrent enqueues racing past the
        #    bound); it still produces a properly-shaped rejection ack.
        qa = QueuedAction(
            action_id=action_id,
            mission_id=mission_id,
            organ_id=organ_id,
            action_type=action_type,
            priority=priority,
            deadline_ms=deadline_ms,
            enqueued_at_ns=int(self._clock()),
            estimated_cost_ms=max(0, estimated_cost_ms),
        )
        outcome = self._queue.enqueue(qa)
        if not outcome.accepted:
            self._build_rejection_receipt(
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                error_category=_ERROR_CATEGORY_BACKPRESSURE,
                reason=outcome.reason,
            )
            return SubmissionAck(
                accepted=False,
                reason=_REASON_QUEUE_FULL,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                position=-1,
            )

        # 5) Schedule the wrapper task. The wrapper owns the entire
        #    lifecycle (dequeue → run → emit outcome → release slot) and
        #    is the single source of outcome events for this action.
        runner = organ_runner if organ_runner is not None else _noop_organ_runner
        task: asyncio.Task[None] = asyncio.create_task(
            self._run_action_wrapper(
                action=action,
                organ_runner=runner,
                deadline_ms=deadline_ms,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
            )
        )
        self._in_flight[action_id] = task
        self._mission_to_actions.setdefault(mission_id, set()).add(action_id)

        return SubmissionAck(
            accepted=True,
            reason=_REASON_QUEUED,
            action_id=action_id,
            mission_id=mission_id,
            organ_id=organ_id,
            position=outcome.position,
        )

    def cancel_mission(self, mission_id: str) -> int:
        """Cancel every queued and in-flight action belonging to ``mission_id``.

        Returns the total count cancelled. The cancellation event for each
        action is emitted by that action's wrapper task in its
        ``CancelledError`` handler — :meth:`cancel_mission` itself does not
        emit cancellation events, which avoids double-emit.

        The queue's queued items are removed via
        :meth:`ToolCallQueue.cancel_mission` so subsequent depth metrics
        reflect the cancellation immediately.
        """
        # Drop queued items first so depth metrics are up to date the
        # instant the cancellation is observed by callers polling depth().
        # The number returned by the queue is informational only — we count
        # by the wrapper-task population below, which is the authoritative
        # set of submitted-but-not-yet-completed actions.
        self._queue.cancel_mission(mission_id)

        action_ids = list(self._mission_to_actions.get(mission_id, set()))
        cancelled_count = 0
        for action_id in action_ids:
            task = self._in_flight.get(action_id)
            if task is None:
                # Already completed between queue.cancel_mission and here.
                continue
            if task.done():
                continue
            task.cancel()
            cancelled_count += 1
        return cancelled_count

    # ------------------------------------------------------------------ #
    # Wrapper — single source of outcome events per action.
    # ------------------------------------------------------------------ #

    async def _run_action_wrapper(
        self,
        *,
        action: _OrganActionLike,
        organ_runner: Callable[[_OrganActionLike], Awaitable[Any]],
        deadline_ms: int,
        action_id: str,
        mission_id: str,
        organ_id: str,
        action_type: str,
    ) -> None:
        """Run ``organ_runner(action)`` under a deadline and emit one outcome.

        Branches on the four possible outcomes:

        * **Success** — ``organ_runner`` returns within the deadline. Emits
          ``ORGAN_EXECUTION_RECEIPT_RECORDED`` (the success completion event)
          plus a non-error :class:`PerformanceReceipt` via
          ``PERFORMANCE_RECEIPT_RECORDED``.
        * **Timeout** — ``asyncio.wait_for`` raises
          :class:`asyncio.TimeoutError`. Emits ``ORGAN_ACTION_TIMEOUT`` plus
          a critical-severity error receipt.
        * **Cancellation** — :class:`asyncio.CancelledError` propagates from
          the awaited runner. Emits ``ORGAN_ACTION_CANCELLED`` plus a
          warning-severity error receipt, then re-raises so the task is
          actually cancelled (asyncio invariant).
        * **Failure** — any other ``BaseException`` from ``organ_runner``.
          Emits ``ORGAN_ACTION_FAILED`` plus a critical-severity error
          receipt with ``error_category`` set to the exception class name.

        ``finally`` always releases the per-organ in-flight slot via
        :meth:`ToolCallQueue.note_completion` and removes the action from
        ``_in_flight``/``_mission_to_actions``, so cleanup is symmetric with
        the four outcome branches.
        """
        # Move the action from "queued" to "in-flight" in the queue's
        # accounting. ``dequeue()`` returns whatever item is at the top of
        # the priority deques — under normal sequential submission that is
        # this action's own QueuedAction; under priority shuffling it may
        # be a different item. Either way, the per-organ in-flight count
        # is updated correctly: we increment via the dequeue result and we
        # decrement via that same organ_id in the finally block.
        dequeued = self._queue.dequeue()
        slot_organ_id = dequeued.organ_id if dequeued is not None else None

        start_ns = self._clock()
        outcome_event_type: AgentEventType
        outcome_summary: str
        outcome_error: bool
        outcome_error_category: str | None
        outcome_severity: PerformanceSeverity

        try:
            await asyncio.wait_for(
                organ_runner(action),
                timeout=deadline_ms / 1000.0,
            )
        except asyncio.CancelledError:
            elapsed_ms = self._elapsed_ms_since(start_ns)
            outcome_event_type = AgentEventType.ORGAN_ACTION_CANCELLED
            outcome_summary = "organ action cancelled by mission cancellation"
            outcome_error = True
            outcome_error_category = _ERROR_CATEGORY_CANCELLED
            outcome_severity = PerformanceSeverity.WARNING
            self._emit_outcome(
                event_type=outcome_event_type,
                summary=outcome_summary,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                reason=_ERROR_CATEGORY_CANCELLED,
                error_category=outcome_error_category,
            )
            self._build_outcome_receipt(
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                error=outcome_error,
                error_category=outcome_error_category,
                severity=outcome_severity,
            )
            # Re-raise to honour the asyncio cancellation contract: the
            # task must transition to CANCELLED state, not COMPLETED.
            raise
        except asyncio.TimeoutError:
            elapsed_ms = self._elapsed_ms_since(start_ns)
            outcome_event_type = AgentEventType.ORGAN_ACTION_TIMEOUT
            outcome_summary = "organ action exceeded its deadline"
            outcome_error = True
            outcome_error_category = _ERROR_CATEGORY_TIMEOUT
            outcome_severity = PerformanceSeverity.CRITICAL
            self._emit_outcome(
                event_type=outcome_event_type,
                summary=outcome_summary,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                reason=_ERROR_CATEGORY_TIMEOUT,
                error_category=outcome_error_category,
            )
            self._build_outcome_receipt(
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                error=outcome_error,
                error_category=outcome_error_category,
                severity=outcome_severity,
            )
        except BaseException as exc:  # noqa: BLE001 - intentional broad catch for outcome routing
            elapsed_ms = self._elapsed_ms_since(start_ns)
            # Use the exception class name as the error_category. Names are
            # short identifiers (e.g. "RuntimeError", "ValueError") and do
            # not carry payload bytes; the receipt's sanitizer would reject
            # any class name that incidentally embeds a secret pattern.
            outcome_event_type = AgentEventType.ORGAN_ACTION_FAILED
            outcome_summary = "organ action failed"
            outcome_error = True
            outcome_error_category = type(exc).__name__
            outcome_severity = PerformanceSeverity.CRITICAL
            self._emit_outcome(
                event_type=outcome_event_type,
                summary=outcome_summary,
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                reason="organ_runner_exception",
                error_category=outcome_error_category,
            )
            self._build_outcome_receipt(
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                error=outcome_error,
                error_category=outcome_error_category,
                severity=outcome_severity,
            )
        else:
            # Success — and only success — emits the success completion
            # event. This honours the spec's explicit rule: "on success
            # emits a success completion event ONLY when the organ
            # actually succeeded". No success event is emitted on
            # rejection, timeout, failure, or cancellation paths.
            elapsed_ms = self._elapsed_ms_since(start_ns)
            self._emit_outcome(
                event_type=AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
                summary="organ action succeeded",
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                reason="success",
                error_category=None,
            )
            self._build_outcome_receipt(
                action_id=action_id,
                mission_id=mission_id,
                organ_id=organ_id,
                action_type=action_type,
                deadline_ms=deadline_ms,
                elapsed_ms=elapsed_ms,
                error=False,
                error_category=None,
                severity=PerformanceSeverity.INFO,
            )
        finally:
            # Always release the per-organ in-flight slot. Use the slot's
            # organ_id from the dequeue (which is what was tracked) so the
            # increment/decrement pair stays balanced even under priority
            # shuffling. If dequeue returned None (queue cancelled before
            # we ran), there's no slot to release.
            if slot_organ_id is not None:
                self._queue.note_completion(slot_organ_id)
            # Remove from tracking maps so cancel_mission cannot re-cancel
            # a completed task and so memory does not grow unboundedly.
            self._in_flight.pop(action_id, None)
            actions_for_mission = self._mission_to_actions.get(mission_id)
            if actions_for_mission is not None:
                actions_for_mission.discard(action_id)
                if not actions_for_mission:
                    self._mission_to_actions.pop(mission_id, None)

    # ------------------------------------------------------------------ #
    # Event emission helpers — payload whitelist enforced here.
    # ------------------------------------------------------------------ #

    def _emit_rejection(
        self,
        *,
        event_type: AgentEventType,
        summary: str,
        action_id: str,
        mission_id: str,
        organ_id: str,
        action_type: str,
        deadline_ms: int,
        reason: str,
        error_category: str,
    ) -> None:
        """Emit a kill-switch or authority rejection event + receipt."""
        self._event_bus.append(
            event_type,
            summary,
            payload={
                "action_id": action_id,
                "mission_id": mission_id,
                "organ_id": organ_id,
                "reason": reason,
            },
        )
        self._build_rejection_receipt(
            action_id=action_id,
            mission_id=mission_id,
            organ_id=organ_id,
            action_type=action_type,
            deadline_ms=deadline_ms,
            error_category=error_category,
            reason=reason,
        )

    def _emit_outcome(
        self,
        *,
        event_type: AgentEventType,
        summary: str,
        action_id: str,
        mission_id: str,
        organ_id: str,
        deadline_ms: int,
        elapsed_ms: int,
        reason: str,
        error_category: str | None,
    ) -> None:
        """Emit a single outcome event with the documented payload whitelist."""
        payload: dict[str, Any] = {
            "action_id": action_id,
            "mission_id": mission_id,
            "organ_id": organ_id,
            "reason": reason,
            "deadline_ms": deadline_ms,
            "elapsed_ms": elapsed_ms,
        }
        if error_category is not None:
            payload["error_category"] = error_category
        self._event_bus.append(event_type, summary, payload=payload)

    # ------------------------------------------------------------------ #
    # PerformanceReceipt construction — sanitized, frozen, append-only.
    # ------------------------------------------------------------------ #

    def _build_rejection_receipt(
        self,
        *,
        action_id: str,
        mission_id: str,
        organ_id: str,
        action_type: str,
        deadline_ms: int,
        error_category: str,
        reason: str,
    ) -> PerformanceReceipt:
        """Build and emit a critical-severity rejection receipt."""
        del reason  # reason is captured in error_category + outcome event payload
        trace = PerformanceTrace(
            action_id=action_id,
            mission_id=mission_id,
            organ_id=organ_id,
            action_type=action_type,
            queue_wait_ms=0,
            wall_ms=0,
            cpu_ms=0,
            bytes_in=0,
            bytes_out=0,
            tokens_in=0,
            tokens_out=0,
            cache_hit=0,
            cache_miss=0,
            organ_latency_ms=0,
            model_prefill_decode_ms=0,
            error=True,
            error_category=error_category,
            severity=PerformanceSeverity.CRITICAL,
        )
        receipt = PerformanceReceipt(
            mission_id=mission_id,
            action_id=action_id,
            organ_id=organ_id,
            action=action_type,
            trace=trace,
            estimated_cost_usd=Decimal("0"),
            budget_remaining=0,
            budget_limit=0,
            deadline_ms=deadline_ms,
            elapsed_ms=0,
            authority_expansion=False,
            raw_secret_leakage=False,
            created_at=datetime.now(UTC),
        )
        self._emit_receipt(receipt)
        return receipt

    def _build_outcome_receipt(
        self,
        *,
        action_id: str,
        mission_id: str,
        organ_id: str,
        action_type: str,
        deadline_ms: int,
        elapsed_ms: int,
        error: bool,
        error_category: str | None,
        severity: PerformanceSeverity,
    ) -> PerformanceReceipt:
        """Build and emit a per-outcome receipt for success / failure / timeout / cancel."""
        trace = PerformanceTrace(
            action_id=action_id,
            mission_id=mission_id,
            organ_id=organ_id,
            action_type=action_type,
            queue_wait_ms=0,
            wall_ms=elapsed_ms,
            cpu_ms=0,
            bytes_in=0,
            bytes_out=0,
            tokens_in=0,
            tokens_out=0,
            cache_hit=0,
            cache_miss=0,
            organ_latency_ms=elapsed_ms,
            model_prefill_decode_ms=0,
            error=error,
            error_category=error_category,
            severity=severity,
        )
        receipt = PerformanceReceipt(
            mission_id=mission_id,
            action_id=action_id,
            organ_id=organ_id,
            action=action_type,
            trace=trace,
            estimated_cost_usd=Decimal("0"),
            budget_remaining=0,
            budget_limit=0,
            deadline_ms=deadline_ms,
            elapsed_ms=elapsed_ms,
            authority_expansion=False,
            raw_secret_leakage=False,
            created_at=datetime.now(UTC),
        )
        self._emit_receipt(receipt)
        return receipt

    def _emit_receipt(self, receipt: PerformanceReceipt) -> None:
        """Append the receipt to the EventBus and (if injected) the cold store."""
        self._event_bus.append(
            AgentEventType.PERFORMANCE_RECEIPT_RECORDED,
            f"PerformanceReceipt recorded for action {receipt.action_id}",
            payload={
                "receipt_id": receipt.id,
                "action_id": receipt.action_id,
                "mission_id": receipt.mission_id,
                "organ_id": receipt.organ_id,
                "error": receipt.trace.error,
                "severity": receipt.trace.severity.value,
            },
        )
        # Best-effort cold-store handoff. The cold store is optional so the
        # scheduler can be exercised in isolation; injection happens at
        # AgentRuntime wiring (Task 8.8). A failing cold store must not
        # disrupt outcome event emission, so we ignore exceptions here.
        if self._cold_store is not None:
            persist = getattr(self._cold_store, "persist", None)
            if callable(persist):
                try:
                    persist(receipt)
                except BaseException:  # noqa: BLE001 - cold-store best-effort
                    pass

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #

    def _elapsed_ms_since(self, start_ns: int) -> int:
        """Compute non-negative elapsed milliseconds from a monotonic start_ns."""
        elapsed_ns = int(self._clock()) - start_ns
        if elapsed_ns < 0:
            return 0
        return elapsed_ns // 1_000_000


__all__ = [
    "AsyncOrganScheduler",
    "SubmissionAck",
]
