# SENTINEL_FIX_CLOAK_LOCAL_BINARY_OVERRIDE_AND_PROFILE_MATERIAL_ACCOUNTING_V1_REPORT

## Verdict

```text
FIX_CLOAK_LOCAL_BINARY_OVERRIDE_AND_PROFILE_MATERIAL_ACCOUNTING_V1 = LOCALLY_COMMITTED
implementation_commit = bd8e15fa17c9574897fb5fbe77f3533a3f2bc55b
provider_calls = 0
real_provider_attempt_rerun = no
push = no
```

## Problem

The previous Cloak readiness fix made bootstrap hangs safe, but the next root blocker was deeper:

```text
cloakbrowser package installed = true
Cloak Chromium binary installed = false
cloakbrowser.ensure_binary() = timed out after bounded local bootstrap attempt
provider_call_allowed = false
```

The session backend was not wrong. Cloak/session was selected correctly. The missing piece was deterministic binary readiness.

## Fix

Sentinel now separates three readiness layers:

```text
1. browser backend selection truth
2. Cloak binary readiness
3. Cloak session/page readiness
```

New behavior:

```text
if Cloak binary is missing and no local override exists:
  block pre-session with CLOAK_BINARY_NOT_INSTALLED

if bootstrap is explicitly requested:
  run cloakbrowser.ensure_binary() in a bounded subprocess
  return CLOAK_BINARY_BOOTSTRAP_TIMEOUT / FAILED / OUTPUT_INVALID safely

if CLOAKBROWSER_BINARY_PATH points to an existing local browser binary:
  treat it as Cloak local binary override
  do not download
  proceed to Cloak/session readiness
```

This uses CloakBrowser as the product-leading backend. It does not silently switch to Sentinel's Playwright compatibility backend.

## Local Proof

With a temporary process-scoped bounded target and local Chrome binary override:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
profile_material_persisted = false
failure_code = null
safe_url_origin_hash = 952b92400b51c20b115f14e357fca0d066d761e3d64c9304fac6578a62122b9c
```

Raw URL and local binary path were not persisted. The local binary path is represented only by safe hash inside diagnostics when needed.

## Profile Material Accounting Correction

The prior profile-material detector counted any file under the capture root, including safe readiness receipts and snapshots.

That produced false positives:

```text
safe snapshot/receipt JSON exists -> profile_material_persisted = true
```

New behavior:

```text
safe readiness receipts/snapshots do not count as profile material
files under a profile directory still count
known browser profile stores such as Cookies, History, Login Data, Local Storage, Session Storage, IndexedDB still count
```

## DevTools / Chrome DevTools MCP Direction

Chrome DevTools MCP remains a strong import pattern for the next browser-power step:

```text
attach to existing browser through DevTools/CDP
collect accessibility/DOM/network/console/performance state
feed compact world-model evidence to the model
keep CDP/MCP as transport/intelligence, not authority
```

Sentinel already has matching organs:

```text
browser_devtools_backend_adapter_v1.py
browser_devtools_machine_intelligence_v1.py
browser_session_manager_l5_live.py
organs/browser/cdp_ax.py
organs/browser/cloak_backend.py
```

This pack does not wire a live MCP adapter yet. It makes the Cloak/session backend actually reachable without the blocking download path.

## Files Changed

```text
sentinel/operator/real_browser_control_runtime.py
tests/operator/test_power_pack6d_browser_skill_spine.py
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_binary_missing_blocks_before_session_manager_construction -q
result: passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_local_binary_override_allows_readiness_without_download -q
result: passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_cloak_readiness_safe_receipts_do_not_count_as_profile_material -q
result: passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result: passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result: passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result: passed

py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py -q
result: passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result: passed

git diff --check
result: passed
```

## Targeted Scan

Scan covered touched runtime/test files and the local readiness artifact directory.

Result:

```text
no raw bounded URL persisted
no local browser binary path persisted
no credential values persisted
no Authorization/Bearer material persisted
no raw provider/reasoning persisted
no raw DOM/screenshot persisted
no cookie/session token/profile material persisted
no provider-native tool introduction
no fallback/AUTO introduction
```

Only expected safe markers appeared:

```text
CLOAKBROWSER_BINARY_PATH env name
raw_provider / reasoning_content negative-test strings
cookie/session sensitive-marker strings
```

## Remaining Blockers

```text
No real provider/browser mission was rerun in this pack.
The next real attempt must pass process-scoped CLOAKBROWSER_BINARY_PATH if the packaged Cloak download remains unavailable.
The DevTools MCP/CDP bridge is still not live in the browser skill spine.
```

## Next Prepared Real Attempt

```text
REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1
```

Preflight must prove:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
receipt_backend_match = true
profile_material_persisted = false
```

If these facts hold and provider config is present, the next run can consume the real provider without repeating the previous Cloak/bootstrap failure.

