# Browser DevTools Machine Intelligence V1 Report

Date: 2026-05-31

Pack: `BROWSER_DEVTOOLS_MACHINE_INTELLIGENCE_V1`

Status: `LOCKED`

## Executive Verdict

Sentinel now has the first DevTools machine-intelligence layer. It converts
browser/DevTools signal inputs into safe structured evidence:

- page target metadata;
- AX snapshot V2 refs;
- network ledger metadata;
- console ledger metadata;
- screenshot evidence hashes;
- evidence bundle hash;
- receipt and FinalGate certificate.

This is still not a live CDP/MCP backend. It is the safe intelligence bundle
that live backends must feed next.

## Models Implemented

```text
BrowserDevToolsMachineIntelligenceStatus
BrowserDevToolsMachineIntelligenceFinalGateDecision
BrowserDevToolsMachineIntelligenceContract
BrowserDevToolsMachineIntelligenceRequest
BrowserDevToolsPageTarget
BrowserDevToolsA11yRefV2
BrowserDevToolsA11ySnapshotV2
BrowserDevToolsNetworkLedger
BrowserDevToolsConsoleLedger
BrowserDevToolsScreenshotEvidence
BrowserDevToolsEvidenceBundle
BrowserDevToolsMachineIntelligenceReceipt
BrowserDevToolsMachineIntelligenceFinalGateCertificate
BrowserDevToolsMachineIntelligenceResult
BrowserDevToolsMachineIntelligenceFinalGate
BrowserDevToolsMachineIntelligenceOrgan
render_browser_devtools_machine_intelligence_receipt_as_untrusted_context
```

## Capability Added

The organ builds a safe evidence bundle:

```text
page_targets -> hashes/hosts only
snapshot_text -> AX refs with label hashes only
network_events -> method/status/resource metadata only
console_messages -> hashed message refs only
screenshot_bytes -> screenshot hash and byte count only
```

## Boundaries Held

No raw durable:

- page text;
- network body;
- auth headers;
- cookies;
- console text;
- screenshot bytes;
- credential values;
- MCP payloads.

Blocked:

- raw authorization headers;
- secret-like payloads;
- missing source backend receipt;
- authority expansion.

## Tests

Added:

```text
tests/test_browser_devtools_machine_intelligence_v1.py
```

Focused tests:

```text
test_machine_intelligence_builds_safe_evidence_bundle
test_machine_intelligence_does_not_persist_raw_page_network_console_or_screenshot
test_machine_intelligence_blocks_raw_auth_headers_and_secrets
test_machine_intelligence_requires_source_backend_receipt
test_machine_intelligence_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Page target metadata | CLOSED | `BrowserDevToolsPageTarget` | Hash/host metadata only |
| AX snapshot V2 | CLOSED | `BrowserDevToolsA11ySnapshotV2` | Text-derived foundation, live CDP next |
| Network ledger metadata | CLOSED | `BrowserDevToolsNetworkLedger` | No HAR/body capture |
| Console ledger metadata | CLOSED | `BrowserDevToolsConsoleLedger` | Hashes only |
| Screenshot evidence hash | CLOSED | `BrowserDevToolsScreenshotEvidence` | No image persistence in this pack |
| Evidence bundle hash | CLOSED | `BrowserDevToolsEvidenceBundle` | Structured data only |
| Receipt + FinalGate | CLOSED | focused tests | Metadata-only |
| Live CDP/MCP backend | NOT_STARTED | no backend invocation | Next backend integration pack |
| Orchestrator | NOT_STARTED | roadmap next | Next pack |

## Next Pack

```text
BROWSER_MULTI_STEP_TASK_ORCHESTRATOR_V1
```

This is where the browser organ becomes mission-capable:

```text
observe -> diagnose -> plan -> act -> verify -> recover -> continue
```

## Anti-Overclaim Statement

This pack does not claim live browser DevTools execution. It locks the
structured intelligence layer that can safely consume DevTools/CDP/MCP signals.
