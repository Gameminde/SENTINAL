"""Golden mission definitions for Phase F benchmark regression gates.

Task 11.1 / sentinel-performance-runtime-foundation.

Requirements: 11.1, 11.5, 11.6, 11.7.

This module defines the canonical mission classes the Phase F benchmark
harness will execute. It is configuration only: no benchmark execution, no
runtime wiring, no authority changes.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator

from sentinel.shared.models import SentinelModel

__all__ = [
    "BROWSER_HEAVY",
    "GOLDEN_MISSION_BY_NAME",
    "GOLDEN_MISSION_CLASSES",
    "MULTI_TOOL",
    "SINGLE_TOOL",
    "STARTUP",
    "GoldenMission",
]


class GoldenMission(SentinelModel):
    """Immutable benchmark class definition with latency budgets.

    Budgets are milliseconds. The harness added in later Phase F tasks will
    compute measured p50 / p95 / p99 values and compare them against these
    structural budgets; this model only records the contract.
    """

    name: str
    min_iterations: int = Field(ge=30)
    p50_budget_ms: int = Field(gt=0)
    p95_budget_ms: int = Field(gt=0)
    p99_budget_ms: int = Field(gt=0)
    benchmarked_modules: tuple[str, ...] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def _validate_budget_order(self) -> "GoldenMission":
        if not self.p50_budget_ms <= self.p95_budget_ms <= self.p99_budget_ms:
            raise ValueError("GoldenMission budgets must satisfy p50 <= p95 <= p99")
        return self


STARTUP = GoldenMission(
    name="startup",
    min_iterations=30,
    p50_budget_ms=150,
    p95_budget_ms=400,
    p99_budget_ms=800,
    benchmarked_modules=(
        "sentinel.agent.runtime",
        "sentinel.mission.runner",
    ),
)

SINGLE_TOOL = GoldenMission(
    name="single_tool",
    min_iterations=30,
    p50_budget_ms=200,
    p95_budget_ms=500,
    p99_budget_ms=1000,
    benchmarked_modules=(
        "sentinel.agent.context_builder",
        "sentinel.agent.context_compressor",
        "sentinel.agent.decision_frame",
        "sentinel.agent.evidence_ranker",
        "sentinel.perf.caches.context_build_cache",
        "sentinel.perf.caches.llm_decision_frame_cache",
        "sentinel.perf.caches.prompt_frame_cache",
        "sentinel.perf.caches.token_budget_governor",
    ),
)

MULTI_TOOL = GoldenMission(
    name="multi_tool",
    min_iterations=30,
    p50_budget_ms=400,
    p95_budget_ms=1000,
    p99_budget_ms=2000,
    benchmarked_modules=(
        "sentinel.perf.sched.async_organ_scheduler",
        "sentinel.perf.sched.backpressure_controller",
        "sentinel.perf.sched.batch_execution_planner",
        "sentinel.perf.sched.tool_call_queue",
    ),
)

BROWSER_HEAVY = GoldenMission(
    name="browser_heavy",
    min_iterations=30,
    p50_budget_ms=800,
    p95_budget_ms=2000,
    p99_budget_ms=4000,
    benchmarked_modules=(
        "sentinel.perf.hot_cold.artifact_ref_store",
        "sentinel.perf.hot_cold.cold_receipt_store",
        "sentinel.perf.hot_cold.receipt_index",
        "sentinel.perf.workspace.workspace_change_watcher",
        "sentinel.perf.workspace.workspace_snapshot_cache",
    ),
)

GOLDEN_MISSION_CLASSES: tuple[GoldenMission, ...] = (
    STARTUP,
    SINGLE_TOOL,
    MULTI_TOOL,
    BROWSER_HEAVY,
)

GOLDEN_MISSION_BY_NAME: dict[str, GoldenMission] = {
    mission.name: mission for mission in GOLDEN_MISSION_CLASSES
}
