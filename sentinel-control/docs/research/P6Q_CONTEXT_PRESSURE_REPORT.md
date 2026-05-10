# P6Q Context Pressure Report

Date: 2026-05-10

## Purpose

P6Q gives Sentinel a way to measure context pressure before a model call.
This is the missing measurement layer between P6Q0 research and the P6R
subquadratic context engine.

## Measurement Fields

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

## Context Modes

P6Q compares:

```text
naive_full_context
summary_context
subquadratic_decision_frame
```

The comparison is deterministic and advisory. It does not call an LLM and does
not execute tools.

## Largest Pressure Source

The analyzer reports the largest token category. This is the bridge into P6R:

```text
tool_schema -> ToolSurfaceRouter
receipt_summary -> ReceiptGraphRetriever
workspace_tree/workspace_diff -> WorkspaceContextCard
market_signal/debate_transcript -> role summary cards
```

## P6R Inputs

P6Q emits concrete implementation inputs:

```text
token_ledger
decision_frame_cost_projection
tool_surface_router
receipt_graph_retriever
workspace_context_card
role_summary_cards
pressure_source:<category>
```

## Product Doctrine

```text
Receipts stay exact outside the prompt.
The model sees a compact decision frame.
The user-selected model remains the selected model.
```

