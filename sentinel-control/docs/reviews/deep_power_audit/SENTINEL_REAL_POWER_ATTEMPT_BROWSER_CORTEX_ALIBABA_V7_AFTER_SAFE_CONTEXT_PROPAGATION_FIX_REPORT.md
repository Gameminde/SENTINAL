# Real Power Attempt Browser Cortex Alibaba V7 After Safe Context Propagation Fix

verdict = VALID_FAILED

failure_classification = FIRST_TURN_EXTRACT_WITHOUT_BROWSER_CONTEXT_GAP

secondary = MODEL_NATIVE_INTENT_ROUTED_TO_NON_LIVING_EXTRACT, VERIFY_EXTRACTION_NOT_TRIGGERED

## Safe Facts

provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
provider_decision_calls = 1
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
raw endpoint / credential / binary path / target URL values persisted = false

## What V7 Proved

```text
Cloak readiness passed before provider
model-native metadata.reply intent was consumed
model emitted / mapper accepted real_browser.extract_product_cards as first action
no raw locator primitive was used as the primary path
replay no-react held
```

## What Failed

The first action was extraction before any search/open/observe/world-model
receipt existed in the product loop.

Because no safe browser context cards existed yet, extraction had no world model
fallback and blocked with `browser_session_missing_or_closed`.

The next fix must route first-turn extract/verify intent without browser cards
into `browse_search` or a living browser observation path, not execute a dead
extraction action.

## Metrics

```text
provider_decision_calls = 1
model_native_intent_accepted_count = 1
metadata_reply_native_count = 1
search_attempt_count = 0
search_material_receipt_count = 0
product_or_result_candidate_card_count = 0
extract_product_cards_count = 1
extract_product_cards_receipt_count = 0
verify_extraction_count = 0
summarize_evidence_count = 0
summary_present = false
finish_present = false
mission_status = blocked
loop_blocked_reason = browser_session_missing_or_closed
browser_receipt_count = 0
product_receipt_count = 0
replay_no_react = true
safety_scan_high_risk_hit_count = 0
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
FIX_BROWSER_MODEL_NATIVE_FIRST_TURN_EXTRACT_ROUTING_V1
```

No retry was performed. No fallback/AUTO, provider-native tools, high-risk
browser action, raw provider/reasoning/DOM/screenshot/cookie/session
persistence, or push.
