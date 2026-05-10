# Phase Roadmap P6 To P10

Each phase declares promotion level:

```text
L0 vendor observation
L1 extraction matrix
L2 Sentinel contract
L3 fake eval
L4 dry-run
L5 sandbox
L6 limited execution
L7 production-scoped execution
L8 continuous OrganBench monitoring
```

| Phase | Purpose | Sources | Current -> target level | Lock criteria |
| --- | --- | --- | --- | --- |
| P6A External Organ Foundry | Build organ contracts and registry | OpenClaw, JARVIS, P5L | L1 -> L2 | contracts, authority, receipts, promotion gate tests |
| P6B AgentLab Organ Harvest | Turn forensic docs into machine-readable harvest refs | agent-lab final reports | L0/L1 -> L2 | references with source evidence |
| P6C Browser Organ Contract Review | Normalize current browser organ and future Cloak-like power | OpenClaw, JARVIS, CloakBrowser | L2 -> L3 | browser contract and misuse fixtures |
| P6D External API Organ | Govern external data/API calls | OpenJarvis, financial connectors | L2 -> L4 | dry-run, cost, rate, privacy receipts |
| P6E Channel Organ | Govern outbound/inbound channels | OpenClaw, Hermes, JARVIS | L2 -> L4 | draft-first and approval tests |
| P6F Credential Vault Policy | Define credential handling without exposing secrets | all vendors | L1 -> L2 | no credential access runtime |
| P6G Capital Operator Sandbox | Model opportunities without spend runtime | financial-services, P5D.5 | L2 -> L5 | opportunity/risk ledger fake evals |
| P6H Spend Runtime Limited | Future scoped spend execution | finance/capital doctrine | L4 -> L6 | max budget, receipts, kill switch |
| P6I Trading Special Authority | Future scoped trading special authority | financial-services, compliance docs | L2 -> L5 | no live trading before special evals |
| P6I.5 Capital Stack Hardening | Close spend/trading/capital authority-binding gaps | P6G/P6H/P6I logic review | L4 -> L5 | regression fixtures for discovered bypasses |
| P6I.6 TradingAgents Harvest | Add trading-firm cognition from TradingAgents | TradingAgents static audit | L1 -> L4 | role graph, ratings, vendor fallback, outcome memory |
| P6J AgentLab Implementation Alignment | Ensure P6C-P6I organs harvest real vendor patterns | AgentLab audits, OpenClaw, Hermes, OpenJarvis, JARVIS, CloakBrowser, financial-services, TradingAgents | L1 -> L4 | rewrite mechanisms, never copy vendor runtime |
| P6K Desktop AgentLab Harvest and Blueprint | Harvest Desktop from real sidecar/desktop agents before coding host control | JARVIS first, OpenClaw, OpenJarvis | L1 -> L2 | source-backed capability map and Sentinel-native sidecar blueprint |
| P6L Desktop Sidecar Organ Implementation | Permissioned host-control contracts from the P6K blueprint | JARVIS first, P6K blueprint | L2 -> L3 | sidecar manifest, fake RPC, sanitizer, approval, kill-switch tests |
| P6M Reality Activation For Existing Organs | Make existing organs perform scoped real work before adding more families | Browser, API, Channel, Credentials, Desktop, Capital, Trading, Spend | L3 -> L5 | public read, read-only API, local draft, env credential ref, workspace files, capital signals, market data paper trade, test-mode spend |
| P6N Existing Organs Capability Frontier | Push every existing P6M organ to current practical limits before adding new organs | Browser, API, Channel, Credentials, Desktop, Capital, Trading, Spend | L5 -> L5 frontier | max actions, limits, failures, missing runtimes, promotion candidates |
| P6O Existing Organs Real World Gauntlet | Push existing organs harder in repeated, combined, max-mode reality scenarios | P6M/P6N organs, AgentLab power doctrine | L5 -> L5/L6 evidence | max-mode runs, concrete fixes, cross-organ evidence paths |
| P6P Existing Organs Runtime Promotion Plan | Choose which existing organs move to the next real runtime level | P6O gauntlet evidence | L5 -> L6 plan | promotion priorities, required adapters, receipts, LLM runtime needs |
| P6Q0 AgentLab Frontier Deep Research | Validate the next direction by analyzing AgentLab first and GitHub trends second | JARVIS, OpenClaw, Hermes, OpenJarvis, TradingAgents, trending agent repos | L0/L1 -> L2 research lock | mechanism cards, context pressure findings, Sentinel rewrite backlog |
| P6Q Context Token And Model Economy Frontier | Measure token/context/model cost before stronger L6 promotions | P6Q0, Hermes context engine, OpenJarvis cost routing, P6O/P6P evidence | L5 -> L5 measurement | raw vs compressed vs decision-frame token/cost reports |
| P6R Subquadratic Agent Context Engine Prototype | Build compact LLM decision frames around receipts, evidence, authority, and selected tools | P6Q findings, Hermes compression, Sentinel Brain L4, P6 organs | L2 -> L4 | `LLMDecisionFrame`, token ledger, receipt retriever, tool surface router tests |
| P6R5 Sentinel Cognitive Mechanics Review | Hard review of Sentinel as math/control/algorithm/product architecture before more L6 power, grounded by P6Q/P6R code review | P5L, P6O/P6P, P6Q/P6R, AgentLab, context engineering research | L4 -> L4 review lock | formal state/action objective, control loop, code-grounded context/evidence/receipt hardening, future-or-generic verdict, P6S go/no-go |
| P6S-A Desktop AgentLab Power Binding | Bind Desktop L6 to source-backed AgentLab power before implementation | JARVIS first, OpenJarvis, OpenClaw, Hermes, P6K/P6L/P6M/P6P/P6R | L5 -> L5 binding | `P6S_DESKTOP_AGENTLAB_POWER_BINDING.md`, source mechanism cards, surpass-not-imitate rewrite matrix |
| P6S-B Desktop Workspace L6 Implementation | Promote workspace file operations after power binding and context economy exist | P6S-A binding, P6P order, P6K/P6L desktop harvest, P6R context engine | L5 -> L6 | workspace adapter, compact workspace cards, receipts, rollback refs, FinalGate |
| P6T-A Browser AgentLab Power Binding | Bind Browser L6 to source-backed browser/navigation power before implementation | OpenClaw first, CloakBrowser, JARVIS, browser-use, Cua, Chrome DevTools MCP, Hermes, P6R | L5 -> L5 binding | `P6T_BROWSER_AGENTLAB_POWER_BINDING.md`, source mechanism cards, controlled-navigation rewrite matrix |
| P6T-B Browser Controlled Navigation L6 Implementation | Promote controlled browser navigation without login/session mutation | P6T-A binding, P6C/P6M/P6O browser evidence, P6R context engine | L5 -> L6 | allowed domains, navigation receipts, timeout budget, compact page evidence |
| P6U API Authenticated Read L6 | Promote authenticated read-only API access through scoped credential refs | P6D/P6F/P6M/P6O evidence, P6R context engine | L5 -> L6 | read-only adapters, rate ledger, credential ref receipts |
| P6V Channel Provider Draft L6 | Promote provider draft creation without live send | P6E/P6M/P6O evidence, P6R context engine | L5 -> L6 | provider draft adapter, recipient provenance, draft rollback |
| P6W Code/Shell AgentLab Harvest | Harvest shell/code powers after context economy and first L6 promotions | OpenClaw first, JARVIS, OpenJarvis | L1 -> L2 | source-backed shell/code capability map and Sentinel-native sandbox blueprint |
| P6X Code/Shell Sandbox Organ Implementation | Permissioned code and shell sandbox contracts from the P6W blueprint | OpenClaw first, P6W blueprint | L2 -> L3 | fake executor, typed commands, sandbox mounts, timeout, receipts |
| P6Y OrganBench External Organ Integrated Review | Continuous organ certification | all P6 organs | L3 -> L8 | benchmark reports and negative regressions |
| P6Z End-to-End Controlled Mission Runtime Review | Certify organs + Brain together | all | L5 -> L6 | controlled mission suite |
| P7 Brain L4 Runtime Wiring | Wire P5 modules into runtime | P5L | L2 -> L6 | AgentRuntime/MissionRunner integration |
| P8 Mission OS Product UI | Productize mission control | Sentinel docs | L4 -> L6 | UI status, approvals, trace viewer |
| P9 Long-Horizon Operational Continuity | Persistent missions, monitoring, workflow loops | Hermes, JARVIS, OpenJarvis | L4 -> L6 | continuity and revocation tests |
| P10 Sentinel Foundry / Skill Marketplace | Controlled skill/procedure ecosystem | OpenClaw, Hermes, financial-services | L2 -> L7 | scanner, eval, signed promotion |

Every phase must name blocked promotion levels and demotion criteria before code
is merged.
