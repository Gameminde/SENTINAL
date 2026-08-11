<div align="center">

# SENTINEL CONTROL

### Give intelligence a body.

Sentinel Control is an experimental cognitive operating system for AI models:
a governed digital body with perception, memory, tools, runtime, proof,
recovery and authority.

```text
MODEL = reasoning / imagination / strategy / discovery
SENTINEL = body / senses / skills / world state / runtime / memory / proof / laws
```

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-experimental-orange.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Architecture](https://img.shields.io/badge/architecture-local--first-111111.svg)
![Runtime](https://img.shields.io/badge/runtime-evidence--driven-success.svg)

`MISSIONS` | `BROWSER` | `COMPUTER` | `CODE` | `MEMORY` | `WORKERS` | `SKILLS` | `PROOF`

[Contributing](CONTRIBUTING.md) | [Security](SECURITY.md) | [Apache-2.0](LICENSE)

</div>

---

## The Idea

Most agent systems add tools to a model.

Sentinel is building the operating layer around the model: the body, senses,
state, memory, laboratories, recovery loops, receipts, replay, kill switches
and authority boundaries required for useful long-running work.

The model remains the mind. It reasons, explores, compares, writes, plans,
invents and decides. Sentinel owns the world interface: what exists, what can
be done, what changed, what evidence was produced, what authority exists and
where execution must stop.

The ambition is not a safer chatbot. It is a new substrate for AI work:

```text
mission
-> observe the world
-> build a structured state
-> let the model reason and choose
-> execute through governed capabilities
-> measure progress
-> recover from failure
-> preserve evidence
-> build new tools when needed
-> finish with proof or an honest blocker
```

## Why It Matters

Powerful models are increasingly capable of strategy, code, research and
creative problem solving. But raw capability is not enough for real work.

A model needs a body that can:

- perceive computers, browsers, files, processes, applications and evidence;
- maintain mission state beyond a single prompt;
- create isolated workspaces and future mission-specific laboratories;
- execute actions through typed capabilities instead of raw unchecked tools;
- recover from stale state, broken sessions, missing evidence and partial work;
- prove what happened with receipts, replay and terminal truth;
- keep human authority above real-world effects.

Sentinel is the system being built to provide that body.

## Core Architecture

Sentinel is converging toward one canonical product spine:

```text
public request
-> RuntimeHost
-> RootMissionRuntime
-> model decision protocol
-> ExecutableCapabilityGraph
-> authority gate
-> ProductActionKernel
-> organ backend
-> receipt
-> CanonicalState
-> MissionProofRoot
-> cleanup / replay
```

The spine is designed so new organs can be connected without becoming separate
agents, hidden planners or bypasses around authority and proof.

## Operating Doctrine

```text
maximum freedom in cognition
maximum power inside governed sandboxes
explicit authority at real-world effect boundaries
receipts, evidence, replay and kill always preserved
```

Sentinel should not police the model's thoughts, topics or vocabulary. It
governs structured effects.

```text
semantic text != capability request
capability request != authority grant
authority grant != executed effect
executed effect != successful outcome
```

The model may discuss login, downloads, uploads, payments or credentials as
ordinary semantic data. Real login, upload, download, message, spending,
destructive change or external mutation must pass the corresponding authority,
sandbox, broker, budget, preview or confirmation boundary.

## Cognitive Organs

### Browser Organ

The browser is treated as an environment, not just a page with selectors.

Sentinel is building browser perception and action around:

```text
DOM / Shadow DOM
accessibility structure
frames and tabs
forms and interactive controls
navigation and search
network and runtime signals
session continuity
semantic evidence extraction
material progress
recoverable failure
receipts and replay
```

The canonical browser backend is moving toward `sentinel_chromium`: a
Sentinel-owned browser runtime using open-source browser machinery internally
while hiding low-level automation objects behind governed affordances. External
or proprietary browser backends can exist only as optional adapters.

### Computer Cortex

Sentinel's computer layer is intended to understand the machine as a structured
world:

```text
windows and applications
processes, services and threads
files, projects and dependencies
CPU, GPU, RAM and storage
network and active connections
logs, errors and performance
devices and authorized hardware state
```

The destination is not blind coordinate clicking. The destination is a computer
world model the AI can reason over and act through safely.

### Workspace And Code

Workspace capabilities are the first spine-compression target: list, read,
search, patch, check, test and summarize work should route through one mission
runtime, one capability graph, one authority boundary and authentic receipts.

The goal is not only to edit files. It is to let the model build, inspect,
repair, test and explain software inside a durable mission context.

### Memory, Workers And Workflows

Sentinel includes foundations for persistent memory, worker execution,
workflow state, checkpoints and long-running missions. Memory is context, not
permission. Workers are bounded children, not independent root agents.

### Mission Studios

For complex objectives, Sentinel should be able to create a mission-specific
laboratory:

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

The answer is not always just a chat response. Sometimes the product is the
environment Sentinel builds to understand, test and verify the answer.

### Skill Genesis

The long-term direction is controlled self-improvement:

```text
observe limitation
-> propose hypothesis
-> build sandbox experiment
-> test and benchmark
-> generate SkillCandidate
-> evaluate safety and usefulness
-> request governed promotion
```

Self-thinking does not mean uncontrolled self-modification. Generated
capabilities can be explored in sandboxes; promotion into the trusted runtime
requires governance.

### Physical And Industrial Cortex

Sentinel's architecture is designed to eventually extend into authorized
physical and industrial environments:

```text
robots
sensors
laboratory instruments
ROS2
MQTT
OPC UA
Modbus
serial / USB devices
digital twins
simulation environments
```

Physical action requires stronger gates: simulation, validation, interlocks,
explicit authority, execution receipts and hardware kill paths.

## Proof Culture

Sentinel is built to avoid fake completion.

Every meaningful capability must graduate through proof tiers:

```text
T0_STATIC_INSPECTED
T1_LOCAL_DETERMINISTIC_CANDIDATE
T2_LIVE_BODY_PROVEN
T3_REAL_MODEL_PRODUCT_PROVEN
T4_FROZEN_HOLDOUT_GENERALIZATION_PROVEN
T5_SUSTAINED_LONG_HORIZON_PROVEN
```

Local tests protect implementation. Live body proof validates physical
capability. Real-model proof validates cognition and mind/body integration.
Holdout proof validates generalization.

The repository preserves honest reports for both successes and failures. A
failed mission with precise evidence is more valuable than an invented win.

## What Exists Today

Sentinel is experimental and under active convergence. The codebase contains
substantial foundations across:

- root mission runtime and product spine;
- workspace and code capabilities;
- browser environment state and browser action routing;
- sovereign Chromium browser backend work;
- authority envelopes and effect boundaries;
- receipts, proof roots, replay and cleanup;
- semantic memory, workers and workflows;
- channel, credential, desktop and voice foundations;
- governed skill/procedure lifecycle;
- evaluation reports, ledgers and adversarial tests.

Some components are mature local foundations. Others remain experimental,
fake/injected, sandbox-only, partially connected or awaiting live proof.
Sentinel's public documentation is expected to say which is which.

## What Sentinel Does Not Claim Yet

Sentinel does not currently claim:

- completed autonomous Mission Studios;
- completed self-improving Skill Genesis;
- universal production-grade computer use;
- unrestricted operating-system control;
- universal public-site login or account creation;
- CAPTCHA, MFA, passkey or KYC bypass;
- ambient credential access;
- live money movement or broker trading;
- physical-system control;
- perfect long-horizon reliability;
- final production certification.

This honesty is part of the project. The system is being built to become more
powerful without weakening the control plane around that power.

## Repository Layout

```text
sentinel-control/        Active Sentinel product code, runtime, tests and docs.
agent-lab/               Research-only comparator and audit workspace.
PLAN/                    Historical strategy notes and architecture drafts.
archive/prototypes/      Archived prototypes, not active Sentinel products.
```

Archived prototypes are kept for provenance and design memory. They are not
presented as active products in this repository.

## Start Here

- [`sentinel-control/WORKSPACE_MAP.md`](sentinel-control/WORKSPACE_MAP.md)
- [`sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md`](sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md)
- [`sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json`](sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json)
- [`sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE_REPORT.md`](sentinel-control/docs/reviews/deep_power_audit/C5_SENTINEL_CHROMIUM_SOVEREIGN_PHYSICAL_GATE_REPORT.md)

## Contributing

Contributions are welcome around perception, mission reliability, browser and
computer state, recovery, evidence, replay, model-facing context, governed
skills, tests and documentation.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before proposing large new capability
surfaces. Security-sensitive findings should follow [`SECURITY.md`](SECURITY.md).

## License

Sentinel Control is licensed under the [Apache License 2.0](LICENSE).

<div align="center">

### Give intelligence a body. Give the body memory. Give it room to create. Keep authority human.

</div>
