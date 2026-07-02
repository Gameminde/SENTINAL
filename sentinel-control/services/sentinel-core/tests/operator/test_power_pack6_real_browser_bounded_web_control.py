from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel
from sentinel.operator.browser_action_candidates import BrowserActionExtractionError, extract_browser_action_envelope
from sentinel.operator.browser_decision_frame import BrowserDecisionFrameCompiler
from sentinel.operator.browser_world_model import BrowserWorldModelBuilder
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopReplay, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.real_browser_control_models import (
    RealBrowserActionReceipt,
    RealBrowserAssertionReceipt,
    RealBrowserObservationReceipt,
    RealBrowserOpenReceipt,
)
from sentinel.operator.real_browser_control_replay import RealBrowserControlReplayView
from sentinel.operator.real_browser_control_runtime import (
    InMemoryRealBrowserEngine,
    RealBrowserControlRuntime,
    RealBrowserControlRuntimeError,
    build_playwright_real_browser_engine_from_env,
)


def test_power_pack6_real_browser_open_and_observe_returns_stable_role_refs(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)

    opened = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    observed = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.observe"),
        authority=fixture.authority,
        context={},
    )
    open_receipt = fixture.load_open_receipt(opened.receipt_refs[0])
    observation_receipt = fixture.load_observation_receipt(observed.receipt_refs[0])

    assert opened.status == "completed"
    assert opened.material_action is False
    assert open_receipt.safe_url_origin_hash
    assert observed.status == "completed"
    assert observed.material_action is False
    assert observation_receipt.page_title == "Sentinel Real Browser Fixture"
    assert [element.ref for element in observation_receipt.elements] == ["input:status", "button:enable_sentinel"]
    assert observation_receipt.elements[0].role == "textbox"
    assert observation_receipt.elements[0].name == "status"
    assert observation_receipt.elements[0].visible is True
    assert observation_receipt.elements[0].enabled is True
    assert observation_receipt.elements[0].value_preview == ""


def test_power_pack6_real_browser_type_assert_and_receipts_do_not_persist_typed_text(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)

    fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    typed = fixture.real_browser_runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.type_text",
            params={"ref": "input:status", "text": "Sentinel real browser control worked"},
        ),
        authority=fixture.authority,
        context={},
    )
    assertion = fixture.real_browser_runtime.execute(
        ActionEnvelope(
            capability_id="real_browser_control",
            operation="real_browser.assert_text",
            params={"text": "Sentinel real browser control worked"},
        ),
        authority=fixture.authority,
        context={},
    )

    assert typed.status == "completed"
    assert typed.material_action is True
    assert assertion.status == "passed"
    assert assertion.material_action is False
    assert fixture.engine.status_value == "Sentinel real browser control worked"
    assert fixture.load_action_receipt(typed.receipt_refs[0]).action_kind == "real_browser.type_text"
    assert fixture.load_assertion_receipt(assertion.receipt_refs[0]).status == "passed"
    persisted = _mission_text(fixture.kernel, fixture.mission_id)
    assert "Sentinel real browser control worked" not in persisted
    assert "raw_provider" not in persisted
    assert "reasoning_content" not in persisted
    assert "cookie" not in persisted.lower()


def test_power_pack6_real_browser_click_changes_state_and_extract_text_is_receipted_without_raw_dump(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)

    fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    clicked = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:enable_sentinel"}),
        authority=fixture.authority,
        context={},
    )
    extracted = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_text"),
        authority=fixture.authority,
        context={},
    )

    assert clicked.status == "completed"
    assert clicked.material_action is True
    assert fixture.engine.enabled is True
    assert fixture.load_action_receipt(clicked.receipt_refs[0]).action_kind == "real_browser.click"
    assert extracted.status == "completed"
    assert extracted.material_action is False
    assert fixture.load_action_receipt(extracted.receipt_refs[0]).action_kind == "real_browser.extract_text"
    persisted = _mission_text(fixture.kernel, fixture.mission_id)
    assert "Sentinel real browser enabled" not in persisted
    assert "text_hash=" in extracted.observation_summary


def test_power_pack6_real_browser_recovers_refs_but_blocks_secret_and_unbounded_material(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)
    fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )

    recoverable = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:missing"}),
        authority=fixture.authority,
        context={},
    )
    assert recoverable.status == "recoverable_failed"
    assert recoverable.recoverable is True
    assert recoverable.blocked_reason == "real_browser_element_ref_unknown"

    for envelope, reason in (
        (
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:hidden"}),
            "real_browser_element_hidden",
        ),
        (
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:disabled"}),
            "real_browser_element_disabled",
        ),
    ):
        recovered = fixture.real_browser_runtime.execute(envelope, authority=fixture.authority, context={})
        assert recovered.status == "recoverable_failed"
        assert recovered.recoverable is True
        assert recovered.blocked_reason == reason

    blocked = [
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.type_text", params={"ref": "input:masked", "text": "hello"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.type_text", params={"ref": "input:status", "text": "sk-live-secret"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open", params={"url": "https://example.com"}),
    ]

    for envelope in blocked:
        with pytest.raises(RealBrowserControlRuntimeError):
            fixture.real_browser_runtime.execute(envelope, authority=fixture.authority, context={})

    assert fixture.engine.click_count == 0
    assert fixture.engine.type_count == 0


def test_power_pack6_generic_loop_executes_real_browser_open_observe_type_assert_finish(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.observe"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "input:status", "text": "Sentinel real browser control worked"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.assert_text",
                params={"text": "Sentinel real browser control worked"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "real browser verified"}),
        ]
    )

    result = fixture.loop(decisions).run()
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)
    browser_replay = RealBrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED
    assert result.capability_sequence == (
        "real_browser_control:real_browser.open",
        "real_browser_control:real_browser.observe",
        "real_browser_control:real_browser.type_text",
        "real_browser_control:real_browser.assert_text",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 1
    assert decisions.contexts[2]["real_browser_control_summary"]["latest_observation"]["element_count"] == 2
    assert decisions.contexts[3]["progress_state"] == "real_browser_action_needs_assertion"
    assert decisions.contexts[3]["next_recommended_actions"] == [
        "real_browser_control.real_browser.extract_product_cards",
        "real_browser_control.real_browser.verify_extraction",
        "real_browser_control.real_browser.assert_text",
    ]
    assert decisions.contexts[-1]["objective_satisfied"] is True
    assert decisions.contexts[-1]["finish_available"] is True
    assert loop_replay.real_browser_open_delta == 0
    assert loop_replay.real_browser_type_delta == 0
    assert loop_replay.real_browser_assert_delta == 0
    assert browser_replay.browser_open_delta == 0
    assert browser_replay.browser_type_delta == 0
    assert browser_replay.browser_assert_delta == 0
    assert browser_replay.artifact_hashes_stable is True
    assert browser_replay.browser_state_hash_stable is True


def test_power_pack6_finish_before_real_browser_assertion_blocks(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "input:status", "text": "Sentinel real browser control worked"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "too early"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_FINISH_BEFORE_REAL_BROWSER_ASSERTION"
    assert decisions.contexts[-1]["objective_satisfied"] is False
    assert decisions.contexts[-1]["finish_available"] is False


def test_power_pack6_assertion_satisfies_budget_finish_only_turn(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "input:status", "text": "Sentinel real browser control worked"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.assert_text",
                params={"text": "Sentinel real browser control worked"},
            ),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "real browser verified"}),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decisions,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=1)),
        available_actions=fixture.available_actions,
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert result.material_action_count == 1
    assert decisions.contexts[-1]["available_actions"] == ["sentinel_loop.finish"]
    assert decisions.contexts[-1]["objective_satisfied"] is True


def test_power_pack6_playwright_engine_requires_process_scoped_bounded_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTINEL_BROWSER_TEST_URL", raising=False)

    with pytest.raises(RealBrowserControlRuntimeError, match="REAL_BROWSER_TEST_URL_CONFIG_MISSING"):
        build_playwright_real_browser_engine_from_env()


def test_power_pack6b_world_model_after_open_exposes_search_refs_candidates_and_product_cards(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())

    opened = fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )
    world_model = opened.context_cards["browser_world_model"]
    decision_frame = opened.context_cards["browser_decision_frame"]

    assert opened.status == "completed"
    assert world_model["page_kind_guess"] in {"catalog_search", "search_results", "product_listing"}
    assert world_model["search_like_refs"] == ["input:search"]
    assert "button:search" in world_model["button_refs"]
    assert "link:glasses_card" in world_model["link_refs"]
    assert world_model["product_or_result_candidate_cards"][0]["title"] == "Polarized sunglasses"
    assert world_model["product_or_result_candidate_cards"][0]["visible_price"] == "$4.80"
    assert world_model["product_or_result_candidate_cards"][0]["minimum_order"] == "10 pieces"
    assert "real_browser.search" in world_model["recommended_browser_actions"]
    assert "real_browser.extract_product_cards" in world_model["recommended_browser_actions"]
    assert decision_frame["current_progress_state"] == "real_browser_opened_world_model_ready"
    assert "real_browser_control.real_browser.search" in decision_frame["allowed_actions"]
    assert decision_frame["exact_action_envelope_examples"]


def test_power_pack6b_decision_context_after_open_exposes_browser_world_model_frame_and_schema(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "too early"}),
        ]
    )

    result = fixture.loop(decisions).run()
    context = decisions.contexts[1]

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert context["progress_state"] == "real_browser_opened_world_model_ready"
    assert context["recommended_next_action"] == "real_browser_control.real_browser.observe"
    assert context["finish_available"] is False
    assert context["objective_satisfied"] is False
    assert context["browser_world_model_summary"]["search_like_refs"] == ["input:search"]
    assert context["browser_decision_frame"]["current_progress_state"] == "real_browser_opened_world_model_ready"
    assert context["top_stable_refs"]
    assert context["top_action_candidates"]
    assert context["top_link_candidates"] == ["link:glasses_card"]
    assert context["search_like_controls"] == ["input:search"]
    assert context["blocker_signals"] == []
    assert context["allowed_action_schema"]["capability_id"] == "real_browser_control"


def test_power_pack6b_decision_frame_compiler_includes_exact_action_schema() -> None:
    snapshot = _HardSearchBrowserEngine().open()
    world_model = BrowserWorldModelBuilder().build_from_snapshot(
        snapshot,
        mission_objective="Find glasses under 5 EUR.",
        origin_hash="origin_hash",
    )

    frame = BrowserDecisionFrameCompiler().compile(
        mission_objective="Find glasses under 5 EUR.",
        world_model=world_model,
        available_actions=(
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.press_key",
            "real_browser_control.real_browser.extract_text",
            "sentinel_loop.finish",
        ),
        progress_state="real_browser_opened_world_model_ready",
    )

    dumped = frame.safe_model_dump()
    assert dumped["allowed_actions"][0] == "real_browser_control.real_browser.observe"
    assert dumped["top_refs"][0]["ref"] == "input:search"
    assert dumped["candidate_extractions"][0]["title"] == "Polarized sunglasses"
    assert dumped["exact_action_envelope_examples"][0]["capability_id"] == "real_browser_control"
    assert dumped["completion_requirements"]


def test_power_pack6b_model_action_extractor_rejects_metadata_only_with_typed_diagnostic() -> None:
    with pytest.raises(BrowserActionExtractionError) as excinfo:
        extract_browser_action_envelope(
            {
                "metadata": {"provider_response_hash": "hash_only"},
                "reply": "I can help with that.",
                "visible_content_char_count": 25,
                "content_source": "choices[0].message.content",
            },
            allowed_actions=("real_browser_control.real_browser.observe", "sentinel_loop.finish"),
            last_successful_browser_action="real_browser.open",
        )

    diagnostics = excinfo.value.diagnostics
    assert diagnostics["visible_content_present"] is True
    assert diagnostics["json_object_detected"] is True
    assert diagnostics["action_object_detected"] is False
    assert diagnostics["content_source"] == "choices[0].message.content"
    assert diagnostics["top_level_keys"] == ["metadata", "reply", "visible_content_char_count", "content_source"]
    assert diagnostics["failure_code"] == "MODEL_ACTION_SCHEMA_INVALID"
    assert diagnostics["recommended_next_action"] == "real_browser_control.real_browser.observe"
    assert diagnostics["last_successful_browser_action"] == "real_browser.open"


def test_power_pack6b_model_action_extractor_parses_valid_visible_json_without_raw_provider_material() -> None:
    extracted = extract_browser_action_envelope(
        {
            "capability_id": "real_browser_control",
            "operation": "real_browser.type_text",
            "params": {"ref": "input:search", "text": "glasses under 5 euro"},
            "visible_content_char_count": 104,
            "content_source": "choices[0].message.content",
        },
        allowed_actions=(
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.press_key",
        ),
        last_successful_browser_action="real_browser.observe",
    )

    assert extracted.envelope.capability_id == "real_browser_control"
    assert extracted.envelope.operation == "real_browser.type_text"
    assert extracted.envelope.params == {"ref": "input:search", "text": "glasses under 5 euro"}
    assert extracted.diagnostics["action_object_detected"] is True
    assert "raw_provider" not in str(extracted.safe_model_dump())
    assert "reasoning_content" not in str(extracted.safe_model_dump())


def test_power_pack6b_hard_browser_mission_can_search_extract_and_finish_with_replay_purity(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path, engine=_HardSearchBrowserEngine())
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.observe"),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                params={"ref": "input:search", "text": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.press_key",
                params={"ref": "input:search", "key": "Enter"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.wait_for_text",
                params={"text": "MOQ"},
            ),
            ActionEnvelope(capability_id="real_browser_control", operation="real_browser.extract_text"),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "browser search extracted"}),
        ]
    )

    result = fixture.loop(decisions).run()
    replay = RealBrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.engine.type_count == 1
    assert fixture.engine.press_count == 1
    assert fixture.engine.wait_count == 1
    assert fixture.engine.extract_count == 1
    assert decisions.contexts[-1]["objective_satisfied"] is True
    assert decisions.contexts[-1]["finish_available"] is True
    assert decisions.contexts[-2]["browser_world_model_summary"]["product_or_result_candidate_count"] >= 1
    assert replay.browser_open_delta == 0
    assert replay.browser_click_delta == 0
    assert replay.browser_type_delta == 0
    assert replay.browser_press_delta == 0
    assert replay.browser_wait_delta == 0
    assert replay.browser_extract_delta == 0
    assert replay.artifact_hashes_stable is True


class _RealBrowserFixture:
    def __init__(self, tmp_path: Path, *, engine: InMemoryRealBrowserEngine | None = None) -> None:
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack6",
            draft=MissionDraft(
                title="Model-led real browser control",
                objective="Let the model operate a bounded real browser page and verify the state changed.",
                constraints=["bounded browser URL", "receipts always", "no arbitrary internet"],
                expected_artifacts=["real browser action receipts"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack6",
                allowed_actions=[
                    "real_browser.open",
                    "real_browser.observe",
                    "real_browser.search",
                    "real_browser.inspect_result",
                    "real_browser.open_result",
                    "real_browser.extract_product_cards",
                    "real_browser.verify_extraction",
                    "real_browser.click",
                    "real_browser.type_text",
                    "real_browser.select_option",
                    "real_browser.assert_text",
                    "real_browser.extract_text",
                    "real_browser.press_key",
                    "real_browser.wait_for_text",
                    "real_browser.wait_for_load",
                    "real_browser.scroll",
                    "finish",
                ],
                forbidden_actions=["payment", "credential_access", "arbitrary_internet", "desktop"],
                summary="Bounded real browser control is granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.engine = engine or InMemoryRealBrowserEngine()
        self.real_browser_runtime = RealBrowserControlRuntime(
            kernel=self.kernel,
            mission_id=self.mission_id,
            engine=self.engine,
            bounded_url_ref="env:SENTINEL_BROWSER_TEST_URL",
        )
        self.action_kernel = ActionKernel(
            executors={
                "real_browser_control": lambda envelope, context: self.real_browser_runtime.execute(
                    envelope,
                    authority=self.authority,
                    context=context,
                )
            }
        )
        self.available_actions = (
            "real_browser_control.real_browser.open",
            "real_browser_control.real_browser.observe",
            "real_browser_control.real_browser.search",
            "real_browser_control.real_browser.inspect_result",
            "real_browser_control.real_browser.open_result",
            "real_browser_control.real_browser.extract_product_cards",
            "real_browser_control.real_browser.verify_extraction",
            "real_browser_control.real_browser.click",
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.select_option",
            "real_browser_control.real_browser.assert_text",
            "real_browser_control.real_browser.extract_text",
            "real_browser_control.real_browser.press_key",
            "real_browser_control.real_browser.wait_for_text",
            "real_browser_control.real_browser.wait_for_load",
            "real_browser_control.real_browser.scroll",
            "sentinel_loop.finish",
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led real browser control",
            mission_objective="Operate the granted bounded browser URL.",
            allowed_tools=["real_browser_control"],
            allowed_actions=[
                "real_browser.open",
                "real_browser.observe",
                "real_browser.search",
                "real_browser.inspect_result",
                "real_browser.open_result",
                "real_browser.extract_product_cards",
                "real_browser.verify_extraction",
                "real_browser.click",
                "real_browser.type_text",
                "real_browser.select_option",
                "real_browser.assert_text",
                "real_browser.extract_text",
                "real_browser.press_key",
                "real_browser.wait_for_text",
                "real_browser.wait_for_load",
                "real_browser.scroll",
                "finish",
            ],
            forbidden_actions=["payment", "credential_access", "arbitrary_internet", "desktop"],
            allowed_domains=["real_browser:bounded_test_url"],
            max_actions=10,
            expires_at=now + timedelta(minutes=30),
        )

    def loop(self, decision_client: ModelLedTaskDecisionClient) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decision_client,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=7, max_material_actions=4)),
            available_actions=self.available_actions,
        )

    def load_open_receipt(self, receipt_ref: str) -> RealBrowserOpenReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        return RealBrowserOpenReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def load_observation_receipt(self, receipt_ref: str) -> RealBrowserObservationReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        return RealBrowserObservationReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def load_action_receipt(self, receipt_ref: str) -> RealBrowserActionReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        return RealBrowserActionReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def load_assertion_receipt(self, receipt_ref: str) -> RealBrowserAssertionReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "real_browser_control" / "receipts" / f"{receipt_ref}.json"
        return RealBrowserAssertionReceipt.model_validate_json(path.read_text(encoding="utf-8"))


def _mission_text(kernel: MissionKernel, mission_id: str) -> str:
    root = kernel.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))


class _HardSearchBrowserEngine(InMemoryRealBrowserEngine):
    def __init__(self) -> None:
        super().__init__()
        self.title = "Alibaba Search Fixture"
        self.search_query = ""
        self.results_visible = True
        self.press_count = 0
        self.wait_count = 0
        self.scroll_count = 0
        self.display_text = (
            "Search products. Polarized sunglasses, visible price $4.80 per piece, "
            "MOQ 10 pieces, supplier Yiwu Test Store, caveat shipping not included."
        )

    def _elements(self):  # type: ignore[no-untyped-def]
        from sentinel.operator.real_browser_control_models import RealBrowserElementSnapshot

        elements = [
            RealBrowserElementSnapshot(
                ref="input:search",
                role="textbox",
                name="Search products",
                visible=True,
                enabled=True,
                value_preview=self.search_query,
            ),
            RealBrowserElementSnapshot(
                ref="button:search",
                role="button",
                name="Search",
                visible=True,
                enabled=True,
            ),
        ]
        if self.results_visible:
            elements.append(
                RealBrowserElementSnapshot(
                    ref="link:glasses_card",
                    role="link",
                    name="Polarized sunglasses $4.80 MOQ 10 pieces",
                    visible=True,
                    enabled=True,
                    text_preview="Polarized sunglasses $4.80 MOQ 10 pieces Yiwu Test Store",
                )
            )
        return elements

    def type_text(self, ref: str, text: str):  # type: ignore[no-untyped-def]
        if ref != "input:search":
            return super().type_text(ref, text)
        self._require_editable(ref)
        self.type_count += 1
        self.search_query = text
        return self.observe()

    def press_key(self, ref: str, key: str):  # type: ignore[no-untyped-def]
        self._require_editable(ref)
        self.press_count += 1
        if key == "Enter" and self.search_query:
            self.results_visible = True
            self.display_text = (
                "Search results for glasses under 5 euro. Polarized sunglasses. "
                "Price $4.80 per piece. MOQ 10 pieces. Supplier Yiwu Test Store. "
                "Caveats: shipping not included, customization unclear."
            )
        return self.observe()

    def wait_for_text(self, text: str, timeout_ms: int = 1000):  # type: ignore[no-untyped-def]
        self.wait_count += 1
        return text in self.display_text, self.observe()

    def wait_for_load(self):  # type: ignore[no-untyped-def]
        self.wait_count += 1
        return self.observe()

    def scroll(self, delta_y: int = 600):  # type: ignore[no-untyped-def]
        self.scroll_count += 1
        return self.observe()


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
