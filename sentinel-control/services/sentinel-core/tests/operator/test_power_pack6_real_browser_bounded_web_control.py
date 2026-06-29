from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel
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


def test_power_pack6_real_browser_blocks_unknown_secret_disabled_and_unbounded_material(tmp_path: Path) -> None:
    fixture = _RealBrowserFixture(tmp_path)
    fixture.real_browser_runtime.execute(
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.open"),
        authority=fixture.authority,
        context={},
    )

    blocked = [
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:missing"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:hidden"}),
        ActionEnvelope(capability_id="real_browser_control", operation="real_browser.click", params={"ref": "button:disabled"}),
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
        "real_browser_control.real_browser.assert_text",
        "real_browser_control.real_browser.extract_text",
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


class _RealBrowserFixture:
    def __init__(self, tmp_path: Path) -> None:
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
                    "real_browser.click",
                    "real_browser.type_text",
                    "real_browser.select_option",
                    "real_browser.assert_text",
                    "real_browser.extract_text",
                    "finish",
                ],
                forbidden_actions=["payment", "credential_access", "arbitrary_internet", "desktop"],
                summary="Bounded real browser control is granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.engine = InMemoryRealBrowserEngine()
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
            "real_browser_control.real_browser.click",
            "real_browser_control.real_browser.type_text",
            "real_browser_control.real_browser.select_option",
            "real_browser_control.real_browser.assert_text",
            "real_browser_control.real_browser.extract_text",
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
                "real_browser.click",
                "real_browser.type_text",
                "real_browser.select_option",
                "real_browser.assert_text",
                "real_browser.extract_text",
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


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
