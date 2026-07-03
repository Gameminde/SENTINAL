# SENTINEL REAL POWER ATTEMPT 5K CLOAK READY SEARCH RELEVANT PRODUCT EXTRACTION V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1 = REAL_BROWSER_CONFIG_MISSING_PRE_PROVIDER
```

This is a valid pre-provider stop, not a consumed real-provider mission.

```text
provider_decision_calls = 0
browser_open_count = 0
search_attempt_count = 0
channel/external side effects = 0
```

## Source State

```text
source_commit = 827f7ffcabfb12efb36a34cda85034c33309b1c3
fix = FIX_CLOAK_SESSION_BOOTSTRAP_AND_PROVIDER_EMPTY_CONTENT_RECOVERY_V1
```

Unrelated pre-existing dirty docs were not staged or modified by this run report.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt5k-20260703-054145
```

Safe artifacts:

```text
safe/preflight.json
safe/cloak_readiness.json
```

No raw endpoint URL, raw browser URL, API key, Authorization value, provider body, provider output, reasoning, cookies, sessions, screenshots, or DOM are printed in this report.

## Preflight Safe Facts

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = provider_catalog_env_or_default
endpoint_hash = 348447b4f644bf44e903dd5220f7d37fb8041d806a66a73d56f83c4fd03383ea
credential_present = true
browser_target_present = false
safe_browser_origin_hash = empty
provider_native_tools_disabled = true
fallback_auto_disabled = true
```

Process/User environment presence check for browser config:

```text
SENTINEL_BROWSER_TEST_URL process_present = false
SENTINEL_BROWSER_TEST_URL user_present = false
SENTINEL_BROWSER_HEADLESS process_present = false
SENTINEL_BROWSER_HEADLESS user_present = false
```

Provider credential and endpoint config were present, but the bounded browser target was absent.

## Cloak Readiness Gate Result

The 5K readiness gate ran before any provider call:

```text
selected_backend_id = cloak_browser
actual_backend_id = empty
session_backend_kind = empty
ready = false
provider_call_allowed = false
failure_code = REAL_BROWSER_TEST_URL_CONFIG_MISSING
diagnostic_hash = 7277306ace747a29ff35906d834df3b3618de35a18f3deace59ec6afa2a9fa25
receipt_backend_match = false
profile_material_persisted = false
readiness_receipt_hash = empty
```

This proves the new readiness gate stopped the mission before provider consumption when the bounded browser target was missing.

## Provider / Browser Calls

```text
provider_decision_calls = 0
browser_open_count = 0
browser_search_count = 0
browser_extract_product_cards_count = 0
browser_verify_extraction_count = 0
summary_present = false
finish_present = false
mission_status = pre_provider_blocked
```

No real browser page was opened. No Cloak bootstrap/download was attempted because the required bounded target URL was absent.

## Replay

Replay is not materially applicable:

```text
material_browser_receipts = 0
provider_calls_delta = 0
browser_open_delta = 0
browser_search_delta = 0
browser_extract_delta = 0
receipt_write_delta = 0
```

Because no material action occurred, there is no no-react browser replay to prove beyond the zero-action artifact state.

## Safety Scan

Targeted scan over the 5K run root found:

```text
safety_scan_high_risk_hit_count = 0
credential/API key persistence = not found
Authorization persistence = not found
raw endpoint/browser URL persistence = not found
raw provider output/reasoning persistence = not found
cookies/session files = not found
screenshots/full DOM persistence = not found
provider-native tools = not used
fallback/AUTO = not used
```

The run root contains only the safe preflight/readiness JSON artifacts.

## Failure Classification

```text
primary_failure_classification = REAL_BROWSER_CONFIG_MISSING_PRE_PROVIDER
failure_code = REAL_BROWSER_TEST_URL_CONFIG_MISSING
```

This is not a product failure of the model, search skill, Cloak backend, provider, or extraction path. The bounded browser target was not available in the process or user environment, so the run stopped before provider use as intended.

## Required Local Step Before 5K Can Be Consumed

Set the bounded browser target locally without printing or committing values:

```text
SENTINEL_BROWSER_TEST_URL
SENTINEL_BROWSER_HEADLESS
```

Then rerun `REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1` once. The next consumed attempt must again start with the Cloak readiness gate before provider.

## Confirmation

```text
one provider mission consumed = no
provider call = no
real browser run = no
retry = no
fallback/AUTO = no
provider-native tools = no
push = no
merge = no
fake success = no
safe evidence only = yes
credentials/env printed = no
```
