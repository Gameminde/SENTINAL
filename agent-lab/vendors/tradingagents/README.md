# TradingAgents Vendor Slot

Source cloned for static audit only:

https://github.com/TauricResearch/TradingAgents

Local source:

```text
agent-lab/vendors/tradingagents/source
```

Commit:

```text
7e9e7b83c7fcc18d941300b253c6ed24d985788d
```

License:

```text
Apache-2.0
```

Do not install dependencies, run the CLI, run Docker, connect LLM providers,
connect market data providers, create credentials, or execute trading runtime
from this vendor checkout.

Research focus:

- multi-agent trading-firm role topology;
- market/news/social/fundamental analyst split;
- bull/bear research debate;
- aggressive/neutral/conservative risk debate;
- structured Research Manager, Trader, and Portfolio Manager outputs;
- five-tier rating scale;
- data vendor routing with fallback;
- checkpoint/resume;
- outcome memory and reflection.

Sentinel rewrite target:

```text
sentinel-control/services/sentinel-core/sentinel/organs/trading/tradingagents_harvest.py
```

Audit docs:

- `../../audits/tradingagents_static_audit.md`
- `../../audits/tradingagents_capability_map.md`
- `../../sentinel_integration_notes/tradingagents_to_sentinel.md`
