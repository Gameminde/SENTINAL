from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.risk import OrganRiskProfile
from sentinel.shared.models import SentinelModel, new_id


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_action_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class OrganDryRunReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("odry"))
    mission_id: str
    organ_id: str
    action: str
    reason: str
    preview: dict[str, Any]
    risk_profile_id: str
    authority_id: str
    evidence_refs: list[str]
    preview_hash: str = ""
    action_payload_hash: str = ""
    execution_started: bool = False
    accepted_for_review: bool = True
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> OrganDryRunReceipt:
        if not self.evidence_refs:
            raise ValueError("OrganDryRunReceipt requires evidence refs.")
        if self.execution_started:
            raise ValueError("OrganDryRunReceipt cannot start execution.")
        if self.authority_expansion:
            raise ValueError("OrganDryRunReceipt cannot expand authority.")
        expected_hash = self.expected_preview_hash()
        if self.preview_hash and self.preview_hash != expected_hash:
            raise ValueError("OrganDryRunReceipt preview hash mismatch.")
        if not self.preview_hash:
            self.preview_hash = expected_hash
        expected_action_payload_hash = self.expected_action_payload_hash()
        if self.action_payload_hash and self.action_payload_hash != expected_action_payload_hash:
            raise ValueError("OrganDryRunReceipt action payload hash mismatch.")
        if not self.action_payload_hash:
            self.action_payload_hash = expected_action_payload_hash
        return self

    def expected_action_payload_hash(self) -> str:
        return _hash_action_payload(
            {
                "action": self.action,
                "preview": self.preview,
            }
        )

    def expected_preview_hash(self) -> str:
        return _hash_payload(
            {
                "mission_id": self.mission_id,
                "organ_id": self.organ_id,
                "action": self.action,
                "reason": self.reason,
                "preview": self.preview,
                "risk_profile_id": self.risk_profile_id,
                "authority_id": self.authority_id,
                "evidence_refs": self.evidence_refs,
            }
        )

    @classmethod
    def create(
        cls,
        authority: OrganAuthorityEnvelope,
        risk_profile: OrganRiskProfile,
        *,
        reason: str,
        preview: dict[str, Any],
        evidence_refs: list[str],
        event_bus: EventBus | None = None,
    ) -> OrganDryRunReceipt:
        receipt = cls(
            mission_id=authority.mission_id,
            organ_id=authority.organ_id,
            action=risk_profile.action,
            reason=reason,
            preview=preview,
            risk_profile_id=risk_profile.id,
            authority_id=authority.id,
            evidence_refs=evidence_refs,
        )
        if event_bus is None:
            return receipt
        event = event_bus.append(
            AgentEventType.ORGAN_DRY_RUN_RECORDED,
            "External organ dry-run receipt recorded without execution.",
            payload={
                "dry_run_receipt_id": receipt.id,
                "organ_id": receipt.organ_id,
                "action": receipt.action,
                "preview_hash": receipt.preview_hash,
                "execution_started": False,
                "authority_expansion": False,
            },
            trace_refs=[*authority.trace_refs, *risk_profile.trace_refs],
        )
        return receipt.model_copy(update={"trace_refs": [event.id]})
