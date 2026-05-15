# Feature: sentinel-performance-runtime-foundation, Property 12: Token-budget enforcement at frame, action, and mission scope
"""Property test — token-budget enforcement at frame, action, and mission.

**Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8.**

Property statement
------------------

Hypothesis-generated budgets, frames, and actions exercising every
:class:`TokenBudgetGovernor` enforcement scope:

* **Per-frame** — ``enforce_frame`` invokes ``compressor.compress`` at
  most :data:`DEFAULT_MAX_COMPRESSION_PASSES` (3) times. If the frame
  fits within those passes the decision is accepted; otherwise the
  frame is rejected after exactly that many passes and
  :data:`AgentEventType.BUDGET_EXCEEDED` is emitted with
  ``scope="frame"``.
* **Per-action** — ``enforce_action`` rejects pre-execution when the
  estimated token count exceeds the budget and emits
  :data:`AgentEventType.BUDGET_EXCEEDED` with ``scope="action"``;
  within-budget calls are accepted.
* **Per-mission warning** — :data:`AgentEventType.BUDGET_WARNING`
  fires exactly once per mission, on the first ``enforce_mission``
  call where cumulative spend crosses
  :data:`DEFAULT_WARNING_THRESHOLD` (0.9). The crossing predicate is
  ``previous < 0.9 * budget <= cumulative`` — strict ``<`` on the
  previous value, ``>=`` on the new cumulative.
* **Per-mission exhaustion** — once cumulative spend reaches the
  mission budget, ``enforce_mission`` returns rejected with
  ``reason=mission_exhausted``; subsequent ``enforce_action`` calls
  are rejected with the same reason; ``begin_call`` / ``end_call``
  are independent — in-flight bookkeeping is unaffected by exhaustion.
* **Event-payload whitelist** — every emitted event payload contains
  exactly the five keys ``{scope, mission_id, tokens_used,
  tokens_budget, reason}`` and nothing else (Requirements 12.1, 12.8
  cross-cutting safety contract documented in the governor's module
  docstring).

Hypothesis settings
-------------------

``max_examples=100, deadline=None`` per the task spec.
``HealthCheck.too_slow`` is suppressed because the per-mission warning
walk pushes up to ~30 deltas through the governor per example, which
is slightly slower than the default Hypothesis budget; total runtime
per test is small.
"""

from __future__ import annotations

from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.perf.caches.token_budget_governor import (
    DEFAULT_MAX_COMPRESSION_PASSES,
    DEFAULT_WARNING_THRESHOLD,
    REASON_ACTION_REJECTED,
    REASON_FRAME_COMPRESSED,
    REASON_FRAME_REJECTED,
    REASON_MISSION_EXHAUSTED,
    REASON_WARNING_THRESHOLD_CROSSED,
    REASON_WITHIN_BUDGET,
    SCOPE_ACTION,
    SCOPE_FRAME,
    SCOPE_MISSION,
    TokenBudgetGovernor,
)
from sentinel.shared.events import AgentEventType, EventBus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


_MISSION_ID = "mission_p12"

# The complete payload-key whitelist for every event the governor
# emits — see the governor module docstring section
# "Hard-constraint event payload schema". Enforced explicitly in
# :func:`test_event_payload_whitelist` and asserted opportunistically
# inside the other property tests via :func:`_assert_payload_whitelisted`.
_PAYLOAD_KEYS: frozenset[str] = frozenset(
    {"scope", "mission_id", "tokens_used", "tokens_budget", "reason"}
)


# ---------------------------------------------------------------------------
# Mocks — duck-typed frame and compressor
# ---------------------------------------------------------------------------


class _MockFrame:
    """Minimal frame-shaped object exposing a ``token_count`` attribute.

    :func:`sentinel.perf.caches.token_budget_governor._estimate_frame_tokens`
    reads ``token_count`` directly, so this lightweight stand-in is
    sufficient and avoids the heavyweight :class:`LLMDecisionFrame`
    pipeline (which would require a full evidence ranker, prompt
    budget allocator, and authority envelope just to populate one
    integer).
    """

    __slots__ = ("token_count",)

    def __init__(self, token_count: int) -> None:
        self.token_count = max(0, int(token_count))


class _MockCompressor:
    """Mock compressor that multiplies ``frame.token_count`` by ``factor``.

    Returns a fresh :class:`_MockFrame` each call (matching the
    real :class:`ContextCompressor` semantics: compression returns
    a new compressed frame rather than mutating in place). The
    :attr:`passes` counter records the number of compression passes
    invoked so the test can verify the governor stops at the
    configured maximum (Requirement 10.3 — at most 3 passes).
    """

    def __init__(self, factor: float) -> None:
        self._factor = factor
        self.passes = 0

    def compress(self, frame: _MockFrame) -> _MockFrame:
        self.passes += 1
        return _MockFrame(token_count=int(frame.token_count * self._factor))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _budget_events(bus: EventBus) -> list[Any]:
    """Return every budget-family event the governor emitted on ``bus``.

    The governor only emits the three budget event types; filtering
    here makes the assertions oblivious to any unrelated lifecycle
    events that might be appended by a future surrounding harness.
    """
    return [
        ev
        for ev in bus.events()
        if ev.event_type
        in (
            AgentEventType.BUDGET_WARNING,
            AgentEventType.BUDGET_EXCEEDED,
            AgentEventType.BUDGET_EXHAUSTED,
        )
    ]


def _assert_payload_whitelisted(payload: dict[str, Any]) -> None:
    """Assert ``payload`` carries exactly the five whitelisted keys.

    Centralizes the check used by every property test below so
    payload-shape regressions are caught uniformly across paths.
    """
    assert set(payload.keys()) == _PAYLOAD_KEYS, (
        f"event payload key set {sorted(payload.keys())!r} differs from "
        f"whitelist {sorted(_PAYLOAD_KEYS)!r}"
    )


def _expected_frame_outcome(
    *, frame_size: int, frame_budget: int, factor: float, max_passes: int
) -> tuple[bool, str, int, int]:
    """Compute the expected (accepted, reason, tokens_used, passes) tuple.

    Mirrors the governor's own loop semantics exactly — using the same
    ``int(tokens * factor)`` formula the mock compressor applies — so
    the property test is reproducing the governor's algorithm with
    the same arithmetic operators. This is intentional: the property
    being asserted is that the governor's *decision* (accept / reject,
    and the reason tag) follows the documented loop rule for any
    Hypothesis-sampled triple, not that the governor implements some
    independent oracle.
    """
    tokens = frame_size
    if tokens <= frame_budget:
        return (True, REASON_WITHIN_BUDGET, tokens, 0)
    passes = 0
    while passes < max_passes and tokens > frame_budget:
        tokens = int(tokens * factor)
        passes += 1
    if tokens <= frame_budget:
        return (True, REASON_FRAME_COMPRESSED, tokens, passes)
    return (False, REASON_FRAME_REJECTED, tokens, passes)


# ---------------------------------------------------------------------------
# 1. Frame compression at most 3 passes
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    frame_size=st.integers(min_value=1, max_value=2_000),
    frame_budget=st.integers(min_value=1, max_value=1_000),
    compressor_factor=st.floats(
        min_value=0.0,
        max_value=1.5,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_frame_compression_at_most_3_passes(
    frame_size: int, frame_budget: int, compressor_factor: float
) -> None:
    """``enforce_frame`` runs at most 3 compression passes (Requirement 10.3).

    For every Hypothesis-sampled ``(frame_size, frame_budget,
    compressor_factor)``:

    * If the initial frame already fits within ``frame_budget`` —
      no compression runs, the decision is accepted with
      ``reason=REASON_WITHIN_BUDGET``.
    * If compression brings the frame within budget within the
      governor's ``max_compression_passes`` cap (default 3) — the
      decision is accepted with ``reason=REASON_FRAME_COMPRESSED``,
      the compressor was invoked at most 3 times, and no
      :data:`AgentEventType.BUDGET_EXCEEDED` event was emitted.
    * If compression cannot reduce the frame within 3 passes — the
      decision is rejected with ``reason=REASON_FRAME_REJECTED``,
      the compressor was invoked exactly 3 times, and
      :data:`AgentEventType.BUDGET_EXCEEDED` is emitted with
      ``scope=frame`` and the same ``reason`` tag.

    Compressors with ``factor >= 1.0`` (no-op or expanding) exercise
    the rejection path on any over-budget frame; ``factor < 1.0``
    exercises the multi-pass acceptance path.

    Validates: Requirements 10.1, 10.2, 10.3.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    governor = TokenBudgetGovernor(event_bus=bus)
    compressor = _MockCompressor(factor=compressor_factor)
    frame = _MockFrame(token_count=frame_size)

    expected_accepted, expected_reason, expected_tokens, expected_passes = (
        _expected_frame_outcome(
            frame_size=frame_size,
            frame_budget=frame_budget,
            factor=compressor_factor,
            max_passes=DEFAULT_MAX_COMPRESSION_PASSES,
        )
    )

    returned_frame, decision = governor.enforce_frame(
        _MISSION_ID,
        lambda: frame,
        compressor,
        frame_budget,
    )

    # Decision matches the documented loop rule.
    assert decision.accepted is expected_accepted, (
        f"frame_size={frame_size}, frame_budget={frame_budget}, "
        f"factor={compressor_factor!r}: "
        f"decision.accepted={decision.accepted!r} != "
        f"expected={expected_accepted!r}"
    )
    assert decision.reason == expected_reason
    assert decision.tokens_used == expected_tokens
    assert decision.tokens_budget == frame_budget

    # Compressor was invoked at most max_compression_passes times,
    # and exactly that many times on the rejection path.
    assert compressor.passes == expected_passes
    assert compressor.passes <= DEFAULT_MAX_COMPRESSION_PASSES

    # Returned frame carries the post-compression token count, not
    # the original (verifies the governor returns the *compressed*
    # frame even on rejection so the caller can inspect what was
    # tried).
    assert isinstance(returned_frame, _MockFrame)
    assert returned_frame.token_count == expected_tokens

    # Event-stream contract.
    events = _budget_events(bus)
    if expected_accepted:
        assert events == [], (
            "no BUDGET_* events should be emitted on the acceptance path"
        )
    else:
        assert len(events) == 1
        ev = events[0]
        assert ev.event_type == AgentEventType.BUDGET_EXCEEDED
        _assert_payload_whitelisted(ev.payload)
        assert ev.payload["scope"] == SCOPE_FRAME
        assert ev.payload["mission_id"] == _MISSION_ID
        assert ev.payload["tokens_used"] == expected_tokens
        assert ev.payload["tokens_budget"] == frame_budget
        assert ev.payload["reason"] == REASON_FRAME_REJECTED


# ---------------------------------------------------------------------------
# 2. Action pre-execution rejects over budget
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    estimated_tokens=st.integers(min_value=0, max_value=10_000),
    action_budget=st.integers(min_value=1, max_value=5_000),
)
def test_action_pre_execution_rejects_over_budget(
    estimated_tokens: int, action_budget: int
) -> None:
    """``enforce_action`` rejects pre-execution when over budget (Req 10.5).

    For every Hypothesis-sampled ``(estimated_tokens, action_budget)``:

    * If ``estimated_tokens > action_budget`` — the decision is
      rejected with ``reason=REASON_ACTION_REJECTED`` and a single
      :data:`AgentEventType.BUDGET_EXCEEDED` event is emitted with
      ``scope=action``.
    * Otherwise the decision is accepted with
      ``reason=REASON_WITHIN_BUDGET`` and no event is emitted.

    The mission counter is untouched on either path — ``enforce_action``
    is a *pre*-execution check; it does not consume budget itself.

    Validates: Requirements 10.4, 10.5.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    governor = TokenBudgetGovernor(event_bus=bus)

    decision = governor.enforce_action(
        _MISSION_ID,
        estimated_tokens=estimated_tokens,
        action_budget=action_budget,
    )

    assert decision.tokens_budget == action_budget
    assert decision.tokens_used == estimated_tokens

    if estimated_tokens > action_budget:
        assert decision.accepted is False
        assert decision.reason == REASON_ACTION_REJECTED

        events = _budget_events(bus)
        assert len(events) == 1
        ev = events[0]
        assert ev.event_type == AgentEventType.BUDGET_EXCEEDED
        _assert_payload_whitelisted(ev.payload)
        assert ev.payload["scope"] == SCOPE_ACTION
        assert ev.payload["mission_id"] == _MISSION_ID
        assert ev.payload["tokens_used"] == estimated_tokens
        assert ev.payload["tokens_budget"] == action_budget
        assert ev.payload["reason"] == REASON_ACTION_REJECTED
    else:
        assert decision.accepted is True
        assert decision.reason == REASON_WITHIN_BUDGET
        assert _budget_events(bus) == []

    # Pre-execution check does not consume budget — mission counter
    # is still zero regardless of the action verdict.
    assert governor.mission_spent(_MISSION_ID) == 0


# ---------------------------------------------------------------------------
# 3. Mission warning fires exactly once at threshold crossing
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    deltas=st.lists(
        st.integers(min_value=0, max_value=200),
        min_size=1,
        max_size=30,
    ),
    mission_budget=st.integers(min_value=10, max_value=10_000),
)
def test_mission_warning_fires_exactly_once_at_threshold_crossing(
    deltas: list[int], mission_budget: int
) -> None:
    """:data:`AgentEventType.BUDGET_WARNING` fires exactly at the crossing.

    Replays a Hypothesis-sampled list of ``tokens_just_spent`` deltas
    against ``enforce_mission`` and asserts:

    * The warning fires on the **first** call where the cumulative
      spend transitions from ``< 0.9 * mission_budget`` to
      ``>= 0.9 * mission_budget`` (boundary is in-bounds — the
      crossing predicate uses ``>=`` on the new cumulative).
    * The warning fires **at most once** per mission, regardless of
      how many subsequent calls also satisfy ``cumulative >= 0.9 *
      mission_budget``.
    * If no delta sequence ever crosses the threshold, no warning is
      emitted at all.
    * Every warning payload satisfies the five-key whitelist with
      ``scope=mission`` and ``reason=REASON_WARNING_THRESHOLD_CROSSED``.

    The crossing is computed independently from the governor's
    counter using a plain Python loop — that is the ground truth the
    governor must match.

    Validates: Requirements 10.6, 10.8.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    governor = TokenBudgetGovernor(event_bus=bus)

    warning_floor = DEFAULT_WARNING_THRESHOLD * mission_budget

    # Walk the deltas independently to compute the ground-truth
    # crossing index (or ``None`` if the cumulative never crosses).
    cumulative = 0
    expected_crossing_index: int | None = None
    expected_crossing_cumulative: int | None = None
    for index, delta in enumerate(deltas):
        previous = cumulative
        cumulative += max(0, delta)
        if (
            previous < warning_floor
            and cumulative >= warning_floor
            and expected_crossing_index is None
        ):
            expected_crossing_index = index
            expected_crossing_cumulative = cumulative

    # Replay against the governor.
    for delta in deltas:
        governor.enforce_mission(
            _MISSION_ID,
            tokens_just_spent=delta,
            mission_budget=mission_budget,
        )

    # Collect every BUDGET_WARNING event for this mission.
    warning_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.BUDGET_WARNING
        and ev.payload.get("mission_id") == _MISSION_ID
    ]

    if expected_crossing_index is None:
        assert warning_events == [], (
            f"deltas={deltas!r} mission_budget={mission_budget}: "
            "cumulative never crossed 0.9 threshold but a warning was emitted"
        )
    else:
        # Exactly one warning, fired at the documented crossing.
        assert len(warning_events) == 1, (
            f"deltas={deltas!r} mission_budget={mission_budget}: "
            f"expected exactly one BUDGET_WARNING, got {len(warning_events)}"
        )
        ev = warning_events[0]
        _assert_payload_whitelisted(ev.payload)
        assert ev.payload["scope"] == SCOPE_MISSION
        assert ev.payload["reason"] == REASON_WARNING_THRESHOLD_CROSSED
        assert ev.payload["tokens_used"] == expected_crossing_cumulative
        assert ev.payload["tokens_budget"] == mission_budget


# ---------------------------------------------------------------------------
# 4. Mission exhaustion blocks new calls only
# ---------------------------------------------------------------------------


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    mission_budget=st.integers(min_value=10, max_value=1_000),
    overshoot=st.integers(min_value=0, max_value=500),
    in_flight_count=st.integers(min_value=0, max_value=8),
    action_tokens=st.integers(min_value=0, max_value=50),
    action_budget=st.integers(min_value=10, max_value=500),
)
def test_mission_exhaustion_blocks_new_calls_only(
    mission_budget: int,
    overshoot: int,
    in_flight_count: int,
    action_tokens: int,
    action_budget: int,
) -> None:
    """Exhaustion blocks **new** calls; in-flight bookkeeping is independent.

    Per Requirement 10.7: "block new model calls for that mission …
    allow in-flight model calls to complete without cancellation".
    The governor implements that by:

    * marking the mission exhausted via
      :attr:`TokenBudgetGovernor._mission_exhausted`,
    * short-circuiting :meth:`enforce_action` to reject with
      ``reason=REASON_MISSION_EXHAUSTED``,
    * leaving :meth:`begin_call` / :meth:`end_call` (the in-flight
      counter) untouched.

    Hypothesis sweeps the budget, the overshoot amount used to push
    the mission to exhaustion, the number of in-flight calls
    started before exhaustion, and the parameters of the post-
    exhaustion ``enforce_action`` probe — including
    ``action_tokens <= action_budget`` so the rejection path
    cannot be confused with the over-budget path tested in test 2.

    Validates: Requirements 10.6, 10.7.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    governor = TokenBudgetGovernor(event_bus=bus)

    # Record some in-flight calls *before* exhaustion. These must
    # survive exhaustion without being decremented or cancelled.
    for _ in range(in_flight_count):
        governor.begin_call(_MISSION_ID)
    assert governor.in_flight(_MISSION_ID) == in_flight_count

    # Push the mission to exhaustion with a single large delta.
    exhausting_delta = mission_budget + overshoot
    decision = governor.enforce_mission(
        _MISSION_ID,
        tokens_just_spent=exhausting_delta,
        mission_budget=mission_budget,
    )
    assert decision.accepted is False
    assert decision.reason == REASON_MISSION_EXHAUSTED
    assert decision.tokens_used == exhausting_delta
    assert governor.is_mission_exhausted(_MISSION_ID) is True

    # Mission-scope BUDGET_EXHAUSTED was emitted exactly once.
    mission_exhausted_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.BUDGET_EXHAUSTED
        and ev.payload.get("scope") == SCOPE_MISSION
        and ev.payload.get("mission_id") == _MISSION_ID
    ]
    assert len(mission_exhausted_events) == 1
    _assert_payload_whitelisted(mission_exhausted_events[0].payload)
    assert (
        mission_exhausted_events[0].payload["reason"]
        == REASON_MISSION_EXHAUSTED
    )

    # In-flight counter is independent of exhaustion — every begin_call
    # made before the exhausting delta is still recorded.
    assert governor.in_flight(_MISSION_ID) == in_flight_count, (
        "in-flight counter must be independent of mission exhaustion "
        "(Requirement 10.7 — in-flight calls must not be cancelled)"
    )

    # New ``enforce_action`` is rejected with mission_exhausted, even
    # for an action that would otherwise be within budget.
    action_decision = governor.enforce_action(
        _MISSION_ID,
        estimated_tokens=action_tokens,
        action_budget=action_budget,
    )
    assert action_decision.accepted is False
    assert action_decision.reason == REASON_MISSION_EXHAUSTED

    action_blocked_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.BUDGET_EXHAUSTED
        and ev.payload.get("scope") == SCOPE_ACTION
        and ev.payload.get("mission_id") == _MISSION_ID
    ]
    assert len(action_blocked_events) == 1
    _assert_payload_whitelisted(action_blocked_events[0].payload)
    assert (
        action_blocked_events[0].payload["reason"] == REASON_MISSION_EXHAUSTED
    )

    # In-flight calls can still be ended; the counter decrements
    # normally. Confirms the in-flight bookkeeping path is unaffected
    # by exhaustion.
    for i in range(in_flight_count):
        governor.end_call(_MISSION_ID)
        assert governor.in_flight(_MISSION_ID) == in_flight_count - (i + 1)
    assert governor.in_flight(_MISSION_ID) == 0


# ---------------------------------------------------------------------------
# 5. Event payload whitelist (cross-path)
# ---------------------------------------------------------------------------


def test_event_payload_whitelist() -> None:
    """Every emitted event payload contains exactly the five whitelisted keys.

    Drives the governor through every event-emitting path in a
    single test so the payload-shape assertion is enforced uniformly:

    * frame rejection      → BUDGET_EXCEEDED, scope=frame
    * action rejection     → BUDGET_EXCEEDED, scope=action
    * mission warning      → BUDGET_WARNING,  scope=mission
    * mission exhaustion   → BUDGET_EXHAUSTED, scope=mission
    * action blocked post-exhaustion → BUDGET_EXHAUSTED, scope=action

    Each emitted payload is asserted to:

    * contain exactly the keys ``{scope, mission_id, tokens_used,
      tokens_budget, reason}`` and nothing else;
    * carry valid scope and reason tags from the documented enum;
    * carry no frame body, action input, evidence content, prompt
      text, organ output, or secret value (verified by the strict
      key-set check — any leak would require an extra key).

    Validates: Requirements 10.3, 10.5, 10.7, 10.8 (payload contract
    cross-cutting safety constraint described in
    :mod:`sentinel.perf.caches.token_budget_governor`).
    """
    bus = EventBus(mission_id=_MISSION_ID)
    governor = TokenBudgetGovernor(event_bus=bus)

    # 1. Frame rejection — over-budget frame, no-op compressor.
    rejecting_compressor = _MockCompressor(factor=1.0)
    governor.enforce_frame(
        _MISSION_ID,
        lambda: _MockFrame(token_count=500),
        rejecting_compressor,
        frame_budget=100,
    )

    # 2. Action rejection — over-budget action, mission still alive
    # (use a separate mission id so the post-exhaustion path below
    # exercises a fresh mission counter without pre-existing spend).
    other_mission = "mission_p12_action"
    governor.enforce_action(
        other_mission,
        estimated_tokens=200,
        action_budget=50,
    )

    # 3. Mission warning + 4. Mission exhaustion — single big delta on
    # a third mission so warning and exhaustion both fire from one
    # ``enforce_mission`` call.
    exhausting_mission = "mission_p12_exhaust"
    governor.enforce_mission(
        exhausting_mission,
        tokens_just_spent=200,
        mission_budget=100,
    )

    # 5. Post-exhaustion action — rejected with mission_exhausted.
    governor.enforce_action(
        exhausting_mission,
        estimated_tokens=10,
        action_budget=100,
    )

    # Verify every emitted budget-event payload satisfies the
    # whitelist. The expected event-type + scope + reason tuples are
    # listed below; the order matches the order of emission above.
    expected_paths: list[tuple[AgentEventType, str, str]] = [
        (AgentEventType.BUDGET_EXCEEDED, SCOPE_FRAME, REASON_FRAME_REJECTED),
        (AgentEventType.BUDGET_EXCEEDED, SCOPE_ACTION, REASON_ACTION_REJECTED),
        (
            AgentEventType.BUDGET_WARNING,
            SCOPE_MISSION,
            REASON_WARNING_THRESHOLD_CROSSED,
        ),
        (
            AgentEventType.BUDGET_EXHAUSTED,
            SCOPE_MISSION,
            REASON_MISSION_EXHAUSTED,
        ),
        (
            AgentEventType.BUDGET_EXHAUSTED,
            SCOPE_ACTION,
            REASON_MISSION_EXHAUSTED,
        ),
    ]

    events = _budget_events(bus)
    assert len(events) == len(expected_paths), (
        f"expected {len(expected_paths)} budget events, got {len(events)}: "
        f"{[(ev.event_type, ev.payload.get('scope'), ev.payload.get('reason')) for ev in events]!r}"
    )

    for ev, (expected_type, expected_scope, expected_reason) in zip(
        events, expected_paths, strict=True
    ):
        # Payload-shape contract — exact key set, no body, no secret.
        _assert_payload_whitelisted(ev.payload)

        # Event type and scope/reason tags match the documented path.
        assert ev.event_type == expected_type
        assert ev.payload["scope"] == expected_scope
        assert ev.payload["reason"] == expected_reason

        # ``mission_id`` is a plain string — never a dict, never a
        # nested structure that could carry hidden context bodies.
        assert isinstance(ev.payload["mission_id"], str)

        # Counters are non-negative integers — not floats, not
        # strings, never the raw frame or action object.
        assert isinstance(ev.payload["tokens_used"], int)
        assert isinstance(ev.payload["tokens_budget"], int)
        assert ev.payload["tokens_used"] >= 0
        assert ev.payload["tokens_budget"] >= 0
