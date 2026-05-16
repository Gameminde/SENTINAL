from __future__ import annotations

from typing import TYPE_CHECKING

from sentinel.agent.models import AgentContext

if TYPE_CHECKING:
    from sentinel.perf.measure.latency_profiler import LatencyProfiler


class ContextCompressor:
    def __init__(self, *, latency_profiler: LatencyProfiler | None = None) -> None:
        self._latency_profiler = latency_profiler

    def compress(self, context: AgentContext) -> AgentContext:
        if self._latency_profiler is not None:
            with self._latency_profiler.instrument(
                mission_id=context.mission.id,
                action_id=f"{context.mission.id}:context_compress",
                action_type="context_compress",
            ):
                return self._do_compress(context)
        return self._do_compress(context)

    def _do_compress(self, context: AgentContext) -> AgentContext:
        summary = context.summary
        if len(summary) > 500:
            summary = f"{summary[:497]}..."
        return context.model_copy(update={"summary": summary})
