# SENTINEL_SINGLE_SPINE_C5A_TARGET_CLOSED_ROOT_CAUSE_REPORT

## Verdict

```text
C5A_CLOAK_NEW_PROCESS_LAUNCH_TARGET_CLOSED_ROOT_CAUSE =
PRIOR_TARGET_CLOSED_NOT_REPRODUCED_AFTER_INSTRUMENTED_FINAL_CODE

C5A_LIVE_READINESS = READY_3_OF_3
ROOT_CAUSE_PROVEN = NO_FOR_PRIOR_TARGET_CLOSED
LIVE_CLOAK_CONTEXT_PAGE_OBSERVE_CLEANUP = PROVEN_IN_READINESS_PROBE

provider_calls = 0
SQLite = NOT_RUN
C5B = NOT_STARTED
Qwen = NOT_RUN
FIXED_PROVEN = 0/65
```

This wave did not start a Browser product mission and did not claim Browser
mission power. It kept the C5A owned child-process readiness boundary intact,
added missing stage-specific launch telemetry, and reran three bounded live
Cloak readiness probes. The prior `TargetClosedError` symptom did not
reproduce on the final instrumented code.

## Source Truth

```text
source_head_before_wave = fb3561f1bfdaee7a004a3bddacf8c39cbd8f057f
implementation_tested_head = SELF_REFERENCE_UNAVAILABLE_IN_COMMIT_CONTENT
attestation_head = SELF_REFERENCE_UNAVAILABLE_IN_COMMIT_CONTENT
post_push_attestation_remote_head_before_wave = fb3561f1bfdaee7a004a3bddacf8c39cbd8f057f
```

The commit cannot contain its own final hash, so the ledger uses explicit
self-reference markers for the current commit fields and preserves the source
head before this wave.

## Root-Cause Investigation

The previous repair report showed:

```text
cloak_open_context
-> new_process_launch
-> TargetClosedError
-> no usable context/page
```

The code path did not yet mark `new_process_launch` as failed when
`cloakbrowser.launch_persistent_context` raised. That made the first failing
sub-stage ambiguous.

The new deterministic regression proves a launch exception now emits:

```text
new_process_launch stage_started
new_process_launch stage_failed exception_class/hash
context_creation stage_failed exception_class/hash
cloak_open_context stage_failed exception_class/hash
```

No raw exception text, local path, selector, DOM, cookie, session, profile
material or provider output is persisted.

## Implementation

- `CloakBrowserSessionBackend.open_context` now emits bounded safe launch
  details and terminalizes launch failures at `new_process_launch` and
  `context_creation`.
- `RealBrowserControlRuntime` now reports `backend_selected = true` when the
  selected backend is already known to be `cloak_browser`, while keeping
  `receipt_backend_match = false` until a real receipt/backend match exists.
- The ledger now separates historical timeout repair truth from the follow-up
  TargetClosed wave.

## Live Probe Results

Three bounded provider-free Sentinel readiness probes were executed with the
same C5A constraints:

```text
provider_calls = 0
SQLite = NOT_RUN
C5B = NOT_STARTED
fixture_backend = false
Playwright_fallback = false
```

Aggregate result:

```text
attempts = 3
ready_count = 3
all_ready = true
target_closed_reproduced = false
cleanup_success_count = 3
profile_material_persisted_count = 0
safe_origin_hash_only = true
```

Each attempt proved:

```text
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
process_operational = true
context_operational = true
page_operational = true
devtools_operational = true
read_only_observation = true
multi_action_reuse_operational = true
reopen_operational = true
cleanup_operational = true
receipt_backend_match = true
```

The safe stage journals show `new_process_launch`, `context_creation`,
`page_creation` and `initial_navigation` all reached `stage_returned` in the
final code. Therefore the prior `TargetClosedError` is not proven as a stable
current blocker.

## Safe Artifacts

```text
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/aggregate.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/live_readiness_summary_attempt1.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/live_readiness_summary_attempt2.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/live_readiness_summary_attempt3.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/readiness_result_attempt1.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/readiness_result_attempt2.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/readiness_result_attempt3.safe.json
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/readiness_stages_attempt1.safe.jsonl
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/readiness_stages_attempt2.safe.jsonl
sentinel-control/docs/reviews/deep_power_audit/C5A_TARGET_CLOSED_ROOT_CAUSE_PROBE/readiness_stages_attempt3.safe.jsonl
```

These artifacts contain only typed statuses, hashes, counts and bounded stage
events.

## Remaining Truth

```text
Browser physical/Cloak live readiness = READY_3_OF_3_CONTEXT_PAGE_OBSERVE_CLEANUP
Browser product mission = NOT_RUN
Browser sandbox/process kill live proof = NOT_RUN_IN_THIS_WAVE
redirect/origin physical enforcement = NOT_RUN
C2 static probe = PARTIAL_TIMEOUT_AST_GENERIC_VISIT
Pack4 Browser regression = TIMEOUT
FIXED_PROVEN = 0/65
```

C5B remains unstarted. The next browser step, after operator acceptance, should
use this readiness proof to enter a controlled physical Browser route/product
mission without hiding the remaining sandbox, redirect/origin and product
mission gaps.

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_records_launch_failure_on_new_process_stage sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_is_primary_and_uses_persistent_context sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_cloakbrowser_backend_closes_partial_context_when_page_creation_fails sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py::test_live_browser_session_lifecycle_sink_records_safe_open_close_substages -q
-> 4/4 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_gate_blocks_before_provider_when_bootstrap_missing sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_owned_process_timeout_kills_tree_and_blocks_late_publication sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_live_builder_uses_owned_process_boundary -q
-> 3/3 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py::test_stage0_finding_ledger_contains_all_65_findings -q
-> 1/1 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_sentinel_single_spine_c5_physical_browser_boundary.py -q
-> 3/3 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
-> passed

JSON/JSONL parse of ledger and C5A target-closed safe probe artifacts
-> json_ok=8; jsonl_ok=3

git diff --check
-> passed

targeted high-confidence secret/path/raw-browser-material scan over docs and safe artifacts
-> passed

py -3.13 -m ruff check targeted changed files
-> unavailable in this Python environment: No module named ruff
```
