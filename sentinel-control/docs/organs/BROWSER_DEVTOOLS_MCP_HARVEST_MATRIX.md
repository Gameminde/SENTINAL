# Browser DevTools MCP Harvest Matrix

Date: 2026-05-31

Status: CHROME_DEVTOOLS_MCP_HARVEST_AUDIT_LOCK

Source audited:

```text
Repository: https://github.com/ChromeDevTools/chrome-devtools-mcp
Package version observed in cloned package.json: 1.1.1
Local audit clone: %TEMP%/chrome-devtools-mcp-audit
Primary docs: README.md, docs/tool-reference.md, docs/design-principles.md, docs/cli.md
Source modules: src/tools/*.ts, src/McpPage.ts, src/McpContext.ts, src/DevToolsConnectionAdapter.ts
```

This matrix harvests capability patterns only. Sentinel must not treat MCP,
Chrome DevTools, CDP, Puppeteer, extensions, or third-party tools as authority.
They are backend transports behind Sentinel contracts, gates, receipts,
FinalGate, replay, and audit.

## Classification Legend

```text
L4 = external read-only perception
L5 = controlled external browser interaction
L6 = sensitive delegated browser execution
L7 = critical or high-risk browser execution
```

## Harvest Decision

Recommended integration:

```text
hybrid path = native DevTools/CDP backend abstraction first,
MCP adapter as one pluggable backend second,
direct third-party/WebMCP tools delayed until L7 bridge.
```

Why:

- Native Sentinel contracts keep authority in Sentinel.
- MCP is useful as a transport and reference implementation, not as the
  control plane.
- CDP exposes the browser nervous system directly: targets, runtime,
  accessibility, network, console, performance, emulation, heap, tracing.
- DevTools MCP proves a useful tool surface and ergonomics, but its own README
  warns it exposes browser contents to MCP clients and can inspect, debug, and
  modify data in the browser.

## Tool Mapping

| MCP Tool | Category | Sentinel Level | Harvest Into | Decision | Notes |
|---|---:|---:|---|---|---|
| `take_snapshot` | Debugging/perception | L4 | `BrowserDevToolsA11ySnapshotV2` | TAKE | Central source for UID/ref binding and target grounding. |
| `take_screenshot` | Debugging/perception | L4 | `BrowserEvidenceBundle` | TAKE | Screenshot artifact, metadata, perceptual hash, bounding-box bridge. |
| `screencast_start` | Debugging/perception | L4/L6 | `BrowserScreencastEvidence` | REWRITE | Useful for replay studio; streaming must be scoped and bounded. |
| `screencast_stop` | Debugging/perception | L4/L6 | `BrowserScreencastEvidence` | REWRITE | Stop/cleanup must be receipted. |
| `list_pages` | Navigation/session | L4 | `PageTargetManager` | TAKE | Target inventory and replay refs. |
| `select_page` | Navigation/session | L5 | `PageTargetManager` | TAKE | Context switch is action-bearing and must be explicit. |
| `new_page` | Navigation/session | L5 | `PageTargetManager` | TAKE | Must bind domain scope and isolated context policy. |
| `close_page` | Navigation/session | L5 | `PageTargetManager` | TAKE | Must record target closure and last evidence. |
| `navigate_page` | Navigation/session | L5/L6 | `BrowserNavigationAction` | REWRITE | URL/back/forward/reload with before/after evidence and redirect ledger. |
| `wait_for` | Navigation/session | L4/L5 | `BrowserWaitCondition` | TAKE | Needed for orchestration and recovery. |
| `click` | Input | L5 | `BrowserInputParity` | TAKE | UID-bound click with pre/post snapshot. |
| `hover` | Input | L5 | `BrowserInputParity` | TAKE | Useful for menus and hidden UI. |
| `fill` | Input | L5/L6 | `BrowserInputParity` | TAKE | Sensitive fields require L6 credential/session policy. |
| `type_text` | Input | L5/L6 | `BrowserInputParity` | TAKE | Raw typed text must not persist; store hashes/length/classes. |
| `press_key` | Input | L5/L6 | `BrowserInputParity` | TAKE | Keyboard parity for shortcuts, tabs, form navigation. |
| `fill_form` | Input | L5/L6 | `BrowserInputParity` | TAKE | High-value speed/reliability improvement for forms. |
| `drag` | Input | L5/L6 | `BrowserInputParity` | TAKE | Needed for real workflows: sliders, builders, kanban, maps. |
| `click_at` | Input/vision | L5/L6 | `BrowserVisualGrounding` | REWRITE | Coordinate action requires visual proof and viewport lock. |
| `handle_dialog` | Input/dialog | L6 | `BrowserFailureRecovery` | TAKE | Dialogs are common blockers; accept/dismiss can be sensitive. |
| `upload_file` | File interaction | L6 | Existing upload quarantine | TAKE | Already aligned with Sentinel quarantine-root pattern. |
| `list_network_requests` | Network | L4/L6 | `BrowserNetworkLedger` | TAKE | Metadata ledger, no raw auth headers/secrets. |
| `get_network_request` | Network | L4/L6/L7 | `BrowserHarResponseQuarantine` | REWRITE | Body capture must be explicit quarantine with size/content policy. |
| `list_console_messages` | Console | L4 | `BrowserConsoleLedger` | TAKE | Key diagnostic signal for orchestration/recovery. |
| `get_console_message` | Console | L4/L6 | `BrowserConsoleLedger` | TAKE | Include safe source maps/stack metadata only. |
| `evaluate_script` | Runtime | L6/L7 | Existing JS sandbox + DevTools bridge | REWRITE | Must preserve Sentinel sandbox restrictions and hash-only receipts. |
| `emulate` | Emulation | L5/L6 | `BrowserEmulationOrgan` | REWRITE | Headers/geolocation/user agent/network/cpu can be sensitive. |
| `resize_page` | Emulation | L4/L5 | `BrowserEmulationOrgan` | TAKE | Needed for responsive testing and visual grounding. |
| `performance_start_trace` | Performance | L4/L6 | `BrowserPerformanceOrgan` | TAKE | Start trace with budget/timeout. |
| `performance_stop_trace` | Performance | L4/L6 | `BrowserPerformanceOrgan` | TAKE | Trace artifact should be file ref/hash. |
| `performance_analyze_insight` | Performance | L4 | `BrowserPerformanceOrgan` | TAKE | Converts traces into actionable evidence cards. |
| `lighthouse_audit` | Performance/audit | L4/L6 | `BrowserPerformanceOrgan` | TAKE | Useful for app-builder; network/CrUX access must be explicit. |
| `take_heapsnapshot` | Memory | L6 | `BrowserHeapMemoryOrgan` | REWRITE | Heavy, sensitive, must be local artifact refs only. |
| `get_heapsnapshot_summary` | Memory | L4/L6 | `BrowserHeapMemoryOrgan` | TAKE | Safe summaries for leak diagnosis. |
| `get_heapsnapshot_class_nodes` | Memory | L6 | `BrowserHeapMemoryOrgan` | REWRITE | Can expose app data; quarantine needed. |
| `get_heapsnapshot_details` | Memory | L6 | `BrowserHeapMemoryOrgan` | REWRITE | Sensitive details; no raw secrets. |
| `get_heapsnapshot_retainers` | Memory | L6 | `BrowserHeapMemoryOrgan` | REWRITE | Useful but data-sensitive. |
| `list_extensions` | Extensions | L6/L7 | `BrowserExtensionBridge` | DEFER | Extension inventory only at first. |
| `install_extension` | Extensions | L7 | `BrowserExtensionBridge` | DEFER | High-risk supply-chain and permission surface. |
| `reload_extension` | Extensions | L7 | `BrowserExtensionBridge` | DEFER | Must be special authority. |
| `trigger_extension_action` | Extensions | L7 | `BrowserExtensionBridge` | DEFER | Can mutate browser/app state unpredictably. |
| `uninstall_extension` | Extensions | L7 | `BrowserExtensionBridge` | DEFER | Destructive browser environment mutation. |
| `list_3p_developer_tools` | Third-party | L6/L7 | `ThirdPartyToolBridge` | DEFER | Inventory only until bridge sandbox exists. |
| `execute_3p_developer_tool` | Third-party | L7 | `ThirdPartyToolBridge` | AVOID UNTIL SANDBOX | External tool execution surface. |
| `list_webmcp_tools` | WebMCP | L6/L7 | `WebMcpBridge` | DEFER | Inventory only, high prompt/authority risk. |
| `execute_webmcp_tool` | WebMCP | L7 | `WebMcpBridge` | AVOID UNTIL SANDBOX | Third-party web tool execution. |

## Sentinel Pack Mapping

### `BROWSER_DEVTOOLS_BACKEND_ADAPTER_FOUNDATION_V1`

Must define:

- `BrowserDevToolsBackend`;
- `BrowserDevToolsSession`;
- `BrowserDevToolsCapability`;
- `BrowserDevToolsRequest`;
- `BrowserDevToolsResult`;
- `BrowserDevToolsReceipt`;
- `BrowserDevToolsFinalGateCertificate`;
- fail-closed behavior when MCP/CDP/Chrome backend is unavailable.

The backend interface must expose capability methods, not raw tool calls.

### `BROWSER_DEVTOOLS_MACHINE_INTELLIGENCE_V1`

Harvest:

- `list_pages`, `select_page`, `new_page`, `close_page`;
- `take_snapshot`;
- `take_screenshot`;
- `list_network_requests`;
- `list_console_messages`;
- safe browser health summary.

Output:

- target refs;
- AX UID/ref map;
- network ledger hash;
- console ledger hash;
- screenshot artifact refs;
- evidence bundle hash.

### `BROWSER_MULTI_STEP_TASK_ORCHESTRATOR_V1`

Inputs:

- existing L4/L5/L6 browser powers;
- DevTools target manager;
- AX refs;
- network and console ledgers;
- screenshot artifacts;
- failure/recovery signals.

Loop:

```text
observe -> diagnose -> plan -> act -> verify -> recover -> continue
```

The orchestrator is the first pack that turns the browser organ from a set of
tools into a long-horizon operator.

### `BROWSER_FAILURE_RECOVERY_ENGINE_V1`

Recovery signals:

- stale UID/ref;
- target missing;
- modal/dialog present;
- redirect loop;
- SPA route error;
- disabled target;
- network failure;
- console exception;
- before/after mismatch;
- submit result uncertain;
- captcha/KYC/payment boundary.

### `BROWSER_DEVTOOLS_INPUT_PARITY_L5_L6`

Harvest:

- `drag`;
- `press_key`;
- `click_at`;
- `handle_dialog`;
- `fill_form`;
- more precise focus/state verification.

### `BROWSER_VISUAL_GROUNDING_OCR_V1`

Harvest:

- screenshot evidence;
- `click_at` only after viewport/screenshot/bounding-box binding;
- OCR and multimodal grounding as evidence candidates, not authority.

### `BROWSER_PERFORMANCE_LIGHTHOUSE_ORGAN_V1`

Harvest:

- `performance_start_trace`;
- `performance_stop_trace`;
- `performance_analyze_insight`;
- `lighthouse_audit`.

CrUX or external field-data lookups must be explicit because upstream docs
state performance tools may contact the Google CrUX API unless disabled.

### `BROWSER_NETWORK_HAR_RESPONSE_QUARANTINE_V1`

Harvest:

- `list_network_requests`;
- `get_network_request`;
- response metadata;
- optional response body capture into quarantine only.

Rules:

- no raw auth headers;
- no cookies;
- no bearer/API keys;
- body capture disabled by default;
- explicit size/type/domain caps.

### `BROWSER_CONTROLLED_EXTENSION_AND_WEBMCP_BRIDGE_L7`

Defer:

- extensions;
- third-party developer tools;
- WebMCP.

These are powerful enough to become a plugin execution fabric, so they require
special authority, sandboxing, provenance, receipt chain, and kill switch.

## Existing Sentinel Fit

Already compatible:

- CloakBrowser backend adapter;
- Playwright compatibility backend;
- browser session manager;
- browser trajectory planner;
- form-submit special authority;
- login credential session broker;
- upload/download quarantine;
- JS sandbox special authority;
- browser receipt wrappers;
- network ledger models;
- screenshot normalization;
- accessibility snapshot models;
- browser FinalGate checks.

Gaps:

- no DevTools target manager;
- no canonical DevTools backend interface;
- no UID/ref stability model across DevTools snapshots;
- no console ledger organ;
- no DevTools HAR response quarantine;
- no performance/Lighthouse organ;
- no browser task orchestrator;
- no browser recovery engine;
- no replay studio.

## Public Research Signals Used

Only public information was used. No private leak material was used.

- Chrome DevTools MCP repository and docs:
  `https://github.com/ChromeDevTools/chrome-devtools-mcp`
- Chrome DevTools Protocol:
  `https://chromedevtools.github.io/devtools-protocol/`
- WebArena:
  `https://webarena.dev/`
- VisualWebArena:
  `https://jykoh.com/vwa`
- BrowserGym:
  `https://github.com/ServiceNow/BrowserGym`
- SeeAct:
  `https://github.com/OSU-NLP-Group/SeeAct`
- OpenAI BrowseComp:
  `https://openai.com/index/browsecomp/`

## Verdict

Chrome DevTools MCP is not the organ. It is a rich reference surface for the
next generation of Sentinel browser organs.

The strongest path is:

```text
DevTools harvest -> Sentinel-native backend abstraction -> machine intelligence
bundle -> multi-step orchestrator -> recovery engine -> input parity -> visual
grounding -> benchmark gauntlet -> L6/L7 boundary manager.
```

This order prevents Sentinel from becoming a bag of browser tools. It becomes
a browser operating system with proof.
