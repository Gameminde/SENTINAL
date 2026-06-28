from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


class ConnectionCredentialSourceKind(StrEnum):
    ENV_VAR = "env_var"
    SECRET_SOURCE = "secret_source"
    PROVIDER_CATALOG = "provider_catalog"
    CREDENTIAL_BROKER = "credential_broker"
    NONE = "none"


class ConnectionCredentialLeaseDecisionStatus(StrEnum):
    APPROVED = "approved"
    DENIED = "denied"


_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
_FORBIDDEN_SECRET_PATTERNS = (
    "sk-",
    "bearer ",
    "authorization",
    "cookie:",
    "session_token",
    "session=",
    "password",
    "private key",
    "-----begin",
    "oauth_access_token",
    "access_token=",
    "api_key=",
    "secret=",
)


class ConnectionIdentityDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    authority_granting: bool = False
    can_grant_authority: bool = False
    registry_can_execute: bool = False
    credential_value_present: bool = False
    raw_secret_material: bool = False

    @model_validator(mode="after")
    def _identity_data_is_not_authority(self) -> "ConnectionIdentityDataModel":
        if self.authority_granting:
            raise ValueError(f"{self.__class__.__name__}: authority granting is forbidden")
        if self.registry_can_execute:
            raise ValueError(f"{self.__class__.__name__}: registry cannot execute")
        if self.credential_value_present:
            raise ValueError(f"{self.__class__.__name__}: credential value persistence is forbidden")
        if self.raw_secret_material:
            raise ValueError(f"{self.__class__.__name__}: raw secret material is forbidden")
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.registry_can_execute,
        )
        return self


class ConnectionPrincipal(ConnectionIdentityDataModel):
    principal_id: str
    principal_kind: str
    display_label: str
    identity_provider_ref: str

    @model_validator(mode="after")
    def _principal_is_safe(self) -> "ConnectionPrincipal":
        _require_trimmed("principal_id", self.principal_id)
        _reject_secret_text(self.principal_kind, "principal_kind")
        _reject_secret_text(self.display_label, "display_label")
        _reject_secret_text(self.identity_provider_ref, "identity_provider_ref")
        return self


class ConnectionTenantScope(ConnectionIdentityDataModel):
    tenant_scope_id: str
    tenant_kind: str
    workspace_scope_ref: str | None = None
    account_scope_ref: str | None = None
    data_residency_label: str

    @model_validator(mode="after")
    def _tenant_scope_is_safe(self) -> "ConnectionTenantScope":
        _require_trimmed("tenant_scope_id", self.tenant_scope_id)
        for label, value in (
            ("tenant_kind", self.tenant_kind),
            ("workspace_scope_ref", self.workspace_scope_ref or ""),
            ("account_scope_ref", self.account_scope_ref or ""),
            ("data_residency_label", self.data_residency_label),
        ):
            _reject_secret_text(value, label)
        return self


class ConnectionCredentialSourceRef(ConnectionIdentityDataModel):
    source_ref_id: str
    source_kind: ConnectionCredentialSourceKind
    env_var_name: str | None = None
    secret_source_name: str | None = None
    provider_id: str | None = None
    credential_scope_label: str
    source_fingerprint: str
    expiry_metadata: str | None = None
    use_count_limit: int | None = Field(default=None, ge=1)
    revocation_id: str | None = None

    @model_validator(mode="after")
    def _credential_source_ref_is_name_only(self) -> "ConnectionCredentialSourceRef":
        _require_trimmed("source_ref_id", self.source_ref_id)
        if self.env_var_name is not None:
            if not _ENV_NAME_RE.fullmatch(self.env_var_name):
                raise ValueError("credential source env_var_name must contain env/config names only")
        for label, value in (
            ("env_var_name", self.env_var_name or ""),
            ("secret_source_name", self.secret_source_name or ""),
            ("provider_id", self.provider_id or ""),
            ("credential_scope_label", self.credential_scope_label),
            ("source_fingerprint", self.source_fingerprint),
            ("expiry_metadata", self.expiry_metadata or ""),
            ("revocation_id", self.revocation_id or ""),
        ):
            _reject_secret_text(value, label)
        if "://" in self.source_fingerprint:
            raise ValueError("credential source raw endpoint values are not allowed")
        return self

    def safe_summary(self) -> dict[str, Any]:
        payload = {
            "source_ref_id": self.source_ref_id,
            "source_kind": self.source_kind.value,
            "env_var_name": self.env_var_name,
            "env_var_name_hash": text_hash(self.env_var_name or ""),
            "secret_source_name": self.secret_source_name,
            "secret_source_name_hash": text_hash(self.secret_source_name or ""),
            "provider_id": self.provider_id,
            "credential_scope_label": self.credential_scope_label,
            "source_fingerprint": self.source_fingerprint,
            "expiry_metadata": self.expiry_metadata,
            "use_count_limit": self.use_count_limit,
            "revocation_id": self.revocation_id,
            "credential_value_present": self.credential_value_present,
            "raw_secret_material": self.raw_secret_material,
        }
        payload["source_safe_hash"] = stable_hash(payload)
        return payload


class ConnectionCredentialLeasePolicy(ConnectionIdentityDataModel):
    policy_id: str
    credential_required: bool
    credential_lease_required: bool
    allowed_source_ref_ids: tuple[str, ...] = Field(default_factory=tuple)
    max_lease_seconds: int | None = Field(default=None, ge=1)
    max_use_count: int | None = Field(default=None, ge=1)
    explicit_approval_required: bool
    revocation_required: bool
    receipt_required: bool
    replay_required: bool

    @model_validator(mode="after")
    def _lease_policy_is_consistent(self) -> "ConnectionCredentialLeasePolicy":
        _require_trimmed("policy_id", self.policy_id)
        if not self.credential_required and self.policy_id != "none_required":
            raise ValueError("credential-free surfaces must use none_required lease policy")
        if self.credential_required and not self.credential_lease_required:
            raise ValueError("credential-required surfaces require a credential lease policy")
        if self.credential_required and not self.allowed_source_ref_ids:
            raise ValueError("credential-required surfaces require allowed credential source refs")
        for source_ref_id in self.allowed_source_ref_ids:
            _reject_secret_text(source_ref_id, "allowed_source_ref_ids")
        return self


class ConnectionCredentialLeaseRequest(ConnectionIdentityDataModel):
    lease_request_id: str
    connection_id: str
    principal_id: str
    tenant_scope_id: str
    requested_source_ref_ids: tuple[str, ...] = Field(default_factory=tuple)
    requested_action: str
    authority_envelope_ref: str

    @model_validator(mode="after")
    def _lease_request_is_safe(self) -> "ConnectionCredentialLeaseRequest":
        for label, value in (
            ("lease_request_id", self.lease_request_id),
            ("connection_id", self.connection_id),
            ("principal_id", self.principal_id),
            ("tenant_scope_id", self.tenant_scope_id),
            ("requested_action", self.requested_action),
            ("authority_envelope_ref", self.authority_envelope_ref),
        ):
            _require_trimmed(label, value)
            _reject_secret_text(value, label)
        for source_ref_id in self.requested_source_ref_ids:
            _reject_secret_text(source_ref_id, "requested_source_ref_ids")
        return self


class ConnectionCredentialLeaseDecision(ConnectionIdentityDataModel):
    lease_decision_id: str
    lease_request_id: str
    connection_id: str
    status: ConnectionCredentialLeaseDecisionStatus
    safe_reason: str
    granted_source_ref_ids: tuple[str, ...] = Field(default_factory=tuple)
    authority_envelope_ref: str

    @model_validator(mode="after")
    def _lease_decision_is_safe(self) -> "ConnectionCredentialLeaseDecision":
        for label, value in (
            ("lease_decision_id", self.lease_decision_id),
            ("lease_request_id", self.lease_request_id),
            ("connection_id", self.connection_id),
            ("safe_reason", self.safe_reason),
            ("authority_envelope_ref", self.authority_envelope_ref),
        ):
            _require_trimmed(label, value)
            _reject_secret_text(value, label)
        if self.status is ConnectionCredentialLeaseDecisionStatus.APPROVED and not self.granted_source_ref_ids:
            raise ValueError("approved credential lease decisions require source refs")
        for source_ref_id in self.granted_source_ref_ids:
            _reject_secret_text(source_ref_id, "granted_source_ref_ids")
        return self


class ConnectionRevocationPolicy(ConnectionIdentityDataModel):
    revocation_policy_id: str
    revocation_required: bool
    expiry_required: bool
    max_ttl_seconds: int | None = Field(default=None, ge=1)
    kill_switch_required: bool
    revocation_event_required: bool

    @model_validator(mode="after")
    def _revocation_policy_is_safe(self) -> "ConnectionRevocationPolicy":
        _require_trimmed("revocation_policy_id", self.revocation_policy_id)
        return self


class ConnectionIdentityBoundary(ConnectionIdentityDataModel):
    connection_id: str
    principal: ConnectionPrincipal
    tenant_scope: ConnectionTenantScope
    credential_sources: tuple[ConnectionCredentialSourceRef, ...] = Field(default_factory=tuple)
    lease_policy: ConnectionCredentialLeasePolicy
    revocation_policy: ConnectionRevocationPolicy
    credential_required: bool
    credential_lease_required: bool
    explicit_approval_required: bool
    mission_authority_envelope_required: bool
    receipt_required: bool
    replay_required: bool
    boundary_can_authorize_action: bool = False
    status_reason: str

    @model_validator(mode="after")
    def _identity_boundary_is_safe(self) -> "ConnectionIdentityBoundary":
        _require_trimmed("connection_id", self.connection_id)
        _reject_secret_text(self.status_reason, "status_reason")
        if self.boundary_can_authorize_action:
            raise ValueError("identity boundary cannot authorize action")
        if not self.mission_authority_envelope_required:
            raise ValueError("identity boundary requires MissionAuthorityEnvelope for action")
        if self.connection_id == "operator_memory_candidate" and (self.credential_required or self.credential_sources):
            raise ValueError("operator memory candidate cannot become a credential source")
        if self.credential_required != self.lease_policy.credential_required:
            raise ValueError("identity boundary credential_required must match lease policy")
        if self.credential_lease_required != self.lease_policy.credential_lease_required:
            raise ValueError("identity boundary credential_lease_required must match lease policy")
        source_ids = {source.source_ref_id for source in self.credential_sources}
        for required_ref in self.lease_policy.allowed_source_ref_ids:
            if required_ref not in source_ids:
                raise ValueError("lease policy references unknown credential source")
        if self.credential_required and not self.credential_sources:
            raise ValueError("credential-required boundary needs source refs")
        return self

    def safe_summary(self) -> dict[str, Any]:
        payload = {
            "connection_id": self.connection_id,
            "principal_id": self.principal.principal_id,
            "principal_kind": self.principal.principal_kind,
            "tenant_scope_id": self.tenant_scope.tenant_scope_id,
            "tenant_kind": self.tenant_scope.tenant_kind,
            "workspace_scope_ref_hash": text_hash(self.tenant_scope.workspace_scope_ref or ""),
            "account_scope_ref_hash": text_hash(self.tenant_scope.account_scope_ref or ""),
            "credential_required": self.credential_required,
            "credential_lease_required": self.credential_lease_required,
            "credential_source_refs": [source.safe_summary() for source in self.credential_sources],
            "credential_env_names": [
                source.env_var_name for source in self.credential_sources if source.env_var_name
            ],
            "credential_env_name_hashes": [
                text_hash(source.env_var_name or "") for source in self.credential_sources if source.env_var_name
            ],
            "lease_policy_id": self.lease_policy.policy_id,
            "explicit_approval_required": self.explicit_approval_required,
            "mission_authority_envelope_required": self.mission_authority_envelope_required,
            "revocation_policy_id": self.revocation_policy.revocation_policy_id,
            "revocation_required": self.revocation_policy.revocation_required,
            "expiry_required": self.revocation_policy.expiry_required,
            "receipt_required": self.receipt_required,
            "replay_required": self.replay_required,
            "boundary_can_authorize_action": self.boundary_can_authorize_action,
            "status_reason": self.status_reason,
        }
        payload["boundary_safe_hash"] = stable_hash(payload)
        return payload


class ConnectionIdentityBoundaryCoverageReport(SentinelModel):
    boundary_ids: tuple[str, ...]
    manifest_ids: tuple[str, ...]
    missing_boundaries: tuple[str, ...]
    missing_boundaries_for_credential_required_manifests: tuple[str, ...]
    credential_required_without_lease_policy: tuple[str, ...]
    high_risk_without_required_controls: tuple[str, ...]


def _require_trimmed(label: str, value: str) -> None:
    if not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be stable and trimmed")


def _reject_secret_text(value: str, label: str) -> None:
    lowered = value.lower()
    if "://" in value:
        raise ValueError(f"{label} cannot contain raw endpoint values")
    if any(marker in lowered for marker in _FORBIDDEN_SECRET_PATTERNS):
        raise ValueError(f"{label} cannot contain credential value or secret material")


__all__ = [
    "ConnectionCredentialLeaseDecision",
    "ConnectionCredentialLeaseDecisionStatus",
    "ConnectionCredentialLeasePolicy",
    "ConnectionCredentialLeaseRequest",
    "ConnectionCredentialSourceKind",
    "ConnectionCredentialSourceRef",
    "ConnectionIdentityBoundary",
    "ConnectionIdentityBoundaryCoverageReport",
    "ConnectionPrincipal",
    "ConnectionRevocationPolicy",
    "ConnectionTenantScope",
]
