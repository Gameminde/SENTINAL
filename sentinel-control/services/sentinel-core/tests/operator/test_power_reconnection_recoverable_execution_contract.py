from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError, ActionResult
from sentinel.operator.action_power_contract import ActionFailureClass
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus


def test_pack_b_in_scope_executor_timeout_becomes_recoverable_and_loop_continues(tmp_path: Path) -> None:
    fixture = _RecoverableFixture(tmp_path)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="read_only_research",
                operation="list_directory",
                target_ref=".",
                params={"path": "."},
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                target_ref="TODO",
                params={"path": ".", "query": "TODO"},
            ),
        ]
    )
    loop = fixture.loop(decisions)

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert decisions.call_count == 2
    assert fixture.executor_calls == ["list_directory", "search_text"]
    assert result.capability_sequence == (
        "read_only_research:list_directory",
        "read_only_research:search_text",
    )
    assert loop.results[0].recoverable is True
    assert loop.results[0].material_action is False
    assert loop.results[0].failure_class is ActionFailureClass.RECOVERABLE_IN_SCOPE_RUNTIME_FAILURE
    assert loop.results[0].failure_code == "EXECUTOR_TIMEOUT"
    assert loop.results[0].receipt_refs == ()
    assert loop.results[1].receipt_refs == ("receipt_search_text",)
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED


def test_pack_b_hard_stop_executor_error_still_blocks_without_fake_receipt(tmp_path: Path) -> None:
    fixture = _RecoverableFixture(tmp_path, hard_stop=True)
    decisions = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="read_only_research",
                operation="list_directory",
                target_ref=".",
                params={"path": "."},
            )
        ]
    )

    result = fixture.loop(decisions).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "recipient_not_allowed"
    assert result.receipt_refs == ()
    assert fixture.executor_calls == ["list_directory"]
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.BLOCKED


class _RecoverableFixture:
    def __init__(self, tmp_path: Path, *, hard_stop: bool = False) -> None:
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        (self.workspace / "README.md").write_text("# Fixture\n\nTODO: recover action.\n", encoding="utf-8")
        self.hard_stop = hard_stop
        self.executor_calls: list[str] = []
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_pack_b",
            draft=MissionDraft(
                title="Recoverable execution contract",
                objective="Recover from in-scope runtime misses.",
                constraints=["hard stops remain terminal"],
                expected_artifacts=["recoverable observation"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="pack_b",
                allowed_actions=["list_directory", "search_text", "finish"],
                forbidden_actions=["credential_access", "payment", "workspace_escape"],
                summary="Read-only actions are granted inside the fixture workspace.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self._envelope()
        self.action_kernel = ActionKernel(executors={"read_only_research": self._execute_read_only})

    def loop(self, decision_client: ModelLedTaskDecisionClient) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decision_client,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=4, max_material_actions=1, max_recovery_turns=1)),
            available_actions=(
                "read_only_research.list_directory",
                "read_only_research.search_text",
                "sentinel_loop.finish",
            ),
        )

    def _envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_pack_b",
            mission_title="Recoverable execution contract",
            mission_objective="Recover from in-scope runtime misses.",
            allowed_tools=["read_only_research"],
            allowed_actions=["read_only_research.list_directory", "read_only_research.search_text", "sentinel_loop.finish"],
            forbidden_actions=["credential_access", "payment", "workspace_escape"],
            allowed_paths=[str(self.workspace)],
            max_actions=4,
            expires_at=now + timedelta(minutes=30),
        )

    def _execute_read_only(self, envelope: ActionEnvelope, _context: dict[str, Any]) -> ActionResult:
        self.executor_calls.append(envelope.operation)
        if self.hard_stop:
            raise ActionKernelError("recipient_not_allowed")
        if len(self.executor_calls) == 1:
            raise TimeoutError("locator timeout while using in-scope read-only observation")
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=(f"receipt_{envelope.operation}",),
            material_action=True,
            observation_summary=f"{envelope.operation} completed after recovery.",
        )


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
