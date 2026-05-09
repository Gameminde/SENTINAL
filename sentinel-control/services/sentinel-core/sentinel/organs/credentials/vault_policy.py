from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field

from sentinel.organs.credentials.scoped_grant import ScopedCredentialGrant
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class CredentialAccessSource(StrEnum):
    PROMPT = "prompt"
    MEMORY = "memory"
    WORKSPACE = "workspace"
    VENDOR_HARVEST = "vendor_harvest"
    EXPECTED_PROFIT = "expected_profit"
    ORGAN_RUNTIME = "organ_runtime"


class CredentialPolicyDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("credpol"))
    credential_ref_id: str
    lane: AutonomyRiskLane = AutonomyRiskLane.RED
    reference_allowed: bool = False
    secret_access_allowed: bool = False
    secret_value: str | None = None
    reasons: list[str]
    trace_refs: list[str]
    authority_expansion: bool = False


class CredentialVaultPolicy:
    BLOCKED_SOURCES = {
        CredentialAccessSource.PROMPT,
        CredentialAccessSource.MEMORY,
        CredentialAccessSource.WORKSPACE,
        CredentialAccessSource.VENDOR_HARVEST,
        CredentialAccessSource.EXPECTED_PROFIT,
    }

    def evaluate(
        self,
        grant: ScopedCredentialGrant,
        *,
        requesting_organ: str,
        action_class: str,
        source: CredentialAccessSource,
        trace_refs: list[str],
        at_time: datetime | None = None,
    ) -> CredentialPolicyDecision:
        now = at_time or datetime.now(UTC)
        reasons: list[str] = []
        if source in self.BLOCKED_SOURCES:
            reasons.append(f"credential_source_blocked:{source.value}")
        if requesting_organ != grant.allowed_organ:
            reasons.append("organ_mismatch")
        if action_class != grant.allowed_action_class:
            reasons.append("action_class_mismatch")
        if grant.revoked:
            reasons.append("grant_revoked")
        if now > grant.expires_at:
            reasons.append("grant_expired")
        reference_allowed = not reasons and source == CredentialAccessSource.ORGAN_RUNTIME
        return CredentialPolicyDecision(
            credential_ref_id=grant.credential_ref.id,
            reference_allowed=reference_allowed,
            secret_access_allowed=False,
            secret_value=None,
            reasons=reasons or ["credential_reference_allowed_only"],
            trace_refs=[*grant.trace_refs, *trace_refs],
        )
