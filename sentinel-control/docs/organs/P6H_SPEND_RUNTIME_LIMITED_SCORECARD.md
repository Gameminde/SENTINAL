# P6H Spend Runtime Limited Scorecard

Date: 2026-05-09

## Scope

P6H defines the limited spend runtime shape. It includes explicit spend
authority, spend requests, provider adapter interface, fake/sandbox provider,
receipts, subscription guard, refund/cancel path, and spend kill switch.

Real providers remain disabled by default.

## Implemented Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/spend/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/spend/runtime.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_spend_runtime_limited.py
```

## Locked Behaviors

```text
SpendAuthorityEnvelope requires explicit budget, vendor, category, expiry,
receipt, kill-switch, and evidence refs.
SpendProviderAdapter exists but rejects real provider execution by default.
FakeSpendProvider creates deterministic sandbox receipts only.
Budget overrun and single-transaction overrun are blocked.
Vendor/category/out-of-expiry spend is blocked.
Hidden subscriptions are blocked.
Explicit subscriptions require explicit subscription authority and a
refund/cancel path.
SpendKillSwitch blocks sandbox execution shape.
CredentialRef is reference-only; raw credential material is blocked.
SpendReceipt cannot start real payment, access secrets, or expand authority.
```

## Verification

```bash
python -m pytest tests/test_p6_spend_runtime_limited.py -v --tb=short
```

Result:

```text
10 passed
```

## Boundaries Preserved

```text
real payment provider execution = 0
real payment started = 0
hidden subscription allowed = 0
raw credential access = 0
trading runtime = 0
account creation runtime = 0
authority expansion = 0
```
