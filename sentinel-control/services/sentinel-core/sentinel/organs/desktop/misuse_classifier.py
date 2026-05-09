from __future__ import annotations

from pydantic import Field

from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel


BLACK_LANE_TERMS = {
    "hidden keystroke",
    "credential theft",
    "secret capture",
    "authority bypass",
    "vendor runtime bridge",
    "fake identity",
    "kyc bypass",
}


class DesktopMisuseDecision(SentinelModel):
    objective: str
    lane: AutonomyRiskLane
    blocked: bool
    reasons: list[str] = Field(default_factory=list)


class DesktopMisuseClassifier:
    def classify(self, objective: str) -> DesktopMisuseDecision:
        normalized = objective.lower()
        hits = [term for term in sorted(BLACK_LANE_TERMS) if term in normalized]
        if hits:
            return DesktopMisuseDecision(objective=objective, lane=AutonomyRiskLane.BLACK, blocked=True, reasons=hits)
        return DesktopMisuseDecision(objective=objective, lane=AutonomyRiskLane.RED, blocked=False, reasons=["high_power_surface"])
