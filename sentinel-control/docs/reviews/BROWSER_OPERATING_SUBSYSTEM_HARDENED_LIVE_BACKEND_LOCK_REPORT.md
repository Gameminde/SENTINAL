# Browser Operating Subsystem Hardened Live Backend Lock Report

Recorded at: 2026-06-05

## Current State

This pack moves the Browser Operating Subsystem from mostly contract/test-locked
DevTools intelligence toward governed live backend paths. It does not add a
default runtime path and does not promote MCP, WebMCP, payment, shell, desktop,
channel, API mutation, or generic credential/browser login authority.

The implementation keeps the Sentinel rule: backend power is a measurement
surface behind contracts, receipts, FinalGate, and hash-only evidence.

External orientation was checked against the Chrome DevTools Protocol and
Chrome DevTools Network model. CDP domains such as Target, Network, Runtime,
Log, Page, DOMSnapshot, and Performance are powerful instrumentation surfaces;
this pack keeps them behind a Sentinel-native backend boundary and does not let
CDP or MCP become authority.

Sources:

- https://chromedevtools.github.io/devtools-protocol/
- https://developer.chrome.com/docs/devtools/network/reference

## Implementation Summary

Implemented:

- `BrowserSessionDevToolsBackend` in
  `sentinel/agent/organs/browser_devtools_backend_adapter_v1.py`.
- `BrowserNativeCdpBackend` in
  `sentinel/agent/organs/browser_devtools_backend_adapter_v1.py`.
- Hash-only live session DevTools metadata in
  `BrowserSessionManagerL5Live.devtools_metadata_for_session(...)`.
- Live browser network and console metadata listeners in
  `sentinel/organs/browser/cloak_backend.py`.
- Live screenshot source builder in
  `BrowserSessionManagerL5Live.visual_grounding_source_for_session(...)`.
- `browser_visual_grounding_request_from_live_session(...)`.
- `BrowserSessionOrchestratorActionBackend`, which routes orchestrator steps
  through the governed L5 session manager instead of the fake backend.
- `browser_live_results_to_replay_events(...)`, which converts live browser
  receipts and FinalGate certificates into hash-only replay timeline events.
- `browser_failure_recovery_request_from_live_devtools_metadata(...)`, which
  converts live console/network metadata into a recovery plan request.

## Component Truth Table

| Component | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| BrowserSessionDevToolsBackend | CLOSED | `test_devtools_backend_collects_hash_only_metadata_from_live_l5_session` | Uses existing governed L5 session manager; not AgentRuntime-promoted in this pack. |
| Native CDP backend boundary | CLOSED | `test_native_cdp_backend_is_hash_only_and_fails_closed_without_transport` | Limited hash-only CDP command plan; no raw CDP firehose and no MCP adapter. |
| Network/console/performance live metadata | CLOSED | `test_live_devtools_backend_exposes_network_console_and_performance_hashes` | Captures safe counts and hashes, not raw headers/bodies/log text. |
| Visual grounding from live session screenshot | CLOSED | `test_visual_grounding_builds_from_live_session_screenshot_without_persisting_raw_bytes` | OCR detections are supplied to the request; no native OCR engine added. |
| Long mission orchestrator live action backend | CLOSED | `test_orchestrator_action_backend_executes_governed_l5_session_step` | Covers governed L5 session action backend; no autonomous unbounded mission loop. |
| Replay studio live timeline bridge | CLOSED | `test_live_session_and_orchestrator_results_feed_replay_timeline_without_raw_payload` | Builds hash-only timeline events; no UI/replay service. |
| Failure recovery from live metadata | CLOSED | `test_live_devtools_metadata_feeds_failure_recovery_plan_without_raw_console` | Produces recovery plan requests only; does not auto-execute recovery. |
| AgentRuntime promotion for new backend paths | NOT_STARTED | Repo scan: no `browser_devtools`/`visual_grounding`/`failure_recovery` runtime_execution or organ_dispatch path in this pack. | Next pack must add explicit opt-in runtime routing if desired. |
| Live MCP adapter | NOT_STARTED | No MCP runtime import or adapter implementation added. | Keep MCP behind Sentinel backend interface if implemented later. |
| CDP raw body/HAR response quarantine | NOT_STARTED | No raw response body capture added. | Future pack must quarantine body data explicitly. |

## Safety Proof

No default behavior changed. All added paths require explicit construction of
the backend/helper by caller code. The new CDP backend fails closed when no
transport is provided.

The result surfaces expose:

- hashes,
- counts,
- backend kind,
- session references as hashes,
- receipt IDs,
- FinalGate certificate IDs,
- safe metadata only.

They do not expose:

- raw browser text,
- raw console messages,
- raw response bodies,
- raw auth headers,
- raw cookies,
- raw credentials,
- raw CDP responses.

## Tests Run

```text
py -3.13 -m pytest tests/test_browser_operating_subsystem_hardened_live_backend_lock.py -q
....... [100%]

py -3.13 -m pytest tests/test_browser_devtools_backend_adapter_foundation_v1.py tests/test_browser_devtools_machine_intelligence_v1.py tests/test_browser_multi_step_task_orchestrator_v1.py tests/test_browser_failure_recovery_engine_v1.py tests/test_browser_visual_grounding_ocr_v1.py tests/test_browser_observability_replay_studio_v1.py tests/test_browser_session_manager_l5_live.py -q
..................................... [100%]

py -3.13 -m pytest tests/test_browser_operator_agent_l4_l5_live.py tests/test_browser_runtime_failure_and_concurrency_hardening_lock.py tests/test_browser_runtime_unification_l5_l6_dispatch_lock.py tests/test_browser_runtime_unification_l6_login_file_js_dispatch_lock.py tests/test_browser_runtime_agentruntime_full_browser_stack_lock.py tests/test_brain_native_candidate_source_and_memory_feedback_lock.py tests/test_brain_to_organ_runtime_closed_loop.py -q
passed [100%]
```

## Non-Scope Confirmed

```text
generic browser login = NOT_STARTED
generic browser submit/upload/download/private session = NOT_STARTED
real credential use = NOT_STARTED
durable credential vault = NOT_STARTED
payment/spend/trading = NOT_STARTED
API mutation = NOT_STARTED
channel send = NOT_STARTED
desktop action = NOT_STARTED
shell/process execution = NOT_STARTED
provider fallback/AUTO routing = NOT_APPROVED
uncontrolled MCP/WebMCP = NOT_STARTED
```

## Next Recommended Pack

```text
BROWSER_OPERATING_SUBSYSTEM_LIVE_BACKEND_RUNTIME_PROMOTION_LOCK
```

Goal: add explicit opt-in AgentRuntime/OrganDispatcher routing for the live
DevTools, visual grounding, replay, and recovery backend paths implemented
here. Keep default-off and fail-closed semantics.
