# Pack 3.10 Read-Only Decision Safe Metadata Filter Fix Report

## Canonical Scope

Pack 3.10 closes the Attempt 5F blocker:

```text
ATTEMPT_5F_EXPLICIT_BOOTSTRAP_READ_ONLY_DECISION = VALID_FAILED_DISPATCHED_BUT_BLOCKED
root_cause = READ_ONLY_DECISION_SAFE_METADATA_EXTRA_FIELD
```

No provider call was executed during this pack. Pack 4 was not started.

## Attempt 5F Evidence

Attempt 5F proved the product mission spine reached the correct execution lane:

```text
explicit product mission bootstrap = proven
cockpit provider calls = 0
mission queued / claimed / routed / dispatched = proven
first provider call = read_only_research_decision_v1
FinalGate = rejected / blocked
MissionKernel = BLOCKED
replay = zero-delta
workspace = unchanged
```

The first read-only decision failed at:

```text
parse_stage = read_only_decision_validation
protocol_version = read_only_research_decision_v1
json_object_detected = true
normalization_strategy = plain_json_object
content_extraction_source = choices[0].message.content
unknown_field_names = ["reasoning_char_count"]
```

## Origin Finding

```text
reasoning_char_count_origin = adapter_metadata_pollution
```

The OpenAI-compatible adapter extracts visible content from
`choices[0].message.content` and then appends safe reasoning-channel metadata
such as `reasoning_char_count` after inspecting provider reasoning fields.
The read-only decision validator previously allowed `reasoning_character_count`
but not the actual adapter key `reasoning_char_count`, so a safe diagnostic
field polluted the decision schema boundary.

This finding does not require accepting raw reasoning. It requires recognizing
one safe scalar adapter metadata key.

## Filter Policy

Before Pydantic validation of a read-only decision, Sentinel now treats only
explicit safe provider metadata keys as non-decision metadata, and only when
their values are scalar:

```text
string
number
boolean
null
```

The safe metadata list now includes:

```text
reasoning_char_count
visible_content_length
```

alongside existing provider/extraction metadata.

`provider_response_hash` remains a safe identity field, but is not counted in
`filtered_safe_metadata_keys`; this avoids duplicating provider-response labels
inside telemetry field-name lists while preserving the dedicated hash field.

Non-scalar metadata values are not filtered. They remain unsafe unknown fields.

## Authority Preservation

The fix does not weaken authority or action validation:

```text
required action field still required
action enum still enforced
arguments still pass read-only control-payload rejection
workspace/model/authority/budget/can_execute fields still rejected
raw reasoning fields still rejected
metadata object still rejected
unsafe actions still rejected
```

The following remain fail-closed:

```text
reasoning
reasoning_content
raw_reasoning
raw_prompt
raw_response
raw_visible_output
metadata
workspace
workspace_ref
model_contract_ref
authority
authority_scope
approval_scope
allowed_actions
budget
credentials
authorization
can_execute
can_grant_authority
tool_choice
tools
shell
write_file
```

## Diagnostics

Read-only decision diagnostics now expose structure-only metadata:

```text
safe_metadata_filtered
filtered_safe_metadata_keys
unsafe_unknown_field_names
validation_payload_key_names
original_top_level_key_names
```

Raw prompt, raw provider response, raw visible output, raw reasoning, provider
wrapper payload, file contents, credentials, and authorization material are not
persisted.

## Prompt Cleanup

The read-only decision prompt was tightened to emphasize the positive schema:

```text
Allowed top-level keys are exactly:
action
arguments
evidence_refs
operator_message
```

It also explicitly instructs the model not to emit diagnostic metadata such as
`reasoning_char_count`, and keeps compact safety bans for workspace/model/
authority fields and mutation/external actions.

## Proofs Added

Focused tests now prove:

```text
valid list_directory + reasoning_char_count validates after filtering
valid search_text + reasoning_char_count validates after filtering
reasoning_char_count alone does not invent a valid action
operator_message + reasoning_char_count does not invent a valid action
reasoning / reasoning_content / metadata remain rejected
workspace/model/authority/budget/can_execute remain rejected
safe metadata filtering can reach a governed read-only receipt
blocked invalid decisions still produce rejected FinalGate and BLOCKED mission state
replay remains zero-delta
```

The CLI fake-provider success fixture was updated to stop using raw provider
wrapper and raw reasoning fields as part of a successful response. Those fields
are now covered by explicit rejection tests instead of being silently ignored.

## Validation

Focused validation executed:

```text
py -3.13 -m pytest -q \
  sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py \
  sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py \
  sentinel-control/services/sentinel-core/tests/test_cockpit_mission_understanding_protocol_v2.py \
  sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py \
  sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py \
  sentinel-control/services/sentinel-core/tests/operator/test_runtime_host_pack1.py \
  sentinel-control/services/sentinel-core/tests/operator/test_mission_execution_coordinator.py \
  sentinel-control/services/sentinel-core/tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result:

```text
PASS
0 failed
```

Focused optimized validation executed:

```text
py -3.13 -O -m pytest -q \
  sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py \
  sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py \
  sentinel-control/services/sentinel-core/tests/test_cockpit_mission_understanding_protocol_v2.py \
  sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py
```

Result:

```text
PASS
0 failed
```

Additional gates:

```text
compileall touched modules = PASS
git diff --check = PASS
targeted secret/raw-provider/fallback/provider-native scans = PASS with benign deny-list mentions only
```

## Remaining Real-Model Risk

Pack 3.10 does not prove a real-provider mission. It prepares Attempt 5G by
preventing harmless safe metadata from blocking an otherwise valid read-only
decision.

Remaining risk:

```text
the model may still choose an invalid action
the model may still omit required action fields
the model may still request unsafe arguments
the model may still fail later report-lane validation
```

Those risks should be measured by exactly one next real-provider attempt, not
by broad speculative rewrites.
