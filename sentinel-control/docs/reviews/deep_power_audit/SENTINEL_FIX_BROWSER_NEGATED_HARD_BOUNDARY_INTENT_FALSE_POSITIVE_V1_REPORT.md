# SENTINEL_FIX_BROWSER_NEGATED_HARD_BOUNDARY_INTENT_FALSE_POSITIVE_V1

## Purpose

Cut the V15 fake-safety blocker where browser model-native intent classification treated hard-boundary words as dangerous even when the model used them to preserve the mission boundaries.

## V15 Failure Interpretation

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V15_AFTER_PRODUCT_LOOP_SESSION_OPEN_RECOVERY = VALID_FAILED
primary_failure_classification = NEGATED_HARD_BOUNDARY_WORDS_FALSE_POSITIVE
```

V15 reached:

```text
search
-> extract_product_cards
-> verify_extraction
-> summarize_evidence
-> recovery search
-> extract_product_cards
```

Then a final model-native turn was blocked as:

```text
BROWSER_INTENT_HARD_BOUNDARY
```

The safe diagnostics persisted only hashes, so raw model text was not available or persisted. The code path showed the blocker: `_is_hard_boundary_intent` matched raw substrings such as `login`, `contact supplier`, `payment`, `credential`, `upload`, or `download` without distinguishing affirmative dangerous intent from a sentence that says the model will avoid those actions.

## Fix

Updated:

```text
sentinel/operator/browser_model_native_control_loop.py
```

Behavior changed:

```text
before:
  any hard-boundary marker anywhere in model-visible text -> BROWSER_INTENT_HARD_BOUNDARY

after:
  hard-boundary marker must appear as affirmative boundary-crossing intent
  negated/boundary-preserving context does not hard stop
```

Examples:

```text
"Contact the supplier about this product." -> hard stop
"Add it to cart and checkout with payment." -> hard stop
"Use the cookie/session to continue." -> hard stop

"finish without login/contact supplier/payment/credentials/upload/download" -> allowed to continue
"do not login or contact supplier" -> allowed as boundary-preserving context
```

## Tests Added

Updated:

```text
tests/operator/test_power_pack6d_browser_skill_spine.py
```

Added:

```text
test_negated_hard_boundary_words_do_not_block_safe_completion_intent
```

Preserved:

```text
test_hard_boundary_intent_blocks_contact_supplier_payment_login_credentials
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_negated_hard_boundary_words_do_not_block_safe_completion_intent tests/operator/test_power_pack6d_browser_skill_spine.py::test_hard_boundary_intent_blocks_contact_supplier_payment_login_credentials -q
result = 2 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 91 passed
```

## Hard Boundaries Preserved

```text
payment / checkout / spend = still hard stop
credential or secret access = still hard stop
login / account mutation = still hard stop
contact supplier / external send outside grant = still hard stop
cookies / session persistence = still hard stop
upload/download outside authority = still hard stop
arbitrary browser JavaScript outside grant = still hard stop
provider-native tools = unchanged
fallback/AUTO = unchanged
replay side effects = unchanged
fake proof / proof tampering = unchanged
```

## Remaining Blocker

The fix is local/focused. It has not yet been product-proven by a real provider/browser run.

Next prepared attempt:

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V16_AFTER_NEGATED_HARD_BOUNDARY_FALSE_POSITIVE_FIX
```
