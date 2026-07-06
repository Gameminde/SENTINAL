# SENTINEL_REAL_MONSTER_PRODUCT_ATTEMPT_5B_USEFUL_APP_ARTIFACT_EXPORT_V1_REPORT

## Verdict

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5B_USEFUL_APP_ARTIFACT_EXPORT_V1 = VALID_FAILED
primary_failure_classification = MODEL_SUPPLIED_CHANNEL_FIELD_OVERRIDES_GRANTED_LOCAL_CHANNEL
secondary = CHANNEL_GRANT_NORMALIZATION_GAP
```

5B was a valid real-provider mission attempt. It proved the useful app objective and semantic check, then exposed a channel-parameter boundary bug before worker/finish/artifact export could complete.

## Provider

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
provider_decision_calls = 5
provider_native_tools_disabled = true
fallback_AUTO = disabled
```

No raw endpoint, credential value, raw provider output, or provider reasoning is persisted in this report.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt5b-20260706-094019
```

## Action Sequence

```text
workspace_patch:apply_patch
workspace_patch:apply_patch
workspace_patch:apply_patch
code_execution_sandbox:code_exec.run_profile
bounded_channel:send_message = blocked
```

Counts:

```text
mission_count = 5
product_receipt_count = 4
product_finalgate_count = 4
workspace_patch_receipt_count = 3
channel_receipt_count = 0
worker_receipt_count = 0
finish_present = false
mission_status = blocked
blocked_reason = bounded_channel_real_transport_not_authorized
```

## Useful App Proof

5B fixed the Attempt 5 objective gap. The workspace contains the requested useful number analyzer:

```text
app.py includes def analyze_numbers(values)
app.py returns count, total, average
app.py main marker = Sentinel useful number analyzer worked.
tests/test_app.py covers [1, 2, 3] and empty input
README.md describes Sentinel Number Analyzer
```

External semantic check:

```text
py -3.13 -m pytest . -q
3 passed
```

This proves:

```text
useful_app_markers = analyze_numbers, number_summary_fields, semantic_number_tests, useful_main_marker
```

## Failure Detail

The model chose `bounded_channel.send_message`, but included a model-supplied channel field:

```text
adapter_id = monster_fake_channel
channel = bounded_local_channel
recipients = founder@example.com
message = Sentinel number analyzer app is ready...
```

The mission-level local/fake channel grant expects Sentinel to own the transport/destination fields. Because the mapper let model payload fields override the granted channel field, the channel runtime treated it as unauthorized real transport and blocked:

```text
blocked_reason = bounded_channel_real_transport_not_authorized
```

This is the correct hard block for the resulting request, but the upstream model-native mapper should not have allowed a model-supplied transport channel to replace the granted bounded local channel.

## Root Cause

```text
CHANNEL_GRANT_NORMALIZATION_GAP
```

`ProductModelNativeDecisionClient` preserves model-authored channel payload too broadly. For the bounded local product-loop channel, the model may author message content, but Sentinel must own:

```text
adapter_id
channel
recipients
recipient_provenance
evidence_refs
idempotency_key
```

## Artifact Export

Artifact export was not reached because the loop blocked before finish:

```text
artifact_export_accepted = not_attempted_after_block
artifact_verifier_accepted = not_attempted_after_block
```

## Replay

Replay no-react was not the primary failure. The loop blocked before the completed mission artifact export path.

The successful material actions remained receipted:

```text
workspace patch receipts = 3
run_check product receipt = 1
channel send receipt = 0
```

## Safety

```text
provider-native tools = disabled
fallback/AUTO = disabled
credential persistence = no
raw provider/reasoning persistence in report = no
real external channel send = no
```

## Recommended Fix

```text
FIX_MODEL_NATIVE_CHANNEL_GRANT_NORMALIZATION_V1
```

Required behavior:

```text
model can author bounded message body
model cannot override adapter_id/channel/recipients/grant provenance
bounded local channel maps to the granted fake/local transport
channel receipt is produced
worker verifier can run
finish can complete
artifact export/verifier can run
replay no-react holds
```

Next real proof:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5C_CHANNEL_GRANT_NORMALIZED_USEFUL_APP_EXPORT_V1
```
