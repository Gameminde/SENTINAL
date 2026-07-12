# SENTINEL_FIX_CLOAK_SESSION_READINESS_TIMEOUT_AND_PROFILE_CLEANUP_V1_REPORT

## Verdict

```text
FIX_CLOAK_SESSION_READINESS_TIMEOUT_AND_PROFILE_CLEANUP_V1 = IMPLEMENTED_CANDIDATE
provider_call = no
real_provider_mission = no
real_browser_readiness_probe = yes
push = no
product_proven = no
```

This fix responds to:

```text
BROWSER_CORTEX_REAL_POWER_READINESS_GATE_V2_CLOAK_SESSION_TIMEOUT_V1
```

The V2 gate showed that process-scoped target and binary override reached
Cloak-first backend truth, but the readiness probe timed out and reported
profile material persisted during the no-go path.

## Root Cause

`_profile_file_count()` counted browser profile material in sensitive folders
such as:

```text
Local Storage
IndexedDB
Sessions
Cookies
History
```

But `_remove_profile_material()` only removed directories named exactly:

```text
profile
```

Therefore real Cloak/session readiness could leave sensitive browser-profile
folders outside an exact `profile` path after a timeout. The fake timeout test
did not catch this because it did not create realistic sensitive profile
subdirectories.

## Files Changed

```text
sentinel/operator/real_browser_control_runtime.py
tests/operator/test_power_pack6d_browser_skill_spine.py
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
```

## Runtime Change

The profile-material detector and remover now share the same sensitive browser
profile name set. Cleanup removes:

```text
profile directories
cookie/history/login/web-data/session/local-storage/indexeddb directories
matching sensitive files
```

This keeps safe readiness receipts/cache artifacts but removes browser profile
material before a timeout result can be considered clean.

## TDD Proof

New regression:

```text
test_cloak_readiness_timeout_removes_sensitive_profile_dirs
```

Red result before fix:

```text
readiness.profile_material_persisted == true
```

Green result after fix:

```text
readiness.profile_material_persisted == false
Local Storage probe directory removed
```

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_removes_sensitive_profile_dirs -q
Result: passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
Result: 85 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
Result: passed
```

## Real Readiness Re-Check

After the fix, a process-scoped readiness probe against the bounded browser
target returned:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
profile_material_persisted = false
failure_code = null
provider_decision_calls = 0
```

No raw browser URL, local binary path, endpoint, API key, cookie, session, DOM,
screenshot, or provider material is persisted here.

## Boundaries Preserved

```text
provider call before readiness = blocked
silent Playwright fallback = blocked
raw cookie/session/profile persistence = blocked
provider-native tools = blocked
fallback/AUTO = blocked
payment/login/contact/credential surfaces = unchanged
```

## Remaining Work

The next step may now be prepared as a single real-provider/browser product
attempt:

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V1
```

That attempt must be launched only after this source/docs fix is committed, and
must preserve:

```text
one provider mission
no retry after provider call
no fallback/AUTO
no provider-native tools
no raw provider/reasoning/browser profile material persistence
no source changes after provider run
no push
```
