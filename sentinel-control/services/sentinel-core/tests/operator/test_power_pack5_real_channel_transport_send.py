from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.agent.organs.channel_draft_send_organ_v1 import ChannelSendTransportReceipt
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionKernel
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
from sentinel.operator.loop_guard import LoopGuard, LoopGuardConfig
from sentinel.operator.model_led_task_loop import ModelLedTaskDecisionClient, ModelLedTaskLoop, ModelLedTaskLoopReplay, ModelLedTaskLoopStatus
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus


def test_power_pack5_real_transport_adapter_interface_injects_without_generic_loop_changes(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    decision_client = ModelLedTaskDecisionClient(
        [
            _send_action(fixture),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Channel send complete."},
            ),
        ]
    )

    result = fixture.loop(decision_client).run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.capability_sequence == ("bounded_channel:send_message", "sentinel_loop:finish")
    assert fixture.transport_calls == 1
    assert result.receipt_refs
    assert result.finalgate_refs
    assert fixture.kernel.store.load_record(fixture.mission_id).status is OperatorMissionStatus.COMPLETED


def test_power_pack5_destination_scope_blocks_before_transport(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    decision_client = ModelLedTaskDecisionClient(
        [
            _send_action(
                fixture,
                recipients=["intruder@example.org"],
                recipient_provenance={"intruder@example.org": "not_granted"},
                idempotency_key="bad-recipient",
            )
        ]
    )

    result = fixture.loop(decision_client).run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "recipient_not_allowed"
    assert fixture.transport_calls == 0
    assert result.receipt_refs == ()


def test_power_pack5_duplicate_idempotency_blocks_without_resend(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    executor = fixture.channel_action_runtime.as_action_executor(mission_id=fixture.mission_id, authority=fixture.authority)
    action = _send_action(fixture, idempotency_key="same-send")

    first = executor(action, {})
    with pytest.raises(ChannelConnectorRuntimeError, match="duplicate_send_blocked"):
        executor(action, {})

    assert first.receipt_refs
    assert fixture.transport_calls == 1


def test_power_pack5_replay_no_resend_and_artifacts_stable(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    result = fixture.channel_action_runtime.execute_action_envelope(
        mission_id=fixture.mission_id,
        envelope=_send_action(fixture),
        authority=fixture.authority,
    )
    calls_before = fixture.transport_calls
    events_before = len(fixture.kernel.store.load_events(fixture.mission_id))

    replay = ChannelAdapterReplayBuilder(fixture.channel_runtime.store).build(fixture.mission_id)
    loop_replay = ModelLedTaskLoopReplay.from_store(fixture.kernel.store, fixture.mission_id)

    assert result.receipt_refs
    assert replay.reexecuted_actions is False
    assert len(replay.receipts) == 1
    assert fixture.transport_calls == calls_before
    assert len(fixture.kernel.store.load_events(fixture.mission_id)) == events_before
    assert loop_replay.channel_transport_sends_delta == 0
    assert loop_replay.receipt_writes_delta == 0
    assert loop_replay.artifact_hashes_stable is True


def test_power_pack5_context_carries_delivery_observation_to_next_model_turn(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    decision_client = ModelLedTaskDecisionClient(
        [
            _send_action(fixture),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Channel send complete."},
            ),
        ]
    )

    result = fixture.loop(decision_client).run()
    second_turn_context = decision_client.contexts[1]

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert second_turn_context["channel_delivery_summary"]["send_count"] == 1
    latest_send = second_turn_context["channel_delivery_summary"]["latest_send"]
    assert latest_send["receipt_count"] >= 1
    assert latest_send["delivery_status"] == "sent"
    assert latest_send["delivery_receipt_ref"].startswith("channel_adapter_receipt_")
    assert latest_send["delivery_ref_hash"]
    assert second_turn_context["recommended_next_action"] == "sentinel_loop.finish"
    assert second_turn_context["finish_available"] is True
    assert second_turn_context["progress_state"] == "channel_delivery_succeeded_needs_finish"


def test_power_pack5_material_budget_after_channel_send_allows_canonical_finish_only_turn(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    decision_client = ModelLedTaskDecisionClient(
        [
            _send_action(fixture),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Channel delivery observed and finished."},
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
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=3, max_material_actions=1)),
        available_actions=("bounded_channel.send_message", "sentinel_loop.finish"),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.COMPLETED
    assert result.final_reason == "model_led_task_loop_finish"
    assert result.capability_sequence == ("bounded_channel:send_message", "sentinel_loop:finish")
    assert result.material_action_count == 1
    assert result.model_call_count == 2
    assert fixture.transport_calls == 1
    finish_context = decision_client.contexts[-1]
    assert finish_context["finish_only_due_to_material_budget"] is True
    assert finish_context["objective_satisfied"] is True
    assert finish_context["finish_available"] is True
    assert finish_context["recommended_next_action"] == "sentinel_loop.finish"
    assert finish_context["available_actions"] == ["sentinel_loop.finish"]
    assert finish_context["progress_state"] == "channel_delivery_succeeded_needs_finish"


def test_power_pack5_finish_only_turn_blocks_non_finish_after_channel_delivery(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture))
    decision_client = ModelLedTaskDecisionClient(
        [
            _send_action(fixture),
            _send_action(fixture, idempotency_key="second-send"),
        ]
    )
    loop = ModelLedTaskLoop(
        mission_id=fixture.mission_id,
        kernel=fixture.kernel,
        authority=fixture.authority,
        action_kernel=fixture.action_kernel,
        decision_client=decision_client,
        decision_context=DecisionContextCompiler(),
        loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=3, max_material_actions=1)),
        available_actions=("bounded_channel.send_message", "sentinel_loop.finish"),
    )

    result = loop.run()

    assert result.status is ModelLedTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "MODEL_FINISH_REQUIRED_AFTER_CHANNEL_DELIVERY"
    assert fixture.transport_calls == 1
    assert result.capability_sequence == ("bounded_channel:send_message",)
    finish_context = decision_client.contexts[-1]
    assert finish_context["finish_only_due_to_material_budget"] is True
    assert finish_context["available_actions"] == ["sentinel_loop.finish"]


def test_power_pack5_no_raw_credentials_authorization_or_message_body_persisted(tmp_path: Path) -> None:
    fixture = _ChannelPowerFixture(tmp_path)
    fixture.register_transport(_RecordingRealTransport(fixture, delivery_ref="provider-message-42"))
    fixture.channel_action_runtime.execute_action_envelope(
        mission_id=fixture.mission_id,
        envelope=_send_action(fixture, body="Safe bounded channel message."),
        authority=fixture.authority,
    )

    persisted = _mission_text(fixture.kernel, fixture.mission_id)

    assert "Safe bounded channel message." not in persisted
    assert "Authorization" not in persisted
    assert "Bearer " not in persisted
    assert "raw_provider" not in persisted
    assert "reasoning_content" not in persisted


def test_power_pack5_real_transport_config_names_are_metadata_not_values(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentinel.operator.channel_adapter import build_webhook_channel_transport_from_env

    monkeypatch.delenv("SENTINEL_CHANNEL_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SENTINEL_CHANNEL_WEBHOOK_TOKEN", raising=False)

    with pytest.raises(ChannelConnectorRuntimeError, match="real_channel_transport_config_missing:SENTINEL_CHANNEL_WEBHOOK_URL"):
        build_webhook_channel_transport_from_env()


def test_power_pack5_telegram_transport_requires_process_scoped_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentinel.operator.channel_adapter import build_telegram_channel_transport_from_env

    monkeypatch.delenv("SENTINEL_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SENTINEL_TELEGRAM_CHAT_ID", raising=False)

    with pytest.raises(ChannelConnectorRuntimeError, match="real_channel_transport_config_missing:SENTINEL_TELEGRAM_BOT_TOKEN"):
        build_telegram_channel_transport_from_env()

    monkeypatch.setenv("SENTINEL_TELEGRAM_BOT_TOKEN", "token-value")
    with pytest.raises(ChannelConnectorRuntimeError, match="real_channel_transport_config_missing:SENTINEL_TELEGRAM_CHAT_ID"):
        build_telegram_channel_transport_from_env()


def test_power_pack5_telegram_transport_posts_send_message_without_persisting_token_or_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentinel.operator.channel_adapter import build_telegram_channel_transport_from_env

    requests: list[object] = []

    class _Response:
        status = 200

        def read(self, _limit: int = -1) -> bytes:
            return b'{"ok":true,"result":{"message_id":123}}'

    def opener(request: object, timeout: float) -> _Response:
        requests.append((request, timeout))
        return _Response()

    monkeypatch.setenv("SENTINEL_TELEGRAM_BOT_TOKEN", "telegram-token-value")
    monkeypatch.setenv("SENTINEL_TELEGRAM_CHAT_ID", "telegram-chat-id")
    transport = build_telegram_channel_transport_from_env(opener=opener)

    receipt = transport(type("Request", (), {"body": "Bounded Telegram message."})())

    assert receipt.delivery_ref == "telegram:123"
    assert len(requests) == 1
    request, timeout = requests[0]
    assert timeout == 15.0
    assert request.full_url.endswith("/sendMessage")
    assert "telegram-token-value" in request.full_url
    body = request.data.decode("utf-8")
    assert '"chat_id": "telegram-chat-id"' in body
    assert '"text": "Bounded Telegram message."' in body


class _ChannelPowerFixture:
    def __init__(self, tmp_path: Path) -> None:
        self.transport_calls = 0
        self.kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=_CertifiedTelemetrySink())
        record = self.kernel.create_mission(
            session_id="session_power_pack5_real_channel",
            draft=MissionDraft(
                title="Model-led real channel send",
                objective="Send one bounded outbound message to the granted test destination.",
                constraints=["mission-level grant", "receipts always"],
                expected_artifacts=["channel delivery receipt"],
            ),
            authority_summary=MissionAuthoritySummary(
                mission_id="power_pack5_real_channel",
                allowed_actions=["channel_send", "finish"],
                forbidden_actions=["payment", "shell", "browser_click", "credential_access"],
                summary="Bounded channel send authority for one test destination.",
            ),
        )
        self.mission_id = record.mission_id
        self.kernel.enqueue(self.mission_id)
        self.authority = _envelope(self.mission_id)
        self.channel_runtime = ChannelConnectorRuntime(self.kernel)
        self.adapter_id = self.channel_runtime.register_adapter(
            mission_id=self.mission_id,
            config=ChannelAdapterConfig(
                adapter_id="adapter_real_channel_power",
                kind=ChannelAdapterKind.WEBHOOK,
                provider_kind=ChannelProviderKind.WEBHOOK,
                display_name="Real channel transport test adapter",
                capability_profile={"supports_inbound": False, "supports_outbound": True},
                recipient_policy=ChannelRecipientPolicy(allowed_domains=["example.com"], max_recipients=1),
                scope_policy=ChannelScopePolicy(allowed_channels=["webhook"]),
                approval_policy={"approval_required_for_send": False},
                endpoint_ref_hash="endpoint_ref_hash_only",
                credential_ref="env:SENTINEL_CHANNEL_WEBHOOK_TOKEN",
            ),
        ).adapter_id
        self.channel_action_runtime = ModelLedLiveChannelActionRuntime(self.channel_runtime)
        self.action_kernel = ActionKernel(
            executors={
                "bounded_channel": self.channel_action_runtime.as_action_executor(
                    mission_id=self.mission_id,
                    authority=self.authority,
                )
            }
        )

    def register_transport(self, transport: object) -> None:
        self.channel_runtime.registry.register(self.channel_runtime.registry.config(self.adapter_id), transport=transport)  # type: ignore[arg-type]

    def loop(self, decision_client: ModelLedTaskDecisionClient) -> ModelLedTaskLoop:
        return ModelLedTaskLoop(
            mission_id=self.mission_id,
            kernel=self.kernel,
            authority=self.authority,
            action_kernel=self.action_kernel,
            decision_client=decision_client,
            decision_context=DecisionContextCompiler(),
            loop_guard=LoopGuard(LoopGuardConfig(max_model_calls=4, max_material_actions=2)),
            available_actions=("bounded_channel.send_message", "sentinel_loop.finish"),
        )


class _RecordingRealTransport:
    def __init__(self, fixture: _ChannelPowerFixture, *, delivery_ref: str = "delivery_real_1") -> None:
        self._fixture = fixture
        self._delivery_ref = delivery_ref

    def __call__(self, request: object) -> ChannelSendTransportReceipt:
        del request
        self._fixture.transport_calls += 1
        return ChannelSendTransportReceipt(delivery_ref=self._delivery_ref)


def _send_action(
    fixture: _ChannelPowerFixture,
    *,
    body: str = "Sentinel bounded channel power worked.",
    recipients: list[str] | None = None,
    recipient_provenance: dict[str, str] | None = None,
    idempotency_key: str = "real-channel-send-1",
) -> ActionEnvelope:
    recipients = recipients or ["founder@example.com"]
    return ActionEnvelope(
        capability_id="bounded_channel",
        operation="send_message",
        target_ref=f"webhook:{recipients[0]}",
        params={
            "adapter_id": fixture.adapter_id,
            "channel": "webhook",
            "body": body,
            "recipients": recipients,
            "recipient_provenance": recipient_provenance or {recipient: "mission_level_destination_grant" for recipient in recipients},
            "evidence_refs": ["evidence:mission_grant"],
        },
        idempotency_key=idempotency_key,
        expected_receipt_type="channel_adapter_receipt",
    )


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Model-led real channel send",
        mission_objective="Send one bounded outbound channel message.",
        allowed_tools=["channel:webhook", "channel_draft_send"],
        allowed_actions=["channel_send", "finish"],
        forbidden_actions=["payment", "shell", "browser_click", "credential_access"],
        allowed_domains=["example.com"],
        max_recipients=1,
        max_actions=5,
        expires_at=now + timedelta(minutes=30),
    )


def _mission_text(kernel: MissionKernel, mission_id: str) -> str:
    root = kernel.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))


class _CertifiedTelemetrySink:
    def require_certified_mode(self) -> None:
        return None

    def require_material_execution(self, _kind: str) -> None:
        return None

    def record_metric(self, *args: object, **kwargs: object) -> None:
        return None

    def record_mission_event(self, *args: object, **kwargs: object) -> None:
        return None
