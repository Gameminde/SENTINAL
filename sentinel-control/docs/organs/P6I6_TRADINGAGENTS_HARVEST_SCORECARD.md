# P6I.6 TradingAgents Harvest Scorecard

Date: 2026-05-09

## Scope

P6I.6 clones TradingAgents into AgentLab, audits it as a trading-agent
specimen, and integrates selected powers into Sentinel as internal,
Sentinel-native trading cognition.

## Source

```text
Repository: https://github.com/TauricResearch/TradingAgents
Local source: agent-lab/vendors/tradingagents/source
Commit: 7e9e7b83c7fcc18d941300b253c6ed24d985788d
License: Apache-2.0
Run decision: clone only
```

## Harvested Powers

```text
trading desk role graph
market/social/news/fundamentals analyst split
bull/bear research debate
research manager synthesis
structured trader proposal
aggressive/neutral/conservative risk debate
portfolio manager final decision
five-tier rating scale
data vendor fallback routing
outcome memory and alpha reflection
```

## Sentinel-Native Integration

```text
TradingAgentsFirmPlan
TradingAgentsRoleAssignment
TradingAgentsSignalParser
TradingAgentsDataVendorRoute
TradingOutcomeMemoryEntry
TradingAgentsVendorPattern
TradingAgentsHarvestIntegrator
```

## Verification

```bash
python -m pytest tests/test_p6_tradingagents_harvest.py -v --tb=short
```

Result:

```text
7 passed
```

Neighbor verification:

```bash
python -m pytest tests/test_p6_trading_special_authority.py tests/test_p6_capital_stack_hardening.py tests/test_p6_capital_operator_sandbox.py tests/test_p6_spend_runtime_limited.py -v --tb=short
python -m pytest tests/test_p6_browser_organ_contract.py tests/test_p6_external_api_organ.py tests/test_p6_channel_organ.py tests/test_p6_credential_vault_policy.py tests/test_p6_agent_lab_organ_harvest.py tests/test_p6_external_organ_foundry.py -v --tb=short
python -m pytest tests/test_agent_brain_l4_integrated_review.py tests/test_agent_brain_l4_premortem_fixtures.py -v --tb=short
```

Result:

```text
37 passed
74 passed
23 passed
```

Full sentinel-core verification:

```bash
python -m pytest tests -v --tb=short
```

Result:

```text
736 passed
```

## Boundaries Preserved

```text
vendor runtime bridge = 0
vendor code copy = 0
live API execution = 0
real trading execution = 0
account creation = 0
credential access = 0
payment/spend execution = 0
browser power expansion = 0
authority expansion = 0
```

## Next Phase

```text
P6J_AGENTLAB_IMPLEMENTATION_ALIGNMENT
```

P6J must now align P6C-P6I plus the TradingAgents harvest against all AgentLab
forensic sources before Desktop Sidecar or OrganBench.
