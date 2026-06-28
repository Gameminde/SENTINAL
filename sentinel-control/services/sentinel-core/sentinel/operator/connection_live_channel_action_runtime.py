from __future__ import annotations

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.channel_adapter import ChannelConnectorRuntime, ChannelConnectorRuntimeError
from sentinel.operator.channel_adapter_models import ChannelOutboundRequest, ChannelOutboundSendRequest
from sentinel.operator.connection_live_channel_action_models import (
    LiveChannelActionResult,
    LiveChannelSendDecision,
    live_channel_hash,
)


class ModelLedLiveChannelActionRuntime:
    """Execute a bounded model-led channel send through the channel adapter runtime."""

    def __init__(self, channel_runtime: ChannelConnectorRuntime) -> None:
        self.channel_runtime = channel_runtime

    def execute_send_decision(
        self,
        *,
        mission_id: str,
        decision: LiveChannelSendDecision,
        envelope: MissionAuthorityEnvelope,
    ) -> LiveChannelActionResult:
        config = self.channel_runtime.registry.config(decision.adapter_id)
        if config.approval_policy.approval_required_for_send:
            raise ChannelConnectorRuntimeError("mission_level_channel_grant_required")

        draft = self.channel_runtime.create_outbound_draft(
            mission_id=mission_id,
            request=ChannelOutboundRequest(
                adapter_id=decision.adapter_id,
                channel=decision.channel,
                subject=decision.subject,
                body=decision.body,
                recipients=list(decision.recipients),
                recipient_provenance=dict(decision.recipient_provenance),
                thread_ref=decision.thread_ref,
                evidence_refs=list(decision.evidence_refs),
                objective_tags=["model_led_channel_action", "mission_level_destination_grant"],
            ),
        )
        send_result = self.channel_runtime.send_outbound(
            mission_id=mission_id,
            request=ChannelOutboundSendRequest(
                adapter_id=decision.adapter_id,
                draft_id=draft.draft_id,
                idempotency_key=decision.idempotency_key or decision.decision_id,
                requested_by="operator_policy",
            ),
            envelope=envelope,
        )
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        delivery_ref_hash = None
        if send_result.adapter_receipt is not None:
            receipt_refs.append(send_result.adapter_receipt.receipt_id)
            if send_result.adapter_receipt.channel_receipt_ref:
                receipt_refs.append(send_result.adapter_receipt.channel_receipt_ref)
            delivery_ref_hash = send_result.adapter_receipt.delivery_ref_hash
        if send_result.finalgate_certificate is not None:
            finalgate_refs.append(send_result.finalgate_certificate.certificate_id)
            if send_result.finalgate_certificate.channel_finalgate_ref:
                finalgate_refs.append(send_result.finalgate_certificate.channel_finalgate_ref)

        result_payload = {
            "decision_id": decision.decision_id,
            "action": decision.action,
            "adapter_id": decision.adapter_id,
            "channel": decision.channel,
            "draft_ref": draft.draft_id,
            "channel_send_result_ref": send_result.send_result_id,
            "receipt_refs": receipt_refs,
            "finalgate_refs": finalgate_refs,
            "evidence_refs": list(decision.evidence_refs),
            "delivery_ref_hash": delivery_ref_hash,
            "decision_safe_hash": stable_hash(decision.safe_summary()),
            "model_led": True,
            "per_message_approval_required": False,
        }
        return LiveChannelActionResult(
            decision_id=decision.decision_id,
            action=decision.action,
            status="sent",
            model_led=True,
            per_message_approval_required=False,
            draft_ref=draft.draft_id,
            channel_send_result_ref=send_result.send_result_id,
            receipt_refs=tuple(receipt_refs),
            finalgate_refs=tuple(finalgate_refs),
            evidence_refs=decision.evidence_refs,
            delivery_ref_hash=delivery_ref_hash,
            result_hash=live_channel_hash(result_payload),
        )


__all__ = ["ModelLedLiveChannelActionRuntime"]
