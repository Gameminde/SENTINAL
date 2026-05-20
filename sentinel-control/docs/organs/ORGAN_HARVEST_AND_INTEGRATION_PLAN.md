# Organ Harvest And Integration Plan

Status: audit lock

Date: 2026-05-19

## Harvest Law

```text
Take mechanisms.
Rewrite Sentinel-native.
Avoid vendor runtime bridges.
Fake-eval before integration.
```

Vendor systems are capability mines, not authority sources.

## Vendor Harvest Matrix

### OpenClaw

Take:

- gateway/action-kernel event shapes;
- browser snapshot, trace, role snapshot, screenshot, interaction dry-run;
- channel/plugin manifest vocabulary;
- static scanner report shape;
- fake runtime benchmark style;
- external-content warning wrappers.

Rewrite:

- browser gateway as Sentinel Browser Organ contracts;
- channel plugins as draft/send candidates with recipient provenance;
- skills/plugins as scanned manifests and sandbox fixtures;
- plugin approvals as Sentinel gates and receipts.

Avoid:

- host plugin install;
- default-open plugin routes;
- shell/PTY tools;
- real channel send;
- browser submit/login/upload/download before special authority;
- background services;
- raw memory/tool/provider persistence.

Safe integration:

- continue source-only audits in `agent-lab`;
- expand scanner fixtures for browser/channel/plugin/MCP;
- port only schemas and eval ideas, not runtime code.

### Hermes Agent

Take:

- durable memory concepts;
- compact skill index;
- context scanning;
- tool hook points;
- subagent budget/delegation traces;
- compression discipline.

Rewrite:

- memory into Sentinel epistemic memory and no-authority retrieval;
- skill index into `SkillIndexCompiler`;
- hook chain into fail-closed `FirewallDispatchPipeline`;
- subagents into proposal-only `SubagentPlan` until explicit lanes exist.

Avoid:

- Hermes runtime;
- OAuth setup;
- tool dispatcher that can execute directly;
- memory-as-policy;
- fail-open hook failures;
- skill scripts as trusted instructions.

Safe integration:

- build skill scanner before skill index;
- allow memory to suggest verification only;
- add hook receipts and pre/post transform audit before any tool hook.

### Claude Code

Take:

- permission layering;
- explicit filesystem and shell boundaries;
- compaction pipeline;
- tool-use transcript discipline;
- code review and verification-before-completion habit.

Rewrite:

- permissions into Sentinel authority envelopes and delegated lanes;
- compaction into memory snapshots with claim status and TTL;
- shell/code execution into sandbox/test-runner organs.

Avoid:

- trusting compacted history as truth;
- shell as ambient capability;
- model-chosen tool permissions.

Safe integration:

- use compaction as data-not-instruction;
- add FinalGate certification to code/test receipts;
- never let code-agent convenience bypass organ gates.

### AutoGen

Take:

- multi-agent role topology;
- conversation orchestration;
- critic/reviewer roles;
- tool-router separation.

Rewrite:

- role society as explicit Brain cognition steps;
- agents as proposal producers, not executors;
- tool calls as organ candidates and gates.

Avoid:

- autonomous agent-to-tool execution;
- role consensus as approval;
- hidden planner/executor loops.

Safe integration:

- every agent output becomes a proposal, evidence critique, or objection;
- no agent can create authority or a lane.

### CrewAI

Take:

- task/role/crew decomposition;
- process templates;
- work package handoff ideas.

Rewrite:

- crew tasks into BrainCognitionLoop traces and proposal artifacts;
- tool assignments into organ candidates.

Avoid:

- task kickoff that directly runs tools;
- persistent tool credentials inside agent roles.

Safe integration:

- crew-style planning remains cognition-only until DelegatedActionGate.

### Open Interpreter

Take:

- interactive code/shell UX ideas;
- local execution trace expectations;
- stdout/stderr capture model.

Rewrite:

- shell into sandbox shell organ;
- code execution into test runner/code execution organ;
- interactive commands into explicit plan/preview/approval receipts.

Avoid:

- host shell;
- arbitrary code execution;
- dependency installs;
- direct filesystem or network mutation.

Safe integration:

- no host interpreter;
- container/diff/receipt first;
- command allowlist and kill switch.

### JARVIS And OpenJarvis

Take:

- sidecar capability manifests;
- approval lifecycle and audit trail;
- desktop/screen awareness;
- hardware/cost/latency routing vocabulary;
- skill import quarantine.

Rewrite:

- sidecar as signed `PermissionedSidecarManifest`;
- desktop observe/action as separate organs;
- routing metrics as budget recommendations only;
- skill import as source-only scanner/quarantine.

Avoid:

- daemon runtime import;
- raw terminal/filesystem/desktop RPC;
- browser templates as prompt authority;
- automatic config evolution;
- auto model/provider routing.

Safe integration:

- desktop observe before action;
- no clipboard/screenshot raw durability;
- cost routing cannot override user model contract.

### Browser Agents And OSWorld-Style Systems

Take:

- long-horizon UI task evals;
- visual grounding benchmarks;
- before/after screen proof;
- action recovery and state checking.

Rewrite:

- action engine into Sentinel Browser Action Organ and Desktop Sidecar Action
  Organ;
- task state into receipts and FinalGate checks.

Avoid:

- direct UI action from natural language;
- CAPTCHA/stealth/bypass;
- login/session mutation without special authority.

Safe integration:

- fake UI benches first;
- observe-only and preparation before action;
- all visual instructions are untrusted.

### AgentMemory

Take:

- typed memory strata;
- observe first, derive later;
- deterministic compression;
- working memory slots;
- TTL/supersession/confidence/retention;
- hybrid retrieval roadmap;
- temporal graph/replay/checkpoints.

Rewrite:

- Sentinel epistemic witness model;
- safe hot slots;
- lexical + metadata retrieval first;
- replay/checkpoints as authority-neutral history.

Avoid:

- default-open memory server;
- raw prompt/tool/provider response persistence;
- memory-as-prompt authority;
- broad MCP/API memory surface;
- LLM graph as truth;
- destructive delete before tombstone/audit.

Safe integration:

- memory may guide verification, never authorize action;
- self-generated receipts cannot satisfy evidence requirements alone.

### MCP And Tool Ecosystems

Take:

- typed tool schemas;
- resource discovery;
- connector marketplace vocabulary;
- user-visible permission UX.

Rewrite:

- MCP broker as Sentinel organ interface;
- tool schemas into organ candidates;
- connector access into credential refs and scoped grants.

Avoid:

- broad tool surface directly exposed to model;
- server/runtime install without scanner;
- hidden background tools;
- memory/tool server granting authority.

Safe integration:

- MCP scanner first;
- all tool invocations pass candidate -> gate -> executor contract.

### TradingAgents

Take:

- analyst role split;
- bull/bear debate;
- risk debate trio;
- portfolio manager gate;
- checkpoint/reflection;
- rating parser.

Rewrite:

- trading cognition as Brain roles and risk review;
- paper-only trading org;
- special authority for any live market action.

Avoid:

- live broker integration;
- live market API dependency by default;
- model output as investment authority;
- credential/provider fallback.

Safe integration:

- fake market data and paper trades first;
- max-loss, stop-loss, broker contract, and L7 authority before live.

### RedditPulse Adjacent App

Take:

- job-worker orchestration pattern;
- config-file handoff instead of long CLI argument interpolation in safer
  routes;
- validation/enrichment/report task decomposition;
- admin capability awareness.

Rewrite:

- Python workers as a Sentinel Job Worker Organ;
- report generation as sandboxed local artifact or sandbox shell job;
- provider-backed analysis as model/API organs with scoped credentials and
  receipts;
- admin scraper as explicit scheduler/job candidate, not env-command exec.

Avoid:

- Node `exec(...)` around command strings;
- arbitrary `ADMIN_SCRAPER_COMMAND`;
- child processes inheriting broad provider/Supabase/encryption keys;
- stdout/stderr logs containing sensitive data;
- web routes triggering host processes outside Sentinel authority envelopes.

Safe integration:

- no direct import into Sentinel organs;
- build a sandbox job organ with argv allowlist, env allowlist, timeout,
  budget, receipts, and FinalGate;
- treat RedditPulse as adjacent product code, not Sentinel control-plane law.

## Cross-Vendor Patterns To Harvest

| Capability | Take | Rewrite target | Required eval |
| --- | --- | --- | --- |
| Browser snapshots | DOM/AX/screenshot trace | Browser Read-Only and Action organs | prompt injection, stale DOM, submit blocked |
| Desktop sidecar | capability manifest and enrollment | Desktop Observe/Action organs | token replay, screenshot secret, destructive click |
| Skill/plugin ecosystem | manifests, scanner, sandbox | Skill Scanner/Sandbox/Plugin Runtime | malicious skill, install script, secret request |
| Tool hooks | pre/post check points | Firewall hook chain | fail-closed hook and transform audit |
| Memory compaction | typed summaries and TTL | Sentinel Memory Bridge | stale memory, contradiction, no authority |
| Multi-agent debate | adversarial role structure | Brain risk/reviewer roles | unsupported claim blocked |
| Cost routing | cost/latency/energy metrics | budget recommendations | no provider/model override |
| Execution receipts | trace/audit style | universal organ receipts | deterministic hash, no raw secret |
| Job workers | config-file handoff and queueing | Job Worker Organ | no shell, env isolation, stdout/stderr redaction |

## Integration Rules

No harvested capability may skip:

1. source audit;
2. static scanner or capability map;
3. Sentinel-native interface spec;
4. fake eval;
5. proposal candidate;
6. DelegatedActionGate;
7. explicit executor contract;
8. receipt;
9. rollback/disable posture;
10. FinalGate.

## Harvest Verdict

The highest-value harvest is OpenClaw browser power plus JARVIS sidecar
discipline plus AgentMemory epistemic memory. The highest-risk harvest is any
plugin/runtime bridge. The correct path is not integration. It is
Sentinel-native rewriting.
