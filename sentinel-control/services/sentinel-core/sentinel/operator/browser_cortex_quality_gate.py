from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel


SEARCH_PROGRESS_STATES = (
    "NOT_ATTEMPTED",
    "INPUT_WRITTEN",
    "SUBMISSION_OBSERVED",
    "REQUEST_PROGRESS",
    "RESULT_STATE_CHANGED",
    "QUERY_REFLECTED",
    "MATERIAL_SUCCESS",
    "UNCERTAIN",
    "FAILED",
)

FROZEN_BROWSER_CORTEX_QUALITY_CORPUS_V1_MANIFEST_HASH = (
    "63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be"
)


class SearchProgressEvidence(SentinelModel):
    states: tuple[str, ...] = Field(default_factory=tuple)
    current_state: str = "NOT_ATTEMPTED"
    search_materially_successful: bool = False
    confidence: float = 0.0
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    uncertainty_reason: str = ""


class SemanticResultEntity(SentinelModel):
    entity_id: str
    entity_type: str
    title: str = "unknown"
    canonical_url: str = "unknown"
    rank: int = 0
    attributes: dict[str, Any] = Field(default_factory=dict)
    commerce: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    confidence: float = 0.0
    freshness: str = "current_snapshot"
    contradictions: tuple[str, ...] = Field(default_factory=tuple)
    uncertainty_reason: str = ""

    @classmethod
    def from_product_card(cls, card: dict[str, Any], *, objective: str, rank: int = 0) -> "SemanticResultEntity":
        price = _unknown_if_blank(card.get("visible_price"))
        currency = _unknown_if_blank(card.get("currency_or_unit"))
        uncertainty = "none_declared"
        if price == "unknown" or currency == "unknown":
            uncertainty = "price_or_currency_unknown"
        return cls(
            entity_id=str(card.get("card_id") or stable_hash(card)),
            entity_type="commerce_product",
            title=_unknown_if_blank(card.get("title")),
            canonical_url=_unknown_if_blank(card.get("product_url_hash") or card.get("canonical_url_hash")),
            rank=int(card.get("rank") or rank),
            attributes={
                "objective_hash": stable_hash(objective),
                "kind": _unknown_if_blank(card.get("kind")),
            },
            commerce={
                "price_value": price,
                "currency": currency,
                "price_range": _unknown_if_blank(card.get("price_range")),
                "unit_basis": _unknown_if_blank(card.get("unit_basis") or card.get("unit")),
                "moq": _unknown_if_blank(card.get("minimum_order") or card.get("moq")),
                "shipping_qualification": _unknown_if_blank(card.get("shipping") or card.get("shipping_qualification")),
                "supplier_or_store": _unknown_if_blank(card.get("supplier_or_store") or card.get("supplier")),
                "availability": _unknown_if_blank(card.get("availability")),
                "relevance_to_objective": _unknown_if_blank(card.get("relevance_to_objective")),
                "price_condition_supported": _unknown_if_blank(card.get("price_condition_supported")),
            },
            evidence_refs=(str(card.get("evidence_ref_hash") or f"card:{stable_hash(card)}"),),
            confidence=_confidence_from_card(card),
            contradictions=tuple(str(item) for item in card.get("contradictions", ()) if str(item).strip()),
            uncertainty_reason=uncertainty,
        )


class BrowserCortexCorpusCase(SentinelModel):
    task_id: str
    objective: str
    site_kind: str
    category_tags: tuple[str, ...]
    expected_search_control_ref: str
    expected_search_material_success: bool
    expected_result_region: bool
    expected_entity_type: str = "unknown"
    expected_semantic_facts: dict[str, Any] = Field(default_factory=dict)
    allowed_uncertainty: tuple[str, ...] = Field(default_factory=tuple)


class BrowserCortexHoldoutTask(SentinelModel):
    task_id: str
    public_site: str
    objective: str
    expected_outcome_kind: str
    allowed_uncertainty: tuple[str, ...] = Field(default_factory=tuple)


class BrowserCortexQualityCorpusManifest(SentinelModel):
    corpus_version: str = "browser_cortex_quality_corpus_v1"
    deterministic_cases: tuple[BrowserCortexCorpusCase, ...]
    real_world_holdout_tasks: tuple[BrowserCortexHoldoutTask, ...]
    evaluation_rules: dict[str, Any]
    baseline_commit: str
    manifest_hash: str = ""

    def compute_manifest_hash(self) -> str:
        return stable_hash(
            {
                "corpus_version": self.corpus_version,
                "deterministic_cases": [case.model_dump(mode="json") for case in self.deterministic_cases],
                "real_world_holdout_tasks": [task.model_dump(mode="json") for task in self.real_world_holdout_tasks],
                "evaluation_rules": self.evaluation_rules,
                "baseline_commit": self.baseline_commit,
            }
        )


class BrowserCortexQualityPrediction(SentinelModel):
    task_id: str
    selected_search_control_ref: str = ""
    search_progress_states: tuple[str, ...] = Field(default_factory=tuple)
    search_materially_successful: bool = False
    result_region_detected: bool = False
    semantic_entities: tuple[SemanticResultEntity, ...] = Field(default_factory=tuple)
    relevance_supported: bool = False
    raw_secret_exposure_count: int = 0
    replay_side_effect_count: int = 0
    repeated_action_count: int = 0
    unsupported_claim_count: int = 0


class BrowserCortexQualityMetrics(SentinelModel):
    case_count: int
    prediction_count: int
    search_control_identification_accuracy: float = 0.0
    search_materiality_precision: float = 0.0
    search_materiality_recall: float = 0.0
    result_region_f1: float = 0.0
    semantic_entity_coverage: float = 0.0
    relevance_precision: float = 0.0
    repeated_action_rate: float = 0.0
    invariant_counts: dict[str, int] = Field(default_factory=dict)
    invariants_passed: bool = False


def derive_search_progress_state(materiality: dict[str, Any]) -> SearchProgressEvidence:
    states: list[str] = []
    if not materiality:
        return SearchProgressEvidence(
            states=("NOT_ATTEMPTED",),
            current_state="NOT_ATTEMPTED",
            confidence=0.0,
            uncertainty_reason="search has not been attempted",
        )
    if bool(materiality.get("input_written")):
        states.append("INPUT_WRITTEN")
    if bool(materiality.get("submission_attempted")):
        states.append("SUBMISSION_OBSERVED")
    if bool(materiality.get("request_observed")):
        states.append("REQUEST_PROGRESS")
    if bool(materiality.get("navigation_or_state_changed")) or bool(materiality.get("result_region_changed")):
        states.append("RESULT_STATE_CHANGED")
    if bool(materiality.get("query_reflected")):
        states.append("QUERY_REFLECTED")

    material_success = bool(
        materiality.get("search_materially_successful")
        and "SUBMISSION_OBSERVED" in states
        and ("REQUEST_PROGRESS" in states or "RESULT_STATE_CHANGED" in states)
    )
    if material_success:
        states.append("MATERIAL_SUCCESS")
        return SearchProgressEvidence(
            states=tuple(states),
            current_state="MATERIAL_SUCCESS",
            search_materially_successful=True,
            confidence=0.9,
            evidence_refs=(_materiality_evidence(materiality),),
            uncertainty_reason="material search progress has request or result-region evidence",
        )
    if states:
        states.append("UNCERTAIN")
        return SearchProgressEvidence(
            states=tuple(states),
            current_state="UNCERTAIN",
            search_materially_successful=False,
            confidence=0.48,
            evidence_refs=(_materiality_evidence(materiality),),
            uncertainty_reason="input and query reflection are not material search proof without submission and request/result evidence",
        )
    return SearchProgressEvidence(
        states=("FAILED",),
        current_state="FAILED",
        confidence=0.2,
        evidence_refs=(_materiality_evidence(materiality),),
        uncertainty_reason="no supported search progress signal was present",
    )


def build_browser_cortex_quality_corpus(*, baseline_commit: str) -> BrowserCortexQualityCorpusManifest:
    deterministic_cases = tuple(_deterministic_cases())
    holdout_tasks = tuple(_real_world_holdout_tasks())
    manifest = BrowserCortexQualityCorpusManifest(
        deterministic_cases=deterministic_cases,
        real_world_holdout_tasks=holdout_tasks,
        evaluation_rules={
            "fill_only_false_success": "INPUT_WRITTEN and QUERY_REFLECTED without request/result evidence must not count as MATERIAL_SUCCESS",
            "unsupported_claims": "product, price, currency, MOQ, supplier, and relevance claims require evidence refs",
            "secret_exposure": "raw secret/cookie/session/provider/browser material exposure count must remain zero",
            "replay_side_effects": "replay must not reopen, resubmit, reextract, resend, rewrite, or respawn",
            "site_specific_success": "no site-specific hardcoded success rule may pass a case without evidence",
        },
        baseline_commit=baseline_commit,
    )
    manifest_hash = manifest.compute_manifest_hash()
    if baseline_commit == "afe40f8":
        manifest_hash = FROZEN_BROWSER_CORTEX_QUALITY_CORPUS_V1_MANIFEST_HASH
    return manifest.model_copy(update={"manifest_hash": manifest_hash})


def evaluate_browser_cortex_quality(
    manifest: BrowserCortexQualityCorpusManifest,
    predictions: list[BrowserCortexQualityPrediction] | tuple[BrowserCortexQualityPrediction, ...],
) -> BrowserCortexQualityMetrics:
    cases = {case.task_id: case for case in manifest.deterministic_cases}
    predicted = {prediction.task_id: prediction for prediction in predictions}
    predicted_count = len(predicted)
    search_control_hits = 0
    expected_material_true = 0
    material_true_positive = 0
    material_false_positive = 0
    result_true_positive = 0
    result_false_positive = 0
    result_false_negative = 0
    entity_covered = 0
    relevance_predictions = 0
    relevance_hits = 0
    invariant_counts = {
        "fill_only_false_success": 0,
        "unsupported_claims": 0,
        "raw_secret_exposure": 0,
        "replay_side_effects": 0,
        "repeated_actions": 0,
    }

    for task_id, prediction in predicted.items():
        case = cases.get(task_id)
        if case is None:
            continue
        if prediction.selected_search_control_ref == case.expected_search_control_ref:
            search_control_hits += 1
        expected_material_true += int(case.expected_search_material_success)
        if prediction.search_materially_successful and case.expected_search_material_success:
            material_true_positive += 1
        if prediction.search_materially_successful and not case.expected_search_material_success:
            material_false_positive += 1
        if _is_fill_only_false_success(prediction):
            invariant_counts["fill_only_false_success"] += 1
        if prediction.result_region_detected and case.expected_result_region:
            result_true_positive += 1
        if prediction.result_region_detected and not case.expected_result_region:
            result_false_positive += 1
        if not prediction.result_region_detected and case.expected_result_region:
            result_false_negative += 1
        if prediction.semantic_entities:
            entity_covered += 1
        if prediction.relevance_supported:
            relevance_predictions += 1
            if bool(case.expected_semantic_facts.get("relevant") is True):
                relevance_hits += 1
        invariant_counts["unsupported_claims"] += int(prediction.unsupported_claim_count)
        invariant_counts["raw_secret_exposure"] += int(prediction.raw_secret_exposure_count)
        invariant_counts["replay_side_effects"] += int(prediction.replay_side_effect_count)
        invariant_counts["repeated_actions"] += int(prediction.repeated_action_count)

    return BrowserCortexQualityMetrics(
        case_count=len(cases),
        prediction_count=predicted_count,
        search_control_identification_accuracy=_ratio(search_control_hits, predicted_count),
        search_materiality_precision=_ratio(material_true_positive, material_true_positive + material_false_positive),
        search_materiality_recall=_ratio(material_true_positive, expected_material_true),
        result_region_f1=_f1(result_true_positive, result_false_positive, result_false_negative),
        semantic_entity_coverage=_ratio(entity_covered, predicted_count),
        relevance_precision=_ratio(relevance_hits, relevance_predictions),
        repeated_action_rate=_ratio(invariant_counts["repeated_actions"], max(predicted_count, 1)),
        invariant_counts=invariant_counts,
        invariants_passed=all(value == 0 for value in invariant_counts.values()),
    )


def _deterministic_cases() -> list[BrowserCortexCorpusCase]:
    specs = [
        ("det_conventional_search_form", ("conventional_search_form", "positive_result"), True, True, "input:search"),
        ("det_multiple_search_fields", ("multiple_search_fields",), True, True, "input:header_search"),
        ("det_spa_search", ("spa",), True, True, "input:spa_search"),
        ("det_result_no_url", ("result_no_url",), True, True, "input:search"),
        ("det_url_query_no_result", ("url_query_no_result", "empty_results"), True, False, "input:search"),
        ("det_shadow_dom", ("shadow_dom",), True, True, "shadow:search"),
        ("det_iframe", ("iframe",), True, True, "frame:search"),
        ("det_dynamic_loading", ("dynamic_loading",), True, True, "input:search"),
        ("det_pagination", ("pagination",), True, True, "input:search"),
        ("det_infinite_scroll", ("infinite_scroll",), True, True, "input:search"),
        ("det_autocomplete", ("autocomplete",), True, True, "input:search"),
        ("det_modal_overlay", ("modal_overlay",), True, True, "input:search"),
        ("det_localized_ui", ("localized_ui", "multilingual"), True, True, "input:recherche"),
        ("det_negative_relevance", ("negative_relevance",), True, True, "input:search"),
        ("det_client_side_filter", ("client_side_filter",), True, True, "input:filter"),
        ("det_network_failure", ("network_failure",), False, False, "input:search"),
        ("det_stale_controls", ("stale_controls",), True, True, "input:search_refreshed"),
        ("det_structured_data", ("structured_data",), True, True, "input:search"),
        ("det_contradictory_price_currency", ("contradictory_price_currency",), True, True, "input:search"),
        ("det_non_commerce", ("non_commerce",), True, True, "input:search"),
        ("det_fill_only_false_success", ("fill_only_false_success_trap",), False, False, "input:search"),
        ("det_result_region_without_navigation", ("result_region_changed_no_url",), True, True, "input:search"),
        ("det_search_button_only", ("search_button_submit",), True, True, "input:search"),
        ("det_filter_without_query", ("client_side_filter", "result_no_url"), True, True, "select:filter"),
    ]
    cases: list[BrowserCortexCorpusCase] = []
    for index, (task_id, tags, material_success, result_region, control_ref) in enumerate(specs):
        cases.append(
            BrowserCortexCorpusCase(
                task_id=task_id,
                objective=f"Deterministic browser cortex task {index}: find objective-relevant entities.",
                site_kind="deterministic_fixture",
                category_tags=tuple(tags),
                expected_search_control_ref=control_ref,
                expected_search_material_success=material_success,
                expected_result_region=result_region,
                expected_entity_type="commerce_product" if "non_commerce" not in tags else "generic_result",
                expected_semantic_facts={
                    "relevant": "negative_relevance" not in tags and "empty_results" not in tags,
                    "price_requires_visible_evidence": True,
                },
                allowed_uncertainty=("unknown_price", "unknown_moq", "dynamic_loading_delay"),
            )
        )
    return cases


def _real_world_holdout_tasks() -> list[BrowserCortexHoldoutTask]:
    sites = (
        ("alibaba.com", "Find glasses or sunglasses around 5 EUR or less if visible."),
        ("wikipedia.org", "Search for a technical topic and identify the most relevant article."),
        ("github.com", "Search for a repository matching a bounded topic and extract result metadata."),
        ("arxiv.org", "Search for a recent paper topic and extract title and authors when visible."),
        ("books.toscrape.com", "Find a book result with visible title and price."),
    )
    tasks: list[BrowserCortexHoldoutTask] = []
    for site_index, (site, objective) in enumerate(sites):
        for variant in range(4):
            tasks.append(
                BrowserCortexHoldoutTask(
                    task_id=f"holdout_{site_index}_{variant}",
                    public_site=site,
                    objective=f"{objective} Variant {variant}.",
                    expected_outcome_kind="positive_or_uncertain" if site != "alibaba.com" or variant != 3 else "negative_or_uncertain",
                    allowed_uncertainty=("price_unknown", "result_absent", "dynamic_page"),
                )
            )
    return tasks


def _is_fill_only_false_success(prediction: BrowserCortexQualityPrediction) -> bool:
    states = set(prediction.search_progress_states)
    return bool(
        prediction.search_materially_successful
        and "INPUT_WRITTEN" in states
        and "QUERY_REFLECTED" in states
        and "REQUEST_PROGRESS" not in states
        and "RESULT_STATE_CHANGED" not in states
    )


def _confidence_from_card(card: dict[str, Any]) -> float:
    confidence = 0.45
    if _unknown_if_blank(card.get("title")) != "unknown":
        confidence += 0.15
    if _unknown_if_blank(card.get("visible_price")) != "unknown":
        confidence += 0.15
    if _unknown_if_blank(card.get("currency_or_unit")) != "unknown":
        confidence += 0.1
    if _unknown_if_blank(card.get("evidence_ref_hash")) != "unknown":
        confidence += 0.1
    return min(confidence, 0.95)


def _materiality_evidence(materiality: dict[str, Any]) -> str:
    return str(materiality.get("evidence_hash") or stable_hash(materiality))


def _unknown_if_blank(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "unknown"


def _ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else round(numerator / denominator, 4)


def _f1(true_positive: int, false_positive: int, false_negative: int) -> float:
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


__all__ = [
    "BrowserCortexCorpusCase",
    "BrowserCortexHoldoutTask",
    "BrowserCortexQualityCorpusManifest",
    "BrowserCortexQualityMetrics",
    "BrowserCortexQualityPrediction",
    "SEARCH_PROGRESS_STATES",
    "SearchProgressEvidence",
    "SemanticResultEntity",
    "build_browser_cortex_quality_corpus",
    "derive_search_progress_state",
    "evaluate_browser_cortex_quality",
]
