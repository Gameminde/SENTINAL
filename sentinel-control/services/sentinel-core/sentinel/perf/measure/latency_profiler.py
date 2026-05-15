"""``LatencyProfiler`` — wall-time instrumentation with EventBus emission.

Provides synchronous and asynchronous context managers plus an explicit
start/stop API for instrumenting action latency. Every completed
instrumentation emits a ``PerformanceTrace`` via the
``PERFORMANCE_TRACE_EMITTED`` event on the injected ``EventBus``.

``aggregate_mission`` computes p50/p95/p99 percentiles across all traces
stored for a given mission.

Requirements covered: 1.1, 1.4, 1.5, 1.6, 1.7.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Callable, Iterator

from pydantic import ConfigDict, Field

from sentinel.perf.measure.performance_trace import PerformanceSeverity, PerformanceTrace
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


class MissionPerformanceAggregate(SentinelModel):
    """Frozen aggregate of latency percentiles for a mission's traces.

    When ``action_count < 2``, all percentiles equal the single value
    (or 0 if no traces exist).

    Requirements: 1.4.
    """

    mission_id: str
    action_count: int = Field(ge=0)
    p50_wall_ms: int = Field(ge=0)
    p95_wall_ms: int = Field(ge=0)
    p99_wall_ms: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", frozen=True)


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Compute the nearest-rank percentile from a sorted list of integers."""
    if not sorted_values:
        return 0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    # Nearest-rank method: index = ceil(pct/100 * n) - 1, clamped
    idx = int((pct / 100.0) * n + 0.5) - 1
    idx = max(0, min(idx, n - 1))
    return sorted_values[idx]


class LatencyProfiler:
    """Wall+CPU+queue instrumentation; attaches PerformanceTrace to EventBus.

    Requirements: 1.1, 1.5, 1.6, 1.7.
    """

    def __init__(
        self,
        event_bus: EventBus,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._event_bus = event_bus
        self._clock = clock
        self._traces: dict[str, list[PerformanceTrace]] = defaultdict(list)
        # Pending handles for explicit start/stop API
        self._pending: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Sync context manager
    # ------------------------------------------------------------------

    @contextmanager
    def instrument(
        self,
        *,
        mission_id: str,
        action_id: str,
        action_type: str,
        organ_id: str | None = None,
    ) -> Iterator[dict[str, int]]:
        """Synchronous context manager for latency instrumentation.

        Yields a mutable ``counters`` dict that the caller can populate with
        additional counter values (e.g. ``bytes_in``, ``tokens_in``). On exit
        the profiler reads from it to construct the ``PerformanceTrace``.

        On exception: ``error=True``, ``error_category=type(exc).__name__``,
        ``severity=PerformanceSeverity.CRITICAL``.

        Emits ``PERFORMANCE_TRACE_EMITTED`` via ``self._event_bus.append(...)``.
        """
        counters: dict[str, int] = {}
        start_ns = self._clock()
        error = False
        error_category: str | None = None
        severity = PerformanceSeverity.INFO
        try:
            yield counters
        except BaseException as exc:
            error = True
            error_category = type(exc).__name__
            severity = PerformanceSeverity.CRITICAL
            raise
        finally:
            end_ns = self._clock()
            wall_ms = (end_ns - start_ns) // 1_000_000
            trace = self._build_trace(
                mission_id=mission_id,
                action_id=action_id,
                action_type=action_type,
                organ_id=organ_id,
                wall_ms=wall_ms,
                error=error,
                error_category=error_category,
                severity=severity,
                counters=counters,
            )
            self._emit_and_store(trace, mission_id)

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def instrument_async(
        self,
        *,
        mission_id: str,
        action_id: str,
        action_type: str,
        organ_id: str | None = None,
    ) -> AsyncIterator[dict[str, int]]:
        """Async context manager for latency instrumentation.

        Same semantics as ``instrument`` but for ``async with`` usage.
        """
        counters: dict[str, int] = {}
        start_ns = self._clock()
        error = False
        error_category: str | None = None
        severity = PerformanceSeverity.INFO
        try:
            yield counters
        except BaseException as exc:
            error = True
            error_category = type(exc).__name__
            severity = PerformanceSeverity.CRITICAL
            raise
        finally:
            end_ns = self._clock()
            wall_ms = (end_ns - start_ns) // 1_000_000
            trace = self._build_trace(
                mission_id=mission_id,
                action_id=action_id,
                action_type=action_type,
                organ_id=organ_id,
                wall_ms=wall_ms,
                error=error,
                error_category=error_category,
                severity=severity,
                counters=counters,
            )
            self._emit_and_store(trace, mission_id)

    # ------------------------------------------------------------------
    # Explicit start / stop API
    # ------------------------------------------------------------------

    def start(
        self,
        *,
        mission_id: str,
        action_id: str,
        action_type: str,
        organ_id: str | None = None,
    ) -> str:
        """Begin timing an action. Returns a unique handle string.

        Use :meth:`stop` with the returned handle to finalize the trace.
        """
        handle = uuid.uuid4().hex
        self._pending[handle] = {
            "start_ns": self._clock(),
            "mission_id": mission_id,
            "action_id": action_id,
            "action_type": action_type,
            "organ_id": organ_id,
        }
        return handle

    def stop(
        self,
        handle: str,
        *,
        error: bool = False,
        error_category: str | None = None,
        counters: dict[str, int] | None = None,
    ) -> PerformanceTrace:
        """Finalize a previously started trace, emit it, store it, and return it.

        Raises ``KeyError`` if the handle is unknown or already stopped.
        """
        pending = self._pending.pop(handle)
        end_ns = self._clock()
        wall_ms = (end_ns - pending["start_ns"]) // 1_000_000

        severity = PerformanceSeverity.CRITICAL if error else PerformanceSeverity.INFO

        trace = self._build_trace(
            mission_id=pending["mission_id"],
            action_id=pending["action_id"],
            action_type=pending["action_type"],
            organ_id=pending["organ_id"],
            wall_ms=wall_ms,
            error=error,
            error_category=error_category,
            severity=severity,
            counters=counters or {},
        )
        self._emit_and_store(trace, pending["mission_id"])
        return trace

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_mission(self, mission_id: str) -> MissionPerformanceAggregate:
        """Compute p50, p95, p99 of ``wall_ms`` across all traces for a mission.

        When ``action_count < 2``, all percentiles equal the single value
        (or 0 if no traces).
        """
        traces = self._traces.get(mission_id, [])
        action_count = len(traces)

        if action_count == 0:
            return MissionPerformanceAggregate(
                mission_id=mission_id,
                action_count=0,
                p50_wall_ms=0,
                p95_wall_ms=0,
                p99_wall_ms=0,
            )

        sorted_wall = sorted(t.wall_ms for t in traces)

        if action_count < 2:
            val = sorted_wall[0]
            return MissionPerformanceAggregate(
                mission_id=mission_id,
                action_count=action_count,
                p50_wall_ms=val,
                p95_wall_ms=val,
                p99_wall_ms=val,
            )

        return MissionPerformanceAggregate(
            mission_id=mission_id,
            action_count=action_count,
            p50_wall_ms=_percentile(sorted_wall, 50),
            p95_wall_ms=_percentile(sorted_wall, 95),
            p99_wall_ms=_percentile(sorted_wall, 99),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_trace(
        self,
        *,
        mission_id: str,
        action_id: str,
        action_type: str,
        organ_id: str | None,
        wall_ms: int,
        error: bool,
        error_category: str | None,
        severity: PerformanceSeverity,
        counters: dict[str, int],
    ) -> PerformanceTrace:
        """Construct a ``PerformanceTrace`` from timing data and caller counters."""
        return PerformanceTrace(
            action_id=action_id,
            mission_id=mission_id,
            organ_id=organ_id,
            action_type=action_type,
            queue_wait_ms=counters.get("queue_wait_ms", 0),
            wall_ms=wall_ms,
            cpu_ms=counters.get("cpu_ms", 0),
            bytes_in=counters.get("bytes_in", 0),
            bytes_out=counters.get("bytes_out", 0),
            tokens_in=counters.get("tokens_in", 0),
            tokens_out=counters.get("tokens_out", 0),
            cache_hit=counters.get("cache_hit", 0),
            cache_miss=counters.get("cache_miss", 0),
            organ_latency_ms=counters.get("organ_latency_ms", 0),
            model_prefill_decode_ms=counters.get("model_prefill_decode_ms", 0),
            error=error,
            error_category=error_category,
            severity=severity,
        )

    def _emit_and_store(self, trace: PerformanceTrace, mission_id: str) -> None:
        """Emit the trace on the EventBus and store it internally."""
        self._traces[mission_id].append(trace)
        self._event_bus.append(
            AgentEventType.PERFORMANCE_TRACE_EMITTED,
            f"PerformanceTrace emitted for action {trace.action_id}",
            payload={"trace": trace.model_dump(mode="json")},
        )


__all__ = ["LatencyProfiler", "MissionPerformanceAggregate"]
