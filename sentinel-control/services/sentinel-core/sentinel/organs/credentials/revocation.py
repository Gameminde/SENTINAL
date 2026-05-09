from __future__ import annotations

from sentinel.organs.credentials.scoped_grant import ScopedCredentialGrant


def revoke_credential_grant(grant: ScopedCredentialGrant, *, reason: str) -> ScopedCredentialGrant:
    return grant.model_copy(update={"revoked": True, "revocation_reason": reason})
