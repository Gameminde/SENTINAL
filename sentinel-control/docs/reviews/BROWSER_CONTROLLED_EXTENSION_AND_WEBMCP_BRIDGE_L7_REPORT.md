# Browser Controlled Extension And WebMCP Bridge L7 Report

Date: 2026-05-31

Pack: `BROWSER_CONTROLLED_EXTENSION_AND_WEBMCP_BRIDGE_L7`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a controlled L7 bridge boundary for browser extensions, WebMCP,
and third-party browser tools. The bridge requires explicit L7 authority,
provenance, sandbox refs, allowed surface/origin/tool policy, before/after
evidence hashes, receipts, and FinalGate.

The default backend in this pack is fake/test-only. Live extension execution,
live MCP adapters, and raw CDP transport remain separate implementation packs.

## Models Implemented

```text
BrowserExtensionBridgeSurface
BrowserExtensionBridgeStatus
BrowserExtensionBridgeFinalGateDecision
BrowserExtensionBridgeContract
BrowserExtensionBridgeRequest
BrowserExtensionBridgeBackendResult
BrowserExtensionBridgeBackend
BrowserExtensionBridgeFakeBackend
BrowserExtensionBridgeReceipt
BrowserExtensionBridgeFinalGateCertificate
BrowserExtensionBridgeResult
BrowserExtensionBridgeFinalGate
BrowserExtensionBridgeOrganL7
render_browser_extension_bridge_receipt_as_untrusted_context
```

## Authority Coverage

Implemented:

- L7 authority ref requirement;
- provenance ref requirement;
- sandbox ref requirement;
- allowed surface policy;
- allowed tool origin policy;
- allowed tool name policy;
- before/after evidence hashes;
- backend execution protocol;
- hash-only tool payload receipts;
- hash-only provider output receipts;
- receipt and FinalGate certification.

## Boundaries Held

Rejected or not added:

- raw CDP surface in v1;
- direct WebMCP/tool authority;
- raw tool payload durability;
- credential payloads;
- authority expansion by bridge receipt;
- live extension adapter;
- live MCP adapter;
- AgentRuntime default wiring.

## Tests

Added:

```text
tests/test_browser_controlled_extension_webmcp_bridge_l7.py
```

Focused tests:

```text
test_extension_webmcp_bridge_executes_with_explicit_l7_authority_and_receipt
test_extension_webmcp_bridge_blocks_missing_l7_authority_provenance_or_sandbox
test_extension_webmcp_bridge_blocks_unapproved_surface_origin_or_tool
test_extension_webmcp_bridge_blocks_raw_tool_payload_credentials_and_authority_expansion
test_extension_webmcp_bridge_receipt_does_not_persist_raw_tool_payload_or_provider_output
test_extension_webmcp_bridge_rendering_is_data_not_instruction
```

Targeted result:

```text
6 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| L7 authority/provenance/sandbox refs | CLOSED | focused tests | Metadata refs |
| Surface/origin/tool allowlist | CLOSED | focused tests | Exact policy only |
| Hash-only tool payload/output | CLOSED | focused tests | No raw payload persistence |
| Bridge backend protocol | CLOSED | focused tests | Fake backend only |
| Receipt + FinalGate | CLOSED | focused tests | Bridge-scoped certification |
| Direct WebMCP authority | REJECTED | focused tests | Tools cannot grant permission |
| Live extension adapter | NOT_STARTED | no live adapter | Future connector pack |
| Live MCP adapter | NOT_STARTED | no MCP adapter | Future connector pack |
| AgentRuntime bridge wiring | NOT_STARTED | no runtime change | Future opt-in pack |

## Next Pack

```text
BROWSER_FINAL_CAPABILITY_LOCK
```

This should run the heavy browser organ audit, lock the final roadmap state,
summarize the implemented power surface, identify remaining live-adapter gaps,
and prove the package through tests and scans.

## Anti-Overclaim Statement

This pack does not claim live extension execution or live MCP tool execution.
It locks the L7 authority boundary, provenance/sandbox requirements, backend
protocol, receipt, and FinalGate structure that live bridges must pass through.
