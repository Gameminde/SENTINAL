# SENTINEL_POWER_PACK6C_ACTIONABILITY_RECOVERY_AND_POWER_STATE_MACHINE_V1_REPORT

## Verdict

`POWER_PACK_6C_ACTIONABILITY_RECOVERY_AND_POWER_STATE_MACHINE_V1 = LOCALLY_IMPLEMENTED_CANDIDATE`

Pack 6C implements the accepted `SENTINEL_CORE_POWER_CONTRACT_LOCK_V1` direction: the model remains the pilot, Sentinel executes inside granted authority, and in-scope actionability failures become recovery/correction context instead of immediate mission death.

No provider call was made during implementation or validation.

## Accepted Core Lock

Canonical doctrine applied:

- Power first, receipts always.
- Do not control intelligence.
- Control only real-world damage.
- Any action shown to the model should be executable or mapped to executable refs/actions.
- In-scope runtime misses become recovery.
- Model protocol misses become correction.
- Real boundary violations remain hard stops.
- FinalGate certifies truth; it does not replace recovery.

## Kernel-Wide Changes

Added `sentinel/operator/action_power_contract.py` with data/control-plane contract objects:

- `ActionFailureClass`
- `RecoverableActionObservation`
- `ActionAliasNormalizer`
- `ActionabilityRef`
- `ActionabilityFrame`
- `BrowserActionabilityRegistry`

These models are not authority and do not execute actions. They describe what is executable, what aliases are accepted, what refs are fresh, and how the next model turn can recover.

## ActionKernel Contract Change

`ActionKernel` now normalizes known action aliases before executor lookup:

- `finish` -> `sentinel_loop.finish`
- `read_only.*` -> `read_only_research.*`
- `real_browser.*` -> `real_browser_control.real_browser.*`
- `browser.*` -> `browser_control.browser.*`
- `channel_transport.send_message` -> `bounded_channel.send_message`

`ActionResult` now carries typed recovery fields:

- `failure_class`
- `failure_code`
- `recoverable`
- `recovery_observation`
- `recommended_next_actions`

Hard boundary errors still raise and remain terminal.

## ModelLedTaskLoop Recovery/Correction Lanes

The generic model-led loop now separates:

- material action lane
- recovery lane
- correction lane
- proof/finish lane

Recoverable runtime failures are appended as safe observations and fed into the next model decision context. Malformed or empty action envelopes become correction observations. The loop terminalizes only when the relevant recovery/correction budget is exhausted.

New terminal reasons:

- `RECOVERY_BUDGET_EXHAUSTED`
- `MODEL_CORRECTION_BUDGET_EXHAUSTED`

Existing hard stops still terminalize immediately.

## ActionabilityFrame

`ActionabilityFrame` exposes a compact executable decision frame:

- source runtime
- state hash / epoch
- canonical action id
- capability / operation
- param schema
- executable refs
- accepted action aliases
- blocked refs
- recovery actions
- proof actions
- finish actions

For browser runs, this frame is carried in the safe model context after page perception.

## BrowserActionabilityRegistry

The real browser runtime now builds a safe registry from the browser world model and decision frame:

- canonical refs
- accepted aliases
- candidate actions
- blocked refs
- recovery actions
- navigation expiry semantics

Example improvement:

- A model can use `search_box`.
- Sentinel resolves it to the current canonical browser ref if available.
- If the ref is missing/stale, Sentinel returns a recoverable observation with refreshed candidates.

The registry/frame are context cards, not authority grants and not external execution.

## Browser Runtime Behavior

New behavior:

- Unknown or stale browser refs return `recoverable_failed` with `RECOVERABLE_BROWSER_STATE_FAILURE`.
- The next model turn receives refreshed executable refs, aliases, and recovery actions.
- Known aliases resolve to canonical refs before action execution.

Preserved hard stops:

- unbounded URL
- hidden/disabled/secret refs
- credential-like typed text
- sensitive provider/raw/reasoning material
- unsupported browser operations

## Budget Changes

`LoopGuardConfig` now includes:

- `max_recovery_turns`
- `max_correction_turns`
- `max_proof_turns`
- `max_finish_turns`

Defaults preserve existing loop behavior while allowing bounded recovery/correction.

## Hard-Stop Preservation Proof

Focused tests prove:

- Unknown browser ref is recoverable.
- Repeated unknown refs exhaust recovery budget and block without fake receipts.
- Unbounded browser URL remains terminal.
- Hidden/disabled/secret refs remain blocked.
- Sensitive typed text remains blocked.
- Empty action envelope does not dispatch an action and retains safe diagnostics.

## Tests Run

Passed:

```text
py -3.13 -m pytest tests/operator/test_power_pack6c_actionability_recovery_contract.py -q
5 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
14 passed

py -3.13 -m pytest tests/operator/test_power_pack6c_actionability_recovery_contract.py tests/operator/test_power_pack6_real_browser_bounded_web_control.py tests/operator/test_power_pack5_real_channel_transport_send.py tests/operator/test_power_pack4_browser_computer_control.py tests/operator/test_power_pack3_code_execution_sandbox.py tests/operator/test_power_pack2_workspace_write_patch.py tests/operator/test_power_pack1_model_led_task_loop.py -q
68 passed

py -3.13 -m pytest tests/test_real_model_read_only_operator_production_spine_v1.py -q
48 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -q
28 passed

py -3.13 -m compileall sentinel/operator/action_power_contract.py sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/model_led_task_loop.py sentinel/operator/loop_guard.py sentinel/operator/real_browser_control_runtime.py
passed

git diff --check
passed
```

Targeted scan result:

- No credential values found.
- No raw provider output/prompt/reasoning persistence introduced.
- No fallback/AUTO enablement introduced.
- No provider-native tools introduced.
- Matches were limited to existing blocklist constants and negative test assertions.

## Power Gained

Before Pack 6C:

```text
model proposes action
runtime misses ref / alias / schema detail
ActionKernelError
mission blocked
```

After Pack 6C:

```text
model proposes in-scope action
Sentinel normalizes aliases and checks actionability
if ref/action is stale or thin, Sentinel returns recoverable context
model gets refreshed executable refs/actions
runtime retries within bounded recovery
hard stops only for real damage or authority boundary escape
```

This is a product-power improvement, not a security pack.

## Git Status

Report created before local commit. Final commit hash is recorded in the operator response after commit.

Known unrelated dirty file excluded from this pack:

```text
sentinel-control/docs/reviews/SENTINEL_REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1_REPORT.md
```

## Confirmation

- Provider call: no.
- Push: no.
- Provider-native tools: no.
- Fallback/AUTO: no.
- Raw provider/reasoning/credential persistence: no.
- New external power: no.
- New power semantics: yes, model-led recovery/actionability inside granted authority.
