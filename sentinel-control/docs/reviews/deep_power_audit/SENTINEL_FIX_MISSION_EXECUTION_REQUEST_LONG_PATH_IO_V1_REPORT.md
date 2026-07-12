# SENTINEL FIX MISSION EXECUTION REQUEST LONG PATH IO V1

## Verdict

```text
FIX_MISSION_EXECUTION_REQUEST_LONG_PATH_IO_V1 = LOCALLY_COMMITTED
commit = b3dae57 fix: make mission execution requests long-path aware
```

## Root Cause

Attempt V2 proved that mission execution request loading still used direct `Path` IO in places that can fail on long Windows run-root paths.

## Runtime Changes

Updated:

```text
sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py
```

Added long-path-aware helpers and routed mission execution request / parameter loading and request listing through them.

## Regression Test

Updated:

```text
sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py
```

Added a long Windows path regression that failed before the fix and passed after it.

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py::test_lifecycle_loads_execution_request_on_long_windows_path -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_mission_lifecycle_service.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/mission_lifecycle_service.py
git diff --check
targeted raw secret/provider/browser material scan
```

All listed validation passed. The targeted scan found no raw credential, provider, browser URL, binary path, DOM, screenshot, cookie/session/profile material persistence.

## No-New-Power Confirmation

This fix did not add new live power, fallback/AUTO, provider-native tools, browser actions, or external sends. It only fixed product-spine filesystem IO.

