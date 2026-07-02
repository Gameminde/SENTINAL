from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.actionability_registry import build_default_actionability_registry
from sentinel.operator.browser_backend_selector import select_browser_backend
from sentinel.operator.browser_decision_frame import BrowserDecisionFrameCompiler
from sentinel.operator.browser_model_native_control_loop import map_browser_model_native_intent
from sentinel.operator.browser_world_model import BrowserWorldModelBuilder
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopReplay, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.power_skill_registry import build_default_power_skill_registry
from sentinel.operator.real_browser_control_replay import RealBrowserControlReplayView
from sentinel.operator.real_browser_control_runtime import (
    InMemoryRealBrowserEngine,
    RealBrowserControlRuntime,
    RealBrowserControlRuntimeError,
    RealBrowserEngineElement,
    RealBrowserEngineSnapshot,
)


def test_browser_skill_frame_prefers_search_inspect_extract_over_type_click() -> None:
    world_model = BrowserWorldModelBuilder().build_from_snapshot(
        _HardProductSearchEngine().open(),
        mission_objective="Search Alibaba for glasses under 5 EUR.",
        origin_hash="origin_hash",
    )

    frame = BrowserDecisionFrameCompiler().compile(
        mission_objective="Search Alibaba for glasses under 5 EUR.",
        world_model=world_model,
        available_actions=_browser_actions(),
        progress_state="real_browser_opened_world_model_ready",
    )
    dumped = frame.safe_model_dump()
    actions = [candidate["action"] for candidate in dumped["candidate_actions"]]

    assert actions[:4] == [
        "real_browser.observe",
        "real_browser.search",
        "real_browser.inspect_result",
        "real_browser.open_result",
    ]
    assert "real_browser.extract_product_cards" in actions
    assert "real_browser.verify_extraction" in actions
    assert "real_browser.type_text" not in actions
    assert "real_browser.click" not in actions
    example_operations = [example["operation"] for example in dumped["exact_action_envelope_examples"]]
    assert "real_browser.search" in example_operations
    assert "real_browser.extract_product_cards" in example_operations
    assert "real_browser.type_text" not in example_operations


def test_browser_skill_actions_are_backed_by_actionability_registry() -> None:
    frame = build_default_actionability_registry().compile_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
    )
    visible = {item.canonical_action_name for item in frame.model_visible_actions}
    internal = {item.canonical_action_name for item in frame.hidden_internal_actions}

    assert {
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
        "real_browser_control.real_browser.open_result",
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
    }.issubset(visible)
    assert {
        "real_browser_control.real_browser.type_text",
        "real_browser_control.real_browser.click",
        "real_browser_control.real_browser.press_key",
    }.issubset(internal)


def test_browser_skill_consumes_power_skill_backend_frame() -> None:
    actionability = build_default_actionability_registry()
    backend_frame = build_default_power_skill_registry().compile_backend_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
        actionability_registry=actionability,
    )

    browser_backend = _backend_by_skill(backend_frame, "real_browser_control")

    assert browser_backend["model_visible_backend_id"] == "browser_skill"
    assert browser_backend["task_loop_reachable"] is True
    assert "CloakBrowser" in browser_backend["organ_refs"]


def test_browser_skill_selects_cloak_session_backend_when_available() -> None:
    selection = select_browser_backend(
        available_backend_modules=(
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        )
    )

    assert selection.preferred_backend_id == "cloak_browser"
    assert selection.model_visible_backend_id == "browser_skill"


def test_backend_frame_preferred_cloak_must_match_actual_backend_or_block(tmp_path: Path) -> None:
    selection = select_browser_backend(
        available_backend_modules=(
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        )
    )

    with pytest.raises(RealBrowserControlRuntimeError, match="real_browser_backend_selection_mismatch"):
        _BrowserSkillFixture(
            tmp_path,
            engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
            backend_selection=selection,
        )


def test_playwright_actual_engine_requires_explicit_compatibility_selection(tmp_path: Path) -> None:
    selection = select_browser_backend(
        available_backend_modules=(
            "sentinel.organs.browser.cloak_backend",
            "sentinel.operator.real_browser_control_runtime",
        )
    )

    fixture = _BrowserSkillFixture(
        tmp_path,
        engine=_PlaywrightCompatibilitySearchEngine(results_visible=True),
        backend_selection=selection,
        selected_backend_id="playwright_real_browser_engine",
    )

    assert fixture.runtime.selected_backend_id == "playwright_real_browser_engine"
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    assert opened.status == "completed"


def test_playwright_backend_requires_explicit_compatibility_selection() -> None:
    selection = select_browser_backend(available_backend_modules=("sentinel.operator.real_browser_control_runtime",))

    assert selection.preferred_backend_id is None
    assert selection.compatibility_backend_id == "playwright_real_browser_engine"
    assert selection.playwright_requires_explicit_compatibility is True


def test_real_browser_search_material_receipt_when_backend_actuates(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert result.material_action is True
    assert result.receipt_refs
    assert fixture.load_action_receipt(result.receipt_refs[0])["action_kind"] == "real_browser.search"


def test_real_browser_search_ranks_search_like_refs_and_tries_alternates(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_AlternateSearchEngine())

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert result.operation == "real_browser.search"
    assert fixture.engine.attempted_refs[:2] == ["input:broken_search", "input:search"]
    assert fixture.engine.search_query == "glasses under 5 euro"
    assert fixture.load_action_receipt(result.receipt_refs[0])["action_kind"] == "real_browser.search"


def test_real_browser_search_focuses_fills_or_types_and_presses_enter_or_search_button(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "completed"
    assert fixture.engine.type_count == 1
    assert fixture.engine.press_count == 1
    assert fixture.engine.results_visible is True
    assert "search submitted" in result.observation_summary


def test_locator_timeout_returns_recoverable_observation_not_terminal_block(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngine())

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert result.status == "recoverable_failed"
    assert result.recoverable is True
    assert result.failure_class is ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE
    assert result.blocked_reason == "real_browser_search_actuation_failed"
    assert result.recovery_observation


def test_search_recoverable_failure_updates_decision_context(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    failed = fixture.runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.search",
            params={"query": "glasses under 5 euro"},
        ),
        authority=fixture.authority,
        context={},
    )
    context = DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=[opened, failed],
        available_actions=_browser_actions(),
        model_calls_used=2,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=1,
        max_recovery_turns=2,
    )

    assert failed.status == "recoverable_failed"
    assert context["recoverable_observations"][-1]["failure_code"] == "real_browser_search_actuation_failed"
    assert context["primary_model_recommended_next_action"] == "real_browser_control.real_browser.extract_product_cards"


def test_recovery_observation_refreshes_world_model_and_decision_context(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "too early"}),
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=2).run()
    context = decisions.contexts[2]

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert context["recoverable_observations"]
    assert context["browser_world_model_summary"]["search_like_refs"]
    assert "real_browser_control.real_browser.search" in context["skill_decision_frame"]["recommended_next_actions"]


def test_recovery_budget_exhaustion_blocks_honestly_without_fake_success(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=0).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "RECOVERY_BUDGET_EXHAUSTED"
    assert result.receipt_refs == tuple(ref for ref in result.receipt_refs if "fake" not in ref)
    assert fixture.engine.type_count == 0


def test_two_search_failures_with_product_cards_recommends_extract_not_repeat_search(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    failures = [
        fixture.runtime.execute(
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.search",
                params={"query": "glasses under 5 euro"},
            ),
            authority=fixture.authority,
            context={},
        )
        for _ in range(2)
    ]
    context = DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=[opened, *failures],
        available_actions=_browser_actions(),
        model_calls_used=3,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=2,
        max_recovery_turns=3,
    )

    assert all(result.status == "recoverable_failed" for result in failures)
    assert context["primary_model_recommended_next_action"] == "real_browser_control.real_browser.extract_product_cards"
    assert context["skill_decision_frame"]["recommended_next_actions"][0] == "real_browser_control.real_browser.extract_product_cards"


def test_extract_product_cards_can_run_from_existing_world_model_cards(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    assert opened.context_cards["browser_world_model"]["product_or_result_candidate_cards"]
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )

    assert extracted.status == "completed"
    assert extracted.context_cards["browser_world_model"]["product_or_result_candidate_cards"]


def test_product_extraction_card_captures_title_price_moq_supplier_caveats_when_visible(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    result = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    cards = result.context_cards["browser_world_model"]["product_or_result_candidate_cards"]

    assert result.status == "completed"
    assert cards[0]["title"] == "Polarized sunglasses"
    assert cards[0]["visible_price"] == "$4.80"
    assert cards[0]["minimum_order"] == "10 pieces"
    assert cards[0]["supplier_or_store"] == "Yiwu Test Store"
    assert "shipping not included" in cards[0]["caveats"]


def test_finish_available_after_verify_extraction_and_summary(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    opened = fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    context = DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=[opened, extracted, verified],
        available_actions=_browser_actions(),
        model_calls_used=3,
        material_actions_used=0,
        max_model_calls=8,
        max_material_actions=4,
    )

    assert verified.status == "passed"
    assert context["finish_available"] is True
    assert context["primary_model_recommended_next_action"] == "sentinel_loop.finish"


def test_product_extraction_card_uses_unknown_fields_without_hallucination() -> None:
    snapshot = RealBrowserEngineSnapshot(
        page_title="Sparse Search",
        state_hash="state_hash",
        elements=(
            RealBrowserEngineElement(
                ref="link:sparse",
                role="link",
                name="Minimal glasses listing",
                text_preview="Minimal glasses listing",
            ),
        ),
    )

    world_model = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    )
    card = world_model.product_or_result_candidate_cards[0]

    assert card.title == "Minimal glasses listing"
    assert card.visible_price == "unknown"
    assert card.minimum_order == "unknown"
    assert card.supplier_or_store == "unknown"


def test_browser_research_proof_accepts_extraction_card_and_summary(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "one product card evaluated"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert decisions.contexts[-1]["objective_satisfied"] is True
    assert decisions.contexts[-1]["finish_available"] is True


def test_login_contact_payment_and_credential_actions_remain_hard_stops(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine())

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    blocked = [
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open", params={"url": "https://example.com/login"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.search", params={"query": "contact supplier"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.contact_supplier", params={}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.checkout", params={}),
    ]

    for envelope in blocked:
        with pytest.raises(RealBrowserControlRuntimeError):
            fixture.runtime.execute(envelope, authority=fixture.authority, context={})


def test_browser_replay_no_reopen_no_reclick_no_retype_no_resubmit_no_reextract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.search", params={"query": "glasses under 5 euro"}),
        authority=fixture.authority,
        context={},
    )
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context={},
    )

    replay = RealBrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)

    assert replay.browser_open_delta == 0
    assert replay.browser_click_delta == 0
    assert replay.browser_type_delta == 0
    assert replay.browser_press_delta == 0
    assert replay.browser_extract_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.artifact_hashes_stable is True
    assert loop_replay.real_browser_open_delta == 0
    assert loop_replay.real_browser_type_delta == 0
    assert loop_replay.real_browser_extract_delta == 0
    assert loop_replay.receipt_writes_delta == 0


def test_no_raw_dom_screenshot_cookie_session_provider_reasoning_persisted(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))

    fixture.runtime.execute(ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"), authority=fixture.authority, context={})
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context={},
    )
    persisted = _real_browser_artifact_text(fixture.kernel, fixture.mission_id).lower()

    for marker in ("raw_provider", "reasoning_content", "session_token", "screenshot", "<html", "<body"):
        assert marker not in persisted


def test_natural_intent_extract_visible_cards_maps_to_extract_product_cards(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent("I will extract the visible product cards now.", context=context)

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "real_browser_control"
    assert mapping.envelope.operation == "real_browser.extract_product_cards"


def test_visible_product_cards_and_ambiguous_intent_maps_to_extract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])
    context["primary_model_recommended_next_action"] = "real_browser_control.real_browser.open"
    context["recommended_next_action"] = "real_browser_control.real_browser.search"

    mapping = map_browser_model_native_intent("I will continue with the visible results.", context=context)

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"


def test_open_intent_with_visible_cards_demotes_open_to_extract(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent("I will open the visible products and extract their details.", context=context)

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"


def test_natural_intent_search_under_price_maps_to_search_with_query(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent("Search for glasses under 5 euro.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.capability_id == "real_browser_control"
    assert mapping.envelope.operation == "real_browser.search"
    assert mapping.envelope.params["query"] == "glasses under 5 euro"


def test_natural_intent_verify_cards_maps_to_verify_extraction(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    context = _compile_browser_context(fixture, observations=[opened, extracted])

    mapping = map_browser_model_native_intent("Verify the extracted cards.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.verify_extraction"


def test_natural_intent_finish_requires_verified_evidence(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    extracted = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_product_cards"),
        authority=fixture.authority,
        context=opened.context_cards,
    )
    before_verify = _compile_browser_context(fixture, observations=[opened, extracted])

    premature = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=before_verify)

    assert premature.envelope is not None
    assert premature.envelope.operation == "real_browser.verify_extraction"

    verified = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.verify_extraction"),
        authority=fixture.authority,
        context=extracted.context_cards,
    )
    after_verify = _compile_browser_context(fixture, observations=[opened, extracted, verified])

    finish = map_browser_model_native_intent("I have enough evidence, summarize and finish.", context=after_verify)

    assert finish.envelope is not None
    assert finish.envelope.capability_id == "sentinel_loop"
    assert finish.envelope.operation == "finish"


def test_ambiguous_safe_intent_uses_primary_skill_recommendation(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent("I will continue with the best safe next step.", context=context)

    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"
    assert context["primary_model_recommended_next_action"] != (
        f"{mapping.envelope.capability_id}.{mapping.envelope.operation}"
    )


def test_safe_ambiguous_intent_without_recommendation_recovers_not_blocks() -> None:
    mapping = map_browser_model_native_intent(
        "I will continue with the best safe browser move.",
        context={
            "available_actions": [
                "real_browser_control.real_browser.observe",
                "real_browser_control.real_browser.search",
                "real_browser_control.real_browser.extract_product_cards",
            ],
            "decision_context_primary_truth": "skill_decision_frame",
        },
    )

    assert mapping.blocked is False
    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.observe"
    assert mapping.safe_diagnostics["fallback_reason"] == "BROWSER_INTENT_NO_SAFE_RECOMMENDATION_RECOVERED"


def test_raw_browser_primitives_not_primary_model_schema(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])
    operation_schema = context["allowed_action_schema"]["operation"]

    assert "real_browser.search" in operation_schema
    assert "real_browser.extract_product_cards" in operation_schema
    assert "real_browser.verify_extraction" in operation_schema
    assert "real_browser.type_text" not in operation_schema
    assert "real_browser.click" not in operation_schema


def test_hidden_or_disabled_ref_recovers_but_secret_ref_hard_stops(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=InMemoryRealBrowserEngine())
    fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )

    for ref in ("button:hidden", "button:disabled"):
        result = fixture.runtime.execute(
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", target_ref=ref),
            authority=fixture.authority,
            context={},
        )
        assert result.recoverable is True
        assert result.failure_class is ActionFailureClass.RECOVERABLE_BROWSER_STATE_FAILURE

    with pytest.raises(RealBrowserControlRuntimeError, match="real_browser_secret_field_blocked"):
        fixture.runtime.execute(
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                target_ref="input:masked",
                params={"text": "not-a-secret"},
            ),
            authority=fixture.authority,
            context={},
        )


def test_hard_boundary_intent_blocks_contact_supplier_payment_login_credentials(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    context = _compile_browser_context(fixture, observations=[])

    for intent in (
        "Log in to Alibaba with credentials.",
        "Contact the supplier about this product.",
        "Add it to cart and checkout with payment.",
        "Use the cookie/session to continue.",
    ):
        mapping = map_browser_model_native_intent(intent, context=context)
        assert mapping.blocked is True
        assert mapping.blocked_reason == "BROWSER_INTENT_HARD_BOUNDARY"
        assert mapping.envelope is None


def test_metadata_reply_with_natural_intent_is_parsed_without_raw_persistence(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    opened = fixture.runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    context = _compile_browser_context(fixture, observations=[opened])

    mapping = map_browser_model_native_intent(
        {
            "metadata": {"finish_reason": "stop"},
            "reply": "I will extract the visible product cards now.",
        },
        context=context,
    )

    assert mapping.envelope is not None
    assert mapping.envelope.operation == "real_browser.extract_product_cards"
    diagnostics_text = str(mapping.safe_diagnostics)
    assert "I will extract the visible product cards now" not in diagnostics_text
    assert "raw_provider" not in diagnostics_text
    assert "reasoning" not in diagnostics_text


def test_action_envelope_remains_internal_runtime_format(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=False))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent("Search for glasses under 5 euro.", context=context)

    assert isinstance(mapping.envelope, ActionEnvelope)
    assert mapping.safe_diagnostics["model_input_kind"] == "natural_intent"
    assert mapping.safe_diagnostics["internal_runtime_format"] == "ActionEnvelope"


def test_no_raw_provider_output_or_reasoning_persisted(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    context = _compile_browser_context(fixture, observations=[])

    mapping = map_browser_model_native_intent(
        {"reply": "Search for glasses under 5 euro.", "metadata": {"safe_provider_latency_ms": 12}},
        context=context,
    )

    persisted = str(mapping.safe_model_dump()).lower()
    assert "search for glasses under 5 euro" not in persisted
    assert "raw_provider" not in persisted
    assert "raw_response" not in persisted
    assert "reasoning_content" not in persisted


def test_replay_no_react_still_holds(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_HardProductSearchEngine(results_visible=True))
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            {"metadata": {"finish_reason": "stop"}, "reply": "I will extract the visible product cards now."},
            {"reply": "Verify the extracted cards."},
            {"reply": "I have enough evidence, summarize and finish."},
        ]
    )

    result = fixture.loop(decisions).run()
    replay = RealBrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert replay.browser_open_delta == 0
    assert replay.browser_type_delta == 0
    assert replay.browser_extract_delta == 0
    assert replay.receipt_writes_delta == 0
    assert loop_replay.model_calls_delta == 0
    assert loop_replay.real_browser_open_delta == 0
    assert loop_replay.real_browser_extract_delta == 0


def test_loop_guard_does_not_preempt_first_extraction_when_cards_visible(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "Search again for a different query: sunglasses under 5 euro.",
            "I will continue with the visible product cards.",
            "Verify the extracted cards.",
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=2).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert "real_browser_control:real_browser.search" in result.capability_sequence
    assert "real_browser_control:real_browser.extract_product_cards" in result.capability_sequence
    assert result.receipt_refs


def test_finalgate_not_written_for_recoverable_pre_extraction_miss(tmp_path: Path) -> None:
    fixture = _BrowserSkillFixture(tmp_path, engine=_TimeoutSearchEngineWithCards())
    decisions = _RawNativeIntentDecisionClient(
        [
            "Open the bounded Alibaba page.",
            "Search again for a different query: sunglasses under 5 euro.",
            "I will continue with the visible product cards.",
            "Verify the extracted cards.",
            "I have enough evidence, summarize and finish.",
        ]
    )

    result = fixture.loop(decisions, max_recovery_turns=2).run()
    mission_text = _mission_text(fixture.kernel, fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert "RECOVERY_BUDGET_EXHAUSTED" not in mission_text
    assert "BROWSER_INTENT_NO_SAFE_RECOMMENDATION" not in mission_text
    assert "model_led_task_loop_blocked" not in mission_text


def test_pack_a_f_regressions_still_pass() -> None:
    actionability_frame = build_default_actionability_registry().compile_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
    )
    backend_frame = build_default_power_skill_registry().compile_backend_frame(
        available_actions=_browser_actions(),
        granted_capabilities=("real_browser_control",),
    )

    assert actionability_frame.invariant == "model_visible_actions_require_executor_authority_proof_and_recovery_policy"
    assert _backend_by_skill(backend_frame, "real_browser_control")["proof_contract"] == "RealBrowserActionReceipt"


def _backend_by_skill(frame: dict[str, Any], skill_id: str) -> dict[str, Any]:
    for backend in frame.get("skill_backends", []):
        if backend.get("skill_id") == skill_id:
            return backend
    raise AssertionError(f"missing backend for {skill_id}")


def _browser_actions() -> tuple[str, ...]:
    return (
        "real_browser_control.real_browser.open",
        "real_browser_control.real_browser.observe",
        "real_browser_control.real_browser.search",
        "real_browser_control.real_browser.inspect_result",
        "real_browser_control.real_browser.open_result",
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
        "real_browser_control.real_browser.extract_text",
        "real_browser_control.real_browser.assert_text",
        "real_browser_control.real_browser.click",
        "real_browser_control.real_browser.type_text",
        "real_browser_control.real_browser.press_key",
        "real_browser_control.real_browser.wait_for_text",
        "sentinel_loop.finish",
    )


def _compile_browser_context(
    fixture: "_BrowserSkillFixture",
    *,
    observations: list[Any],
    model_calls_used: int = 0,
    material_actions_used: int = 0,
) -> dict[str, Any]:
    return DecisionContextCompiler().compile(
        mission_id=fixture.mission_id,
        mission_objective=fixture.authority.mission_objective,
        authority=fixture.authority,
        observations=observations,
        available_actions=_browser_actions(),
        model_calls_used=model_calls_used,
        material_actions_used=material_actions_used,
        max_model_calls=8,
        max_material_actions=4,
        recovery_turns_used=0,
        max_recovery_turns=2,
        correction_turns_used=0,
        max_correction_turns=2,
    )


class _RawNativeIntentDecisionClient:
    def __init__(self, intents: list[Any]) -> None:
        self._intents = list(intents)
        self.call_count = 0
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> Any:
        self.contexts.append(context)
        self.call_count += 1
        if not self._intents:
            raise AssertionError("native intent decisions exhausted")
        return self._intents.pop(0)


class _BrowserSkillFixture:
    def __init__(
        self,
        tmp_path: Path,
        *,
        engine: InMemoryRealBrowserEngine,
        backend_selection: Any | None = None,
        selected_backend_id: str | None = None,
    ) -> None:
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack6d",
            draft=MissionDraft(
                title="Model-led browser skill spine",
                objective="Search a bounded catalog page and extract one product card.",
                constraints=["bounded browser URL", "receipts always", "no login/contact/payment"],
                expected_artifacts=["real browser action receipts"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack6d",
                allowed_actions=[
                    "real_browser.open",
                    "real_browser.observe",
                    "real_browser.search",
                    "real_browser.inspect_result",
                    "real_browser.open_result",
                    "real_browser.extract_product_cards",
                    "real_browser.verify_extraction",
                    "real_browser.extract_text",
                    "real_browser.assert_text",
                    "real_browser.click",
                    "real_browser.type_text",
                    "real_browser.press_key",
                    "real_browser.wait_for_text",
                    "finish",
                ],
                forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
                summary="Bounded browser skill search/extraction is granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.engine = engine
        runtime_kwargs: dict[str, Any] = {
            "kernel": self.kernel,
            "mission_id": self.mission_id,
            "engine": self.engine,
            "bounded_url_ref": "env:SENTINEL_BROWSER_TEST_URL",
        }
        if backend_selection is not None:
            runtime_kwargs["browser_backend_selection"] = backend_selection
        if selected_backend_id is not None:
            runtime_kwargs["selected_backend_id"] = selected_backend_id
        self.runtime = RealBrowserControlRuntime(**runtime_kwargs)
        self.action_kernel = ActionKernel(
            executors={
                "real_browser_control": lambda envelope, context: self.runtime.execute(
                    envelope,
                    authority=self.authority,
                    context=context,
                )
            }
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led browser skill spine",
            mission_objective="Search a bounded catalog page and extract one product card.",
            allowed_tools=["real_browser_control"],
            allowed_actions=[action.replace("real_browser_control.", "") for action in _browser_actions() if action != "sentinel_loop.finish"]
            + ["finish"],
            forbidden_actions=["login", "contact_supplier", "checkout", "payment", "credential_access"],
            allowed_domains=["real_browser:bounded_test_url"],
            max_actions=12,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )

    def loop(self, decisions: ModelLedTaskDecisionClient, *, max_recovery_turns: int = 2) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decisions,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=8, max_material_actions=4, max_recovery_turns=max_recovery_turns)),
            available_actions=_browser_actions(),
        )

    def load_action_receipt(self, receipt_ref: str) -> dict[str, Any]:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        import json

        return json.loads(path.read_text(encoding="utf-8"))


class _HardProductSearchEngine(InMemoryRealBrowserEngine):
    def __init__(self, *, results_visible: bool = True) -> None:
        super().__init__()
        self.search_query = ""
        self.results_visible = results_visible
        self.display_text = "Catalog search page."
        if results_visible:
            self.display_text = _PRODUCT_TEXT

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        elements = [
            RealBrowserEngineElement("input:search", "textbox", "Search products", value_preview=self.search_query),
            RealBrowserEngineElement("button:search", "button", "Search", text_preview="Search"),
        ]
        if self.results_visible:
            elements.append(
                RealBrowserEngineElement(
                    "link:glasses_card",
                    "link",
                    "Polarized sunglasses $4.80 MOQ 10 pieces",
                    text_preview="Polarized sunglasses $4.80 MOQ 10 pieces Yiwu Test Store shipping not included",
                )
            )
        elements.append(RealBrowserEngineElement("input:secret", "textbox", "password", secret=True))
        return tuple(elements)

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self._require_editable(ref)
        self.type_count += 1
        self.search_query = text
        self.status_value = text
        return self._snapshot()

    def press_key(self, ref: str, key: str) -> RealBrowserEngineSnapshot:
        self._require_editable(ref)
        self.press_count += 1
        if key == "Enter" and self.search_query:
            self.results_visible = True
            self.display_text = _PRODUCT_TEXT
        return self._snapshot()

    def click(self, ref: str) -> RealBrowserEngineSnapshot:
        element = self._require_interactable(ref)
        self.click_count += 1
        if element.ref == "button:search" and self.search_query:
            self.results_visible = True
            self.display_text = _PRODUCT_TEXT
        return self._snapshot()

    def extract_text(self) -> tuple[str, RealBrowserEngineSnapshot]:
        self._require_open()
        self.extract_count += 1
        return self.display_text, self._snapshot()


class _AlternateSearchEngine(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=False)
        self.attempted_refs: list[str] = []

    def _elements(self) -> tuple[RealBrowserEngineElement, ...]:
        return (
            RealBrowserEngineElement("input:broken_search", "textbox", "Search broken"),
            *super()._elements(),
        )

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        self.attempted_refs.append(ref)
        if ref == "input:broken_search":
            raise RealBrowserControlRuntimeError("real_browser_locator_timeout")
        return super().type_text(ref, text)


class _TimeoutSearchEngine(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=False)

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        del ref, text
        raise RealBrowserControlRuntimeError("real_browser_locator_timeout")


class _TimeoutSearchEngineWithCards(_HardProductSearchEngine):
    def __init__(self) -> None:
        super().__init__(results_visible=True)

    def type_text(self, ref: str, text: str) -> RealBrowserEngineSnapshot:
        del ref, text
        raise RealBrowserControlRuntimeError("real_browser_locator_timeout")


class _PlaywrightCompatibilitySearchEngine(_HardProductSearchEngine):
    browser_backend_id = "playwright_real_browser_engine"


_PRODUCT_TEXT = (
    "Search results for glasses under 5 euro. Polarized sunglasses. "
    "Price $4.80 per piece. MOQ 10 pieces. Supplier Yiwu Test Store. "
    "Caveats: shipping not included, customization unclear."
)


def _mission_text(kernel: MissionKernel, mission_id: str) -> str:
    root = kernel.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))


def _real_browser_artifact_text(kernel: MissionKernel, mission_id: str) -> str:
    root = kernel.store.mission_dir(mission_id) / "real_browser_control"
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
