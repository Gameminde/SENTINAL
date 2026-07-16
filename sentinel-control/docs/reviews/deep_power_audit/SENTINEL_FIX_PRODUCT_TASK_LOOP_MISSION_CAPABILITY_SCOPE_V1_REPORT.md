# SENTINEL_FIX_PRODUCT_TASK_LOOP_MISSION_CAPABILITY_SCOPE_V1_REPORT

Date: 2026-07-16

## Verdict

```text
FIX_PRODUCT_TASK_LOOP_MISSION_CAPABILITY_SCOPE_V1
= VALID_SUCCESS_LOCAL_REGRESSION

implementation_commit = 29bb1803bdd939d232e3af8f4858dec173599c4f
```

This is a product-loop authority/scope fix. It is not a new live browser or real-model product proof.

## Trigger

The clean Python.org V4 live attempt after the browser runtime failure fix exposed a new blocker:

```text
MODEL_SKILL_SURFACE_DRIFT_TO_NON_BROWSER_ACTIONS
```

In a browser-only public-web mission, the real model selected a code execution skill. The product loop then allowed the action to reach execution authority per action instead of enforcing the mission capability envelope first.

That violated the core doctrine:

```text
semantic strategy freedom != authority expansion
model may choose strategy inside scope
model cannot grant itself new mission capabilities
```

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py
```

## Behavior Before

```text
browser-only mission context
-> model-selected code_execution_sandbox action
-> product loop accepted the selected capability
-> ProductActionKernel attempted execution
-> mission drifted away from the browser body path
```

## Behavior After

```text
RuntimeHost/Product task loop receives allowed_capabilities
-> available runtime actions are filtered before skill-surface compilation
-> simple model-facing browser skills remain visible
-> off-scope model-selected capability is rejected before execution
-> MODEL_SELECTED_SKILL_OUTSIDE_MISSION_SCOPE recovery observation is sent to next model turn
-> no new authority is granted
```

For browser-only missions, this preserves the model-facing mission language:

```text
browse_search remains visible
run_check is hidden
ActionEnvelope remains internal
sentinel_loop remains available for finish/completion lanes
```

## Hard Boundaries Preserved

```text
model cannot self-grant authority
trusted runtime keys cannot be overridden
backend identity cannot be silently substituted
raw provider output/reasoning must not persist
raw DOM/cookies/session/profile material must not persist
replay must not re-execute real side effects
```

This fix does not convert ordinary topics or words into prohibitions. It only prevents execution of a capability outside the mission grant.

## Regression Proof

Added:

```text
test_off_scope_skill_selection_recovers_without_granting_authority
```

The test proves:

```text
allowed_capabilities = real_browser_control + sentinel_loop
-> initial model context exposes browse_search
-> initial model context does not expose run_check
-> model attempts code_execution_sandbox
-> product loop creates MODEL_SELECTED_SKILL_OUTSIDE_MISSION_SCOPE
-> no code execution dispatch happens
-> next model turn can select real_browser_control.real_browser.search
-> browser runtime body failure remains recoverable through the existing packet path
```

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py::test_off_scope_skill_selection_recovers_without_granting_authority -q
result: 1 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
result: 6 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result: 29 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_search_actuation_open_world_feedback.py -q
result: 4 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
result: 106 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result: 9 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
result: 2 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
result: passed

git diff --check
result: passed with CRLF normalization warnings only
```

Targeted scan over touched runtime/test files found no secret values, raw provider output, raw provider reasoning, raw DOM, cookies, session material, or raw Cloak binary path persistence.

## Truth Boundary

This fix proves local mission capability scope enforcement in the product task loop.

It does not prove:

```text
new real-model Python.org mission success
new Cloak browser actuation
repeat golden-slice reliability
multi-site generalization
```

The next proof should rerun the same bounded Python.org non-holdout mission with:

```text
allowed_capabilities = real_browser_control + sentinel_loop
real provider/model
real Cloak backend
no fixture
no Playwright fallback
no holdout
```

The expected result is not a forced trajectory. The expected invariant is that the model remains free inside the browser mission while the runtime refuses off-scope capability expansion before execution.
