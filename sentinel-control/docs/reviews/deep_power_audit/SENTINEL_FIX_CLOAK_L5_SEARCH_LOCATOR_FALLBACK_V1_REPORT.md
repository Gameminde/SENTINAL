# SENTINEL_FIX_CLOAK_L5_SEARCH_LOCATOR_FALLBACK_V1_REPORT

## Verdict

```text
SENTINEL_FIX_CLOAK_L5_SEARCH_LOCATOR_FALLBACK_V1 = LOCALLY_COMMITTED
implementation_commit = af6320504a02d1fa42d63385c4fb89e2dec2e64f
provider_call = no
real_browser_run = no
push = no
```

## Context

Real Power Attempt V10 proved that Sentinel can now drive the real Alibaba bounded path through:

```text
search intent
-> extract_product_cards
-> verify_extraction
-> summarize_evidence
```

V10 also exposed the next power blocker:

```text
SEARCH_ACTUATION_FAILED_WITH_IRRELEVANT_VISIBLE_CARDS
```

The product backend was correctly selected as Cloak/session, but the live L5 session manager used a single exact role/name locator for interaction. On a real page, a model-visible search ref can be semantically correct while the exact accessible name differs from the runtime locator expectation.

## Root Cause

```text
BrowserSessionManagerL5Live._execute_step
-> _locator
-> _role_locator(... exact=True)
-> Playwright/Cloak locator timeout
-> search actuation recoverable failure
```

This was not a provider issue, schema issue, or Playwright product fallback. It was a brittle actuation seam in the selected Cloak/L5 backend.

## Fix

For promoted in-scope L5 interaction actions:

```text
click
type/fill
select
hover
```

the manager now tries:

```text
1. same role + same target name + exact=True
2. same role + same target name + exact=False
```

It does not cross roles, does not invent authority, and does not enable login/payment/contact/credential actions.

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_session_manager_l5_live.py
sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py
```

## Regression Test

Added:

```text
test_live_browser_session_falls_back_from_exact_role_name_to_fuzzy_same_role
```

The test first failed because the exact locator miss raised immediately. After the fix, it passes by retrying the same role/name with fuzzy matching.

## Validation

```text
py -3.13 -m pytest tests/test_browser_session_manager_l5_live.py::test_live_browser_session_falls_back_from_exact_role_name_to_fuzzy_same_role -q
result = passed

py -3.13 -m pytest tests/test_browser_session_manager_l5_live.py -q
result = 13 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 16 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 88 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result = 14 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py tests/operator/test_power_reconnection_decision_context_skill_frames.py tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
result = 65 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check
result = passed with CRLF warnings only
```

## Safety / Raw Material Scan

Targeted scan of changed files found no new raw provider output, reasoning, credential, cookie, session token, raw DOM, or profile-material persistence.

The scan returned only existing browser-session terms and test screenshot assertions already present in the L5 live test/module.

## Hard Boundaries Preserved

```text
payment / checkout / spend = still blocked
credential / secret access = still blocked
login / account mutation = still blocked unless special authority path is explicitly used
contact supplier / external send outside grant = not enabled
cookies/session/profile material persistence = not introduced
provider-native tools = not introduced
fallback/AUTO = not introduced
replay side effects = not introduced
```

## Remaining Product Truth

This fix is local proof only. It does not mark real Alibaba search actuation as product-proven.

Next prepared proof:

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V11_AFTER_CLOAK_L5_SEARCH_LOCATOR_FALLBACK
```

Expected honest outcomes:

```text
VALID_SUCCESS
VALID_FAILED
CONFIG_MISSING
```

