from __future__ import annotations

from sentinel.cueidea_bridge.schemas import Competitor


def summarize_competitor_gaps(competitors: list[Competitor]) -> list[str]:
    gaps: list[str] = []
    for competitor in competitors:
        if competitor.gap:
            gaps.append(f"{competitor.name}: {competitor.gap}")
        else:
            gaps.append(f"{competitor.name}: gap not established yet")
    return gaps

