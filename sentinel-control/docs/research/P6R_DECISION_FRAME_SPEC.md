# P6R Decision Frame Spec

Date: 2026-05-10

## Purpose

`LLMDecisionFrame` is the compact decision object Sentinel sends to the
user-selected model. It exists to prevent raw mission dumps while preserving the
minimum cognition needed for the next decision.

## Included By Default

```text
mission_card
authority_card
progress_card
top_k_evidence
selected_tool_surface
current_blockers
next_decision_options
required_output_schema
receipt_refs
```

The frame carries receipt refs so exact receipts can be replayed outside the
prompt.

## Excluded By Default

```text
all raw receipts
all raw files
all browser pages
all API outputs
all channel messages
all tool schemas
all debate transcripts
all historical state
raw secret-like values
```

## Construction Flow

```text
ContextNeedEstimator
-> ReceiptGraphRetriever
-> EvidenceRanker
-> StateCardBuilder / AuthorityCardBuilder
-> ToolSurfaceRouter
-> PromptBudgetAllocator
-> LLMDecisionFrame
-> DecisionFrameVerifier
```

## Verification Metrics

```text
authority_preserved = true
critical_evidence_preserved = true
tool_surface_minimized = true
receipt_refs_resolvable = true
deterministic_frame_hash = true
prompt_budget_respected = true
no raw secret leakage = true
no authority expansion = true
```

## Compression Target

The hard target for P6R is:

```text
20k-30k raw context -> 1k-2k decision frame
```

The target is valid only when authority constraints, critical evidence refs,
current objective, blockers, selected tool correctness, and receipt replay
integrity remain preserved.

## User Model Rule

`PromptBudgetAllocator` uses the `UserModelContract` selected by the user. It
does not pick a different model. Model cost, context window, cache behavior, and
quality expectation remain configurable profiles.

## Authority Rule

Decision frames cannot grant tools, actions, paths, browser powers, payment
powers, credentials, or authority. They only select the relevant already-allowed
tool surface for the next LLM decision.
