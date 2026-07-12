# Sentinel Real Power Attempt Browser Cortex Alibaba V5 After Recoverable Search To Extraction Fix

verdict = VALID_FAILED

failure_classification = EXTRACT_AFTER_RECOVERABLE_SEARCH_SESSION_CONTINUITY_GAP

## Safe Run Facts

provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
provider_decision_calls_inferred_min = 2
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
Cloak readiness before provider = passed
raw target URL / endpoint / credential / binary path persisted = false

## Product Truth

V5 proved the previous blocker was cut. The real path reached:

```text
real_browser.search
-> recoverable search actuation failure with safe world model
-> visible product/result cards detected
-> real_browser.extract_product_cards emitted
```

The run then blocked because `real_browser.extract_product_cards` still required
a live browser session. The safe world model already contained product/result
candidate cards, but the extraction runtime did not yet know how to produce a
material extraction receipt from existing context when the live session was
missing or closed.

## Metrics

```text
search_attempt_count = 1
extract_product_cards_count = 1
verify_extraction_count = 0
summary_present = false
finish_present = false
mission_status = blocked
loop_blocked_reason = browser_session_missing_or_closed
product_or_result_candidate_card_count = 6
stable_refs_count = 462
search_like_refs_count = 1
replay_no_react = true
```

## Safety

No retry was performed after provider consumption. No fallback/AUTO or
provider-native tools were used. The report persists safe hashes, ids, counts,
and classifications only.

## Next Fix

```text
FIX_BROWSER_EXTRACT_FROM_CONTEXT_WORLD_MODEL_WITHOUT_LIVE_SESSION_V1
```

The next fix must let extraction/verification consume already-captured safe
world-model cards when no live actuation is needed, while leaving live session
requirements intact for actual browser movement.
