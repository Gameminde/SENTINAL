# SENTINEL_REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V2_REPORT

## Verdict

```text
REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V2 = VALID_FAILED
```

This run consumed exactly one real-provider mission. No retry was run.

The product loop completed, but the mission quality target was not satisfied. The run proves the typed browser search parameter was no longer blocked as topic-policing at mission creation/preflight, and it proves real Cloak backend truth for later browser actions. It does not prove useful Python.org documentation search completion.

## Frozen Mission

```text
target_site = python.org
frozen_holdout_used = no
fixture_backend = false
Playwright_fallback = false
provider_is_real = true
real_browser_backend = cloak_browser
max_provider_calls = 6
max_material_actions = 8
```

Mission objective hash:

```text
d481f23cb8cef5e9
```

Mission objective, frozen before execution:

```text
Use the bounded Python.org public search page to find official Python documentation about pathlib Path.glob. Generate an appropriate search query yourself, inspect/search safely, extract grounded evidence from visible results or page content, preserve unknowns, assess objective relevance, provide a short useful answer, and finish.
```

Forbidden effects remained:

```text
login
credentials
personal/contact form submission
upload
download
contact
payment
checkout
provider-native tools
fallback/AUTO
```

## Preflight

Provider smoke test was run before the mission to validate the replaced API key without printing or persisting key/base URL values.

```text
provider_config_present = true
provider_smoke_auth_failure = false
provider_smoke_raw_output_printed = false
provider_smoke_raw_output_persisted = false
provider_id = aliyun_dashscope
provider_backend = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
```

Cloak readiness passed before provider mission consumption:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
backend_identity_matched = true
process_operational = true
context_operational = true
page_operational = true
devtools_operational = true
multi_action_reuse_operational = true
cleanup_operational = true
reopen_operational = true
profile_material_persisted = false
safe_url_origin_hash = e89a56b7e964e4b6055990b874700f32ecc5cc22c2f7226851bbf5d48c9577ac
```

The Cloak package printed an update notice during readiness. No install/update/download/substitution was performed.

## Execution Path

Required product path used:

```text
real provider/model
-> ProductModelNativeDecisionClient
-> ModelLedProductActionKernelTaskLoop
-> RuntimeHost
-> MissionLifecycleService
-> ProductActionKernel
-> RealBrowserControlRuntime / browser skill backend
-> BrowserSessionManager / Cloak backend
-> receipts
-> FinalGate
-> static replay view
```

The report synthesis script crashed after the mission had completed because it attempted to read a nonexistent reporting-only attribute:

```text
AttributeError: 'UnifiedDispatchResult' object has no attribute 'material_action'
```

This was a post-run report synthesis bug. It did not trigger a provider retry or runtime patch. The evidence below was recovered from the persisted mission store.

## Provider And Model Decisions

```text
provider_decision_calls = 4
provider_decisions_model_native = true
provider_native_tools = false
raw_provider_output_persisted = false
raw_provider_reasoning_persisted = false
```

Provider call count is reconstructed from the four persisted product-loop actions. The in-memory counter from the runner was lost when report synthesis crashed.

Model-selected product action sequence:

```text
1. browse_search -> real_browser.search
2. extract -> real_browser.extract_product_cards
3. extract -> real_browser.verify_extraction
4. finish/summarize_evidence -> loop finish
```

Task-loop final certificate:

```text
certificate_id = product_action_kernel_task_loop_finalgate_45897f9fd0db4d9598bf959eb4331bd2
status = completed
reason = model_led_product_action_kernel_task_loop_finish
certificate_file_hash = e436b78acbba231b4965ba0cb23520918e2e07cf343cbdf7b8242a6525b79930
```

## Typed Query Boundary Proof

The search action persisted typed parameters as inert data:

```text
mission_id = mission_83fa89bf7e5f44b5a646735fc6748a15
operation = real_browser.search
parameters_keys = query
query_hash = 19016c07c531e00e
parameter_hash = d1222ac588454911c1b0ce6de5191b3241c00ea13f64f66011b0299213e70c98
authority_effect = none
data_not_authority = true
```

The query was accepted as a typed browser search parameter through MissionLifecycleService and ProductActionKernel. It was not rejected as an unsafe topic.

Browser dispatch context for the search action recorded:

```text
canonical_action_id = real_browser_control.real_browser.search
capability_id = real_browser_control
source_runtime = real_browser_control
browser_backend_execution.selected_backend_id = cloak_browser
browser_backend_execution.actual_backend_id = cloak_browser
browser_backend_execution.session_backend_kind = cloakbrowser
browser_backend_execution.product_backend_proven = true
```

However, the search action did not produce a material search receipt:

```text
status = blocked
blocked_reason = real_browser_search_actuation_failed
product_receipt = product_action_kernel_receipt_11198775f8204c61bb28ee9dae6312cf
execution_status = recoverable_failed
material_action = false
recovery_classification = RECOVERABLE_BROWSER_STATE_FAILURE
terminal_certificate = dispatch_terminal_99a42818eaa543fdb8f6f5c4fb212acc
```

Conclusion:

```text
typed_query_reached_product_browser_dispatch = true
typed_query_was_not_topic_policed = true
typed_query_materially_actuated_by_search = false
typed_query_search_receipt_created = false
```

## Browser Body Evidence

Search action environment state:

```text
browser_environment_state_id = browser_env_state_dd37767862ba4d5687227aa77f5ee7ac
browser_environment_state_hash = d657348809d013a0ec060e82ff2e92a4f115e0faf57a7684f055a2c93a5434d9
page_kind_guess = search_results
stable_ref_count = 188
product_or_result_candidate_count = 6
relevant_product_candidate_count = 0
raw_material_persisted = false
cookie_count = 0
storage_key_count = 0
profile_material_persisted = false
origin_hash = e89a56b7e964e4b6055990b874700f32ecc5cc22c2f7226851bbf5d48c9577ac
```

Material browser receipts:

```text
real_browser_action_1c22a39c4ab148d9b5333ff9da8bd3d1
  action_kind = real_browser.extract_product_cards
  status = completed
  selected_backend_id = cloak_browser
  actual_backend_id = cloak_browser
  session_backend_kind = cloakbrowser
  backend_mismatch = false
  replay_behavior = no_reexecute_on_replay

real_browser_action_47bb20b7fb3745b2a154c64042b4a128
  action_kind = real_browser.verify_extraction
  status = passed
  selected_backend_id = cloak_browser
  actual_backend_id = cloak_browser
  session_backend_kind = cloakbrowser
  backend_mismatch = false
  replay_behavior = no_reexecute_on_replay
```

Root/session continuity truth:

```text
browser_session_ref_count_inside_root = not_proven_as_1
extract_browser_session_ref = mission_workspace:browser_session:83fcd1f5e65fad3b
verify_browser_session_ref = mission_workspace:browser_session:d47e875fe207908b
search_browser_receipt_session_ref = absent
```

The run proves selected/actual Cloak backend truth for material extract and verify actions. It does not prove a single stable browser session ref across every child action.

## Evidence Quality

The recovery path after failed search extracted visible candidate cards, then verified extraction, then produced a summary lane.

```text
product_or_result_candidate_card_count = 6
relevant_product_candidate_count = 0
unknown_price_count = 6
objective_relevance_assessed = true in summary cards
under_price_condition_supported_by_visible_evidence = no_relevant_products
unknown_fields_preserved = true
```

But the extraction and summary machinery remained commerce/product-shaped on a Python documentation task:

```text
card_kind = product_candidate
relevance_to_objective = unknown
summary_kind = grounded_browser_evidence_summary
has_relevant_product_evidence = false
```

The final summary lane did not produce a useful answer about official Python documentation for `pathlib Path.glob`. It produced a grounded but irrelevant product-style negative/unknown summary.

Therefore:

```text
unsupported_claims = 0
unknown_values_preserved = true
objective_relevance_quality = failed
useful_python_docs_answer = false
search_quality_success = false
```

## Replay And Cleanup

Static replay view from persisted store:

```text
reexecuted_actions = false
model_calls_delta = 0
product_dispatch_delta = 0
command_executions_delta = 0
channel_transport_sends_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
```

Post-run cleanup checks:

```text
matching_browser_process_count_after_run = 0
profile_like_material_in_run_workspace = 0
profile_like_material_in_preflight_artifacts = 0
profile_like_material_in_run_store = 0
raw_dom_persisted = 0
cookies_persisted = 0
session_profile_material_persisted = 0
```

Replay ledger directories in mission workspaces were empty; no separate replay artifact was written. The no-react result above is a static store replay view, not a full exported replay bundle.

## Body Verdict

```text
lifecycle = partial_pass
backend_truth = pass
cloak_selected_actual_match = pass
Playwright_fallback = false
fixture_backend = false
search_actuation = failed
search_material_receipt = absent
session_reuse_across_child_actions = not_proven
cleanup = pass
profile_material_cleanup = pass
```

## Mind/Body Verdict

```text
model_strategy_accepted = true
safe_alternate_model_trajectory_allowed = true
hardcoded_query_override = false
useful_action_ratio = 3/4 completed-or-passed product-loop actions
material_browser_action_count = 2
repeated_identical_action_without_new_evidence = 0
recovery_quality = partial_pass
evidence_quality = failed_for_objective
```

The model was not blocked for discussing or searching ordinary sensitive vocabulary. The remaining failure is not the old topic-policing blocker. It is a browser body/search-quality and evidence-shaping failure.

## Mission Verdict

```text
product_loop_status = completed
product_loop_final_reason = model_led_product_action_kernel_task_loop_finish
mission_quality_status = VALID_FAILED
mission_verdict = completed_but_not_useful_for_objective
```

Failure classifications:

```text
SEARCH_ACTUATION_RUNTIME_FAILURE
SEARCH_MATERIAL_RECEIPT_MISSING
EVIDENCE_QUALITY_FAILURE
BROWSER_ENTITY_ONTOLOGY_DISTORTION
SESSION_REUSE_NOT_PROVEN
REPORT_SYNTHESIS_POST_RUN_BUG
```

Not observed:

```text
topic_policing_regression = false
provider_auth_failure = false
Cloak_backend_mismatch = false
silent_Playwright_fallback = false
fixture_backend_used = false
raw_provider_output_persisted = false
raw_provider_reasoning_persisted = false
raw_DOM_persisted = false
cookie_or_session_persistence = false
hard_boundary_violation = false
```

## Next Fix Recommendation

Do not rerun Python.org immediately and do not return to topic policing.

Recommended next work:

```text
FIX_BROWSER_SEARCH_ACTUATION_AND_OPEN_WORLD_EVIDENCE_ROUTING_V1
```

Target:

```text
1. real_browser.search must produce a material search/navigation/result-region receipt or a clearer typed recoverable body failure.
2. Browser extraction must route non-commerce information tasks into open-world result/document entities, not commerce product cards.
3. Completion should require a useful grounded answer for documentation/information objectives, not merely a product-style summary.
4. Root browser lease/session continuity across child actions must be made explicit and persisted in receipts.
5. Report synthesis must not assume UnifiedDispatchResult.material_action exists.
```

No runtime changes were made during or after this run.
