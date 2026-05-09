from __future__ import annotations

from sentinel.organs.desktop.receipts import DesktopActionReceipt
from sentinel.shared.models import SentinelModel


class DesktopFinalGateAdapter(SentinelModel):
    required_fields: list[str] = [
        "mission_id",
        "sidecar_id",
        "action_family",
        "authority_refs",
        "evidence_refs",
        "receipt_hash",
    ]

    def accepts(self, receipt: DesktopActionReceipt) -> bool:
        return all(getattr(receipt, field) for field in self.required_fields) and not receipt.execution_started
