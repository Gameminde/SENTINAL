# Agent Lab Plan

## Mission

Build a controlled research lab for agent runtimes. The lab studies capabilities, failure modes, and reusable architecture patterns without integrating risky execution into Sentinel Control.

## Current Decision

Keep this workspace separate from `sentinel-control`.

## 2026-06-06 Strategic Refresh

The previous forensic reports remain historical baselines, but they are no
longer sufficient as current competitive truth.

Refreshed doctrine:

```text
measure product power under provable authority
control is a release condition, not the only score
contract-only is not live power
vendor source is a specimen, never a runtime dependency
```

Current work products:

- `audits/TRENDING_AGENT_ADMISSION_MATRIX_2026_06_06.md`
- `audits/final/2026-06-06_agent_lab_vendor_refresh_delta_report.md`
- `audits/final/2026-06-06_sentinel_competitive_power_delta_and_roadmap.md`

The immediate Sentinel recommendation remains `PERSISTENT_SEMANTIC_MEMORY_V1`,
followed by durable automatic replan/workflow execution and a real
authority-inheriting worker fleet. The next operating-layer step is a
production mission daemon with a proactive scheduler whose triggers can
propose work but never create authority. A model-amplifying execution harness
then improves completion power through better edit anchors, typed workers,
analysis kernels, and tool ergonomics without changing the selected LLM.

Sentinel remains focused on:

1. GTM Pack quality.
2. Evidence-backed business decisions.
3. AgentOps Firewall controls.
4. Safe local execution only.

Agent Lab focuses on:

1. Runtime research.
2. Capability benchmarking.
3. Failure-mode mapping.
4. Future runtime blueprinting.

Current strategic correction:

- Agent Lab is now upgraded into Agent Forensics Lab.
- Vendors are specimens, not integrations.
- The output is Sentinel rewrite knowledge: `Superpower`, `Failure`, `Sentinel Rewrite`.
- No OpenClaw/Hermes/OpenJarvis/JARVIS bridge is authorized.
- No vendor code is copied into Sentinel.
- No vendor runtime is installed or run.

## Sprint A - Lab Setup

Status: in progress.

Tasks:

- Create isolated workspace structure.
- Add README and safety rules.
- Add capability matrix.
- Add failure matrix.
- Add reuse strategy.
- Add benchmark plan.
- Add Sentinel integration notes.

Acceptance:

- No vendor code is copied into Sentinel.
- Every benchmark uses sandbox resources.
- Every risky feature has a proposed Sentinel Firewall mitigation.

## Sprint B - Capability Matrix

Status: started with OpenClaw Sprint B1 static audit.

Tasks:

- Fill in observations for OpenClaw, Hermes Agent, OpenJarvis, and JARVIS.
- Map each capability to Sentinel current and Sentinel target.
- Mark each capability as Take, Rewrite, Avoid, or Later.

Acceptance:

- No capability enters Sentinel target without a policy implication.
- Every execution feature has a Firewall position.

## Sprint B1 - OpenClaw Static Audit

Status: completed.

Completed:

- cloned OpenClaw source into `vendors/openclaw/source`;
- recorded clone decision in `audits/vendor_clone_checks.md`;
- created `audits/openclaw_static_audit.md`;
- updated `audits/openclaw_capability_map.md`;
- updated `audits/CAPABILITY_MATRIX.md` with source-backed OpenClaw observations;
- updated `audits/FAILURE_MODES.md` with OpenClaw-specific risk notes;
- created `sentinel_integration_notes/openclaw_to_sentinel.md`.

Acceptance:

- OpenClaw was not run.
- Dependencies were not installed.
- No real accounts were connected.
- Findings cite local source paths.
- Reusable patterns include Sentinel Firewall implications.

## Sprint B2 - OpenClaw Dependency Audit And Static Scanner

Status: completed.

Completed:

- created `audits/openclaw_dependency_audit.md`;
- inspected root package scripts, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, postinstall scripts, Dockerfiles, env example, native dependency declarations, and browser/messaging/credential surfaces;
- built `tools/openclaw_static_scanner/` as a read-only Python scanner;
- added scanner fixtures for safe plugin, shell plugin, env-secret plugin, channel-send plugin, secret-manager skill, package-install skill, and prompt-injection skill;
- added unit tests for scanner risk classification and output schema;
- generated `audits/openclaw_scanner_report.json`;
- created `audits/openclaw_scanner_report.md`;
- updated `audits/FAILURE_MODES.md` with scanner-backed OpenClaw findings;
- updated `sentinel_integration_notes/openclaw_to_sentinel.md` with SkillScanner, ChannelAdapterManifest, PluginRiskClassifier, and promotion requirements.

Acceptance:

- OpenClaw was not run.
- Dependencies were not installed.
- Skills and plugins were not executed.
- Scanner reads files only.
- Scanner flags shell, secrets, network, filesystem, install commands, browser, channel send, background service, memory, and prompt-injection patterns.
- High-risk skills/plugins are classified as `blocked` or `needs_review`.
- No pattern is promoted to Sentinel without Firewall policy implications.

## Sprint B2.5 - Scanner Report Consistency Lock

Status: completed.

Completed:

- upgraded `tools/openclaw_static_scanner/scanner.py` to `scanner_version` `0.2.0`;
- added `ruleset_version` `2026-04-24.b2.5`;
- added canonical report metadata: scan timestamp, source commit, source path, total items, and JSON content hash;
- changed scanner CLI so one command generates both `audits/openclaw_scanner_report.json` and `audits/openclaw_scanner_report.md`;
- made the Markdown report generated from the JSON report only;
- added machine-readable Markdown count comments for consistency checks;
- added consistency tests comparing JSON totals, risk counts, and Sentinel decision counts against Markdown;
- added risk-threshold and Sentinel decision explanations to the generated Markdown report;
- regenerated the canonical OpenClaw scanner report from source commit `a2288c2b09e621f89a915960398f58e200b3b69d`.

Canonical scanner result:

- total items: 83;
- plugins/root-script items: 31;
- skills: 52;
- risk counts: `critical` 52, `high` 29, `medium` 2;
- Sentinel decisions: `blocked` 52, `needs_review` 29, `draft_only_tool` 2;
- JSON report hash: recorded in `audits/openclaw_scanner_report.json` under `metadata.json_sha256`.

Acceptance:

- One canonical scanner JSON exists.
- One Markdown report exists and is generated from that JSON.
- No contradictory scanner counts remain in current B2.5 outputs.
- Consistency tests pass.
- Scanner results are reproducible from one command.

Fresh clone verification note, 2026-04-26:

- committed B2.5 JSON/Markdown artifacts are internally consistent;
- scanner consistency tests pass in this clone;
- `vendors/openclaw/source` was restored locally from `https://github.com/basetenlabs/openclaw-baseten.git`;
- source checkout is `a2288c2b09e621f89a915960398f58e200b3b69d`;
- a fresh scanner rerun from OpenClaw source completed successfully;
- no dependencies were installed, no runtime was executed, and no accounts were connected.

## Sprint B3 - OpenClaw Fake Runtime Benchmarks

Status: completed initial fake-only benchmark harness.

Completed:

- created `benchmarks/openclaw_fake_runtime/`;
- added fake channel messages for prompt injection, external-send request, browser form submit, filesystem traversal, and memory/policy override;
- added a fake plugin manifest declaring `sendMessage`;
- added fake skills for package install, 1Password access, and persistent policy override;
- added `expected_results.json`;
- added `benchmark_runner.py`;
- generated `reports/openclaw_fake_benchmark_report.md`.

Result:

- fixtures: `9`;
- failures: `0`;
- decisions: `blocked` 9;
- risk counts: `critical` 2, `high` 7.

Acceptance:

- No OpenClaw runtime was executed.
- No OpenClaw skills or plugins were executed.
- No dependencies were installed.
- No accounts, channels, browsers, or credentials were connected.
- Every fake input produced policy mapping, dry-run preview, approval simulation, and trace events.
- All fake dangerous inputs were blocked.

## Sprint C - Failure Matrix

Tasks:

- Analyze prompt injection.
- Analyze malicious skills.
- Analyze credential leakage.
- Analyze unauthorized external actions.
- Analyze filesystem escape.
- Analyze shell abuse.
- Analyze memory poisoning.
- Analyze cost explosion.
- Analyze unsafe self-improvement.

Acceptance:

- Each failure has a Sentinel mitigation.
- Each mitigation has a test requirement.

## Sprint D - Runtime Blueprint

Tasks:

- Decide whether to build browser sandbox.
- Decide whether to build desktop sidecar.
- Decide whether to build channel adapters.
- Decide whether to build skill scanner.
- Decide whether to build local model/cost router.

Acceptance:

- No advanced runtime feature can move forward without a risk class, dry-run design, approval rule, and trace schema.

## Do Not Do Yet

- Do not run vendor sidecars.
- Do not connect real accounts.
- Do not enable browser submit.
- Do not enable email send.
- Do not enable shell execution.
- Do not enable desktop automation.
- Do not add vendor code to Sentinel.

## Sprint G0 - Agent Forensics Protocol

Status: completed initial protocol and genome artifacts.

Completed:

- created `audits/AGENT_FORENSICS_PROTOCOL.md`;
- created `audits/SUPER_AGENT_GENOME.md`;
- created `audits/AGENT_COMPARISON_MATRIX.md`;
- created `audits/SUPERPOWER_EXTRACTION_TABLE.md`;
- created `audits/VENDOR_FAILURE_INDEX.md`;
- created `audits/SENTINEL_REWRITE_PRINCIPLES.md`;
- updated `audits/vendor_clone_checks.md` for Hermes Agent, OpenJarvis, and JARVIS clone-only status.

Acceptance:

- Every vendor remains source-only.
- Every documented superpower maps to a Sentinel rewrite, not an integration.
- Every risky power has Firewall, trace, and eval implications.

## Sprint G1 - Hermes Forensic Audit

Status: initial source-only forensic audit completed.

Focus:

- memory persistence;
- skill prompt index;
- tool hooks;
- prompt injection scanning;
- delegation/subagent iteration budgets;
- skill creation and Google Workspace setup risks.

## Sprint G2 - OpenJarvis Forensic Audit

Status: initial source-only forensic audit completed.

Focus:

- local/cloud routing;
- hardware-aware model choice;
- learning metrics;
- agent config evolution;
- skill import/sync from external sources.

## Sprint G3 - JARVIS Forensic Audit

Status: initial source-only forensic audit completed.

Focus:

- daemon and sidecar;
- authority model;
- approval and audit trail;
- desktop/browser/clipboard/filesystem/terminal RPC;
- app-specific browser templates.

## Sprint G4 - Sentinel Super Agent Synthesis

Status: initial synthesis completed, now paused before build planning.

Completed:

- created `audits/SENTINEL_SUPER_AGENT_BLUEPRINT.md`;
- created `audits/SENTINEL_RUNTIME_CAPABILITY_ROADMAP.md`;
- created `audits/SENTINEL_AGENT_LOOP_SPEC.md`;
- created `audits/SENTINEL_MEMORY_SPEC.md`;
- created `audits/SENTINEL_SKILL_SPEC.md`;
- created `audits/SENTINEL_COST_ROUTER_SPEC.md`;
- created `audits/SENTINEL_SIDECAR_SPEC.md`.

Synthesis rule:

- OpenClaw, Hermes Agent, OpenJarvis, and JARVIS remain lab specimens.
- Sentinel must rewrite capabilities from first principles.
- No vendor runtime, vendor bridge, vendor dependency, or vendor code path is approved for Sentinel.
- This synthesis is not sufficient to build the final Sentinel runtime.
- The next phase is one final lab-grade forensic report per vendor before any global build plan.

Core Sentinel loop:

```text
see -> verify -> reason -> debate -> plan -> simulate -> approve -> execute -> trace -> learn
```

Capability gates:

- memory can inform decisions but cannot override policy;
- skills must be scanned, declared, sandboxed, permissioned, tested, approved, and traced;
- cost routing must enforce budget caps and trace model/provider choices;
- sidecar/browser/channel powers remain later-stage capabilities behind manifests, dry-run previews, approval, and fake benchmarks.

## Agent-by-Agent Deep Reverse Phase

Status: active.

Rule:

- No Sentinel runtime build is authorized from G0-G4 alone.
- Each vendor must receive a final forensic report before final cross-agent synthesis.
- Reports must cite local source paths, functions/classes/modules, algorithms, prompts, side effects, failures, and Sentinel rewrite principles.
- Vendor sources remain specimens only: no install, no runtime, no integration, no copied code.

Order:

1. OpenClaw final forensic report.
2. Hermes final forensic report.
3. OpenJarvis final forensic report.
4. JARVIS final forensic report.
5. Final cross-agent comparison.
6. Sentinel architecture from first principles.

## Sprint G5 - OpenClaw Final Forensic Report

Status: completed source-only final report.

Output:

- `audits/final/openclaw_final_forensic_report.md`

Completed:

- consolidated B1 static audit, B2 dependency audit, B2.5 scanner consistency lock, and B3 fake runtime benchmark evidence;
- inspected OpenClaw source paths for agent loop, prompts, skills, plugin loader/registry/runtime, gateway, exec approval, browser, channels, memory, model fallback, sub-agents, security helpers, and side effects;
- extracted algorithm/math mechanisms including context window guard, model fallback, auth profile ordering, memory hybrid scoring, exec allowlist logic, plugin install path guard, and sub-agent ping-pong bounds;
- separated `TAKE`, `REWRITE`, and `AVOID` decisions;
- documented missing runtime behavior and unknowns caused by the source-only constraint.

Acceptance:

- OpenClaw was not run.
- Dependencies were not installed.
- Skills and plugins were not executed.
- No accounts, channels, browsers, shells, or credentials were connected.
- The final report cites local source paths and functions/modules.
- The report is rewrite knowledge only, not a Sentinel build plan.

## Sprint G6 - Hermes Final Forensic Report

Status: completed source-only final report.

Output:

- `audits/final/hermes_final_forensic_report.md`

Completed:

- consolidated G1 Hermes static audit, algorithm map, prompt map, memory map, skill map, failure modes, learning map, and Sentinel rewrite notes;
- inspected Hermes source paths for agent loop, iteration budgets, context compression, prompt assembly, memory stores, external memory providers, skill index, skill command expansion, plugin loaders, shell hooks, terminal/code execution surfaces, approvals, Google Workspace setup, delegation, and tool dispatch hooks;
- extracted algorithm/math mechanisms including parent/child iteration budgets, subagent concurrency/depth/timeout, compression thresholds, prompt-cache routing, memory char limits, skill prompt caching, provider search scoring, approval hardline/smart approval flow, and hook dispatch behavior;
- separated `TAKE`, `REWRITE`, and `AVOID` decisions;
- documented missing runtime behavior and unknowns caused by the source-only constraint;
- identified the next needed experiment as a deterministic Hermes static scanner for skills, plugins, memory providers, setup scripts, OAuth scopes, and shell/process surfaces.

Acceptance:

- Hermes was not run.
- Dependencies were not installed.
- Skills, plugins, memory providers, shell hooks, gateways, OAuth flows, browsers, channels, and background services were not executed.
- No accounts, credentials, browser profiles, or external services were connected.
- The final report cites local source paths and functions/modules.
- The report is rewrite knowledge only, not a Sentinel build plan.

## Sprint G7 - OpenJarvis Final Forensic Report

Status: completed source-only final report.

Output:

- `audits/final/openjarvis_final_forensic_report.md`

Completed:

- consolidated G2 OpenJarvis static audit, algorithm map, cost router map, skill import map, failure modes, and Sentinel rewrite notes;
- inspected OpenJarvis source paths for hardware detection, model recommendation, query complexity scoring, heuristic routing, learned routing, agent loop, loop guard, tool executor, capability policy, boundary guard, skill import, memory retrieval, cost/savings math, telemetry, benchmarks, sandbox, shell/code/browser/HTTP tools, Claude Code bridge, WhatsApp bridge, scanners, and audit logging;
- extracted algorithm/math mechanisms including hardware memory estimation, model tiering, query complexity weighted score, thinking-token multiplier, heuristic router thresholds, learned router confidence threshold, route reward, tool/agent scoring, max-turn recommendation, loop guard thresholds, RRF memory fusion, dense retrieval scoring, ColBERT MaxSim, cloud cost estimate, savings/FLOPs/MFU formulas, and benchmark p95/throughput/energy stats;
- separated `TAKE`, `REWRITE`, and `AVOID` decisions;
- documented missing runtime behavior and unknowns caused by the source-only constraint;
- identified the next needed experiment as a deterministic OpenJarvis static scanner for tools, channel adapters, skill imports, subprocess surfaces, dynamic loaders, prompt overrides, memory injection sites, and config-write paths.

Acceptance:

- OpenJarvis was not run.
- Dependencies were not installed.
- Skills, plugins, channels, browser tools, shell tools, code tools, sandboxes, model hosts, dashboards, and background services were not executed.
- No accounts, credentials, browser profiles, WhatsApp auth state, Docker containers, local models, or cloud providers were connected.
- The final report cites local source paths and functions/modules.
- The report is rewrite knowledge only, not a Sentinel build plan.

## Sprint G8 - JARVIS Final Forensic Report

Status: completed source-only final report.

Output:

- `audits/final/jarvis_final_forensic_report.md`

Completed:

- consolidated G3 JARVIS static audit, sidecar map, desktop awareness map, permission map, failure modes, and Sentinel rewrite notes;
- inspected JARVIS source paths for daemon startup, agent loop, tool registry, authority engine, approval lifecycle, deferred executor, audit trail, sidecar enrollment, sidecar RPC protocol, terminal/filesystem/clipboard/screenshot handlers, browser CDP tools, desktop tools, observers, awareness/OCR/struggle scoring, workflow triggers, role prompts, webapp templates, and vault retrieval;
- extracted algorithm/math mechanisms including authority thresholds, effective authority logic, unknown-tool fallback, RPC/detached timeouts, heartbeat limits, event size caps, sidecar default capability config, browser snapshot limits, screen-diff sampling, awareness cost estimate, struggle weighted score, suggestion rate limits, workflow auto-suggest thresholds, poll intervals, vault retrieval limits, and goal score clamping;
- separated `TAKE`, `REWRITE`, and `AVOID` decisions;
- documented missing runtime behavior and unknowns caused by the source-only constraint;
- identified the next needed experiment as a deterministic JARVIS static scanner for sidecar RPC methods, desktop/browser tools, workflow nodes, role tools/authority, webapp templates, config mutation surfaces, OAuth/channel adapters, and prompt-injection sources.

Acceptance:

- JARVIS was not run.
- Dependencies were not installed.
- Sidecar, daemon, browser, terminal, desktop automation, clipboard, screenshot, channels, workflows, OAuth setup, and account integrations were not executed.
- No accounts, credentials, browser profiles, sidecar tokens, local desktop sessions, messages, or external services were connected.
- The final report cites local source paths and functions/modules.
- The report is rewrite knowledge only, not a Sentinel build plan.

## Sprint G9 - Cross-Agent Forensic Synthesis

Status: completed source-only synthesis.

Output:

- `audits/final/g9_cross_agent_synthesis.md`

Completed:

- consolidated the four final vendor reports into one strict cross-agent synthesis;
- compared OpenClaw, Hermes Agent, OpenJarvis, and JARVIS by core power, failure surface, Sentinel rewrite value, runtime risk, immediate relevance, and future moat;
- extracted the dominant primitives: gateway action kernel, skill scanner, approval queue, trace ledger, persistent memory, skill manifest, CostRouter, query complexity scoring, context compression, sidecar manifest, screen awareness, browser operator, workflow triggers, and learning from traces;
- produced a convergence failure index covering prompt injection, memory poisoning, malicious skills/plugins, shell abuse, filesystem escape, browser submit, external send, credential leakage, sidecar overreach, runtime install, dynamic loading, cost explosion, unsafe self-improvement, policy fragmentation, and trace gaps;
- ruled on the key conflicts: execution is blocked until firewall exists, memory is never authority, cost is a safety boundary, sidecar is a separate product track, browser starts read-only, skills are supply chain, and learning proposes rather than mutates;
- defined the Sentinel Super Agent Genome as G9 synthesis only: Evidence Authority, Capability Manifest, Firewall Kernel, Memory Without Authority, Cost-Aware Reasoning, Skill Quarantine, Read-Only Browser First, Permissioned Sidecar Later, Learning As Proposal, and Trace As Product Memory;
- defined G10 constraints and entry criteria without implementing Sentinel runtime modules.

Acceptance:

- No vendor runtime was run.
- No dependency install was performed.
- No skills, plugins, browsers, sidecars, shells, desktop tools, channels, OAuth flows, or accounts were executed.
- No vendor code was integrated into Sentinel.
- G9 produces comparison and rewrite knowledge only.
- G10 remains design/spec work unless separately approved.

## Sprint G10 - Sentinel Super Agent Architecture Specs

Status: completed architecture/specification sprint.

Output:

- `audits/final/g10_sentinel_architecture.md`
- `audits/SENTINEL_SUPER_AGENT_BLUEPRINT.md`
- `audits/SENTINEL_AGENT_LOOP_SPEC.md`
- `audits/SENTINEL_MEMORY_SPEC.md`
- `audits/SENTINEL_SKILL_SPEC.md`
- `audits/SENTINEL_COST_ROUTER_SPEC.md`
- `audits/SENTINEL_SIDECAR_SPEC.md`
- `audits/SENTINEL_BROWSER_SPEC.md`
- `audits/SENTINEL_CHANNEL_SPEC.md`
- `audits/SENTINEL_EVAL_ROADMAP.md`
- `audits/SENTINEL_RUNTIME_CAPABILITY_ROADMAP.md`

Completed:

- converted G9 cross-agent synthesis into a Sentinel architecture constitution;
- defined the two product faces: Sentinel GTM Operator and Sentinel Control;
- specified the core loop: see, verify, research, debate, decide, plan, simulate, approve, execute_safe, trace, learn;
- defined module contracts for Perception Gateway, Evidence Ledger, Research Enrichment, Debate Engine, Action Kernel, Firewall, Safe Executors, Learning Layer, Memory, Skill Scanner, CostRouter, Browser, Channels, Sidecar, and Eval Roadmap;
- defined core data contracts for EvidenceItem, DecisionPlan, AgentAction, DryRun, TraceRecord, Memory, Skill Manifest, Cost Route, Sidecar Manifest, Browser Extraction, and Channel Draft;
- locked runtime capability order: product core first, control core second, AgentOps moat third, runtime power later;
- kept future browser, channel, workflow, sidecar, and desktop capabilities disabled until fake benchmarks and policy gates exist;
- documented eval gates for evidence quality, GTM readiness, firewall blocking, memory poisoning, skill scanning, budget control, trace completeness, fake browser, fake channel, fake workflow, and fake sidecar behavior.

Acceptance:

- G10 produced specs only.
- No Sentinel runtime module was implemented.
- No vendor bridge was created.
- No vendor code was copied into Sentinel.
- No dependency install was performed.
- No skills, plugins, browsers, sidecars, shells, desktop tools, channels, OAuth flows, or accounts were executed.
- Shell, browser submit, real channel send, sidecar runtime, desktop automation, runtime install, and production self-mutation remain blocked.

## Sprint G11 - Aggressive Control Doctrine And Power Mode Spec

Status: completed debate/specification correction.

Output:

- `audits/final/g11_debate_verdict_aggressive_control.md`
- `audits/SENTINEL_POWER_MODE_SPEC.md`

Completed:

- analyzed `debat.md` as a product-strategy debate source;
- accepted the correction that Sentinel must be aggressive in safe, reversible, local, and draft-only zones;
- rejected a global Full Access button as too broad and weakly auditable;
- defined Power Mode as future scoped authority through explicit authority envelopes;
- reframed the Firewall as a tempo router: green executes, amber previews, red requires approval or scoped authority, black remains unavailable until capability-specific evals pass;
- preserved the G10 boundary that no shell, browser submit, real channel send, sidecar runtime, desktop automation, runtime install, production self-mutation, or vendor bridge is enabled now;
- set the next implementation direction as Core Kernel with green-zone auto-execution rather than fear-based blocking.

Acceptance:

- Power Mode exists as a future architecture spec only.
- No risky runtime power is enabled.
- Safe local generation should feel fast and powerful.
- High-impact capabilities are blocked by default and unlockable later only through scoped Power Mode after fake benchmarks, policy gates, trace requirements, and evals.

## Sprint G12 - Mission Authority Kernel Doctrine

Status: completed deep-research synthesis/specification correction.

Output:

- `audits/final/g12_mission_authority_kernel_verdict.md`
- `audits/SENTINEL_MISSION_AUTHORITY_SPEC.md`
- `audits/SENTINEL_AUTONOMY_ENGINE_SPEC.md`
- `audits/SENTINEL_MISSION_UI_FLOW.md`

Completed:

- reviewed the three local deep research reports:
  - `deep-research-report (1).md`;
  - `deep-research-report (1)cc.md`;
  - `Designing Autonomous Agent Mission Authority.md`;
- accepted the research conclusion that Sentinel should not be permission-per-action by default;
- promoted `MissionAuthorityEnvelope` above Power Mode as the primary agentic primitive;
- defined the core doctrine: permission once for the mission, autonomy inside the mission, escalation only at the boundary;
- preserved G10/G11 boundaries: no shell, real browser submit, real email/channel send, desktop control, sidecar runtime, payment, dependency install, credential access, production mutation, or vendor runtime integration;
- specified MissionAuthorityEnvelope, MissionState, MissionAction, EscalationRequest, MissionTraceEvent, AutonomyEngine v0, deterministic classifiers, MissionBudgetController, MissionKillSwitch, MissionTraceTimeline, and SafeMissionExecutors;
- updated Power Mode, runtime roadmap, and super-agent blueprint language so Power Mode is one authority level inside mission-scoped execution, not a global Full Access toggle.

Acceptance:

- Mission Authority is now the center of the G12 plan.
- Safe local GTM missions should execute end-to-end without micro-approval.
- Risky real-world powers remain disabled.
- Escalation happens at mission boundaries, not every action.
- Power Mode remains future and scoped.

## Sprint G12A - Pre-Implementation Architecture Lock

Status: completed architecture/roadmap lock before coding.

Output:

- `../sentinel-control/docs/architecture/SENTINEL_AGENT_MASTER_ARCHITECTURE.md`
- `../sentinel-control/docs/architecture/SENTINEL_AGENT_IMPLEMENTATION_ROADMAP.md`

Completed:

- converted G12 Mission Authority doctrine into a concrete implementation architecture for `sentinel-control`;
- mapped the existing code baseline: shared models/enums, CueIdea bridge, research enrichment, debate, GTM pack, firewall, action runner, file executor, email draft executor, and trace ledger;
- defined the new `sentinel/mission/` package and every module to build before agent implementation;
- specified mission data contracts, mission enums, autonomy routing, deterministic classifiers, budget controller, kill switch, escalation gateway, safe mission executors, trace timeline, memory protocol, skill protocol, security protocol, evidence protocol, GTM mission protocol, UI surfaces, API routes, storage model, tests, and build order;
- locked the immediate implementation sequence as G12B Mission Authority Kernel v0.

Acceptance:

- no runtime power is enabled;
- no new agent code is implemented in this sprint;
- the next coding sprint has a precise module, file, test, and acceptance map;
- Mission Authority remains the center of the architecture.
