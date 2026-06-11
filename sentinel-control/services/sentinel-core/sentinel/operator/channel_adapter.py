from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.agent.organs.channel_draft_send_organ_v1 import (
    ChannelDraftSendContract,
    ChannelDraftSendOrganV1,
    ChannelDraftSendRequest,
    ChannelDraftSendStatus,
    ChannelSendTransportReceipt,
)
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.channel_adapter_models import (
    ChannelAdapterConfig,
    ChannelAdapterFinalGateCertificate,
    ChannelAdapterReceipt,
    ChannelDeliveryResult,
    ChannelDeliveryStatus,
    ChannelInboundEnvelope,
    ChannelInboundMessage,
    ChannelIdentityRef,
    ChannelLinkQuarantine,
    ChannelAttachmentQuarantine,
    ChannelOutboundApproval,
    ChannelOutboundDraft,
    ChannelOutboundRequest,
    ChannelOutboundSendRequest,
    ChannelOutboundSendResult,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text
from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


ChannelTransport = Callable[[Any], Any]


class ChannelConnectorRuntimeError(ValueError):
    """Raised when channel execution would violate authority or connector policy."""


class ChannelConnectorRegistry:
    def __init__(self) -> None:
        self._configs: dict[str, ChannelAdapterConfig] = {}
        self._transports: dict[str, ChannelTransport] = {}

    def register(self, config: ChannelAdapterConfig, *, transport: ChannelTransport | None = None) -> ChannelAdapterConfig:
        self._configs[config.adapter_id] = config
        if transport is not None:
            self._transports[config.adapter_id] = transport
        return config

    def config(self, adapter_id: str) -> ChannelAdapterConfig:
        try:
            return self._configs[adapter_id]
        except KeyError as exc:
            raise ChannelConnectorRuntimeError("channel_adapter_not_registered") from exc

    def transport(self, adapter_id: str, channel: str) -> ChannelTransport | None:
        return self._transports.get(adapter_id) or self._transports.get(channel)


class ChannelConnectorRuntime:
    """Mission-scoped channel connector layer over the existing channel organ.

    The runtime owns adapter admission, untrusted inbound recording, outbound
    draft/approval/send lifecycle, telemetry, receipts, and replay artifacts.
    It does not store credential values and does not send except through an
    injected transport behind the existing ChannelDraftSendOrganV1.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        registry: ChannelConnectorRegistry | None = None,
        transports: dict[str, ChannelTransport] | None = None,
    ) -> None:
        self.kernel = kernel
        self.store = kernel.store
        self.registry = registry or ChannelConnectorRegistry()
        self._draft_requests: dict[tuple[str, str], ChannelOutboundRequest] = {}
        self._approvals: dict[tuple[str, str], ChannelOutboundApproval] = {}
        for key, transport in (transports or {}).items():
            self.registry._transports[key] = transport

    def register_adapter(self, *, mission_id: str, config: ChannelAdapterConfig) -> ChannelAdapterConfig:
        self.store.load_record(mission_id)
        config = config.with_hash()
        self.registry.register(config, transport=self.registry.transport(config.adapter_id, config.kind.value))
        self._write_json(mission_id, "adapters", config.adapter_id, config.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="channel_adapter_registered",
            safe_summary="Channel adapter registered as governed local connector descriptor.",
            metadata={
                "adapter_id": config.adapter_id,
                "kind": config.kind.value,
                "provider_kind": config.provider_kind.value,
                "config_hash": config.config_hash,
            },
        )
        return config

    def ingest_inbound(
        self,
        *,
        mission_id: str,
        adapter_id: str,
        envelope: ChannelInboundEnvelope,
    ) -> ChannelInboundMessage:
        self.store.load_record(mission_id)
        config = self._load_config(mission_id, adapter_id)
        if not config.capability_profile.supports_inbound:
            raise ChannelConnectorRuntimeError("channel_inbound_not_supported")
        if envelope.channel.lower() not in config.scope_policy.allowed_channels:
            raise ChannelConnectorRuntimeError("channel_not_in_scope")
        identity = ChannelIdentityRef(
            adapter_id=adapter_id,
            external_sender_hash=stable_hash(envelope.sender_ref),
            verified=False,
            binding_source="untrusted_inbound",
        )
        attachment_quarantine = [
            ChannelAttachmentQuarantine(
                attachment_id=attachment.attachment_id,
                content_sha256=attachment.content_sha256,
            )
            for attachment in envelope.attachment_refs
        ]
        link_quarantine = [
            ChannelLinkQuarantine(link_hash=stable_hash(link))
            for link in envelope.link_refs
        ]
        message = ChannelInboundMessage(
            adapter_id=adapter_id,
            channel=envelope.channel.lower(),
            external_message_hash=stable_hash(envelope.external_message_id),
            sender_hash=stable_hash(envelope.sender_ref),
            thread_hash=stable_hash(envelope.thread_ref) if envelope.thread_ref else None,
            subject_hash=stable_hash(envelope.subject) if envelope.subject else None,
            safe_text=redact_operator_text(envelope.text),
            text_hash=envelope.text_hash,
            identity_binding=identity,
            attachment_quarantine=attachment_quarantine,
            link_quarantine=link_quarantine,
        ).with_hash()
        self._write_json(mission_id, "inbound", message.message_id, message.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="channel_inbound_received",
            safe_summary="Inbound channel message recorded as untrusted data.",
            metadata={
                "adapter_id": adapter_id,
                "message_id": message.message_id,
                "message_hash": message.message_hash,
                "attachment_quarantine_count": len(attachment_quarantine),
                "link_quarantine_count": len(link_quarantine),
            },
        )
        self._append_event(
            mission_id,
            event_type="channel_identity_bound",
            safe_summary="Inbound channel identity binding recorded as unverified data.",
            metadata={"adapter_id": adapter_id, "identity_ref": identity.identity_ref},
        )
        if attachment_quarantine or link_quarantine:
            self._append_event(
                mission_id,
                event_type="channel_inbound_quarantined",
                safe_summary="Inbound channel attachments or links were quarantined.",
                metadata={
                    "adapter_id": adapter_id,
                    "message_id": message.message_id,
                    "attachment_quarantine_count": len(attachment_quarantine),
                    "link_quarantine_count": len(link_quarantine),
                },
            )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.CHANNEL_INBOUND_MESSAGE_COUNT,
            1.0,
            "Channel inbound message count sample.",
            metadata={"adapter_id": adapter_id},
        )
        return message

    def create_outbound_draft(
        self,
        *,
        mission_id: str,
        request: ChannelOutboundRequest,
    ) -> ChannelOutboundDraft:
        self._assert_mission_open(mission_id)
        config = self._load_config(mission_id, request.adapter_id)
        self._assert_channel_scope(config, request.channel, request.thread_ref)
        self._assert_recipient_policy(config, request.recipients, request.recipient_provenance)
        draft = ChannelOutboundDraft(
            adapter_id=request.adapter_id,
            channel=request.channel.lower(),
            subject_hash=stable_hash(request.subject) if request.subject else None,
            body_hash=stable_hash(request.body),
            recipient_hashes=[stable_hash(recipient.lower()) for recipient in request.recipients],
            recipient_count=len(request.recipients),
            recipient_provenance_hash=stable_hash(request.recipient_provenance),
            thread_hash=stable_hash(request.thread_ref) if request.thread_ref else None,
            evidence_refs=list(request.evidence_refs),
            objective_tags=list(request.objective_tags),
            attachment_refs=list(request.attachment_refs),
        ).with_hash()
        self._draft_requests[(mission_id, draft.draft_id)] = request
        self._write_json(mission_id, "drafts", draft.draft_id, draft.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="channel_outbound_draft_created",
            safe_summary="Channel outbound draft created; no send attempted.",
            metadata={
                "adapter_id": request.adapter_id,
                "draft_id": draft.draft_id,
                "draft_hash": draft.draft_hash,
                "recipient_count": draft.recipient_count,
            },
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.CHANNEL_OUTBOUND_DRAFT_COUNT,
            1.0,
            "Channel outbound draft count sample.",
            metadata={"adapter_id": request.adapter_id},
        )
        return draft

    def approve_outbound(self, *, mission_id: str, approval: ChannelOutboundApproval) -> ChannelOutboundApproval:
        self.store.load_record(mission_id)
        approval = approval.with_hash()
        self._approvals[(mission_id, approval.approval_id)] = approval
        self._write_json(mission_id, "approvals", approval.approval_id, approval.safe_model_dump())
        self._append_event(
            mission_id,
            event_type="channel_outbound_approval_recorded",
            safe_summary="Operator channel outbound approval recorded.",
            metadata={
                "adapter_id": approval.adapter_id,
                "draft_id": approval.draft_id,
                "approval_id": approval.approval_id,
                "approval_hash": approval.approval_hash,
            },
        )
        return approval

    def send_outbound(
        self,
        *,
        mission_id: str,
        request: ChannelOutboundSendRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> ChannelOutboundSendResult:
        self._append_event(
            mission_id,
            event_type="channel_outbound_send_requested",
            safe_summary="Channel outbound send requested.",
            metadata={"adapter_id": request.adapter_id, "draft_id": request.draft_id},
        )
        self._assert_send_authority(mission_id, envelope)
        self._assert_mission_open(mission_id)
        config = self._load_config(mission_id, request.adapter_id)
        draft_request = self._draft_requests.get((mission_id, request.draft_id))
        if draft_request is None:
            raise ChannelConnectorRuntimeError("draft_ephemeral_recipient_context_missing")
        self._assert_channel_scope(config, draft_request.channel, draft_request.thread_ref)
        self._assert_recipient_policy(config, draft_request.recipients, draft_request.recipient_provenance)
        self._assert_envelope_recipient_scope(envelope, draft_request.recipients)
        self._assert_approval(mission_id, config, request)
        idempotency_hash = stable_hash(request.idempotency_key or f"{request.adapter_id}:{request.draft_id}:{request.approval_id or ''}")
        if self._idempotency_path(mission_id, idempotency_hash).exists():
            self._append_event(
                mission_id,
                event_type="channel_duplicate_send_blocked",
                safe_summary="Duplicate channel send blocked by idempotency key.",
                metadata={"adapter_id": request.adapter_id, "draft_id": request.draft_id, "idempotency_hash": idempotency_hash},
            )
            self._record_metric(
                mission_id,
                TelemetryMetricKind.CHANNEL_DUPLICATE_SEND_BLOCK_COUNT,
                1.0,
                "Channel duplicate send block count sample.",
                metadata={"adapter_id": request.adapter_id},
            )
            raise ChannelConnectorRuntimeError("duplicate_send_blocked")
        transport = self.registry.transport(request.adapter_id, draft_request.channel)
        if transport is None:
            raise ChannelConnectorRuntimeError("channel_transport_missing")

        organ = ChannelDraftSendOrganV1(sender=_organ_sender(transport))
        organ_result = organ.execute(
            ChannelDraftSendRequest(
                mission_id=mission_id,
                mode="send",
                channel=draft_request.channel,
                subject=draft_request.subject,
                body=draft_request.body,
                recipients=list(draft_request.recipients),
                recipient_provenance=dict(draft_request.recipient_provenance),
                send_authority_ref=f"mission_authority:{envelope.id if envelope else mission_id}",
                evidence_refs=list(draft_request.evidence_refs),
                objective_tags=list(draft_request.objective_tags),
            ),
            contract=ChannelDraftSendContract(
                allowed_channels=config.scope_policy.allowed_channels,
                send_authorized=True,
                max_recipients_per_window=min(
                    config.rate_limit_policy.max_recipients_per_window,
                    max(getattr(envelope, "max_recipients", 0), 0) or config.rate_limit_policy.max_recipients_per_window,
                ),
                require_recipient_provenance=config.recipient_policy.require_recipient_provenance,
            ),
        )
        if organ_result.status is not ChannelDraftSendStatus.SENT or organ_result.receipt is None:
            return self._blocked_send_result(
                mission_id,
                request,
                reason=organ_result.blocked_reason or organ_result.status.value,
                event_type="channel_outbound_send_blocked",
            )
        delivery = ChannelDeliveryResult(
            adapter_id=request.adapter_id,
            draft_id=request.draft_id,
            status=ChannelDeliveryStatus.SENT,
            delivery_ref=organ_result.receipt.delivery_ref,
            provider_message_ref_hash=stable_hash(organ_result.receipt.delivery_ref) if organ_result.receipt.delivery_ref else None,
            safe_summary="Channel message sent through injected transport and channel organ.",
        ).with_hash()
        self._write_json(mission_id, "deliveries", delivery.delivery_id, delivery.safe_model_dump())
        adapter_receipt = ChannelAdapterReceipt(
            adapter_id=request.adapter_id,
            draft_id=request.draft_id,
            mission_id=mission_id,
            channel_receipt_ref=organ_result.receipt.receipt_id,
            channel_receipt_hash=stable_hash(organ_result.receipt.safe_model_dump() if hasattr(organ_result.receipt, "safe_model_dump") else organ_result.receipt.model_dump(mode="json")),
            channel_finalgate_ref=organ_result.finalgate_certificate.certificate_id if organ_result.finalgate_certificate else None,
            delivery_ref_hash=stable_hash(organ_result.receipt.delivery_ref) if organ_result.receipt.delivery_ref else None,
            idempotency_key_hash=idempotency_hash,
            recipient_hashes=list(organ_result.receipt.recipient_hashes),
            evidence_refs=list(organ_result.receipt.evidence_refs),
        ).with_hash()
        self._write_json(mission_id, "receipts", adapter_receipt.receipt_id, adapter_receipt.safe_model_dump())
        finalgate = ChannelAdapterFinalGateCertificate(
            adapter_id=request.adapter_id,
            draft_id=request.draft_id,
            mission_id=mission_id,
            passed=bool(organ_result.finalgate_certificate and organ_result.finalgate_certificate.passed),
            receipt_ref=adapter_receipt.receipt_id,
            channel_finalgate_ref=adapter_receipt.channel_finalgate_ref,
            failures=list(organ_result.finalgate_certificate.failures if organ_result.finalgate_certificate else ["missing_channel_finalgate"]),
        )
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        send_result = ChannelOutboundSendResult(
            adapter_id=request.adapter_id,
            draft_id=request.draft_id,
            mission_id=mission_id,
            status="sent",
            delivery_result=delivery,
            adapter_receipt=adapter_receipt,
            finalgate_certificate=finalgate,
            channel_receipt_ref=adapter_receipt.channel_receipt_ref,
            channel_finalgate_ref=adapter_receipt.channel_finalgate_ref,
            safe_summary="Channel outbound message sent through governed adapter runtime.",
        ).with_hash()
        self._write_json(mission_id, "send_results", send_result.send_result_id, send_result.safe_model_dump())
        self.store.atomic_write_json(
            self._idempotency_path(mission_id, idempotency_hash),
            {"idempotency_hash": idempotency_hash, "send_result_id": send_result.send_result_id},
        )
        self._append_event(
            mission_id,
            event_type="channel_outbound_sent",
            safe_summary=send_result.safe_summary,
            metadata={
                "adapter_id": request.adapter_id,
                "draft_id": request.draft_id,
                "result_hash": stable_hash(send_result.send_result_id),
                "delivery_record_hash": delivery.delivery_hash,
                "proof_record_hash": adapter_receipt.receipt_hash,
            },
            receipt_refs=[adapter_receipt.receipt_id, adapter_receipt.channel_receipt_ref or ""],
            finalgate_certificate_refs=[finalgate.certificate_id, finalgate.channel_finalgate_ref or ""],
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.CHANNEL_OUTBOUND_SEND_COUNT,
            1.0,
            "Channel outbound send count sample.",
            metadata={"adapter_id": request.adapter_id},
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.CHANNEL_RECEIPT_COMPLETENESS,
            1.0,
            "Channel receipt completeness sample.",
            metadata={"adapter_id": request.adapter_id},
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.CHANNEL_DELIVERY_SUCCESS_RATE,
            1.0,
            "Channel delivery success sample.",
            metadata={"adapter_id": request.adapter_id},
        )
        return send_result

    def _blocked_send_result(
        self,
        mission_id: str,
        request: ChannelOutboundSendRequest,
        *,
        reason: str,
        event_type: str,
    ) -> ChannelOutboundSendResult:
        result = ChannelOutboundSendResult(
            adapter_id=request.adapter_id,
            draft_id=request.draft_id,
            mission_id=mission_id,
            status="blocked",
            blocked_reason=reason,
            safe_summary=f"Channel outbound send blocked: {reason}.",
        ).with_hash()
        self._write_json(mission_id, "send_results", result.send_result_id, result.safe_model_dump())
        self._append_event(
            mission_id,
            event_type=event_type,
            safe_summary=result.safe_summary,
            metadata={"adapter_id": request.adapter_id, "draft_id": request.draft_id, "reason": reason},
        )
        self._record_metric(
            mission_id,
            TelemetryMetricKind.CHANNEL_OUTBOUND_BLOCK_COUNT,
            1.0,
            "Channel outbound block count sample.",
            metadata={"adapter_id": request.adapter_id, "reason": reason},
        )
        raise ChannelConnectorRuntimeError(reason)

    def _assert_send_authority(self, mission_id: str, envelope: MissionAuthorityEnvelope | None) -> None:
        if envelope is None:
            raise ChannelConnectorRuntimeError("channel_send_authority_missing")
        if envelope.id != mission_id:
            raise ChannelConnectorRuntimeError("mission_authority_envelope_mismatch")
        if getattr(envelope, "revoked_at", None) is not None:
            self._append_event(mission_id, event_type="channel_revocation_detected", safe_summary="Channel send blocked by revoked authority.")
            raise ChannelConnectorRuntimeError("mission_authority_revoked")
        if envelope.resolved_expires_at() <= datetime.now(UTC):
            raise ChannelConnectorRuntimeError("mission_authority_expired")
        if "channel_send" not in set(getattr(envelope, "allowed_actions", []) or []):
            raise ChannelConnectorRuntimeError("channel_send_not_allowed_by_envelope")
        tools = set(getattr(envelope, "allowed_tools", []) or [])
        if "channel_draft_send" not in tools and not any(tool.startswith("channel:") for tool in tools):
            raise ChannelConnectorRuntimeError("channel_tool_not_allowed_by_envelope")

    def _assert_mission_open(self, mission_id: str) -> None:
        reason = self.kernel.terminal_block_reason(mission_id)
        if reason:
            if reason.endswith(":killed"):
                self._append_event(mission_id, event_type="channel_kill_switch_triggered", safe_summary="Channel send blocked by mission kill switch.")
            raise ChannelConnectorRuntimeError(reason)

    def _assert_channel_scope(self, config: ChannelAdapterConfig, channel: str, thread_ref: str | None) -> None:
        if channel.lower() not in config.scope_policy.allowed_channels:
            raise ChannelConnectorRuntimeError("channel_not_in_scope")
        if config.scope_policy.allowed_threads and thread_ref is not None and thread_ref not in config.scope_policy.allowed_threads:
            raise ChannelConnectorRuntimeError("thread_not_in_scope")

    def _assert_recipient_policy(
        self,
        config: ChannelAdapterConfig,
        recipients: list[str],
        provenance: dict[str, str],
    ) -> None:
        if len(recipients) > config.recipient_policy.max_recipients:
            raise ChannelConnectorRuntimeError("recipient_limit_exceeded")
        for recipient in recipients:
            normalized = recipient.strip().lower()
            if normalized in set(config.recipient_policy.blocked_recipients):
                raise ChannelConnectorRuntimeError("recipient_blocked")
            if config.recipient_policy.allowed_recipients and normalized not in set(config.recipient_policy.allowed_recipients):
                raise ChannelConnectorRuntimeError("recipient_not_allowed")
            if config.recipient_policy.allowed_domains and _domain_for_recipient(normalized) not in set(config.recipient_policy.allowed_domains):
                raise ChannelConnectorRuntimeError("recipient_not_allowed")
            if config.recipient_policy.require_recipient_provenance and recipient not in provenance:
                raise ChannelConnectorRuntimeError("recipient_provenance_missing")

    def _assert_envelope_recipient_scope(self, envelope: MissionAuthorityEnvelope | None, recipients: list[str]) -> None:
        assert envelope is not None
        if len(recipients) > envelope.max_recipients:
            raise ChannelConnectorRuntimeError("mission_recipient_budget_exceeded")
        allowed_domains = set(envelope.allowed_domains or [])
        if allowed_domains:
            for recipient in recipients:
                if _domain_for_recipient(recipient) not in allowed_domains:
                    raise ChannelConnectorRuntimeError("recipient_not_allowed")

    def _assert_approval(
        self,
        mission_id: str,
        config: ChannelAdapterConfig,
        request: ChannelOutboundSendRequest,
    ) -> None:
        if request.requested_by not in {"operator", "operator_policy", "manual_operator"}:
            raise ChannelConnectorRuntimeError("operator_approval_required")
        if not config.approval_policy.approval_required_for_send:
            return
        if not request.approval_id:
            self._record_metric(
                mission_id,
                TelemetryMetricKind.CHANNEL_APPROVAL_REQUIRED_COUNT,
                1.0,
                "Channel approval required count sample.",
                metadata={"adapter_id": request.adapter_id},
            )
            raise ChannelConnectorRuntimeError("operator_approval_required")
        approval = self._approvals.get((mission_id, request.approval_id)) or self._load_approval(mission_id, request.approval_id)
        if approval is None or approval.draft_id != request.draft_id or approval.adapter_id != request.adapter_id:
            raise ChannelConnectorRuntimeError("operator_approval_required")
        if not approval.verify_hash() or not approval.approved:
            raise ChannelConnectorRuntimeError("operator_approval_required")

    def _load_config(self, mission_id: str, adapter_id: str) -> ChannelAdapterConfig:
        try:
            return self.registry.config(adapter_id)
        except ChannelConnectorRuntimeError:
            path = self._path(mission_id, "adapters", adapter_id)
            if not path.exists():
                raise
            config = ChannelAdapterConfig.model_validate_json(path.read_text(encoding="utf-8"))
            if not config.verify_hash():
                raise ChannelConnectorRuntimeError("channel_adapter_config_hash_mismatch")
            self.registry.register(config)
            return config

    def _load_approval(self, mission_id: str, approval_id: str) -> ChannelOutboundApproval | None:
        path = self._path(mission_id, "approvals", approval_id)
        if not path.exists():
            return None
        approval = ChannelOutboundApproval.model_validate_json(path.read_text(encoding="utf-8"))
        self._approvals[(mission_id, approval.approval_id)] = approval
        return approval

    def _write_json(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        self.store.atomic_write_json(self._path(mission_id, category, name), payload)

    def _path(self, mission_id: str, category: str, name: str) -> Path:
        return self.store.mission_dir(mission_id, create=True) / "channel_adapters" / category / f"{stable_hash(name)[:24]}.json"

    def _idempotency_path(self, mission_id: str, idempotency_hash: str) -> Path:
        return self.store.mission_dir(mission_id, create=True) / "channel_adapters" / "idempotency" / f"{idempotency_hash[:24]}.json"

    def _append_event(
        self,
        mission_id: str,
        *,
        event_type: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
    ):
        return self.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata or {},
            receipt_refs=[ref for ref in (receipt_refs or []) if ref],
            finalgate_certificate_refs=[ref for ref in (finalgate_certificate_refs or []) if ref],
        )

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = getattr(self.store, "telemetry_sink", None)
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.CHANNEL_ADAPTER,
                domain=TelemetryDomain.PRODUCT_POWER,
                metric_kind=metric_kind,
                value=value,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )


def _organ_sender(transport: ChannelTransport):
    def _sender(request: Any) -> ChannelSendTransportReceipt:
        result = transport(request)
        if isinstance(result, ChannelSendTransportReceipt):
            return result
        if isinstance(result, ChannelDeliveryResult):
            return ChannelSendTransportReceipt(delivery_ref=result.delivery_ref or result.delivery_id)
        if isinstance(result, dict):
            return ChannelSendTransportReceipt(delivery_ref=str(result.get("delivery_ref") or result.get("delivery_id") or stable_hash(result)))
        return ChannelSendTransportReceipt(delivery_ref=stable_hash(str(result)))

    return _sender


def _domain_for_recipient(recipient: str) -> str:
    if "@" in recipient:
        return recipient.rsplit("@", 1)[-1].strip().lower()
    return recipient.strip().lower()
