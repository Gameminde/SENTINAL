from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class InboundChannelMessage(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chin"))
    channel: str
    sender: str
    content_summary: str
    trust_level: str = "untrusted"
    authority_granted: bool = False
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> InboundChannelMessage:
        if not self.evidence_refs:
            raise ValueError("InboundChannelMessage requires evidence refs.")
        if self.trust_level != "untrusted":
            raise ValueError("Inbound channel messages must remain untrusted context in P6E.")
        if self.authority_granted:
            raise ValueError("Inbound channel messages cannot grant authority.")
        return self
