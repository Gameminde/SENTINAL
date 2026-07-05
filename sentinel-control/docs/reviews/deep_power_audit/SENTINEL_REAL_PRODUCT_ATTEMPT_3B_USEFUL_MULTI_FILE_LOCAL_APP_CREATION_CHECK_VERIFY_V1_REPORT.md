# SENTINEL_REAL_PRODUCT_ATTEMPT_3B_USEFUL_MULTI_FILE_LOCAL_APP_CREATION_CHECK_VERIFY_V1_REPORT

## Verdict

```text
REAL_PRODUCT_ATTEMPT_3B_USEFUL_MULTI_FILE_LOCAL_APP_CREATION_CHECK_VERIFY_V1 = VALID_FAILED
primary_failure_classification = POST_MATERIAL_PROVIDER_EMPTY_VISIBLE_CONTENT_RECOVERY_GAP
secondary = HARNESS_EXPORT_ON_BLOCKED_PARTIAL_RUN_GAP
```

This was a consumed real-provider mission attempt.

## Safe Preflight

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = process scoped Aliyun/DashScope endpoint env
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
credential_present = true
endpoint_present = true
missing_config_names = []
provider_native_tools_disabled = true
fallback_AUTO_disabled = true
real_browser_disabled = true
real_external_channel_disabled = true
explicit_pre_material_recovery_turns = 1
```

No endpoint value, credential value, provider prompt body, provider response body, or provider reasoning is persisted in this report.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-product-attempt3b-20260705-145853
```

## Product Truth

3B improved over 3A.

```text
provider_decision_calls = 2
model_native_intent_accepted_count = 1
workspace_patch_count = 1
material_action_count = 1
product_receipt_count = 1
product_finalgate_count = 1
mission_status = blocked
blocked_reason = MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT
```

Actual action sequence:

```text
workspace_patch:apply_patch
```

Workspace result:

```text
app_marker_replaced = true
readme_marker_replaced = false
test_marker_replaced = false
```

The real model selected enough actionable intent for the first `workspace_patch.apply_patch`. Sentinel executed it through the product spine and produced a product receipt plus FinalGate.

## Receipt Proof

```text
receipt = product_action_kernel_receipt_e6ab3f8f3e1a4e2d8b504dae66cd0e1a
receipt capability = workspace_patch
receipt operation = apply_patch
receipt backend = workspace_patch_skill
receipt status = completed
replay_behavior = no_reexecute_on_replay
```

Loop FinalGate:

```text
accepted = false
reason = MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT
product_receipt_refs = [product_action_kernel_receipt_e6ab3f8f3e1a4e2d8b504dae66cd0e1a]
```

## Replay

```text
replay_no_react = true
reexecuted_actions = false
receipt_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
```

## Safety Scan

```text
safety_scan_hit_count = 0
credential_env_cleanup_confirmation = true
provider_native_tools = false
fallback_AUTO = false
real_browser_used = false
real_external_channel_used = false
```

## Failure Interpretation

The Pack 2 app creation path works for at least the first real model-selected patch.

The remaining blocker is:

```text
post-material empty provider content is terminal
```

The fix from `FIX_REAL_PRODUCT_PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION_V1` only allowed recovery before the first material action. 3B proved the same provider failure can occur after a successful material action, and should become a counted recovery lane instead of immediate mission death.

The harness also attempted bundle export on a blocked partial run and recorded a `ValueError`. That is secondary and should not obscure the product truth: one patch receipt was real; the mission blocked on the next model decision.

## Recommended Next Fix

```text
FIX_REAL_PRODUCT_POST_MATERIAL_EMPTY_CONTENT_RECOVERY_V1
```

Required behavior:

```text
1. Empty/unsupported provider visible content can become recoverable after material actions too.
2. Recovery must be explicit, counted, and budgeted.
3. Recovery must not create fake receipts.
4. Recovery context must include prior product receipts and the strongest next skill.
5. Bundle export should not be attempted for blocked partial runs unless using a partial-run bundle mode.
6. Default behavior remains no silent retry unless the attempt contract opts in.
```

## Next Real Attempt After Fix

```text
REAL_PRODUCT_ATTEMPT_3C_USEFUL_MULTI_FILE_LOCAL_APP_CREATION_CHECK_VERIFY_V1
```

Success threshold:

```text
provider_decision_calls >= 6
workspace_patch.apply_patch count >= 3
bounded check run
fake/local channel receipt
worker verifier receipt
sentinel_loop.finish
mission completed
artifact bundle accepted
offline verifier accepted
replay no-react
unsafe-material scan clean
```
