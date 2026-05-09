from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class RecipientProvenance(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("chrecip"))
    recipient: str
    source: str
    consent_basis: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> RecipientProvenance:
        if not self.evidence_refs:
            raise ValueError("RecipientProvenance requires evidence refs.")
        return self
