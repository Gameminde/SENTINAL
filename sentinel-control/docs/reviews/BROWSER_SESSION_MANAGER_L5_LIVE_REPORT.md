# Browser Session Manager L5 Live Report

Date: 2026-05-30

## Current State

This pack turns the browser from single-shot observe/act into a governed
persistent session workflow:

```text
Power Lab CLI
-> BrowserSessionManagerL5Live
-> CloakBrowserSessionBackend primary adapter
-> PlaywrightSessionBackend compatibility adapter
-> persistent browser context/profile directory
-> open/type/observe/close receipts
-> screenshot + accessibility snapshot + form-state hash artifacts
```

This is not a read-only-only browser pack. It gives Sentinel session continuity
and live browser state across multiple operations.

## Agent-Lab And Public Research Signals

The implementation follows the local Agent Lab browser binding:

```text
OpenClaw = action kernel / browser surface / preview lifecycle
CloakBrowser = reliability / session / fingerprint-aware browser substrate
Hermes = task-scoped browser session lifecycle and cleanup discipline
BrowserGym/WebArena-style research = benchmarkable browser task loops
OSWorld-style research = browser power must connect to broader computer use
```

No leaked or private material was used. The public research lesson is that a
serious browser organ needs session continuity, evidence capture, action
grounding, cleanup, benchmark tasks, and failure recovery. This pack implements
the session-continuity layer and leaves trajectory/self-healing as the next
browser pack.

## Models And Contracts Added

- `BrowserSessionActionKind`
- `BrowserSessionStatus`
- `BrowserSessionContract`
- `BrowserSessionRequest`
- `BrowserSessionSafetyValidationResult`
- `BrowserSessionReceipt`
- `BrowserSessionResult`
- `BrowserSessionFinalGateDecision`
- `BrowserSessionFinalGateCertificate`
- `BrowserSessionFinalGate`
- `BrowserSessionManagerL5Live`
- `BrowserSessionBackend`
- `BrowserEngineSession`
- `CloakBrowserSessionBackend`
- `PlaywrightSessionBackend`

## CloakBrowser Primary Adapter

`CloakBrowserSessionBackend` wraps `cloakbrowser.launch_persistent_context(...)`
behind a Sentinel-native adapter.

The adapter:

- creates a persistent browser context under a scoped profile directory;
- passes viewport and headless settings;
- disables downloads;
- supports CloakBrowser humanize/stealth argument posture;
- installs HTML fixture routing only for deterministic local tests;
- returns a backend-neutral `BrowserEngineSession`.

If the optional `cloakbrowser` package is missing, the backend blocks with a
safe `cloakbrowser_not_installed` engine error rather than falling back silently.

## Playwright Compatibility Backend

`PlaywrightSessionBackend` remains only a compatibility and deterministic test
engine. It is explicitly selected through `engine="playwright"` or
`--engine playwright`.

The product default is:

```text
engine = cloak
```

## Live Browser Power

Implemented:

- persistent public browser session open;
- stateful type/fill/click/select/hover/wait-for-text operations;
- observe existing session without opening a new context;
- close session and cleanup backend owner;
- before/after screenshot artifacts for L5 interaction;
- accessibility snapshot hashes;
- hashed form-state continuity;
- typed text hash only, no raw typed text in receipt;
- metadata-only Browser Session FinalGate certificate for success and blocked
  receipts;
- CLI command:
  - `sentinel browser-session-demo`

## Scanner Fix

The shared scanner no longer treats the word `session` inside benign action IDs
such as `browser_session_open` as a credential leak. It still blocks a truthy
`session` key and nested cookie/session credential surfaces.

This fixes the Power Lab mission-file path for real browser session actions
without weakening the key-level credential firewall.

## Boundaries

Still blocked:

- browser submit;
- browser login;
- upload;
- download;
- arbitrary browser JavaScript;
- credential access/use;
- API mutation;
- channel send;
- shell/process;
- desktop action;
- payment/spend/trading.

## Files Changed

- `sentinel-control/services/sentinel-core/sentinel/organs/browser/cloak_backend.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_session_manager_l5_live.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/organs/__init__.py`
- `sentinel-control/services/sentinel-core/sentinel/cli.py`
- `sentinel-control/services/sentinel-core/sentinel/power_lab.py`
- `sentinel-control/services/sentinel-core/sentinel/shared/safety_scanner.py`
- `sentinel-control/services/sentinel-core/pyproject.toml`
- `sentinel-control/services/sentinel-core/tests/test_browser_session_manager_l5_live.py`
- `sentinel-control/services/sentinel-core/tests/test_organ_safety_scanner_consolidation.py`
- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md`
- `sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md`

## Verification

Targeted:

```text
python -m pytest tests/test_browser_session_manager_l5_live.py -q
6 passed

python -m pytest tests/test_browser_operator_agent_l4_l5_live.py -q
12 passed

python -m pytest tests/test_sentinel_power_lab_runtime_v0.py -q
7 passed

python -m pytest tests/test_organ_safety_scanner_consolidation.py -q
16 passed
```

Browser regression:

```text
python -m pytest tests/test_browser_session_manager_l5_live.py tests/test_browser_operator_agent_l4_l5_live.py tests/test_agent_browser_operator_runtime_integration.py tests/test_agent_browser_operator_runtime_minicorpus.py -q
31 passed

python -m pytest tests/test_browser_readonly_organ_v1.py -q
21 passed

python -m pytest tests/test_browser_preparation_organ_v1.py -q
20 passed

python -m pytest tests/test_browser_semantic_extraction_organ_v1.py -q
11 passed

python -m pytest tests/test_browser_semantic_extraction_agentruntime_opt_in.py tests/test_browser_readonly_preparation_agentruntime_opt_in.py -q
19 passed

python -m pytest tests -k browser -q
passed
```

## Truth Table

| Segment | Status | Evidence | Limitation |
|---|---:|---|---|
| CloakBrowser primary adapter | CLOSED | `test_cloakbrowser_backend_is_primary_and_uses_persistent_context` | Uses fake import in tests; real package remains optional external dependency. |
| No silent engine fallback | CLOSED | `test_default_engine_is_cloak_and_never_silently_falls_back` | Operator must explicitly choose compatibility engine if CloakBrowser is unavailable. |
| Playwright compatibility backend | CLOSED | `test_live_browser_session_persists_form_state_across_steps` | Compatibility/test engine, not product default. |
| Persistent browser session | CLOSED | same session ID across open/type/observe/close tests | Public/domain-scoped session only. |
| Form-state continuity | CLOSED | hashed form-state in type and observe receipts matches | Hashes only; raw field values not stored in receipt. |
| Browser Session FinalGate | CLOSED | session tests assert certificate ID is attached and `finalgate_verified=True` | Metadata-only certification, not authority. |
| CLI session workflow | CLOSED | `test_cli_browser_session_demo_runs_multi_step_workflow` | Demo workflow currently types one target value. |
| Browser submit/login/upload/download/JS | CLOSED as blocked | blocked action tests and contract validators | Separate authority packs required to promote. |
| Credentialed browser session | NOT_STARTED | no credential resolver called | Requires vault backend and session broker. |
| Trajectory planner / self-healing browser agent | NOT_STARTED | roadmap only | Next recommended pack. |

## Next Recommended Pack

```text
BROWSER_TRAJECTORY_PLANNER_AND_SELF_HEALING_L5
```

Purpose:

- rank target/action trajectories from DOM, accessibility, screenshot, and
  source confidence;
- recover when selectors drift;
- reuse session state across pages/tabs;
- produce local benchmark tasks inspired by BrowserGym/WebArena and Agent Lab
  browser corpora;
- keep submit/login/payment/upload/download/arbitrary JS behind separate
  special-authority packs.
