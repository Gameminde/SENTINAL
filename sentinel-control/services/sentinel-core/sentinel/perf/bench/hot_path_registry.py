"""Hot-path module registry and CI coverage gate for Phase F.

Task 11.6 / sentinel-performance-runtime-foundation.

Requirement: 11.8.

This module is a structural CI gate only. It does not execute benchmarks and
does not wire into production runtime. It verifies that modules declared as
part of the Sentinel hot path are represented by at least one golden mission
benchmark entry.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from sentinel.perf.bench.golden_missions import GOLDEN_MISSION_CLASSES, GoldenMission
from sentinel.shared.models import SentinelModel

__all__ = [
    "HOT_PATH_MODULES",
    "HotPathCoverageError",
    "HotPathCoverageReport",
    "HotPathModule",
    "assert_hot_path_modules_are_benchmarked",
    "hot_path_coverage_report",
]


class HotPathCoverageError(AssertionError):
    """Raised by the CI gate when a hot-path module lacks benchmark coverage."""


class HotPathModule(SentinelModel):
    """Declared module on the Phase F hot path."""

    module_path: str
    surface: str
    reason: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class HotPathCoverageReport(SentinelModel):
    """Coverage result for Requirement 11.8."""

    total_modules: int = Field(ge=0)
    covered_modules: tuple[str, ...]
    missing_modules: tuple[str, ...]
    passed: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


HOT_PATH_MODULES: tuple[HotPathModule, ...] = (
    HotPathModule(
        module_path="sentinel.agent.runtime",
        surface="decision_core",
        reason="AgentRuntime drives the decision-core mission loop.",
    ),
    HotPathModule(
        module_path="sentinel.mission.runner",
        surface="decision_core",
        reason="MissionRunner drives mission startup and terminal lifecycle.",
    ),
    HotPathModule(
        module_path="sentinel.agent.context_builder",
        surface="context_building",
        reason="ContextBuilder assembles mission context before reasoning.",
    ),
    HotPathModule(
        module_path="sentinel.agent.context_compressor",
        surface="context_building",
        reason="ContextCompressor runs on the context build path.",
    ),
    HotPathModule(
        module_path="sentinel.agent.decision_frame",
        surface="prompt_frame_assembly",
        reason="LLMDecisionFrame is the compact prompt-frame artifact.",
    ),
    HotPathModule(
        module_path="sentinel.agent.evidence_ranker",
        surface="prompt_frame_assembly",
        reason="Evidence ranking shapes prompt-frame evidence selection.",
    ),
    HotPathModule(
        module_path="sentinel.perf.caches.context_build_cache",
        surface="context_building",
        reason="ContextBuildCache wraps the context build call site.",
    ),
    HotPathModule(
        module_path="sentinel.perf.caches.llm_decision_frame_cache",
        surface="prompt_frame_assembly",
        reason="LLMDecisionFrameCache covers compact decision-frame reuse.",
    ),
    HotPathModule(
        module_path="sentinel.perf.caches.prompt_frame_cache",
        surface="prompt_frame_assembly",
        reason="PromptFrameCache covers rendered prompt reuse.",
    ),
    HotPathModule(
        module_path="sentinel.perf.caches.token_budget_governor",
        surface="prompt_frame_assembly",
        reason="TokenBudgetGovernor enforces frame/action/mission budgets.",
    ),
    HotPathModule(
        module_path="sentinel.perf.hot_cold.cold_receipt_store",
        surface="receipt_retrieval",
        reason="ColdReceiptStore persists and loads receipt bodies.",
    ),
    HotPathModule(
        module_path="sentinel.perf.hot_cold.receipt_index",
        surface="receipt_retrieval",
        reason="ReceiptIndex resolves receipt refs on retrieval paths.",
    ),
    HotPathModule(
        module_path="sentinel.perf.hot_cold.artifact_ref_store",
        surface="receipt_retrieval",
        reason="ArtifactRefStore retrieves large receipt-linked artifacts.",
    ),
    HotPathModule(
        module_path="sentinel.perf.sched.async_organ_scheduler",
        surface="decision_core",
        reason="AsyncOrganScheduler is the non-blocking organ submission path.",
    ),
    HotPathModule(
        module_path="sentinel.perf.sched.backpressure_controller",
        surface="decision_core",
        reason="BackpressureController gates hot-path organ submission.",
    ),
    HotPathModule(
        module_path="sentinel.perf.sched.batch_execution_planner",
        surface="decision_core",
        reason="BatchExecutionPlanner fuses safe hot-path read operations.",
    ),
    HotPathModule(
        module_path="sentinel.perf.sched.tool_call_queue",
        surface="decision_core",
        reason="ToolCallQueue is the observable queue behind scheduling.",
    ),
    HotPathModule(
        module_path="sentinel.perf.workspace.workspace_change_watcher",
        surface="context_building",
        reason="WorkspaceChangeWatcher feeds context cache invalidation.",
    ),
    HotPathModule(
        module_path="sentinel.perf.workspace.workspace_snapshot_cache",
        surface="context_building",
        reason="WorkspaceSnapshotCache supplies workspace_snapshot_id input.",
    ),
)


def _benchmarked_modules(golden_missions: tuple[GoldenMission, ...]) -> set[str]:
    covered: set[str] = set()
    for mission in golden_missions:
        covered.update(mission.benchmarked_modules)
    return covered


def hot_path_coverage_report(
    *,
    hot_path_modules: tuple[HotPathModule, ...] = HOT_PATH_MODULES,
    golden_missions: tuple[GoldenMission, ...] = GOLDEN_MISSION_CLASSES,
) -> HotPathCoverageReport:
    """Return coverage status for hot-path modules vs. golden missions."""

    covered = _benchmarked_modules(golden_missions)
    hot_paths = tuple(entry.module_path for entry in hot_path_modules)
    missing = tuple(sorted(module for module in hot_paths if module not in covered))
    return HotPathCoverageReport(
        total_modules=len(hot_paths),
        covered_modules=tuple(sorted(module for module in hot_paths if module in covered)),
        missing_modules=missing,
        passed=not missing,
    )


def assert_hot_path_modules_are_benchmarked(
    *,
    hot_path_modules: tuple[HotPathModule, ...] = HOT_PATH_MODULES,
    golden_missions: tuple[GoldenMission, ...] = GOLDEN_MISSION_CLASSES,
) -> HotPathCoverageReport:
    """CI gate for Requirement 11.8."""

    report = hot_path_coverage_report(
        hot_path_modules=hot_path_modules,
        golden_missions=golden_missions,
    )
    if not report.passed:
        missing = ", ".join(report.missing_modules)
        raise HotPathCoverageError(
            "hot_path_modules_missing_golden_benchmark_entries: "
            f"{missing}"
        )
    return report
