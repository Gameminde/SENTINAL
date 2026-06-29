# SENTINEL FIX POWER LOOP POST PATCH VERIFICATION ORDERING V1

## Canonical Input

Attempt 2D was accepted as a valid failed real-provider power-loop run.

What 2D proved:

- The real model chose `read_only_research.list_directory`.
- The real model chose `code_execution_sandbox.code_exec.run_profile`.
- The real model chose `workspace_patch.apply_patch`.
- The real model emitted `sentinel_loop.finish`.
- The patch applied.
- Three receipts were persisted.
- Replay material deltas stayed zero.
- The empty `ActionEnvelope` blocker did not recur.

Why 2D remained failed:

- No bounded check ran.
- No post-patch read-only verification ran.
- Finish happened too early.

## Root Cause

The model-led loop treated any read-only receipt as verification, even when the read-only receipt was produced before `workspace_patch.apply_patch`.

For workspace mutation missions, that ordering is too loose:

```text
read-only receipt before patch = observation
read-only receipt after patch = verification
bounded check after patch = verification
```

## Fix

`DecisionContextCompiler` now computes post-patch verification from the ordered action-result sequence.

Objective satisfaction for patch missions now requires:

- a successful code execution receipt,
- a successful workspace patch receipt,
- at least one verification receipt after the latest successful patch.

Post-patch verification may come from:

- `workspace_patch.run_bounded_check`
- `code_execution_sandbox.code_exec.run_profile`
- `read_only_research.search_text`
- `read_only_research.read_file_segment`

`ModelLedTaskLoop` now blocks premature `sentinel_loop.finish` when a patch receipt exists but post-patch verification is still missing:

```text
MODEL_FINISH_BEFORE_POST_PATCH_VERIFICATION
```

This is a power-correctness guard, not a new security layer. It prevents false completion while still leaving the model in charge of choosing the verification action.

## Context Guidance

Before post-patch verification, the loop now keeps:

```text
objective_satisfied = false
finish_available = false
recommended_next_action = null
```

and recommends:

```text
workspace_patch.run_bounded_check
read_only_research.search_text
read_only_research.read_file_segment
```

After post-patch verification, finish becomes available and recommended.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_pre_patch_read_only_receipt_does_not_satisfy_patch_verification tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_post_patch_read_only_search_text_satisfies_verification tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_post_patch_read_file_segment_satisfies_verification tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_post_patch_bounded_check_satisfies_verification -q
4 passed

py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
19 passed

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

py -3.13 -m compileall sentinel/operator/model_led_task_loop.py sentinel/operator/decision_context.py sentinel/operator/action_kernel.py sentinel/operator/code_execution_sandbox_runtime.py sentinel/operator/workspace_patch_runtime.py sentinel/operator/read_only_operator_spine.py
passed

git diff --check
passed
```

Targeted scan found only existing redaction fixtures in `test_power_pack3_code_execution_sandbox.py` for `Authorization: Bearer token` and `secret=hidden`; these are test inputs that verify secret material is not persisted.

## Power-First Confirmation

- New power added: no.
- Model autonomy removed: no.
- Finish action removed: no.
- Gate bypassed: no.
- Fallback/AUTO added: no.
- Provider-native tools added: no.
- Provider behavior changed: no.
- Raw provider/reasoning persistence added: no.

This fix keeps the power loop moving, but makes completion truthful: observe, run bounded code execution, patch, verify after patch, then finish.

## Commit

Commit hash: recorded after local commit creation.
