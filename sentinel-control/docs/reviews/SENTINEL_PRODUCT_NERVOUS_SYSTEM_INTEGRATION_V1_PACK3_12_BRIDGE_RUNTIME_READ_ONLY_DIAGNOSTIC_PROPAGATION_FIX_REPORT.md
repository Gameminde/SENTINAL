# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.12 BRIDGE RUNTIME READ-ONLY DIAGNOSTIC PROPAGATION FIX REPORT

Date: 2026-06-23

Base commit:

```text
dc48a8a4076ee76f0c99bb276b2258c36453a71a
```

## Verdict

```text
PACK_3.12 = LOCALLY IMPLEMENTED
provider call = NOT EXECUTED
Pack 4 = NOT STARTED
push = NOT PERFORMED
```

Pack 3.12 does not prove a real-provider mission. It prepares Attempt 5I by ensuring real read-only decision failures retain safe diagnostics through bridge/runtime surfaces.

## Attempt 5H Evidence

Attempt 5H proved:

```text
explicit bootstrap mission creation = PROVEN
MissionExecutionRequest persistence = PROVEN
daemon claim = PROVEN
coordinator routing = PROVEN
dispatcher start = PROVEN
read-only spine start = PROVEN
first provider call in read_only_research_decision_v1 lane = PROVEN
false success avoided = PROVEN
workspace unchanged = PROVEN
material replay purity = PROVEN
```

Attempt 5H did not cross the operational power threshold:

```text
governed read-only action receipt = NOT PROVEN
tool call = 0
receipt = 0
report artifact = 0
FinalGate accepted = false
MissionKernel = BLOCKED
```

Observed blocker:

```text
read_only_model_diagnostics = null
runtime_phase = bridge_runtime
typed_failure_code = BRIDGE_INTERNAL_FAILURE
read_only_decision_schema_invalid also appeared as a separate rejected FinalGate
```

## Bridge Diagnostic Loss Location

```text
bridge_diagnostic_loss_location =
sentinel/operator/read_only_operator_spine.py
  ReadOnlyProductionSpineSession._record_blocked()
  ReadOnlyProductionSpineSession.run_via_agent_runtime()

bridge_diagnostic_loss_cause =
blocked_result_mapping_loss after safe diagnostic payload collided with event/proof safety constraints
```

The important path is:

```text
ReadOnlyProviderDecisionClient.complete()
-> raises ReadOnlySpineError(... legacy_reason="read_only_decision_schema_invalid", diagnostics=...)
-> ReadOnlyProductionSpineSession.run()
-> _record_blocked()
-> read_only_spine_blocked event persistence
-> bridge wrapper observes failure if the original blocked result is not preserved
```

The original failure identity was also under-classified:

```text
reason = read_only_decision_schema_invalid
old typed_failure_code = READ_INTERNAL_RUNTIME_FAILURE
new typed_failure_code = READ_MODEL_DECISION_ERROR
```

## Fix

Pack 3.12 makes two narrow runtime-spine changes:

1. `read_only_decision_schema_invalid` and `read_only_report_schema_invalid` now map to `READ_MODEL_DECISION_ERROR`.
2. Read-only model diagnostics are made event-safe before MissionRunStore persistence.

Diagnostic safety now preserves canonical diagnostic field names such as:

```text
provider_response_hash
parse_stage
validation_payload_key_names
unsafe_unknown_field_names
diagnostic_retention_status
```

But labels that look like raw provider/reasoning/credential surfaces are not persisted literally. They are replaced with deterministic labels:

```text
diagnostic_label_hash:<sha256>
```

This keeps the structure useful while avoiding raw or misleading unsafe labels in durable MissionRunStore events.

## Safe Diagnostic Example

For a fake provider response containing an unsafe top-level field name, the retained event diagnostic is shaped like:

```json
{
  "protocol_version": "read_only_research_decision_v1",
  "parse_stage": "read_only_decision_validation",
  "provider_response_hash": "hash_forbidden_field",
  "json_object_detected": true,
  "top_level_type": "dict",
  "original_top_level_key_names": [
    "content_extraction_source",
    "json_object_detected",
    "normalization_strategy",
    "diagnostic_label_hash:<hash>",
    "visible_content_char_count"
  ],
  "validation_payload_key_names": [],
  "safe_metadata_filtered": true,
  "filtered_safe_metadata_keys": [
    "content_extraction_source",
    "json_object_detected",
    "normalization_strategy",
    "visible_content_char_count"
  ],
  "unsafe_unknown_field_names": [
    "diagnostic_label_hash:<hash>"
  ],
  "missing_required_field_names": [
    "action"
  ],
  "validation_error_codes": [
    "unknown_field"
  ],
  "normalization_strategy": "plain_json_object",
  "content_extraction_source": "choices[0].message.content",
  "conversation_or_phase": "read_only_exploration_decision",
  "diagnostic_retention_status": "retained"
}
```

The diagnostic does not persist raw provider output, raw visible content, raw prompt, raw reasoning, `reasoning_content`, file contents, credentials, authorization material, or provider wrapper payload.

## Failure Identity Preservation

For read-only decision validation failure:

```text
blocked_reason = read_only_decision_schema_invalid
typed_failure_code = READ_MODEL_DECISION_ERROR
runtime_phase = model_decision
MissionKernel = BLOCKED
FinalGate accepted = false
receipt_refs = []
```

`BRIDGE_INTERNAL_FAILURE` remains reserved for actual bridge/runtime failures rather than expected model-decision validation rejection.

## Duplicate FinalGate Handling

Pack 3.12 fixes the local duplicate path for this failure class. The regression test proves a single rejected read-only FinalGate is created for the invalid decision:

```text
finalgate reasons = ["read_only_decision_schema_invalid"]
```

Broader FinalGate deduplication is not redesigned here.

## Validation Preservation

This pack does not make invalid decisions valid.

Still rejected:

```text
missing action
unknown action
unsafe action
shell/write/credential/payment/email/browser-click
workspace_ref
model_contract_ref
authority
authority_scope
approval_scope
budget
can_execute
metadata object
reasoning
reasoning_content
raw_reasoning
raw_response
raw_prompt
```

No automatic repair, no second provider call, no fallback/AUTO, and no provider-native tools were added.

## Replay Telemetry Side-Effect

No replay redesign was performed.

Classification remains:

```text
material replay purity = held
telemetry replay side-effect = known_non_material_side_effect
```

## Focused Validation

RED test before fix:

```text
py -3.13 -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py::test_pack3_12_bridge_preserves_read_only_validation_diagnostics_with_forbidden_field_name
```

Result before fix:

```text
FAILED
old typed_failure_code = READ_INTERNAL_RUNTIME_FAILURE
```

Result after fix:

```text
1 passed
```

Pack 3.7 / 3.10 / 3.11 / 3.12 focused file:

```text
py -3.13 -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py
```

Result:

```text
21 passed
```

Additional validation results are recorded in the final Codex response for this pack.

Additional focused route validation:

```text
py -3.13 -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py tests/operator/test_product_nervous_system_pack3.py tests/test_cockpit_mission_understanding_protocol_v2.py tests/test_cli_runtime_host_product_wiring_pack1b.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_mission_execution_coordinator.py tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result:

```text
PASS
```

Python optimized focused slice:

```text
py -3.13 -O -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py tests/operator/test_product_nervous_system_pack3.py tests/test_cli_runtime_host_product_wiring_pack1b.py tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result:

```text
PASS
pytest emitted the expected warning that assert statements are ignored under python -O
```

Compile/check/scan:

```text
py -3.13 -m compileall -q sentinel\operator\read_only_operator_spine.py tests\operator\test_read_only_research_decision_protocol_pack3_7.py
git diff --check
targeted raw-provider/secret/fallback/provider-native scans
```

Result:

```text
PASS
scan occurrences are sanitizer constants, adversarial test inputs, and negative documentation only
```

## Remaining Real-Model Risk

Pack 3.12 only guarantees that the next real read-only decision failure should retain safe structured diagnostics through the bridge/runtime surfaces.

It does not prove:

```text
real model produces valid read-only action
tool call executes
receipt is produced
report lane is reached
FinalGate accepts
MissionKernel completes
```

Those remain the purpose of Attempt 5I.
