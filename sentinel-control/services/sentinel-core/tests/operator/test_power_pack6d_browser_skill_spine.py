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


def test_playwright_backend_requires_explicit_compatibility_selection() -> None:
    selection = select_browser_backend(available_backend_modules=("sentinel.operator.real_browser_control_runtime",))

    assert selection.preferred_backend_id is None
    assert selection.compatibility_backend_id == "playwright_real_browser_engine"
    assert selection.playwright_requires_explicit_compatibility is True


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


class _BrowserSkillFixture:
    def __init__(self, tmp_path: Path, *, engine: InMemoryRealBrowserEngine) -> None:
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
        self.runtime = RealBrowserControlRuntime(
            kernel=self.kernel,
            mission_id=self.mission_id,
            engine=self.engine,
            bounded_url_ref="env:SENTINEL_BROWSER_TEST_URL",
        )
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
