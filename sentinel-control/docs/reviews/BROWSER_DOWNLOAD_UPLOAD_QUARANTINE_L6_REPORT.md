# Browser Download Upload Quarantine L6 Report

Recorded at: 2026-05-31

Pack:

```text
BROWSER_DOWNLOAD_UPLOAD_QUARANTINE_L6
```

## Current State

Sentinel now supports browser file upload and browser file download only through
explicit quarantine controls. This is not ambient file access.

Upload requires an approved local upload root. Download requires a quarantine
root. Both produce file hashes, before/after browser evidence, receipts, and
FinalGate certificates.

## Models And Contracts Added

Implemented in:

```text
sentinel/agent/organs/browser_download_upload_quarantine_l6.py
```

Models:

- `BrowserFileQuarantineActionKind`
- `BrowserFileQuarantineStatus`
- `BrowserFileQuarantineFinalGateDecision`
- `BrowserFileQuarantineContract`
- `BrowserFileQuarantineRequest`
- `BrowserFileQuarantineSafetyValidationResult`
- `BrowserFileQuarantineReceipt`
- `BrowserFileQuarantineFinalGateCertificate`
- `BrowserFileQuarantineResult`
- `BrowserFileQuarantineFinalGate`
- `BrowserFileQuarantineOrganL6`

## Execution Path

Upload:

```text
approved upload root
-> path containment proof
-> file hash
-> browser file input
-> before/after browser evidence
-> receipt + FinalGate
```

Download:

```text
browser download event
-> quarantine root
-> safe filename
-> file hash
-> before/after browser evidence
-> receipt + FinalGate
```

## Boundaries Held

```text
Upload outside approved root = BLOCKED
Download outside quarantine root = BLOCKED
Executable upload extension = BLOCKED
Provider/backend/model override = BLOCKED
Raw downloaded body in receipt = BLOCKED
Raw upload body in receipt = BLOCKED
Payment/spend/trading = BLOCKED
Arbitrary JavaScript = BLOCKED
```

## Truth Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Upload quarantine | CLOSED | `test_l6_uploads_only_from_approved_root_with_file_hash` | Uses existing live browser session |
| Upload path containment | CLOSED | `test_l6_blocks_upload_outside_approved_root` | Approved root must be explicit |
| Download quarantine | CLOSED | `test_l6_downloads_only_to_quarantine_with_hash` | Browser context must be opened with downloads enabled |
| Unsafe payload block | CLOSED | `test_l6_file_quarantine_blocks_provider_override_and_raw_secret_paths` | Scanner remains conservative |
| Arbitrary JavaScript | NOT_STARTED | No JS sandbox organ added | Next pack |
| Payment upload/download | NOT_STARTED | Not supported | Separate payment authority needed |

## Verification

Fresh verification run during this pack:

```text
python -m pytest tests/test_browser_download_upload_quarantine_l6.py -q
python -m pytest tests/test_browser_download_upload_quarantine_l6.py tests/test_browser_login_credential_session_broker_l6.py tests/test_browser_form_submit_special_authority_l6.py tests/test_browser_trajectory_planner_l5.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py tests/test_organ_safety_scanner_consolidation.py -q
python -m pytest tests/test_browser_session_manager_l5_live.py tests/test_browser_operator_agent_l4_l5_live.py tests/test_agent_browser_operator_runtime_integration.py tests/test_agent_browser_operator_runtime_minicorpus.py -q
python -m pytest tests -k browser -q
```

Result:

```text
4 passed
20 passed
23 passed
31 passed
412 passed with -k browser
```

## Next Pack

```text
BROWSER_ARBITRARY_JS_SANDBOX_SPECIAL_AUTHORITY_L6
```

The next browser pack should add a constrained JavaScript sandbox for DOM
inspection and bounded page-side operations, not arbitrary ambient script
execution.
