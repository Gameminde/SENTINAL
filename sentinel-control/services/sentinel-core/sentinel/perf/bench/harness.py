"""Benchmark harness run foundation for Phase F.

Task 11.2 / sentinel-performance-runtime-foundation.

Requirements: 11.2, 11.9.

This module implements ``BenchmarkHarness.run`` plus gate evaluation. The
default runner executes deterministic local golden missions. Tests may still
inject runners for boundary/property cases.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Self

from pydantic import ConfigDict, Field, model_validator

from sentinel.perf.bench.golden_missions import GOLDEN_MISSION_CLASSES, GoldenMission
from sentinel.perf.bench.golden_runners import run_golden_mission_iteration
from sentinel.perf.measure.latency_profiler import MissionPerformanceAggregate
from sentinel.shared.models import SentinelModel

__all__ = [
    "BenchmarkHarness",
    "BenchmarkReport",
    "GateRegression",
    "GateVerdict",
    "GoldenMissionIterationRunner",
]


GoldenMissionIterationRunner = Callable[[GoldenMission, int], int]


def _percentile(sorted_values: list[int], pct: float) -> int:
    """Compute nearest-rank percentile, matching ``LatencyProfiler``."""

    if not sorted_values:
        return 0
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    idx = int((pct / 100.0) * n + 0.5) - 1
    idx = max(0, min(idx, n - 1))
    return sorted_values[idx]


class BenchmarkReport(SentinelModel):
    """Structured result emitted by ``BenchmarkHarness.run``."""

    started_at: datetime
    completed_at: datetime | None
    iteration_count: int = Field(ge=0)
    per_mission: dict[str, MissionPerformanceAggregate]
    passed: bool

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def _validate_completion_shape(self) -> Self:
        if self.completed_at is None and self.passed:
            raise ValueError("BenchmarkReport cannot pass before completed_at is set.")
        return self

    def structured_pass_report(self) -> dict[str, Any]:
        """Return the Requirement 11.9 pass report shape.

        ``BenchmarkHarness.run`` sets ``passed`` only after
        ``evaluate_gates`` passes. This method exposes the structured shape
        only for completed, passing runs.
        """

        if self.completed_at is None or not self.passed:
            raise ValueError("structured pass report requires a completed passing run.")
        return {
            "run_timestamp": self.completed_at.isoformat(),
            "iteration_count": self.iteration_count,
            "per_class": {
                name: {
                    "iteration_count": aggregate.action_count,
                    "p50": aggregate.p50_wall_ms,
                    "p95": aggregate.p95_wall_ms,
                    "p99": aggregate.p99_wall_ms,
                }
                for name, aggregate in self.per_mission.items()
            },
        }


class GateRegression(SentinelModel):
    """Single p95/p99 regression entry from benchmark gate evaluation."""

    metric: str
    mission_class: str
    measured_ms: int = Field(ge=0)
    budget_ms: int = Field(ge=0)
    overage_percent: float = Field(ge=0)

    model_config = ConfigDict(extra="forbid", frozen=True)


class GateVerdict(SentinelModel):
    """Benchmark gate verdict for completed or in-progress reports."""

    passed: bool
    in_progress: bool = False
    p95_regressions: tuple[GateRegression, ...] = ()
    p99_regressions: tuple[GateRegression, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def _validate_verdict_shape(self) -> Self:
        if self.in_progress and (self.p95_regressions or self.p99_regressions):
            raise ValueError("In-progress GateVerdict cannot carry regressions.")
        if self.passed and (self.in_progress or self.p95_regressions or self.p99_regressions):
            raise ValueError("Passing GateVerdict cannot be in-progress or carry regressions.")
        return self


class BenchmarkHarness:
    """Runs golden missions and computes p50/p95/p99 per class."""

    P95_FAIL_TOLERANCE = 1.10
    P99_FAIL_TOLERANCE = 1.15

    def __init__(
        self,
        *,
        iteration_runner: GoldenMissionIterationRunner | None = None,
        golden_missions: tuple[GoldenMission, ...] = GOLDEN_MISSION_CLASSES,
    ) -> None:
        self._iteration_runner = iteration_runner or run_golden_mission_iteration
        self._golden_missions = golden_missions

    def run(self) -> BenchmarkReport:
        """Run every golden mission for at least its configured iterations."""

        started_at = datetime.now(timezone.utc)
        per_mission: dict[str, MissionPerformanceAggregate] = {}
        total_iterations = 0

        for mission in self._golden_missions:
            measurements: list[int] = []
            for iteration in range(mission.min_iterations):
                measured_ms = int(self._iteration_runner(mission, iteration))
                if measured_ms < 0:
                    raise ValueError(
                        "Benchmark iteration runner returned negative latency."
                    )
                measurements.append(measured_ms)

            total_iterations += len(measurements)
            sorted_measurements = sorted(measurements)
            per_mission[mission.name] = MissionPerformanceAggregate(
                mission_id=mission.name,
                action_count=len(sorted_measurements),
                p50_wall_ms=_percentile(sorted_measurements, 50),
                p95_wall_ms=_percentile(sorted_measurements, 95),
                p99_wall_ms=_percentile(sorted_measurements, 99),
            )

        completed_at = datetime.now(timezone.utc)
        completed_report = BenchmarkReport(
            started_at=started_at,
            completed_at=completed_at,
            iteration_count=total_iterations,
            per_mission=per_mission,
            passed=False,
        )
        verdict = self.evaluate_gates(completed_report)
        return completed_report.model_copy(update={"passed": verdict.passed})

    def evaluate_gates(self, report: BenchmarkReport) -> GateVerdict:
        """Evaluate p95/p99 gates for a benchmark report.

        Task 11.3 only evaluates already-produced reports. It never calls
        ``run`` or the injected iteration runner.
        """

        if report.completed_at is None:
            return GateVerdict(passed=False, in_progress=True)

        mission_by_name = {mission.name: mission for mission in self._golden_missions}
        p95_regressions: list[GateRegression] = []
        p99_regressions: list[GateRegression] = []

        for mission_name, aggregate in report.per_mission.items():
            mission = mission_by_name.get(mission_name)
            if mission is None:
                continue
            p95_overage = self._overage_percent(
                measured_ms=aggregate.p95_wall_ms,
                budget_ms=mission.p95_budget_ms,
            )
            p99_overage = self._overage_percent(
                measured_ms=aggregate.p99_wall_ms,
                budget_ms=mission.p99_budget_ms,
            )
            if p95_overage > 10.0:
                p95_regressions.append(
                    self._regression(
                        metric="p95",
                        mission=mission,
                        measured_ms=aggregate.p95_wall_ms,
                        budget_ms=mission.p95_budget_ms,
                    )
                )
            if p99_overage > 15.0:
                p99_regressions.append(
                    self._regression(
                        metric="p99",
                        mission=mission,
                        measured_ms=aggregate.p99_wall_ms,
                        budget_ms=mission.p99_budget_ms,
                    )
                )

        return GateVerdict(
            passed=not p95_regressions and not p99_regressions,
            p95_regressions=tuple(p95_regressions),
            p99_regressions=tuple(p99_regressions),
        )

    @staticmethod
    def _regression(
        *,
        metric: str,
        mission: GoldenMission,
        measured_ms: int,
        budget_ms: int,
    ) -> GateRegression:
        overage_percent = ((measured_ms - budget_ms) / budget_ms) * 100.0
        return GateRegression(
            metric=metric,
            mission_class=mission.name,
            measured_ms=measured_ms,
            budget_ms=budget_ms,
            overage_percent=overage_percent,
        )

    @staticmethod
    def _overage_percent(*, measured_ms: int, budget_ms: int) -> float:
        return ((measured_ms - budget_ms) / budget_ms) * 100.0
