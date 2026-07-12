# SENTINEL FIX BROWSER PRODUCT LOOP RECOVERABLE SEARCH TO EXTRACTION V1

## Verdict

```text
FIX_BROWSER_PRODUCT_LOOP_RECOVERABLE_SEARCH_TO_EXTRACTION_V1 = LOCALLY_COMMITTED
commit = 6c1fa74 fix: recover browser search cards through product loop
```

## V4 Failure Interpretation

V4 proved that the real model reached the right product browser skill and that the selected Cloak/session path was active, but search actuation produced a recoverable browser state failure while visible product/result cards were already present. The product loop still blocked instead of continuing into extraction.

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/browser_decision_frame.py
sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
```

## Behavior Before / After

Before:

```text
search recoverable failure + product cards visible
-> ProductActionKernel receipt recoverable_failed
-> task loop blocked
-> FinalGate certifies avoidable blocked truth
```

After:

```text
search recoverable failure + product cards visible
-> recoverable_action_observation
-> browser decision frame prioritizes extract_product_cards
-> extract_product_cards
-> verify_extraction
-> summarize_evidence
-> finish
```

## Implementation Details

1. Browser decision frames now put `extract_product_cards` and `verify_extraction` ahead of search/open when product/result cards already exist.
2. ProductActionKernel task loop now treats known in-scope browser state/ref/search failures as recoverable action failures.
3. Browser recoverable action failures get at least one recovery turn even when the caller did not explicitly set a recovery budget.
4. Recoverable browser failures with visible cards recommend the `extract` model skill.
5. `real_browser.verify_extraction` now records a material proof receipt because it re-extracts and verifies visible product cards without producing an external side effect.

## Regression Proof

Added:

```text
test_product_loop_continues_to_extract_after_recoverable_browser_search_with_cards
```

The test first failed with the product loop blocked after recoverable browser search failure. After the fix it passes and proves:

```text
real_browser.search recoverable_failed
-> real_browser.extract_product_cards
-> real_browser.verify_extraction
-> sentinel_loop.summarize_evidence
-> sentinel_loop.finish
-> completed
```

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_product_loop_continues_to_extract_after_recoverable_browser_search_with_cards -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/browser_decision_frame.py sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
git diff --check
targeted raw secret/provider/browser material scan
```

All listed validation passed. Targeted scan hits were benign hard-boundary/redaction strings only.

## Hard Boundaries Preserved

```text
payment / checkout / spend = still hard stop
credentials / secrets = still hard stop
login / account mutation = still hard stop
contact supplier / external send outside grant = still hard stop
cookies/session/profile/raw DOM/screenshot persistence = still blocked
provider-native tools = disabled
fallback/AUTO = disabled
replay real side effects = blocked
fake proof / proof tampering = blocked
```

## Remaining Product Truth

This is local proof only. It prepares the next real run:

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V5_AFTER_RECOVERABLE_SEARCH_TO_EXTRACTION_FIX
```

V5 must prove the same sequence with the real provider and bounded Alibaba browser target.

