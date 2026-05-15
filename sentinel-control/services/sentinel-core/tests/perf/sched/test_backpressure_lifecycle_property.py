# Feature: sentinel-performance-runtime-foundation, Property 10: Backpressure lifecycle never expands authority
"""Property test — backpressure lifecycle never expands authority.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 12.6.**

Property statement
------------------

For any :class:`MissionAuthorityEnvelope` and any load of submissions
flowing through :class:`BackpressureController`:

* every :class:`BackpressureDecision` has all values in
  ``decision.bounds_used`` less-than-or-equal-to the corresponding
  ``envelope.max_actions`` field — the controller never widens authority
  (Requirement 12.6);
* ``QUEUE_BACKPRESSURE_CLEARED`` is emitted **iff** both predicates of
  the cleared-iff rule hold simultaneously: the controller was under
  pressure prior to the call, and the current queue depth is strictly
  below the configured cap (Requirement 8.7);
* the per-organ sliding byte-rate window covers exactly 1 second
  (Requirement 8.5) — bytes admitted at ``t=0`` are still counted at
  ``t=0.5s`` and have fallen out of the window by ``t=1.001s``;
* the ``QUEUE_BACKPRESSURE_APPLIED`` event payload is exactly
  ``{organ_type, queue_depth, estimated_wait_ms, reason}`` and the
  ``QUEUE_BACKPRESSURE_CLEARED`` event payload is exactly
  ``{organ_type, queue_depth}`` — no leakage of action body, organ
  output, or secret material into the event ledger;
* repeated accepted submissions on an empty queue never emit
  ``QUEUE_BACKPRESSURE_CLEARED`` (the controller never falsely
  declares "cleared" when there was no prior pressure).

Hypothesis settings
-------------------

* ``max_examples=200`` for the four safety sweeps (bounds-clamping,
  cleared-iff lifecycle, payload whitelist, no-CLEARED-without-pressure).
  Authority/safety properties use 200 examples per spec.
* ``max_examples=100`` for the byte-rate sliding-window sweep — the
  invariant is structural (no FSM blow-up) so 100 examples suffice.
* ``HealthCheck.too_slow`` and ``HealthCheck.function_scoped_fixture``
  are suppressed because each example builds a fresh
  :class:`EventBus` + :class:`ToolCallQueue` +
  :class:`BackpressureController` trio.

Layering
--------

This test only exercises :class:`BackpressureController` directly. It
does NOT construct an :class:`AsyncOrganScheduler`, an
:class:`AgentRuntime`, or any organ adapter. The action object is a
minimal frozen pydantic model exposing ``organ_id`` (the Protocol the
controller reads from); no payload bytes ever enter the controller.
The :class:`MissionAuthorityEnvelope` is constructed minimally — the
controller only consults ``envelope.max_actions``.
"""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ConfigDict

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.sched.backpressure_controller import (
    BackpressureController,
    BackpressureDecision,
)
from sentinel.perf.sched.tool_call_queue import (
    Priority,
    QueuedAction,
    ToolCallQueue,
)
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MISSION_ID = "mission_p10_backpressure"

# Documented payload-whitelist contracts mirrored from
# :class:`BackpressureController` — see its module docstring for the
# rationale ("no leakage of action body, organ output, or secret material
# into the event ledger"). Keep this list in lock-step with the
# controller; widening the controller's payload contract MUST be
# reflected here in the same change.
_APPLIED_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {"organ_type", "queue_depth", "estimated_wait_ms", "reason"}
)
_CLEARED_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {"organ_type", "queue_depth"}
)

# 1 second expressed in nanoseconds — must match the controller's
# ``_ONE_SECOND_NS`` constant exactly. Duplicated here rather than
# imported privately so this test depends only on the public byte-rate
# contract documented in Requirement 8.5.
_ONE_SECOND_NS = 1_000_000_000

# 50 MB byte estimate used in the byte-rate sliding-window test. The
# documented 1 s window means a single 50 MB enqueue at ``t=0`` is still
# fully visible at ``t=0.5s`` and fully out of the window by ``t=1.001s``.
_FIFTY_MB = 50 * 1024 * 1024


# ---------------------------------------------------------------------------
# Stub action — Protocol-compatible (only ``organ_id`` is read)
# ---------------------------------------------------------------------------


class _StubAction(SentinelModel):
    """Minimal frozen action object exposing only ``organ_id``.

    The :class:`BackpressureController` reads exactly one attribute from
    submissions — ``organ_id`` — via the structural ``_OrganActionLike``
    Protocol. Anything else (action body, payload bytes, expected output)
    is irrelevant. This stub matches that contract exactly so the test
    cannot accidentally depend on fields the controller does not actually
    consult.
    """

    organ_id: str

    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _envelope(*, max_actions: int) -> MissionAuthorityEnvelope:
    """Build a minimal :class:`MissionAuthorityEnvelope` for the controller.

    The controller consults only ``envelope.max_actions``; every other
    field is irrelevant to the admission decision. ``user_id``,
    ``mission_title``, and ``mission_objective`` are required by pydantic
    and filled with placeholder strings.
    """
    return MissionAuthorityEnvelope(
        user_id="user_p10",
        mission_title="property test mission",
        mission_objective="property test objective",
        max_actions=max_actions,
    )


def _controller(
    *,
    bus: EventBus,
    queue: ToolCallQueue,
    max_queue_depth: int = 1000,
    max_byte_rate_per_s: int = 10**12,
    max_organ_concurrency: int = 8,
    clock: Any = None,
) -> BackpressureController:
    """Construct a :class:`BackpressureController` for the test.

    ``max_byte_rate_per_s`` defaults to a deliberately enormous value so
    the byte-rate gate never fires accidentally in tests that target
    other gates; tests that DO exercise the byte-rate gate (test 3) pass
    a finite cap and an injected clock.
    """
    if clock is None:
        return BackpressureController(
            event_bus=bus,
            queue=queue,
            max_queue_depth=max_queue_depth,
            max_byte_rate_per_s=max_byte_rate_per_s,
            max_organ_concurrency=max_organ_concurrency,
        )
    return BackpressureController(
        event_bus=bus,
        queue=queue,
        max_queue_depth=max_queue_depth,
        max_byte_rate_per_s=max_byte_rate_per_s,
        max_organ_concurrency=max_organ_concurrency,
        clock=clock,
    )


def _make_queued_item(
    *,
    organ_id: str = "organ_filler",
    mission_id: str = _MISSION_ID,
    action_id: str = "act_filler",
) -> QueuedAction:
    """Build a :class:`QueuedAction` used to fill the queue directly.

    The controller never enqueues — it only inspects depth — so to
    trigger a queue-depth rejection in tests we push :class:`QueuedAction`
    instances onto the underlying :class:`ToolCallQueue` directly. The
    fields here are minimal valid values; the controller never reads them.
    """
    return QueuedAction(
        action_id=action_id,
        mission_id=mission_id,
        organ_id=organ_id,
        action_type="filler",
        priority=Priority.NORMAL,
        deadline_ms=1000,
        enqueued_at_ns=0,
        estimated_cost_ms=0,
    )


def _fill_queue(queue: ToolCallQueue, n: int) -> None:
    """Push ``n`` filler items onto ``queue`` so its depth becomes ``n``.

    Asserts each enqueue succeeds; if the underlying queue's
    ``max_depth`` is smaller than ``n`` this builder would silently
    rejected items, masking the test setup. The assertion guards against
    that.
    """
    for i in range(n):
        outcome = queue.enqueue(_make_queued_item(action_id=f"filler_{i}"))
        assert outcome.accepted, (
            f"setup error: filler item {i} not accepted by queue; "
            f"reason={outcome.reason!r}"
        )


def _drain_queue(queue: ToolCallQueue, n: int) -> None:
    """Pop ``n`` items off ``queue`` to lower its depth.

    Each dequeue increments the queue's per-organ in-flight counter; the
    counter is decremented immediately via :meth:`note_completion` so the
    test does not accidentally hit the per-organ concurrency cap on
    subsequent submissions.
    """
    for _ in range(n):
        item = queue.dequeue()
        assert item is not None, "setup error: queue drained too far"
        queue.note_completion(item.organ_id)


# ---------------------------------------------------------------------------
# Helpers — event lookup and assertion
# ---------------------------------------------------------------------------


def _events_of(bus: EventBus, event_type: AgentEventType) -> list[Any]:
    """Return every event of ``event_type`` from ``bus`` in append order."""
    return [ev for ev in bus.events() if ev.event_type == event_type]


def _applied_events(bus: EventBus) -> list[Any]:
    return _events_of(bus, AgentEventType.QUEUE_BACKPRESSURE_APPLIED)


def _cleared_events(bus: EventBus) -> list[Any]:
    return _events_of(bus, AgentEventType.QUEUE_BACKPRESSURE_CLEARED)


def _assert_bounds_within_envelope(
    decision: BackpressureDecision, envelope: MissionAuthorityEnvelope
) -> None:
    """Assert every entry in ``decision.bounds_used`` is ≤ envelope.max_actions.

    This is the Requirement 12.6 invariant in test form. The controller
    documents ``bounds_used`` as ``min(configured_bound,
    envelope.max_actions)`` for each clamped field, plus the envelope's
    own ``max_actions`` for transparency; every value MUST therefore be
    ≤ ``envelope.max_actions``.
    """
    for key, value in decision.bounds_used.items():
        assert value <= envelope.max_actions, (
            f"bounds_used[{key!r}]={value} exceeds envelope.max_actions="
            f"{envelope.max_actions}; controller widened authority"
        )
        assert value >= 0, (
            f"bounds_used[{key!r}]={value} is negative; this is a "
            "schema violation"
        )


# ---------------------------------------------------------------------------
# Controlled-clock helper for test 3
# ---------------------------------------------------------------------------


class _ControlledClock:
    """Mutable monotonic clock injected into :class:`BackpressureController`.

    The controller's byte-rate window is 1 s wide and is anchored on
    ``time.monotonic_ns`` by default. Tests that need to drive the
    window deterministically inject this stub instead. ``advance(ns)``
    moves the clock forward by ``ns`` nanoseconds; ``set(ns)`` jumps to
    an absolute value. The clock returns its current value when called
    as a callable.
    """

    def __init__(self, *, start_ns: int = 0) -> None:
        self._now_ns: int = int(start_ns)

    def __call__(self) -> int:
        return self._now_ns

    def advance(self, ns: int) -> None:
        if ns < 0:
            raise ValueError("controlled clock cannot go backwards")
        self._now_ns += int(ns)

    def set(self, ns: int) -> None:
        if ns < self._now_ns:
            raise ValueError("controlled clock cannot go backwards")
        self._now_ns = int(ns)


# ---------------------------------------------------------------------------
# 1. test_bounds_used_never_exceed_envelope (200 examples)
# ---------------------------------------------------------------------------


@given(
    envelope_max_actions=st.integers(min_value=1, max_value=10_000),
    configured_max_queue_depth=st.integers(min_value=1, max_value=10_000),
    configured_max_organ_concurrency=st.integers(min_value=1, max_value=10_000),
)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_bounds_used_never_exceed_envelope(
    envelope_max_actions: int,
    configured_max_queue_depth: int,
    configured_max_organ_concurrency: int,
) -> None:
    """Every bound returned by ``check_submission`` is ≤ envelope.max_actions.

    Hypothesis sweeps the three free parameters that govern the clamp:
    the envelope's ``max_actions`` ceiling, the configured queue-depth
    cap, and the configured per-organ concurrency cap. For every
    combination — including the awkward shapes where the configured
    cap massively overshoots the envelope — the controller MUST clamp
    each emitted bound down to (or below) ``envelope.max_actions``.

    The action body and queue state are irrelevant to this property, so
    the queue is empty and a single :class:`_StubAction` is submitted.
    The decision is asserted to be ``accepted=True`` (anchoring the
    property as non-vacuous in the empty-queue case) and every value in
    ``bounds_used`` is asserted to be ≤ ``envelope.max_actions``.

    Validates: Requirement 12.6.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    queue = ToolCallQueue(max_depth=max(configured_max_queue_depth, 1))
    controller = _controller(
        bus=bus,
        queue=queue,
        max_queue_depth=configured_max_queue_depth,
        max_organ_concurrency=configured_max_organ_concurrency,
    )
    envelope = _envelope(max_actions=envelope_max_actions)

    action = _StubAction(organ_id="organ_p10")
    decision = controller.check_submission(action, envelope=envelope)

    # Empty queue + accepted submission anchors the property as non-vacuous.
    assert decision.accepted is True, (
        f"expected accepted=True on empty queue, got reason={decision.reason!r}"
    )
    assert decision.reason == "within_envelope"

    # The Requirement 12.6 invariant.
    _assert_bounds_within_envelope(decision, envelope)


# ---------------------------------------------------------------------------
# 2. test_cleared_iff_predicate (200 examples)
# ---------------------------------------------------------------------------


# Operations driving the cleared-iff state machine.
#
# * "submit"  — call check_submission and capture the decision.
# * "fill_one"  — push a single filler onto the queue (raises queue depth by 1).
# * "drain_one" — pop one item off the queue (lowers queue depth by 1) if non-empty.
#
# The strategy mixes the three so Hypothesis exercises every interleaving
# of pressure-creating and pressure-relieving moves, which is what the
# cleared-iff predicate must hold across.
_op_st = st.sampled_from(("submit", "fill_one", "drain_one"))


@given(
    ops=st.lists(_op_st, min_size=1, max_size=20),
    max_queue_depth=st.integers(min_value=1, max_value=8),
)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_cleared_iff_predicate(
    ops: list[str], max_queue_depth: int
) -> None:
    """``QUEUE_BACKPRESSURE_CLEARED`` iff (was_under_pressure AND depth < cap).

    The cleared-iff rule (Requirement 8.7) is verified by re-running the
    state machine in pure Python alongside the controller. For every
    ``submit`` operation we predict whether the controller MUST emit
    ``CLEARED`` based on:

    * the model-tracked ``under_pressure`` flag (set on any prior
      rejection, cleared by the next ``CLEARED`` emission); and
    * the live queue depth being **strictly less** than the configured
      ``max_queue_depth``.

    After each submit we compare the count of ``CLEARED`` events on the
    bus to the predicted count. Filling the queue to the cap forces a
    rejection (which sets ``under_pressure=True``); draining the queue
    drops the depth below the cap and the next ``submit`` MUST emit
    exactly one ``CLEARED``. Subsequent submits without intervening
    rejection MUST NOT emit any further ``CLEARED`` — the iff direction.

    Validates: Requirement 8.7.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    queue = ToolCallQueue(max_depth=max_queue_depth)
    controller = _controller(
        bus=bus,
        queue=queue,
        max_queue_depth=max_queue_depth,
        # Generous concurrency so the cap never trips and confounds the test.
        max_organ_concurrency=1_000_000,
    )
    envelope = _envelope(max_actions=1_000_000)
    action = _StubAction(organ_id="organ_p10_iff")

    # Model state (mirrors the controller's private flag).
    expected_under_pressure = False
    expected_cleared_count = 0
    expected_applied_count = 0

    for op in ops:
        if op == "fill_one":
            if queue.depth() < max_queue_depth:
                _fill_queue(queue, 1)
            continue
        if op == "drain_one":
            if queue.depth() > 0:
                _drain_queue(queue, 1)
            continue

        # op == "submit"
        depth_before = queue.depth()
        decision = controller.check_submission(action, envelope=envelope)
        _assert_bounds_within_envelope(decision, envelope)

        if depth_before >= max_queue_depth:
            # Controller MUST reject with queue-depth-overflow.
            assert decision.accepted is False
            assert decision.reason == "queue_depth_overflow"
            expected_applied_count += 1
            # Any rejection sets the controller's under_pressure to True.
            expected_under_pressure = True
        else:
            assert decision.accepted is True
            assert decision.reason == "within_envelope"
            # Cleared iff the model says we were under pressure AND the
            # depth at decision time was strictly < cap. depth_before is
            # the value the controller observed.
            if expected_under_pressure and depth_before < max_queue_depth:
                expected_cleared_count += 1
                expected_under_pressure = False

        applied = _applied_events(bus)
        cleared = _cleared_events(bus)
        assert len(applied) == expected_applied_count, (
            f"after op={op!r} depth_before={depth_before} cap={max_queue_depth} "
            f"expected APPLIED count={expected_applied_count}, "
            f"got {len(applied)}"
        )
        assert len(cleared) == expected_cleared_count, (
            f"after op={op!r} depth_before={depth_before} cap={max_queue_depth} "
            f"expected CLEARED count={expected_cleared_count}, "
            f"got {len(cleared)}"
        )


# ---------------------------------------------------------------------------
# 3. test_byte_rate_window_1s_sliding (100 examples)
# ---------------------------------------------------------------------------


@given(
    # Initial clock offset — the window is relative, so the absolute
    # start value should not affect any assertion. Bounded to a wide
    # but reasonable range.
    start_ns=st.integers(min_value=0, max_value=10**18),
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_byte_rate_window_1s_sliding(start_ns: int) -> None:
    """The per-organ byte-rate window covers exactly 1 second.

    A 50 MB enqueue at logical ``t=0`` is fully visible at ``t=0.5s``
    (``sliding_byte_rate == 50 MB``) and fully outside the window by
    ``t=1.001s`` (``sliding_byte_rate == 0``). Hypothesis varies the
    absolute start time of the controlled clock to confirm the window
    is relative to ``now`` rather than tied to any wall-clock anchor.

    Validates: Requirement 8.5.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    queue = ToolCallQueue(max_depth=1000)
    clock = _ControlledClock(start_ns=start_ns)
    controller = _controller(
        bus=bus,
        queue=queue,
        max_queue_depth=1000,
        max_byte_rate_per_s=10**12,
        max_organ_concurrency=8,
        clock=clock,
    )
    action = _StubAction(organ_id="organ_p10_byterate")

    # t=0 — admit 50 MB.
    controller.note_enqueue(action, byte_estimate=_FIFTY_MB)
    assert controller.sliding_byte_rate(action.organ_id) == _FIFTY_MB

    # t=0.5s — still inside the window.
    clock.advance(_ONE_SECOND_NS // 2)
    assert controller.sliding_byte_rate(action.organ_id) == _FIFTY_MB, (
        "byte-rate MUST remain at 50 MB at t=0.5s; the entry has not "
        "yet aged out of the 1 s sliding window"
    )

    # t=1.001s — strictly past the window.
    # Advance from t=0.5s by another 501 ms to land at t=1.001s.
    clock.advance((_ONE_SECOND_NS // 2) + 1_000_000)
    assert controller.sliding_byte_rate(action.organ_id) == 0, (
        "byte-rate MUST drop to 0 at t=1.001s; the entry has aged out "
        "of the 1 s sliding window"
    )

    # Sanity: a fresh organ with no admissions reports zero at every t.
    assert controller.sliding_byte_rate("untouched_organ") == 0


# ---------------------------------------------------------------------------
# 4. test_payload_whitelist (200 examples)
# ---------------------------------------------------------------------------


@given(
    max_queue_depth=st.integers(min_value=1, max_value=8),
)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_payload_whitelist(max_queue_depth: int) -> None:
    """APPLIED and CLEARED payloads are exactly their documented whitelists.

    * ``QUEUE_BACKPRESSURE_APPLIED`` payload keys MUST equal
      ``{organ_type, queue_depth, estimated_wait_ms, reason}``.
    * ``QUEUE_BACKPRESSURE_CLEARED`` payload keys MUST equal
      ``{organ_type, queue_depth}``.

    Triggering both events in a single test isolates any regression that
    widens either payload (e.g. accidentally including action body, organ
    output, or secret material). The strict equality (``==`` rather than
    ``⊆``) catches both unauthorized additions AND silent removals.

    Validates: Requirements 8.2, 8.7, 12.6 (no secret leakage via events).
    """
    bus = EventBus(mission_id=_MISSION_ID)
    queue = ToolCallQueue(max_depth=max_queue_depth)
    controller = _controller(
        bus=bus,
        queue=queue,
        max_queue_depth=max_queue_depth,
        max_organ_concurrency=1_000_000,
    )
    envelope = _envelope(max_actions=1_000_000)
    action = _StubAction(organ_id="organ_p10_payload")

    # Trigger APPLIED — fill the queue to the cap so the next submit is
    # rejected with queue_depth_overflow.
    _fill_queue(queue, max_queue_depth)
    rejection = controller.check_submission(action, envelope=envelope)
    assert rejection.accepted is False
    assert rejection.reason == "queue_depth_overflow"

    applied = _applied_events(bus)
    assert len(applied) == 1, f"expected 1 APPLIED, got {len(applied)}"
    applied_payload = applied[0].payload
    assert set(applied_payload.keys()) == _APPLIED_PAYLOAD_KEYS, (
        f"APPLIED payload keys {sorted(applied_payload.keys())!r} "
        f"do not equal documented whitelist "
        f"{sorted(_APPLIED_PAYLOAD_KEYS)!r}"
    )
    assert applied_payload["organ_type"] == action.organ_id
    assert applied_payload["reason"] == "queue_depth_overflow"
    assert isinstance(applied_payload["queue_depth"], int)
    assert isinstance(applied_payload["estimated_wait_ms"], int)

    # Trigger CLEARED — drain the queue below cap and submit again.
    _drain_queue(queue, max_queue_depth)
    accept = controller.check_submission(action, envelope=envelope)
    assert accept.accepted is True
    _assert_bounds_within_envelope(accept, envelope)

    cleared = _cleared_events(bus)
    assert len(cleared) == 1, f"expected 1 CLEARED, got {len(cleared)}"
    cleared_payload = cleared[0].payload
    assert set(cleared_payload.keys()) == _CLEARED_PAYLOAD_KEYS, (
        f"CLEARED payload keys {sorted(cleared_payload.keys())!r} "
        f"do not equal documented whitelist "
        f"{sorted(_CLEARED_PAYLOAD_KEYS)!r}"
    )
    assert cleared_payload["organ_type"] == action.organ_id
    assert isinstance(cleared_payload["queue_depth"], int)


# ---------------------------------------------------------------------------
# 5. test_no_cleared_without_prior_pressure (200 examples)
# ---------------------------------------------------------------------------


@given(
    n_submissions=st.integers(min_value=1, max_value=50),
)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
def test_no_cleared_without_prior_pressure(n_submissions: int) -> None:
    """Repeated accepted submissions on an empty queue emit no CLEARED.

    The cleared-iff rule (Requirement 8.7) requires both predicates to
    hold; the "prior pressure" predicate is the one that prevents the
    controller from emitting ``CLEARED`` on every successful admission.
    This test pins the second axis of the iff: even with arbitrarily
    many accepted submissions, if no submission was ever rejected the
    bus contains zero ``CLEARED`` events.

    Validates: Requirement 8.7 (the "iff" direction — no CLEARED without
    prior pressure).
    """
    bus = EventBus(mission_id=_MISSION_ID)
    # Cap is generous so no submission is ever rejected — that is the
    # entire point of this property.
    queue = ToolCallQueue(max_depth=10_000)
    controller = _controller(
        bus=bus,
        queue=queue,
        max_queue_depth=10_000,
        max_organ_concurrency=1_000_000,
    )
    envelope = _envelope(max_actions=1_000_000)
    action = _StubAction(organ_id="organ_p10_no_cleared")

    for _ in range(n_submissions):
        decision = controller.check_submission(action, envelope=envelope)
        assert decision.accepted is True
        assert decision.reason == "within_envelope"
        _assert_bounds_within_envelope(decision, envelope)

    assert _applied_events(bus) == [], (
        "no rejection should occur on an under-cap queue"
    )
    assert _cleared_events(bus) == [], (
        "CLEARED MUST NOT be emitted without a prior rejection (no "
        "prior pressure means the iff predicate is False)"
    )
