# SENTINEL_FIX_BROWSER_RUNTIME_EXCEPTION_TO_STAGE_SPECIFIC_RECOVERABLE_BODY_FACT_V1_REPORT

Date: 2026-07-16

## Verdict

```text
FIX_BROWSER_RUNTIME_EXCEPTION_TO_STAGE_SPECIFIC_RECOVERABLE_BODY_FACT_V1
= VALID_SUCCESS_LOCAL_REGRESSION
```

This is a local runtime-loop fix, not a new live browser or real-model proof.

## Trigger

The Python.org golden vertical slice exposed a case where a browser action had already started, but a `RealBrowserControlRuntimeError` escaped the product browser dispatch path as a generic action-start failure. That prevented the next model turn from receiving a precise safe body-state packet.

The system needed to preserve two truths:

```text
runtime_failure_fact = authoritative mechanical truth
model_visible_body_failure_packet = safe advisory recovery context for the model
```

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py
```

## Behavior Before

```text
RealBrowserControlRuntimeError during runtime.execute
-> escaped into generic action-start exception handling
-> blocked reason was not treated as recoverable browser body failure
-> model loop stopped after one provider/model turn
-> no next-turn model-visible body failure packet
```

## Behavior After

```text
RealBrowserControlRuntimeError during runtime.execute
-> stage-specific runtime failure result
-> failure_code = real_browser_runtime_dispatch_exception
-> failure_stage such as browser_runtime_observe / browser_search_write / browser_search_submit
-> runtime_failure_fact persisted in dispatch safe_context_cards
-> model_visible_body_failure_packet exposed to next model context
-> loop can perform one bounded recovery turn
```

Hard boundaries remain non-recoverable when the runtime error corresponds to authority, secret, origin, backend mismatch, or compatibility preflight failures.

## Regression Proof

Added:

```text
test_browser_runtime_exception_reaches_next_model_turn_as_recoverable_fact
```

The test proves:

```text
RuntimeHost product path receives a real_browser.search action
-> fake Cloak-compatible engine raises RealBrowserControlRuntimeError during observe
-> dispatch result failure_code = real_browser_runtime_dispatch_exception
-> runtime_failure_fact.failure_stage = browser_runtime_observe
-> model_visible_body_failure_packet.failure_stage = browser_runtime_observe
-> root lease continuity remains present
-> model decision client receives a second context with recoverable_action_observations
```

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py::test_browser_runtime_exception_reaches_next_model_turn_as_recoverable_fact -q
result: 1 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
result: 5 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result: 29 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_search_actuation_open_world_feedback.py -q
result: 4 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
result: 106 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py -q
result: 15 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
result: passed

git diff --check
result: passed with CRLF normalization warnings only
```

Targeted scan over touched runtime/test/report files found no secret values, raw provider output, raw provider reasoning, raw DOM, cookies, session material, or raw Cloak binary path persistence.

## Truth Boundary

This fix proves local recovery transport for stage-specific browser runtime exceptions.

It does not prove:

```text
new live Cloak actuation
new real-model mission success
repeat golden-slice reliability
multi-site generalization
```

Next proof remains a bounded live/real-model tranche, not a claim from deterministic tests alone.
