# TradingAgents Capability Map

Date: 2026-05-09

## Capability Harvest Matrix

| TradingAgents Pattern | Source Files | Sentinel Rewrite | Integrated Now |
| --- | --- | --- | --- |
| Trading desk role topology | `tradingagents/graph/setup.py`, `tradingagents/agents/utils/agent_states.py` | `TradingAgentsFirmPlan`, `TradingAgentsRoleAssignment` | yes |
| Analyst evidence split | `tradingagents/agents/analysts/*` | role purposes for market, sentiment, news, fundamentals | yes |
| Bull/bear thesis debate | `tradingagents/agents/researchers/*` | debate role assignments and source-backed pattern ledger | yes |
| Research manager synthesis | `tradingagents/agents/managers/research_manager.py` | structured research synthesis contract | yes |
| Trader proposal | `tradingagents/agents/trader/trader.py` | structured trader proposal output contract | yes |
| Risk debate trio | `tradingagents/agents/risk_mgmt/*` | aggressive/neutral/conservative risk role assignments | yes |
| Portfolio manager final decision | `tradingagents/agents/managers/portfolio_manager.py` | portfolio final decision role and five-tier rating parser | yes |
| Five-tier rating scale | `tradingagents/agents/utils/rating.py`, `tradingagents/graph/signal_processing.py` | `TradingDecisionRating`, `TradingAgentsSignalParser` | yes |
| Vendor fallback routing | `tradingagents/dataflows/interface.py` | `TradingAgentsDataVendorRoute` | yes |
| Checkpoint/resume | `tradingagents/graph/checkpointer.py` | documented as future replay/checkpoint policy | partial |
| Outcome memory/reflection | `tradingagents/agents/utils/memory.py`, `tradingagents/graph/reflection.py` | `TradingOutcomeMemoryEntry` | yes |

## What Sentinel Does Not Take

```text
No LangGraph runtime bridge.
No vendor LLM client import.
No yfinance or Alpha Vantage live execution.
No CLI/Docker/package runtime.
No real broker execution.
No investment advice authority from model output.
No raw credential handling.
```

## Why This Matters

TradingAgents is valuable because it separates trading cognition into
evidence-specialized roles and then forces adversarial review before final
portfolio decision. Sentinel already has authority, receipts, FinalGate, and
paper-first trading controls. The harvest adds a stronger trading-cognition
shape without weakening Sentinel's authority boundaries.
