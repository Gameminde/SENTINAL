from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import scan_forbidden_payload_categorized


def financial_utc_now() -> datetime:
    return datetime.now(UTC)


class FinancialAuthorityDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _financial_data_is_not_authority(self) -> FinancialAuthorityDataModel:
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return _safe_financial_key_names(redact_operator_value(self.model_dump(mode="json")))


class FinancialAuthorityMode(StrEnum):
    DISABLED = "disabled"
    PLAN_ONLY = "plan_only"
    SANDBOX_ONLY = "sandbox_only"
    PAPER_TRADING_ONLY = "paper_trading_only"
    OPERATOR_ASSISTED_SPEND = "operator_assisted_spend"
    OPERATOR_ASSISTED_TRADE = "operator_assisted_trade"
    DELEGATED_MICRO_SPEND_SESSION = "delegated_micro_spend_session"
    DELEGATED_PAPER_TRADING_SESSION = "delegated_paper_trading_session"
    LIVE_MONEY_SPECIAL_AUTHORITY_LOCKED = "live_money_special_authority_locked"


class FinancialActionKind(StrEnum):
    SPEND = "spend"
    PAYMENT = "payment"
    TRANSFER = "transfer"
    TRADE = "trade"
    PAPER_TRADE = "paper_trade"


class FinancialSurfaceKind(StrEnum):
    BROWSER = "browser"
    DESKTOP = "desktop"
    VOICE = "voice"
    CHANNEL = "channel"
    API_DESCRIPTOR = "api_descriptor"


class FinancialProviderKind(StrEnum):
    SANDBOX = "sandbox"
    FAKE_PAYMENT = "fake_payment"
    PAYMENT_DESCRIPTOR = "payment_descriptor"
    BANK_DESCRIPTOR = "bank_descriptor"
    PAPER_BROKER = "paper_broker"
    BROKER_DESCRIPTOR = "broker_descriptor"


class FinancialPlanStatus(StrEnum):
    READY = "ready"
    CHECKPOINT_REQUIRED = "checkpoint_required"
    BLOCKED = "blocked"
    EXECUTED = "executed"
    FAILED = "failed"


class FinancialFinalGateDecision(StrEnum):
    CERTIFIED_SANDBOX_SPEND = "certified_sandbox_spend"
    CERTIFIED_PAPER_TRADE = "certified_paper_trade"
    CERTIFIED_BLOCKED = "certified_blocked"
    REJECTED_UNSAFE_RECEIPT = "rejected_unsafe_receipt"


class FinancialAccountRef(FinancialAuthorityDataModel):
    account_ref: str
    account_ref_hash: str = ""

    def with_hash(self) -> FinancialAccountRef:
        payload = self.safe_model_dump()
        payload["account_ref_hash"] = ""
        return self.model_copy(update={"account_ref_hash": stable_hash(payload)})


class FinancialInstrumentRef(FinancialAuthorityDataModel):
    symbol: str
    asset_class: str = "equity"
    instrument_ref_hash: str = ""

    @model_validator(mode="after")
    def _normalize_symbol(self) -> FinancialInstrumentRef:
        self.symbol = _safe_identifier(self.symbol, "symbol").upper()
        self.asset_class = _safe_identifier(self.asset_class, "asset_class")
        return self

    def with_hash(self) -> FinancialInstrumentRef:
        payload = self.safe_model_dump()
        payload["instrument_ref_hash"] = ""
        return self.model_copy(update={"instrument_ref_hash": stable_hash(payload)})


class FinancialRecipientRef(FinancialAuthorityDataModel):
    recipient_ref: str
    recipient_ref_hash: str = ""

    def with_hash(self) -> FinancialRecipientRef:
        payload = self.safe_model_dump()
        payload["recipient_ref_hash"] = ""
        return self.model_copy(update={"recipient_ref_hash": stable_hash(payload)})


class FinancialMerchantRef(FinancialRecipientRef):
    pass


class FinancialPaymentMethodRef(FinancialAuthorityDataModel):
    payment_method_ref_hash: str
    scope_ref: str


class FinancialBudgetPolicy(FinancialAuthorityDataModel):
    max_single_amount_minor: int = Field(default=0, ge=0)
    max_total_amount_minor: int = Field(default=0, ge=0)
    currency: str = "USD"

    @model_validator(mode="after")
    def _normalize_currency(self) -> FinancialBudgetPolicy:
        self.currency = _safe_currency(self.currency)
        return self


class FinancialVelocityPolicy(FinancialAuthorityDataModel):
    max_plans_per_mission: int = Field(default=1, ge=1)


class FinancialRecipientPolicy(FinancialAuthorityDataModel):
    allowed_recipients: list[str] = Field(default_factory=list)
    checkpoint_for_new_recipient: bool = True

    @model_validator(mode="after")
    def _normalize_recipients(self) -> FinancialRecipientPolicy:
        self.allowed_recipients = sorted({_safe_text_ref(item) for item in self.allowed_recipients if str(item).strip()})
        return self


class FinancialMerchantPolicy(FinancialAuthorityDataModel):
    allowed_merchants: list[str] = Field(default_factory=list)
    checkpoint_for_new_merchant: bool = True

    @model_validator(mode="after")
    def _normalize_merchants(self) -> FinancialMerchantPolicy:
        self.allowed_merchants = sorted({_safe_text_ref(item) for item in self.allowed_merchants if str(item).strip()})
        return self


class FinancialInstrumentPolicy(FinancialAuthorityDataModel):
    allowed_symbols: list[str] = Field(default_factory=list)
    allowed_order_types: list[str] = Field(default_factory=lambda: ["limit"])
    allow_market_order_with_checkpoint: bool = False
    allow_margin: bool = False
    allow_leverage: bool = False
    allow_options: bool = False
    allow_derivatives: bool = False

    @model_validator(mode="after")
    def _normalize_policy(self) -> FinancialInstrumentPolicy:
        self.allowed_symbols = sorted({_safe_identifier(item, "symbol").upper() for item in self.allowed_symbols if str(item).strip()})
        self.allowed_order_types = sorted({_safe_identifier(item, "order_type") for item in self.allowed_order_types if str(item).strip()})
        if self.allow_margin or self.allow_leverage or self.allow_options or self.allow_derivatives:
            raise ValueError("financial_v1_blocks_margin_leverage_options_derivatives")
        return self


class FinancialMarketPolicy(FinancialAuthorityDataModel):
    allowed_markets: list[str] = Field(default_factory=list)
    market_manipulation_allowed: bool = False
    insider_information_allowed: bool = False

    @model_validator(mode="after")
    def _market_policy_safe(self) -> FinancialMarketPolicy:
        if self.market_manipulation_allowed or self.insider_information_allowed:
            raise ValueError("financial_market_abuse_not_allowed")
        self.allowed_markets = sorted({_safe_identifier(item, "market") for item in self.allowed_markets if str(item).strip()})
        return self


class FinancialRiskLimit(FinancialAuthorityDataModel):
    max_risk_lane: str = "special_authority"
    max_position_value_minor: int = Field(default=0, ge=0)
    stop_loss_required: bool = False


class FinancialApprovalPolicy(FinancialAuthorityDataModel):
    operator_approval_required: bool = True
    require_fresh_confirmation_for_live_money: bool = True
    allow_voice_approval: bool = False
    allow_memory_approval: bool = False

    @model_validator(mode="after")
    def _approval_safe(self) -> FinancialApprovalPolicy:
        if not self.operator_approval_required or self.allow_voice_approval or self.allow_memory_approval:
            raise ValueError("financial_approval_must_be_operator_originated")
        return self


class FinancialAuthorityPolicy(FinancialAuthorityDataModel):
    mission_scoped: bool = True
    sandbox_first: bool = True
    paper_trading_first: bool = True
    live_money_default_allowed: bool = False
    operator_approval_required: bool = True
    no_duplicate_submit: bool = True
    policy_hash: str = ""

    @model_validator(mode="after")
    def _policy_safe(self) -> FinancialAuthorityPolicy:
        if self.live_money_default_allowed or not self.operator_approval_required or not self.no_duplicate_submit:
            raise ValueError("financial_authority_policy_must_fail_closed")
        return self

    def with_hash(self) -> FinancialAuthorityPolicy:
        payload = self.safe_model_dump()
        payload["policy_hash"] = ""
        return self.model_copy(update={"policy_hash": stable_hash(payload)})


class FinancialAuthorityConfig(FinancialAuthorityDataModel):
    config_id: str = Field(default_factory=lambda: new_id("financial_auth_config"))
    default_mode: FinancialAuthorityMode = FinancialAuthorityMode.PLAN_ONLY
    allowed_modes: list[FinancialAuthorityMode] = Field(default_factory=lambda: [FinancialAuthorityMode.PLAN_ONLY])
    allowed_surfaces: list[FinancialSurfaceKind] = Field(default_factory=list)
    allowed_merchants: list[str] = Field(default_factory=list)
    allowed_recipients: list[str] = Field(default_factory=list)
    allowed_instruments: list[str] = Field(default_factory=list)
    budget_policy: FinancialBudgetPolicy = Field(default_factory=FinancialBudgetPolicy)
    velocity_policy: FinancialVelocityPolicy = Field(default_factory=FinancialVelocityPolicy)
    recipient_policy: FinancialRecipientPolicy = Field(default_factory=FinancialRecipientPolicy)
    merchant_policy: FinancialMerchantPolicy = Field(default_factory=FinancialMerchantPolicy)
    instrument_policy: FinancialInstrumentPolicy = Field(default_factory=FinancialInstrumentPolicy)
    market_policy: FinancialMarketPolicy = Field(default_factory=FinancialMarketPolicy)
    risk_limit: FinancialRiskLimit = Field(default_factory=FinancialRiskLimit)
    approval_policy: FinancialApprovalPolicy = Field(default_factory=FinancialApprovalPolicy)
    live_money_execution_allowed: bool = False
    live_broker_orders_allowed: bool = False
    card_testing_allowed: bool = False
    refund_dispute_abuse_allowed: bool = False
    mfa_sca_kyc_bypass_allowed: bool = False
    market_manipulation_allowed: bool = False
    provider_key_persistence_allowed: bool = False
    raw_payment_data_persistence_allowed: bool = False
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_safe(self) -> FinancialAuthorityConfig:
        if self.default_mode not in set(self.allowed_modes):
            raise ValueError("financial_authority_default_mode_not_allowed")
        if self.default_mode is FinancialAuthorityMode.LIVE_MONEY_SPECIAL_AUTHORITY_LOCKED:
            raise ValueError("financial_v1_live_money_default_not_allowed")
        if FinancialAuthorityMode.LIVE_MONEY_SPECIAL_AUTHORITY_LOCKED in set(self.allowed_modes):
            raise ValueError("financial_v1_live_money_mode_not_allowed")
        if not self.allowed_surfaces:
            raise ValueError("financial_authority_allowed_surface_required")
        if any(
            [
                self.live_money_execution_allowed,
                self.live_broker_orders_allowed,
                self.card_testing_allowed,
                self.refund_dispute_abuse_allowed,
                self.mfa_sca_kyc_bypass_allowed,
                self.market_manipulation_allowed,
                self.provider_key_persistence_allowed,
                self.raw_payment_data_persistence_allowed,
            ]
        ):
            raise ValueError("financial_authority_live_abuse_or_secret_persistence_not_allowed")
        self.allowed_merchants = sorted({_safe_text_ref(item) for item in self.allowed_merchants if str(item).strip()})
        self.allowed_recipients = sorted({_safe_text_ref(item) for item in self.allowed_recipients if str(item).strip()})
        self.allowed_instruments = sorted({_safe_identifier(item, "instrument").upper() for item in self.allowed_instruments if str(item).strip()})
        return self

    def with_hash(self) -> FinancialAuthorityConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class FinancialCheckpoint(FinancialAuthorityDataModel):
    checkpoint_id: str = Field(default_factory=lambda: new_id("financial_checkpoint"))
    mission_id: str
    reason: str
    checkpoint_kind: str
    operator_required: bool = True
    bypass_allowed: bool = False
    safe_summary: str = "Financial human checkpoint required."
    checkpoint_hash: str = ""

    @model_validator(mode="after")
    def _checkpoint_is_safe(self) -> FinancialCheckpoint:
        if not self.operator_required or self.bypass_allowed:
            raise ValueError("financial_checkpoint_cannot_allow_bypass")
        self.reason = _safe_identifier(self.reason, "checkpoint_reason")
        self.checkpoint_kind = _safe_identifier(self.checkpoint_kind, "checkpoint_kind")
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> FinancialCheckpoint:
        payload = self.safe_model_dump()
        payload["checkpoint_hash"] = ""
        return self.model_copy(update={"checkpoint_hash": stable_hash(payload)})


class FinancialHumanConfirmation(FinancialAuthorityDataModel):
    confirmation_ref: str
    operator_originated: bool = True
    approved: bool = True
    confirmation_hash: str = ""

    @model_validator(mode="after")
    def _confirmation_safe(self) -> FinancialHumanConfirmation:
        if not self.operator_originated or not self.approved:
            raise ValueError("financial_confirmation_must_be_operator_approved")
        return self

    def with_hash(self) -> FinancialHumanConfirmation:
        payload = self.safe_model_dump()
        payload["confirmation_hash"] = ""
        return self.model_copy(update={"confirmation_hash": stable_hash(payload)})


class FinancialKillSwitchBinding(FinancialAuthorityDataModel):
    mission_id: str
    kill_switch_required: bool = True


class FinancialRevocationCheck(FinancialAuthorityDataModel):
    mission_id: str
    revoked: bool = False
    expired: bool = False
    check_hash: str = ""

    def with_hash(self) -> FinancialRevocationCheck:
        payload = self.safe_model_dump()
        payload["check_hash"] = ""
        return self.model_copy(update={"check_hash": stable_hash(payload)})


class FinancialIdempotencyRecord(FinancialAuthorityDataModel):
    record_id: str = Field(default_factory=lambda: new_id("financial_idempotency"))
    mission_id: str
    action_kind: FinancialActionKind
    key_hash: str
    action_hash: str
    reserved: bool = True
    duplicate: bool = False
    status: str = "reserved"
    created_at: datetime = Field(default_factory=financial_utc_now)
    record_hash: str = ""

    def with_hash(self) -> FinancialIdempotencyRecord:
        payload = self.safe_model_dump()
        payload["record_hash"] = ""
        return self.model_copy(update={"record_hash": stable_hash(payload)})


class FinancialDuplicatePreventionRecord(FinancialAuthorityDataModel):
    mission_id: str
    idempotency_record_ref: str
    duplicate_blocked: bool = False
    duplicate_hash: str = ""

    def with_hash(self) -> FinancialDuplicatePreventionRecord:
        payload = self.safe_model_dump()
        payload["duplicate_hash"] = ""
        return self.model_copy(update={"duplicate_hash": stable_hash(payload)})


class SpendRiskProfile(FinancialAuthorityDataModel):
    risk_lane: str = "financial_special_authority"
    requires_operator_checkpoint: bool = False
    risk_reasons: list[str] = Field(default_factory=list)


class TradeRiskProfile(FinancialAuthorityDataModel):
    risk_lane: str = "financial_special_authority"
    requires_operator_checkpoint: bool = False
    risk_reasons: list[str] = Field(default_factory=list)


class PaymentIntentDescriptor(FinancialAuthorityDataModel):
    provider_kind: FinancialProviderKind
    merchant_ref_hash: str
    amount_minor: int = Field(ge=0)
    currency: str
    descriptor_hash: str = ""

    def with_hash(self) -> PaymentIntentDescriptor:
        payload = self.safe_model_dump()
        payload["descriptor_hash"] = ""
        return self.model_copy(update={"descriptor_hash": stable_hash(payload)})


class PaymentAuthorizationDescriptor(FinancialAuthorityDataModel):
    authorization_ref_hash: str
    sandbox_only: bool = True


class PaymentCaptureDescriptor(FinancialAuthorityDataModel):
    capture_ref_hash: str
    live_capture_allowed: bool = False


class PaymentRefundDescriptor(FinancialAuthorityDataModel):
    refund_ref_hash: str
    checkpoint_required: bool = True


class PaymentDisputeDescriptor(FinancialAuthorityDataModel):
    dispute_ref_hash: str
    checkpoint_required: bool = True


class PaymentIdempotencyKey(FinancialIdempotencyRecord):
    pass


class SpendRequest(FinancialAuthorityDataModel):
    request_id: str = Field(default_factory=lambda: new_id("spend_request"))
    provider_kind: FinancialProviderKind = FinancialProviderKind.SANDBOX
    surface_kind: FinancialSurfaceKind = FinancialSurfaceKind.BROWSER
    merchant_ref: str
    recipient_ref: str
    payment_method_ref: str
    amount_minor: int = Field(ge=0)
    currency: str = "USD"
    purpose: str
    idempotency_nonce: str
    boundary_descriptors: list[str] = Field(default_factory=list)
    credential_lease_id: str | None = None
    operator_note: str | None = None

    @model_validator(mode="after")
    def _spend_request_safe(self) -> SpendRequest:
        self.merchant_ref = _safe_text_ref(self.merchant_ref)
        self.recipient_ref = _safe_text_ref(self.recipient_ref)
        self.payment_method_ref = _safe_identifier(self.payment_method_ref, "payment_method_ref")
        self.currency = _safe_currency(self.currency)
        self.purpose = _safe_identifier(self.purpose, "purpose")
        self.idempotency_nonce = redact_operator_text(self.idempotency_nonce.strip())
        self.boundary_descriptors = [_safe_identifier(item, "boundary") for item in self.boundary_descriptors]
        self.operator_note = redact_operator_text(self.operator_note) if self.operator_note else None
        return self


class SpendPreview(FinancialAuthorityDataModel):
    preview_id: str = Field(default_factory=lambda: new_id("spend_preview"))
    merchant_ref_hash: str
    recipient_ref_hash: str
    amount_minor: int
    currency: str
    checkpoint_refs: list[str] = Field(default_factory=list)


class SpendPlan(FinancialAuthorityDataModel):
    plan_id: str = Field(default_factory=lambda: new_id("spend_plan"))
    mission_id: str
    request_id: str
    config_id: str
    status: FinancialPlanStatus = FinancialPlanStatus.READY
    provider_kind: FinancialProviderKind
    surface_kind: FinancialSurfaceKind
    merchant_ref_hash: str
    merchant_label: str
    recipient_ref_hash: str
    recipient_label: str
    payment_method_ref_hash: str
    payment_method_scope_ref: str
    amount_minor: int
    currency: str
    purpose_hash: str
    credential_lease_ref: str | None = None
    credential_lease_ref_hash: str | None = None
    checkpoints: list[FinancialCheckpoint] = Field(default_factory=list)
    risk_profile: SpendRiskProfile = Field(default_factory=SpendRiskProfile)
    preview: SpendPreview | None = None
    idempotency_record: FinancialIdempotencyRecord
    safety_scan: FinancialSafetyScanResult
    plan_hash: str = ""

    def with_hash(self) -> SpendPlan:
        payload = self.safe_model_dump()
        payload["plan_hash"] = ""
        return self.model_copy(update={"plan_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["plan_hash"]
        payload["plan_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class SpendApproval(FinancialHumanConfirmation):
    pass


class SpendReceipt(FinancialAuthorityDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("spend_receipt"))
    mission_id: str
    plan_id: str
    status: FinancialPlanStatus
    provider_kind: FinancialProviderKind
    merchant_ref_hash: str
    recipient_ref_hash: str
    payment_method_ref_hash: str
    amount_minor: int
    currency: str
    approval_ref_hash: str | None = None
    credential_lease_ref_hash: str | None = None
    secret_use_receipt_ref: str | None = None
    checkout_result_ref: str | None = None
    idempotency_record_ref: str
    sandbox_or_paper: bool = True
    live_money_executed: bool = False
    live_provider_called: bool = False
    raw_credential_persisted: bool = False
    raw_payment_data_persisted: bool = False
    safe_summary: str = "Sandbox spend receipt metadata only."
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _receipt_safe(self) -> SpendReceipt:
        if self.live_money_executed or self.live_provider_called or self.raw_credential_persisted or self.raw_payment_data_persisted:
            raise ValueError("spend_receipt_cannot_persist_sensitive_material_or_live_money")
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> SpendReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})


class SpendResult(FinancialAuthorityDataModel):
    accepted: bool
    status: FinancialPlanStatus
    reason: str
    mission_id: str
    receipt: SpendReceipt
    finalgate_certificate: FinancialFinalGateCertificate | None = None


class TransferRequest(SpendRequest):
    transfer_ref: str = Field(default_factory=lambda: new_id("transfer_request"))


class TransferPlan(SpendPlan):
    pass


class TransferPreview(SpendPreview):
    pass


class TransferApproval(SpendApproval):
    pass


class TransferReceipt(SpendReceipt):
    pass


class TransferResult(SpendResult):
    pass


class TradingVenueDescriptor(FinancialAuthorityDataModel):
    venue_ref: str = "paper_broker"
    paper_only: bool = True


class TradingAccountDescriptor(FinancialAuthorityDataModel):
    account_ref_hash: str
    paper_only: bool = True


class OrderTypeDescriptor(FinancialAuthorityDataModel):
    order_type: str
    checkpoint_required: bool = False


class OrderTimeInForceDescriptor(FinancialAuthorityDataModel):
    time_in_force: str = "day"


class TradingRequest(FinancialAuthorityDataModel):
    request_id: str = Field(default_factory=lambda: new_id("trade_request"))
    provider_kind: FinancialProviderKind = FinancialProviderKind.PAPER_BROKER
    surface_kind: FinancialSurfaceKind = FinancialSurfaceKind.BROWSER
    account_ref: str
    symbol: str
    asset_class: str = "equity"
    side: str = "buy"
    quantity: float = Field(gt=0)
    order_type: str = "limit"
    limit_price_minor: int | None = Field(default=None, ge=0)
    currency: str = "USD"
    idempotency_nonce: str
    margin_requested: bool = False
    operator_note: str | None = None

    @model_validator(mode="after")
    def _trade_request_safe(self) -> TradingRequest:
        self.account_ref = _safe_identifier(self.account_ref, "account_ref")
        self.symbol = _safe_identifier(self.symbol, "symbol").upper()
        self.asset_class = _safe_identifier(self.asset_class, "asset_class")
        self.side = _safe_identifier(self.side, "side")
        self.order_type = _safe_identifier(self.order_type, "order_type")
        self.currency = _safe_currency(self.currency)
        self.idempotency_nonce = redact_operator_text(self.idempotency_nonce.strip())
        self.operator_note = redact_operator_text(self.operator_note) if self.operator_note else None
        return self


class TradeOrderTicket(FinancialAuthorityDataModel):
    ticket_id: str = Field(default_factory=lambda: new_id("trade_ticket"))
    account_ref_hash: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    limit_price_minor: int | None = None
    currency: str = "USD"
    paper_only: bool = True


class TradeOrderPreview(FinancialAuthorityDataModel):
    preview_id: str = Field(default_factory=lambda: new_id("trade_preview"))
    ticket: TradeOrderTicket
    checkpoint_refs: list[str] = Field(default_factory=list)


class TradingPlan(FinancialAuthorityDataModel):
    plan_id: str = Field(default_factory=lambda: new_id("trade_plan"))
    mission_id: str
    request_id: str
    config_id: str
    status: FinancialPlanStatus = FinancialPlanStatus.READY
    provider_kind: FinancialProviderKind
    surface_kind: FinancialSurfaceKind
    account_ref_hash: str
    symbol: str
    asset_class: str
    side: str
    quantity: float
    order_type: str
    limit_price_minor: int | None = None
    currency: str
    checkpoints: list[FinancialCheckpoint] = Field(default_factory=list)
    risk_profile: TradeRiskProfile = Field(default_factory=TradeRiskProfile)
    ticket: TradeOrderTicket
    preview: TradeOrderPreview
    idempotency_record: FinancialIdempotencyRecord
    safety_scan: FinancialSafetyScanResult
    plan_hash: str = ""

    def with_hash(self) -> TradingPlan:
        payload = self.safe_model_dump()
        payload["plan_hash"] = ""
        return self.model_copy(update={"plan_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["plan_hash"]
        payload["plan_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class TradeApproval(FinancialHumanConfirmation):
    pass


class TradeOrderReceipt(FinancialAuthorityDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("trade_receipt"))
    mission_id: str
    plan_id: str
    status: FinancialPlanStatus
    provider_kind: FinancialProviderKind
    account_ref_hash: str
    symbol: str
    side: str
    quantity: float
    order_type: str
    limit_price_minor: int | None = None
    currency: str
    approval_ref_hash: str | None = None
    idempotency_record_ref: str
    sandbox_or_paper: bool = True
    live_broker_order_submitted: bool = False
    live_provider_called: bool = False
    raw_credential_persisted: bool = False
    raw_provider_response_persisted: bool = False
    safe_summary: str = "Paper trade receipt metadata only."
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _trade_receipt_safe(self) -> TradeOrderReceipt:
        if self.live_broker_order_submitted or self.live_provider_called or self.raw_credential_persisted or self.raw_provider_response_persisted:
            raise ValueError("trade_receipt_cannot_persist_sensitive_material_or_submit_live_order")
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> TradeOrderReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})


class TradeOrderResult(FinancialAuthorityDataModel):
    accepted: bool
    status: FinancialPlanStatus
    reason: str
    mission_id: str
    receipt: TradeOrderReceipt
    finalgate_certificate: FinancialFinalGateCertificate | None = None


class PaperTradingSession(FinancialAuthorityDataModel):
    session_id: str = Field(default_factory=lambda: new_id("paper_trade_session"))
    mission_id: str
    paper_only: bool = True


class PaperTradingResult(TradeOrderResult):
    pass


class FinancialFinalGateCertificate(FinancialAuthorityDataModel):
    certificate_id: str = Field(default_factory=lambda: new_id("financial_finalgate"))
    mission_id: str
    receipt_id: str
    decision: FinancialFinalGateDecision
    certified: bool
    reasons: list[str] = Field(default_factory=list)
    receipt_hash: str
    certificate_hash: str = ""

    def with_hash(self) -> FinancialFinalGateCertificate:
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})


class FinancialSafetyScanResult(FinancialAuthorityDataModel):
    valid: bool = True
    reasons: list[str] = Field(default_factory=list)
    rejected_paths: list[str] = Field(default_factory=list)
    scan_hash: str = ""

    def with_hash(self) -> FinancialSafetyScanResult:
        payload = self.safe_model_dump()
        payload["scan_hash"] = ""
        return self.model_copy(update={"scan_hash": stable_hash(payload)})


class FinancialReplayView(FinancialAuthorityDataModel):
    mission_id: str
    configs: list[FinancialAuthorityConfig] = Field(default_factory=list)
    spend_plans: list[SpendPlan] = Field(default_factory=list)
    trade_plans: list[TradingPlan] = Field(default_factory=list)
    spend_receipts: list[SpendReceipt] = Field(default_factory=list)
    trade_receipts: list[TradeOrderReceipt] = Field(default_factory=list)
    checkpoints: list[FinancialCheckpoint] = Field(default_factory=list)
    finalgate_certificates: list[FinancialFinalGateCertificate] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    executed_live_money: bool = False
    placed_live_trade: bool = False
    materialized_credential: bool = False
    replayed_financial_action: bool = False
    called_live_provider: bool = False
    called_live_broker: bool = False
    filled_card_field: bool = False
    submitted_checkout: bool = False
    submitted_order: bool = False


class FinancialTelemetrySummary(FinancialAuthorityDataModel):
    mission_id: str
    event_count: int = 0
    metric_count: int = 0
    checkpoint_count: int = 0
    receipt_count: int = 0


def scan_financial_payload(payload: Any) -> FinancialSafetyScanResult:
    rejected = _unsafe_paths(payload)
    financial_reasons = _financial_abuse_reasons(payload)
    reasons = list(dict.fromkeys([*(["unsafe_financial_payload"] if rejected else []), *financial_reasons]))
    return FinancialSafetyScanResult(valid=not reasons, reasons=reasons, rejected_paths=rejected).with_hash()


def build_financial_checkpoints(mission_id: str, descriptors: list[str]) -> list[FinancialCheckpoint]:
    checkpoints: list[FinancialCheckpoint] = []
    for descriptor in descriptors:
        normalized = _safe_identifier(descriptor, "boundary")
        if normalized in {"mfa", "sca", "kyc"}:
            reason = "mfa_sca_kyc_checkpoint_required"
            kind = "mfa_sca_kyc"
        elif normalized == "subscription":
            reason = "subscription_checkpoint_required"
            kind = "subscription"
        elif normalized in {"refund", "dispute", "chargeback"}:
            reason = "refund_dispute_checkpoint_required"
            kind = "refund_dispute"
        elif normalized in {"external_transfer", "wire_transfer", "ach_transfer"}:
            reason = "external_transfer_checkpoint_required"
            kind = "external_transfer"
        else:
            reason = f"{normalized}_checkpoint_required"
            kind = normalized
        checkpoints.append(
            FinancialCheckpoint(
                mission_id=mission_id,
                reason=reason,
                checkpoint_kind=kind,
                safe_summary=f"Financial human checkpoint required for {kind}.",
            ).with_hash()
        )
    return checkpoints


def _unsafe_paths(payload: Any) -> list[str]:
    scan = scan_forbidden_payload_categorized(payload, path="$")
    return sorted(
        set(
            scan["secret"]
            + scan["provider_override"]
            + scan["authority_expansion"]
            + scan["unsafe_payload"]
            + scan["credential_dangerous"]
        )
    )


def _financial_abuse_reasons(payload: Any) -> list[str]:
    text = str(payload).lower()
    reasons: list[str] = []
    checks = {
        "raw_card_or_payment_material_blocked": [
            "card_number",
            "credit_card",
            "debit_card",
            "cvv",
            "cvc",
            " pan=",
            "raw_card",
            "bank_password",
            "routing_number",
            "account_number",
        ],
        "broker_or_provider_secret_blocked": ["broker_api_key", "provider_key", "api_key=", "secret_key=", "access_token=", "refresh_token="],
        "raw_prompt_or_provider_material_blocked": ["raw_prompt", "provider_response", "reasoning", "chain_of_thought"],
        "financial_abuse_blocked": [
            "card testing",
            "chargeback abuse",
            "refund abuse",
            "launder",
            "sanctions evasion",
            "spoofing",
            "layering",
            "wash trading",
            "pump and dump",
            "insider information",
        ],
    }
    for reason, markers in checks.items():
        if any(marker in text for marker in markers):
            reasons.append(reason)
    if _CARD_NUMBER_PATTERN.search(text):
        reasons.append("raw_card_or_payment_material_blocked")
    return list(dict.fromkeys(reasons))


def _safe_identifier(value: str, label: str) -> str:
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    if not normalized:
        raise ValueError(f"{label}_required")
    if any(ch in normalized for ch in ("/", "\\", "..")):
        raise ValueError(f"{label}_invalid")
    return redact_operator_text(normalized)


def _safe_text_ref(value: Any) -> str:
    return redact_operator_text(str(value).strip())


def _safe_currency(value: str) -> str:
    normalized = str(value).strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("financial_currency_invalid")
    return normalized


def _safe_financial_key_names(value: Any) -> Any:
    if isinstance(value, dict):
        rendered: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = str(key)
            if safe_key.lower() in _SENSITIVE_FINANCIAL_KEYS:
                safe_key = f"redacted_key_{stable_hash(safe_key)[:12]}"
            rendered[safe_key] = _safe_financial_key_names(item)
        return rendered
    if isinstance(value, list):
        return [_safe_financial_key_names(item) for item in value]
    return value


_CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
_SENSITIVE_FINANCIAL_KEYS = {
    "secret_value",
    "password",
    "provider_response",
    "reasoning",
    "raw_prompt",
    "card_number",
    "credit_card",
    "debit_card",
    "pan",
    "cvv",
    "cvc",
    "bank_password",
    "routing_number",
    "account_number",
    "broker_api_key",
    "provider_key",
    "api_key",
    "token",
    "access_token",
    "refresh_token",
}


__all__ = [
    "FinancialAccountRef",
    "FinancialActionKind",
    "FinancialApprovalPolicy",
    "FinancialAuthorityConfig",
    "FinancialAuthorityDataModel",
    "FinancialAuthorityMode",
    "FinancialAuthorityPolicy",
    "FinancialBudgetPolicy",
    "FinancialCheckpoint",
    "FinancialDuplicatePreventionRecord",
    "FinancialFinalGateCertificate",
    "FinancialFinalGateDecision",
    "FinancialHumanConfirmation",
    "FinancialIdempotencyRecord",
    "FinancialInstrumentPolicy",
    "FinancialInstrumentRef",
    "FinancialKillSwitchBinding",
    "FinancialMarketPolicy",
    "FinancialMerchantPolicy",
    "FinancialMerchantRef",
    "FinancialPaymentMethodRef",
    "FinancialPlanStatus",
    "FinancialProviderKind",
    "FinancialRecipientPolicy",
    "FinancialRecipientRef",
    "FinancialReplayView",
    "FinancialRevocationCheck",
    "FinancialRiskLimit",
    "FinancialSafetyScanResult",
    "FinancialSurfaceKind",
    "FinancialTelemetrySummary",
    "FinancialVelocityPolicy",
    "OrderTimeInForceDescriptor",
    "OrderTypeDescriptor",
    "PaperTradingResult",
    "PaperTradingSession",
    "PaymentAuthorizationDescriptor",
    "PaymentCaptureDescriptor",
    "PaymentDisputeDescriptor",
    "PaymentIdempotencyKey",
    "PaymentIntentDescriptor",
    "PaymentRefundDescriptor",
    "SpendApproval",
    "SpendPlan",
    "SpendPreview",
    "SpendReceipt",
    "SpendRequest",
    "SpendResult",
    "SpendRiskProfile",
    "TradeApproval",
    "TradeOrderPreview",
    "TradeOrderReceipt",
    "TradeOrderResult",
    "TradeOrderTicket",
    "TradeRiskProfile",
    "TradingAccountDescriptor",
    "TradingPlan",
    "TradingRequest",
    "TradingVenueDescriptor",
    "TransferApproval",
    "TransferPlan",
    "TransferPreview",
    "TransferReceipt",
    "TransferRequest",
    "TransferResult",
    "build_financial_checkpoints",
    "financial_utc_now",
    "scan_financial_payload",
]
