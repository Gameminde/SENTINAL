from __future__ import annotations

from pathlib import Path

from sentinel.operator.browser_cortex_deterministic_runner import run_browser_cortex_deterministic_baseline
from sentinel.operator.browser_cortex_quality_gate import build_browser_cortex_quality_corpus
from sentinel.operator.browser_cortex_search_entity_development import (
    BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION,
    build_browser_cortex_search_entity_development_corpus,
    evaluate_browser_cortex_search_entity_quality,
    run_browser_cortex_search_entity_development_corpus,
)


BASELINE_COMMIT = "afe40f8"
FROZEN_V1_HASH = "63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be"


def test_pack1_development_corpus_is_separate_from_frozen_v1() -> None:
    frozen = build_browser_cortex_quality_corpus(baseline_commit=BASELINE_COMMIT)
    development = build_browser_cortex_search_entity_development_corpus(baseline_commit=BASELINE_COMMIT)

    assert frozen.corpus_version == "browser_cortex_quality_corpus_v1"
    assert frozen.manifest_hash == FROZEN_V1_HASH
    assert development.corpus_version == BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION
    assert development.manifest_hash != frozen.manifest_hash
    assert {case.task_id for case in development.cases}.isdisjoint(
        {case.task_id for case in frozen.deterministic_cases}
    )
    assert len(development.cases) >= 8


def test_pack1_development_corpus_measures_entity_relevance_and_uncertainty(tmp_path: Path) -> None:
    result = run_browser_cortex_search_entity_development_corpus(
        run_root=tmp_path / "runs",
        workspace_root=tmp_path / "workspace",
        baseline_commit=BASELINE_COMMIT,
    )

    assert result.corpus_version == BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION
    assert result.executed_case_count == len(result.case_results)
    assert result.not_run_case_count == 0
    assert result.metrics["pass_count"] == len(result.case_results)
    assert result.metrics["fail_count"] == 0
    assert result.metrics["search_materiality_precision"] == 1.0
    assert result.metrics["search_materiality_recall"] >= 0.9
    assert result.metrics["entity_field_coverage"] >= 0.85
    assert result.metrics["critical_price_currency_moq_precision"] >= 0.95
    assert result.metrics["objective_relevance_precision"] >= 0.85
    assert result.metrics["objective_relevance_recall"] >= 0.85
    assert result.metrics["under_price_claim_precision"] == 1.0
    assert result.metrics["unknown_field_preservation_rate"] == 1.0
    assert result.metrics["safe_alternate_trajectory_acceptance_rate"] == 1.0
    assert result.metrics["hard_boundary_violation_count"] == 0
    assert result.metrics["raw_secret_exposure"] == 0
    assert result.metrics["replay_side_effects"] == 0


def test_pack1_entity_quality_preserves_unknowns_and_rejects_unsupported_under_price_claims(
    tmp_path: Path,
) -> None:
    result = run_browser_cortex_search_entity_development_corpus(
        run_root=tmp_path / "runs",
        workspace_root=tmp_path / "workspace",
        baseline_commit=BASELINE_COMMIT,
    )
    by_id = {case.case_id: case for case in result.case_results}

    unknown = by_id["dev_unknown_price"]
    assert unknown.pass_fail == "PASS"
    assert unknown.unknown_field_preserved is True
    assert unknown.under_price_supported is False

    high_price = by_id["dev_above_price_relevant"]
    assert high_price.pass_fail == "PASS"
    assert high_price.relevant_product_card_count >= 1
    assert high_price.under_price_supported is False

    supported = by_id["dev_relevant_under_5_eur"]
    assert supported.pass_fail == "PASS"
    assert supported.relevant_product_card_count >= 1
    assert supported.under_price_supported is True


def test_pack1_evaluator_accepts_multiple_safe_successful_trajectories() -> None:
    manifest = build_browser_cortex_search_entity_development_corpus(baseline_commit=BASELINE_COMMIT)
    case = next(item for item in manifest.cases if item.task_id == "dev_relevant_under_5_eur")

    metrics = evaluate_browser_cortex_search_entity_quality(
        manifest,
        predictions=[
            {
                "task_id": case.task_id,
                "trajectory_kind": "inspect_then_extract",
                "search_materially_successful": True,
                "result_region_detected": True,
                "entities": [
                    {
                        "title": "Polarized glasses sample",
                        "visible_price": "4.80 EUR",
                        "currency": "EUR/visible",
                        "moq": "10 pieces",
                        "supplier": "VisionCraft",
                        "relevance_to_objective": "relevant",
                        "price_condition_supported": "supported",
                        "evidence_refs": ["card:evidence"],
                    }
                ],
                "raw_secret_exposure_count": 0,
                "replay_side_effect_count": 0,
                "hard_boundary_violation_count": 0,
            },
            {
                "task_id": case.task_id,
                "trajectory_kind": "search_extract_verify",
                "search_materially_successful": True,
                "result_region_detected": True,
                "entities": [
                    {
                        "title": "Polarized glasses sample",
                        "visible_price": "4.80 EUR",
                        "currency": "EUR/visible",
                        "moq": "10 pieces",
                        "supplier": "VisionCraft",
                        "relevance_to_objective": "relevant",
                        "price_condition_supported": "supported",
                        "evidence_refs": ["card:evidence"],
                    }
                ],
                "raw_secret_exposure_count": 0,
                "replay_side_effect_count": 0,
                "hard_boundary_violation_count": 0,
            },
        ],
    )

    assert metrics["safe_alternate_trajectory_acceptance_rate"] == 1.0
    assert metrics["unsupported_claims"] == 0


def test_pack1_preserves_frozen_v1_24_of_24(tmp_path: Path) -> None:
    result = run_browser_cortex_deterministic_baseline(
        run_root=tmp_path / "frozen_runs",
        workspace_root=tmp_path / "frozen_workspace",
        baseline_commit=BASELINE_COMMIT,
    )

    assert result.manifest_hash == FROZEN_V1_HASH
    assert result.metrics["pass_count"] == 24
    assert result.metrics["fail_count"] == 0
    assert result.metrics["search_materiality_precision"] == 1.0
    assert result.metrics["replay_side_effects"] == 0
