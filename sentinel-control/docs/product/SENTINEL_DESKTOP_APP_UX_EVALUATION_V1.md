# Sentinel Desktop App UX Evaluation V1

Date: 2026-06-13

Prototype evaluated:

```text
C:\Users\youcef cheriet\Downloads\sentinel_living_os_prototype_v3.html
```

This document evaluates the HTML as a visual and interaction prototype only. It
does not evaluate it as runtime code, backend integration, or production
accessibility implementation.

## 1. Executive Verdict

Prototype V3 understands Sentinel's emotional center: a calm living presence
that can become mission control when depth is needed. The central orb, command
dock, proof modal, scoped approval modal, and kill overlay are all directionally
right.

Score:

```text
overall prototype score = 7.6 / 10
visual presence = 8.5 / 10
emotional feeling = 8.5 / 10
authority/proof language = 7.5 / 10
desktop-app suitability = 7 / 10
compact/full adaptability = 6.5 / 10
mission comprehension = 6.5 / 10
real capability truthfulness = 7 / 10
```

The main issue is not aesthetics. The main issue is product information
architecture. V3 feels alive, but it does not yet make the full Sentinel loop
obvious enough:

```text
Conversation -> Mission -> Authority -> Operation -> Proof -> Memory -> Replay
```

V4 should keep the presence-first feeling but make mission state, authority,
proof, and maturity labels more explicit without turning the product into a
dashboard.

## 2. What The Prototype Understands Correctly

V3 correctly treats Sentinel as a desktop presence, not as a website. The main
composition is app-like: a persistent top state, a rail, a central living
presence, an ambient status column, and a bottom command dock.

It also correctly avoids making the first screen a dense admin panel. The user
is greeted by a single question:

```text
Tell me what to handle.
```

This is close to the right product promise. Sentinel should feel available
before it feels technical.

Strong choices:

- central orb as presence, listening, thinking, alert, and running state;
- global kill visible in the top-right;
- compact ambient cards for desktop, voice, authority, and proof;
- command chips that model real user requests;
- authority modal that explains allowed, blocked, expiry, and proof;
- proof modal that states replay is view-only and does not re-execute;
- kill overlay that names revoked surfaces.

## 3. What Should Remain Unchanged

Keep the calm dark spatial identity. It differentiates Sentinel from SaaS
dashboards and developer IDEs.

Keep the orb as the default emotional anchor. It should be the compact-mode
center of gravity, not a decorative logo.

Keep the bottom command dock. It is the right metaphor for natural language,
voice, and mission shortcuts.

Keep the idea of a depth panel rather than exposing every subsystem by default.
Sentinel must be inspectable, but the first experience should be simple.

Keep the explicit kill affordance in the top-right. It should never be hidden
inside settings.

Keep proof and replay close to the main surface. Receipts and FinalGate are not
developer-only concepts; they are part of why the user can trust the system.

## 4. What Should Evolve

The prototype should evolve from "ambient sci-fi command presence" into
"usable local operator app." The next version should add more concrete product
states:

```text
idle
drafting mission
awaiting authority
running mission
monitoring quietly
approval required
checkpoint blocked
completed with proof
killed / revoked
degraded certified mode
```

The side rail should not be the main information architecture. Icons alone are
too cryptic for a product that handles credentials, desktop control, channels,
and money boundaries. V4 should show labels in full cockpit mode and use icons
only in compact mode.

The authority modal should become more specific. The current modal says
Allowed, Blocked, Expiry, Proof. V4 should include:

```text
mission
scope
where Sentinel may act
allowed action classes
blocked action classes
duration
budget/caps
credential scope
approval rules
kill/revocation behavior
proof requirements
maturity label
```

The telemetry state should appear as Certified / Degraded / Tamper detected /
Unavailable / Read-only safe mode, not as optional analytics.

The visual maturity of surfaces must be shown honestly:

```text
Foundation
Sandbox
Local
Live opt-in
Production
```

## 5. Desktop Application Mental Model

The final app should feel like three connected products sharing one Sentinel
Core:

```text
Tray mode = is Sentinel alive, safe, paused, blocked, or needing approval?
Compact mode = talk to Sentinel and supervise active work.
Full cockpit mode = inspect missions, authority, operation, proof, memory, and system state.
```

The app window is not the runtime. Closing the UI should not stop Sentinel Core.

Product law:

```text
closing UI != stopping Sentinel
kill switch = stopping/revoking active powers
```

## 6. Tray / Compact / Full Cockpit Architecture

Tray mode should show only:

```text
Sentinel state
active mission count
voice state
desktop state
approval needed
pause
open compact
kill all
```

Compact mode should be the everyday default:

```text
Sentinel orb
natural command input
push-to-talk
short response
active mission capsule
checkpoint/approval card
global kill
certified-mode indicator
```

Full cockpit mode should be optional depth:

```text
Missions
Live Operation
Desktop / Browser
Voice
Workers
Memory
Channels
Vault
Authority
Receipts / FinalGate
Replay
System Status
```

## 7. Main Navigation Recommendation

Primary navigation should reflect the user mental model, not internal organ
names.

Recommended primary full-cockpit navigation:

```text
Home
Missions
Live World
Approvals
Proof
Memory
Settings
```

Secondary/contextual surfaces:

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
Telemetry
```

Advanced/developer surfaces:

```text
MissionAuthorityEnvelope raw view
workflow checkpoints
worker task graph internals
telemetry event chain
route receipts
skill scanner internals
daemon lease diagnostics
```

Hidden internal surfaces by default:

```text
provider raw responses
raw prompts
raw reasoning
raw credential material
raw screenshots unless explicitly policy-allowed
raw secret-bearing logs
```

## 8. Information Architecture

The UI should use a progressive disclosure stack:

```text
Level 1: Presence and command
Level 2: Mission capsule and current action
Level 3: Authority summary and approvals
Level 4: Proof, replay, receipts, FinalGate
Level 5: Advanced diagnostics and raw-safe technical records
```

The default view should answer:

```text
Is Sentinel alive?
What is it doing?
Where is it acting?
Is anything blocked?
Does it need me?
How do I stop it?
Can I prove what happened?
```

## 9. Main Screen Anatomy

V4 compact main screen should include:

```text
top status: Certified / Degraded / Approval needed / Killed
orb: presence and voice/listening/thinking/running state
short response: one human sentence from Sentinel
mission capsule: active mission title, current step, current surface
approval/checkpoint card: appears only when needed
command dock: type, push-to-talk, suggested mission chips
global kill: always visible
proof shortcut: visible when proof exists
```

The ambient right column in V3 is good, but V4 should make those cards
actionable only when safe. "Proof replay ready" can open replay. "Authority
limited" can open authority summary. "Desktop observe" can open Live World.

## 10. Mission UX

Mission creation should be a guided conversation, not a form-first flow.

Flow:

```text
natural request
clarification
mission draft
authority summary
confirmation
mission starts
mission capsule appears
```

Mission capsule should show:

```text
mission title
state
current step
surface acting now
authority lane
deadline / budget / caps
blocked items
last proof
pause / details / kill
```

## 11. Authority UX

Authority should feel like a readable contract, not a generic permission popup.

Authority card sections:

```text
Mission: what this authority is for
Where: app/site/channel/account/sandbox
Allowed: action classes
Blocked: red lines
Duration: expiry and revocation
Budget/caps: spend, tokens, time, worker count
Credentials: lease scope and maturity
Approvals: what still needs human confirmation
Proof: receipts, FinalGate, replay
Maturity: Foundation / Sandbox / Local / Live opt-in / Production
```

No authority view should imply memory, receipts, FinalGate, telemetry, or LLM
output can create permission.

## 12. Desktop And Browser UX

Desktop and browser should live under "Live World" in primary navigation.

Desktop panel should show:

```text
control mode
current app/window/display
monitoring policy
allowed regions/apps
blocked regions/apps
sensitive-region status
last snapshot hash/ref
current action preview
before/after evidence
kill/revocation state
```

Browser panel should show:

```text
current tab/site
allowed action lane
blocked sensitive forms
login/account/payment boundaries
current step
recovery state
receipts and FinalGate refs
```

V3 captures the feeling of desktop awareness but not enough operational
specificity. V4 needs a concrete "World / Live Operation" screen.

## 13. Voice UX

Voice should show a clear state machine:

```text
Muted
Push-to-talk ready
Listening
Transcribing
Thinking
Speaking
Barge-in active
Kill word armed
Ambient alert
```

Voice should never appear as authority. It is transport into the cockpit.

Voice UX should always expose:

```text
what Sentinel heard
what command envelope was created
whether the command needs authority
whether it was blocked
how to interrupt
how to kill
```

## 14. Workers / Memory / Skills UX

Workers should be represented as helpers inside a mission, not as separate
agents the user must manage.

Worker card:

```text
role
task
authority subset
budget/deadline
state
result contract
merge/reject/conflict status
```

Memory should feel like "what Sentinel knows and why," not a chat history.

Memory card:

```text
recalled facts
source refs
trust class
stale/contradiction labels
used for context only
```

Skills should feel like approved procedures:

```text
approved / promoted / revoked
declared authority
side effects
scorecard
rollback posture
last successful receipt
```

## 15. Vault / Login / Financial UX

Vault UX should avoid showing secrets. It should show leases, scopes, expiry,
and use receipts.

Login UX:

```text
credential lease requested
login step progress
MFA/CAPTCHA/passkey/KYC checkpoint
safe resume
session binding status
```

Financial UX:

```text
Sandbox / Paper label
preview
caps
velocity
merchant/recipient/instrument policy
risk lane
approval
receipt
FinalGate
```

The UI must never make sandbox/paper/fake-injected flows look like production
live money or live broker execution.

## 16. Telemetry / Certified Mode UX

Telemetry should be presented as safety infrastructure, not optional analytics.

States:

```text
Certified
Degraded
Tamper detected
Unavailable
Read-only safe mode
```

Rules:

```text
No verified telemetry = no certified high-power execution.
Telemetry status can be inspected.
Telemetry cannot be disabled from a normal toggle.
Internal anti-tamper details stay out of the normal UI.
Product analytics and safety telemetry are separate.
```

## 17. Replay / Proof UX

Replay should be a proof studio, not a log dump.

Replay default view:

```text
mission timeline
authority changes
actions attempted
actions blocked
receipts
FinalGate terminal status
evidence refs
worker results
credential lease use
channel/desktop/browser/financial boundaries
no re-execution banner
```

Advanced proof view:

```text
hash-chain verification
receipt JSON-safe view
FinalGate certificate refs
telemetry refs
memory refs
redaction notes
tamper warnings
```

## 18. Kill / Revocation UX

Kill must be global, visible, and emotionally clear.

Kill overlay should show:

```text
active powers stopped
missions paused/killed
workers stopped
desktop/browser action stopped
voice interrupted
channel sends blocked
credential leases revoked
financial/account actions stopped
post-kill safe state
replay/proof preserved
```

After kill, the UI should not return silently to idle. It should show a
post-kill summary and an option to inspect proof.

## 19. Notification System

Notifications should be few and meaningful:

```text
approval needed
checkpoint blocked
mission completed
risk detected
telemetry degraded
kill executed
credential lease expiring
desktop/system threshold reached
financial cap reached
```

Do not notify for every internal step. Use quiet progress unless the user asked
for verbose mode.

## 20. Motion / Orb Behavior

The orb should encode state through subtle motion:

```text
idle = slow breathing
listening = ring pulse
thinking = rotating internal light
running = steady orbit
approval needed = amber pulse
blocked = red outer ring
completed = brief green proof flash
killed = motion stops, desaturated
degraded telemetry = broken/dashed outer ring
```

Motion must degrade cleanly for low-power mode and reduced-motion preference.

## 21. Visual Identity Strengths And Weaknesses

Strengths:

- feels calm, premium, and alive;
- strong contrast between presence and depth;
- avoids generic SaaS dashboard language;
- proof and kill are visually present;
- good early command vocabulary.

Weaknesses:

- heavy dark/glow style can feel too cinematic if overused;
- small rail icons are cryptic without labels;
- mission/authority state is not concrete enough;
- right-side metrics look decorative instead of operational;
- no maturity labels for foundation/sandbox/local/live/production;
- not enough distinction between compact and full cockpit.

## 22. Accessibility Considerations

V4 should plan for:

```text
keyboard-only navigation
visible focus rings
screen-reader labels for orb, kill, proof, voice, authority
reduced motion
high contrast mode
color-independent status labels
larger text mode
no information conveyed only by glow or color
safe timeout behavior for approvals
```

The prototype should not be penalized for missing production accessibility, but
the final desktop app must treat accessibility as a core operator-safety
feature.

## 23. Lightweight App Constraints

The final app should stay lightweight:

```text
fast launch
low idle memory
tray/background operation
UI independent from Sentinel Core
local IPC with Core
no always-running web dashboard unless opened
compact window first
optional full cockpit
GPU effects degradable
offline/local-first operation
```

Conceptual framework posture:

```text
Tauri = likely best fit for lightweight local desktop shell plus web UI
native shell + web UI = strong if control over tray/service/IPC matters most
Flutter = strong cross-platform UI but heavier product stack choice
Qt = mature native desktop, heavier design/developer workflow
Electron = easiest rich UI, but only justified if speed of product iteration beats memory cost
```

No framework should be selected until the V4 UX states and IPC contract are
clear.

## 24. Exact Screens To Prototype Next

V4 should prototype a focused set:

```text
Tray state
Compact idle/presence
Compact conversation
Mission drafting
Mission running
Approval/checkpoint
Desktop/browser live world
Voice session
Vault lease request
Financial sandbox/paper preview
Mission completed
Replay
Killed/revoked state
Full cockpit
```

## 25. Exact Interaction Flows To Prototype Next

Prototype these flows end to end:

```text
Sentinel, are you there?
I want to launch a business.
Monitor my PC while this render runs.
Finish this browser task while I am away.
Login and stop at MFA.
Draft and send this if it passes policy.
Run a paper trade preview with caps.
What are you doing?
Show proof.
Kill everything.
Replay the mission.
```

## 26. V4 Prototype Plan

V4 should not add dozens of pages. It should deepen the product states around
the existing presence model.

V4 principle:

```text
one compact presence surface
one full cockpit shell
one reusable authority/checkpoint pattern
one proof/replay pattern
one live-world pattern
```

The detailed V4 screen plan is in:

```text
sentinel-control/docs/product/SENTINEL_DESKTOP_APP_V4_PROTOTYPE_PLAN.md
```

## 27. Future Implementation Architecture Recommendation

The app should be a separate UI shell connected to Sentinel Core through local
IPC.

Recommended conceptual split:

```text
Sentinel Core = daemon, MissionKernel, authority, runtime, telemetry, replay
Desktop App UI = tray, compact, full cockpit
Local IPC = command envelopes, status streams, approval requests, proof refs
Sidecar adapters = desktop/voice/channel providers through governed contracts
```

The UI should never own authority or execute actions directly.

## 28. Risks And Unresolved Design Questions

Risks:

- over-stylized UI may obscure operational truth;
- too many surfaces may make compact mode feel like a dashboard;
- fake/injected maturity may be visually confused with live production power;
- telemetry may be misunderstood as optional analytics;
- authority popups may become habituated if too frequent;
- kill may be scary if it does not explain post-kill safety;
- proof may be ignored if hidden too deep.

Unresolved questions:

```text
Should compact mode be always-on floating, tray-opened, or normal window?
Should the orb remain central in full cockpit, or become a status widget?
How much telemetry should be visible to non-technical users?
Should Live World combine desktop and browser or split them in full cockpit?
What is the minimum first public demo gauntlet?
Which live backend should become production first: desktop, voice, channel, or vault?
```

## Reference Notes

AgentLab and current public references reinforce the same design lesson:
competitors are often ahead on product surface and live reach, while Sentinel's
advantage is authority/proof. V4 should absorb their immediacy without copying
their risk posture.

Observed reference patterns:

```text
UI-TARS / Agent TARS = immediate GUI/computer-use presence and visual grounding
Agent Zero = visible local workspace and operator intervention
gptme = local session continuity and compact task interaction
Letta = stateful memory as a product identity
Microsoft Agent Framework = durable workflow visibility and HITL patterns
OpenClaw = skills/channels reach plus supply-chain warning
JARVIS/OpenJarvis = daemon, sidecar, voice, hardware/model ergonomics
```
