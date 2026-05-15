# Feature: sentinel-performance-runtime-foundation, Property 1: PerformanceTrace shape is total and non-negative
"""Property-based test for PerformanceTrace shape totality and non-negativity.

**Validates: Requirements 1.1, 1.7, 10.9, 12.8**

Exercises sync ``instrument``, async ``instrument_async``, and explicit
``start``/``stop`` emission paths. Verifies:
  a. All 11 numeric fields are non-negative integers.
  b. Error consistency (error=True ↔ non-empty error_category).
  c. Critical severity carries no raw secret substrings.
  d–g. Sync, async, explicit start/stop, and failure paths all produce
       conformant traces.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sentinel.agent.evidence_ranker import SECRET_PATTERNS
from sentinel.perf.measure.latency_profiler import LatencyProfiler
from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.shared.events import EventBus


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_MISSION_ID = "mission_test_property_001"

# The 11 numeric counter field names on PerformanceTrace.
NUMERIC_FIELDS = [
    "queue_wait_ms",
    "wall_ms",
    "cpu_ms",
    "bytes_in",
    "bytes_out",
    "tokens_in",
    "tokens_out",
    "cache_hit",
    "cache_miss",
    "organ_latency_ms",
    "model_prefill_decode_ms",
]


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_non_neg_int = st.integers(min_value=0, max_value=10_000_000)

_severity_st = st.sampled_from(list(PerformanceSeverity))

# Strategy for error/error_category that are jointly consistent.
_error_pair_st = st.one_of(
    # error=False, error_category=None
    st.just((False, None)),
    # error=True, error_category=non-empty string
    st.tuples(
        st.just(True),
        st.text(min_size=1, max_size=50, alphabet=st.characters(categories=("L", "N", "P"))),
    ),
)

# Strategy for a valid PerformanceTrace (all fields consistent).
_trace_st = st.builds(
    lambda counters, error_pair, severity, action_id, action_type, organ_id: PerformanceTrace(
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
        error=error_pair[0],
        error_category=error_pair[1],
        severity=severity,
    ),
    counters=st.tuples(*([_non_neg_int] * 11)),
    error_pair=_error_pair_st,
    severity=_severity_st,
    action_id=st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
    organ_id=st.one_of(st.none(), st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N")))),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_trace_shape(trace: PerformanceTrace) -> None:
    """Assert the trace satisfies shape totality and non-negativity."""
    # (a) All 11 numeric fields present, int, >= 0
    for field_name in NUMERIC_FIELDS:
        value = getattr(trace, field_name)
        assert isinstance(value, int), f"{field_name} is not int: {type(value)}"
        assert value >= 0, f"{field_name} is negative: {value}"

    # (b) Error consistency
    if trace.error:
        assert isinstance(trace.error_category, str), "error=True but error_category is not str"
        assert trace.error_category.strip(), "error=True but error_category is empty/whitespace"
    else:
        assert trace.error_category is None, f"error=False but error_category={trace.error_category!r}"

    # (c) Critical severity carries no raw secret substrings
    if trace.severity == PerformanceSeverity.CRITICAL or trace.severity == "critical":
        _assert_no_secrets_in_trace(trace)


def _assert_no_secrets_in_trace(trace: PerformanceTrace) -> None:
    """Verify no string field on the trace matches any SECRET_PATTERN."""
    string_fields: dict[str, str] = {}
    for field_name in PerformanceTrace.model_fields:
        value = getattr(trace, field_name)
        if isinstance(value, str):
            string_fields[field_name] = value

    for field_name, value in string_fields.items():
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(value), (
                f"Secret pattern matched in trace field '{field_name}': "
                f"pattern={pattern.pattern!r}, value={value!r}"
            )


def _get_last_emitted_trace(event_bus: EventBus) -> PerformanceTrace:
    """Extract the last PerformanceTrace emitted to the EventBus."""
    events = event_bus.events()
    assert len(events) > 0, "No events emitted to EventBus"
    last_event = events[-1]
    assert "trace" in last_event.payload, "Last event has no 'trace' in payload"
    trace_data = last_event.payload["trace"]
    return PerformanceTrace(**trace_data)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@given(trace=_trace_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_shape_totality_all_numeric_fields_non_negative(trace: PerformanceTrace) -> None:
    """(a) Every generated trace has exactly 11 numeric fields, all int, all >= 0.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """
    _assert_trace_shape(trace)


@given(error_pair=_error_pair_st)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_error_consistency(error_pair: tuple[bool, str | None]) -> None:
    """(b) error=True → error_category is non-empty string; error=False → None.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """
    trace = PerformanceTrace(
        action_id="act_test",
        mission_id=TEST_MISSION_ID,
        action_type="test_action",
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
        error=error_pair[0],
        error_category=error_pair[1],
        severity=PerformanceSeverity.CRITICAL if error_pair[0] else PerformanceSeverity.INFO,
    )
    _assert_trace_shape(trace)


@given(
    action_id=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_critical_severity_no_raw_secrets(action_id: str, action_type: str) -> None:
    """(c) When severity='critical', no string field matches SECRET_PATTERNS.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """
    trace = PerformanceTrace(
        action_id=action_id,
        mission_id=TEST_MISSION_ID,
        action_type=action_type,
        queue_wait_ms=0,
        wall_ms=100,
        cpu_ms=50,
        bytes_in=0,
        bytes_out=0,
        tokens_in=0,
        tokens_out=0,
        cache_hit=0,
        cache_miss=0,
        organ_latency_ms=0,
        model_prefill_decode_ms=0,
        error=True,
        error_category="SecurityViolation",
        severity=PerformanceSeverity.CRITICAL,
    )
    _assert_no_secrets_in_trace(trace)


@given(
    action_id=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_sync_instrument_path(action_id: str, action_type: str) -> None:
    """(d) Sync instrument path emits a conformant PerformanceTrace.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """
    event_bus = EventBus(mission_id=TEST_MISSION_ID)
    profiler = LatencyProfiler(event_bus)

    with profiler.instrument(
        mission_id=TEST_MISSION_ID,
        action_id=action_id,
        action_type=action_type,
    ) as counters:
        counters["bytes_in"] = 100
        counters["tokens_in"] = 50

    trace = _get_last_emitted_trace(event_bus)
    _assert_trace_shape(trace)
    assert trace.action_id == action_id
    assert trace.mission_id == TEST_MISSION_ID
    assert trace.action_type == action_type
    assert trace.error is False
    assert trace.bytes_in == 100
    assert trace.tokens_in == 50


@given(
    action_id=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_async_instrument_path(action_id: str, action_type: str) -> None:
    """(e) Async instrument_async path emits a conformant PerformanceTrace.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """

    async def _run() -> PerformanceTrace:
        event_bus = EventBus(mission_id=TEST_MISSION_ID)
        profiler = LatencyProfiler(event_bus)

        async with profiler.instrument_async(
            mission_id=TEST_MISSION_ID,
            action_id=action_id,
            action_type=action_type,
        ) as counters:
            counters["tokens_out"] = 25

        return _get_last_emitted_trace(event_bus)

    trace = asyncio.run(_run())
    _assert_trace_shape(trace)
    assert trace.action_id == action_id
    assert trace.mission_id == TEST_MISSION_ID
    assert trace.action_type == action_type
    assert trace.error is False
    assert trace.tokens_out == 25


@given(
    action_id=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_explicit_start_stop_path(action_id: str, action_type: str) -> None:
    """(f) Explicit start/stop path emits a conformant PerformanceTrace.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """
    event_bus = EventBus(mission_id=TEST_MISSION_ID)
    profiler = LatencyProfiler(event_bus)

    handle = profiler.start(
        mission_id=TEST_MISSION_ID,
        action_id=action_id,
        action_type=action_type,
    )
    trace = profiler.stop(handle, counters={"cache_hit": 3, "cache_miss": 1})

    _assert_trace_shape(trace)
    assert trace.action_id == action_id
    assert trace.mission_id == TEST_MISSION_ID
    assert trace.action_type == action_type
    assert trace.error is False
    assert trace.cache_hit == 3
    assert trace.cache_miss == 1

    # Also verify it was emitted to EventBus
    emitted_trace = _get_last_emitted_trace(event_bus)
    assert emitted_trace.action_id == action_id


@given(
    action_id=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))),
    action_type=st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L",))),
)
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_failure_path_sets_error_and_critical(action_id: str, action_type: str) -> None:
    """(g) Failure inside instrument sets error=True, error_category, severity='critical'.

    **Validates: Requirements 1.1, 1.7, 10.9, 12.8**
    """
    event_bus = EventBus(mission_id=TEST_MISSION_ID)
    profiler = LatencyProfiler(event_bus)

    class CustomTestError(Exception):
        pass

    with pytest.raises(CustomTestError):
        with profiler.instrument(
            mission_id=TEST_MISSION_ID,
            action_id=action_id,
            action_type=action_type,
        ):
            raise CustomTestError("simulated failure")

    trace = _get_last_emitted_trace(event_bus)
    _assert_trace_shape(trace)
    assert trace.error is True
    assert trace.error_category == "CustomTestError"
    assert trace.severity == PerformanceSeverity.CRITICAL
