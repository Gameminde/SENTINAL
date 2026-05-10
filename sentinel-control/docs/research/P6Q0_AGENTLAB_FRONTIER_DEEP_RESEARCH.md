# P6Q0 AgentLab Frontier Deep Research

Date: 2026-05-10

## Verdict

P6Q0 confirms that Sentinel should not start Code/Shell harvest or Desktop L6
yet. The next correct move is Context/Token/Model Economy, because every
stronger organ creates more receipts, logs, tool schemas, browser output,
workspace output, channel drafts, market data, and retry state.

```text
recommended_next = P6Q_CONTEXT_TOKEN_AND_MODEL_ECONOMY_FRONTIER
then = P6R_SUBQUADRATIC_AGENT_CONTEXT_ENGINE_PROTOTYPE
then = P6S_DESKTOP_WORKSPACE_L6_PROMOTION
```

The product thesis is unchanged:

```text
Sentinel absorbs powerful mechanisms.
Sentinel rewrites them under Brain + Organs + Authority + Receipts.
Sentinel does not copy vendor runtime.
Sentinel does not delete high-power surfaces.
Sentinel controls when and why power is used.
```

## Source Priority

P6Q0 uses AgentLab as the deep source and GitHub trends as cross-check only.

```text
1. JARVIS
2. OpenClaw
3. Hermes
4. OpenJarvis
5. TradingAgents
6. GitHub trend cross-check
```

AgentLab evidence inspected:

```text
agent-lab/audits/final/jarvis_final_forensic_report.md
agent-lab/audits/final/openclaw_final_forensic_report.md
agent-lab/audits/final/hermes_final_forensic_report.md
agent-lab/audits/final/openjarvis_final_forensic_report.md
agent-lab/audits/tradingagents_static_audit.md
agent-lab/audits/tradingagents_capability_map.md
agent-lab/audits/SUPERPOWER_EXTRACTION_TABLE.md
agent-lab/audits/final/g9_cross_agent_synthesis.md
agent-lab/sentinel_integration_notes/*.md
```

## Mechanism Cards

### JARVIS

Source:

```text
agent-lab/vendors/jarvis/source
agent-lab/audits/final/jarvis_final_forensic_report.md
agent-lab/audits/jarvis_sidecar_map.md
agent-lab/audits/jarvis_desktop_capability_map.md
agent-lab/sentinel_integration_notes/jarvis_desktop_to_sentinel.md
```

Exact mechanism:

```text
daemon + permission model + sidecar enrollment + RPC registry
+ terminal/filesystem/desktop/browser/clipboard/screenshot capabilities
+ approval/deferred execution/audit lifecycle
```

Why powerful:

```text
JARVIS turns an agent from text into a machine operator.
The sidecar can observe and mutate the user's local environment.
```

Where it beats Sentinel today:

```text
live host-side power surface
desktop/window/screen awareness
sidecar capability registration
approval lifecycle around machine actions
```

Where Sentinel is stronger:

```text
phase locks
FinalGate
root authority doctrine
receipt/replay discipline
power promotion ladder
```

Context/token pressure:

```text
window trees, screenshots, clipboard previews, file trees, RPC outputs,
terminal output, action logs, and approval state can explode the LLM context.
```

Sentinel rewrite:

```text
PermissionedSidecarManifest
SidecarEnrollmentGrant
DesktopActionPreview
ScreenContextSanitizer
ClipboardSanitizer
DesktopActionReceipt
DesktopFinalGateAdapter
```

P6Q implication:

```text
Measure desktop observation, file tree, diff, preview, and receipt token cost.
```

P6R implication:

```text
Desktop context must be compressed into workspace state cards, top changed
files, rollback refs, evidence refs, and current blockers.
```

P6S implication:

```text
Desktop Workspace L6 can proceed only after it emits compact decision frames,
not full workspace dumps.
```

### OpenClaw

Source:

```text
agent-lab/vendors/openclaw/source
agent-lab/audits/final/openclaw_final_forensic_report.md
agent-lab/audits/openclaw_scanner_report.md
agent-lab/sentinel_integration_notes/openclaw_to_sentinel.md
```

Exact mechanism:

```text
gateway/action runtime + skill/plugin surfaces + browser + channels + shell
+ filesystem + memory + approval UI patterns + static scanner artifacts
```

Why powerful:

```text
OpenClaw exposes many real action surfaces to an agent through one runtime.
It feels powerful because the LLM can reach browser, plugins, channels, shell,
filesystem, and memory.
```

Where it beats Sentinel today:

```text
broad tool surface
plugin ecosystem
integrated browser/channel/shell route
marketplace-style capability loading
```

Where Sentinel is stronger:

```text
authority is not prompt-derived
vendor runtime is not bridged
tools are promoted through L0-L8
receipts and replay are first-class
```

Context/token pressure:

```text
large plugin manifests, tool schemas, browser pages, channel history, shell
outputs, file content, and approval metadata can bloat every model turn.
```

Sentinel rewrite:

```text
SentinelActionKernel
SkillScanner
ToolSurfaceRouter
CapabilityPromotionPath
ActionReceipt
FinalGateAdapter
```

P6Q implication:

```text
Measure tool schema tokens and compare broad tool exposure against selected
minimal tool surface.
```

P6R implication:

```text
Build ToolSurfaceRouter so the LLM sees only the tools relevant to the next
decision, not every possible organ.
```

P6S implication:

```text
Desktop L6 should expose only workspace file operations required by the
current mission, not the whole future sidecar catalog.
```

### Hermes

Source:

```text
agent-lab/vendors/hermes-agent/source
agent-lab/vendors/hermes-agent/source/agent/context_engine.py
agent-lab/vendors/hermes-agent/source/agent/context_compressor.py
agent-lab/vendors/hermes-agent/source/trajectory_compressor.py
agent-lab/audits/final/hermes_final_forensic_report.md
agent-lab/sentinel_integration_notes/hermes_to_sentinel.md
```

Exact mechanism:

```text
persistent memory + skill prompt index + context engine interface
+ automatic compression + trajectory compression + tool hook pipeline
```

Why powerful:

```text
Hermes shows that long-lived agents need a context engine, not just a large
prompt. It tracks token usage, compresses middle turns, protects head/tail
context, and preserves work continuity.
```

Where it beats Sentinel today:

```text
implemented context engine abstraction
automatic compression threshold
tool-output pruning
trajectory compression metrics
memory/skill surfaces feeding the prompt
```

Where Sentinel is stronger:

```text
memory is non-authoritative
skills are procedures, not silent authority
workspace and receipts already exist
Brain L4 can route evidence before calling the LLM
```

Context/token pressure:

```text
memory hits, skill prompts, tool results, long trajectories, provider output,
and compressed summaries can still become huge if not ranked by decision need.
```

Sentinel rewrite:

```text
ContextNeedEstimator
TokenLedger
ReceiptGraphRetriever
EvidenceRanker
DecisionFrameBuilder
AuthorityCardBuilder
```

P6Q implication:

```text
Measure raw context, compressed context, receipt summaries, state card tokens,
authority card tokens, and tool schema tokens.
```

P6R implication:

```text
Build a Sentinel-native context engine that preserves authority and evidence
while reducing 20k-30k raw tokens into a 1k-2k LLM decision frame.
```

P6S implication:

```text
Desktop L6 must write receipts and summaries that are compressible and
retrievable by evidence refs.
```

### OpenJarvis

Source:

```text
agent-lab/vendors/openjarvis/source
agent-lab/audits/final/openjarvis_final_forensic_report.md
agent-lab/audits/openjarvis_cost_router_map.md
agent-lab/sentinel_integration_notes/openjarvis_to_sentinel.md
```

Exact mechanism:

```text
hardware-aware model routing + query complexity scoring + learned routing
+ skill import + sandbox/timeout discipline + cost and telemetry signals
```

Why powerful:

```text
OpenJarvis treats intelligence cost and model fit as runtime architecture,
not billing afterthought.
```

Where it beats Sentinel today:

```text
explicit local/cloud routing
hardware-aware model selection
cost and latency as first-class route features
learned tool/agent recommendations from traces
```

Where Sentinel is stronger:

```text
user-selected model doctrine
authority boundaries
phase locks
no auto-applied learned config mutation
```

Context/token pressure:

```text
routing metadata, hardware profiles, model choices, telemetry, benchmark
results, and tool history can become prompt clutter if sent directly.
```

Sentinel rewrite:

```text
UserModelContract
ModelCostProfile
ModelCapabilityProfile
TokenCostProjection
ContextBudgetPolicy
ImprovementProposal
```

P6Q implication:

```text
Measure estimated cost under the user-selected model and alternate model
profiles without letting Sentinel override the user's choice.
```

P6R implication:

```text
PromptBudgetAllocator should adapt to expensive or cheap selected models.
Cheap models can allow broader batch exploration; expensive models demand
tighter, proof-rich calls.
```

P6S implication:

```text
Desktop L6 should produce costed decision frames so expensive model calls are
reserved for meaningful decisions.
```

### TradingAgents

Source:

```text
agent-lab/vendors/tradingagents/source
agent-lab/audits/tradingagents_static_audit.md
agent-lab/audits/tradingagents_capability_map.md
agent-lab/sentinel_integration_notes/tradingagents_to_sentinel.md
```

Exact mechanism:

```text
market/social/news/fundamentals analyst split
+ bull/bear research debate
+ research manager synthesis
+ trader proposal
+ aggressive/neutral/conservative risk debate
+ portfolio manager final decision
+ rating scale, vendor fallback, outcome memory
```

Why powerful:

```text
TradingAgents shows how specialized role topology and structured debate create
better capital decisions than a single generic planner.
```

Where it beats Sentinel today:

```text
domain-specific trading desk topology
market-data fallback flow
structured risk debate
portfolio decision memory
```

Where Sentinel is stronger:

```text
special trading authority
paper-first execution
max loss and leverage policy
FinalGate and receipt discipline
```

Context/token pressure:

```text
analyst reports, debates, news snippets, ratings, risk arguments, and market
data can overflow the model unless summarized into decision cards.
```

Sentinel rewrite:

```text
TradingDeskRoleGraph
TradingSignalCard
RiskDebateSummary
PortfolioDecisionCard
OutcomeMemoryRef
```

P6Q implication:

```text
Measure role-report and debate-summary token cost for capital/trading missions.
```

P6R implication:

```text
Context engine needs role-specific slices and final aggregation summaries, not
full raw debate transcripts.
```

P6S implication:

```text
Desktop L6 may write or read trading/capital artifacts, but the LLM should see
only selected evidence cards and receipt refs.
```

## Cross-Source Synthesis

The strongest agents all win through broad surfaces and persistent state:

```text
JARVIS: machine surface
OpenClaw: action surface
Hermes: memory/context surface
OpenJarvis: cost/model surface
TradingAgents: domain-role surface
```

Their shared weakness is that power creates context pressure:

```text
more organs -> more receipts
more receipts -> more summaries
more summaries -> more prompt pressure
more prompt pressure -> higher cost and lower decision clarity
```

Sentinel's next moat is therefore not another organ. It is the ability to
operate many organs while showing the user-selected LLM only the small,
evidence-preserving decision frame it needs.
