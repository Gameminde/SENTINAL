# SENTINEL_REAL_MONSTER_PRODUCT_ATTEMPT_7B_REAL_TELEGRAM_PRODUCT_SPINE_ARTIFACT_BUNDLE_V1_REPORT

## Verdict

```text
REAL_MONSTER_PRODUCT_ATTEMPT_7B_REAL_TELEGRAM_PRODUCT_SPINE_ARTIFACT_BUNDLE_V1 = VALID_FAILED
primary_failure_classification = MODEL_INTERNAL_ACTION_ENVELOPE_LEAKAGE
telegram_send_count = 0
```

7B was launched after fixing the channel-only mission workspace export gap. It did not send Telegram. The provider decision returned enough content to reach mission creation, but the model-native mapper allowed a canonical-ish `capability_id/operation` payload to pass as raw internal `ActionEnvelope` parameters. The mission lifecycle scanner correctly rejected those parameters as unsafe operator payload.

## Run

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt7b-20260706-150356
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
provider_call_started = true
telegram_send_attempted = false
```

Safe preflight facts were written:

```text
provider credential present = true
provider endpoint present = true
telegram token present = true
telegram chat present = true
provider-native tools disabled = true
fallback/AUTO disabled = true
```

No endpoint, credential, token, or chat ID values were printed or intentionally persisted.

## Failure

Observed failure:

```text
ValueError: mission_execution_request_parameters: unsafe operator payload
```

Failure location:

```text
ProductModelNativeDecisionClient.complete
-> ActionEnvelope-like bounded_channel decision
-> ModelLedProductActionKernelTaskLoop._dispatch_product_action
-> MissionLifecycleService.create_mission
-> reject_operator_control_payload(parameters)
-> unsafe operator payload
```

## Root Cause

`ProductModelNativeDecisionClient` treated any provider output with:

```text
capability_id
operation
params
```

as an already-canonical internal `ActionEnvelope`. That violated the Monster Runtime doctrine:

```text
ActionEnvelope = internal runtime language
model output = natural or semi-structured skill intent
```

For product skills, canonical-ish model output must be normalized back to the safe skill mapper, so parameters are rebuilt from:

```text
mission plans
mission-level channel destination grants
bounded runtime defaults
```

not accepted from the provider as operator-control material.

## Artifacts

The run interrupted before mission creation, so no product receipt, channel receipt, FinalGate, mission workspace, or artifact bundle exists for 7B.

```text
safe-preflight.json = present
safe-result.json = not written
mission_id = none
product_receipt_count = 0
telegram_send_count = 0
artifact_export = not reached
replay = not applicable
```

## Safety

This was a safe failure:

```text
Telegram send = not attempted
secret values persisted = false
provider raw output persisted = false
raw reasoning persisted = false
```

## Follow-Up Fix

```text
FIX_MODEL_NATIVE_CANONICAL_PAYLOAD_REMAP_TO_SAFE_SKILLS_V1
```

Required behavior:

```text
Known product capability_id/operation provider payloads map back to simple skills.
bounded_channel.send_message reconstructs params from mission channel grants.
model-supplied authority/control fields are discarded.
unknown canonical payloads may still use the internal path for compatibility.
```
