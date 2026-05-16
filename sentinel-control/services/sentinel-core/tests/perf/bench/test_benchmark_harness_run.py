from __future__ import annotations

from datetime import datetime

from sentinel.perf.bench.golden_missions import GOLDEN_MISSION_CLASSES, GoldenMission
from sentinel.perf.bench.harness import BenchmarkHarness, BenchmarkReport


def test_benchmark_harness_run_completes_all_golden_missions() -> None:
    calls: list[tuple[str, int]] = []

    def runner(mission: GoldenMission, iteration: int) -> int:
        calls.append((mission.name, iteration))
        return 10 + iteration

    report = BenchmarkHarness(iteration_runner=runner).run()

    assert report.completed_at is not None
    assert report.passed is True
    assert report.iteration_count == sum(m.min_iterations for m in GOLDEN_MISSION_CLASSES)
    assert set(report.per_mission) == {mission.name for mission in GOLDEN_MISSION_CLASSES}
    assert len(calls) == report.iteration_count
    for mission in GOLDEN_MISSION_CLASSES:
        assert [call for call in calls if call[0] == mission.name] == [
            (mission.name, iteration) for iteration in range(mission.min_iterations)
        ]
        assert report.per_mission[mission.name].action_count == mission.min_iterations


def test_benchmark_harness_run_computes_p50_p95_p99_per_class() -> None:
    mission = GoldenMission(
        name="synthetic",
        min_iterations=30,
        p50_budget_ms=100,
        p95_budget_ms=200,
        p99_budget_ms=300,
        benchmarked_modules=("sentinel.agent.runtime",),
    )

    def runner(_mission: GoldenMission, iteration: int) -> int:
        return iteration + 1

    report = BenchmarkHarness(golden_missions=(mission,), iteration_runner=runner).run()
    aggregate = report.per_mission["synthetic"]

    assert aggregate.action_count == 30
    assert aggregate.p50_wall_ms == 15
    assert aggregate.p95_wall_ms == 29
    assert aggregate.p99_wall_ms == 30
    assert aggregate.p50_wall_ms <= aggregate.p95_wall_ms <= aggregate.p99_wall_ms


def test_benchmark_report_supports_in_progress_shape() -> None:
    report = BenchmarkReport(
        started_at=datetime(2026, 1, 1),
        completed_at=None,
        iteration_count=0,
        per_mission={},
        passed=False,
    )

    assert report.completed_at is None
    assert report.passed is False


def test_benchmark_harness_deterministic_runner_produces_stable_metrics() -> None:
    mission = GoldenMission(
        name="stable",
        min_iterations=30,
        p50_budget_ms=100,
        p95_budget_ms=200,
        p99_budget_ms=300,
        benchmarked_modules=("sentinel.agent.runtime",),
    )

    def runner(_mission: GoldenMission, iteration: int) -> int:
        return 7 if iteration < 29 else 11

    first = BenchmarkHarness(golden_missions=(mission,), iteration_runner=runner).run()
    second = BenchmarkHarness(golden_missions=(mission,), iteration_runner=runner).run()

    assert first.per_mission == second.per_mission
    assert first.iteration_count == second.iteration_count == 30


def test_benchmark_harness_default_runner_executes_golden_missions() -> None:
    """Full-lock requirement: run can execute deterministic local golden missions."""

    report = BenchmarkHarness().run()

    assert report.completed_at is not None
    assert report.passed is True
    assert report.structured_pass_report()["iteration_count"] == sum(
        mission.min_iterations for mission in GOLDEN_MISSION_CLASSES
    )
    for mission in GOLDEN_MISSION_CLASSES:
        aggregate = report.per_mission[mission.name]
        assert aggregate.action_count >= mission.min_iterations
        assert aggregate.p50_wall_ms <= aggregate.p95_wall_ms <= aggregate.p99_wall_ms


def test_benchmark_harness_run_exposes_pass_report_only_after_gates_pass() -> None:
    mission = GoldenMission(
        name="regression",
        min_iterations=30,
        p50_budget_ms=1,
        p95_budget_ms=1,
        p99_budget_ms=1,
        benchmarked_modules=("sentinel.agent.runtime",),
    )

    report = BenchmarkHarness(
        golden_missions=(mission,),
        iteration_runner=lambda *_: 100,
    ).run()

    assert report.completed_at is not None
    assert report.passed is False
    try:
        report.structured_pass_report()
    except ValueError as exc:
        assert "completed passing run" in str(exc)
    else:
        raise AssertionError("structured_pass_report must be gated by evaluate_gates")
