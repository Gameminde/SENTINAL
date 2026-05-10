# P6Q Model Cost Projection Report

Date: 2026-05-10

## Summary

P6Q implements model cost projection around the user-selected model. Sentinel
does not choose the model for the user.

## User Model Contract

```text
UserModelContract
  selected_model
  ModelCostProfile
  ModelCapabilityProfile
  ContextBudgetPolicy
  QualityExpectationContract
```

## Configurable Profile Fields

```text
input_usd_per_1m
output_usd_per_1m
cached_input_usd_per_1m
context_window_tokens
supports_tool_calling
supports_vision
supports_prompt_caching
max_decision_frame_tokens
max_tool_schema_tokens
max_evidence_tokens
reserve_output_tokens
retry_budget
```

These values are configurable. They are not hardcoded truth because provider
pricing and capabilities change.

## Cost Projection

`DecisionFrameCostProjection` reports:

```text
input_tokens
output_tokens
cached_input_tokens
retry_budget
input_cost_usd
output_cost_usd
cached_input_cost_usd
retry_cost_usd
cache_savings_usd
total_estimated_usd
```

P6R5 code-grounded review hardened this behavior:

```text
decision_frame_tokens are measured, not capped before projection
decision_frame_over_budget records whether the selected model budget is exceeded
input cost is projected from measured decision_frame_tokens
```

This keeps token pressure honest for expensive or narrow-budget models. A
frame that exceeds the user's configured decision-frame budget must be visible
before P6R attempts compression.

## Cheap Vs Expensive Model Behavior

For cheap user-selected models, Sentinel can project broader exploration and
retry budget while still measuring total cost.

For expensive user-selected models, Sentinel can project tighter decision
frames and higher evidence requirements.

In both cases:

```text
model_override_attempted = false
```

Sentinel may recommend an alternative model, but it must not silently replace
the user's selected model.
