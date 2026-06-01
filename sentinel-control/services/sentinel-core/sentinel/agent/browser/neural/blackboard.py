from __future__ import annotations

from pydantic import Field

from sentinel.agent.browser.neural.models import BrowserSignalGraph
from sentinel.shared.models import SentinelModel


class BrowserEvidenceBlackboard(SentinelModel):
    mission_id: str
    signal_graph: BrowserSignalGraph
    evidence_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    data_not_instruction: bool = True
    authority_effect: str = "none"
    execution_effect: str = "none"

    @classmethod
    def empty(cls, mission_id: str) -> "BrowserEvidenceBlackboard":
        return cls(mission_id=mission_id, signal_graph=BrowserSignalGraph(mission_id=mission_id))
