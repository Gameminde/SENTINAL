from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.operator.connection_identity_models import (
    ConnectionCredentialLeasePolicy,
    ConnectionCredentialSourceKind,
    ConnectionCredentialSourceRef,
    ConnectionIdentityBoundary,
    ConnectionIdentityBoundaryCoverageReport,
    ConnectionPrincipal,
    ConnectionRevocationPolicy,
    ConnectionTenantScope,
)
from sentinel.operator.connection_manifest_models import ConnectionRiskClass
from sentinel.operator.connection_manifest_registry import (
    ConnectionManifestRegistry,
    build_default_connection_manifest_registry,
)
from sentinel.shared.models import SentinelModel


class ConnectionIdentityRegistry(SentinelModel):
    boundaries: tuple[ConnectionIdentityBoundary, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> "ConnectionIdentityRegistry":
        ids = [boundary.connection_id for boundary in self.boundaries]
        if len(ids) != len(set(ids)):
            raise ValueError("ConnectionIdentityRegistry cannot contain duplicate connection ids.")
        return self

    def list_boundaries(self) -> tuple[ConnectionIdentityBoundary, ...]:
        return tuple(sorted(self.boundaries, key=lambda item: item.connection_id))

    def get(self, connection_id: str) -> ConnectionIdentityBoundary:
        for boundary in self.boundaries:
            if boundary.connection_id == connection_id:
                return boundary
        raise KeyError(f"Unknown connection identity boundary `{connection_id}`.")

    def export_safe_summaries(self) -> list[dict[str, Any]]:
        return [boundary.safe_summary() for boundary in self.list_boundaries()]

    def compare_manifest_coverage(
        self,
        manifest_registry: ConnectionManifestRegistry | None = None,
    ) -> ConnectionIdentityBoundaryCoverageReport:
        manifest_registry = manifest_registry or build_default_connection_manifest_registry()
        boundary_ids = tuple(boundary.connection_id for boundary in self.list_boundaries())
        boundary_id_set = set(boundary_ids)
        manifest_ids = tuple(manifest.connection_id for manifest in manifest_registry.list_manifests())
        missing = tuple(connection_id for connection_id in manifest_ids if connection_id not in boundary_id_set)
        missing_credential_required = tuple(
            manifest.connection_id
            for manifest in manifest_registry.list_manifests()
            if manifest.credential_required and manifest.connection_id not in boundary_id_set
        )
        credential_required_without_policy: list[str] = []
        high_risk_missing_controls: list[str] = []
        for manifest in manifest_registry.list_manifests():
            if manifest.connection_id not in boundary_id_set:
                continue
            boundary = self.get(manifest.connection_id)
            if boundary.credential_required and not boundary.credential_lease_required:
                credential_required_without_policy.append(manifest.connection_id)
            if manifest.risk_class in {ConnectionRiskClass.C4, ConnectionRiskClass.C5} and not (
                not manifest.product_dispatchable
                and boundary.credential_lease_required
                and boundary.explicit_approval_required
                and boundary.revocation_policy.revocation_required
                and boundary.receipt_required
                and boundary.replay_required
            ):
                high_risk_missing_controls.append(manifest.connection_id)
        return ConnectionIdentityBoundaryCoverageReport(
            boundary_ids=boundary_ids,
            manifest_ids=manifest_ids,
            missing_boundaries=missing,
            missing_boundaries_for_credential_required_manifests=missing_credential_required,
            credential_required_without_lease_policy=tuple(credential_required_without_policy),
            high_risk_without_required_controls=tuple(high_risk_missing_controls),
        )


def build_default_connection_identity_registry() -> ConnectionIdentityRegistry:
    manifest_registry = build_default_connection_manifest_registry()
    boundaries: list[ConnectionIdentityBoundary] = []
    for manifest in manifest_registry.list_manifests():
        boundaries.append(_boundary_for_manifest(manifest.connection_id, manifest.credential_env_names, manifest.credential_required, manifest.risk_class))
    return ConnectionIdentityRegistry(boundaries=tuple(sorted(boundaries, key=lambda item: item.connection_id)))


def _boundary_for_manifest(
    connection_id: str,
    credential_env_names: tuple[str, ...],
    credential_required: bool,
    risk_class: ConnectionRiskClass,
) -> ConnectionIdentityBoundary:
    high_risk = risk_class in {ConnectionRiskClass.C4, ConnectionRiskClass.C5}
    if connection_id == "read_only_research":
        return _boundary(connection_id, credential_required=False, lease_required=False, status_reason="Read-only research uses workspace authority and no credentials.")
    if connection_id == "operator_memory_candidate":
        return _boundary(connection_id, credential_required=False, lease_required=False, status_reason="Operator memory candidate is data-only and cannot be a credential source.")
    sources = tuple(
        _source(
            connection_id=connection_id,
            env_var_name=env_name,
            provider_id=_provider_for_connection(connection_id),
            index=index,
        )
        for index, env_name in enumerate(credential_env_names)
    )
    requires_credential = credential_required or high_risk
    if requires_credential and not sources:
        sources = (
            _source(
                connection_id=connection_id,
                env_var_name=None,
                secret_source_name=f"{connection_id}_credential_source_name",
                provider_id=_provider_for_connection(connection_id),
                index=0,
            ),
        )
    return _boundary(
        connection_id,
        credential_required=requires_credential,
        lease_required=requires_credential,
        sources=sources,
        explicit_approval_required=high_risk or requires_credential,
        revocation_required=high_risk or requires_credential,
        receipt_required=high_risk or connection_id in {"model_provider_catalog", "external_api_dry_run"},
        replay_required=high_risk or connection_id in {"model_provider_catalog", "external_api_dry_run"},
        status_reason=(
            "High-risk surface requires explicit approval, revocation, receipts, and replay."
            if high_risk
            else "Credential-required surface is bound to source names only."
            if requires_credential
            else "Credential-free local/data-only surface."
        ),
    )


def _boundary(
    connection_id: str,
    *,
    credential_required: bool,
    lease_required: bool,
    sources: tuple[ConnectionCredentialSourceRef, ...] = (),
    explicit_approval_required: bool = False,
    revocation_required: bool = False,
    receipt_required: bool = False,
    replay_required: bool = False,
    status_reason: str,
) -> ConnectionIdentityBoundary:
    allowed_source_ids = tuple(source.source_ref_id for source in sources)
    return ConnectionIdentityBoundary(
        connection_id=connection_id,
        principal=ConnectionPrincipal(
            principal_id=f"principal_{connection_id}",
            principal_kind="operator_or_user_session",
            display_label=f"{connection_id}_principal",
            identity_provider_ref="local_operator_identity_context",
        ),
        tenant_scope=ConnectionTenantScope(
            tenant_scope_id=f"tenant_{connection_id}",
            tenant_kind="sentinel_local_or_external_scope",
            workspace_scope_ref="workspace:approved_or_none",
            account_scope_ref="account_scope_ref_by_name_only" if credential_required else None,
            data_residency_label="local_or_provider_contract_metadata",
        ),
        credential_sources=sources,
        lease_policy=ConnectionCredentialLeasePolicy(
            policy_id="none_required" if not credential_required else f"lease_policy_{connection_id}",
            credential_required=credential_required,
            credential_lease_required=lease_required,
            allowed_source_ref_ids=allowed_source_ids,
            max_lease_seconds=900 if credential_required else None,
            max_use_count=1 if credential_required else None,
            explicit_approval_required=explicit_approval_required,
            revocation_required=revocation_required,
            receipt_required=receipt_required,
            replay_required=replay_required,
        ),
        revocation_policy=ConnectionRevocationPolicy(
            revocation_policy_id=f"revocation_policy_{connection_id}",
            revocation_required=revocation_required,
            expiry_required=credential_required or revocation_required,
            max_ttl_seconds=900 if credential_required or revocation_required else None,
            kill_switch_required=revocation_required,
            revocation_event_required=revocation_required,
        ),
        credential_required=credential_required,
        credential_lease_required=lease_required,
        explicit_approval_required=explicit_approval_required,
        mission_authority_envelope_required=True,
        receipt_required=receipt_required,
        replay_required=replay_required,
        boundary_can_authorize_action=False,
        status_reason=status_reason,
    )


def _source(
    *,
    connection_id: str,
    env_var_name: str | None,
    provider_id: str | None,
    index: int,
    secret_source_name: str | None = None,
) -> ConnectionCredentialSourceRef:
    return ConnectionCredentialSourceRef(
        source_ref_id=f"credential_source_{connection_id}_{index}",
        source_kind=ConnectionCredentialSourceKind.ENV_VAR if env_var_name else ConnectionCredentialSourceKind.SECRET_SOURCE,
        env_var_name=env_var_name,
        secret_source_name=secret_source_name,
        provider_id=provider_id,
        credential_scope_label=f"{connection_id}_credential_scope",
        source_fingerprint=f"hash:{connection_id}:{index}:source_name_only",
        expiry_metadata="process_or_vault_scoped_expiry_metadata",
        use_count_limit=1,
        revocation_id=f"revocation_{connection_id}_{index}",
    )


def _provider_for_connection(connection_id: str) -> str | None:
    if connection_id == "model_provider_catalog":
        return "provider_catalog"
    if "browser" in connection_id:
        return "browser_session_or_credential_broker"
    if "channel" in connection_id:
        return "channel_credential_broker"
    if "external_api" in connection_id:
        return "external_api_credential_broker"
    if "supabase" in connection_id:
        return "supabase"
    if "cueidea" in connection_id:
        return "cueidea_bridge"
    if "voice" in connection_id:
        return "voice_provider_contract"
    if "financial" in connection_id or "account" in connection_id:
        return "special_authority_credential_broker"
    if "desktop" in connection_id:
        return "desktop_sidecar_enrollment"
    if "credential_vault" in connection_id:
        return "credential_vault"
    if "skill" in connection_id:
        return "skill_fabric"
    return None


__all__ = [
    "ConnectionIdentityRegistry",
    "build_default_connection_identity_registry",
]
