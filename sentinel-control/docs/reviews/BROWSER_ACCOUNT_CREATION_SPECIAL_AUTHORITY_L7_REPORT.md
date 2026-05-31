# Browser Account Creation Special Authority L7 Report

Date: 2026-05-31

Pack: `BROWSER_ACCOUNT_CREATION_SPECIAL_AUTHORITY_L7`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a browser account creation/onboarding special authority organ.
It supports account creation through an explicit backend protocol with service
policy, user approval refs, identity profile refs, credential session refs,
terms acknowledgement refs, boundary checkpoint linkage, receipts, and
FinalGate.

The default backend in this pack is fake/test-only. Real site-specific account
creation adapters remain separate.

## Models Implemented

```text
BrowserAccountCreationStatus
BrowserAccountCreationFinalGateDecision
BrowserAccountCreationContract
BrowserAccountCreationRequest
BrowserAccountCreationBackendResult
BrowserAccountCreationBackend
BrowserAccountCreationFakeBackend
BrowserAccountCreationReceipt
BrowserAccountCreationFinalGateCertificate
BrowserAccountCreationResult
BrowserAccountCreationFinalGate
BrowserAccountCreationOrganL7
render_browser_account_creation_receipt_as_untrusted_context
```

## Authority Coverage

Implemented:

- service allowlist;
- user approval ref requirement;
- identity profile ref requirement;
- credential session ref requirement;
- terms acknowledgement ref requirement;
- boundary checkpoint hash requirement;
- fake identity rejection;
- before/after evidence hashes;
- backend execution protocol;
- receipt and FinalGate certification.

## Boundaries Held

Rejected:

- fake identity request;
- missing user approval;
- missing identity profile ref;
- missing credential session ref;
- missing terms ack ref;
- missing boundary checkpoint;
- raw password/tool payload.

No added:

- AgentRuntime default wiring;
- real site account adapter;
- raw credential persistence;
- future-account approval by receipt.

## Tests

Added:

```text
tests/test_browser_account_creation_special_authority_l7.py
```

Focused tests:

```text
test_account_creation_executes_with_explicit_l7_authority_and_receipt
test_account_creation_blocks_fake_identity_missing_refs_and_kill_switch
test_account_creation_blocks_raw_password_or_tool_payload
test_account_creation_receipt_does_not_persist_raw_profile_or_credentials
test_account_creation_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Service policy | CLOSED | focused test | Exact service allowlist |
| Approval/profile/session refs | CLOSED | focused test | Metadata refs only |
| Fake identity rejection | CLOSED | focused test | No identity generation |
| Boundary checkpoint | CLOSED | focused test | Requires prior boundary hash |
| Raw password/tool blocking | CLOSED | focused test | No raw credential payloads |
| Backend protocol | CLOSED | focused test | Fake backend only |
| Receipt + FinalGate | CLOSED | focused test | Special-authority receipt |
| Real account adapter | NOT_STARTED | no provider adapter | Future connector pack |
| AgentRuntime account wiring | NOT_STARTED | no runtime change | Future opt-in pack |

## Next Pack

```text
BROWSER_OBSERVABILITY_AND_REPLAY_STUDIO_V1
```

This should build the full replay timeline across screenshots, DOM, AX,
network, console, traces, actions, receipts, and FinalGate decisions.

## Anti-Overclaim Statement

This pack does not claim live account creation on real websites. It locks the
L7 contract, backend protocol, receipt, and FinalGate structure that real
account-creation adapters must pass through.
