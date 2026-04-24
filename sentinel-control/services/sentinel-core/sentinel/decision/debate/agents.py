from __future__ import annotations

from sentinel.shared.enums import EvidenceType
from sentinel.shared.models import EvidenceItem


def evidence_refs(evidence: list[EvidenceItem], limit: int = 5) -> list[str]:
    return [item.id for item in evidence[:limit]]


def count_type(evidence: list[EvidenceItem], *types: EvidenceType) -> int:
    return sum(1 for item in evidence if item.evidence_type in types)


def strongest_summary(evidence: list[EvidenceItem], fallback: str) -> str:
    if not evidence:
        return fallback
    strongest = sorted(
        evidence,
        key=lambda item: item.relevance_score * 0.45 + item.confidence * 0.35 + item.freshness_score * 0.20,
        reverse=True,
    )[0]
    return strongest.summary

