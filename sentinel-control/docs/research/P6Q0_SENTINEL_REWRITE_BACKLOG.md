# P6Q0 Sentinel Rewrite Backlog

Date: 2026-05-10

## Immediate Backlog For P6Q

P6Q should be a measurement frontier, not a full runtime rewrite.

```text
UserModelContract
ModelCostProfile
TokenLedger
ContextPressureReport
ToolSchemaTokenReport
ReceiptTokenReport
OrganOutputTokenReport
DecisionFrameCostProjection
```

Required scenarios:

```text
browser/API/desktop/channel receipts -> token pressure report
workspace tree + file diffs -> desktop context pressure report
TradingAgents-style role outputs -> debate/report token pressure
OpenClaw-style broad tool surface -> tool schema token pressure
Hermes-style compression baseline -> summary context comparison
user-selected cheap model -> broad exploration cost projection
user-selected expensive model -> narrow high-quality decision projection
```

## Immediate Backlog For P6R

P6R should build the first Sentinel-native subquadratic agent context engine.

```text
ContextNeedEstimator
ReceiptGraphRetriever
EvidenceRanker
StateCardBuilder
AuthorityCardBuilder
ToolSurfaceRouter
PromptBudgetAllocator
LLMDecisionFrame
DecisionFrameVerifier
```

Required behavior:

```text
preserve authority constraints
preserve critical evidence refs
pin current objective and blockers
select top-k relevant receipts
exclude irrelevant tool schemas
estimate prompt tokens
produce deterministic frame hash
keep exact receipts outside prompt
```

## Immediate Backlog For P6S

P6S should promote Desktop Workspace L6 only after P6R exists.

```text
WorkspaceOperationAdapter
WorkspaceReceiptAdapter
WorkspaceContextCard
WorkspaceDiffSummary
WorkspaceRollbackRef
PathContainmentProofRef
DesktopDecisionFrameSlice
```

Desktop L6 must not send raw workspace dumps to the LLM by default.

## Deferred Backlog

These stay after P6Q/P6R/P6S:

```text
Code/Shell AgentLab Harvest
Code/Shell Sandbox Organ
browser login/session mutation
desktop screenshot/clipboard live
live channel send
real payment provider
real broker execution
```

They are not deleted. They remain high-power surfaces with promotion paths.

## Research-Derived Implementation Priorities

1. Build token/context measurement before new power.
2. Build model-cost projection around user-selected model.
3. Build receipt graph retrieval before Desktop L6.
4. Build tool surface minimization before MCP expansion.
5. Build evidence-preserving compression before long mission runtime.

## Non-Goals

```text
No vendor runtime bridge.
No vendor code copy.
No new external powers in P6Q0.
No Desktop L6 in P6Q0.
No Code/Shell harvest in P6Q0.
No model auto-selection over the user.
```
