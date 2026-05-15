# Feature: sentinel-performance-runtime-foundation, Property 6: Hot/cold size bounds and overflow round-trip
"""Property-based test for HotMissionCache size bounds and overflow semantics.

**Validates: Requirements 4.1, 4.2, 4.5, 4.7, 4.8**

Tests:
  1. Footprint stays under the per-tier threshold for reasonable workloads
     (bounded structures + overflow-to-receipt-id keeps memory in check).
  2. Overflow replaces oldest summaries with receipt IDs in FIFO order;
     recent_action_summaries is capped at 10.
  3. Eviction is same-tick: after evict_mission, get(mission_id) is None
     immediately.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.perf.hot_cold.hot_mission_cache import (
    ActionSummary,
    HotMissionCache,
    MAX_ACTION_SUMMARIES_PER_MISSION,
    MAX_SUMMARY_LEN,
)
from sentinel.shared.models import new_id


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Short strings suitable for action summaries (capped at MAX_SUMMARY_LEN=200).
_short_text = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=50,
)

_receipt_id_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=4,
    max_size=20,
).map(lambda s: f"rcpt_{s}")

_action_type_st = st.sampled_from(["browse", "file_read", "api_call", "compute", "validate"])

_organ_id_st = st.one_of(st.none(), st.sampled_from(["browser", "fs", "net", "llm"]))

_ts_ns_st = st.integers(min_value=0, max_value=10**18)


@st.composite
def action_summary_st(draw: st.DrawFn) -> ActionSummary:
    """Generate a valid ActionSummary with short strings."""
    return ActionSummary(
        receipt_id=draw(_receipt_id_st),
        action_type=draw(_action_type_st),
        organ_id=draw(_organ_id_st),
        summary=draw(_short_text.filter(lambda s: len(s) <= MAX_SUMMARY_LEN)),
        ts_ns=draw(_ts_ns_st),
    )


# ---------------------------------------------------------------------------
# Property 1: Footprint stays under tier threshold
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    n=st.integers(min_value=1, max_value=50),
    summaries=st.lists(action_summary_st(), min_size=50, max_size=50),
)
def test_footprint_stays_under_tier_threshold(
    n: int,
    summaries: list[ActionSummary],
) -> None:
    """Push N action summaries into a HotMissionCache for a single mission.

    After each push, assert memory_footprint_bytes(mission_id) <=
    tier_budget_bytes(mission_id). This validates that the bounded structures
    + overflow-to-receipt-id mechanism keeps the footprint under the tier
    ceiling for reasonable workloads.
    """
    cache = HotMissionCache()
    mission_id = "mission_bounds_test"

    for i in range(n):
        summary = summaries[i]
        cache.push_action_summary(mission_id, summary)

        footprint = cache.memory_footprint_bytes(mission_id)
        budget = cache.tier_budget_bytes(mission_id)
        assert footprint <= budget, (
            f"Footprint {footprint} exceeds tier budget {budget} "
            f"after {i + 1} pushes (tier={cache.current_tier(mission_id)})"
        )


# ---------------------------------------------------------------------------
# Property 2: Overflow replaced by receipt ID (FIFO order)
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    n=st.integers(min_value=11, max_value=30),
    summaries=st.lists(action_summary_st(), min_size=30, max_size=30),
)
def test_overflow_replaced_by_receipt_id(
    n: int,
    summaries: list[ActionSummary],
) -> None:
    """Push N summaries (N from 11-30). Assert recent_action_summaries is
    capped at 10, overflow_receipt_ids has N-10 entries, and each overflow
    receipt_id matches the receipt_id of the corresponding evicted summary
    in FIFO order.
    """
    cache = HotMissionCache()
    mission_id = "mission_overflow_test"

    # Use the first N summaries from the generated list.
    used_summaries = summaries[:n]

    for summary in used_summaries:
        cache.push_action_summary(mission_id, summary)

    view = cache.get(mission_id)
    assert view is not None

    # Cap: recent_action_summaries has at most 10 entries.
    assert len(view.recent_action_summaries) == MAX_ACTION_SUMMARIES_PER_MISSION, (
        f"Expected {MAX_ACTION_SUMMARIES_PER_MISSION} recent summaries, "
        f"got {len(view.recent_action_summaries)}"
    )

    # Overflow count: N - 10 entries evicted.
    expected_overflow_count = n - MAX_ACTION_SUMMARIES_PER_MISSION
    assert len(view.overflow_receipt_ids) == expected_overflow_count, (
        f"Expected {expected_overflow_count} overflow receipt IDs, "
        f"got {len(view.overflow_receipt_ids)}"
    )

    # FIFO order: the first (N-10) summaries were evicted in order.
    evicted_summaries = used_summaries[:expected_overflow_count]
    for i, (overflow_rid, evicted_summary) in enumerate(
        zip(view.overflow_receipt_ids, evicted_summaries)
    ):
        assert overflow_rid == evicted_summary.receipt_id, (
            f"Overflow receipt_id at index {i} is {overflow_rid!r}, "
            f"expected {evicted_summary.receipt_id!r} (FIFO order)"
        )

    # The remaining 10 summaries in the view are the last 10 pushed.
    remaining_summaries = used_summaries[expected_overflow_count:]
    for i, (view_summary, expected_summary) in enumerate(
        zip(view.recent_action_summaries, remaining_summaries)
    ):
        assert view_summary.receipt_id == expected_summary.receipt_id, (
            f"recent_action_summaries[{i}].receipt_id is "
            f"{view_summary.receipt_id!r}, expected {expected_summary.receipt_id!r}"
        )


# ---------------------------------------------------------------------------
# Property 3: Eviction is same-tick
# ---------------------------------------------------------------------------


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    n=st.integers(min_value=1, max_value=20),
    summaries=st.lists(action_summary_st(), min_size=20, max_size=20),
)
def test_eviction_is_same_tick(
    n: int,
    summaries: list[ActionSummary],
) -> None:
    """Push some summaries, then call evict_mission. Assert get(mission_id)
    is None immediately (same-tick, no deferred cleanup).
    """
    cache = HotMissionCache()
    mission_id = "mission_eviction_test"

    # Push N summaries.
    for i in range(n):
        cache.push_action_summary(mission_id, summaries[i])

    # Verify the mission exists before eviction.
    assert cache.get(mission_id) is not None, "Mission should exist before eviction"

    # Evict synchronously.
    cache.evict_mission(mission_id)

    # Same-tick: get returns None immediately after eviction.
    assert cache.get(mission_id) is None, (
        "get(mission_id) must return None immediately after evict_mission "
        "(same-tick eviction, Requirement 4.7)"
    )

    # Footprint is 0 after eviction.
    assert cache.memory_footprint_bytes(mission_id) == 0, (
        "memory_footprint_bytes must be 0 after eviction"
    )
