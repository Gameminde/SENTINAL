from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from sentinel.organs.credentials.credential_ref import CredentialRef
from sentinel.shared.models import SentinelModel, new_id


class ScopedCredentialGrant(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("credgrant"))
    mission_id: str
    credential_ref: CredentialRef
    allowed_organ: str
    allowed_action_class: str
    scope: list[str]
    expires_at: datetime
    revoked: bool = False
    revocation_reason: str | None = None
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> ScopedCredentialGrant:
        if not self.scope:
            raise ValueError("ScopedCredentialGrant requires scope.")
        if not self.evidence_refs:
            raise ValueError("ScopedCredentialGrant requires evidence refs.")
        if self.authority_expansion:
            raise ValueError("ScopedCredentialGrant cannot expand authority.")
        return self

    def is_active(self, at_time: datetime) -> bool:
        return not self.revoked and at_time < self.expires_at
