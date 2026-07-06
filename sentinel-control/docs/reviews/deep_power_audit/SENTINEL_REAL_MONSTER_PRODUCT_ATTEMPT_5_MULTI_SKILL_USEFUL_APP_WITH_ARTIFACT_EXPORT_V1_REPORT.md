# SENTINEL_REAL_MONSTER_PRODUCT_ATTEMPT_5_MULTI_SKILL_USEFUL_APP_WITH_ARTIFACT_EXPORT_V1_REPORT

## Verdict

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5_MULTI_SKILL_USEFUL_APP_WITH_ARTIFACT_EXPORT_V1 = VALID_FAILED
primary_failure_classification = USEFUL_APP_OBJECTIVE_DEFAULT_PLAN_GAP
```

This was a valid real-provider product-spine run. It did not prove the useful-app objective because the workspace creation lane fell back to the legacy arbitrary app fixture.

## Provider

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

No endpoint value, credential value, raw provider output, or provider reasoning was persisted in this report.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt5-20260706-091500
```

## Product Spine Proof

```text
provider_decision_calls = 8
model_native_intent_accepted_count = 8
recoverable_provider_turns = 0
material_action_count = 7
product_receipt_count = 7
product_finalgate_count = 7
task_loop_certificate_count = 1
mission_status = completed
blocked_reason = none
```

Action sequence:

```text
workspace_patch:apply_patch
workspace_patch:apply_patch
workspace_patch:apply_patch
code_execution_sandbox:code_exec.run_profile
code_execution_sandbox:code_exec.run_profile
bounded_channel:send_message
worker_fleet:spawn_worker
sentinel_loop:finish
```

## Semantic Check

```text
external_pytest_passed = true
external_pytest_stdout_tail = 1 passed
```

This proves the generated project was syntactically and semantically checkable, but it checked the legacy arbitrary app behavior rather than the requested useful number-analyzer behavior.

## Artifact Export And Verifier

```text
artifact_export_accepted = true
artifact_verifier_accepted = true
bundle_id = mission_artifact_bundle_229593b6ee4d0c60
local_integrity_seal = cd5d900c78d497391226654878437a1ebcc41586d55961aa122e8412f1cbc508
verifier_failure_codes = []
checked_from_exported_bundle_only = true
```

Bundle path:

```text
C:\Users\youcef cheriet\.sentinel-runs\monster-runtime\real-monster-product-attempt5-20260706-091500\runs\mission_ac25de90b66a4e3780c6223622fbc38e\mission_workspace\artifact_exports\mission_artifact_bundle_229593b6ee4d0c60
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

## Failure Evidence

Expected useful-app markers were absent:

```text
useful_app_markers = []
```

Persisted safe file excerpts showed the old arbitrary fixture:

```text
app.py marker = Sentinel arbitrary local app worked.
README.md marker = Sentinel Local App / created from scratch by ProductActionKernel spine
tests/test_app.py marker = test_main_returns_message
```

The run completed correctly for the wrong app. This is not a provider failure, channel failure, worker failure, artifact-export failure, replay failure, or FinalGate failure.

## Root Cause

```text
USEFUL_APP_OBJECTIVE_DEFAULT_PLAN_GAP
```

The product task-loop workspace create-file plan recognized the objective as a from-scratch local app mission, then selected the legacy arbitrary-app default plan. It did not specialize the plan for the requested number-analyzer objective.

## Safety Scan

```text
safety_scan_high_risk_hit_count = 0
provider_native_tools = disabled
fallback_AUTO = disabled
raw_provider_reasoning_persisted = no
credential_values_persisted = no
```

## Recommended Next Fix

```text
FIX_REAL_MONSTER_USEFUL_APP_OBJECTIVE_CREATE_FILE_PLANS_V1
```

Required behavior:

```text
number-analyzer objective
-> app.py exposes analyze_numbers(values)
-> tests validate count, total, average
-> README describes the useful app
-> bounded pytest checks the useful behavior
-> channel + worker + finish remain product-spine actions
-> artifact export/verifier still pass
-> replay no-react still holds
```

Next real proof after local validation:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5B_USEFUL_APP_ARTIFACT_EXPORT_V1
```
