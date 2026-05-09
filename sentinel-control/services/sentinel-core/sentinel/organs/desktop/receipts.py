from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class DesktopActionReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("drcpt"))
    mission_id: str
    sidecar_id: str
    action_family: str
    method: str
    target: dict[str, Any] = Field(default_factory=dict)
    lane: AutonomyRiskLane
    authority_refs: list[str]
    evidence_refs: list[str]
    trace_refs: list[str]
    sanitized_summary: str
    dry_run_only: bool = True
    execution_started: bool = False
    live_host_control_enabled: bool = False
    receipt_hash: str = ""
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> DesktopActionReceipt:
        if not self.authority_refs:
            raise ValueError("DesktopActionReceipt requires authority refs.")
        if not self.evidence_refs:
            raise ValueError("DesktopActionReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("DesktopActionReceipt requires trace refs.")
        if not self.dry_run_only:
            raise ValueError("DesktopActionReceipt must remain dry-run-only in P6L.")
        if self.execution_started:
            raise ValueError("DesktopActionReceipt cannot start host execution in P6L.")
        if self.live_host_control_enabled:
            raise ValueError("DesktopActionReceipt cannot enable live host control in P6L.")
        if self.authority_expansion:
            raise ValueError("DesktopActionReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("DesktopActionReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    def expected_hash(self) -> str:
        return _hash_payload(
            {
                "mission_id": self.mission_id,
                "sidecar_id": self.sidecar_id,
                "action_family": self.action_family,
                "method": self.method,
                "target": self.target,
                "lane": self.lane.value,
                "authority_refs": self.authority_refs,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
                "sanitized_summary": self.sanitized_summary,
                "dry_run_only": self.dry_run_only,
            }
        )
