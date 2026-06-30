# SENTINEL_REAL_POWER_ATTEMPT_5E_MODEL_LED_ALIBABA_BROWSER_BACKEND_BRIDGE_AND_SEARCH_RECOVERY_V1_REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_5E = VALID_FAILED
primary_failure_classification = PROVIDER_DECISION_FAILURE
secondary_failure_classifications = SEARCH_ACTUATION_STILL_FAILED, RECOVERY_DID_NOT_ROUTE_TO_EXTRACTION
```

This was one real-provider mission run after `FIX_BROWSER_BACKEND_SELECTION_BRIDGE_AND_SEARCH_ACTUATION_V1`.

It did not meet the success threshold. The run did prove that the backend mismatch is no longer silent for this path: the attempt explicitly selected the Playwright compatibility backend before execution, and the actual runtime engine was Playwright. The remaining product failure is that the model did not reach extraction/summary/finish after recoverable browser search failures.

## Run Identity

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt5e-20260701-002449
mission_id = mission_a59782b21f294df1aef308094caa6abb
source_commit = e2f7958d742b9e56b4bfce0499db38893cec300a
attempt_exit_code = 0
```

Source/runtime/test tree before the run:

```text
source_runtime_test_dirty_count = 0
repo_git_status_before = dirty docs only, status_short_count = 3
```

The pre-existing dirty docs were not part of runtime execution.

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

## Backend Truth

Backend frame:

```text
model_visible_backend_id = browser_skill
preferred_backend_id = cloak_browser
compatibility_backend_id = playwright_real_browser_engine
selection_reason = cloak_browser_backend_available
playwright_requires_explicit_compatibility = true
```

Run selection:

```text
selected_backend_id = playwright_real_browser_engine
actual_engine_class = PlaywrightRealBrowserEngine
cloak_session_backend_actually_used = false
silent_mismatch = false
```

Interpretation:

```text
BACKEND_SELECTION_STILL_MISMATCHED = false
EXPLICIT_COMPATIBILITY_BACKEND_BLOCKED = false
```

The run did not silently execute Playwright under an undeclared Cloak-preferred frame. It explicitly declared the compatibility backend before execution.

## Provider Decisions

```text
provider_decision_calls = 7
provider_failures = 0
model_extraction_failures = 3
```

Safe extraction diagnostics:

```text
turn 2:
  failure_class = JSONDecodeError
  failure_code = Expecting value: line 1 column 1 (char 0)
  top_level_keys = metadata, reply

turn 3:
  failure_class = ValueError
  failure_code = no_action_json_object_detected
  top_level_keys =
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

turn 7:
  failure_class = JSONDecodeError
  failure_code = Expecting value: line 1 column 1 (char 0)
  top_level_keys = metadata, reply
```

These diagnostics retain structure and hashes only; no raw model/provider output is included here.

## Model Action Sequence

```text
1. real_browser_control.real_browser.open
2. model_protocol.empty_action_envelope
3. model_protocol.empty_action_envelope
4. real_browser_control.real_browser.search
5. real_browser_control.real_browser.open
6. real_browser_control.real_browser.search
7. model_protocol.empty_action_envelope
```

Safe actionable decisions extracted:

```text
real_browser.open
real_browser.search
real_browser.open
real_browser.search
```

Skill-first status:

```text
model_visible_actions_skill_first = true
raw_locator_primitives_as_primary_path = false
```

The model did not choose raw primitive browser actions:

```text
real_browser.type_text = not chosen
real_browser.click = not chosen
real_browser.select_option = not chosen
real_browser.press_key = not chosen
real_browser.wait_for_load = not chosen
real_browser.wait_for_text = not chosen
```

## Browser Runtime Result

Browser counts:

```text
open = 2
observe = 4
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

Search/navigation:

```text
search_or_navigation_evidence = true
search_actions_completed_materially = false
```

Product/world-model evidence:

```text
world_model_cards = 3
max_visible_refs = 60
search_like_refs_seen = true
link_refs_seen = true
product_or_result_candidate_card_count = 12
```

Extraction/summary:

```text
real_browser.extract_product_cards chosen = false
real_browser.verify_extraction chosen = false
meaningful_extraction_evidence = false
summary_produced = false
finish_emitted = false
```

The page perception remained useful, but the model did not convert the existing product cards into an extraction/verification/finish sequence.

## Mission / FinalGate

```text
mission_status = blocked
loop_status = blocked
loop_final_reason = model_led_task_loop_blocked
loop_blocked_reason = MODEL_CORRECTION_BUDGET_EXHAUSTED
loop_certificate_count = 1
loop_finalgate_status = blocked
loop_finalgate_accepted = false
loop_finalgate_reason = MODEL_CORRECTION_BUDGET_EXHAUSTED
```

Receipts:

```text
receipt_count = 2
receipt_refs =
  real_browser_open_08e49594bbed44f4985f03f4c7f12ab1
  real_browser_open_ce79844ba0704e1aa32ca240628b7d8e
```

No fake browser search receipt, extraction receipt, summary, or finish certificate was created.

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
reexecuted_actions = false
artifact_hashes_stable = true
browser_state_hash_stable = true
replay_no_react = true
```

Replay did not reopen, reclick, retype, resubmit, or reextract.

## Safety Scan

The run script's built-in scan reported:

```text
safety_scan.hit_count = 0
```

A broader targeted scan over run artifacts found only benign guard/diagnostic markers:

```text
run_attempt5e.py guard strings:
  API key
  Authorization
  raw_prompt
  raw_response
  raw_reasoning
  reasoning_content
  provider wrapper payload
  provider-native
  fallback
  AUTO
  raw_provider_response

safe provider diagnostics:
  raw_provider_response as a top-level key name only
  fallback_auto_disabled field names

page/world-model artifacts:
  AUTO substring in visible page text / generated safe cards
```

No credential values, endpoint values, Authorization values, raw provider payloads, cookies, sessions, screenshots, full DOM, provider-native tool enablement, or fallback/AUTO enablement were found.

## Classification

```text
REAL_POWER_ATTEMPT_5E = VALID_FAILED
primary = PROVIDER_DECISION_FAILURE
secondary = SEARCH_ACTUATION_STILL_FAILED
observed_not_finished = SUMMARY_FINISH_POLICY_GAP
not_selected = BACKEND_SELECTION_STILL_MISMATCHED
not_selected = EXPLICIT_COMPATIBILITY_BACKEND_BLOCKED
not_selected = REPLAY_NO_REACT_GAP
```

The strongest blocker is provider/model decision shape under this browser skill context:

```text
metadata/reply envelope or no_action_json_object_detected
=> empty_action_envelope
=> correction budget exhausted
```

The browser still has a search actuation weakness too:

```text
real_browser.search reached runtime twice
both search attempts recoverable_failed
no material search receipt
```

Because product cards already existed but no extraction action was emitted, the next fix should focus on the real model action protocol/context after recoverable search and existing cards, not on backend selection.

## Recommended Next Action

```text
FIX_PROVIDER_OR_MODEL_DECISION_FAILURE_V1
```

Tight scope:

```text
make the browser skill decision frame force valid canonical ActionEnvelope after recoverable search
prefer extract_product_cards / verify_extraction when product cards exist
avoid open/search loop when page perception already has candidate cards
preserve explicit backend truth and replay no-react
```

Do not run another real attempt until that fix is locally validated.

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
process-scoped credentials removed after run = yes
```

