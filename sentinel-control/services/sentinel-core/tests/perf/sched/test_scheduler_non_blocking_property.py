# Feature: sentinel-performance-runtime-foundation, Property 9: Scheduler non-blocking + outcome-event correctness + kill-switch/authority enforcement
"""Property test — scheduler non-blocking + outcome events + kill-switch/authority.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 12.5.**

Property statement
------------------

Hypothesis FSM-style sweep over submissions × outcomes × (kill-switch /
authority) states. Asserts:

* **Kill-switch rejection** (Requirement 12.5): a submission whose
  kill-switch is ``triggered=True`` OR ``execution_allowed=False``
  returns ``reason="kill_switch_blocked"``, emits exactly one
  ``KILL_SWITCH_BLOCKED`` event, and NEVER emits a success completion
  event for that action.

* **Authority denial** (Requirement 12.5): a submission whose
  authority has ``execution_authorized=False`` OR ``dry_run_only=True``
  returns ``reason="authority_denied"``, emits exactly one
  ``AUTHORITY_VIOLATION`` event, and NEVER emits a success
  completion event for that action.

* **Outcome-event correctness** (Requirements 7.3, 7.4, 7.5, 7.8):
  for every accepted submission whose runner outcome is in
  ``{success, raise, timeout, cancel}`` exactly one outcome event
  is emitted per action — no double-emit, no missed-emit. Success
  → ``ORGAN_EXECUTION_RECEIPT_RECORDED``; failure →
  ``ORGAN_ACTION_FAILED``; timeout → ``ORGAN_ACTION_TIMEOUT``;
  cancellation → ``ORGAN_ACTION_CANCELLED``. No success event is
  emitted for non-success outcomes.

* **Higher-priority precedence** (Requirements 7.6, 7.7): with
  sequential dispatch (``max_organ_concurrency=1``) ``CRITICAL``
  actions complete before ``NORMAL``, ``NORMAL`` before ``LOW``.
  Verified by the timestamp ordering of completion events.

* **Submit non-blocking** (Requirement 7.1): the wall-clock time
  of :meth:`AsyncOrganScheduler.submit` itself remains well below
  the runner's sleep duration. The canonical 1 ms p95 target lives
  in Phase F's ``BenchmarkHarness``; here we use a generous 50 ms
  bound for CI stability against a 100 ms runner sleep.

* **Payload whitelist** (Requirements 7.2, 7.4, 7.5, 7.8): every
  event emitted by the scheduler carries payload keys only within
  the documented whitelist — ``{action_id, mission_id, organ_id,
  reason, deadline_ms, elapsed_ms, error_category, receipt_id,
  error, severity}``. The last three apply to
  ``PERFORMANCE_RECEIPT_RECORDED``.

Hypothesis settings
-------------------

``max_examples=200`` for the four safety sweeps (kill-switch,
authority, outcome correctness, payload whitelist) and
``max_examples=100`` for the two cost-bounded sweeps (priority
precedence, non-blocking submit). ``HealthCheck.too_slow`` and
``HealthCheck.function_scoped_fixture`` are suppressed because each
example spins a fresh asyncio event loop, an :class:`EventBus`, a
:class:`ToolCallQueue`, a :class:`BackpressureController`, and an
:class:`AsyncOrganScheduler`.

Layering
--------

This test only exercises the *scheduler* surface — it does not
construct an :class:`AgentRuntime`, a :class:`MissionRunner`, or any
real organ adapter. Authority / kill-switch / dry-run envelopes are
constructed minimally with the required fields. Organ runners are
inline async stubs; payload bytes never enter the scheduler.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ConfigDict, Field

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.dry_run import OrganDryRunReceipt
from sentinel.organs.kill_switch import OrganKillSwitch
from sentinel.perf.sched.async_organ_scheduler import (
    AsyncOrganScheduler,
    SubmissionAck,
)
from sentinel.perf.sched.backpressure_controller import BackpressureController
from sentinel.perf.sched.tool_call_queue import Priority, ToolCallQueue
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MISSION_ID = "mission_p9_scheduler"
_ROOT_AUTH_ID = "root_auth_p9"

# Payload whitelist for every event emitted by the scheduler. Mirrors the
# task spec's documented contract:
#
#   {action_id, mission_id, organ_id, reason, deadline_ms, elapsed_ms,
#    error_category}                              — outcome / rejection
#   {receipt_id, error, severity, action_id,
#    mission_id, organ_id}                        — PERFORMANCE_RECEIPT_RECORDED
#
# The combined whitelist below is the union of the two — every emitted
# event MUST have its payload keys be a subset of this set.
_PAYLOAD_WHITELIST: frozenset[str] = frozenset(
    {
        "action_id",
        "mission_id",
        "organ_id",
        "reason",
        "deadline_ms",
        "elapsed_ms",
        "error_category",
        "receipt_id",
        "error",
        "severity",
    }
)

# Reason tags the scheduler emits in SubmissionAck.reason. Mirrored from
# the scheduler's private constants so this test depends only on the
# documented contract, not on importing private symbols.
_REASON_QUEUED = "queued"
_REASON_KILL_SWITCH_BLOCKED = "kill_switch_blocked"
_REASON_AUTHORITY_DENIED = "authority_denied"


# ---------------------------------------------------------------------------
# Action stub — a minimal frozen model satisfying _OrganActionLike
# ---------------------------------------------------------------------------


class _StubAction(SentinelModel):
    """Minimal frozen action object for scheduler tests.

    The scheduler reads only ``action_id``, ``mission_id``, ``organ_id``,
    and ``action_type`` from the action — never any payload bytes. This
    stub is therefore sufficient and matches the structural ``_OrganActionLike``
    protocol the scheduler expects.
    """

    action_id: str
    mission_id: str
    organ_id: str
    action_type: str

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


# ---------------------------------------------------------------------------
# Builders — authority, kill-switch, dry-run
# ---------------------------------------------------------------------------


def _authority(
    *,
    organ_id: str = "organ_p9",
    execution_authorized: bool = True,
    dry_run_only: bool = False,
    max_actions: int = 32,
) -> OrganAuthorityEnvelope:
    """Build a minimal :class:`OrganAuthorityEnvelope`.

    The pydantic validator rejects ``execution_authorized=True`` with
    ``dry_run_only=True``, so callers asking for the
    "execution-authorized AND dry-run" combination are silently flipped
    to the closest legal state — but this builder is only called with
    one of three intended combinations:

    * (True,  False)  — clean execute (default)
    * (False, True)   — dry-run only
    * (False, False)  — execution not authorised, not dry-run-only either

    The fourth (True, True) is rejected by pydantic; callers must not
    pass it. The authority gate in the scheduler treats any of the
    last three as denial.
    """
    return OrganAuthorityEnvelope(
        mission_id=_MISSION_ID,
        root_authority_id=_ROOT_AUTH_ID,
        organ_id=organ_id,
        organ_name="organ_p9_name",
        allowed_actions=["safe_action"],
        allowed_tools=[],
        allowed_domains=[],
        allowed_accounts=[],
        allowed_paths=[],
        max_actions=max_actions,
        max_cost_usd=0.0,
        execution_authorized=execution_authorized,
        dry_run_only=dry_run_only,
    )


def _kill_switch(
    *,
    organ_id: str = "organ_p9",
    triggered: bool = False,
    execution_allowed: bool = True,
) -> OrganKillSwitch:
    """Build a minimal :class:`OrganKillSwitch` in the requested state."""
    return OrganKillSwitch(
        mission_id=_MISSION_ID,
        organ_id=organ_id,
        enabled=True,
        triggered=triggered,
        reason=("test_blocked" if triggered else None),
        execution_allowed=execution_allowed,
    )


def _dry_run(
    *,
    organ_id: str = "organ_p9",
    action: str = "safe_action",
) -> OrganDryRunReceipt:
    """Build a minimal :class:`OrganDryRunReceipt`.

    The dry-run receipt is required by ``AsyncOrganScheduler.submit``
    but is not consulted on either rejection path; we construct a
    minimal valid receipt and let the scheduler ignore it for these
    tests.
    """
    return OrganDryRunReceipt(
        mission_id=_MISSION_ID,
        organ_id=organ_id,
        action=action,
        reason="property test stub",
        preview={"action": action},
        risk_profile_id="orisk_p9",
        authority_id="orgauth_p9",
        evidence_refs=["ev_p9"],
    )


def _scheduler(
    *,
    bus: EventBus,
    max_organ_concurrency: int = 8,
) -> tuple[AsyncOrganScheduler, ToolCallQueue, BackpressureController]:
    """Construct the (queue, controller, scheduler) trio for a test.

    Returns the trio in (scheduler, queue, controller) order so callers
    can inspect queue depth and controller state alongside scheduler
    behaviour. ``max_organ_concurrency`` is parameterised so the
    higher-priority-precedence test can pin it to ``1`` for sequential
    dispatch.
    """
    queue = ToolCallQueue(max_depth=1000)
    controller = BackpressureController(
        event_bus=bus,
        queue=queue,
        max_queue_depth=1000,
        max_byte_rate_per_s=10**9,
        max_organ_concurrency=max_organ_concurrency,
    )
    scheduler = AsyncOrganScheduler(
        event_bus=bus,
        queue=queue,
        backpressure=controller,
    )
    return scheduler, queue, controller


# ---------------------------------------------------------------------------
# Helpers — event lookup
# ---------------------------------------------------------------------------


def _events_for_action(
    bus: EventBus,
    action_id: str,
    *,
    event_type: AgentEventType,
) -> list[Any]:
    """Return events of ``event_type`` whose payload references ``action_id``.

    The match is on ``payload['action_id']`` for events that carry it,
    which covers KILL_SWITCH_BLOCKED, AUTHORITY_VIOLATION, all four
    organ-action outcome events, and PERFORMANCE_RECEIPT_RECORDED. The
    queue/controller events use ``organ_type`` not ``action_id``, so
    they are correctly excluded.
    """
    return [
        ev
        for ev in bus.events()
        if ev.event_type == event_type
        and ev.payload.get("action_id") == action_id
    ]


def _all_action_events(bus: EventBus, action_id: str) -> list[Any]:
    """Return every event whose payload references ``action_id``."""
    return [
        ev
        for ev in bus.events()
        if ev.payload.get("action_id") == action_id
    ]


def _assert_payload_whitelist(events: list[Any]) -> None:
    """Assert every event in ``events`` has a whitelisted payload key set.

    The whitelist is :data:`_PAYLOAD_WHITELIST`. A regression that adds
    a new key (e.g. action body, organ output bytes, secret material)
    fails this assertion immediately.
    """
    for ev in events:
        extra = set(ev.payload.keys()) - _PAYLOAD_WHITELIST
        assert not extra, (
            f"event {ev.event_type!r} payload contains keys outside "
            f"the whitelist: {sorted(extra)!r}; "
            f"full payload={ev.payload!r}"
        )


# ---------------------------------------------------------------------------
# Helpers — action factory and runners
# ---------------------------------------------------------------------------


def _make_action(
    *,
    action_id: str = "act_p9",
    organ_id: str = "organ_p9",
    action_type: str = "safe_action",
) -> _StubAction:
    return _StubAction(
        action_id=action_id,
        mission_id=_MISSION_ID,
        organ_id=organ_id,
        action_type=action_type,
    )


async def _runner_success(action: Any) -> None:
    """Returns immediately — success path."""
    del action
    return None


async def _runner_raise(action: Any) -> None:
    """Raises a ``RuntimeError`` — failure path."""
    del action
    raise RuntimeError("intentional failure for property test")


async def _runner_sleep(seconds: float) -> Callable[[Any], Awaitable[None]]:
    """Build a sleeper runner that awaits ``seconds`` then returns."""

    async def _sleeper(action: Any) -> None:
        del action
        await asyncio.sleep(seconds)

    return _sleeper  # type: ignore[return-value]


def _make_sleep_runner(seconds: float) -> Callable[[Any], Awaitable[None]]:
    """Synchronous helper that returns an async sleeper runner."""

    async def _sleeper(action: Any) -> None:
        del action
        await asyncio.sleep(seconds)

    return _sleeper


# ---------------------------------------------------------------------------
# 1. test_kill_switch_rejection_blocks_submission
# ---------------------------------------------------------------------------


@given(
    triggered=st.booleans(),
    execution_allowed=st.booleans(),
)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_kill_switch_rejection_blocks_submission(
    triggered: bool,
    execution_allowed: bool,
) -> None:
    """Kill-switch states ``(triggered, execution_allowed)`` block submission.

    Per Requirement 12.5: a kill-switch is "blocking" when either
    ``triggered=True`` OR ``execution_allowed=False``. For every blocking
    pair the scheduler MUST:

    * return ``SubmissionAck(accepted=False, reason="kill_switch_blocked")``;
    * emit exactly one ``KILL_SWITCH_BLOCKED`` event for the action;
    * never emit ``ORGAN_EXECUTION_RECEIPT_RECORDED`` (success completion)
      for that action.

    For the (False, True) non-blocking pair the submission MUST be
    accepted; this anchors the property as non-vacuous.

    Validates: Requirement 12.5.
    """
    is_blocking = triggered or not execution_allowed
    bus = EventBus(mission_id=_MISSION_ID)
    scheduler, _queue, _controller = _scheduler(bus=bus)

    action = _make_action(action_id="act_kill_switch")
    authority = _authority()
    kill_switch = _kill_switch(
        triggered=triggered,
        execution_allowed=execution_allowed,
    )
    dry_run = _dry_run()

    async def _drive() -> SubmissionAck:
        ack = await scheduler.submit(
            action,
            authority=authority,
            kill_switch=kill_switch,
            dry_run=dry_run,
            deadline_ms=1000,
            organ_runner=_runner_success,
        )
        # Drain any in-flight tasks so success completion events on the
        # accepted-path branch have a chance to fire before assertions.
        # On rejection the scheduler creates no task at all, so this is
        # a no-op for blocking inputs.
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        return ack

    ack = asyncio.run(_drive())

    if is_blocking:
        # Rejection contract.
        assert ack.accepted is False
        assert ack.reason == _REASON_KILL_SWITCH_BLOCKED, (
            f"expected reason={_REASON_KILL_SWITCH_BLOCKED!r}, got {ack.reason!r}"
        )
        assert ack.position == -1

        # Exactly one KILL_SWITCH_BLOCKED event for this action.
        ks_events = _events_for_action(
            bus, action.action_id, event_type=AgentEventType.KILL_SWITCH_BLOCKED
        )
        assert len(ks_events) == 1, (
            f"expected exactly one KILL_SWITCH_BLOCKED, got {len(ks_events)}"
        )
        assert ks_events[0].payload["reason"] == _REASON_KILL_SWITCH_BLOCKED

        # No success completion event for this action.
        success_events = _events_for_action(
            bus,
            action.action_id,
            event_type=AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        )
        assert success_events == [], (
            "kill-switch rejection MUST NOT emit a success completion event"
        )

        # No AUTHORITY_VIOLATION event — kill-switch is checked first.
        auth_events = _events_for_action(
            bus, action.action_id, event_type=AgentEventType.AUTHORITY_VIOLATION
        )
        assert auth_events == [], (
            "kill-switch rejection MUST NOT also raise an AUTHORITY_VIOLATION"
        )
    else:
        # Non-blocking pair anchors the property: submission is accepted
        # and (since the runner is _runner_success) emits exactly one
        # success completion event.
        assert ack.accepted is True, (
            f"expected accepted=True for non-blocking kill-switch pair, "
            f"got reason={ack.reason!r}"
        )
        assert ack.reason == _REASON_QUEUED
        ks_events = _events_for_action(
            bus, action.action_id, event_type=AgentEventType.KILL_SWITCH_BLOCKED
        )
        assert ks_events == []
        success_events = _events_for_action(
            bus,
            action.action_id,
            event_type=AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        )
        assert len(success_events) == 1, (
            f"expected exactly one success completion event for accepted "
            f"submission, got {len(success_events)}"
        )

    # Whitelist: every emitted event for this action keeps payload keys
    # within the whitelist.
    _assert_payload_whitelist(_all_action_events(bus, action.action_id))


# ---------------------------------------------------------------------------
# 2. test_authority_denial_blocks_submission
# ---------------------------------------------------------------------------


# Authority pair generator: skip the (True, True) combination because
# OrganAuthorityEnvelope's pydantic validator rejects it
# ("Execution-authorized organ authority cannot be dry-run-only").
_authority_pair_st = st.tuples(st.booleans(), st.booleans()).filter(
    lambda pair: not (pair[0] is True and pair[1] is True)
)


@given(pair=_authority_pair_st)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_authority_denial_blocks_submission(pair: tuple[bool, bool]) -> None:
    """Authority states ``(execution_authorized, dry_run_only)`` deny submission.

    Per Requirement 12.5: authority denies execution when
    ``execution_authorized=False`` OR ``dry_run_only=True``. For every
    denying pair the scheduler MUST:

    * return ``SubmissionAck(accepted=False, reason="authority_denied")``;
    * emit exactly one ``AUTHORITY_VIOLATION`` event for the action;
    * never emit ``ORGAN_EXECUTION_RECEIPT_RECORDED`` for that action.

    The (True, False) clean-execute pair anchors the property as
    non-vacuous: submission is accepted and produces exactly one
    success completion event under ``_runner_success``.

    Validates: Requirement 12.5.
    """
    execution_authorized, dry_run_only = pair
    is_denying = (not execution_authorized) or dry_run_only

    bus = EventBus(mission_id=_MISSION_ID)
    scheduler, _queue, _controller = _scheduler(bus=bus)

    action = _make_action(action_id="act_authority")
    authority = _authority(
        execution_authorized=execution_authorized,
        dry_run_only=dry_run_only,
    )
    kill_switch = _kill_switch()  # clean — does not interfere
    dry_run = _dry_run()

    async def _drive() -> SubmissionAck:
        ack = await scheduler.submit(
            action,
            authority=authority,
            kill_switch=kill_switch,
            dry_run=dry_run,
            deadline_ms=1000,
            organ_runner=_runner_success,
        )
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        return ack

    ack = asyncio.run(_drive())

    if is_denying:
        assert ack.accepted is False
        assert ack.reason == _REASON_AUTHORITY_DENIED, (
            f"expected reason={_REASON_AUTHORITY_DENIED!r}, got {ack.reason!r}"
        )
        assert ack.position == -1

        # Exactly one AUTHORITY_VIOLATION event for this action.
        auth_events = _events_for_action(
            bus, action.action_id, event_type=AgentEventType.AUTHORITY_VIOLATION
        )
        assert len(auth_events) == 1, (
            f"expected exactly one AUTHORITY_VIOLATION, got {len(auth_events)}"
        )
        assert auth_events[0].payload["reason"] == _REASON_AUTHORITY_DENIED

        # No success completion event.
        success_events = _events_for_action(
            bus,
            action.action_id,
            event_type=AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        )
        assert success_events == [], (
            "authority denial MUST NOT emit a success completion event"
        )

        # No KILL_SWITCH_BLOCKED — the kill-switch is clean here.
        ks_events = _events_for_action(
            bus, action.action_id, event_type=AgentEventType.KILL_SWITCH_BLOCKED
        )
        assert ks_events == []
    else:
        assert ack.accepted is True, (
            f"expected accepted=True for clean (True, False) pair, "
            f"got reason={ack.reason!r}"
        )
        success_events = _events_for_action(
            bus,
            action.action_id,
            event_type=AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        )
        assert len(success_events) == 1

    _assert_payload_whitelist(_all_action_events(bus, action.action_id))


# ---------------------------------------------------------------------------
# 3. test_outcome_event_correctness
# ---------------------------------------------------------------------------


_OUTCOMES = ("success", "raise", "timeout", "cancel")
_outcome_st = st.sampled_from(_OUTCOMES)


def _build_runner(outcome: str) -> Callable[[Any], Awaitable[None]]:
    """Return an async runner producing the requested outcome.

    * ``success`` — returns immediately
    * ``raise``   — raises ``RuntimeError``
    * ``timeout`` — sleeps far longer than the deadline so
      :func:`asyncio.wait_for` raises :class:`asyncio.TimeoutError`
    * ``cancel``  — sleeps briefly so the wrapper task can be
      cancelled by ``cancel_mission`` while the runner is in-flight
    """

    async def _success(action: Any) -> None:
        del action

    async def _raise(action: Any) -> None:
        del action
        raise RuntimeError("intentional failure")

    async def _timeout(action: Any) -> None:
        del action
        # Sleep substantially longer than the test's deadline so the
        # ``asyncio.wait_for`` envelope raises TimeoutError. 5 s is
        # generous; the deadline below is 50 ms.
        await asyncio.sleep(5.0)

    async def _cancel(action: Any) -> None:
        del action
        # Sleep briefly so cancel_mission has time to fire while the
        # runner is awaiting; the deadline is generous enough that
        # this would otherwise succeed cleanly.
        await asyncio.sleep(2.0)

    return {
        "success": _success,
        "raise": _raise,
        "timeout": _timeout,
        "cancel": _cancel,
    }[outcome]


_OUTCOME_TO_EVENT_TYPE: dict[str, AgentEventType] = {
    "success": AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
    "raise": AgentEventType.ORGAN_ACTION_FAILED,
    "timeout": AgentEventType.ORGAN_ACTION_TIMEOUT,
    "cancel": AgentEventType.ORGAN_ACTION_CANCELLED,
}

_NON_OUTCOME_EVENT_TYPES_BY_OUTCOME: dict[str, list[AgentEventType]] = {
    outcome: [
        et
        for k, et in _OUTCOME_TO_EVENT_TYPE.items()
        if k != outcome
    ]
    for outcome in _OUTCOMES
}


@given(outcome=_outcome_st)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_outcome_event_correctness(outcome: str) -> None:
    """Each outcome emits exactly one matching outcome event; no double-emit.

    For every outcome in ``{success, raise, timeout, cancel}``:

    * exactly one event of the matching type is emitted for the action;
    * none of the other three outcome types is emitted for the action;
    * non-success outcomes never emit ``ORGAN_EXECUTION_RECEIPT_RECORDED``;
    * exactly one ``PERFORMANCE_RECEIPT_RECORDED`` event accompanies the
      outcome event (single source of truth for the receipt).

    Validates: Requirements 7.3, 7.4, 7.5, 7.8.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    scheduler, _queue, _controller = _scheduler(bus=bus)

    action = _make_action(action_id=f"act_outcome_{outcome}")
    authority = _authority()
    kill_switch = _kill_switch()
    dry_run = _dry_run()
    runner = _build_runner(outcome)

    # Use a 50 ms deadline for "timeout" so the wait_for envelope fires
    # quickly; for the other outcomes the deadline is generous (1 s) so
    # success/raise/cancel never trip the timeout branch.
    deadline_ms = 50 if outcome == "timeout" else 1000

    async def _drive() -> SubmissionAck:
        ack = await scheduler.submit(
            action,
            authority=authority,
            kill_switch=kill_switch,
            dry_run=dry_run,
            deadline_ms=deadline_ms,
            organ_runner=runner,
        )
        if outcome == "cancel":
            # Give the wrapper a tick to start awaiting the runner before
            # we cancel; cancel_mission then cancels the wrapper task,
            # which propagates CancelledError into the awaited runner.
            await asyncio.sleep(0.01)
            scheduler.cancel_mission(_MISSION_ID)

        # Drain in-flight tasks so the wrapper's outcome branch (and its
        # event emission) completes before we make assertions.
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        return ack

    ack = asyncio.run(_drive())
    assert ack.accepted is True, (
        f"setup error: outcome={outcome!r} requires an accepted submission; "
        f"got reason={ack.reason!r}"
    )

    # Exactly one event of the matching outcome type.
    expected_event_type = _OUTCOME_TO_EVENT_TYPE[outcome]
    matching = _events_for_action(
        bus, action.action_id, event_type=expected_event_type
    )
    assert len(matching) == 1, (
        f"outcome={outcome!r} expected exactly one {expected_event_type.value} "
        f"event for the action, got {len(matching)}"
    )

    # No other outcome-type event for the action.
    for forbidden in _NON_OUTCOME_EVENT_TYPES_BY_OUTCOME[outcome]:
        forbidden_events = _events_for_action(
            bus, action.action_id, event_type=forbidden
        )
        assert forbidden_events == [], (
            f"outcome={outcome!r} MUST NOT emit {forbidden.value}; "
            f"got {len(forbidden_events)} such events"
        )

    # Non-success outcomes specifically must not emit success completion.
    if outcome != "success":
        success_events = _events_for_action(
            bus,
            action.action_id,
            event_type=AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        )
        assert success_events == [], (
            f"outcome={outcome!r} MUST NOT emit ORGAN_EXECUTION_RECEIPT_RECORDED"
        )

    # Exactly one PerformanceReceipt event accompanies the outcome.
    pr_events = _events_for_action(
        bus,
        action.action_id,
        event_type=AgentEventType.PERFORMANCE_RECEIPT_RECORDED,
    )
    assert len(pr_events) == 1, (
        f"outcome={outcome!r} expected exactly one PERFORMANCE_RECEIPT_RECORDED, "
        f"got {len(pr_events)}"
    )
    pr_payload = pr_events[0].payload
    if outcome == "success":
        assert pr_payload["error"] is False
        assert pr_payload["severity"] == "info"
    else:
        assert pr_payload["error"] is True
        # Cancellation is a warning; failure / timeout are critical.
        assert pr_payload["severity"] in {"warning", "critical"}

    # Whitelist sweep across every event the action produced.
    _assert_payload_whitelist(_all_action_events(bus, action.action_id))


# ---------------------------------------------------------------------------
# 4. test_higher_priority_runs_first
# ---------------------------------------------------------------------------


# Strategy: a list of (priority_level, position_tag) pairs such that all
# three priority levels are represented at least once. The list size is
# bounded above to keep the test fast; sequential dispatch with
# max_organ_concurrency=1 means every dispatched action is single-file
# behind the previous one.
_priority_batch_st = st.lists(
    st.sampled_from([Priority.CRITICAL, Priority.NORMAL, Priority.LOW]),
    min_size=3,
    max_size=8,
).filter(
    lambda priorities: (
        Priority.CRITICAL in priorities
        and Priority.NORMAL in priorities
        and Priority.LOW in priorities
    )
)


@given(priorities=_priority_batch_st)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_higher_priority_runs_first(priorities: list[Priority]) -> None:
    """Higher-priority actions are dequeued first by the scheduler's queue.

    The scheduler's priority semantics live in :class:`ToolCallQueue` —
    its three priority deques (CRITICAL → NORMAL → LOW) are what
    actually order pending work. ``AsyncOrganScheduler`` itself spawns
    one wrapper task per :meth:`submit`, and each wrapper invokes
    :meth:`ToolCallQueue.dequeue` exactly once. The queue is therefore
    the single observation point at which Requirement 7.6's
    "higher-priority first" invariant is enforced.

    Test design
    -----------

    1. Build a fresh scheduler (with ``max_organ_concurrency=1`` per
       the task spec, even though admission gating does not change the
       observation; we keep the cap=1 setup to mirror the task wording).
    2. Submit every action with the runner pinned via a shared
       :class:`asyncio.Event` so the runner blocks before completing —
       this keeps every submitted item from completing immediately and
       allows us to inspect the queue's pending state, then release.
    3. The wrappers each call :meth:`ToolCallQueue.dequeue` in their
       asyncio-creation order (FIFO of the loop's ready queue). Each
       dequeue pulls the highest-priority remaining queued action; the
       resulting per-organ in-flight increments are the priority-ordered
       evidence.
    4. We tag each submission with a unique ``organ_id`` carrying its
       priority in the suffix; we then snapshot the order in which
       :attr:`ToolCallQueue._per_organ_in_flight` keys appear (mapped
       through a dispatch-recording instrumentation hook on
       :meth:`dequeue`).

    Concretely: we wrap :meth:`queue.dequeue` to record the order in
    which queued items are pulled, then assert the recorded sequence
    is monotonic in priority — every CRITICAL pull precedes every
    NORMAL pull, every NORMAL pull precedes every LOW pull. This is
    Requirement 7.6's invariant expressed exactly at the layer that
    enforces it.

    Validates: Requirements 7.6, 7.7.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    # max_organ_concurrency=1 mirrors the task's "force ordering"
    # wording. The cap does not affect the observation here because
    # we record dequeue order via instrumentation, not via completion
    # events. The depth cap is large so no submission is rejected.
    scheduler, queue, _controller = _scheduler(bus=bus, max_organ_concurrency=1)

    # Instrument the queue's dequeue: every successful pop records the
    # popped item's priority in a list. The recorded sequence is what
    # the test asserts on. We monkeypatch the bound method on this
    # specific queue instance only — no global state is touched.
    dequeue_priorities: list[Priority] = []
    original_dequeue = queue.dequeue

    def _instrumented_dequeue() -> Any:
        item = original_dequeue()
        if item is not None:
            dequeue_priorities.append(item.priority)
        return item

    queue.dequeue = _instrumented_dequeue  # type: ignore[method-assign]

    # All wrappers will block on this event until the test releases it.
    # This holds the queue full while we inspect submission state, then
    # lets the wrappers proceed so their dequeues happen in asyncio
    # FIFO order.
    runner_gate: asyncio.Event | None = None  # populated inside _drive

    authority_template = lambda organ_id: _authority(  # noqa: E731
        organ_id=organ_id, max_actions=64
    )
    kill_switch_template = lambda organ_id: _kill_switch(organ_id=organ_id)  # noqa: E731
    dry_run_template = lambda organ_id: _dry_run(organ_id=organ_id)  # noqa: E731

    async def _drive() -> None:
        nonlocal runner_gate
        runner_gate = asyncio.Event()

        async def _gated_runner(action: Any) -> None:
            del action
            # Wait for the gate; once released, return immediately.
            await runner_gate.wait()  # type: ignore[union-attr]

        # Submit every action. Each submission has a unique organ_id so
        # per-organ caps never bind across distinct submissions.
        for index, priority in enumerate(priorities):
            organ_id = f"organ_priority_{priority.name}_{index}"
            action = _make_action(
                action_id=f"act_priority_{index}",
                organ_id=organ_id,
            )
            ack = await scheduler.submit(
                action,
                authority=authority_template(organ_id),
                kill_switch=kill_switch_template(organ_id),
                dry_run=dry_run_template(organ_id),
                deadline_ms=5000,
                priority=priority,
                organ_runner=_gated_runner,
            )
            assert ack.accepted is True, (
                f"setup error: submission act_priority_{index} not accepted: "
                f"reason={ack.reason!r}"
            )

        # Yield once so every wrapper task has a chance to enter and
        # call dequeue() against the still-full queue.
        await asyncio.sleep(0)

        # Release the gate so all runners return; drain wrapper tasks.
        runner_gate.set()
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    asyncio.run(_drive())

    # Every submission produced exactly one dequeue.
    assert len(dequeue_priorities) == len(priorities), (
        f"expected one dequeue per submission; "
        f"got {len(dequeue_priorities)} dequeues for {len(priorities)} submissions"
    )

    # Priority invariant: the dequeue sequence is monotonic non-decreasing
    # in numeric priority value (CRITICAL=0 < NORMAL=1 < LOW=2). The
    # queue's deque-per-priority structure pops CRITICAL first, then
    # NORMAL, then LOW; within each priority FIFO is preserved.
    numeric_seq = [p.value for p in dequeue_priorities]
    for i in range(1, len(numeric_seq)):
        assert numeric_seq[i] >= numeric_seq[i - 1], (
            f"queue dequeue order violated priority precedence at index "
            f"{i}: priorities={dequeue_priorities!r}"
        )

    # Stronger check: every CRITICAL dequeue index < every NORMAL index
    # < every LOW index.
    crit_idx = [i for i, p in enumerate(dequeue_priorities) if p == Priority.CRITICAL]
    norm_idx = [i for i, p in enumerate(dequeue_priorities) if p == Priority.NORMAL]
    low_idx = [i for i, p in enumerate(dequeue_priorities) if p == Priority.LOW]

    if crit_idx and norm_idx:
        assert max(crit_idx) < min(norm_idx), (
            f"every CRITICAL dequeue MUST precede every NORMAL dequeue; "
            f"crit_idx={crit_idx!r}, norm_idx={norm_idx!r}"
        )
    if norm_idx and low_idx:
        assert max(norm_idx) < min(low_idx), (
            f"every NORMAL dequeue MUST precede every LOW dequeue; "
            f"norm_idx={norm_idx!r}, low_idx={low_idx!r}"
        )
    if crit_idx and low_idx:
        assert max(crit_idx) < min(low_idx), (
            f"every CRITICAL dequeue MUST precede every LOW dequeue; "
            f"crit_idx={crit_idx!r}, low_idx={low_idx!r}"
        )

    # Sanity: queue is empty after every wrapper has run.
    assert queue.depth() == 0


# ---------------------------------------------------------------------------
# 5. test_submit_non_blocking
# ---------------------------------------------------------------------------


# Strategy: a small set of priority/byte-estimate combinations to drive
# variability; the timing assertion is what matters.
_submit_input_st = st.tuples(
    st.sampled_from([Priority.CRITICAL, Priority.NORMAL, Priority.LOW]),
    st.integers(min_value=0, max_value=128),
)


@given(inputs=_submit_input_st)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_submit_non_blocking(inputs: tuple[Priority, int]) -> None:
    """``submit()`` returns well before the runner's 100 ms sleep completes.

    Submits an action whose runner sleeps for 100 ms. Wall-clock time
    of :meth:`AsyncOrganScheduler.submit` itself MUST be < 50 ms — well
    below the runner's sleep duration. The canonical 1 ms p95 target
    lives in Phase F's ``BenchmarkHarness``; the 50 ms bound here is
    generous for CI stability.

    Validates: Requirement 7.1.
    """
    priority, byte_estimate = inputs
    bus = EventBus(mission_id=_MISSION_ID)
    scheduler, _queue, _controller = _scheduler(bus=bus)

    action = _make_action(action_id="act_non_blocking")
    authority = _authority()
    kill_switch = _kill_switch()
    dry_run = _dry_run()
    runner = _make_sleep_runner(0.1)  # 100 ms

    async def _drive() -> tuple[float, SubmissionAck]:
        start_ns = time.perf_counter_ns()
        ack = await scheduler.submit(
            action,
            authority=authority,
            kill_switch=kill_switch,
            dry_run=dry_run,
            deadline_ms=2000,
            priority=priority,
            organ_runner=runner,
            action_byte_estimate=byte_estimate,
        )
        elapsed_ns = time.perf_counter_ns() - start_ns

        # Drain so the test does not leak the still-running 100 ms task
        # into subsequent examples. The drain happens AFTER the timing
        # measurement, so it does not contaminate the elapsed reading.
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        return elapsed_ns / 1_000_000.0, ack

    elapsed_ms, ack = asyncio.run(_drive())

    assert ack.accepted is True, (
        f"setup error: submission not accepted: reason={ack.reason!r}"
    )
    # Wall-clock submit time MUST be far below the runner's 100 ms sleep.
    # 50 ms is intentionally generous for CI variance; the canonical
    # 1 ms p95 lives in BenchmarkHarness (Phase F).
    assert elapsed_ms < 50.0, (
        f"submit() took {elapsed_ms:.2f}ms — must be <50ms (well below "
        f"the 100ms runner sleep). The non-blocking contract is broken."
    )


# ---------------------------------------------------------------------------
# 6. test_payload_whitelist_across_outcomes
# ---------------------------------------------------------------------------


def test_payload_whitelist_across_outcomes() -> None:
    """Every event the scheduler emits has whitelisted payload keys only.

    Drives one example of each event type — kill-switch rejection,
    authority denial, success completion, failure completion, timeout
    completion, cancellation — and asserts that every event's payload
    keys are within the documented whitelist:
    ``{action_id, mission_id, organ_id, reason, deadline_ms, elapsed_ms,
    error_category, receipt_id, error, severity}``.

    No raw action body, no organ output bytes, no secret material.

    Validates: Requirements 7.2, 7.4, 7.5, 7.8.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    scheduler, _queue, _controller = _scheduler(bus=bus)

    organ_id = "organ_whitelist"
    clean_authority = _authority(organ_id=organ_id)
    clean_ks = _kill_switch(organ_id=organ_id)
    dry_run = _dry_run(organ_id=organ_id)

    async def _drive() -> None:
        # 1) Kill-switch rejection.
        await scheduler.submit(
            _make_action(action_id="act_wl_ks", organ_id=organ_id),
            authority=clean_authority,
            kill_switch=_kill_switch(organ_id=organ_id, triggered=True),
            dry_run=dry_run,
            deadline_ms=1000,
            organ_runner=_runner_success,
        )

        # 2) Authority denial.
        await scheduler.submit(
            _make_action(action_id="act_wl_auth", organ_id=organ_id),
            authority=_authority(
                organ_id=organ_id,
                execution_authorized=False,
                dry_run_only=True,
            ),
            kill_switch=clean_ks,
            dry_run=dry_run,
            deadline_ms=1000,
            organ_runner=_runner_success,
        )

        # 3) Success completion.
        await scheduler.submit(
            _make_action(action_id="act_wl_success", organ_id=organ_id),
            authority=clean_authority,
            kill_switch=clean_ks,
            dry_run=dry_run,
            deadline_ms=1000,
            organ_runner=_runner_success,
        )

        # 4) Failure completion.
        await scheduler.submit(
            _make_action(action_id="act_wl_fail", organ_id=organ_id),
            authority=clean_authority,
            kill_switch=clean_ks,
            dry_run=dry_run,
            deadline_ms=1000,
            organ_runner=_runner_raise,
        )

        # 5) Timeout completion. Submit FIRST, then sleep past the
        #    deadline so the wait_for envelope has time to fire — if we
        #    submit and cancel back-to-back, ``cancel_mission`` would
        #    abort the wrapper task before its asyncio.wait_for raises
        #    TimeoutError.
        await scheduler.submit(
            _make_action(action_id="act_wl_timeout", organ_id=organ_id),
            authority=clean_authority,
            kill_switch=clean_ks,
            dry_run=dry_run,
            deadline_ms=20,
            organ_runner=_make_sleep_runner(2.0),
        )
        # Wait long enough for the 20 ms deadline to elapse and the
        # ORGAN_ACTION_TIMEOUT branch to run before any cancellation.
        await asyncio.sleep(0.1)

        # 6) Cancellation completion. We use a separate mission_id for
        #    the cancel-target so ``cancel_mission`` only cancels this
        #    one wrapper — leaving every other completed action's events
        #    intact on the shared bus.
        cancel_mission_id = "mission_p9_scheduler_cancel"
        cancel_action = _StubAction(
            action_id="act_wl_cancel",
            mission_id=cancel_mission_id,
            organ_id=organ_id,
            action_type="safe_action",
        )
        cancel_authority = OrganAuthorityEnvelope(
            mission_id=cancel_mission_id,
            root_authority_id=_ROOT_AUTH_ID,
            organ_id=organ_id,
            organ_name="organ_p9_name",
            allowed_actions=["safe_action"],
            allowed_tools=[],
            allowed_domains=[],
            allowed_accounts=[],
            allowed_paths=[],
            max_actions=32,
            max_cost_usd=0.0,
            execution_authorized=True,
            dry_run_only=False,
        )
        cancel_dry_run = OrganDryRunReceipt(
            mission_id=cancel_mission_id,
            organ_id=organ_id,
            action="safe_action",
            reason="property test stub",
            preview={"action": "safe_action"},
            risk_profile_id="orisk_p9",
            authority_id="orgauth_p9",
            evidence_refs=["ev_p9"],
        )
        cancel_kill_switch = OrganKillSwitch(
            mission_id=cancel_mission_id,
            organ_id=organ_id,
            enabled=True,
            triggered=False,
            execution_allowed=True,
        )
        await scheduler.submit(
            cancel_action,
            authority=cancel_authority,
            kill_switch=cancel_kill_switch,
            dry_run=cancel_dry_run,
            deadline_ms=5000,
            organ_runner=_make_sleep_runner(2.0),
        )
        # Give the cancel-target wrapper a tick to start, then cancel
        # only its mission.
        await asyncio.sleep(0.01)
        scheduler.cancel_mission(cancel_mission_id)

        # Drain everything.
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    asyncio.run(_drive())

    # Sweep every scheduler-emitted event type for payload-key compliance.
    relevant_event_types = {
        AgentEventType.KILL_SWITCH_BLOCKED,
        AgentEventType.AUTHORITY_VIOLATION,
        AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        AgentEventType.ORGAN_ACTION_FAILED,
        AgentEventType.ORGAN_ACTION_TIMEOUT,
        AgentEventType.ORGAN_ACTION_CANCELLED,
        AgentEventType.PERFORMANCE_RECEIPT_RECORDED,
    }
    relevant = [ev for ev in bus.events() if ev.event_type in relevant_event_types]

    # We expect at least one of each event type to be present.
    types_present = {ev.event_type for ev in relevant}
    expected_present = {
        AgentEventType.KILL_SWITCH_BLOCKED,
        AgentEventType.AUTHORITY_VIOLATION,
        AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        AgentEventType.ORGAN_ACTION_FAILED,
        AgentEventType.ORGAN_ACTION_TIMEOUT,
        AgentEventType.ORGAN_ACTION_CANCELLED,
        AgentEventType.PERFORMANCE_RECEIPT_RECORDED,
    }
    missing = expected_present - types_present
    assert not missing, (
        f"setup error: not every event type fired this run; missing "
        f"{sorted(t.value for t in missing)}"
    )

    _assert_payload_whitelist(relevant)
