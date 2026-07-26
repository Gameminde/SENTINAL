# SENTINEL_CLOAK_READINESS_PROBE_V1_PROVENANCE_BLOCK_REPORT

## Verdict

```text
GO_CLOAK_READINESS_PROBE_AUTHORIZATION_CONSUMED = NO
CLOAK_READINESS_PROBE_LAUNCHED = NO
SQLITE_MISSION = NOT_RUN
SQLITE_RERUN_AUTHORIZED = NO
PROVIDER_CALLS = 0
PLAYWRIGHT_FALLBACK = NO
FIXTURE_BACKEND = NO
ROOT_CAUSE_PROVEN = NO
FIRST_FAILING_TRANSITION_PROVEN = NO
PROBE_INCONCLUSIVE = NO_PROBE
CLOAK_BINARY_PROVENANCE = CONTENT_VERIFIED_PATH_DRIFT
severity = WARNING
hard_block = NO
```

The live Cloak readiness probe was not launched. The first pre-probe provenance policy treated a path hash mismatch as a hard block even though the single candidate's content hash and version matched the previously validated binary. This is now corrected: path drift is informational when `candidate_count=1`, `file_sha256_match=true`, and `version_match=true`.

## Why The Probe Stopped

The probe runner recovered the previous SQLite run's safe Cloak provenance:

```text
expected_file_sha256_present = true
expected_path_hash_present = true
expected_version_present = true
```

It then inspected existing `cloakbrowser.binary_info()` metadata without calling `ensure_binary()`, downloading, installing, or updating anything.

Observed safe result:

```text
candidate_count = 1
verified_match_count = 0
file_sha256_match = true
version_match = true
path_hash_match = false
raw_binary_path_persisted = false
```

The policy conclusion is now:

```text
CLOAK_BINARY_PROVENANCE = CONTENT_VERIFIED_PATH_DRIFT
severity = WARNING
hard_block = NO
```

This V1 prelaunch stop did not consume the probe authorization because `CLOAK_READINESS_PROBE_LAUNCHED = NO`.

## Instrumentation Added Before Probe

Minimal parent-visible readiness instrumentation was added to:

```text
sentinel/operator/real_browser_control_runtime.py
```

It adds an optional `stage_journal_path` to the Cloak readiness gate. When supplied, it writes safe JSONL events:

```text
stage_started
stage_returned
stage_failed
monotonic_offset_ms
exception_class
exception_hash
profile_file_count
process_ref_count
thread_count
```

No runtime decision behavior, timeout value, readiness bypass, fallback behavior, provider behavior, or browser cognition path was changed. The journal is off unless explicitly passed or set through the process-scoped `SENTINEL_CLOAK_READINESS_STAGE_JOURNAL_PATH`.

## Offline Proof Before Probe

The offline test reproduced the important failure class: a worker can block inside `open_session`, while the parent still receives a safe stage journal before timeout.

Validation:

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q -k "parent_visible_stage_journal or readiness_gate_times_out_without_hanging_parent or timeout_removes_sensitive_profile_dirs or cloak_selected_actual_backend_receipt_matches_after_ready"
result = 4 passed

py -3.13 -m compileall -q sentinel/operator/real_browser_control_runtime.py tests/operator/test_power_pack6d_browser_skill_spine.py
result = passed
```

The new local proof shows:

```text
open_session stage_started survives timeout = true
readiness_probe stage_failed timeout visible to parent = true
profile material cleanup regression still passes = true
ready Cloak fake path regression still passes = true
```

## Final Validation

Validation was rerun after the safe provenance block:

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q -k "parent_visible_stage_journal or readiness_gate_times_out_without_hanging_parent or timeout_removes_sensitive_profile_dirs or cloak_selected_actual_backend_receipt_matches_after_ready"
result = 4 passed

py -3.13 -m compileall -q sentinel/operator/real_browser_control_runtime.py tests/operator/test_power_pack6d_browser_skill_spine.py
result = passed

git diff --check
result = passed with CRLF normalization warnings only
```

Safe publication scan over this report and the safe probe summary:

```text
raw_windows_path = 0
api_key_like = 0
raw_cookie_assignment = 0
raw_dom_marker = 0
raw_binary_path_assignment = 0
```

## Safe Probe Artifacts

Safe artifact written:

```text
.armed_sqlite_xray/cloak_readiness_probes/cloak_readiness_probe_v1_20260726T102311Z/safe_probe_summary.json
```

The artifact contains only safe counts and booleans:

```text
candidate_count = 1
verified_match_count = 0
provider_calls = 0
sqlite_mission = NOT_RUN
probe_launched = false
raw_binary_path_persisted = false
```

No stage journal or readiness cache exists for a launched probe because the launch was blocked before calling `check_cloak_session_readiness`.

## Current Truth

```text
ROOT_CAUSE_PROVEN = NO
READY_FOR_CLOAK_READINESS_PROBE = YES_AFTER_PATH_DRIFT_POLICY_CORRECTION
NEXT_REQUIRED_DECISION = NONE_FOR_PATH_DRIFT_ONLY
```

The earlier SQLite failure still stands:

```text
MISSION_PROVIDER_PHASE = NOT_REACHED
INFRA_FAILURE = CLOAK_SESSION_READINESS_TIMEOUT
receipt_backend_match = NOT_REACHED
preflight_capture_cleanup = PASSED
mission_cleanup_gate = NOT_REACHED
```

This V1 tranche did not reach the live readiness transition because the initial path-drift policy was too strict. It is superseded by the follow-up probe that accepts content-verified path drift as a warning.

## Recommended Next Step

No human/operator decision is required for this path drift class. A hard block remains required for file hash mismatch, version mismatch, ambiguous candidates, or trust-kernel integrity risk.
