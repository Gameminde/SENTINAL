from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized


def channel_utc_now() -> datetime:
    return datetime.now(UTC)


class ChannelAdapterKind(StrEnum):
    WEBHOOK = "webhook"
    SMTP_EMAIL = "smtp_email"
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"


class ChannelProviderKind(StrEnum):
    WEBHOOK = "webhook"
    SMTP = "smtp"
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    DESCRIPTOR_ONLY = "descriptor_only"


class ChannelDeliveryStatus(StrEnum):
    DRAFT_CREATED = "draft_created"
    SENT = "sent"
    BLOCKED = "blocked"
    FAILED = "failed"


class ChannelDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _channel_data_is_not_authority(self) -> ChannelDataModel:
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return redact_operator_value(self.model_dump(mode="json"))


class ChannelCapabilityProfile(ChannelDataModel):
    supports_inbound: bool = False
    supports_outbound: bool = True
    supports_threads: bool = True
    supports_attachments: bool = False
    live_send_opt_in: bool = True
    safe_summary: str = "Channel adapter capability descriptor."

    @model_validator(mode="after")
    def _sanitize_summary(self) -> ChannelCapabilityProfile:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self


class ChannelRecipientPolicy(ChannelDataModel):
    allowed_recipients: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_recipients: list[str] = Field(default_factory=list)
    max_recipients: int = Field(default=1, ge=0)
    require_recipient_provenance: bool = True

    @model_validator(mode="after")
    def _normalize_policy(self) -> ChannelRecipientPolicy:
        self.allowed_recipients = [_normalize_recipient(item) for item in self.allowed_recipients]
        self.allowed_domains = [item.strip().lower() for item in self.allowed_domains if item.strip()]
        self.blocked_recipients = [_normalize_recipient(item) for item in self.blocked_recipients]
        return self


class ChannelScopePolicy(ChannelDataModel):
    allowed_channels: list[str] = Field(default_factory=lambda: ["webhook"])
    allowed_threads: list[str] = Field(default_factory=list)
    allowed_objective_tags: list[str] = Field(default_factory=list)
    allow_external_mutation: bool = False

    @model_validator(mode="after")
    def _normalize_scope(self) -> ChannelScopePolicy:
        self.allowed_channels = [item.strip().lower() for item in self.allowed_channels if item.strip()]
        self.allowed_threads = [redact_operator_text(item) for item in self.allowed_threads]
        self.allowed_objective_tags = [redact_operator_text(item) for item in self.allowed_objective_tags]
        if self.allow_external_mutation:
            raise ValueError("channel scope policy cannot allow unbounded external mutation")
        return self


class ChannelRateLimitPolicy(ChannelDataModel):
    max_recipients_per_window: int = Field(default=10, ge=0)
    window_seconds: int = Field(default=3600, ge=1)


class ChannelApprovalPolicy(ChannelDataModel):
    approval_required_for_send: bool = True
    allowed_approval_sources: list[str] = Field(default_factory=lambda: ["operator", "operator_policy", "manual_operator"])

    @model_validator(mode="after")
    def _approval_sources_are_operator(self) -> ChannelApprovalPolicy:
        allowed = {"operator", "operator_policy", "manual_operator"}
        self.allowed_approval_sources = [source for source in self.allowed_approval_sources if source in allowed]
        if not self.allowed_approval_sources:
            raise ValueError("channel approval policy requires an operator approval source")
        return self


class ChannelAdapterConfig(ChannelDataModel):
    adapter_id: str
    kind: ChannelAdapterKind
    provider_kind: ChannelProviderKind
    display_name: str
    capability_profile: ChannelCapabilityProfile = Field(default_factory=ChannelCapabilityProfile)
    recipient_policy: ChannelRecipientPolicy = Field(default_factory=ChannelRecipientPolicy)
    scope_policy: ChannelScopePolicy = Field(default_factory=ChannelScopePolicy)
    rate_limit_policy: ChannelRateLimitPolicy = Field(default_factory=ChannelRateLimitPolicy)
    approval_policy: ChannelApprovalPolicy = Field(default_factory=ChannelApprovalPolicy)
    identity_ref: str | None = None
    session_ref: str | None = None
    endpoint_ref_hash: str | None = None
    credential_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=channel_utc_now)
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_safe(self) -> ChannelAdapterConfig:
        self.display_name = redact_operator_text(self.display_name)
        self.metadata = _sanitize_channel_payload(self.metadata, context="channel_adapter_config")
        if self.credential_ref and _looks_like_raw_secret(self.credential_ref):
            raise ValueError("channel adapter credential_ref must be a metadata ref, not a credential value")
        if not self.adapter_id.strip():
            raise ValueError("channel adapter id is required")
        return self

    def with_hash(self) -> ChannelAdapterConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelIdentityRef(ChannelDataModel):
    identity_ref: str = Field(default_factory=lambda: new_id("channel_identity"))
    adapter_id: str
    external_sender_hash: str
    verified: bool = False
    binding_source: str = "untrusted_inbound"
    safe_summary: str = "Inbound identity bound as untrusted data."


class ChannelAttachmentRef(ChannelDataModel):
    attachment_id: str = Field(default_factory=lambda: new_id("channel_attachment"))
    filename: str
    content_sha256: str
    size_bytes: int = Field(ge=0)
    content_type: str | None = None

    @model_validator(mode="after")
    def _attachment_is_metadata_only(self) -> ChannelAttachmentRef:
        self.filename = redact_operator_text(self.filename)
        if len(self.content_sha256) < 32:
            raise ValueError("channel attachment requires a content hash")
        return self


class ChannelAttachmentQuarantine(ChannelDataModel):
    quarantine_id: str = Field(default_factory=lambda: new_id("channel_attachment_quarantine"))
    attachment_id: str
    content_sha256: str
    safe_reason: str = "Attachment quarantined pending explicit review."


class ChannelLinkQuarantine(ChannelDataModel):
    quarantine_id: str = Field(default_factory=lambda: new_id("channel_link_quarantine"))
    link_hash: str
    safe_reason: str = "Inbound link quarantined pending explicit review."


class ChannelInboundEnvelope(ChannelDataModel):
    adapter_id: str
    channel: str
    external_message_id: str
    sender_ref: str
    thread_ref: str | None = None
    subject: str | None = None
    text: str = Field(default="", exclude=True, repr=False)
    attachment_refs: list[ChannelAttachmentRef] = Field(default_factory=list)
    link_refs: list[str] = Field(default_factory=list, exclude=True, repr=False)
    identity_claims: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=channel_utc_now)

    @property
    def safe_text(self) -> str:
        return redact_operator_text(self.text)

    @property
    def text_hash(self) -> str:
        return text_hash(self.text)


class ChannelInboundMessage(ChannelDataModel):
    message_id: str = Field(default_factory=lambda: new_id("channel_inbound"))
    adapter_id: str
    channel: str
    external_message_hash: str
    sender_hash: str
    thread_hash: str | None = None
    subject_hash: str | None = None
    safe_text: str = ""
    text_hash: str
    identity_binding: ChannelIdentityRef | None = None
    attachment_quarantine: list[ChannelAttachmentQuarantine] = Field(default_factory=list)
    link_quarantine: list[ChannelLinkQuarantine] = Field(default_factory=list)
    message_hash: str = ""
    created_at: datetime = Field(default_factory=channel_utc_now)

    def with_hash(self) -> ChannelInboundMessage:
        payload = self.safe_model_dump()
        payload["message_hash"] = ""
        return self.model_copy(update={"message_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["message_hash"]
        payload["message_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelContentPolicyResult(ChannelDataModel):
    result_id: str = Field(default_factory=lambda: new_id("channel_content_policy"))
    passed: bool = True
    reasons: list[str] = Field(default_factory=lambda: ["channel_content_policy_clear"])


class ChannelOutboundRequest(ChannelDataModel):
    adapter_id: str
    channel: str
    subject: str | None = None
    body: str = Field(exclude=True, repr=False)
    recipients: list[str] = Field(default_factory=list, exclude=True, repr=False)
    recipient_provenance: dict[str, str] = Field(default_factory=dict, exclude=True, repr=False)
    thread_ref: str | None = None
    evidence_refs: list[str]
    objective_tags: list[str] = Field(default_factory=list)
    attachment_refs: list[ChannelAttachmentRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _request_is_safe(self) -> ChannelOutboundRequest:
        if not self.evidence_refs:
            raise ValueError("channel outbound request requires evidence refs")
        if _looks_like_raw_secret(self.body) or _looks_like_raw_secret(self.subject or ""):
            raise ValueError("channel outbound content contains secret-like text")
        self.metadata = _sanitize_channel_payload(self.metadata, context="channel_outbound_request")
        return self


class ChannelOutboundDraft(ChannelDataModel):
    draft_id: str = Field(default_factory=lambda: new_id("channel_draft"))
    adapter_id: str
    channel: str
    subject_hash: str | None = None
    body_hash: str
    recipient_hashes: list[str] = Field(default_factory=list)
    recipient_count: int = 0
    recipient_provenance_hash: str | None = None
    thread_hash: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    objective_tags: list[str] = Field(default_factory=list)
    content_policy_result: ChannelContentPolicyResult = Field(default_factory=ChannelContentPolicyResult)
    attachment_refs: list[ChannelAttachmentRef] = Field(default_factory=list)
    send_attempted: bool = False
    created_at: datetime = Field(default_factory=channel_utc_now)
    draft_hash: str = ""

    def with_hash(self) -> ChannelOutboundDraft:
        payload = self.safe_model_dump()
        payload["draft_hash"] = ""
        return self.model_copy(update={"draft_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["draft_hash"]
        payload["draft_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelOutboundApproval(ChannelDataModel):
    approval_id: str = Field(default_factory=lambda: new_id("channel_approval"))
    adapter_id: str
    draft_id: str
    approved_by: str = "operator"
    approval_source: str = "operator"
    approved: bool = True
    safe_summary: str = "Operator approved channel send."
    created_at: datetime = Field(default_factory=channel_utc_now)
    approval_hash: str = ""

    @model_validator(mode="after")
    def _approval_is_operator_only(self) -> ChannelOutboundApproval:
        if self.approval_source not in {"operator", "operator_policy", "manual_operator"}:
            raise ValueError("operator approval source required for channel send")
        self.approved_by = redact_operator_text(self.approved_by)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> ChannelOutboundApproval:
        payload = self.safe_model_dump()
        payload["approval_hash"] = ""
        return self.model_copy(update={"approval_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["approval_hash"]
        payload["approval_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelOutboundSendRequest(ChannelDataModel):
    adapter_id: str
    draft_id: str
    approval_id: str | None = None
    idempotency_key: str | None = None
    requested_by: str = "operator"


class ChannelDeliveryResult(ChannelDataModel):
    delivery_id: str = Field(default_factory=lambda: new_id("channel_delivery"))
    adapter_id: str
    draft_id: str
    status: ChannelDeliveryStatus = ChannelDeliveryStatus.SENT
    delivery_ref: str | None = None
    provider_message_ref_hash: str | None = None
    safe_summary: str = "Channel delivery result recorded."
    created_at: datetime = Field(default_factory=channel_utc_now)
    delivery_hash: str = ""

    def with_hash(self) -> ChannelDeliveryResult:
        payload = self.safe_model_dump()
        payload["delivery_hash"] = ""
        return self.model_copy(update={"delivery_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["delivery_hash"]
        payload["delivery_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelAdapterReceipt(ChannelDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("channel_adapter_receipt"))
    adapter_id: str
    draft_id: str
    mission_id: str
    channel_receipt_ref: str | None = None
    channel_receipt_hash: str | None = None
    channel_finalgate_ref: str | None = None
    delivery_ref_hash: str | None = None
    idempotency_key_hash: str | None = None
    recipient_hashes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    backend_id: str | None = None
    backend_owner: str | None = None
    product_dispatch_owner: str | None = None
    future_permission: bool = False
    created_at: datetime = Field(default_factory=channel_utc_now)
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _receipt_is_evidence_only(self) -> ChannelAdapterReceipt:
        if self.future_permission:
            raise ValueError("channel adapter receipt cannot become future permission")
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        return self

    def with_hash(self) -> ChannelAdapterReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["receipt_hash"]
        payload["receipt_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelAdapterFinalGateCertificate(ChannelDataModel):
    certificate_id: str = Field(default_factory=lambda: new_id("channel_adapter_finalgate"))
    adapter_id: str
    draft_id: str
    mission_id: str
    passed: bool
    receipt_ref: str | None = None
    channel_finalgate_ref: str | None = None
    failures: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=channel_utc_now)


class ChannelOutboundSendResult(ChannelDataModel):
    send_result_id: str = Field(default_factory=lambda: new_id("channel_send_result"))
    adapter_id: str
    draft_id: str
    mission_id: str
    status: str
    delivery_result: ChannelDeliveryResult | None = None
    adapter_receipt: ChannelAdapterReceipt | None = None
    finalgate_certificate: ChannelAdapterFinalGateCertificate | None = None
    channel_receipt_ref: str | None = None
    channel_finalgate_ref: str | None = None
    blocked_reason: str | None = None
    safe_summary: str = "Channel send result."
    created_at: datetime = Field(default_factory=channel_utc_now)
    result_hash: str = ""

    def with_hash(self) -> ChannelOutboundSendResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["result_hash"]
        payload["result_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class ChannelAdapterTelemetrySummary(ChannelDataModel):
    mission_id: str
    event_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)
    safe_summary: str = "Channel adapter telemetry summary."


class ChannelAdapterReplayView(ChannelDataModel):
    mission_id: str
    adapters: list[ChannelAdapterConfig] = Field(default_factory=list)
    inbound_messages: list[ChannelInboundMessage] = Field(default_factory=list)
    outbound_drafts: list[ChannelOutboundDraft] = Field(default_factory=list)
    approvals: list[ChannelOutboundApproval] = Field(default_factory=list)
    send_results: list[ChannelOutboundSendResult] = Field(default_factory=list)
    receipts: list[ChannelAdapterReceipt] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    reexecuted_actions: bool = False

    @model_validator(mode="after")
    def _replay_never_reexecutes(self) -> ChannelAdapterReplayView:
        if self.reexecuted_actions:
            raise ValueError("channel adapter replay must not re-execute actions")
        return self


def _sanitize_channel_payload(value: Any, *, context: str) -> Any:
    _reject_channel_forbidden_payload(value)
    sanitized = redact_operator_value(value)
    reject_operator_control_payload(sanitized, context=context)
    return sanitized


def _reject_channel_forbidden_payload(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {
                "raw_token",
                "token_value",
                "credential_value",
                "raw_credential",
                "password",
                "api_key",
            }:
                raise ValueError("raw channel token or credential persistence is not allowed")
            if lowered in {"raw_prompt", "prompt", "prompt_text"} and "hash" not in lowered:
                raise ValueError("raw prompt persistence is not allowed")
            if lowered in {"raw_provider_response", "provider_response", "raw_response"} and "hash" not in lowered:
                raise ValueError("raw provider response persistence is not allowed")
            if lowered in {"raw_reasoning", "reasoning", "thinking"} and "hash" not in lowered:
                raise ValueError("raw reasoning persistence is not allowed")
            if lowered in {"fallback", "auto", "auto_route", "provider_override", "model_override"}:
                raise ValueError("provider fallback/AUTO or override is not allowed")
            _reject_channel_forbidden_payload(item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _reject_channel_forbidden_payload(item)
        return
    if isinstance(value, str):
        if _looks_like_raw_secret(value):
            raise ValueError("raw channel token or credential persistence is not allowed")
        lowered = value.lower()
        if "fallback" in lowered or lowered.strip() == "auto":
            raise ValueError("provider fallback/AUTO or override is not allowed")


def _looks_like_raw_secret(value: str) -> bool:
    redacted = redact_operator_text(value)
    if redacted != value:
        return True
    scan = scan_forbidden_payload_categorized(value, path="$")
    return bool(scan[OrganSafetyScanCategory.SECRET.value])


def _normalize_recipient(value: str) -> str:
    return value.strip().lower()
