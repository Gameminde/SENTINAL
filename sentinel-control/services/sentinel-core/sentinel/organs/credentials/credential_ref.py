from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class CredentialRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("credref"))
    provider: str
    label: str
    credential_type: str = "generic"
    mission_id: str | None = None
    organ_kind: str | None = None
    domain_scope: list[str] = Field(default_factory=list)
    action_scope: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    scope_tags: list[str] = Field(default_factory=list)
    raw_secret: str | None = None
    secret_value: str | None = None
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_approve_future_execution: bool = False
    can_create_delegated_lane: bool = False
    can_execute: bool = False
    can_override_provider_model: bool = False
    data_not_instruction: bool = True

    @model_validator(mode="after")
    def _validate(self) -> CredentialRef:
        if not self.evidence_refs:
            raise ValueError("CredentialRef requires evidence refs.")
        if self.raw_secret is not None or self.secret_value is not None:
            raise ValueError("CredentialRef cannot store raw secret material.")
        if self.authority_effect != "none":
            raise ValueError("CredentialRef cannot grant authority.")
        if self.execution_effect != "none":
            raise ValueError("CredentialRef cannot execute.")
        for field, message in {
            "can_grant_authority": "grant authority",
            "can_approve_execution": "approve execution",
            "can_approve_future_execution": "approve future execution",
            "can_create_delegated_lane": "create delegated lanes",
            "can_execute": "execute",
            "can_override_provider_model": "override provider/model",
        }.items():
            if bool(getattr(self, field, False)):
                raise ValueError(f"CredentialRef cannot {message}.")
        if self.data_not_instruction is not True:
            raise ValueError("CredentialRef is data, not instruction.")
        return self

    def redacted_label(self) -> str:
        return f"credref:{self.id}:{self.provider}:{self.label}"
