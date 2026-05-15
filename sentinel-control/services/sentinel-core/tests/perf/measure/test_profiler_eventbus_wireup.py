"""Unit tests — profiler EventBus wire-up.

Validates: Requirements 1.6, 12.8

Asserts that:
  a. ``LatencyProfiler.instrument`` emits ``PERFORMANCE_TRACE_EMITTED``
     through the ``EventBus``.
  b. Failure paths emit ``severity='critical'`` without raw secrets in payload.
  c. The async surface produces the same trace shape as the sync surface.
  d. Explicit ``start``/``stop`` emits ``PERFORMANCE_TRACE_EMITTED``.
"""

from __future__ import annotations

import asyncio

import pytest

from sentinel.agent.evidence_ranker import SECRET_PATTERNS
from sentinel.perf.measure.latency_profiler import LatencyProfiler
from sentinel.perf.measure.performance_trace import PerformanceSeverity
from sentinel.shared.events import AgentEventType, EventBus


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_MISSION_ID = "mission_wireup_test_001"

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
# Helpers
# ---------------------------------------------------------------------------


def _get_perf_events(bus: EventBus) -> list:
    """Return all events with type PERFORMANCE_TRACE_EMITTED from the bus."""
    return [
        e
        for e in bus.events()
        if e.event_type == AgentEventType.PERFORMANCE_TRACE_EMITTED
    ]


def _payload_string_values(payload: dict) -> list[str]:
    """Recursively collect all string values from a nested dict."""
    values: list[str] = []
    for v in payload.values():
        if isinstance(v, str):
            values.append(v)
        elif isinstance(v, dict):
            values.extend(_payload_string_values(v))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, dict):
                    values.extend(_payload_string_values(item))
    return values


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInstrumentEmitsPerformanceTraceEmitted:
    """test_instrument_emits_performance_trace_emitted"""

    def test_instrument_emits_performance_trace_emitted(self) -> None:
        """Sync instrument(...) emits PERFORMANCE_TRACE_EMITTED with a trace
        dict containing all 11 numeric fields."""
        bus = EventBus(mission_id=TEST_MISSION_ID)
        profiler = LatencyProfiler(event_bus=bus)

        with profiler.instrument(
            mission_id=TEST_MISSION_ID,
            action_id="act_001",
            action_type="test_action",
            organ_id="organ_test",
        ):
            pass  # simulate a successful action

        perf_events = _get_perf_events(bus)
        assert len(perf_events) == 1

        event = perf_events[0]
        assert event.event_type == AgentEventType.PERFORMANCE_TRACE_EMITTED

        # Payload must contain a 'trace' dict with all 11 numeric fields
        assert "trace" in event.payload
        trace = event.payload["trace"]
        assert isinstance(trace, dict)

        for field in NUMERIC_FIELDS:
            assert field in trace, f"Missing numeric field: {field}"
            assert isinstance(trace[field], int), f"{field} is not int"
            assert trace[field] >= 0, f"{field} is negative"


class TestFailurePathEmitsCriticalNoSecrets:
    """test_failure_path_emits_critical_no_secrets"""

    def test_failure_path_emits_critical_no_secrets(self) -> None:
        """When an exception is raised inside instrument(...), the emitted
        trace has severity='critical' and no payload string values match
        SECRET_PATTERNS."""
        bus = EventBus(mission_id=TEST_MISSION_ID)
        profiler = LatencyProfiler(event_bus=bus)

        with pytest.raises(RuntimeError):
            with profiler.instrument(
                mission_id=TEST_MISSION_ID,
                action_id="act_fail_001",
                action_type="failing_action",
                organ_id="organ_fail",
            ):
                raise RuntimeError("something went wrong")

        perf_events = _get_perf_events(bus)
        assert len(perf_events) == 1

        event = perf_events[0]
        trace = event.payload["trace"]

        # Severity must be critical
        assert trace["severity"] == PerformanceSeverity.CRITICAL.value

        # No raw secrets in any string value of the payload
        all_strings = _payload_string_values(event.payload)
        for s in all_strings:
            for pattern in SECRET_PATTERNS:
                assert not pattern.search(s), (
                    f"Secret pattern matched in payload string: {s!r}"
                )


class TestAsyncSurfaceSameTraceShape:
    """test_async_surface_same_trace_shape"""

    def test_async_surface_same_trace_shape(self) -> None:
        """instrument_async(...) emits the same event structure (same
        event_type, same payload keys, same trace field names) as the sync
        surface."""
        # --- Sync ---
        sync_bus = EventBus(mission_id=TEST_MISSION_ID)
        sync_profiler = LatencyProfiler(event_bus=sync_bus)

        with sync_profiler.instrument(
            mission_id=TEST_MISSION_ID,
            action_id="act_sync",
            action_type="sync_action",
            organ_id="organ_sync",
        ):
            pass

        sync_events = _get_perf_events(sync_bus)
        assert len(sync_events) == 1
        sync_event = sync_events[0]

        # --- Async ---
        async_bus = EventBus(mission_id=TEST_MISSION_ID)
        async_profiler = LatencyProfiler(event_bus=async_bus)

        async def _run_async() -> None:
            async with async_profiler.instrument_async(
                mission_id=TEST_MISSION_ID,
                action_id="act_async",
                action_type="async_action",
                organ_id="organ_async",
            ):
                pass

        asyncio.run(_run_async())

        async_events = _get_perf_events(async_bus)
        assert len(async_events) == 1
        async_event = async_events[0]

        # Same event_type
        assert sync_event.event_type == async_event.event_type

        # Same payload keys
        assert set(sync_event.payload.keys()) == set(async_event.payload.keys())

        # Same trace field names
        sync_trace_keys = set(sync_event.payload["trace"].keys())
        async_trace_keys = set(async_event.payload["trace"].keys())
        assert sync_trace_keys == async_trace_keys


class TestStartStopEmitsEvent:
    """test_start_stop_emits_event"""

    def test_start_stop_emits_event(self) -> None:
        """Explicit start(...) / stop(...) emits PERFORMANCE_TRACE_EMITTED."""
        bus = EventBus(mission_id=TEST_MISSION_ID)
        profiler = LatencyProfiler(event_bus=bus)

        handle = profiler.start(
            mission_id=TEST_MISSION_ID,
            action_id="act_startstop",
            action_type="startstop_action",
            organ_id="organ_startstop",
        )

        # No event emitted yet
        assert len(_get_perf_events(bus)) == 0

        profiler.stop(handle)

        perf_events = _get_perf_events(bus)
        assert len(perf_events) == 1

        event = perf_events[0]
        assert event.event_type == AgentEventType.PERFORMANCE_TRACE_EMITTED

        # Payload contains a trace dict with all 11 numeric fields
        assert "trace" in event.payload
        trace = event.payload["trace"]
        for field in NUMERIC_FIELDS:
            assert field in trace
            assert isinstance(trace[field], int)
            assert trace[field] >= 0
