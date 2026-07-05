# SENTINEL_REAL_PRODUCT_ATTEMPT_4E_SEMANTIC_CHANNEL_WORKER_FINISH_V1_REPORT

## Verdict

```text
REAL_PRODUCT_ATTEMPT_4E_SEMANTIC_APP_TEST_ADVANCE_TO_CHANNEL_WORKER_FINISH_V1 = VALID_FAILED
```

Primary actionable failure:

```text
MODEL_LOW_LEVEL_RUN_CHECK_PARAMS_LEAK
```

4E proved semantic app correctness and bounded local channel progress, but failed before worker/finish because the model supplied low-level code execution parameters that mapped to a blocked raw shell profile.

## Safe Preflight

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_present = true
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
credential_present = true
provider_native_tools_disabled = true
fallback_auto_disabled = true
```

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-product-attempt4e-20260706-014347
```

## Metrics

```text
provider_decision_calls = 7
model_native_intent_accepted_count = 7
material_action_count = 6
product_receipt_count = 6
product_finalgate_count = 6
mission_status = blocked
blocked_reason = code_exec_raw_shell_blocked
semantic_pytest_passed = true
bounded_channel_send = true
worker_dispatch = false
finish = false
replay_no_react = true
safety_scan_high_risk_hit_count = 0
```

## Action Sequence

```text
workspace_patch.apply_patch
workspace_patch.apply_patch
workspace_patch.apply_patch
code_execution_sandbox.code_exec.run_profile
code_execution_sandbox.code_exec.run_profile
bounded_channel.send_message
code_execution_sandbox.code_exec.run_profile
```

## Product Truth

What 4E proves:

```text
real provider product loop reached provider
semantic app files were created
external pytest passed
bounded fake/local channel send occurred
receipts/finalgates were issued
replay no-react held
raw material scan was clean
```

What 4E does not prove:

```text
worker verifier dispatch
finish after channel and semantic proof
full app -> check -> channel -> worker -> finish product path
```

## Required Fix

Proceed to:

```text
FIX_REAL_PRODUCT_RUN_CHECK_BOUNDED_PLAN_OWNS_PROFILE_V1
```

Required behavior:

```text
run_check is a simple model-facing skill
when a bounded check plan exists, Sentinel owns profile_id and args
model-supplied raw shell/profile parameters must not override the bounded plan
```

