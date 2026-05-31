# Browser Visual Grounding OCR V1 Report

Date: 2026-05-31

Pack: `BROWSER_VISUAL_GROUNDING_OCR_V1`

Status: `LOCKED`

## Executive Verdict

Sentinel now has a browser visual grounding organ that converts screenshot
evidence plus OCR detections into hash-bound visual targets and perception
frames.

This is the layer that helps the browser operator handle pages where DOM and
accessibility trees are incomplete, misleading, hidden behind canvas, or not
enough for reliable targeting.

## Models Implemented

```text
BrowserVisualGroundingStatus
BrowserVisualGroundingFinalGateDecision
BrowserVisualGroundingContract
BrowserVisualGroundingRequest
BrowserVisualGroundingBox
BrowserVisualGroundingTarget
BrowserVisualGroundingReceipt
BrowserVisualGroundingFinalGateCertificate
BrowserVisualGroundingResult
BrowserVisualGroundingFinalGate
BrowserVisualGroundingOrganV1
render_browser_visual_grounding_receipt_as_untrusted_context
```

## Grounding Coverage

Implemented:

- screenshot hash binding;
- OCR detection to bounding-box region;
- hash-bound target refs;
- injection flag preservation;
- `PerceptionFrame` integration;
- hash-only OCR text persistence;
- receipt and FinalGate certification.

## Evidence And Safety Model

Each grounded target carries:

- source screenshot hash;
- bounding box;
- target ref hash;
- text hash;
- role hint hash;
- confidence score;
- injection flag;
- `authoritative_for_action = false`.

The organ does not persist raw screenshot bytes or raw OCR text in results.
OCR output is evidence data, not authority.

## Boundaries Held

No added:

- live OCR engine dependency;
- AgentRuntime default wiring;
- live CDP/MCP invocation;
- browser submit/login/payment;
- extension/WebMCP execution;
- raw screenshot-byte durability;
- raw OCR-text durability.

## Tests

Added:

```text
tests/test_browser_visual_grounding_ocr_v1.py
```

Focused tests:

```text
test_visual_grounding_creates_ocr_regions_targets_and_hashes
test_visual_grounding_preserves_injection_flags_as_untrusted_data
test_visual_grounding_blocks_missing_screenshot_hash_and_unsafe_control_payload
test_visual_grounding_does_not_persist_screenshot_bytes_or_raw_secret_ocr
test_visual_grounding_rendering_is_data_not_instruction
```

Targeted result:

```text
5 passed
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| OCR detection to bbox | CLOSED | focused test | OCR detections supplied by request/future backend |
| Screenshot binding | CLOSED | focused test | Hash binding only |
| Target ref hashes | CLOSED | focused test | Not wired to live backend yet |
| Injection flag preservation | CLOSED | focused test | Flags are evidence data only |
| PerceptionFrame integration | CLOSED | focused test | Hash/redacted text only |
| Raw OCR and screenshot non-durability | CLOSED | focused test | Raw output not persisted |
| Receipt + FinalGate | CLOSED | focused test | Metadata only |
| Live OCR engine | NOT_STARTED | no dependency in this pack | Future backend pack |
| AgentRuntime visual grounding wiring | NOT_STARTED | no runtime change | Future browser orchestration pack |

## Next Pack

```text
BROWSER_PERFORMANCE_LIGHTHOUSE_ORGAN_V1
```

This should add trace/performance insight capture for app-builder and browser
operator workflows.

## Anti-Overclaim Statement

This pack does not claim live OCR extraction from pixels yet. It locks the
Sentinel-native visual grounding contract, target model, receipt model, and
FinalGate boundary that a live OCR/screenshot backend can feed.
