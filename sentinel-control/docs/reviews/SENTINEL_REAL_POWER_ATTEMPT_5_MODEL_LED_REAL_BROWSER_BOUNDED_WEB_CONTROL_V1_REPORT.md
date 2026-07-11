# SENTINEL REAL POWER ATTEMPT 5 MODEL LED REAL BROWSER BOUNDED WEB CONTROL V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1 = VALID_FAILED
```

Pack 6 is not yet product-proven on a real complex web page.

## Run Scope

Consumed run root:

```text
C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\attempt5-real-browser-20260629-151253
```

The bounded target was the configured Alibaba origin. Retained artifacts use only the bounded origin hash:

```text
safe_url_origin_hash = fb99d58087af0b45bbe293cc38e342df510378e14772907216db74a46a5a0efe
```

Raw URL, cookies, session data, screenshots, full DOM, provider raw output, and reasoning were not persisted.

## Preflight Safe Facts

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = provider_catalog_env_or_default
endpoint_hash = dbcce923efcb09c238dc02f7f7f275b02e9c6346b6af7b5783d63d3276c3083b
credential_present = true
browser_target_config_present = true
browser_headless_config_present = true
playwright_importable = true
provider_native_tools_disabled = true
fallback_auto_disabled = true
```

Source commit:

```text
a3be7a21c8ab2f7a6b6cc4379a13da64b81be60c
```

Repo status before run:

```text
branch = experimental/real-model-lab-freeze-v1
status_short_count = 0
```

## Provider / Browser Counts

```text
provider_decision_calls = 2
model_extraction_failures = 1

browser_open = 1
browser_observe = 1
browser_type = 0
browser_click = 0
browser_select = 0
browser_extract = 0
browser_assert = 0

receipt_count = 1
finalgate_count = 0
loop_certificate_count = 1
```

## Model Action Sequence

```text
real_browser_control:real_browser.open
```

The model successfully chose the first bounded browser action. The runtime opened the configured target and persisted:

```text
receipt = real_browser_open_9776acfc4e6b4d898161f8d0aead62b8
receipt_status = completed
```

The second provider decision did not yield a canonical action envelope.

## Safe Diagnostics

Failure:

```text
failure_blocker = MODEL_DECISION_EXTRACTION_FAILURE
loop_blocked_reason = MODEL_DECISION_EXTRACTION_FAILURE:no_action_json_object_detected
mission_status = blocked
loop_status = blocked
```

Turn 2 provider transport did not fail:

```text
provider_failure = false
error_class = null
http_status = null
```

Turn 2 safe top-level keys retained:

```text
content_extraction_source
finish_reason
json_object_detected
normalization_strategy
output_truncated
raw_provider_response
raw_text_hash
reasoning_char_count
reasoning_hash
reasoning_present
visible_content_char_count
visible_content_estimated_tokens
```

No `reply`, `content`, `action`, `capability_id`, or `operation` field reached the loop extractor on turn 2.

## Stable Refs / Extraction Proof

```text
stable_refs_quality.observation_receipts = 0
stable_refs_quality.max_visible_refs = 0
stable_refs_quality.search_like_refs_seen = false
stable_refs_quality.link_refs_seen = false
```

The open receipt proves the real browser reached a bounded page, but the run did not reach an explicit `real_browser.observe` action receipt. Therefore the model did not get stable Alibaba UI refs for search controls, product cards, links, or extraction. The product extraction objective was not satisfied.

## Summary / Finish

```text
summary_produced = false
finish = false
```

No product title, price/unit, MOQ, supplier/store, caveats, or evaluative summary were produced.

## Replay Proof

Material replay remained pure:

```text
model_calls_delta = 0
real_browser_open_delta = 0
real_browser_observe_delta = 0
real_browser_click_delta = 0
real_browser_type_delta = 0
real_browser_assert_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
workspace_mutations_delta = 0
artifact_hashes_stable = true
browser_state_hash_stable = true
```

Replay did not reopen, reclick, retype, resubmit, or reassert.

## Safety Scan

Targeted artifact scan result:

```text
hit_count = 0
```

No secret values, Authorization material, provider payloads, fallback/AUTO enablement, or provider-native tool enablement were found in retained safe artifacts. A textual negative assertion in this report mentions forbidden categories only to state absence.

## Interpretation

This is a useful product failure. Pack 6 proved that the real model can choose an initial bounded browser action and that Sentinel can open the real configured browser target with a receipt. It did not prove model-led real browser search/extraction on Alibaba.

The blocker is not endpoint, credential, provider transport, browser launch, authority, replay, fallback, or provider-native tools. The blocker is the real browser model-interface bridge after the first browser open:

```text
REAL_BROWSER_MODEL_ACTION_EXTRACTION_CONTEXT_GAP
```

Specifically, the second provider response reached Sentinel as safe provider metadata and hashes, but no extractable action object was available to the generic loop extractor.

## Recommended Next Fix

```text
FIX_REAL_BROWSER_MODEL_ACTION_PROTOCOL_OR_CONTEXT_V1
```

The fix should be narrow and power-first:

1. Ensure the real browser decision lane exposes normalized visible model content to the action extractor in memory, without persisting raw provider output.
2. Strengthen the post-open prompt/context so the next action is explicitly `real_browser.observe`.
3. Preserve provider-truth diagnostics if visible content is empty, hidden behind metadata, or not JSON.
4. Keep bounded URL authority, no cookies/session/full DOM persistence, no provider-native tools, no fallback/AUTO.
5. After the fix, rerun exactly one real browser attempt against the same bounded target.

## Confirmation

```text
one provider mission run consumed = true
no retry after provider call = true
no fallback/AUTO = true
no provider-native tools = true
no source changes after provider run = true
no push = true
```
