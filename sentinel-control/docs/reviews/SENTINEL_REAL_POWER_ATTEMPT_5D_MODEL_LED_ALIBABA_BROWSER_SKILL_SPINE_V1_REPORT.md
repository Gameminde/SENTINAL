# Sentinel Real Power Attempt 5D Model-Led Alibaba Browser Skill Spine V1 Report

## Verdict

```text
REAL_POWER_ATTEMPT_5D = VALID_FAILED
primary_failure_classification = PLAYWRIGHT_COMPAT_ONLY_RUNTIME_GAP
secondary_failure_classifications = SEARCH_ACTUATION_FAILURE, PROVIDER_DECISION_FAILURE
```

This was a valid one-shot real-provider mission run after Pack 6D. It did not meet the success threshold, but it produced useful product truth: the real model consumed the new browser skill path instead of raw locator primitives, while the actual live runtime still actuated through Playwright compatibility and failed to complete search/extraction/finish.

## Run Identity

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt5d-20260630-232313
mission_id = mission_44c77c612b8543b4a5f3e476910793f4
source_commit = b6614ae500148a0dc2cca782d34ccbb04bfd55b3
mission_exit_code = 0
```

There was one pre-provider bootstrap launch issue before the mission run:

```text
bootstrap_import_failure = ModuleNotFoundError: sentinel
provider_calls_before_bootstrap_fix = 0
mission_created_before_bootstrap_fix = false
```

The bootstrap failure was preserved separately as local run evidence and did not consume a provider or mission attempt. The actual provider mission then ran exactly once.

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

## Provider Decision Calls

```text
provider_decision_calls = 5
provider_failures = 0
model_extraction_failures = 1
provider_native_tools = not used
fallback_AUTO = not used
```

Turn 5 failed safe action extraction:

```text
failure_class = ValueError
failure_code = no_action_json_object_detected
json_object_detected = retained in provider diagnostics
top_level_keys = content_extraction_source, finish_reason, json_object_detected, normalization_strategy, output_truncated, raw_provider_response, raw_text_hash, reasoning_char_count, reasoning_hash, reasoning_present, visible_content_char_count, visible_content_estimated_tokens
```

Only hashes and structure fields were retained.

## Model Action Sequence

```text
1. real_browser_control.real_browser.open
2. real_browser_control.real_browser.search
3. real_browser_control.real_browser.open
4. real_browser_control.real_browser.search
5. model_protocol.empty_action_envelope
```

Model-visible actions were skill-first:

```text
model_visible_actions_skill_first = true
raw_locator_primitives_as_primary_path = false
raw_model_actions_seen = 0
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

## Browser Backend

Backend frame:

```text
model_visible_backend_id = browser_skill
preferred_backend_id = cloak_browser
compatibility_backend_id = playwright_real_browser_engine
selection_reason = cloak_browser_backend_available
playwright_requires_explicit_compatibility = true
```

Actual runtime:

```text
actual_engine_class = PlaywrightRealBrowserEngine
cloak_session_backend_actually_used = false
```

Interpretation:

```text
Cloak is visible/preferred in the backend frame, but the real attempt still actuated through Playwright compatibility.
This keeps the browser organ/backend bridge gap open.
```

## Browser Action Counts

```text
open = 2
observe = 5
search = 2 model decisions, both recoverable_failed
type = 0
click = 0
press = 0
select = 0
extract = 0
assert = 0
wait = 0
scroll = 0
```

Search/navigation evidence:

```text
search_or_navigation_evidence = true
search_actions_completed_materially = false
```

The two `real_browser.search` decisions reached the skill runtime, but both completed as recoverable failures. No material search receipt was created.

## World Model And Product Cards

World model proof:

```text
world_model_cards = 4
max_visible_refs = 60
search_like_refs_seen = true
link_refs_seen = true
blocker_signals = 0
```

Page/card summaries:

```text
world_model_1 page_kind = product_listing, stable_refs = 60, product_cards = 6
world_model_2 page_kind = product_listing, stable_refs = 60, product_cards = 6
world_model_3 page_kind = search_results, stable_refs = 45, search_like_refs = 1, product_cards = 3
world_model_4 page_kind = search_results, stable_refs = 43, search_like_refs = 1, product_cards = 3
```

Product/search card field coverage:

```text
product_or_result_candidate_card_count = 18
title_non_unknown = 18
short_features_non_unknown = 18
caveats_non_unknown = 2
visible_price_non_unknown = 0
currency_or_unit_non_unknown = 0
minimum_order_non_unknown = 0
supplier_or_store_non_unknown = 0
```

This is useful partial extraction from the world model, but it does not satisfy the full success threshold because the model never emitted `real_browser.extract_product_cards` or `real_browser.verify_extraction`, and no evaluative summary was produced.

## Mission / FinalGate

```text
mission_status = blocked
loop_status = blocked
loop_final_reason = model_led_task_loop_blocked
loop_blocked_reason = loop_guard_deadline
finish_emitted = false
summary_produced = false
browser_finalgate_count = 0
loop_certificate_count = 1
loop_finalgate_status = blocked
loop_finalgate_accepted = false
loop_finalgate_reason = loop_guard_deadline
receipt_count = 2
receipt_refs =
  real_browser_open_7a6c72cd253744c3ba0602236096e173
  real_browser_open_fcad406083714b60b2e86737cc36a068
```

The run did not fake success.

## Replay No-React Proof

Replay material deltas:

```text
model_calls_delta = 0
real_browser_open_delta = 0
real_browser_observe_delta = 0
real_browser_click_delta = 0
real_browser_type_delta = 0
real_browser_press_delta = 0
real_browser_extract_delta = 0
real_browser_wait_delta = 0
real_browser_scroll_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
workspace_mutations_delta = 0
artifact_hashes_stable = true
browser_state_hash_stable = true
```

Replay did not reopen, reclick, retype, resubmit, or reextract.

## Safety Scan

Targeted scan over the run root found:

```text
safety_scan_hit_count = 0
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

Process-scoped credential/browser environment variables were removed after the command.

## Success Criteria Check

| Criterion | Result |
|---|---|
| provider decision calls >= 3 | passed, 5 |
| model uses browser skill actions | passed |
| raw locator primitives not primary | passed |
| real search/navigation/state change or meaningful extraction | partial: search skill attempted, world model cards existed, but search material action failed |
| product/search extraction card exists | partial: world-model candidate cards existed, no explicit extraction action receipt |
| evaluative summary exists | failed |
| finish emitted | failed |
| mission completes by model finish | failed |
| replay no-react | passed |
| no raw DOM/screenshot/cookies/session/provider reasoning persisted | passed |

## Failure Interpretation

Primary blocker:

```text
PLAYWRIGHT_COMPAT_ONLY_RUNTIME_GAP
```

Why:

```text
The Pack 6D frame preferred Cloak/browser skill ownership, but actual actuation still used PlaywrightRealBrowserEngine. The model chose skill actions, but the live search skill returned recoverable_failed twice rather than producing a material search/navigation receipt.
```

Secondary blockers:

```text
SEARCH_ACTUATION_FAILURE
PROVIDER_DECISION_FAILURE
```

Why:

```text
Search reached runtime but did not materially actuate.
After two recoverable search failures and a repeated open, the fifth provider decision did not contain an actionable JSON object.
```

This is not:

```text
SKILL_FRAME_NOT_CONSUMED
EXTRACTION_CARD_INSUFFICIENT as the first blocker
REPLAY_NO_REACT_GAP
fallback/AUTO behavior
provider-native tool behavior
credential or endpoint failure
```

## Recommended Next Action

```text
FIX_BROWSER_BACKEND_SELECTION_BRIDGE_AND_SEARCH_ACTUATION_V1
```

Narrow target:

```text
Make the real browser skill spine execute through the selected live backend when Cloak/session is available, or explicitly mark Playwright compatibility as the chosen backend before the run.
Then ensure real_browser.search can create a material search/navigation receipt or return recovery that drives extract/verify instead of repeated open/search loops.
```

Do not start another provider/browser run until that bridge is fixed locally and fake/local tests prove the selected backend/search path.

## Confirmation

```text
one provider mission run = yes
retry after provider call = no
fallback/AUTO = no
provider-native tools = no
push = no
merge = no
fake success = no
credentials removed after use = yes
safe evidence only = yes
```
