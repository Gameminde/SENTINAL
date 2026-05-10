from __future__ import annotations

import re
from typing import Any

from pydantic import Field

from sentinel.agent.context_engine import ContextNeed
from sentinel.agent.receipt_retriever import ReceiptRecord
from sentinel.agent.token_ledger import estimate_tokens
from sentinel.shared.models import SentinelModel, new_id


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*=\s*\S+"),
]


def sanitize_context_text(text: str) -> str:
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


def sanitize_context_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        return sanitize_context_text(payload)
    if isinstance(payload, list):
        return [sanitize_context_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(sanitize_context_payload(item) for item in payload)
    if isinstance(payload, dict):
        return {sanitize_context_payload(key): sanitize_context_payload(value) for key, value in payload.items()}
    return payload


class EvidenceCard(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("evcard"))
    receipt_id: str
    source_type: str
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0)
    token_count: int = Field(ge=0)
    critical: bool = False


class EvidenceRanker:
    """Turns selected receipts into compact evidence cards."""

    def rank(self, receipts: list[ReceiptRecord], need: ContextNeed) -> list[EvidenceCard]:
        cards = [self._card(receipt, need) for receipt in receipts]
        return sorted(cards, key=lambda card: (-card.relevance_score, card.receipt_id))

    @staticmethod
    def _card(receipt: ReceiptRecord, need: ContextNeed) -> EvidenceCard:
        required_bonus = 2.0 if set(receipt.evidence_refs) & set(need.required_evidence_refs) else 0.0
        critical_bonus = 1.0 if receipt.critical else 0.0
        tag_bonus = len(set(receipt.relevance_tags) & set(need.keywords)) * 0.5
        summary = sanitize_context_text(receipt.summary)
        return EvidenceCard(
            receipt_id=receipt.receipt_id,
            source_type=receipt.source_type,
            summary=summary,
            evidence_refs=receipt.evidence_refs,
            relevance_score=round(1.0 + required_bonus + critical_bonus + tag_bonus, 6),
            token_count=estimate_tokens(summary),
            critical=receipt.critical,
        )
