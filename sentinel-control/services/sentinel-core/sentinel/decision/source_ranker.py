from __future__ import annotations

from sentinel.shared.models import EvidenceItem


def rank_sources(evidence: list[EvidenceItem]) -> list[EvidenceItem]:
    return sorted(
        evidence,
        key=lambda item: (
            item.relevance_score * 0.45
            + item.confidence * 0.35
            + item.freshness_score * 0.20
        ),
        reverse=True,
    )

