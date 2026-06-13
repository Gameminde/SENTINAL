from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.credential_vault import CredentialVaultRuntime
from sentinel.operator.credential_vault_models import (
    CredentialConsumerKind,
    CredentialScopePolicy,
    CredentialUseRiskProfile,
    CredentialVaultConfig,
    CredentialVaultMaturity,
    SecretKind,
    SecretSensitivity,
    SecretUseContext,
    SecretUsePolicy,
    VaultUnlockPolicy,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft


def test_financial_authority_initialization_and_modes_are_data_not_authority(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntime
    from sentinel.operator.financial_authority_models import (
        FinancialAuthorityConfig,
        FinancialAuthorityMode,
        FinancialSurfaceKind,
    )

    runtime, mission_id = _runtime(tmp_path)
    config = runtime.register_config(
        mission_id=mission_id,
        config=FinancialAuthorityConfig(
            default_mode=FinancialAuthorityMode.PLAN_ONLY,
            allowed_modes=[FinancialAuthorityMode.PLAN_ONLY, FinancialAuthorityMode.SANDBOX_ONLY],
            allowed_surfaces=[FinancialSurfaceKind.BROWSER],
            allowed_merchants=["Example Shop"],
            allowed_recipients=["Example Vendor"],
            allowed_instruments=["AAPL"],
        ),
    )

    assert isinstance(runtime, FinancialAuthorityRuntime)
    assert config.data_not_authority is True
    assert config.can_grant_authority is False
    assert config.can_execute is False
    assert FinancialAuthorityMode.LIVE_MONEY_SPECIAL_AUTHORITY_LOCKED.value == "live_money_special_authority_locked"


def test_spend_and_trade_require_mission_authority_envelope(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)

    with pytest.raises(FinancialAuthorityRuntimeError, match="mission_authority_required"):
        runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(), envelope=None)

    with pytest.raises(FinancialAuthorityRuntimeError, match="mission_authority_required"):
        runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(), envelope=None)


def test_spend_and_trade_block_without_financial_scope(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    envelope = _envelope(mission_id).model_copy(update={"allowed_actions": ["financial_plan"]})

    with pytest.raises(FinancialAuthorityRuntimeError, match="mission_authority_missing_financial_action"):
        runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(), envelope=envelope)

    with pytest.raises(FinancialAuthorityRuntimeError, match="mission_authority_missing_financial_action"):
        runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(), envelope=envelope)


def test_spend_plan_enforces_amount_caps_merchant_policy_and_velocity(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)

    ok = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(amount_minor=2500), envelope=_envelope(mission_id))
    over_cap = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(amount_minor=12500), envelope=_envelope(mission_id))
    new_merchant = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(merchant_ref="New Merchant"), envelope=_envelope(mission_id))
    velocity = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(idempotency_nonce="spend-velocity-2"), envelope=_envelope(mission_id))

    assert ok.status.value == "ready"
    assert over_cap.status.value == "checkpoint_required"
    assert "amount_above_cap" in {checkpoint.reason for checkpoint in over_cap.checkpoints}
    assert new_merchant.status.value == "checkpoint_required"
    assert "new_merchant_checkpoint_required" in {checkpoint.reason for checkpoint in new_merchant.checkpoints}
    assert velocity.status.value == "checkpoint_required"
    assert "velocity_limit_checkpoint_required" in {checkpoint.reason for checkpoint in velocity.checkpoints}


def test_trade_plan_enforces_instrument_order_type_and_default_blocks_margin_options(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)

    ok = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(symbol="AAPL", order_type="limit"), envelope=_envelope(mission_id))
    market = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(symbol="AAPL", order_type="market"), envelope=_envelope(mission_id))
    blocked_symbol = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(symbol="TSLA", order_type="limit"), envelope=_envelope(mission_id))
    margin = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(symbol="AAPL", margin_requested=True), envelope=_envelope(mission_id))
    options = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(symbol="AAPL", asset_class="option"), envelope=_envelope(mission_id))

    assert ok.status.value == "ready"
    assert market.status.value == "checkpoint_required"
    assert "market_order_checkpoint_required" in {checkpoint.reason for checkpoint in market.checkpoints}
    assert blocked_symbol.status.value == "checkpoint_required"
    assert "new_instrument_checkpoint_required" in {checkpoint.reason for checkpoint in blocked_symbol.checkpoints}
    assert margin.status.value == "blocked"
    assert "margin_leverage_blocked" in margin.risk_profile.risk_reasons
    assert options.status.value == "blocked"
    assert "options_derivatives_blocked" in options.risk_profile.risk_reasons


def test_payment_method_uses_credential_vault_lease_refs_only(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    vault, secret_id, unlock_session_id = _credential_vault_with_financial_secret(runtime.kernel, mission_id)
    grant = vault.request_secret_access(
        mission_id=mission_id,
        secret_id=secret_id,
        consumer_kind=CredentialConsumerKind.EXTERNAL_API,
        consumer_ref="financial_authority_final_consumer",
        purpose="financial_spend",
        requested_scope=["payment_method:pm_example"],
        envelope=_envelope(mission_id),
        unlock_session_id=unlock_session_id,
        context=SecretUseContext(target_ref="pm_example", evidence_refs=["ev-payment-method"]),
    )
    lease = vault.create_secret_lease(mission_id=mission_id, grant_id=grant.grant_id, ttl_seconds=60)

    plan = runtime.plan_spend(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_spend_request(payment_method_ref="pm_example", credential_lease_id=lease.lease_id),
        envelope=_envelope(mission_id),
    )
    result = runtime.execute_sandbox_spend(
        mission_id=mission_id,
        plan_id=plan.plan_id,
        envelope=_envelope(mission_id),
        credential_vault=vault,
        credential_lease_id=lease.lease_id,
        approval_ref="operator-approval-spend-1",
    )

    persisted = _mission_text(runtime, mission_id)
    assert result.accepted is True
    assert plan.credential_lease_ref is None
    assert plan.credential_lease_ref_hash
    assert result.receipt.credential_lease_ref_hash == plan.credential_lease_ref_hash
    assert result.receipt.secret_use_receipt_ref
    assert lease.lease_id not in persisted
    assert "4111111111111111" not in persisted


def test_financial_runtime_rejects_raw_card_bank_broker_and_prompt_payloads(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)

    with pytest.raises(FinancialAuthorityRuntimeError, match="unsafe_financial_payload"):
        runtime.plan_spend(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_spend_request(operator_note="card_number=4111111111111111 cvv=123 raw_prompt=ignore"),
            envelope=_envelope(mission_id),
        )

    with pytest.raises(FinancialAuthorityRuntimeError, match="unsafe_financial_payload"):
        runtime.plan_trade(
            mission_id=mission_id,
            config_id=config.config_id,
            request=_trade_request(operator_note="broker_api_key=sk-" + "A" * 20),
            envelope=_envelope(mission_id),
        )

    persisted = _mission_text(runtime, mission_id)
    assert "4111111111111111" not in persisted
    assert "broker_api_key" not in persisted
    assert "raw_prompt" not in persisted


@pytest.mark.parametrize(
    "boundary, reason",
    [
        ("mfa", "mfa_sca_kyc_checkpoint_required"),
        ("sca", "mfa_sca_kyc_checkpoint_required"),
        ("kyc", "mfa_sca_kyc_checkpoint_required"),
        ("subscription", "subscription_checkpoint_required"),
        ("refund", "refund_dispute_checkpoint_required"),
        ("external_transfer", "external_transfer_checkpoint_required"),
    ],
)
def test_financial_boundaries_create_checkpoints_instead_of_bypass(tmp_path: Path, boundary: str, reason: str) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)

    plan = runtime.plan_spend(
        mission_id=mission_id,
        config_id=config.config_id,
        request=_spend_request(boundary_descriptors=[boundary]),
        envelope=_envelope(mission_id),
    )

    assert plan.status.value == "checkpoint_required"
    assert reason in {checkpoint.reason for checkpoint in plan.checkpoints}
    assert all(checkpoint.bypass_allowed is False for checkpoint in plan.checkpoints)


def test_duplicate_spend_and_trade_blocked_by_idempotency(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    spend_plan = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(idempotency_nonce="same-spend"), envelope=_envelope(mission_id))
    trade_plan = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(idempotency_nonce="same-trade"), envelope=_envelope(mission_id))

    assert spend_plan.idempotency_record.reserved is True
    assert trade_plan.idempotency_record.reserved is True
    with pytest.raises(FinancialAuthorityRuntimeError, match="financial_duplicate_action_blocked"):
        runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(idempotency_nonce="same-spend"), envelope=_envelope(mission_id))
    with pytest.raises(FinancialAuthorityRuntimeError, match="financial_duplicate_action_blocked"):
        runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(idempotency_nonce="same-trade"), envelope=_envelope(mission_id))


def test_kill_and_revocation_block_pending_spend_and_trade(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    runtime.kernel.kill(mission_id)
    with pytest.raises(FinancialAuthorityRuntimeError, match="mission_killed"):
        runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(), envelope=_envelope(mission_id))

    runtime2, mission_id2 = _runtime(tmp_path)
    config2 = _register_config(runtime2, mission_id2)
    revoked = _envelope(mission_id2).model_copy(update={"revoked_at": datetime.now(UTC)})
    with pytest.raises(FinancialAuthorityRuntimeError, match="mission_authority_revoked"):
        runtime2.plan_trade(mission_id=mission_id2, config_id=config2.config_id, request=_trade_request(), envelope=revoked)


def test_sandbox_spend_and_paper_trade_execute_only_fake_results(tmp_path: Path) -> None:
    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    spend_plan = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(), envelope=_envelope(mission_id))
    trade_plan = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(), envelope=_envelope(mission_id))

    spend = runtime.execute_sandbox_spend(mission_id=mission_id, plan_id=spend_plan.plan_id, envelope=_envelope(mission_id), approval_ref="approval-spend")
    trade = runtime.execute_paper_trade(mission_id=mission_id, plan_id=trade_plan.plan_id, envelope=_envelope(mission_id), approval_ref="approval-trade")

    assert spend.accepted is True
    assert spend.receipt.sandbox_or_paper is True
    assert spend.receipt.live_money_executed is False
    assert spend.finalgate_certificate is not None
    assert spend.finalgate_certificate.certified is True
    assert trade.accepted is True
    assert trade.receipt.sandbox_or_paper is True
    assert trade.receipt.live_broker_order_submitted is False
    assert trade.finalgate_certificate is not None
    assert trade.finalgate_certificate.certified is True


@pytest.mark.parametrize("source", ["voice", "desktop", "browser", "channel", "skill", "worker", "daemon", "scheduler", "memory", "llm"])
def test_advisory_surfaces_cannot_approve_or_execute_financial_actions(tmp_path: Path, source: str) -> None:
    from sentinel.operator.financial_authority import FinancialAuthorityRuntimeError

    runtime, mission_id = _runtime(tmp_path)

    with pytest.raises(FinancialAuthorityRuntimeError, match="financial_advisory_surface_blocked"):
        runtime.request_advisory_surface_financial_action(
            mission_id=mission_id,
            source=source,
            requested_action="approve_and_submit_payment",
        )


def test_memory_receipt_finalgate_telemetry_and_replay_are_not_authority(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority_replay import FinancialAuthorityReplayBuilder

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    spend_plan = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(), envelope=_envelope(mission_id))
    result = runtime.execute_sandbox_spend(mission_id=mission_id, plan_id=spend_plan.plan_id, envelope=_envelope(mission_id), approval_ref="approval-spend")
    memory_summary = runtime.build_memory_summary(mission_id=mission_id, financial_ref=result.receipt.receipt_id)
    replay = FinancialAuthorityReplayBuilder(runtime.store).build(mission_id)

    assert result.receipt.can_grant_authority is False
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.can_grant_authority is False
    assert memory_summary["memory_is_authority"] is False
    assert replay.executed_live_money is False
    assert replay.placed_live_trade is False
    assert replay.materialized_credential is False
    assert replay.replayed_financial_action is False
    assert runtime.store.verify_timeline(mission_id)


def test_telemetry_records_financial_events_and_metrics(tmp_path: Path) -> None:
    from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    spend_plan = runtime.plan_spend(mission_id=mission_id, config_id=config.config_id, request=_spend_request(), envelope=_envelope(mission_id))
    runtime.execute_sandbox_spend(mission_id=mission_id, plan_id=spend_plan.plan_id, envelope=_envelope(mission_id), approval_ref="approval-spend")
    snapshot = runtime.kernel.telemetry_sink.certified_mode_status()

    assert snapshot.event_counts_by_kind[TelemetryEventKind.FINANCIAL_ACTION_PLANNED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.SPEND_SANDBOX_EXECUTED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.FINANCIAL_REPLAY_BUILT.value] == 0
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.FINANCIAL_ACTION_REQUEST_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.SPEND_SANDBOX_EXECUTION_COUNT.value] >= 1


def test_replay_reconstructs_without_financial_execution(tmp_path: Path) -> None:
    from sentinel.operator.financial_authority_replay import FinancialAuthorityReplayBuilder
    from sentinel.telemetry.models import TelemetryEventKind

    runtime, mission_id = _runtime(tmp_path)
    config = _register_config(runtime, mission_id)
    trade_plan = runtime.plan_trade(mission_id=mission_id, config_id=config.config_id, request=_trade_request(), envelope=_envelope(mission_id))
    runtime.execute_paper_trade(mission_id=mission_id, plan_id=trade_plan.plan_id, envelope=_envelope(mission_id), approval_ref="approval-trade")

    replay = FinancialAuthorityReplayBuilder(runtime.store).build(mission_id)
    snapshot = runtime.kernel.telemetry_sink.certified_mode_status()

    assert replay.trade_plans
    assert replay.trade_receipts
    assert replay.finalgate_certificates
    assert replay.replayed_financial_action is False
    assert replay.called_live_provider is False
    assert snapshot.event_counts_by_kind[TelemetryEventKind.FINANCIAL_REPLAY_BUILT.value] >= 1


def _runtime(tmp_path: Path):
    from sentinel.operator.financial_authority import FinancialAuthorityRuntime

    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session-financial-authority",
        draft=MissionDraft(
            title="Financial authority test mission",
            objective="Exercise governed payment, spend, and paper trading authority.",
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="mission-summary",
            allowed_actions=["financial_plan", "financial_spend", "financial_trade", "credential_use"],
            forbidden_actions=["live_money", "market_manipulation", "card_testing"],
            summary="Financial authority test summary.",
        ),
    )
    return FinancialAuthorityRuntime(kernel), record.mission_id


def _register_config(runtime, mission_id: str):
    from sentinel.operator.financial_authority_models import (
        FinancialApprovalPolicy,
        FinancialAuthorityConfig,
        FinancialAuthorityMode,
        FinancialBudgetPolicy,
        FinancialInstrumentPolicy,
        FinancialMerchantPolicy,
        FinancialRecipientPolicy,
        FinancialSurfaceKind,
        FinancialVelocityPolicy,
    )

    return runtime.register_config(
        mission_id=mission_id,
        config=FinancialAuthorityConfig(
            default_mode=FinancialAuthorityMode.SANDBOX_ONLY,
            allowed_modes=[
                FinancialAuthorityMode.PLAN_ONLY,
                FinancialAuthorityMode.SANDBOX_ONLY,
                FinancialAuthorityMode.PAPER_TRADING_ONLY,
                FinancialAuthorityMode.OPERATOR_ASSISTED_SPEND,
                FinancialAuthorityMode.OPERATOR_ASSISTED_TRADE,
            ],
            allowed_surfaces=[FinancialSurfaceKind.BROWSER, FinancialSurfaceKind.DESKTOP, FinancialSurfaceKind.VOICE],
            allowed_merchants=["Example Shop"],
            allowed_recipients=["Example Vendor"],
            allowed_instruments=["AAPL"],
            budget_policy=FinancialBudgetPolicy(max_single_amount_minor=5000, max_total_amount_minor=10000, currency="USD"),
            velocity_policy=FinancialVelocityPolicy(max_plans_per_mission=1),
            merchant_policy=FinancialMerchantPolicy(allowed_merchants=["Example Shop"], checkpoint_for_new_merchant=True),
            recipient_policy=FinancialRecipientPolicy(allowed_recipients=["Example Vendor"], checkpoint_for_new_recipient=True),
            instrument_policy=FinancialInstrumentPolicy(allowed_symbols=["AAPL"], allowed_order_types=["limit"], allow_market_order_with_checkpoint=True),
            approval_policy=FinancialApprovalPolicy(operator_approval_required=True),
        ),
    )


def _spend_request(**overrides):
    from sentinel.operator.financial_authority_models import FinancialProviderKind, FinancialSurfaceKind, SpendRequest

    data = dict(
        provider_kind=FinancialProviderKind.SANDBOX,
        surface_kind=FinancialSurfaceKind.BROWSER,
        merchant_ref="Example Shop",
        recipient_ref="Example Vendor",
        payment_method_ref="pm_example",
        amount_minor=2500,
        currency="USD",
        purpose="operator_owned_test_purchase",
        idempotency_nonce="spend-1",
        boundary_descriptors=[],
        credential_lease_id=None,
        operator_note="sandbox spend only",
    )
    data.update(overrides)
    return SpendRequest(**data)


def _trade_request(**overrides):
    from sentinel.operator.financial_authority_models import FinancialProviderKind, FinancialSurfaceKind, TradingRequest

    data = dict(
        provider_kind=FinancialProviderKind.PAPER_BROKER,
        surface_kind=FinancialSurfaceKind.BROWSER,
        account_ref="paper-account",
        symbol="AAPL",
        asset_class="equity",
        side="buy",
        quantity=1,
        order_type="limit",
        limit_price_minor=18000,
        currency="USD",
        idempotency_nonce="trade-1",
        margin_requested=False,
        operator_note="paper trade only",
    )
    data.update(overrides)
    return TradingRequest(**data)


def _credential_vault_with_financial_secret(kernel: MissionKernel, mission_id: str):
    vault = CredentialVaultRuntime(kernel)
    vault.initialize_vault(mission_id=mission_id, config=CredentialVaultConfig(vault_id="financial-vault", maturity=CredentialVaultMaturity.FAKE_SEALED_STORE))
    metadata = vault.register_secret(
        mission_id=mission_id,
        kind=SecretKind.PAYMENT_METHOD_REF,
        label="Example payment method ref",
        scope_policy=CredentialScopePolicy(
            allowed_consumers=[CredentialConsumerKind.EXTERNAL_API],
            allowed_consumer_refs=["financial_authority_final_consumer"],
            allowed_purposes=["financial_spend"],
            allowed_scopes=["payment_method:pm_example"],
        ),
        use_policy=SecretUsePolicy(
            allowed_purposes=["financial_spend"],
            allowed_kinds=[SecretKind.PAYMENT_METHOD_REF],
            max_lease_seconds=120,
            require_unlock_session=True,
            require_operator_approval=False,
            risk_profile=CredentialUseRiskProfile.SPECIAL_AUTHORITY,
        ),
        sensitivity=SecretSensitivity.SPECIAL_AUTHORITY,
        provenance="operator_supplied_test_fixture",
        secret_material="4111111111111111",
    )
    requested = vault.request_unlock(
        mission_id=mission_id,
        policy=VaultUnlockPolicy(ttl_seconds=120, allowed_purposes=["financial_spend"]),
        purpose="financial_spend",
        requested_by="operator",
    )
    unlocked = vault.approve_unlock_session(
        mission_id=mission_id,
        unlock_session_id=requested.unlock_session_id,
        approval_source="operator",
    )
    return vault, metadata.secret_id, unlocked.unlock_session_id


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user-financial-authority",
        mission_title="Financial authority mission",
        mission_objective="Use sandbox spend and paper trading only under explicit authority.",
        allowed_systems=["financial_authority", "credential_vault", "browser", "desktop", "voice"],
        allowed_tools=["financial_authority", "secret_broker", "browser_payment_spend_special_authority_l7"],
        allowed_actions=["financial_plan", "financial_spend", "financial_trade", "credential_use"],
        forbidden_actions=["live_money", "live_trade", "card_testing", "market_manipulation", "mfa_bypass", "kyc_bypass"],
        allowed_domains=["shop.example.test", "broker.example.test"],
        max_duration_minutes=30,
        max_cost_usd=0.0,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
    )


def _mission_text(runtime, mission_id: str) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in runtime.store.mission_dir(mission_id, create=True).rglob("*") if path.is_file())
