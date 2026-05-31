# Browser JavaScript Sandbox Special Authority L6 Report

Recorded at: 2026-05-31

Pack:

```text
BROWSER_ARBITRARY_JS_SANDBOX_SPECIAL_AUTHORITY_L6
```

## Current State

Sentinel now supports bounded page-side JavaScript execution in a live browser
session. This is not generic ambient script execution: the organ blocks network,
storage, cookie, submit, credential, eval/import, and similar surfaces before
execution.

The receipt stores only hashes for script and result.

## Models And Contracts Added

Implemented in:

```text
sentinel/agent/organs/browser_js_sandbox_special_authority_l6.py
```

Models:

- `BrowserJSSandboxStatus`
- `BrowserJSSandboxFinalGateDecision`
- `BrowserJSSandboxContract`
- `BrowserJSSandboxRequest`
- `BrowserJSSandboxSafetyValidationResult`
- `BrowserJSSandboxReceipt`
- `BrowserJSSandboxFinalGateCertificate`
- `BrowserJSSandboxResult`
- `BrowserJSSandboxFinalGate`
- `BrowserJSSandboxOrganL6`

## Execution Path

```text
mission authority
-> JS contract
-> forbidden JS surface scanner
-> existing live browser session
-> page.evaluate(...)
-> before/after browser evidence
-> script hash + result hash
-> receipt + FinalGate
```

## Boundaries Held

```text
Raw script persistence = BLOCKED
Raw result persistence = BLOCKED
fetch/XMLHttpRequest/WebSocket/sendBeacon = BLOCKED
document.cookie = BLOCKED
localStorage/sessionStorage = BLOCKED
form.submit = BLOCKED
credential/key/token/password markers = BLOCKED
eval/import/new Function = BLOCKED
payment/spend/trading = BLOCKED
```

## Truth Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Bounded DOM script execution | CLOSED | `test_l6_js_sandbox_executes_bounded_dom_script_with_hashes` | Existing live browser session required |
| Raw script/result durability block | CLOSED | `test_l6_js_sandbox_does_not_persist_raw_script_or_result` | Hashes only |
| Forbidden JS surfaces blocked | CLOSED | `test_l6_js_sandbox_blocks_network_storage_cookie_submit_and_credentials` | Conservative string scanner |
| Special authority required | CLOSED | `test_l6_js_sandbox_requires_special_authority` | Mission action/tool required |
| Payment/spend/trading | NOT_STARTED | Not implemented | L7 pack required |

## Verification

Fresh verification run during this pack:

```text
python -m pytest tests/test_browser_js_sandbox_special_authority_l6.py -q
python -m pytest tests/test_browser_js_sandbox_special_authority_l6.py tests/test_browser_download_upload_quarantine_l6.py tests/test_browser_login_credential_session_broker_l6.py tests/test_browser_form_submit_special_authority_l6.py tests/test_browser_trajectory_planner_l5.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py tests/test_organ_safety_scanner_consolidation.py -q
python -m pytest tests/test_browser_session_manager_l5_live.py tests/test_browser_operator_agent_l4_l5_live.py tests/test_agent_browser_operator_runtime_integration.py tests/test_agent_browser_operator_runtime_minicorpus.py -q
python -m pytest tests -k browser -q
```

Result:

```text
4 passed
24 passed
23 passed
31 passed
416 passed with -k browser
```

## Next Pack

```text
BROWSER_PAYMENT_SPEND_SPECIAL_AUTHORITY_L7
```

Payment/spend must be L7 with caps, human approval, receipts, revocation, and
hard kill-switch posture.
