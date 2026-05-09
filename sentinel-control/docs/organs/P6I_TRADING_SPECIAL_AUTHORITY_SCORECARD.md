# P6I Trading Special Authority Scorecard

Date: 2026-05-09

## Scope

P6I defines special trading authority, broker contracts, asset policy, position
sizing, max-loss policy, stop-loss policy, paper trade provider, trade journal,
and deterministic trading receipts.

Real trading remains disabled by default.

## Implemented Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/trading/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/trading/special_authority.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_trading_special_authority.py
```

## Locked Behaviors

```text
TradingSpecialAuthority requires broker/exchange, asset classes, symbols, max
capital, max loss, leverage policy, expiry, and evidence refs.
BrokerContract is paper-provider first and real provider disabled by default.
AssetPolicy blocks unapproved asset classes or symbols.
PositionSizingPolicy reduces exposure under volatility/risk.
MaxLossPolicy and StopLossPolicy are required.
Leverage is blocked unless explicitly authorized.
Profit guarantee claims are blocked.
PaperTradeProvider records paper trades only.
TradeJournal records paper receipts.
Missing authority creates a proposal-only object.
TradingReceipt is deterministic and cannot start real trading or expand
authority.
```

## Verification

```bash
python -m pytest tests/test_p6_trading_special_authority.py -v --tb=short
```

Result:

```text
11 passed
```

## Boundaries Preserved

```text
real trading provider execution = 0
real trade started = 0
leverage without authority = 0
profit guarantee accepted = 0
payment/spend runtime expansion = 0
credential access = 0
authority expansion = 0
```
