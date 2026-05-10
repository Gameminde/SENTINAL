# P6Q0 Context Economy Findings

Date: 2026-05-10

## Core Finding

Context economy is now a gating layer for stronger organs.

The question is not only:

```text
Can Sentinel act?
```

The new question is:

```text
Can Sentinel act for a long mission without paying the full token cost of
every past observation, receipt, tool schema, file, page, draft, and debate?
```

## User-Selected Model Doctrine

P6Q0 locks this product rule:

```text
The user chooses the LLM.
Sentinel optimizes the selected LLM.
```

Sentinel may recommend a model class, but it must not silently replace the
user's selection. A cheap user-selected model should be used with broader
batching and careful verification. An expensive user-selected model should
receive a tighter, higher-quality, proof-rich decision frame.

Model prices and context lengths are not hardcoded truth. They are configurable
profiles:

```text
UserModelContract
ModelCostProfile
ModelCapabilityProfile
ContextBudgetPolicy
QualityExpectationContract
```

## Why P6Q/P6R Must Precede Desktop L6

Desktop L6 is the closest existing organ to production-scoped execution, but it
is also a context amplifier.

Desktop can generate:

```text
workspace trees
file contents
file diffs
write receipts
rollback metadata
path containment proof
errors and retries
future screen/window/clipboard summaries
```

If the LLM sees all of that raw, Sentinel becomes expensive and confused. If
the LLM sees a compact decision frame, Sentinel becomes stronger and cheaper.

## Measurement Targets For P6Q

P6Q should measure these fields:

```text
raw_context_tokens
compressed_context_tokens
decision_frame_tokens
tool_schema_tokens
receipt_summary_tokens
workspace_tree_tokens
browser_output_tokens
api_output_tokens
channel_draft_tokens
market_signal_tokens
authority_card_tokens
state_card_tokens
estimated_cost_by_user_model
retry_cost_projection
cache_savings_if_available
```

It should compare:

```text
naive_full_context
summary_context
subquadratic_decision_frame
```

## P6R Engine Shape

P6R should build a Sentinel-native context engine:

```text
TokenLedger
ContextNeedEstimator
ReceiptGraphRetriever
EvidenceRanker
StateCardBuilder
AuthorityCardBuilder
ToolSurfaceRouter
PromptBudgetAllocator
LLMDecisionFrame
```

The LLM should see:

```text
mission card
authority card
progress card
top-k evidence
selected tool surface
current blockers
next decision options
required output schema
```

The LLM should not see by default:

```text
all receipts
all files
all browser pages
all API outputs
all channel messages
all tool schemas
all debate transcripts
all historical state
```

## Acceptance Target

P6R should demonstrate:

```text
20k-30k raw context -> 1k-2k decision frame
authority constraints preserved
critical evidence preserved
tool surface minimized
receipts exact outside prompt
deterministic replay possible from receipt refs
```

## Vendor Lessons

Hermes provides the strongest context-engine evidence:

```text
context engine interface
token usage tracking
compression threshold
head/tail protection
tool output pruning
trajectory compression metrics
```

OpenClaw and JARVIS show why context pressure grows:

```text
broad tool manifests
browser and channel outputs
desktop and sidecar observations
file and shell outputs
approval and trace metadata
```

OpenJarvis shows why cost must be part of routing:

```text
model fit
latency
hardware/local-cloud signals
query complexity
```

TradingAgents shows why role outputs need aggregation:

```text
analyst reports
debate transcripts
risk arguments
portfolio decisions
outcome memory
```
