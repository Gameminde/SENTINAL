from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import scan_forbidden_payload_categorized


def account_utc_now() -> datetime:
    return datetime.now(UTC)


class AccountAuthorityDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _account_data_is_not_authority(self) -> AccountAuthorityDataModel:
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return _safe_account_key_names(redact_operator_value(self.model_dump(mode="json")))


class AccountAuthorityMode(StrEnum):
    DISABLED = "disabled"
    PLAN_ONLY = "plan_only"
    SANDBOX_ONLY = "sandbox_only"
    OPERATOR_ASSISTED_LOGIN = "operator_assisted_login"
    OPERATOR_ASSISTED_ACCOUNT_CREATION = "operator_assisted_account_creation"
    DELEGATED_LOGIN_SESSION = "delegated_login_session"
    DELEGATED_ACCOUNT_CREATION_SESSION = "delegated_account_creation_session"


class AccountFlowKind(StrEnum):
    LOGIN = "login"
    ACCOUNT_CREATION = "account_creation"
    OAUTH = "oauth"
    OIDC = "oidc"
    WEB_AUTHN_PASSKEY = "web_authn_passkey"


class AccountProviderKind(StrEnum):
    SANDBOX = "sandbox"
    FAKE_INJECTED = "fake_injected"
    OAUTH_DESCRIPTOR = "oauth_descriptor"
    OIDC_DESCRIPTOR = "oidc_descriptor"
    PUBLIC_SITE_DESCRIPTOR = "public_site_descriptor"
    ENTERPRISE_SSO_DESCRIPTOR = "enterprise_sso_descriptor"


class AccountSurfaceKind(StrEnum):
    BROWSER = "browser"
    DESKTOP = "desktop"
    VOICE = "voice"
    CHANNEL = "channel"
    API_DESCRIPTOR = "api_descriptor"


class AccountPlanStatus(StrEnum):
    READY = "ready"
    CHECKPOINT_REQUIRED = "checkpoint_required"
    BLOCKED = "blocked"
    EXECUTED = "executed"
    FAILED = "failed"


class AccountSessionState(StrEnum):
    PLANNED = "planned"
    BOUND = "bound"
    ACTIVE = "active"
    CHECKPOINT_REQUIRED = "checkpoint_required"
    REVOKED = "revoked"
    FAILED = "failed"


class AccountAuthorityFinalGateDecision(StrEnum):
    CERTIFIED_LOGIN = "certified_login"
    CERTIFIED_ACCOUNT_CREATED = "certified_account_created"
    CERTIFIED_BLOCKED = "certified_blocked"
    REJECTED_UNSAFE_RECEIPT = "rejected_unsafe_receipt"


class AccountAuthorityConfig(AccountAuthorityDataModel):
    config_id: str = Field(default_factory=lambda: new_id("account_auth_config"))
    default_mode: AccountAuthorityMode = AccountAuthorityMode.PLAN_ONLY
    allowed_modes: list[AccountAuthorityMode] = Field(default_factory=lambda: [AccountAuthorityMode.PLAN_ONLY])
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_services: list[str] = Field(default_factory=list)
    allowed_surfaces: list[AccountSurfaceKind] = Field(default_factory=list)
    sandbox_accounts_allowed: bool = False
    disposable_accounts_allowed: bool = False
    live_public_site_calls_allowed: bool = False
    account_farming_allowed: bool = False
    credential_stuffing_allowed: bool = False
    captcha_bypass_allowed: bool = False
    mfa_bypass_allowed: bool = False
    kyc_bypass_allowed: bool = False
    raw_session_cookie_capture_allowed: bool = False
    provider_token_exchange_live_allowed: bool = False
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_bounded(self) -> AccountAuthorityConfig:
        if self.default_mode not in set(self.allowed_modes):
            raise ValueError("account_authority_default_mode_not_allowed")
        if not self.allowed_domains:
            raise ValueError("account_authority_allowed_domain_required")
        if not self.allowed_surfaces:
            raise ValueError("account_authority_allowed_surface_required")
        if any(
            [
                self.account_farming_allowed,
                self.credential_stuffing_allowed,
                self.captcha_bypass_allowed,
                self.mfa_bypass_allowed,
                self.kyc_bypass_allowed,
                self.raw_session_cookie_capture_allowed,
            ]
        ):
            raise ValueError("account_authority_abuse_or_secret_capture_not_allowed")
        if self.live_public_site_calls_allowed or self.provider_token_exchange_live_allowed:
            raise ValueError("account_authority_v1_live_provider_calls_not_allowed")
        self.allowed_domains = sorted({_safe_domain(domain) for domain in self.allowed_domains if domain.strip()})
        self.allowed_services = sorted({redact_operator_text(service.strip()) for service in self.allowed_services if service.strip()})
        return self

    def with_hash(self) -> AccountAuthorityConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class AccountAuthorityPolicy(AccountAuthorityDataModel):
    mission_scoped: bool = True
    operator_approval_required: bool = True
    credential_vault_required: bool = True
    checkpoint_for_mfa: bool = True
    checkpoint_for_captcha: bool = True
    checkpoint_for_kyc: bool = True
    checkpoint_for_passkey: bool = True
    live_public_site_execution_allowed: bool = False
    policy_hash: str = ""

    def with_hash(self) -> AccountAuthorityPolicy:
        payload = self.safe_model_dump()
        payload["policy_hash"] = ""
        return self.model_copy(update={"policy_hash": stable_hash(payload)})


class AccountIdentityRef(AccountAuthorityDataModel):
    identity_ref: str
    operator_owned: bool = True
    identity_ref_hash: str = ""

    def with_hash(self) -> AccountIdentityRef:
        payload = self.safe_model_dump()
        payload["identity_ref_hash"] = ""
        return self.model_copy(update={"identity_ref_hash": stable_hash(payload)})


class AccountProfileRef(AccountAuthorityDataModel):
    profile_ref: str
    profile_ref_hash: str = ""

    def with_hash(self) -> AccountProfileRef:
        payload = self.safe_model_dump()
        payload["profile_ref_hash"] = ""
        return self.model_copy(update={"profile_ref_hash": stable_hash(payload)})


class AccountSessionRef(AccountAuthorityDataModel):
    session_ref: str = Field(default_factory=lambda: new_id("account_session"))
    service_hash: str
    target_domain: str
    session_hash: str = ""

    def with_hash(self) -> AccountSessionRef:
        payload = self.safe_model_dump()
        payload["session_hash"] = ""
        return self.model_copy(update={"session_hash": stable_hash(payload)})


class AccountSessionPolicy(AccountAuthorityDataModel):
    session_scope: list[str] = Field(default_factory=list)
    credential_material_in_session: bool = False
    cookie_capture_allowed: bool = False
    persist_live_session_allowed: bool = False

    @model_validator(mode="after")
    def _session_policy_is_safe(self) -> AccountSessionPolicy:
        if self.credential_material_in_session or self.cookie_capture_allowed or self.persist_live_session_allowed:
            raise ValueError("account_session_policy_blocks_credential_or_cookie_persistence")
        self.session_scope = sanitize_operator_refs(self.session_scope)
        return self


class AccountSessionBinding(AccountAuthorityDataModel):
    binding_id: str = Field(default_factory=lambda: new_id("account_session_binding"))
    mission_id: str
    session_ref: str
    state: AccountSessionState = AccountSessionState.BOUND
    service_hash: str
    provider_kind: AccountProviderKind
    target_domain: str
    credential_lease_ref_hash: str | None = None
    receipt_ref: str | None = None
    finalgate_ref: str | None = None
    created_at: datetime = Field(default_factory=account_utc_now)
    binding_hash: str = ""

    def with_hash(self) -> AccountSessionBinding:
        payload = self.safe_model_dump()
        payload["binding_hash"] = ""
        return self.model_copy(update={"binding_hash": stable_hash(payload)})


class LoginCredentialRequirement(AccountAuthorityDataModel):
    requires_credential: bool = True
    accepted_secret_kinds: list[str] = Field(default_factory=lambda: ["username_password"])
    final_consumer_kind: str = "browser_login"
    final_consumer_ref: str = "account_authority_final_consumer"
    credential_lease_required: bool = True


class CredentialLeaseBinding(AccountAuthorityDataModel):
    binding_id: str = Field(default_factory=lambda: new_id("credential_lease_binding"))
    mission_id: str
    lease_id: str
    lease_ref_hash: str
    consumer_kind: str
    consumer_ref: str
    checkout_result_ref: str | None = None
    secret_use_receipt_ref: str | None = None
    binding_hash: str = ""

    def with_hash(self) -> CredentialLeaseBinding:
        payload = self.safe_model_dump()
        payload["binding_hash"] = ""
        return self.model_copy(update={"binding_hash": stable_hash(payload)})


class CredentialFieldBinding(AccountAuthorityDataModel):
    field_role: str
    credential_binding_ref: str
    target_ref_hash: str


class CredentialFillPolicy(AccountAuthorityDataModel):
    final_consumer_only: bool = True
    reveal_to_llm: bool = False
    reveal_to_memory: bool = False
    reveal_to_telemetry: bool = False
    reveal_to_replay: bool = False

    @model_validator(mode="after")
    def _no_reveal(self) -> CredentialFillPolicy:
        if not self.final_consumer_only or self.reveal_to_llm or self.reveal_to_memory or self.reveal_to_telemetry or self.reveal_to_replay:
            raise ValueError("credential fill policy forbids non-consumer reveal")
        return self


class CredentialRevealPolicy(CredentialFillPolicy):
    pass


class PKCEStateDescriptor(AccountAuthorityDataModel):
    code_challenge_ref: str
    code_verifier_ref_hash: str
    method: str = "S256"


class OAuthFlowDescriptor(AccountAuthorityDataModel):
    provider_hash: str
    redirect_uri_ref: str
    state_ref: str
    nonce_ref: str | None = None
    pkce: PKCEStateDescriptor | None = None
    consent_checkpoint_required: bool = True
    token_exchange_live: bool = False
    access_token_persisted: bool = False
    refresh_token_persisted: bool = False

    @model_validator(mode="after")
    def _oauth_is_descriptor_only(self) -> OAuthFlowDescriptor:
        if self.token_exchange_live or self.access_token_persisted or self.refresh_token_persisted:
            raise ValueError("oauth v1 is descriptor-only and cannot persist tokens")
        return self


class OAuthConsentDescriptor(AccountAuthorityDataModel):
    consent_checkpoint_required: bool = True
    requested_scope_hashes: list[str] = Field(default_factory=list)


class OAuthRedirectDescriptor(AccountAuthorityDataModel):
    redirect_uri_ref: str
    redirect_domain: str
    state_ref: str


class OIDCIdentityDescriptor(AccountAuthorityDataModel):
    issuer_hash: str
    subject_ref_hash: str | None = None
    nonce_ref: str


class UserPresenceRequirement(StrEnum):
    REQUIRED = "required"
    DISCOURAGED = "discouraged"


class UserVerificationRequirement(StrEnum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    DISCOURAGED = "discouraged"


class WebAuthnPasskeyDescriptor(AccountAuthorityDataModel):
    credential_id_hash: str | None = None
    user_presence: UserPresenceRequirement = UserPresenceRequirement.REQUIRED
    user_verification: UserVerificationRequirement = UserVerificationRequirement.REQUIRED
    private_key_extractable: bool = False
    bypass_allowed: bool = False

    @model_validator(mode="after")
    def _passkey_requires_human(self) -> WebAuthnPasskeyDescriptor:
        if self.private_key_extractable or self.bypass_allowed:
            raise ValueError("passkey bypass or private key extraction is blocked")
        return self


class MFADescriptor(AccountAuthorityDataModel):
    factor_kind: str = "authenticator_app"
    checkpoint_required: bool = True
    bypass_allowed: bool = False


class OTPDescriptor(MFADescriptor):
    factor_kind: str = "otp"


class EmailVerificationDescriptor(MFADescriptor):
    factor_kind: str = "email_verification"


class PhoneVerificationDescriptor(MFADescriptor):
    factor_kind: str = "phone_verification"


class CaptchaChallengeDescriptor(AccountAuthorityDataModel):
    challenge_hash: str | None = None
    checkpoint_required: bool = True
    bypass_allowed: bool = False


class KYCChallengeDescriptor(CaptchaChallengeDescriptor):
    pass


class HumanCheckpoint(AccountAuthorityDataModel):
    checkpoint_id: str = Field(default_factory=lambda: new_id("account_checkpoint"))
    mission_id: str
    reason: str
    checkpoint_kind: str
    operator_required: bool = True
    bypass_allowed: bool = False
    safe_summary: str = "Human checkpoint required."
    checkpoint_hash: str = ""

    @model_validator(mode="after")
    def _checkpoint_is_human(self) -> HumanCheckpoint:
        if not self.operator_required or self.bypass_allowed:
            raise ValueError("human checkpoint cannot allow bypass")
        self.reason = redact_operator_text(self.reason)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> HumanCheckpoint:
        payload = self.safe_model_dump()
        payload["checkpoint_hash"] = ""
        return self.model_copy(update={"checkpoint_hash": stable_hash(payload)})


class AccountCreationFieldPolicy(AccountAuthorityDataModel):
    allow_raw_password_field: bool = False
    allow_unverified_identity_fields: bool = False
    require_hash_only_field_plan: bool = True


class AccountIdentityTruthPolicy(AccountAuthorityDataModel):
    operator_owned_profile_required: bool = True
    fake_identity_allowed: bool = False
    kyc_bypass_allowed: bool = False
    age_misrepresentation_allowed: bool = False

    @model_validator(mode="after")
    def _truth_policy_blocks_false_identity(self) -> AccountIdentityTruthPolicy:
        if self.fake_identity_allowed or self.kyc_bypass_allowed or self.age_misrepresentation_allowed:
            raise ValueError("account identity truth policy blocks fake identity and KYC bypass")
        return self


class DisposableAccountPolicy(AccountAuthorityDataModel):
    disposable_allowed: bool = False
    operator_owned_required: bool = True
    abuse_or_ban_evasion_allowed: bool = False


class SandboxAccountPolicy(AccountAuthorityDataModel):
    sandbox_allowed: bool = False
    public_site_farming_allowed: bool = False


class TermsAndPolicyAcknowledgement(AccountAuthorityDataModel):
    terms_ack_ref: str
    operator_acknowledged: bool = True
    acknowledgement_hash: str = ""

    def with_hash(self) -> TermsAndPolicyAcknowledgement:
        payload = self.safe_model_dump()
        payload["acknowledgement_hash"] = ""
        return self.model_copy(update={"acknowledgement_hash": stable_hash(payload)})


class AccountFlowSafetyScanResult(AccountAuthorityDataModel):
    valid: bool = True
    reasons: list[str] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    scan_hash: str = ""

    def with_hash(self) -> AccountFlowSafetyScanResult:
        payload = self.safe_model_dump()
        payload["scan_hash"] = ""
        return self.model_copy(update={"scan_hash": stable_hash(payload)})


class AccountFlowRiskProfile(AccountAuthorityDataModel):
    risk_lane: str = "special_authority"
    requires_operator_checkpoint: bool = False
    risk_reasons: list[str] = Field(default_factory=list)


class AccountFlowApproval(AccountAuthorityDataModel):
    approval_ref: str
    source: str = "operator"
    approved: bool = True

    @model_validator(mode="after")
    def _approval_source_is_operator(self) -> AccountFlowApproval:
        if self.source not in {"operator", "operator_policy", "manual_operator"}:
            raise ValueError("account flow approval must be operator-originated")
        return self


class AccountFlowCheckpoint(HumanCheckpoint):
    pass


class AccountFlowIdempotencyKey(AccountAuthorityDataModel):
    key_id: str = Field(default_factory=lambda: new_id("account_idempotency"))
    mission_id: str
    flow_kind: AccountFlowKind
    target_hash: str
    key_hash: str = ""

    def with_hash(self) -> AccountFlowIdempotencyKey:
        payload = self.safe_model_dump()
        payload["key_hash"] = ""
        return self.model_copy(update={"key_hash": stable_hash(payload)})


class AccountLoginRequest(AccountAuthorityDataModel):
    request_id: str = Field(default_factory=lambda: new_id("account_login_request"))
    target_url: str
    service_name: str
    provider_kind: AccountProviderKind = AccountProviderKind.SANDBOX
    surface_kind: AccountSurfaceKind = AccountSurfaceKind.BROWSER
    credential_lease_id: str | None = None
    target_evidence_refs: list[str] = Field(default_factory=list)
    boundary_descriptors: list[str] = Field(default_factory=list)
    operator_note: str | None = None

    @model_validator(mode="after")
    def _login_request_is_safe(self) -> AccountLoginRequest:
        self.service_name = redact_operator_text(self.service_name)
        self.operator_note = redact_operator_text(self.operator_note) if self.operator_note else None
        self.target_evidence_refs = sanitize_operator_refs(self.target_evidence_refs)
        self.boundary_descriptors = [_safe_identifier(item, "boundary") for item in self.boundary_descriptors]
        return self


class AccountLoginStep(AccountAuthorityDataModel):
    step_id: str = Field(default_factory=lambda: new_id("account_login_step"))
    action: str
    target_ref_hash: str | None = None
    checkpoint_required: bool = False


class AccountLoginPlan(AccountAuthorityDataModel):
    plan_id: str = Field(default_factory=lambda: new_id("account_login_plan"))
    mission_id: str
    request_id: str
    config_id: str
    status: AccountPlanStatus = AccountPlanStatus.READY
    target_domain: str
    target_url_hash: str
    service_hash: str
    provider_kind: AccountProviderKind
    surface_kind: AccountSurfaceKind
    credential_requirement: LoginCredentialRequirement | None = None
    credential_lease_ref: str | None = None
    credential_lease_ref_hash: str | None = None
    steps: list[AccountLoginStep] = Field(default_factory=list)
    checkpoints: list[HumanCheckpoint] = Field(default_factory=list)
    safety_scan: AccountFlowSafetyScanResult = Field(default_factory=AccountFlowSafetyScanResult)
    idempotency_key: AccountFlowIdempotencyKey | None = None
    plan_hash: str = ""

    def with_hash(self) -> AccountLoginPlan:
        payload = self.safe_model_dump()
        payload["plan_hash"] = ""
        return self.model_copy(update={"plan_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["plan_hash"]
        payload["plan_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class AccountLoginReceipt(AccountAuthorityDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("account_login_receipt"))
    mission_id: str
    plan_id: str
    status: AccountPlanStatus
    target_domain: str
    target_url_hash: str
    service_hash: str
    provider_kind: AccountProviderKind
    session_ref: str | None = None
    credential_lease_ref_hash: str | None = None
    secret_use_receipt_ref: str | None = None
    checkout_result_ref: str | None = None
    checkpoint_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    raw_credential_persisted: bool = False
    raw_token_persisted: bool = False
    raw_session_cookie_persisted: bool = False
    safe_summary: str = "Account login receipt metadata only."
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _receipt_is_safe(self) -> AccountLoginReceipt:
        if self.raw_credential_persisted or self.raw_token_persisted or self.raw_session_cookie_persisted:
            raise ValueError("account login receipt cannot persist credential, token, or session cookie material")
        self.checkpoint_refs = sanitize_operator_refs(self.checkpoint_refs)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> AccountLoginReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})


class AccountLoginResult(AccountAuthorityDataModel):
    accepted: bool
    status: AccountPlanStatus
    reason: str
    mission_id: str
    receipt: AccountLoginReceipt
    session_binding: AccountSessionBinding
    finalgate_certificate: AccountAuthorityFinalGateCertificate | None = None


class AccountCreationRequest(AccountAuthorityDataModel):
    request_id: str = Field(default_factory=lambda: new_id("account_creation_request"))
    target_url: str
    service_name: str
    provider_kind: AccountProviderKind = AccountProviderKind.SANDBOX
    surface_kind: AccountSurfaceKind = AccountSurfaceKind.BROWSER
    operator_approval_ref: str | None = None
    identity_profile_ref: str | None = None
    terms_ack_ref: str | None = None
    operator_owned_profile_authorized: bool = False
    sandbox_account: bool = False
    disposable_account: bool = False
    before_evidence_refs: list[str] = Field(default_factory=list)
    operator_note: str | None = None

    @model_validator(mode="after")
    def _creation_request_is_safe(self) -> AccountCreationRequest:
        self.service_name = redact_operator_text(self.service_name)
        self.operator_note = redact_operator_text(self.operator_note) if self.operator_note else None
        self.before_evidence_refs = sanitize_operator_refs(self.before_evidence_refs)
        return self


class AccountCreationStep(AccountAuthorityDataModel):
    step_id: str = Field(default_factory=lambda: new_id("account_creation_step"))
    action: str
    field_plan_hash: str | None = None
    checkpoint_required: bool = False


class AccountCreationPlan(AccountAuthorityDataModel):
    plan_id: str = Field(default_factory=lambda: new_id("account_creation_plan"))
    mission_id: str
    request_id: str
    config_id: str
    status: AccountPlanStatus = AccountPlanStatus.READY
    target_domain: str
    target_url_hash: str
    service_hash: str
    provider_kind: AccountProviderKind
    surface_kind: AccountSurfaceKind
    identity_truth_policy: AccountIdentityTruthPolicy = Field(default_factory=AccountIdentityTruthPolicy)
    field_policy: AccountCreationFieldPolicy = Field(default_factory=AccountCreationFieldPolicy)
    sandbox_policy: SandboxAccountPolicy = Field(default_factory=SandboxAccountPolicy)
    disposable_policy: DisposableAccountPolicy = Field(default_factory=DisposableAccountPolicy)
    terms_ack_ref: str | None = None
    identity_profile_ref_hash: str | None = None
    operator_approval_ref: str | None = None
    steps: list[AccountCreationStep] = Field(default_factory=list)
    checkpoints: list[HumanCheckpoint] = Field(default_factory=list)
    safety_scan: AccountFlowSafetyScanResult = Field(default_factory=AccountFlowSafetyScanResult)
    idempotency_key: AccountFlowIdempotencyKey | None = None
    plan_hash: str = ""

    def with_hash(self) -> AccountCreationPlan:
        payload = self.safe_model_dump()
        payload["plan_hash"] = ""
        return self.model_copy(update={"plan_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["plan_hash"]
        payload["plan_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class AccountCreationReceipt(AccountAuthorityDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("account_creation_receipt"))
    mission_id: str
    plan_id: str
    status: AccountPlanStatus
    target_domain: str
    target_url_hash: str
    service_hash: str
    provider_kind: AccountProviderKind
    session_ref: str | None = None
    identity_profile_ref_hash: str | None = None
    terms_ack_ref: str | None = None
    operator_approval_ref: str | None = None
    checkpoint_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    account_creation_hash: str | None = None
    live_public_site_called: bool = False
    raw_credential_persisted: bool = False
    raw_token_persisted: bool = False
    safe_summary: str = "Account creation receipt metadata only."
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _creation_receipt_is_safe(self) -> AccountCreationReceipt:
        if self.live_public_site_called or self.raw_credential_persisted or self.raw_token_persisted:
            raise ValueError("account creation receipt cannot claim live public-site call or persist sensitive material")
        self.checkpoint_refs = sanitize_operator_refs(self.checkpoint_refs)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> AccountCreationReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})


class AccountCreationResult(AccountAuthorityDataModel):
    accepted: bool
    status: AccountPlanStatus
    reason: str
    mission_id: str
    receipt: AccountCreationReceipt
    session_binding: AccountSessionBinding
    finalgate_certificate: AccountAuthorityFinalGateCertificate | None = None


class AccountSessionReceipt(AccountLoginReceipt):
    pass


class AccountAuthorityFinalGateCertificate(AccountAuthorityDataModel):
    certificate_id: str = Field(default_factory=lambda: new_id("account_finalgate"))
    mission_id: str
    receipt_id: str
    decision: AccountAuthorityFinalGateDecision
    certified: bool
    reasons: list[str] = Field(default_factory=list)
    receipt_hash: str
    certificate_hash: str = ""

    def with_hash(self) -> AccountAuthorityFinalGateCertificate:
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})


class AccountAuthorityReplayView(AccountAuthorityDataModel):
    mission_id: str
    configs: list[AccountAuthorityConfig] = Field(default_factory=list)
    login_plans: list[AccountLoginPlan] = Field(default_factory=list)
    account_creation_plans: list[AccountCreationPlan] = Field(default_factory=list)
    login_receipts: list[AccountLoginReceipt] = Field(default_factory=list)
    account_creation_receipts: list[AccountCreationReceipt] = Field(default_factory=list)
    session_bindings: list[AccountSessionBinding] = Field(default_factory=list)
    checkpoints: list[HumanCheckpoint] = Field(default_factory=list)
    finalgate_certificates: list[AccountAuthorityFinalGateCertificate] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    replayed_login: bool = False
    created_live_account: bool = False
    materialized_credential: bool = False
    called_provider_api: bool = False
    executed_browser_action: bool = False
    solved_captcha: bool = False
    bypassed_mfa: bool = False
    bypassed_kyc: bool = False


class AccountAuthorityTelemetrySummary(AccountAuthorityDataModel):
    mission_id: str
    event_count: int = 0
    metric_count: int = 0
    checkpoint_count: int = 0
    receipt_count: int = 0


def build_checkpoints(mission_id: str, descriptors: list[str]) -> list[HumanCheckpoint]:
    checkpoints: list[HumanCheckpoint] = []
    for descriptor in descriptors:
        normalized = _safe_identifier(descriptor, "boundary")
        if normalized in {"mfa", "authenticator", "totp"}:
            reason = "mfa_checkpoint_required"
            kind = "mfa"
        elif normalized in {"otp", "email", "email_verification", "phone", "phone_verification"}:
            reason = "otp_checkpoint_required"
            kind = "otp"
        elif normalized == "captcha":
            reason = "captcha_checkpoint_required"
            kind = "captcha"
        elif normalized == "kyc":
            reason = "kyc_checkpoint_required"
            kind = "kyc"
        elif normalized in {"passkey", "webauthn", "webauthn_passkey"}:
            reason = "passkey_user_presence_required"
            kind = "passkey"
        else:
            reason = f"{normalized}_checkpoint_required"
            kind = normalized
        checkpoints.append(
            HumanCheckpoint(
                mission_id=mission_id,
                reason=reason,
                checkpoint_kind=kind,
                safe_summary=f"Human checkpoint required for {kind}.",
            ).with_hash()
        )
    return checkpoints


def scan_account_flow_payload(payload: Any) -> AccountFlowSafetyScanResult:
    rejected = _unsafe_paths(payload)
    abuse_reasons = _abuse_reasons(payload)
    reasons = list(dict.fromkeys([*(["unsafe_account_flow_payload"] if rejected else []), *abuse_reasons]))
    return AccountFlowSafetyScanResult(
        valid=not reasons,
        reasons=reasons,
        rejected_paths=rejected,
    ).with_hash()


def _unsafe_paths(payload: Any) -> list[str]:
    scan = scan_forbidden_payload_categorized(payload, path="$")
    return sorted(set(scan["all"]))


def _abuse_reasons(payload: Any) -> list[str]:
    text = str(payload).lower()
    checks = {
        "account_farming_blocked": ["mass account", "100 fake account", "account farm", "spam account"],
        "ban_evasion_blocked": ["ban evasion", "evade ban"],
        "credential_stuffing_blocked": ["credential stuffing", "account takeover", "stolen credential"],
        "captcha_bypass_blocked": ["bypass captcha", "captcha bypass", "solve captcha"],
        "fake_identity_blocked": ["fake identity", "false identity"],
        "session_theft_blocked": ["session cookie theft", "cookie theft", "session hijack"],
        "kyc_bypass_blocked": ["kyc bypass", "bypass kyc"],
    }
    reasons: list[str] = []
    for reason, markers in checks.items():
        if any(marker in text for marker in markers):
            reasons.append(reason)
    return reasons


def _raise_if_unsafe_payload(payload: Any, reason: str) -> None:
    if _unsafe_paths(payload) or _abuse_reasons(payload):
        raise ValueError(reason)


def _safe_identifier(value: str, label: str) -> str:
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if not normalized:
        raise ValueError(f"{label}_required")
    if any(ch in normalized for ch in ("/", "\\", "..")):
        raise ValueError(f"{label}_invalid")
    return redact_operator_text(normalized)


def _safe_domain(value: str) -> str:
    normalized = str(value).strip().lower()
    if not normalized or "/" in normalized or "\\" in normalized or ".." in normalized:
        raise ValueError("account_authority_domain_invalid")
    return normalized


def _safe_account_key_names(value: Any) -> Any:
    if isinstance(value, dict):
        rendered: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = str(key)
            if safe_key in {"secret_value", "password", "provider_response", "reasoning", "raw_prompt"}:
                safe_key = f"redacted_key_{stable_hash(safe_key)[:12]}"
            rendered[safe_key] = _safe_account_key_names(item)
        return rendered
    if isinstance(value, list):
        return [_safe_account_key_names(item) for item in value]
    return value


__all__ = [
    "AccountAuthorityConfig",
    "AccountAuthorityDataModel",
    "AccountAuthorityFinalGateCertificate",
    "AccountAuthorityFinalGateDecision",
    "AccountAuthorityMode",
    "AccountAuthorityPolicy",
    "AccountAuthorityReplayView",
    "AccountAuthorityTelemetrySummary",
    "AccountCreationFieldPolicy",
    "AccountCreationPlan",
    "AccountCreationReceipt",
    "AccountCreationRequest",
    "AccountCreationResult",
    "AccountCreationStep",
    "AccountFlowApproval",
    "AccountFlowCheckpoint",
    "AccountFlowIdempotencyKey",
    "AccountFlowKind",
    "AccountFlowRiskProfile",
    "AccountFlowSafetyScanResult",
    "AccountIdentityRef",
    "AccountIdentityTruthPolicy",
    "AccountLoginPlan",
    "AccountLoginReceipt",
    "AccountLoginRequest",
    "AccountLoginResult",
    "AccountLoginStep",
    "AccountPlanStatus",
    "AccountProfileRef",
    "AccountProviderKind",
    "AccountSessionBinding",
    "AccountSessionPolicy",
    "AccountSessionReceipt",
    "AccountSessionRef",
    "AccountSessionState",
    "AccountSurfaceKind",
    "CaptchaChallengeDescriptor",
    "CredentialFieldBinding",
    "CredentialFillPolicy",
    "CredentialLeaseBinding",
    "CredentialRevealPolicy",
    "DisposableAccountPolicy",
    "EmailVerificationDescriptor",
    "HumanCheckpoint",
    "KYCChallengeDescriptor",
    "LoginCredentialRequirement",
    "MFADescriptor",
    "OAuthConsentDescriptor",
    "OAuthFlowDescriptor",
    "OAuthRedirectDescriptor",
    "OIDCIdentityDescriptor",
    "OTPDescriptor",
    "PKCEStateDescriptor",
    "PhoneVerificationDescriptor",
    "SandboxAccountPolicy",
    "TermsAndPolicyAcknowledgement",
    "UserPresenceRequirement",
    "UserVerificationRequirement",
    "WebAuthnPasskeyDescriptor",
    "account_utc_now",
    "build_checkpoints",
    "scan_account_flow_payload",
]
