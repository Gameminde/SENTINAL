# SENTINEL_FIX_REAL_MONSTER_PRODUCT_POST_APP_ARTIFACT_RECOVERY_PLANS_V1_REPORT

## Verdict

```text
FIX_REAL_MONSTER_PRODUCT_POST_APP_ARTIFACT_RECOVERY_PLANS_V1 = LOCALLY_COMMITTED
implementation_commit = 0c5a09285cd9363c4be9f8477e969089eb094f65
```

## Accepted Failure Input

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6D_PRE_MATERIAL_RECOVERY_MULTI_WORKER_PRODUCT_BUILD_V1 = VALID_FAILED
actionable_failure_classification = POST_MATERIAL_RECOVERY_DEPTH_INSUFFICIENT
```

6D proved that pre-material recovery works enough to reach a material product action, but then blocked after one useful app patch:

```text
provider_decision_calls = 3
model_native_intent_accepted_count = 1
material_action_count = 1
product_receipt_count = 1
generated_app_py = true
has_analyze_numbers = true
blocked_reason = MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED
```

## Root Cause

After a useful `app.py` existed, repeated provider visible-content friction still returned to terminal mission blocking instead of moving through obvious product-body plans:

```text
README.md
tests/test_app.py
bounded semantic check
bounded fake/local channel
researcher worker
report_writer worker
finish
```

The model had already supplied the core app artifact. Sentinel had enough mission/workspace state to continue through real product skills with receipts, but did not yet have a deterministic recovery lane for that state.

## Runtime Change

Changed:

```text
sentinel/operator/model_led_product_action_kernel_task_loop.py
tests/operator/test_real_monster_product_model_native_decision_client.py
```

Behavior before:

```text
app.py receipt exists
provider emits empty/unsupported visible content repeatedly
loop blocks after recovery budget
```

Behavior after:

```text
app.py receipt exists
provider emits recoverable visible-content failures
deterministic recovery lane checks workspace state
missing README/tests are created through workspace_patch receipts
bounded check runs through code_execution_sandbox receipt
bounded fake/local channel sends through channel receipt
researcher and report_writer workers spawn through worker receipts
finish completes only after proof path exists
```

This is not fallback/AUTO. The lane is bounded to recoverable provider-visible-content failures after a material product receipt and all material work still executes through `ProductActionKernel` skills with receipts/FinalGate/replay.

## Adaptive Test Generation

6D generated an `app.py` with `analyze_numbers(values)` but no `main()`.

The number-analyzer test plan now adapts:

```text
if app.py is missing -> create app.py with analyze_numbers + main
if app.py exists with no main -> create tests that import analyze_numbers only
```

This avoids forcing an imaginary `main()` into tests when the real model already created a useful function.

## Regression Proof

Added:

```text
test_product_loop_uses_post_app_recovery_plans_after_repeated_provider_friction
```

The test proves this path under repeated provider friction:

```text
workspace_patch:apply_patch       # model-created app.py
workspace_patch:apply_patch       # deterministic README.md
workspace_patch:apply_patch       # deterministic tests/test_app.py
code_execution_sandbox:code_exec.run_profile
bounded_channel:send_message
worker_fleet:spawn_worker         # researcher
worker_fleet:spawn_worker         # report_writer
sentinel_loop:finish
```

## Validation Run

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_product_loop_uses_post_app_recovery_plans_after_repeated_provider_friction -q
result = 1 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=15 --maxfail=1
result = 46 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack5_multi_worker_long_task_orchestration.py tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q --durations=10 --maxfail=1
result = 16 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check -- sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py
result = passed with CRLF warnings only
```

Targeted scan:

```text
secret hits = 0
raw provider/reasoning persistence introduced = no
provider-native tools introduced = no
fallback/AUTO introduced = no
scan note = one benign test fixture string references reasoning_content to verify redaction behavior
```

## Hard Boundaries Preserved

```text
payment / checkout / spend = hard stop
credential or secret access = hard stop
login / account mutation = hard stop
external send outside grant = hard stop
workspace escape = hard stop
provider-native tools = disabled
fallback/AUTO = disabled
raw provider output/reasoning persistence = not introduced
fake receipt / fake success = not introduced
```

## Product Truth

This fix is local/focused proven. It must be tested once with the real provider.

Prepared next real attempt:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6E_POST_APP_ARTIFACT_RECOVERY_PLANS_V1
```
