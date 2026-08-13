# MODEL_FREEDOM_INTENT_BRIDGE_V1

## Verdict

```text
MODEL_FREEDOM_INTENT_BRIDGE_V1
= IMPLEMENTED_LOCAL_CANDIDATE

provider_calls = 0
ProductActionKernel dispatch = 0
Browser launches/actions = 0
FIXED_PROVEN = 0/65
```

This tranche changes the model-facing contract: models are no longer required
to speak Sentinel's internal `CanonicalDecision` IR. `CanonicalDecision` remains
the internal compiler output used before the governed ProductActionKernel
effect boundary.

## Important Truth

Before this direction correction was applied, one protocol-only MiniMax probe
from the prior directive was accidentally consumed:

```text
MINIMAX_DECISION_PROTOCOL_ONLY_V1
= VALID_REAL_PROVIDER_PROTOCOL_REJECTION

provider_calls = 1
ProductActionKernel dispatch = 0
Browser launches/actions = 0
typed_rejection_reason = capability_missing
```

That call is preserved as a separate non-C5B artifact. It was not hidden, not
used to patch the parser after observation, and did not dispatch an effect.

## Bridge

The new flow is:

```text
ModelExpression
-> CandidateIntent
-> validation against visible ExecutableCapabilityGraph
-> CanonicalDecision internal compiler output
-> ProductActionKernel governed effect boundary
```

The previous strict decoders remain fast paths, but they are no longer the only
language Sentinel understands.

Supported expression forms now include:

```text
native_tool_call
canonical JSON
partial JSON
affordance_id
function-like expression
ReAct-style action
explicit natural-language intent
final answer
```

## Rules

Compilation succeeds only when exactly one visible affordance is compatible
with the expressed intent and schema-valid arguments. If more than one route is
plausible, Sentinel returns `ambiguous_intent`. If material arguments are
missing, Sentinel returns `invalid_arguments`.

The bridge does not:

```text
create new capabilities
invent material arguments
grant authority
select from multiple plausible candidates
expose Playwright
add MiniMax-specific parsing
```

Selection basis is recorded in safe telemetry:

```text
explicit_native_tool
explicit_action_name
explicit_affordance_id
unique_schema_compatible_candidate
unique_semantic_candidate
explicit_final_answer
```

## Prompt Contract

The product prompt no longer says "Return exactly one JSON object". It tells
chat-only models they may express the next intent clearly using JSON,
`Action: ...`, function-like calls, explicit natural language, or a final
answer. Sentinel compiles only the execution-crossing intent and keeps the
model free to reason and explain.

## Validation

```text
py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py -k "model_expression_bridge" -q
= 6 passed

py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py -k "canonical_decision_client_accepts_openai_strict_json_content or canonical_decision_client_accepts_fenced_json_only_when_profile_allows or canonical_decision_client_accepts_native_tool_call_only_when_profile_allows or canonical_decision_transport_rejects_partial_or_ambiguous_outputs or canonical_decision_transport_rejects_unadvertised_tool_call_without_inventing_action or unknown_provider_profile_is_unsupported_without_silent_json_assumption or model_expression_bridge or product_model_native_decision_client_can_emit_canonical_decision or public_product_cli_real_provider_mode_uses_product_native_transport or provider_failure_diagnostics_preserve_safe_auth_cause" -q
= 23 passed
```

## Next Step

If the remaining offline gates pass, the next action in this same tranche is a
single live mission:

```text
C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION_SOVEREIGN_V2
```

No parser changes may be made after that live run starts.
