# SENTINEL_SINGLE_SPINE_C5A_PHYSICAL_BROWSER_BOUNDARY_REPORT

## C5A Repair Update

```text
latest_repair_tranche = C5A_CLOAK_NEW_PROCESS_LAUNCH_TARGET_CLOSED_ROOT_CAUSE
timeout_containment_race = REPAIRED_LOCAL_DETERMINISTIC
prior_live_blocker_after_repair = CLOAK_NEW_PROCESS_LAUNCH_TARGET_CLOSED
prior_live_blocker_after_instrumentation = NOT_REPRODUCED
live_cloak_ready_after_target_closed_wave = true
live_cloak_readiness_probes_after_target_closed_wave = 3
provider_calls = 0
SQLite mission = NOT_RUN
C5B = NOT_STARTED
FIXED_PROVEN = 0/65
```

The earlier readiness timeout root cause remains valid history. The latest
code no longer runs the live readiness path in an uncancellable daemon thread:
the live path now uses an owned child process boundary and deterministic tests
prove timeout kill/reap, late-publication blocking, cleanup completion before
return, visible cleanup failure and one terminal timeout receipt.

After this repair, a follow-up TargetClosed root-cause wave added
stage-specific launch telemetry and reran three bounded live Cloak readiness
probes against a public read-only non-SQLite target. The prior
`TargetClosedError` symptom did not reproduce on the final instrumented code:
all three probes reached usable context, usable page, bounded read-only
observation, reopen and cleanup. No provider, SQLite mission, fixture backend
or Playwright fallback was used.

Detailed repair report:

```text
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_SINGLE_SPINE_C5A_TIMEOUT_CONTAINMENT_REPAIR_REPORT.md
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_SINGLE_SPINE_C5A_TARGET_CLOSED_ROOT_CAUSE_REPORT.md
```

## Verdict

```text
C5A = PHYSICAL_BROWSER_BOUNDARY_ADAPTER_LOCAL_DETERMINISTIC_PLUS_LIVE_READINESS_BLOCKER
FIXED_PROVEN = 0/65
provider_calls = 0
live_cloak_readiness_probes = 3
live_cloak_ready = true
browser_runs = 0 product browser missions
scripted_physical_backend_actions = 3
real Cloak readiness probe = READY_3_OF_3_CONTEXT_PAGE_OBSERVE_CLEANUP
SQLite mission = NOT_RUN
root_cause_probe = ROOT_CAUSE_PROVEN_TIMEOUT_CONTAINMENT_RACE
target_closed_followup = PRIOR_TARGET_CLOSED_NOT_REPRODUCED_AFTER_INSTRUMENTED_FINAL_CODE
```

This tranche does not claim live Browser/Cloak mission power. It proves the
canonical single spine can route a Browser read-only physical backend through
the existing `RealBrowserControlRuntime` and `ProductActionKernel` without
creating another cognitive loop. The latest follow-up readiness probes prove
the physical Cloak body can create a usable context/page and perform a bounded
read-only observation under the readiness harness. C5B is still unstarted, so
this is not yet a real provider Browser mission claim.

## Architecture After C5A

```text
public canonical product/dev request
-> RuntimeHost hosting/lifecycle
-> RootMissionRuntime single cognition/root state owner
-> CanonicalDecision + DecisionOrigin
-> CanonicalState with BrowserEnvironmentState
-> ExecutableCapabilityGraph
-> RootMissionRuntime authority check
-> ProductActionKernel.execute_typed
-> CanonicalBrowserReadOnlyAdapter
-> PhysicalBrowserReadOnlyBackend
-> RealBrowserControlRuntime
-> physical-style Cloak engine contract
-> real_browser_control terminal receipts
-> canonical receipt linked to root MissionRecord
-> MissionProofRoot
-> cleanup
```

`ActionEnvelope` remains internal to `ProductActionKernel.execute_typed`; it is
not exposed to the public canonical route or the model.

## What Changed

- Added `PhysicalBrowserReadOnlyBackend` as a Browser read-only backend adapter
  that delegates to `RealBrowserControlRuntime`.
- Kept `FakeBrowserReadOnlyBackend` for deterministic C4 tests and prevented it
  from certifying material browser proof.
- Transported the typed mission authority envelope into the kernel execution
  context for Browser physical dispatch.
- Extended canonical authority actions with route operations such as
  `real_browser.open`, `real_browser.observe`, and
  `real_browser.extract_evidence`.
- Added the bounded Browser domain authority ref required by the physical
  Browser runtime.
- Projected real Browser runtime state back into the compact canonical
  `BrowserEnvironmentState` shape consumed by `CanonicalState`.

## Gates

| Gate | Value |
| --- | --- |
| `single_cognition_loop` | `RootMissionRuntime` |
| `effect_dispatch_owner` | `ProductActionKernel` |
| `physical_backend_delegates_to_real_browser_runtime` | `true` |
| `legacy_action_envelope_on_public_route` | `0` |
| `provider_calls` | `0` |
| `live_cloak_readiness_probes` | `3` |
| `live_cloak_ready` | `true` |
| `live_cloak_failure_code` | `null` |
| `prior_timeout_active_stage` | `initial_navigation` |
| `prior_timeout_open_stage_count` | `3` |
| `target_closed_reproduced_after_instrumentation` | `false` |
| `context_operational_after_target_closed_wave` | `true` |
| `page_operational_after_target_closed_wave` | `true` |
| `read_only_observation_after_target_closed_wave` | `true` |
| `cleanup_after_target_closed_wave` | `true` |
| `profile_material_persisted_after_target_closed_wave` | `false` |
| `scripted_physical_backend_actions` | `3` |
| `authority_denial_before_engine_call` | `true` |
| `bounded_domain_authority_ref_present` | `true` |
| `selected_backend_id` | `cloak_browser` |
| `actual_backend_id` | `cloak_browser` |
| `session_backend_kind` | `cloakbrowser` |
| `fixture_backend` | `false` |
| `Playwright_fallback_selected` | `false` |
| `SQLite_mission_reached` | `false` |
| `real_browser_terminal_receipt_written` | `true` |
| `canonical_receipt_linked_to_root_mission_record` | `true` |
| `proof_root_receipt_artifacts_verified` | `true` |
| `canonical_state_browser_backend_visible_next_turn` | `true` |
| `fake_material_success_on_physical_route` | `0` |
| `cancellation_after_dispatch_blocks_completion` | `true` |
| `cleanup_after_completion_denial_cancellation` | `true` |
| `raw_dom_exposed` | `false` |
| `cookies_exposed` | `false` |
| `tokens_exposed` | `false` |
| `raw_provider_output_persisted` | `false` |

## Validation Results

| Name | Status | Result |
| --- | --- | --- |
| `C5A physical browser boundary` | `PASSED` | `3/3 passed` |
| `C4 + C5A browser cutover group` | `PASSED` | `9/9 passed` |
| `C4 + C5A + observe receipt proof` | `PASSED` | `10/10 passed` |
| `C5A target-closed launch telemetry focused group` | `PASSED` | `4/4 passed` |
| `C5A readiness truth focused group` | `PASSED` | `3/3 passed` |
| `C5A target-closed follow-up readiness artifacts` | `PASSED` | `3/3 ready; json_ok=8; jsonl_ok=3` |
| `compileall sentinel` | `PASSED` | `exit 0` |
| `canonical core C2/C3/C4 probe group` | `PARTIAL` | `test_sentinel_dev_max_power_canonical_core_v1.py = 44/44 passed; test_sentinel_single_spine_c1_executable_mapping.py timed out at test_c2_workspace_compression_artifacts_match_current_source` |
| `pack4 Browser product-spine regression` | `TIMEOUT` | `31 tests collected; full file timed out before completion` |

Commands executed:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c4_browser_readonly_cutover.py sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c4_browser_readonly_cutover.py sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py sentinel-control/services/sentinel-core/tests/operator/test_browser_observe_receipt_proof_completeness.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c1_executable_mapping.py::test_c2_workspace_compression_artifacts_match_current_source -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_records_launch_failure_on_new_process_stage sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_is_primary_and_uses_persistent_context sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_closes_partial_context_when_page_creation_fails sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_live_browser_session_lifecycle_sink_records_safe_open_close_substages -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_gate_blocks_before_provider_when_bootstrap_missing sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_owned_process_timeout_kills_tree_and_blocks_late_publication sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_live_builder_uses_owned_process_boundary -q
```

Timeout evidence:

```text
test_sentinel_single_spine_c1_executable_mapping.py::test_c2_workspace_compression_artifacts_match_current_source
-> timed out at 60s
-> instrumented reproduction showed execution inside ast.generic_visit while rebuilding the C2 static baseline

test_power_unification_pack4_browser_l5_l6_product_backend.py
-> 31 tests collected
-> full file timed out at 240s before completion
```

## Live Cloak Status

```text
CLOAK binary provenance = single existing candidate recovered process-scoped
candidate_count = 1
installed = true
version = 146.0.7680.177.5
tier = free
platform = windows-x64
path_present = true
path_hash = a78c3a809e49a8ee24a77f220b45d10a4f2e764e4ed62f72452e4d4e08b55eec
file_sha256 = 03f53661a5c47e7b0a661bee2bce8a0d302b7a60834c328df417561fa0636d80
ensure_binary_called = false
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
readiness_ready = true after target-closed follow-up
failure_code = null after target-closed follow-up
diagnostic_event_count = 93 on attempt 1
stage_sequence_hash = 88844136e519f217cf0af696c02550bfe8d23441afea693fcf2fdbc4d002a01a on attempt 1
profile_material_persisted = false
probe_temp_cleanup = true
provider_calls = 0
SQLite mission = NOT_RUN
Playwright fallback selected = false
```

Safe stage telemetry shows provenance resolution reached a single candidate and
the live backend route selected `cloak_browser`. The historical timeout probe
proved a containment race; the final target-closed follow-up probes show
`new_process_launch`, `context_creation`, `page_creation`, and
`initial_navigation` returning successfully under the owned child-process
boundary. No raw stack, local path, profile material, DOM, screenshot, cookie,
token, or provider material is persisted in this report.

The historical post-timeout process census was intentionally not treated as
owned-process cleanup proof because it counted unrelated user browser and Node
processes. It did show no process name containing `cloak` or `chromium` at
that moment.

## Historical Timeout Root Cause Probe

```text
root_cause_probe = ROOT_CAUSE_PROVEN_TIMEOUT_CONTAINMENT_RACE
provider_calls = 0
SQLite mission = NOT_RUN
candidate_count = 1
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
failure_code = CLOAK_SESSION_READINESS_TIMEOUT
timeout_active_stage = initial_navigation
timeout_open_stage_count = 3
stage_event_count = 63
stage_sequence_hash = 3078c005d3a0cb0271fdf29d3948d5bc0985842e388d05a82178ff93821ecfe0
context_operational = false at parent timeout
page_operational = false at parent timeout
cleanup_operational = false at parent timeout
profile_material_persisted = true at parent timeout
temp_probe_cleanup_after_wait = true
```

The timeout parent returned while the worker was still inside the open-session
path. The safe stage tail then showed `context_creation`, `page_creation`,
`initial_navigation`, `backend_open_context`, and `session_publication` events
continuing after the parent had already emitted `CLOAK_SESSION_READINESS_TIMEOUT`.
That historical probe proved the immediate blocker was the readiness
containment design: a daemon thread could outlive the parent timeout and race
cleanup. The later repair replaced that boundary with an owned child process.

`EPIPE` remains classified as a post-timeout driver-pipe symptom until a
separate proof shows it is the first causal failure.

## Remaining Open Truth

```text
Browser physical/Cloak live proof = C5A_LIVE_READINESS_READY_3_OF_3_CONTEXT_PAGE_OBSERVE_CLEANUP
readiness timeout root cause = ROOT_CAUSE_PROVEN_TIMEOUT_CONTAINMENT_RACE_REPAIRED_LOCAL
new process TargetClosedError = PRIOR_BLOCKER_NOT_REPRODUCED_AFTER_INSTRUMENTED_FINAL_CODE
Browser sandbox/process kill live proof = NOT_RUN
redirect/origin physical enforcement = NOT_RUN
provider/model Browser mission = NOT_RUN
FIXED_PROVEN = 0/65
P0-01 = IMPLEMENTING
C-P0-01 = IMPLEMENTING
C-P0-03 = IMPLEMENTING
C-P0-06 = IMPLEMENTING
P1-25 = IMPLEMENTING
C-P1-17 = IMPLEMENTING
P0-07 = IMPLEMENTING
```

## Next Correct Step

```text
C5B_PHYSICAL_BROWSER_PRODUCT_MISSION_AFTER_OPERATOR_ACCEPTANCE
provider_calls = not consumed in C5A follow-up
real Cloak readiness = READY_3_OF_3
fixture backend = no
Playwright fallback = no
canonical single spine = required
SQLite mission = NOT_RUN in this wave
```

The timeout root cause is repaired locally. The prior TargetClosed symptom did
not reproduce after adding launch-stage failure telemetry, so this report does
not claim a TargetClosed root cause. C5B must still wait for operator
acceptance because no real provider Browser mission was run in this wave.
