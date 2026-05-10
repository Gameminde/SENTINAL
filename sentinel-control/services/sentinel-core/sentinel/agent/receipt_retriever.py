from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.agent.context_engine import ContextNeed
from sentinel.agent.token_ledger import estimate_tokens
from sentinel.shared.models import SentinelModel, new_id


class ReceiptRecord(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("receipt"))
    receipt_id: str
    source_type: str
    summary: str
    text: str
    evidence_refs: list[str] = Field(default_factory=list)
    relevance_tags: list[str] = Field(default_factory=list)
    critical: bool = False
    token_count: int = 0

    @model_validator(mode="after")
    def _fill_tokens(self) -> ReceiptRecord:
        if not self.token_count:
            self.token_count = estimate_tokens(self.text)
        return self


class ReceiptGraphRetriever:
    """Selects evidence-bearing receipt refs without returning raw receipts."""

    def retrieve_top_k(self, receipts: list[ReceiptRecord], *, need: ContextNeed, k: int) -> list[ReceiptRecord]:
        scored = [(self._score(receipt, need), receipt.receipt_id, receipt) for receipt in receipts]
        ranked = sorted(scored, key=lambda item: (-item[0], item[1]))
        return [receipt for score, _, receipt in ranked[: max(0, k)] if score > 0]

    @staticmethod
    def _score(receipt: ReceiptRecord, need: ContextNeed) -> float:
        score = 0.0
        if receipt.critical:
            score += 4.0
        if set(receipt.evidence_refs) & set(need.required_evidence_refs):
            score += 5.0
        tags = {tag.lower() for tag in receipt.relevance_tags}
        text = f"{receipt.summary} {receipt.source_type}".lower()
        for keyword in need.keywords:
            if keyword in tags:
                score += 1.5
            if keyword in text:
                score += 0.8
        if "old" in tags or "noise" in text:
            score -= 2.0
        return score
