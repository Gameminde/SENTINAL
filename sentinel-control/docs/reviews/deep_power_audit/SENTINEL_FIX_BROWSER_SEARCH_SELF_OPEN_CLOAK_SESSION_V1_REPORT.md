# SENTINEL FIX BROWSER SEARCH SELF OPEN CLOAK SESSION V1

## Verdict

```text
FIX_BROWSER_SEARCH_SELF_OPEN_CLOAK_SESSION_V1 = LOCALLY_COMMITTED
commit = 30519f8 fix: let browser search open cloak sessions
```

## Root Cause

V3 showed that `real_browser.search` in the product browser runtime could receive the selected Cloak/session backend while no live session was open yet. The runtime treated this as a terminal blocked search instead of opening the bounded session for the high-level search skill.

## Runtime Change

Updated:

```text
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
```

`RealBrowserControlRuntime._search` now catches the closed/missing-session observation failure and opens the bounded selected backend session before continuing search actuation.

## Regression Test

Updated:

```text
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py
```

Added a strict fake session manager regression: `real_browser.search` must open the selected Cloak/session backend when no session exists.

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py::test_real_browser_search_opens_cloak_session_when_not_already_open -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py
git diff --check
targeted raw secret/provider/browser material scan
```

All listed validation passed. Scan hits were benign guard/redaction strings only.

## No-New-Power Confirmation

No arbitrary browser, login, payment, contact supplier, credential, cookie/session persistence, provider-native tool, fallback/AUTO, or external send power was added.

