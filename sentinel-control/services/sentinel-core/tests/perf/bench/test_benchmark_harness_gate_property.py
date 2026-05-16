# Feature: sentinel-performance-runtime-foundation, Property 14: Benchmark-gate semantics under completed runs
"""Property tests for benchmark gate semantics.

Validates: Requirements 11.2, 11.3, 11.4, 11.9.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hypothesis import given, settings
from hypothesis import strategies as st
from pytest import approx

from sentinel.perf.bench.golden_missions import GOLDEN_MISSION_CLASSES
from sentinel.perf.bench.harness import BenchmarkHarness, BenchmarkReport
from sentinel.perf.measure.latency_profiler import MissionPerformanceAggregate


def _completed_report(
    per_mission: dict[str, MissionPerformanceAggregate],
) -> BenchmarkReport:
    return BenchmarkReport(
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 1, 0, 1, tzinfo=timezone.utc),
        iteration_count=sum(aggregate.action_count for aggregate in per_mission.values()),
        per_mission=per_mission,
        passed=True,
    )


@st.composite
def _completed_reports(
    draw: st.DrawFn,
) -> tuple[BenchmarkReport, set[str], set[str]]:
    per_mission: dict[str, MissionPerformanceAggregate] = {}
    expected_p95_failures: set[str] = set()
    expected_p99_failures: set[str] = set()

    for mission in GOLDEN_MISSION_CLASSES:
        p95 = draw(st.integers(min_value=0, max_value=mission.p95_budget_ms * 2))
        raw_p99 = draw(st.integers(min_value=0, max_value=mission.p99_budget_ms * 2))
        p99 = max(p95, raw_p99)
        p95_overage = ((p95 - mission.p95_budget_ms) / mission.p95_budget_ms) * 100.0
        p99_overage = ((p99 - mission.p99_budget_ms) / mission.p99_budget_ms) * 100.0

        if p95_overage > 10.0:
            expected_p95_failures.add(mission.name)
        if p99_overage > 15.0:
            expected_p99_failures.add(mission.name)

        per_mission[mission.name] = MissionPerformanceAggregate(
            mission_id=mission.name,
            action_count=mission.min_iterations,
            p50_wall_ms=min(p95, p99),
            p95_wall_ms=p95,
            p99_wall_ms=p99,
        )

    return _completed_report(per_mission), expected_p95_failures, expected_p99_failures


@given(case=_completed_reports())
@settings(max_examples=200, deadline=None)
def test_benchmark_gate_property_completed_reports(
    case: tuple[BenchmarkReport, set[str], set[str]],
) -> None:
    """Completed reports fail exactly on >10% p95 and >15% p99 regressions."""

    report, expected_p95_failures, expected_p99_failures = case

    verdict = BenchmarkHarness(iteration_runner=lambda *_: 0).evaluate_gates(report)

    assert verdict.in_progress is False
    assert verdict.passed is (not expected_p95_failures and not expected_p99_failures)
    assert {regression.mission_class for regression in verdict.p95_regressions} == expected_p95_failures
    assert {regression.mission_class for regression in verdict.p99_regressions} == expected_p99_failures

    mission_by_name = {mission.name: mission for mission in GOLDEN_MISSION_CLASSES}
    for regression in (*verdict.p95_regressions, *verdict.p99_regressions):
        mission = mission_by_name[regression.mission_class]
        aggregate = report.per_mission[regression.mission_class]
        expected_measured = (
            aggregate.p95_wall_ms
            if regression.metric == "p95"
            else aggregate.p99_wall_ms
        )
        expected_budget = (
            mission.p95_budget_ms
            if regression.metric == "p95"
            else mission.p99_budget_ms
        )
        expected_overage = ((expected_measured - expected_budget) / expected_budget) * 100.0

        assert regression.metric in {"p95", "p99"}
        assert regression.measured_ms == expected_measured
        assert regression.budget_ms == expected_budget
        assert regression.overage_percent == approx(expected_overage)

    if verdict.passed:
        pass_report = report.structured_pass_report()
        assert pass_report["run_timestamp"] == report.completed_at.isoformat()
        assert pass_report["iteration_count"] == report.iteration_count
        assert set(pass_report["per_class"]) == {mission.name for mission in GOLDEN_MISSION_CLASSES}


@given(
    p95=st.integers(min_value=0, max_value=10_000),
    p99=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=100, deadline=None)
def test_benchmark_gate_property_in_progress_reports_wait(
    p95: int,
    p99: int,
) -> None:
    """In-progress reports return an in-progress verdict without false failures."""

    aggregate = MissionPerformanceAggregate(
        mission_id="startup",
        action_count=30,
        p50_wall_ms=min(p95, p99),
        p95_wall_ms=p95,
        p99_wall_ms=max(p95, p99),
    )
    report = BenchmarkReport(
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=None,
        iteration_count=30,
        per_mission={"startup": aggregate},
        passed=False,
    )

    verdict = BenchmarkHarness(iteration_runner=lambda *_: 0).evaluate_gates(report)

    assert verdict.passed is False
    assert verdict.in_progress is True
    assert verdict.p95_regressions == ()
    assert verdict.p99_regressions == ()
