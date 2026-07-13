from __future__ import annotations

import json
from pathlib import Path

from sentinel.operator.browser_cortex_deterministic_runner import run_browser_cortex_deterministic_baseline
from sentinel.operator.browser_cortex_search_entity_development import (
    BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION,
    BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION,
    build_browser_cortex_search_entity_development_corpus,
    build_browser_cortex_search_entity_development_corpus_v2,
    create_browser_cortex_pack1b_baseline_artifact,
    run_browser_cortex_search_entity_development_corpus,
    run_browser_cortex_search_entity_development_corpus_v2,
)


BASELINE_COMMIT = "afe40f8"
FROZEN_V1_HASH = "63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be"
PACK1_V1_HASH = "f93ef09ad583649a8c641d31b27b0ddc969c25431dc279cdd4a57aeb98dbc08b"


def test_pack1b_v2_corpus_is_separate_and_covers_required_generalization_axes() -> None:
    v1 = build_browser_cortex_search_entity_development_corpus(baseline_commit=BASELINE_COMMIT)
    v2 = build_browser_cortex_search_entity_development_corpus_v2(baseline_commit=BASELINE_COMMIT)

    assert v1.corpus_version == BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION
    assert v1.manifest_hash == PACK1_V1_HASH
    assert v2.corpus_version == BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION
    assert v2.manifest_hash != v1.manifest_hash
    assert len(v2.cases) >= 40
    assert {case.task_id for case in v2.cases}.isdisjoint({case.task_id for case in v1.cases})

    tags = {tag for case in v2.cases for tag in case.category_tags}
    required_tags = {
        "non_commerce",
        "localized_ui",
        "unknown_language",
        "alternate_search_control",
        "multiple_result_regions",
        "query_refinement",
        "weak_contaminated_results",
        "sponsored_results",
        "duplicate_variants",
        "price_range",
        "package_price",
        "locale_currency",
        "moq_constraint",
        "shipping_qualification",
        "availability_signal",
        "contradictory_price_currency",
        "pack1_unknown_price",
        "ambiguous_relevance",
        "negative_relevance",
        "synonym_relevance",
        "keyword_semantic_mismatch",
        "pagination",
        "infinite_scroll",
        "dynamic_result_replacement",
        "frames",
        "shadow_dom",
        "stale_controls",
        "confirmed_empty_results",
        "uncertain_empty_results",
    }
    assert required_tags.issubset(tags)


def test_pack1b_baseline_artifact_is_same_corpus_and_immutable(tmp_path: Path) -> None:
    artifact_path = create_browser_cortex_pack1b_baseline_artifact(
        output_path=tmp_path / "pack1b_baseline.json",
        run_root=tmp_path / "baseline_runs",
        workspace_root=tmp_path / "baseline_workspace",
        baseline_commit=BASELINE_COMMIT,
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["corpus_version"] == BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION
    assert artifact["runtime_commit"] == BASELINE_COMMIT
    assert artifact["executed_case_count"] >= 40
    assert artifact["not_run_case_count"] == 0
    assert artifact["manifest_hash"] == build_browser_cortex_search_entity_development_corpus_v2(
        baseline_commit=BASELINE_COMMIT
    ).manifest_hash
    assert artifact["baseline_artifact_hash"]
    assert len(artifact["case_results"]) == artifact["executed_case_count"]
    assert artifact["case_results"][0]["action_trace"]
    assert "fluidity_measurements" in artifact["case_results"][0]


def test_pack1b_v2_quality_and_fluidity_gates(tmp_path: Path) -> None:
    result = run_browser_cortex_search_entity_development_corpus_v2(
        run_root=tmp_path / "runs",
        workspace_root=tmp_path / "workspace",
        baseline_commit=BASELINE_COMMIT,
    )

    assert result.executed_case_count == len(result.case_results)
    assert result.executed_case_count >= 40
    assert result.not_run_case_count == 0
    assert result.metrics["pass_count"] == result.executed_case_count
    assert result.metrics["fail_count"] == 0
    assert result.metrics["relevance_precision"] >= 0.95
    assert result.metrics["relevance_recall"] >= 0.85
    assert result.metrics["claimed_entity_field_precision"] >= 0.95
    assert result.metrics["required_field_coverage"] >= 0.85
    assert result.metrics["unknown_preservation"] == 1.0
    assert result.metrics["duplicate_variant_resolution_accuracy"] >= 0.90
    assert result.metrics["constraint_classification_accuracy"] >= 0.90
    assert result.metrics["safe_alternate_trajectory_acceptance_rate"] == 1.0
    assert result.metrics["unsupported_claims"] == 0
    assert result.metrics["hard_boundary_violation_count"] == 0
    assert result.metrics["raw_secret_exposure"] == 0
    assert result.metrics["replay_side_effects"] == 0
    assert result.fluidity_metrics["useful_action_ratio"] >= 0.75
    assert result.fluidity_metrics["repeated_action_rate"] <= 0.05
    assert result.fluidity_metrics["recoverable_missions_terminate_honestly"] is True
    assert result.fluidity_metrics["repeated_identical_action_without_new_evidence"] == 0


def test_pack1b_preserves_frozen_and_pack1_v1(tmp_path: Path) -> None:
    frozen = run_browser_cortex_deterministic_baseline(
        run_root=tmp_path / "frozen_runs",
        workspace_root=tmp_path / "frozen_workspace",
        baseline_commit=BASELINE_COMMIT,
    )
    pack1 = run_browser_cortex_search_entity_development_corpus(
        run_root=tmp_path / "pack1_runs",
        workspace_root=tmp_path / "pack1_workspace",
        baseline_commit=BASELINE_COMMIT,
    )

    assert frozen.manifest_hash == FROZEN_V1_HASH
    assert frozen.metrics["pass_count"] == 24
    assert frozen.metrics["fail_count"] == 0
    assert pack1.manifest_hash == PACK1_V1_HASH
    assert pack1.metrics["pass_count"] == 8
    assert pack1.metrics["fail_count"] == 0
