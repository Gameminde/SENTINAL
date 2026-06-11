# Sentinel Control

**An agentic operating system for controlled real-world power.**

Sentinel is built for one thing: let intelligence act with serious power while
authority, proof, telemetry, replay, and shutdown remain stronger than the
agent.

```text
LLM = intelligence, dialogue, strategy
Sentinel Kernel = authority, runtime, proof, receipts
Mission Kernel = queue, workflow, state, replay
Organs = controlled muscles
Memory = durable context, never permission
FinalGate = terminal truth certification
```

The GitHub repository is named `SENTINAL`; the product and codebase are
**Sentinel Control**.

## Current Snapshot

```text
snapshot_date = 2026-06-11
current_phase = REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_LOCKED
previous_phase = LIVE_DESKTOP_OPERATOR_BACKEND_AND_SYSTEM_MONITORING_V1_LOCKED
next_phase = DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1
doctrine = product power under provable authority
```

Sentinel is no longer a vision document. It is now a local controlled-agent
runtime with browser power, mission state, memory, workflow, workers, telemetry,
daemon/scheduler foundation, model amplification, skill/procedure fabric,
explicit model routing, real channel adapter foundation, desktop sidecar,
live-desktop monitoring foundation, and realtime voice foundation.

The current top-level lock report is:

```text
sentinel-control/docs/reviews/REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_LOCK_REPORT.md
```

The canonical state truth is:

```text
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
```

## North Star

Sentinel is not:

```text
not just a chatbot
not just an IDE
not just a browser agent
not a CLI mission database
not a decorative UI
not a vendor-agent wrapper
```

Sentinel is:

```text
a mission operating system
with an LLM live cockpit
with governed runtime power
with controlled organs
with durable memory
with workers
with desktop/channel/browser reach
with receipts
with FinalGate
with replay
with kill/revocation
```

The product experience should feel simple:

```text
User: Sentinel, are you there?
Sentinel: Yes, I am here. What do you want to build or run?

User: I want to launch a business around AI training.
Sentinel: Good. I will clarify the goal, market, budget, constraints, and
authority level. Then I can start a governed mission.
```

Under the surface, that natural conversation becomes:

```text
conversation
-> MissionDraft
-> MissionAuthorityEnvelope
-> Gate
-> MissionKernel
-> workflow / daemon / workers
-> PowerRuntime or AgentRuntime
-> organs
-> receipts
-> FinalGate
-> telemetry
-> replay
-> memory feedback as context only
```

## Power Map

### 1. Live Operator Cockpit

Sentinel has an LLM-backed operator cockpit and deterministic test mode.
The LLM may think, clarify, draft, summarize, and propose. It cannot execute,
grant authority, unlock credentials, call organs directly, or bypass Gate,
receipts, FinalGate, telemetry, or replay.

```text
LLM cockpit = CLOSED
explicit UserModelContract required for product LLM mode = CLOSED
deterministic test mode = CLOSED / non-product
conversation-to-mission flow = CLOSED
pause/resume/kill/status/timeline/replay from conversation = CLOSED
```

### 2. Authority Kernel

Sentinel power is controlled by authority envelopes, gates, receipts, terminal
certification, kill switches, and replayable evidence.

```text
MissionAuthorityEnvelope = only authority source
DelegatedActionGate = CLOSED
receipts = CLOSED
FinalGate = CLOSED
kill/revocation checks = CLOSED across major runtime surfaces
memory/receipt/telemetry/FinalGate-as-authority = BLOCKED
```

### 3. Runtime Power

Sentinel has controlled local execution paths. These are not ambient root
powers; they are runtime-bound, tested, scoped, and receipt-producing.

```text
PowerRuntime V0 = CLOSED
AgentRuntime bridge = CLOSED / default-off controlled bridge
sandbox shell/code organ = CLOSED / allowlisted dev commands only
external API read/write organ = CLOSED / scoped domain-method authority
channel draft/send organ = CLOSED / draft default, send requires authority
browser L4/L5/L6/L7 stack = CLOSED across implemented locks
```

### 4. Durable Mission System

Sentinel can persist mission state, replay events, checkpoint workflows,
resume safely, replan inside authority, and avoid duplicate execution.

```text
MissionKernel/store/queue = CLOSED
mission timeline and replay = CLOSED
durable workflow records/checkpoints/resume cursors = CLOSED
automatic replan inside unchanged authority = CLOSED
duplicate tick prevention = CLOSED
safe terminal/handoff/dead-letter records = CLOSED
```

### 5. Memory

Sentinel has persistent semantic memory, but memory is context only. It cannot
grant authority, approve tools, unlock credentials, or override the model.

```text
persistent semantic memory = CLOSED / local runtime
Brain/cockpit recall = CLOSED / optional
AgentRuntime write-through = CLOSED / optional
mission timeline memory refs = CLOSED
memory-as-authority = BLOCKED
```

### 6. Telemetry And Product-Power Metrics

Telemetry is local, hash-bound, redacted, operator-visible, and required for
Certified Sentinel Mode.

```text
TelemetryKernel / TelemetryStore = CLOSED
operational/authority/LLM/organ/memory/workflow/replan/worker/cost/safety/product-power domains = CLOSED
replay completeness telemetry = CLOSED
Certified Mode telemetry snapshot = CLOSED
telemetry-as-authority = BLOCKED
```

### 7. Worker Fleet

Sentinel can spawn governed same-process workers with strict child authority
inheritance, budgets, deadlines, scopes, result contracts, merge/reject logic,
conflict detection, telemetry, and replay.

```text
Worker Fleet = CLOSED / same-process governed runtime
child authority strict subset = CLOSED
worker budgets/deadlines/scopes = CLOSED
merge/reject/conflict contracts = CLOSED
worker direct organ bypass = BLOCKED
```

### 8. Daemon And Scheduler

Sentinel has a local daemon/scheduler foundation for durable background mission
operation. The scheduler is proposal-only: it cannot create ambient authority.

```text
MissionDaemonRuntime = CLOSED / local same-process foundation
leases/heartbeats/stale takeover proof = CLOSED
crash recovery inspection = CLOSED
dead-letter records = CLOSED
proactive scheduler = CLOSED / proposal-only
ambient authority = BLOCKED
```

### 9. Model Amplification

Sentinel improves the selected model with hash-anchored state, minimized tool
output, evidence-linked diagnostics, analysis kernel records, worker-safe typed
results, and conflict detection.

```text
Model Amplification Harness = CLOSED
content-addressed artifacts = CLOSED
hash-anchored edits = CLOSED
tool-output economy = CLOSED
analysis kernel records = CLOSED / data-only
harness-as-authority = BLOCKED
```

### 10. Skill And Procedure Fabric

Sentinel can turn repeated work into governed procedures with provenance,
scanner, quarantine, approval, promotion, revocation, rollback posture,
receipts, telemetry, and replay.

```text
Governed Skill/Procedure Fabric = CLOSED
manifest/provenance/version pinning = CLOSED
scanner/quarantine/evaluation/approval lifecycle = CLOSED
receipt-bound procedure execution = CLOSED
remote plugin execution = BLOCKED
skill-as-authority = BLOCKED
```

### 11. Model Router

Sentinel can compare model candidates by hardware, cost, latency, privacy,
context fit, and policy. It binds only to an explicit `UserModelContract`.
It never silently switches providers.

```text
Local Model Hardware And Cost Router = CLOSED
candidate discovery and route simulation = CLOSED
route receipts = CLOSED
explicit operator policy/approval = CLOSED where required
provider fallback/AUTO = NOT_APPROVED
hidden provider/backend/model switch = BLOCKED
```

### 12. Channels

Sentinel has real channel adapter foundation with untrusted inbound handling,
outbound drafts, approval gates, recipient/scope/rate/idempotency constraints,
receipts, FinalGate refs, telemetry, and replay without resend.

```text
Real Channel Adapters = CLOSED / governed local adapter foundation
outbound draft default = CLOSED
send requires explicit authority = CLOSED
ambient send = BLOCKED
real provider credentials = NOT_STARTED
```

### 13. Desktop And Visual Grounding

Sentinel now has a Computer Operator Spine: permissioned observation, visual
grounding, monitoring snapshots, action previews/proposals, fake/injected
actions, before/after evidence, receipts, FinalGate, telemetry, replay, and
kill/revocation checks.

```text
Permissioned Desktop Sidecar = CLOSED
Live Desktop Backend And System Monitoring = CLOSED / local foundation
system/window/app/process snapshots = CLOSED
hardware metric snapshots = CLOSED / UNKNOWN/UNSUPPORTED when unavailable
fake/injected click/type/hotkey backend = CLOSED
hidden screenshot loop = BLOCKED
keylogging/credential harvesting = BLOCKED
production OS tray/service app = NOT_STARTED
```

### 14. Voice

Sentinel has a Sentinel-owned realtime voice and ambient operator foundation.
Voice is a transport into the cockpit and mission kernel, never an authority
source.

```text
Realtime Voice Runtime = CLOSED / local same-process foundation
voice provider descriptors = CLOSED / no live provider call
fake/injected audio backend = CLOSED
VAD and turn detection = CLOSED
partial/final transcript refs = CLOSED / hash and redacted excerpt only
barge-in and kill-word events = CLOSED
voice command envelope = CLOSED / data and proposal only
voice-to-desktop proposal path = CLOSED / no direct desktop action
voice replay = CLOSED / no audio playback, provider call, or action replay
```

## What Sentinel Does Not Claim Yet

Sentinel is powerful, but the README must not lie. These are still not started
or not approved:

```text
durable credential vault = NOT_STARTED / next
production microphone/speaker live provider adapters = NOT_STARTED
voice cloning or speaker biometrics = NOT_STARTED
production installed desktop tray/service app = NOT_STARTED
durable channel credential/session vaults = NOT_STARTED
payment/spend/trading/account/security/device powers = NOT_STARTED
platform app/operator cloud = NOT_STARTED
provider fallback/AUTO = NOT_APPROVED
vendor runtime integration = NOT_APPROVED
remote plugin marketplace execution = NOT_APPROVED
```

## Why This Is Different

Most agent systems make a model stronger by giving it tools. Sentinel makes the
model stronger by wrapping power in an operating system:

```text
authority before action
proof before trust
receipts before claims
FinalGate before completion
telemetry before scale
replay before certification
memory as context, never permission
workers as bounded children, never root agents
voice/desktop/channel as surfaces, never authority
```

The goal is not to keep Sentinel weak. The goal is to let it become extremely
powerful without becoming uncontrolled.

## Canonical Files

Use these files as the source of truth:

```text
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/docs/reviews/REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_LOCK_REPORT.md
```

For current implementation code, start here:

```text
sentinel-control/services/sentinel-core/sentinel/operator/
sentinel-control/services/sentinel-core/sentinel/power/
sentinel-control/services/sentinel-core/sentinel/agent/
sentinel-control/services/sentinel-core/sentinel/memory/
sentinel-control/services/sentinel-core/sentinel/telemetry/
sentinel-control/services/sentinel-core/tests/
```

## Quick Commands

Run the Sentinel core test slices from the repository root unless noted:

```powershell
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_realtime_voice_ambient_operator_v1.py -q
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
```

Run the cockpit from the Sentinel core package context:

```powershell
cd sentinel-control/services/sentinel-core
python -m sentinel cockpit --deterministic-test-mode
```

Product LLM mode requires an explicit model contract. No hidden default
provider, no fallback/AUTO routing, and no provider/backend/model override are
approved.

```powershell
python -m sentinel cockpit --model-contract <config>
```

## Repository Layout

```text
sentinel-control/
  docs/
    CURRENT_STATE_LOCK.md
    roadmaps/
    reviews/
  services/sentinel-core/
    sentinel/
      agent/
      memory/
      operator/
      power/
      telemetry/
    tests/

agent-lab/
  audits/
  audits/final/
  AGENT_LAB_PLAN.md
```

`agent-lab/` is research-only. It can inspect external systems and extract
mechanisms, but vendor runtime code does not enter Sentinel.

Legacy archives may still exist in the working tree, but they are not the
current product direction and should not shape Sentinel architecture.

## Build Order From Here

```text
1. DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1
2. ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1
3. PAYMENT_SPEND_TRADING_SPECIAL_AUTHORITY_V1
4. SECURITY_TESTING_SPECIAL_AUTHORITY_V1
5. ELECTRONICS_DEVICE_CONTROL_AND_IOT_ORGAN_V1
6. BUSINESS_AUTOMATION_PLAYBOOKS_AND_MARKETPLACE_V1
7. SENTINEL_PLATFORM_APP_AND_OPERATOR_CLOUD_V1
8. FINAL_CAPABILITY_GAUNTLET_AND_RELEASE_CERTIFICATION
```

Next implementation title:

```text
DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1
```

## Hard Rules

```text
MissionAuthorityEnvelope is the only authority source.
LLM output is never authority.
Voice is never authority.
Memory is never authority.
Telemetry is never authority.
Receipts are never authority.
FinalGate is certification, not future permission.
No direct organ bypass.
No provider fallback/AUTO.
No vendor runtime bridge.
Every dangerous power needs authority, Gate, receipts, FinalGate, telemetry,
replay, kill/revocation, and a safe terminal state.
```

## Definition Of Done

No phase is done because it "looks implemented." A Sentinel phase is done only
when:

```text
runtime or docs scope is complete
targeted tests pass
relevant regressions pass
self-audit is complete
P0/P1 and serious P2 issues are fixed
CURRENT_STATE_LOCK.md is updated
master roadmap is updated
relevant subordinate roadmap is updated
lock report is created or updated
README is updated
changes are committed
changes are pushed to origin/main
local HEAD == origin/main
working tree is clean
```

## North Star, In One Sentence

Sentinel is the operating system that lets powerful AI act in the real world
under explicit authority, visible proof, replayable truth, and human command.
