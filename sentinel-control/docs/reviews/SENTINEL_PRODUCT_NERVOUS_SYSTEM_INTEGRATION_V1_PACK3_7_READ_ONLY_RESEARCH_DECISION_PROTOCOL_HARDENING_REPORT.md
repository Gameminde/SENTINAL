# Sentinel Product Nervous System Integration V1

## Pack 3.7 — Read-Only Research Decision Protocol Hardening

Status: locally implemented and focused-validation green.

Base commit:

```text
f1d4417eb1cb80b6b1f1e66a234be139cb4a3521
```

## Attempt 5C Interpretation

Attempt 5C is treated as valid failed evidence:

```text
ATTEMPT_5C_WITH_HARDENED_COCKPIT_V2 = VALID_FAILED_DISPATCHED_BUT_BLOCKED
classification = DISPATCHED_BUT_BLOCKED
root_cause = READ_ONLY_RESEARCH_EXPLORATION_DECISION_SCHEMA_ADHERENCE
```

What it proved:

- the real product route reached the provider;
- cockpit mission understanding V2 was active;
- a mission was created and dispatched;
- the dispatcher reached the read-only research route;
- the failure moved from cockpit setup into the exploration decision lane.

What it did not prove:

- a successful read-only research mission;
- a valid real-provider exploration decision;
- a successful report lane;
- Pack 4 readiness.

## Old Versus New Decision Prompt

Before Pack 3.7, the read-only decision prompt was a compact schema reminder:

```text
Return exactly one read-only exploration decision JSON object.
allowed_actions = list_directory, read_file_segment, search_text, finish_exploration
schema = action, arguments, evidence_refs, operator_message
```

After Pack 3.7, the prompt is still bounded and generic, but explicitly states:

- protocol version: `read_only_research_decision_v1`;
- return exactly one JSON object;
- no Markdown wrapper;
- no prose outside JSON;
- no reasoning;
- no legacy `OperatorLLMDecisionResult`;
- no `MissionStartProposal`, `OperatorIntent`, `MissionDraft`, or `MissionAuthoritySummary`;
- no model-owned workspace, `workspace_ref`, `model_contract_ref`, credentials, budget, approval scope, authority, `allowed_actions`, or `can_execute`;
- one action per turn;
- minimal skeleton examples for `list_directory`, `search_text`, `read_file_segment`, and `finish_exploration`.

The prompt remains advisory only. Sentinel still owns authority, workspace binding, model-contract binding, request creation, Gate checks, receipts, FinalGate, and MissionKernel closeout.

## Decision Schema Summary

Provider-visible decision object:

```json
{
  "action": "list_directory | read_file_segment | search_text | finish_exploration",
  "arguments": {},
  "evidence_refs": [],
  "operator_message": "optional short display text"
}
```

Rejected provider-owned control fields include:

```text
workspace
workspace_ref
path as a top-level field
allowed_paths
model_contract_ref
authority_scope
approval_scope
allowed_actions
budget
credentials
authorization
authority
authority_envelope
can_execute
can_grant_authority
authority_effect
data_not_authority
MissionStartProposal
MissionDraft
MissionAuthoritySummary
OperatorIntent
```

`path` remains legal only inside governed action arguments, where the read-only spine applies snapshot-root, sensitive-path, excluded-path, symlink, and authority checks.

## Safe Diagnostics

Read-only decision failures now carry structure-only diagnostics on the `ReadOnlySpineError` and relay them into the blocked mission event.

Example shape:

```json
{
  "protocol_version": "read_only_research_decision_v1",
  "parse_stage": "read_only_decision_validation",
  "provider_response_hash": "hash_bad_decision",
  "visible_content_length": 2,
  "finish_reason": "stop",
  "output_truncated": false,
  "json_object_detected": true,
  "top_level_type": "dict",
  "top_level_key_names": [],
  "missing_required_field_names": ["action"],
  "unknown_field_names": [],
  "validation_error_codes": ["missing"],
  "validation_error_paths": ["action"],
  "markdown_fence_detected": null,
  "multiple_json_objects_detected": null,
  "normalization_strategy": "plain_json_object",
  "content_extraction_source": "choices[0].message.content",
  "content_extraction_error": null
}
```

Diagnostics intentionally exclude:

- raw prompt;
- raw provider wrapper;
- raw visible output;
- raw reasoning;
- field values from the model;
- credentials;
- authorization material.

## Response Extraction And Normalization

The OpenAI-compatible provider already performs deterministic visible-content extraction and normalization:

- plain JSON object accepted;
- a single JSON object in one Markdown JSON fence normalized by the provider layer;
- empty content classified as `empty_visible_content`;
- non-object JSON classified as `json_value_not_object`;
- invalid or truncated JSON classified without persisting raw text.

Pack 3.7 consumes that safe metadata without allowing it to pollute the Pydantic decision schema.

## Provider Call Counters

The read-only provider clients now use the existing telemetry surface:

- `record_model_call_started`;
- `record_model_call_completed`;
- `schema_invalid=True` for invalid exploration or report schema.

The request metadata includes:

```text
read_only_lane = exploration_decision
read_only_lane = final_report
```

This separates:

- cockpit model calls;
- read-only exploration decision calls;
- read-only final report calls.

No provider-native tools and no fallback/AUTO behavior are introduced.

## Blocked FinalGate Behavior

If a real provider produces an invalid read-only decision:

```text
provider response
-> safe diagnostics
-> ReadOnlySpineError
-> no decision checkpoint
-> no tool execution
-> no action receipt
-> rejected read-only FinalGate
-> read_only_spine_blocked event with diagnostics
-> MissionKernel BLOCKED
```

The blocked path does not fabricate:

- successful action receipts;
- report artifacts;
- accepted FinalGate certificates;
- completed MissionKernel state.

## Replay Purity

The Pack 3.7 blocked-path regression asserts replay remains read-only:

- model call count does not increase;
- tool call count does not increase;
- receipt write count does not increase;
- FinalGate write count does not increase;
- mission events are not re-executed.

Replay reconstructs from persisted events and artifacts only.

## JSON-Mode Gating

Pack 3.7 does not add a new JSON response-format switch.

Existing provider behavior remains:

- JSON response format is sent only when request metadata asks for it and backend metadata declares JSON-mode support;
- no hidden provider-specific fallback is introduced;
- read-only validation remains local and fail-closed.

## Files Changed

Expected implementation files:

- `sentinel-control/services/sentinel-core/sentinel/operator/read_only_model_clients.py`
- `sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py`
- `sentinel-control/services/sentinel-core/sentinel/cli.py`

Expected tests:

- `sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py`

## Remaining Real-Model Risk

Pack 3.7 increases the probability that DeepSeek/Aliyun returns a valid read-only exploration decision and makes future failures more diagnosable.

It does not prove:

- the next real-provider mission will complete;
- the model will choose useful actions;
- the final report will be high quality;
- Pack 4 or additional capability surfaces are ready.

Next real-provider attempt should be a single Attempt 5D-style run only after focused local validation is green and this pack is committed locally.

## Focused Validation

Executed focused commands:

```text
py -3.13 -m pytest -q sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py sentinel-control/services/sentinel-core/tests/test_cockpit_mission_understanding_protocol_v2.py sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py sentinel-control/services/sentinel-core/tests/operator/test_runtime_host_pack1.py sentinel-control/services/sentinel-core/tests/test_llm_operator_model_client_v0.py sentinel-control/services/sentinel-core/tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result:

```text
137 passed
```

```text
py -3.13 -O -m pytest -q sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py sentinel-control/services/sentinel-core/tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result:

```text
77 passed
```

```text
py -3.13 -m pytest -q sentinel-control/services/sentinel-core/tests/operator/test_mission_execution_coordinator.py sentinel-control/services/sentinel-core/tests/operator/test_agent_runtime_event_bridge_pack2a.py
```

Result:

```text
37 passed
```

```text
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/read_only_model_clients.py sentinel-control/services/sentinel-core/sentinel/operator/read_only_operator_spine.py sentinel-control/services/sentinel-core/sentinel/cli.py
```

Result:

```text
PASS
```

```text
git diff --check
```

Result:

```text
PASS
```

Targeted safety scan result:

```text
No API key or Authorization material found in changed files.
Provider-material terms appear only in denylist keys or negative documentation statements.
No fallback/AUTO implementation and no provider-native tool material introduced.
```
