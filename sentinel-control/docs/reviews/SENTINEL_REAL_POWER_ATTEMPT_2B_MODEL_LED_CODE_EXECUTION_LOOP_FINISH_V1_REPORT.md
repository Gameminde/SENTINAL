# SENTINEL REAL POWER ATTEMPT 2B MODEL LED CODE EXECUTION LOOP FINISH V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_2B_MODEL_LED_CODE_EXECUTION_LOOP_FINISH_V1 = VALID_FAILED
```

This was one real-provider run after:

```text
FIX_REAL_MODEL_CODE_EXECUTION_ACTION_PROTOCOL_OR_CONTEXT_V1 = LOCALLY_COMMITTED
commit = e1ba980702c0630263ab5c70f391bf02530e5563
```

No source code was changed after the provider run.

## Real Provider Used

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_hash = aec3b934d7d71744f60faa21da5f9e55e1efd715baa09306e784514497b9f271
credential_present = true
```

No endpoint value, API key, Authorization header, raw provider output, raw
prompt, raw reasoning, or provider wrapper payload is persisted in this report.

## Run

```text
source_commit = e1ba980702c0630263ab5c70f391bf02530e5563
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt2b-20260629-090658
exit_code = 0
provider_decision_calls = 5
model_extraction_failures = 0
provider_failure = none
```

## Mission Objective

```text
Run a model-led workspace loop that inspects the fixture, uses bounded code execution, patches README.md to say the Sentinel model-led code execution sandbox worked, verifies with bounded checks/read-only search, then finishes.
```

Temporary fixture:

```text
README.md initially contained a TODO marker for the model-led code execution patch.
```

## Parsed Action Sequence

The real model produced canonical `ActionEnvelope` decisions:

```text
1. read_only_research.list_directory
2. read_only_research.read_file_segment
3. code_execution_sandbox.code_exec.run_profile
4. read_only_research.read_file_segment
5. workspace_patch.apply_patch
```

The model did not emit:

```text
sentinel_loop.finish
workspace_patch.run_bounded_check
```

## Execution Results

```text
material_actions_executed = 5
code_commands_executed = 1
patch_applied = true
bounded_check_run = false
verification_action_attempted = true
finish = false
mission_status = completed
loop_final_reason = model_led_task_loop_material_budget_reached
blocked_reason = null
```

Receipts:

```text
code_exec_receipt_8ce0e491d98b49c3a24b7e1332d68512
workspace_patch_receipt_184c61df803442e2bacd6e74c44ae372
```

Loop certificate:

```text
model_led_loop_finalgate_ae2e447e48b54738b8f0c2bd0abb86f6
```

Mission id:

```text
mission_d6565a68b48b4dc8b3f4530ff4fa84da
```

## Root Cause

The finish-only turn added by the fix was not reached.

Safe context retained during the run shows:

```text
objective_satisfied = false for all 5 model turns
finish_available = false for all 5 model turns
finish_only_due_to_material_budget = null for all 5 model turns
```

The reason is not provider failure or action-envelope extraction failure. The
read-only verification actions were attempted but denied by the read-only Gate:

```text
failure_code = READ_ACCESS_BLOCKED
proof_kind = gate_denial
successful_action_receipt_ref = null
```

Because the read-only verification attempts produced no successful receipt,
the objective-satisfied predicate remained false. The loop therefore closed
honestly by material budget after the patch action, instead of entering the
finish-only turn.

## Workspace Diff

```diff
--- README.before
+++ README.after
@@ -1,3 +1,3 @@
 # Real Power Attempt 2B
 
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

## Safety Scan

Targeted run-artifact scan result:

```text
API key persisted = no
Authorization persisted = no
raw_prompt persisted = no
raw_response persisted = no
raw_reasoning persisted = no
reasoning_content persisted = no
provider wrapper payload persisted = no
fallback/AUTO enablement = no
provider-native tool use = no
```

One safe string match appeared in `record.json`:

```text
provider_native_tools
```

It was part of the explicit forbidden-actions list, not enabled provider-native
tool material.

## Comparison With Attempt 2

Attempt 2:

```text
provider_decision_calls = 5
code execution = yes
patch = yes
bounded check = yes
read-only verification = yes
finish = no
final reason = model_led_task_loop_material_budget_reached
```

Attempt 2B:

```text
provider_decision_calls = 5
code execution = yes
patch = yes
bounded check = no
read-only verification attempted but Gate-denied
finish = no
final reason = model_led_task_loop_material_budget_reached
```

The new finish-only context was present in the runtime, but it correctly did
not activate because objective receipts were not satisfied.

## Recommendation

```text
recommended_decision = FIX_POWER_LOOP_READ_ONLY_VERIFICATION_GATE_AUTHORITY_V1
```

This should be a narrow runtime/harness fix, not a provider or model-protocol
micro-fix:

```text
ensure model-led workspace-loop read-only verification actions carry the same approved workspace read authority used by the successful product read-only route
preserve Gate checks
preserve receipts
do not weaken path boundaries
do not add fallback/AUTO
do not add provider-native tools
```

## Confirmation

```text
one real-provider mission run = yes
retry after provider call = no
fallback/AUTO = no
provider-native tools = no
raw provider/reasoning persistence = no
credential persistence = no
source changes after provider run = no
push = not performed
Power Pack 4 = not started
```
