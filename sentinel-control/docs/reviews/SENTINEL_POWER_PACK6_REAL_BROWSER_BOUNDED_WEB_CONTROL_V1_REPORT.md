# SENTINEL POWER PACK 6 REAL BROWSER BOUNDED WEB CONTROL V1 REPORT

## Verdict

`POWER_PACK_6_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1 = LOCALLY_COMMITTED_IMPLEMENTED_CANDIDATE`

Implementation commit:

```text
7393ea7c468e50c52bd18be49341665e97b920d0
```

Provider calls during implementation:

```text
0
```

Push:

```text
not performed
```

## Pack 5 Accepted State

Pack 5 proved the first real bounded outbound channel path:

```text
mission-level grant
-> real model send_message
-> Telegram transport send exactly once
-> delivery receipts
-> model finish
-> replay no-resend
```

Power Pack 6 continues the same product direction:

```text
power first
receipts always
model leads inside granted scope
Sentinel blocks only boundary violations
```

## Power Added

Pack 6 adds a bounded real browser control capability:

```text
capability_id = real_browser_control
```

Supported actions:

```text
real_browser.open
real_browser.observe
real_browser.click
real_browser.type_text
real_browser.select_option
real_browser.assert_text
real_browser.extract_text
```

This is not the older synthetic browser fixture. The runtime now has a real browser engine seam and a Playwright-backed engine builder when the environment is configured.

## Engine Selected

Implementation includes:

```text
PlaywrightRealBrowserEngine
build_playwright_real_browser_engine_from_env
```

Local dependency preflight showed:

```text
playwright importable = true
```

Runtime config names:

```text
SENTINEL_BROWSER_TEST_URL
SENTINEL_BROWSER_HEADLESS
```

If `SENTINEL_BROWSER_TEST_URL` is missing, the engine builder fails before browser/provider work with:

```text
REAL_BROWSER_TEST_URL_CONFIG_MISSING
```

Raw URL values are not persisted in receipts. Receipts carry bounded URL refs and origin hashes only.

## Adapter Design

New modules:

```text
sentinel/operator/real_browser_control_models.py
sentinel/operator/real_browser_control_runtime.py
sentinel/operator/real_browser_control_replay.py
```

The runtime uses an injectable engine protocol:

```text
open
observe
click
type_text
select_option
assert_text
extract_text
```

Tests use `InMemoryRealBrowserEngine` for deterministic fake-local engine behavior. Real attempts use `PlaywrightRealBrowserEngine` when bounded URL config is present.

## Stable Refs

Observation receipts expose bounded stable element snapshots:

```text
ref
role
name
visible
enabled
text_preview
value_preview
```

The Playwright engine prefers `data-sentinel-ref` when present and otherwise derives bounded role/name refs. The model is expected to act through stable refs rather than raw DOM selectors.

## Receipts And Replay Model

New receipt/certificate models:

```text
RealBrowserOpenReceipt
RealBrowserObservationReceipt
RealBrowserActionReceipt
RealBrowserAssertionReceipt
RealBrowserFinalCertificate
RealBrowserControlReplayView
```

Receipt fields are structure-only:

```text
browser_session_ref
bounded_url_ref
safe_url_origin_hash
page title hash or bounded title
stable element ref
action kind
before/after state hash
assertion result
receipt hash
```

The replay view proves no material replay:

```text
browser_open_delta = 0
browser_observe_delta = 0
browser_click_delta = 0
browser_type_delta = 0
browser_select_delta = 0
browser_assert_delta = 0
browser_extract_delta = 0
receipt_writes_delta = 0
artifact_hashes_stable = true
browser_state_hash_stable = true
```

Replay does not reopen, click, type, select, assert, or extract again.

## Generic Loop Semantics

`DecisionContextCompiler` now recognizes `real_browser_control` as its own mode.

Loop guidance:

```text
not started -> real_browser.open
opened -> real_browser.observe
observed -> real_browser.type_text / click / select_option
state changed -> real_browser.assert_text / extract_text
assertion passed -> sentinel_loop.finish
```

Premature finish after a browser state-changing action but before assertion blocks with:

```text
MODEL_FINISH_BEFORE_REAL_BROWSER_ASSERTION
```

If material budget is reached after a real browser action but before assertion, the loop permits a bounded assertion-only turn. After successful assertion, it permits a finish-only turn.

## Boundaries Preserved

Pack 6 does not add:

```text
arbitrary open internet browsing
credentialed browser profiles
cookie/session persistence
password persistence
payment/account actions
desktop-wide control
provider-native tools
fallback/AUTO
```

Runtime still requires:

```text
allowed_tools includes real_browser_control
allowed_actions include the specific real_browser action
allowed_domains includes real_browser:bounded_test_url
```

## Raw Material Persistence

Tests and targeted scans verified no persistence of:

```text
raw provider output
raw provider reasoning
credentials
Authorization
cookies
session tokens
browser profile material
full raw DOM
typed text payloads in receipts
```

The targeted scan only found benign deny-list/test assertion strings.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result: 8 passed

py -3.13 -m pytest tests/operator/test_power_pack5_real_channel_transport_send.py -q
result: 11 passed

py -3.13 -m pytest tests/operator/test_power_pack4_browser_computer_control.py -q
result: 6 passed

py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
result: 19 passed

py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py -q
result: 6 passed

py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
result: 7 passed

py -3.13 -m pytest tests/test_real_model_read_only_operator_production_spine_v1.py -q
result: 48 passed

py -3.13 -m compileall sentinel/operator/real_browser_control_models.py sentinel/operator/real_browser_control_runtime.py sentinel/operator/real_browser_control_replay.py sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/model_led_task_loop.py
result: passed

git diff --check
result: passed
```

Targeted scan:

```text
API key / Authorization / raw prompt / raw response / raw reasoning / reasoning_content / provider wrapper payload / fallback-AUTO / provider-native tools
result: only benign deny-list and test assertion strings
```

## Git Status

After implementation commit, before report commit:

```text
branch = experimental/real-model-lab-freeze-v1
working tree = report file only
push = not performed
```

## Recommended Real Attempt

Proceed after report commit with exactly one preflighted real attempt:

```text
REAL_POWER_ATTEMPT_5_MODEL_LED_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1
```

If provider or browser URL config is missing, stop before provider/browser action and report:

```text
CONFIG_MISSING
REAL_BROWSER_TEST_URL_CONFIG_MISSING
REAL_BROWSER_ENGINE_CONFIG_MISSING
```

If configured, the product proof target is:

```text
real model opens bounded browser page
-> observes stable refs
-> chooses click/type/select action
-> browser state changes
-> asserts state
-> emits sentinel_loop.finish
-> replay no reopen / no click / no type / no assert
```

Success recommendation:

```text
START_POWER_PACK_7_MULTI_POWER_MISSION_WEB_TO_CHANNEL_V1
```

## Confirmation

```text
provider call during Pack 6 implementation = 0
external live browser attempt during implementation = 0
fallback/AUTO introduced = no
provider-native tools introduced = no
push performed = no
```
