# Fix Browser Model Native First Turn Extract Routing V1

implementation_status = LOCAL_IMPLEMENTED_CANDIDATE

## V7 Failure Interpretation

V7 proved model-native browser intent was consumed, but also exposed a dead
first-turn route:

```text
provider reply / metadata intent
-> mapped to real_browser.extract_product_cards
-> no browser search/open/observe/world-model context existed yet
-> extraction blocked with browser_session_missing_or_closed
```

This was not a provider, schema, credential, or Cloak readiness failure. It was
a product-loop routing problem: extraction is a living skill only after a
browser world model exists, unless an explicit fake/local engine profile is
provided for a local test.

## Fix

`ModelLedProductActionKernelTaskLoop` now routes first-turn
`real_browser.extract_product_cards` or `real_browser.verify_extraction`
decisions without browser context into `real_browser.search` using a deterministic
query derived from the mission objective.

Explicit local/test extraction remains direct when `engine_profile` is set.

## Regression Test

Added:

```text
test_first_turn_extract_without_browser_context_routes_to_search_before_extract
```

The test starts with a model decision for `extract_product_cards` before any
browser context exists. The loop now performs:

```text
real_browser.search
-> real_browser.extract_product_cards
-> real_browser.verify_extraction
-> sentinel_loop.summarize_evidence
-> sentinel_loop.finish
```

## Tests Run

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_first_turn_extract_without_browser_context_routes_to_search_before_extract -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
git diff --check
targeted scan for secrets/raw-provider/provider-native/fallback/AUTO/raw DOM/cookies/session material
```

All listed validations passed. The targeted scan returned no hits.

## Hard Boundaries Preserved

```text
payment / checkout / spend = still blocked
credential / secret access = still blocked
login / account mutation = still blocked
contact supplier / external send outside grant = still blocked
raw provider / reasoning persistence = not introduced
raw DOM / screenshot / cookie / session persistence = not introduced
provider-native tools = not introduced
fallback/AUTO = not introduced
replay side effects = not introduced
```

## Remaining Product Truth

This fix does not claim real Alibaba/browser success. It proves locally that the
V7 blocker is cut. The next real attempt must show whether the live path reaches
search, extraction, verification, grounded summary, and finish, and must still
reject irrelevant product cards as product success.

## Next Prepared Attempt

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V8_AFTER_FIRST_TURN_EXTRACT_ROUTING_FIX
```
