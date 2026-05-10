# P6Q0 AgentLab Power To Sentinel Rewrite Matrix

Date: 2026-05-10

## Matrix

| Source | Exact mechanism | Why powerful | Context pressure | Sentinel-native rewrite | Do not copy | P6Q/P6R/P6S impact |
| --- | --- | --- | --- | --- | --- | --- |
| JARVIS | Sidecar enrollment, RPC registry, desktop/filesystem/browser/clipboard/screenshot capability map, approval/audit lifecycle | Gives the agent machine-operation power | Window trees, screenshots, clipboard, file trees, RPC outputs | `PermissionedSidecarManifest`, `DesktopActionPreview`, `DesktopActionReceipt`, `ScreenContextSanitizer` | Live host bridge, all-capability default sidecar, raw shell handlers | P6Q measures desktop context pressure; P6R creates compact workspace cards; P6S promotes workspace L6 only after context controls |
| OpenClaw | Gateway/action kernel, plugins, skills, browser, channels, shell, filesystem, scanner | Gives broad tool and execution reach | Tool manifests, plugin schemas, browser pages, channel output, shell/file output | `SentinelActionKernel`, `ToolSurfaceRouter`, `SkillScanner`, `ActionReceipt` | Vendor runtime bridge, unscanned marketplace loading, broad shell/channel/browser mutation | P6Q measures tool schema cost; P6R selects minimal tool surface; P6S exposes only scoped workspace actions |
| Hermes | Context engine, context compressor, trajectory compressor, memory providers, skill prompt index, hook pipeline | Keeps long sessions usable and persistent | Memory hits, skill prompts, tool results, summaries, compressed trajectories | `TokenLedger`, `ContextNeedEstimator`, `ReceiptGraphRetriever`, `EvidenceRanker`, `LLMDecisionFrame` | Memory as authority, skill prompt injection, fail-open hooks | P6Q measures raw/compressed cost; P6R builds Sentinel context engine; P6S requires compressible desktop receipts |
| OpenJarvis | Hardware/model router, query complexity scoring, cost telemetry, learned tool/agent recommendations | Treats model cost and fit as architecture | Routing metadata, telemetry, benchmark and model choice clutter | `UserModelContract`, `ModelCostProfile`, `PromptBudgetAllocator`, `ImprovementProposal` | Auto-overriding user model choice, auto-applied learned configs | P6Q projects cost by user-selected model; P6R adapts context budget to chosen model; P6S costs Desktop L6 decisions |
| TradingAgents | Analyst role graph, bull/bear debate, risk desk, portfolio manager, rating scale, outcome memory | Turns finance decisions into structured debate and synthesis | Analyst reports, raw news, debate transcripts, market data | `TradingSignalCard`, `RiskDebateSummary`, `PortfolioDecisionCard`, `OutcomeMemoryRef` | Real trading bridge, profit guarantee, unchecked leverage | P6Q measures role/debate token cost; P6R uses role-specific slices; P6S keeps financial artifacts as refs/cards |

## Required Sentinel Rewrite Rules

```text
Vendor source is evidence, not runtime.
Power surfaces are harvested, not deleted.
Misuse objectives are blocked, not capabilities.
The user chooses the model.
Sentinel optimizes context for the selected model.
Receipts stay exact outside the prompt.
Decision frames stay compact inside the prompt.
```

## Where Vendors Beat Sentinel Today

```text
JARVIS beats Sentinel on live desktop/sidecar operation.
OpenClaw beats Sentinel on breadth of integrated action surfaces.
Hermes beats Sentinel on implemented context compression lifecycle.
OpenJarvis beats Sentinel on explicit model/cost routing.
TradingAgents beats Sentinel on domain-specific role topology.
```

## Where Sentinel Is Stronger

```text
MissionAuthorityEnvelope style authority boundaries.
FinalGate and lock verdicts.
Receipts, replay, and evidence chain doctrine.
Power promotion ladder from L0 to L8.
User-selected model doctrine.
No vendor runtime bridge.
```

## Rewrite Backlog Seeds

```text
P6Q TokenLedger should measure organ output, receipts, tool schemas, state cards.
P6Q UserModelContract should record selected model and configurable cost profile.
P6Q ContextPressureReport should compare naive, summary, and decision-frame modes.
P6R ReceiptGraphRetriever should pull top-k evidence by mission need.
P6R ToolSurfaceRouter should expose only relevant tools for the next decision.
P6R LLMDecisionFrame should preserve authority and critical evidence.
P6S Desktop Workspace L6 should emit compact workspace summaries and receipt refs.
```
