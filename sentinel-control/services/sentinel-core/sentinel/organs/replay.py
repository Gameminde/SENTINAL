from __future__ import annotations

from pydantic import Field

from sentinel.organs.dry_run import OrganDryRunReceipt
from sentinel.organs.receipts import OrganExecutionReceipt
from sentinel.shared.models import SentinelModel, new_id


class OrganReplayRecord(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("oreplay"))
    mission_id: str
    dry_run_receipts: list[OrganDryRunReceipt] = Field(default_factory=list)
    execution_receipts: list[OrganExecutionReceipt] = Field(default_factory=list)
    accepted: bool = False
    errors: list[str] = Field(default_factory=list)
    authority_expansion: bool = False

    @classmethod
    def replay(
        cls,
        mission_id: str,
        *,
        dry_run_receipts: list[OrganDryRunReceipt],
        execution_receipts: list[OrganExecutionReceipt] | None = None,
    ) -> OrganReplayRecord:
        executions = execution_receipts or []
        errors = []
        seen_ids = set()
        for receipt in [*dry_run_receipts, *executions]:
            if receipt.id in seen_ids:
                errors.append(f"duplicate_receipt_id:{receipt.id}")
            seen_ids.add(receipt.id)
            if receipt.mission_id != mission_id:
                errors.append(f"receipt_mission_mismatch:{receipt.id}")
            if receipt.authority_expansion:
                errors.append(f"receipt_authority_expansion:{receipt.id}")
            if isinstance(receipt, OrganDryRunReceipt) and receipt.preview_hash != receipt.expected_preview_hash():
                errors.append(f"dry_run_hash_mismatch:{receipt.id}")
            if isinstance(receipt, OrganExecutionReceipt) and receipt.receipt_hash != receipt.expected_receipt_hash():
                errors.append(f"execution_hash_mismatch:{receipt.id}")
        dry_ids = {receipt.id for receipt in dry_run_receipts}
        dry_by_id = {receipt.id: receipt for receipt in dry_run_receipts}
        for execution in executions:
            if execution.dry_run_receipt_id not in dry_ids:
                errors.append(f"execution_without_dry_run:{execution.id}")
                continue
            dry_run = dry_by_id[execution.dry_run_receipt_id]
            if execution.organ_id != dry_run.organ_id:
                errors.append(f"execution_organ_mismatch:{execution.id}")
            if execution.action != dry_run.action:
                errors.append(f"execution_action_mismatch:{execution.id}")
        return cls(
            mission_id=mission_id,
            dry_run_receipts=dry_run_receipts,
            execution_receipts=executions,
            accepted=not errors,
            errors=errors,
        )
