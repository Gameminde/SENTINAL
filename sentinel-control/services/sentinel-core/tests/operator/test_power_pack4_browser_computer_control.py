from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError
from sentinel.operator.browser_control_models import BrowserActionReceipt, BrowserAssertionReceipt, BrowserObservationReceipt
from sentinel.operator.browser_control_replay import BrowserControlReplayView
from sentinel.operator.browser_control_runtime import BrowserControlRuntime, BrowserControlRuntimeError
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopReplay, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus


def test_power_pack4_browser_observe_returns_stable_role_refs(tmp_path: Path) -> None:
    fixture = _BrowserFixture(tmp_path)

    result = fixture.browser_runtime.execute(
        ActionEnvelope(capability_id="browser_control", operation="browser.observe"),
        authority=fixture.authority,
        context={},
    )
    receipt = fixture.load_observation_receipt(result.receipt_refs[0])

    assert result.status == "completed"
    assert result.material_action is False
    assert result.receipt_refs[0].startswith("browser_observation_")
    assert receipt.page_title == "Sentinel Browser Fixture"
    assert [element.ref for element in receipt.elements] == ["button:enable_sentinel", "input:status"]
    assert receipt.elements[0].role == "button"
    assert receipt.elements[0].name == "Enable Sentinel"
    assert receipt.elements[1].role == "textbox"
    assert receipt.elements[1].name == "status"


def test_power_pack4_browser_click_type_and_assert_change_fixture_state_with_receipts(tmp_path: Path) -> None:
    fixture = _BrowserFixture(tmp_path)

    click = fixture.browser_runtime.execute(
        ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:enable_sentinel"}),
        authority=fixture.authority,
        context={},
    )
    typed = fixture.browser_runtime.execute(
        ActionEnvelope(
            capability_id="browser_control",
            operation="browser.type_text",
            params={"ref": "input:status", "text": "Sentinel browser control worked"},
        ),
        authority=fixture.authority,
        context={},
    )
    assertion = fixture.browser_runtime.execute(
        ActionEnvelope(capability_id="browser_control", operation="browser.assert_text", params={"text": "Sentinel browser control worked"}),
        authority=fixture.authority,
        context={},
    )

    assert click.status == "completed"
    assert typed.status == "completed"
    assert assertion.status == "passed"
    assert click.material_action is True
    assert typed.material_action is True
    assert assertion.material_action is False
    assert fixture.browser_runtime.state.display_text == "Sentinel browser control worked"
    assert fixture.load_action_receipt(click.receipt_refs[0]).action_kind == "browser.click"
    assert fixture.load_action_receipt(typed.receipt_refs[0]).action_kind == "browser.type_text"
    assert fixture.load_assertion_receipt(assertion.receipt_refs[0]).status == "passed"


def test_power_pack4_browser_unknown_disabled_secret_and_unbounded_material_block(tmp_path: Path) -> None:
    fixture = _BrowserFixture(tmp_path)

    blocked = [
        ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:missing"}),
        ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:hidden"}),
        ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:disabled"}),
        ActionEnvelope(capability_id="browser_control", operation="browser.type_text", params={"ref": "input:secret", "text": "hello"}),
        ActionEnvelope(capability_id="browser_control", operation="browser.type_text", params={"ref": "input:status", "text": "sk-live-secret"}),
        ActionEnvelope(capability_id="browser_control", operation="browser.navigate_fixture", params={"url": "https://example.com"}),
    ]

    for envelope in blocked:
        with pytest.raises(BrowserControlRuntimeError):
            fixture.browser_runtime.execute(envelope, authority=fixture.authority, context={})

    assert fixture.browser_runtime.click_count == 0
    assert fixture.browser_runtime.type_count == 0


def test_power_pack4_generic_loop_executes_browser_observe_click_type_assert_finish(tmp_path: Path) -> None:
    fixture = _BrowserFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="browser_control", operation="browser.observe"),
            ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:enable_sentinel"}),
            ActionEnvelope(
                capability_id="browser_control",
                operation="browser.type_text",
                params={"ref": "input:status", "text": "Sentinel browser control worked"},
            ),
            ActionEnvelope(capability_id="browser_control", operation="browser.assert_text", params={"text": "Sentinel browser control worked"}),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "browser fixture verified"}),
        ]
    )

    result = fixture.loop(decisions).run()
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)
    browser_replay = BrowserControlReplayView.from_store(fixture.kernel.store, mission_id=fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED
    assert result.capability_sequence == (
        "browser_control:browser.observe",
        "browser_control:browser.click",
        "browser_control:browser.type_text",
        "browser_control:browser.assert_text",
        "sentinel_loop:finish",
    )
    assert result.material_action_count == 2
    assert decisions.contexts[1]["browser_control_summary"]["latest_observation"]["element_count"] == 2
    assert decisions.contexts[3]["next_recommended_actions"] == ["browser_control.browser.assert_text"]
    assert decisions.contexts[-1]["objective_satisfied"] is True
    assert loop_replay.browser_click_delta == 0
    assert loop_replay.browser_type_delta == 0
    assert loop_replay.browser_assert_delta == 0
    assert browser_replay.browser_click_delta == 0
    assert browser_replay.browser_type_delta == 0
    assert browser_replay.browser_assert_delta == 0
    assert browser_replay.artifact_hashes_stable is True
    assert browser_replay.browser_state_hash_stable is True


def test_power_pack4_finish_before_browser_assertion_blocks(tmp_path: Path) -> None:
    fixture = _BrowserFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="browser_control", operation="browser.observe"),
            ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:enable_sentinel"}),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "too early"}),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_FINISH_BEFORE_BROWSER_ASSERTION"
    assert decisions.contexts[-1]["objective_satisfied"] is False
    assert decisions.contexts[-1]["finish_available"] is False


def test_power_pack4_browser_assertion_satisfies_budget_finish_only_turn(tmp_path: Path) -> None:
    fixture = _BrowserFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="browser_control", operation="browser.click", params={"ref": "button:enable_sentinel"}),
            ActionEnvelope(
                capability_id="browser_control",
                operation="browser.type_text",
                params={"ref": "input:status", "text": "Sentinel browser control worked"},
            ),
            ActionEnvelope(capability_id="browser_control", operation="browser.assert_text", params={"text": "Sentinel browser control worked"}),
            ActionEnvelope(capability_id="sentinel_loop", operation="finish", params={"safe_summary": "browser verified"}),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decisions,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=2)),
        available_actions=fixture.available_actions,
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert result.material_action_count == 2
    assert decisions.contexts[-1]["available_actions"] == ["finish"]
    assert decisions.contexts[-1]["objective_satisfied"] is True


class _BrowserFixture:
    def __init__(self, tmp_path: Path) -> None:
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack4",
            draft=MissionDraft(
                title="Model-led browser control",
                objective="Let the model operate a bounded browser fixture and verify the state changed.",
                constraints=["bounded browser fixture", "receipts always", "no arbitrary internet"],
                expected_artifacts=["browser action receipts"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack4",
                allowed_actions=[
                    "browser.observe",
                    "browser.click",
                    "browser.type_text",
                    "browser.select_option",
                    "browser.assert_text",
                    "browser.finish_browser_step",
                    "finish",
                ],
                forbidden_actions=["payment", "credential_access", "arbitrary_internet", "desktop"],
                summary="Bounded browser fixture control is granted.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.browser_runtime = BrowserControlRuntime(kernel=self.kernel, mission_id=self.mission_id)
        self.action_kernel = ActionKernel(
            executors={
                "browser_control": lambda envelope, context: self.browser_runtime.execute(
                    envelope,
                    authority=self.authority,
                    context=context,
                )
            }
        )
        self.available_actions = (
            "browser_control.browser.observe",
            "browser_control.browser.click",
            "browser_control.browser.type_text",
            "browser_control.browser.select_option",
            "browser_control.browser.assert_text",
            "browser_control.browser.finish_browser_step",
            "finish",
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led browser control",
            mission_objective="Operate the Sentinel Browser Fixture inside the granted browser scope.",
            allowed_tools=["browser_control"],
            allowed_actions=[
                "browser.observe",
                "browser.click",
                "browser.type_text",
                "browser.select_option",
                "browser.assert_text",
                "browser.finish_browser_step",
                "finish",
            ],
            forbidden_actions=["payment", "credential_access", "arbitrary_internet", "desktop"],
            allowed_domains=["fixture:sentinel-browser"],
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

    def load_observation_receipt(self, receipt_ref: str) -> BrowserObservationReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "browser_control" / "receipts" / f"{receipt_ref}.json"
        return BrowserObservationReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def load_action_receipt(self, receipt_ref: str) -> BrowserActionReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "browser_control" / "receipts" / f"{receipt_ref}.json"
        return BrowserActionReceipt.model_validate_json(path.read_text(encoding="utf-8"))

    def load_assertion_receipt(self, receipt_ref: str) -> BrowserAssertionReceipt:
        path = self.kernel.store.mission_dir(self.mission_id) / "browser_control" / "receipts" / f"{receipt_ref}.json"
        return BrowserAssertionReceipt.model_validate_json(path.read_text(encoding="utf-8"))


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
