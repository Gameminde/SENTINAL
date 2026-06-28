from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
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
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_pack5_model_led_channel_send_executes_after_mission_level_grant_without_per_message_approval(tmp_path: Path) -> None:
    calls: list[object] = []
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery_1"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))
    action_runtime = ModelLedLiveChannelActionRuntime(channel_runtime)

    result = action_runtime.execute_send_decision(
        mission_id=mission_id,
        decision=_decision(adapter.adapter_id),
        envelope=_envelope(mission_id),
    )

    assert result.status == "sent"
    assert result.model_led is True
    assert result.per_message_approval_required is False
    assert calls
    assert result.receipt_refs
    assert result.finalgate_refs
    assert result.channel_send_result_ref
    replay = ChannelAdapterReplayBuilder(channel_runtime.store).build(mission_id)
    assert replay.approvals == []
    assert replay.receipts
    assert replay.finalgate_refs


def test_pack5_each_live_send_gets_receipt_finalgate_and_evidence_refs(tmp_path: Path) -> None:
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery_2"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))
    result = ModelLedLiveChannelActionRuntime(channel_runtime).execute_send_decision(
        mission_id=mission_id,
        decision=_decision(adapter.adapter_id, evidence_refs=("inbound_receipt_1", "operator_context_1")),
        envelope=_envelope(mission_id),
    )

    assert result.receipt_refs
    assert result.finalgate_refs
    assert result.evidence_refs == ("inbound_receipt_1", "operator_context_1")
    assert result.delivery_ref_hash
    replay = ChannelAdapterReplayBuilder(channel_runtime.store).build(mission_id)
    assert replay.send_results[0].adapter_receipt is not None
    assert replay.send_results[0].finalgate_certificate is not None
    assert replay.send_results[0].finalgate_certificate.passed is True


def test_pack5_out_of_scope_destination_blocks_before_transport(tmp_path: Path) -> None:
    calls: list[object] = []
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))

    with pytest.raises(ChannelConnectorRuntimeError, match="recipient_not_allowed"):
        ModelLedLiveChannelActionRuntime(channel_runtime).execute_send_decision(
            mission_id=mission_id,
            decision=_decision(adapter.adapter_id, recipients=("person@example.org",)),
            envelope=_envelope(mission_id),
        )

    assert calls == []


def test_pack5_revocation_and_kill_switch_block_further_sends(tmp_path: Path) -> None:
    calls: list[object] = []
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))
    action_runtime = ModelLedLiveChannelActionRuntime(channel_runtime)

    with pytest.raises(ChannelConnectorRuntimeError, match="mission_authority_revoked"):
        action_runtime.execute_send_decision(
            mission_id=mission_id,
            decision=_decision(adapter.adapter_id),
            envelope=_envelope(mission_id, revoked=True),
        )

    channel_runtime.kernel.kill(mission_id)
    with pytest.raises(ChannelConnectorRuntimeError, match="operator_mission_terminal:killed"):
        action_runtime.execute_send_decision(
            mission_id=mission_id,
            decision=_decision(adapter.adapter_id, idempotency_key="after_kill"),
            envelope=_envelope(mission_id),
        )

    assert calls == []


def test_pack5_replay_never_resends_live_channel_action(tmp_path: Path) -> None:
    calls: list[object] = []
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery_3"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))
    ModelLedLiveChannelActionRuntime(channel_runtime).execute_send_decision(
        mission_id=mission_id,
        decision=_decision(adapter.adapter_id),
        envelope=_envelope(mission_id),
    )
    calls_before = len(calls)
    events_before = len(channel_runtime.store.load_events(mission_id))

    replay = ChannelAdapterReplayBuilder(channel_runtime.store).build(mission_id)

    assert replay.reexecuted_actions is False
    assert len(calls) == calls_before
    assert len(channel_runtime.store.load_events(mission_id)) == events_before


def test_pack5_duplicate_send_blocks_without_second_transport_call(tmp_path: Path) -> None:
    calls: list[object] = []
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery_4"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))
    runtime = ModelLedLiveChannelActionRuntime(channel_runtime)
    decision = _decision(adapter.adapter_id, idempotency_key="same-send")

    runtime.execute_send_decision(mission_id=mission_id, decision=decision, envelope=_envelope(mission_id))
    with pytest.raises(ChannelConnectorRuntimeError, match="duplicate_send_blocked"):
        runtime.execute_send_decision(mission_id=mission_id, decision=decision, envelope=_envelope(mission_id))

    assert len(calls) == 1


def test_pack5_decision_rejects_credentials_shell_browser_payment_and_provider_native_tools() -> None:
    with pytest.raises(ValueError, match="credential value|secret material"):
        _decision("adapter", body="Authorization: Bearer token")
    with pytest.raises(ValueError, match="unsupported live channel action"):
        LiveChannelSendDecision(action="shell", adapter_id="adapter", channel="webhook", body="x", recipients=("founder@example.com",), evidence_refs=("ev",))
    with pytest.raises(ValueError, match="provider-native"):
        LiveChannelSendDecision(
            action="send_message",
            adapter_id="adapter",
            channel="webhook",
            body="x",
            recipients=("founder@example.com",),
            evidence_refs=("ev",),
            provider_native_tools_allowed=True,
        )


def test_pack5_no_raw_recipient_body_credentials_or_provider_material_persisted(tmp_path: Path) -> None:
    channel_runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery_5"})
    adapter = channel_runtime.register_adapter(mission_id=mission_id, config=_webhook_config(require_approval=False))
    ModelLedLiveChannelActionRuntime(channel_runtime).execute_send_decision(
        mission_id=mission_id,
        decision=_decision(adapter.adapter_id, recipients=("founder@example.com",), body="Safe bounded reply."),
        envelope=_envelope(mission_id),
    )

    persisted = _mission_text(channel_runtime, mission_id)
    assert "founder@example.com" not in persisted
    assert "Safe bounded reply." not in persisted
    assert "raw_prompt" not in persisted
    assert "raw_response" not in persisted
    assert "reasoning_content" not in persisted
    assert "Authorization" not in persisted


def test_pack5_runtimehost_dispatch_remains_unchanged() -> None:
    source = inspect.getsource(SentinelRuntimeHost.__init__)

    assert '"read_only_research_adapter"' in source
    assert "connection_live_channel_action" not in source.lower()


def _runtime(tmp_path: Path, transport=None) -> tuple[ChannelConnectorRuntime, str]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_channel_power",
        draft=MissionDraft(
            title="Respond in a granted channel",
            objective="Let Sentinel send one scoped channel response after a mission-level grant.",
            constraints=["bounded channel only", "receipts always"],
            expected_artifacts=["channel send receipt"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="channel_power_mission",
            allowed_actions=["channel_send"],
            forbidden_actions=["payment", "desktop", "shell", "browser_click"],
            summary="Mission-level bounded channel grant.",
        ),
    )
    runtime = ChannelConnectorRuntime(kernel, transports={"webhook": transport} if transport else {})
    return runtime, record.mission_id


def _webhook_config(*, require_approval: bool) -> ChannelAdapterConfig:
    return ChannelAdapterConfig(
        adapter_id="adapter_webhook_power",
        kind=ChannelAdapterKind.WEBHOOK,
        provider_kind=ChannelProviderKind.WEBHOOK,
        display_name="Bounded local webhook",
        capability_profile={"supports_inbound": True, "supports_outbound": True},
        recipient_policy=ChannelRecipientPolicy(allowed_domains=["example.com"], max_recipients=1),
        scope_policy=ChannelScopePolicy(allowed_channels=["webhook"]),
        approval_policy={"approval_required_for_send": require_approval},
    )


def _decision(
    adapter_id: str,
    *,
    recipients: tuple[str, ...] = ("founder@example.com",),
    body: str = "Here is a bounded channel reply.",
    evidence_refs: tuple[str, ...] = ("evidence:channel_context",),
    idempotency_key: str = "pack5-send-1",
) -> LiveChannelSendDecision:
    return LiveChannelSendDecision(
        decision_id=f"decision_{idempotency_key}",
        action="send_message",
        adapter_id=adapter_id,
        channel="webhook",
        body=body,
        recipients=recipients,
        recipient_provenance={recipient: "mission_level_destination_grant" for recipient in recipients},
        evidence_refs=evidence_refs,
        idempotency_key=idempotency_key,
    )


def _envelope(
    mission_id: str,
    *,
    revoked: bool = False,
    expired: bool = False,
) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Bounded channel mission",
        mission_objective="Send one scoped channel message.",
        allowed_tools=["channel:webhook", "channel_draft_send"],
        allowed_actions=["channel_send"],
        forbidden_actions=["payment", "trading", "desktop", "shell", "browser_click"],
        allowed_domains=["example.com"],
        max_recipients=1,
        max_actions=10,
        created_at=now - timedelta(minutes=10) if expired else now,
        expires_at=now - timedelta(minutes=1) if expired else now + timedelta(minutes=30),
        revoked_at=now if revoked else None,
    )


def _mission_text(runtime: ChannelConnectorRuntime, mission_id: str) -> str:
    root = runtime.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))
