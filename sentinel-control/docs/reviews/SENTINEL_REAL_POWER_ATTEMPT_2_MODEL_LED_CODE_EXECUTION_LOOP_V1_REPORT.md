# SENTINEL REAL POWER ATTEMPT 2 MODEL LED CODE EXECUTION LOOP V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_2_MODEL_LED_CODE_EXECUTION_LOOP_V1 = VALID_FAILED_FINISH_NOT_EMITTED
```

This was a valid real-provider run after `POWER_PACK_3_SHELL_AND_CODE_EXECUTION_SANDBOX_V1`.

The run proved real model-led bounded code execution power, but it did not emit an explicit `sentinel_loop.finish` action before the material-action budget closed the loop. The mission terminal state is completed by budget, not by model finish.

## Real Provider Used

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_hash = aec3b934d7d71744f60faa21da5f9e55e1efd715baa09306e784514497b9f271
credential_present = true
```

No endpoint value, API key, Authorization header, raw provider output, raw prompt, raw reasoning, or provider wrapper payload is persisted in this report.

## Source

```text
source_commit = 46d0e8c33d592d5f4479ee99b4cae7df021e858f
```

Run root:

```text
C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt2-20260628-231803
```

## Mission Objective

```text
Run a model-led workspace loop that inspects the fixture, uses bounded code execution, patches README.md to say the Sentinel model-led code execution sandbox worked, verifies with bounded checks/read-only search, then finishes.
```

Temporary fixture:

```text
README.md initially contained a TODO marker for the model-led code execution patch.
```

## Decision Context Shape

The real model received safe context only:

```text
mission_objective
available_actions
budget_remaining
last_action_status
previous_receipt_refs
bounded_observation_summaries
workspace_patch_summary
workspace_verification_summary
code_execution_summary
workspace_targets
code_execution_profiles
```

The context included safe fixture metadata:

```text
README.md path
README.md current hash
known marker
desired replacement hint
available code execution profiles and safe argument examples
```

No raw model output was persisted.

## Parsed Action Sequence

The real model produced canonical `ActionEnvelope` decisions:

```text
1. read_only_research.list_directory
2. code_execution_sandbox.code_exec.run_profile
3. workspace_patch.apply_patch
4. read_only_research.search_text
5. workspace_patch.run_bounded_check
```

The model did not emit:

```text
sentinel_loop.finish
```

## Execution Results

```text
provider_decision_calls = 5
model_extraction_failures = 0
provider_failure = none
material_actions_executed = 5
code_commands_executed = 1
patch_applied = true
bounded_check_run = true
verification_action = true
finish = false
mission_status = completed
loop_final_reason = model_led_task_loop_material_budget_reached
blocked_reason = null
```

Receipts:

```text
code_exec_receipt_cf25f1c847654b08b633d0414be1e943
workspace_patch_receipt_dbda5de8ff8644b294137b3f2d7c2f5b
workspace_patch_verification_2bc76b9881c74175b31cf7b42e081fc0
```

Loop certificate:

```text
model_led_loop_finalgate_2dc097f198f34585961d9677c9c49f73
```

Mission id:

```text
mission_e7361b90e11041d3ad41feff2f5b0e7f
```

## Workspace Diff

```diff
--- README.before
+++ README.after
@@ -1,3 +1,3 @@
 # Real Power Attempt 2
 
-TODO: replace this marker with a model-led Sentinel code execution patch
+Sentinel model-led code execution sandbox worked.
```

Workspace mutation was limited to the temporary fixture `README.md`.

## Replay Proof

Replay views reconstructed from persisted artifacts and workspace fingerprint:

```text
model_calls_delta = 0
read_only_action_delta = 0
patch_application_delta = 0
bounded_check_delta = 0
code_command_delta = 0
workspace_mutation_delta = 0
receipt_writes_delta = 0
artifact_hashes_stable = true
stdout_stderr_hashes_stable = true
```

Replay did not recall the model, rerun read-only actions, reapply the patch, rerun bounded checks, rerun code execution, mutate the workspace, or write new receipts.

## Safety Scan

```text
credential values persisted = false
Authorization persisted = false
raw provider output persisted = false
raw prompt persisted = false
raw reasoning persisted = false
provider wrapper payload persisted = false
fallback/AUTO used = false
provider-native tools used = false
```

The scan found one benign policy string:

```text
record.json forbidden_actions contains provider_native_tools
```

This is a negative authority boundary, not provider-native tool use or persisted provider material.

## What Is Proven

```text
real model produced canonical ActionEnvelope decisions
real model chose bounded code execution
code_execution_sandbox.code_exec.run_profile executed
code execution receipt persisted
workspace_patch.apply_patch executed
read_only_research.search_text verification executed
workspace_patch.run_bounded_check executed
receipts were created
replay purity held
raw provider/reasoning/credential persistence remained absent
fallback/AUTO and provider-native tools remained off
```

## What Is Not Proven

```text
explicit model-chosen finish action
Power Pack 4 readiness
```

The model spent the fifth material action on `workspace_patch.run_bounded_check`; the loop then completed via material budget. This is useful power, but not the exact requested proof path.

## Recommended Next Action

```text
FIX_REAL_MODEL_CODE_EXECUTION_ACTION_PROTOCOL_OR_CONTEXT_V1
```

Narrow fix target:

```text
Make the real model loop reserve room for an explicit finish action, or teach the context/prompt to finish once code execution, patch, and verification receipts exist.
```

Do not rerun provider until that fix is reviewed.
