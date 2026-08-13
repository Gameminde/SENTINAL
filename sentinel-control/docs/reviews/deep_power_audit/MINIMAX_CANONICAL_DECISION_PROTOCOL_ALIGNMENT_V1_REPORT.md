# MINIMAX_CANONICAL_DECISION_PROTOCOL_ALIGNMENT_V1

## Verdict

```text
MINIMAX_CANONICAL_DECISION_PROTOCOL_ALIGNMENT_V1
= IMPLEMENTED_LOCAL_CANDIDATE

C5B_CONTROLLED_LIVE_BROWSER_PRODUCT_MISSION_SOVEREIGN_V1
= CONSUMED_IMMUTABLE

provider_calls = 0
ProductActionKernel dispatch = 0
Browser actions = 0
FIXED_PROVEN = 0/65
```

This tranche did not rerun C5B, did not call NVIDIA, did not dispatch an
effect, and did not start a Browser action. It only aligns the canonical
decision transport boundary so future MiniMax/NVIDIA experiments cannot invent
an action from narrative, partial, ambiguous or unsupported provider output.

## Historical C5B Truth

The previous sovereign C5B run remains the only authorized V1 mission attempt.

```text
provider = nvidia / minimaxai/minimax-m3
historical provider calls = 1
historical ProductActionKernel dispatch = NOT_REACHED
historical browser actions = 0
historical failure = CANONICAL_DECISION_CAPABILITY_OPERATION_REQUIRED
```

The raw MiniMax response was not found in local artifacts. The safe artifacts
only preserve the typed failure, event hashes and counters. Therefore this
report does not claim the exact observed MiniMax response shape. It records the
absence honestly and proposes a separate decision-protocol-only probe if the
operator authorizes one later.

## Implementation

The canonical product model client now decodes provider transport through an
explicit profile list:

```text
native_tool_call
strict_json_content
fenced_strict_json
unsupported
```

A decision is accepted only when it explicitly selects an advertised capability
and operation, arguments validate against the visible capability graph schema,
and the `DecisionOrigin` chain records the transport transformation. Unknown
providers default to `unsupported`, so Sentinel does not silently assume JSON,
tool-call or response-format support.

Typed rejections are now covered for:

```text
content_absent
multiple_candidate_decisions
malformed_json
capability_missing
operation_missing
unknown_capability
unavailable_operation
invalid_arguments
narrative_only_response
unsupported_transport
```

NVIDIA MiniMax is marked as OpenAI-compatible chat without assumed tool calling,
JSON mode or JSON schema support. It can still be used through explicitly
configured visible-content JSON profiles; native tool calls require explicit
profile support and an unambiguous `capability.operation` tool name.

## Safe Telemetry

The diagnostic boundary records only safe shape telemetry:

```text
response root type
choices count
message/content presence and type
tool_calls presence/count
reasoning_content presence
finish_reason
content length bucket/hash
JSON detected
JSON root type
canonical fields present/missing
extraction stage
typed rejection reason
```

It does not persist raw provider output, raw arguments, URLs, private reasoning
or payload text.

Safe bundle:

```text
sentinel-control/docs/reviews/deep_power_audit/MINIMAX_CANONICAL_DECISION_PROTOCOL_ALIGNMENT_V1/minimax_decision_protocol_alignment.safe.json
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py -k "canonical_decision_client_accepts_openai_strict_json_content or canonical_decision_client_accepts_fenced_json_only_when_profile_allows or canonical_decision_client_accepts_native_tool_call_only_when_profile_allows or canonical_decision_transport_rejects_partial_or_ambiguous_outputs or canonical_decision_transport_rejects_unadvertised_tool_call_without_inventing_action or unknown_provider_profile_is_unsupported_without_silent_json_assumption or product_model_native_decision_client_can_emit_canonical_decision or public_product_cli_real_provider_mode_uses_product_native_transport or provider_failure_diagnostics_preserve_safe_auth_cause" -q
= 19 passed

py -3.13 -m pytest tests/test_real_model_execution_nvidia.py tests/test_model_provider_catalog.py::test_nvidia_catalog_registers_minimax_m3_openai_compatible_route -q
= 7 passed

py -3.13 -m compileall -q sentinel
= passed

git diff --check
= passed

JSON parse of ledger and safe bundle
= passed

targeted high-confidence secret scan over changed files
= passed
```

Final repository validation is recorded in the commit log and safe bundle for
this tranche. No provider call or browser run is part of those validations.

## Next Authorized Step

No C5B rerun is authorized by this report. If the operator wants the exact
MiniMax response shape, the next bounded step should be a separate:

```text
MINIMAX_DECISION_PROTOCOL_ONLY_V1
```

That probe would consume one provider call, execute no ProductActionKernel
effect, start no Browser action, and persist only the same safe shape telemetry.
