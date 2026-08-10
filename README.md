<div align="center">

# SENTINEL CONTROL

### A cognitive operating system that gives AI a governed digital body — able to perceive, build, experiment, remember, recover, and operate across computers, browsers, code, simulations, and eventually physical systems.

**Not just tool use. Sentinel is building the body around the model: perception, world state, mission runtime, memory, laboratories, skills, recovery, evidence, authority, and proof.**

<br>

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-experimental-orange.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-local--first-111111.svg)
![Runtime](https://img.shields.io/badge/runtime-evidence--driven-success.svg)

<br>

`COMPUTER` · `BROWSER` · `CODE` · `MEMORY` · `WORKERS` · `MISSIONS` · `SKILLS` · `SIMULATION`

<br>

**Model = brain. Sentinel = body, senses, skills, world model, runtime, memory, proof, and laws.**

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Apache-2.0](LICENSE)

</div>

---

# What is Sentinel?

Sentinel Control is an experimental **cognitive operating system for AI agents**.

It is not intended to end as a generic agent, a chatbot with tools, a browser-automation framework, or a clone of existing coding-agent products.

The fundamental split is:

```text
MODEL
  reasoning
  imagination
  strategy
  discovery
  language
        │
        ▼
SENTINEL
  body
  perception
  world state
  browser + computer organs
  skills
  mission runtime
  memory
  workers
  evidence
  replay
  authority
  revocation
  kill
```

The model supplies intelligence.
Sentinel supplies the persistent operating layer that lets that intelligence **understand an environment, pursue durable missions, build and test things, recover from failure, remember useful context, act through governed capabilities, and prove what actually happened**.

The project is **experimental and actively under development**. The maintainer currently estimates that Sentinel is roughly **65% through its current development roadmap**. That number is a roadmap estimate, not a production-readiness score: substantial operating foundations exist today, while several major cognitive layers are still being converged or built.

---

# The North Star

The final architecture is a cognitive operating system that gives a model a **complete governed digital body**: deep perception of computers and browsers, durable memory, mission-specific laboratories, the freedom to experiment and invent inside sandboxes, and eventually controlled interaction with physical systems.

The governing equation is:

```text
maximum freedom in cognition
maximum power inside governed sandboxes
explicit authority at real-world effect boundaries
receipts, evidence, replay and kill always preserved
```

The model should be free to reason, search, imagine, compare, simulate, create, and experiment inside the authority already granted to a mission.

It should not require human approval for every normal micro-action already covered by that mission.

But intelligence can never silently become authority.

```text
The model cannot:

  grant itself authority
  expand its own permission envelope
  silently promote generated code into the trusted runtime
  hide or forge evidence
  use credentials outside their grant
  create irreversible external effects outside authority
  disable kill, revocation, replay, telemetry or proof
```

---

# Five Cognitive Frontiers

## 1. Browser Cortex

**Substantial foundations exist. Deep convergence is in progress.**

The browser should not be understood only through screenshots, selectors, or low-level automation commands.

Sentinel is being built to understand a browser as a changing cognitive environment:

```text
DOM + Shadow DOM
accessibility structure
frames + tabs
forms + interactive controls
page lifecycle
network activity
runtime / console state
sessions + storage metadata
streaming state
visual structure
semantic entities
blockers
uncertainty
mission progress
recovery paths
```

The model should receive a compact semantic state of the browser and choose mission-level skills rather than directly driving raw automation primitives.

---

## 2. Computer Cortex

**Experimental foundations exist. The persistent machine world model is still being built.**

The destination is deeper than desktop automation.

The Computer Cortex should understand relationships across:

```text
sessions + desktops
windows + applications
processes + services + threads
files + projects + dependencies
CPU + GPU + RAM + storage
network activity
logs + errors
visual state
supported hardware metrics
drivers + peripherals
USB + serial devices
authorized hardware state
```

The target abstraction is not merely:

```text
"I see this window."
```

It is closer to:

```text
This project is open in this application.
It uses this environment and these dependencies.
These processes belong to it.
This process is consuming these resources.
This connected instrument is producing data used by this mission.
This state changed because of the previous action.
```

The computer becomes part of Sentinel's persistent world model.

---

## 3. Mission Studios

**Architectural destination, built on top of existing workspace, execution, worker, browser, code, and artifact primitives.**

Some missions require more than a browser or a terminal.

Sentinel should be able to construct an isolated working environment appropriate to the problem:

```text
Software Studio
Research Room
Game Studio
Electronics Lab
3D Simulation Lab
Data Analysis Lab
Video Creation Studio
Browser Research Workspace
```

A Mission Studio may combine:

```text
editors
terminals
browsers
notebooks
databases
simulators
3D engines
workers
temporary tools
generated applications
artifact viewers
```

Sentinel should not only answer a question.

When necessary, it should **build the environment required to discover and verify the answer**.

### Example mission

```text
MISSION
"Explain this complex electronics PDF."

        ↓
understand text, tables, schematics and components
        ↓
build a structured model of the document
        ↓
create an isolated Electronics Lab
        ↓
reconstruct relevant circuits
        ↓
build temporary analysis / simulation tools
        ↓
simulate expected signals
        ↓
compare simulation with source evidence
        ↓
generate an interactive explanation
        ↓
preserve artifacts, uncertainty and receipts
```

If the mission later needs to interact with a real instrument, that transition crosses an explicit authority boundary.

> **The answer is not always the product. The environment Sentinel builds to reach and verify the answer can be part of the product.**

---

## 4. Self-Thinking & Skill Genesis

**The governed skill lifecycle exists today. Autonomous invention is a development target.**

Sentinel already contains a governed Skill Fabric with explicit lifecycle concepts for:

```text
registration
scanning
quarantine
sandbox evaluation
scorecards
approval
promotion
revocation
```

The long-term step is to connect that governance layer to increasingly autonomous research and invention:

```text
observe limitation or opportunity
        ↓
form hypothesis
        ↓
create sandbox experiment
        ↓
build temporary tool
        ↓
benchmark
        ↓
analyze failure
        ↓
improve
        ↓
generate SkillCandidate
        ↓
adversarial + quality evaluation
        ↓
propose promotion with evidence
```

The distinction is critical:

```text
self-thinking != uncontrolled self-modification

self-thinking = bounded autonomous research and invention
```

Generated capabilities may be explored freely inside governed environments.
Promotion into Sentinel's trusted runtime remains outside the model's unilateral authority.

---

## 5. Physical & Industrial Cortex

**Long-term frontier. Not a current production capability.**

The same architecture is intended to eventually extend beyond browsers and computers toward authorized physical systems:

```text
robots
ROVs
sensors
laboratory instruments
ROS2
MQTT
OPC UA
Modbus
serial / USB instruments
industrial systems
digital twins
electronic test and measurement
```

Physical action requires an even stronger boundary:

```text
simulation
→ validation
→ interlocks
→ explicit authority
→ physical execution
→ receipts
→ hardware kill
```

Sentinel should be able to grow into the physical world without weakening the rules that govern the digital one.

---

# Current Reality vs Destination

| Layer | Current state | Destination |
|---|---|---|
| **Mission Runtime** | substantial kernel, lifecycle, authority, worker and evidence foundations | reliable long-horizon cognitive execution |
| **Browser Cortex** | substantial environment-state and control foundations | deep semantic browser world model with robust recovery |
| **Computer Cortex** | experimental desktop state, monitoring, visual grounding and governed-action foundations | persistent machine-level cognition across software and authorized devices |
| **Skill Fabric** | governed scan/evaluate/approve/promote/revoke lifecycle | autonomous SkillCandidate research and invention |
| **Memory / Workers / Workflows** | implemented foundations | unified persistent cognitive runtime |
| **Mission Studios** | supporting workspace, code, browser, worker and artifact primitives | generated mission-specific laboratories |
| **Physical Cortex** | architectural frontier | governed interaction with devices, robots and industrial systems |

This table is intentional: **Sentinel's North Star is not a claim that every layer is available today.** It is the architecture the current system is being built toward.

---

# Browser Intelligence Today

The current Browser Cortex is already moving beyond a simple action API.

A `BrowserEnvironmentState` can represent multiple connected views of reality:

```text
BrowserEnvironmentState
│
├── Backend Truth
│     ├── selected backend
│     ├── actual backend
│     └── session provenance
│
├── Page State
│     ├── page identity / kind
│     ├── visible content
│     └── stable references
│
├── Action Graph
│     ├── accessible controls
│     ├── search controls
│     ├── forms
│     ├── buttons
│     └── links
│
├── Extraction Graph
│     ├── result candidates
│     ├── entities
│     └── relevance to mission
│
├── Protocol Graph
│     ├── network activity
│     └── console activity
│
├── Session Graph
│     ├── storage metadata
│     ├── login state
│     └── continuity
│
├── Blocker Graph
│     ├── modals / consent
│     ├── login boundaries
│     └── hard blockers
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

That changes the model's question from:

```text
"Where can I click?"
```

to:

```text
"What kind of page am I on?"
"Which controls matter for my objective?"
"Did the previous action materially change state?"
"Did this search produce useful results?"
"Is the session still what I expect?"
"What is blocking progress?"
"Can I recover without restarting the mission?"
"Do I already have enough evidence?"
```

**Browser understanding + actuation + memory + recovery + proof.**

---

# Computer Intelligence Today

Sentinel's computer-use architecture is not centered around blind coordinate clicking.

The current desktop layer contains foundations for:

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
action previews + proposals
before / after evidence
operator sessions
permission state
kill / revocation state
replay
```

Instead of treating the machine as:

```text
x = 842
y = 419
click()
```

Sentinel is moving toward:

```text
I am operating inside this mission.
This application and window are relevant.
This visual region corresponds to the target.
This action is allowed.
This is the state before the action.
This is the state after the action.
The environment changed as expected.
The mission can continue.
```

The current desktop layer remains an **experimental controlled foundation**. Sentinel does not yet claim universal production-grade computer use or unrestricted OS control.

---

# Mission Intelligence Today

## A mission is not a prompt

Sentinel does not treat a complex objective as one giant conversation with an LLM.

A mission is intended to be a **durable computational object** with identity, state, authority, workspace, execution history, evidence, failures, progress, workers, artifacts, checkpoints and terminal truth.

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

Useful work should not have to live entirely inside a temporary model context window.

**The operating system carries the mission. The model reasons inside it.**

---

# Governed Skill Fabric Today

Skills are not hidden permission shortcuts.

Sentinel's current Skill Fabric treats a reusable capability as a governed contract with explicit scanning, evaluation and promotion state.

```text
DRAFT
  ↓
SCAN
  ├── unsafe → QUARANTINE
  └── pass
        ↓
SANDBOX EVALUATION
        ↓
SCORECARD
        ↓
HUMAN / GOVERNED APPROVAL
        ↓
PROMOTION
        ↓
CONTROLLED USE
        ↓
REVOCATION when required
```

A skill cannot execute by itself, create authority, or bypass the existing runtime/proof spine.

This is the governance substrate for the future Skill Genesis loop.

---

# The Power Stack

| Layer | Purpose |
|---|---|
| **Perception** | Understand what currently exists across browser, desktop, workspace, mission state and runtime. |
| **World State** | Turn raw observations into structured context the model can reason about. |
| **Memory** | Carry useful context beyond a single inference without turning memory into authority. |
| **Mission State** | Know what the system is trying to accomplish, what already happened and what remains. |
| **Creation** | Let the system build temporary tools, artifacts and eventually mission-specific environments inside governed sandboxes. |
| **Execution** | Give the model controlled muscles across browser, computer, code, workers, APIs and communication surfaces. |
| **Verification** | Observe what actually changed instead of trusting that an attempted action succeeded. |
| **Recovery** | Recognize stale state, failed actions, blockers and incomplete progress, then continue through another path when authority allows. |
| **Proof** | Keep receipts, evidence, telemetry and replay so the system can defend its own claims. |
| **Governance** | Keep all that power subordinate to explicit human authority. |

---

# Core Doctrine

Sentinel is intentionally asymmetric:

```text
maximum freedom in cognition
maximum power inside governed sandboxes
explicit human authority at real-world effect boundaries
```

The model can reason, imagine, explore, compare, plan, discover and propose broadly.

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

Ordinary friction should become **state, diagnosis, recovery, or replanning** rather than automatically terminating a mission.

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
Governed Skill Fabric
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

Some capabilities are substantial local foundations; others remain experimental, fake/injected, sandbox-only, or still being converged onto the canonical runtime.

---

# What Sentinel Does **Not** Claim Yet

Ambition should be clear without pretending unfinished work is finished.

Sentinel does **not** currently claim:

```text
completed Mission Studios
completed autonomous Skill Genesis
production Physical / Industrial Cortex
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

# Repository

The GitHub repository is named `SENTINAL`; the product and primary codebase are **Sentinel Control**.

The important public engineering surfaces are:

```text
sentinel-control/                                  primary product + docs
agent-lab/                                         research / evaluation workspace
sentinel-control/services/sentinel-core/sentinel/  core Python package
sentinel-control/services/sentinel-core/sentinel/operator/  operator/runtime surfaces
```

The repository is still being cleaned for public OSS use. Historical planning material and an unrelated legacy workspace are being classified/extracted without erasing engineering history.

---

# Development Status

**Status: experimental / pre-release.**

Sentinel is undergoing active convergence toward a single canonical cognitive/runtime spine.

The hard remaining problems include:

```text
reliable browser understanding on real missions
robust session continuity and recovery
computer world-model depth
mission progress measurement
long-horizon reliability
model-facing cognitive state quality
Mission Studio composition
Skill Genesis
proof authenticity
real-provider certification
removing obsolete parallel execution paths
future physical-system governance
```

Development reports inside the repository contain detailed engineering truth for individual milestones, including failures and incomplete proof gates. Public presentation should improve clarity without rewriting that history.

---

# Open Development

Sentinel is being developed in public because powerful agent infrastructure benefits from inspection.

The interesting question is not only:

```text
How capable can the model become?
```

It is also:

```text
Can that capability become persistent?
Can it understand the environment instead of blindly acting?
Can it build the environment it needs for a mission?
Can it invent new capabilities inside safe sandboxes?
Can it recover from failure?
Can it prove what happened?
Can authority remain outside the model?
Can humans revoke that power cleanly?
```

Those are the problems Sentinel is trying to solve.

---

# Contributing

Contributions are welcome, especially around browser/computer perception, mission reliability, recovery, evidence, replay, model-facing state quality, governed skills, tests and documentation.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before proposing large new capability surfaces.

Security-sensitive findings should follow [`SECURITY.md`](SECURITY.md) rather than being disclosed with exploit details in a public issue.

---

# License

Sentinel Control is licensed under the **Apache License 2.0**.

See [`LICENSE`](LICENSE).

---

<div align="center">

### SENTINEL CONTROL

**Give intelligence a body. Give the body memory. Give it room to create. Give the system power. Keep authority human.**

</div>
