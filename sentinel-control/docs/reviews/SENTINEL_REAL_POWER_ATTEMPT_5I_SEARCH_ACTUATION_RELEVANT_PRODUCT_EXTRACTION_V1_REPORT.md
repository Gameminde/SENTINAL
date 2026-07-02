# SENTINEL REAL POWER ATTEMPT 5I SEARCH ACTUATION RELEVANT PRODUCT EXTRACTION V1

## Verdict

```text
REAL_POWER_ATTEMPT_5I_SEARCH_ACTUATION_RELEVANT_PRODUCT_EXTRACTION_V1 = VALID_FAILED
```

Primary failure classification:

```text
SEARCH_MATERIAL_RECEIPT_MISSING
```

Secondary signals:

```text
IRRELEVANT_CARDS_CORRECTLY_REJECTED, FINISH_POLICY_GAP_BY_DESIGN_UNTIL_RELEVANT_EVIDENCE, MODEL_FINISH_BEFORE_REAL_BROWSER_ASSERTION
```

5I was a consumed one-provider mission. It did **not** prove search actuation plus relevant product extraction quality. It did prove that Pack 3 did not fake success from irrelevant visible cards.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt5i-20260702-203543
```

## Source State

```text
source_commit = c039ed6e477d18a05c87a5ecd2813015a93a3c32
branch = experimental/real-model-lab-freeze-v1
git_status_before_count = 3
```

Pre-existing dirty docs were not staged or reverted.

## Safe Preflight

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = provider_catalog_env_or_default
endpoint_hash = dbcce923efcb09c238dc02f7f7f275b02e9c6346b6af7b5783d63d3276c3083b
provider_api_key_present = true
browser_test_url_present = true
browser_headless_config_present = true
safe_url_origin_hash = fb99d58087af0b45bbe293cc38e342df510378e14772907216db74a46a5a0efe
provider_native_tools_disabled = true
fallback_auto_disabled = true
```

Raw endpoint values, API keys, Authorization values, raw provider output, raw reasoning, raw DOM, screenshots, cookies, and session data are omitted.

## Metrics

```text
provider_decision_calls = 8
model_native_intent_accepted_count = 8
metadata.reply_native_count = 0
search_attempt_count = 2
search_material_receipt_count = 0
search_failure_recovery_path = None
product_or_result_candidate_card_count = 6
relevant_product_card_count = 0
under_5_eur_supported_count = 0
unknown_price_or_currency_count = 6
extract_product_cards_count = 1
verify_extraction_count = 1
summarize_evidence_count = 1
summary_present = true
finish_present = false
mission_status = blocked
loop_final_reason = model_led_task_loop_blocked
blocked_reason = MODEL_FINISH_BEFORE_REAL_BROWSER_ASSERTION
```

## Backend Truth

```text
selected_backend_id = playwright_real_browser_engine
actual_backend_id = playwright_real_browser_engine
backend_mismatch_status = none
cloak_session_backend_actually_used = false
```

There was no silent selected/actual backend mismatch.

## Model Action Sequence

1. `real_browser_control:real_browser.open`
2. `real_browser_control:real_browser.observe`
3. `real_browser_control:real_browser.search`
4. `real_browser_control:real_browser.extract_product_cards`
5. `real_browser_control:real_browser.verify_extraction`
6. `sentinel_loop:summarize_evidence`
7. `real_browser_control:real_browser.search`

Raw locator primitives were not the model-facing primary path:

```text
real_browser.type_text/click/select_option/press_key/wait_for_text/wait_for_load primary path = false
```

## Search And Extraction Proof

```text
real_browser.search_attempted = true
search_material_receipt_exists = false
relevant_visible_cards_recovery = false
extraction_card_exists = true
relevance_fields_present = true
relevant_product_evidence = false
under_5_eur_supported_by_visible_evidence = false
unknown_fields_preserved = true
```

Safe extracted samples:

- title=`Amplificateur de basse`, price=`unknown`, currency=`unknown`, moq=`unknown`, relevance=`irrelevant`, price_support=`unknown`
- title=`Processeur audio`, price=`unknown`, currency=`unknown`, moq=`unknown`, relevance=`irrelevant`, price_support=`unknown`
- title=`Lecteur de cassettes`, price=`unknown`, currency=`unknown`, moq=`unknown`, relevance=`irrelevant`, price_support=`unknown`
- title=`Amplificateurs`, price=`unknown`, currency=`unknown`, moq=`unknown`, relevance=`irrelevant`, price_support=`unknown`
- title=`Protecteur de câble`, price=`unknown`, currency=`unknown`, moq=`unknown`, relevance=`irrelevant`, price_support=`unknown`

The extracted cards were visible product/result candidates, but they were irrelevant to the requested glasses/sunglasses objective and did not provide visible EUR under-5 support. This is a valid failure, not a fake success.

## Replay Proof

```text
replay_no_react = true
model_calls_delta = 0
browser_open_delta = 0
browser_click_delta = 0
browser_type_delta = 0
browser_press_delta = 0
browser_extract_delta = 0
receipt_writes_delta = 0
artifact_hashes_stable = true
```

Replay did not reopen, reclick, retype, resubmit, or reextract.

## Safety Scan

```text
safety_scan_high_risk_hit_count = 0
provider_failures = 0
raw_provider_values_persisted = false
raw_reasoning_persisted = false
raw_dom_or_screenshot_persisted = false
cookies_or_session_persisted = false
credential_values_persisted = false
```

Safe diagnostics may retain provider top-level key names and response hashes, but not raw provider bodies.

## Credential Cleanup

```text
process_scoped_env_removed_after_command = true
raw_credential_values_printed = false
raw_endpoint_values_printed = false
```

The run shell removed the process-scoped model/browser env variables in a `finally` block.

## Contract Check

```text
provider_decision_calls >= 3 = true
model_native_intent_accepted = true
real_browser.search_attempted = true
search_material_receipt_or_relevant_recovery = false
product_cards_extracted = true
relevance_fields_present = true
under_5_eur_visible_support = false
verify_extraction_emitted = true
grounded_summary_present = true
finish_emitted = false
mission_completed = false
replay_no_react = true
high_risk_scan_clean = true
```

Therefore:

```text
REAL_POWER_ATTEMPT_5I = VALID_FAILED
```

## Interpretation

5I proves the system now refuses irrelevant completion. The model/loop reached the browser skill path, attempted search, extracted cards, verified extraction, and produced a summary. But search did not produce a material search receipt, the extracted cards were non-eyewear homepage/category cards, no visible under-5-EUR support existed, and the mission blocked rather than pretending the shopping objective was satisfied.

Recommended next action:

```text
FIX_BROWSER_SEARCH_ACTUATION_MATERIAL_RECEIPT_V1
```

## Confirmation

```text
one provider mission consumed = true
retry after provider call = false
fallback/AUTO = false
provider-native tools = false
push = false
merge = false
fake success = false
safe evidence only = true
source changes after provider run = false
```
