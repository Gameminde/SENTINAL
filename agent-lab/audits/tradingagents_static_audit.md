# TradingAgents Static Audit

Date: 2026-05-09

## Source

```text
Repository: https://github.com/TauricResearch/TradingAgents
Local source: agent-lab/vendors/tradingagents/source
Commit: 7e9e7b83c7fcc18d941300b253c6ed24d985788d
License: Apache-2.0
Clone size: 100 files / 5,079,309 bytes
Run decision: clone only
```

TradingAgents is a Python/LangGraph multi-agent financial trading framework.
It is a useful AgentLab specimen because it models a trading desk as a role
graph, not as a single trader prompt.

## Mechanisms Observed

```text
Analyst roles:
- market analyst
- social/sentiment analyst
- news analyst
- fundamentals analyst

Research debate:
- bull researcher
- bear researcher
- research manager

Execution proposal:
- trader structured transaction proposal

Risk debate:
- aggressive risk analyst
- conservative risk analyst
- neutral risk analyst
- portfolio manager final decision
```

The graph is built in:

```text
tradingagents/graph/setup.py
tradingagents/graph/conditional_logic.py
tradingagents/agents/utils/agent_states.py
```

Structured output is defined in:

```text
tradingagents/agents/schemas.py
tradingagents/agents/managers/research_manager.py
tradingagents/agents/trader/trader.py
tradingagents/agents/managers/portfolio_manager.py
```

Data source routing is defined in:

```text
tradingagents/dataflows/interface.py
tradingagents/default_config.py
```

Checkpoint and outcome memory mechanisms are defined in:

```text
tradingagents/graph/checkpointer.py
tradingagents/agents/utils/memory.py
tradingagents/graph/reflection.py
```

## High-Value Patterns

```text
1. Trading-firm role graph instead of one trader agent.
2. Analyst separation by evidence type.
3. Bull/bear adversarial research debate.
4. Aggressive/neutral/conservative risk debate.
5. Portfolio Manager as final decision gate.
6. Typed decision schemas rendered back to human-readable markdown.
7. Deterministic five-tier rating extraction.
8. Data vendor fallback chains.
9. Per-symbol checkpoint/resume.
10. Outcome memory with alpha-vs-benchmark reflection.
```

## Risk Findings

```text
External market data calls exist through yfinance and Alpha Vantage adapters.
LLM provider clients require API credentials.
CLI/Docker/package runtime should not be run inside AgentLab without a separate
sandbox plan.
Trading decision language can imply investment advice if reused without
Sentinel authority, disclaimers, and special trading controls.
Portfolio decisions are not authority by themselves.
Vendor runtime must not be bridged into Sentinel.
```

## Sentinel Rewrite Decision

Sentinel harvests the architecture, not the runtime:

```text
TradingAgents role graph -> TradingAgentsFirmPlan
five-tier rating parser -> TradingAgentsSignalParser
vendor fallback routing -> TradingAgentsDataVendorRoute
outcome reflection memory -> TradingOutcomeMemoryEntry
pattern ledger -> TradingAgentsVendorPattern
```

No vendor code is copied. No vendor runtime is imported. No live API, broker,
trading, account, payment, or credential power is added by this audit.
