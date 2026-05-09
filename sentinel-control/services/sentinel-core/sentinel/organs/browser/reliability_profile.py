from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class BrowserReliabilityProfile(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("breliability"))
    stable_launch: bool = True
    session_continuity: bool = True
    viewport_consistency: bool = True
    locale_timezone_consistency: bool = True
    profile_management: bool = True
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> BrowserReliabilityProfile:
        if not self.evidence_refs:
            raise ValueError("BrowserReliabilityProfile requires evidence refs.")
        return self
