# SENTINEL FIX REAL MODEL CODE EXECUTION ACTION PROTOCOL OR CONTEXT V1 REPORT

## Verdict

```text
FIX_REAL_MODEL_CODE_EXECUTION_ACTION_PROTOCOL_OR_CONTEXT_V1 = LOCALLY_IMPLEMENTED_CANDIDATE
```

This is a narrow protocol/context reconciliation after:

```text
REAL_POWER_ATTEMPT_2_MODEL_LED_CODE_EXECUTION_LOOP_V1 = VALID_FAILED_FINISH_NOT_EMITTED
```

## Root Cause

Attempt 2 proved the real model could drive the Power Pack 3 loop through useful material actions:

```text
read_only_research.list_directory
code_execution_sandbox.code_exec.run_profile
workspace_patch.apply_patch
read_only_research.search_text
workspace_patch.run_bounded_check
```

The blocker was not provider, schema, Gate, patching, code execution, or verification. The loop closed at the material-action budget before the real model received a final finish-only turn, so the terminal reason was:

```text
model_led_task_loop_material_budget_reached
```

instead of:

```text
model_led_task_loop_finish
```

## Runtime Changes

Updated:

```text
sentinel/operator/decision_context.py
sentinel/operator/model_led_task_loop.py
tests/operator/test_power_pack3_code_execution_sandbox.py
```

The decision context now exposes safe completion signals:

```text
objective_satisfied
finish_available
recommended_next_action
finish_instruction
read_only_verification_summary
```

The model-led loop now allows exactly one finish-only decision turn after the material-action budget is reached when persisted receipts already prove:

```text
code execution receipt exists
workspace patch receipt exists
workspace/read-only verification receipt exists
sentinel_loop.finish is an available action
```

If the model emits any non-finish action during the finish-only turn, the loop blocks honestly:

```text
model_led_task_loop_finish_required_after_objective_satisfied
```

## What Did Not Change

```text
no new capability
no new execution power
no provider-native tools
no fallback/AUTO
no Gate bypass
no schema weakening
no raw provider/reasoning persistence
no credential handling change
no RuntimeHost adapter registration change
```

## Regression Proof

New tests prove:

```text
objective satisfied at material budget -> finish-only turn -> model_led_task_loop_finish
budget reached without objective satisfied -> model_led_task_loop_material_budget_reached
```

The second test preserves honest budget closeout for incomplete objectives.

## Validation

Commands run:

```text
py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack1_model_led_task_loop.py tests/operator/test_connection_live_channel_action_pack5.py tests/test_real_model_read_only_operator_production_spine_v1.py tests/test_cli_runtime_host_product_wiring_pack1b.py -q
```

Result:

```text
passed
```

```text
py -3.13 -m compileall sentinel/operator/code_execution_sandbox_models.py sentinel/operator/code_execution_sandbox_runtime.py sentinel/operator/code_execution_sandbox_replay.py sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/model_led_task_loop.py sentinel/operator/loop_guard.py
```

Result:

```text
passed
```

```text
git diff --check
```

Result:

```text
passed
```

Targeted scan:

```text
rg -n "API key|Authorization|raw_prompt|raw_response|raw_reasoning|reasoning_content|provider-native|provider_native|fallback|AUTO|Bearer|secret=|api_key=|curl|wget|shell=True|shell=False" sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py sentinel-control/services/sentinel-core/sentinel/operator/model_led_task_loop.py sentinel-control/services/sentinel-core/tests/operator/test_power_pack3_code_execution_sandbox.py
```

Result:

```text
runtime files clean
test-only redaction fixtures matched Authorization: Bearer token and secret=hidden
```

## Next Step

After this fix is committed, run exactly one real-provider attempt:

```text
REAL_POWER_ATTEMPT_2B_MODEL_LED_CODE_EXECUTION_LOOP_FINISH_V1
```

Expected proof target:

```text
real model emits sentinel_loop.finish explicitly
code execution happens
patch or verification happens
receipts/certificates persist
mission completes by model finish rather than material budget
replay does not rerun provider/tool/patch/check
```

## Confirmation

```text
provider call during fix = 0
source behavior changed only for finish-only closeout after objective receipts
new execution power = no
fallback/AUTO introduced = no
provider-native tools introduced = no
push = not performed
Power Pack 4 = not started
```
