from __future__ import annotations

from pydantic import ValidationError

from sentinel.perf.bench.golden_missions import (
    GOLDEN_MISSION_BY_NAME,
    GOLDEN_MISSION_CLASSES,
    GoldenMission,
)

EXPECTED_BUDGETS = {
    "startup": (150, 400, 800),
    "single_tool": (200, 500, 1000),
    "multi_tool": (400, 1000, 2000),
    "browser_heavy": (800, 2000, 4000),
}


def test_11_5_golden_mission_names_match_spec() -> None:
    missions = {mission.name: mission for mission in GOLDEN_MISSION_CLASSES}

    assert tuple(missions) == ("startup", "single_tool", "multi_tool", "browser_heavy")


def test_11_5_golden_mission_min_iterations_meet_floor() -> None:
    assert all(mission.min_iterations >= 30 for mission in GOLDEN_MISSION_CLASSES)


def test_11_5_golden_mission_budget_constants_match_design() -> None:
    missions = {mission.name: mission for mission in GOLDEN_MISSION_CLASSES}

    assert set(missions) == set(EXPECTED_BUDGETS)
    for mission_name, expected in EXPECTED_BUDGETS.items():
        mission = missions[mission_name]
        assert (
            mission.p50_budget_ms,
            mission.p95_budget_ms,
            mission.p99_budget_ms,
        ) == expected


def test_11_5_golden_mission_lookup_matches_enumeration() -> None:
    missions = {mission.name: mission for mission in GOLDEN_MISSION_CLASSES}

    assert GOLDEN_MISSION_BY_NAME == missions


def test_golden_mission_budget_order_is_enforced() -> None:
    try:
        GoldenMission(
            name="bad_budget",
            min_iterations=30,
            p50_budget_ms=100,
            p95_budget_ms=90,
            p99_budget_ms=110,
            benchmarked_modules=("sentinel.agent.context_builder",),
        )
    except ValidationError as exc:
        assert "GoldenMission budgets must satisfy p50 <= p95 <= p99" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("invalid golden mission budget ordering was accepted")


def test_golden_mission_min_iterations_floor_is_enforced() -> None:
    try:
        GoldenMission(
            name="too_few_iterations",
            min_iterations=29,
            p50_budget_ms=100,
            p95_budget_ms=200,
            p99_budget_ms=300,
            benchmarked_modules=("sentinel.agent.context_builder",),
        )
    except ValidationError as exc:
        assert "greater than or equal to 30" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("min_iterations below 30 was accepted")
