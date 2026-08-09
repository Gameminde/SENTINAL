# SENTINEL_SINGLE_SPINE_C5A_TIMEOUT_CONTAINMENT_REPAIR_REPORT

## Verdict

```text
C5A_TIMEOUT_CONTAINMENT_REPAIR = IMPLEMENTED_LOCAL_WITH_LIVE_NEXT_BLOCKER
timeout_containment_race = REPAIRED_BY_OWNED_CHILD_PROCESS_BOUNDARY
live_cloak_ready = false
live_next_blocker = CLOAK_NEW_PROCESS_LAUNCH_TARGET_CLOSED
provider_calls = 0
SQLite mission = NOT_RUN
C5B = NOT_STARTED
Qwen = NOT_RUN
FIXED_PROVEN = 0/65
```

This tranche repairs the proven timeout-containment defect without promoting
Browser live power yet. The real readiness path now runs live Cloak startup
inside an owned child process boundary. On parent timeout, Sentinel kills and
reaps the owned process tree, blocks late publication by process death, attempts
profile cleanup before returning, and records only bounded status/hash/count
telemetry.

## What Changed

```text
live readiness parent
-> binary provenance already verified
-> owned child process
-> child performs Cloak/session/context/page readiness
-> parent owns timeout, kill, cleanup and terminal receipt
```

Added:

```text
_run_owned_process_with_wall_timeout
_terminate_owned_process_tree
_timeout_snapshot_from_stage_events
_cleanup_profile_material_with_status
_probe_cloak_readiness_in_owned_child_process
safe child process entrypoint
```

Extended `CloakSessionReadinessResult` with:

```text
timeout_worker_terminated
owned_process_tree_killed
late_publication_blocked
cleanup_completed_before_return
cleanup_failure_code
terminal_receipt_count
```

Also fixed one newly exposed observation issue: `BrowserSessionManagerL5Live`
now treats form-state capture as optional secondary telemetry. If form-state
inspection raises `FileNotFoundError` after a valid snapshot, the observation
receipt still persists with an empty form-state summary and a safe lifecycle
failure event. This fixes the first live repair probe divergence without
weakening receipt/finalgates.

## Deterministic Repair Proof

```text
initial_navigation blocked = covered
parent timeout = covered
late publication rejected = covered
child/grandchild killed = covered
cleanup failure visible = covered
terminal receipt unique = covered
no provider call = true
no browser mission = true
```

Key tests:

```text
test_cloak_readiness_owned_process_timeout_kills_tree_and_blocks_late_publication
test_cloak_readiness_timeout_reports_cleanup_failure_when_profile_material_survives
test_cloak_readiness_live_builder_uses_owned_process_boundary
test_live_browser_session_observe_preserves_snapshot_when_form_state_file_disappears
```

## Live Cloak Probe After Repair

Three bounded live readiness probes were executed after local repair. They used
the previously validated Cloak binary provenance and a public read-only
non-holdout target recorded only by safe origin hash. They did not use a
provider, SQLite, Playwright fallback or a fixture backend.

```text
candidate_count = 1
file_sha256_match = true
version = 146.0.7680.177.5
version_match = true
path_hash = f3fad5133de1a876082e5a7f6be7c61cf083e2a4742c4cf44fcfa6cfe34d3a2e
provider_calls = 0
SQLite = NOT_RUN
C5B = NOT_STARTED
```

Attempt results:

| Attempt | Result | First Failing Transition | Cleanup |
| --- | --- | --- | --- |
| 1 | `CLOAK_SESSION_BOOTSTRAP_NOT_READY` | `first_observe -> FileNotFoundError` | profile material removed |
| 2 | `CLOAK_SESSION_BOOTSTRAP_NOT_READY` | `cloak_open_context -> TargetClosedError` during `new_process_launch` | profile material removed |
| 3 | `CLOAK_SESSION_BOOTSTRAP_NOT_READY` | `cloak_open_context -> TargetClosedError` during `new_process_launch` | profile material removed |

Final live status:

```text
usable_context = NOT_PROVEN
usable_page = NOT_PROVEN
read_only_observation = NOT_PROVEN
profile_material_persisted = false
cleanup_operational = true on final attempt
timeout_reproduced_after_repair = false
next_stable_blocker = TargetClosedError during Cloak new_process_launch
```

## Still Visible Debt

```text
global ledger historical C4/C4S heads still reference d1408193 as historical artifact heads
C2 static probe remains PARTIAL/TIMEOUT in ast.generic_visit
Pack4 Browser regression remains TIMEOUT
Browser physical usable context/page = NOT_PROVEN
Browser live mission = NOT_RUN
```

These debts are not hidden and no finding is closed.

## Validation

```text
RED:
py -3.13 -m pytest test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_owned_process_timeout_kills_tree_and_blocks_late_publication test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_reports_cleanup_failure_when_profile_material_survives -q
-> 2 failed for missing owned process boundary / cleanup telemetry

GREEN:
py -3.13 -m pytest test_power_pack6d_browser_skill_spine.py -k "cloak or readiness or provenance" -q
-> 28/28 passed

py -3.13 -m pytest test_sentinel_single_spine_c5_physical_browser_boundary.py -q
-> 3/3 passed

py -3.13 -m pytest test_sentinel_single_spine_c4_browser_readonly_cutover.py -q
-> 6/6 passed

py -3.13 -m pytest test_browser_observe_receipt_proof_completeness.py -q
-> 1/1 passed

py -3.13 -m pytest test_browser_session_manager_l5_live.py::<form-state/reopen focused group> -q
-> 4/4 passed

py -3.13 -m pytest test_sentinel_dev_max_power_canonical_core_v1.py::test_stage0_finding_ledger_contains_all_65_findings -q
-> 1/1 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
-> passed

JSON/JSONL parse of ledger and C5A safe probe artifacts
-> json_ok=7, jsonl_ok=3

git diff --check
-> passed

targeted secret/path/raw-browser-material scan
-> passed; no key, raw local path, raw URL, cookie/session/profile material or raw provider output found

py -3.13 -m ruff check targeted changed files
-> unavailable in this Python environment: No module named ruff
```

## Next Correct Step

```text
C5A_CLOAK_NEW_PROCESS_LAUNCH_TARGET_CLOSED_ROOT_CAUSE
provider_calls = 0
SQLite = NOT_RUN
C5B = NOT_STARTED
```

Do not start C5B until real Cloak proves usable context, usable page, bounded
read-only observation and owned cleanup.
