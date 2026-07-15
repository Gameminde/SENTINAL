# SENTINEL_REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_V1_REPORT

## Verdict

```text
REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_V1 = VALID_FAILED
mission_verdict = blocked
primary_failure = MODEL_OUTPUT_TO_SEARCH_PARAMS_REJECTED_BY_OPERATOR_CONTROL_SCAN
provider_calls = 1
runtime_behavior_modified_before_run = no
second_provider_mission = no
frozen_holdout_used = no
12_task_calibration_resumed = no
fixture_backend = false
Playwright_fallback = false
selected_backend = cloak_browser
actual_backend = cloak_browser
```

This was the single allowed real-provider mission. It was not retried.

The useful truth: live Cloak readiness passed before provider use, but the mission blocked before the first material browser action because model-native browser intent was mapped into search parameters that the operator control scanner rejected as unsafe payload.

## Frozen Mission

```text
attempt_id = REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_V1
target_site = www.python.org
target_origin_hash = 7a70cdd2ec2277c8f8e0c2cb8240646ca24a10e54af7230d1784d24e30be6fc6
mission_objective_hash = bbf8fded1342e74dfc33873f9c2945e077ec097875dbf07e3f155bc2ce1c94c0
authority_scope = read_only_public_web_single_non_holdout
allowed_domains = real_browser:bounded_test_url, www.python.org
max_provider_calls = 6
max_material_actions = 8
```

Mission objective, frozen before execution:

```text
Use the bounded Python.org public search page to find official Python documentation about pathlib Path.glob. Generate an appropriate search query yourself, inspect/search safely, extract grounded evidence from visible results or page content, preserve unknowns, assess objective relevance, provide a short useful answer, and finish.
```

Forbidden mission effects:

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

The task did not require one exact model action sequence.

## Preflight

```text
provider configuration present = true
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
provider_is_real = true
credential value printed = false
endpoint value printed = false
raw binary path printed = false
raw binary path persisted = false
```

Cloak binary provenance:

```text
candidate_found = true
path_hash = f3fad5133de1a876082e5a7f6be7c61cf083e2a4742c4cf44fcfa6cfe34d3a2e
file_sha256 = 03f53661a5c47e7b0a661bee2bce8a0d302b7a60834c328df417561fa0636d80
size_bytes = 3902976
version = 146.0.7680.177.5
bundled_version = 146.0.7680.177.5
platform = windows-x64
tier = free
```

Cloak readiness:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
backend_selected = true
backend_identity_matched = true
process_operational = true
context_operational = true
page_operational = true
multi_action_reuse_operational = true
cleanup_operational = true
reopen_operational = true
profile_material_persisted = false
```

## Execution Path

Required path reached up to the model decision and pre-dispatch mission creation boundary:

```text
real provider/model
-> ProductModelNativeDecisionClient
-> ModelLedProductActionKernelTaskLoop
-> mapped model-native intent to internal ActionEnvelope
-> attempted ProductActionKernel browser dispatch mission creation
-> blocked by operator control payload scan before material browser action
```

The first material browser action did not execute.

Observed exception:

```text
ValueError: mission_execution_request_parameters: unsafe operator payload
```

Call boundary:

```text
ModelLedProductActionKernelTaskLoop.run
-> _dispatch_product_action
-> MissionLifecycleService.create_mission
-> reject_operator_control_payload(parameters, context="mission_execution_request_parameters")
```

## Required Evidence

```text
provider_is_real = true
provider_decisions_model_native = true
fixture_backend = false
Playwright_fallback = false
selected_backend = cloak_browser
actual_backend = cloak_browser
root_lease_stable_across_child_actions = not_reached
browser_session_ref_count_inside_root = 0
child_receipt_ids_unique = not_reached
authority_expansion_count = 0
search_query_model_generated = true
hardcoded_query_override = false
safe_alternate_model_trajectory_allowed = true
typed_search_outcome_recorded = false
search_materiality_recorded = false
objective_relevance_assessed = false
unsupported_claims = 0
unknown_values_preserved = not_reached
raw DOM/cookies/session/provider reasoning persisted = 0
body_circuit_breaker_additional_provider_calls_after_body_failure = 0
browser_processes_after_mission = 0
live_contexts_after_mission = 0
profile_material_after_mission = 0
replay_side_effects = 0
```

## Body Verdict

```text
lifecycle = preflight_passed; mission_material_body_not_reached
session_reuse = not_reached
cleanup = passed
backend_truth = passed
```

Interpretation:

The live body was ready and selected correctly. The mission did not reach a material body action, so this run cannot prove root lease reuse inside the provider mission.

## Mind / Body Verdict

```text
model_strategy_accepted = false_at_parameter_scan_boundary
useful_action_ratio = 0
repeated_actions = 0
recovery_quality = not_reached
search_actuation = not_reached
evidence_quality = not_reached
```

Interpretation:

Do not blame browser actuation or Cloak lifecycle for this result. The failure occurred after the real model decision but before browser execution.

The actionable blocker is a product-spine parameter sanitation gap:

```text
safe model-native browser/search intent
-> internal search parameters
-> generic operator control scanner
-> unsafe payload block
```

This resembles prior “fake safety friction” findings, but it was not fixed in this tranche because the experiment contract forbids runtime changes after the single provider mission.

## Mission Verdict

```text
mission_status = blocked
blocked_before_material_browser_action = true
completion = no
truthful_partial = no
truthful_negative = no
```

The run is honest: no relevant result was claimed, no search success was invented, and no product/browser evidence was fabricated.

## Cleanup

```text
browser_processes_after_mission = 0
live_contexts_after_mission = 0
profile_material_after_mission = 0
raw provider output persisted = false
raw reasoning persisted = false
raw DOM persisted = false
cookies/session/profile material persisted = false
credential values persisted = false
```

## What This Proves

```text
real provider route starts successfully
model-native decision layer is reached
Cloak readiness gates provider use correctly
backend truth remains cloak_browser / cloak_browser
the product spine can block before material browser side effects
cleanup remains clean after the failed mission
```

## What This Does Not Prove

```text
root lease stability across child browser actions = not proven in provider mission
browser search actuation = not proven in provider mission
typed search outcome quality = not proven
objective relevance quality = not proven
useful final answer = not produced
```

## Next Recommended Fix

```text
FIX_MODEL_NATIVE_BROWSER_SEARCH_PARAMETER_SANITATION_AND_NEGATIVE_CONTROL_SCAN_V1
```

Goal:

```text
Preserve hard stops for real dangerous parameters, but prevent safe search/query text or negative boundary wording from becoming a terminal unsafe operator payload before browser dispatch.
```

Do not rerun a provider mission until that blocker is fixed locally and tested.
