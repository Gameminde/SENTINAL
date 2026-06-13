# Sentinel Desktop App V4 Prototype Plan

Date: 2026-06-13

Purpose: define a focused V4 prototype plan for the Sentinel desktop app
product lane.

This is a design/prototype plan only. It does not start app implementation,
runtime code, or Security Testing.

## V4 Goal

V4 should transform V3 from a beautiful presence prototype into a usable
desktop-app product model.

The goal is not to add many pages. The goal is to prove:

```text
Sentinel can feel alive in compact mode.
Sentinel can explain mission, authority, operation, proof, and kill clearly.
Sentinel can open full cockpit depth when needed.
Sentinel does not overclaim fake/sandbox/foundation capabilities.
```

## Prototype Scope

Prototype these states:

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

## Screen 1 - Tray State

Purpose: show Sentinel is running in the background.

User question answered:

```text
Is Sentinel alive, safe, acting, or waiting for me?
```

Visible information:

```text
Certified mode state
active mission count
voice state
desktop monitoring state
approval needed count
pause
open
kill all
```

Hidden/deferred information:

```text
mission internals
worker graphs
receipts
telemetry chain
```

Primary action: open compact mode.

Secondary action: kill all active powers.

System state: background Core alive; UI may be closed.

Transition in: app starts, window closes, or user minimizes.

Transition out: open compact/full cockpit, pause, or kill.

## Screen 2 - Compact Idle / Presence

Purpose: make Sentinel feel present, calm, and ready.

User question answered:

```text
Can I talk to Sentinel now?
```

Visible information:

```text
orb idle state
Certified mode
short prompt
command input
push-to-talk
mission suggestion chips
proof shortcut if previous proof exists
kill
```

Hidden/deferred information:

```text
advanced navigation
subsystem internals
raw telemetry
```

Primary action: speak/type a mission.

Secondary action: open full cockpit or proof.

System state: no active mission or all missions quiet.

Transition in: launch/open app, mission completed, safe reset.

Transition out: compact conversation or mission drafting.

## Screen 3 - Compact Conversation

Purpose: support natural dialogue without feeling like a generic chatbot.

User question answered:

```text
Did Sentinel understand me, and what is it asking next?
```

Visible information:

```text
latest user request
Sentinel short answer
clarifying question
detected intent
voice/listening status
input
```

Hidden/deferred information:

```text
raw prompts
LLM provider response
reasoning
structured output internals
```

Primary action: answer the clarification.

Secondary action: cancel, show draft, or open depth.

System state: conversation intake active; no execution.

Transition in: user speaks/types.

Transition out: mission drafting or idle.

## Screen 4 - Mission Drafting

Purpose: turn natural language into a governed mission.

User question answered:

```text
What will Sentinel do if I approve this?
```

Visible information:

```text
mission title
objective
target surface
constraints
budget/caps
autonomy level
blocked actions
maturity labels
authority summary preview
```

Hidden/deferred information:

```text
internal mission record JSON
workflow internals
raw model output
```

Primary action: approve mission start.

Secondary action: edit scope, add constraint, cancel.

System state: draft ready; no execution.

Transition in: clarified request complete.

Transition out: approval/checkpoint or mission running.

## Screen 5 - Mission Running

Purpose: supervise active work without noise.

User question answered:

```text
What is Sentinel doing right now?
```

Visible information:

```text
mission capsule
current step
active surface
authority lane
worker count
budget/time remaining
last proof event
pause
details
kill
```

Hidden/deferred information:

```text
full event log
worker internals
telemetry samples
```

Primary action: monitor or pause.

Secondary action: open full cockpit, show proof, kill.

System state: mission executing inside authority.

Transition in: mission approved.

Transition out: checkpoint, completed, failed, killed.

## Screen 6 - Approval / Checkpoint

Purpose: ask for human authority at boundaries.

User question answered:

```text
What exactly am I approving or denying?
```

Visible information:

```text
mission
requested authority
where Sentinel will act
allowed actions
blocked actions
duration
budget/caps
credential scope
proof requirements
reason approval is needed
maturity label
```

Hidden/deferred information:

```text
raw MissionAuthorityEnvelope unless user expands
```

Primary action: approve scope.

Secondary action: deny, edit scope, view details.

System state: execution paused at checkpoint.

Transition in: authority required, MFA/CAPTCHA/KYC/passkey/checkpoint, send,
financial preview, live desktop action.

Transition out: mission running, paused, or blocked.

## Screen 7 - Desktop / Browser Live World

Purpose: show where Sentinel is operating.

User question answered:

```text
Where is Sentinel looking or acting?
```

Visible information:

```text
desktop/browser current surface
current app/site/window/tab
control mode
allowed regions/actions
blocked regions/actions
sensitive-region status
last snapshot hash/ref
current action preview
before/after evidence refs
kill/revocation state
```

Hidden/deferred information:

```text
raw screenshot by default
raw DOM/sensitive OCR text
browser/session secrets
```

Primary action: approve preview or continue monitoring.

Secondary action: pause, open proof, kill.

System state: observation/monitoring/action-preview active.

Transition in: mission uses desktop/browser or user opens Live World.

Transition out: action result, checkpoint, completed, killed.

## Screen 8 - Voice Session

Purpose: make voice state legible and interruptible.

User question answered:

```text
Is Sentinel listening, thinking, or speaking?
```

Visible information:

```text
voice mode
listening/transcribing/thinking/speaking state
latest transcript
command envelope summary
barge-in
kill word armed
ambient alert policy
```

Hidden/deferred information:

```text
raw audio persistence
provider transcript internals
raw prompts/provider responses/reasoning
```

Primary action: speak / stop speaking / barge in.

Secondary action: mute, inspect command, kill.

System state: voice transport active.

Transition in: push-to-talk or voice session starts.

Transition out: command captured, muted, killed, idle.

## Screen 9 - Vault Lease Request

Purpose: explain credential use without exposing secrets.

User question answered:

```text
What credential is Sentinel asking to use, and for what scope?
```

Visible information:

```text
secret type label
credential handle/ref label
mission needing it
consumer surface
scope
duration
checkout policy
approval requirement
raw material never shown
```

Hidden/deferred information:

```text
raw password/API key/token/payment method
sealed material internals
```

Primary action: approve lease.

Secondary action: deny, reduce scope, inspect previous use receipts.

System state: mission paused before credential use.

Transition in: login/account/payment/authorized connector needs lease.

Transition out: mission resumes, blocked, or safe idle.

## Screen 10 - Financial Sandbox / Paper Preview

Purpose: make money/trading boundaries unmistakable.

User question answered:

```text
Is this real money, sandbox, or paper?
```

Visible information:

```text
Sandbox or Paper label
spend/trade preview
merchant/recipient/instrument
caps
velocity
risk lane
approval needed
idempotency key/ref
blocked live-money note
receipt/FinalGate requirements
```

Hidden/deferred information:

```text
raw payment method
bank/broker provider key
live provider credentials
```

Primary action: approve sandbox/paper execution.

Secondary action: deny, edit caps, view policy.

System state: no live money execution; sandbox/paper only.

Transition in: financial mission reaches preview.

Transition out: sandbox/paper result, checkpoint, blocked, killed.

## Screen 11 - Mission Completed

Purpose: close the loop with proof and memory.

User question answered:

```text
What happened, and can I trust it?
```

Visible information:

```text
mission outcome
useful result
duration
actions completed
actions blocked
receipt completeness
FinalGate state
memory feedback summary
replay ready
```

Hidden/deferred information:

```text
full telemetry and raw-safe event chain
```

Primary action: view replay/proof.

Secondary action: start follow-up mission, save result, close.

System state: terminal completed.

Transition in: mission terminal success.

Transition out: replay, follow-up, idle.

## Screen 12 - Replay

Purpose: inspect history without re-executing anything.

User question answered:

```text
Can I reconstruct what Sentinel did?
```

Visible information:

```text
timeline
authority changes
actions attempted
actions blocked
receipts
FinalGate
evidence refs
worker results
memory refs
telemetry status
no re-execution banner
```

Hidden/deferred information:

```text
raw secrets
raw prompts
raw provider responses
raw reasoning
raw screenshots unless policy allowed
```

Primary action: inspect event/receipt.

Secondary action: export safe summary, return to mission.

System state: read-only replay.

Transition in: proof button, mission completion, replay request.

Transition out: mission detail, home.

## Screen 13 - Killed / Revoked State

Purpose: make shutdown concrete.

User question answered:

```text
What did kill stop?
```

Visible information:

```text
active powers stopped
missions killed/paused
workers stopped
desktop/browser stopped
voice interrupted
channel sends blocked
credential leases revoked
financial/account actions stopped
post-kill safe state
proof preserved
```

Hidden/deferred information:

```text
internal cleanup logs unless user opens proof
```

Primary action: inspect post-kill proof.

Secondary action: return to safe idle.

System state: killed/revoked.

Transition in: global kill, kill word, authority revocation.

Transition out: safe idle, proof.

## Screen 14 - Full Cockpit

Purpose: provide depth without making it the default experience.

User question answered:

```text
Can I inspect and control Sentinel's operating system state?
```

Visible information:

```text
Home
Missions
Live World
Approvals
Proof
Memory
Settings
active mission detail
workers
authority summary
telemetry status
vault/channel/desktop/voice/financial contextual panels
```

Hidden/deferred information:

```text
raw internals until advanced mode
```

Primary action: inspect active mission or approval.

Secondary action: open proof, pause, kill, settings.

System state: full inspection shell.

Transition in: user opens Depth/Full Cockpit.

Transition out: compact mode, tray, or specific panel.

## Interaction Flow Set

V4 should prototype these flows in clickable form:

1. Natural greeting:

```text
Sentinel, are you there?
-> presence response
```

2. Mission creation:

```text
I want to launch a business
-> clarification
-> mission draft
-> authority summary
-> confirmation
-> mission starts
```

3. Quiet monitoring:

```text
Monitor my PC while this render runs
-> monitoring policy
-> system metrics snapshot
-> quiet mission capsule
-> notification if threshold/risk/completed
```

4. Delegated browser/desktop work:

```text
Finish this task while I am away
-> scope request
-> active control mode
-> current app/browser step
-> worker/checkpoint/proof
```

5. Account/login checkpoint:

```text
Login and stop at MFA
-> vault lease request
-> login progress
-> MFA checkpoint
-> safe resume
```

6. Channel send:

```text
Draft and send this if it passes policy
-> draft
-> recipient/policy
-> approval
-> send result
-> receipt
```

7. Financial sandbox/paper:

```text
paper trade / sandbox spend
-> preview/caps/risk
-> approval
-> sandbox/paper execution
-> receipt/FinalGate
```

8. Voice:

```text
push-to-talk
-> listening
-> transcript
-> command envelope
-> barge-in
-> kill word
```

9. Kill:

```text
kill all
-> revoked surfaces
-> post-kill proof
-> safe idle
```

10. Replay:

```text
show replay
-> timeline
-> authority
-> receipts
-> FinalGate
-> no re-execution
```

## V4 Visual Direction

Keep:

```text
dark spatial calm
central orb
command dock
subtle glow
proof/kill presence
```

Add:

```text
maturity badges
certified-mode badge
mission capsule
approval card pattern
live-world panel
full-cockpit labeled navigation
post-kill summary
financial sandbox/paper labels
```

Reduce:

```text
cryptic icon-only navigation
decorative metric bars without operational meaning
large typography inside compact controls
overly cinematic glow in dense full cockpit mode
```

## V4 Success Criteria

V4 is successful if a user can answer:

```text
What is Sentinel doing?
Where is it acting?
What is allowed?
What is blocked?
What needs approval?
What proof exists?
How do I stop it?
Is this live, sandbox, local, foundation, or production?
```

without reading internal JSON or docs.
