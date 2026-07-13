# SENTINEL_FIX_BROWSER_NEGATIVE_RELEVANCE_COMPLETION_LANE_V1

## Purpose

Fix the V16B loop gap where Sentinel kept searching/extracting after verified extraction and grounded relevance assessment because no relevant product evidence was found.

The old behavior was too rigid:

```text
finish requires relevant product evidence
```

The corrected behavior is:

```text
finish requires verified extraction + grounded relevance assessment
```

Relevant product evidence may be positive, negative, or unknown. Sentinel must not hallucinate a match, but it must be able to finish with an honest negative/uncertain product-research result.

## Files Changed

```text
sentinel/operator/browser_model_native_control_loop.py
sentinel/operator/decision_context.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
tests/operator/test_power_pack6d_browser_skill_spine.py
```

## Behavior Before / After

Before:

```text
verified extraction + grounded summary + no relevant product evidence
-> search/extract kept outranking finish
-> model call budget could exhaust
```

After:

```text
verified extraction + grounded relevance assessment + no relevant product evidence
-> finish is model-visible and preferred
-> summary remains grounded and must preserve unknowns/caveats
```

This does not fake success. It turns "no supported under-5-EUR product found" into a valid terminal mission result.

## Tests Updated

```text
test_visible_irrelevant_cards_finish_with_negative_relevance_not_fake_match
test_relevance_gap_after_search_does_not_repeat_search_as_primary
test_finish_intent_after_irrelevant_summary_finishes_with_grounded_caveat
test_finish_requires_relevance_assessment
```

Preserved invariant:

```text
finish without objective relevance assessment is still blocked/routed to summarize_evidence
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_visible_irrelevant_cards_finish_with_negative_relevance_not_fake_match tests/operator/test_power_pack6d_browser_skill_spine.py::test_relevance_gap_after_search_does_not_repeat_search_as_primary tests/operator/test_power_pack6d_browser_skill_spine.py::test_finish_intent_after_irrelevant_summary_finishes_with_grounded_caveat tests/operator/test_power_pack6d_browser_skill_spine.py::test_finish_requires_relevance_assessment -q
result = 4 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 92 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 18 passed
```

## Hard Boundaries Preserved

```text
payment / checkout / spend = unchanged hard stop
credential or secret access = unchanged hard stop
login / account mutation = unchanged hard stop
contact supplier / external send outside grant = unchanged hard stop
cookies / session persistence = unchanged hard stop
upload/download outside authority = unchanged hard stop
arbitrary browser JavaScript outside grant = unchanged hard stop
provider-native tools = unchanged
fallback/AUTO = unchanged
replay side effects = unchanged
fake proof / proof tampering = unchanged
```

## Remaining Blocker

This local fix has not yet been product-proven by a real provider/browser attempt.

Next prepared attempt:

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V17_AFTER_NEGATIVE_RELEVANCE_COMPLETION_LANE
```
