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


class TradingAuthorityProposal(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tradeprop"))
    mission_id: str
    requested_broker: str
    requested_asset_class: str
    requested_symbol: str
    proposal_only: bool = True
    real_trade_started: bool = False
    reasons: list[str]
    evidence_refs: list[str]


class TradingSpecialAuthority(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tradeauth"))
    mission_id: str
    root_authority_id: str
    broker: str
    exchange: str
    allowed_asset_classes: list[str]
    allowed_symbols: list[str]
    max_capital_usd: float = Field(gt=0.0)
    max_loss_usd: float = Field(gt=0.0)
    leverage_allowed: bool = False
    max_leverage: float = Field(default=1.0, ge=1.0)
    expires_at: datetime
    paper_trading_only: bool = True
    real_trading_enabled: bool = False
    evidence_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> TradingSpecialAuthority:
        if not self.allowed_asset_classes:
            raise ValueError("TradingSpecialAuthority requires asset classes.")
        if not self.allowed_symbols:
            raise ValueError("TradingSpecialAuthority requires allowed symbols.")
        if self.real_trading_enabled:
            raise ValueError("Real trading is disabled by default.")
        if not self.leverage_allowed and self.max_leverage > 1.0:
            raise ValueError("Leverage requires explicit authority.")
        if not self.evidence_refs:
            raise ValueError("TradingSpecialAuthority requires evidence refs.")
        if self.authority_expansion:
            raise ValueError("TradingSpecialAuthority cannot expand authority.")
        return self

    @classmethod
    def propose_missing_authority(
        cls,
        *,
        mission_id: str,
        requested_broker: str,
        requested_asset_class: str,
        requested_symbol: str,
        evidence_refs: list[str],
    ) -> TradingAuthorityProposal:
        return TradingAuthorityProposal(
            mission_id=mission_id,
            requested_broker=requested_broker,
            requested_asset_class=requested_asset_class,
            requested_symbol=requested_symbol,
            reasons=["missing_trading_special_authority"],
            evidence_refs=evidence_refs,
        )


class BrokerContract(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("broker"))
    broker: str
    exchange: str
    paper_provider: bool = True
    real_provider_enabled: bool = False
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> BrokerContract:
        if self.real_provider_enabled:
            raise ValueError("real broker provider is disabled by default")
        if not self.evidence_refs:
            raise ValueError("BrokerContract requires evidence refs.")
        return self


class AssetPolicyDecision(SentinelModel):
    accepted: bool
    errors: list[str] = Field(default_factory=list)


class AssetPolicy(SentinelModel):
    allowed_asset_classes: list[str]
    allowed_symbols: list[str]
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> AssetPolicy:
        if not self.evidence_refs:
            raise ValueError("AssetPolicy requires evidence refs.")
        return self

    def evaluate(self, *, asset_class: str, symbol: str) -> AssetPolicyDecision:
        errors = []
        if asset_class not in self.allowed_asset_classes:
            errors.append(f"asset_class_not_allowed:{asset_class}")
        if symbol not in self.allowed_symbols:
            errors.append(f"symbol_not_allowed:{symbol}")
        return AssetPolicyDecision(accepted=not errors, errors=errors)


class PositionSizingPolicy(SentinelModel):
    base_fraction: float = Field(gt=0.0, le=1.0)
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> PositionSizingPolicy:
        if not self.evidence_refs:
            raise ValueError("PositionSizingPolicy requires evidence refs.")
        return self

    def size(self, authority: TradingSpecialAuthority, *, volatility: float, confidence: float) -> float:
        volatility = max(0.0, min(1.0, volatility))
        confidence = max(0.0, min(1.0, confidence))
        raw = authority.max_capital_usd * self.base_fraction * confidence * (1 - volatility)
        return round(min(authority.max_capital_usd, max(0.0, raw)), 2)


class MaxLossPolicy(SentinelModel):
    max_loss_usd: float = Field(ge=0.0)
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> MaxLossPolicy:
        if self.max_loss_usd <= 0:
            raise ValueError("max loss must be positive.")
        if not self.evidence_refs:
            raise ValueError("MaxLossPolicy requires evidence refs.")
        return self


class StopLossPolicy(SentinelModel):
    stop_loss_percent: float = Field(ge=0.0, le=100.0)
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> StopLossPolicy:
        if self.stop_loss_percent <= 0:
            raise ValueError("stop-loss must be positive.")
        if not self.evidence_refs:
            raise ValueError("StopLossPolicy requires evidence refs.")
        return self


class TradingReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tradercpt"))
    mission_id: str
    broker: str
    exchange: str
    symbol: str
    asset_class: str
    side: str
    notional_usd: float = Field(ge=0.0)
    max_loss_usd: float = Field(gt=0.0)
    stop_loss_percent: float = Field(gt=0.0)
    leverage: float = 1.0
    paper_trade: bool = True
    real_trade_started: bool = False
    evidence_refs: list[str]
    trace_refs: list[str]
    receipt_hash: str = ""
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> TradingReceipt:
        if not self.evidence_refs:
            raise ValueError("TradingReceipt requires evidence refs.")
        if not self.trace_refs:
            raise ValueError("TradingReceipt requires trace refs.")
        if self.real_trade_started:
            raise ValueError("TradingReceipt cannot start real trading by default.")
        if self.authority_expansion:
            raise ValueError("TradingReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("TradingReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "broker": self.broker,
                "exchange": self.exchange,
                "symbol": self.symbol,
                "asset_class": self.asset_class,
                "side": self.side,
                "notional_usd": self.notional_usd,
                "max_loss_usd": self.max_loss_usd,
                "stop_loss_percent": self.stop_loss_percent,
                "leverage": self.leverage,
                "paper_trade": self.paper_trade,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
            }
        )


class TradeJournal(SentinelModel):
    mission_id: str
    entries: list[TradingReceipt] = Field(default_factory=list)

    def record(self, receipt: TradingReceipt) -> TradeJournal:
        self.entries.append(receipt)
        return self


class PaperTradeProvider:
    def paper_trade(
        self,
        *,
        authority: TradingSpecialAuthority,
        broker_contract: BrokerContract,
        asset_policy: AssetPolicy,
        position_sizing: PositionSizingPolicy,
        max_loss: MaxLossPolicy,
        stop_loss: StopLossPolicy | None,
        journal: TradeJournal,
        symbol: str,
        asset_class: str,
        side: str,
        confidence: float,
        volatility: float,
        leverage: float,
        thesis: str,
        evidence_refs: list[str],
        trace_refs: list[str],
    ) -> TradingReceipt:
        if datetime.now(UTC) > authority.expires_at:
            raise ValueError("trading authority expired")
        if stop_loss is None:
            raise ValueError("stop-loss policy required")
        if "guaranteed profit" in thesis.lower() or "risk-free profit" in thesis.lower():
            raise ValueError("profit guarantee claim blocked")
        if leverage > 1.0 and not authority.leverage_allowed:
            raise ValueError("leverage not authorized")
        if broker_contract.broker != authority.broker or broker_contract.exchange != authority.exchange:
            raise ValueError("broker contract does not match authority")
        decision = asset_policy.evaluate(asset_class=asset_class, symbol=symbol)
        if not decision.accepted:
            raise ValueError(";".join(decision.errors))
        notional = position_sizing.size(authority, volatility=volatility, confidence=confidence)
        max_allowed_loss = min(authority.max_loss_usd, max_loss.max_loss_usd)
        if notional <= 0:
            raise ValueError("position sizing produced zero exposure")
        receipt = TradingReceipt(
            mission_id=authority.mission_id,
            broker=authority.broker,
            exchange=authority.exchange,
            symbol=symbol,
            asset_class=asset_class,
            side=side,
            notional_usd=notional,
            max_loss_usd=max_allowed_loss,
            stop_loss_percent=stop_loss.stop_loss_percent,
            leverage=leverage,
            evidence_refs=[*authority.evidence_refs, *broker_contract.evidence_refs, *asset_policy.evidence_refs, *position_sizing.evidence_refs, *max_loss.evidence_refs, *stop_loss.evidence_refs, *evidence_refs],
            trace_refs=trace_refs,
        )
        journal.record(receipt)
        return receipt
