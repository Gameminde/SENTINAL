from __future__ import annotations

from datetime import datetime, timezone

from pytest import approx

from sentinel.perf.bench.golden_missions import GoldenMission
from sentinel.perf.bench.harness import BenchmarkHarness, BenchmarkReport
from sentinel.perf.measure.latency_profiler import MissionPerformanceAggregate


def _mission() -> GoldenMission:
    return GoldenMission(
        name="gate_test",
        min_iterations=30,
        p50_budget_ms=50,
        p95_budget_ms=100,
        p99_budget_ms=200,
        benchmarked_modules=("sentinel.agent.runtime",),
    )


def _report(*, p95: int, p99: int, completed: bool = True) -> BenchmarkReport:
    completed_at = datetime.now(timezone.utc) if completed else None
    return BenchmarkReport(
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        completed_at=completed_at,
        iteration_count=30,
        per_mission={
            "gate_test": MissionPerformanceAggregate(
                mission_id="gate_test",
                action_count=30,
                p50_wall_ms=40,
                p95_wall_ms=p95,
                p99_wall_ms=p99,
            )
        },
        passed=completed,
    )


def test_evaluate_gates_passes_completed_report_within_tolerance() -> None:
    verdict = BenchmarkHarness(golden_missions=(_mission(),), iteration_runner=lambda *_: 0).evaluate_gates(
        _report(p95=110, p99=230)
    )

    assert verdict.passed is True
    assert verdict.in_progress is False
    assert verdict.p95_regressions == ()
    assert verdict.p99_regressions == ()


def test_evaluate_gates_fails_p95_over_more_than_10_percent() -> None:
    verdict = BenchmarkHarness(golden_missions=(_mission(),), iteration_runner=lambda *_: 0).evaluate_gates(
        _report(p95=111, p99=200)
    )

    assert verdict.passed is False
    assert len(verdict.p95_regressions) == 1
    regression = verdict.p95_regressions[0]
    assert regression.metric == "p95"
    assert regression.mission_class == "gate_test"
    assert regression.measured_ms == 111
    assert regression.budget_ms == 100
    assert regression.overage_percent == approx(11.0)
    assert verdict.p99_regressions == ()


def test_evaluate_gates_fails_p99_over_more_than_15_percent() -> None:
    verdict = BenchmarkHarness(golden_missions=(_mission(),), iteration_runner=lambda *_: 0).evaluate_gates(
        _report(p95=100, p99=231)
    )

    assert verdict.passed is False
    assert verdict.p95_regressions == ()
    assert len(verdict.p99_regressions) == 1
    regression = verdict.p99_regressions[0]
    assert regression.metric == "p99"
    assert regression.mission_class == "gate_test"
    assert regression.measured_ms == 231
    assert regression.budget_ms == 200
    assert regression.overage_percent == approx(15.5)


def test_evaluate_gates_returns_in_progress_without_false_failure() -> None:
    verdict = BenchmarkHarness(golden_missions=(_mission(),), iteration_runner=lambda *_: 0).evaluate_gates(
        _report(p95=999, p99=999, completed=False)
    )

    assert verdict.passed is False
    assert verdict.in_progress is True
    assert verdict.p95_regressions == ()
    assert verdict.p99_regressions == ()


def test_evaluate_gates_does_not_execute_benchmarks() -> None:
    def runner(_mission: GoldenMission, _iteration: int) -> int:
        raise AssertionError("evaluate_gates must not run benchmark iterations")

    verdict = BenchmarkHarness(golden_missions=(_mission(),), iteration_runner=runner).evaluate_gates(
        _report(p95=100, p99=200)
    )

    assert verdict.passed is True
