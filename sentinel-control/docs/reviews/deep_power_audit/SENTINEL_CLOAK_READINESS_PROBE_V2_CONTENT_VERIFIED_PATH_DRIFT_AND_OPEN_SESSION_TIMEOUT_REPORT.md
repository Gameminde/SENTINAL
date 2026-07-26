# SENTINEL_CLOAK_READINESS_PROBE_V2_CONTENT_VERIFIED_PATH_DRIFT_AND_OPEN_SESSION_TIMEOUT_REPORT

## Verdict

```text
GO_CLOAK_READINESS_PROBE_AUTHORIZATION_CONSUMED_BY_V1 = NO
GO_CLOAK_READINESS_PROBE_AUTHORIZATION_CONSUMED_BY_V2 = YES
CLOAK_READINESS_PROBE_LAUNCHED = YES
SQLITE_MISSION = NOT_RUN
SQLITE_RERUN_AUTHORIZED = NO
PROVIDER_CALLS = 0
PLAYWRIGHT_FALLBACK = NO
FIXTURE_BACKEND = NO
CLOAK_READINESS = NOT_READY
ROOT_CAUSE_PROVEN = NO
FIRST_FAILING_TRANSITION_PROVEN = YES
ACTIONABLE_BLOCKER = CLOAK_READINESS_GLOBAL_DEADLINE_STARVED_REOPEN
```

The path-hash mismatch was reclassified correctly:

```text
CLOAK_BINARY_PROVENANCE = CONTENT_VERIFIED_PATH_DRIFT
severity = WARNING
hard_block = NO
candidate_count = 1
file_sha256_match = true
version_match = true
path_hash_match = false
```

The probe launched through the Cloak readiness path after accepting the content-verified path drift. The first attempt used a parent containment guard that was too narrow to let Sentinel's internal readiness timeout publish its own cleanup event. The second attempt kept Sentinel's readiness timeout unchanged and only widened the parent process containment window so the internal timeout could report.

The initial Cloak session did become operational enough to open, observe twice, read safe DevTools metadata, and close. At this V2 evidence point, the first unreturned stage was `reopen_session`:

```text
last_confirmed_success = close_session.stage_returned
initial_open_session_returned = true
first_observe_returned = true
second_observe_returned = true
devtools_metadata_returned = true
close_session_returned = true
reopen_session_returned = false
first_failing_transition = reopen_session.stage_started_without_stage_returned_or_stage_failed_before_internal_readiness_timeout
failure_code = CLOAK_SESSION_READINESS_TIMEOUT
```

Later local repair evidence corrected the interpretation: the probe entered `reopen_session` only after the one-operation global watchdog budget had already been consumed by earlier successful stages. V2 therefore proves deadline starvation at the readiness-sequence boundary, not an intrinsic Cloak reopen hang.

## Probe Boundaries

```text
provider_calls = 0
SQLite mission dispatch = not_run
ProductActionKernel mission dispatch = not_run
Playwright fallback = no
fixture backend = no
blind identical retry = no
readiness timeout inflation = no
raw binary path persisted = false
```

The probe used one accepted content-verified Cloak candidate in process scope only. The raw binary path was not printed or persisted.

```text
attempts_authorized = 3
attempts_used = 2
third_attempt_used = false
third_attempt_reason = not_needed_after_first_failing_transition_proven
```

## Stage Timeline

Safe stage evidence shows:

| Stage | Event | Meaning |
| --- | --- | --- |
| configuration | stage_started / stage_returned | Cloak backend selection and bounded target configuration completed. |
| binary_resolution | stage_started / stage_returned | Local binary override/provenance checks completed. |
| engine_construction | stage_started / stage_returned | Runtime engine constructed with `actual_backend_id=cloak_browser` and `session_backend_kind=cloakbrowser`. |
| readiness_probe | stage_started | Probe entered live readiness sequence. |
| bind_authority | stage_started / stage_returned | Authority binding completed. |
| open_session | stage_started / stage_returned | Initial session open completed. |
| first_observe | stage_started / stage_returned | First safe observation completed. |
| second_observe | stage_started / stage_returned | Second safe observation completed. |
| devtools_metadata | stage_started / stage_returned | Safe DevTools metadata completed. |
| close_session | stage_started / stage_returned | Initial session close completed and profile count returned to zero. |
| reopen_session | stage_started only | First unreturned transition before the one-operation global watchdog fired. |
| readiness_probe | stage_failed | Internal readiness timeout fired while `reopen_session` was outstanding. |
| timeout_cleanup | stage_started / stage_returned | Timeout cleanup completed. |

No `reopen_session.stage_returned` or `reopen_session.stage_failed` was produced before the internal readiness timeout. This was later reclassified as sequence watchdog starvation because the reopen was started after prior successful stages had already exceeded the single-operation global watchdog.

## Cleanup

The parent process removed generated profile material from the probe capture directories after measurement.

```text
worker_terminated = true
post_probe_generated_profile_cleanup_attempted = true
post_probe_generated_profile_cleanup_removed = true
post_probe_generated_profile_file_count_before_cleanup = 145
post_probe_generated_profile_file_count_after_cleanup = 0
owned_process_count_after_probe = UNKNOWN_WITH_SAFE_COUNTER_ONLY
```

The remaining browser-like process count is recorded only as an informational host-wide counter. It is not treated as owned-process proof because command-line/raw path inspection was intentionally not persisted.

## Safe Artifacts

Safe probe summary:

```text
.armed_sqlite_xray/cloak_readiness_probes/cloak_readiness_probe_v2_20260726T110055Z/safe_probe_summary.json
```

Safe stage journal:

```text
.armed_sqlite_xray/cloak_readiness_probes/cloak_readiness_probe_v2_20260726T110055Z/attempt_1/readiness_stages.jsonl
```

The generated profile captures were removed after measurement.

## Implementation Delta

Files changed for this tranche:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_CLOAK_READINESS_PROBE_V1_PROVENANCE_BLOCK_REPORT.md
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_CLOAK_READINESS_PROBE_V2_CONTENT_VERIFIED_PATH_DRIFT_AND_OPEN_SESSION_TIMEOUT_REPORT.md
```

The runtime delta is limited to:

```text
parent-visible Cloak readiness stage journal
safe provenance classification helper
```

No browser cognition, search, SQLite mission behavior, provider behavior, timeout value, readiness bypass, fallback behavior, or ProductActionKernel mission route was modified.

## Tests

```text
test_cloak_binary_path_drift_is_warning_when_content_and_version_match = passed
test_cloak_binary_provenance_blocks_ambiguous_or_modified_candidates = passed
test_cloak_readiness_timeout_writes_parent_visible_stage_journal = passed
```

Adjacent focused checks were also rerun:

```text
readiness_gate_times_out_without_hanging_parent = passed
timeout_removes_sensitive_profile_dirs = passed
cloak_selected_actual_backend_receipt_matches_after_ready = passed
```

Final validation:

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q -k "cloak_binary_path_drift_is_warning or cloak_binary_provenance_blocks or parent_visible_stage_journal or readiness_gate_times_out_without_hanging_parent or timeout_removes_sensitive_profile_dirs or cloak_selected_actual_backend_receipt_matches_after_ready"
result = 6 passed

py -3.13 -m compileall -q sentinel/operator/real_browser_control_runtime.py tests/operator/test_power_pack6d_browser_skill_spine.py
result = passed

git diff --check
result = passed with CRLF normalization warnings only
```

Safe report/artifact scan:

```text
raw_windows_path = 0
api_key_like = 0
raw_cookie_assignment = 0
raw_dom_marker = 0
raw_binary_path_assignment = 0
remaining_generated_profile_file_count = 0
```

## Current Technical Truth

The exact internal root cause inside Cloak/session reopen is not proven by V2. The first unreturned transition is proven:

```text
BrowserSessionManagerRealBrowserEngine.open
-> BrowserSessionManager.open_session
-> initial open/observe/close succeeds
-> reopen_session starts
-> no return and no typed exception before internal readiness timeout
```

The next correction should not inflate timeout or bypass readiness. It should make the `open_session` reopen path internally observable and cancellable enough to classify whether the block is process launch, endpoint discovery, context creation, page creation, or stale post-close state.

Superseding local repair evidence:

```text
superseded_actionable_blocker = CLOAK_REOPEN_SESSION_HANG_AFTER_SUCCESSFUL_CLOSE
current_actionable_blocker = CLOAK_READINESS_GLOBAL_DEADLINE_STARVED_REOPEN
```
