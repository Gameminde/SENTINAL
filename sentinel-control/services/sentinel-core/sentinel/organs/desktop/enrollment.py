from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel


class SidecarEnrollmentGrant(SentinelModel):
    sidecar_id: str
    sidecar_identity: str
    signed_enrollment: str
    policy_hash: str
    issued_at: datetime
    expires_at: datetime
    revoked: bool = False
    revoked_reason: str | None = None
    evidence_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SidecarEnrollmentGrant:
        if not self.sidecar_id:
            raise ValueError("SidecarEnrollmentGrant requires sidecar id.")
        if not self.sidecar_identity:
            raise ValueError("SidecarEnrollmentGrant requires sidecar identity.")
        if not self.signed_enrollment:
            raise ValueError("SidecarEnrollmentGrant requires signed enrollment.")
        if not self.policy_hash:
            raise ValueError("SidecarEnrollmentGrant requires policy hash.")
        if self.expires_at <= self.issued_at:
            raise ValueError("SidecarEnrollmentGrant expiry must be after issue time.")
        if not self.evidence_refs:
            raise ValueError("SidecarEnrollmentGrant requires evidence refs.")
        if self.authority_expansion:
            raise ValueError("SidecarEnrollmentGrant cannot expand authority.")
        return self

    def is_active(self, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return not self.revoked and self.expires_at > current

    def revoke(self, *, reason: str) -> SidecarEnrollmentGrant:
        return self.model_copy(update={"revoked": True, "revoked_reason": reason})
