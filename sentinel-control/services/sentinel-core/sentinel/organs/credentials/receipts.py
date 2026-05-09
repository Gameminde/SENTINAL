from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.credentials.scoped_grant import ScopedCredentialGrant
from sentinel.organs.credentials.vault_policy import CredentialPolicyDecision
from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CredentialPolicyReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("credrcpt"))
    mission_id: str
    credential_ref_id: str
    grant_id: str
    decision_id: str
    reference_allowed: bool
    secret_accessed: bool = False
    secret_value: str | None = None
    reasons: list[str]
    evidence_refs: list[str]
    trace_refs: list[str]
    receipt_hash: str = ""
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> CredentialPolicyReceipt:
        if not self.evidence_refs:
            raise ValueError("CredentialPolicyReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("CredentialPolicyReceipt requires trace refs.")
        if self.secret_accessed or self.secret_value is not None:
            raise ValueError("CredentialPolicyReceipt cannot contain or access secret value.")
        if self.authority_expansion:
            raise ValueError("CredentialPolicyReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("CredentialPolicyReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    @classmethod
    def create(
        cls,
        grant: ScopedCredentialGrant,
        decision: CredentialPolicyDecision,
        *,
        trace_refs: list[str],
    ) -> CredentialPolicyReceipt:
        return cls(
            mission_id=grant.mission_id,
            credential_ref_id=grant.credential_ref.id,
            grant_id=grant.id,
            decision_id=decision.id,
            reference_allowed=decision.reference_allowed,
            reasons=list(decision.reasons),
            evidence_refs=[*grant.evidence_refs, *grant.credential_ref.evidence_refs],
            trace_refs=[*decision.trace_refs, *trace_refs],
        )

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "credential_ref_id": self.credential_ref_id,
                "grant_id": self.grant_id,
                "decision_id": self.decision_id,
                "reference_allowed": self.reference_allowed,
                "secret_accessed": self.secret_accessed,
                "reasons": self.reasons,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
            }
        )
