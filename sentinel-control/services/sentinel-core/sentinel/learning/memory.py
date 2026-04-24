from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel.learning.feedback import FeedbackRecord, summarize_feedback
from sentinel.shared.models import new_id


MemoryKind = Literal["evidence_preference", "asset_quality", "action_quality", "run_preference"]


class MemoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("mem"))
    kind: MemoryKind
    subject: str
    summary: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self.entries: list[MemoryEntry] = []

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        self.entries.append(entry)
        return entry

    def list(self) -> list[MemoryEntry]:
        return list(self.entries)


def derive_memory_entries(records: list[FeedbackRecord]) -> list[MemoryEntry]:
    summary = summarize_feedback(records)
    entries: list[MemoryEntry] = []

    if summary.useful_targets:
        entries.append(MemoryEntry(
            kind="asset_quality",
            subject="useful_outputs",
            summary="User marked these outputs as useful or approved; prioritize similar structure in future packs.",
            confidence=min(0.95, 0.45 + len(summary.useful_targets) * 0.1),
            evidence_refs=summary.useful_targets,
        ))

    if summary.weak_targets:
        entries.append(MemoryEntry(
            kind="asset_quality",
            subject="weak_outputs",
            summary="User marked these outputs as weak; create an improvement proposal before reusing this pattern.",
            confidence=min(0.95, 0.5 + len(summary.weak_targets) * 0.12),
            evidence_refs=summary.weak_targets,
        ))

    return entries
