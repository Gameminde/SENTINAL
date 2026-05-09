from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class CredentialRef(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("credref"))
    provider: str
    label: str
    scope_tags: list[str] = Field(default_factory=list)
    raw_secret: str | None = None
    secret_value: str | None = None
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> CredentialRef:
        if not self.evidence_refs:
            raise ValueError("CredentialRef requires evidence refs.")
        if self.raw_secret is not None or self.secret_value is not None:
            raise ValueError("CredentialRef cannot store raw secret material.")
        return self

    def redacted_label(self) -> str:
        return f"credref:{self.id}:{self.provider}:{self.label}"
