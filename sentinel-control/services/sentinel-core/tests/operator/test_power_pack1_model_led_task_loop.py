from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel, ActionKernelError, ActionResult
from sentinel.operator.channel_adapter import ChannelConnectorRuntime, ChannelConnectorRuntimeError
from sentinel.operator.channel_adapter_models import (
    ChannelAdapterConfig,
    ChannelAdapterKind,
    ChannelProviderKind,
    ChannelRecipientPolicy,
    ChannelScopePolicy,
)
from sentinel.operator.channel_adapter_replay import ChannelAdapterReplayBuilder
from sentinel.operator.connection_live_channel_action_models import LiveChannelSendDecision
from sentinel.operator.connection_live_channel_action_runtime import ModelLedLiveChannelActionRuntime
from sentinel.operator.decision_context import DecisionContextCompiler
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig, LoopGuardError
from sentinel.operator.model_led_task_loop import (
    ModelLedTaskDecisionClient,
    ModelLedTaskLoop,
    ModelLedTaskLoopReplay,
    ModelLedTaskLoopStatus,
)
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyActionKind,
    ReadOnlyDecision,
    ReadOnlyDecisionClient,
    ReadOnlyProductionSpineSession,
)


def test_power_pack1_loop_executes_read_only_channel_read_only_finish_and_replays_without_reexecute(
    tmp_path: Path,
) -> None:
    fixture = _LoopFixture(tmp_path)
    decision_client = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="read_only_research",
                operation="list_directory",
                target_ref=".",
                params={"path": "."},
                idempotency_key="list-root",
                expected_receipt_type="read_only_action_receipt",
            ),
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                target_ref="webhook:founder@example.com",
                params={
                    "adapter_id": fixture.adapter_id,
                    "channel": "webhook",
                    "body": "Bounded product power receipt created.",
                    "recipients": ["founder@example.com"],
                    "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
                    "evidence_refs": ["evidence:read_only_context"],
                },
                idempotency_key="send-channel",
                expected_receipt_type="channel_adapter_receipt",
            ),
            ActionEnvelope(
                capability_id="read_only_research",
                operation="search_text",
                target_ref="TODO",
                params={"path": ".", "query": "TODO"},
                idempotency_key="search-todo",
                expected_receipt_type="read_only_action_receipt",
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                target_ref="mission",
                params={"safe_summary": "Initial cross-capability task loop complete."},
                idempotency_key="finish",
                expected_receipt_type="none",
            ),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decision_client,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=4)),
    )

    result = loop.run()
    replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED
    assert decision_client.call_count == 4
    assert [entry["last_action_status"] for entry in decision_client.contexts[1:]] == ["completed", "completed", "completed"]
    assert result.material_action_count == 3
    assert result.receipt_refs
    assert result.capability_sequence == (
        "read_only_research:list_directory",
        "bounded_channel:send_message",
        "read_only_research:search_text",
        "sentinel_loop:finish",
    )
    assert fixture.read_only_tool_calls == 2
    assert fixture.channel_transport_sends == 1
    assert replay.reexecuted_actions is False
    assert replay.model_calls_delta == 0
    assert replay.read_only_tool_calls_delta == 0
    assert replay.channel_transport_sends_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.event_count_stable is True
    assert replay.artifact_hashes_stable is True


def test_power_pack1_channel_destination_out_of_scope_blocks_before_transport(tmp_path: Path) -> None:
    fixture = _LoopFixture(tmp_path)
    decision_client = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(
                capability_id="bounded_channel",
                operation="send_message",
                target_ref="webhook:intruder@example.org",
                params={
                    "adapter_id": fixture.adapter_id,
                    "channel": "webhook",
                    "body": "This must not send.",
                    "recipients": ["intruder@example.org"],
                    "recipient_provenance": {"intruder@example.org": "not_granted"},
                    "evidence_refs": ["evidence:blocked_context"],
                },
                idempotency_key="bad-send",
                expected_receipt_type="channel_adapter_receipt",
            )
        ]
    )
    loop = fixture.loop(decision_client)

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "recipient_not_allowed"
    assert fixture.channel_transport_sends == 0
    assert result.receipt_refs == ()


def test_power_pack1_revoked_authority_blocks_next_action(tmp_path: Path) -> None:
    fixture = _LoopFixture(tmp_path)
    decision_client = _RevokingLoopDecisionClient(
        fixture.authority,
        [
            ActionEnvelope(
                capability_id="read_only_research",
                operation="list_directory",
                target_ref=".",
                params={"path": "."},
            )
        ],
    )

    result = fixture.loop(decision_client).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "mission_authority_inactive"
    assert fixture.read_only_tool_calls == 0


def test_power_pack1_kill_switch_blocks_next_action(tmp_path: Path) -> None:
    fixture = _LoopFixture(tmp_path)
    decision_client = _KillingLoopDecisionClient(
        fixture.kernel,
        fixture.mission_id,
        [
            ActionEnvelope(
                capability_id="read_only_research",
                operation="list_directory",
                target_ref=".",
                params={"path": "."},
            )
        ],
    )

    result = fixture.loop(decision_client).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "operator_mission_terminal:killed"
    assert fixture.read_only_tool_calls == 0


def test_power_pack1_loop_guard_blocks_repeated_no_progress_actions(tmp_path: Path) -> None:
    fixture = _LoopFixture(tmp_path)
    repeated = ActionEnvelope(
        capability_id="read_only_research",
        operation="list_directory",
        target_ref=".",
        params={"path": "."},
        idempotency_key="same",
    )
    decision_client = ModelLedTaskDecisionClient([repeated, repeated.model_copy(update={"action_id": "action_repeat_2"})])
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decision_client,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_same_action_hash=1, max_no_progress_turns=1)),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "loop_guard_repeated_action"
    assert fixture.read_only_tool_calls == 1


def test_power_pack1_max_material_actions_stops_cleanly_without_extra_receipt(tmp_path: Path) -> None:
    fixture = _LoopFixture(tmp_path)
    decision_client = ModelLedTaskDecisionClient(
        [
            ActionEnvelope(capability_id="read_only_research", operation="list_directory", target_ref=".", params={"path": "."}),
            ActionEnvelope(capability_id="read_only_research", operation="search_text", target_ref="TODO", params={"path": ".", "query": "TODO"}),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decision_client,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=1)),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_material_budget_reached"
    assert result.material_action_count == 1
    assert fixture.read_only_tool_calls == 1


def test_power_pack1_rejects_raw_provider_reasoning_credentials_and_provider_native_material() -> None:
    with pytest.raises(ValueError, match="raw provider"):
        ActionEnvelope(
            capability_id="read_only_research",
            operation="list_directory",
            params={"raw_provider_response": "hidden"},
        )
    with pytest.raises(ValueError, match="credential|secret"):
        ActionEnvelope(
            capability_id="bounded_channel",
            operation="send_message",
            params={"body": "Authorization: Bearer token"},
        )
    with pytest.raises(ValueError, match="provider-native"):
        ActionEnvelope(
            capability_id="read_only_research",
            operation="list_directory",
            params={"provider_native_tools": True},
        )


class _LoopFixture:
    def __init__(self, tmp_path: Path) -> None:
        self.workspace = tmp_path / "workspace"
        self.workspace.mkdir()
        (self.workspace / "README.md").write_text("# Project\n\nTODO: wire power loop.\n", encoding="utf-8")
        (self.workspace / "src").mkdir()
        (self.workspace / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack1",
            draft=MissionDraft(
                title="Model-led task loop",
                objective="Let the model drive multiple granted actions.",
                constraints=["receipts always", "no per-action approval"],
                expected_artifacts=["cross-capability receipts"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack1",
                allowed_actions=["list_directory", "search_text", "channel_send", "finish"],
                forbidden_actions=["shell", "payment", "browser_click", "credential_access"],
                summary="Read-only and local channel send are granted for this mission.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = self.envelope()
        self.channel_transport_sends = 0
        self.channel_runtime = ChannelConnectorRuntime(
            self.kernel,
            transports={"webhook": self._transport},
        )
        self.adapter_id = self.channel_runtime.register_adapter(
            mission_id=self.mission_id,
            config=ChannelAdapterConfig(
                adapter_id="adapter_power_pack1",
                kind=ChannelAdapterKind.WEBHOOK,
                provider_kind=ChannelProviderKind.WEBHOOK,
                display_name="Power Pack 1 local channel",
                capability_profile={"supports_inbound": True, "supports_outbound": True},
                recipient_policy=ChannelRecipientPolicy(allowed_domains=["example.com"], max_recipients=1),
                scope_policy=ChannelScopePolicy(allowed_channels=["webhook"]),
                approval_policy={"approval_required_for_send": False},
            ),
        ).adapter_id
        self.read_only_tool_calls = 0
        self.action_kernel = ActionKernel(
            executors={
                "read_only_research": self._execute_read_only,
                "bounded_channel": self._execute_channel,
            }
        )

    def loop(self, decision_client: ModelLedTaskDecisionClient) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decision_client,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=5, max_material_actions=5)),
        )

    def envelope(self) -> MissionAuthorityEnvelope:
        now = datetime.now(UTC)
        return MissionAuthorityEnvelope(
            id=self.mission_id,
            user_id="user_youcef",
            mission_title="Model-led task loop",
            mission_objective="Run granted read-only and bounded channel actions.",
            allowed_tools=[
                "read_only_observation",
                "read_only_research_adapter",
                "read_only_research",
                "channel:webhook",
                "channel_draft_send",
            ],
            allowed_actions=["list_directory", "search_text", "read_file_segment", "channel_send", "finish"],
            forbidden_actions=["shell", "payment", "browser_click", "credential_access"],
            allowed_paths=[str(self.workspace)],
            allowed_domains=["example.com"],
            max_actions=10,
            max_recipients=1,
            expires_at=now + timedelta(minutes=30),
        )

    def _transport(self, _request: object) -> dict[str, str]:
        self.channel_transport_sends += 1
        return {"delivery_ref": f"delivery_{self.channel_transport_sends}"}

    def _execute_read_only(self, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        del context
        self.read_only_tool_calls += 1
        decision = ReadOnlyDecision(
            action=ReadOnlyActionKind(envelope.operation),
            arguments=dict(envelope.params),
        )
        session = ReadOnlyProductionSpineSession(
            cockpit=_KernelBackedCockpit(self.kernel),
            mission_id=self.mission_id,
            snapshot_root=self.workspace,
            decision_client=ReadOnlyDecisionClient([decision]),
            stop_after_first_material_receipt=True,
            low_friction_read_only_power_mode=True,
            owns_kernel_terminal=False,
        )
        result = session.run_via_agent_runtime(envelope=self.authority)
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=result.status,
            receipt_refs=tuple(result.receipt_refs),
            evidence_refs=tuple(_evidence_refs_for_latest_read_only(self.kernel, self.mission_id)),
            finalgate_refs=tuple(result.finalgate_refs),
            material_action=True,
            observation_summary=f"{envelope.operation} completed with {len(result.receipt_refs)} receipt(s).",
        )

    def _execute_channel(self, envelope: ActionEnvelope, context: dict[str, Any]) -> ActionResult:
        del context
        params = dict(envelope.params)
        result = ModelLedLiveChannelActionRuntime(self.channel_runtime).execute_send_decision(
            mission_id=self.mission_id,
            decision=LiveChannelSendDecision(
                decision_id=envelope.decision_ref or envelope.action_id,
                action="send_message",
                adapter_id=str(params["adapter_id"]),
                channel=str(params["channel"]),
                body=str(params["body"]),
                recipients=tuple(params["recipients"]),
                recipient_provenance=dict(params["recipient_provenance"]),
                evidence_refs=tuple(params["evidence_refs"]),
                idempotency_key=envelope.idempotency_key,
            ),
            envelope=self.envelope(),
        )
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status="completed",
            receipt_refs=tuple(result.receipt_refs),
            evidence_refs=tuple(result.evidence_refs),
            finalgate_refs=tuple(result.finalgate_refs),
            material_action=True,
            observation_summary="bounded channel send completed with receipt.",
        )


class _RevokingLoopDecisionClient(ModelLedTaskDecisionClient):
    def __init__(self, authority: MissionAuthorityEnvelope, decisions: list[ActionEnvelope]) -> None:
        super().__init__(decisions)
        self._authority = authority

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        decision = super().complete(context)
        self._authority.revoked_at = datetime.now(UTC)
        return decision


class _KillingLoopDecisionClient(ModelLedTaskDecisionClient):
    def __init__(self, kernel: MissionKernel, mission_id: str, decisions: list[ActionEnvelope]) -> None:
        super().__init__(decisions)
        self._kernel = kernel
        self._mission_id = mission_id

    def complete(self, context: dict[str, Any]) -> ActionEnvelope:
        decision = super().complete(context)
        self._kernel.kill(self._mission_id)
        return decision


def _evidence_refs_for_latest_read_only(kernel: MissionKernel, mission_id: str) -> list[str]:
    evidence_root = kernel.store.mission_dir(mission_id) / "read_only_spine" / "evidence"
    if not evidence_root.exists():
        return []
    return [path.stem for path in sorted(evidence_root.glob("*.json"))]


class _KernelBackedCockpit:
    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel

    def handle(self, _message: str) -> None:
        return None


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
