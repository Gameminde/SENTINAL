# SENTINEL_FIX_BROWSER_BACKEND_SELECTION_BRIDGE_AND_SEARCH_ACTUATION_V1_REPORT

## Verdict

```text
FIX_BROWSER_BACKEND_SELECTION_BRIDGE_AND_SEARCH_ACTUATION_V1 = IMPLEMENTED_CANDIDATE
provider_calls = 0
real_browser_runs = 0
push = not performed
```

This fix responds to the accepted 5D failure:

```text
REAL_POWER_ATTEMPT_5D = VALID_FAILED
primary_failure_classification = PLAYWRIGHT_COMPAT_ONLY_RUNTIME_GAP
secondary = SEARCH_ACTUATION_FAILURE, PROVIDER_DECISION_FAILURE
```

## Root Cause

Pack 6D exposed a model-facing browser backend frame that could prefer the Cloak/session backend, but `RealBrowserControlRuntime` had no execution-time backend selection contract. The actual runtime could still execute through `PlaywrightRealBrowserEngine` without declaring Playwright compatibility as the selected backend.

Search recovery also stayed too low-power: a recoverable search actuation failure could send the next model turn back toward observe/search even when the browser world model already held actionable product/result cards.

## Runtime Changes

`RealBrowserControlRuntime` now records and validates:

```text
actual_backend_id
selected_backend_id
browser_backend_selection
```

If the execution engine is Playwright and a backend frame is available:

```text
preferred_backend = cloak_browser
actual_backend = playwright_real_browser_engine
selected_backend missing
=> real_browser_backend_selection_mismatch
```

To use Playwright under a Cloak-preferred frame, the caller must explicitly declare:

```text
selected_backend_id = playwright_real_browser_engine
```

The runtime also adds a safe `browser_backend_execution` context card with backend ids and selection reason only. It does not persist endpoint values, cookies, sessions, screenshots, DOM dumps, provider output, or reasoning.

## Search Recovery Change

Browser actionability recovery is now card-aware:

```text
actionable product/result cards present
-> recommend extract_product_cards
-> recommend verify_extraction
-> then observe
```

If no actionable cards exist, the normal recovery lane remains:

```text
observe
search
extract_product_cards
```

This prevents repeated recoverable search failures from trapping the loop in open/search/open/search when the page already contains extraction-ready product evidence.

## Power Preservation

The fix does not add a registry-only layer. It affects actual runtime construction and execution context. It keeps the model-facing browser path skill-first while forcing execution truth:

```text
model sees browser skill backend
runtime must execute through the selected backend
or block before pretending compatibility
```

## Hard Stops Preserved

Unchanged:

```text
login/contact/payment/credential boundaries
bounded URL requirement
secret field block
no provider-native tools
no fallback/AUTO
no raw DOM/cookies/session/screenshots/provider reasoning persistence
no fake success
```

## Tests Added

```text
test_backend_frame_preferred_cloak_must_match_actual_backend_or_block
test_playwright_actual_engine_requires_explicit_compatibility_selection
test_real_browser_search_material_receipt_when_backend_actuates
test_search_recoverable_failure_updates_decision_context
test_two_search_failures_with_product_cards_recommends_extract_not_repeat_search
test_extract_product_cards_can_run_from_existing_world_model_cards
test_finish_available_after_verify_extraction_and_summary
```

Existing replay coverage remains:

```text
test_browser_replay_no_reopen_no_reclick_no_retype_no_resubmit_no_reextract
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 24 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result = 14 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result = 8 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py -q
result = 5 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
result = passed

git diff --check
result = passed with CRLF conversion warnings only
```

## Targeted Scan

Targeted scan over the changed runtime, tests, and this report found only benign guard/test/report strings:

```text
real_browser_control_runtime.py sensitive-text rejection markers:
authorization
bearer
raw_prompt
raw_response
raw_reasoning
reasoning_content

test_power_pack6d_browser_skill_spine.py no-raw-persistence assertion markers:
raw_provider
reasoning_content
session_token
screenshot
<html
<body

report negative confirmations:
no provider-native tools
no fallback/AUTO
no raw DOM/cookies/session/screenshots/provider reasoning persistence
```

No credential values, endpoint values, raw provider payloads, cookies, sessions, screenshots, DOM dumps, provider-native tool enablement, or fallback/AUTO enablement were added.

## Commit

```text
commit = 59012e7 fix: bridge browser backend selection to runtime
```

## Next

Do not run `REAL_POWER_ATTEMPT_5E` without explicit user approval.
