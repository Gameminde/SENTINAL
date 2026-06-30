# SENTINEL_REAL_POWER_ATTEMPT_5F_MODEL_NATIVE_BROWSER_CONTROL_LOOP_V1_REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_5F_MODEL_NATIVE_BROWSER_CONTROL_LOOP_V1 = VALID_FAILED
primary_failure_classification = EXTRACTION_NOT_TRIGGERED_WITH_VISIBLE_CARDS
```

This was the single approved real-provider mission after `BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1`.

The run did not meet the product success threshold. It did prove the important protocol correction from 5E:

```text
metadata.reply / natural browser intent no longer collapsed into empty_action_envelope
ModelLedTaskLoop consumed model-native intent
safe native intent was mapped into internal ActionEnvelope skills
ActionEnvelope remained internal runtime language
```

The remaining blocker is now narrower and more concrete:

```text
product cards were visible in the world model
but the loop/model path did not route to extract_product_cards / verify_extraction / finish
```

## Run Identity

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt5f-20260701-012507
mission_id = mission_f8f26fb2232d4ce99a334d85f765fd13
source_commit = 1cebea5613d288939c9b0a038cbc6f3932ced924
attempt_exit_code = 0
```

There was one pre-provider bootstrap launch issue before the actual mission:

```text
bootstrap_import_failure = ModuleNotFoundError: sentinel
provider_calls_before_bootstrap_fix = 0
mission_created_before_bootstrap_fix = false
```

That did not consume a provider attempt. The actual provider mission then ran once with the correct `PYTHONPATH`.

## Preflight Safe Facts

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = provider_catalog_env_or_default
endpoint_hash = dbcce923efcb09c238dc02f7f7f275b02e9c6346b6af7b5783d63d3276c3083b
bounded_origin_hash = fb99d58087af0b45bbe293cc38e342df510378e14772907216db74a46a5a0efe
provider_api_key_present = true
aliyun_base_url_present = true
cert_model_base_url_present = true
browser_test_url_present = true
browser_headless_config_present = true
playwright_importable = true
provider_native_tools_disabled = true
fallback_auto_disabled = true
```

No raw endpoint URL, credential value, Authorization header, raw provider output, raw reasoning, cookies, session data, full DOM, or screenshot is included in this report.

## Provider And Native Intent

```text
provider_decision_calls = 4
provider_failures = 0
model_extraction_failures = 0
model_native_mapping_failures = 0
model_native_intent_accepted_count = 4
model_native_noncanonical_accepted_count = 3
metadata_reply_native_count = 2
```

Safe provider response shapes:

```text
turn 1 top_level_keys =
  content_extraction_source, finish_reason, json_object_detected,
  markdown_fence_detected, multiple_json_objects_detected,
  normalization_strategy, output_truncated, raw_provider_response,
  raw_text_hash, reasoning_char_count, reasoning_hash,
  reasoning_present, visible_content_char_count,
  visible_content_estimated_tokens

turn 2 top_level_keys = metadata, reply
turn 3 top_level_keys = metadata, reply

turn 4 top_level_keys =
  capability_id, content_extraction_source, finish_reason,
  json_object_detected, normalization_strategy, operation,
  output_truncated, params, raw_provider_response,
  reasoning_char_count, reasoning_hash, reasoning_present,
  visible_content_char_count, visible_content_estimated_tokens
```

The key proof is that turns 2 and 3 were `metadata/reply` envelope responses with visible content. In 5E this class of response fed `empty_action_envelope` correction churn. In 5F, the model-native mapper consumed them and produced internal browser skill envelopes.

## Model Action Sequence

```text
1. real_browser_control:real_browser.open
2. real_browser_control:real_browser.open
3. real_browser_control:real_browser.open
4. real_browser_control:real_browser.search
```

Model-facing behavior:

```text
skill_first_path = true
raw_locator_primitives_as_primary_path = false
ActionEnvelope_internal_runtime_format = true
```

The model did not choose:

```text
real_browser.type_text
real_browser.click
real_browser.select_option
real_browser.press_key
real_browser.wait_for_load
real_browser.wait_for_text
```

Native mapping summary:

```text
turn 1: empty_or_ambiguous_intent -> real_browser.open
turn 2: safe_ambiguous_intent from reply -> real_browser.open
turn 3: safe_ambiguous_intent from reply -> real_browser.open
turn 4: canonical_action -> real_browser.search
```

## Browser Backend

Backend frame:

```text
model_visible_backend_id = browser_skill
preferred_backend_id = cloak_browser
compatibility_backend_id = playwright_real_browser_engine
playwright_requires_explicit_compatibility = true
selection_reason = cloak_browser_backend_available
```

Actual runtime:

```text
actual_engine_class = PlaywrightRealBrowserEngine
cloak_session_backend_actually_used = false
```

This run used the explicit compatibility path rather than a silent Cloak-preferred / Playwright-actual mismatch. Browser backend selection was not the primary 5F blocker.

## Browser Runtime Counts

```text
open = 2 material open receipts
observe = 3
search = 1 model decision, recoverable_failed
type = 0
click = 0
press = 0
select = 0
extract = 0
assert = 0
wait = 0
scroll = 0
```

Receipts:

```text
receipt_count = 2
receipt_refs =
  real_browser_open_e45008fe32f74bc68111ea7428a83187
  real_browser_open_ed188723cf62485b8cae043eeb0b9d0a
```

## Product Card Evidence

World model and refs:

```text
world_model_cards = 2
max_visible_refs = 45
search_like_refs_seen = true
link_refs_seen = true
product_or_result_candidate_card_count = 6
```

Safe product card field coverage:

```text
title_non_unknown = 6
short_features_non_unknown = 6
caveats_non_unknown = 6
visible_price_non_unknown = 0
minimum_order_non_unknown = 0
supplier_or_store_non_unknown = 0
```

This means the page perception was not empty. Sentinel already had enough safe product/result card structure to attempt `extract_product_cards`, but that action was not triggered.

## Finish And Mission Status

```text
product_cards_extracted_explicitly = false
verify_extraction_emitted = false
summary_produced = false
finish_emitted = false
mission_status = blocked
loop_status = blocked
loop_blocked_reason = loop_guard_deadline
loop_finalgate_status = blocked
loop_finalgate_accepted = false
loop_finalgate_reason = loop_guard_deadline
```

FinalGate:

```text
certificate = model_led_loop_finalgate_5fa178a05ae94a7c962593b5996dc9f4
accepted = false
reason = loop_guard_deadline
```

No fake extraction receipt, fake verification receipt, fake summary, or fake completion certificate was created.

## Replay No-React Proof

```text
model_calls_delta = 0
real_browser_open_delta = 0
real_browser_observe_delta = 0
real_browser_click_delta = 0
real_browser_type_delta = 0
real_browser_press_delta = 0
real_browser_scroll_delta = 0
real_browser_extract_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
workspace_mutations_delta = 0
reexecuted_actions = false
artifact_hashes_stable = true
browser_state_hash_stable = true
replay_no_react = true
```

Replay did not reopen, reclick, retype, resubmit, or reextract.

## Safety Scan

```text
safety_scan.hit_count = 0
api_key_persisted = false
authorization_persisted = false
raw_prompt_persisted = false
raw_provider_output_persisted = false
raw_reasoning_persisted = false
reasoning_content_persisted = false
cookies_or_session_material_persisted = false
full_dom_or_screenshot_persisted = false
provider_native_tools_enabled = false
fallback_AUTO_enabled = false
```

The run used process-scoped credential and browser environment variables and removed them from the shell process after execution.

## Success Criteria Check

| Criterion | Result |
|---|---|
| provider decision calls >= 3 | passed, 4 |
| model-native intent accepted at least once | passed, 4 accepted / 3 noncanonical |
| metadata.reply/content/reply envelope avoids empty_action_envelope | passed for turns 2 and 3 |
| no raw locator primitives as primary path | passed |
| product/result cards extracted explicitly | failed |
| verify_extraction emitted | failed |
| summary produced | failed |
| finish emitted | failed |
| mission completes by model finish | failed |
| replay no-react | passed |
| no raw provider/reasoning/DOM/screenshot/cookies/session persisted | passed |

## Failure Interpretation

Primary blocker:

```text
EXTRACTION_NOT_TRIGGERED_WITH_VISIBLE_CARDS
```

Why:

```text
product/result cards existed in the world model
native metadata.reply intents were consumed safely
but safe ambiguous intent still followed primary_recommended_action = real_browser.open
even after product_card_count became 3
the loop then reached search too late and blocked on loop_guard_deadline
```

This is not the 5E failure:

```text
PROVIDER_DECISION_FAILURE_STILL_PRESENT = false as primary
MODEL_NATIVE_INTENT_NOT_CONSUMED = false
empty_action_envelope churn = not observed
raw locator primitive path = not observed
```

The next bug is a routing/priority bug in the model-native mapper or skill decision frame:

```text
when product/result cards exist,
safe ambiguous browser intent should prefer extract_product_cards / verify_extraction
instead of repeating real_browser.open
```

## Recommended Next Action

```text
FIX_BROWSER_EXTRACTION_ROUTING_FROM_VISIBLE_CARDS_V1
```

Narrow target:

```text
when product cards exist and the provider reply is safe but ambiguous,
prefer extract_product_cards over another open/search loop

when extraction exists,
prefer verify_extraction

when verified extraction exists,
allow finish with summary
```

Do not add stricter JSON requirements. Keep the model-native loop. The right fix is routing useful natural intent toward the strongest available browser skill once the world model already has cards.

## Contract Confirmation

```text
one provider mission = yes
retry after provider call = no
fallback/AUTO = no
provider-native tools = no
push = no
merge = no
fake success = no
safe evidence only = yes
credentials removed after use = yes
```
