# Sentinel Desktop App UX Architecture V1

Date: 2026-06-13

Purpose: define the product UX architecture for a lightweight installable
Sentinel desktop application connected to local Sentinel Core.

This is a product/design document only. It does not mark the desktop app as
implemented and does not change runtime truth.

## Product Mental Model

Sentinel is a living agent operating system.

The user should experience:

```text
calm intelligent presence
+ mission control
+ desktop/voice operator
+ authority console
+ proof/replay system
```

The user should not feel they are using:

```text
chatbot
IDE
SaaS admin panel
generic analytics dashboard
browser-only product
```

The core loop:

```text
Conversation -> Mission -> Authority -> Operation -> Proof -> Memory -> Replay
```

## Architecture Principles

1. The UI is not authority.
2. Sentinel Core owns mission state, authority, execution, telemetry, receipts,
   FinalGate, replay, and memory.
3. The app displays and requests; Core validates and acts.
4. Closing the UI does not stop Sentinel Core.
5. Kill/revocation stops powers and must remain visible.
6. Telemetry is safety infrastructure, not optional analytics.
7. Maturity labels must prevent fake/injected capability overclaim.

## App Modes

### Tray Mode

Tray mode answers:

```text
Is Sentinel alive?
Is it acting?
Does it need me?
Can I pause or kill?
```

Visible state:

```text
Certified / Degraded / Safe mode
active mission count
voice state
desktop state
approval needed count
pause
open compact
kill all
```

### Compact Mode

Compact mode is the everyday interface.

Visible state:

```text
orb / presence
natural command input
push-to-talk
short Sentinel response
active mission capsule
approval/checkpoint card when needed
proof shortcut when available
global kill
certified-mode status
```

Compact mode should not show full navigation by default.

### Full Cockpit Mode

Full cockpit mode is for depth, inspection, and supervision.

Visible state:

```text
mission list and active mission detail
live world desktop/browser state
workers
memory
channels
vault
account/login and financial authority surfaces
authority console
receipts and FinalGate
replay/proof studio
telemetry/system status
settings/permissions
```

## Recommended Navigation

Primary full-cockpit navigation:

| Navigation | Purpose |
| --- | --- |
| Home | Presence, command, active missions, approvals |
| Missions | Mission list, state, workflow, workers, checkpoints |
| Live World | Desktop, browser, voice, channels currently acting |
| Approvals | Pending authority, checkpoints, sends, leases |
| Proof | Receipts, FinalGate, replay, evidence |
| Memory | Durable context, recalled facts, trust/stale labels |
| Settings | Permissions, providers, telemetry state, app/core connection |

Secondary/contextual panels:

```text
Desktop
Browser
Voice
Workers
Channels
Credential Vault
Account/Login
Financial Authority
Skills
Model Route
Telemetry
Daemon
```

Advanced/developer panels:

```text
MissionAuthorityEnvelope raw view
workflow checkpoint internals
worker graph internals
telemetry hash chain
route receipts
skill scanner records
daemon lease diagnostics
redaction diagnostics
```

## Core Surfaces

### Presence

Purpose: make Sentinel feel alive and safe.

Includes:

```text
orb state
short response
certified-mode state
current mission capsule
voice push-to-talk
kill
```

### Mission Cockpit

Purpose: show what Sentinel is doing and why.

Includes:

```text
mission title and status
current step
surface currently acting
authority lane
budget/caps/deadline
workers
blocked actions
pending approvals
proof summary
```

### Live World

Purpose: show where Sentinel is operating.

Includes:

```text
desktop state
browser state
channel state
voice state
current app/site/channel
allowed and blocked regions/actions
sensitive-region posture
before/after evidence refs
```

### Authority Console

Purpose: make permission understandable.

Includes:

```text
mission
scope
where Sentinel may act
allowed actions
blocked actions
duration
budget/caps
credential lease scope
human checkpoints
kill/revocation behavior
proof requirements
maturity labels
```

### Proof Studio

Purpose: make trust inspectable.

Includes:

```text
timeline
authority changes
receipts
FinalGate certificates
evidence refs
worker result refs
memory refs
telemetry refs
no re-execution banner
tamper status
```

## Capability Maturity Labels

Every high-power surface should carry one of:

| Label | Meaning |
| --- | --- |
| Foundation | Data contracts and governed local foundation exist. |
| Sandbox | Fake/injected/sandbox execution only. |
| Local | Real local runtime exists, bounded to machine/workspace. |
| Live opt-in | Real provider/backend can run only with explicit opt-in and authority. |
| Production | Production-ready connector/backend with hardened install, support, and gauntlet proof. |

Examples:

```text
Payment/spend/trading = Sandbox / Paper
Credential vault = Foundation / fake sealed store
Desktop action backend = Foundation / fake-injected action; local monitoring exists
Voice = Foundation / fake-injected audio
Channels = Foundation / injected transport
Browser = Local for governed paths
```

## IPC Concept

Future app implementation should be UI-independent from Sentinel Core.

Conceptual IPC messages:

```text
CoreStatusSnapshot
MissionListSnapshot
MissionDetailSnapshot
ApprovalRequest
ApprovalDecision
CommandEnvelope
VoiceTurnEnvelope
KillRequest
ReplayRequest
ProofView
AuthoritySummary
TelemetryStatusSnapshot
```

IPC law:

```text
UI can request.
Core decides.
UI can display proof.
Core owns proof.
UI cannot execute organs.
```

## Authority UX Pattern

Use one consistent authority pattern across desktop, browser, channels,
credentials, login, and finance.

Pattern:

```text
1. Human-readable mission purpose
2. Where Sentinel can act
3. Allowed actions
4. Blocked actions
5. Duration / expiry
6. Budget / caps
7. Credential scope
8. Approval checkpoints
9. Proof requirements
10. Kill/revocation effect
11. Maturity label
```

## Telemetry UX Pattern

Telemetry state is always visible in compact or full mode:

```text
Certified
Degraded
Tamper detected
Unavailable
Read-only safe mode
```

Do not expose a normal user toggle to disable certified safety telemetry.

If telemetry is unavailable or tampered:

```text
high-power execution disabled
sensitive execution fail-closed
proof/replay still inspectable when available
```

## Notification Architecture

Notification severity:

```text
Quiet progress
Info
Needs approval
Risk
Blocked
Killed/revoked
Certified-mode degraded
Completed
```

Notifications should prefer mission capsules over noisy toasts.

Tray notifications should only interrupt for:

```text
approval needed
checkpoint blocked
risk/safety issue
mission completion
kill/revocation
certified-mode degradation
```

## Competitor Pattern Absorption

Absorb:

```text
UI-TARS / Agent TARS = immediate visual computer-use language
Agent Zero = shared workspace and human intervention clarity
gptme = compact local session ergonomics
Letta = memory as durable product identity
Microsoft Agent Framework = workflow durability and human-in-the-loop state
OpenClaw = skills/channels reach and explicit approvals
JARVIS/OpenJarvis = daemon, sidecar, voice, local model/system status
```

Avoid:

```text
ambient full-system authority
community plugin trust by default
hidden provider fallback
memory-as-policy
voice auto-approval
raw screen/credential capture
dashboard sprawl
developer-first complexity in the default UI
```

## Lightweight Implementation Constraints

The future app should be:

```text
fast launch
low idle memory
tray-capable
offline/local-first
Core-independent UI process
local IPC only by default
responsive compact window
optional full cockpit
GPU effects degradable
reduced motion compatible
```

Framework comparison for later decision:

| Option | Fit |
| --- | --- |
| Tauri | Best likely balance for lightweight desktop shell plus rich web UI. |
| Native shell + web UI | Strong for tray/service/IPC control; more custom work. |
| Flutter | Good cross-platform UI; heavier native desktop/service integration decisions. |
| Qt | Mature desktop; less aligned with web-prototype iteration speed. |
| Electron | Fastest rich UI path but heavier idle footprint; justify only if iteration speed dominates. |

No framework is selected in this design phase.

## Product Truth Rules

The UI must distinguish:

```text
locked runtime capability
foundation/fake-injected capability
sandbox/paper capability
future live provider/backend capability
```

Never show:

```text
fake login as real provider login
paper trading as live brokerage
fake desktop action as production OS control
descriptor channel as real connector
credential metadata vault as OS keychain vault
voice fake backend as live speech provider
```
