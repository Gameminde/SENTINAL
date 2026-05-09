from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.browser.power_governor import BrowserPowerDecision
from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class BrowserActionPlanReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bplan"))
    mission_id: str
    action: str
    selected_power: str
    lane: str
    dry_run_only: bool = True
    preview: dict[str, Any]
    evidence_refs: list[str]
    trace_refs: list[str]
    plan_hash: str = ""
    execution_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> BrowserActionPlanReceipt:
        if not self.evidence_refs:
            raise ValueError("BrowserActionPlanReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("BrowserActionPlanReceipt requires trace refs.")
        if self.execution_started:
            raise ValueError("BrowserActionPlanReceipt cannot start execution.")
        if self.authority_expansion:
            raise ValueError("BrowserActionPlanReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.plan_hash and self.plan_hash != expected:
            raise ValueError("BrowserActionPlanReceipt hash mismatch.")
        if not self.plan_hash:
            self.plan_hash = expected
        return self

    @classmethod
    def create(
        cls,
        *,
        mission_id: str,
        decision: BrowserPowerDecision,
        preview: dict[str, Any],
        trace_refs: list[str],
    ) -> BrowserActionPlanReceipt:
        return cls(
            mission_id=mission_id,
            action=decision.action,
            selected_power=decision.selected_power.value,
            lane=decision.lane.value,
            dry_run_only=decision.dry_run_only,
            preview=preview,
            evidence_refs=list(decision.evidence_refs),
            trace_refs=[*decision.trace_refs, *trace_refs],
        )

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "action": self.action,
                "selected_power": self.selected_power,
                "lane": self.lane,
                "dry_run_only": self.dry_run_only,
                "preview": self.preview,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
            }
        )
