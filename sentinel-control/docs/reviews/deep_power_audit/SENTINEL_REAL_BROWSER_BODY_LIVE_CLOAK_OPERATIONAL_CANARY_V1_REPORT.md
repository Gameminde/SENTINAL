# SENTINEL_REAL_BROWSER_BODY_LIVE_CLOAK_OPERATIONAL_CANARY_V1_REPORT

## Verdict

```text
REAL_BROWSER_BODY_LIVE_CLOAK_OPERATIONAL_CANARY_V1 = VALID_INFRA_BLOCKED
implementation_defect_reproduced = yes
implementation_fix_commit = d3a9615
provider_calls = 0
frozen_holdout_used = no
Playwright fallback = no
deterministic/fixture backend = no
real provider canary = not_run
12-task calibration = not_resumed
frozen holdout = not_opened
```

Do not mark the overall lifecycle pack `VALID_SUCCESS` yet.

The requested live Cloak body canary did not reach live multi-action reuse because the required local Cloak binary override was not present in process, user, or machine environment.

## Preflight

```text
CLOAKBROWSER_BINARY_PATH process = false
CLOAKBROWSER_BINARY_PATH user = false
CLOAKBROWSER_BINARY_PATH machine = false
SENTINEL_BROWSER_TEST_URL process = false
SENTINEL_BROWSER_TEST_URL user = false
SENTINEL_BROWSER_TEST_URL machine = false
provider config present = yes
provider used = no
```

The canary contract required restoring `CLOAKBROWSER_BINARY_PATH` only from the previously validated local Cloak configuration. No persisted raw binary path was available, and no binary was installed, updated, discovered, or substituted automatically.

## Reproduced Defect

Before the fix, a body-only readiness probe was executed with:

```text
provider_calls = 0
prepare_binary = false
target = non-holdout public-Web target
target persisted = no raw URL
safe_url_origin_hash = ab069103af9db8016ebccd048001e0fa9aebe1fab282574d2659c7c8241904d1
```

Observed result:

```text
ready = false
provider_call_allowed = false
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
failure_code = CLOAK_SESSION_READINESS_TIMEOUT
profile_material_persisted = true
cleanup exception = PermissionError while removing profile cache data
```

This proved the preflight still allowed a packaged Cloak/session launch when the canary required a previously validated local binary override. The timeout path also exposed profile cleanup fragility on Windows.

No `FileNotFoundError` reappeared in this canary. The reproduced cleanup issue was `PermissionError`.

## Correction

Implemented in:

```text
d3a9615 fix: require cloak local override for live canary
```

Changed behavior:

```text
check_cloak_session_readiness_from_env supports require_local_binary_override
SENTINEL_REQUIRE_CLOAKBROWSER_BINARY_PATH=true enables the gate from env
check_cloak_session_readiness supports require_local_binary_override
missing CLOAKBROWSER_BINARY_PATH returns CLOAK_LOCAL_BINARY_OVERRIDE_REQUIRED
readiness blocks before BrowserSessionManager launch
timeout cleanup now joins briefly after close_all and retries profile material removal
```

The fix does not enable Playwright fallback and does not change provider behavior.

## Post-Fix Canary Gate

The same body-only preflight was rerun with the local override requirement enabled:

```text
provider_calls = 0
frozen_holdout_used = false
Playwright fallback = false
deterministic/fixture backend = false
selected_backend_id = cloak_browser
actual_backend_id =
session_backend_kind =
ready = false
provider_call_allowed = false
failure_code = CLOAK_LOCAL_BINARY_OVERRIDE_REQUIRED
profile_material_persisted = false
remaining_profile_file_count = 0
readiness_cache_written = true
```

This is the correct result for the current environment: block before live browser launch rather than spending provider/browser power or silently using a substituted browser binary.

## Requirements Status

```text
1. provider_calls = 0: passed
2. frozen_holdout_used = no: passed
3. Playwright fallback = no: passed
4. deterministic/fixture backend = no: passed
5. real RuntimeHost product spine: not_reached_due_missing_local_override
6. one reused Cloak body across child actions: not_proven
7. close on completion/block/exception/shutdown: not_proven_live
8. sequential root reopen: not_proven_live
9. concurrent roots serialize under one-context limit: not_proven_live
10. zero remaining live contexts/profile material after close: passed_for_prelaunch_gate; not_proven_live
11. FileNotFoundError preservation/investigation: no_FileNotFoundError_reappeared
12. lease identity/lifecycle cleanup via safe hashes: no_live_lease_created
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_can_require_local_binary_override_before_launch tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_gate_times_out_without_hanging_parent tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_timeout_removes_sensitive_profile_dirs -q
result = 3 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check
result = passed with CRLF warnings only

targeted scan for secrets/raw-provider/provider-native/fallback/AUTO/raw DOM/cookies/session/profile material
result = benign test redaction markers and profile cleanup identifiers only
```

## Remaining Blocker

```text
CLOAKBROWSER_BINARY_PATH must be restored process-scoped from the previously validated local Cloak configuration.
```

Until that happens, the live canary must remain blocked before launch.

## Next Action

After the operator restores the validated local Cloak config process-scoped:

```text
rerun REAL_BROWSER_BODY_LIVE_CLOAK_OPERATIONAL_CANARY_V1
```

The next rerun must prove, before any provider mission:

```text
live RuntimeHost product spine execution
one reused Cloak body across multiple child browser actions
close on completion, block, exception and shutdown
sequential root reopen
concurrent root serialization under the measured one-context limit
zero remaining live contexts/profile material after close
```

No real provider, no frozen holdout, no calibration resume until that live body proof passes.
