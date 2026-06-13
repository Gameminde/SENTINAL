# Sentinel Power Kernel And Actuator Fabric Roadmap

Date: 2026-05-26

Status: canonical strategic roadmap for moving Sentinel from controlled internal
runtime to real-world controlled automation.

## Current Execution Truth - 2026-06-14

```text
current_phase = REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION_LOCKED
previous_phase = REAL_WORLD_POWER_BASELINE_AND_AGENTLAB_TASK_AUDIT_LOCKED
active_implementation_phase = REAL_WORLD_POWER_BASELINE_GREEN_GATE_REMEDIATION_LOCKED
next_phase = REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER
roadmap_doctrine = product power under provable authority
```

The baseline green-gate remediation closes the two failures recorded by the
baseline and AgentLab task audit. It is a zero-growth hardening lock, not a new
actuator phase. The full canonical core suite is green at `2686 passed, 0
failed, 3 skipped`. Existing foundations must now become demonstrated
end-to-end user power before Sentinel adds more special-authority or actuator
families. Security Testing Special Authority remains deferred.

Canonical roadmap:

```text
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_REAL_WORLD_POWER_CONVERGENCE_ROADMAP.md
```

This actuator-fabric roadmap remains the historical and architectural record
for the power kernel. The master roadmap owns the current cross-system build
sequence.

The company-level audit has been updated after Wave 1:

```text
updated_audit = sentinel-control/docs/reviews/SENTINEL_EXHAUSTIVE_COMPANY_LEVEL_AUDIT_UPDATED_AFTER_WAVE_1.md
delta_report = sentinel-control/docs/reviews/COMPETITIVE_GAP_DELTA_LOCK_REPORT.md
measurement_doctrine = product power under provable authority
```

Wave 1 is no longer a browser-only continuation. Browser is now one actuator
family inside the fabric. AgentLab is the extraction forge: OpenClaw, JARVIS,
OpenJarvis, Hermes, AgentMemory, TradingAgents, Chrome DevTools, and
CloakBrowser patterns are harvested conceptually and rewritten as
Sentinel-native contracts.

Wave 1 actuator families:

```text
browser
shell_sandbox
code_execution
external_api
channel
workspace
credential_ref
```

Canonical spec:

```text
sentinel-control/docs/actuators/POWER_ACTUATOR_FABRIC_WAVE_1_SPEC.md
sentinel-control/docs/reviews/SENTINEL_POWER_RUNTIME_V0_REPORT.md
sentinel-control/docs/reviews/SANDBOX_SHELL_CODE_ORGAN_V1_REPORT.md
sentinel-control/docs/reviews/EXTERNAL_API_READ_WRITE_ORGAN_V1_REPORT.md
sentinel-control/docs/reviews/CHANNEL_DRAFT_SEND_ORGAN_V1_REPORT.md
sentinel-control/docs/reviews/POWER_FABRIC_ORCHESTRATION_DEMO_REPORT.md
sentinel-control/docs/reviews/POWER_ACTUATOR_FABRIC_WAVE_1_SELF_AUDIT_REMEDIATION_REPORT.md
```

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
  FinalGate checks;
- CloakBrowser primary adapter for persistent browser sessions;
- Playwright compatibility backend for deterministic browser-session tests;
- persistent browser open/type/observe/close workflow with screenshot,
  accessibility snapshot, form-state hash, and receipt artifacts;
- deterministic browser trajectory planning from accessibility evidence, with
  self-healing target recovery for live L5 interactions;
- special-authority browser form submit for non-sensitive forms with
  before/after evidence and sensitive-field blocking;
- browser login credential session broker using scoped credential refs,
  metadata-only proofs, and ephemeral credential value resolution;
- browser upload/download quarantine using approved upload roots, download
  quarantine roots, and file hashes;
- browser JavaScript sandbox special authority for bounded page-side DOM
  operations with network/storage/cookie/submit/credential surfaces blocked.
- PowerRuntime orchestration demo coordinating browser/API/shell/workspace/
  channel-style steps with receipt refs, FinalGate refs, memory refs, and a
  verified timeline.
- LLM live operator cockpit with explicit UserModelContract product mode,
  deterministic test mode, structured output validation, internal mission
  kernel, pause/resume/kill, timeline, replay, PowerRuntime bridge, and
  default-off AgentRuntime bridge.
- durable local semantic memory with scoped namespaces, provenance, FTS,
  deterministic semantic retrieval, contradiction/supersession, expiry,
  deletion tombstones, optional Brain/cockpit recall, and optional AgentRuntime
  memory-feedback write-through.
- durable MissionKernel workflow records, checkpoints, branches, automatic
  PowerRuntime replan inside unchanged authority, and replay without
  re-execution.
- unified local observability telemetry/product-power metrics runtime before
  Worker Fleet, with hash-bound local event/metric streams and Certified Mode
  telemetry status.
- governed Mission Worker Fleet with strict child authority inheritance,
  worker budgets/deadlines/scopes, merge/reject/conflict contracts, telemetry,
  workflow checkpoint binding, and replay without re-execution.
- production local MissionDaemonRuntime with durable queue, leases, heartbeat,
  crash recovery inspection, dead-letter state, proposal-only scheduler, and
  operator-visible status/replay.
- local Model Amplification Execution Harness with content-addressed artifacts,
  hash-anchored edit verification, mission-scoped analysis kernel records,
  minimized tool-output envelopes, worker-safe typed results, conflict
  detection, telemetry, and replay without re-execution.
- governed Skill/Procedure Fabric with provenance-pinned manifests, declared
  authority and side effects, scanner, quarantine, dry-run evaluation,
  scorecards, approval/promotion/revocation lifecycle, receipt-bound
  execution, rollback posture, telemetry, and replay without re-execution.
- local Model Hardware And Cost Router with explicit `UserModelContract`,
  provider-catalog, local-runtime descriptor, and API descriptor candidates;
  safe read-only hardware snapshots; explicit-loopback-only runtime probes;
  route simulation, policy rejection reasons, route receipts, operator
  approvals, explicit UserModelContract bindings, telemetry, and replay without
  re-execution.
- real Channel Adapter foundation with webhook-style adapter descriptors,
  untrusted inbound handling, attachment/link quarantine, outbound drafts,
  operator approvals, recipient/scope/rate/idempotency gates, injected
  transport sends through the existing ChannelDraftSendOrganV1, receipts,
  FinalGate refs, telemetry, and replay without resend.
- realtime voice and ambient operator foundation with Sentinel-owned voice
  runtime, provider descriptors, fake/injected audio backend, VAD/turn
  detection, partial/final transcript events, barge-in/kill-word interruption,
  voice command envelopes, scoped ambient notifications, voice-to-desktop
  proposals, receipts, FinalGate, telemetry, and replay without audio playback,
  provider calls, or action replay.
- durable credential vault and secret broker foundation with local fake sealed
  store maturity, durable secret metadata, sealed hash refs, unlock sessions,
  scoped secret handles/leases, checkout token metadata, secret use receipts,
  FinalGate certificates, telemetry, leak scans, revocation/expiry/kill
  behavior, safe memory/worker/model-prompt summaries, and replay without
  secret materialization or external action.
- account creation/login special-authority foundation with governed account
  flow planning, CredentialVault lease binding, fake/injected login final
  consumer, fake/injected sandbox account creation, CAPTCHA/MFA/OTP/passkey/KYC
  checkpoints, session binding, receipts, FinalGate, telemetry, and replay
  without credential materialization or live provider calls.
- payment/spend/trading special-authority foundation with sandbox spend
  planning/execution, paper trade planning/execution, caps, velocity,
  merchant/recipient/instrument policy, checkpoints, payment idempotency,
  duplicate prevention, CredentialVault payment method lease refs, receipts,
  FinalGate, telemetry, and replay without live money, bank calls, payment
  provider calls, or live broker orders.

Still not enough for real-world power:

- no production multi-agent mission society orchestrator;
- no public skill marketplace or remote plugin execution;
- no production LSP/debugger/deep coding harness integration;
- no automatic model failover, hidden provider switching, model downloads, or
  model server management;
- durable credential vault / secret broker = CLOSED / local fake sealed store
  maturity with no raw secret persistence;
- production OS keychain, cloud vault, password manager import, and real
  encrypted secret backend = NOT_STARTED;
- account/session login special authority = CLOSED / local fake-injected sandbox foundation;
- live public-site account/login adapters and production OAuth/OIDC token exchange = NOT_STARTED;
- provider-specific Telegram/Slack/Gmail connectors and durable channel
  credential/session vaults are not started;
- no unbounded API mutation;
- permissioned desktop sidecar/visual grounding = CLOSED / local runtime with
  fake/injected action backend;
- live desktop operator backend and system monitoring = CLOSED / local
  same-process backend foundation with safe system/app/window/process/hardware
  snapshots, explicit monitoring sessions, fake/injected actions, benchmark
  gauntlet, receipts, FinalGate, telemetry, replay, and kill/revocation;
- production live opt-in desktop adapter and installed OS service sidecar =
  NOT_STARTED;
- production microphone/speaker voice adapters and live voice provider
  integrations = NOT_STARTED / V1 supports descriptors and fake/injected
  backend only;
- hidden always-on voice recorder, speaker biometric authentication, voice
  cloning, provider-owned tools, and voice-created authority = BLOCKED;
- payment/spend/trading special authority = CLOSED / sandbox spend and paper-trading local runtime;
- live money execution, payment provider/bank/broker connectors, and live
  broker order submission = NOT_STARTED / locked special authority;
- no durable EventBus/WAL as the operational black box;
- unified observability telemetry/product-power metrics runtime = CLOSED / local runtime;
- production telemetry service/cloud = NOT_STARTED;
- no production multi-process worker service or daemon service / OS supervisor.

Wave 1 current completion:

```text
POWER_ACTUATOR_FABRIC_WAVE_1_SPEC = CLOSED
SENTINEL_POWER_RUNTIME_V0 = CLOSED
SANDBOX_SHELL_CODE_ORGAN_V1 = CLOSED
EXTERNAL_API_READ_WRITE_ORGAN_V1 = CLOSED
CHANNEL_DRAFT_SEND_ORGAN_V1 = CLOSED
POWER_FABRIC_ORCHESTRATION_DEMO = CLOSED
POWER_ACTUATOR_FABRIC_SELF_AUDIT_REMEDIATION = CLOSED
POWER_ACTUATOR_FABRIC_WAVE_1 = LOCKED
COMPETITIVE_GAP_DELTA_LOCK = CLOSED
SENTINEL_LLM_LIVE_OPERATOR_COCKPIT_AND_MISSION_KERNEL_V0 = CLOSED
PERSISTENT_SEMANTIC_MEMORY_V1 = CLOSED
DURABLE_MISSION_WORKFLOW_AND_AUTOMATIC_REPLAN_V1 = CLOSED
OBSERVABILITY_TELEMETRY_AND_PRODUCT_POWER_METRICS_V1 = CLOSED
MISSION_WORKER_FLEET_AND_AUTHORITY_INHERITANCE_V1 = CLOSED
PRODUCTION_MISSION_DAEMON_AND_PROACTIVE_SCHEDULER_V1 = CLOSED
MODEL_AMPLIFICATION_EXECUTION_HARNESS_V1 = CLOSED
GOVERNED_SKILL_AND_PROCEDURE_FABRIC_V1 = CLOSED
LOCAL_MODEL_HARDWARE_AND_COST_ROUTER_V1 = CLOSED
REAL_CHANNEL_ADAPTERS_V1 = CLOSED
PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1 = CLOSED
LIVE_DESKTOP_OPERATOR_BACKEND_AND_SYSTEM_MONITORING_V1 = CLOSED
REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1 = CLOSED
DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1 = CLOSED
ACCOUNT_CREATION_AND_LOGIN_SPECIAL_AUTHORITY_V1 = CLOSED
PAYMENT_SPEND_TRADING_SPECIAL_AUTHORITY_V1 = CLOSED
REAL_WORLD_POWER_BASELINE_AND_AGENTLAB_TASK_AUDIT = LOCKED
REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER = NEXT
SECURITY_TESTING_SPECIAL_AUTHORITY_V1 = DEFERRED / NOT_STARTED
```

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

- CloakBrowser primary backend and Playwright compatibility backend behind
  Sentinel contracts;
- persistent scoped browser sessions with hashed profile metadata;
- screenshot/DOM/text evidence chain;
- read-only live navigation;
- L5 click/type/navigation with before/after evidence;
- deterministic target ranking and recovery for accessible browser targets;
- L6 non-sensitive form submit behind special authority;
- L6 credential-backed login/session broker with raw credential durability
  blocked;
- L6 upload/download quarantine with file hash receipts;
- L6 JavaScript sandbox with hash-only script/result receipts;
- no payment until separately authorized.

Status:

- `BROWSER_OPERATOR_AGENT_L4_L5_LIVE` = CLOSED;
- `BROWSER_SESSION_MANAGER_L5_LIVE` = CLOSED;
- `BROWSER_TRAJECTORY_PLANNER_AND_SELF_HEALING_L5` = CLOSED;
- `BROWSER_FORM_SUBMIT_SPECIAL_AUTHORITY_L6` = CLOSED;
- `BROWSER_LOGIN_CREDENTIAL_SESSION_BROKER_L6` = CLOSED;
- `BROWSER_DOWNLOAD_UPLOAD_QUARANTINE_L6` = CLOSED;
- `BROWSER_ARBITRARY_JS_SANDBOX_SPECIAL_AUTHORITY_L6` = CLOSED;
- `BROWSER_PAYMENT_SPEND_SPECIAL_AUTHORITY_L7` = NEXT.

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

### 3. `BROWSER_TRAJECTORY_PLANNER_AND_SELF_HEALING_L5`

Create the genius browser layer:

- transform observations into ranked target/action trajectories;
- maintain session memory across tabs/pages;
- recover from missing selectors, navigation changes, and dynamic UIs;
- compare screenshot/AX/DOM evidence before choosing an action;
- run local benchmark missions against BrowserGym/WebArena-style tasks;
- still keep submit/login/payment/upload/download/arbitrary JS behind later
  special-authority packs.

### 4. `SHELL_CODE_APP_BUILDER_SANDBOX_V0`

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

- No vendor runtime may become authority. Approved engines such as CloakBrowser
  can be wrapped behind Sentinel-native adapters, contracts, receipts, and
  kill switches.
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
REAL_WORLD_POWER_CONVERGENCE_WAVE_1_CODING_WORKSPACE_AND_BROWSER_LIVE_POWER
```

Reason:

```text
Sentinel has a strong governed local runtime and multiple mature foundations,
but the task-level baseline measures overall real-world product power at
5.4 / 10 because live external backend reach and productized end-to-end task
proof remain limited. The next step is to converge the already-real bounded
workspace, shell, harness, and browser paths into representative coding and
browser missions with measured recovery, interventions, receipts, replay, and
kill behavior. No new actuator family or special authority is required.
```
