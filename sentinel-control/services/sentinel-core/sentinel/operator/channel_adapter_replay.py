from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.channel_adapter_models import (
    ChannelAdapterConfig,
    ChannelAdapterReceipt,
    ChannelAdapterReplayView,
    ChannelInboundMessage,
    ChannelOutboundApproval,
    ChannelOutboundDraft,
    ChannelOutboundSendResult,
)
from sentinel.operator.store import MissionRunStore


class ChannelAdapterReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str) -> ChannelAdapterReplayView:
        root = self._root(mission_id)
        adapters = _load_many(root / "adapters", ChannelAdapterConfig)
        inbound = _load_many(root / "inbound", ChannelInboundMessage)
        drafts = _load_many(root / "drafts", ChannelOutboundDraft)
        approvals = _load_many(root / "approvals", ChannelOutboundApproval)
        send_results = _load_many(root / "send_results", ChannelOutboundSendResult)
        receipts = _load_many(root / "receipts", ChannelAdapterReceipt)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (adapters, inbound, drafts, approvals, send_results, receipts):
            for item in collection:
                if hasattr(item, "verify_hash") and not item.verify_hash():
                    tampered = True
        events = [
            event
            for event in self._store.load_events(mission_id)
            if event.event_type.startswith("channel_")
        ]
        finalgate_refs = []
        for result in send_results:
            if result.finalgate_certificate is not None:
                finalgate_refs.append(result.finalgate_certificate.certificate_id)
            if result.channel_finalgate_ref:
                finalgate_refs.append(result.channel_finalgate_ref)
        return ChannelAdapterReplayView(
            mission_id=mission_id,
            adapters=adapters,
            inbound_messages=inbound,
            outbound_drafts=drafts,
            approvals=approvals,
            send_results=send_results,
            receipts=receipts,
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            memory_feedback_refs=[],
            tampered=tampered,
            reexecuted_actions=False,
        )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id) / "channel_adapters"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]
