# Feature: sentinel-performance-runtime-foundation, Property 2: PerformanceReceipt is append-only and immutable
"""Property-based test for PerformanceReceipt immutability and aggregate ordering.

**Validates: Requirements 1.3, 1.4**

Tests:
  a. **Immutability**: for any valid receipt, attempting to set any field
     raises ``ValidationError`` (pydantic frozen model). The receipt remains
     unchanged after the failed mutation.
  b. **Aggregate ordering**: use ``LatencyProfiler`` to record N traces
     (N drawn from Hypothesis, range 0–50) for a mission, then call
     ``aggregate_mission``. Assert:
       - When ``action_count < 2``: ``p50 == p95 == p99`` (all equal the
         single value, or 0 if no traces).
       - When ``action_count >= 2``: ``p50 <= p95 <= p99``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from sentinel.perf.measure.latency_profiler import LatencyProfiler
from sentinel.perf.measure.performance_receipt import PerformanceReceipt
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.shared.events import EventBus


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_MISSION_ID = "mission_receipt_prop_002"

# Fields on PerformanceReceipt that can be mutated for immutability testing.
# We pick representative fields of different types.
RECEIPT_MUTABLE_FIELDS = {
    "mission_id": "mutated_mission",
    "action_id": "mutated_action",
    "action": "mutated_action_name",
    "budget_remaining": 999999,
    "budget_limit": 999999,
    "authority_expansion": True,
    "raw_secret_leakage": True,
    "receipt_hash": "0000000000000000000000000000000000000000000000000000000000000000",
}


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_non_neg_int = st.integers(min_value=0, max_value=10_000_000)

# Strategy for a valid PerformanceTrace (consistent error fields).
_trace_st = st.builds(
    lambda counters, action_id, action_type, organ_id: PerformanceTrace(
        action_id=action_id,
        mission_id=TEST_MISSION_ID,
        organ_id=organ_id,
        action_type=action_type,
        queue_wait_ms=counters[0],
        wall_ms=counters[1],
        cpu_ms=counters[2],
        bytes_in=counters[3],
        bytes_out=counters[4],
        tokens_in=counters[5],
        tokens_out=counters[6],
        cache_hit=counters[7],
        cache_miss=counters[8],
        organ_latency_ms=counters[9],
        model_prefill_decode_ms=counters[10],
        error=False,
        error_category=None,
        severity=PerformanceSeverity.INFO,
    ),
    counters=st.tuples(*([_non_neg_int] * 11)),
    action_id=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
    organ_id=st.one_of(
        st.none(),
        st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    ),
)

# Strategy for valid budget values.
_budget_st = st.integers(min_value=0, max_value=1_000_000)

# Strategy for a valid PerformanceReceipt.
_receipt_st = st.builds(
    lambda trace, budget_remaining, budget_limit, action: PerformanceReceipt(
        mission_id=TEST_MISSION_ID,
        action_id=trace.action_id,
        organ_id=trace.organ_id,
        action=action,
        trace=trace,
        estimated_cost_usd=Decimal("0.001000"),
        model_id="test-model",
        budget_remaining=budget_remaining,
        budget_limit=max(budget_remaining, budget_limit),
        cache_type=None,
        backpressure_reason=None,
        queue_depth_at_receipt=None,
        deadline_ms=None,
        elapsed_ms=None,
        authority_expansion=False,
        raw_secret_leakage=False,
        created_at=datetime.now(UTC),
    ),
    trace=_trace_st,
    budget_remaining=_budget_st,
    budget_limit=_budget_st,
    action=st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N"))),
)


# ---------------------------------------------------------------------------
# Property tests — Immutability
# ---------------------------------------------------------------------------


@given(receipt=_receipt_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_receipt_immutability_field_mutation_raises(receipt: PerformanceReceipt) -> None:
    """(a) Any field mutation on a frozen PerformanceReceipt raises ValidationError.

    The receipt remains unchanged after the failed mutation attempt.

    **Validates: Requirements 1.3**
    """
    # Snapshot the original hash to verify receipt is unchanged after mutation attempts.
    original_hash = receipt.receipt_hash
    original_dump = receipt.model_dump(mode="json")

    for field_name, mutant_value in RECEIPT_MUTABLE_FIELDS.items():
        with pytest.raises(ValidationError):
            setattr(receipt, field_name, mutant_value)

        # Receipt must be unchanged after the failed mutation.
        assert receipt.receipt_hash == original_hash, (
            f"Receipt hash changed after failed mutation of '{field_name}'"
        )
        assert receipt.model_dump(mode="json") == original_dump, (
            f"Receipt state changed after failed mutation of '{field_name}'"
        )


@given(receipt=_receipt_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_receipt_embedded_trace_immutability(receipt: PerformanceReceipt) -> None:
    """(a-ext) Embedded PerformanceTrace is also immutable — mutation raises.

    **Validates: Requirements 1.3**
    """
    original_dump = receipt.model_dump(mode="json")

    # Attempt to mutate the embedded trace's wall_ms field.
    with pytest.raises(ValidationError):
        receipt.trace.wall_ms = 999999  # type: ignore[misc]

    # Receipt must be unchanged.
    assert receipt.model_dump(mode="json") == original_dump


# ---------------------------------------------------------------------------
# Property tests — Aggregate ordering
# ---------------------------------------------------------------------------


@given(n_traces=st.integers(min_value=0, max_value=50))
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_aggregate_mission_ordering(n_traces: int) -> None:
    """(b) aggregate_mission yields correct percentile ordering.

    - When action_count < 2: p50 == p95 == p99 (single value or 0).
    - When action_count >= 2: p50 <= p95 <= p99.

    **Validates: Requirements 1.4**
    """
    event_bus = EventBus(mission_id=TEST_MISSION_ID)
    profiler = LatencyProfiler(event_bus)

    # Record N traces using the sync instrument path.
    for i in range(n_traces):
        with profiler.instrument(
            mission_id=TEST_MISSION_ID,
            action_id=f"action_{i}",
            action_type="test_aggregate",
        ):
            pass  # Just record the trace with wall_ms from clock.

    aggregate = profiler.aggregate_mission(TEST_MISSION_ID)

    assert aggregate.mission_id == TEST_MISSION_ID
    assert aggregate.action_count == n_traces

    if n_traces < 2:
        # All percentiles must be equal (single value or 0).
        assert aggregate.p50_wall_ms == aggregate.p95_wall_ms == aggregate.p99_wall_ms, (
            f"Expected equal percentiles for action_count={n_traces}, "
            f"got p50={aggregate.p50_wall_ms}, p95={aggregate.p95_wall_ms}, p99={aggregate.p99_wall_ms}"
        )
        if n_traces == 0:
            assert aggregate.p50_wall_ms == 0
    else:
        # p50 <= p95 <= p99
        assert aggregate.p50_wall_ms <= aggregate.p95_wall_ms, (
            f"p50={aggregate.p50_wall_ms} > p95={aggregate.p95_wall_ms}"
        )
        assert aggregate.p95_wall_ms <= aggregate.p99_wall_ms, (
            f"p95={aggregate.p95_wall_ms} > p99={aggregate.p99_wall_ms}"
        )


@given(
    wall_values=st.lists(
        st.integers(min_value=0, max_value=100_000),
        min_size=0,
        max_size=50,
    )
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_aggregate_mission_ordering_explicit_values(wall_values: list[int]) -> None:
    """(b-ext) aggregate_mission with explicit wall_ms values preserves ordering.

    Uses explicit start/stop with a controlled clock to inject specific
    wall_ms values, then verifies percentile ordering.

    **Validates: Requirements 1.4**
    """
    # Use a controllable clock to produce specific wall_ms values.
    clock_ns = [0]  # mutable container for the clock state

    def controlled_clock() -> int:
        return clock_ns[0]

    event_bus = EventBus(mission_id=TEST_MISSION_ID)
    profiler = LatencyProfiler(event_bus, clock=controlled_clock)

    for i, wall_ms in enumerate(wall_values):
        # Set clock to 0 at start, then advance by wall_ms * 1_000_000 ns at stop.
        clock_ns[0] = 0
        handle = profiler.start(
            mission_id=TEST_MISSION_ID,
            action_id=f"action_{i}",
            action_type="test_explicit",
        )
        clock_ns[0] = wall_ms * 1_000_000  # Convert ms to ns
        profiler.stop(handle)

    aggregate = profiler.aggregate_mission(TEST_MISSION_ID)

    assert aggregate.action_count == len(wall_values)

    if len(wall_values) < 2:
        assert aggregate.p50_wall_ms == aggregate.p95_wall_ms == aggregate.p99_wall_ms
        if len(wall_values) == 0:
            assert aggregate.p50_wall_ms == 0
        elif len(wall_values) == 1:
            assert aggregate.p50_wall_ms == wall_values[0]
    else:
        assert aggregate.p50_wall_ms <= aggregate.p95_wall_ms <= aggregate.p99_wall_ms
