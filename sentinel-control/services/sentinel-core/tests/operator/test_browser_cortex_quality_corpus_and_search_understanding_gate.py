from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionResult
from sentinel.operator.browser_cortex_quality_gate import (
    BrowserCortexQualityPrediction,
    SemanticResultEntity,
    build_browser_cortex_quality_corpus,
    derive_search_progress_state,
    evaluate_browser_cortex_quality,
)
from sentinel.operator.decision_context import DecisionContextCompiler


def test_decision_context_counterfactual_environment_state_changes_recommendations() -> None:
    cards_visible = _compile_with_environment_state(
        _environment_state(
            page_kind="search_results",
            search_refs=("input:search",),
            candidate_count=4,
            relevant_candidate_count=2,
            recommended_skills=("extract", "verify", "browse_search"),
        )
    )
    search_ready = _compile_with_environment_state(
        _environment_state(
            page_kind="landing",
            search_refs=("input:search", "input:header_search"),
            candidate_count=0,
            relevant_candidate_count=0,
            recommended_skills=("browse_search", "extract"),
        )
    )

    assert (
        cards_visible["primary_model_recommended_next_action"]
        == "real_browser_control.real_browser.extract_product_cards"
    )
    assert search_ready["primary_model_recommended_next_action"] == "real_browser_control.real_browser.search"
    assert cards_visible["browser_environment_memory"]["latest_product_or_result_candidate_count"] == 4
    assert search_ready["browser_environment_memory"]["latest_product_or_result_candidate_count"] == 0


def test_state_field_values_survive_context_redaction_without_secret_material() -> None:
    state = _environment_state(
        page_kind="search_results",
        search_refs=("input:search",),
        candidate_count=3,
        relevant_candidate_count=1,
        recommended_skills=("extract",),
    )
    state["session_graph"]["cookies"] = [{"name_hash": stable_hash("session"), "value": "raw-cookie"}]

    context = _compile_with_environment_state(state)
    safe_state = context["browser_environment_state"]
    serialized = json.dumps(safe_state, sort_keys=True)

    assert safe_state["state_fields"]["result_regions"]["value"]["candidate_count"] == 3
    assert safe_state["state_fields"]["search_controls"]["value"]["ranked_count"] == 1
    assert "raw-cookie" not in serialized


def test_frozen_deterministic_corpus_has_required_coverage_and_manifest_hash() -> None:
    manifest = build_browser_cortex_quality_corpus(baseline_commit="test_baseline")
    categories = {
        category
        for case in manifest.deterministic_cases
        for category in case.category_tags
    }
    required_categories = {
        "conventional_search_form",
        "multiple_search_fields",
        "spa",
        "result_no_url",
        "url_query_no_result",
        "shadow_dom",
        "iframe",
        "dynamic_loading",
        "pagination",
        "infinite_scroll",
        "autocomplete",
        "modal_overlay",
        "localized_ui",
        "empty_results",
        "negative_relevance",
        "client_side_filter",
        "network_failure",
        "stale_controls",
        "structured_data",
        "contradictory_price_currency",
        "non_commerce",
        "fill_only_false_success_trap",
    }

    assert manifest.corpus_version == "browser_cortex_quality_corpus_v1"
    assert len(manifest.deterministic_cases) >= 24
    assert required_categories <= categories
    assert len(manifest.real_world_holdout_tasks) >= 20
    assert len({task.public_site for task in manifest.real_world_holdout_tasks}) >= 5
    assert manifest.manifest_hash == manifest.compute_manifest_hash()


def test_evaluator_flags_fill_only_false_success_and_invariants() -> None:
    manifest = build_browser_cortex_quality_corpus(baseline_commit="test_baseline")
    trap = next(case for case in manifest.deterministic_cases if "fill_only_false_success_trap" in case.category_tags)

    metrics = evaluate_browser_cortex_quality(
        manifest,
        predictions=[
            BrowserCortexQualityPrediction(
                task_id=trap.task_id,
                selected_search_control_ref=trap.expected_search_control_ref,
                search_progress_states=("INPUT_WRITTEN", "QUERY_REFLECTED", "MATERIAL_SUCCESS"),
                search_materially_successful=True,
                result_region_detected=False,
                semantic_entities=(),
                raw_secret_exposure_count=0,
                replay_side_effect_count=0,
                unsupported_claim_count=0,
            )
        ],
    )

    assert metrics.invariant_counts["fill_only_false_success"] == 1
    assert metrics.invariants_passed is False
    assert metrics.search_materiality_precision == 0.0


def test_search_progress_state_requires_material_evidence_beyond_input_fill() -> None:
    progress = derive_search_progress_state(
        {
            "input_written": True,
            "query_reflected": True,
            "submission_attempted": False,
            "request_observed": False,
            "navigation_or_state_changed": False,
            "result_region_changed": False,
        }
    )

    assert progress.states == ("INPUT_WRITTEN", "QUERY_REFLECTED", "UNCERTAIN")
    assert progress.current_state == "UNCERTAIN"
    assert progress.search_materially_successful is False
    assert "input and query reflection are not material search proof" in progress.uncertainty_reason


def test_semantic_result_entity_graph_preserves_unknowns_and_contradictions() -> None:
    entity = SemanticResultEntity.from_product_card(
        {
            "card_id": "card_1",
            "title": "Polarized sunglasses sample",
            "product_url_hash": stable_hash("https://bounded.example/product/1"),
            "visible_price": "unknown",
            "currency_or_unit": "unknown",
            "minimum_order": "50 pieces",
            "supplier_or_store": "Example Supplier",
            "relevance_to_objective": "partial",
            "evidence_ref_hash": "card:evidence",
            "contradictions": ["visible text says EUR, structured data says USD"],
        },
        objective="Find glasses under 5 EUR.",
    )

    assert entity.entity_type == "commerce_product"
    assert entity.title == "Polarized sunglasses sample"
    assert entity.commerce["price_value"] == "unknown"
    assert entity.commerce["currency"] == "unknown"
    assert entity.commerce["moq"] == "50 pieces"
    assert entity.commerce["relevance_to_objective"] == "partial"
    assert entity.contradictions == ("visible text says EUR, structured data says USD",)
    assert entity.uncertainty_reason == "price_or_currency_unknown"


def _compile_with_environment_state(state: dict[str, object]) -> dict[str, object]:
    authority = MissionAuthorityEnvelope(
        user_id="user_browser_cortex_quality",
        mission_title="Browser Cortex Quality Gate",
        mission_objective="Search a bounded product page and extract relevant cards.",
        allowed_tools=["real_browser_control"],
        allowed_actions=[
            "real_browser.open",
            "real_browser.search",
            "real_browser.extract_product_cards",
            "real_browser.verify_extraction",
            "finish",
        ],
        forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
        allowed_domains=["real_browser:bounded_test_url"],
        max_actions=8,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )
    return DecisionContextCompiler().compile(
        mission_id="mission_browser_cortex_quality",
        mission_objective=authority.mission_objective,
        authority=authority,
        observations=[
            ActionResult(
                action_id="act_real_browser_observe",
                capability_id="real_browser_control",
                operation="real_browser.observe",
                status="completed",
                receipt_refs=("observe_receipt",),
                material_action=False,
                observation_summary="browser observed",
                result_hash=stable_hash(state),
                context_cards={
                    "browser_environment_state": state,
                    "browser_environment_state_hash": stable_hash(state),
                },
            )
        ],
        available_actions=(
            "real_browser_control.real_browser.open",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "sentinel_loop.finish",
        ),
        model_calls_used=1,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=0,
        max_recovery_turns=3,
    )


def _environment_state(
    *,
    page_kind: str,
    search_refs: tuple[str, ...],
    candidate_count: int,
    relevant_candidate_count: int,
    recommended_skills: tuple[str, ...],
) -> dict[str, object]:
    cards = tuple(
        {
            "card_id": f"card_{index}",
            "kind": "product",
            "title": f"Bounded product {index}",
            "visible_price": "4.50 EUR" if index == 0 else "unknown",
            "currency_or_unit": "EUR / piece" if index == 0 else "unknown",
            "minimum_order": "unknown",
            "supplier_or_store": "Example Supplier" if index == 0 else "unknown",
            "relevance_to_objective": "relevant" if index < relevant_candidate_count else "unknown",
            "evidence_ref_hash": f"card:evidence:{index}",
        }
        for index in range(candidate_count)
    )
    result_region_value = {
        "candidate_count": candidate_count,
        "relevant_candidate_count": relevant_candidate_count,
    }
    search_value = {"search_like_refs": list(search_refs), "ranked_count": len(search_refs)}
    return {
        "schema_version": "browser_environment_state_v1",
        "state_id": f"browser_env_state_{page_kind}_{candidate_count}_{len(search_refs)}",
        "cognitive_graph_ready": True,
        "backend_truth": {
            "selected_backend_id": "cloak_browser",
            "actual_backend_id": "cloak_browser",
            "session_backend_kind": "cloakbrowser",
            "product_backend_proven": True,
        },
        "page_state": {
            "page_state_hash": stable_hash({"page_kind": page_kind, "candidate_count": candidate_count}),
            "origin_hash": stable_hash("https://bounded.example"),
            "page_kind_guess": page_kind,
            "title_hash_or_safe_title": "Bounded Product Page",
            "visible_text_summary_hash": stable_hash(page_kind),
            "stable_ref_count": len(search_refs) + candidate_count,
        },
        "action_graph": {
            "search_like_refs": list(search_refs),
            "form_controls": list(search_refs),
            "button_refs": ["button:search"] if search_refs else [],
            "link_refs": [f"link:result_{index}" for index in range(candidate_count)],
            "recommended_browser_actions": [
                "real_browser.search" if search_refs and not candidate_count else "real_browser.extract_product_cards"
            ],
        },
        "extraction_graph": {
            "product_or_result_candidate_count": candidate_count,
            "relevant_product_candidate_count": relevant_candidate_count,
            "cards": list(cards),
        },
        "protocol_graph": {"network_event_count": 0, "console_event_count": 0},
        "session_graph": {"cookie_count": 0, "storage_key_count": 0, "cookies": [], "storage_keys": []},
        "blocker_graph": {"modal_or_consent_signals": [], "captcha_or_login_signals": [], "hard_boundary_signals": []},
        "visual_graph": {"visual_refs_available": False, "screenshot_persisted": False},
        "state_fields": {
            "result_regions": _state_field(result_region_value, evidence=("cards",)),
            "candidate_entity_regions": _state_field({"cards": list(cards)}, evidence=("cards",)),
            "search_controls": _state_field(search_value, evidence=("refs",)),
            "recommended_recovery_paths": _state_field(
                {"paths": ["extract_product_cards"] if candidate_count else ["retry_best_ranked_search_control"]},
                evidence=("recovery",),
            ),
        },
        "recommended_model_skills": list(recommended_skills),
        "raw_material_persisted": False,
        "can_execute": False,
    }


def _state_field(value: object, *, evidence: tuple[str, ...]) -> dict[str, object]:
    return {
        "value": value,
        "confidence": 0.9,
        "evidence_refs": list(evidence),
        "freshness": "current_snapshot",
        "source": "test_safe_browser_state",
        "uncertainty_reason": "test fixture",
    }
