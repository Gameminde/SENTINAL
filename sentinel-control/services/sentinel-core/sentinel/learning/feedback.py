from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sentinel.shared.models import new_id


FeedbackTargetType = Literal["action", "asset", "evidence", "run"]
FeedbackRating = Literal["useful", "weak", "approved", "rejected"]


class FeedbackRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: new_id("fb"))
    run_id: str
    target_type: FeedbackTargetType
    target_id: str
    rating: FeedbackRating
    note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FeedbackSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    useful: int
    weak: int
    approved: int
    rejected: int
    weak_targets: list[str] = Field(default_factory=list)
    useful_targets: list[str] = Field(default_factory=list)


def summarize_feedback(records: list[FeedbackRecord]) -> FeedbackSummary:
    weak_targets = [record.target_id for record in records if record.rating == "weak"]
    useful_targets = [record.target_id for record in records if record.rating in {"useful", "approved"}]

    return FeedbackSummary(
        total=len(records),
        useful=sum(1 for record in records if record.rating == "useful"),
        weak=sum(1 for record in records if record.rating == "weak"),
        approved=sum(1 for record in records if record.rating == "approved"),
        rejected=sum(1 for record in records if record.rating == "rejected"),
        weak_targets=weak_targets,
        useful_targets=useful_targets,
    )
