from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from sentinel.operator.browser_cortex_deterministic_runner import (
    BROWSER_CORTEX_DETERMINISTIC_RUNNER_VERSION,
    BrowserCortexDeterministicCaseResult,
    BrowserCortexDeterministicCorpusRunResult,
    run_browser_cortex_deterministic_baseline,
)
from sentinel.operator.browser_cortex_quality_gate import build_browser_cortex_quality_corpus


BASELINE_COMMIT = "afe40f8"
MANIFEST_HASH = "63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be"


@pytest.fixture(scope="module")
def deterministic_baseline_result(request: pytest.FixtureRequest) -> BrowserCortexDeterministicCorpusRunResult:
    root = Path("C:/sbc") / uuid4().hex[:8]
    request.addfinalizer(lambda: shutil.rmtree(root, ignore_errors=True))
    return run_browser_cortex_deterministic_baseline(
        run_root=root / "runs",
        workspace_root=root / "workspace",
        baseline_commit=BASELINE_COMMIT,
    )


def test_deterministic_baseline_executes_all_24_cases_through_product_spine(
    deterministic_baseline_result: BrowserCortexDeterministicCorpusRunResult,
) -> None:
    result = deterministic_baseline_result

    assert result.corpus_version == "browser_cortex_quality_corpus_v1"
    assert result.manifest_hash == MANIFEST_HASH
    assert result.runtime_commit == BASELINE_COMMIT
    assert result.runner_version == BROWSER_CORTEX_DETERMINISTIC_RUNNER_VERSION
    assert result.executed_case_count == 24
    assert result.not_run_case_count == 0
    assert result.metrics["executed_case_coverage"] == 1.0
    assert len(result.case_results) == 24

    for case in result.case_results:
        assert case.status != "NOT_RUN"
        assert case.fixture_hash
        assert case.expected_labels_hash
        assert case.fixture_bundle_hash == result.fixture_bundle_hash
        assert case.selected_skill in {"browse_search", "extract", "finish"}
        assert case.action_trace
        assert case.pre_environment_state_hash
        assert case.post_environment_state_hash
        assert case.receipt_refs
        assert case.product_receipt_refs
        assert case.finalgate_result in {"accepted", "blocked"}
        assert case.replay_result["reexecuted_actions"] is False
        assert case.replay_result["receipt_writes_delta"] == 0


def test_manifest_labels_and_fixture_hashes_are_separate_and_stable(
    deterministic_baseline_result: BrowserCortexDeterministicCorpusRunResult,
) -> None:
    result = deterministic_baseline_result
    manifest = build_browser_cortex_quality_corpus(baseline_commit=BASELINE_COMMIT)

    assert result.manifest_hash == manifest.manifest_hash
    assert result.expected_labels_hash
    assert result.fixture_bundle_hash
    assert result.expected_labels_hash != result.fixture_bundle_hash
    assert result.baseline_commit == BASELINE_COMMIT
    assert result.runtime_commit == BASELINE_COMMIT


def test_fill_only_false_success_trap_executes_without_material_success(
    deterministic_baseline_result: BrowserCortexDeterministicCorpusRunResult,
) -> None:
    result = deterministic_baseline_result
    trap = result.case_by_id("det_fill_only_false_success")

    assert trap.status == "EXECUTED"
    assert "INPUT_WRITTEN" in trap.search_progress["states"]
    assert trap.search_progress["current_state"] == "UNCERTAIN"
    assert trap.search_progress["search_materially_successful"] is False
    assert trap.pass_fail == "PASS"
    assert result.metrics["fill_only_false_success"] == 0
    assert result.metrics["search_materiality_precision"] == 1.0


def test_missing_case_counts_as_not_run_instead_of_passed() -> None:
    result = BrowserCortexDeterministicCorpusRunResult(
        corpus_version="browser_cortex_quality_corpus_v1",
        manifest_hash=MANIFEST_HASH,
        baseline_commit=BASELINE_COMMIT,
        runtime_commit=BASELINE_COMMIT,
        runner_version=BROWSER_CORTEX_DETERMINISTIC_RUNNER_VERSION,
        expected_labels_hash="labels",
        fixture_bundle_hash="fixtures",
        case_results=(
            BrowserCortexDeterministicCaseResult(
                case_id="det_conventional_search_form",
                status="EXECUTED",
                pass_fail="PASS",
                failure_classification="",
                fixture_hash="fixture",
                fixture_bundle_hash="fixtures",
                expected_labels_hash="labels",
                mission_objective="Search products.",
                expected_semantic_outcome={"relevant": True},
                observed_search_control="input:search",
                selected_skill="browse_search",
                action_trace=("real_browser_control:real_browser.search",),
                pre_environment_state_hash="pre",
                post_environment_state_hash="post",
                search_progress={"current_state": "MATERIAL_SUCCESS", "search_materially_successful": True},
                result_region_observation={"detected": True},
                semantic_entities=(),
                recovery_attempts=(),
                receipt_refs=("receipt",),
                product_receipt_refs=("product_receipt",),
                finalgate_result="accepted",
                replay_result={"reexecuted_actions": False, "receipt_writes_delta": 0},
            ),
        ),
        expected_case_ids=("det_conventional_search_form", "det_fill_only_false_success"),
    )

    assert result.executed_case_count == 1
    assert result.not_run_case_count == 1
    assert result.metrics["executed_case_coverage"] == 0.5
    assert result.case_by_id("det_fill_only_false_success").status == "NOT_RUN"
    assert result.case_by_id("det_fill_only_false_success").pass_fail == "FAIL"
