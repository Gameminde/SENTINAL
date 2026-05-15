# Feature: sentinel-performance-runtime-foundation, Property 11: Decision-frame cache lifecycle and prefix reuse
"""Property test — decision-frame cache lifecycle and prefix reuse.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7.**

Property statement
------------------

* TTL/LRU/authority-change invariants on
  :class:`LLMDecisionFrameCache`.
* Per-mission counters reported by ``cache.stats(mission_id)`` equal
  the ground-truth event counts that the cache emitted on the
  :class:`EventBus` (Requirement 9.4 — no counter is incremented on
  an outcome that does not match its event type).
* :meth:`PromptFrameCache.reuse_prefix` output equals a manually
  concatenated ``prefix + delta_render`` (Requirement 9.3).

Hypothesis settings
-------------------

``max_examples=100, deadline=None`` per the task spec.
``HealthCheck.too_slow`` is suppressed because the per-mission LRU
test pushes 130+ entries through the cache, which is slightly slower
than the default Hypothesis budget; total runtime per test is small.
"""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.agent.evidence_ranker import EvidenceCard
from sentinel.perf.caches.llm_decision_frame_cache import (
    CACHE_TYPE as FRAME_CACHE_TYPE,
)
from sentinel.perf.caches.llm_decision_frame_cache import (
    MAX_ENTRIES_PER_MISSION,
    TTL_SECONDS,
    LLMDecisionFrameCache,
)
from sentinel.perf.caches.prompt_frame_cache import (
    CACHE_TYPE_PREFIX as PROMPT_PREFIX_CACHE_TYPE,
)
from sentinel.perf.caches.prompt_frame_cache import PromptFrameCache
from sentinel.shared.events import AgentEventType, EventBus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


_MISSION_A = "mission_p11_a"
_MISSION_B = "mission_p11_b"

# Eviction-reason tags. Mirrored from the cache's private module
# constants so this test only depends on the public payload contract.
_REASON_TTL_EXPIRED = "ttl_expired"
_REASON_AUTHORITY_EXPANSION = "authority_expansion_bypass"
_REASON_RAW_SECRET_LEAKAGE = "raw_secret_leakage_bypass"
_REASON_LRU_CAPACITY = "lru_capacity"


# ---------------------------------------------------------------------------
# Controlled clock
# ---------------------------------------------------------------------------


class _ManualClock:
    """A monotonic-ns clock whose advance is fully under test control.

    Tests for the 600 s TTL boundary need to step past
    :data:`TTL_SECONDS` without sleeping. The cache accepts a
    ``clock`` callable returning nanoseconds; this holder satisfies
    that contract while exposing :meth:`advance` for whole-second
    steps.
    """

    def __init__(self, start_ns: int = 0) -> None:
        self._now_ns = start_ns

    def __call__(self) -> int:
        return self._now_ns

    def advance(self, *, seconds: int) -> None:
        """Advance the clock by ``seconds`` whole seconds."""
        self._now_ns += seconds * 10**9


# ---------------------------------------------------------------------------
# Frame builder
# ---------------------------------------------------------------------------


def _frame(
    *,
    frame_hash: str,
    authority_expansion: bool = False,
    raw_secret_leakage: bool = False,
) -> SimpleNamespace:
    """Build a frame-shaped object for :class:`LLMDecisionFrameCache`.

    The cache only reads ``frame.frame_hash``,
    ``frame.authority_expansion``, and ``frame.raw_secret_leakage``;
    a :class:`types.SimpleNamespace` is sufficient and avoids the
    heavyweight :meth:`LLMDecisionFrame.build` pipeline. The cache
    deep-copies on store, so subsequent mutation of the input does
    not affect the cached entry — the white-box mutation tests
    reach into ``cache._entries`` directly to test the read-side
    safety guard (Requirements 12.2, 12.3).
    """
    return SimpleNamespace(
        frame_hash=frame_hash,
        authority_expansion=authority_expansion,
        raw_secret_leakage=raw_secret_leakage,
    )


def _composite(
    cache: LLMDecisionFrameCache,
    *,
    mission_hot_hash: str = "hot_v1",
    authority_hash: str = "auth_v1",
    evidence_set_hash: str = "ev_v1",
    tool_surface_hash: str = "tool_v1",
) -> str:
    """Convenience wrapper around :meth:`composite_hash` with defaults."""
    return cache.composite_hash(
        mission_hot_hash=mission_hot_hash,
        authority_hash=authority_hash,
        evidence_set_hash=evidence_set_hash,
        tool_surface_hash=tool_surface_hash,
    )


# ---------------------------------------------------------------------------
# Event-stream helpers
# ---------------------------------------------------------------------------


def _frame_cache_events(
    bus: EventBus, *, mission_id: str
) -> list[dict[str, Any]]:
    """Return all frame-cache event payloads for ``mission_id``.

    Filters by ``cache_type == FRAME_CACHE_TYPE`` so the
    prefix-table events emitted by :class:`PromptFrameCache` cannot
    accidentally count toward the frame-cache counters.
    """
    return [
        ev.payload
        for ev in bus.events()
        if ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("mission_id") == mission_id
    ]


def _ground_truth_counters(
    bus: EventBus, *, mission_id: str
) -> dict[str, int]:
    """Compute the ground-truth per-mission counters from the event stream.

    The five per-mission counters tracked by
    :meth:`LLMDecisionFrameCache.stats`:

    * ``hits``           — :data:`AgentEventType.CACHE_HIT` count.
    * ``misses``         — :data:`AgentEventType.CACHE_MISS` count.
    * ``evictions``      — :data:`AgentEventType.CACHE_EVICTED` with
                           ``reason="lru_capacity"``.
    * ``ttl_evictions``  — :data:`AgentEventType.CACHE_EVICTED` with
                           ``reason="ttl_expired"``.
    * ``safety_bypasses``— :data:`AgentEventType.CACHE_EVICTED` with
                           ``reason="authority_expansion_bypass"`` or
                           ``"raw_secret_leakage_bypass"``.

    Computed by walking the bus's event stream and matching the
    documented payload shape. Requirement 9.4 — the counters MUST
    equal these ground-truth event counts.
    """
    counters = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "ttl_evictions": 0,
        "safety_bypasses": 0,
    }
    for ev in bus.events():
        payload = ev.payload
        if payload.get("cache_type") != FRAME_CACHE_TYPE:
            continue
        if payload.get("mission_id") != mission_id:
            continue
        if ev.event_type == AgentEventType.CACHE_HIT:
            counters["hits"] += 1
        elif ev.event_type == AgentEventType.CACHE_MISS:
            counters["misses"] += 1
        elif ev.event_type == AgentEventType.CACHE_EVICTED:
            reason = payload.get("reason")
            if reason == _REASON_LRU_CAPACITY:
                counters["evictions"] += 1
            elif reason == _REASON_TTL_EXPIRED:
                counters["ttl_evictions"] += 1
            elif reason in (
                _REASON_AUTHORITY_EXPANSION,
                _REASON_RAW_SECRET_LEAKAGE,
            ):
                counters["safety_bypasses"] += 1
    return counters


# ---------------------------------------------------------------------------
# 1. LRU cap enforced per mission
# ---------------------------------------------------------------------------


def test_lru_cap_enforced_per_mission() -> None:
    """LRU cap (128) is enforced per mission. Mission B is untouched.

    Insert 130 frames for mission A (>128) and assert:

    * mission A's bucket size stays at exactly
      :data:`MAX_ENTRIES_PER_MISSION` (128);
    * the two oldest mission-A entries are evicted (LRU FIFO order);
    * mission B's 5 entries are untouched — its bucket still holds
      all 5 keys after mission A's overflow;
    * each mission-A LRU eviction emits one
      :data:`AgentEventType.CACHE_EVICTED` event with
      ``reason="lru_capacity"`` and ``mission_id="mission_p11_a"``;
    * **no** mission-B eviction event is emitted.

    Validates: Requirement 9.2.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus)

    # Mission B: 5 entries, all should remain present after mission A's
    # overflow because the LRU cap is enforced **per mission**.
    b_composites: list[str] = []
    for i in range(5):
        comp = _composite(cache, mission_hot_hash=f"b_hot_{i:03d}")
        b_composites.append(comp)
        cache.put(comp, _frame(frame_hash=f"b_hash_{i:03d}"), mission_id=_MISSION_B)

    # Mission A: 130 entries — 2 over the cap.
    a_composites: list[str] = []
    for i in range(130):
        comp = _composite(cache, mission_hot_hash=f"a_hot_{i:03d}")
        a_composites.append(comp)
        cache.put(comp, _frame(frame_hash=f"a_hash_{i:03d}"), mission_id=_MISSION_A)

    # Mission A bucket capped at MAX_ENTRIES_PER_MISSION.
    assert len(cache._entries[_MISSION_A]) == MAX_ENTRIES_PER_MISSION, (
        f"mission A bucket should be capped at {MAX_ENTRIES_PER_MISSION}, "
        f"got {len(cache._entries[_MISSION_A])}"
    )

    # Mission B bucket untouched — all 5 entries still present.
    assert len(cache._entries[_MISSION_B]) == 5
    for comp in b_composites:
        assert comp in cache._entries[_MISSION_B], (
            f"mission B entry {comp!r} should be untouched by mission A's "
            "LRU overflow but was evicted"
        )

    # Two oldest mission-A entries (indices 0 and 1) were evicted in
    # FIFO order.
    assert a_composites[0] not in cache._entries[_MISSION_A]
    assert a_composites[1] not in cache._entries[_MISSION_A]
    # The 3rd through 130th remain.
    for comp in a_composites[2:]:
        assert comp in cache._entries[_MISSION_A]

    # Exactly 2 LRU-eviction events for mission A; none for mission B.
    a_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("mission_id") == _MISSION_A
        and ev.payload.get("reason") == _REASON_LRU_CAPACITY
    ]
    assert len(a_evictions) == 2, (
        f"expected 2 LRU evictions for mission A, got {len(a_evictions)}"
    )

    b_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("mission_id") == _MISSION_B
    ]
    assert b_evictions == [], (
        "mission B should not have any eviction events from mission A's overflow"
    )

    # Counter for mission A reflects the 2 LRU evictions; mission B
    # has zero evictions.
    assert cache.stats(_MISSION_A)["evictions"] == 2
    assert cache.stats(_MISSION_B)["evictions"] == 0


# ---------------------------------------------------------------------------
# 2. TTL expires after 600s
# ---------------------------------------------------------------------------


def test_ttl_expires_after_600s() -> None:
    """TTL bound is exactly :data:`TTL_SECONDS` (600s).

    With a controlled clock at t=0:

    * put a frame, advance to t=600 s — get returns the cached
      frame (boundary is in-bounds; cache uses strict ``>`` against
      ``_TTL_NS``);
    * advance to t=601 s — get returns ``None`` and the cache emits
      :data:`AgentEventType.CACHE_EVICTED` with
      ``reason="ttl_expired"``;
    * subsequent get is a plain miss (entry already evicted).

    Validates: Requirement 9.7.
    """
    clock = _ManualClock(start_ns=0)
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus, clock=clock)
    composite = _composite(cache)

    cache.put(composite, _frame(frame_hash="hash_v1"), mission_id=_MISSION_A)

    # Within the 600 s TTL: boundary is in-bounds.
    clock.advance(seconds=TTL_SECONDS)
    result = cache.get(composite, mission_id=_MISSION_A)
    assert result is not None, (
        f"frame should still hit at exactly {TTL_SECONDS} s — cache uses "
        "strict elapsed > TTL comparison"
    )
    assert result.frame_hash == "hash_v1"

    # One second past the bound: TTL eviction kicks in.
    clock.advance(seconds=1)
    result = cache.get(composite, mission_id=_MISSION_A)
    assert result is None, (
        f"frame should miss after {TTL_SECONDS + 1} s "
        f"(> {TTL_SECONDS} s TTL)"
    )

    # CACHE_EVICTED with reason=ttl_expired emitted exactly once.
    ttl_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("reason") == _REASON_TTL_EXPIRED
    ]
    assert len(ttl_evictions) == 1
    assert ttl_evictions[0].payload["composite"] == composite
    assert ttl_evictions[0].payload["mission_id"] == _MISSION_A

    # Counter reflects the TTL eviction.
    assert cache.stats(_MISSION_A)["ttl_evictions"] == 1

    # Subsequent get is a plain miss — the entry was already evicted.
    assert cache.get(composite, mission_id=_MISSION_A) is None
    misses = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_MISS
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
    ]
    assert len(misses) == 1


# ---------------------------------------------------------------------------
# 3. Authority change evicts (different composite key)
# ---------------------------------------------------------------------------


def test_authority_change_evicts() -> None:
    """Different authority hashes produce different composite keys.

    A frame stored under ``authority_hash="auth_A"`` is **not**
    served when queried under ``authority_hash="auth_B"`` because
    the ``authority_hash`` is part of the composite key (Requirement
    9.2). The "eviction" is structural — the second composite key
    has no entry — not a literal cache eviction event. Verify that:

    * the two composite keys differ;
    * a get under ``auth_B`` returns ``None`` and emits a plain
      :data:`AgentEventType.CACHE_MISS` (no
      :data:`AgentEventType.CACHE_EVICTED`, because there is no
      entry to evict — it was never stored);
    * the entry under ``auth_A`` is still present and still hits.

    Validates: Requirements 9.2, 9.7 (authority-hash change ⇒ rebuild).
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus)

    composite_a = _composite(cache, authority_hash="auth_A")
    composite_b = _composite(cache, authority_hash="auth_B")

    # Composite keys differ purely on the authority component.
    assert composite_a != composite_b, (
        "different authority hashes must produce different composite keys"
    )

    cache.put(composite_a, _frame(frame_hash="hash_under_auth_A"), mission_id=_MISSION_A)

    # Query under auth B — different composite key, returns None.
    result = cache.get(composite_b, mission_id=_MISSION_A)
    assert result is None

    # The miss is a plain CACHE_MISS (no CACHE_EVICTED): there was no
    # entry under auth_B to evict.
    miss_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_MISS
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
    ]
    assert len(miss_events) == 1
    assert miss_events[0].payload["composite"] == composite_b

    evict_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
    ]
    assert evict_events == [], (
        "authority-change-induced miss must not emit a CACHE_EVICTED — "
        "the entry under the new key was never stored"
    )

    # Original entry under auth_A is still hit-serviceable.
    result_a = cache.get(composite_a, mission_id=_MISSION_A)
    assert result_a is not None
    assert result_a.frame_hash == "hash_under_auth_A"


# ---------------------------------------------------------------------------
# 4. Counters match ground-truth event counts (Hypothesis FSM)
# ---------------------------------------------------------------------------


# Operation kinds for the FSM. Each tuple element is the op tag plus
# its parameters; the strategy below keeps the parameter space small
# so Hypothesis exercises the FSM densely rather than degrade into
# wide-input search.
_OP_PUT = "put"
_OP_GET = "get"
_OP_ADVANCE = "advance"

# Three composites — small enough that put + get hit the same key
# repeatedly, exercising the hit/miss/LRU branches without inflating
# the bucket past the per-mission cap.
_COMPOSITES = ("comp_0", "comp_1", "comp_2")

# Advance amounts in seconds. Hypothesis samples around the 600 s TTL
# boundary so the FSM exercises in-bounds, just-over, and far-over
# cases.
_advance_seconds = st.one_of(
    st.integers(min_value=0, max_value=599),
    st.integers(min_value=600, max_value=1200),
)

_op_strategy = st.one_of(
    st.tuples(st.just(_OP_PUT), st.sampled_from(_COMPOSITES)),
    st.tuples(st.just(_OP_GET), st.sampled_from(_COMPOSITES)),
    st.tuples(st.just(_OP_ADVANCE), _advance_seconds),
)


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(ops=st.lists(_op_strategy, min_size=1, max_size=40))
def test_counters_match_ground_truth_events(
    ops: list[tuple[str, Any]],
) -> None:
    """After every op, ``cache.stats(mission_id)`` equals the ground-truth event counts.

    Replays Hypothesis-generated operations against a fresh cache
    while walking the bus's event stream after each op to compute
    the ground-truth counter dict from the actual events emitted.
    Per Requirement 9.4 — counters MUST equal the event ground
    truth, with no counter incremented on an outcome that does not
    match its event type.

    The operation set covers every counter-bearing path:

    * ``put`` — populates an entry; never increments any counter
      directly (the put-time eviction path increments ``evictions``
      only when the bucket is over cap, which the small composite
      space here does not exercise).
    * ``get`` — increments ``hits`` on a clean hit, ``misses`` on a
      composite-hash miss, ``ttl_evictions`` on a TTL-expired hit.
    * ``advance`` — moves the controlled clock forward to age
      cached entries past their TTL boundary.

    Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6, 9.7.
    """
    clock = _ManualClock(start_ns=0)
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus, clock=clock)

    composite_for: dict[str, str] = {
        tag: _composite(cache, mission_hot_hash=f"hot_{tag}")
        for tag in _COMPOSITES
    }

    for op in ops:
        kind = op[0]
        if kind == _OP_PUT:
            tag = op[1]
            cache.put(
                composite_for[tag],
                _frame(frame_hash=f"hash_{tag}"),
                mission_id=_MISSION_A,
            )
        elif kind == _OP_GET:
            tag = op[1]
            cache.get(composite_for[tag], mission_id=_MISSION_A)
        elif kind == _OP_ADVANCE:
            seconds = op[1]
            clock.advance(seconds=seconds)
        else:
            raise AssertionError(f"unknown op kind {kind!r}")

        # Invariant after every op: cache.stats matches ground-truth.
        actual = cache.stats(_MISSION_A)
        expected = _ground_truth_counters(bus, mission_id=_MISSION_A)
        assert actual == expected, (
            f"after op {op!r}: cache.stats={actual!r} != "
            f"ground-truth event counts={expected!r}"
        )


# ---------------------------------------------------------------------------
# 5. reuse_prefix output equals a full rebuild
# ---------------------------------------------------------------------------


def _evidence_card(
    *,
    receipt_id: str = "receipt_a",
    summary: str = "alpha",
    source_type: str = "test",
) -> EvidenceCard:
    """Build a minimal :class:`EvidenceCard` for the prefix test."""
    return EvidenceCard(
        receipt_id=receipt_id,
        source_type=source_type,
        summary=summary,
        relevance_score=1.0,
        token_count=4,
    )


# Strategy for prefix text: lowercase ASCII + digits + spaces so the
# generated values cannot contain the substrings the renderer emits
# (``"- "``, ``" (receipt="``) and cannot accidentally match the
# canonical secret-redaction patterns.
_prefix_text = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789 "),
    min_size=0,
    max_size=64,
).map(lambda s: f"PREFIX[{s}]")

_card_summary = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=1,
    max_size=24,
).map(lambda s: f"SUM_{s}")

_card_receipt = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    min_size=1,
    max_size=12,
).map(lambda s: f"rcpt_{s}")


@given(
    prefix_text=_prefix_text,
    summary=_card_summary,
    receipt_id=_card_receipt,
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_reuse_prefix_equals_full_rebuild(
    prefix_text: str, summary: str, receipt_id: str
) -> None:
    """``reuse_prefix`` returns ``prefix + delta_render`` byte-for-byte.

    Registers a stable prefix in the prefix table and calls
    :meth:`PromptFrameCache.reuse_prefix` with a single-card delta.
    The output equals the manual concatenation of the prefix text
    with the deterministic evidence-delta rendering — the same
    rendering a full rebuild would produce. Hypothesis sweeps the
    prefix and the card's ``summary`` / ``receipt_id`` so the
    equality holds under arbitrary content.

    The renderer for an evidence card is documented in
    :mod:`sentinel.perf.caches.prompt_frame_cache._render_evidence_delta`
    as ``f"- {card.summary} (receipt={card.receipt_id})\\n"``;
    this test reproduces that line manually as the ground truth.

    On hit, the cache emits :data:`AgentEventType.CACHE_HIT` with
    ``cache_type="prompt_prefix"`` and ``prefix_hash`` payload.

    Validates: Requirement 9.3.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = PromptFrameCache(event_bus=bus)

    prefix_hash = "prefix_hash_v1"
    cache.register_prefix(prefix_hash, prefix_text)

    card = _evidence_card(receipt_id=receipt_id, summary=summary)
    actual = cache.reuse_prefix(prefix_hash, [card], mission_id=_MISSION_A)

    expected = prefix_text + f"- {summary} (receipt={receipt_id})\n"
    assert actual == expected, (
        f"reuse_prefix output {actual!r} differs from manual "
        f"prefix + delta_render {expected!r}"
    )

    # Prefix-cache hit event was emitted with the documented payload.
    hit_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_HIT
        and ev.payload.get("cache_type") == PROMPT_PREFIX_CACHE_TYPE
    ]
    assert len(hit_events) == 1
    assert hit_events[0].payload["prefix_hash"] == prefix_hash
    assert hit_events[0].payload["mission_id"] == _MISSION_A


def test_reuse_prefix_equals_full_rebuild_with_empty_delta() -> None:
    """Empty delta path returns the prefix unchanged.

    Documents the boundary case: when the caller passes an empty
    ``evidence_delta`` list, the rendering is the empty string and
    the output equals the prefix verbatim. Confirms the
    delta-renderer matches the documented "no-op" semantics so the
    Hypothesis property above is not vacuously satisfied on that
    edge.

    Validates: Requirement 9.3.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = PromptFrameCache(event_bus=bus)
    prefix_hash = "prefix_hash_empty"
    prefix_text = "STABLE_PREFIX_BODY"
    cache.register_prefix(prefix_hash, prefix_text)

    actual = cache.reuse_prefix(prefix_hash, [], mission_id=_MISSION_A)
    assert actual == prefix_text


def test_reuse_prefix_multi_card_delta_equals_full_rebuild() -> None:
    """Multi-card delta preserves order and concatenates lines.

    Three cards in order; the output equals
    ``prefix + line_0 + line_1 + line_2`` where each ``line_i``
    is the documented per-card rendering. Confirms the renderer is
    order-preserving and append-only — the property the spec gives
    for "stable prefix + changed evidence sections" reuse.

    Validates: Requirement 9.3.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = PromptFrameCache(event_bus=bus)
    prefix_hash = "prefix_hash_multi"
    prefix_text = "MULTI_PREFIX|"
    cache.register_prefix(prefix_hash, prefix_text)

    cards = [
        _evidence_card(receipt_id="r0", summary="alpha"),
        _evidence_card(receipt_id="r1", summary="beta"),
        _evidence_card(receipt_id="r2", summary="gamma"),
    ]
    actual = cache.reuse_prefix(prefix_hash, cards, mission_id=_MISSION_A)
    expected = (
        prefix_text
        + "- alpha (receipt=r0)\n"
        + "- beta (receipt=r1)\n"
        + "- gamma (receipt=r2)\n"
    )
    assert actual == expected


def test_reuse_prefix_miss_returns_none() -> None:
    """Unknown prefix-hash returns ``None`` and emits CACHE_MISS.

    Confirms the documented miss path — the caller is expected to
    perform a full rebuild when ``reuse_prefix`` returns ``None``.

    Validates: Requirement 9.3 (fall-through-to-rebuild semantics).
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = PromptFrameCache(event_bus=bus)
    actual = cache.reuse_prefix("unknown_hash", [], mission_id=_MISSION_A)
    assert actual is None

    miss_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_MISS
        and ev.payload.get("cache_type") == PROMPT_PREFIX_CACHE_TYPE
    ]
    assert len(miss_events) == 1
    assert miss_events[0].payload["prefix_hash"] == "unknown_hash"


# ---------------------------------------------------------------------------
# 6. Safety bypass evicts and returns None
# ---------------------------------------------------------------------------


def _mutate_cached_safety_flag(
    cache: LLMDecisionFrameCache,
    *,
    mission_id: str,
    composite: str,
    field: str,
) -> None:
    """White-box: flip a safety flag on the cached frame.

    The cache stores a ``copy.deepcopy(frame)`` on ``put``, so
    mutating the original frame after store does **not** affect the
    cached copy — that is the whole point of the deepcopy. To test
    the read-side safety guard (Requirements 12.2 and 12.3), this
    helper reaches into the cache's internal storage and flips the
    flag on the cached object directly. This simulates the worst-case
    path the cache is hardened against: post-store mutation of a
    ``LLMDecisionFrame`` (which inherits the unfrozen
    :class:`SentinelModel`).
    """
    cached_frame, created_at_ns = cache._entries[mission_id][composite]
    setattr(cached_frame, field, True)


def test_safety_bypass_evicts_and_returns_none_authority_expansion() -> None:
    """``authority_expansion=True`` post-store: get evicts, returns None.

    Put a clean frame (``authority_expansion=False``). Mutate the
    cached frame in place to simulate post-store mutation. The next
    ``get`` must:

    * return ``None``;
    * emit :data:`AgentEventType.CACHE_EVICTED` with
      ``reason="authority_expansion_bypass"``;
    * remove the entry from the bucket;
    * increment the ``safety_bypasses`` counter for that mission.

    A subsequent get is a plain miss (entry already evicted).

    Validates: Requirement 12.2.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus)
    composite = _composite(cache)

    cache.put(
        composite,
        _frame(frame_hash="hash_clean", authority_expansion=False),
        mission_id=_MISSION_A,
    )

    # Sanity: clean hit before the mutation.
    pre = cache.get(composite, mission_id=_MISSION_A)
    assert pre is not None
    assert pre.frame_hash == "hash_clean"
    assert pre.authority_expansion is False

    # White-box: flip the safety flag on the cached deepcopy. This
    # replicates the hostile post-store-mutation case the cache's
    # read-side guard is built to detect.
    _mutate_cached_safety_flag(
        cache,
        mission_id=_MISSION_A,
        composite=composite,
        field="authority_expansion",
    )

    # Get returns None and evicts under the safety bypass.
    result = cache.get(composite, mission_id=_MISSION_A)
    assert result is None

    bypass_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("reason") == _REASON_AUTHORITY_EXPANSION
    ]
    assert len(bypass_evictions) == 1
    assert bypass_evictions[0].payload["composite"] == composite
    assert bypass_evictions[0].payload["mission_id"] == _MISSION_A

    # Counter incremented exactly once.
    assert cache.stats(_MISSION_A)["safety_bypasses"] == 1

    # Entry removed from the bucket.
    assert composite not in cache._entries.get(_MISSION_A, {})

    # Subsequent get is a plain miss.
    assert cache.get(composite, mission_id=_MISSION_A) is None


def test_safety_bypass_evicts_and_returns_none_raw_secret_leakage() -> None:
    """``raw_secret_leakage=True`` post-store: get evicts, returns None.

    Mirror of the authority-expansion test for the second safety
    flag. Eviction reason is ``"raw_secret_leakage_bypass"``.

    Validates: Requirement 12.3.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus)
    composite = _composite(cache)

    cache.put(
        composite,
        _frame(frame_hash="hash_clean", raw_secret_leakage=False),
        mission_id=_MISSION_A,
    )

    pre = cache.get(composite, mission_id=_MISSION_A)
    assert pre is not None
    assert pre.raw_secret_leakage is False

    _mutate_cached_safety_flag(
        cache,
        mission_id=_MISSION_A,
        composite=composite,
        field="raw_secret_leakage",
    )

    result = cache.get(composite, mission_id=_MISSION_A)
    assert result is None

    bypass_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("reason") == _REASON_RAW_SECRET_LEAKAGE
    ]
    assert len(bypass_evictions) == 1
    assert bypass_evictions[0].payload["composite"] == composite
    assert bypass_evictions[0].payload["mission_id"] == _MISSION_A

    assert cache.stats(_MISSION_A)["safety_bypasses"] == 1
    assert composite not in cache._entries.get(_MISSION_A, {})
    assert cache.get(composite, mission_id=_MISSION_A) is None


def test_put_rejects_authority_expansion_true() -> None:
    """``put`` rejects ``authority_expansion=True`` writes with ValueError.

    The frame is never stored — no temporary entry, no half-written
    record (Requirement 12.2). The cache's bucket for the mission
    is either absent or empty after the rejected put.

    Validates: Requirement 12.2.
    """
    bus = EventBus(mission_id=_MISSION_A)
    cache = LLMDecisionFrameCache(event_bus=bus)
    composite = _composite(cache)

    bad_frame = _frame(frame_hash="hash_bad", authority_expansion=True)
    try:
        cache.put(composite, bad_frame, mission_id=_MISSION_A)
    except ValueError:
        pass
    else:
        raise AssertionError(
            "put with authority_expansion=True must raise ValueError"
        )

    # No entry stored.
    bucket = cache._entries.get(_MISSION_A, {})
    assert composite not in bucket

    # Subsequent get under the same composite is a plain miss.
    assert cache.get(composite, mission_id=_MISSION_A) is None
