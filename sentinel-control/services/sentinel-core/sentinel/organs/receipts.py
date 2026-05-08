from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.event_bus import EventBus
from sentinel.agent.events import AgentEventType
from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.contracts import OrganPromotionLevel, PROMOTION_ORDER
from sentinel.organs.dry_run import OrganDryRunReceipt
from sentinel.organs.kill_switch import OrganKillSwitch
from sentinel.shared.models import SentinelModel, new_id


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class OrganExecutionReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("oexec"))
    mission_id: str
    organ_id: str
    action: str
    dry_run_receipt_id: str
    promotion_level: OrganPromotionLevel
    output_summary: str
    output_ref: str | None = None
    receipt_hash: str = ""
    execution_started: bool = False
    execution_completed: bool = False
    authority_expansion: bool = False
    trace_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> OrganExecutionReceipt:
        if self.authority_expansion:
            raise ValueError("OrganExecutionReceipt cannot expand authority.")
        if self.execution_started and not self.trace_refs:
            raise ValueError("Started OrganExecutionReceipt requires trace refs.")
        if self.execution_started and PROMOTION_ORDER[self.promotion_level] < PROMOTION_ORDER[OrganPromotionLevel.L6_LIMITED_EXECUTION]:
            raise ValueError("Organ execution cannot start before L6 limited execution.")
        expected_hash = self.expected_receipt_hash()
        if self.receipt_hash and self.receipt_hash != expected_hash:
            raise ValueError("OrganExecutionReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected_hash
        return self

    def expected_receipt_hash(self) -> str:
        return _hash_payload(
            {
                "mission_id": self.mission_id,
                "organ_id": self.organ_id,
                "action": self.action,
                "dry_run_receipt_id": self.dry_run_receipt_id,
                "promotion_level": self.promotion_level.value,
                "output_summary": self.output_summary,
                "output_ref": self.output_ref,
                "trace_refs": self.trace_refs,
            }
        )

    @classmethod
    def planned_only(
        cls,
        dry_run: OrganDryRunReceipt,
        *,
        promotion_level: OrganPromotionLevel,
        output_summary: str,
        event_bus: EventBus | None = None,
    ) -> OrganExecutionReceipt:
        receipt = cls(
            mission_id=dry_run.mission_id,
            organ_id=dry_run.organ_id,
            action=dry_run.action,
            dry_run_receipt_id=dry_run.id,
            promotion_level=promotion_level,
            output_summary=output_summary,
            execution_started=False,
            execution_completed=False,
            trace_refs=list(dry_run.trace_refs),
        )
        if event_bus is None:
            return receipt
        event = event_bus.append(
            AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
            "External organ execution receipt recorded as planned-only.",
            payload={
                "execution_receipt_id": receipt.id,
                "dry_run_receipt_id": dry_run.id,
                "organ_id": receipt.organ_id,
                "action": receipt.action,
                "execution_started": False,
                "execution_completed": False,
                "authority_expansion": False,
            },
            trace_refs=list(dry_run.trace_refs),
        )
        return cls(
            id=receipt.id,
            mission_id=receipt.mission_id,
            organ_id=receipt.organ_id,
            action=receipt.action,
            dry_run_receipt_id=receipt.dry_run_receipt_id,
            promotion_level=receipt.promotion_level,
            output_summary=receipt.output_summary,
            output_ref=receipt.output_ref,
            execution_started=False,
            execution_completed=False,
            trace_refs=[*receipt.trace_refs, event.id],
        )

    @classmethod
    def started(
        cls,
        dry_run: OrganDryRunReceipt,
        authority: OrganAuthorityEnvelope,
        kill_switch: OrganKillSwitch,
        *,
        promotion_level: OrganPromotionLevel,
        output_summary: str,
        trace_refs: list[str],
        output_ref: str | None = None,
        execution_completed: bool = False,
        event_bus: EventBus | None = None,
    ) -> OrganExecutionReceipt:
        if authority.id != dry_run.authority_id:
            raise ValueError("Organ execution request authority does not match dry-run receipt.")
        if authority.organ_id != dry_run.organ_id:
            raise ValueError("Organ execution request organ does not match dry-run receipt.")
        if authority.dry_run_only or not authority.execution_authorized:
            raise ValueError("Organ execution request is not execution authorized.")
        if kill_switch.organ_id != dry_run.organ_id:
            raise ValueError("Organ execution request kill switch does not match organ.")
        if kill_switch.triggered or not kill_switch.execution_allowed:
            raise ValueError("Organ execution request blocked by kill switch.")
        receipt = cls(
            mission_id=dry_run.mission_id,
            organ_id=dry_run.organ_id,
            action=dry_run.action,
            dry_run_receipt_id=dry_run.id,
            promotion_level=promotion_level,
            output_summary=output_summary,
            output_ref=output_ref,
            execution_started=True,
            execution_completed=execution_completed,
            trace_refs=trace_refs,
        )
        if event_bus is None:
            return receipt
        event = event_bus.append(
            AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
            "External organ execution-shaped receipt recorded after authority and kill-switch checks.",
            payload={
                "execution_receipt_id": receipt.id,
                "dry_run_receipt_id": dry_run.id,
                "organ_id": receipt.organ_id,
                "action": receipt.action,
                "execution_started": True,
                "execution_completed": execution_completed,
                "authority_expansion": False,
            },
            trace_refs=trace_refs,
        )
        return cls(
            id=receipt.id,
            mission_id=receipt.mission_id,
            organ_id=receipt.organ_id,
            action=receipt.action,
            dry_run_receipt_id=receipt.dry_run_receipt_id,
            promotion_level=receipt.promotion_level,
            output_summary=receipt.output_summary,
            output_ref=receipt.output_ref,
            execution_started=True,
            execution_completed=execution_completed,
            trace_refs=[*receipt.trace_refs, event.id],
        )
