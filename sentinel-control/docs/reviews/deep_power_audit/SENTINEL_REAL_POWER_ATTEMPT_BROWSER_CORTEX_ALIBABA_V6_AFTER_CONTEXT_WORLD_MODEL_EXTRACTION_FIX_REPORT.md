# Real Power Attempt Browser Cortex Alibaba V6 After Context World Model Extraction Fix

verdict = VALID_FAILED

failure_classification = PRODUCT_LOOP_BROWSER_CONTEXT_PROPAGATION_GAP_AFTER_MATERIAL_SEARCH

secondary = RELEVANT_CARDS_NOT_FOUND, RUNNER_REPORTING_SAFE_MODEL_DUMP_GAP

## Safe Facts

provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
provider_decision_calls_inferred_min = 2
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
raw endpoint / credential / binary path / target URL values persisted = false

## What V6 Proved

```text
Cloak readiness passed before provider
real_browser.search executed through Cloak/session backend
search produced a material ProductActionKernel receipt
world model captured visible search-result state and product/result cards
model/runtime attempted real_browser.extract_product_cards next
replay no-react held from stored artifacts
```

## What Failed

The search mission closeout contained rich safe context cards, including
`browser_world_model` and `browser_world_model_summary`. The following extract
mission closeout had empty `safe_context_cards` and blocked with
`browser_session_missing_or_closed`.

That means the V5 runtime fallback exists, but the product loop did not
propagate the previous completed browser world model into the next material
extraction request.

A second quality truth also remains: the captured cards were not relevant
eyewear results, so this cannot be called product success even if extraction had
completed.

## Metrics

```text
search_attempt_count = 1
search_material_receipt_count = 1
extract_product_cards_count = 1
extract_product_cards_receipt_count = 0
verify_extraction_count = 0
summarize_evidence_count = 0
summary_present = false
finish_present = false
mission_status = blocked
loop_blocked_reason = browser_session_missing_or_closed
product_or_result_candidate_card_count = 6
relevant_product_card_count = 0
under_5_eur_supported_count = 0
unknown_price_or_currency_count = 6
browser_receipt_count = 1
product_receipt_count = 1
replay_no_react = true
safety_scan_high_risk_hit_count = 0
```

## World Model Snapshot

```json
{
  "captcha_or_login_signals": 0,
  "dynamic_loading_signals": 0,
  "modal_or_consent_signals": 0,
  "page_kind_guess": "search_results",
  "product_or_result_candidate_card_count": 6,
  "search_like_refs_count": 2,
  "stable_refs_count": 753,
  "world_model_id": "browser_world_model_85092f4fbd854a5cb3f0529bcf5783ed"
}
```

## Context Propagation Proof

```text
search_closeout_safe_context_card_keys_count = 9
extract_closeout_safe_context_card_keys_count = 0
extract_blocked_reason = browser_session_missing_or_closed
```

## Replay

```json
{
  "artifact_hashes_stable": true,
  "channel_transport_sends_delta": 0,
  "command_executions_delta": 0,
  "finalgate_writes_delta": 0,
  "model_calls_delta": 0,
  "product_dispatch_delta": 0,
  "receipt_writes_delta": 0,
  "reexecuted_actions": false
}
```

## Next Fix

```text
FIX_PRODUCT_LOOP_BROWSER_SAFE_CONTEXT_PROPAGATION_AFTER_MATERIAL_SEARCH_V1
```

No retry was performed. No fallback/AUTO, provider-native tools, high-risk
browser action, raw provider/reasoning/DOM/screenshot/cookie/session
persistence, or push.
