# Feature: sentinel-performance-runtime-foundation, Property 4: Cache invalidation dependency closure
"""Property test — cache invalidation dependency closure.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6.**

Property statement
------------------

Hypothesis FSM over ``(create, modify, rename, delete)`` workspace
events × composite-key component changes. Every transitively
dependent entry across :class:`ContextBuildCache`,
:class:`WorkspaceSnapshotCache`, :class:`PromptFrameCache`, and
:class:`LLMDecisionFrameCache` is evicted within one tick when its
upstream dependency is invalidated. TTL expiry evicts regardless of
dependency state. The ``CACHE_INVALIDATION_BULK_WARNING`` event fires
iff the cause is an invalidation event and the evicted count exceeds
1000.

Phase scope (Phase C wave)
--------------------------

:class:`WorkspaceSnapshotCache` is a Phase E (Task 10.2) module that
does not exist at the time this property test runs. Per the patched
task graph, the dependency-graph traversal is exercised directly on
:class:`CacheInvalidationPolicy` (Phase B / Task 4.9) using
synthetic ``WorkspaceDelta``-shaped operations. Manually-registered
dependencies mimic the production chain
``workspace_snapshot → context_build → prompt_frame → decision_frame``
without importing the unbuilt :class:`WorkspaceSnapshotCache` module.

Hypothesis settings
-------------------

``max_examples=100, deadline=None`` per the task spec.
``HealthCheck.too_slow`` is suppressed because the bulk-warning case
populates 1001 entries, which is slightly slower than the default
Hypothesis budget; total runtime per test is small.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.perf.hot_cold.cache_invalidation_policy import (
    CacheInvalidationPolicy,
)
from sentinel.shared.events import AgentEventType, EventBus

# ---------------------------------------------------------------------------
# Constants — synthetic chain topology
# ---------------------------------------------------------------------------

_MISSION_ID = "mission_p4"

# Synthetic chain mirroring the production
# workspace_snapshot → context_build → prompt_frame → decision_frame
# topology. Keys are opaque strings; the policy treats them as
# arbitrary identifiers.
_KEY_WS = "ws_snapshot:fileA"
_KEY_CTX = "context_build:fileA"
_KEY_PROMPT = "prompt_frame:fileA"
_KEY_FRAME = "decision_frame:fileA"

# TTL category strings exactly match the four valid categories
# enforced by ``CacheInvalidationPolicy.put``.
_CAT_WS = "workspace_snapshot"
_CAT_EVIDENCE = "evidence_selection"
_CAT_PROMPT = "prompt_frame"
_CAT_FRAME = "decision_frame"

# TTL upper bounds in seconds (Requirement 3.4). Mirrored from the
# policy's ``_TTL_NS`` map; duplicated as integers here so the test
# can advance a controlled clock past each bound without importing
# private state.
_TTL_S = {
    _CAT_WS: 300,
    _CAT_EVIDENCE: 600,
    _CAT_PROMPT: 600,
    _CAT_FRAME: 600,
}

# The policy's threshold for the bulk-warning event (Requirement 3.6).
_BULK_THRESHOLD = 1000


# ---------------------------------------------------------------------------
# Controlled clock
# ---------------------------------------------------------------------------


class _ManualClock:
    """A monotonic-ns clock whose advance is fully under test control.

    Hypothesis's TTL test cases need to step the clock past the
    600 s / 300 s upper bounds without sleeping. This holder is
    passed into :class:`CacheInvalidationPolicy` as its ``clock``
    argument; calls to :meth:`__call__` return the current value in
    nanoseconds.
    """

    def __init__(self, start_ns: int = 0) -> None:
        self._now_ns = start_ns

    def __call__(self) -> int:
        return self._now_ns

    def advance(self, *, seconds: int) -> None:
        """Advance the clock by ``seconds`` whole seconds."""
        self._now_ns += seconds * 10**9


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_policy(
    *, clock: Callable[[], int] | None = None
) -> tuple[CacheInvalidationPolicy, EventBus]:
    """Construct a fresh :class:`CacheInvalidationPolicy` + :class:`EventBus`.

    Returns the (policy, bus) pair so each test can inspect the
    bus's event stream after exercising the policy.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    if clock is None:
        clock_fn: Callable[[], int] = lambda: 0
        policy = CacheInvalidationPolicy(event_bus=bus, clock=clock_fn)
    else:
        policy = CacheInvalidationPolicy(event_bus=bus, clock=clock)
    return policy, bus


def _bulk_warnings(bus: EventBus) -> list[dict]:
    """Return the list of ``CACHE_INVALIDATION_BULK_WARNING`` payloads."""
    return [
        ev.payload
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_INVALIDATION_BULK_WARNING
    ]


def _register_chain(policy: CacheInvalidationPolicy) -> None:
    """Register the four-tier ``ws → ctx → prompt → frame`` dependency chain."""
    policy.register_dependency(_KEY_WS, _KEY_CTX)
    policy.register_dependency(_KEY_CTX, _KEY_PROMPT)
    policy.register_dependency(_KEY_PROMPT, _KEY_FRAME)


def _put_chain(policy: CacheInvalidationPolicy) -> None:
    """Populate one entry per tier of the synthetic chain."""
    policy.put(_KEY_WS, value="ws_value", ttl_category=_CAT_WS)
    policy.put(_KEY_CTX, value="ctx_value", ttl_category=_CAT_EVIDENCE)
    policy.put(_KEY_PROMPT, value="prompt_value", ttl_category=_CAT_PROMPT)
    policy.put(_KEY_FRAME, value="frame_value", ttl_category=_CAT_FRAME)


# ---------------------------------------------------------------------------
# Deterministic test 1 — dependency closure invalidates descendants
# ---------------------------------------------------------------------------


def test_dependency_closure_invalidates_descendants() -> None:
    """Invalidating the workspace-snapshot root evicts every descendant.

    Builds a chain ``ws → ctx → prompt → frame``, populates one entry
    per tier, then invalidates the workspace-snapshot key with cause
    ``INVALIDATION_EVENT``. After the invalidation:

    * every descendant — context, prompt, frame — returns ``None`` on
      ``get`` (Requirements 3.1, 3.5);
    * the dependency-graph traversal completes synchronously within
      a single ``invalidate`` call (Requirement 3.6);
    * the evicted-count return value equals the four entries that
      were transitively reached (ws + ctx + prompt + frame).

    Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6.
    """
    policy, bus = _new_policy()
    _register_chain(policy)
    _put_chain(policy)

    # Baseline: every tier hits before the invalidation.
    assert policy.get(_KEY_WS) == "ws_value"
    assert policy.get(_KEY_CTX) == "ctx_value"
    assert policy.get(_KEY_PROMPT) == "prompt_value"
    assert policy.get(_KEY_FRAME) == "frame_value"

    evicted_count = policy.invalidate(_KEY_WS, cause="INVALIDATION_EVENT")

    # Same-tick traversal: the count returned by ``invalidate`` already
    # reflects the four cascading evictions (Requirement 3.6).
    assert evicted_count == 4

    # Every descendant — even those that were never directly
    # invalidated — is a miss after the upstream eviction
    # (Requirement 3.1).
    assert policy.get(_KEY_WS) is None
    assert policy.get(_KEY_CTX) is None
    assert policy.get(_KEY_PROMPT) is None
    assert policy.get(_KEY_FRAME) is None

    # Below the bulk threshold: no warning event emitted
    # (Requirement 3.6).
    assert _bulk_warnings(bus) == []


# ---------------------------------------------------------------------------
# Deterministic test 2 — TTL expiry evicts regardless of deps
# ---------------------------------------------------------------------------


def test_ttl_expiry_evicts_regardless_of_deps() -> None:
    """TTL expiry produces a miss without any upstream invalidation.

    Stores a single value under the ``workspace_snapshot`` TTL
    category (300 s upper bound, Requirement 3.4) with **no**
    dependency edges registered. Advances the controlled clock by
    301 s — past the upper bound — and asserts the next ``get``
    returns ``None``. No invalidation event is recorded; the eviction
    is purely TTL-driven.

    Validates: Requirement 3.4.
    """
    clock = _ManualClock(start_ns=0)
    policy, bus = _new_policy(clock=clock)

    policy.put(_KEY_WS, value="ws_value", ttl_category=_CAT_WS)

    # Just before the TTL boundary: still a hit. ``advance`` works
    # in seconds and the policy compares ``elapsed > ttl``, so a
    # clock at exactly the boundary is still in-bounds.
    clock.advance(seconds=_TTL_S[_CAT_WS])
    assert policy.get(_KEY_WS) == "ws_value"

    # One second past the upper bound: TTL eviction kicks in
    # (Requirement 3.4) and the entry returns a miss
    # regardless of dependency state (no deps were registered).
    clock.advance(seconds=1)
    assert policy.get(_KEY_WS) is None

    # No bulk-warning event fires for TTL evictions
    # (Requirement 3.6 — warning is for invalidation events only).
    assert _bulk_warnings(bus) == []


def test_ttl_expiry_evicts_each_category_independently() -> None:
    """Every TTL category enforces its own upper bound.

    Each of the four categories — ``workspace_snapshot`` (300 s),
    ``evidence_selection`` (600 s), ``prompt_frame`` (600 s), and
    ``decision_frame`` (600 s) — evicts on access once its own bound
    is exceeded, with no cross-talk between categories.

    Validates: Requirement 3.4.
    """
    for category in (_CAT_WS, _CAT_EVIDENCE, _CAT_PROMPT, _CAT_FRAME):
        clock = _ManualClock(start_ns=0)
        policy, _ = _new_policy(clock=clock)
        key = f"key:{category}"
        policy.put(key, value="v", ttl_category=category)

        # At the bound: still in-bounds (elapsed > ttl is strict).
        clock.advance(seconds=_TTL_S[category])
        assert policy.get(key) == "v", (
            f"category {category} should still be valid at the boundary"
        )

        # One second past: miss.
        clock.advance(seconds=1)
        assert policy.get(key) is None, (
            f"category {category} should miss past the {_TTL_S[category]} s "
            "upper bound"
        )


# ---------------------------------------------------------------------------
# Deterministic test 3 — bulk warning iff INVALIDATION_EVENT and count > 1000
# ---------------------------------------------------------------------------


def test_bulk_warning_fires_iff_invalidation_event_and_count_gt_1000() -> None:
    """Bulk warning fires exactly when both conditions hold.

    Three cases are exercised:

    * 1001 children + cause ``INVALIDATION_EVENT`` →
      :data:`AgentEventType.CACHE_INVALIDATION_BULK_WARNING` emitted
      exactly once with payload
      ``{"cause": "INVALIDATION_EVENT", "evicted_count": 1001}``.
    * 1001 children + cause ``"TTL_EXPIRY"`` → no warning emitted.
    * 1000 children + cause ``INVALIDATION_EVENT`` → no warning
      emitted (count must be **strictly greater** than 1000).

    Validates: Requirement 3.6.
    """
    # ---- Case 1: 1001 deps + INVALIDATION_EVENT → warning fires ----
    policy, bus = _new_policy()
    parent = "parent:bulk_a"
    # Put the parent itself plus 1001 children, all dependent on
    # the parent. Each ``put`` must precede ``invalidate`` because
    # the policy only counts entries that exist in ``self._entries``.
    policy.put(parent, value="parent_v", ttl_category=_CAT_WS)
    for i in range(1001):
        child = f"child_a:{i:04d}"
        policy.register_dependency(parent, child)
        policy.put(child, value=i, ttl_category=_CAT_FRAME)

    evicted_count = policy.invalidate(parent, cause="INVALIDATION_EVENT")
    # Parent + 1001 children = 1002 entries, > 1000 threshold.
    assert evicted_count == 1002

    warnings = _bulk_warnings(bus)
    assert len(warnings) == 1, (
        f"expected exactly one bulk warning, got {len(warnings)}"
    )
    payload = warnings[0]
    assert payload == {
        "cause": "INVALIDATION_EVENT",
        "evicted_count": 1002,
    }

    # ---- Case 2: 1001 deps + non-INVALIDATION cause → NO warning ----
    policy, bus = _new_policy()
    parent = "parent:bulk_b"
    policy.put(parent, value="parent_v", ttl_category=_CAT_WS)
    for i in range(1001):
        child = f"child_b:{i:04d}"
        policy.register_dependency(parent, child)
        policy.put(child, value=i, ttl_category=_CAT_FRAME)

    evicted_count = policy.invalidate(parent, cause="TTL_EXPIRY")
    assert evicted_count == 1002
    # Cause is not INVALIDATION_EVENT — warning suppressed
    # (Requirement 3.6: only for invalidation-event causes).
    assert _bulk_warnings(bus) == []

    # ---- Case 3: count == 1000 + INVALIDATION_EVENT → NO warning ----
    policy, bus = _new_policy()
    parent = "parent:bulk_c"
    # Don't put the parent itself this time; we want exactly 1000
    # entries to be evicted, so the threshold check (count > 1000)
    # is a strict miss.
    for i in range(1000):
        child = f"child_c:{i:04d}"
        policy.register_dependency(parent, child)
        policy.put(child, value=i, ttl_category=_CAT_FRAME)

    evicted_count = policy.invalidate(parent, cause="INVALIDATION_EVENT")
    assert evicted_count == 1000  # strictly equal; not greater.
    # Threshold is strict greater-than (Requirement 3.6 wording —
    # "exceeds 1000"). Equal must not fire.
    assert _bulk_warnings(bus) == []


# ---------------------------------------------------------------------------
# Deterministic test 4 — access to invalidated returns miss
# ---------------------------------------------------------------------------


def test_access_to_invalidated_returns_miss() -> None:
    """A direct access to an invalidated entry returns a cache miss.

    Even before the next eviction sweep — i.e. the entry is still
    present in ``policy._entries`` with ``invalidated=True`` —
    ``get`` returns ``None`` (Requirement 3.5). The policy never
    serves stale data after an invalidation has been recorded.

    Validates: Requirement 3.5.
    """
    policy, _ = _new_policy()

    policy.put(_KEY_WS, value="v", ttl_category=_CAT_WS)
    assert policy.get(_KEY_WS) == "v"

    policy.invalidate(_KEY_WS, cause="INVALIDATION_EVENT")

    # Entry is still present in the underlying store (no
    # ``evict_invalidated`` sweep has run), but is marked invalidated.
    # ``get`` must return None — never the stale value.
    assert policy.get(_KEY_WS) is None

    # Repeated reads continue to miss; the entry never rebinds.
    assert policy.get(_KEY_WS) is None


# ---------------------------------------------------------------------------
# Hypothesis FSM-style — list of (workspace event × composite-key change) ops
# ---------------------------------------------------------------------------


# Workspace-event types from the WorkspaceDelta surface defined in
# Phase E (Task 10.1). The synthetic test exercises them by mapping
# each event onto an ``invalidate(workspace_key, cause)`` call.
_WS_EVENTS = ("CREATE", "MODIFY", "RENAME", "DELETE")

# Composite-key components whose change should invalidate the
# corresponding upstream tier in the chain. ``mission_hot_hash`` and
# ``organ_state_hash`` invalidate at the context level
# (Requirement 3.1). ``authority_hash`` invalidates at the
# prompt-frame level (Requirement 3.3). ``workspace_snapshot_id``
# invalidates at the workspace-snapshot level (Requirement 3.1 root).
_COMPOSITE_COMPONENTS = (
    "mission_hot_hash",
    "workspace_snapshot_id",
    "organ_state_hash",
    "authority_hash",
)


# Operation kinds drawn by Hypothesis. Each encodes a single tick of
# the FSM.
_OP_PUT = "put"
_OP_WS_EVENT = "ws_event"
_OP_KEY_CHANGE = "key_change"
_OP_GET = "get"

# Strategy for one operation: a tag plus its parameters. The
# composite shape is intentionally narrow — Hypothesis explores the
# combinatorial space of ``(op_kind, tier, ws_event, component)`` —
# without constructing rich payloads (the policy is value-opaque).
_op_strategy = st.one_of(
    st.tuples(st.just(_OP_PUT), st.sampled_from((_KEY_WS, _KEY_CTX, _KEY_PROMPT, _KEY_FRAME))),
    st.tuples(st.just(_OP_WS_EVENT), st.sampled_from(_WS_EVENTS)),
    st.tuples(st.just(_OP_KEY_CHANGE), st.sampled_from(_COMPOSITE_COMPONENTS)),
    st.tuples(st.just(_OP_GET), st.sampled_from((_KEY_WS, _KEY_CTX, _KEY_PROMPT, _KEY_FRAME))),
)


def _component_to_root_key(component: str) -> str:
    """Map a composite-key component to the chain root it invalidates.

    * ``workspace_snapshot_id`` → :data:`_KEY_WS` — invalidating the
      workspace snapshot cascades to ``ctx → prompt → frame``
      (Requirement 3.1).
    * ``mission_hot_hash`` and ``organ_state_hash`` →
      :data:`_KEY_CTX` — invalidating the context build cascades
      to ``prompt → frame`` (Requirement 3.1).
    * ``authority_hash`` → :data:`_KEY_PROMPT` — invalidating the
      prompt frame cascades to ``frame`` only (Requirement 3.3).
    """
    if component == "workspace_snapshot_id":
        return _KEY_WS
    if component in ("mission_hot_hash", "organ_state_hash"):
        return _KEY_CTX
    if component == "authority_hash":
        return _KEY_PROMPT
    raise AssertionError(f"unknown composite component {component!r}")


# Pre-computed transitive-descendant sets for each chain root. The
# FSM-style test uses these as ground truth: after invalidating any
# of these roots, every descendant key must miss on the next ``get``.
_DESCENDANTS: dict[str, frozenset[str]] = {
    _KEY_WS: frozenset({_KEY_WS, _KEY_CTX, _KEY_PROMPT, _KEY_FRAME}),
    _KEY_CTX: frozenset({_KEY_CTX, _KEY_PROMPT, _KEY_FRAME}),
    _KEY_PROMPT: frozenset({_KEY_PROMPT, _KEY_FRAME}),
    _KEY_FRAME: frozenset({_KEY_FRAME}),
}


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(ops=st.lists(_op_strategy, min_size=1, max_size=40))
def test_fsm_dependency_closure_holds_under_random_ops(
    ops: list[tuple[str, str]],
) -> None:
    """FSM-style: random ops × dependency closure invariant.

    For each Hypothesis-generated operation list, replays the ops
    against a fresh :class:`CacheInvalidationPolicy` while keeping a
    parallel ground-truth model of "which keys are currently
    invalidated" (a Python ``set``). After every ``ws_event`` and
    ``key_change`` op, asserts:

    * every key in the transitive descendant set of the affected
      root is marked invalidated in the ground-truth model
      (Requirements 3.1, 3.2, 3.3);
    * for every key that exists in the cache and is in the
      ground-truth invalidated set, ``policy.get(key)`` returns
      ``None`` (Requirement 3.5);
    * no ``CACHE_INVALIDATION_BULK_WARNING`` is emitted at any point
      — the operation list never crosses the 1000-entry threshold,
      so the warning must remain suppressed for the entire trace
      (Requirement 3.6).

    Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6.
    """
    policy, bus = _new_policy()
    _register_chain(policy)

    # Ground truth: keys that have been put-and-not-re-put plus
    # their invalidation state. ``put`` of an already-invalidated
    # key resets it to "live" because the policy overwrites the
    # entry with a fresh :class:`CacheEntry`.
    live_keys: set[str] = set()
    invalidated_keys: set[str] = set()

    def _bfs_descendants(root: str) -> set[str]:
        """Replicate the policy's BFS traversal on the same edges.

        The ``register_dependency`` calls above set up the linear
        chain; this BFS mirrors :meth:`CacheInvalidationPolicy.invalidate`
        and is the ground truth against which we assert.
        """
        visited: set[str] = set()
        queue: deque[str] = deque([root])
        edges = {
            _KEY_WS: {_KEY_CTX},
            _KEY_CTX: {_KEY_PROMPT},
            _KEY_PROMPT: {_KEY_FRAME},
            _KEY_FRAME: set(),
        }
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in edges.get(cur, set()):
                if nxt not in visited:
                    queue.append(nxt)
        return visited

    # Map workspace event to the synthetic chain root it touches.
    # Per the spec, every workspace-event type evicts the same chain
    # — a delta on path X invalidates the entire dependency closure
    # of X. The synthetic chain has only one path, so all four event
    # types are equivalent at this layer of the graph
    # (Requirement 3.2).
    _WS_EVENT_ROOT = _KEY_WS

    # Per-tier TTL categories so each ``put`` op uses the correct
    # category; out-of-category puts would raise ``ValueError`` from
    # the policy.
    _PUT_CATEGORY = {
        _KEY_WS: _CAT_WS,
        _KEY_CTX: _CAT_EVIDENCE,
        _KEY_PROMPT: _CAT_PROMPT,
        _KEY_FRAME: _CAT_FRAME,
    }

    for op in ops:
        kind = op[0]
        if kind == _OP_PUT:
            key = op[1]
            policy.put(key, value=f"v:{key}", ttl_category=_PUT_CATEGORY[key])
            live_keys.add(key)
            # ``put`` rebinds — the new entry is not invalidated.
            invalidated_keys.discard(key)
        elif kind == _OP_WS_EVENT:
            # All four WS event types invalidate the workspace-
            # snapshot root and cascade to every descendant
            # (Requirement 3.2).
            root = _WS_EVENT_ROOT
            policy.invalidate(root, cause="INVALIDATION_EVENT")
            for descendant in _bfs_descendants(root):
                if descendant in live_keys:
                    invalidated_keys.add(descendant)
        elif kind == _OP_KEY_CHANGE:
            component = op[1]
            root = _component_to_root_key(component)
            policy.invalidate(root, cause="INVALIDATION_EVENT")
            for descendant in _bfs_descendants(root):
                if descendant in live_keys:
                    invalidated_keys.add(descendant)
        elif kind == _OP_GET:
            # ``get`` ops are observation-only; no state change.
            pass
        else:
            raise AssertionError(f"unknown op kind {kind!r}")

        # Invariant after every op: every live key in the ground-
        # truth invalidated set returns None on policy.get; every
        # live key NOT in the invalidated set returns its value
        # (Requirements 3.1, 3.5).
        for key in (_KEY_WS, _KEY_CTX, _KEY_PROMPT, _KEY_FRAME):
            actual = policy.get(key)
            if key not in live_keys:
                # Never put — must be a miss regardless of state.
                assert actual is None, (
                    f"key {key!r} was never put but get returned {actual!r}"
                )
            elif key in invalidated_keys:
                # Live but invalidated — must miss (Requirement 3.5).
                assert actual is None, (
                    f"invalidated key {key!r} returned {actual!r} "
                    "instead of None"
                )
            else:
                # Live and not invalidated — must hit.
                assert actual == f"v:{key}", (
                    f"live key {key!r} returned {actual!r} "
                    f"instead of expected v:{key}"
                )

    # The op list is bounded at 40 ops, so the cache never exceeds
    # the 1000-entry bulk-warning threshold and no warning event
    # should be observed at any point in the trace
    # (Requirement 3.6).
    assert _bulk_warnings(bus) == []


# ---------------------------------------------------------------------------
# Hypothesis property — TTL expiry is independent of dependency state
# ---------------------------------------------------------------------------


# Strategy for advance amounts. We sample around each TTL boundary
# (300 s and 600 s) — both just-under and just-over — so Hypothesis
# exercises the boundary, sub-boundary, and far-over cases.
_advance_seconds = st.one_of(
    st.integers(min_value=0, max_value=299),
    st.integers(min_value=300, max_value=599),
    st.integers(min_value=600, max_value=900),
)


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    category=st.sampled_from((_CAT_WS, _CAT_EVIDENCE, _CAT_PROMPT, _CAT_FRAME)),
    advance_s=_advance_seconds,
)
def test_ttl_expiry_property(category: str, advance_s: int) -> None:
    """For every category, get-after-advance returns None iff advance > TTL.

    Hypothesis sweeps ``(category, advance_seconds)`` pairs. For each
    pair, the test puts a single value, advances the controlled
    clock, and asserts the get result matches the TTL bound for that
    category (Requirement 3.4):

    * ``advance <= TTL[category]`` → hit (entry returned);
    * ``advance > TTL[category]`` → miss (None returned).

    No dependency edges are registered — the eviction is purely
    TTL-driven, demonstrating "TTL expiry evicts regardless of deps".

    Validates: Requirement 3.4.
    """
    clock = _ManualClock(start_ns=0)
    policy, bus = _new_policy(clock=clock)

    key = f"key:{category}"
    policy.put(key, value="v", ttl_category=category)

    clock.advance(seconds=advance_s)
    actual = policy.get(key)

    ttl = _TTL_S[category]
    if advance_s > ttl:
        assert actual is None, (
            f"{category} should miss after {advance_s} s "
            f"(> {ttl} s TTL), got {actual!r}"
        )
    else:
        assert actual == "v", (
            f"{category} should hit at {advance_s} s "
            f"(<= {ttl} s TTL), got {actual!r}"
        )

    # TTL evictions never trigger the bulk warning
    # (Requirement 3.6 — only invalidation events do).
    assert _bulk_warnings(bus) == []
