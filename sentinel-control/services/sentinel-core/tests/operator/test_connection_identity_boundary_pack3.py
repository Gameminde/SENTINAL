from __future__ import annotations

import inspect

import pytest

from sentinel.operator.connection_identity_models import (
    ConnectionCredentialLeaseDecision,
    ConnectionCredentialLeaseDecisionStatus,
    ConnectionCredentialLeasePolicy,
    ConnectionCredentialLeaseRequest,
    ConnectionCredentialSourceKind,
    ConnectionCredentialSourceRef,
    ConnectionIdentityBoundary,
    ConnectionPrincipal,
    ConnectionRevocationPolicy,
    ConnectionTenantScope,
)
from sentinel.operator.connection_identity_registry import build_default_connection_identity_registry
from sentinel.operator.connection_manifest_models import ConnectionRiskClass
from sentinel.operator.connection_manifest_registry import build_default_connection_manifest_registry
from sentinel.operator.runtime_host import SentinelRuntimeHost


def _source(**overrides: object) -> ConnectionCredentialSourceRef:
    values: dict[str, object] = {
        "source_ref_id": "credential_source_ref_test",
        "source_kind": ConnectionCredentialSourceKind.ENV_VAR,
        "env_var_name": "SENTINEL_CERT_MODEL_API_KEY",
        "secret_source_name": None,
        "provider_id": "aliyun_dashscope",
        "credential_scope_label": "model_provider_read_only_decision",
        "source_fingerprint": "sha256:credential-source-name-only",
        "expiry_metadata": "process_scoped_or_external_rotation",
        "use_count_limit": 1,
        "revocation_id": "revocation_test",
    }
    values.update(overrides)
    return ConnectionCredentialSourceRef(**values)


def _lease_policy(**overrides: object) -> ConnectionCredentialLeasePolicy:
    values: dict[str, object] = {
        "policy_id": "lease_policy_test",
        "credential_required": True,
        "credential_lease_required": True,
        "allowed_source_ref_ids": ("credential_source_ref_test",),
        "max_lease_seconds": 900,
        "max_use_count": 1,
        "explicit_approval_required": True,
        "revocation_required": True,
        "receipt_required": True,
        "replay_required": True,
    }
    values.update(overrides)
    return ConnectionCredentialLeasePolicy(**values)


def _principal(**overrides: object) -> ConnectionPrincipal:
    values: dict[str, object] = {
        "principal_id": "principal_operator",
        "principal_kind": "operator",
        "display_label": "operator",
        "identity_provider_ref": "local_operator_session",
    }
    values.update(overrides)
    return ConnectionPrincipal(**values)


def _tenant(**overrides: object) -> ConnectionTenantScope:
    values: dict[str, object] = {
        "tenant_scope_id": "tenant_local",
        "tenant_kind": "local_workspace",
        "workspace_scope_ref": "workspace:approved",
        "account_scope_ref": None,
        "data_residency_label": "local_only",
    }
    values.update(overrides)
    return ConnectionTenantScope(**values)


def _revocation(**overrides: object) -> ConnectionRevocationPolicy:
    values: dict[str, object] = {
        "revocation_policy_id": "revocation_policy_test",
        "revocation_required": True,
        "expiry_required": True,
        "max_ttl_seconds": 900,
        "kill_switch_required": True,
        "revocation_event_required": True,
    }
    values.update(overrides)
    return ConnectionRevocationPolicy(**values)


def _boundary(**overrides: object) -> ConnectionIdentityBoundary:
    values: dict[str, object] = {
        "connection_id": "model_provider_catalog",
        "principal": _principal(),
        "tenant_scope": _tenant(),
        "credential_sources": (_source(),),
        "lease_policy": _lease_policy(),
        "revocation_policy": _revocation(),
        "credential_required": True,
        "credential_lease_required": True,
        "explicit_approval_required": True,
        "mission_authority_envelope_required": True,
        "receipt_required": True,
        "replay_required": True,
        "boundary_can_authorize_action": False,
        "status_reason": "test boundary",
    }
    values.update(overrides)
    return ConnectionIdentityBoundary(**values)


@pytest.mark.parametrize(
    "bad_value",
    [
        "sk-live-actual-key",
        "Bearer secret-token",
        "Authorization: Bearer secret-token",
        "Cookie: session=secret",
        "session_token=secret",
        "password=secret",
        "-----BEGIN PRIVATE KEY-----",
        "oauth_access_token=secret",
    ],
)
def test_pack3_credential_source_rejects_secret_material(bad_value: str) -> None:
    with pytest.raises(ValueError, match="credential value|secret material"):
        _source(credential_scope_label=bad_value)


def test_pack3_env_var_names_are_allowed_but_values_are_not() -> None:
    source = _source(env_var_name="SENTINEL_CERT_MODEL_API_KEY")

    assert source.env_var_name == "SENTINEL_CERT_MODEL_API_KEY"
    assert source.credential_value_present is False
    assert source.raw_secret_material is False

    with pytest.raises(ValueError, match="env/config names"):
        _source(env_var_name="sk-ws-real-value")
    with pytest.raises(ValueError, match="raw endpoint"):
        _source(source_fingerprint="https://example.invalid/secret")


def test_pack3_lease_request_and_decision_are_data_only() -> None:
    request = ConnectionCredentialLeaseRequest(
        lease_request_id="lease_request_test",
        connection_id="model_provider_catalog",
        principal_id="principal_operator",
        tenant_scope_id="tenant_local",
        requested_source_ref_ids=("credential_source_ref_test",),
        requested_action="model_provider_call",
        authority_envelope_ref="authority_env_test",
    )
    decision = ConnectionCredentialLeaseDecision(
        lease_decision_id="lease_decision_test",
        lease_request_id=request.lease_request_id,
        connection_id=request.connection_id,
        status=ConnectionCredentialLeaseDecisionStatus.DENIED,
        safe_reason="no MissionAuthorityEnvelope grants action in tests",
        granted_source_ref_ids=(),
        authority_envelope_ref=request.authority_envelope_ref,
    )

    assert request.data_not_authority is True
    assert request.can_grant_authority is False
    assert request.registry_can_execute is False
    assert decision.data_not_authority is True
    assert decision.can_grant_authority is False
    assert decision.registry_can_execute is False

    with pytest.raises(ValueError, match="grant authority"):
        ConnectionCredentialLeaseRequest(
            lease_request_id="lease_request_bad",
            connection_id="model_provider_catalog",
            principal_id="principal_operator",
            tenant_scope_id="tenant_local",
            requested_source_ref_ids=("credential_source_ref_test",),
            requested_action="model_provider_call",
            authority_envelope_ref="authority_env_test",
            can_grant_authority=True,
        )
    with pytest.raises(ValueError, match="execute"):
        ConnectionCredentialLeaseDecision(
            lease_decision_id="lease_decision_bad",
            lease_request_id=request.lease_request_id,
            connection_id=request.connection_id,
            status=ConnectionCredentialLeaseDecisionStatus.DENIED,
            safe_reason="no MissionAuthorityEnvelope grants action in tests",
            granted_source_ref_ids=(),
            authority_envelope_ref=request.authority_envelope_ref,
            registry_can_execute=True,
        )


def test_pack3_identity_boundary_cannot_override_mission_authority() -> None:
    boundary = _boundary()

    assert boundary.boundary_can_authorize_action is False
    assert boundary.mission_authority_envelope_required is True
    assert boundary.authority_granting is False

    with pytest.raises(ValueError, match="authorize action"):
        _boundary(boundary_can_authorize_action=True)
    with pytest.raises(ValueError, match="authority"):
        _boundary(authority_granting=True)


def test_pack3_boundary_registry_covers_credential_required_manifests() -> None:
    manifest_registry = build_default_connection_manifest_registry()
    boundary_registry = build_default_connection_identity_registry()

    coverage = boundary_registry.compare_manifest_coverage(manifest_registry)

    assert coverage.missing_boundaries_for_credential_required_manifests == ()
    assert "read_only_research" not in coverage.missing_boundaries
    assert "model_provider_catalog" not in coverage.missing_boundaries
    assert "supabase_trace_repository" not in coverage.missing_boundaries


def test_pack3_high_risk_boundaries_require_approval_revocation_receipts_and_replay() -> None:
    manifest_registry = build_default_connection_manifest_registry()
    boundary_registry = build_default_connection_identity_registry()

    for manifest in manifest_registry.list_manifests():
        if manifest.risk_class not in {ConnectionRiskClass.C4, ConnectionRiskClass.C5}:
            continue
        boundary = boundary_registry.get(manifest.connection_id)
        assert manifest.product_dispatchable is False
        assert boundary.credential_lease_required is True
        assert boundary.explicit_approval_required is True
        assert boundary.revocation_policy.revocation_required is True
        assert boundary.receipt_required is True
        assert boundary.replay_required is True


def test_pack3_read_only_research_remains_credential_free_and_product_dispatchable() -> None:
    manifest = build_default_connection_manifest_registry().get("read_only_research")
    boundary = build_default_connection_identity_registry().get("read_only_research")

    assert manifest.product_dispatchable is True
    assert boundary.credential_required is False
    assert boundary.credential_lease_required is False
    assert boundary.lease_policy.policy_id == "none_required"
    assert boundary.credential_sources == ()


def test_pack3_model_provider_references_env_names_without_values() -> None:
    boundary = build_default_connection_identity_registry().get("model_provider_catalog")
    source_names = [source.env_var_name for source in boundary.credential_sources]

    assert "SENTINEL_CERT_MODEL_API_KEY" in source_names
    assert all(source.credential_value_present is False for source in boundary.credential_sources)
    assert all(source.raw_secret_material is False for source in boundary.credential_sources)
    assert all(source.source_fingerprint for source in boundary.credential_sources)

    with pytest.raises(ValueError, match="credential value"):
        _boundary(credential_sources=(_source(env_var_name="SENTINEL_CERT_MODEL_API_KEY", credential_value_present=True),))


def test_pack3_operator_memory_candidate_cannot_become_credential_source() -> None:
    boundary = build_default_connection_identity_registry().get("operator_memory_candidate")

    assert boundary.credential_required is False
    assert boundary.credential_sources == ()

    with pytest.raises(ValueError, match="memory candidate"):
        _boundary(
            connection_id="operator_memory_candidate",
            credential_required=True,
            credential_lease_required=True,
            credential_sources=(_source(),),
            lease_policy=_lease_policy(),
        )


def test_pack3_safe_export_contains_names_hashes_and_no_secret_values() -> None:
    registry = build_default_connection_identity_registry()

    exported = registry.export_safe_summaries()
    text = repr(exported)

    assert "SENTINEL_CERT_MODEL_API_KEY" in text
    assert "credential_env_name_hashes" in text
    assert "sk-" not in text
    assert "Bearer " not in text
    assert "Authorization:" not in text
    assert "Cookie:" not in text
    assert "-----BEGIN PRIVATE KEY-----" not in text
    assert "https://" not in text


def test_pack3_runtimehost_dispatch_remains_unaware_of_identity_registry() -> None:
    source = inspect.getsource(SentinelRuntimeHost.__init__)

    assert '"read_only_research_adapter"' in source
    assert "connection_identity" not in source.lower()
