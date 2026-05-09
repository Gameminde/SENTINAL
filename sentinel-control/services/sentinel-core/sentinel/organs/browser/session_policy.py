from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class BrowserSessionContinuityPolicy(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bsession"))
    persistent_profile_allowed: bool = False
    credential_storage_allowed: bool = False
    cookie_storage_allowed: bool = False
    allowed_domains: list[str] = Field(default_factory=list)
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> BrowserSessionContinuityPolicy:
        if not self.evidence_refs:
            raise ValueError("BrowserSessionContinuityPolicy requires evidence refs.")
        if self.credential_storage_allowed:
            raise ValueError("BrowserSessionContinuityPolicy cannot allow credential storage in P6C.")
        return self
