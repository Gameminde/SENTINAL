from __future__ import annotations

from pydantic import Field

from sentinel.organs.channels.draft import ChannelMessageDraft
from sentinel.shared.models import SentinelModel, new_id


class ChannelRateLimitDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chrate"))
    accepted: bool
    recipient_count: int = Field(ge=0)
    max_recipients_per_window: int = Field(ge=0)
    reasons: list[str] = Field(default_factory=list)


class ChannelRateLimitPolicy(SentinelModel):
    max_recipients_per_window: int = Field(ge=0)

    def evaluate(self, draft: ChannelMessageDraft) -> ChannelRateLimitDecision:
        count = len(draft.recipients)
        accepted = count <= self.max_recipients_per_window
        return ChannelRateLimitDecision(
            accepted=accepted,
            recipient_count=count,
            max_recipients_per_window=self.max_recipients_per_window,
            reasons=["rate_limit_ok"] if accepted else ["rate_limit_exceeded"],
        )
