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
| P6J AgentLab Implementation Alignment | Ensure P6C-P6I organs harvest real vendor patterns | AgentLab audits, OpenClaw, Hermes, OpenJarvis, JARVIS, CloakBrowser, financial-services | L1 -> L4 | rewrite mechanisms, never copy vendor runtime |
| P6K OrganBench External Organ Integrated Review | Continuous organ certification | all P6 organs | L3 -> L8 | benchmark reports and negative regressions |
| P6L Desktop Sidecar Organ | Permissioned host-control contracts | JARVIS | L1 -> L3 | sidecar manifest and fake RPC tests |
| P6M End-to-End Controlled Mission Runtime Review | Certify organs + Brain together | all | L5 -> L6 | controlled mission suite |
| P7 Brain L4 Runtime Wiring | Wire P5 modules into runtime | P5L | L2 -> L6 | AgentRuntime/MissionRunner integration |
| P8 Mission OS Product UI | Productize mission control | Sentinel docs | L4 -> L6 | UI status, approvals, trace viewer |
| P9 Long-Horizon Operational Continuity | Persistent missions, monitoring, workflow loops | Hermes, JARVIS, OpenJarvis | L4 -> L6 | continuity and revocation tests |
| P10 Sentinel Foundry / Skill Marketplace | Controlled skill/procedure ecosystem | OpenClaw, Hermes, financial-services | L2 -> L7 | scanner, eval, signed promotion |

Every phase must name blocked promotion levels and demotion criteria before code
is merged.
