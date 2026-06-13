from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    scan_forbidden_payload_categorized,
    scan_secret_like_text,
)


def vault_utc_now() -> datetime:
    return datetime.now(UTC)


class CredentialVaultDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _credential_vault_data_is_not_authority(self) -> CredentialVaultDataModel:
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        payload = redact_operator_value(self.model_dump(mode="json"))
        return _safe_secret_key_names(payload)


class CredentialVaultMaturity(StrEnum):
    METADATA_ONLY = "metadata_only"
    FAKE_SEALED_STORE = "fake_sealed_store"
    LOCAL_ENCRYPTED_STORE = "local_encrypted_store"
    OS_KEYCHAIN_DESCRIPTOR = "os_keychain_descriptor"
    OS_KEYCHAIN_LIVE_OPT_IN = "os_keychain_live_opt_in"
    PRODUCTION_READY_VAULT = "production_ready_vault"


class SecretKind(StrEnum):
    API_KEY = "api_key"
    OAUTH_ACCESS_TOKEN = "oauth_access_token"
    OAUTH_REFRESH_TOKEN = "oauth_refresh_token"
    SESSION_COOKIE = "session_cookie"
    BROWSER_SESSION_REF = "browser_session_ref"
    SMTP_PASSWORD = "smtp_password"
    CHANNEL_TOKEN = "channel_token"
    USERNAME_PASSWORD = "username_password"
    SSH_KEY_REF = "ssh_key_ref"
    LOCAL_APP_SECRET = "local_app_secret"
    PAYMENT_METHOD_REF = "payment_method_ref"
    TRADING_API_KEY_REF = "trading_api_key_ref"
    DEVICE_PAIRING_SECRET = "device_pairing_secret"


class SecretSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    SPECIAL_AUTHORITY = "special_authority"


class SecretVersionState(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ROTATION_REQUIRED = "rotation_required"


class SecretAccessLeaseState(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    USED = "used"
    REJECTED = "rejected"


class VaultLockState(StrEnum):
    LOCKED = "locked"
    UNLOCK_REQUESTED = "unlock_requested"
    UNLOCKED_FOR_SESSION = "unlocked_for_session"
    PARTIALLY_UNLOCKED = "partially_unlocked"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOCKED_AFTER_KILL = "locked_after_kill"


class CredentialConsumerKind(StrEnum):
    EXTERNAL_API = "external_api"
    CHANNEL_ADAPTER = "channel_adapter"
    BROWSER_LOGIN = "browser_login"
    DESKTOP_SIDECAR = "desktop_sidecar"
    MODEL_PROVIDER = "model_provider"
    WORKER = "worker"
    SKILL = "skill"
    DAEMON = "daemon"
    VOICE = "voice"
    MEMORY = "memory"
    LLM = "llm"
    TEST_CONSUMER = "test_consumer"


class CredentialUseRiskProfile(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SPECIAL_AUTHORITY = "special_authority"


class SecretFinalGateDecision(StrEnum):
    REGISTERED = "registered"
    REJECTED = "rejected"
    UNLOCKED = "unlocked"
    LOCKED = "locked"
    ACCESS_GRANTED = "access_granted"
    ACCESS_REJECTED = "access_rejected"
    LEASE_CREATED = "lease_created"
    LEASE_EXPIRED = "lease_expired"
    LEASE_REVOKED = "lease_revoked"
    USED = "used"
    FAILED = "failed"
    REVOKED = "revoked"
    ROTATION_REQUIRED = "rotation_required"


class CredentialVaultConfig(CredentialVaultDataModel):
    vault_id: str = Field(default_factory=lambda: new_id("credential_vault"))
    maturity: CredentialVaultMaturity = CredentialVaultMaturity.FAKE_SEALED_STORE
    durable_metadata: bool = True
    durable_raw_secret_persistence: bool = False
    durable_secret_material_persistence: bool = False
    os_keychain_live_calls_allowed: bool = False
    cloud_vault_calls_allowed: bool = False
    password_manager_import_allowed: bool = False
    operator_visible: bool = True
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_honest_v1(self) -> CredentialVaultConfig:
        if not self.vault_id.strip():
            raise ValueError("credential vault id is required")
        if self.durable_raw_secret_persistence or self.durable_secret_material_persistence:
            raise ValueError("durable raw secret persistence is blocked")
        if self.os_keychain_live_calls_allowed or self.cloud_vault_calls_allowed or self.password_manager_import_allowed:
            raise ValueError("credential vault v1 does not call OS keychains, cloud vaults, or password managers")
        if self.maturity not in {CredentialVaultMaturity.METADATA_ONLY, CredentialVaultMaturity.FAKE_SEALED_STORE, CredentialVaultMaturity.OS_KEYCHAIN_DESCRIPTOR}:
            raise ValueError("credential vault v1 may only claim metadata, fake sealed, or descriptor maturity")
        return self

    def with_hash(self) -> CredentialVaultConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class CredentialVaultId(CredentialVaultDataModel):
    vault_id: str
    mission_id: str | None = None
    vault_ref_hash: str = ""

    def with_hash(self) -> CredentialVaultId:
        payload = self.safe_model_dump()
        payload["vault_ref_hash"] = ""
        return self.model_copy(update={"vault_ref_hash": stable_hash(payload)})


class SecretScope(CredentialVaultDataModel):
    allowed_scopes: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)


class CredentialScopePolicy(CredentialVaultDataModel):
    allowed_consumers: list[CredentialConsumerKind] = Field(default_factory=list)
    allowed_consumer_refs: list[str] = Field(default_factory=list)
    allowed_purposes: list[str] = Field(default_factory=list)
    allowed_scopes: list[str] = Field(default_factory=list)
    blocked_kinds: list[SecretKind] = Field(default_factory=lambda: [
        SecretKind.PAYMENT_METHOD_REF,
        SecretKind.TRADING_API_KEY_REF,
        SecretKind.DEVICE_PAIRING_SECRET,
    ])
    policy_hash: str = ""

    @model_validator(mode="after")
    def _policy_is_bounded(self) -> CredentialScopePolicy:
        if not self.allowed_consumers:
            raise ValueError("credential scope policy requires allowed consumers")
        if not self.allowed_purposes:
            raise ValueError("credential scope policy requires allowed purposes")
        if not self.allowed_scopes:
            raise ValueError("credential scope policy requires allowed scopes")
        self.allowed_consumer_refs = [redact_operator_text(item) for item in self.allowed_consumer_refs]
        self.allowed_purposes = [_safe_identifier(item, "purpose") for item in self.allowed_purposes]
        self.allowed_scopes = [redact_operator_text(item) for item in self.allowed_scopes]
        return self

    def with_hash(self) -> CredentialScopePolicy:
        payload = self.safe_model_dump()
        payload["policy_hash"] = ""
        return self.model_copy(update={"policy_hash": stable_hash(payload)})


class SecretUsePurpose(CredentialVaultDataModel):
    purpose: str


class SecretUsePolicy(CredentialVaultDataModel):
    allowed_purposes: list[str] = Field(default_factory=list)
    allowed_kinds: list[SecretKind] = Field(default_factory=list)
    max_lease_seconds: int = Field(default=300, ge=1)
    require_unlock_session: bool = True
    require_operator_approval: bool = True
    risk_profile: CredentialUseRiskProfile = CredentialUseRiskProfile.MEDIUM
    policy_hash: str = ""

    @model_validator(mode="after")
    def _use_policy_is_bounded(self) -> SecretUsePolicy:
        if not self.allowed_purposes:
            raise ValueError("secret use policy requires allowed purposes")
        if not self.allowed_kinds:
            raise ValueError("secret use policy requires allowed kinds")
        self.allowed_purposes = [_safe_identifier(item, "purpose") for item in self.allowed_purposes]
        return self

    def with_hash(self) -> SecretUsePolicy:
        payload = self.safe_model_dump()
        payload["policy_hash"] = ""
        return self.model_copy(update={"policy_hash": stable_hash(payload)})


class SecretUseContext(CredentialVaultDataModel):
    target_ref: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Secret use context metadata only."

    @model_validator(mode="after")
    def _context_is_safe(self) -> SecretUseContext:
        self.target_ref = redact_operator_text(self.target_ref) if self.target_ref else None
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class SecretProvenance(CredentialVaultDataModel):
    source: str
    source_ref_hash: str | None = None
    safe_summary: str = "Secret provenance metadata only."

    @model_validator(mode="after")
    def _provenance_is_safe(self) -> SecretProvenance:
        self.source = redact_operator_text(self.source)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class SecretVersion(CredentialVaultDataModel):
    version_id: str = Field(default_factory=lambda: new_id("secret_version"))
    version_number: int = Field(default=1, ge=1)
    state: SecretVersionState = SecretVersionState.ACTIVE
    created_at: datetime = Field(default_factory=vault_utc_now)
    expires_at: datetime | None = None
    version_hash: str = ""

    def with_hash(self) -> SecretVersion:
        payload = self.safe_model_dump()
        payload["version_hash"] = ""
        return self.model_copy(update={"version_hash": stable_hash(payload)})


class SecretRotationPolicy(CredentialVaultDataModel):
    rotation_supported: bool = False
    rotation_required: bool = False
    rotation_due_at: datetime | None = None
    rotation_status: str = "rotation_metadata_only_v1"


class SecretExpiryPolicy(CredentialVaultDataModel):
    expires_at: datetime | None = None
    fail_closed_after_expiry: bool = True


class SecretRevocationRecord(CredentialVaultDataModel):
    revocation_id: str = Field(default_factory=lambda: new_id("secret_revocation"))
    secret_id: str
    mission_id: str
    reason: str
    revoked_at: datetime = Field(default_factory=vault_utc_now)
    revocation_hash: str = ""

    @model_validator(mode="after")
    def _revocation_is_safe(self) -> SecretRevocationRecord:
        self.reason = redact_operator_text(self.reason)
        return self

    def with_hash(self) -> SecretRevocationRecord:
        payload = self.safe_model_dump()
        payload["revocation_hash"] = ""
        return self.model_copy(update={"revocation_hash": stable_hash(payload)})


class SecretRef(CredentialVaultDataModel):
    secret_ref_id: str = Field(default_factory=lambda: new_id("secret_ref"))
    secret_id: str
    kind: SecretKind
    label: str
    ref_hash: str = ""

    @model_validator(mode="after")
    def _ref_is_safe(self) -> SecretRef:
        self.label = redact_operator_text(self.label)
        return self

    @property
    def redacted_label(self) -> str:
        return f"secret_ref:{self.secret_ref_id}:{self.kind.value}:{self.label}"

    def with_hash(self) -> SecretRef:
        payload = self.safe_model_dump()
        payload["ref_hash"] = ""
        return self.model_copy(update={"ref_hash": stable_hash(payload)})


class SecretHandle(CredentialVaultDataModel):
    handle_id: str = Field(default_factory=lambda: new_id("secret_handle"))
    secret_id: str
    secret_ref_id: str
    kind: SecretKind
    redacted_label: str
    scope_hash: str
    handle_hash: str = ""

    @model_validator(mode="after")
    def _handle_is_safe(self) -> SecretHandle:
        self.redacted_label = redact_operator_text(self.redacted_label)
        return self

    def with_hash(self) -> SecretHandle:
        payload = self.safe_model_dump()
        payload["handle_hash"] = ""
        return self.model_copy(update={"handle_hash": stable_hash(payload)})


class SecretMaterialEnvelope(CredentialVaultDataModel):
    envelope_id: str = Field(default_factory=lambda: new_id("secret_material"))
    storage_maturity: CredentialVaultMaturity = CredentialVaultMaturity.FAKE_SEALED_STORE
    sealed_payload_hash: str
    fake_sealed_ref: str
    raw_secret_persisted: bool = False
    secret_material_persisted: bool = False
    encrypted: bool = False
    materialized: bool = False
    envelope_hash: str = ""

    @model_validator(mode="after")
    def _material_envelope_is_honest(self) -> SecretMaterialEnvelope:
        if self.raw_secret_persisted or self.secret_material_persisted:
            raise ValueError("raw secret material persistence is blocked")
        if self.encrypted and self.storage_maturity is not CredentialVaultMaturity.LOCAL_ENCRYPTED_STORE:
            raise ValueError("credential vault cannot claim encryption without encrypted-store maturity")
        if self.materialized:
            raise ValueError("secret material envelope cannot materialize secret values")
        return self

    def with_hash(self) -> SecretMaterialEnvelope:
        payload = self.safe_model_dump()
        payload["envelope_hash"] = ""
        return self.model_copy(update={"envelope_hash": stable_hash(payload)})


class SecretMetadata(CredentialVaultDataModel):
    secret_id: str = Field(default_factory=lambda: new_id("secret"))
    vault_id: str
    mission_id: str
    kind: SecretKind
    label: str
    sensitivity: SecretSensitivity
    provenance: SecretProvenance
    version: SecretVersion
    scope_policy: CredentialScopePolicy
    use_policy: SecretUsePolicy
    material_envelope: SecretMaterialEnvelope
    secret_ref: SecretRef
    secret_handle: SecretHandle
    expiry_policy: SecretExpiryPolicy = Field(default_factory=SecretExpiryPolicy)
    rotation_policy: SecretRotationPolicy = Field(default_factory=SecretRotationPolicy)
    revoked_at: datetime | None = None
    revocation_ref: str | None = None
    created_at: datetime = Field(default_factory=vault_utc_now)
    metadata_hash: str = ""

    @model_validator(mode="after")
    def _metadata_is_safe(self) -> SecretMetadata:
        self.label = redact_operator_text(self.label)
        return self

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None or self.version.state is SecretVersionState.REVOKED

    def is_expired(self, current_time: datetime | None = None) -> bool:
        now = current_time or vault_utc_now()
        return self.expiry_policy.expires_at is not None and now >= self.expiry_policy.expires_at

    def with_hash(self) -> SecretMetadata:
        payload = self.safe_model_dump()
        payload["metadata_hash"] = ""
        return self.model_copy(update={"metadata_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["metadata_hash"]
        payload["metadata_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class VaultUnlockMethodDescriptor(CredentialVaultDataModel):
    method_id: str = Field(default_factory=lambda: new_id("unlock_method"))
    method_kind: str = "operator_approval_descriptor"
    biometric_allowed: bool = False
    password_manager_extraction_allowed: bool = False

    @model_validator(mode="after")
    def _method_is_safe(self) -> VaultUnlockMethodDescriptor:
        if self.biometric_allowed:
            raise ValueError("voice/biometric unlock is not allowed in credential vault v1")
        if self.password_manager_extraction_allowed:
            raise ValueError("password manager extraction is not allowed in credential vault v1")
        return self


class VaultUnlockPolicy(CredentialVaultDataModel):
    ttl_seconds: int = Field(default=300, ge=1)
    allowed_purposes: list[str] = Field(default_factory=list)
    mission_scoped: bool = True
    operator_approval_required: bool = True
    method: VaultUnlockMethodDescriptor = Field(default_factory=VaultUnlockMethodDescriptor)

    @model_validator(mode="after")
    def _unlock_policy_is_scoped(self) -> VaultUnlockPolicy:
        if not self.allowed_purposes:
            raise ValueError("vault unlock policy requires allowed purposes")
        self.allowed_purposes = [_safe_identifier(item, "purpose") for item in self.allowed_purposes]
        return self


class VaultOperatorApproval(CredentialVaultDataModel):
    approval_id: str = Field(default_factory=lambda: new_id("vault_approval"))
    unlock_session_id: str
    approval_source: str
    approved: bool = True
    approved_at: datetime = Field(default_factory=vault_utc_now)
    approval_hash: str = ""

    @model_validator(mode="after")
    def _approval_is_operator_only(self) -> VaultOperatorApproval:
        if self.approval_source not in {"operator", "operator_policy", "manual_operator"}:
            raise ValueError("vault unlock approval must come from operator")
        return self

    def with_hash(self) -> VaultOperatorApproval:
        payload = self.safe_model_dump()
        payload["approval_hash"] = ""
        return self.model_copy(update={"approval_hash": stable_hash(payload)})


class VaultUnlockSession(CredentialVaultDataModel):
    unlock_session_id: str = Field(default_factory=lambda: new_id("vault_unlock"))
    mission_id: str
    vault_id: str
    purpose: str
    state: VaultLockState = VaultLockState.UNLOCK_REQUESTED
    requested_by: str = "operator"
    requested_at: datetime = Field(default_factory=vault_utc_now)
    approved_at: datetime | None = None
    expires_at: datetime
    revoked_at: datetime | None = None
    approval_ref: str | None = None
    unlock_session_is_authority: bool = False
    session_hash: str = ""

    @model_validator(mode="after")
    def _unlock_session_is_not_authority(self) -> VaultUnlockSession:
        self.purpose = _safe_identifier(self.purpose, "purpose")
        self.requested_by = redact_operator_text(self.requested_by)
        if self.unlock_session_is_authority:
            raise ValueError("vault unlock session is not authority")
        return self

    def is_active(self, current_time: datetime | None = None) -> bool:
        now = current_time or vault_utc_now()
        return self.state is VaultLockState.UNLOCKED_FOR_SESSION and self.revoked_at is None and now < self.expires_at

    def with_hash(self) -> VaultUnlockSession:
        payload = self.safe_model_dump()
        payload["session_hash"] = ""
        return self.model_copy(update={"session_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["session_hash"]
        payload["session_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class CredentialConsumerRef(CredentialVaultDataModel):
    consumer_kind: CredentialConsumerKind
    consumer_ref: str

    @model_validator(mode="after")
    def _consumer_ref_is_safe(self) -> CredentialConsumerRef:
        self.consumer_ref = redact_operator_text(self.consumer_ref)
        return self


class CredentialBinding(CredentialVaultDataModel):
    binding_id: str = Field(default_factory=lambda: new_id("credential_binding"))
    secret_id: str
    consumer: CredentialConsumerRef
    binding_hash: str = ""


class SecretAccessRequest(CredentialVaultDataModel):
    request_id: str = Field(default_factory=lambda: new_id("secret_access_request"))
    mission_id: str
    secret_id: str
    consumer: CredentialConsumerRef
    purpose: str
    requested_scope: list[str] = Field(default_factory=list)
    unlock_session_id: str | None = None
    context: SecretUseContext = Field(default_factory=SecretUseContext)
    requested_at: datetime = Field(default_factory=vault_utc_now)
    request_hash: str = ""

    @model_validator(mode="after")
    def _request_is_safe(self) -> SecretAccessRequest:
        self.purpose = _safe_identifier(self.purpose, "purpose")
        self.requested_scope = [redact_operator_text(item) for item in self.requested_scope]
        return self

    def with_hash(self) -> SecretAccessRequest:
        payload = self.safe_model_dump()
        payload["request_hash"] = ""
        return self.model_copy(update={"request_hash": stable_hash(payload)})


class SecretAccessGrant(CredentialVaultDataModel):
    grant_id: str = Field(default_factory=lambda: new_id("secret_grant"))
    request_id: str
    mission_id: str
    secret_id: str
    secret_handle: SecretHandle
    consumer: CredentialConsumerRef
    purpose: str
    granted_scope: list[str]
    unlock_session_id: str | None
    issued_at: datetime = Field(default_factory=vault_utc_now)
    expires_at: datetime
    receipt_ref: str | None = None
    finalgate_ref: str | None = None
    grant_hash: str = ""

    def with_hash(self) -> SecretAccessGrant:
        payload = self.safe_model_dump()
        payload["grant_hash"] = ""
        return self.model_copy(update={"grant_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["grant_hash"]
        payload["grant_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class SecretAccessLease(CredentialVaultDataModel):
    lease_id: str = Field(default_factory=lambda: new_id("secret_lease"))
    lease_ref_hash: str = ""
    grant_id: str
    mission_id: str
    secret_id: str
    secret_handle: SecretHandle
    state: SecretAccessLeaseState = SecretAccessLeaseState.ACTIVE
    created_at: datetime = Field(default_factory=vault_utc_now)
    expires_at: datetime
    revoked_at: datetime | None = None
    used_at: datetime | None = None
    lease_hash: str = ""

    def is_active(self, current_time: datetime | None = None) -> bool:
        now = current_time or vault_utc_now()
        return self.state is SecretAccessLeaseState.ACTIVE and self.revoked_at is None and now < self.expires_at

    def with_hash(self) -> SecretAccessLease:
        payload = self.safe_model_dump()
        payload["lease_hash"] = ""
        return self.model_copy(update={"lease_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["lease_hash"]
        payload["lease_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        payload = super().safe_model_dump()
        raw_lease_id = str(payload.pop("lease_id", self.lease_id))
        payload["lease_ref_hash"] = self.lease_ref_hash or stable_hash(raw_lease_id)
        return payload


class SecretCheckoutToken(CredentialVaultDataModel):
    checkout_token_id: str = Field(default_factory=lambda: new_id("secret_checkout"))
    lease_id: str | None = None
    lease_ref_hash: str | None = None
    token_hash: str
    issued_at: datetime = Field(default_factory=vault_utc_now)
    expires_at: datetime
    raw_token_persisted: bool = False
    token_material_persisted: bool = False
    token_materialized: bool = False

    @model_validator(mode="after")
    def _checkout_token_is_safe(self) -> SecretCheckoutToken:
        if self.raw_token_persisted or self.token_material_persisted or self.token_materialized:
            raise ValueError("secret checkout token cannot persist or materialize raw token values")
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        payload = super().safe_model_dump()
        raw_lease_id = payload.pop("lease_id", None) or self.lease_id
        if raw_lease_id:
            payload["lease_ref_hash"] = self.lease_ref_hash or stable_hash(raw_lease_id)
        return payload


class SecretCheckoutResult(CredentialVaultDataModel):
    checkout_result_id: str = Field(default_factory=lambda: new_id("secret_checkout_result"))
    mission_id: str
    lease_id: str | None = None
    lease_ref_hash: str | None = None
    secret_handle: SecretHandle
    checkout_token: SecretCheckoutToken
    consumer: CredentialConsumerRef
    status: str = "checked_out"
    raw_secret_materialized: bool = False
    secret_material_materialized: bool = False
    secret_value: str | None = None
    result_hash: str = ""

    @model_validator(mode="after")
    def _checkout_is_handle_only(self) -> SecretCheckoutResult:
        if self.raw_secret_materialized or self.secret_material_materialized or self.secret_value is not None:
            raise ValueError("secret checkout result cannot contain raw secret material")
        return self

    def with_hash(self) -> SecretCheckoutResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        payload = super().safe_model_dump()
        raw_lease_id = payload.pop("lease_id", None) or self.lease_id
        if raw_lease_id:
            payload["lease_ref_hash"] = self.lease_ref_hash or stable_hash(raw_lease_id)
        if isinstance(payload.get("checkout_token"), dict):
            token = dict(payload["checkout_token"])
            token_raw_lease_id = token.pop("lease_id", None)
            if token_raw_lease_id:
                token["lease_ref_hash"] = token.get("lease_ref_hash") or stable_hash(token_raw_lease_id)
            payload["checkout_token"] = token
        return payload


class SecretFinalGateCertificate(CredentialVaultDataModel):
    certificate_id: str = Field(default_factory=lambda: new_id("secret_finalgate"))
    mission_id: str
    secret_id: str | None = None
    decision: SecretFinalGateDecision
    passed: bool
    receipt_ref: str | None = None
    receipt_hash: str | None = None
    safe_summary: str
    certificate_hash: str = ""

    @model_validator(mode="after")
    def _certificate_is_safe(self) -> SecretFinalGateCertificate:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> SecretFinalGateCertificate:
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})


class SecretUseReceipt(CredentialVaultDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("secret_receipt"))
    mission_id: str
    secret_id: str
    secret_kind: SecretKind
    consumer: CredentialConsumerRef
    purpose: str
    scope_hash: str
    grant_id: str | None = None
    lease_id: str | None = None
    lease_ref_hash: str | None = None
    checkout_token_id: str | None = None
    expiry: datetime | None = None
    revocation_status: str = "active"
    policy_hash: str | None = None
    approval_ref: str | None = None
    telemetry_refs: list[str] = Field(default_factory=list)
    status: str
    secret_accessed: bool = False
    receipt_hash: str = ""
    finalgate_certificate: SecretFinalGateCertificate | None = None

    @model_validator(mode="after")
    def _receipt_is_secret_free(self) -> SecretUseReceipt:
        if self.secret_accessed:
            raise ValueError("secret use receipt cannot record raw secret access")
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        return self

    def with_hash(self) -> SecretUseReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        payload["finalgate_certificate"] = None
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["receipt_hash"]
        payload["receipt_hash"] = ""
        payload["finalgate_certificate"] = None
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        payload = super().safe_model_dump()
        raw_lease_id = payload.pop("lease_id", None) or self.lease_id
        if raw_lease_id:
            payload["lease_ref_hash"] = self.lease_ref_hash or stable_hash(raw_lease_id)
        return payload


class SecretRedactionResult(CredentialVaultDataModel):
    redacted: Any
    redaction_hit: bool = False
    redaction_paths: list[str] = Field(default_factory=list)


class SecretLeakScanResult(CredentialVaultDataModel):
    scan_id: str = Field(default_factory=lambda: new_id("secret_leak_scan"))
    mission_id: str
    findings: list[str] = Field(default_factory=list)
    payload_hash: str
    raw_secret_persisted: bool = False
    secret_material_persisted: bool = False
    scan_hash: str = ""

    def with_hash(self) -> SecretLeakScanResult:
        payload = self.safe_model_dump()
        payload["scan_hash"] = ""
        return self.model_copy(update={"scan_hash": stable_hash(payload)})


class SecretAuditRecord(CredentialVaultDataModel):
    audit_id: str = Field(default_factory=lambda: new_id("secret_audit"))
    mission_id: str
    event_type: str
    safe_summary: str
    refs: list[str] = Field(default_factory=list)
    audit_hash: str = ""


class SecretTelemetrySummary(CredentialVaultDataModel):
    mission_id: str
    event_count: int = 0
    metric_count: int = 0
    secret_count: int = 0
    leak_findings_count: int = 0


class SecretReplayView(CredentialVaultDataModel):
    mission_id: str
    configs: list[CredentialVaultConfig] = Field(default_factory=list)
    secret_metadata: list[SecretMetadata] = Field(default_factory=list)
    unlock_sessions: list[VaultUnlockSession] = Field(default_factory=list)
    grants: list[SecretAccessGrant] = Field(default_factory=list)
    leases: list[SecretAccessLease] = Field(default_factory=list)
    checkout_results: list[SecretCheckoutResult] = Field(default_factory=list)
    use_receipts: list[SecretUseReceipt] = Field(default_factory=list)
    revocations: list[SecretRevocationRecord] = Field(default_factory=list)
    leak_scans: list[SecretLeakScanResult] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    materialized_secret: bool = False
    unlocked_vault: bool = False
    called_os_keychain: bool = False
    called_provider_api: bool = False
    replayed_login: bool = False
    sent_channel_message: bool = False
    filled_desktop_field: bool = False
    invoked_model_provider: bool = False


HIGH_RISK_SECRET_KINDS = {
    SecretKind.PAYMENT_METHOD_REF,
    SecretKind.TRADING_API_KEY_REF,
    SecretKind.DEVICE_PAIRING_SECRET,
}


def build_material_envelope(secret_material: str | None, *, maturity: CredentialVaultMaturity) -> SecretMaterialEnvelope:
    if secret_material is None:
        payload_hash = stable_hash({"metadata_only": True})
    else:
        payload_hash = stable_hash(secret_material)
    return SecretMaterialEnvelope(
        storage_maturity=maturity,
        sealed_payload_hash=payload_hash,
        fake_sealed_ref=f"fake_sealed_ref:{payload_hash}",
        raw_secret_persisted=False,
        encrypted=False,
        materialized=False,
    ).with_hash()


def build_secret_metadata(
    *,
    vault_id: str,
    mission_id: str,
    kind: SecretKind,
    label: str,
    sensitivity: SecretSensitivity,
    provenance: str,
    scope_policy: CredentialScopePolicy,
    use_policy: SecretUsePolicy,
    material_envelope: SecretMaterialEnvelope,
    expires_at: datetime | None = None,
) -> SecretMetadata:
    secret_id = new_id("secret")
    secret_ref = SecretRef(secret_id=secret_id, kind=kind, label=label).with_hash()
    scope_hash = stable_hash(scope_policy.safe_model_dump())
    handle = SecretHandle(
        secret_id=secret_id,
        secret_ref_id=secret_ref.secret_ref_id,
        kind=kind,
        redacted_label=secret_ref.redacted_label,
        scope_hash=scope_hash,
    ).with_hash()
    return SecretMetadata(
        secret_id=secret_id,
        vault_id=vault_id,
        mission_id=mission_id,
        kind=kind,
        label=label,
        sensitivity=sensitivity,
        provenance=SecretProvenance(source=provenance),
        version=SecretVersion(expires_at=expires_at).with_hash(),
        scope_policy=scope_policy.with_hash(),
        use_policy=use_policy.with_hash(),
        material_envelope=material_envelope,
        secret_ref=secret_ref,
        secret_handle=handle,
        expiry_policy=SecretExpiryPolicy(expires_at=expires_at),
    ).with_hash()


def scan_payload_for_secret_leaks(payload: Any, *, mission_id: str) -> SecretLeakScanResult:
    rendered = repr(redact_operator_value(payload))
    categorized = scan_forbidden_payload_categorized(payload)
    findings = [
        f"redacted:{stable_hash(path)}"
        for path in categorized[OrganSafetyScanCategory.SECRET.value]
    ]
    if isinstance(payload, str):
        findings.extend(f"redacted:{stable_hash(path)}" for path in scan_secret_like_text(payload))
    return SecretLeakScanResult(
        mission_id=mission_id,
        findings=list(dict.fromkeys(findings)),
        payload_hash=stable_hash(rendered),
        raw_secret_persisted=False,
    ).with_hash()


def _reject_raw_secret_payload(payload: Any, *, context: str) -> None:
    scan = scan_forbidden_payload_categorized(payload, path="$")
    blocked = [
        *scan[OrganSafetyScanCategory.SECRET.value],
        *scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value],
    ]
    if blocked:
        raise ValueError(f"{context}: raw secret or provider override blocked")
    reject_operator_control_payload(payload, context=context)


def _safe_identifier(value: str, label: str) -> str:
    cleaned = value.strip().lower().replace(" ", "_")
    if not cleaned:
        raise ValueError(f"{label} is required")
    return redact_operator_text(cleaned)


def _safe_secret_key_names(value: Any) -> Any:
    if isinstance(value, dict):
        renamed: dict[str, Any] = {}
        for key, item in value.items():
            if key == "durable_raw_secret_persistence":
                renamed["durable_secret_material_persistence"] = _safe_secret_key_names(item)
                continue
            if key == "raw_secret_persisted":
                renamed["secret_material_persisted"] = _safe_secret_key_names(item)
                continue
            if key == "raw_secret_materialized":
                renamed["secret_material_materialized"] = _safe_secret_key_names(item)
                continue
            if key == "raw_token_persisted":
                renamed["token_material_persisted"] = _safe_secret_key_names(item)
                continue
            if key == "secret_value" and item is None:
                continue
            renamed[key] = _safe_secret_key_names(item)
        return renamed
    if isinstance(value, list):
        return [_safe_secret_key_names(item) for item in value]
    return value
