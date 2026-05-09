from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SpendAuthorityEnvelope(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("spauth"))
    mission_id: str
    root_authority_id: str
    budget_max_usd: float = Field(ge=0.0)
    budget_remaining_usd: float = Field(ge=0.0)
    max_single_transaction_usd: float = Field(ge=0.0)
    allowed_categories: list[str]
    allowed_vendors: list[str]
    expires_at: datetime
    credential_ref: str | None = None
    receipt_required: bool = True
    kill_switch_required: bool = True
    explicit_subscription_authority: bool = False
    real_provider_enabled: bool = False
    evidence_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SpendAuthorityEnvelope:
        if self.budget_remaining_usd > self.budget_max_usd:
            raise ValueError("SpendAuthorityEnvelope budget remaining cannot exceed budget max.")
        if not self.allowed_categories:
            raise ValueError("SpendAuthorityEnvelope requires allowed categories.")
        if not self.allowed_vendors:
            raise ValueError("SpendAuthorityEnvelope requires allowed vendors.")
        if not self.evidence_refs:
            raise ValueError("SpendAuthorityEnvelope requires evidence refs.")
        if self.authority_expansion:
            raise ValueError("SpendAuthorityEnvelope cannot expand authority.")
        return self


class SpendRequest(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("spreq"))
    vendor: str
    category: str
    amount_usd: float = Field(ge=0.0)
    purpose: str
    expected_information_gain: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str]
    signal_refs: list[str]
    credential_ref: str | None = None
    raw_credential: str | None = None
    subscription: bool = False
    hidden_subscription: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SpendRequest:
        if not self.evidence_refs:
            raise ValueError("SpendRequest requires evidence refs.")
        if not self.signal_refs:
            raise ValueError("SpendRequest requires signal refs.")
        if self.raw_credential is not None:
            raise ValueError("SpendRequest cannot contain raw credential material.")
        if self.authority_expansion:
            raise ValueError("SpendRequest cannot expand authority.")
        return self


class RefundCancelPath(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("sprefund"))
    steps: list[str]
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> RefundCancelPath:
        if not self.steps:
            raise ValueError("RefundCancelPath requires steps.")
        if not self.evidence_refs:
            raise ValueError("RefundCancelPath requires evidence refs.")
        return self


class SubscriptionGuard:
    def validate(self, request: SpendRequest, authority: SpendAuthorityEnvelope, refund_cancel_path: RefundCancelPath) -> None:
        if request.hidden_subscription:
            raise ValueError("hidden subscription blocked")
        if request.subscription and not authority.explicit_subscription_authority:
            raise ValueError("explicit subscription authority required")
        if request.subscription and not refund_cancel_path.steps:
            raise ValueError("subscription requires refund/cancel path")


class SpendKillSwitch(SentinelModel):
    mission_id: str
    triggered: bool = False
    reason: str | None = None

    @property
    def execution_allowed(self) -> bool:
        return not self.triggered

    def trigger(self, *, reason: str) -> SpendKillSwitch:
        return self.model_copy(update={"triggered": True, "reason": reason})


class SpendReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("sprcpt"))
    mission_id: str
    vendor: str
    category: str
    amount_usd: float = Field(ge=0.0)
    credential_ref: str | None = None
    provider_name: str = "fake_spend_provider"
    sandbox_provider: bool = True
    real_payment_started: bool = False
    subscription: bool = False
    refund_cancel_path_ref: str | None = None
    secret_accessed: bool = False
    evidence_refs: list[str]
    signal_refs: list[str]
    trace_refs: list[str]
    receipt_hash: str = ""
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SpendReceipt:
        if not self.evidence_refs:
            raise ValueError("SpendReceipt requires evidence refs.")
        if not self.signal_refs:
            raise ValueError("SpendReceipt requires signal refs.")
        if not self.trace_refs:
            raise ValueError("SpendReceipt requires trace refs.")
        if self.real_payment_started:
            raise ValueError("SpendReceipt cannot start real payment by default.")
        if self.secret_accessed:
            raise ValueError("SpendReceipt cannot access credential secrets.")
        if self.authority_expansion:
            raise ValueError("SpendReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("SpendReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "vendor": self.vendor,
                "category": self.category,
                "amount_usd": self.amount_usd,
                "credential_ref": self.credential_ref,
                "provider_name": self.provider_name,
                "sandbox_provider": self.sandbox_provider,
                "subscription": self.subscription,
                "refund_cancel_path_ref": self.refund_cancel_path_ref,
                "evidence_refs": self.evidence_refs,
                "signal_refs": self.signal_refs,
                "trace_refs": self.trace_refs,
            }
        )


class SpendProviderAdapter:
    provider_name = "real_spend_provider_interface"
    real_provider_enabled = False

    def execute(self, request: SpendRequest, authority: SpendAuthorityEnvelope) -> SpendReceipt:
        raise ValueError("real spend provider is disabled by default")


class FakeSpendProvider(SpendProviderAdapter):
    provider_name = "fake_spend_provider"

    def execute(
        self,
        request: SpendRequest,
        authority: SpendAuthorityEnvelope,
        *,
        kill_switch: SpendKillSwitch,
        subscription_guard: SubscriptionGuard,
        refund_cancel_path: RefundCancelPath,
        trace_refs: list[str],
    ) -> SpendReceipt:
        self._validate_request(request, authority, kill_switch)
        subscription_guard.validate(request, authority, refund_cancel_path)
        return SpendReceipt(
            mission_id=authority.mission_id,
            vendor=request.vendor,
            category=request.category,
            amount_usd=request.amount_usd,
            credential_ref=request.credential_ref or authority.credential_ref,
            subscription=request.subscription,
            refund_cancel_path_ref=refund_cancel_path.id if request.subscription else None,
            evidence_refs=[*authority.evidence_refs, *request.evidence_refs, *refund_cancel_path.evidence_refs],
            signal_refs=list(request.signal_refs),
            trace_refs=trace_refs,
        )

    def _validate_request(
        self,
        request: SpendRequest,
        authority: SpendAuthorityEnvelope,
        kill_switch: SpendKillSwitch,
    ) -> None:
        if kill_switch.triggered or not kill_switch.execution_allowed:
            raise ValueError("spend blocked by kill switch")
        if datetime.now(UTC) > authority.expires_at:
            raise ValueError("spend authority expired")
        if request.vendor not in authority.allowed_vendors:
            raise ValueError(f"vendor_not_allowed:{request.vendor}")
        if request.category not in authority.allowed_categories:
            raise ValueError(f"category_not_allowed:{request.category}")
        if request.amount_usd > authority.max_single_transaction_usd:
            raise ValueError("single transaction cap exceeded")
        if request.amount_usd > authority.budget_remaining_usd:
            raise ValueError("budget remaining exceeded")
        if not authority.receipt_required or not authority.kill_switch_required:
            raise ValueError("spend requires receipt and kill-switch")
