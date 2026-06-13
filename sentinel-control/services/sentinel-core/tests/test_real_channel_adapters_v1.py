from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.channel_adapter import ChannelConnectorRuntime, ChannelConnectorRuntimeError
from sentinel.operator.channel_adapter_models import (
    ChannelAdapterConfig,
    ChannelAdapterKind,
    ChannelAttachmentRef,
    ChannelInboundEnvelope,
    ChannelOutboundApproval,
    ChannelOutboundRequest,
    ChannelOutboundSendRequest,
    ChannelProviderKind,
    ChannelRecipientPolicy,
    ChannelScopePolicy,
)
from sentinel.operator.channel_adapter_replay import ChannelAdapterReplayBuilder
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind


def test_adapter_registration_and_inbound_message_are_untrusted_data(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())

    inbound = runtime.ingest_inbound(
        mission_id=mission_id,
        adapter_id=adapter.adapter_id,
        envelope=ChannelInboundEnvelope(
            adapter_id=adapter.adapter_id,
            channel="webhook",
            external_message_id="msg_1",
            sender_ref="contact:founder",
            thread_ref="thread:launch",
            subject="Need help",
            text="Can Sentinel draft the launch note?",
            attachment_refs=[ChannelAttachmentRef(filename="brief.pdf", content_sha256="a" * 64, size_bytes=123)],
            link_refs=["https://example.com/brief"],
            identity_claims={"email": "founder@example.com"},
        ),
    )

    assert adapter.capability_profile.supports_inbound is True
    assert adapter.capability_profile.supports_outbound is True
    assert inbound.data_not_authority is True
    assert inbound.can_grant_authority is False
    assert inbound.can_execute is False
    assert inbound.identity_binding is not None
    assert inbound.identity_binding.verified is False
    assert inbound.attachment_quarantine
    assert inbound.link_quarantine
    assert inbound.message_hash
    assert runtime.store.verify_timeline(mission_id)


def test_inbound_secret_like_content_is_redacted_before_persistence(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())

    runtime.ingest_inbound(
        mission_id=mission_id,
        adapter_id=adapter.adapter_id,
        envelope=ChannelInboundEnvelope(
            adapter_id=adapter.adapter_id,
            channel="webhook",
            external_message_id="msg_secret",
            sender_ref="contact:unknown",
            text="my token is Bearer secret-value-1234567890",
        ),
    )

    persisted = _mission_text(runtime, mission_id)
    assert "secret-value-1234567890" not in persisted
    assert "Bearer secret-value" not in persisted
    assert "[REDACTED" in persisted


def test_outbound_draft_never_calls_transport(tmp_path: Path) -> None:
    calls: list[object] = []
    runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request))
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())

    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=ChannelOutboundRequest(
            adapter_id=adapter.adapter_id,
            channel="webhook",
            subject="Launch plan",
            body="Here is the safe draft.",
            recipients=["founder@example.com"],
            recipient_provenance={"founder@example.com": "operator_supplied"},
            evidence_refs=["evidence:brief"],
        ),
    )

    assert calls == []
    assert draft.send_attempted is False
    assert draft.body_hash
    assert "founder@example.com" not in str(draft.safe_model_dump())
    assert draft.data_not_authority is True


def test_send_requires_authority_recipient_scope_rate_and_operator_approval(tmp_path: Path) -> None:
    calls: list[object] = []

    def transport(request):
        calls.append(request)
        return {"delivery_ref": "fixture_delivery_1"}

    runtime, mission_id = _runtime(tmp_path, transport=transport)
    adapter = runtime.register_adapter(
        mission_id=mission_id,
        config=_webhook_config(require_approval=True, max_recipients=1),
    )
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )

    with pytest.raises(ChannelConnectorRuntimeError, match="channel_send_authority_missing"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
            envelope=None,
        )

    envelope = _envelope(mission_id, max_recipients=1)
    with pytest.raises(ChannelConnectorRuntimeError, match="operator_approval_required"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
            envelope=envelope,
        )

    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(
            adapter_id=adapter.adapter_id,
            draft_id=draft.draft_id,
            approved_by="operator_youcef",
            approval_source="operator",
        ),
    )
    result = runtime.send_outbound(
        mission_id=mission_id,
        request=ChannelOutboundSendRequest(
            adapter_id=adapter.adapter_id,
            draft_id=draft.draft_id,
            approval_id=approval.approval_id,
            idempotency_key="idem_1",
        ),
        envelope=envelope,
    )

    assert result.status == "sent"
    assert calls
    assert result.delivery_result is not None
    assert result.delivery_result.delivery_ref == "fixture_delivery_1"
    assert result.adapter_receipt is not None
    assert result.adapter_receipt.verify_hash()
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.passed is True
    assert result.channel_receipt_ref
    assert result.channel_finalgate_ref

    with pytest.raises(ChannelConnectorRuntimeError, match="duplicate_send_blocked"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(
                adapter_id=adapter.adapter_id,
                draft_id=draft.draft_id,
                approval_id=approval.approval_id,
                idempotency_key="idem_1",
            ),
            envelope=envelope,
        )


def test_send_blocks_revoked_expired_killed_and_out_of_scope_missions(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )
    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
    )

    with pytest.raises(ChannelConnectorRuntimeError, match="recipient_not_allowed"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
            envelope=_envelope(mission_id, allowed_domains=["example.org"]),
        )

    with pytest.raises(ChannelConnectorRuntimeError, match="mission_authority_revoked"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
            envelope=_envelope(mission_id, revoked=True),
        )

    with pytest.raises(ChannelConnectorRuntimeError, match="mission_authority_expired"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
            envelope=_envelope(mission_id, expired=True),
        )

    runtime.kernel.kill(mission_id)
    with pytest.raises(ChannelConnectorRuntimeError, match="operator_mission_terminal:killed"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
            envelope=_envelope(mission_id),
        )


@pytest.mark.parametrize("source", ["llm", "memory", "skill", "worker", "daemon", "scheduler", "telemetry"])
def test_non_operator_sources_cannot_approve_or_send(tmp_path: Path, source: str) -> None:
    runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )

    with pytest.raises(ValueError, match="operator approval source required"):
        ChannelOutboundApproval(
            adapter_id=adapter.adapter_id,
            draft_id=draft.draft_id,
            approved_by=source,
            approval_source=source,
        )

    with pytest.raises(ChannelConnectorRuntimeError, match="operator_approval_required"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(
                adapter_id=adapter.adapter_id,
                draft_id=draft.draft_id,
                approval_id=f"{source}_approval",
                requested_by=source,
            ),
            envelope=_envelope(mission_id),
        )


def test_receipts_are_hash_bound_and_cannot_become_future_permission(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )
    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
    )
    result = runtime.send_outbound(
        mission_id=mission_id,
        request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
        envelope=_envelope(mission_id),
    )

    receipt = result.adapter_receipt
    assert receipt is not None
    assert receipt.verify_hash()
    assert receipt.data_not_authority is True
    assert receipt.can_execute is False
    assert receipt.can_grant_authority is False
    assert receipt.future_permission is False

    payload = receipt.model_dump(mode="json")
    payload["future_permission"] = True
    with pytest.raises(ValueError):
        type(receipt).model_validate(payload)


def test_channel_send_requires_certified_telemetry_before_transport(tmp_path: Path) -> None:
    calls: list[object] = []
    runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )
    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
    )
    runtime.kernel.telemetry_sink.store.enabled = False

    with pytest.raises(ChannelConnectorRuntimeError, match="telemetry_certified_mode_required"):
        runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(
                adapter_id=adapter.adapter_id,
                draft_id=draft.draft_id,
                approval_id=approval.approval_id,
            ),
            envelope=_envelope(mission_id),
        )

    assert calls == []


def test_replay_reconstructs_channel_activity_without_resending(tmp_path: Path) -> None:
    calls: list[object] = []
    runtime, mission_id = _runtime(tmp_path, transport=lambda request: calls.append(request) or {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )
    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
    )
    runtime.send_outbound(
        mission_id=mission_id,
        request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
        envelope=_envelope(mission_id),
    )
    calls_before = len(calls)
    events_before = len(runtime.store.load_events(mission_id))

    replay = ChannelAdapterReplayBuilder(runtime.store).build(mission_id)

    assert replay.mission_id == mission_id
    assert replay.reexecuted_actions is False
    assert replay.tampered is False
    assert replay.adapters
    assert replay.outbound_drafts
    assert replay.send_results
    assert replay.receipts
    assert replay.finalgate_refs
    assert len(calls) == calls_before
    assert len(runtime.store.load_events(mission_id)) == events_before


def test_telemetry_events_and_metrics_are_recorded(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(mission_id=mission_id, config=_webhook_config())
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=_outbound_request(adapter.adapter_id, recipients=["founder@example.com"]),
    )
    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
    )
    runtime.send_outbound(
        mission_id=mission_id,
        request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
        envelope=_envelope(mission_id),
    )

    snapshot = runtime.store.telemetry_sink.store.snapshot()
    assert snapshot.event_counts_by_kind[TelemetryEventKind.CHANNEL_ADAPTER_REGISTERED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.CHANNEL_OUTBOUND_DRAFT_CREATED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.CHANNEL_OUTBOUND_SENT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.CHANNEL_OUTBOUND_SEND_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.CHANNEL_RECEIPT_COMPLETENESS.value] >= 1


def test_no_raw_token_prompt_provider_response_or_recipient_persistence(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path, transport=lambda _request: {"delivery_ref": "delivery"})
    adapter = runtime.register_adapter(
        mission_id=mission_id,
        config=_webhook_config(metadata={"token_ref": "ephemeral-ref", "raw_prompt_hash": "ok"}),
    )
    draft = runtime.create_outbound_draft(
        mission_id=mission_id,
        request=ChannelOutboundRequest(
            adapter_id=adapter.adapter_id,
            channel="webhook",
            subject="Hello",
            body="Safe body",
            recipients=["founder@example.com"],
            recipient_provenance={"founder@example.com": "operator_supplied"},
            evidence_refs=["evidence:brief"],
            metadata={"provider_response_hash": "hash-only"},
        ),
    )
    approval = runtime.approve_outbound(
        mission_id=mission_id,
        approval=ChannelOutboundApproval(adapter_id=adapter.adapter_id, draft_id=draft.draft_id),
    )
    runtime.send_outbound(
        mission_id=mission_id,
        request=ChannelOutboundSendRequest(adapter_id=adapter.adapter_id, draft_id=draft.draft_id, approval_id=approval.approval_id),
        envelope=_envelope(mission_id),
    )

    persisted = _mission_text(runtime, mission_id)
    forbidden = [
        "founder@example.com",
        '"raw_token"',
        '"credential_value"',
        "raw_prompt\"",
        "raw_provider_response",
        "raw_reasoning",
        "secret-value-1234567890",
    ]
    assert all(item not in persisted for item in forbidden)

    with pytest.raises(ValueError):
        ChannelAdapterConfig(
            adapter_id="bad_adapter",
            kind=ChannelAdapterKind.WEBHOOK,
            provider_kind=ChannelProviderKind.WEBHOOK,
            display_name="Bad",
            metadata={"raw_token": "secret-value-1234567890"},
        )


def _runtime(tmp_path: Path, transport=None) -> tuple[ChannelConnectorRuntime, str]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_channel",
        draft=MissionDraft(
            title="Reach a customer through a governed channel",
            objective="Create and optionally send a scoped outbound channel message.",
            constraints=["no ambient send", "no credential persistence"],
            expected_artifacts=["channel receipt"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="channel_mission",
            allowed_actions=["channel_draft", "channel_send"],
            forbidden_actions=["credential_unlock", "payment", "provider_override"],
            summary="Channel sends require explicit mission authority and operator approval.",
        ),
    )
    runtime = ChannelConnectorRuntime(kernel, transports={"webhook": transport} if transport else {})
    return runtime, record.mission_id


def _webhook_config(*, require_approval: bool = True, max_recipients: int = 5, metadata: dict | None = None) -> ChannelAdapterConfig:
    return ChannelAdapterConfig(
        adapter_id="adapter_webhook_sales",
        kind=ChannelAdapterKind.WEBHOOK,
        provider_kind=ChannelProviderKind.WEBHOOK,
        display_name="Sales webhook",
        capability_profile={"supports_inbound": True, "supports_outbound": True, "supports_attachments": True},
        recipient_policy=ChannelRecipientPolicy(allowed_domains=["example.com"], max_recipients=max_recipients),
        scope_policy=ChannelScopePolicy(allowed_channels=["webhook"], allowed_threads=["thread:launch"]),
        approval_policy={"approval_required_for_send": require_approval},
        metadata=metadata or {},
    )


def _outbound_request(adapter_id: str, *, recipients: list[str]) -> ChannelOutboundRequest:
    return ChannelOutboundRequest(
        adapter_id=adapter_id,
        channel="webhook",
        subject="Launch plan",
        body="Here is the safe launch draft.",
        recipients=recipients,
        recipient_provenance={recipient: "operator_supplied" for recipient in recipients},
        evidence_refs=["evidence:brief"],
    )


def _envelope(
    mission_id: str,
    *,
    allowed_domains: list[str] | None = None,
    max_recipients: int = 5,
    revoked: bool = False,
    expired: bool = False,
) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Channel mission",
        mission_objective="Send a scoped channel message.",
        allowed_tools=["channel:webhook", "channel_draft_send"],
        allowed_actions=["channel_draft", "channel_send"],
        forbidden_actions=["credential_unlock", "payment", "trading", "desktop"],
        allowed_domains=allowed_domains or ["example.com"],
        max_recipients=max_recipients,
        max_actions=10,
        created_at=now - timedelta(minutes=10) if expired else now,
        expires_at=now - timedelta(minutes=1) if expired else now + timedelta(minutes=30),
        revoked_at=now if revoked else None,
    )


def _mission_text(runtime: ChannelConnectorRuntime, mission_id: str) -> str:
    root = runtime.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))
