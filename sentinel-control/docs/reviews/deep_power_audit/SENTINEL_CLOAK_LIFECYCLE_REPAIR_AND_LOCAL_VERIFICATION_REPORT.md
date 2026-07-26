# SENTINEL_CLOAK_LIFECYCLE_REPAIR_AND_LOCAL_VERIFICATION_REPORT

## Verdict

```text
CLOAK_LIFECYCLE_REPAIR_AND_LOCAL_VERIFICATION = VALID_SUCCESS_LOCAL_AND_LIVE_BODY_PROBE
ROOT_CAUSE_PROVEN = YES
ROOT_CAUSE = CLOAK_READINESS_GLOBAL_DEADLINE_STARVED_REOPEN
CLOAK_READINESS = READY
SQLITE = NOT_RUN
SQLITE_RERUN_AUTHORIZED = NO
PROVIDER_CALLS = 0
PLAYWRIGHT_FALLBACK = NO
FIXTURE_BACKEND_FOR_LIVE_PROBE = NO
```

This tranche did not rerun SQLite and did not consume a provider call. It repaired the local Cloak lifecycle/readiness path and then ran one local live Cloak readiness probe with the previously validated binary candidate restored only in the probe process.

## Root Cause

The earlier V2 probe showed:

```text
initial open/observe/close = PASSED
sequential reopen_session = first unreturned stage
```

The repair investigation proved the sharper cause:

```text
first failing boundary = readiness sequence watchdog
old behavior = whole readiness sequence used one browser-operation timeout
effect = reopen_session was entered after prior successful stages had already consumed the global watchdog
```

The stale/post-close state found locally was:

```text
BrowserSessionManagerL5Live.close_session closed the live context but did not remove profile material.
BrowserSessionManagerL5Live.open_session failure could leave a newly created profile directory behind.
close_all also closed sessions without releasing profile material.
```

The readiness journal also showed that host process counting was safe but too expensive when sampled at every stage. It could distort timing during instrumentation. That counter is now cached for the readiness sequence instead of becoming a blocking signal.

## Correctif Applique

Files changed:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_session_manager_l5_live.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/cloak_backend.py
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py
sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py
```

Implementation changes:

```text
per-operation timeout remains unchanged
readiness watchdog is now sequence-scoped, capped, and not a one-operation budget
readiness now proves reopen -> observe -> close, not only reopen returns
BrowserSessionManagerL5Live removes profile material on close_session, close_all, and open_session failure
safe lifecycle event sink exposes manager/backend substages without raw paths
Cloak backend emits safe lifecycle substages for profile creation, process launch, context creation, page creation, and navigation
browser-like process count telemetry is cached so instrumentation does not consume the probe budget
```

No timeout bypass, readiness bypass, Playwright fallback, provider path, SQLite mission path, or browser cognition behavior was introduced.

## Live Cloak Probe

Safe artifact:

```text
.armed_sqlite_xray/cloak_readiness_probes/cloak_lifecycle_repair_probe_20260726T113853Z/safe_probe_summary.json
.armed_sqlite_xray/cloak_readiness_probes/cloak_lifecycle_repair_probe_20260726T114433Z/safe_probe_summary.json
```

Safe result:

```text
terminal_status = CLOAK_READINESS_READY
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
profile_material_persisted = false
backend_identity_matched = true
process_operational = true
context_operational = true
page_operational = true
devtools_operational = true
multi_action_reuse_operational = true
reopen_operational = true
```

Binary provenance:

```text
candidate_count = 1
file_sha256_match = true
version_match = true
path_hash_match = true
provenance = VALIDATED
hard_block = false
ensure_binary_called = false
raw_binary_path_persisted = false
```

## Sequential Reopen Evidence

Safe stage journals:

```text
.armed_sqlite_xray/cloak_readiness_probes/cloak_lifecycle_repair_probe_20260726T113853Z/readiness_stages.jsonl
.armed_sqlite_xray/cloak_readiness_probes/cloak_lifecycle_repair_probe_20260726T114433Z/readiness_stages.jsonl
```

Observed transition:

```text
open_session.stage_returned
first_observe.stage_returned
second_observe.stage_returned
devtools_metadata.stage_returned
close_session.stage_returned
profile_lease_release.profile_material_count = 0
post_close_state_reset.live_session_count = 0
reopen_session.stage_returned
reopened_observe.stage_returned
reopened_close_session.stage_returned
profile_lease_release.profile_material_count = 0
readiness_probe.stage_returned
```

The complete live readiness sequence returned in the same probe process without provider usage.

The final post-cleanup-fix proof is `cloak_lifecycle_repair_probe_20260726T114433Z`; it returned `CLOAK_READINESS_READY` after the partial-context cleanup fix was added and is the canonical final probe for this tranche.

## Cleanup Result

```text
generated_profile_material_after_probe = 0
owned_process_count_after_probe = 0
global_browser_like_process_count = informational_only
```

The owned-process check counted only processes whose command line referenced the probe capture root, without printing or persisting the raw path.

## Tests

Red/green proof added:

```text
test_cloak_readiness_default_watchdog_does_not_starve_sequential_reopen
test_cloak_readiness_reopens_observes_and_closes_reopened_session
test_live_browser_session_sequential_reopen_cycles_cleanup_profile_material
test_live_browser_session_reopen_failure_cleans_profile_and_next_open_is_clean
test_live_browser_session_lifecycle_sink_records_safe_open_close_substages
test_cloakbrowser_backend_closes_partial_context_when_page_creation_fails
```

Validation run:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_live_browser_session_lifecycle_sink_records_safe_open_close_substages sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_live_browser_session_sequential_reopen_cycles_cleanup_profile_material sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_live_browser_session_reopen_failure_cleans_profile_and_next_open_is_clean sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_closes_partial_context_when_page_creation_fails -q
result = passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result = passed

git diff --check
result = passed with CRLF normalization warnings only
```

The full `test_browser_session_manager_l5_live.py` file was also attempted. It still contains Playwright compatibility tests that fail in this environment because the Playwright backend cannot open here. Those failures are not used as Cloak product proof and were not introduced by this Cloak-first lifecycle fix.

## Remaining Boundaries

```text
provider_calls = 0
SQLite mission = NOT_RUN
SQLite live authorization remains consumed
no real provider mission authorized by this tranche
no Playwright fallback
no raw binary path, raw DOM, screenshot, cookie, session/profile material, or provider reasoning persisted
```

Next step, only after explicit authorization, is to decide whether to re-arm a new mission or run a narrower browser-body regression. The old SQLite live authorization remains consumed and was not reused here.
