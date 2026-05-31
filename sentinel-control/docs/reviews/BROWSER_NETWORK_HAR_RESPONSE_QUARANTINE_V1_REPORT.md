# Browser Network HAR Response Quarantine V1 Report

Date: 2026-05-31

Pack: `BROWSER_NETWORK_HAR_RESPONSE_QUARANTINE_V1`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a HAR-style browser network evidence organ. It captures safe
request/response metadata, redacts auth headers, hashes URLs and header values,
and quarantines response bodies only when explicitly allowed by contract.

This gives the browser stack network awareness without turning network bodies
or auth headers into durable prompt material.

## Models Implemented

```text
BrowserHARStatus
BrowserHARFinalGateDecision
BrowserHARContract
BrowserHARRequest
BrowserHARRecord
BrowserHARQuarantinedBody
BrowserHARLedger
BrowserHARReceipt
BrowserHARFinalGateCertificate
BrowserHARResult
BrowserHARFinalGate
BrowserHAROrganV1
render_browser_har_receipt_as_untrusted_context
```

## HAR Coverage

Implemented:

- URL hash metadata;
- host/method/status/mime metadata;
- request/response header hashes;
- auth/cookie header redaction;
- status and method buckets;
- failure count;
- response body quarantine refs when explicitly allowed;
- receipt and FinalGate certification.

## Quarantine Model

Response bodies are rejected unless `allow_response_body_quarantine = true`.
When allowed, the organ stores:

- body hash;
- byte count;
- mime type;
- quarantine ref.

It does not store the raw response body.

## Boundaries Held

No added:

- live CDP/MCP HAR collection;
- AgentRuntime default wiring;
- raw auth header durability;
- raw response body durability;
- browser submit/login/payment;
- extension/WebMCP execution.

## Tests

Added:

```text
tests/test_browser_network_har_response_quarantine_v1.py
```

Focused tests:

```text
test_har_capture_builds_safe_request_response_metadata
test_har_capture_blocks_response_body_without_quarantine_authority
test_har_capture_quarantines_allowed_response_body_as_hash_only
test_har_capture_redacts_auth_headers_without_raw_header_durability
test_har_capture_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| HAR metadata ledger | CLOSED | focused test | Entries supplied by future backend |
| URL/header hashing | CLOSED | focused test | Hash metadata only |
| Auth/cookie redaction | CLOSED | focused test | Counts only, no raw names/values |
| Body quarantine contract | CLOSED | focused test | No body writes in this pack |
| Body hash-only refs | CLOSED | focused test | Quarantine ref metadata only |
| Receipt + FinalGate | CLOSED | focused test | Certification data only |
| Live HAR collection | NOT_STARTED | no backend in this pack | Future CDP/MCP backend work |
| AgentRuntime HAR wiring | NOT_STARTED | no runtime change | Future browser orchestration pack |

## Next Pack

```text
BROWSER_BENCHMARK_GAUNTLET_WEB_ARENA_STYLE
```

This should create the browser benchmark gauntlet for multi-page workflows,
broken selectors, authorized login, upload/download, JS sandbox, recovery, and
score regression.

## Anti-Overclaim Statement

This pack does not claim live HAR capture. It locks the HAR metadata,
quarantine, receipt, and FinalGate layer that live CDP/MCP network collection
can later feed.
