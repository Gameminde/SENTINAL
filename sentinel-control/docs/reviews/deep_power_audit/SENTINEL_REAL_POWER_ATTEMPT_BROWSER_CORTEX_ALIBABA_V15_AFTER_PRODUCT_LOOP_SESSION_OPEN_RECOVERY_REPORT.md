# SENTINEL_REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V15_AFTER_PRODUCT_LOOP_SESSION_OPEN_RECOVERY

## Verdict

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V15_AFTER_PRODUCT_LOOP_SESSION_OPEN_RECOVERY = VALID_FAILED
```

## Safe Preflight

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
credential_present = true
endpoint_present = true
bounded_browser_origin_hash = f798ab60f961c456
cloak_binary_override_present = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
raw endpoint/token/binary path values persisted = false
```

## Metrics

```text
provider_decision_calls = 7
model_native_intent_accepted_count = 6
metadata_reply_native_count = 6
search_attempt_count = 2
search_material_receipt_count = 1
product_or_result_candidate_card_count = 0
relevant_product_card_count = 0
under_5_eur_supported_count = 0
extract_product_cards_count = 2
verify_extraction_count = 1
summarize_evidence_count = 1
summary_present = true
finish_present = false
mission_status = blocked
loop_blocked_reason = BROWSER_INTENT_HARD_BOUNDARY
browser_receipt_count = 17
product_receipt_count = 6
replay_no_react = true
safety_scan_high_risk_hit_count = 0
```

## Action Sequence

```text
real_browser_control:real_browser.search
-> real_browser_control:real_browser.extract_product_cards
-> real_browser_control:real_browser.verify_extraction
-> sentinel_loop:summarize_evidence
-> real_browser_control:real_browser.search
-> real_browser_control:real_browser.extract_product_cards
```

## What V15 Proved

V15 proved that `real_browser_search_session_open_failed` no longer terminalizes the product loop immediately.

```text
old V14 blocker = real_browser_search_session_open_failed
V15 continued past that recovery condition
second extract_product_cards action was reached
provider_decision_calls increased from 5 to 7
product_receipt_count increased from 5 to 6
replay_no_react = true
safety_scan_high_risk_hit_count = 0
```

## Failure

The final provider turn was classified as:

```text
BROWSER_INTENT_HARD_BOUNDARY
```

The actionable blocker is not a real browser danger. The model-native intent parser treated hard-boundary words as dangerous even when they appear in a boundary-preserving sentence such as finishing or summarizing "without login/contact/payment/credentials/upload/download".

This is fake-safety friction:

```text
real danger = affirmative request to login, pay, contact supplier, use credentials, persist session/cookies, upload/download
fake blocker = model says it will avoid those actions while finishing
```

## Classification

```text
primary_failure_classification = NEGATED_HARD_BOUNDARY_WORDS_FALSE_POSITIVE
secondary = FINISH_NOT_TRIGGERED_AFTER_SUMMARY
```

## Replay

```text
replay_no_react = true
model_calls_delta = 0
product_dispatch_delta = 0
receipt_writes_delta = 0
reexecuted_actions = false
artifact_hashes_stable = true
```

## Required Next Fix

```text
FIX_BROWSER_NEGATED_HARD_BOUNDARY_INTENT_FALSE_POSITIVE_V1
```

Expected behavior:

```text
"contact supplier" / "payment" / "credentials" as affirmative action intent -> hard stop
"without contact supplier/payment/credentials" or "do not login/download" -> safe context, continue mapping
```
