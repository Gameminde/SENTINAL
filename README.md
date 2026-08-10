<div align="center">

# SENTINEL CONTROL

### A cognitive operating system built to let AI understand, operate, and persist across computers, browsers, code, and long-running missions.

**Not just tool use. Sentinel is building a governed digital body around the model: perception, world state, memory, execution, recovery, evidence, and control.**

<br>

`COMPUTER` · `BROWSER` · `CODE` · `MEMORY` · `WORKERS` · `MISSIONS` · `VOICE` · `CHANNELS`

<br>

**Model = intelligence. Sentinel = body, senses, memory, runtime, authority, and proof.**

</div>

---

## What is Sentinel?

Sentinel Control is an experimental **cognitive operating system for AI agents**.

The model supplies reasoning, imagination, strategy, discovery, and language.
Sentinel supplies the persistent digital body around that intelligence:

```text
MODEL
  reasoning
  imagination
  strategy
  discovery
        │
        ▼
SENTINEL
  perception
  world state
  browser + computer organs
  skills
  memory
  mission runtime
  workers
  evidence
  replay
  authority
  revocation
  kill
```

The goal is not to build another chatbot with more tools.

The goal is to build an operating layer that lets intelligence **understand an environment, pursue durable missions, act through governed capabilities, observe consequences, recover from failure, remember useful context, and prove what actually happened**.

---

# Power is not the click

A computer agent that can click a button is useful.

A computer agent that understands **where it is, what environment it is operating in, what changed, what the mission requires, what it already tried, what failed, what remains possible, and how to continue** is something much more powerful.

That is the direction of Sentinel.

```text
OBSERVE
   ↓
UNDERSTAND
   ↓
DECIDE
   ↓
ACT
   ↓
VERIFY
   ↓
REMEMBER
   ↓
RECOVER
   ↓
CONTINUE
```

Sentinel is not being built as a collection of disconnected tools attached to an LLM.

It is being built as a **persistent operating layer around intelligence**.

The model should not need to rediscover the entire world after every action.
Sentinel's job is to give it a structured, governed understanding of that world.

---

# Computer Intelligence

## More than mouse and keyboard

Sentinel's computer-use architecture is not centered around blind coordinate clicking.

The system is being built so the model can operate with a **machine-level picture of the environment around it**.

The desktop architecture already contains foundations for:

```text
system state
window state
application state
process state
display state
supported hardware metrics
visual grounding
desktop monitoring
target identification
action previews
action proposals
before / after evidence
operator sessions
permission state
kill / revocation state
replay
```

Instead of treating the computer as:

```text
x = 842
y = 419
click()
```

the target abstraction is closer to:

```text
I am operating inside this mission.

This application is active.
This window is relevant.
This process exists.
This visual region corresponds to the target.
This action is allowed.

This is the state before the action.
This is the state after the action.
The environment changed as expected.
The mission can continue.
```

### Sentinel is trying to understand the machine it inhabits.

The computer is not just an actuator. It becomes part of Sentinel's environment model.

```text
Computer
│
├── system
├── displays
├── applications
├── windows
├── processes
├── visual regions
├── hardware signals
├── activity
└── actions
        ↓
   Sentinel perception
        ↓
   model decision context
        ↓
   governed action
        ↓
   before / after evidence
```

The current desktop layer remains an **experimental controlled foundation**.
Sentinel does not yet claim universal production-grade computer use or unrestricted OS control.

But the architecture is already moving beyond “give the LLM a mouse.”

---

# Browser Intelligence

## The browser is becoming a world, not a tool

Most browser agents expose actions:

```text
open
click
type
scroll
extract
```

Sentinel is moving toward something deeper.

Its Browser Cortex is designed to transform the live browser into a **structured cognitive environment** that the model can reason over.

A browser state can include multiple connected views of reality:

```text
BrowserEnvironmentState
│
├── Backend Truth
│     ├── selected browser backend
│     ├── actual browser backend
│     └── session provenance
│
├── Page State
│     ├── page identity
│     ├── page kind
│     ├── title
│     ├── visible content
│     └── stable references
│
├── Action Graph
│     ├── accessible controls
│     ├── search controls
│     ├── forms
│     ├── buttons
│     ├── links
│     └── possible actions
│
├── Extraction Graph
│     ├── result candidates
│     ├── entities
│     ├── cards
│     └── relevance to mission
│
├── Protocol Graph
│     ├── network activity
│     └── console activity
│
├── Session Graph
│     ├── cookie metadata
│     ├── storage state
│     ├── login state
│     └── session continuity
│
├── Blocker Graph
│     ├── modals
│     ├── consent
│     ├── login boundaries
│     ├── dynamic loading
│     └── hard boundaries
│
├── Visual Graph
│     └── visual evidence
│
└── World Model
      ├── what Sentinel believes is happening
      ├── what changed
      ├── mission progress
      ├── recoverable errors
      └── useful next skills
```

That changes the question the model can ask.

Not only:

```text
"Where can I click?"
```

but:

```text
"What kind of page am I on?"
"What does this page contain?"
"Which controls actually matter for my objective?"
"Did my previous action change the state?"
"Did this search produce material results?"
"What entities appeared?"
"Is the browser still in the expected session?"
"What is blocking progress?"
"Can I recover without restarting the mission?"
"Do I already have enough evidence to answer?"
"What should I do next?"
```

That is the direction of **Browser Cortex**.

Not browser automation alone.

**Browser understanding + actuation + memory + recovery + proof.**

---

# Mission Intelligence

## A mission is not a prompt

Sentinel does not treat a complex objective as one giant conversation with an LLM.

A mission is intended to become a **durable computational object**.

It has identity. It has state. It has authority. It has a workspace. It has execution history. It has evidence. It has failures. It has progress. It has workers. It can pause. It can resume. It can replan. It can terminate.

And its history can be inspected without blindly executing the actions again.

```text
MISSION
│
├── objective
├── current state
├── authority
├── workspace
├── model contract
├── execution requests
├── workflows
├── workers
├── artifacts
├── memory
├── receipts
├── blockers
├── checkpoints
├── progress
├── replay
└── terminal truth
```

The runtime models execution through explicit lifecycle states such as:

```text
PREPARED
   ↓
QUEUED
   ↓
CLAIMED
   ↓
DISPATCH DECIDED
   ↓
DISPATCH RUNNING
   ↓
COMPLETED / BLOCKED
```

This matters for long-horizon intelligence.

Useful work should not have to live entirely inside the model's temporary context window.

**The operating system carries the mission. The model reasons inside it.**

---

# From Tool Use to Environmental Intelligence

The long-term power of Sentinel comes from combining these layers.

```text
               MODEL
          reasoning / strategy
                 │
                 ▼
        SENTINEL COGNITIVE STATE
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
   COMPUTER    BROWSER   MISSION
     STATE      STATE     STATE
       │         │         │
       └─────────┼─────────┘
                 ▼
           DECISION CONTEXT
                 │
                 ▼
        GOVERNED EXECUTION
                 │
     ┌───────────┼────────────┐
     ▼           ▼            ▼
  Browser      Desktop     Code/Tools
     │           │            │
     └───────────┼────────────┘
                 ▼
        REAL WORLD CHANGES
                 │
                 ▼
       RECEIPTS + EVIDENCE
                 │
                 ▼
        WORLD STATE UPDATE
                 │
                 ▼
        MEMORY / RECOVERY
                 │
                 └──────────────► MODEL
```

The important loop is not:

```text
think → click → think → click
```

It is:

```text
perceive
→ build state
→ reason
→ act
→ observe consequences
→ verify
→ update the world model
→ measure mission progress
→ recover if necessary
→ continue
```

---

# The Power Stack

Sentinel's power comes from several layers working together.

| Layer | Purpose |
|---|---|
| **Perception** | Understand what currently exists across browser, desktop, workspace, mission state and runtime. |
| **World State** | Turn raw observations into structured context the model can reason about. |
| **Memory** | Carry useful context beyond a single inference without turning memory into authority. |
| **Mission State** | Know what the system is trying to accomplish, what already happened and what remains. |
| **Execution** | Give the model controlled muscles across browser, computer, code, workers, APIs and communication surfaces. |
| **Verification** | Observe what actually changed instead of trusting that an attempted action succeeded. |
| **Recovery** | Recognize stale state, failed actions, blockers and incomplete progress, then continue through another path when authority allows. |
| **Proof** | Keep receipts, evidence, telemetry and replay so the system can defend its own claims. |
| **Governance** | Keep all that power subordinate to explicit human authority. |

---

# Core Doctrine

Sentinel is designed around an intentionally asymmetric rule:

```text
maximum freedom in cognition
maximum power inside governed sandboxes
explicit human authority at real-world effect boundaries
```

The model can reason, imagine, explore, compare, plan, discover, and propose broadly.

But it cannot silently create its own authority.

```text
MODEL ≠ AUTHORITY
MEMORY ≠ AUTHORITY
TOOL OUTPUT ≠ AUTHORITY
RECEIPT ≠ AUTHORITY
TELEMETRY ≠ AUTHORITY
```

Authority must remain explicit, scoped, revocable, and stronger than the agent.

The system is built to preserve:

```text
authority boundaries
receipts
evidence
provenance
replay
revocation
kill
FinalGate
```

Hard boundaries are for things that actually matter:

```text
authority escape
secret leakage
ungranted external effects
origin or workspace escape
proof tampering
replay that re-executes side effects
kill or revocation bypass
```

Ordinary friction should not automatically kill a mission.
It should become **state, diagnosis, recovery, or replanning**.

---

# Current Capability Surface

Sentinel already contains substantial foundations across the operating system:

```text
Mission Kernel
Authority envelopes and gates
Browser control runtime
Browser world model / environment state
Desktop sidecar and live-desktop foundations
Visual grounding
Model-led task loops
Code execution sandbox
Workspace read / patch runtimes
Semantic memory foundations
Worker fleet and orchestration
Workflow runtime
Daemon / scheduler foundations
Skill fabric
Model routing
Channel adapters
Voice runtime foundations
Credential vault
Account authority coordination
Financial sandbox / paper-trading authority foundations
Receipts
Telemetry
Replay
FinalGate
Kill / revocation paths
```

This is a research and engineering system in active development, not a finished consumer product.

Some capabilities are mature local foundations; others are experimental, fake/injected, sandbox-only, or still being converged onto the canonical runtime.

---

# What Sentinel Does **Not** Claim Yet

The README should make the ambition clear without pretending unfinished work is finished.

Sentinel does **not** currently claim:

```text
unrestricted autonomous OS control
universal production-grade computer use
universal live public-site login/account automation
CAPTCHA, MFA, passkey, KYC, or security-checkpoint bypass
production password-manager / OS-keychain / cloud-vault integration
ambient credential access
live money execution
live broker order submission
unrestricted autonomous external side effects
production cloud operator platform
perfect long-horizon mission reliability
fully certified real-world mission completion across all surfaces
```

The project is intentionally trying to increase capability **without weakening the control plane that surrounds it**.

---

# Why Sentinel Is Different

Many agent systems make a model stronger by giving it more tools.

Sentinel is trying to make the model stronger by giving it a **body and an operating system**.

```text
tools                 → organs
prompt context        → persistent mission state
screenshots           → environment state
clicks                → governed actions
logs                  → evidence
retry                 → recovery
chat history          → memory
single-agent loop     → workers + workflows
"done"                → FinalGate / terminal truth
permissions           → explicit authority
```

The objective is not to keep Sentinel weak.

The objective is to let it become **extremely capable without becoming uncontrolled**.

---

# What Sentinel Is Becoming

Sentinel's endgame is not:

```text
AI + 100 tools
```

It is closer to:

```text
                    INTELLIGENCE
                         │
                         ▼
                 ┌───────────────┐
                 │   SENTINEL    │
                 │               │
                 │ perception    │
                 │ world model   │
                 │ memory        │
                 │ missions      │
                 │ recovery      │
                 │ workers       │
                 │ runtime       │
                 │ evidence      │
                 │ authority     │
                 └───────┬───────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       COMPUTER        BROWSER        DIGITAL
       ENVIRONMENT     ENVIRONMENT    SYSTEMS
```

A model should eventually be able to enter a mission and have a body capable of understanding:

**where it is, what it sees, what it can do, what it is allowed to do, what happened before, what changed, what failed, what remains, and how to continue.**

That is the kind of power Sentinel is being built for.

And as that power grows, the governing rule stays the same:

> **The model may become more intelligent. Sentinel may become more capable. Neither becomes the authority.**

---

# Repository

The GitHub repository is named `SENTINAL`; the product and codebase are **Sentinel Control**.

```text
SENTINAL/
├── sentinel-control/   # primary Sentinel Control codebase and docs
├── agent-lab/          # agent experiments / evaluation work
├── PLAN/               # planning material
├── RedditPulse/        # adjacent experimental project material
└── README.md
```

Key architecture and state documents live under `sentinel-control/docs/`.

Important source surfaces are concentrated under:

```text
sentinel-control/services/sentinel-core/sentinel/
```

with the operator/runtime work under:

```text
sentinel-control/services/sentinel-core/sentinel/operator/
```

---

# Development Status

**Status: experimental / pre-release.**

Sentinel is undergoing active convergence toward a single canonical cognitive/runtime spine.
The project has substantial implemented infrastructure, but the remaining work is not just “add more tools.”

The hard problems now include:

```text
reliable browser understanding on real missions
robust session continuity and recovery
computer-use convergence
mission progress measurement
long-horizon reliability
model-facing cognitive state quality
proof authenticity
real-provider certification
removing obsolete parallel execution paths
```

Development reports and lock documents inside the repository contain the detailed engineering truth for individual milestones.

---

# Research Direction

Current and future work is centered around several major cognitive organs:

### Browser Cortex
A structured browser world model that understands pages, controls, entities, sessions, blockers, progress and action consequences.

### Computer Cortex
A permissioned machine model that understands applications, windows, processes, visual state, system state and governed desktop actions.

### Mission Cortex
Long-running mission state, checkpoints, progress, recovery, planning, workers and terminal truth.

### Skill Fabric
Reusable governed procedures that can be discovered, evaluated, promoted, revoked and replayed without becoming hidden authority.

### Memory
Durable context that helps the model continue intelligently while remaining incapable of granting permissions.

### Physical / Device Cortex
A future boundary for governed interaction with devices and physical systems, only where authority, safety and proof can remain explicit.

---

# Open Development

Sentinel is being developed in public because powerful agent infrastructure benefits from inspection.

The interesting questions are not only:

```text
How capable can the model become?
```

but also:

```text
Can we make that capability persistent?
Can it understand the environment instead of blindly acting?
Can it recover from failure?
Can it prove what happened?
Can authority remain outside the model?
Can humans revoke that power cleanly?
```

Those are the problems Sentinel is trying to solve.

---

<div align="center">

### SENTINEL CONTROL

**Give intelligence a body. Give the body memory. Give the system power. Keep authority human.**

</div>
