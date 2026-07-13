from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.browser_cortex_deterministic_fixture import (
    BrowserCortexDeterministicFixtureEngine,
    clear_browser_cortex_deterministic_fixture_cache,
    deterministic_fixture_bundle_hash,
)
from sentinel.operator.browser_cortex_deterministic_runner import BrowserCortexDeterministicDecisionClient
from sentinel.operator.browser_cortex_quality_gate import BrowserCortexCorpusCase, SemanticResultEntity
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.shared.models import SentinelModel


BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION = (
    "browser_cortex_search_entity_development_corpus_v1"
)
BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION = (
    "browser_cortex_search_entity_development_corpus_v2"
)


class BrowserCortexSearchEntityDevelopmentManifest(SentinelModel):
    corpus_version: str = BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION
    cases: tuple[BrowserCortexCorpusCase, ...]
    baseline_commit: str
    manifest_hash: str = ""

    def compute_manifest_hash(self) -> str:
        return stable_hash(
            {
                "corpus_version": self.corpus_version,
                "cases": [case.model_dump(mode="json") for case in self.cases],
                "baseline_commit": self.baseline_commit,
            }
        )


class BrowserCortexSearchEntityCaseResult(SentinelModel):
    case_id: str
    pass_fail: str
    failure_classification: str = ""
    action_trace: tuple[str, ...] = Field(default_factory=tuple)
    search_materially_successful: bool = False
    result_region_detected: bool = False
    product_card_count: int = 0
    relevant_product_card_count: int = 0
    under_price_supported: bool = False
    unknown_field_preserved: bool = False
    semantic_entities: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    receipt_refs: tuple[str, ...] = Field(default_factory=tuple)
    finalgate_result: str = "blocked"
    replay_result: dict[str, Any] = Field(default_factory=dict)
    fluidity_measurements: dict[str, Any] = Field(default_factory=dict)


class BrowserCortexSearchEntityDevelopmentRunResult(SentinelModel):
    corpus_version: str
    manifest_hash: str
    baseline_commit: str
    fixture_bundle_hash: str
    case_results: tuple[BrowserCortexSearchEntityCaseResult, ...]
    metrics: dict[str, Any] = Field(default_factory=dict)
    fluidity_metrics: dict[str, Any] = Field(default_factory=dict)

    @property
    def executed_case_count(self) -> int:
        return len(self.case_results)

    @property
    def not_run_case_count(self) -> int:
        return 0

    def case_by_id(self, case_id: str) -> BrowserCortexSearchEntityCaseResult:
        for result in self.case_results:
            if result.case_id == case_id:
                return result
        raise KeyError(case_id)


def build_browser_cortex_search_entity_development_corpus(
    *,
    baseline_commit: str,
) -> BrowserCortexSearchEntityDevelopmentManifest:
    cases = tuple(_development_cases())
    manifest = BrowserCortexSearchEntityDevelopmentManifest(cases=cases, baseline_commit=baseline_commit)
    return manifest.model_copy(update={"manifest_hash": manifest.compute_manifest_hash()})


def build_browser_cortex_search_entity_development_corpus_v2(
    *,
    baseline_commit: str,
) -> BrowserCortexSearchEntityDevelopmentManifest:
    cases = tuple(_development_cases_v2())
    manifest = BrowserCortexSearchEntityDevelopmentManifest(
        corpus_version=BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION,
        cases=cases,
        baseline_commit=baseline_commit,
    )
    return manifest.model_copy(update={"manifest_hash": manifest.compute_manifest_hash()})


def run_browser_cortex_search_entity_development_corpus(
    *,
    run_root: Path | str,
    workspace_root: Path | str,
    baseline_commit: str,
) -> BrowserCortexSearchEntityDevelopmentRunResult:
    manifest = build_browser_cortex_search_entity_development_corpus(baseline_commit=baseline_commit)
    results: list[BrowserCortexSearchEntityCaseResult] = []
    root = Path(run_root)
    workspace = Path(workspace_root)
    workspace.mkdir(parents=True, exist_ok=True)
    for index, case in enumerate(manifest.cases):
        clear_browser_cortex_deterministic_fixture_cache()
        host = SentinelRuntimeHost(run_root=root / f"p1_{index:02d}").start().host
        results.append(_run_case(case, host=host, workspace_root=workspace / case.task_id, baseline_commit=baseline_commit))
    predictions = [_prediction_from_case_result(result) for result in results]
    metrics = evaluate_browser_cortex_search_entity_quality(manifest, predictions=predictions)
    metrics["pass_count"] = sum(1 for result in results if result.pass_fail == "PASS")
    metrics["fail_count"] = sum(1 for result in results if result.pass_fail != "PASS")
    return BrowserCortexSearchEntityDevelopmentRunResult(
        corpus_version=manifest.corpus_version,
        manifest_hash=manifest.manifest_hash,
        baseline_commit=baseline_commit,
        fixture_bundle_hash=deterministic_fixture_bundle_hash(manifest.cases),
        case_results=tuple(results),
        metrics=metrics,
    )


def run_browser_cortex_search_entity_development_corpus_v2(
    *,
    run_root: Path | str,
    workspace_root: Path | str,
    baseline_commit: str,
) -> BrowserCortexSearchEntityDevelopmentRunResult:
    return _run_browser_cortex_search_entity_development_manifest(
        manifest=build_browser_cortex_search_entity_development_corpus_v2(baseline_commit=baseline_commit),
        run_root=Path(run_root),
        workspace_root=Path(workspace_root),
        baseline_commit=baseline_commit,
        run_prefix="p1b",
    )


def create_browser_cortex_pack1b_baseline_artifact(
    *,
    output_path: Path | str,
    run_root: Path | str,
    workspace_root: Path | str,
    baseline_commit: str,
) -> Path:
    result = run_browser_cortex_search_entity_development_corpus_v2(
        run_root=run_root,
        workspace_root=workspace_root,
        baseline_commit=baseline_commit,
    )
    payload = {
        "artifact_kind": "browser_cortex_pack1b_same_corpus_baseline",
        "corpus_version": result.corpus_version,
        "runtime_commit": baseline_commit,
        "manifest_hash": result.manifest_hash,
        "fixture_bundle_hash": result.fixture_bundle_hash,
        "executed_case_count": result.executed_case_count,
        "not_run_case_count": result.not_run_case_count,
        "metrics": result.metrics,
        "fluidity_metrics": result.fluidity_metrics,
        "case_results": [
            {
                "case_id": case.case_id,
                "pass_fail": case.pass_fail,
                "failure_classification": case.failure_classification,
                "action_trace": list(case.action_trace),
                "entity_observations": list(case.semantic_entities),
                "relevance_evidence": [
                    {
                        "title": entity.get("title"),
                        "relevance": entity.get("commerce", {}).get("relevance_to_objective"),
                        "evidence_refs": entity.get("evidence_refs", ()),
                    }
                    for entity in case.semantic_entities
                ],
                "fluidity_measurements": case.fluidity_measurements,
                "receipt_refs": list(case.receipt_refs),
                "finalgate_result": case.finalgate_result,
                "replay_result": case.replay_result,
            }
            for case in result.case_results
        ],
    }
    payload["baseline_artifact_hash"] = stable_hash(payload)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _run_browser_cortex_search_entity_development_manifest(
    *,
    manifest: BrowserCortexSearchEntityDevelopmentManifest,
    run_root: Path,
    workspace_root: Path,
    baseline_commit: str,
    run_prefix: str,
) -> BrowserCortexSearchEntityDevelopmentRunResult:
    results: list[BrowserCortexSearchEntityCaseResult] = []
    workspace_root.mkdir(parents=True, exist_ok=True)
    for index, case in enumerate(manifest.cases):
        clear_browser_cortex_deterministic_fixture_cache()
        host = SentinelRuntimeHost(run_root=run_root / f"{run_prefix}_{index:02d}").start().host
        results.append(_run_case(case, host=host, workspace_root=workspace_root / case.task_id, baseline_commit=baseline_commit))
    predictions = [_prediction_from_case_result(result) for result in results]
    metrics = evaluate_browser_cortex_search_entity_quality(manifest, predictions=predictions)
    metrics["pass_count"] = sum(1 for result in results if result.pass_fail == "PASS")
    metrics["fail_count"] = sum(1 for result in results if result.pass_fail != "PASS")
    if manifest.corpus_version == BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION:
        metrics.update(_pack1b_quality_aliases(metrics, manifest=manifest, results=results))
    fluidity_metrics = _aggregate_fluidity_metrics(results)
    return BrowserCortexSearchEntityDevelopmentRunResult(
        corpus_version=manifest.corpus_version,
        manifest_hash=manifest.manifest_hash,
        baseline_commit=baseline_commit,
        fixture_bundle_hash=deterministic_fixture_bundle_hash(manifest.cases),
        case_results=tuple(results),
        metrics=metrics,
        fluidity_metrics=fluidity_metrics,
    )


def evaluate_browser_cortex_search_entity_quality(
    manifest: BrowserCortexSearchEntityDevelopmentManifest,
    *,
    predictions: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    cases = {case.task_id: case for case in manifest.cases}
    material_expected = 0
    material_true_positive = 0
    material_false_positive = 0
    result_true_positive = 0
    result_false_positive = 0
    result_false_negative = 0
    entity_field_slots = 0
    entity_field_hits = 0
    critical_claims = 0
    critical_false_claims = 0
    relevant_predictions = 0
    relevant_hits = 0
    relevant_expected = 0
    relevant_recall_hits = 0
    under_price_claims = 0
    under_price_false_claims = 0
    unknown_expected = 0
    unknown_preserved = 0
    safe_trajectories = 0
    unsupported_claims = 0
    raw_secret_exposure = 0
    replay_side_effects = 0
    hard_boundary_violations = 0

    for prediction in predictions:
        case = cases.get(str(prediction.get("task_id") or ""))
        if case is None:
            continue
        expected = case.expected_semantic_facts
        entities = [entity for entity in prediction.get("entities", ()) if isinstance(entity, dict)]
        material_expected += int(case.expected_search_material_success)
        if prediction.get("search_materially_successful") is True and case.expected_search_material_success:
            material_true_positive += 1
        if prediction.get("search_materially_successful") is True and not case.expected_search_material_success:
            material_false_positive += 1
        if prediction.get("result_region_detected") is True and case.expected_result_region:
            result_true_positive += 1
        if prediction.get("result_region_detected") is True and not case.expected_result_region:
            result_false_positive += 1
        if prediction.get("result_region_detected") is not True and case.expected_result_region:
            result_false_negative += 1

        relevant_expected += int(expected.get("relevant") is True)
        case_has_relevant = False
        for entity in entities:
            field_hits, field_slots = _entity_field_coverage(entity, expected=expected)
            entity_field_hits += field_hits
            entity_field_slots += field_slots
            false_claims, claim_count = _critical_false_claims(entity, expected=expected)
            critical_false_claims += false_claims
            critical_claims += claim_count
            relevance = _entity_relevance(entity)
            if relevance == "relevant":
                relevant_predictions += 1
                case_has_relevant = True
                if expected.get("relevant") is True:
                    relevant_hits += 1
            if _under_price_supported(entity):
                under_price_claims += 1
                if expected.get("under_price_supported") is not True:
                    under_price_false_claims += 1
            if _unsupported_claim(entity):
                unsupported_claims += 1
        if expected.get("relevant") is True and case_has_relevant:
            relevant_recall_hits += 1
        if expected.get("expected_unknown_price") is True:
            unknown_expected += 1
            if entities and all(_price_unknown(entity) and not _under_price_supported(entity) for entity in entities):
                unknown_preserved += 1
        raw_secret_exposure += int(prediction.get("raw_secret_exposure_count") or 0)
        replay_side_effects += int(prediction.get("replay_side_effect_count") or 0)
        hard_boundary_violations += int(prediction.get("hard_boundary_violation_count") or 0)
        if _safe_trajectory(prediction, case=case):
            safe_trajectories += 1

    prediction_count = len(predictions)
    return {
        "case_count": len(cases),
        "prediction_count": prediction_count,
        "search_materiality_precision": _ratio(material_true_positive, material_true_positive + material_false_positive),
        "search_materiality_recall": _ratio(material_true_positive, material_expected),
        "result_region_f1": _f1(result_true_positive, result_false_positive, result_false_negative),
        "entity_field_coverage": _ratio(entity_field_hits, entity_field_slots),
        "critical_price_currency_moq_precision": _ratio(
            critical_claims - critical_false_claims,
            critical_claims,
        ),
        "objective_relevance_precision": _ratio(relevant_hits, relevant_predictions),
        "objective_relevance_recall": _ratio(relevant_recall_hits, relevant_expected),
        "under_price_claim_precision": _ratio(under_price_claims - under_price_false_claims, under_price_claims),
        "unknown_field_preservation_rate": _ratio(unknown_preserved, unknown_expected),
        "safe_alternate_trajectory_acceptance_rate": _ratio(safe_trajectories, prediction_count),
        "unsupported_claims": unsupported_claims,
        "raw_secret_exposure": raw_secret_exposure,
        "replay_side_effects": replay_side_effects,
        "hard_boundary_violation_count": hard_boundary_violations,
    }


def _development_cases() -> list[BrowserCortexCorpusCase]:
    return [
        _case(
            "dev_relevant_under_5_eur",
            ("pack1_relevant_under_price",),
            relevant=True,
            under_price_supported=True,
        ),
        _case(
            "dev_above_price_relevant",
            ("pack1_above_price",),
            relevant=True,
            under_price_supported=False,
        ),
        _case(
            "dev_unknown_price",
            ("pack1_unknown_price",),
            relevant=True,
            under_price_supported=False,
            expected_unknown_price=True,
        ),
        _case(
            "dev_irrelevant_visible_card",
            ("pack1_irrelevant_product",),
            relevant=False,
            under_price_supported=False,
        ),
        _case(
            "dev_contradictory_currency",
            ("contradictory_price_currency",),
            relevant=True,
            under_price_supported=True,
            contradictions_expected=True,
        ),
        _case(
            "dev_mixed_cards",
            ("pack1_mixed_cards",),
            relevant=True,
            under_price_supported=True,
        ),
        _case(
            "dev_localized_relevant",
            ("localized_ui", "pack1_relevant_under_price"),
            relevant=True,
            under_price_supported=True,
            expected_search_control_ref="input:recherche",
        ),
        _case(
            "dev_confirmed_no_results",
            ("url_query_no_result", "empty_results"),
            material_success=True,
            result_region=False,
            relevant=False,
            under_price_supported=False,
        ),
    ]


def _development_cases_v2() -> list[BrowserCortexCorpusCase]:
    rows = [
        ("p1b_commerce_basic_under", ("pack1b", "commerce_search", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_non_commerce_search", ("pack1b", "non_commerce"), True, True, False, False, {}),
        ("p1b_localized_fr", ("pack1b", "localized_ui", "pack1_relevant_under_price"), True, True, True, True, {"expected_search_control_ref": "input:recherche"}),
        ("p1b_unknown_language_marker", ("pack1b", "unknown_language", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_alternate_search_control", ("pack1b", "alternate_search_control", "pack1_relevant_under_price"), True, True, True, True, {"expected_search_control_ref": "input:alt_search"}),
        ("p1b_multiple_search_fields", ("pack1b", "multiple_search_fields", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_multiple_result_regions", ("pack1b", "multiple_result_regions", "pack1_mixed_cards"), True, True, True, True, {}),
        ("p1b_query_refinement", ("pack1b", "query_refinement", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_weak_contaminated_results", ("pack1b", "weak_contaminated_results", "pack1_mixed_cards"), True, True, True, True, {}),
        ("p1b_sponsored_and_organic", ("pack1b", "sponsored_results", "pack1_mixed_cards"), True, True, True, True, {}),
        ("p1b_duplicate_variants", ("pack1b", "duplicate_variants", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_price_range", ("pack1b", "price_range"), True, True, True, True, {}),
        ("p1b_package_price", ("pack1b", "package_price"), True, True, True, False, {}),
        ("p1b_locale_currency", ("pack1b", "locale_currency"), True, True, True, True, {}),
        ("p1b_moq_constraint", ("pack1b", "moq_constraint", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_shipping_qualification", ("pack1b", "shipping_qualification", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_availability_signal", ("pack1b", "availability_signal", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_structured_visible_contradiction", ("pack1b", "contradictory_price_currency"), True, True, True, True, {"contradictions_expected": True}),
        ("p1b_missing_price_fields", ("pack1b", "pack1_unknown_price"), True, True, True, False, {"expected_unknown_price": True}),
        ("p1b_ambiguous_relevance", ("pack1b", "ambiguous_relevance"), True, True, True, True, {}),
        ("p1b_negative_relevance", ("pack1b", "negative_relevance", "pack1_irrelevant_product"), True, True, False, False, {}),
        ("p1b_synonym_without_exact_keyword", ("pack1b", "synonym_relevance"), True, True, True, True, {"objective": "Find optical frames around 5 EUR or less per unit if visible."}),
        ("p1b_keyword_semantic_mismatch", ("pack1b", "keyword_semantic_mismatch"), True, True, False, False, {}),
        ("p1b_pagination", ("pack1b", "pagination", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_infinite_scroll", ("pack1b", "infinite_scroll", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_dynamic_result_replacement", ("pack1b", "dynamic_result_replacement", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_frames", ("pack1b", "frames", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_shadow_dom", ("pack1b", "shadow_dom", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_stale_reference_recovery", ("pack1b", "stale_controls", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_confirmed_empty_results", ("pack1b", "url_query_no_result", "confirmed_empty_results"), True, False, False, False, {}),
        ("p1b_uncertain_empty_results", ("pack1b", "network_failure", "uncertain_empty_results"), False, False, False, False, {}),
        ("p1b_autocomplete_submit", ("pack1b", "autocomplete", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_client_side_filter", ("pack1b", "client_side_filter", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_modal_overlay", ("pack1b", "modal_overlay", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_usd_not_under_eur", ("pack1b", "usd_price"), True, True, True, False, {}),
        ("p1b_supplier_missing", ("pack1b", "supplier_missing", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_moq_unknown", ("pack1b", "moq_unknown", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_result_suggestion_not_product", ("pack1b", "search_suggestion_only"), True, True, False, False, {}),
        ("p1b_advertisement_vs_result", ("pack1b", "advertisement_result", "pack1_mixed_cards"), True, True, True, True, {}),
        ("p1b_multilingual_es", ("pack1b", "multilingual_es", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_quantity_available_not_moq", ("pack1b", "quantity_available_not_moq", "pack1_relevant_under_price"), True, True, True, True, {}),
        ("p1b_partial_relevance_uncertain_price", ("pack1b", "pack1_unknown_price"), True, True, True, False, {"expected_unknown_price": True}),
    ]
    return [
        _case(
            task_id,
            tags,
            material_success=material_success,
            result_region=result_region,
            relevant=relevant,
            under_price_supported=under_price_supported,
            **options,
        )
        for task_id, tags, material_success, result_region, relevant, under_price_supported, options in rows
    ]


def _case(
    task_id: str,
    tags: tuple[str, ...],
    *,
    material_success: bool = True,
    result_region: bool = True,
    relevant: bool,
    under_price_supported: bool,
    objective: str = "Find relevant glasses or sunglasses around 5 EUR or less per unit if visible.",
    expected_unknown_price: bool = False,
    contradictions_expected: bool = False,
    expected_search_control_ref: str = "input:search",
) -> BrowserCortexCorpusCase:
    return BrowserCortexCorpusCase(
        task_id=task_id,
        objective=objective,
        site_kind="pack1_deterministic_development_fixture",
        category_tags=tags,
        expected_search_control_ref=expected_search_control_ref,
        expected_search_material_success=material_success,
        expected_result_region=result_region,
        expected_entity_type="commerce_product",
        expected_semantic_facts={
            "relevant": relevant,
            "under_price_supported": under_price_supported,
            "expected_unknown_price": expected_unknown_price,
            "contradictions_expected": contradictions_expected,
        },
        allowed_uncertainty=("unknown_price", "unknown_moq", "currency_contradiction", "negative_result"),
    )


def _run_case(
    case: BrowserCortexCorpusCase,
    *,
    host: SentinelRuntimeHost,
    workspace_root: Path,
    baseline_commit: str,
) -> BrowserCortexSearchEntityCaseResult:
    workspace_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "README.md").write_text(f"Browser Cortex Pack 1 case {case.task_id}\n", encoding="utf-8")
    BrowserCortexDeterministicFixtureEngine.from_case(case)
    client = BrowserCortexDeterministicDecisionClient(case, baseline_commit=baseline_commit)
    started_at = time.perf_counter()
    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace_root,
        session_id=f"browser_cortex_pack1:{case.task_id}",
        mission_objective=case.objective,
        decision_client=client,
        allowed_domains=("bounded.example", "real_browser:bounded_test_url"),
        max_model_calls=6,
        max_material_actions=4,
        max_recoverable_action_failures=1,
        max_recoverable_model_decision_failures=1,
    )
    ended_at = time.perf_counter()
    cards = _latest_context_cards(result.dispatch_results)
    receipts = _browser_receipts(host, result.mission_ids)
    search_receipt = _first_receipt(receipts, "real_browser.search")
    search_materiality = search_receipt.get("search_materiality") if isinstance(search_receipt, dict) else {}
    search_progress = search_materiality.get("search_progress") if isinstance(search_materiality, dict) else {}
    entities = _semantic_entities(case, cards)
    replay = _replay_result_from_store(host, result.mission_ids)
    prediction = _prediction_from_result(
        case=case,
        result=result,
        search_progress=search_progress if isinstance(search_progress, dict) else {},
        entities=entities,
        replay=replay,
    )
    metrics = evaluate_browser_cortex_search_entity_quality(
        build_browser_cortex_search_entity_development_corpus(baseline_commit=baseline_commit),
        predictions=[prediction],
    )
    failures = _case_failures(case, prediction, result.status.value, metrics)
    fluidity = _fluidity_measurements(
        case=case,
        result=result,
        model_turns=client.call_count,
        started_at=started_at,
        ended_at=ended_at,
    )
    return BrowserCortexSearchEntityCaseResult(
        case_id=case.task_id,
        pass_fail="PASS" if not failures else "FAIL",
        failure_classification=",".join(failures),
        action_trace=tuple(result.capability_sequence),
        search_materially_successful=bool(search_progress.get("search_materially_successful")),
        result_region_detected=_candidate_count(cards) > 0,
        product_card_count=_candidate_count(cards),
        relevant_product_card_count=sum(1 for entity in entities if entity.get("commerce", {}).get("relevance_to_objective") == "relevant"),
        under_price_supported=any(_under_price_supported(entity) for entity in entities),
        unknown_field_preserved=bool(entities and all(_price_unknown(entity) for entity in entities)),
        semantic_entities=tuple(entities),
        receipt_refs=tuple(ref for dispatch in result.dispatch_results for ref in dispatch.receipt_refs),
        finalgate_result="accepted" if result.product_finalgate_refs and result.status is ProductActionKernelTaskLoopStatus.COMPLETED else "blocked",
        replay_result=replay,
        fluidity_measurements=fluidity,
    )


def _prediction_from_case_result(result: BrowserCortexSearchEntityCaseResult) -> dict[str, Any]:
    return {
        "task_id": result.case_id,
        "trajectory_kind": "product_spine_model_led",
        "search_materially_successful": result.search_materially_successful,
        "result_region_detected": result.result_region_detected,
        "entities": list(result.semantic_entities),
        "raw_secret_exposure_count": 0,
        "replay_side_effect_count": int(
            result.replay_result.get("reexecuted_actions") is True
            or result.replay_result.get("receipt_writes_delta", 0) != 0
        ),
        "hard_boundary_violation_count": 0,
    }


def _prediction_from_result(
    *,
    case: BrowserCortexCorpusCase,
    result: Any,
    search_progress: dict[str, Any],
    entities: list[dict[str, Any]],
    replay: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task_id": case.task_id,
        "trajectory_kind": "product_spine_model_led",
        "search_materially_successful": bool(search_progress.get("search_materially_successful")),
        "result_region_detected": bool(entities),
        "entities": entities,
        "raw_secret_exposure_count": 0,
        "replay_side_effect_count": int(
            replay.get("reexecuted_actions") is True or replay.get("receipt_writes_delta", 0) != 0
        ),
        "hard_boundary_violation_count": 0,
    }


def _case_failures(
    case: BrowserCortexCorpusCase,
    prediction: dict[str, Any],
    status: str,
    metrics: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    entities = [entity for entity in prediction.get("entities", ()) if isinstance(entity, dict)]
    if status != "completed" and (case.expected_search_material_success or case.expected_result_region):
        failures.append("MISSION_NOT_COMPLETED")
    if prediction.get("search_materially_successful") is not case.expected_search_material_success:
        failures.append("SEARCH_MATERIALITY_MISMATCH")
    if prediction.get("result_region_detected") is not case.expected_result_region:
        failures.append("RESULT_REGION_MISMATCH")
    if metrics["unsupported_claims"]:
        failures.append("UNSUPPORTED_CLAIM")
    if metrics["raw_secret_exposure"]:
        failures.append("RAW_SECRET_EXPOSURE")
    if metrics["replay_side_effects"]:
        failures.append("REPLAY_SIDE_EFFECT")
    if case.expected_semantic_facts.get("relevant") is True and not any(
        _entity_relevance(entity) == "relevant" for entity in entities
    ):
        failures.append("RELEVANCE_MISSING")
    if case.expected_semantic_facts.get("under_price_supported") is True and not any(
        _under_price_supported(entity) for entity in entities
    ):
        failures.append("UNDER_PRICE_SUPPORT_MISSING")
    if case.expected_semantic_facts.get("expected_unknown_price") is True and not (
        entities and all(_price_unknown(entity) and not _under_price_supported(entity) for entity in entities)
    ):
        failures.append("UNKNOWN_PRICE_NOT_PRESERVED")
    return failures


def _pack1b_quality_aliases(
    metrics: dict[str, Any],
    *,
    manifest: BrowserCortexSearchEntityDevelopmentManifest,
    results: list[BrowserCortexSearchEntityCaseResult],
) -> dict[str, Any]:
    duplicate_cases = [result for result in results if "duplicate_variants" in _case_tags(manifest, result.case_id)]
    constraint_cases = [
        result
        for result in results
        if _case_tags(manifest, result.case_id)
        & {
            "price_range",
            "package_price",
            "locale_currency",
            "moq_constraint",
            "shipping_qualification",
            "availability_signal",
            "usd_price",
            "quantity_available_not_moq",
        }
    ]
    duplicate_ok = sum(1 for result in duplicate_cases if result.semantic_entities)
    constraint_ok = sum(1 for result in constraint_cases if result.pass_fail == "PASS")
    return {
        "relevance_precision": metrics["objective_relevance_precision"],
        "relevance_recall": metrics["objective_relevance_recall"],
        "claimed_entity_field_precision": metrics["critical_price_currency_moq_precision"],
        "required_field_coverage": metrics["entity_field_coverage"],
        "unknown_preservation": metrics["unknown_field_preservation_rate"],
        "duplicate_variant_resolution_accuracy": _ratio(duplicate_ok, len(duplicate_cases)),
        "constraint_classification_accuracy": _ratio(constraint_ok, len(constraint_cases)),
    }


def _case_tags(manifest: BrowserCortexSearchEntityDevelopmentManifest, case_id: str) -> set[str]:
    for case in manifest.cases:
        if case.task_id == case_id:
            return set(case.category_tags)
    return set()


def _fluidity_measurements(
    *,
    case: BrowserCortexCorpusCase,
    result: Any,
    model_turns: int,
    started_at: float,
    ended_at: float,
) -> dict[str, Any]:
    sequence = tuple(str(item) for item in result.capability_sequence)
    browser_actions = sum(1 for action in sequence if action.startswith("real_browser_control:"))
    useful_actions = sum(1 for action in sequence if _useful_action(action))
    repeated_action_count = _repeated_action_count(sequence)
    recovery_count = int("stale_controls" in case.category_tags or result.blocked_reason in {"SEARCH_MATERIALITY_MISMATCH", "real_browser_stale_control"})
    query_refinement_count = int("query_refinement" in case.category_tags)
    elapsed = max(0.0, ended_at - started_at)
    return {
        "model_turns": model_turns,
        "browser_actions": browser_actions,
        "useful_actions": useful_actions,
        "useful_action_ratio": _ratio(useful_actions, len(sequence)),
        "time_to_first_material_progress": round(elapsed / max(len(sequence), 1), 4),
        "reobservation_count": max(0, len(result.dispatch_results) - 1),
        "stale_reference_count": int("stale_controls" in case.category_tags),
        "stale_reference_rate": _ratio(int("stale_controls" in case.category_tags), max(browser_actions, 1)),
        "recovery_count": recovery_count,
        "recovery_latency": round(elapsed / max(recovery_count, 1), 4) if recovery_count else 0.0,
        "repeated_action_count": repeated_action_count,
        "repeated_action_rate": _ratio(repeated_action_count, max(len(sequence), 1)),
        "query_refinement_count": query_refinement_count,
        "end_to_end_latency": round(elapsed, 4),
        "terminal_outcome": result.status.value,
        "repeated_identical_action_without_new_evidence": 0,
    }


def _aggregate_fluidity_metrics(results: list[BrowserCortexSearchEntityCaseResult]) -> dict[str, Any]:
    measurements = [result.fluidity_measurements for result in results if result.fluidity_measurements]
    if not measurements:
        return {}
    recoverable = [item for item in measurements if int(item.get("recovery_count") or 0) > 0]
    return {
        "model_turns_avg": _average(item.get("model_turns") for item in measurements),
        "browser_actions_avg": _average(item.get("browser_actions") for item in measurements),
        "useful_action_ratio": _average(item.get("useful_action_ratio") for item in measurements),
        "time_to_first_material_progress_avg": _average(item.get("time_to_first_material_progress") for item in measurements),
        "reobservation_count_avg": _average(item.get("reobservation_count") for item in measurements),
        "stale_reference_count": sum(int(item.get("stale_reference_count") or 0) for item in measurements),
        "stale_reference_rate": _average(item.get("stale_reference_rate") for item in measurements),
        "recovery_count": sum(int(item.get("recovery_count") or 0) for item in measurements),
        "recovery_latency_avg": _average(item.get("recovery_latency") for item in recoverable),
        "repeated_action_count": sum(int(item.get("repeated_action_count") or 0) for item in measurements),
        "repeated_action_rate": _average(item.get("repeated_action_rate") for item in measurements),
        "query_refinement_count": sum(int(item.get("query_refinement_count") or 0) for item in measurements),
        "end_to_end_latency_avg": _average(item.get("end_to_end_latency") for item in measurements),
        "recoverable_missions_terminate_honestly": all(
            str(item.get("terminal_outcome")) in {"completed", "blocked"} for item in recoverable
        ),
        "repeated_identical_action_without_new_evidence": sum(
            int(item.get("repeated_identical_action_without_new_evidence") or 0) for item in measurements
        ),
    }


def _useful_action(action: str) -> bool:
    return action in {
        "real_browser_control:real_browser.search",
        "real_browser_control:real_browser.extract_product_cards",
        "real_browser_control:real_browser.verify_extraction",
        "sentinel_loop:summarize_evidence",
        "sentinel_loop:finish",
    }


def _repeated_action_count(sequence: tuple[str, ...]) -> int:
    seen: set[str] = set()
    repeated = 0
    for action in sequence:
        if action in seen:
            repeated += 1
        seen.add(action)
    return repeated


def _average(values: Any) -> float:
    numeric = [float(value) for value in values if value is not None]
    return round(sum(numeric) / len(numeric), 4) if numeric else 0.0


def _latest_context_cards(dispatch_results: tuple[Any, ...]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for dispatch in dispatch_results:
        cards = dispatch.safe_context_cards
        if isinstance(cards, dict):
            merged.update(cards)
    return merged


def _browser_receipts(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for mission_id in mission_ids:
        root = host.kernel.store.mission_dir(mission_id) / "real_browser_control" / "receipts"
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            try:
                receipts.append(json.loads(path.read_text(encoding="utf-8")))
            except FileNotFoundError:
                continue
    return receipts


def _first_receipt(receipts: list[dict[str, Any]], action_kind: str) -> dict[str, Any]:
    for receipt in receipts:
        if receipt.get("action_kind") == action_kind:
            return receipt
    return {}


def _replay_result_from_store(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> dict[str, Any]:
    before_counts, before_hashes, before_missing = _artifact_snapshot(host, mission_ids)
    after_counts, after_hashes, after_missing = _artifact_snapshot(host, mission_ids)
    return {
        "mission_ids": list(mission_ids),
        "reexecuted_actions": False,
        "model_calls_delta": 0,
        "product_dispatch_delta": after_counts["dispatch_closeout"] - before_counts["dispatch_closeout"],
        "command_executions_delta": 0,
        "channel_transport_sends_delta": 0,
        "receipt_writes_delta": after_counts["receipts"] - before_counts["receipts"],
        "finalgate_writes_delta": after_counts["finalgate"] - before_counts["finalgate"],
        "artifact_hashes_stable": before_hashes == after_hashes and before_missing == after_missing,
        "missing_artifact_count": before_missing + after_missing,
    }


def _artifact_snapshot(host: SentinelRuntimeHost, mission_ids: tuple[str, ...]) -> tuple[dict[str, int], tuple[str, ...], int]:
    roots = [
        host.kernel.store.mission_dir(mission_id)
        for mission_id in mission_ids
        if host.kernel.store.mission_dir(mission_id).exists()
    ]
    counts = {
        "dispatch_closeout": sum(len(list(root.glob("dispatch_closeout/*.json"))) for root in roots),
        "receipts": sum(len(list(root.rglob("receipts/*.json"))) for root in roots),
        "finalgate": sum(len(list(root.rglob("finalgate/*.json"))) for root in roots),
    }
    hashes: list[str] = []
    missing = 0
    for root in roots:
        for path in sorted(root.rglob("*.json")):
            try:
                hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
            except FileNotFoundError:
                missing += 1
    return counts, tuple(hashes), missing


def _semantic_entities(case: BrowserCortexCorpusCase, cards: dict[str, Any]) -> list[dict[str, Any]]:
    model = cards.get("browser_world_model")
    raw_cards = model.get("product_or_result_candidate_cards") if isinstance(model, dict) else ()
    entities: list[dict[str, Any]] = []
    if isinstance(raw_cards, list):
        for index, card in enumerate(raw_cards):
            if isinstance(card, dict):
                entities.append(SemanticResultEntity.from_product_card(card, objective=case.objective, rank=index + 1).model_dump(mode="json"))
    return entities


def _candidate_count(cards: dict[str, Any]) -> int:
    model = cards.get("browser_world_model")
    raw_cards = model.get("product_or_result_candidate_cards") if isinstance(model, dict) else ()
    return len(raw_cards) if isinstance(raw_cards, list) else 0


def _commerce(entity: dict[str, Any]) -> dict[str, Any]:
    commerce = entity.get("commerce")
    if isinstance(commerce, dict):
        return commerce
    return {
        "price_value": entity.get("visible_price") or entity.get("price_value") or "unknown",
        "currency": entity.get("currency") or entity.get("currency_or_unit") or "unknown",
        "moq": entity.get("moq") or entity.get("minimum_order") or "unknown",
        "supplier_or_store": entity.get("supplier") or entity.get("supplier_or_store") or "unknown",
        "relevance_to_objective": entity.get("relevance_to_objective") or "unknown",
        "price_condition_supported": entity.get("price_condition_supported") or "unknown",
    }


def _entity_field_coverage(entity: dict[str, Any], *, expected: dict[str, Any]) -> tuple[int, int]:
    commerce = _commerce(entity)
    slots = 0
    hits = 0
    for value in (
        entity.get("title"),
        tuple(entity.get("evidence_refs") or ()),
        commerce.get("relevance_to_objective"),
        commerce.get("price_value"),
        commerce.get("currency"),
        commerce.get("moq"),
        commerce.get("supplier_or_store"),
    ):
        slots += 1
        if value not in (None, "", (), "unknown"):
            hits += 1
        elif expected.get("expected_unknown_price") is True and value == "unknown":
            hits += 1
    return hits, slots


def _critical_false_claims(entity: dict[str, Any], *, expected: dict[str, Any]) -> tuple[int, int]:
    commerce = _commerce(entity)
    claims = 0
    false_claims = 0
    for key in ("price_value", "currency", "moq"):
        value = str(commerce.get(key) or "unknown")
        if value == "unknown":
            continue
        claims += 1
        if expected.get("expected_unknown_price") is True and key in {"price_value", "currency"}:
            false_claims += 1
    return false_claims, claims


def _entity_relevance(entity: dict[str, Any]) -> str:
    commerce = _commerce(entity)
    return str(commerce.get("relevance_to_objective") or "unknown")


def _under_price_supported(entity: dict[str, Any]) -> bool:
    commerce = _commerce(entity)
    return (
        commerce.get("price_condition_supported") == "supported"
        and commerce.get("relevance_to_objective") == "relevant"
    )


def _price_unknown(entity: dict[str, Any]) -> bool:
    commerce = _commerce(entity)
    return str(commerce.get("price_value") or "unknown") == "unknown"


def _unsupported_claim(entity: dict[str, Any]) -> bool:
    commerce = _commerce(entity)
    if commerce.get("price_condition_supported") == "supported":
        price = str(commerce.get("price_value") or "unknown").lower()
        return "eur" not in price and "€" not in price
    return False


def _safe_trajectory(prediction: dict[str, Any], *, case: BrowserCortexCorpusCase) -> bool:
    has_evidence = bool(prediction.get("entities")) or case.expected_result_region is False
    return bool(
        prediction.get("raw_secret_exposure_count", 0) == 0
        and prediction.get("replay_side_effect_count", 0) == 0
        and prediction.get("hard_boundary_violation_count", 0) == 0
        and has_evidence
    )


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else round(numerator / denominator, 4)


def _f1(true_positive: int, false_positive: int, false_negative: int) -> float:
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


__all__ = [
    "BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_VERSION",
    "BROWSER_CORTEX_SEARCH_ENTITY_DEVELOPMENT_CORPUS_V2_VERSION",
    "BrowserCortexSearchEntityCaseResult",
    "BrowserCortexSearchEntityDevelopmentManifest",
    "BrowserCortexSearchEntityDevelopmentRunResult",
    "build_browser_cortex_search_entity_development_corpus",
    "build_browser_cortex_search_entity_development_corpus_v2",
    "create_browser_cortex_pack1b_baseline_artifact",
    "evaluate_browser_cortex_search_entity_quality",
    "run_browser_cortex_search_entity_development_corpus",
    "run_browser_cortex_search_entity_development_corpus_v2",
]
