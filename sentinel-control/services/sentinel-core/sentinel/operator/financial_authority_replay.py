from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.financial_authority_models import (
    FinancialAuthorityConfig,
    FinancialCheckpoint,
    FinancialFinalGateCertificate,
    FinancialReplayView,
    SpendPlan,
    SpendReceipt,
    TradeOrderReceipt,
    TradingPlan,
)
from sentinel.operator.store import MissionRunStore


class FinancialAuthorityReplayBuilder:
    def __init__(self, store: Any) -> None:
        self._financial_store = store if hasattr(store, "_mission_store") else None
        self._store = getattr(store, "_mission_store", store)
        if not isinstance(self._store, MissionRunStore):
            self._store = store

    def build(self, mission_id: str) -> FinancialReplayView:
        root = self._root(mission_id)
        configs = _load_many(root / "configs", FinancialAuthorityConfig)
        spend_plans = _load_many(root / "spend_plans", SpendPlan)
        trade_plans = _load_many(root / "trade_plans", TradingPlan)
        spend_receipts = _load_many(root / "spend_receipts", SpendReceipt)
        trade_receipts = _load_many(root / "trade_receipts", TradeOrderReceipt)
        checkpoints = _load_many(root / "checkpoints", FinancialCheckpoint)
        finalgate = _load_many(root / "finalgate", FinancialFinalGateCertificate)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (configs, spend_plans, trade_plans):
            for item in collection:
                verifier = getattr(item, "verify_hash", None)
                if callable(verifier) and not verifier():
                    tampered = True
        self._append_replay_event(mission_id)
        events = [
            event
            for event in self._store.load_events(mission_id)
            if (
                event.event_type.startswith("financial_")
                or event.event_type.startswith("spend_")
                or event.event_type.startswith("payment_")
                or event.event_type.startswith("transfer_")
                or event.event_type.startswith("trade_")
                or event.event_type.startswith("paper_trade_")
                or event.event_type in {"finalgate_passed", "finalgate_failed"}
            )
        ]
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        for receipt in [*spend_receipts, *trade_receipts]:
            receipt_refs.append(receipt.receipt_id)
        for certificate in finalgate:
            finalgate_refs.append(certificate.certificate_id)
        for event in events:
            receipt_refs.extend(event.receipt_refs)
            finalgate_refs.extend(event.finalgate_certificate_refs)
        return FinancialReplayView(
            mission_id=mission_id,
            configs=configs,
            spend_plans=spend_plans,
            trade_plans=trade_plans,
            spend_receipts=spend_receipts,
            trade_receipts=trade_receipts,
            checkpoints=checkpoints,
            finalgate_certificates=finalgate,
            receipt_refs=list(dict.fromkeys(receipt_refs)),
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            tampered=tampered,
            executed_live_money=False,
            placed_live_trade=False,
            materialized_credential=False,
            replayed_financial_action=False,
            called_live_provider=False,
            called_live_broker=False,
            filled_card_field=False,
            submitted_checkout=False,
            submitted_order=False,
        )

    def _append_replay_event(self, mission_id: str) -> None:
        if self._financial_store is not None and hasattr(self._financial_store, "append_event"):
            self._financial_store.append_event(
                mission_id,
                "financial_replay_built",
                "Financial authority replay built from existing records without financial execution.",
                metadata={"replay_reexecutes": False},
            )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id, create=True) / "financial_authority"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


__all__ = ["FinancialAuthorityReplayBuilder"]
