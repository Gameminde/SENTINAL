# P6Q Context Token And Model Economy Frontier Scorecard

Date: 2026-05-10

## Summary

P6Q turns P6Q0 research into measurable context economy primitives. It does
not build the full context engine yet; it measures token pressure and model
cost before P6R constructs compact decision frames.

## Implemented

```text
UserModelContract
ModelCostProfile
ModelCapabilityProfile
ContextBudgetPolicy
QualityExpectationContract
TokenLedger
TokenLedgerEntry
ContextPressureReport
ToolSchemaTokenReport
ReceiptTokenReport
OrganOutputTokenReport
DecisionFrameCostProjection
ContextModeComparison
ContextPressureAnalyzer
```

## Locked Behaviors

```text
user chooses selected_model
Sentinel projects cost for selected_model
Sentinel may recommend alternatives without overriding selected_model
model cost/context/capability values are configurable profiles
naive_full_context vs summary_context vs subquadratic_decision_frame are compared
largest pressure source is identified
P6R implementation inputs are generated
over-budget decision frames are reported instead of capped
cost projection uses measured decision frame tokens
no authority expansion
no external execution
```

## Scenario Coverage

```text
browser/API/desktop/channel receipts -> token pressure report
workspace tree + file diffs -> desktop pressure report
TradingAgents-style role outputs -> debate/report pressure
OpenClaw-style broad tool surface -> tool schema pressure
Hermes-style compression baseline -> mode comparison
cheap user-selected model -> broad exploration cost projection
expensive user-selected model -> narrow quality cost projection
```

## Test Result

```text
python -m pytest tests/test_p6_context_token_model_economy_frontier.py -v --tb=short
9 passed
```

## Boundaries

P6Q did not:

```text
start P6R implementation
start Desktop Workspace L6
start Code/Shell harvest
create a new organ family
add new external execution powers
override the user-selected model
copy or bridge vendor runtime
```
