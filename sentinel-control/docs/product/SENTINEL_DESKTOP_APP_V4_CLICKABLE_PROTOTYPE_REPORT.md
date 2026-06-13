# Sentinel Desktop App V4 Clickable Prototype Report

Date: 2026-06-13

Pack:

```text
SENTINEL_DESKTOP_APP_V4_CLICKABLE_PROTOTYPE
```

This is a product/design prototype pack only. It does not modify Sentinel
runtime code, does not initialize a production desktop framework, does not mark
any new runtime capability as complete, and does not start
`SECURITY_TESTING_SPECIAL_AUTHORITY_V1`.

## Files Created

```text
sentinel-control/docs/product/prototypes/sentinel_desktop_app_v4.html
sentinel-control/docs/product/SENTINEL_DESKTOP_APP_V4_CLICKABLE_PROTOTYPE_REPORT.md
```

## Input Design Baseline

The V4 prototype uses the V3 visual identity as its foundation:

```text
dark spatial calm
living orb
cyan/violet energy
bottom command dock
visible Kill
progressive disclosure
```

The V3 screenshot is treated as:

```text
Expanded Presence / Full Cockpit Home
```

not as the final everyday compact window.

## Product Forms Implemented

V4 demonstrates three connected desktop app forms:

```text
Tray
Compact
Full Cockpit
```

### Tray

Shows:

```text
Sentinel status
Certified-mode status
active mission count
approval/checkpoint count
voice state
desktop monitoring state
Open Compact
Open Cockpit
Pause
Kill All
```

### Compact

Sized conceptually for the requested everyday window:

```text
480-560 px wide
620-720 px high
```

Shows:

```text
small/medium living orb
short Sentinel response
real-looking command input
push-to-talk
current mission capsule
approval/checkpoint card only when needed
Certified / Degraded state
Proof through mission/proof state
Kill
Expand Cockpit
```

Compact mode intentionally does not show the full left rail or complete right
status stack.

### Full Cockpit

Sized conceptually for:

```text
1200-1440 px wide
760-960 px high
```

Primary navigation:

```text
Home
Missions
Live World
Approvals
Proof & Replay
Memory
Settings
```

Contextual surfaces:

```text
Desktop
Browser
Voice
Workers
Channels
Vault
Account/Login
Financial
Skills
Model Route
Telemetry
Daemon
```

## Navigation Corrections

V4 replaces the ambiguous `Depth` language with:

```text
Cockpit
```

when idle, and:

```text
Mission
```

when a mission is active.

The full cockpit uses:

```text
Proof & Replay
```

and approvals show attention state:

```text
Approvals - 0
Needs you - 1
```

## Ambient Status Corrections

Decorative progress percentages from V3 were removed. Concrete state text is
used instead:

```text
Desktop = Observe only / Monitoring quietly
Voice = Push-to-talk ready / Listening / Speaking / Barge-in
Authority = shown through allowed/blocked/approval state
Proof = receipt count and replay state
```

## Continuous Flows Implemented

The prototype is not disconnected pages. It uses a small local state machine
inside the HTML to move between app forms and mission states.

### Flow A - Mission Lifecycle

Implemented:

```text
Presence
-> natural conversation
-> clarification / thinking
-> mission draft
-> authority summary
-> approve
-> mission running
-> checkpoint
-> resume
-> mission completed
-> proof/replay
```

### Flow B - Kill Lifecycle

Implemented:

```text
mission running
-> Kill
-> active powers visibly revoked
-> leases/workers/voice/desktop/channel stopped
-> post-kill proof path
-> safe idle
```

### Flow C - App Form Lifecycle

Implemented:

```text
Tray
-> Compact
-> Full Cockpit
-> Compact
-> Tray
```

Also modeled:

```text
minimize
close to tray
restore compact
expand cockpit
push-to-talk shortcut hint
global summon shortcut hint
emergency kill shortcut hint
```

Law displayed:

```text
Close window != Kill Sentinel
Kill Sentinel = revoke/stop active power
```

### Flow D - Quiet Monitoring

Implemented:

```text
"Monitor my PC while the render runs"
-> monitoring policy
-> quiet mission capsule
-> CPU/GPU/temperature state
-> threshold alert
-> proof
```

### Flow E - Login Checkpoint

Implemented:

```text
"Login and stop at MFA"
-> mission draft
-> authority
-> vault lease request
-> login progress
-> MFA checkpoint
-> operator resumes
-> completion/proof
```

## Prototype States Implemented

States represented in the UI/state machine:

```text
Idle
Listening
Thinking
Drafting mission
Awaiting authority
Running
Monitoring quietly
Needs approval
Checkpoint blocked
Voice speaking
Barge-in
Completed
Replay
Killed
Telemetry degraded
Read-only safe mode
```

## Orb Semantics

The orb communicates state:

```text
Idle = slow breathing
Listening = input ring pulse
Thinking = rotating internal light
Running = stable orbit
Monitoring = slow scanning/dashed ring
Approval needed = amber pulse
Blocked = red outer ring
Completed = proof/green emphasis
Telemetry degraded = dashed amber outer ring
Killed = motion stops and desaturates
```

Reduced motion is supported with:

```css
@media (prefers-reduced-motion: reduce)
```

## Maturity Labels

V4 applies product truth labels:

```text
Foundation
Sandbox
Local
Live opt-in
Production
```

Examples shown in prototype:

```text
Voice = Foundation
Desktop monitoring = Local foundation
Desktop actions = Foundation / injected
Channels = Foundation / injected transport
Credential Vault = Foundation / fake sealed
Finance = Sandbox / Paper
Browser governed runtime = Local
```

The prototype does not visually represent fake/injected/foundation capability
as production live power.

## Visual Changes From V3

Kept:

```text
dark spatial calm
living orb
cyan/violet energy
visible kill
progressive disclosure
bottom command dock
```

Improved:

```text
Tray / Compact / Full Cockpit form simulation
mission capsule
authority contract card
maturity labels
concrete status cards
Proof & Replay language
post-kill proof path
Close to tray behavior
native shortcut hints
stateful continuous flows
```

Removed or reduced:

```text
ambiguous Depth label
decorative percentage bars
full rail in compact mode
overclaiming live production maturity
```

## Validation Questions

V4 answers:

```text
What is Sentinel doing?
Where is Sentinel acting?
What is it allowed to do?
What is blocked?
Does it need me?
What maturity level is this capability?
What proof exists?
How do I stop it?
Does closing the UI stop the Core?
```

## Remaining UX Questions

Open questions:

```text
Should compact mode be a floating always-on window or a normal resizable window?
Should the full cockpit keep the orb central or move it into a status header?
Should mission capsules stack in compact mode or show only the highest-attention mission?
Should tray approval count split approvals, checkpoints, and degraded telemetry?
How much proof detail belongs in compact mode before opening Proof & Replay?
Which live backend should get the first public demo: desktop, voice, channel, or browser?
Should a future app use Tauri, native shell plus web UI, Flutter, Qt, or Electron?
```

## Product Truth

This pack is prototype-only.

```text
no runtime code changed
no Sentinel Core behavior changed
no production desktop framework selected
no Tauri/Electron/Flutter/Qt initialized
no capability overclaim
no Security Testing phase started
```

## Suggested Next UX Step

Review V4 visually and interactionally, then choose one focused next move:

```text
Option A: refine V4 visual polish and responsive compact window.
Option B: add a product demo storyboard using the V4 states.
Option C: design the local IPC contract between future app UI and Sentinel Core.
```

Recommended:

```text
Option A first, then Option C.
```
