# Feature: sentinel-performance-runtime-foundation, Property 13: Safety invariants are preserved across receipts, caches, and deltas
"""Property test — safety invariants across receipts, caches, and deltas.

**Validates: Requirements 12.1, 12.2, 12.3, 12.7.**

Property statement
------------------

Across the three components that touch the cognitive hot path —
:class:`PerformanceReceipt`, :class:`LLMDecisionFrameCache`, and
:class:`DeltaStateEngine` — every documented safety guard fires
deterministically:

* **Receipts** (Requirement 12.1): construction rejects raw secrets
  in any string field. The exception is a ``ValueError`` whose
  message is exactly ``"PerformanceReceipt contains raw secret in
  <field>"`` per the validator in
  :mod:`sentinel.perf.measure.performance_receipt`.

* **LLMDecisionFrameCache writes** (Requirement 12.2): :meth:`put`
  rejects ``authority_expansion=True`` writes with a ``ValueError``.
  No entry is stored — the bucket is unaffected and the eviction
  counter is not incremented (the rejection happens *before* any
  storage path runs).

* **LLMDecisionFrameCache reads** (Requirement 12.3): a clean entry
  whose ``raw_secret_leakage`` flag is mutated post-store to
  ``True`` MUST evict on the next :meth:`get`, return ``None``, and
  emit ``CACHE_EVICTED reason="raw_secret_leakage_bypass"``.

* **DeltaStateEngine** (Requirement 12.7): a ``push_action_summary``
  delta whose application would cross the
  :class:`MissionAuthorityEnvelope`'s ``max_actions`` bound MUST be
  rejected with a ``ValueError`` and an emitted
  ``AUTHORITY_VIOLATION`` event. Prior state is preserved exactly
  — both the action counter and the action-summary list at the
  rejected moment match the pre-call snapshot.

* **Combined** (Requirements 12.1, 12.2, 12.3, 12.7): No path that
  should reject ever silently succeeds. For each component the
  rejection branch is asserted in the same Hypothesis sweep that
  exercises the success branch, so a regression that drops one of
  the guards cannot pass either limb of the property.

Hypothesis settings
-------------------

``max_examples=200, deadline=None`` per the task spec (safety
properties take the higher coverage budget).
``HealthCheck.too_slow`` is suppressed because each example
constructs a fresh :class:`EventBus` and a fresh cache /
:class:`HotMissionCache` instance, which is slightly slower than
the default Hypothesis budget; total runtime per test is small.

Why the secret strategy is the same fixed list used elsewhere
-------------------------------------------------------------

The :data:`SECRET_PATTERNS` regexes in
:mod:`sentinel.agent.evidence_ranker` use ``\\b`` and explicit
class-negation lookarounds; building a Hypothesis strategy that
reliably hits every pattern requires careful boundary
construction. The same ``_secret_patterns_st`` /
``_separator_st`` pair from
:mod:`tests.perf.hot_cold.test_artifact_ref_store_property` is
mirrored here so this property test exercises the same secret
shapes the artifact-store property test does, and so the
boundary-aware separator strategy keeps every generated string
valid for the regex set.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.caches.llm_decision_frame_cache import (
    CACHE_TYPE as FRAME_CACHE_TYPE,
)
from sentinel.perf.caches.llm_decision_frame_cache import LLMDecisionFrameCache
from sentinel.perf.hot_cold.delta_state_engine import DeltaStateEngine, StateDelta
from sentinel.perf.hot_cold.hot_mission_cache import ActionSummary, HotMissionCache
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.shared.enums import MissionMode, MissionType
from sentinel.shared.events import AgentEventType, EventBus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MISSION_ID = "mission_p13_safety"

# Eviction-reason tags. Mirrored from the cache module's private
# constants so this test only depends on the documented payload
# contract — not on importing the private symbols.
_REASON_AUTHORITY_EXPANSION = "authority_expansion_bypass"
_REASON_RAW_SECRET_LEAKAGE = "raw_secret_leakage_bypass"


# ---------------------------------------------------------------------------
# Hypothesis strategies — secrets
# ---------------------------------------------------------------------------

# Sampled secret-bearing strings. Same fixed list used by
# :mod:`tests.perf.hot_cold.test_artifact_ref_store_property` so this
# property exercises the same secret shapes the artifact-store
# rejection property exercises. Each entry is a documented
# :data:`SECRET_PATTERNS` shape from
# :mod:`sentinel.agent.evidence_ranker`:
#   * ``password=...``        → name=value pattern
#   * ``secret=...``          → name=value pattern
#   * ``api_key=sk-...``      → name=value + sk- pattern
#   * ``AKIA...``             → AWS access-key id
#   * ``ghp_...``             → GitHub PAT
#   * ``token=eyJ...``        → JWT
#   * ``authorization: ...``  → Authorization header
#   * ``client_secret=...``   → name=value pattern
#   * ``private_key=...``     → name=value pattern
#   * ``passwd=...``          → name=value pattern
_secret_patterns_st = st.sampled_from(
    [
        "password=abc123",
        "secret=mysecretvalue",
        "api_key=sk-abcdefghij1234567890",
        "AKIAIOSFODNN7EXAMPL0",
        "ghp_ABCDEFGHIJKLMNOPQRSTU",
        "token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
        "authorization: Bearer sk-abcdefghij1234567890",
        "client_secret=verysecretvalue123",
        "private_key=supersecretprivatekey",
        "passwd=hunter2",
    ]
)

# Boundary-preserving separators. Many SECRET_PATTERNS use ``\\b``
# (word boundaries); the surrounding chars must be non-word so the
# pattern actually fires. The empty separator covers the edge case
# where the secret sits at the start or end of the field.
_separator_st = st.sampled_from(["", " ", "\n", "; ", ", ", ": ", "  ", "\t"])

# Receipt fields that accept arbitrary strings and run through the
# sanitizer. Each name maps to where the secret will live: the
# receipt's own field, or a string field on the embedded trace.
# ``cache_type`` is excluded — its sanitizer check fires *before*
# the cache_type whitelist check, so injecting "context" + secret
# would fail the whitelist instead of producing a secret-rejection
# error and would not validate Requirement 12.1's contract.
_RECEIPT_STRING_FIELDS = ("action", "model_id", "backpressure_reason")

# Trace string fields that flow through the receipt's sanitizer
# (Requirement 12.1: ``_flat_string_fields`` walks nested models
# and rejects on any embedded match). ``error_category`` is the only
# trace-level free-form string field we can safely populate without
# breaking the trace's own ``error/error_category`` consistency
# validator (we set ``error=True`` so a non-empty category is valid).
_TRACE_STRING_FIELDS = ("error_category",)

_TARGET_FIELDS_ST = st.sampled_from(
    [("receipt", f) for f in _RECEIPT_STRING_FIELDS]
    + [("trace", f) for f in _TRACE_STRING_FIELDS]
)


# ---------------------------------------------------------------------------
# Builders — clean PerformanceReceipt and PerformanceTrace
# ---------------------------------------------------------------------------


def _clean_trace(
    *,
    error: bool = False,
    error_category: str | None = None,
) -> PerformanceTrace:
    """Build a clean ``PerformanceTrace`` with no secrets and consistent error fields."""
    return PerformanceTrace(
        action_id="act_safety",
        mission_id=_MISSION_ID,
        organ_id=None,
        action_type="safety_test",
        queue_wait_ms=0,
        wall_ms=1,
        cpu_ms=1,
        bytes_in=0,
        bytes_out=0,
        tokens_in=0,
        tokens_out=0,
        cache_hit=0,
        cache_miss=0,
        organ_latency_ms=0,
        model_prefill_decode_ms=0,
        error=error,
        error_category=error_category,
        severity=(
            PerformanceSeverity.CRITICAL if error else PerformanceSeverity.INFO
        ),
    )


def _clean_receipt_kwargs() -> dict[str, Any]:
    """Build the clean kwargs for a valid :class:`PerformanceReceipt`.

    Returns a fresh dict on every call so a test can override exactly one
    field with a secret-bearing value and confirm the construction is
    rejected for that one mutation.
    """
    return {
        "mission_id": _MISSION_ID,
        "action_id": "act_safety",
        "organ_id": None,
        "action": "safe_action",
        "trace": _clean_trace(),
        "estimated_cost_usd": Decimal("0.000000"),
        "model_id": "model-safe",
        "budget_remaining": 100,
        "budget_limit": 100,
        "cache_type": None,
        "backpressure_reason": None,
        "queue_depth_at_receipt": None,
        "deadline_ms": None,
        "elapsed_ms": None,
        "authority_expansion": False,
        "raw_secret_leakage": False,
        "created_at": datetime.now(UTC),
    }


# ---------------------------------------------------------------------------
# Builders — frame-shaped object for LLMDecisionFrameCache
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
    heavyweight :meth:`LLMDecisionFrame.build` pipeline. Mirrors the
    builder used in :mod:`test_decision_frame_cache_lifecycle_property`.
    """
    return SimpleNamespace(
        frame_hash=frame_hash,
        authority_expansion=authority_expansion,
        raw_secret_leakage=raw_secret_leakage,
    )


def _composite(cache: LLMDecisionFrameCache, *, tag: str = "v1") -> str:
    """Build a deterministic composite hash for ``cache``."""
    return cache.composite_hash(
        mission_hot_hash=f"hot_{tag}",
        authority_hash=f"auth_{tag}",
        evidence_set_hash=f"ev_{tag}",
        tool_surface_hash=f"tool_{tag}",
    )


# ---------------------------------------------------------------------------
# Builders — MissionAuthorityEnvelope + HotMissionCache state
# ---------------------------------------------------------------------------


def _envelope(*, max_actions: int) -> MissionAuthorityEnvelope:
    """Build a minimal :class:`MissionAuthorityEnvelope` with the given action cap.

    Other fields use defaults; this property only stresses the
    ``max_actions`` axis (Requirement 12.7's authority-envelope bounds
    check on ``push_action_summary`` deltas).
    """
    return MissionAuthorityEnvelope(
        user_id="user_safety_test",
        mission_type=MissionType.GTM,
        mission_title="Safety invariants property",
        mission_objective="Validate Property 13 invariants.",
        success_criteria=["test"],
        mode=MissionMode.SAFE,
        allowed_systems=["local_workspace"],
        allowed_tools=["safe_tool"],
        allowed_actions=["safe_action"],
        max_duration_minutes=10,
        max_actions=max_actions,
    )


def _summary_delta(receipt_id: str = "rcpt_safety") -> StateDelta:
    """Build a ``push_action_summary`` delta carrying a fresh action summary."""
    return StateDelta(
        delta_type="push_action_summary",
        payload={
            "summary": {
                "receipt_id": receipt_id,
                "action_type": "safe_action",
                "organ_id": None,
                "summary": "noop",
                "ts_ns": 0,
            }
        },
    )


def _seed_action_count(
    hot: HotMissionCache,
    mission_id: str,
    *,
    count: int,
) -> None:
    """Push ``count`` action summaries into the hot cache.

    Used to set up the "current_action_count >= envelope.max_actions"
    pre-condition for the rejection branch of
    :meth:`DeltaStateEngine.apply`.
    """
    for i in range(count):
        hot.push_action_summary(
            mission_id,
            ActionSummary(
                receipt_id=f"rcpt_seed_{i}",
                action_type="safe_action",
                organ_id=None,
                summary=f"seed_{i}",
                ts_ns=i,
            ),
        )


# ---------------------------------------------------------------------------
# 1. PerformanceReceipt rejects raw secrets
# ---------------------------------------------------------------------------


@given(
    secret=_secret_patterns_st,
    prefix=_separator_st,
    suffix=_separator_st,
    target=_TARGET_FIELDS_ST,
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_performance_receipt_rejects_raw_secrets(
    secret: str,
    prefix: str,
    suffix: str,
    target: tuple[str, str],
) -> None:
    """``PerformanceReceipt(...)`` raises ``ValueError`` on raw-secret fields.

    For every (location, field) pair in ``_TARGET_FIELDS_ST`` a clean
    receipt construction is attempted with one field replaced by a
    secret-bearing string. The construction MUST raise ``ValueError``
    whose message starts with ``"PerformanceReceipt contains raw secret
    in "`` and names the offending field. The :func:`_flat_string_fields`
    walker emits dotted names for nested-model fields (e.g.
    ``trace.error_category``); for trace-level injections we therefore
    assert the dotted form, and for receipt-level injections the bare
    field name.

    No partial receipt is exposed — the failed construction yields the
    exception only, never a half-built model. We assert this by
    capturing the raised exception type and message and confirming no
    receipt object is leaked back to the caller.

    Validates: Requirement 12.1.
    """
    location, field = target
    payload = f"{prefix}{secret}{suffix}"
    kwargs = _clean_receipt_kwargs()

    if location == "receipt":
        kwargs[field] = payload
        expected_field_in_message = field
    elif location == "trace":
        # Mutate the embedded trace by rebuilding it with the secret in
        # the chosen string field. ``error_category`` requires
        # ``error=True`` to satisfy the trace's own consistency validator.
        if field == "error_category":
            kwargs["trace"] = _clean_trace(error=True, error_category=payload)
        else:  # pragma: no cover — only error_category is currently a target
            raise AssertionError(f"unsupported trace field: {field!r}")
        expected_field_in_message = f"trace.{field}"
    else:  # pragma: no cover — strategy is sampled from a closed set
        raise AssertionError(f"unsupported location: {location!r}")

    with pytest.raises(ValueError) as excinfo:
        PerformanceReceipt(**kwargs)

    msg = str(excinfo.value)
    assert "PerformanceReceipt contains raw secret in" in msg, (
        f"expected secret-rejection message, got: {msg!r}"
    )
    assert expected_field_in_message in msg, (
        f"expected field name {expected_field_in_message!r} in error "
        f"message, got: {msg!r}"
    )


def test_performance_receipt_clean_construction_succeeds() -> None:
    """A clean kwargs payload constructs successfully — the property is non-vacuous.

    Confirms the secret-injection path above is the only path that
    fails. Without this test, a regression that rejected *every*
    receipt would still pass the rejection property vacuously.

    Validates: Requirement 12.1 (negative case anchoring the property).
    """
    receipt = PerformanceReceipt(**_clean_receipt_kwargs())
    assert receipt.mission_id == _MISSION_ID
    assert receipt.authority_expansion is False
    assert receipt.raw_secret_leakage is False
    # Receipt hash is sealed (non-empty) on a clean construction.
    assert receipt.receipt_hash != ""


# ---------------------------------------------------------------------------
# 2. LLMDecisionFrameCache rejects authority_expansion=True writes
# ---------------------------------------------------------------------------


@given(tag=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8))
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_llm_frame_cache_rejects_authority_expansion_put(tag: str) -> None:
    """:meth:`put` raises ``ValueError`` for ``authority_expansion=True`` frames.

    The cache MUST NOT store any trace of the rejected frame:

    * the per-mission bucket is unchanged (still empty for a fresh cache);
    * no events are emitted (the ``put`` rejection happens before the
      eviction-event path that would surface a ``CACHE_EVICTED``);
    * a follow-up :meth:`get` for the same composite key returns
      ``None`` and emits a plain :data:`AgentEventType.CACHE_MISS`,
      confirming that no entry was leaked into the bucket.

    Validates: Requirement 12.2.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    cache = LLMDecisionFrameCache(event_bus=bus)
    composite = _composite(cache, tag=tag)
    events_before = len(bus.events())

    with pytest.raises(ValueError):
        cache.put(
            composite,
            _frame(frame_hash=f"hash_{tag}", authority_expansion=True),
            mission_id=_MISSION_ID,
        )

    # No entry stored — the per-mission bucket is either absent (cache
    # never created one) or present but empty. Both are acceptable
    # — the invariant the spec cares about is "no entry stored".
    bucket = cache._entries.get(_MISSION_ID)
    if bucket is not None:
        assert composite not in bucket, (
            "rejected frame leaked into the per-mission bucket — the "
            "authority_expansion=True guard MUST run before any storage path"
        )

    # No events were emitted by the rejection. ``put`` is silent — the
    # bus state is unchanged.
    assert len(bus.events()) == events_before, (
        "put rejection MUST be silent; no event should be appended"
    )

    # Stats are zero — no counter was incremented either.
    stats = cache.stats(_MISSION_ID)
    assert stats == {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "ttl_evictions": 0,
        "safety_bypasses": 0,
    }, (
        f"put rejection MUST NOT touch counters; got stats={stats!r}"
    )

    # Follow-up get confirms the bucket is empty for this composite.
    result = cache.get(composite, mission_id=_MISSION_ID)
    assert result is None
    miss_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_MISS
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
    ]
    assert len(miss_events) == 1, (
        "the post-rejection get should emit exactly one CACHE_MISS — "
        "the only event on the bus for this composite"
    )
    assert miss_events[0].payload["composite"] == composite


# ---------------------------------------------------------------------------
# 3. LLMDecisionFrameCache evicts raw_secret_leakage=True on get
# ---------------------------------------------------------------------------


@given(tag=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=8))
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_llm_frame_cache_evicts_raw_secret_leakage_get(tag: str) -> None:
    """Mutating a cached entry to ``raw_secret_leakage=True`` evicts on next get.

    The cache deepcopies frames on :meth:`put` (so post-store mutation
    of the original frame cannot affect the cached copy). To test the
    read-side guard (Requirement 12.3) the test reaches into
    ``cache._entries`` and flips the flag on the cached object
    directly — simulating the worst-case path the cache is hardened
    against. The next :meth:`get` MUST:

    * return ``None``;
    * emit :data:`AgentEventType.CACHE_EVICTED` with
      ``reason="raw_secret_leakage_bypass"``;
    * remove the entry from the bucket;
    * increment ``safety_bypasses`` to exactly 1.

    A subsequent :meth:`get` of the same composite key is a plain
    miss (entry already evicted), confirming a single eviction
    rather than a re-served stale entry.

    Validates: Requirement 12.3.
    """
    bus = EventBus(mission_id=_MISSION_ID)
    cache = LLMDecisionFrameCache(event_bus=bus)
    composite = _composite(cache, tag=tag)

    # Put a clean frame.
    cache.put(
        composite,
        _frame(frame_hash=f"hash_{tag}", raw_secret_leakage=False),
        mission_id=_MISSION_ID,
    )

    # Sanity: clean hit before mutation.
    pre = cache.get(composite, mission_id=_MISSION_ID)
    assert pre is not None
    assert pre.raw_secret_leakage is False

    # White-box: flip the safety flag on the cached deepcopy.
    cached_frame, _ = cache._entries[_MISSION_ID][composite]
    cached_frame.raw_secret_leakage = True

    # Get returns None and evicts under the safety bypass.
    result = cache.get(composite, mission_id=_MISSION_ID)
    assert result is None

    # Exactly one CACHE_EVICTED with reason="raw_secret_leakage_bypass".
    bypass_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("reason") == _REASON_RAW_SECRET_LEAKAGE
    ]
    assert len(bypass_evictions) == 1, (
        f"expected exactly one raw_secret_leakage_bypass eviction, "
        f"got {len(bypass_evictions)}"
    )
    assert bypass_evictions[0].payload["composite"] == composite
    assert bypass_evictions[0].payload["mission_id"] == _MISSION_ID

    # Entry was removed from the bucket.
    assert composite not in cache._entries.get(_MISSION_ID, {}), (
        "evicted entry should be removed from the bucket"
    )

    # Counter reflects the safety bypass.
    stats = cache.stats(_MISSION_ID)
    assert stats["safety_bypasses"] == 1, (
        f"safety_bypasses counter should be 1 after a raw_secret_leakage "
        f"eviction, got {stats!r}"
    )

    # Subsequent get is a plain miss — the entry was already evicted.
    follow_up = cache.get(composite, mission_id=_MISSION_ID)
    assert follow_up is None
    # Total of one bypass eviction and one trailing plain miss.
    miss_events = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_MISS
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
    ]
    assert len(miss_events) == 1, (
        "exactly one trailing plain miss expected — the post-eviction get"
    )


# ---------------------------------------------------------------------------
# 4. DeltaStateEngine rejects out-of-envelope transitions
# ---------------------------------------------------------------------------


# Generate a (max_actions, current_action_count) pair where current >=
# max_actions so the next push_action_summary delta would exceed the
# envelope. ``max_actions`` is bounded above by 32 to keep test runtime
# manageable; the rejection branch is independent of the absolute size
# of the cap, only the relationship ``current >= max`` matters.
_envelope_breach_st = st.integers(min_value=1, max_value=16).flatmap(
    lambda max_actions: st.tuples(
        st.just(max_actions),
        st.integers(min_value=max_actions, max_value=max_actions + 16),
    )
)


@given(pair=_envelope_breach_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_delta_state_engine_rejects_out_of_envelope(pair: tuple[int, int]) -> None:
    """``push_action_summary`` deltas at or above ``max_actions`` are rejected.

    Pre-condition: seed the hot cache with ``current`` action summaries.
    The engine's ``_check_bounds`` reads
    ``self._hot_cache._action_count[mission_id]`` and rejects any
    push when that counter has reached ``envelope.max_actions``.

    On rejection the engine MUST:

    * raise ``ValueError`` whose message names the rejected delta type;
    * emit :data:`AgentEventType.AUTHORITY_VIOLATION` with payload
      ``{"mission_id": ..., "delta_type": "push_action_summary",
      "reason": "exceeds_envelope_bounds"}``;
    * preserve prior state — both the action counter and the
      action-summary list at the rejected moment match the pre-call
      snapshot. We capture the pre-call state with
      :func:`copy.deepcopy` and assert the post-rejection state
      equals the snapshot exactly.

    Validates: Requirement 12.7.
    """
    max_actions, current = pair
    bus = EventBus(mission_id=_MISSION_ID)
    hot = HotMissionCache()
    engine = DeltaStateEngine(hot, event_bus=bus)
    envelope = _envelope(max_actions=max_actions)

    # Seed the cache so action_count reaches `current`. Hot cache only
    # caps action_count when current > max_actions inside the
    # push_action_summary path, but seeding directly through the
    # public push API is the cleanest way to set up the pre-condition.
    _seed_action_count(hot, _MISSION_ID, count=current)

    # Snapshot prior state for the "preserved on rejection" check.
    view_before = hot.get(_MISSION_ID)
    assert view_before is not None
    summaries_before = copy.deepcopy(view_before.recent_action_summaries)
    overflow_before = copy.deepcopy(view_before.overflow_receipt_ids)
    action_count_before = hot._action_count.get(_MISSION_ID, 0)
    events_before = len(bus.events())

    # Attempt the rejecting push.
    delta = _summary_delta(receipt_id="rcpt_envelope_breach")
    with pytest.raises(ValueError) as excinfo:
        engine.apply(_MISSION_ID, delta, envelope)

    msg = str(excinfo.value)
    assert "push_action_summary" in msg, (
        f"expected delta_type in rejection message, got: {msg!r}"
    )
    assert "exceeds authority bounds" in msg, (
        f"expected envelope-bounds rejection wording, got: {msg!r}"
    )

    # AUTHORITY_VIOLATION event was emitted with the documented payload.
    new_events = list(bus.events()[events_before:])
    violation_events = [
        ev
        for ev in new_events
        if ev.event_type == AgentEventType.AUTHORITY_VIOLATION
    ]
    assert len(violation_events) == 1, (
        f"expected exactly one AUTHORITY_VIOLATION, got {len(violation_events)}"
    )
    payload = violation_events[0].payload
    assert payload["mission_id"] == _MISSION_ID
    assert payload["delta_type"] == "push_action_summary"
    assert payload["reason"] == "exceeds_envelope_bounds"

    # Prior state preserved exactly.
    view_after = hot.get(_MISSION_ID)
    assert view_after is not None
    assert view_after.recent_action_summaries == summaries_before, (
        "recent_action_summaries MUST be unchanged after rejection"
    )
    assert view_after.overflow_receipt_ids == overflow_before, (
        "overflow_receipt_ids MUST be unchanged after rejection"
    )
    assert hot._action_count.get(_MISSION_ID, 0) == action_count_before, (
        "_action_count MUST be unchanged after rejection"
    )


def test_delta_state_engine_accepts_within_envelope() -> None:
    """A push_action_summary below ``max_actions`` is accepted — the property is non-vacuous.

    Confirms the rejection property above is real, not vacuous: when
    ``current_action_count < envelope.max_actions`` the delta applies
    successfully, the action counter increments by exactly one, and
    no AUTHORITY_VIOLATION event is emitted.

    Validates: Requirement 12.7 (negative case anchoring the property).
    """
    bus = EventBus(mission_id=_MISSION_ID)
    hot = HotMissionCache()
    engine = DeltaStateEngine(hot, event_bus=bus)
    envelope = _envelope(max_actions=5)

    _seed_action_count(hot, _MISSION_ID, count=2)
    count_before = hot._action_count[_MISSION_ID]

    delta = _summary_delta(receipt_id="rcpt_within_envelope")
    engine.apply(_MISSION_ID, delta, envelope)

    # Counter advanced by one.
    assert hot._action_count[_MISSION_ID] == count_before + 1

    # No authority violation event was emitted.
    violations = [
        ev for ev in bus.events()
        if ev.event_type == AgentEventType.AUTHORITY_VIOLATION
    ]
    assert violations == []


# ---------------------------------------------------------------------------
# 5. Combined: no rejection path silently succeeds
# ---------------------------------------------------------------------------


@given(
    secret=_secret_patterns_st,
    prefix=_separator_st,
    suffix=_separator_st,
    pair=_envelope_breach_st,
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_no_authority_expansion_silently_succeeds(
    secret: str,
    prefix: str,
    suffix: str,
    pair: tuple[int, int],
) -> None:
    """All three rejection branches fire on the same example.

    Combined property: in a single Hypothesis example, exercise each
    component's rejection path and assert the rejection happens. A
    regression that drops a guard in any component will fail this
    test on the corresponding limb. The test specifically looks for:

    * receipt construction with a secret in ``action`` raises
      ``ValueError`` (Requirement 12.1);
    * ``cache.put`` with ``authority_expansion=True`` raises
      ``ValueError`` and stores nothing (Requirement 12.2);
    * a clean cached entry mutated to ``raw_secret_leakage=True``
      evicts on the next ``get`` and returns ``None`` (Requirement
      12.3);
    * a ``push_action_summary`` delta at the envelope cap raises
      ``ValueError`` and emits ``AUTHORITY_VIOLATION`` (Requirement
      12.7).

    No path produces a silent success.

    Validates: Requirements 12.1, 12.2, 12.3, 12.7.
    """
    max_actions, current = pair
    bus = EventBus(mission_id=_MISSION_ID)
    cache = LLMDecisionFrameCache(event_bus=bus)
    hot = HotMissionCache()
    engine = DeltaStateEngine(hot, event_bus=bus)
    envelope = _envelope(max_actions=max_actions)

    # --- (a) Receipt rejects raw secrets (Requirement 12.1) ---
    kwargs = _clean_receipt_kwargs()
    kwargs["action"] = f"{prefix}{secret}{suffix}"
    with pytest.raises(ValueError) as excinfo_receipt:
        PerformanceReceipt(**kwargs)
    assert "PerformanceReceipt contains raw secret in" in str(excinfo_receipt.value)
    assert "action" in str(excinfo_receipt.value)

    # --- (b) Cache rejects authority_expansion=True writes (Requirement 12.2) ---
    composite_b = _composite(cache, tag="ae")
    with pytest.raises(ValueError):
        cache.put(
            composite_b,
            _frame(frame_hash="hash_ae", authority_expansion=True),
            mission_id=_MISSION_ID,
        )
    # No entry in the bucket for this composite.
    bucket = cache._entries.get(_MISSION_ID)
    if bucket is not None:
        assert composite_b not in bucket

    # --- (c) Cache evicts raw_secret_leakage on get (Requirement 12.3) ---
    composite_c = _composite(cache, tag="rsl")
    cache.put(
        composite_c,
        _frame(frame_hash="hash_rsl", raw_secret_leakage=False),
        mission_id=_MISSION_ID,
    )
    # White-box flip: trigger the read-side guard.
    cached_frame, _ = cache._entries[_MISSION_ID][composite_c]
    cached_frame.raw_secret_leakage = True
    assert cache.get(composite_c, mission_id=_MISSION_ID) is None
    bypass_evictions = [
        ev
        for ev in bus.events()
        if ev.event_type == AgentEventType.CACHE_EVICTED
        and ev.payload.get("cache_type") == FRAME_CACHE_TYPE
        and ev.payload.get("reason") == _REASON_RAW_SECRET_LEAKAGE
        and ev.payload.get("composite") == composite_c
    ]
    assert len(bypass_evictions) == 1

    # --- (d) Delta engine rejects out-of-envelope push (Requirement 12.7) ---
    _seed_action_count(hot, _MISSION_ID, count=current)
    summaries_before = copy.deepcopy(hot.get(_MISSION_ID).recent_action_summaries)
    action_count_before = hot._action_count[_MISSION_ID]

    with pytest.raises(ValueError):
        engine.apply(_MISSION_ID, _summary_delta(), envelope)

    # AUTHORITY_VIOLATION emitted.
    violation_events = [
        ev for ev in bus.events()
        if ev.event_type == AgentEventType.AUTHORITY_VIOLATION
    ]
    assert len(violation_events) >= 1
    assert any(
        ev.payload.get("delta_type") == "push_action_summary"
        and ev.payload.get("reason") == "exceeds_envelope_bounds"
        for ev in violation_events
    )

    # Prior state preserved.
    assert hot.get(_MISSION_ID).recent_action_summaries == summaries_before
    assert hot._action_count[_MISSION_ID] == action_count_before
