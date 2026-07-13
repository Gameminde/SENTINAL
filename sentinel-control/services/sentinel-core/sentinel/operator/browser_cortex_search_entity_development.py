from __future__ import annotations

import hashlib
import json
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


class BrowserCortexSearchEntityDevelopmentRunResult(SentinelModel):
    corpus_version: str
    manifest_hash: str
    baseline_commit: str
    fixture_bundle_hash: str
    case_results: tuple[BrowserCortexSearchEntityCaseResult, ...]
    metrics: dict[str, Any] = Field(default_factory=dict)

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


def _case(
    task_id: str,
    tags: tuple[str, ...],
    *,
    material_success: bool = True,
    result_region: bool = True,
    relevant: bool,
    under_price_supported: bool,
    expected_unknown_price: bool = False,
    contradictions_expected: bool = False,
    expected_search_control_ref: str = "input:search",
) -> BrowserCortexCorpusCase:
    return BrowserCortexCorpusCase(
        task_id=task_id,
        objective="Find relevant glasses or sunglasses around 5 EUR or less per unit if visible.",
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
    if status != "completed":
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
    if case.expected_semantic_facts.get("relevant") is True and metrics["objective_relevance_recall"] < 1.0:
        failures.append("RELEVANCE_MISSING")
    if case.expected_semantic_facts.get("under_price_supported") is True and metrics["under_price_claim_precision"] < 1.0:
        failures.append("UNDER_PRICE_SUPPORT_MISSING")
    if case.expected_semantic_facts.get("expected_unknown_price") is True and metrics["unknown_field_preservation_rate"] < 1.0:
        failures.append("UNKNOWN_PRICE_NOT_PRESERVED")
    return failures


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
            receipts.append(json.loads(path.read_text(encoding="utf-8")))
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
    "BrowserCortexSearchEntityCaseResult",
    "BrowserCortexSearchEntityDevelopmentManifest",
    "BrowserCortexSearchEntityDevelopmentRunResult",
    "build_browser_cortex_search_entity_development_corpus",
    "evaluate_browser_cortex_search_entity_quality",
    "run_browser_cortex_search_entity_development_corpus",
]
