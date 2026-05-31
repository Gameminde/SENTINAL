# Browser DevTools Backend Adapter Foundation V1 Report

Date: 2026-05-31

Pack: `BROWSER_DEVTOOLS_BACKEND_ADAPTER_FOUNDATION_V1`

Status: `LOCKED`

## Executive Verdict

Sentinel now has the canonical DevTools backend adapter foundation.

This pack does not add live Chrome DevTools execution yet. It creates the
Sentinel-native boundary that future native CDP and MCP transports must obey.

The important decision is architectural:

```text
MCP/CDP can be backend transport.
MCP/CDP cannot be Sentinel authority.
```

## Models Implemented

```text
BrowserDevToolsCapability
BrowserDevToolsStatus
BrowserDevToolsFinalGateDecision
BrowserDevToolsContract
BrowserDevToolsRequest
BrowserDevToolsBackendPayload
BrowserDevToolsBackend
BrowserDevToolsFakeBackend
BrowserDevToolsReceipt
BrowserDevToolsFinalGateCertificate
BrowserDevToolsResult
BrowserDevToolsFinalGate
BrowserDevToolsAdapter
render_browser_devtools_receipt_as_untrusted_context
```

## Contract Semantics

`BrowserDevToolsContract` requires:

- mission scope;
- allowed domains;
- explicit allowed capabilities;
- receipts;
- FinalGate posture;
- data-not-instruction posture;
- authority effect = none;
- execution effect = none at contract level.

It rejects:

- raw MCP tool calls;
- extension execution;
- third-party tool execution;
- WebMCP tool execution;
- payment/spend;
- authority expansion;
- delegated lane creation.

## Backend Semantics

The adapter accepts a backend object behind the Sentinel interface.

Current backends:

```text
BrowserDevToolsFakeBackend = deterministic test/backend shape
None backend = fail closed
```

Future backends:

```text
native_cdp
mcp_adapter
cloakbrowser_devtools_bridge
```

## Receipt Semantics

Receipts contain:

- mission id;
- request id;
- backend kind;
- capability;
- status;
- URL hash;
- output hash;
- optional snapshot/screenshot/network/console/performance hashes;
- page target count;
- blocked reason;
- safe summary;
- authority effect = none;
- data_not_instruction = true.

Receipts do not contain:

- raw browser body;
- raw snapshot text;
- raw screenshot bytes;
- raw network headers;
- raw console payloads;
- raw MCP tool payloads;
- raw credential material.

## FinalGate Semantics

`BrowserDevToolsFinalGate` is metadata-only.

It certifies:

- safe success receipts;
- honest blocked receipts;
- data-not-instruction posture;
- no authority expansion.

It rejects:

- unsafe receipt payloads;
- authority effect drift;
- future authority flags.

## Tests

Added:

```text
tests/test_browser_devtools_backend_adapter_foundation_v1.py
```

Focused tests:

```text
test_devtools_contract_is_metadata_not_authority
test_missing_devtools_backend_fails_closed_with_safe_receipt
test_fake_devtools_backend_returns_hash_only_snapshot_receipt
test_direct_mcp_tool_name_cannot_expand_authority
test_l7_extension_third_party_and_webmcp_are_deferred
test_devtools_receipt_rendering_is_data_not_instruction
```

Targeted result:

```text
6 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| DevTools backend interface | CLOSED | `BrowserDevToolsBackend` protocol | No native CDP implementation yet |
| DevTools request/contract | CLOSED | contract/request validators | Foundation only |
| Missing backend fail-closed | CLOSED | focused test | No live backend invocation |
| Fake backend hash-only output | CLOSED | focused test | Deterministic backend only |
| Receipt model | CLOSED | `BrowserDevToolsReceipt` | Metadata/hashes only |
| FinalGate model | CLOSED | `BrowserDevToolsFinalGate` | Metadata-only |
| Raw MCP authority rejection | CLOSED | focused test | No raw MCP runtime |
| Extension/WebMCP/third-party deferral | CLOSED | focused test | L7 bridge later |
| Runtime default behavior | CLOSED | no AgentRuntime wiring changed | opt-in wiring later |

## Next Pack

```text
BROWSER_DEVTOOLS_MACHINE_INTELLIGENCE_V1
```

This should implement the first real DevTools intelligence bundle:

- page target manager;
- AX snapshot V2 with UID/ref binding;
- safe network ledger metadata;
- safe console ledger metadata;
- screenshot/snapshot evidence bundle;
- no raw auth headers;
- no raw secrets.

## Anti-Overclaim Statement

This pack does not claim:

- live CDP connection;
- live MCP server invocation;
- live DevTools browser control;
- extension/WebMCP execution;
- payment/spend execution.

It only locks the Sentinel-native boundary that those powers must pass through.
