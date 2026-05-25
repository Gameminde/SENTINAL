from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.organs.delegated_action_gate import DelegatedActionGate, DelegatedActionGateDecision
from sentinel.agent.organs.proposal_bridge import (
    BaseOrganCandidate,
    OrganCandidateAuthorityClass,
    OrganCandidateRiskClass,
    OrganProposalKind,
)
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionConfig
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.organs.credentials import (
    AuthorityCredentialSafetyValidationResult,
    AuthorityPresetFactory,
    CredentialAccessProof,
    CredentialAccessRequest,
    CredentialAccessSource,
    CredentialAuditReceipt,
    CredentialGrant,
    CredentialGrantStatus,
    CredentialRef,
    CredentialRevocation,
    MissionAuthorityGrant,
    MissionAuthorityGrantStatus,
    evaluate_credential_access,
    validate_authority_credential_payload,
    validate_credential_proof_for_finalgate,
)


MISSION_ID = "mission-credential-foundation"
Credential_REF_ID = "credref-browser-public"
NOW = datetime(2026, 5, 25, 12, 0, tzinfo=UTC)


def _credential_ref() -> CredentialRef:
    return CredentialRef(
        id=Credential_REF_ID,
        provider="vault_ref",
        label="public-browser-token-ref",
        credential_type="api_key",
        mission_id=MISSION_ID,
        organ_kind="browser",
        domain_scope=["example.com"],
        action_scope=["navigate"],
        evidence_refs=["ev-credential-user-approved"],
    )


def _credential_grant(**updates: object) -> CredentialGrant:
    payload = {
        "mission_id": MISSION_ID,
        "credential_ref_id": Credential_REF_ID,
        "allowed_organs": ["browser"],
        "allowed_action_levels": [DelegatedActionLevel.L5],
        "domain_scope": ["example.com"],
        "action_scope": ["navigate"],
        "expires_at": NOW + timedelta(minutes=10),
        "max_use_count": 1,
        "evidence_refs": ["ev-credential-user-approved"],
        "receipt_refs": ["receipt-authority-grant"],
    }
    payload.update(updates)
    return CredentialGrant(**payload)


def _access_request(**updates: object) -> CredentialAccessRequest:
    payload = {
        "mission_id": MISSION_ID,
        "credential_ref_id": Credential_REF_ID,
        "organ_kind": "browser",
        "action_level": DelegatedActionLevel.L5,
        "domain": "example.com",
        "action": "navigate",
        "source": CredentialAccessSource.ORGAN_RUNTIME,
        "evidence_refs": ["ev-credential-user-approved"],
        "receipt_refs": ["receipt-authority-grant"],
    }
    payload.update(updates)
    return CredentialAccessRequest(**payload)


def _candidate(level: DelegatedActionLevel = DelegatedActionLevel.L4) -> BaseOrganCandidate:
    return BaseOrganCandidate(
        candidate_id="candidate-browser-credential-proof",
        mission_id=MISSION_ID,
        source_proposal_id="proposal-browser",
        organ_kind=OrganProposalKind.BROWSER,
        action_level_candidate=level,
        authority_class=OrganCandidateAuthorityClass.NEEDS_GATE,
        risk_class=OrganCandidateRiskClass.LOW,
        evidence_refs=["ev-browser"],
        receipt_refs=["receipt-browser"],
        expected_outcome="Browser metadata candidate remains gated.",
        rollback_posture="No external mutation in foundation pack.",
        user_review_required=False,
        safe_summary="Browser candidate with credential proof metadata only.",
        params_hash="params-hash",
    )


def _organ_contract(requires_proof: bool = False) -> dict[str, object]:
    return {
        "available": True,
        "allowed_action_levels": [DelegatedActionLevel.L4.value, DelegatedActionLevel.L5.value],
        "required_receipt_fields": ["evidence_refs", "receipt_refs"],
        "credential_proof_required": requires_proof,
    }


def test_default_presets_do_not_enable_credentials() -> None:
    for preset in (
        AuthorityPresetFactory.development_local(),
        AuthorityPresetFactory.browser_perception(),
        AuthorityPresetFactory.operator_browser_l5_template(),
        AuthorityPresetFactory.full_power_template(),
    ):
        assert preset.credential_use_enabled is False
        assert preset.can_grant_authority is False
        assert preset.can_approve_execution is False
        assert preset.data_not_instruction is True


def test_development_local_allows_l2_l3_only_no_credentials() -> None:
    preset = AuthorityPresetFactory.development_local()
    assert preset.allowed_action_levels == [DelegatedActionLevel.L2, DelegatedActionLevel.L3]
    assert preset.allowed_organs == ["local_artifact", "reversible_workspace"]
    assert preset.credential_grants == []


def test_browser_perception_allows_l4_readonly_only_no_credentials() -> None:
    preset = AuthorityPresetFactory.browser_perception()
    assert preset.allowed_action_levels == [DelegatedActionLevel.L4]
    assert preset.allowed_organs == ["browser_readonly", "browser_preparation", "browser_semantic_extraction"]
    assert preset.credential_use_enabled is False


def test_operator_browser_l5_template_is_non_executing_without_explicit_grant() -> None:
    preset = AuthorityPresetFactory.operator_browser_l5_template()
    assert DelegatedActionLevel.L5 in preset.allowed_action_levels
    assert preset.execution_enabled is False
    assert preset.credential_use_enabled is False
    assert preset.forbidden_actions == ["submit", "login", "payment", "credential_use"]


def test_credential_ref_contains_no_raw_secret() -> None:
    ref = _credential_ref()
    dumped = str(ref.model_dump(mode="json")).lower()
    assert "secret-value" not in dumped
    with pytest.raises(ValueError, match="raw secret"):
        CredentialRef(**{"provider": "vault_ref", "label": "bad", "raw_" + "secret": "blocked-material", "evidence_refs": ["ev"]})


def test_credential_grant_requires_mission_scope() -> None:
    with pytest.raises(ValueError, match="mission"):
        _credential_grant(mission_id="")


def test_credential_grant_requires_organ_scope() -> None:
    with pytest.raises(ValueError, match="organ"):
        _credential_grant(allowed_organs=[])


def test_credential_grant_requires_action_scope() -> None:
    with pytest.raises(ValueError, match="action"):
        _credential_grant(action_scope=[])


def test_expired_grant_blocks_access() -> None:
    grant = _credential_grant(expires_at=NOW - timedelta(seconds=1))
    receipt = evaluate_credential_access(_access_request(), [grant], current_time=NOW)
    assert receipt.decision.value == "blocked_expired"
    assert receipt.secret_accessed is False


def test_revoked_grant_blocks_access() -> None:
    grant = _credential_grant(status=CredentialGrantStatus.REVOKED, revoked_at=NOW)
    receipt = evaluate_credential_access(_access_request(), [grant], current_time=NOW)
    assert receipt.decision.value == "blocked_revoked"
    assert receipt.secret_accessed is False


def test_scope_mismatch_blocks_access() -> None:
    grant = _credential_grant(domain_scope=["allowed.example"])
    receipt = evaluate_credential_access(_access_request(domain="example.com"), [grant], current_time=NOW)
    assert receipt.decision.value == "blocked_scope_mismatch"
    assert receipt.secret_accessed is False


def test_credential_access_proof_cannot_grant_authority() -> None:
    with pytest.raises(ValueError, match="grant authority"):
        CredentialAccessProof(
            credential_ref_id=_credential_ref().id,
            mission_id=MISSION_ID,
            organ_kind="browser",
            action_level=DelegatedActionLevel.L5,
            action_scope=["navigate"],
            proof_hash="abc",
            can_grant_authority=True,
        )


def test_credential_access_proof_cannot_approve_future_execution() -> None:
    with pytest.raises(ValueError, match="approve"):
        CredentialAccessProof(
            credential_ref_id=_credential_ref().id,
            mission_id=MISSION_ID,
            organ_kind="browser",
            action_level=DelegatedActionLevel.L5,
            action_scope=["navigate"],
            proof_hash="abc",
            can_approve_future_execution=True,
        )


def test_memory_or_receipt_cannot_create_credential_grant() -> None:
    result = validate_authority_credential_payload(
        {"credential_grants": [_credential_grant().model_dump(mode="json")]},
        source="memory",
    )
    assert isinstance(result, AuthorityCredentialSafetyValidationResult)
    assert result.valid is False
    assert "source_cannot_create_credential_grant" in result.reasons


def test_provider_backend_model_override_rejected() -> None:
    result = validate_authority_credential_payload(
        {"provider_override": "new-provider", "model_override": "new-model"},
        source="operator",
    )
    assert result.valid is False
    assert result.can_override_provider_model is False
    assert any("provider" in path or "model" in path for path in result.rejected_paths)


def test_no_global_enable_credentials_switch() -> None:
    config = OrganRuntimeExecutionConfig()
    assert config.deny_credentials is True
    assert not hasattr(config, "enable_credentials")


def test_delegated_gate_rejects_missing_credential_proof_when_required() -> None:
    result = DelegatedActionGate().decide(
        {
            "mission_id": MISSION_ID,
            "candidate": _candidate(),
            "authority": {
                "root_authority_present": True,
                "allowed_action_levels": [DelegatedActionLevel.L4.value],
                "allowed_organs": [OrganProposalKind.BROWSER.value],
                "max_risk": "low",
                "special_authority": True,
                "user_review_granted": True,
            },
            "budget": {"remaining_action_count": 1, "remaining_tokens": 100},
            "available_evidence_refs": ["ev-browser"],
            "organ_contracts": {OrganProposalKind.BROWSER.value: _organ_contract(requires_proof=True)},
        }
    )
    assert result.decision is DelegatedActionGateDecision.AUTHORITY_EXTENSION_REQUIRED
    assert "credential_proof_missing" in [reason.value for reason in result.reasons]
    assert result.lane is None


def test_delegated_gate_accepts_valid_credential_proof_as_metadata_only() -> None:
    proof = evaluate_credential_access(_access_request(action_level=DelegatedActionLevel.L4), [_credential_grant(allowed_action_levels=[DelegatedActionLevel.L4])], current_time=NOW).proof
    result = DelegatedActionGate().decide(
        {
            "mission_id": MISSION_ID,
            "candidate": _candidate(),
            "authority": {
                "root_authority_present": True,
                "allowed_action_levels": [DelegatedActionLevel.L4.value],
                "allowed_organs": [OrganProposalKind.BROWSER.value],
                "max_risk": "low",
                "special_authority": True,
                "user_review_granted": True,
            },
            "budget": {"remaining_action_count": 1, "remaining_tokens": 100},
            "available_evidence_refs": ["ev-browser"],
            "credential_access_proofs": [proof.model_dump(mode="json")],
            "organ_contracts": {OrganProposalKind.BROWSER.value: _organ_contract(requires_proof=True)},
        }
    )
    assert result.decision is DelegatedActionGateDecision.ALLOWED
    assert result.lane is not None
    assert result.lane.execution_enabled is False
    assert result.can_execute is False


def test_finalgate_can_validate_credential_proof_metadata_only() -> None:
    receipt = evaluate_credential_access(_access_request(), [_credential_grant()], current_time=NOW)
    result = validate_credential_proof_for_finalgate(
        proof=receipt.proof,
        mission_id=MISSION_ID,
        expected_credential_ref_id=_credential_ref().id,
    )
    assert result.valid is True
    assert result.data_not_instruction is True
    assert result.can_grant_authority is False


def test_no_browser_login_api_mutation_channel_send_shell_desktop_payment_enabled() -> None:
    preset = AuthorityPresetFactory.full_power_template()
    assert preset.execution_enabled is False
    forbidden = set(preset.forbidden_actions)
    assert {
        "browser_login",
        "browser_submit",
        "api_mutation",
        "channel_send",
        "shell",
        "desktop",
        "payment",
    }.issubset(forbidden)


def test_mission_authority_envelope_accepts_credential_grants_as_metadata_only() -> None:
    grant = _credential_grant()
    envelope = MissionAuthorityEnvelope(
        user_id="user",
        mission_title="Credential foundation",
        mission_objective="Test credential grant metadata only.",
        credential_grants=[grant],
    )
    assert envelope.credential_grants[0].credential_ref_id == grant.credential_ref_id
    assert envelope.credential_grants[0].authority_effect == "none"


def test_credential_revocation_and_audit_receipt_are_metadata_only() -> None:
    grant = _credential_grant()
    revocation = CredentialRevocation.revoke(grant, reason="operator_revoked", revoked_at=NOW)
    receipt = CredentialAuditReceipt.from_revocation(revocation, trace_refs=["trace-revocation"])
    assert revocation.status is MissionAuthorityGrantStatus.REVOKED
    assert receipt.secret_accessed is False
    assert receipt.authority_effect == "none"
    assert receipt.data_not_instruction is True


def test_mission_authority_grant_is_metadata_only() -> None:
    grant = MissionAuthorityGrant(
        mission_id=MISSION_ID,
        allowed_organs=["browser"],
        allowed_action_levels=[DelegatedActionLevel.L4],
        domain_scope=["example.com"],
        action_scope=["observe"],
        expires_at=NOW + timedelta(minutes=5),
        evidence_refs=["ev-authority"],
    )
    assert grant.status is MissionAuthorityGrantStatus.ACTIVE
    assert grant.can_grant_authority is False
    assert grant.can_approve_execution is False
