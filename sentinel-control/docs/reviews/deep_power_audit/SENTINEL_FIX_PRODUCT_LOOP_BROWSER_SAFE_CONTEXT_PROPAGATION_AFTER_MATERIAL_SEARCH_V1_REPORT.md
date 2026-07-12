# Fix Product Loop Browser Safe Context Propagation After Material Search V1

implementation_status = LOCAL_IMPLEMENTED_CANDIDATE

## V6 Failure Interpretation

V6 proved that Cloak-backed `real_browser.search` can complete through the
ProductActionKernel path and produce a material receipt. It also showed the next
blocker precisely:

```text
completed real_browser.search
-> search closeout safe_context_cards contained browser_world_model
-> next real_browser.extract_product_cards mission received empty safe_context_cards
-> extraction blocked with browser_session_missing_or_closed
```

The V5 runtime fallback for extracting from existing safe world-model cards was
therefore correct, but the product loop was not delivering that safe context to
the next browser material action.

## Fix

`ModelLedProductActionKernelTaskLoop` now attaches a narrow safe browser
context lane to `real_browser.extract_product_cards` and
`real_browser.verify_extraction` when prior browser context contains product or
result cards.

`RuntimeHost` now merges that safe loop context into the real browser executor
context before calling `RealBrowserControlRuntime`.

The fix is deliberately scoped:

```text
real_browser.search/open/click/type movement actions = no loop context injection
real_browser.extract_product_cards = receives safe browser context when cards exist
real_browser.verify_extraction = receives safe browser context when cards exist
sentinel_loop.summarize_evidence = existing completion-lane context path unchanged
```

## Regression Test

Added:

```text
test_completed_browser_search_context_propagates_to_extract_when_live_session_missing
```

The test reproduces the V6 shape: search completes and captures product cards,
then the extraction backend reports `browser_session_missing_or_closed`. Before
the fix, the loop blocked. After the fix, extraction and verification consume
the existing safe world model, summarize evidence, and finish.

## Tests Run

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_completed_browser_search_context_propagates_to_extract_when_live_session_missing -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
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

This fix does not claim Alibaba product success. V6 also showed that the visible
cards were not relevant eyewear results. The next real proof must verify both:

```text
completed search context propagates to extraction
extraction/verification/summary/finish can complete if relevant evidence exists
irrelevant cards are not inflated into product success
```

## Next Prepared Attempt

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V7_AFTER_SAFE_CONTEXT_PROPAGATION_FIX
```
