# SENTINEL_FIX_CLOAK_SEARCH_WRITE_READBACK_AND_SUBMIT_MATERIALITY_V1_REPORT

## Verdict

```text
FIX_CLOAK_SEARCH_WRITE_READBACK_AND_SUBMIT_MATERIALITY_V1 = IMPLEMENTED
implementation_commit = b705b6bb97adc866cccb5d92ea4a20a733512d7c

T1_LOCAL_CANDIDATE = PASSED
T2_LIVE_BODY_SEARCH_PROVEN = PASSED
T3_REAL_MODEL_SEARCH_PRODUCT_PROVEN = PASSED_ON_SINGLE_FULL_MISSION
T3_REPEATED_RELIABILITY = NOT_PROVEN
T4_HOLDOUT_GENERALIZATION = NOT_RUN
```

This tranche fixes the original search materiality gap: input write, safe readback, Enter submit, observed request/navigation/result-region progress, typed search outcome, and replay no-react are now proven on the real Cloak body and on one complete real-model Python.org mission.

Do not overclaim. The repeated reliability target is still open because a later real-model run exposed an intermittent or context-specific `real_browser_action_start_exception` at `dispatch_preparation` before actuation.

## Scope

Objective:

```text
Fix Cloak search write/readback and submit materiality without patching Python.org selectors.
```

Rules preserved:

```text
no Playwright fallback
no fixture backend for live proof
no frozen holdout
no raw query / raw URL / selector / DOM / cookies / session / provider reasoning persistence
model remains strategy owner
Sentinel handles body mechanics, evidence, authority, receipts and replay
```

## Files Changed

```text
sentinel/operator/store.py
sentinel/operator/authority_issuer.py
sentinel/operator/mission_lifecycle_service.py
sentinel/operator/runtime_host.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/real_browser_control_runtime.py
sentinel/agent/organs/browser_session_manager_l5_live.py
tests/operator/test_authority_issuer.py
tests/operator/test_mission_lifecycle_service.py
tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py
tests/operator/test_power_pack6d_browser_skill_spine.py
tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
tests/test_browser_session_manager_l5_live.py
```

## Implementation Summary

Search actuation:

```text
fresh semantic control ref
-> focus
-> clear/write
-> safe readback hash or typed receipt proof
-> observed submit affordance
-> Enter submit
-> observe recovery if post-submit snapshot fails after materialization
-> typed materiality outcome
```

Key changes:

```text
BrowserSessionManagerL5Live:
  Enter fallback uses page.keyboard.press("Enter") when a text/search/combo locator detaches.

RealBrowserControlRuntime:
  SearchActuationTrace records submit/readback evidence.
  Post-Enter snapshot failure can recover via observe-before-resubmit.
  Search success requires materiality evidence, not fill-only success.

MissionLifecycleService:
  raw browser query is in-memory only.
  persisted execution parameters contain only hash/redacted query evidence.

RuntimeHost:
  browser authority carries the internal bounded URL authority ref when allowed domains exist.

ProductActionKernelTaskLoop replay/store:
  uses store filesystem helpers for Windows long/stale path resilience.
```

## Local Validation

Fresh validation before implementation commit:

```text
py -3.13 -m pytest tests/test_browser_session_manager_l5_live.py -q
15 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
106 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
4 passed

py -3.13 -m pytest tests/operator/test_authority_issuer.py -q
11 passed

py -3.13 -m pytest tests/operator/test_mission_lifecycle_service.py -q
10 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
29 passed

py -3.13 -m pytest tests/operator/test_browser_search_actuation_open_world_feedback.py -q
4 passed

py -3.13 -m compileall -q sentinel/operator/store.py sentinel/operator/authority_issuer.py sentinel/operator/mission_lifecycle_service.py sentinel/operator/runtime_host.py sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel/operator/real_browser_control_runtime.py sentinel/agent/organs/browser_session_manager_l5_live.py
passed

git diff --check
passed with CRLF warnings only
```

Targeted scan over touched files/tests found only benign existing guard/test/env-name strings, and no secret values, raw provider output, raw DOM, cookies, session material or credential values.

## T2 Live Body Proof

Artifact:

```text
sentinel-control/services/sentinel-core/tmp/fix_cloak_search_write_readback_materiality/body_t2_rerun9_result_safe_reconciled.json
```

Safe result:

```text
verdict = T2_LIVE_BODY_SEARCH_PROVEN
provider_calls = 0
fixture_backend = false
playwright_fallback = false
frozen_holdout = false
browser_receipt_count = 3
search_receipt_count = 1
input_written = true
submission_attempted = true
request_observed = true
navigation_or_state_changed = true
result_region_changed = true
search_materially_successful = true
typed_search_outcome = MATERIAL_RESULTS
write_readback_status = matched_receipt_hash
write_readback_alternative_proof = l5_typed_text_receipt_hash
submit_method_selected = enter_key
submit_observe_recovery_attempted = true
submit_observe_recovery_succeeded = true
raw_query_artifact_hits = 0
```

This graduates the body mechanics from local deterministic proof to real Cloak body proof.

## T3 Real Model Missions

### Mission 1

Artifact root:

```text
sentinel-control/services/sentinel-core/tmp/fix_cloak_search_write_readback_materiality/t3_python_org_mission_1_1784193077
```

Split result:

```text
provider_decision_calls = 7
real_browser.search = emitted
search input/write/submit/materiality = proven in receipt
extract_evidence = emitted
verify_extraction = emitted
mission_status = blocked
blocked_reason = recipient_not_allowed
replay_no_react = true
```

Interpretation:

```text
T3_SEARCH_ACTUATION_MATERIALITY = PROVEN_ON_MISSION_1
T3_GROUNDED_OBJECTIVE_COMPLETION = FAILED_MISSION_1_RECIPIENT_NOT_ALLOWED
```

This run proved the browser body path but exposed model-surface drift into `bounded_channel.send_message` inside a browser-only proof mission.

### Mission 2

Artifact:

```text
sentinel-control/services/sentinel-core/tmp/fix_cloak_search_write_readback_materiality/t3_python_org_mission_2_1784193574/t3_result_safe.json
```

Result:

```text
terminal_verdict = T3_REAL_MODEL_SEARCH_PRODUCT_PROVEN_MISSION_SUCCESS
provider_is_real = true
provider_decision_calls = 6
status = completed
final_reason = model_led_product_action_kernel_task_loop_finish
fixture_backend = false
playwright_fallback = false
selected_backend = cloak_browser
actual_backend = cloak_browser
backend_mismatch = false
browser_receipt_count = 4
search_receipt_count = 1
product_receipt_count = 5
material_action_count = 5
finalgate_count = 10
replay_no_react = true
raw_query_persisted = false
```

Action sequence:

```text
real_browser.search
-> real_browser.extract_evidence
-> real_browser.extract_evidence
-> real_browser.verify_extraction
-> sentinel_loop.summarize_evidence
-> sentinel_loop.finish
```

Search proof:

```text
input_written = true
submit_attempted = true
request_progress = observed
navigation_progress = changed
result_region_progress = changed
typed_search_outcome = MATERIAL_RESULTS
write_readback_status = matched_receipt_hash
write_readback_alternative_proof = l5_typed_text_receipt_hash
```

This is the first complete T3 proof for this fix: real provider, model-native browser skill, ProductActionKernel, real Cloak, search materiality, extraction, verification, summary, finish, FinalGate and replay no-react.

### Mission 3

Artifact root:

```text
sentinel-control/services/sentinel-core/tmp/fix_cloak_search_write_readback_materiality/t3_python_org_mission_3_1784194424
```

Safe evidence sink survived a runner summary crash and recorded:

```text
provider_decision_count = 1
action_sequence = real_browser_control.real_browser.search
cleanup_recorded = true
terminal_verdict = blocked
raw_material_persisted = false
```

Dispatch closeout:

```text
blocked_reason = real_browser_action_start_exception
failure_stage = dispatch_preparation
resource_kind = browser_runtime_dispatch
exception_class = RealBrowserControlRuntimeError
material_effect_observed = false
root_lease_present = true
root_lease_lifecycle_state = active at failure
global_context_lock_acquired = true at failure
cleanup_completed = true
root lease lifecycle_state = closed after cleanup
global_context_lock_acquired = false after cleanup
```

Interpretation:

```text
T3_REPEATED_RELIABILITY = NOT_PROVEN
new blocker = REAL_BROWSER_RUNTIME_EXCEPTION_ESCAPES_AS_ACTION_START_EXCEPTION
secondary = DISPATCH_PREPARATION_STAGE_TOO_COARSE_FOR_RUNTIME_EXECUTE_ERRORS
```

The failure is not evidence that write/readback or submit materiality failed. The action did not reach that stage. It is evidence that an exception from `RealBrowserControlRuntime.execute(...)` can still escape as a top-level action-start block instead of a stage-specific browser recovery/failure packet that the model can reason over during the same mission.

## Safety And Persistence

Observed safety properties:

```text
raw provider reasoning persisted = no
raw DOM persisted = no
raw screenshots persisted = no
cookies/session/profile material persisted = no
raw Cloak binary path persisted in reports = no
raw browser query persisted in mission execution parameters = no
Playwright fallback = no
fixture backend in live missions = no
replay side effects on successful mission = no
```

Note: during interactive debugging, an unsafe local diagnostic print exposed raw Cloak metadata in terminal output. It was not written into this report or committed artifacts. Future runner diagnostics must sanitize all Cloak metadata keys, including `binary_path` and `cache_dir`, not only `path`.

## Capability Truth

```text
CLOAK_SEARCH_WRITE_READBACK = PROVEN_T2_AND_T3_SINGLE_SUCCESS
SEARCH_SUBMISSION_MATERIALITY = PROVEN_T2_AND_T3_SINGLE_SUCCESS
REAL_MODEL_BROWSER_SEARCH_COMPLETION = PROVEN_ON_ONE_FULL_NON_HOLDOUT_MISSION
REPEATED_REAL_MODEL_BROWSER_SEARCH_RELIABILITY = NOT_PROVEN
MULTI_SITE_GENERALIZATION = NOT_PROVEN
FROZEN_HOLDOUT_GENERALIZATION = NOT_RUN
```

## Remaining Blockers

P0:

```text
REAL_BROWSER_RUNTIME_EXCEPTION_ESCAPES_AS_ACTION_START_EXCEPTION
```

Observed effect:

```text
RealBrowserControlRuntime.execute(...) can raise RealBrowserControlRuntimeError.
RuntimeHost catches it around dispatch and records real_browser_action_start_exception.
The failure stage remains dispatch_preparation even though the root lease is active.
This loses the precise browser operation stage needed for model-visible recovery.
```

Required next fix:

```text
FIX_BROWSER_RUNTIME_EXCEPTION_TO_STAGE_SPECIFIC_RECOVERABLE_BODY_FACT_V1
```

Acceptance for the next fix:

```text
RealBrowserControlRuntimeError during observe/search/write/submit/extract/verify becomes:
  runtime_failure_fact with precise browser stage
  model_visible_body_failure_packet
  typed recoverability
  no raw exception text
  no raw DOM/query/session material

The loop must allow one normal next model turn when the failure is recoverable and material effect is false.
True authority/secret/credential/payment/login/contact/fallback/provider-native hard boundaries remain hard stops.
```

P1:

```text
MODEL_SKILL_SURFACE_DRIFT_TO_NON_BROWSER_ACTIONS
```

Mission 1 showed the model can attempt `bounded_channel.send_message` after browser evidence in a browser-only proof. It was correctly blocked by authority, but browser-only mission skill filtering should be sharper so non-browser skills do not appear as attractive completion paths.

## Next Recommended Proof

After the P0 fix:

```text
REAL_MODEL_PYTHON_ORG_SEARCH_MATERIALITY_REPEAT_V4
```

Run conditions:

```text
same non-holdout Python.org objective
real provider/model
real Cloak
no fixture
no Playwright fallback
no frozen holdout
3 successful repeated missions required before reliability claim
```

The next proof should count mission 2 as a prior successful data point but must not claim repeated reliability until the dispatch-preparation escape is fixed and repeated runs pass.
