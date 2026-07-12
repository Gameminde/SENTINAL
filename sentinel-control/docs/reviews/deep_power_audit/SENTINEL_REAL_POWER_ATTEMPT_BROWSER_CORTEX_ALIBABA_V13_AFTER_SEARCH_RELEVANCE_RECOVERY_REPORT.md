# SENTINEL_REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V13_AFTER_SEARCH_RELEVANCE_RECOVERY

## Verdict

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V13_AFTER_SEARCH_RELEVANCE_RECOVERY = VALID_FAILED
```

## Purpose

Prove whether the irrelevant-evidence completion fix could move the real Alibaba path beyond the V12 summary loop.

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
under_5_eur_supported_count = 0
unknown_price_or_currency_count = 0
extract_product_cards_count = 1
verify_extraction_count = 1
summarize_evidence_count = 1
summary_present = true
finish_present = false
mission_status = blocked
loop_final_reason = model_led_product_action_kernel_task_loop_blocked
loop_blocked_reason = cloakbrowser_open_failed:Error
browser_receipt_count = 15
product_receipt_count = 4
replay_no_react = true
safety_scan_high_risk_hit_count = 14
```

The safety scan count is treated as a scanner precision issue for this runner because it matched safe category words and null/false fields, while the report/summary contract records:

```text
raw provider/reasoning/DOM/screenshot/cookies/session persistence = false
raw binary path persistence = false
```

## Action Sequence

```text
real_browser_control:real_browser.search
-> real_browser_control:real_browser.extract_product_cards
-> real_browser_control:real_browser.verify_extraction
-> sentinel_loop:summarize_evidence
-> real_browser_control:real_browser.search
```

## What V13 Proved

The V12 blocker was cut:

```text
verified extraction + summary + no relevant product evidence
no longer loops on summarize_evidence
it routes back to real_browser.search
```

This is a real product-routing improvement:

```text
old V12 end = summarize_evidence repeated until material budget exhausted
new V13 end = relevance recovery search attempted
```

## Failure

The new blocker is:

```text
CLOAK_SEARCH_RECOVERY_REOPEN_FAILURE
```

The second relevance-recovery search blocked before a new browser receipt:

```text
operation = real_browser.search
blocked_reason = cloakbrowser_open_failed:Error
receipt_refs = []
finalgate_status = rejected
```

## Replay

```text
model_calls_delta = 0
product_dispatch_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
reexecuted_actions = false
replay_no_react = true
```

## Classification

```text
primary_failure_classification = CLOAK_SEARCH_RECOVERY_REOPEN_FAILURE
secondary = RELEVANT_CARDS_NOT_FOUND, FINISH_NOT_TRIGGERED_AFTER_SUMMARY
```

## Required Next Fix

```text
FIX_CLOAK_SEARCH_REOPEN_FAILURE_RECOVERY_V1
```

Expected behavior:

```text
search recovery tries to reopen a missing/closed Cloak session
if reopen fails in-scope
-> recoverable browser observation
-> no terminal dispatch death
-> next model turn gets recovery context
```

No provider retry was performed.
