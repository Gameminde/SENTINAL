# SENTINEL_REAL_MODEL_LIVE_CLOAK_PYTHON_ORG_V4_AFTER_BOUNDED_HOST_AUTHORITY_FIX_REPORT

## Verdict

```text
REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V4_AFTER_BOUNDED_HOST_AUTHORITY_FIX
= VALID_FAILED

primary_blocker = BODY_SESSION_UNAVAILABLE
important_power_proof = REAL_CLOAK_SEARCH_WRITE_READBACK_AND_SUBMISSION_MATERIALITY_PROVEN_IN_RUN
runtime_commit = a3b4f6e
push = not performed
```

This was a single bounded real-model mission after:

```text
implementation_commit = 8b8c1acd46e05eec25bfb127e5280086f5b4f56d
docs_commit = a3b4f6e
```

The run was not retried. The prior terminal interruption did not erase evidence because the crash-safe sink had already persisted the full safe run ledger.

## Frozen Mission

```text
target = public non-holdout Python.org search path
objective = find grounded official Python documentation explaining pathlib Path.glob and provide a short useful answer
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
backend = real Cloak/session
fixture_backend = false
Playwright fallback = false
max_model_calls = 10
max_material_actions = 16
allowed_capabilities = real_browser_control, sentinel_loop
allowed_domains = python.org
```

No raw URL, raw query, raw provider output, raw reasoning, raw DOM, cookies, session values, profile material, secrets or raw binary path are persisted in this report.

## Run Identity

```text
run_id = python_org_v4_after_host_fix_1784198788
safe_evidence_snapshot = .live/scope/e/python_org_v4_after_host_fix_1784198788/safe_evidence_snapshot.json
result_safe = .live/scope/python_org_v4_after_host_fix_1784198788/result_safe.json
```

## Metrics

```text
provider_decision_calls = 7
provider_is_real = true
model_native_path = true
fixture_backend = false
Playwright_fallback = false
selected_backend = cloak_browser
actual_backend = cloak_browser
product_receipt_count = 7
product_finalgate_count = 6
material_action_count = 6
mission_id_count = 7
replay_no_react = true
replay_artifact_hashes_stable = true
raw_material_persisted = false
raw_binary_path_persisted = false
terminal_status = blocked
terminal_blocked_reason = BODY_SESSION_UNAVAILABLE
```

## Model Action Sequence

```text
1. real_browser_control:real_browser.search
2. real_browser_control:real_browser.extract_evidence
3. real_browser_control:real_browser.search
4. real_browser_control:real_browser.extract_evidence
5. real_browser_control:real_browser.extract_evidence
6. real_browser_control:real_browser.extract_evidence
7. real_browser_control:real_browser.search
```

This proves the model stayed on browser product skills rather than raw Playwright/Cloak primitives.

## Power Proven By This Run

The previous blocker was:

```text
browser_session_domain_not_authorized
```

That blocker did not recur. The bounded parent-domain grant successfully allowed the exact bounded target host without widening to an unrelated domain.

The run produced material browser search evidence through the real Cloak backend:

```text
input_written = true
write_method = fill
write_readback_match = true
write_readback_status = matched_receipt_hash
submit_attempted = true
submit_mechanisms_observed = enter_key, search_button
request_observed = true
navigation_or_state_changed = true
result_region_changed = true
query_reflected = true
typed_search_outcome = MATERIAL_RESULTS
search_materially_successful = true
confidence = 0.92
```

This is the first useful evidence in this tranche that the Python.org search body can write, read back and submit materially through the product path with Cloak.

## Failure Truth

The run later failed on a new body lifecycle blocker:

```text
blocked_reason = BODY_SESSION_UNAVAILABLE
failure_code = real_browser_search_session_open_failed
failure_stage = session_lifecycle
material_effect_observed_on_failed_action = false
receipt_backed_after_product_dispatch = true
root_lease_present = true
root_lifecycle_state = active_after_recovery
root_open_count = 2
root_recovery_attempt_count = 1
global_context_lock_acquire_count = 2
cleanup_completed = true
remaining_product_task_resource_scope_count = 0
```

Interpretation:

```text
SEARCH_CONTROL_DISCOVERY = PROVEN_IN_RUN
SEARCH_WRITE_READBACK = PROVEN_IN_RUN
SEARCH_SUBMISSION_MATERIALITY = PROVEN_IN_RUN
ROOT_SESSION_CONTINUITY = PARTIAL
LONGER_MULTI_ACTION_CLOAK_SESSION_STABILITY = NOT PROVEN
GROUNDED_OBJECTIVE_COMPLETION = NOT PROVEN
```

The failure is not a topic-policing blocker, provider-routing blocker, Playwright fallback, or fixture shortcut. It is a real body/session lifecycle stability issue after multiple successful material browser actions.

## Mind/Body Feedback

The run created model-visible body failure evidence:

```text
runtime_failure_fact = authoritative
model_visible_body_failure_packet = created
typed_outcome.failure_class = RECOVERABLE_BROWSER_STATE_FAILURE
typed_outcome.failure_code = real_browser_search_session_open_failed
safe_current_page_state_summary = present
session_continuity = present
raw DOM/cookies/session material = not present
```

However the mission terminalized after this failure; no additional provider turn was used to obtain a final explicit model blocker assessment after the terminal failure.

```text
EXPLICIT_MODEL_BLOCKER_ASSESSMENT_AFTER_FINAL_BODY_FAILURE = NOT PROVEN
```

## Safety And Hygiene

```text
provider_native_tools = not used
fallback/AUTO = not used
Playwright fallback = not used
fixture backend = not used
login/payment/contact/upload/download = not used
authority_expansion = 0
raw provider output/reasoning persisted = 0
raw DOM/cookies/session/profile material persisted = 0
raw binary path persisted in result_safe = false
cleanup_completed = true
replay_side_effects = 0
```

## Next Fix

Do not rerun the provider immediately.

Next local tranche should target the newly exposed class:

```text
FIX_CLOAK_ROOT_SESSION_STABILITY_AFTER_MULTI_ACTION_RECOVERY_V1
```

Required focus:

```text
1. Diagnose why root lifecycle reached active_after_recovery after successful search/extract actions.
2. Determine why a later search returned BODY_SESSION_UNAVAILABLE despite root_lease_present = true.
3. Preserve root lease/engine/context identity across repeated search/extract actions.
4. Ensure recovery can rehydrate a usable page/session or return a model-continuable failure packet without terminalizing before one post-failure model assessment when budget remains.
5. Keep exact-host authority fix intact.
6. Keep search write/readback/materiality proofs intact.
```

No provider retry should happen until this lifecycle class has local and live-body proof.
