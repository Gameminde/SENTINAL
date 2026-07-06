# SENTINEL_REAL_MONSTER_PRODUCT_ATTEMPT_7A_REAL_TELEGRAM_PRODUCT_SPINE_SEND_V1_REPORT

## Verdict

```text
REAL_MONSTER_PRODUCT_ATTEMPT_7A_REAL_TELEGRAM_PRODUCT_SPINE_SEND_V1 = VALID_FAILED
primary_failure_classification = MISSION_WORKSPACE_ARTIFACT_EXPORT_GAP
live_telegram_product_power = PROVEN
```

7A proved the real provider can drive a live Telegram send through the unified product spine, but the attempt is not full Monster Runtime success because the signed mission artifact exporter could not export the channel-only run.

## Run

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt7a-20260706-144315
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_value_persisted = false
credential_value_persisted = false
telegram_token_or_chat_value_persisted = false
```

Preflight safe facts:

```text
provider credential present = true
provider endpoint present = true
telegram token present = true
telegram chat present = true
provider-native tools disabled = true
fallback/AUTO disabled = true
```

## Product Path

```text
real provider decision
-> model-native skill intent
-> RuntimeHost product task loop
-> ProductActionKernel
-> bounded_channel.send_message
-> Telegram live channel transport
-> ProductActionKernel receipt
-> ProductActionKernel FinalGate
-> model-native finish
-> product task-loop final certificate
-> replay no-react
```

Observed action sequence:

```text
bounded_channel:send_message
sentinel_loop:finish
```

## Metrics

```text
provider_decision_calls = 2
request_factory_calls = 2
model_native_intent_accepted_count = 2
model_native_failure_codes = []
material_action_count = 1
telegram_send_count = 1
finish_present = true
mission_status = completed
product_receipt_count = 1
product_finalgate_count = 1
task_loop_certificate_count = 1
```

Safe receipt refs:

```text
mission_id = mission_4fb1360b13be4052bc1a725bfef8f0f8
product_receipt = product_action_kernel_receipt_2ca9cb93821649348ba770dfe4d2725b
product_finalgate = product_action_kernel_finalgate_2b5d621339374996b6db411bc7eb95bb
task_loop_finalgate = product_action_kernel_task_loop_finalgate_a302e6b3ab5644caa3a7353f064f1c37
channel_adapter_receipt = channel_adapter_receipt_43c2f8220d7d46a083a101be1181f5f4
channel_receipt = channel_receipt_ed61e575ae6a45b1971f80bc42733735
```

The delivery ref was persisted as a safe Telegram delivery reference and provider message hash. No Telegram token or chat ID value was persisted.

## Replay

```text
model_calls_delta = 0
product_dispatch_delta = 0
command_executions_delta = 0
channel_transport_sends_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
reexecuted_actions = false
replay_no_react = true
```

Replay did not resend the Telegram message.

## Artifact Export Gap

```text
artifact_export = failed
artifact_export_failure = artifact_export_failure:ValueError
root_cause = channel-only product task loop mission did not prepare mission_workspace/manifest.json
```

The Pack 6 artifact exporter expects the owner mission to contain:

```text
mission_workspace/manifest.json
artifact_export handle
```

The channel-only live product route wrote channel, ProductActionKernel, FinalGate, telemetry, and replay artifacts, but no `mission_workspace` manifest. This is a product-spine body gap, not a Telegram delivery failure.

## Safety Scan

Targeted scan over the 7A run root:

```text
Authorization hits = 0
Bearer hits = 0
SENTINEL_CERT_MODEL_API_KEY hits = 0
SENTINEL_TELEGRAM_BOT_TOKEN hits = 0
SENTINEL_TELEGRAM_CHAT_ID hits = 0
api key hits = 0
raw_provider_response hits = 0
raw_reasoning hits = 0
reasoning_content hits = 0
cookie hits = 0
session token hits = 0
CLOAKBROWSER_BINARY_PATH hits = 0
high_risk_hit_count = 0
```

Process-scoped provider and Telegram environment values were removed by the runner after the command scope.

## Interpretation

7A is a strong power proof:

```text
real provider -> product spine -> real Telegram send -> receipt -> finish -> replay no-resend
```

But it is not the full signed-verifiable Monster Runtime proof because:

```text
mission artifact bundle export = missing channel-only mission workspace body
```

## Next Fix

```text
FIX_PRODUCT_TASK_LOOP_MISSION_WORKSPACE_BODY_FOR_CHANNEL_ONLY_RUNS_V1
```

Required behavior:

```text
Every ProductActionKernel task-loop material mission prepares the MissionWorkspaceRuntime body before dispatch.
Channel-only product loops must export and verify signed mission artifact bundles.
Replay must remain no-react.
No provider call during implementation.
No real Telegram send during implementation.
```
