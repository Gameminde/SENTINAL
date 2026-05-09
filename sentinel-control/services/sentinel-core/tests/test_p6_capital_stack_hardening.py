from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    AdaptiveOperatingEnvelope,
    AssetPolicy,
    BrokerContract,
    BudgetReallocator,
    CapitalOpportunity,
    CapitalRiskReview,
    CapitalSignal,
    DynamicSpendPolicy,
    FakeSpendProvider,
    MaxLossPolicy,
    OpportunityPortfolio,
    PaperTradeProvider,
    PositionSizingPolicy,
    RefundCancelPath,
    SignalLedger,
    SpendAuthorityEnvelope,
    SpendKillSwitch,
    SpendRequest,
    StopLossPolicy,
    SubscriptionGuard,
    TradeJournal,
    TradingSpecialAuthority,
)


def signal(signal_id: str = "sig_roi", strength: float = 0.8) -> CapitalSignal:
    return CapitalSignal(
        id=signal_id,
        signal_type="roi",
        source="hardening_fixture",
        strength=strength,
        summary="Hardening signal.",
        evidence_refs=["ev_signal"],
    )


def opportunity(**overrides) -> CapitalOpportunity:
    data = {
        "name": "Revenue experiment",
        "category": "ads",
        "expected_profit_or_progress": 100.0,
        "expected_information_gain": 0.6,
        "downside_risk": 0.2,
        "proposed_spend_usd": 25.0,
        "confidence": 0.7,
        "evidence_refs": ["ev_opp"],
        "signal_refs": ["sig_roi"],
    }
    data.update(overrides)
    return CapitalOpportunity(**data)


def envelope(**overrides) -> AdaptiveOperatingEnvelope:
    data = {
        "root_budget_max_usd": 100.0,
        "budget_remaining_usd": 100.0,
        "max_single_transaction_usd": 25.0,
        "sub_budgets": {"existing": 20.0},
        "exploration_fraction": 0.4,
        "stop_loss_usd": 25.0,
        "signal_refs": ["sig_initial"],
        "evidence_refs": ["ev_envelope"],
    }
    data.update(overrides)
    return AdaptiveOperatingEnvelope(**data)


def spend_authority(**overrides) -> SpendAuthorityEnvelope:
    data = {
        "mission_id": "mission_spend",
        "root_authority_id": "root_spend",
        "budget_max_usd": 100.0,
        "budget_remaining_usd": 100.0,
        "max_single_transaction_usd": 25.0,
        "allowed_categories": ["api"],
        "allowed_vendors": ["Vendor"],
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "credential_ref": "cred_allowed",
        "evidence_refs": ["ev_spend_authority"],
    }
    data.update(overrides)
    return SpendAuthorityEnvelope(**data)


def spend_request(**overrides) -> SpendRequest:
    data = {
        "vendor": "Vendor",
        "category": "api",
        "amount_usd": 10.0,
        "purpose": "Buy API trial.",
        "expected_information_gain": 0.7,
        "evidence_refs": ["ev_spend_request"],
        "signal_refs": ["sig_roi"],
        "credential_ref": "cred_allowed",
    }
    data.update(overrides)
    return SpendRequest(**data)


def trading_authority(**overrides) -> TradingSpecialAuthority:
    data = {
        "mission_id": "mission_trade",
        "root_authority_id": "root_trade",
        "broker": "PaperBroker",
        "exchange": "paper",
        "allowed_asset_classes": ["equity"],
        "allowed_symbols": ["AAPL"],
        "max_capital_usd": 100.0,
        "max_loss_usd": 10.0,
        "leverage_allowed": False,
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "evidence_refs": ["ev_trade_authority"],
    }
    data.update(overrides)
    return TradingSpecialAuthority(**data)


def paper_trade(**overrides):
    auth = overrides.pop("authority", trading_authority())
    data = {
        "authority": auth,
        "broker_contract": BrokerContract(broker="PaperBroker", exchange="paper", evidence_refs=["ev_broker"]),
        "asset_policy": AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["ev_asset"]),
        "position_sizing": PositionSizingPolicy(base_fraction=0.2, evidence_refs=["ev_size"]),
        "max_loss": MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["ev_loss"]),
        "stop_loss": StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["ev_stop"]),
        "journal": TradeJournal(mission_id=auth.mission_id),
        "symbol": "AAPL",
        "asset_class": "equity",
        "side": "buy",
        "confidence": 0.8,
        "volatility": 0.2,
        "leverage": 1.0,
        "thesis": "Paper test.",
        "evidence_refs": ["ev_trade"],
        "trace_refs": ["trace_trade"],
    }
    data.update(overrides)
    return PaperTradeProvider().paper_trade(**data)


def test_dynamic_spend_rejects_unmatched_signal_refs():
    ledger = SignalLedger().record(signal("other_sig", strength=0.9))

    with pytest.raises(ValueError, match="signal refs not found"):
        DynamicSpendPolicy().propose(opportunity(signal_refs=["missing_sig"]), envelope(), ledger)


def test_budget_reallocator_cannot_overallocate_sub_budgets():
    ledger = SignalLedger().record(signal("sig_roi", strength=1.0))
    portfolio = OpportunityPortfolio(opportunities=[opportunity(signal_refs=["sig_roi"])], evidence_refs=["ev_portfolio"])
    constrained = envelope(sub_budgets={"existing": 95.0}, budget_remaining_usd=100.0)

    updated = BudgetReallocator().reallocate(constrained, portfolio, ledger)

    assert sum(updated.sub_budgets.values()) <= updated.budget_remaining_usd
    assert updated.sub_budgets["ads"] == 5.0


def test_spend_rejects_kill_switch_from_different_mission():
    with pytest.raises(ValueError, match="kill switch mission mismatch"):
        FakeSpendProvider().execute(
            spend_request(),
            spend_authority(),
            kill_switch=SpendKillSwitch(mission_id="different_mission"),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["refund"], evidence_refs=["ev_refund"]),
            trace_refs=["trace_spend"],
        )


def test_spend_rejects_credential_ref_outside_authority():
    with pytest.raises(ValueError, match="credential_ref_not_allowed"):
        FakeSpendProvider().execute(
            spend_request(credential_ref="cred_not_allowed"),
            spend_authority(credential_ref="cred_allowed"),
            kill_switch=SpendKillSwitch(mission_id="mission_spend"),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["refund"], evidence_refs=["ev_refund"]),
            trace_refs=["trace_spend"],
        )


def test_trading_provider_enforces_authority_asset_scope_not_just_policy():
    with pytest.raises(ValueError, match="authority_symbol_not_allowed:MSFT"):
        paper_trade(
            asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["MSFT"], evidence_refs=["ev_asset"]),
            symbol="MSFT",
        )


def test_trading_provider_enforces_authority_max_leverage():
    auth = trading_authority(leverage_allowed=True, max_leverage=2.0)

    with pytest.raises(ValueError, match="max leverage exceeded"):
        paper_trade(authority=auth, leverage=10.0)


def test_capital_and_trading_flag_broader_profit_guarantees():
    review = CapitalRiskReview.review(opportunity(objective_text="Guaranteed returns and 100% win rate."))

    assert review.profit_guarantee_flagged is True
    assert "profit_guarantee_claim" in review.risk_flags

    with pytest.raises(ValueError, match="profit guarantee"):
        paper_trade(thesis="Riskless income and 100% win rate.")
