# P6G Capital Operator Sandbox Scorecard

Date: 2026-05-09

## Scope

P6G creates the capital operator sandbox. It models opportunities, signals,
adaptive operating envelopes, budget reallocation, risk review, spend proposals,
and sandbox receipts. It does not perform live spend.

## Implemented Files

```text
sentinel-control/services/sentinel-core/sentinel/organs/capital/__init__.py
sentinel-control/services/sentinel-core/sentinel/organs/capital/sandbox.py
sentinel-control/services/sentinel-core/sentinel/organs/__init__.py
sentinel-control/services/sentinel-core/sentinel/agent/events.py
sentinel-control/services/sentinel-core/tests/test_p6_capital_operator_sandbox.py
```

## Locked Behaviors

```text
CapitalOpportunity models opportunities and planned organ inputs only.
SignalLedger records market/API/outreach/ROI/risk signals with evidence refs.
AdaptiveOperatingEnvelope separates root budget boundaries from dynamic
operating allocation.
BudgetReallocator moves sandbox budget toward stronger evidence.
Dynamic spend changes require signal refs.
CapitalRiskReview flags profit guarantee claims.
DynamicSpendPolicy produces spend proposals, not live spend.
SpendDecisionTrace requires evidence refs and signal refs.
CapitalSandboxReceipt is deterministic, non-executing, and non-spending.
```

## Verification

```bash
python -m pytest tests/test_p6_capital_operator_sandbox.py -v --tb=short
```

Result:

```text
9 passed
```

## Boundaries Preserved

```text
live spend = 0
payment provider execution = 0
trading runtime = 0
account creation runtime = 0
credential access = 0
external API execution = 0
browser power expansion = 0
channel send = 0
authority expansion = 0
```
