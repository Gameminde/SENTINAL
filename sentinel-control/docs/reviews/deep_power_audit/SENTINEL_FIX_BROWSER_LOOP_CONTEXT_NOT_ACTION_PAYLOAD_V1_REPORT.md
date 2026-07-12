# SENTINEL_FIX_BROWSER_LOOP_CONTEXT_NOT_ACTION_PAYLOAD_V1_REPORT

## Verdict

```text
FIX_BROWSER_LOOP_CONTEXT_NOT_ACTION_PAYLOAD_V1 = LOCALLY_COMMITTED
implementation_commit = 7fe20bf fix: keep loop context out of action payload
```

## Problem

V9 proved the product route could execute real Cloak-backed browser search, but the second mission blocked on:

```text
adapter_exception:ValidationError
```

Root cause:

```text
loop_context was treated as ActionEnvelope.params.
```

That made safe execution context subject to action-payload safety scanning. Policy words such as login, contact supplier, credentials, payment, and checkout are valid context/hard-boundary text, but they are not valid action input.

## Fix

Changed the product dispatcher to split action parameters from execution context:

```text
MissionExecutionRequest.parameters
-> action_params without loop_context
-> ActionEnvelope.params = action_params only
-> ProductActionKernel executor context.loop_context = safe loop context
```

Updated executors:

```text
real_browser executor reads loop_context from internal executor context first
sentinel_loop executor reads loop_context from internal executor context first
legacy envelope.params loop_context remains compatibility fallback
```

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
```

## Regression Test

Added:

```text
test_browser_loop_context_is_not_scanned_as_action_payload
```

The test reproduces the V9 failure shape:

```text
search action creates rich browser loop context
mission objective contains hard-boundary words
second extract action receives loop context
ActionEnvelope.params remains clean
extract_product_cards completes
```

## Behavior Before

```text
safe loop context -> ActionEnvelope.params
ActionEnvelope scanner sees hard-boundary words
ValidationError
adapter_exception
mission blocked before extract receipt
```

## Behavior After

```text
safe loop context -> executor context
small action params -> ActionEnvelope.params
real_browser.extract_product_cards executes
product-spine receipt/finalgate path preserved
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_browser_loop_context_is_not_scanned_as_action_payload -q
result: passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result: 15 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result: 9 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
result: 2 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result: 88 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q
result: 54 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result: 14 passed

py -3.13 -m compileall -q sentinel
result: passed

git diff --check
result: passed, line-ending warnings only

targeted scan for secrets/raw-provider/provider-native/fallback/AUTO/raw DOM/cookies/session/profile material
result: no hits in changed files
```

## Hard Boundaries Preserved

No hard boundary was weakened:

```text
payment / checkout / spend = still blocked
credentials / secrets = still blocked as action input
login / account mutation = still blocked
contact supplier / external send outside grant = still blocked
cookies/session/raw DOM/raw screenshot persistence = still blocked
provider-native tools = still blocked
fallback/AUTO = still blocked
replay side effects = still blocked
fake proof / proof tampering = still blocked
```

This fix only stops scanning internal safe context as if it were command payload.

## Remaining Blockers

V9 still did not prove:

```text
verify_extraction
grounded summary
finish
relevant under-5-EUR eyewear extraction quality
```

## Next Prepared Real Attempt

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V10_AFTER_LOOP_CONTEXT_ACTION_PAYLOAD_FIX
```

V10 should prove whether the pipeline can now move:

```text
search receipt
-> extract_product_cards receipt
-> verify_extraction
-> summarize_evidence
-> finish
```

