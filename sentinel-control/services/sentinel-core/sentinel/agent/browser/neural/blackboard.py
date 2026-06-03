from __future__ import annotations

from pydantic import Field, model_validator

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

    @model_validator(mode="after")
    def _blackboard_is_data_only(self) -> "BrowserEvidenceBlackboard":
        if not self.data_not_instruction:
            raise ValueError("browser_evidence_blackboard_must_be_data_not_instruction")
        if self.authority_effect != "none" or self.execution_effect != "none":
            raise ValueError("browser_evidence_blackboard_cannot_have_authority_or_execution_effect")
        if self.signal_graph.mission_id != self.mission_id:
            raise ValueError("browser_evidence_blackboard_mission_mismatch")
        return self

    @classmethod
    def empty(cls, mission_id: str) -> "BrowserEvidenceBlackboard":
        return cls(mission_id=mission_id, signal_graph=BrowserSignalGraph(mission_id=mission_id))
