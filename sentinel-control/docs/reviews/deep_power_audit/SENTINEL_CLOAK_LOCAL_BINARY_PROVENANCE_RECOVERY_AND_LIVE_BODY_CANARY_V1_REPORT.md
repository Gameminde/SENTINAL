# SENTINEL_CLOAK_LOCAL_BINARY_PROVENANCE_RECOVERY_AND_LIVE_BODY_CANARY_V1_REPORT

## Verdict

```text
CLOAK_LOCAL_BINARY_PROVENANCE_RECOVERY_AND_LIVE_BODY_CANARY_V1 = VALID_SUCCESS_LIVE_BODY_PROVEN
implementation_commit = 8ca3aeb
provider_calls = 0
frozen_holdout_used = no
Playwright fallback = no
deterministic/fixture backend = no
real provider canary = not_run
12-task calibration = not_resumed
frozen holdout = not_opened
search_quality = NOT_PROVEN
```

This tranche proves Cloak binary provenance recovery, timeout containment, live Cloak body reuse, cleanup, sequential reopen and concurrent root serialization through the RuntimeHost product spine.

It does not prove browser search quality, search relevance, or deep browser cognition.

## Stage A - Read-Only Binary Provenance Recovery

Allowed read-only provenance source used:

```text
cloakbrowser.binary_info()
```

Forbidden operations were not used:

```text
cloakbrowser.ensure_binary() = not_called
download/install/update/bootstrap = not_called
browser launch during provenance = not_called
Playwright substitution = not_used
raw binary path printed = false
raw binary path persisted = false
```

Safe provenance result:

```text
candidate_count = 1
verified_candidate_count = 1
decision = EXACTLY_ONE_VERIFIED_CANDIDATE
source = binary_info.binary_path
path_hash = f3fad5133de1a876082e5a7f6be7c61cf083e2a4742c4cf44fcfa6cfe34d3a2e
file_sha256 = 03f53661a5c47e7b0a661bee2bce8a0d302b7a60834c328df417561fa0636d80
size_bytes = 3902976
version = 146.0.7680.177.5
bundled_version = 146.0.7680.177.5
platform = windows-x64
tier = free
```

The recovered binary path was used only as a process-scoped environment value for the canary process. It was not committed, printed, or persisted in reports.

## Stage B - Timeout Containment

The previous daemon-thread style timeout was not accepted because a worker could continue after timeout. Stage B used a killable isolated child process and parent-side process-tree termination.

Result:

```text
worker_exit_kind = killed_after_parent_timeout
worker_terminated = true
browser_process_count_after_timeout = 0
live_context_count_after_timeout = 0
profile_lock_after_timeout = false
profile_material_after_timeout = 0
cleanup_root_removed = true
raw_paths_printed = false
provider_calls = 0
verdict = STAGE_B_PASS
```

No `FileNotFoundError` reappeared during timeout containment. The earlier Windows cleanup issue was contained by process isolation and full tree termination.

## Runtime Fix

Implemented in:

```text
8ca3aeb fix: stabilize live cloak body lifecycle
```

Files changed:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py
sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
```

Fix details:

```text
BrowserSessionManagerRealBrowserEngine now owns a default capture root when none is supplied.
Product/browser authority is translated into internal L5 browser_session_* actions.
Live Cloak product root leases acquire a process-wide live context lock.
The live context lock is released on normal close and on engine-build failure.
RuntimeHost safe lease dump includes live lock state/count.
Tests cover internal L5 authority translation and live Cloak root serialization.
```

This does not expose new model-facing power. It aligns product-spine browser skill execution with the hidden Cloak/session body requirements.

## Stage C - Live Cloak Body Canary

Stage C used a bounded non-holdout public target. The raw URL is intentionally omitted.

```text
target_origin_hash = c7953ead217ba1d4865213fd20202076b33f31aaa26a29854cc80df31d923e0e
runtimehost_product_spine_used = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
provider_calls = 0
Playwright fallback = false
fixture backend = false
raw_paths_printed = false
```

Completion segment:

```text
status = completed
sequence = real_browser_control:real_browser.search -> real_browser_control:real_browser.verify_extraction -> sentinel_loop:finish
product_receipts = 2
real_browser_skill_receipts = 1
unique_browser_session_ref_count = 1
receipt_ids_unique = true
backend_truth = cloak_browser / cloak_browser / cloakbrowser
```

Block segment:

```text
status = blocked
blocked_reason = real_browser_search_actuation_failed
sequence = real_browser_control:real_browser.search -> real_browser_control:real_browser.search
product_receipts = 2
```

This is preserved as a search actuation quality signal, not a lifecycle failure. The body still closed and cleaned up.

Exception segment:

```text
exception_kind = RuntimeError
remaining_scope_count = 0
scope_closed = true
```

RuntimeHost shutdown segment:

```text
before_lifecycle_state = active
before_lock_acquired = true
after_lifecycle_state = closed
after_close_count = 1
after_lock_acquired = false
scope_closed = true
```

Sequential reopen:

```text
first_status = completed
second_status = blocked
first_receipts = 1
second_receipts = 0
sequential_root_reopen = proven
```

Concurrent roots:

```text
root_1_status = completed
root_2_status = completed
root_1_duration_seconds = 83.408
root_2_duration_seconds = 166.026
concurrent_roots_serialized = true
one_context_limit_respected = true
```

The second root completed after waiting behind the first live Cloak body. The targeted regression test proves the maximum active engine count remains one.

Final cleanup:

```text
browser_process_count_after = 0
profile_material_after = 0
cleanup_root_removed = true
```

## Requirements Status

```text
one reused real Cloak body across multiple child actions = passed
stable root lease identity inside one root = passed
child receipt separation = passed
close on completion = passed
close on block = passed
close on exception = passed
close on RuntimeHost shutdown = passed
sequential root close/reopen = passed
concurrent roots serialize under one-context limit = passed
zero remaining browser processes/contexts/handles/profile material = passed
FileNotFoundError preserved if reappears = no_FileNotFoundError_reappeared
lease identity/lifecycle states via safe hashes only = passed
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_browser_session_engine_translates_product_authority_to_l5_session_actions tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_live_cloak_root_leases_serialize_until_close tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_runtimehost_shutdown_closes_leaked_root_browser_lease -q
result = 3 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 97 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 26 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check
result = passed with CRLF warnings only

targeted scan for secrets/raw-provider/provider-native/fallback/AUTO/raw DOM/cookies/session/profile material
result = benign test redaction markers and cleanup identifiers only
```

## Remaining Gaps

```text
search_quality = not_proven
search_materiality = not_proven
deep_browser_cognition = not_proven
real_provider_non_holdout_calibration = not_resumed
frozen_holdout = not_opened
```

The important body defect is closed: Sentinel can now create, reuse, serialize and clean up the live Cloak body through the product spine without provider calls, Playwright fallback, fixture backend, raw binary path persistence, or leftover process/profile material.

## Next Action

The next tranche may run exactly one real-provider non-holdout mission against the live Cloak body, but it must not resume the 12-task calibration or open frozen holdout sites automatically.
