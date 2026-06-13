from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.credential_vault import CredentialVaultRuntime, CredentialVaultRuntimeError
from sentinel.operator.credential_vault_models import CredentialConsumerKind
from sentinel.operator.financial_authority_models import (
    FinancialActionKind,
    FinancialAuthorityConfig,
    FinancialCheckpoint,
    FinancialFinalGateCertificate,
    FinancialFinalGateDecision,
    FinancialIdempotencyRecord,
    FinancialPlanStatus,
    FinancialProviderKind,
    FinancialSafetyScanResult,
    SpendPlan,
    SpendPreview,
    SpendReceipt,
    SpendRequest,
    SpendResult,
    SpendRiskProfile,
    TradeOrderReceipt,
    TradeOrderResult,
    TradeOrderTicket,
    TradeOrderPreview,
    TradeRiskProfile,
    TradingPlan,
    TradingRequest,
    build_financial_checkpoints,
    financial_utc_now,
    scan_financial_payload,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.store import MissionRunStore
from sentinel.shared.safety_scanner import scan_forbidden_payload_categorized
from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


class FinancialAuthorityRuntimeError(ValueError):
    """Raised when payment/spend/trading special authority would violate Sentinel boundaries."""


class FinancialAuthorityStore:
    def __init__(self, mission_store: MissionRunStore) -> None:
        self._mission_store = mission_store

    def verify_timeline(self, mission_id: str) -> bool:
        return self._mission_store.verify_timeline(mission_id)

    def mission_dir(self, mission_id: str, *, create: bool = True) -> Path:
        return self._mission_store.mission_dir(mission_id, create=create)

    def root(self, mission_id: str) -> Path:
        return self._mission_store.mission_dir(mission_id, create=True) / "financial_authority"

    def item_path(self, mission_id: str, category: str, name: str) -> Path:
        root = self.root(mission_id) / category
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{stable_hash({'financial_authority_item': name})[:24]}.json"

    def write(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        self._mission_store.atomic_write_json(self.item_path(mission_id, category, name), payload)

    def append_event(
        self,
        mission_id: str,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
    ) -> None:
        self._mission_store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=_safe_event_metadata(metadata or {}),
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
        )

    def load_events(self, mission_id: str) -> list[Any]:
        return self._mission_store.load_events(mission_id)


class FinancialAuthorityRuntime:
    """Sandbox-first financial authority coordinator over Sentinel's existing spine."""

    def __init__(self, kernel: MissionKernel) -> None:
        self.kernel = kernel
        self.store = FinancialAuthorityStore(kernel.store)

    def register_config(self, *, mission_id: str, config: FinancialAuthorityConfig) -> FinancialAuthorityConfig:
        self.kernel.store.load_record(mission_id)
        config = config.with_hash()
        self.store.write(mission_id, "configs", config.config_id, config.safe_model_dump())
        self.store.append_event(
            mission_id,
            "financial_authority_initialized",
            "Financial authority config registered as sandbox/paper special-authority metadata.",
            metadata={"config_id": config.config_id, "config_hash": config.config_hash, "default_mode": config.default_mode.value},
        )
        return config

    def plan_spend(
        self,
        *,
        mission_id: str,
        config_id: str,
        request: SpendRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> SpendPlan:
        config = self._load_config(mission_id, config_id)
        self._assert_authority(mission_id, envelope, action="financial_spend", tool="financial_authority")
        self._scan_or_raise(request.safe_model_dump())
        self._assert_surface(config, request.surface_kind)
        action_hash = stable_hash(
            {
                "kind": "spend",
                "merchant": request.merchant_ref,
                "recipient": request.recipient_ref,
                "payment_method": request.payment_method_ref,
                "amount_minor": request.amount_minor,
                "currency": request.currency,
                "purpose": request.purpose,
            }
        )
        idempotency = self._reserve_idempotency(
            mission_id=mission_id,
            action_kind=FinancialActionKind.SPEND,
            nonce=request.idempotency_nonce,
            action_hash=action_hash,
        )
        checkpoints = self._spend_checkpoints(mission_id, config, request)
        risk_reasons = [checkpoint.reason for checkpoint in checkpoints]
        status = FinancialPlanStatus.CHECKPOINT_REQUIRED if checkpoints else FinancialPlanStatus.READY
        scan = scan_financial_payload(request.safe_model_dump())
        plan = SpendPlan(
            mission_id=mission_id,
            request_id=request.request_id,
            config_id=config.config_id,
            status=status,
            provider_kind=request.provider_kind,
            surface_kind=request.surface_kind,
            merchant_ref_hash=stable_hash(request.merchant_ref),
            merchant_label=request.merchant_ref,
            recipient_ref_hash=stable_hash(request.recipient_ref),
            recipient_label=request.recipient_ref,
            payment_method_ref_hash=stable_hash(request.payment_method_ref),
            payment_method_scope_ref=f"payment_method:{request.payment_method_ref}",
            amount_minor=request.amount_minor,
            currency=request.currency,
            purpose_hash=stable_hash(request.purpose),
            credential_lease_ref=None,
            credential_lease_ref_hash=stable_hash(request.credential_lease_id) if request.credential_lease_id else None,
            checkpoints=checkpoints,
            risk_profile=SpendRiskProfile(requires_operator_checkpoint=bool(checkpoints), risk_reasons=risk_reasons),
            preview=SpendPreview(
                merchant_ref_hash=stable_hash(request.merchant_ref),
                recipient_ref_hash=stable_hash(request.recipient_ref),
                amount_minor=request.amount_minor,
                currency=request.currency,
                checkpoint_refs=[checkpoint.checkpoint_id for checkpoint in checkpoints],
            ),
            idempotency_record=idempotency,
            safety_scan=scan,
        ).with_hash()
        self._persist_checkpoints(mission_id, checkpoints)
        self.store.write(mission_id, "idempotency", idempotency.record_id, idempotency.safe_model_dump())
        self.store.write(mission_id, "spend_plans", plan.plan_id, plan.safe_model_dump())
        self.store.append_event(
            mission_id,
            "financial_action_requested",
            "Financial spend action requested as governed plan data.",
            metadata={"request_id": request.request_id, "action_kind": "spend"},
        )
        self.store.append_event(
            mission_id,
            "spend_requested",
            "Sandbox spend request accepted for planning only.",
            metadata={"request_id": request.request_id, "amount_minor": request.amount_minor, "currency": request.currency},
        )
        self.store.append_event(
            mission_id,
            "payment_idempotency_reserved",
            "Payment idempotency key reserved as hash-only metadata.",
            metadata={"record_id": idempotency.record_id, "key_hash": idempotency.key_hash},
        )
        self.store.append_event(
            mission_id,
            "financial_action_planned",
            "Financial spend plan created; no live money executed.",
            metadata={"plan_id": plan.plan_id, "status": plan.status.value, "checkpoint_count": len(checkpoints)},
        )
        self.store.append_event(
            mission_id,
            "spend_preview_created",
            "Sandbox spend preview created with safe metadata only.",
            metadata={"plan_id": plan.plan_id, "preview_id": plan.preview.preview_id if plan.preview else None},
        )
        if checkpoints:
            self.store.append_event(
                mission_id,
                "financial_approval_required",
                "Financial human approval/checkpoint required before execution.",
                metadata={"plan_id": plan.plan_id, "checkpoint_count": len(checkpoints)},
            )
        self._record_metric(mission_id, TelemetryMetricKind.FINANCIAL_ACTION_REQUEST_COUNT, 1, "Financial action request count sample.")
        self._record_metric(mission_id, TelemetryMetricKind.SPEND_PREVIEW_COUNT, 1, "Spend preview count sample.")
        if checkpoints:
            self._record_metric(mission_id, TelemetryMetricKind.FINANCIAL_CHECKPOINT_COUNT, len(checkpoints), "Financial checkpoint count sample.")
        return plan

    def plan_trade(
        self,
        *,
        mission_id: str,
        config_id: str,
        request: TradingRequest,
        envelope: MissionAuthorityEnvelope | None,
    ) -> TradingPlan:
        config = self._load_config(mission_id, config_id)
        self._assert_authority(mission_id, envelope, action="financial_trade", tool="financial_authority")
        self._scan_or_raise(request.safe_model_dump())
        self._assert_surface(config, request.surface_kind)
        action_hash = stable_hash(
            {
                "kind": "trade",
                "account": request.account_ref,
                "symbol": request.symbol,
                "asset_class": request.asset_class,
                "side": request.side,
                "quantity": request.quantity,
                "order_type": request.order_type,
                "limit_price_minor": request.limit_price_minor,
                "margin_requested": request.margin_requested,
            }
        )
        idempotency = self._reserve_idempotency(
            mission_id=mission_id,
            action_kind=FinancialActionKind.TRADE,
            nonce=request.idempotency_nonce,
            action_hash=action_hash,
        )
        checkpoints, risk_reasons, blocked = self._trade_findings(mission_id, config, request)
        status = FinancialPlanStatus.BLOCKED if blocked else FinancialPlanStatus.CHECKPOINT_REQUIRED if checkpoints else FinancialPlanStatus.READY
        ticket = TradeOrderTicket(
            account_ref_hash=stable_hash(request.account_ref),
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            limit_price_minor=request.limit_price_minor,
            currency=request.currency,
        )
        preview = TradeOrderPreview(ticket=ticket, checkpoint_refs=[checkpoint.checkpoint_id for checkpoint in checkpoints])
        plan = TradingPlan(
            mission_id=mission_id,
            request_id=request.request_id,
            config_id=config.config_id,
            status=status,
            provider_kind=request.provider_kind,
            surface_kind=request.surface_kind,
            account_ref_hash=stable_hash(request.account_ref),
            symbol=request.symbol,
            asset_class=request.asset_class,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            limit_price_minor=request.limit_price_minor,
            currency=request.currency,
            checkpoints=checkpoints,
            risk_profile=TradeRiskProfile(requires_operator_checkpoint=bool(checkpoints), risk_reasons=risk_reasons),
            ticket=ticket,
            preview=preview,
            idempotency_record=idempotency,
            safety_scan=scan_financial_payload(request.safe_model_dump()),
        ).with_hash()
        self._persist_checkpoints(mission_id, checkpoints)
        self.store.write(mission_id, "idempotency", idempotency.record_id, idempotency.safe_model_dump())
        self.store.write(mission_id, "trade_plans", plan.plan_id, plan.safe_model_dump())
        self.store.append_event(
            mission_id,
            "trade_requested",
            "Paper trade request accepted for planning only.",
            metadata={"request_id": request.request_id, "symbol": request.symbol, "order_type": request.order_type},
        )
        self.store.append_event(
            mission_id,
            "trade_order_preview_created",
            "Paper trade order preview created with safe metadata only.",
            metadata={"plan_id": plan.plan_id, "status": plan.status.value},
        )
        self.store.append_event(
            mission_id,
            "financial_action_planned",
            "Financial trade plan created; no live broker order submitted.",
            metadata={"plan_id": plan.plan_id, "status": plan.status.value, "checkpoint_count": len(checkpoints)},
        )
        if blocked:
            self.store.append_event(
                mission_id,
                "trade_order_blocked",
                "Trade order blocked by financial authority risk policy.",
                metadata={"plan_id": plan.plan_id, "risk_reasons": plan.risk_profile.risk_reasons},
            )
            self._record_metric(mission_id, TelemetryMetricKind.TRADE_BLOCK_COUNT, 1, "Trade block count sample.")
        if checkpoints:
            self.store.append_event(
                mission_id,
                "financial_approval_required",
                "Financial human approval/checkpoint required before paper trade execution.",
                metadata={"plan_id": plan.plan_id, "checkpoint_count": len(checkpoints)},
            )
            self._record_metric(mission_id, TelemetryMetricKind.FINANCIAL_CHECKPOINT_COUNT, len(checkpoints), "Financial checkpoint count sample.")
        self._record_metric(mission_id, TelemetryMetricKind.FINANCIAL_ACTION_REQUEST_COUNT, 1, "Financial action request count sample.")
        self._record_metric(mission_id, TelemetryMetricKind.TRADE_PREVIEW_COUNT, 1, "Trade preview count sample.")
        return plan

    def execute_sandbox_spend(
        self,
        *,
        mission_id: str,
        plan_id: str,
        envelope: MissionAuthorityEnvelope | None,
        credential_vault: CredentialVaultRuntime | None = None,
        credential_lease_id: str | None = None,
        approval_ref: str | None = None,
    ) -> SpendResult:
        plan = self._load_one(mission_id, "spend_plans", plan_id, SpendPlan)
        if not plan.verify_hash():
            raise FinancialAuthorityRuntimeError("spend_plan_hash_mismatch")
        config = self._load_config(mission_id, plan.config_id)
        self._assert_authority(mission_id, envelope, action="financial_spend", tool="financial_authority")
        self._assert_certified_telemetry()
        if plan.status is FinancialPlanStatus.CHECKPOINT_REQUIRED:
            raise FinancialAuthorityRuntimeError("financial_checkpoint_required")
        if plan.status is FinancialPlanStatus.BLOCKED:
            raise FinancialAuthorityRuntimeError("financial_plan_blocked")
        if config.approval_policy.operator_approval_required and not approval_ref:
            raise FinancialAuthorityRuntimeError("financial_operator_approval_required")
        secret_use_ref: str | None = None
        checkout_ref: str | None = None
        if plan.credential_lease_ref_hash:
            if not credential_vault or not credential_lease_id:
                raise FinancialAuthorityRuntimeError("credential_lease_required")
            if stable_hash(credential_lease_id) != plan.credential_lease_ref_hash:
                raise FinancialAuthorityRuntimeError("credential_lease_hash_mismatch")
            try:
                credential_vault.assert_lease_matches_scope(
                    mission_id=mission_id,
                    lease_id=credential_lease_id,
                    expected_purpose="financial_spend",
                    expected_scope=[plan.payment_method_scope_ref],
                    expected_consumer_kind=CredentialConsumerKind.EXTERNAL_API,
                    expected_consumer_ref="financial_authority_final_consumer",
                )
                checkout = credential_vault.checkout_secret(
                    mission_id=mission_id,
                    lease_id=credential_lease_id,
                    consumer_kind=CredentialConsumerKind.EXTERNAL_API,
                    consumer_ref="financial_authority_final_consumer",
                )
                secret_use = credential_vault.record_secret_use(
                    mission_id=mission_id,
                    checkout_token_id=checkout.checkout_token.checkout_token_id,
                    status="used",
                )
                checkout_ref = checkout.checkout_result_id
                secret_use_ref = secret_use.receipt_id
            except CredentialVaultRuntimeError as exc:
                raise FinancialAuthorityRuntimeError(str(exc)) from exc
            except Exception as exc:  # pragma: no cover - defensive fail-closed bridge
                raise FinancialAuthorityRuntimeError(f"credential_vault_checkout_failed:{type(exc).__name__}") from exc
        receipt = SpendReceipt(
            mission_id=mission_id,
            plan_id=plan.plan_id,
            status=FinancialPlanStatus.EXECUTED,
            provider_kind=plan.provider_kind,
            merchant_ref_hash=plan.merchant_ref_hash,
            recipient_ref_hash=plan.recipient_ref_hash,
            payment_method_ref_hash=plan.payment_method_ref_hash,
            amount_minor=plan.amount_minor,
            currency=plan.currency,
            approval_ref_hash=stable_hash(approval_ref) if approval_ref else None,
            credential_lease_ref_hash=plan.credential_lease_ref_hash,
            secret_use_receipt_ref=secret_use_ref,
            checkout_result_ref=checkout_ref,
            idempotency_record_ref=plan.idempotency_record.record_id,
            safe_summary="Sandbox spend executed through fake financial authority runtime only.",
        ).with_hash()
        certificate = self._certify_spend(receipt)
        self.store.write(mission_id, "spend_receipts", receipt.receipt_id, receipt.safe_model_dump())
        self.store.write(mission_id, "finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self.store.append_event(
            mission_id,
            "financial_approval_completed",
            "Financial approval ref recorded as hash-only metadata.",
            metadata={"plan_id": plan.plan_id, "approval_ref_hash": receipt.approval_ref_hash},
        )
        self.store.append_event(
            mission_id,
            "spend_sandbox_executed",
            "Sandbox spend executed without live provider call or raw payment persistence.",
            metadata={"plan_id": plan.plan_id, "receipt_id": receipt.receipt_id},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self.store.append_event(
            mission_id,
            "spend_completed",
            "Sandbox spend completed and certified.",
            metadata={"plan_id": plan.plan_id, "certified": certificate.certified},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.SPEND_SANDBOX_EXECUTION_COUNT, 1, "Spend sandbox execution count sample.")
        return SpendResult(
            accepted=certificate.certified,
            status=FinancialPlanStatus.EXECUTED if certificate.certified else FinancialPlanStatus.FAILED,
            reason="sandbox_spend_completed" if certificate.certified else "sandbox_spend_finalgate_rejected",
            mission_id=mission_id,
            receipt=receipt,
            finalgate_certificate=certificate,
        )

    def execute_paper_trade(
        self,
        *,
        mission_id: str,
        plan_id: str,
        envelope: MissionAuthorityEnvelope | None,
        approval_ref: str | None = None,
    ) -> TradeOrderResult:
        plan = self._load_one(mission_id, "trade_plans", plan_id, TradingPlan)
        if not plan.verify_hash():
            raise FinancialAuthorityRuntimeError("trade_plan_hash_mismatch")
        config = self._load_config(mission_id, plan.config_id)
        self._assert_authority(mission_id, envelope, action="financial_trade", tool="financial_authority")
        self._assert_certified_telemetry()
        if plan.status is FinancialPlanStatus.CHECKPOINT_REQUIRED:
            raise FinancialAuthorityRuntimeError("financial_checkpoint_required")
        if plan.status is FinancialPlanStatus.BLOCKED:
            raise FinancialAuthorityRuntimeError("financial_plan_blocked")
        if config.approval_policy.operator_approval_required and not approval_ref:
            raise FinancialAuthorityRuntimeError("financial_operator_approval_required")
        receipt = TradeOrderReceipt(
            mission_id=mission_id,
            plan_id=plan.plan_id,
            status=FinancialPlanStatus.EXECUTED,
            provider_kind=FinancialProviderKind.PAPER_BROKER,
            account_ref_hash=plan.account_ref_hash,
            symbol=plan.symbol,
            side=plan.side,
            quantity=plan.quantity,
            order_type=plan.order_type,
            limit_price_minor=plan.limit_price_minor,
            currency=plan.currency,
            approval_ref_hash=stable_hash(approval_ref) if approval_ref else None,
            idempotency_record_ref=plan.idempotency_record.record_id,
            safe_summary="Paper trade executed through fake paper-trading runtime only.",
        ).with_hash()
        certificate = self._certify_trade(receipt)
        self.store.write(mission_id, "trade_receipts", receipt.receipt_id, receipt.safe_model_dump())
        self.store.write(mission_id, "finalgate", certificate.certificate_id, certificate.safe_model_dump())
        self.store.append_event(
            mission_id,
            "paper_trade_executed",
            "Paper trade executed without live broker order submission.",
            metadata={"plan_id": plan.plan_id, "receipt_id": receipt.receipt_id},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self.store.append_event(
            mission_id,
            "trade_order_completed",
            "Paper trade completed and certified.",
            metadata={"plan_id": plan.plan_id, "certified": certificate.certified},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.PAPER_TRADE_COUNT, 1, "Paper trade count sample.")
        return TradeOrderResult(
            accepted=certificate.certified,
            status=FinancialPlanStatus.EXECUTED if certificate.certified else FinancialPlanStatus.FAILED,
            reason="paper_trade_completed" if certificate.certified else "paper_trade_finalgate_rejected",
            mission_id=mission_id,
            receipt=receipt,
            finalgate_certificate=certificate,
        )

    def build_memory_summary(self, *, mission_id: str, financial_ref: str) -> dict[str, Any]:
        self.kernel.store.load_record(mission_id)
        return {
            "mission_id": mission_id,
            "financial_ref_hash": stable_hash(financial_ref),
            "memory_is_authority": False,
            "financial_authority_effect": "none",
            "credential_material_in_memory": False,
            "route_or_approval_from_memory": False,
        }

    def request_advisory_surface_financial_action(self, *, mission_id: str, source: str, requested_action: str) -> None:
        self.kernel.store.load_record(mission_id)
        blocked = {"voice", "desktop", "browser", "channel", "skill", "worker", "daemon", "scheduler", "memory", "llm"}
        if source in blocked:
            raise FinancialAuthorityRuntimeError("financial_advisory_surface_blocked")
        raise FinancialAuthorityRuntimeError("financial_surface_not_approved")

    def _spend_checkpoints(
        self,
        mission_id: str,
        config: FinancialAuthorityConfig,
        request: SpendRequest,
    ) -> list[FinancialCheckpoint]:
        checkpoints = build_financial_checkpoints(mission_id, request.boundary_descriptors)
        if config.budget_policy.max_single_amount_minor and request.amount_minor > config.budget_policy.max_single_amount_minor:
            checkpoints.append(self._checkpoint(mission_id, "amount_above_cap", "budget"))
        if config.budget_policy.currency != request.currency:
            checkpoints.append(self._checkpoint(mission_id, "currency_mismatch_checkpoint_required", "budget"))
        allowed_merchants = set(config.merchant_policy.allowed_merchants or config.allowed_merchants)
        if allowed_merchants and request.merchant_ref not in allowed_merchants and config.merchant_policy.checkpoint_for_new_merchant:
            checkpoints.append(self._checkpoint(mission_id, "new_merchant_checkpoint_required", "merchant"))
        allowed_recipients = set(config.recipient_policy.allowed_recipients or config.allowed_recipients)
        if allowed_recipients and request.recipient_ref not in allowed_recipients and config.recipient_policy.checkpoint_for_new_recipient:
            checkpoints.append(self._checkpoint(mission_id, "new_recipient_checkpoint_required", "recipient"))
        existing = self._load_all(mission_id, "spend_plans", SpendPlan)
        if len(existing) >= config.velocity_policy.max_plans_per_mission:
            checkpoints.append(self._checkpoint(mission_id, "velocity_limit_checkpoint_required", "velocity"))
        return _dedupe_checkpoints(checkpoints)

    def _trade_findings(
        self,
        mission_id: str,
        config: FinancialAuthorityConfig,
        request: TradingRequest,
    ) -> tuple[list[FinancialCheckpoint], list[str], bool]:
        checkpoints: list[FinancialCheckpoint] = []
        reasons: list[str] = []
        blocked = False
        if request.margin_requested:
            reasons.append("margin_leverage_blocked")
            blocked = True
        if request.asset_class in {"option", "options", "future", "futures", "derivative", "crypto_derivative"}:
            reasons.append("options_derivatives_blocked")
            blocked = True
        if request.symbol not in set(config.instrument_policy.allowed_symbols or config.allowed_instruments):
            checkpoints.append(self._checkpoint(mission_id, "new_instrument_checkpoint_required", "instrument"))
        if request.order_type not in set(config.instrument_policy.allowed_order_types):
            if request.order_type == "market" and config.instrument_policy.allow_market_order_with_checkpoint:
                checkpoints.append(self._checkpoint(mission_id, "market_order_checkpoint_required", "order_type"))
            else:
                reasons.append("order_type_blocked")
                blocked = True
        reasons.extend(checkpoint.reason for checkpoint in checkpoints)
        return _dedupe_checkpoints(checkpoints), list(dict.fromkeys(reasons)), blocked

    def _checkpoint(self, mission_id: str, reason: str, kind: str) -> FinancialCheckpoint:
        return FinancialCheckpoint(
            mission_id=mission_id,
            reason=reason,
            checkpoint_kind=kind,
            safe_summary=f"Financial checkpoint required for {kind}.",
        ).with_hash()

    def _persist_checkpoints(self, mission_id: str, checkpoints: list[FinancialCheckpoint]) -> None:
        for checkpoint in checkpoints:
            self.store.write(mission_id, "checkpoints", checkpoint.checkpoint_id, checkpoint.safe_model_dump())
            self.store.append_event(
                mission_id,
                "financial_checkpoint_created",
                "Financial human checkpoint created.",
                metadata={"checkpoint_id": checkpoint.checkpoint_id, "reason": checkpoint.reason, "kind": checkpoint.checkpoint_kind},
            )

    def _reserve_idempotency(
        self,
        *,
        mission_id: str,
        action_kind: FinancialActionKind,
        nonce: str,
        action_hash: str,
    ) -> FinancialIdempotencyRecord:
        key_hash = stable_hash({"mission_id": mission_id, "action_kind": action_kind.value, "nonce": nonce})
        for existing in self._load_all(mission_id, "idempotency", FinancialIdempotencyRecord):
            if existing.key_hash == key_hash and existing.action_hash == action_hash and existing.reserved:
                self.store.append_event(
                    mission_id,
                    "payment_duplicate_blocked",
                    "Financial duplicate action blocked by idempotency hash.",
                    metadata={"existing_record_id": existing.record_id, "action_kind": action_kind.value},
                )
                self._record_metric(mission_id, TelemetryMetricKind.PAYMENT_DUPLICATE_BLOCK_COUNT, 1, "Payment duplicate block count sample.")
                raise FinancialAuthorityRuntimeError("financial_duplicate_action_blocked")
        return FinancialIdempotencyRecord(
            mission_id=mission_id,
            action_kind=action_kind,
            key_hash=key_hash,
            action_hash=action_hash,
        ).with_hash()

    def _load_config(self, mission_id: str, config_id: str) -> FinancialAuthorityConfig:
        config = self._load_one(mission_id, "configs", config_id, FinancialAuthorityConfig)
        if not config.verify_hash():
            raise FinancialAuthorityRuntimeError("financial_authority_config_hash_mismatch")
        return config

    def _load_one(self, mission_id: str, category: str, item_id: str, model: Any) -> Any:
        return model.model_validate_json(self.store.item_path(mission_id, category, item_id).read_text(encoding="utf-8"))

    def _load_all(self, mission_id: str, category: str, model: Any) -> list[Any]:
        root = self.store.root(mission_id) / category
        if not root.exists():
            return []
        return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(root.glob("*.json"))]

    def _assert_authority(self, mission_id: str, envelope: MissionAuthorityEnvelope | None, *, action: str, tool: str) -> None:
        if envelope is None:
            raise FinancialAuthorityRuntimeError("mission_authority_required")
        if envelope.id != mission_id:
            raise FinancialAuthorityRuntimeError("mission_authority_mismatch")
        if envelope.revoked_at is not None:
            raise FinancialAuthorityRuntimeError("mission_authority_revoked")
        if envelope.resolved_expires_at() <= financial_utc_now():
            raise FinancialAuthorityRuntimeError("mission_authority_expired")
        record = self.kernel.store.load_record(mission_id)
        if record.status is OperatorMissionStatus.KILLED:
            raise FinancialAuthorityRuntimeError("mission_killed")
        if self.kernel.is_terminal(mission_id):
            raise FinancialAuthorityRuntimeError(f"mission_terminal:{record.status.value}")
        if tool not in set(envelope.allowed_tools):
            raise FinancialAuthorityRuntimeError("mission_authority_missing_financial_tool")
        if action not in set(envelope.allowed_actions):
            raise FinancialAuthorityRuntimeError("mission_authority_missing_financial_action")
        forbidden = {"live_money", "live_trade", "card_testing", "market_manipulation", "mfa_bypass", "kyc_bypass"}
        if forbidden.intersection(set(envelope.allowed_actions)):
            raise FinancialAuthorityRuntimeError("mission_authority_contains_forbidden_financial_action")

    def _assert_surface(self, config: FinancialAuthorityConfig, surface_kind: Any) -> None:
        if surface_kind not in set(config.allowed_surfaces):
            raise FinancialAuthorityRuntimeError("financial_surface_not_allowed")

    def _assert_certified_telemetry(self) -> None:
        sink = getattr(self.kernel, "telemetry_sink", None)
        if sink is None or not hasattr(sink, "require_certified_mode"):
            raise FinancialAuthorityRuntimeError("telemetry_certified_mode_required")
        try:
            sink.require_certified_mode()
        except Exception as exc:
            raise FinancialAuthorityRuntimeError("telemetry_certified_mode_required") from exc

    def _scan_or_raise(self, payload: Any) -> None:
        rendered = str(payload)
        if "[REDACTED_SECRET]" in rendered:
            raise FinancialAuthorityRuntimeError("unsafe_financial_payload:redaction_hit")
        scan = scan_financial_payload(payload)
        if not scan.valid:
            raise FinancialAuthorityRuntimeError(f"unsafe_financial_payload:{','.join(scan.reasons)}")

    def _certify_spend(self, receipt: SpendReceipt) -> FinancialFinalGateCertificate:
        reasons: list[str] = []
        if receipt.authority_effect != "none" or receipt.can_grant_authority or receipt.can_execute:
            reasons.append("receipt_authority_violation")
        if receipt.live_money_executed or receipt.live_provider_called or receipt.raw_credential_persisted or receipt.raw_payment_data_persisted:
            reasons.append("spend_receipt_live_or_sensitive_violation")
        if receipt.status is FinancialPlanStatus.EXECUTED and not receipt.sandbox_or_paper:
            reasons.append("spend_receipt_not_sandbox")
        if receipt.credential_lease_ref_hash and not receipt.secret_use_receipt_ref:
            reasons.append("spend_receipt_missing_secret_use_ref")
        decision = FinancialFinalGateDecision.REJECTED_UNSAFE_RECEIPT if reasons else FinancialFinalGateDecision.CERTIFIED_SANDBOX_SPEND
        certificate = FinancialFinalGateCertificate(
            mission_id=receipt.mission_id,
            receipt_id=receipt.receipt_id,
            decision=decision,
            certified=not reasons,
            reasons=reasons,
            receipt_hash=receipt.receipt_hash,
        ).with_hash()
        self.store.append_event(
            receipt.mission_id,
            "finalgate_passed" if certificate.certified else "finalgate_failed",
            "Financial spend FinalGate certificate recorded.",
            metadata={"receipt_id": receipt.receipt_id, "certified": certificate.certified},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        return certificate

    def _certify_trade(self, receipt: TradeOrderReceipt) -> FinancialFinalGateCertificate:
        reasons: list[str] = []
        if receipt.authority_effect != "none" or receipt.can_grant_authority or receipt.can_execute:
            reasons.append("receipt_authority_violation")
        if receipt.live_broker_order_submitted or receipt.live_provider_called or receipt.raw_credential_persisted or receipt.raw_provider_response_persisted:
            reasons.append("trade_receipt_live_or_sensitive_violation")
        if receipt.status is FinancialPlanStatus.EXECUTED and not receipt.sandbox_or_paper:
            reasons.append("trade_receipt_not_paper")
        decision = FinancialFinalGateDecision.REJECTED_UNSAFE_RECEIPT if reasons else FinancialFinalGateDecision.CERTIFIED_PAPER_TRADE
        certificate = FinancialFinalGateCertificate(
            mission_id=receipt.mission_id,
            receipt_id=receipt.receipt_id,
            decision=decision,
            certified=not reasons,
            reasons=reasons,
            receipt_hash=receipt.receipt_hash,
        ).with_hash()
        self.store.append_event(
            receipt.mission_id,
            "finalgate_passed" if certificate.certified else "finalgate_failed",
            "Financial trade FinalGate certificate recorded.",
            metadata={"receipt_id": receipt.receipt_id, "certified": certificate.certified},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[certificate.certificate_id],
        )
        return certificate

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = self.kernel.store.telemetry_sink
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.FINANCIAL_AUTHORITY,
                domain=TelemetryDomain.SAFETY,
                metric_kind=metric_kind,
                value=value,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )


def _dedupe_checkpoints(checkpoints: list[FinancialCheckpoint]) -> list[FinancialCheckpoint]:
    rendered: dict[str, FinancialCheckpoint] = {}
    for checkpoint in checkpoints:
        rendered.setdefault(checkpoint.reason, checkpoint)
    return list(rendered.values())


def _safe_event_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        probe = {key: value}
        scan = scan_forbidden_payload_categorized(probe, path="$")
        if scan["all"]:
            safe[f"{key}_hash"] = stable_hash(value)
        else:
            safe[key] = value
    return safe


__all__ = [
    "FinancialAuthorityRuntime",
    "FinancialAuthorityRuntimeError",
    "FinancialAuthorityStore",
]
