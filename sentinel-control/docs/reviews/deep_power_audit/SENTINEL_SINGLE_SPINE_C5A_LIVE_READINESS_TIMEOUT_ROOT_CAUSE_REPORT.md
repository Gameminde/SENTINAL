# SENTINEL_SINGLE_SPINE_C5A_LIVE_READINESS_TIMEOUT_ROOT_CAUSE_REPORT

## Verdict

```text
C5A_LIVE_READINESS_TIMEOUT_ROOT_CAUSE = ROOT_CAUSE_PROVEN_TIMEOUT_CONTAINMENT_RACE
provider_calls = 0
SQLite mission = NOT_RUN
C5B = NOT_STARTED
FIXED_PROVEN = 0/65
```

The live Cloak blocker is no longer a generic browser failure. Sentinel selects
`cloak_browser`, validates one existing binary candidate, starts the real Cloak
session path, then the parent readiness watchdog returns before the worker has
finished publishing a usable context/page. The worker can continue after the
timeout and race cleanup.

## Proven Timeline

```text
configuration = returned
binary_resolution = returned
engine_construction = returned
bind_authority = returned
open_session = started
post_close_state_reset = returned
profile_lease_create = returned
backend_open_context = started
profile_material_creation = returned
new_process_launch = returned
context_creation = returned after parent timeout window
page_creation = returned after parent timeout window
initial_navigation = active at parent timeout
readiness_probe = failed with CLOAK_SESSION_READINESS_TIMEOUT
backend_open_context = returned after timeout
session_publication = returned after timeout
timeout_cleanup = returned, but cleanup was racing a live worker
```

Latest safe live probe:

```text
candidate_count = 1
installed = true
version = 146.0.7680.177.5
tier = free
platform = windows-x64
file_sha256 = 03f53661a5c47e7b0a661bee2bce8a0d302b7a60834c328df417561fa0636d80
path_hash = a78c3a809e49a8ee24a77f220b45d10a4f2e764e4ed62f72452e4d4e08b55eec
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
failure_code = CLOAK_SESSION_READINESS_TIMEOUT
timeout_active_stage = initial_navigation
timeout_open_stage_count = 3
stage_event_count = 63
stage_sequence_hash = 3078c005d3a0cb0271fdf29d3948d5bc0985842e388d05a82178ff93821ecfe0
provider_calls = 0
SQLite mission = NOT_RUN
Playwright fallback selected = false
```

## Root Cause

```text
root_cause = readiness timeout containment uses an uncancellable daemon thread
first causal defect = parent timeout can return while Cloak open/context/page/navigation continues
cleanup defect = cleanup can run concurrently with late session publication
EPIPE classification = post-timeout driver-pipe symptom, not proven first cause
```

This does not prove Cloak is unusable. It proves Sentinel cannot yet safely
contain a slow Cloak readiness sequence. The Browser physical proof must not
graduate until readiness runs inside a killable isolation boundary or equivalent
cancellation mechanism.

## Code Change

Added safe timeout-stage telemetry:

```text
CloakSessionReadinessResult.timeout_active_stage
CloakSessionReadinessResult.timeout_open_stage_count
_CloakReadinessStageJournal.timeout_snapshot()
```

The telemetry is status/hash/count only. It does not persist raw paths, DOM,
selectors, URLs, screenshots, cookies, tokens, sessions, profile material, raw
provider output, or private reasoning.

## Validation

```text
RED:
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_reports_active_stage_without_raw_material -q
-> failed with KeyError: timeout_active_stage

GREEN:
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_reports_active_stage_without_raw_material -q
-> 1/1 passed

RELATED:
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_gate_times_out_without_hanging_parent sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_writes_parent_visible_stage_journal sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_reports_active_stage_without_raw_material sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_default_watchdog_does_not_starve_sequential_reopen sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_reopens_observes_and_closes_reopened_session -q
-> 5/5 passed
```

Previous C5A validations remain:

```text
C5A physical browser boundary = 3/3 passed
C4 + C5A + observe receipt proof = 10/10 passed
compileall sentinel = passed
C2 static baseline rebuild = PARTIAL/TIMEOUT in ast.generic_visit
Pack4 Browser regression = TIMEOUT after 31 tests collected
```

## Next Step

```text
C5A-TIMEOUT-CONTAINMENT-REPAIR
provider_calls = 0
SQLite mission = NOT_RUN
real Cloak = required only for body proof after local repair
fixture backend = no for live proof
Playwright fallback = no
```

Acceptance before C5B:

```text
real Cloak
usable context
usable page
bounded read-only observation
owned-process cleanup proven
profile_material_persisted = false
provider_calls = 0
SQLite = NOT_RUN
```

