# Browser Payment Spend Special Authority L7 Report

Date: 2026-05-31

Pack: `BROWSER_PAYMENT_SPEND_SPECIAL_AUTHORITY_L7`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a browser payment/spend special authority organ. It supports
bounded checkout/spend execution through an explicit backend protocol with
merchant policy, spend caps, spend authority refs, payment instrument refs,
boundary checkpoint linkage, kill switch, receipts, and FinalGate.

The default backend in this pack is fake/test-only. Real payment provider
adapters remain separate.

## Models Implemented

```text
BrowserPaymentSpendStatus
BrowserPaymentSpendFinalGateDecision
BrowserPaymentSpendContract
BrowserPaymentSpendRequest
BrowserPaymentBackendResult
BrowserPaymentBackend
BrowserPaymentFakeBackend
BrowserPaymentSpendReceipt
BrowserPaymentSpendFinalGateCertificate
BrowserPaymentSpendResult
BrowserPaymentSpendFinalGate
BrowserPaymentSpendOrganL7
render_browser_payment_spend_receipt_as_untrusted_context
```

## Authority Coverage

Implemented:

- allowed merchant policy;
- single spend cap;
- total spend cap;
- spend authority ref requirement;
- payment instrument ref requirement;
- payment instrument hash-only receipt;
- boundary checkpoint hash requirement;
- before/after evidence hashes;
- kill-switch block;
- backend execution protocol;
- receipt and FinalGate certification.

## Boundaries Held

Rejected:

- raw card number;
- CVV/CVC;
- raw payment token;
- raw card payload;
- unapproved merchant;
- over-cap spend;
- missing spend authority;
- missing boundary checkpoint;
- kill-switch engaged.

No added:

- AgentRuntime default wiring;
- real payment provider adapter;
- raw payment credential persistence;
- future-payment approval by receipt.

## Tests

Added:

```text
tests/test_browser_payment_spend_special_authority_l7.py
```

Focused tests:

```text
test_payment_spend_executes_with_explicit_l7_authority_and_receipt
test_payment_spend_blocks_over_cap_unapproved_merchant_missing_refs_and_kill_switch
test_payment_spend_blocks_raw_payment_credentials
test_payment_spend_receipt_does_not_persist_raw_instrument_or_payload
test_payment_spend_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Merchant policy | CLOSED | focused test | Exact merchant allowlist only |
| Spend caps | CLOSED | focused test | No cumulative store yet |
| Spend authority refs | CLOSED | focused test | Metadata refs only |
| Payment instrument refs | CLOSED | focused test | Hash-only, no raw values |
| Boundary checkpoint | CLOSED | focused test | Requires prior boundary pack hash |
| Kill switch | CLOSED | focused test | Contract-level kill switch |
| Backend protocol | CLOSED | focused test | Fake backend only |
| Receipt + FinalGate | CLOSED | focused test | Special-authority receipt |
| Real payment provider | NOT_STARTED | no provider adapter | Future connector pack |
| AgentRuntime payment wiring | NOT_STARTED | no runtime change | Future opt-in pack |

## Next Pack

```text
BROWSER_ACCOUNT_CREATION_SPECIAL_AUTHORITY_L7
```

This should add account creation/onboarding contracts, with no fake identity and
explicit handoff boundaries.

## Anti-Overclaim Statement

This pack does not claim live card processing or real provider integration. It
locks the L7 contract, backend protocol, receipt, and FinalGate structure that
real payment adapters must pass through.
