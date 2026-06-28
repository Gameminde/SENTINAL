# SENTINEL POWER PACK 3 SHELL AND CODE EXECUTION SANDBOX V1 REPORT

## Verdict

`POWER_PACK_3_SHELL_AND_CODE_EXECUTION_SANDBOX_V1 = LOCALLY_IMPLEMENTED_CANDIDATE`

This pack adds bounded code execution power to the generic model-led task loop without adding ambient shell access.

## Accepted Starting State

- `REAL_POWER_ATTEMPT_1_MODEL_LED_WORKSPACE_LOOP_V1 = SUCCESS`
- Real model produced canonical `ActionEnvelope` decisions.
- Real product loop proved `workspace_patch.apply_patch`, `workspace_patch.run_bounded_check`, read-only verification, finish, receipts, and replay purity.
- Strategic rule: green pytest builds the rail, real model run proves the power.

## Runtime Changes

Added:

- `sentinel/operator/code_execution_sandbox_models.py`
- `sentinel/operator/code_execution_sandbox_runtime.py`
- `sentinel/operator/code_execution_sandbox_replay.py`
- `tests/operator/test_power_pack3_code_execution_sandbox.py`

Updated:

- `sentinel/operator/decision_context.py`
- `sentinel/operator/model_led_task_loop.py`

## Capability

New capability:

`code_execution_sandbox`

Actions:

- `code_exec.run_profile`
- `code_exec.inspect_result`

Initial command profiles:

- `fake_pass`
- `python_compileall`
- `pytest_file`
- `python_module_smoke`

The model supplies only:

- `profile_id`
- validated args

The runtime owns:

- executable
- fixed args prefix
- cwd
- timeout
- bounded stdout/stderr
- minimal environment
- artifact persistence
- receipt/finalgate generation

## Power Semantics

This is real local code execution power, but it is bounded:

- no raw shell strings
- no `shell=True`
- no arbitrary command
- no network-looking args
- no credential-looking args
- no browser/desktop/payment expansion
- no fallback/AUTO
- no provider-native tools

No per-command approval is required once the mission authority grants the profile-backed capability.

## Workspace Purity

Profiles default to `writes_allowed = false`.

Subprocess-backed profiles run against a temporary copy of the approved workspace, not the approved workspace itself. This prevents tools such as `compileall` and `pytest` from leaving `__pycache__` or `.pytest_cache` artifacts in the real workspace while still giving the model useful execution feedback.

## Receipt / FinalGate Behavior

For `code_exec.run_profile`, the runtime persists:

- `CodeExecutionRequest`
- `CodeExecutionResult`
- `CodeExecutionReceipt`
- `CodeExecutionFinalCertificate`

The receipt records:

- profile id
- args hash
- workspace ref
- exit code
- duration
- stdout hash and bounded redacted excerpt
- stderr hash and bounded redacted excerpt
- result hash
- receipt hash

Timeouts and non-zero exits produce honest blocked/failed status. They do not create fake success.

`code_exec.inspect_result` is non-material and does not rerun commands.

## Replay Proof

Added `CodeExecutionReplayView`.

Replay reports:

- `command_executions_delta = 0`
- `workspace_mutations_delta = 0`
- `receipt_writes_delta = 0`
- `result_writes_delta = 0`
- `finalgate_writes_delta = 0`
- `event_writes_delta = 0`
- artifact hashes stable
- stdout/stderr hashes stable
- workspace hash stable

The generic loop replay also exposes `command_executions_delta = 0`.

## Decision Context

`DecisionContextCompiler` now includes `code_execution_summary` from recent `code_execution_sandbox:code_exec.run_profile` results. This gives the model safe continuity from previous command receipts without raw stdout/stderr dumps.

## Tests Run

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
7 passed

py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py -q
6 passed

py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
7 passed

py -3.13 -m pytest tests/operator/test_connection_live_channel_action_pack5.py -q
9 passed

py -3.13 -m pytest tests/test_real_model_read_only_operator_production_spine_v1.py -q
48 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -q
28 passed
```

Passed:

```text
py -3.13 -m compileall sentinel/operator/code_execution_sandbox_models.py sentinel/operator/code_execution_sandbox_runtime.py sentinel/operator/code_execution_sandbox_replay.py sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/model_led_task_loop.py sentinel/operator/loop_guard.py

git diff --check
```

Targeted scan result:

- no raw provider material persisted
- no credential values persisted
- no fallback/AUTO enablement introduced
- no provider-native tools introduced
- matches were limited to deny-list/runtime guard strings and rejection fixtures

## No-New-Surface Confirmation

No real provider call was made during implementation.

No external network call was made by Sentinel runtime code during tests.

No browser, desktop, payment, email, provider-native tool, fallback/AUTO, or arbitrary host shell power was added.

No RuntimeHost dispatch adapter registration was changed.

## Recommended Next Step

Run one real-provider product attempt:

`REAL_POWER_ATTEMPT_2_MODEL_LED_CODE_EXECUTION_LOOP_V1`

If provider config is missing, stop with `CONFIG_MISSING`.

If it succeeds, recommended next action:

`POWER_PACK_4_BROWSER_COMPUTER_CONTROL_V1`

If it fails due model/action/context protocol, recommended next action:

`FIX_REAL_MODEL_CODE_EXECUTION_ACTION_PROTOCOL_OR_CONTEXT_V1`
