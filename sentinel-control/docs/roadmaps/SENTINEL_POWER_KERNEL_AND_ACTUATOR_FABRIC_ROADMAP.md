# Sentinel Power Kernel And Actuator Fabric Roadmap

Date: 2026-05-26

Status: canonical strategic roadmap for moving Sentinel from controlled internal
runtime to real-world controlled automation.

## Strategic Correction

Sentinel is not meant to become another single agent that can browse, summarize,
and write a report. That class of system is already commodity.

The target is stronger:

```text
Sentinel is a maximum-power controlled operating system for many specialized
agents and many real actuators.
```

The control plane remains the moat, but the next phase must be power-first. The
goal is not less safety. The goal is more real capability flowing through
explicit authority, receipts, evidence, budgets, kill switches, rollback where
possible, and FinalGate certification.

The practical doctrine:

```text
Do not control intelligence.
Control authority.
Give the system real hands.
Prove every side effect.
```

## Current Truth

Already real:

- native `BrainCognitionLoop` candidate source behind opt-in;
- `OrganDispatcher` into `DelegatedActionGate`;
- L2 local artifact execution;
- L3 reversible workspace mutation;
- L4 browser read-only/preparation/semantic extraction wrappers;
- low-risk FinalGate certificates;
- memory feedback through `RoleLoopMemoryBridge.build(...)`;
- replan-ready packets;
- mission authority and credential grant foundation;
- canonical organ safety scanner;
- audit remediation for several safety and determinism findings.
- Power Lab operator shell and mission-file runner;
- live Playwright-backed browser observation;
- live limited browser interaction through a hash-bound observation and browser
  FinalGate checks.

Still not enough for real-world power:

- no multi-agent mission society orchestrator;
- no persistent browser sessions or account/session continuity;
- no shell/code/app-builder sandbox;
- no real credential storage/resolution;
- no controlled channel send;
- no controlled API mutation;
- no desktop/vision/OCR sidecar;
- no spend/trading/broker adapters beyond fake or paper modes;
- no durable EventBus/WAL as the operational black box;
- no continuous mission loop.

## Target Architecture

Sentinel should be organized as four layers.

### 1. Power Kernel

The Power Kernel is the authority and proof layer. It owns:

- `MissionAuthorityEnvelope`;
- mission and credential grants;
- delegated lanes;
- budgets and use counters;
- kill switches;
- safety scanners;
- receipts;
- rollback posture;
- FinalGate certification;
- replay and memory feedback;
- durable audit trail.

Nothing in the Power Kernel should directly act on the world. It decides what is
allowed, records what happened, and can stop or revoke power.

### 2. Agent Society

Sentinel should not be one monolithic agent. It should supervise a controlled
society of agents:

- Mission Commander;
- Strategist;
- Researcher;
- Browser Operator;
- Code Builder;
- Security Tester;
- API Operator;
- Channel Operator;
- Finance/Spend Operator;
- Trading Operator;
- Desktop/Vision Operator;
- Verifier;
- Critic;
- Memory Curator.

Each agent proposes. None of them gets raw authority from model output. The
Power Kernel assigns lanes, budgets, contracts, and receipts.

### 3. Actuator Fabric

The Actuator Fabric is where real power lives:

- browser sessions, navigation, click, type, screenshots, DOM, downloads only
  when explicitly authorized;
- shell/code sandbox for builds, tests, scripts, local servers, app generation;
- filesystem/workspace mutation;
- external API read and controlled mutation;
- channel draft/send connectors;
- desktop app launch, screenshots, OCR, vision, window control;
- credential vault and session broker;
- spend/payment/trading adapters with hard limits;
- plugin/skill marketplace and sandbox;
- scheduler and continuous mission loop.

Actuators are allowed to be dangerous. They are not allowed to be undocumented,
ungated, unreceipted, or default-on.

### 4. Evidence And Memory Layer

Evidence and memory are measurements, not authority.

This layer stores:

- evidence refs;
- before/after screenshots;
- DOM/text snapshots;
- command output hashes;
- API response summaries;
- receipts and certificates;
- memory feedback signals;
- unresolved objections;
- replan packets.

Memory can influence future reasoning. Memory cannot grant power.

## Agent Lab Power Extraction Pipeline

`agent-lab/` becomes the Power Extraction Forge.

It studies systems such as OpenClaw, JARVIS, Hermes, Open Interpreter, browser
agents, AgentMemory systems, plugin ecosystems, and MCP-style tool systems.

The extraction process:

1. Audit the external system and identify actual capability surfaces.
2. Classify each surface by Sentinel level L2-L7.
3. Extract the capability pattern, not the vendor runtime.
4. Rewrite the capability as a Sentinel-native contract.
5. Add gate, budget, receipt, rollback or disable posture, and FinalGate.
6. Build a fake backend or dry-run adapter first.
7. Promote to a live backend only after tests prove containment.
8. Add the organ to a power preset.

What to take:

- OpenClaw-style browser/channel/plugin breadth;
- JARVIS-style multi-step autonomous tasking;
- Open Interpreter-style shell and code execution;
- Claude Code-style permission checkpoints and compaction;
- AgentMemory-style structured long-term state;
- OSWorld-style desktop tasks;
- CrewAI/AutoGen-style multi-agent division of labor.

What to avoid:

- direct tool calls from model output;
- vendor runtime import as production substrate;
- memory as instruction;
- plugins with ambient authority;
- browser sessions that bypass gate/receipt/FinalGate;
- credentials inside prompts or durable receipts;
- global auto mode.

## Power Presets

Presets are operator UX, not authority bypass.

### `lab_local`

Purpose: local development and proof.

Allowed by template:

- L2 artifacts;
- L3 reversible workspace mutation;
- local test/report artifacts;
- no credentials;
- no external mutation;
- no browser submit/login;
- no shell until shell sandbox pack is implemented.

### `browser_operator`

Purpose: live browser perception and controlled browser operations.

Allowed by template:

- L4 live read-only;
- L4 semantic extraction;
- L5 navigation/click/type after explicit grants;
- screenshots, DOM, text evidence;
- no login/session credentials by default;
- no payment, account creation, upload/download, arbitrary JS, or submit until
  separate authority contracts exist.

### `builder_dev`

Purpose: build apps and run local software.

Allowed by template after implementation:

- shell/code sandbox;
- dependency install inside scoped workspace or container;
- run tests/build/linters;
- start local dev servers;
- capture logs and receipts;
- no host-wide shell;
- no credential use by default.

### `red_team_authorized`

Purpose: authorized security testing.

Allowed by template after implementation:

- scope-bound target list;
- safe scanners and fuzzers;
- rate limits;
- no credential theft;
- no persistence, stealth, lateral movement, or destructive payloads;
- evidence-first reporting.

### `founder_growth`

Purpose: business-building workflows.

Allowed by template after implementation:

- market research;
- content drafting;
- CRM/API drafts;
- channel drafts;
- controlled send only after explicit approval;
- spend disabled by default.

### `finance_trading_guarded`

Purpose: paper trading first, later real trading with hard caps.

Allowed by template:

- paper trading;
- simulated spend;
- risk policy evaluation;
- real broker/spend adapters only under special authority, caps, kill switch,
  and explicit human approval gates.

### `full_power_special_authority`

Purpose: rare L7 authority.

Allowed by template:

- no default execution;
- explicit per-mission grants only;
- human confirmation checkpoints;
- hard budgets;
- revocation and kill switch;
- maximum receipts and audit.

## Roadmap Waves

### Wave A - Power Map Lock

Goal: replace the narrow browser-readonly roadmap with a real power map.

Deliverables:

- this roadmap;
- Agent Lab extraction backlog;
- preset definitions;
- first live-power benchmark list.

Status: PREPARED by this document.

### Wave B - Sentinel Power Lab Runtime V0

Goal: make Sentinel runnable as a real operator shell.

Deliverables:

- CLI entry point;
- mission file runner;
- explicit config loader;
- local run directory;
- event log artifact;
- Power Kernel status report;
- opt-in organ dispatch using existing L2/L3/L4 organs;
- no new dangerous actuator yet.

Capability gain: user can run Sentinel as a system, not only as a library.

Risk increase: low.

Rollback: remove CLI runner; core runtime unchanged.

### Wave C - Browser Operator Live L4/L5

Goal: give Sentinel real browser eyes and controlled hands.

Deliverables:

- Playwright or equivalent backend behind Sentinel contracts;
- persistent scoped browser sessions;
- screenshot/DOM/text evidence chain;
- read-only live navigation;
- L5 click/type/navigation with before/after evidence;
- no arbitrary JS in first pass;
- no submit/login/payment/upload/download until separately authorized.

Capability gain: high.

Risk increase: medium-high.

Rollback: terminate session; preserve evidence and receipts.

### Wave D - Shell, Code, And App Builder Sandbox

Goal: let Sentinel build and test software for real.

Deliverables:

- sandboxed command runner;
- command allowlist profiles;
- timeout and resource limits;
- workspace/container containment;
- stdout/stderr hashing and safe summaries;
- run tests, builds, linters, package installs, local servers;
- kill switch.

Capability gain: very high.

Risk increase: high.

Rollback: stop process, clean generated workspace when reversible, preserve
logs and receipts.

### Wave E - Skill And Plugin Fabric

Goal: harvest OpenClaw-style breadth without importing unsafe plugin authority.

Deliverables:

- skill manifest format;
- static scanner;
- capability classification;
- dry-run mode;
- permission prompts;
- adapter sandbox;
- revocation and disable list.

Capability gain: high.

Risk increase: high if unscanned; medium when sandboxed.

Rollback: disable skill, revoke grants, preserve audit.

### Wave F - Real Credential Vault And Session Broker

Goal: support scoped credentialed workflows without leaking secrets.

Deliverables:

- encrypted local vault backend;
- credential resolver;
- session broker;
- credential access proofs;
- revocation wins over all grants;
- no secret in memory, prompt, receipt, or logs.

Capability gain: very high.

Risk increase: high.

Rollback: revoke refs, rotate credentials, terminate sessions.

### Wave G - API, Channel, And DevOps Controlled Mutation

Goal: let Sentinel operate external systems under explicit contracts.

Deliverables:

- API read and mutation adapters;
- Slack/Discord/email draft and send connectors;
- GitHub/devops connectors;
- rate limits;
- recipient/domain allowlists;
- before/after proofs where possible.

Capability gain: very high.

Risk increase: very high.

Rollback: revoke tokens, issue compensating action where available, preserve
audit.

### Wave H - Spend, Payment, Trading, And Business Ops

Goal: let Sentinel participate in economic workflows.

Deliverables:

- paper-to-real promotion path;
- hard spend caps;
- per-action human confirmation;
- broker/payment adapters;
- loss limits;
- journal and audit receipts.

Capability gain: extreme.

Risk increase: extreme.

Rollback: kill switch, revoke credentials, close positions where authorized,
audit every action.

### Wave I - Desktop, Vision, OCR, And OS Control

Goal: operate outside the browser when needed.

Deliverables:

- desktop sidecar;
- screenshots;
- OCR;
- app launcher allowlist;
- window focus;
- no stealth;
- no host-wide uncontrolled shell.

Capability gain: high.

Risk increase: high.

Rollback: terminate sidecar and preserve visual evidence.

### Wave J - Continuous Multi-Agent Mission Orchestrator

Goal: move from single-run missions to a supervised society of agents.

Deliverables:

- mission queue;
- scheduler;
- agent roster;
- shared blackboard;
- task decomposition;
- parallel worker agents;
- supervisor and verifier;
- durable WAL;
- replan loop.

Capability gain: extreme.

Risk increase: high.

Rollback: pause queue, revoke lanes, preserve WAL.

## First Three Packs To Execute

### 1. `SENTINEL_POWER_LAB_RUNTIME_V0`

Create the runnable shell:

- CLI entry point;
- YAML/JSON mission input;
- config profiles;
- local run directory;
- explicit preset selection;
- run `AgentRuntime.run()`;
- output receipts, FinalGate, memory feedback, and replan packet paths.

No new dangerous actuator is introduced here.

### 2. `BROWSER_OPERATOR_AGENT_L4_L5_LIVE`

Create the first visible power:

- live browser backend;
- domain-scoped session;
- screenshot/DOM/text evidence;
- read-only navigation;
- controlled click/type/navigation;
- before/after evidence for L5;
- hard block submit/login/payment/upload/download/arbitrary JS in v0.

### 3. `SHELL_CODE_APP_BUILDER_SANDBOX_V0`

Create the builder muscle:

- run tests/builds/scripts inside a scoped sandbox;
- dependency install only in workspace/container;
- local app server launch;
- process kill switch;
- stdout/stderr receipts;
- no host-wide ambient shell.

## Real-World Benchmark Missions

These are the credibility tests. A roadmap that cannot pass these is not enough.

1. Build a small local app from a mission file, run its tests, start it locally,
   and produce an evidence report.
2. Browse a competitor website live, capture screenshots and DOM evidence, then
   update a local product page using L3 or shell sandbox.
3. Run an authorized security test against a local test app and produce a safe
   vulnerability report with reproduction evidence.
4. Create a growth campaign with channel drafts and a blocked-send receipt until
   explicit send authority exists.
5. Run a paper trading strategy with loss caps, receipts, and a kill switch.
6. Execute a multi-agent business-building mission where Browser Operator,
   Code Builder, Verifier, and Memory Curator coordinate through the Power
   Kernel.

## Non-Negotiables

- No vendor runtime import into production.
- No default-on dangerous power.
- No model output as authority.
- No memory, replay, receipt, or certificate as authority.
- No provider/backend/model override.
- No fallback or AUTO routing.
- No credential values in prompts, memory, receipts, logs, or tests.
- Every real side effect has a lane, contract, budget, receipt, and FinalGate.
- Every high-risk organ has a kill switch.
- Every irreversible or economic action needs explicit special authority.

## Next Pack

Start:

```text
SENTINEL_POWER_LAB_RUNTIME_V0
```

Reason:

```text
Before adding more actuators, Sentinel needs an operator shell that can run real
missions, select presets, write run artifacts, and make the existing closed
loop visible outside tests.
```
