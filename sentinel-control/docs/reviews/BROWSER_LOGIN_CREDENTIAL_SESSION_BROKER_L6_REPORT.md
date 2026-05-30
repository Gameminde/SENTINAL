# Browser Login Credential Session Broker L6 Report

Recorded at: 2026-05-31

Pack:

```text
BROWSER_LOGIN_CREDENTIAL_SESSION_BROKER_L6
```

## Current State

Sentinel now has a browser login organ that can use credential values at
execution time without storing raw credential material in model output, memory,
receipts, certificates, or artifacts.

This is not a durable vault. The pack uses existing credential grant metadata
and a deliberately ephemeral value provider. The real secret backend remains a
separate pack.

## Models And Contracts Added

Implemented in:

```text
sentinel/agent/organs/browser_login_credential_session_broker_l6.py
```

Models:

- `BrowserCredentialValueProvider`
- `EphemeralBrowserCredentialProvider`
- `BrowserLoginCredentialSessionStatus`
- `BrowserLoginCredentialSessionFinalGateDecision`
- `BrowserLoginCredentialSessionContract`
- `BrowserLoginCredentialSessionRequest`
- `BrowserLoginCredentialSessionSafetyValidationResult`
- `BrowserLoginCredentialSessionReceipt`
- `BrowserLoginCredentialSessionFinalGateCertificate`
- `BrowserLoginCredentialSessionResult`
- `BrowserLoginCredentialSessionFinalGate`
- `BrowserLoginCredentialSessionBrokerL6`

## Credential Flow

The organ requires:

- mission tool `browser_login_credential_session_broker_l6`;
- mission action `browser_login_credential_session`;
- scoped `CredentialGrant` entries for username and password refs;
- domain scope match;
- action level `L6`;
- action scope `browser_login_credential_session`;
- ephemeral value provider at execution time.

`evaluate_credential_access(...)` produces metadata-only
`CredentialAccessProof` objects. The ephemeral value provider supplies actual
values only in memory for the immediate browser interaction.

## Execution Path

```text
mission authority + credential grants
-> credential access evaluation
-> metadata-only credential proofs
-> ephemeral value resolution
-> persistent browser session fills login fields
-> submit button click
-> before/after screenshots and AX hashes
-> login receipt
-> login FinalGate certificate
```

## Boundaries Held

```text
Raw credential persistence = BLOCKED
Credential values in receipts = BLOCKED
Credential values in memory = BLOCKED
Credential values in artifacts = BLOCKED
Missing grant = BLOCKED
Revoked grant = BLOCKED
Expired grant = BLOCKED
Scope mismatch = BLOCKED
Payment/upload fields = BLOCKED
Provider/backend/model override = BLOCKED
Arbitrary JavaScript = BLOCKED
Payment/spend/trading = BLOCKED
```

## Truth Table

| Segment | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Credential-backed login | CLOSED | `test_l6_login_uses_scoped_credential_refs_and_preserves_evidence` | Uses existing live browser session |
| Raw credential durability block | CLOSED | `test_l6_login_does_not_persist_raw_credentials` | Ephemeral provider only |
| Missing/revoked/expired grant block | CLOSED | `test_l6_login_blocks_missing_revoked_and_expired_grants` | Durable vault remains separate |
| Payment/upload/provider override block | CLOSED | `test_l6_login_blocks_payment_upload_or_provider_override` | Conservative scanner remains active |
| Sensitive non-login page block | CLOSED | `test_l6_login_blocks_sensitive_page_even_with_safe_note` | Payment fields require separate L7/payment pack |
| Durable credential vault | NOT_STARTED | No storage backend added | Next credential infrastructure pack |
| Upload/download handling | NOT_STARTED | Still blocked | Next browser pack |

## Verification

Fresh verification run during this pack:

```text
python -m pytest tests/test_browser_login_credential_session_broker_l6.py -q
python -m pytest tests/test_browser_login_credential_session_broker_l6.py tests/test_browser_form_submit_special_authority_l6.py tests/test_browser_trajectory_planner_l5.py -q
python -m pytest tests/test_sentinel_power_lab_runtime_v0.py tests/test_organ_safety_scanner_consolidation.py -q
python -m pytest tests/test_browser_session_manager_l5_live.py tests/test_browser_operator_agent_l4_l5_live.py tests/test_agent_browser_operator_runtime_integration.py tests/test_agent_browser_operator_runtime_minicorpus.py -q
python -m pytest tests -k browser -q
```

Result:

```text
5 passed
16 passed
23 passed
31 passed
408 passed with -k browser
```

## Next Pack

```text
BROWSER_DOWNLOAD_UPLOAD_QUARANTINE_L6
```

The next browser pack should add upload/download through quarantine, path
containment, MIME/extension scanning, hashes, user-visible receipts, and explicit
MissionAuthorityEnvelope grants.
