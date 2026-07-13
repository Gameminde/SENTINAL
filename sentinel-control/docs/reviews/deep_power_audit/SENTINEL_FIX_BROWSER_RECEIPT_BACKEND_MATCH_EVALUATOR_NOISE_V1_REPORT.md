# SENTINEL_FIX_BROWSER_RECEIPT_BACKEND_MATCH_EVALUATOR_NOISE_V1

## Purpose

Fix a reporting/evaluation noise issue exposed by V17:

```text
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
real browser action receipts all match
but receipt_backend_match reported false
```

## Root Cause

The backend-match helper accepted every artifact-like dict that carried backend fields. The V17 runner's collection step included request/parameter artifacts and action receipts in the same list.

Request/parameter artifacts are not browser action receipts and must not decide backend truth.

## Fix

Updated:

```text
sentinel/operator/real_browser_attempt_evaluation.py
```

Backend matching now considers only real browser action receipts:

```text
receipt_id starts with real_browser_action_
or receipt_kind = real_browser_action
or action_kind starts with real_browser.
```

## Test Added

Updated:

```text
tests/operator/test_power_pack6d_browser_skill_spine.py
```

The existing backend-match test now includes a noisy non-receipt artifact with compatibility backend fields and still requires the true action receipt to prove Cloak.

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py::test_backend_match_ignores_open_receipt_without_backend_truth -q
result = 1 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 92 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 18 passed

offline V17 artifact backend-match check
result = true
```

## Safety

```text
no provider call during fix
no real browser run during fix
no runtime power expansion
no fallback/AUTO
no provider-native tools
```
