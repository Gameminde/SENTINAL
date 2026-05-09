# P6I.5 Capital Stack Hardening Scorecard

Date: 2026-05-09

## Scope

P6I.5 is a logic hardening pass across the locked capital stack after P6G,
P6H, and P6I. It does not create a new organ. It closes authority, evidence,
budget, and risk-binding gaps found during the logic review.

## Hardened Surfaces

```text
P6G Capital Operator Sandbox
P6H Spend Runtime Limited
P6I Trading Special Authority
```

## Regression Fixtures Added

```text
unmatched spend signal refs are rejected
sandbox sub-budgets cannot exceed budget remaining
spend kill switch must match authority mission
spend request credential ref cannot override authority credential ref
paper trading must obey TradingSpecialAuthority asset scope
paper trading must obey TradingSpecialAuthority max leverage
capital/trading profit guarantee variants are blocked
```

## Fixes Applied

```text
DynamicSpendPolicy now requires opportunity signal refs to exist in SignalLedger.
BudgetReallocator now caps allocation to unallocated sandbox budget.
AdaptiveOperatingEnvelope now rejects over-allocated sub-budgets.
FakeSpendProvider now rejects kill-switch mission mismatch.
FakeSpendProvider now rejects request credential refs outside spend authority.
PaperTradeProvider now enforces authority asset class and symbol scope.
PaperTradeProvider now enforces authority max_leverage.
CapitalRiskReview and PaperTradeProvider detect broader profit guarantee language.
```

## Verification

Initial hardening regression run before fixes:

```text
tests/test_p6_capital_stack_hardening.py = 7 failed
```

After fixes:

```bash
python -m pytest tests/test_p6_capital_stack_hardening.py -v --tb=short
```

Result:

```text
7 passed
```

Neighbor capital stack verification:

```bash
python -m pytest tests/test_p6_capital_operator_sandbox.py tests/test_p6_spend_runtime_limited.py tests/test_p6_trading_special_authority.py -v --tb=short
```

Result:

```text
30 passed
```

## Boundaries Preserved

```text
real payment execution = 0
real trading execution = 0
account creation runtime = 0
credential secret access = 0
external API mutation = 0
browser power expansion = 0
vendor runtime bridge = 0
vendor code copy = 0
silent authority expansion = 0
```

## Next Phase Correction

The next phase is corrected to:

```text
P6J_AGENTLAB_IMPLEMENTATION_ALIGNMENT
```

Sentinel should not proceed to Desktop Sidecar or OrganBench before checking
whether P6C-P6I actually harvest and rewrite the best AgentLab vendor patterns.
