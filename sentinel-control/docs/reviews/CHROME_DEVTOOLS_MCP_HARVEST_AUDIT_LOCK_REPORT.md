# Chrome DevTools MCP Harvest Audit Lock Report

Date: 2026-05-31

Pack: `CHROME_DEVTOOLS_MCP_HARVEST_AUDIT_LOCK`

Status: `LOCKED`

## Executive Verdict

Chrome DevTools MCP should be harvested as a browser power reference and
possible backend transport, not imported as Sentinel authority.

The package exposes the browser nervous system:

- target/page management;
- AX snapshot and screenshot perception;
- click/type/fill/drag/keyboard/dialog input;
- network and console diagnostics;
- script evaluation;
- emulation;
- traces and Lighthouse-style performance;
- heap snapshots;
- extensions;
- third-party developer tools;
- WebMCP.

Sentinel already has live browser organs. The next jump is not another
single-action tool. The next jump is DevTools-grade machine intelligence plus a
multi-step browser orchestrator.

## Scope

This pack is docs/audit only.

It adds no runtime power, no backend invocation, no MCP server config, no CDP
client, no browser action, no credentials, and no default-on behavior.

## Evidence Read

External source audit:

```text
https://github.com/ChromeDevTools/chrome-devtools-mcp
README.md
docs/tool-reference.md
docs/design-principles.md
docs/cli.md
package.json
src/tools/*.ts
src/McpPage.ts
src/McpContext.ts
src/DevToolsConnectionAdapter.ts
```

Local Sentinel source audit:

```text
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_operator_agent_l4_l5_live.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_session_manager_l5_live.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_trajectory_planner_l5.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_form_submit_special_authority_l6.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_login_credential_session_broker_l6.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_download_upload_quarantine_l6.py
sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_js_sandbox_special_authority_l6.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/cloak_backend.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/rendered_snapshot.py
sentinel-control/services/sentinel-core/sentinel/organs/browser/ui_observation.py
```

Public research context:

```text
WebArena
VisualWebArena
BrowserGym
SeeAct
OpenAI BrowseComp
Chrome DevTools Protocol
Chrome DevTools MCP
```

No private leak material was used. The "latest technology" review was limited
to public repositories, docs, papers, benchmarks, and public product research.

## Upstream Capability Surface

Chrome DevTools MCP currently exposes 43 documented tools:

```text
Input automation: click, drag, fill, fill_form, handle_dialog, hover,
press_key, type_text, upload_file, click_at

Navigation automation: close_page, list_pages, navigate_page, new_page,
select_page, wait_for

Emulation: emulate, resize_page

Performance: performance_analyze_insight, performance_start_trace,
performance_stop_trace

Network: get_network_request, list_network_requests

Debugging: evaluate_script, get_console_message, lighthouse_audit,
list_console_messages, take_screenshot, take_snapshot, screencast_start,
screencast_stop

Memory: take_heapsnapshot, get_heapsnapshot_class_nodes,
get_heapsnapshot_details, get_heapsnapshot_retainers, get_heapsnapshot_summary

Extensions: install_extension, list_extensions, reload_extension,
trigger_extension_action, uninstall_extension

Third-party: execute_3p_developer_tool, list_3p_developer_tools

WebMCP: execute_webmcp_tool, list_webmcp_tools
```

The upstream design principles also align with several Sentinel instincts:

- small deterministic tools;
- semantic summaries over giant raw dumps;
- reference/file handles over heavy inline blobs;
- self-healing errors;
- human-readable and machine-readable output.

But upstream also makes a critical warning explicit: the server exposes browser
content to MCP clients and can inspect, debug, and modify browser state.
Therefore, Sentinel must never make MCP a direct authority path.

## Harvest Decision

Recommended architecture:

```text
hybrid backend strategy
```

Meaning:

- define a Sentinel-native DevTools backend interface first;
- support a native CDP implementation where direct control is needed;
- allow an MCP adapter as a transport behind that interface;
- preserve CloakBrowser as the primary live browser engine path where stealth,
  session persistence, and browser realism matter;
- use Playwright compatibility for deterministic test paths;
- never expose raw MCP tool calls to Brain, memory, replay, or AgentRuntime as
  executable authority.

## Why Orchestrator Moves Up

Tools are not enough.

Without `BROWSER_MULTI_STEP_TASK_ORCHESTRATOR_V1`, Sentinel has powerful
browser actions but not yet long-horizon browser autonomy.

With it, the browser organ can:

```text
observe -> diagnose -> plan -> act -> verify -> recover -> continue
```

That loop is what turns:

```text
DevTools tools
```

into:

```text
Browser Operator agent
```

The orchestrator must therefore follow immediately after DevTools backend and
machine-intelligence foundations.

## Sentinel Mapping

See:

```text
sentinel-control/docs/organs/BROWSER_DEVTOOLS_MCP_HARVEST_MATRIX.md
```

Summary:

- L4: snapshot, screenshot, network metadata, console metadata, performance
  summaries, page list;
- L5: navigation, page selection, click, hover, wait, type/fill when
  non-sensitive;
- L6: upload, dialog handling, sensitive form fields, script sandbox,
  heap/memory diagnostics, response body quarantine, emulation with headers or
  geolocation;
- L7: extensions, third-party tools, WebMCP execution, payment/spend,
  account creation, KYC/auth-wall flows.

## Next Pack Contract

The next pack should be:

```text
BROWSER_DEVTOOLS_BACKEND_ADAPTER_FOUNDATION_V1
```

It must define:

- `BrowserDevToolsBackend`;
- `BrowserDevToolsSession`;
- `BrowserDevToolsCapability`;
- `BrowserDevToolsRequest`;
- `BrowserDevToolsResult`;
- `BrowserDevToolsReceipt`;
- `BrowserDevToolsFinalGateCertificate`;
- backend availability probes;
- fail-closed missing-backend behavior;
- safe metadata-only error reporting.

It must not:

- make MCP direct authority;
- invoke browser actions by default;
- enable extension/WebMCP execution;
- enable generic arbitrary JS;
- enable raw auth header/body capture;
- enable payment/spend;
- enable account creation.

## Roadmap Update

The browser roadmap order is now:

```text
0. BROWSER_ROADMAP_STATE_TRUTH_REPAIR
1. CHROME_DEVTOOLS_MCP_HARVEST_AUDIT_LOCK
2. BROWSER_DEVTOOLS_BACKEND_ADAPTER_FOUNDATION_V1
3. BROWSER_DEVTOOLS_MACHINE_INTELLIGENCE_V1
4. BROWSER_MULTI_STEP_TASK_ORCHESTRATOR_V1
5. BROWSER_FAILURE_RECOVERY_ENGINE_V1
6. BROWSER_DEVTOOLS_INPUT_PARITY_L5_L6
7. BROWSER_VISUAL_GROUNDING_OCR_V1
8. BROWSER_PERFORMANCE_LIGHTHOUSE_ORGAN_V1
9. BROWSER_NETWORK_HAR_RESPONSE_QUARANTINE_V1
10. BROWSER_BENCHMARK_GAUNTLET_WEB_ARENA_STYLE
11. BROWSER_BOUNDARY_MANAGER_L6_L7
12. BROWSER_PAYMENT_SPEND_SPECIAL_AUTHORITY_L7
13. BROWSER_ACCOUNT_CREATION_SPECIAL_AUTHORITY_L7
14. BROWSER_OBSERVABILITY_AND_REPLAY_STUDIO_V1
15. BROWSER_CONTROLLED_EXTENSION_AND_WEBMCP_BRIDGE_L7
16. BROWSER_FINAL_CAPABILITY_LOCK
```

## Closed Truth Table

| Segment | Status | Evidence | Limitation |
|---|---|---|---|
| Chrome DevTools MCP repository audit | CLOSED | README/tool reference/source clone inspected | No runtime import |
| Tool-to-Sentinel level mapping | CLOSED | Harvest matrix created | Mapping only |
| Native CDP vs MCP adapter decision | CLOSED | Hybrid recommendation recorded | Implementation next pack |
| DevTools machine intelligence scope | CLOSED | Page/AX/network/console/screenshot bundle defined | No code yet |
| Orchestrator priority correction | CLOSED | Roadmap order moves orchestrator to position 4 | Implementation later |
| Runtime power added | NOT_STARTED | Docs-only pack | Intentional |
| MCP server config | NOT_STARTED | No config files changed | Intentional |
| Extension/WebMCP bridge | NOT_STARTED | Deferred to L7 | Intentional |
| Payment/spend | NOT_STARTED | Moved after DevTools/orchestrator/boundary manager | Intentional |

## Anti-Overclaim Statement

This pack does not claim Sentinel has DevTools backend execution yet.

It claims only:

- Chrome DevTools MCP was audited;
- the tool surface was classified;
- the safe harvest path was selected;
- the browser roadmap was corrected;
- the next implementation pack is clearly defined.

## Final Verdict

Chrome DevTools MCP confirms the right direction: Sentinel should not be a
read-only browser toy, and it should not be a direct-tool chaos agent either.

The winning path is:

```text
DevTools-grade perception and debugging
+ Sentinel-native authority
+ multi-step orchestration
+ recovery
+ replay
= elite browser organ
```

The next implementation should start immediately with:

```text
BROWSER_DEVTOOLS_BACKEND_ADAPTER_FOUNDATION_V1
```
