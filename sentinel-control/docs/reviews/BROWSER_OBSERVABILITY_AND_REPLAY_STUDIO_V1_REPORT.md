# Browser Observability And Replay Studio V1 Report

Date: 2026-05-31

Pack: `BROWSER_OBSERVABILITY_AND_REPLAY_STUDIO_V1`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a browser observability and replay studio organ. It builds a
deterministic timeline from browser evidence surfaces: screenshots, DOM, AX,
network, console, actions, receipts, and FinalGate decisions.

The organ is metadata-only. It does not browse, click, submit, install
extensions, execute WebMCP tools, or persist raw page/network/console/screenshot
payloads.

## Models Implemented

```text
BrowserReplayEventKind
BrowserReplayStudioStatus
BrowserReplayStudioFinalGateDecision
BrowserReplayStudioContract
BrowserReplayStudioRequest
BrowserReplayTimelineItem
BrowserReplayTimeline
BrowserReplayStudioReceipt
BrowserReplayStudioFinalGateCertificate
BrowserReplayStudioResult
BrowserReplayStudioFinalGate
BrowserReplayStudioOrganV1
render_browser_replay_studio_receipt_as_untrusted_context
```

## Replay Coverage

Implemented:

- ordered timeline construction;
- screenshot evidence refs;
- DOM evidence refs;
- AX evidence refs;
- network evidence refs;
- console evidence refs;
- action refs;
- receipt refs;
- FinalGate certificate refs;
- deterministic timeline hash;
- deterministic replay hash;
- raw payload redaction and hash-only persistence.

## Boundaries Held

Rejected or not added:

- raw DOM persistence;
- raw console persistence;
- raw network response body persistence;
- raw screenshot byte persistence;
- browser submit/login/upload/download execution;
- extension/WebMCP execution;
- AgentRuntime default wiring;
- future authority granted by replay receipt.

## Tests

Added:

```text
tests/test_browser_observability_replay_studio_v1.py
```

Focused tests:

```text
test_replay_studio_builds_ordered_timeline_with_all_browser_surfaces
test_replay_studio_does_not_persist_raw_dom_network_console_or_screenshot
test_replay_studio_links_receipts_and_finalgate_refs
test_replay_studio_hash_is_deterministic
test_replay_studio_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Timeline construction | CLOSED | focused test | Evidence input only |
| Screenshot/DOM/AX/network/console refs | CLOSED | focused test | Hash-only |
| Receipt and FinalGate refs | CLOSED | focused test | Metadata refs |
| Deterministic replay hash | CLOSED | focused test | Stable sanitized inputs |
| Raw payload durability block | CLOSED | focused test | Redact/hash, do not persist raw |
| Data-not-instruction rendering | CLOSED | focused test | Untrusted context only |
| UI replay studio | NOT_STARTED | no UI code | Future observability UI pack |
| AgentRuntime replay wiring | NOT_STARTED | no runtime change | Future opt-in pack |

## Next Pack

```text
BROWSER_CONTROLLED_EXTENSION_AND_WEBMCP_BRIDGE_L7
```

This should add the late-stage extension/WebMCP/third-party browser tool bridge
behind special authority, sandboxing, receipts, strict provenance, and no direct
tool-as-authority path.

## Anti-Overclaim Statement

This pack does not claim a live replay UI or a live extension/WebMCP bridge. It
locks the browser evidence timeline, replay hashes, receipt, and FinalGate
structure that those future surfaces must feed.
