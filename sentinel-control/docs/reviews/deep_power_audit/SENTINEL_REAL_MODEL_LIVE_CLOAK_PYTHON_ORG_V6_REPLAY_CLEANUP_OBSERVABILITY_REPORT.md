# SENTINEL_REAL_MODEL_LIVE_CLOAK_PYTHON_ORG_V6_REPLAY_CLEANUP_OBSERVABILITY_REPORT

## Verdict

```text
REAL_MODEL_LIVE_CLOAK_PYTHON_ORG_V6_REPLAY_CLEANUP_OBSERVABILITY
= VALID_SUCCESS_REPLAY_AND_POST_CLOSE_OBSERVABILITY_PROVEN

provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
selected_backend = cloak_browser
actual_backend = cloak_browser
fixture_backend = false
Playwright_fallback = false
push = not performed
```

This was one bounded real-provider, real-Cloak, public non-holdout Python.org mission after:

```text
observability_fix_commit = 42843c8
```

No runtime patch was made during or after the run.

## Mission

```text
objective = find grounded official Python documentation explaining pathlib Path.glob and provide a short useful answer
allowed_domains = python.org
allowed_capabilities = real_browser_control, sentinel_loop
max_provider_decisions = 10
max_material_actions = 16
```

Raw URL, raw query, raw provider output, raw reasoning, raw DOM, cookies, session values, profile material, secrets and raw binary path are not persisted in this report.

## Run Identity

```text
run_id = python_org_v6_replay_cleanup_1784200920
result_safe = .live/scope/python_org_v6_replay_cleanup_1784200920/result_safe.json
safe_evidence_snapshot = .live/scope/e/python_org_v6_replay_cleanup_1784200920/safe_evidence_snapshot.json
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
safe_evidence_event_count = 28
safety_scan_hits = 0
raw_material_persisted = false
```

## Model Action Sequence

```text
1. real_browser_control:real_browser.search
2. real_browser_control:real_browser.extract_evidence
3. real_browser_control:real_browser.verify_extraction
4. sentinel_loop:summarize_evidence
5. sentinel_loop:finish
```

## Search Materiality

The real Cloak search receipt recorded:

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
pre_state_hash_present = true
post_state_hash_present = true
query_hash_present = true
```

## Replay Proof

The replay proof now serializes through:

```text
ProductActionKernelTaskLoopReplay.from_host(...)
ProductActionKernelTaskLoopReplay.safe_model_dump()
```

Live result:

```text
replay_no_react = true
reexecuted_actions = false
model_calls_delta = 0
product_dispatch_delta = 0
receipt_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
```

The previous live reporting `ValidationError` did not recur.

## Cleanup Proof

The cleanup event now records the browser lease card after `resource_scope.close()`:

```text
cleanup_recorded = true
cleanup_completed = true
remaining_product_task_resource_scope_count = 0
cleanup_post_close_proven = true
cleanup_lease_lifecycle_state = closed
cleanup_lease_close_count = 1
cleanup_lease_global_context_lock_acquired = false
```

The previous pre-close `active` cleanup card did not recur.

## Body Feedback Truth

No recoverable browser body failure occurred in this run:

```text
runtime_failure_fact_count = 0
model_visible_body_failure_packet_count = 0
latest_model_assessment_present = false
```

So V6 proves the stable successful path and observability fixes. It still does not exercise model diagnosis after a live body failure.

## Safety And Hygiene

```text
provider_native_tools = not used
fallback/AUTO = not used
fixture backend = not used
Playwright fallback = not used
authority_expansion = 0
raw provider/reasoning persisted = 0
raw DOM/cookies/session/profile material persisted = 0
raw binary path persisted = 0
targeted safety scan hits = 0
```

## Capability Truth

```text
REAL_MODEL_PRODUCT_SPINE_PYTHON_ORG_GOLDEN_SLICE_T3 = REPROVEN
REAL_CLOAK_SEARCH_MATERIALITY_T3 = REPROVEN
REPLAY_REPORTING_JSON_SAFE_LIVE = PROVEN
POST_CLOSE_CLEANUP_LEASE_CARD_LIVE = PROVEN
BODY_SESSION_UNAVAILABLE_MODEL_FEEDBACK_ON_LIVE_FAILURE = NOT EXERCISED
MULTI_SITE_GENERALIZATION = NOT PROVEN
FROZEN_HOLDOUT_GENERALIZATION = NOT PROVEN
```

## Next

The next evidence step should not be another Python.org one-off unless the goal is reliability measurement. The correct graduation path is:

```text
1. Run repeated non-holdout Python.org golden missions for success-rate variance.
2. Then run the broader non-holdout multi-site calibration suite.
3. Only after thresholds pass, consume the frozen holdout once.
```
