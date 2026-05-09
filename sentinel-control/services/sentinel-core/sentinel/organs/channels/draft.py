from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class ChannelMessageDraft(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chdraft"))
    channel: str
    subject: str | None = None
    body: str
    purpose: str
    recipients: list[str] = Field(default_factory=list)
    objective_tags: list[str] = Field(default_factory=list)
    external_context: bool = True
    send_attempted: bool = False
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ChannelMessageDraft:
        if not self.evidence_refs:
            raise ValueError("ChannelMessageDraft requires evidence refs.")
        if self.send_attempted:
            raise ValueError("ChannelMessageDraft cannot attempt send.")
        if self.authority_expansion:
            raise ValueError("ChannelMessageDraft cannot expand authority.")
        return self

    @property
    def lane(self) -> AutonomyRiskLane:
        return AutonomyRiskLane.BLUE if self.external_context or self.recipients else AutonomyRiskLane.GREEN
