from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import (
    ModelLedTaskDecisionClient,
    ModelLedTaskLoop,
    ModelLedTaskLoopStatus,
)
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus


def test_hidden_internal_browser_primitive_recovers_without_executor_call(tmp_path: Path) -> None:
    fixture = _ExecutableTruthFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.type_text",
                target_ref="search_box",
                params={"text": "glasses under 5 euro"},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
                params={},
            ),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.executor_calls == ["real_browser.extract_product_cards"]
    assert fixture.loop_results[0].recoverable is True
    assert fixture.loop_results[0].failure_class is ActionFailureClass.RECOVERABLE_MODEL_PROTOCOL_FAILURE
    assert fixture.loop_results[0].failure_code == "MODEL_ACTION_HIDDEN_INTERNAL"
    assert "real_browser_control.real_browser.extract_product_cards" in fixture.loop_results[0].recommended_next_actions
    assert fixture.loop_results[0].receipt_refs == ()
    assert result.receipt_refs == ("receipt_extract_cards",)


def test_unregistered_model_action_recovers_to_visible_skill_truth(tmp_path: Path) -> None:
    fixture = _ExecutableTruthFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="ghost_browser",
                operation="poke_dom",
                params={},
            ),
            ActionEnvelope(
                capability_id="real_browser_control",
                operation="real_browser.extract_product_cards",
                params={},
            ),
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.executor_calls == ["real_browser.extract_product_cards"]
    assert fixture.loop_results[0].failure_code == "MODEL_ACTION_NOT_REGISTERED"
    assert fixture.loop_results[0].recoverable is True
    assert "real_browser_control.real_browser.extract_product_cards" in fixture.loop_results[0].recommended_next_actions


def test_locked_payment_action_remains_hard_stop(tmp_path: Path) -> None:
    fixture = _ExecutableTruthFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="payment_authority",
                operation="submit",
                params={"amount": "5"},
            )
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_ACTION_LOCKED_HARD_STOP"
    assert fixture.executor_calls == []
    assert result.receipt_refs == ()


class _ExecutableTruthFixture:
    def __init__(self, tmp_path: Path) -> None:
        self.executor_calls: list[str] = []
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_cleanup",
            draft=MissionDraft(
                title="Executable skill truth",
                objective="Only expose executable model-facing skill truth.",
                constraints=["hard stops remain terminal"],
                expected_artifacts=["recoverable observations", "receipts"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_cleanup",
                allowed_actions=["real_browser.extract_product_cards", "finish"],
                forbidden_actions=["payment", "credentials"],
                summary="Browser extraction is granted; payment remains blocked.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self._envelope()
        self.action_kernel = ActionKernel(executors={"real_browser_control": self._execute_real_browser})
        self.loop_results: list[ActionResult] = []

    def loop(self, decision_client: ModelLedTaskDecisionClient) -> ModelLedTaskLoop:
        loop = ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decision_client,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(
                LoopGuardConfig(max_model_calls=4, max_material_actions=1, max_recovery_turns=2, max_correction_turns=2)
            ),
            available_actions=(
                "real_browser_control.real_browser.type_text",
                "real_browser_control.real_browser.click",
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.verify_extraction",
                "sentinel_loop.finish",
                "payment_authority.submit",
            ),
        )
        self.loop_results = loop.results
        return loop

    def _envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_power_cleanup",
            mission_title="Executable skill truth",
            mission_objective="Only expose executable model-facing skill truth.",
            allowed_tools=["real_browser_control"],
            allowed_actions=[
                "real_browser_control.real_browser.extract_product_cards",
                "real_browser_control.real_browser.verify_extraction",
                "sentinel_loop.finish",
            ],
            forbidden_actions=["payment", "credential_access"],
            allowed_domains=["bounded.test"],
            allowed_paths=[],
            max_actions=4,
            expires_at=now + timedelta(minutes=30),
        )

    def _execute_real_browser(self, envelope: ActionEnvelope, _context: dict[str, Any]) -> ActionResult:
        self.executor_calls.append(envelope.operation)
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=("receipt_extract_cards",),
            material_action=True,
            observation_summary="extracted safe visible product cards.",
        )


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
