from __future__ import annotations

from enum import StrEnum


class AutonomyRiskLane(StrEnum):
    GREEN = "green"
    BLUE = "blue"
    ORANGE = "orange"
    RED = "red"
    BLACK = "black"


def lane_allows_auto_execute(lane: AutonomyRiskLane) -> bool:
    return lane in {AutonomyRiskLane.GREEN, AutonomyRiskLane.BLUE}
