from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    AssetPolicy,
    BrokerContract,
    MaxLossPolicy,
    PaperTradeProvider,
    PositionSizingPolicy,
    StopLossPolicy,
    TradeJournal,
    TradingReceipt,
    TradingSpecialAuthority,
)


def authority(**overrides) -> TradingSpecialAuthority:
    data = {
        "mission_id": "mission_p6i",
        "root_authority_id": "root_trade_1",
        "broker": "PaperBroker",
        "exchange": "paper_exchange",
        "allowed_asset_classes": ["equity"],
        "allowed_symbols": ["AAPL"],
        "max_capital_usd": 100.0,
        "max_loss_usd": 10.0,
        "leverage_allowed": False,
        "expires_at": datetime.now(UTC) + timedelta(hours=2),
        "evidence_refs": ["ev_trading_authority"],
    }
    data.update(overrides)
    return TradingSpecialAuthority(**data)


def test_trading_special_authority_requires_explicit_broker_asset_caps_loss_and_expiry():
    auth = authority()

    assert auth.broker == "PaperBroker"
    assert auth.max_capital_usd == 100.0
    assert auth.max_loss_usd == 10.0
    assert auth.paper_trading_only is True
    assert auth.real_trading_enabled is False
    assert auth.leverage_allowed is False


def test_broker_contract_is_paper_first_and_real_disabled_by_default():
    contract = BrokerContract(broker="PaperBroker", exchange="paper_exchange", evidence_refs=["ev_broker"])

    assert contract.paper_provider is True
    assert contract.real_provider_enabled is False

    with pytest.raises(ValueError, match="real broker provider"):
        BrokerContract(broker="LiveBroker", exchange="live", real_provider_enabled=True, evidence_refs=["ev_broker"])


def test_asset_policy_blocks_unapproved_asset_class_or_symbol():
    policy = AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["ev_asset"])

    assert policy.evaluate(asset_class="equity", symbol="AAPL").accepted is True
    assert policy.evaluate(asset_class="crypto", symbol="BTC").accepted is False
    assert "asset_class_not_allowed:crypto" in policy.evaluate(asset_class="crypto", symbol="BTC").errors


def test_position_sizing_reduces_exposure_for_volatility_and_risk():
    sizing = PositionSizingPolicy(base_fraction=0.5, evidence_refs=["ev_size"])

    calm = sizing.size(authority(), volatility=0.1, confidence=0.8)
    volatile = sizing.size(authority(), volatility=0.8, confidence=0.8)

    assert calm > volatile
    assert volatile <= authority().max_capital_usd


def test_max_loss_and_stop_loss_are_required():
    with pytest.raises(ValueError, match="max loss"):
        MaxLossPolicy(max_loss_usd=0.0, evidence_refs=["ev_loss"])

    with pytest.raises(ValueError, match="stop-loss"):
        StopLossPolicy(stop_loss_percent=0.0, evidence_refs=["ev_stop"])


def test_no_leverage_unless_explicitly_authorized():
    provider = PaperTradeProvider()
    auth = authority(leverage_allowed=False)

    with pytest.raises(ValueError, match="leverage not authorized"):
        provider.paper_trade(
            authority=auth,
            broker_contract=BrokerContract(broker="PaperBroker", exchange="paper_exchange", evidence_refs=["ev_broker"]),
            asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["ev_asset"]),
            position_sizing=PositionSizingPolicy(base_fraction=0.2, evidence_refs=["ev_size"]),
            max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["ev_loss"]),
            stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["ev_stop"]),
            journal=TradeJournal(mission_id=auth.mission_id),
            symbol="AAPL",
            asset_class="equity",
            side="buy",
            confidence=0.8,
            volatility=0.2,
            leverage=2.0,
            thesis="Paper test",
            evidence_refs=["ev_trade"],
            trace_refs=["trace_trade"],
        )


def test_profit_guarantee_claim_is_blocked():
    provider = PaperTradeProvider()

    with pytest.raises(ValueError, match="profit guarantee"):
        provider.paper_trade(
            authority=authority(),
            broker_contract=BrokerContract(broker="PaperBroker", exchange="paper_exchange", evidence_refs=["ev_broker"]),
            asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["ev_asset"]),
            position_sizing=PositionSizingPolicy(base_fraction=0.2, evidence_refs=["ev_size"]),
            max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["ev_loss"]),
            stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["ev_stop"]),
            journal=TradeJournal(mission_id="mission_p6i"),
            symbol="AAPL",
            asset_class="equity",
            side="buy",
            confidence=0.8,
            volatility=0.2,
            leverage=1.0,
            thesis="Guaranteed profit setup",
            evidence_refs=["ev_trade"],
            trace_refs=["trace_trade"],
        )


def test_paper_trade_receipt_is_deterministic_and_no_real_trade():
    auth = authority()
    journal = TradeJournal(mission_id=auth.mission_id)
    receipt = PaperTradeProvider().paper_trade(
        authority=auth,
        broker_contract=BrokerContract(broker="PaperBroker", exchange="paper_exchange", evidence_refs=["ev_broker"]),
        asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["ev_asset"]),
        position_sizing=PositionSizingPolicy(base_fraction=0.2, evidence_refs=["ev_size"]),
        max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["ev_loss"]),
        stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["ev_stop"]),
        journal=journal,
        symbol="AAPL",
        asset_class="equity",
        side="buy",
        confidence=0.8,
        volatility=0.2,
        leverage=1.0,
        thesis="Paper test with stop-loss.",
        evidence_refs=["ev_trade"],
        trace_refs=["trace_trade"],
    )

    assert receipt.paper_trade is True
    assert receipt.real_trade_started is False
    assert receipt.receipt_hash == receipt.expected_hash()
    assert len(journal.entries) == 1


def test_missing_authority_creates_proposal_only():
    proposal = TradingSpecialAuthority.propose_missing_authority(
        mission_id="mission_p6i",
        requested_broker="LiveBroker",
        requested_asset_class="equity",
        requested_symbol="AAPL",
        evidence_refs=["ev_proposal"],
    )

    assert proposal.proposal_only is True
    assert proposal.real_trade_started is False
    assert "missing_trading_special_authority" in proposal.reasons


def test_expired_authority_and_missing_stop_loss_block_trade():
    provider = PaperTradeProvider()
    common = {
        "broker_contract": BrokerContract(broker="PaperBroker", exchange="paper_exchange", evidence_refs=["ev_broker"]),
        "asset_policy": AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["ev_asset"]),
        "position_sizing": PositionSizingPolicy(base_fraction=0.2, evidence_refs=["ev_size"]),
        "max_loss": MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["ev_loss"]),
        "journal": TradeJournal(mission_id="mission_p6i"),
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

    with pytest.raises(ValueError, match="trading authority expired"):
        provider.paper_trade(
            authority=authority(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
            stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["ev_stop"]),
            **common,
        )
    with pytest.raises(ValueError, match="stop-loss"):
        provider.paper_trade(authority=authority(), stop_loss=None, **common)


def test_trading_receipt_rejects_authority_expansion_and_requires_trace_refs():
    with pytest.raises(ValueError, match="cannot expand authority"):
        TradingReceipt(
            mission_id="mission",
            broker="PaperBroker",
            exchange="paper_exchange",
            symbol="AAPL",
            asset_class="equity",
            side="buy",
            notional_usd=10.0,
            max_loss_usd=1.0,
            stop_loss_percent=5.0,
            evidence_refs=["ev"],
            trace_refs=["trace"],
            authority_expansion=True,
        )

    with pytest.raises(ValueError, match="requires trace refs"):
        TradingReceipt(
            mission_id="mission",
            broker="PaperBroker",
            exchange="paper_exchange",
            symbol="AAPL",
            asset_class="equity",
            side="buy",
            notional_usd=10.0,
            max_loss_usd=1.0,
            stop_loss_percent=5.0,
            evidence_refs=["ev"],
            trace_refs=[],
        )
