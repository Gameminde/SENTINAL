# SENTINEL FIX REAL MODEL EMPTY ACTION ENVELOPE REJECTION AND CONTEXT GUIDANCE V1

## Canonical Input

Attempt 2C was accepted as a valid failed real-provider power-loop run.

Proven by Attempt 2C:

- The prior `READ_ACCESS_BLOCKED` issue was fixed.
- Real read-only verification reached the production Gate and produced a receipt.
- Workspace mutation stayed limited to the granted fixture.
- Replay material deltas stayed zero.
- No fallback/AUTO, provider-native tools, raw provider output, raw reasoning, or credentials were persisted.

Observed blocker:

- A later real model decision normalized into an empty `ActionEnvelope`.
- The loop attempted dispatch with `capability_id=""` and `operation=""`.
- Runtime blocked with `action_executor_missing:` instead of a typed model-action failure.

## Root Cause

The model-led task loop did not reject blank `capability_id` / `operation` fields before the `ActionKernel` dispatch lookup. That made a model-interface failure look like a missing executor instead of an actionable protocol/context failure.

The decision context also did not provide explicit post-receipt progress guidance after the first read-only observation, so a real model had too little structure for choosing the next useful power action.

## Fix

`ModelLedTaskLoop` now validates every model-produced `ActionEnvelope` before action dispatch:

- Empty or whitespace-only capability/operation is blocked with `MODEL_ACTION_EMPTY_ENVELOPE`.
- No material executor, Gate, patch runtime, code runtime, or read-only runtime is invoked for the empty envelope.
- The blocked result and blocked event include safe structure-only diagnostics:
  - `decision_ref`
  - `turn_index`
  - `allowed_capabilities`
  - `allowed_operations`
  - `last_successful_action`
  - `last_receipt_refs`
  - `failure_code`
  - `capability_present`
  - `operation_present`

`DecisionContextCompiler` now emits progress guidance:

- `progress_state`
- `next_recommended_actions`
- `objective_remaining_steps`
- `completion_requirements`

After an initial read-only receipt, the context guides the model toward bounded code execution, workspace patching, bounded verification, and read-only verification rather than finish or a blank reply.

## Gate And Boundary Preservation

This fix does not bypass Gate, does not broaden read authority, does not add new capabilities, and does not alter provider behavior.

The only new block occurs before dispatch when the model provides no actionable capability or operation. All real action execution still flows through the existing `ActionKernel` and per-capability runtime checks.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_empty_action_envelope_blocks_before_action_kernel_dispatch_with_safe_diagnostics tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_blank_capability_or_operation_blocks_with_typed_reason tests/operator/test_power_pack3_code_execution_sandbox.py::test_power_pack3_context_after_read_only_receipt_guides_next_power_actions -q
3 passed

py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
15 passed

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

py -3.13 -m compileall sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/model_led_task_loop.py sentinel/operator/code_execution_sandbox_runtime.py sentinel/operator/workspace_patch_runtime.py sentinel/operator/read_only_operator_spine.py
passed

git diff --check
passed
```

Targeted secret/raw-provider/fallback/provider-native scan only found existing redaction fixtures in `test_power_pack3_code_execution_sandbox.py` that intentionally verify `Authorization: Bearer token` and `secret=hidden` are not persisted.

## Commit

Commit hash: recorded after local commit creation.

## Confirmation

- Provider call during this fix: no.
- New power added: no.
- Gate bypass: no.
- RuntimeHost dispatch change: no.
- Fallback/AUTO introduced: no.
- Provider-native tools introduced: no.
- Push performed: no.
