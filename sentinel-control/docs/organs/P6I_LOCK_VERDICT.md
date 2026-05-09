# P6I Lock Verdict

Date: 2026-05-09

## Verdict

```text
P6I_TRADING_SPECIAL_AUTHORITY = FULL_LOCKED
```

P6I is accepted as the paper-first trading special authority tranche.

## Accepted Scope

```text
TradingSpecialAuthority implemented
BrokerContract implemented
AssetPolicy implemented
PositionSizingPolicy implemented
MaxLossPolicy implemented
StopLossPolicy implemented
TradeJournal implemented
PaperTradeProvider implemented
TradingReceipt implemented
Targeted P6I tests passed
```

## Product Doctrine Locked

```text
Trading is Red Lane special authority.
Paper trading comes first.
Real trading is disabled by default.
Trading requires explicit broker/exchange, asset class, max capital, max loss,
leverage policy, stop-loss, journal, expiry, and evidence.
Missing authority creates a proposal only.
```

## Verification

```text
P6I targeted tests = 11 passed
```

Verified command:

```bash
python -m pytest tests/test_p6_trading_special_authority.py -v --tb=short
```

## Next Phase

```text
next_phase = P6J_DESKTOP_SIDECAR_ORGAN
```
