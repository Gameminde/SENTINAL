from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    CredentialAccessSource,
    CredentialPolicyReceipt,
    CredentialRef,
    CredentialTraceRedactor,
    CredentialVaultPolicy,
    ScopedCredentialGrant,
    revoke_credential_grant,
)
from sentinel.organs.lanes import AutonomyRiskLane


def credential_ref(**overrides) -> CredentialRef:
    data = {
        "provider": "example_api",
        "label": "readonly market data",
        "scope_tags": ["read_only", "market_data"],
        "evidence_refs": ["ev_credential_registered"],
    }
    data.update(overrides)
    return CredentialRef(**data)


def grant(**overrides) -> ScopedCredentialGrant:
    ref = overrides.pop("credential_ref", credential_ref())
    data = {
        "mission_id": "mission_p6f",
        "credential_ref": ref,
        "allowed_organ": "external_api_organ",
        "allowed_action_class": "read_only_api",
        "scope": ["read:market_data"],
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "evidence_refs": ["ev_grant"],
    }
    data.update(overrides)
    return ScopedCredentialGrant(**data)


def test_credential_ref_never_stores_raw_secret():
    ref = credential_ref()

    assert ref.raw_secret is None
    assert ref.secret_value is None
    assert ref.redacted_label().startswith("credref:")

    with pytest.raises(ValueError, match="raw secret"):
        credential_ref(raw_secret="sk-live-secret")


def test_scoped_credential_grant_defines_scope_expiry_organ_and_action_class():
    scoped = grant()

    assert scoped.allowed_organ == "external_api_organ"
    assert scoped.allowed_action_class == "read_only_api"
    assert scoped.is_active(datetime.now(UTC)) is True
    assert scoped.revoked is False


def test_redaction_removes_secret_like_values_from_trace_payload():
    payload = {
        "Authorization": "Bearer sk-live-123456",
        "nested": {"api_key": "secret_value"},
        "safe": "credential_ref:credref_123",
    }

    redacted = CredentialTraceRedactor().redact(payload)

    assert "sk-live" not in str(redacted)
    assert "secret_value" not in str(redacted)
    assert redacted["safe"] == "credential_ref:credref_123"


def test_revocation_disables_scoped_grant():
    scoped = grant()

    revoked = revoke_credential_grant(scoped, reason="user revoked")

    assert revoked.revoked is True
    assert revoked.revocation_reason == "user revoked"
    assert revoked.is_active(datetime.now(UTC)) is False


@pytest.mark.parametrize(
    "source",
    [
        CredentialAccessSource.PROMPT,
        CredentialAccessSource.MEMORY,
        CredentialAccessSource.WORKSPACE,
        CredentialAccessSource.VENDOR_HARVEST,
        CredentialAccessSource.EXPECTED_PROFIT,
    ],
)
def test_policy_blocks_credential_access_from_untrusted_or_advisory_sources(source):
    scoped = grant()

    decision = CredentialVaultPolicy().evaluate(
        scoped,
        requesting_organ="external_api_organ",
        action_class="read_only_api",
        source=source,
        trace_refs=["trace_policy"],
    )

    assert decision.reference_allowed is False
    assert decision.secret_access_allowed is False
    assert f"credential_source_blocked:{source.value}" in decision.reasons


def test_policy_allows_reference_only_for_matching_scoped_grant():
    scoped = grant()

    decision = CredentialVaultPolicy().evaluate(
        scoped,
        requesting_organ="external_api_organ",
        action_class="read_only_api",
        source=CredentialAccessSource.ORGAN_RUNTIME,
        trace_refs=["trace_policy"],
    )

    assert decision.lane == AutonomyRiskLane.RED
    assert decision.reference_allowed is True
    assert decision.secret_access_allowed is False
    assert decision.secret_value is None


def test_policy_blocks_wrong_organ_action_expired_and_revoked_grants():
    expired = grant(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    revoked = revoke_credential_grant(grant(), reason="rotated")

    wrong = CredentialVaultPolicy().evaluate(
        grant(),
        requesting_organ="channel_organ",
        action_class="send",
        source=CredentialAccessSource.ORGAN_RUNTIME,
        trace_refs=["trace_policy"],
    )
    expired_decision = CredentialVaultPolicy().evaluate(
        expired,
        requesting_organ="external_api_organ",
        action_class="read_only_api",
        source=CredentialAccessSource.ORGAN_RUNTIME,
        trace_refs=["trace_policy"],
    )
    revoked_decision = CredentialVaultPolicy().evaluate(
        revoked,
        requesting_organ="external_api_organ",
        action_class="read_only_api",
        source=CredentialAccessSource.ORGAN_RUNTIME,
        trace_refs=["trace_policy"],
    )

    assert "organ_mismatch" in wrong.reasons
    assert "action_class_mismatch" in wrong.reasons
    assert "grant_expired" in expired_decision.reasons
    assert "grant_revoked" in revoked_decision.reasons


def test_policy_receipt_is_deterministic_and_redacted():
    scoped = grant()
    decision = CredentialVaultPolicy().evaluate(
        scoped,
        requesting_organ="external_api_organ",
        action_class="read_only_api",
        source=CredentialAccessSource.ORGAN_RUNTIME,
        trace_refs=["trace_policy"],
    )

    receipt = CredentialPolicyReceipt.create(scoped, decision, trace_refs=["trace_receipt"])

    assert receipt.secret_accessed is False
    assert receipt.secret_value is None
    assert receipt.receipt_hash == receipt.expected_hash()
    assert receipt.authority_expansion is False


def test_receipt_requires_trace_and_evidence_refs():
    scoped = grant()
    traced_decision = CredentialVaultPolicy().evaluate(
        scoped,
        requesting_organ="external_api_organ",
        action_class="read_only_api",
        source=CredentialAccessSource.ORGAN_RUNTIME,
        trace_refs=["trace_policy"],
    )
    untraced_decision = traced_decision.model_copy(update={"trace_refs": []})

    with pytest.raises(ValueError, match="requires trace refs"):
        CredentialPolicyReceipt.create(scoped, untraced_decision, trace_refs=[])

    with pytest.raises(ValueError, match="requires evidence refs"):
        credential_ref(evidence_refs=[])
