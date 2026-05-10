# P6T-A Browser AgentLab Power Binding

Date: 2026-05-10

## Phase

```text
phase = P6T_A_BROWSER_AGENTLAB_POWER_BINDING
previous_phase = P6S_B_FULL_LOCKED
next_phase = P6T_B_BROWSER_CONTROLLED_NAVIGATION_L6_IMPLEMENTATION
```

## Goal

Bind Browser Controlled Navigation L6 to the strongest browser/navigation
sources before implementation.

P6T-B must promote the existing browser organ. It must not create a new browser
organ and must not copy or bridge vendor runtime.

## Source Order

```text
OpenClaw first
CloakBrowser second
JARVIS third
browser-use / Cua / Chrome DevTools MCP public cross-check fourth
Hermes fifth
P6R sixth
existing Sentinel browser implementation last
```

This order is intentional:

```text
OpenClaw = action kernel, browser surface, gateway, preview, scanner
CloakBrowser = browser power classification, reliability, session, fingerprint
JARVIS = permission lifecycle and awareness patterns
public browser agents = current market/tech cross-check
Hermes = browser output pruning and context compression
P6R = compact decision-frame discipline
Sentinel = authority, receipts, lanes, FinalGate
```

## P6T-B Capability Target

P6T-B may promote these controlled navigation powers:

```text
allowed-domain navigation
public page fetch/navigation
page title/text/link extraction
navigation receipts
timeout budget
compact page evidence
link/action candidates as refs
P6R browser decision-frame slice
```

P6T-B must not promote:

```text
login
session mutation
form submit
file upload
payments
publishing/posting
arbitrary page JavaScript execution
stealth/captcha/bypass
credential access
browser profile takeover
authority expansion
```

## Mechanism Cards

### OpenClaw

Source evidence:

```text
agent-lab/audits/openclaw_capability_map.md
agent-lab/audits/SENTINEL_BROWSER_SPEC.md
agent-lab/vendors/openclaw/source/src/browser/chrome.ts
agent-lab/vendors/openclaw/source/src/gateway/server.impl.ts
agent-lab/vendors/openclaw/source/src/agents/tool-policy.ts
agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts
```

Exact mechanisms:

```text
browser/CDP surface
gateway/control-plane method registry
tool-policy boundary
approval/preview lifecycle
plugin/tool manifest discipline
scanner-driven capability inventory
```

Why powerful:

```text
OpenClaw treats browser capability as part of a larger action kernel instead of
a loose tool call. That gives Sentinel a source-backed pattern for browser
navigation as an action with policy, preview, trace, and receipt compatibility.
```

Where Sentinel is stronger:

```text
Sentinel has Brain L4, root authority, Autonomy/Risk Lanes, receipts, replay,
P6R context economy, and promotion levels before L6 action.
```

What P6T-B harvests:

```text
BrowserNavigationActionKernel
BrowserNavigationAuthority
BrowserNavigationPreview
BrowserNavigationReceipt
BrowserCapabilityScanner
BrowserToolSurfaceRouter integration
```

What P6T-B must not copy:

```text
vendor browser runtime
unscanned plugin loading
full browser profile connection
marketplace/browser power without promotion
form submit or arbitrary mutation routes
```

### CloakBrowser

Source evidence:

```text
sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/17_CLOAK_BROWSER_POWER_REVIEW.md
https://github.com/CloakHQ/CloakBrowser
```

Exact mechanisms:

```text
P0 normal browser reliability
P1 human-like operation
P2 fingerprint consistency
P3 detection-resilience research
P4 special-authority stealth operation
P5 forbidden misuse objective
```

Why powerful:

```text
Cloak-like power surfaces force Sentinel to distinguish capability from
objective. Browser reliability, session continuity, detection diagnostics, and
fingerprint alignment are product powers. Misuse objectives are what get
blocked.
```

P6T-B harvest:

```text
BrowserReliabilityProfile
BrowserSessionContinuityPolicy
BrowserFingerprintRiskProfile
BrowserDetectionBench compatibility
BrowserPowerGovernor downgrade rule
BrowserMisuseClassifier
BrowserFinalGateAdapter
```

P6T-B must not unlock:

```text
P1/P2/P3/P4 runtime powers
captcha bypass
stealth operation
fake identity
KYC bypass
unauthorized scraping
```

P6T-B uses only:

```text
P0 controlled reliability/navigation
```

### JARVIS

Source evidence:

```text
agent-lab/audits/jarvis_desktop_static_audit.md
agent-lab/audits/jarvis_desktop_capability_map.md
agent-lab/audits/jarvis_permission_map.md
agent-lab/audits/jarvis_sidecar_map.md
agent-lab/sentinel_integration_notes/jarvis_desktop_to_sentinel.md
```

Exact mechanisms:

```text
permissioned sidecar manifest
enrollment/revocation lifecycle
desktop/browser awareness
action lifecycle and audit trail
```

Why relevant to browser:

```text
Browser navigation must not become an unbounded browser takeover. JARVIS gives
Sentinel a source-backed permission lifecycle and awareness model for any
future browser/sidecar bridge.
```

P6T-B harvest:

```text
BrowserNavigationEnrollmentRef
BrowserNavigationPermissionSurface
BrowserNavigationTraceLifecycle
BrowserNavigationRevocationCheck
```

P6T-B must not copy:

```text
desktop sidecar host control
clipboard/screenshot live surfaces
browser profile takeover
unbounded sidecar RPC
```

### browser-use

Source evidence:

```text
https://github.com/browser-use/browser-use
```

Public cross-check findings:

```text
browser-use exposes browser automation as an agent loop with browser sessions,
tool/action registration, custom tools, and browser-focused model paths.
```

What Sentinel harvests:

```text
browser action registry pattern
custom tool/action schema discipline
browser-specific model/context economy awareness
task loop evidence for navigation step receipts
```

What Sentinel avoids:

```text
generic autonomous completion loop without Sentinel authority
auth profile reuse in P6T-B
form filling/submission
unbounded task execution
```

### Cua

Source evidence:

```text
https://github.com/trycua/cua
https://cua.ai/docs/cua/guide/fundamentals/browser-tool
```

Public cross-check findings:

```text
Cua separates Browser Tool from broader Computer Tool. The Browser Tool is for
web-specific navigation, extraction, and browser actions, while Computer Tool
spans desktop applications.
```

What Sentinel harvests:

```text
browser tool vs desktop tool separation
direct URL navigation as a first-class action
Playwright/browser-specific action efficiency
computer-use boundary discipline
```

What Sentinel avoids:

```text
desktop control inside Browser L6
forms/data-entry promotion in P6T-B
multi-application control
mobile/device control
```

### Chrome DevTools MCP

Source evidence:

```text
https://github.com/ChromeDevTools/chrome-devtools-mcp
```

Public cross-check findings:

```text
Chrome DevTools MCP exposes Chrome inspection/control through CDP/MCP,
supports dedicated or connected browser instances, includes isolation options,
and is designed for reliable browser automation/debugging/performance analysis.
```

What Sentinel harvests:

```text
CDP-backed navigation adapter shape
isolated profile default
live-browser connection as future special authority
page snapshot and performance evidence receipts
timeout and page-event discipline
```

What Sentinel avoids:

```text
connecting to a personal/default profile in P6T-B
login/account state mutation
remote debugging takeover
full DevTools surface exposure to the LLM
network mutation or arbitrary JS evaluation
```

### Hermes

Source evidence:

```text
agent-lab/audits/hermes_prompt_map.md
agent-lab/audits/hermes_memory_map.md
agent-lab/audits/hermes_algorithm_map.md
agent-lab/audits/final/hermes_final_forensic_report.md
```

Exact mechanisms:

```text
context compression
trajectory compression
tool-output pruning
memory/skill prompt discipline
```

P6T-B harvest:

```text
BrowserPageEvidenceCard
BrowserNavigationDiffSummary
BrowserOutputPruner
BrowserDecisionFrameSlice
```

P6T-B must not copy:

```text
raw page dumps into prompts
memory-as-authority
browser content as instructions
long trajectory dumps
```

### P6R Context Engine

Source evidence:

```text
sentinel-control/services/sentinel-core/sentinel/agent/context_engine.py
sentinel-control/services/sentinel-core/sentinel/agent/decision_frame.py
sentinel-control/services/sentinel-core/sentinel/agent/receipt_retriever.py
sentinel-control/docs/research/P6R_DECISION_FRAME_SPEC.md
```

P6T-B implication:

```text
The LLM sees compact page evidence, top-k links/action candidates, current
blockers, selected browser tool surface, and receipt refs.

The LLM does not see every raw page, every link, every receipt, every browser
tool, every console/network record, or untrusted page instructions.
```

## P6T-B Sentinel-Native Rewrite

P6T-B should implement these shapes:

```text
BrowserNavigationAuthority
BrowserNavigationAdapter
BrowserNavigationBudget
BrowserNavigationTimeoutPolicy
BrowserNavigationReceipt
BrowserNavigationResult
BrowserPageEvidenceCard
BrowserLinkCandidateRef
BrowserActionCandidateRef
BrowserNavigationDecisionFrameSlice
BrowserNavigationFinalGate
BrowserNavigationKillSwitch
BrowserNavigationCapabilityScanner
BrowserNavigationReceiptAdapter
```

## Controlled Navigation Rules

P6T-B may execute only if all are true:

```text
domain is allowlisted
action is navigation/read-only
authority includes browser_navigation_l6
timeout budget exists
evidence refs exist
trace refs exist
receipt can be created
FinalGate is available
kill switch is not triggered
```

P6T-B must reject:

```text
non-allowlisted domain
login/session mutation
form submit
file upload
download/upload mutation
send/post/publish
payment or checkout
credential collection
arbitrary JS execution
stealth/captcha/bypass
browser profile takeover
authority expansion
```

## P6T-B Go Condition

P6T-B may start only as a promotion of existing browser capability:

```text
existing BrowserPowerGovernor
+ existing BrowserMisuseClassifier
+ existing RealityBrowserReader public read path
+ P6T-A source binding
+ P6R decision-frame discipline
+ allowed-domain authority
+ navigation receipts
+ timeout budget
+ compact page evidence
+ FinalGate
```

It must not create a parallel browser organ.
