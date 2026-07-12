# SENTINEL_FIX_PRODUCT_BROWSER_NATIVE_MAPPER_TO_PRODUCT_SPINE_V1_REPORT

Recorded at: 2026-07-12

```text
FIX_PRODUCT_BROWSER_NATIVE_MAPPER_TO_PRODUCT_SPINE_V1 = IMPLEMENTED_CANDIDATE
provider_calls = 0
real_browser_runs = 0
push = no
next = REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V1
```

## Purpose

This fix closes a pre-provider product-spine gap found immediately before the
real Browser Cortex Alibaba attempt.

The Browser Cortex lane was ready at the Cloak/session level, but the product
model-native path still had three wiring defects:

```text
1. ProductModelNativeDecisionClient did not consume browser native intent mapping.
2. sentinel_loop.summarize_evidence was known to actionability/power-skill maps
   but not to RuntimeConnectionRegistry / ProductActionKernel dispatch.
3. ModelLedProductActionKernelTaskLoop did not carry browser extraction and
   verification context into the next model turn or completion lane.
```

If left unfixed, the real run could spend provider calls and then fail after
verified extraction because summary/finish was not a living product-spine path.

## Root Cause

The generic task loop already consumed:

```text
model natural intent
-> browser_model_native_control_loop.map_browser_model_native_intent
-> canonical internal ActionEnvelope
```

The product task-loop client did not. It only mapped the older simple skill
surface directly. As a result, natural or semi-structured browser completion
intent could bypass:

```text
real_browser.verify_extraction
sentinel_loop.summarize_evidence
sentinel_loop.finish
```

The second root cause was registry mismatch:

```text
actionability_registry = sentinel_loop.summarize_evidence exists
power_skill_registry = sentinel_loop exists
RuntimeHost route = added for sentinel_loop.summarize_evidence
runtime_connections = missing sentinel_loop profile
```

The coordinator therefore rejected the internal completion lane as not
product-dispatchable.

The third root cause was context starvation. Browser runtimes already produced
safe `context_cards`, but the product loop only exposed minimal dispatch
summaries. The next turn could not reliably see:

```text
browser extraction receipt exists
browser verification receipt exists
grounded summary missing
finish availability
safe product/result cards from BrowserWorldModel
```

## Files Changed

```text
sentinel/operator/product_model_native_decision_client.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/runtime_connections.py
sentinel/operator/runtime_host.py
sentinel/operator/unified_execution_dispatcher.py
tests/operator/test_real_monster_product_model_native_decision_client.py
```

## Runtime Changes

### Product Native Browser Mapper

`ProductModelNativeDecisionClient` now uses
`map_browser_model_native_intent` when the context or payload is genuinely
browser-native.

The router was deliberately constrained so browser mapping does not hijack:

```text
workspace/code missions
channel send missions
worker delegation missions
generic "researcher" worker language
non-browser completion intents
```

Browser native mapping activates only when one of these is true:

```text
explicit real_browser_control action payload
actual browser progress exists
recommended skill/action is browser
mission objective is browser/web/product-page oriented
```

### Sentinel Loop Completion Dispatch

`sentinel_loop.summarize_evidence` is now a local governed product-spine
connection:

```text
capability = sentinel_loop
operation = summarize_evidence
route = ProductActionKernelDispatchAdapter
power = internal completion proof only
external side effects = none
```

`RuntimeHost` routes this action through `ActionKernel`, and the dispatcher
allows its non-material completion receipt as valid proof only for the exact
internal completion-lane action.

This does not make browser/channel/shell/payment power available. It only lets
the product loop summarize already-receipted evidence before finish.

### Loop Context and Completion Lane

`ModelLedProductActionKernelTaskLoop` now compiles safe next-turn context:

```text
dispatch_summaries
bounded_observation_summaries
completion_requirements
real_browser_control_summary
browser_world_model
browser_world_model_summary
browser_decision_frame
grounded_evidence_summary
finish_available
objective_satisfied
```

If browser extraction is verified and summary is missing, the dominant next
action becomes:

```text
sentinel_loop.summarize_evidence
```

If verified extraction and grounded relevant evidence summary exist, the
dominant next action becomes:

```text
sentinel_loop.finish
```

## Before / After

Before:

```text
real_browser extraction/verification could succeed
-> product loop did not expose enough browser proof context
-> model/native completion could route incorrectly
-> summarize_evidence was rejected as not product-dispatchable or proofless
```

After:

```text
browser/native intent
-> internal ActionEnvelope
-> ProductActionKernel route
-> safe browser context carried forward
-> summarize_evidence dispatch accepted
-> finish can become the living next path
```

## Proof

Focused TDD tests added:

```text
test_product_native_client_uses_browser_native_mapper_for_verify_intent
test_product_native_client_routes_verified_browser_extraction_to_summary_lane
test_product_action_kernel_loop_dispatches_summarize_evidence
test_product_task_loop_context_exposes_verified_browser_cards_completion_lane
```

Validation run:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
result = 54 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result = 14 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result = 9 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
result = 12 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 8 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_product_action_kernel_dispatch_adapter.py -q
result = 5 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_connections.py sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py
result = passed

git diff --check
result = passed
```

Targeted scan found only hard-boundary labels and redaction-test strings. It
did not find persisted endpoint values, credential values, raw provider output,
provider reasoning, raw DOM, cookies, screenshots, or browser profile material
in the changed implementation.

## Hard Boundaries Preserved

```text
payment / checkout / spend = hard stop preserved
credential or secret access = hard stop preserved
login / account mutation = hard stop preserved
contact supplier = hard stop preserved
provider-native tools = blocked
fallback/AUTO = blocked
raw provider/reasoning persistence = blocked
raw DOM/cookie/session/profile persistence = blocked
replay side effects = not enabled
```

## Limitations

This is not real Alibaba product proof. It is the final pre-provider wiring
fix required so the next real Browser Cortex attempt can exercise the product
spine honestly.

The next run must still prove:

```text
real provider decision calls
Cloak/session backend remains selected and actual
real bounded browser page opens
model sees/uses simple browser skills
search/extract/verify/summary/finish happen through product spine
replay no-react holds
safe evidence only
```

## Next Prepared Attempt

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V1
```

Rules:

```text
one provider mission
no retry after provider call
no fallback/AUTO
no provider-native tools
no push
no fake success
safe evidence only
```

