from __future__ import annotations

import pytest

from sentinel.perf.bench.golden_missions import GOLDEN_MISSION_CLASSES
from sentinel.perf.bench.hot_path_registry import (
    HOT_PATH_MODULES,
    HotPathCoverageError,
    HotPathModule,
    assert_hot_path_modules_are_benchmarked,
    hot_path_coverage_report,
)


def test_hot_path_registry_enumerates_phase_f_surfaces() -> None:
    modules = {entry.module_path: entry for entry in HOT_PATH_MODULES}

    assert modules["sentinel.agent.runtime"].surface == "decision_core"
    assert modules["sentinel.agent.context_builder"].surface == "context_building"
    assert modules["sentinel.agent.decision_frame"].surface == "prompt_frame_assembly"
    assert modules["sentinel.perf.hot_cold.receipt_index"].surface == "receipt_retrieval"
    assert all(entry.reason for entry in HOT_PATH_MODULES)


def test_hot_path_coverage_passes_for_declared_golden_missions() -> None:
    report = hot_path_coverage_report(
        hot_path_modules=HOT_PATH_MODULES,
        golden_missions=GOLDEN_MISSION_CLASSES,
    )

    assert report.passed is True
    assert report.missing_modules == ()
    assert_hot_path_modules_are_benchmarked()


def test_hot_path_ci_gate_fails_when_module_lacks_benchmark_entry() -> None:
    unbenchmarked = HotPathModule(
        module_path="sentinel.agent.new_hot_path",
        surface="decision_core",
        reason="test-only simulated hot-path addition",
    )

    report = hot_path_coverage_report(
        hot_path_modules=(*HOT_PATH_MODULES, unbenchmarked),
        golden_missions=GOLDEN_MISSION_CLASSES,
    )

    assert report.passed is False
    assert report.missing_modules == ("sentinel.agent.new_hot_path",)
    with pytest.raises(HotPathCoverageError, match="sentinel.agent.new_hot_path"):
        assert_hot_path_modules_are_benchmarked(
            hot_path_modules=(*HOT_PATH_MODULES, unbenchmarked),
            golden_missions=GOLDEN_MISSION_CLASSES,
        )
