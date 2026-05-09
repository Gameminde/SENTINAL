from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.channels.draft import ChannelMessageDraft
from sentinel.organs.channels.send_gate import ChannelSendGateDecision
from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ChannelDraftReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chdrcpt"))
    mission_id: str
    organ_id: str
    draft_id: str
    channel: str
    lane: str
    subject: str | None = None
    body_preview: str
    evidence_refs: list[str]
    trace_refs: list[str]
    draft_hash: str = ""
    send_attempted: bool = False
    execution_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ChannelDraftReceipt:
        if not self.evidence_refs:
            raise ValueError("ChannelDraftReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("ChannelDraftReceipt requires trace refs.")
        if self.send_attempted or self.execution_started:
            raise ValueError("ChannelDraftReceipt cannot send or execute.")
        if self.authority_expansion:
            raise ValueError("ChannelDraftReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.draft_hash and self.draft_hash != expected:
            raise ValueError("ChannelDraftReceipt hash mismatch.")
        if not self.draft_hash:
            self.draft_hash = expected
        return self

    @classmethod
    def create(
        cls,
        draft: ChannelMessageDraft,
        authority: OrganAuthorityEnvelope,
        *,
        trace_refs: list[str],
    ) -> ChannelDraftReceipt:
        return cls(
            mission_id=authority.mission_id,
            organ_id=authority.organ_id,
            draft_id=draft.id,
            channel=draft.channel,
            lane=draft.lane.value,
            subject=draft.subject,
            body_preview=draft.body[:160],
            evidence_refs=list(draft.evidence_refs),
            trace_refs=[*draft.trace_refs, *authority.trace_refs, *trace_refs],
        )

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "organ_id": self.organ_id,
                "draft_id": self.draft_id,
                "channel": self.channel,
                "lane": self.lane,
                "subject": self.subject,
                "body_preview": self.body_preview,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
            }
        )


class ChannelSendGateReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chsrcpt"))
    mission_id: str
    organ_id: str
    draft_id: str
    decision_id: str
    lane: str
    reasons: list[str]
    evidence_refs: list[str]
    trace_refs: list[str]
    receipt_hash: str = ""
    send_attempted: bool = False
    execution_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ChannelSendGateReceipt:
        if not self.evidence_refs:
            raise ValueError("ChannelSendGateReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("ChannelSendGateReceipt requires trace refs.")
        if self.send_attempted or self.execution_started:
            raise ValueError("ChannelSendGateReceipt cannot send or execute.")
        if self.authority_expansion:
            raise ValueError("ChannelSendGateReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("ChannelSendGateReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    @classmethod
    def create(
        cls,
        draft: ChannelMessageDraft,
        decision: ChannelSendGateDecision,
        authority: OrganAuthorityEnvelope,
        *,
        trace_refs: list[str],
    ) -> ChannelSendGateReceipt:
        return cls(
            mission_id=authority.mission_id,
            organ_id=authority.organ_id,
            draft_id=draft.id,
            decision_id=decision.id,
            lane=decision.lane.value,
            reasons=list(decision.reasons),
            evidence_refs=list(draft.evidence_refs),
            trace_refs=[*draft.trace_refs, *authority.trace_refs, *trace_refs],
        )

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "organ_id": self.organ_id,
                "draft_id": self.draft_id,
                "decision_id": self.decision_id,
                "lane": self.lane,
                "reasons": self.reasons,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
            }
        )
