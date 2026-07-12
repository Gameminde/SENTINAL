# SENTINEL_REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V14_AFTER_CLOAK_SEARCH_REOPEN_RECOVERY

## Verdict

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V14_AFTER_CLOAK_SEARCH_REOPEN_RECOVERY = VALID_FAILED
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
provider_decision_calls = 5
model_native_intent_accepted_count = 5
metadata_reply_native_count = 5
search_attempt_count = 2
search_material_receipt_count = 1
product_or_result_candidate_card_count = 0
relevant_product_card_count = 0
extract_product_cards_count = 1
verify_extraction_count = 1
summarize_evidence_count = 1
summary_present = true
finish_present = false
mission_status = blocked
loop_blocked_reason = real_browser_search_session_open_failed
browser_receipt_count = 16
product_receipt_count = 5
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
```

## What V14 Proved

The V13 raw Cloak reopen exception was converted into a recoverable product receipt:

```text
old V13 blocker = cloakbrowser_open_failed:Error
new V14 blocker = real_browser_search_session_open_failed
product_receipt_count increased to include recoverable failed search
safety scan high-risk hit count = 0
```

## Failure

The product task loop still treated the new recoverable browser failure code as terminal because its recoverable browser action whitelist did not include:

```text
real_browser_search_session_open_failed
```

## Classification

```text
primary_failure_classification = PRODUCT_LOOP_RECOVERABLE_BROWSER_FAILURE_WHITELIST_GAP
secondary = RELEVANT_CARDS_NOT_FOUND, FINISH_NOT_TRIGGERED_AFTER_SUMMARY
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
FIX_PRODUCT_LOOP_BROWSER_RECOVERABLE_SESSION_OPEN_FAILURE_V1
```

Expected behavior:

```text
real_browser_search_session_open_failed
-> recoverable_action_observation
-> next model turn
-> no immediate task-loop block while recovery budget remains
```
