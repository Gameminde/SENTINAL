"""Benchmark: LatencyProfiler overhead < 1 ms per instrumented action.

Validates: Requirements 1.5

Measures the wall-time overhead introduced by LatencyProfiler.instrument()
on a single-action sequential workload. The overhead budget is 1 ms
(1_000_000 ns) per instrumented action.

Note: Each iteration uses a fresh EventBus to isolate the profiler's
per-action instrumentation cost from the EventBus O(n) chain-integrity
verification (Task 7 / Requirement 7). In production, each mission has
its own EventBus and actions are not accumulated in a single bus before
the first action completes. The chain-integrity cost is a separate
concern addressed by the BenchmarkHarness in Phase F.
"""

from __future__ import annotations

import time

from sentinel.perf.measure.latency_profiler import LatencyProfiler
from sentinel.shared.events import EventBus

ITERATIONS = 100
OVERHEAD_BUDGET_NS = 1_000_000  # 1 ms in nanoseconds


def _make_profiler() -> tuple[EventBus, LatencyProfiler]:
    """Create a fresh EventBus + LatencyProfiler pair."""
    bus = EventBus(mission_id="bench-mission")
    profiler = LatencyProfiler(event_bus=bus)
    return bus, profiler


def test_latency_profiler_overhead_under_1ms() -> None:
    """Assert average overhead per instrumented no-op action < 1 ms.

    Runs 100 iterations of a no-op action through instrument(...),
    each with a fresh profiler to measure per-action instrumentation cost.
    Measures total wall time and computes average overhead per action.
    """
    # Pre-create profilers to exclude setup from timing
    profilers = [_make_profiler() for _ in range(ITERATIONS)]

    start_ns = time.perf_counter_ns()
    for i in range(ITERATIONS):
        _, profiler = profilers[i]
        with profiler.instrument(
            mission_id="bench-mission",
            action_id=f"action-{i}",
            action_type="noop",
        ):
            pass  # no-op action body
    end_ns = time.perf_counter_ns()

    total_ns = end_ns - start_ns
    avg_overhead_ns = total_ns // ITERATIONS
    avg_overhead_us = avg_overhead_ns / 1_000

    print(f"\n[Benchmark] LatencyProfiler overhead (absolute):")
    print(f"  Total for {ITERATIONS} instrumented no-ops: {total_ns / 1_000_000:.3f} ms")
    print(f"  Average per action: {avg_overhead_us:.1f} µs ({avg_overhead_ns} ns)")
    print(f"  Budget: {OVERHEAD_BUDGET_NS / 1_000:.0f} µs (1 ms)")

    assert avg_overhead_ns < OVERHEAD_BUDGET_NS, (
        f"LatencyProfiler overhead {avg_overhead_us:.1f} µs exceeds 1 ms budget"
    )


def test_latency_profiler_overhead_vs_uninstrumented() -> None:
    """Assert instrumentation overhead (instrumented - uninstrumented) < 1 ms.

    Runs 100 iterations of the same no-op action WITHOUT instrumentation,
    then 100 iterations WITH instrumentation (fresh profiler per action),
    and computes the per-action overhead as the difference.
    """
    # Pre-create profilers to exclude setup from timing
    profilers = [_make_profiler() for _ in range(ITERATIONS)]

    # --- Uninstrumented baseline ---
    start_ns = time.perf_counter_ns()
    for i in range(ITERATIONS):
        pass  # no-op action body (same as instrumented)
    end_ns = time.perf_counter_ns()
    uninstrumented_total_ns = end_ns - start_ns

    # --- Instrumented ---
    start_ns = time.perf_counter_ns()
    for i in range(ITERATIONS):
        _, profiler = profilers[i]
        with profiler.instrument(
            mission_id="bench-mission",
            action_id=f"action-{i}",
            action_type="noop",
        ):
            pass  # no-op action body
    end_ns = time.perf_counter_ns()
    instrumented_total_ns = end_ns - start_ns

    # --- Compute overhead ---
    overhead_total_ns = instrumented_total_ns - uninstrumented_total_ns
    overhead_per_action_ns = overhead_total_ns // ITERATIONS
    overhead_per_action_us = overhead_per_action_ns / 1_000

    print(f"\n[Benchmark] LatencyProfiler overhead (differential):")
    print(f"  Uninstrumented {ITERATIONS} no-ops: {uninstrumented_total_ns / 1_000_000:.3f} ms")
    print(f"  Instrumented {ITERATIONS} no-ops:   {instrumented_total_ns / 1_000_000:.3f} ms")
    print(f"  Overhead per action: {overhead_per_action_us:.1f} µs ({overhead_per_action_ns} ns)")
    print(f"  Budget: {OVERHEAD_BUDGET_NS / 1_000:.0f} µs (1 ms)")

    assert overhead_per_action_ns < OVERHEAD_BUDGET_NS, (
        f"LatencyProfiler overhead {overhead_per_action_us:.1f} µs exceeds 1 ms budget"
    )
