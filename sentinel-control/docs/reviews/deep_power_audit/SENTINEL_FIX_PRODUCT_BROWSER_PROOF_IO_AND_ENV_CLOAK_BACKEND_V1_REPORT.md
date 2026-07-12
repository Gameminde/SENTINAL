# Sentinel Fix Product Browser Proof IO And Env Cloak Backend V1 Report

Date: 2026-07-12

## Verdict

```text
FIX_PRODUCT_BROWSER_PROOF_IO_AND_ENV_CLOAK_BACKEND_V1 = LOCALLY_COMMITTED
proof_io_fix_commit = 6087d81
env_cloak_backend_fix_commit = 8fa9e86
provider_call_during_fix = no
real_browser_run_during_fix = no
push = no
```

## Root Cause

`REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V1` produced browser and
ProductActionKernel receipts, but the task-loop blocked as
`proof_receipt_missing`.

The receipts existed. The failure was caused by normal Windows path APIs in the
proof verifier on long artifact paths.

A second issue was discovered while classifying the run: the product browser
executor always used `_ProductLocalCloakBrowserEngine`, so the attempt was still
using a local fixture engine even though Cloak/session readiness was green.

## Runtime Changes

### Product Proof IO

Changed:

```text
sentinel/operator/unified_execution_dispatcher.py
```

Behavior:

```text
ProductActionKernel proof verification now uses long-path-aware JSON artifact existence/read helpers.
Product receipts and ProductActionKernel FinalGate files can be verified under long Windows run roots.
The verifier no longer reports proof_receipt_missing when the receipt exists but the path is long.
```

### Product Browser Backend Selection

Changed:

```text
sentinel/operator/runtime_host.py
```

Behavior:

```text
If a product browser action explicitly requests fake/local engine_profile, RuntimeHost keeps the local fixture backend.
If the bounded browser target env is present and no fake/local profile is requested, RuntimeHost builds the Cloak-first env browser engine.
No silent Playwright fallback is introduced.
Playwright remains compatibility-only.
```

## Tests Run

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_browse_search_product_proof_survives_long_run_root -q
result = passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_env_configured_browser_product_route_uses_cloak_first_engine_factory sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_browse_search_product_proof_survives_long_run_root -q
result = 2 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 10 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result = 14 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py -q
result = 54 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
result = passed

git diff --check
result = passed
```

## Targeted Scan

```text
changed_file_scan = clean except benign env-name and hard-boundary strings
raw provider/reasoning persistence = no
credential/session/cookie persistence = no
provider-native/fallback AUTO introduced = no
```

## Remaining Blockers

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V2 still required.
V1 did not mechanically prove provider call count from summary artifacts.
V1 did not prove real Alibaba page extraction because executor still used local fixture before 8fa9e86.
```

## Next Prepared Proof

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V2_AFTER_PROOF_IO_AND_ENV_CLOAK_FIX
```

