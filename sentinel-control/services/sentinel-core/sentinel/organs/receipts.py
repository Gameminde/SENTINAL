from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from pydantic import Field, model_validator

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.contracts import OrganPromotionLevel, PROMOTION_ORDER
from sentinel.organs.dry_run import OrganDryRunReceipt, _hash_action_payload
from sentinel.organs.exceptions import ReceiptIntegrityError
from sentinel.organs.kill_switch import OrganKillSwitch
from sentinel.shared.models import SentinelModel, new_id

if TYPE_CHECKING:
    from sentinel.perf.hot_cold.cold_receipt_store import ColdReceiptStore
    from sentinel.perf.hot_cold.receipt_index import ReceiptIndex


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
    action_payload_hash: str
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
                "action_payload_hash": self.action_payload_hash,
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
        cold_store: ColdReceiptStore | None = None,
        receipt_index: ReceiptIndex | None = None,
    ) -> OrganExecutionReceipt:
        receipt = cls(
            mission_id=dry_run.mission_id,
            organ_id=dry_run.organ_id,
            action=dry_run.action,
            dry_run_receipt_id=dry_run.id,
            promotion_level=promotion_level,
            output_summary=output_summary,
            action_payload_hash=dry_run.action_payload_hash,
            execution_started=False,
            execution_completed=False,
            trace_refs=list(dry_run.trace_refs),
        )
        if event_bus is None:
            # Persist to cold store even without event_bus
            _persist_receipt_to_cold(receipt, cold_store=cold_store, receipt_index=receipt_index)
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
        final_receipt = cls(
            id=receipt.id,
            mission_id=receipt.mission_id,
            organ_id=receipt.organ_id,
            action=receipt.action,
            dry_run_receipt_id=receipt.dry_run_receipt_id,
            promotion_level=receipt.promotion_level,
            output_summary=receipt.output_summary,
            output_ref=receipt.output_ref,
            action_payload_hash=dry_run.action_payload_hash,
            execution_started=False,
            execution_completed=False,
            trace_refs=[*receipt.trace_refs, event.id],
        )
        # Persist to cold store after event emission (Requirement 5.2, 5.5)
        _persist_receipt_to_cold(final_receipt, cold_store=cold_store, receipt_index=receipt_index)
        return final_receipt

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
        execution_action_payload: dict[str, Any],
        output_ref: str | None = None,
        execution_completed: bool = False,
        event_bus: EventBus | None = None,
        cold_store: ColdReceiptStore | None = None,
        receipt_index: ReceiptIndex | None = None,
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
        actual_hash = _hash_action_payload(execution_action_payload)
        if actual_hash != dry_run.action_payload_hash:
            raise ReceiptIntegrityError(
                f"execution_action_payload_hash_mismatch: expected={dry_run.action_payload_hash} actual={actual_hash}"
            )
        receipt = cls(
            mission_id=dry_run.mission_id,
            organ_id=dry_run.organ_id,
            action=dry_run.action,
            dry_run_receipt_id=dry_run.id,
            promotion_level=promotion_level,
            output_summary=output_summary,
            output_ref=output_ref,
            action_payload_hash=actual_hash,
            execution_started=True,
            execution_completed=execution_completed,
            trace_refs=trace_refs,
        )
        if event_bus is None:
            # Persist to cold store even without event_bus
            _persist_receipt_to_cold(receipt, cold_store=cold_store, receipt_index=receipt_index)
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
        final_receipt = cls(
            id=receipt.id,
            mission_id=receipt.mission_id,
            organ_id=receipt.organ_id,
            action=receipt.action,
            dry_run_receipt_id=receipt.dry_run_receipt_id,
            promotion_level=receipt.promotion_level,
            output_summary=receipt.output_summary,
            output_ref=receipt.output_ref,
            action_payload_hash=actual_hash,
            execution_started=True,
            execution_completed=execution_completed,
            trace_refs=[*receipt.trace_refs, event.id],
        )
        # Persist to cold store after event emission (Requirement 5.2, 5.5)
        _persist_receipt_to_cold(final_receipt, cold_store=cold_store, receipt_index=receipt_index)
        return final_receipt


def _persist_receipt_to_cold(
    receipt: OrganExecutionReceipt,
    *,
    cold_store: ColdReceiptStore | None = None,
    receipt_index: ReceiptIndex | None = None,
) -> None:
    """Persist an OrganExecutionReceipt to the cold store and/or index.

    Guards with ``if ... is not None:`` so default behavior is unchanged
    when neither cold_store nor receipt_index is provided.

    Priority order (Requirement 5.2, 5.5):
    - If receipt_index is provided, use ``persist_and_index`` which handles
      both cold-store persistence and indexing atomically.
    - If only cold_store is provided (no index), call ``cold_store.persist``
      directly.
    - If neither is provided, this is a no-op (preserves existing behavior).
    """
    if receipt_index is not None:
        receipt_index.persist_and_index(receipt)
    elif cold_store is not None:
        cold_store.persist(receipt)
