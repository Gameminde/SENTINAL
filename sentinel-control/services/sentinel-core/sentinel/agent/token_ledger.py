from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, ceil(len(text) / 4))


class TokenLedgerEntry(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tok"))
    mission_id: str
    category: str
    source_id: str
    token_count: int = Field(ge=0)
    text_preview: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate(self) -> TokenLedgerEntry:
        if not self.category:
            raise ValueError("TokenLedgerEntry category is required.")
        if not self.source_id:
            raise ValueError("TokenLedgerEntry source_id is required.")
        return self


class TokenLedger(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tledger"))
    mission_id: str
    entries: list[TokenLedgerEntry] = Field(default_factory=list)

    def add_text(
        self,
        category: str,
        source_id: str,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> TokenLedgerEntry:
        entry = TokenLedgerEntry(
            mission_id=self.mission_id,
            category=category,
            source_id=source_id,
            token_count=estimate_tokens(text),
            text_preview=text[:240],
            metadata=metadata or {},
        )
        self.entries.append(entry)
        return entry

    def total_tokens(self) -> int:
        return sum(entry.token_count for entry in self.entries)

    def tokens_by_category(self) -> dict[str, int]:
        totals: dict[str, int] = defaultdict(int)
        for entry in self.entries:
            totals[entry.category] += entry.token_count
        return dict(sorted(totals.items()))

    def count_by_category(self, category: str) -> int:
        return sum(1 for entry in self.entries if entry.category == category)
