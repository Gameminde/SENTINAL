# SENTINEL_REAL_MONSTER_PRODUCT_ATTEMPT_5C_CHANNEL_GRANT_NORMALIZED_USEFUL_APP_EXPORT_V1_REPORT

## Verdict

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5C_CHANNEL_GRANT_NORMALIZED_USEFUL_APP_EXPORT_V1 = VALID_SUCCESS
```

This is the strongest Monster Runtime product proof so far.

5C proves:

```text
real provider
-> model-native simple skill decisions
-> RuntimeHost product task loop
-> ProductActionKernel
-> useful multi-file workspace app creation
-> semantic pytest
-> bounded fake/local channel receipt
-> worker verifier receipt
-> model finish
-> mission completed
-> artifact export accepted
-> verifier accepted from exported bundle
-> replay no-react
```

## Provider

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
provider_decision_calls = 7
model_native_intent_accepted_count = 7
model_native_failure_codes = []
provider_native_tools_disabled = true
fallback_AUTO = disabled
```

Safe endpoint state:

```text
endpoint_present = true
endpoint_hash = aec3b934d7d71744f60faa21da5f9e55e1efd715baa09306e784514497b9f271
credential_present = true
```

No endpoint value, credential value, raw provider output, or provider reasoning is persisted in this report.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt5c-20260706-095035
```

## Product Action Sequence

```text
workspace_patch:apply_patch
workspace_patch:apply_patch
workspace_patch:apply_patch
code_execution_sandbox:code_exec.run_profile
bounded_channel:send_message
worker_fleet:spawn_worker
sentinel_loop:finish
```

Counts:

```text
mission_status = completed
loop_final_reason = model_led_product_action_kernel_task_loop_finish
blocked_reason = none
material_action_count = 6
product_receipt_count = 6
product_finalgate_count = 6
task_loop_certificate_count = 1
channel_present = true
worker_present = true
finish_present = true
```

## Useful App Proof

Created app:

```text
app.py exposes analyze_numbers(values)
analyze_numbers returns count, total, average
main returns Sentinel useful number analyzer worked.
README.md documents Sentinel Number Analyzer
tests/test_app.py covers normal input, empty input, and main marker
```

Markers:

```text
useful_app_markers = analyze_numbers, number_summary_fields, semantic_number_tests, useful_main_marker
```

Safe file hashes:

```text
app.py sha256 = ecb474601407476a3bd5c9f81be24affb8143553c512fb97c75082b388edc0ce
README.md sha256 = dcf066a55f6a3e6a0bf26808fb7ce4ba372b40beff653ff94d2f58a3a54721dc
tests/test_app.py sha256 = 4e0fcfdc5ecee4d3f5e91e406b048da7cb5ab924d3bff59a7ea7ab0a8aba34b1
```

## Semantic Check

External workspace pytest:

```text
py -3.13 -m pytest . -q
3 passed in 1.13s
```

This is product-useful semantic proof, not only syntax proof.

## Channel Grant Normalization Proof

5B failed because model-supplied channel fields were allowed to override the granted bounded local channel. 5C ran after:

```text
FIX_MODEL_NATIVE_CHANNEL_GRANT_NORMALIZATION_V1
implementation_commit = 9c69c2c
```

5C proves the normalized path:

```text
bounded_channel:send_message = completed
channel receipt = present through ProductActionKernel
real external channel = not used
model-authored message content = allowed
transport/destination grant = Sentinel-owned
```

## Worker Proof

```text
worker_fleet:spawn_worker = completed
worker_present = true
```

The worker path is inside the product spine, not a side channel.

## Artifact Export And Verifier

```text
artifact_export_accepted = true
artifact_verifier_accepted = true
bundle_id = mission_artifact_bundle_92382aa7c52a9b8d
local_integrity_seal = c2c1c71d326b4a0181d0ac27b78bc9df03be591fa1a4ae12fd3d6be880ad697c
verifier_failure_codes = []
checked_from_exported_bundle_only = true
```

Bundle path:

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt5c-20260706-095035\runs\mission_067d419ea24540d7bd745141914f0f3a\mission_workspace\artifact_exports\mission_artifact_bundle_92382aa7c52a9b8d
```

## Replay

```text
replay_no_react = true
model_calls_delta = 0
product_dispatch_delta = 0
command_executions_delta = 0
channel_transport_sends_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
reexecuted_actions = false
```

Replay did not rerun code, resend channel, rewrite workspace, respawn workers, or create new receipts/finalgates.

## Safety Scan

```text
safety_scan_high_risk_hit_count = 0
provider-native tools = disabled
fallback/AUTO = disabled
credential persistence = no
raw provider output persistence = no
raw provider reasoning persistence = no
real external channel send = no
```

Hard boundaries preserved:

```text
payment / checkout / spend
credential or secret access
login / account mutation
contact supplier / external send outside grant
workspace escape
provider-native tools
fallback/AUTO
replay side effects
proof tampering / fake receipt
```

## Product Meaning

5C crosses the next threshold:

```text
Sentinel is no longer only proving first receipts or tiny local fixtures.
It can now let a real model drive a useful multi-skill product mission:
create useful code, verify it, notify a bounded channel, delegate a worker,
finish, export the proof bundle, verify the bundle, and replay without side effects.
```

## Remaining Gaps

Still not claimed:

```text
real external channel send inside this exact product loop
real browser/Cloak product backend in this exact product loop
long-running multi-worker planning beyond one verifier worker
production-grade app generation beyond a small number analyzer
```

## Recommended Next

Move from one useful local app proof to a richer product mission:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6_MULTI_WORKER_PRODUCT_BUILD_AND_VERIFY_V1
```

Target:

```text
real provider
-> model builds a slightly richer useful app
-> multiple semantic checks
-> at least two worker roles
-> artifact export/verifier
-> replay no-react
```
