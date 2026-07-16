# SENTINEL_REAL_MODEL_LIVE_CLOAK_PYTHON_ORG_V5_BODY_OUTAGE_MODEL_FEEDBACK_REPORT

## Verdict

```text
REAL_MODEL_LIVE_CLOAK_PYTHON_ORG_V5_BODY_OUTAGE_MODEL_FEEDBACK
= VALID_SUCCESS_GOLDEN_VERTICAL_SLICE_COMPLETED

provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
selected_backend = cloak_browser
actual_backend = cloak_browser
fixture_backend = false
Playwright_fallback = false
push = not performed
```

This was exactly one real-provider, real-Cloak, non-holdout Python.org mission after:

```text
fix_commit = bbb0e9b
fix_report_commit = 1252991
```

No runtime patch was made during or after the run.

## Frozen Mission

```text
objective = find grounded official Python documentation explaining pathlib Path.glob and provide a short useful answer
target = public non-holdout Python.org search path
allowed_domains = python.org
allowed_capabilities = real_browser_control, sentinel_loop
max_provider_decisions = 10
max_material_actions = 16
```

Raw URL, raw query, raw provider output, raw provider reasoning, raw DOM, cookies, session values, profile material, secrets and raw binary path are not persisted in this report.

## Run Identity

```text
run_id = python_org_v5_body_feedback_1784200065
result_safe = .live/scope/python_org_v5_body_feedback_1784200065/result_safe.json
analysis_safe = .live/scope/python_org_v5_body_feedback_1784200065/analysis_safe.json
safe_evidence_snapshot = .live/scope/e/python_org_v5_body_feedback_1784200065/safe_evidence_snapshot.json
```

## Metrics

```text
provider_decision_calls = 5
status = completed
final_reason = model_led_product_action_kernel_task_loop_finish
blocked_reason = none
mission_id_count = 4
product_receipt_count = 4
product_finalgate_count = 4
safe_evidence_event_count = 29
raw_material_persisted = false
safety_scan_hits = 0
```

## Model Action Sequence

```text
1. real_browser_control:real_browser.search
2. real_browser_control:real_browser.extract_evidence
3. real_browser_control:real_browser.verify_extraction
4. sentinel_loop:summarize_evidence
5. sentinel_loop:finish
```

The model used the product browser skill path and did not use raw Playwright/Cloak locator primitives.

## Search Materiality Proof

The real browser receipt for `real_browser.search` records:

```text
outcome_kind = MATERIAL_RESULTS
search_materially_successful = true
confidence = 0.92
input_written = true
submission_attempted = true
request_observed = true
navigation_or_state_changed = true
result_region_changed = true
query_reflected = true
before_result_region_count = 12
after_result_region_count = 14
pre_state_hash_present = true
post_state_hash_present = true
query_hash_present = true
```

This keeps the important V4 power proof and completes the mission without the V4 body-session terminal failure.

## Backend Truth

Real browser receipts showed:

```text
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
```

Observed browser receipt statuses:

```text
real_browser.search = completed
real_browser.extract_evidence = completed
real_browser.verify_extraction = passed
```

## Body Feedback Truth

The V4 blocker was:

```text
BODY_SESSION_UNAVAILABLE
```

V5 did not reproduce that blocker:

```text
runtime_failure_fact_count = 0
model_visible_body_failure_packet_count = 0
latest_model_assessment_present = false
```

Therefore this run proves the mission can complete without the body outage after the local fix, but it does not prove the post-failure model assessment path on a live failure. That remains a separate live failure-path proof.

## Replay And Cleanup

Replay summary:

```text
replay_no_react = true
```

The local replay helper produced a safe `ValidationError` payload while rendering the replay object:

```text
replay_error_class = ValidationError
raw_error_persisted = false
```

No re-execute, resend, rewrite or new receipt side effect was observed by the wrapper. This should be cleaned up as a replay-reporting schema issue, not a browser mission failure.

Cleanup evidence:

```text
cleanup_recorded = true
remaining_product_task_resource_scope_count = 0
```

The evidence sink also recorded a safe-hashed `runtime_host_shutdown` `AttributeError` after cleanup. The mission had already completed and cleanup was recorded, but the shutdown/reporting path should be tightened.

Important observability caveat:

```text
browser_lease_card is captured before resource_scope.close()
```

So the current cleanup event proves resource-scope cleanup was attempted and completed, but it does not independently prove post-close browser lease state. Future reports should capture a post-close lease card.

## Safety And Hygiene

```text
provider_native_tools = not used
fallback/AUTO = not used
Playwright fallback = not used
fixture backend = not used
authority_expansion = 0
raw provider output/reasoning persisted = 0
raw DOM/cookies/session/profile material persisted = 0
raw binary path persisted = 0
targeted safety scan hits = 0
```

## Capability Truth

```text
REAL_MODEL_PRODUCT_SPINE_PYTHON_ORG_GOLDEN_SLICE_T3 = PROVEN_ON_THIS_RUN
REAL_CLOAK_SEARCH_MATERIALITY_T3 = PROVEN_ON_THIS_RUN
GENERIC_EXTRACT_EVIDENCE_ROUTE_T3 = PROVEN_ON_THIS_RUN
VERIFY_EXTRACTION_TO_SUMMARY_TO_FINISH_T3 = PROVEN_ON_THIS_RUN
BODY_SESSION_UNAVAILABLE_MODEL_FEEDBACK_ON_LIVE_FAILURE = NOT EXERCISED
POST_CLOSE_CLEANUP_OBSERVABILITY = NEEDS IMPROVEMENT
REPLAY_RESULT_RENDERING_SCHEMA = NEEDS IMPROVEMENT
MULTI_SITE_GENERALIZATION = NOT PROVEN
FROZEN_HOLDOUT_GENERALIZATION = NOT PROVEN
```

## Remaining Work

Do not call the monster complete from this single run. The next serious moves are:

```text
1. Fix replay result rendering so replay proof serializes without ValidationError.
2. Capture post-close browser lease state after resource_scope.close().
3. Run repeated non-holdout Python.org missions only after those observability gaps are patched.
4. Then graduate to the broader non-holdout calibration suite.
5. Do not consume frozen holdout until non-holdout thresholds are stable.
```
