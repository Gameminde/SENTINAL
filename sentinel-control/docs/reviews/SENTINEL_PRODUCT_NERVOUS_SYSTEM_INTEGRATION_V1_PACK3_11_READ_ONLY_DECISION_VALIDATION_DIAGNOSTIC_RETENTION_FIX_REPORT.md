# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.11 READ-ONLY DECISION VALIDATION DIAGNOSTIC RETENTION FIX REPORT

Date: 2026-06-22

Base commit:

```text
1821bbb6c333395a0989f8e040d0fab07d6f7bd6
```

## Verdict

```text
PACK_3.11 = LOCALLY IMPLEMENTED
provider call = NOT EXECUTED
Pack 4 = NOT STARTED
push = NOT PERFORMED
```

Pack 3.11 does not prove a real-provider mission. It prepares Attempt 5H by ensuring the next blocked read-only decision exposes safe diagnostics instead of `null`.

## Attempt 5G Evidence

Attempt 5G proved:

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

Attempt 5G did not prove:

```text
successful governed read-only action = NOT PROVEN
receipt creation under real model = NOT PROVEN
report lane = NOT PROVEN
FinalGate accepted = NOT PROVEN
MissionKernel COMPLETED = NOT PROVEN
```

Observed blocker:

```text
read_only_spine_blocked.metadata.read_only_model_diagnostics = null
typed_failure_code = READ_MODEL_DECISION_ERROR
runtime_phase = model_decision
exception_class = ValidationError
```

## Diagnostic Loss Location

```text
diagnostic_loss_location =
sentinel/operator/read_only_model_clients.py::_record_model_completed
and Sentinel telemetry safety validation

diagnostic_loss_cause =
exception_wrap after telemetry diagnostic persistence rejected the diagnostics payload
```

The provider decision client already created diagnostics for direct validation failures. The missing case was when the model client raised before returning a normalized visible-output payload. A first fix built partial diagnostics for that path, but the telemetry event rejected the `diagnostic_missing_fields` list because the string value `provider_response_hash` was treated as unsafe payload. That telemetry exception then replaced the original decision failure and the spine recorded a generic blocked event with null diagnostics.

## Fix

The fix has three parts:

1. `ReadOnlyProviderDecisionClient.complete()` now catches model-client exceptions before a raw payload is returned and raises `ReadOnlySpineError` with partial safe diagnostics.
2. `ReadOnlyProviderReportClient.complete()` receives the same protection for the separate report lane.
3. `_record_model_completed()` is best-effort, so telemetry persistence cannot erase the mission-store diagnostic path.

For scanner compatibility, unavailable diagnostic field names are stored as a boolean mapping:

```json
{
  "diagnostic_missing_fields": {
    "provider_response_hash": true
  }
}
```

This preserves the missing-field evidence while avoiding free-form string payloads that trigger the safety scanner.

## Safe Diagnostic Example

```json
{
  "protocol_version": "read_only_research_decision_v1",
  "parse_stage": "read_only_decision_validation",
  "provider_response_hash": null,
  "json_object_detected": null,
  "top_level_type": null,
  "original_top_level_key_names": [],
  "validation_payload_key_names": [],
  "safe_metadata_filtered": false,
  "filtered_safe_metadata_keys": [],
  "unsafe_unknown_field_names": [],
  "missing_required_field_names": [],
  "unknown_field_names": [],
  "validation_error_codes": [
    "ValidationError",
    "model_client_exception"
  ],
  "validation_error_paths": [],
  "normalization_strategy": null,
  "content_extraction_source": null,
  "content_extraction_error": "model_client_exception",
  "finish_reason": null,
  "output_truncated": null,
  "conversation_or_phase": "read_only_exploration_decision",
  "diagnostic_retention_status": "partial",
  "diagnostic_missing_fields": {
    "provider_response_hash": true
  },
  "diagnostic_missing_reason": {
    "model_client_exception_before_visible_payload": true
  }
}
```

The diagnostic contains field names, enum labels, booleans, counts, nulls, and hashes only. It does not persist raw provider output, raw visible text, raw prompt, hidden reasoning, file contents, credentials, authorization material, or provider wrapper payload.

## Validation Preservation

This pack does not make invalid model decisions valid.

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

Attempt 5G replay showed:

```text
material replay purity = held
mission tree hash delta = 0
MissionRunStore event delta = 0
receipt/report/FinalGate/dispatch/MissionKernel deltas = 0
telemetry events delta = +1
telemetry metrics delta = +1
```

Classification:

```text
material replay purity = held
telemetry replay side-effect = known non-material side-effect
```

Pack 3.11 does not redesign replay telemetry. That should remain a later focused replay telemetry purity pack if needed.

## Focused Validation

Commands executed:

```text
py -3.13 -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py::test_pack3_11_model_client_validation_error_retains_partial_safe_diagnostics
```

Result:

```text
1 passed
```

Command:

```text
py -3.13 -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py
```

Result:

```text
20 passed
```

Command:

```text
py -3.13 -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py tests/operator/test_product_nervous_system_pack3.py tests/test_cockpit_mission_understanding_protocol_v2.py tests/test_cli_runtime_host_product_wiring_pack1b.py tests/operator/test_mission_lifecycle_service.py tests/operator/test_runtime_host_pack1.py tests/test_real_model_read_only_operator_production_spine_v1.py
```

Result:

```text
PASS
```

The configured quiet output emitted progress dots and no failure summary.

Command:

```text
py -3.13 -O -m pytest -q tests/operator/test_read_only_research_decision_protocol_pack3_7.py tests/operator/test_product_nervous_system_pack3.py tests/test_cockpit_mission_understanding_protocol_v2.py
```

Result:

```text
PASS
```

Pytest emitted the expected `python -O` assertion warning.

Command:

```text
py -3.13 -m compileall -q sentinel\operator\read_only_model_clients.py
```

Result:

```text
PASS
```

Command:

```text
git diff --check
```

Result:

```text
PASS
```

Targeted scan:

```text
raw_prompt/raw_response/raw_reasoning/reasoning_content/provider_wrapper/Authorization/apiKey/fallback true/AUTO/provider-native true
```

Result:

```text
No secret or provider-material persistence found.
Matches were limited to forbidden-key constants and tests proving rejection.
```

## Remaining Real-Model Risk

Attempt 5H may still fail to produce a valid read-only action. If it fails, the expected improvement is that Sentinel will now retain the safe structure-only reason instead of collapsing to `read_only_model_diagnostics = null`.

