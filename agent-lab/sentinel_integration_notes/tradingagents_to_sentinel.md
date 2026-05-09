# TradingAgents To Sentinel Integration Notes

Date: 2026-05-09

## Integration Rule

```text
Harvest mechanisms.
Rewrite Sentinel-native.
Do not copy vendor code.
Do not import vendor runtime.
Do not add live trading/API/credential power.
```

## Integrated Sentinel Surface

```text
sentinel-control/services/sentinel-core/sentinel/organs/trading/tradingagents_harvest.py
sentinel-control/services/sentinel-core/tests/test_p6_tradingagents_harvest.py
```

## Sentinel-Native Models

```text
TradingDecisionRating
TradingRolePurpose
TradingAgentsRoleAssignment
TradingAgentsFirmPlan
TradingAgentsSignalParser
TradingAgentsDataVendorRoute
TradingOutcomeMemoryEntry
TradingAgentsVendorPattern
TradingAgentsHarvestIntegrator
```

## Product Meaning

TradingAgents upgrades Sentinel trading cognition from:

```text
paper trade provider + risk limits
```

to:

```text
paper-first trading desk cognition:
analysts -> bull/bear debate -> research synthesis -> trader proposal
-> aggressive/neutral/conservative risk debate -> portfolio decision
```

The output is still advisory/paper/internal unless future phases explicitly
promote live trading with special authority, broker contract, max loss,
kill-switch, receipts, replay, and FinalGate.

## Future P6J Alignment Input

P6J must include TradingAgents as an official AgentLab source for:

```text
Capital Operator Sandbox
Trading Special Authority
External API Organ
Brain debate and role orchestration
OrganBench trading negative fixtures
```
