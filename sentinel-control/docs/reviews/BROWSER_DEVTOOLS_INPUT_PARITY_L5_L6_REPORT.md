# Browser DevTools Input Parity L5/L6 Report

Date: 2026-05-31

Pack: `BROWSER_DEVTOOLS_INPUT_PARITY_L5_L6`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a controlled browser input parity organ for the operator
actions that were missing after DevTools machine intelligence and failure
recovery.

The organ supports fast form fill, press-key, drag, coordinate click, and
dialog handling behind an explicit contract. It stores hashes and evidence
references, not raw field values.

## Models Implemented

```text
BrowserInputParityActionKind
BrowserInputParityStatus
BrowserInputParityFinalGateDecision
BrowserInputParityContract
BrowserInputParityRequest
BrowserInputParityBackendResult
BrowserInputParityBackend
BrowserInputParityFakeBackend
BrowserInputParityReceipt
BrowserInputParityFinalGateCertificate
BrowserInputParityResult
BrowserInputParityFinalGate
BrowserInputParityOrganL5L6
render_browser_input_parity_receipt_as_untrusted_context
```

## Action Coverage

Implemented:

- `fill_form`;
- `press_key`;
- `drag`;
- `click_at`;
- `handle_dialog`.

Blocked or out of scope:

- payment/spend;
- extension execution;
- WebMCP execution;
- raw credential input;
- raw field value durability.

## Evidence And Receipt Model

Every accepted request links:

- request id;
- mission id;
- URL hash;
- action kind;
- before evidence hash;
- after evidence hash;
- optional screenshot evidence hash;
- input payload hash;
- FinalGate certificate.

`click_at` requires screenshot evidence binding because coordinate clicks are
unsafe without visual context.

## Boundaries Held

No added:

- AgentRuntime default wiring;
- live CDP/MCP invocation;
- generic browser submit;
- credential persistence;
- payment/spend execution;
- extension/WebMCP execution.

Raw field values are hashed in the safe payload and are not durable in the
result or receipt.

## Tests

Added:

```text
tests/test_browser_devtools_input_parity_l5_l6.py
```

Focused tests:

```text
test_input_parity_executes_fill_form_and_press_key_with_hashes_only
test_input_parity_executes_drag_click_at_and_handle_dialog
test_input_parity_blocks_click_at_without_screenshot_binding
test_input_parity_blocks_forbidden_payloads_and_sensitive_actions
test_input_parity_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Fill form parity | CLOSED | focused test | Backend is fake protocol implementation |
| Press key parity | CLOSED | focused test | Backend is fake protocol implementation |
| Drag parity | CLOSED | focused test | Backend is fake protocol implementation |
| Click-at parity | CLOSED | focused test | Requires screenshot binding |
| Dialog handling parity | CLOSED | focused test | Backend is fake protocol implementation |
| Hash-only input payload | CLOSED | focused test | No raw field values durable |
| Receipt + FinalGate | CLOSED | focused test | Metadata only |
| Live CDP/MCP backend invocation | NOT_STARTED | no wiring in this pack | Backend adapter pack remains the boundary |
| AgentRuntime input parity wiring | NOT_STARTED | no runtime change | Future orchestration pack |

## Next Pack

```text
BROWSER_VISUAL_GROUNDING_OCR_V1
```

This should add screenshot/OCR/bounding-box grounding so Sentinel can work on
pages where DOM and accessibility trees are incomplete, deceptive, or
insufficient.

## Anti-Overclaim Statement

This pack does not claim a complete live DevTools operator yet. It locks the
input parity contract, receipt, and FinalGate layer that a live CDP/MCP backend
can later execute through.
