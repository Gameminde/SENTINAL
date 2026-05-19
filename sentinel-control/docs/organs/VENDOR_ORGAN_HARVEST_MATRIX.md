# Vendor Organ Harvest Matrix

Status: docs/spec lock

Date: 2026-05-19

## Purpose

This matrix maps agent-lab specimens to Sentinel organs. Vendors are studied as
capability mines, not integrated as runtimes.

No vendor runtime is approved for Sentinel by this document. No dependency
install, server, browser, sidecar, shell, skill, plugin, credential, channel, or
provider bridge is authorized here.

## Harvest Rule

```text
TAKE mechanisms.
REWRITE Sentinel-native.
AVOID runtime bridges and hidden authority.
FAKE-EVAL before integration.
```

## Matrix

| Vendor/System | Powerful mechanisms found | Organ categories | TAKE | REWRITE | AVOID | Dangerous surfaces | Required Sentinel gates | Fake evals before implementation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenClaw | Gateway/control plane, plugin manifests, channels, browser/CDP, skills, scanner, approval UI, memory plugins | Browser, channels, skill/plugin, API, memory, shell | manifest vocabulary, gateway event shape, browser snapshot ideas, scanner report model | skill scanner, channel adapter manifest, browser sandbox, plugin risk classifier | runtime bridge, host install, unscanned marketplace, shell-as-tool, browser submit, outbound send | 83 scanner items; 52 blocked, 29 needs review; shell, network, secrets, channels, browser, background services | skill/plugin scan gate, browser sandbox gate, channel send gate, secret policy, no-runtime gate | malicious skill, plugin install, channel prompt injection, browser submit, filesystem traversal, memory override |
| JARVIS | Authority engine, approval lifecycle, audit trail, daemon/sidecar, desktop/browser awareness, screenshot/clipboard/terminal RPC | desktop sidecar, browser, shell, vision/OCR, authority | approval lifecycle, sidecar capability manifest, desktop awareness model | PermissionedSidecar, ScreenContextSanitizer, sidecar revocation, host action preview | daemon/sidecar runtime, raw terminal, click/type, clipboard write, executable web templates | host-level authority, screenshot secrets, desktop click, shell, token replay | sidecar enrollment gate, sanitizer gate, approval gate, kill switch, FinalGate | fake token replay, fake screenshot secret, fake destructive click, fake browser submit, capability mismatch |
| OpenJarvis | Hardware-aware routing, local/cloud model selection, cost/latency/energy metrics, skill import quarantine, learning config writes | model routing future, skill scanner, cost/budget, self-improvement | cost/risk/latency model vocabulary, skill quarantine idea, reward metrics | Sentinel CostRouter later, SkillImportScanner, ImprovementProposal only | runtime skill sync, auto-written configs, browser/channel extras, bridge execution | unscanned imports, learned config mutation, shell/code/browser optional extras | budget gate, skill import gate, no-auto-routing gate, self-improvement proposal gate | unscanned skill import blocked, learning proposal cannot apply, route budget cap, secret scan |
| Hermes Agent | Memory, skill index, prompt builder, tool hooks, delegation, context scanner, external memory providers | memory, skills, subagents, tool dispatch, scheduler | compact skill index, tool hook points, delegation trace, context scanning | SkillIndexCompiler, ContextTrustScanner, FirewallDispatchPipeline, SubagentPlan | Hermes runtime, skills, Google Workspace setup, memory provider plugins, tool dispatcher | memory-as-policy, OAuth scope expansion, skill scripts, fail-open hooks | memory no-authority gate, skill scanner, OAuth scope gate, subagent budget gate | prompt injection in context, skill script execution, memory policy attempt, subagent permission bypass |
| AgentMemory | typed memory strata, observe-first, deterministic compression, slots, retrieval, temporal graph, replay, checkpoints, lessons/routines | memory maintenance, hot slots, retrieval, replay, temporal graph | typed strata, TTL/supersession, replay/checkpoint, access/retention model | Sentinel epistemic memory, data-not-instruction retrieval, graph with provenance | AgentMemory server/runtime, MCP/API surface, raw prompt/tool persistence, default-open auth | memory-as-authority, raw leakage, direct prompt injection, destructive delete | memory authority firewall, raw leakage scanner, retrieval data-not-instruction gate | stale memory, contradiction survival, self-generated evidence laundering, duplicate-source suppression |
| TradingAgents | analyst role graph, bull/bear debate, risk debate, portfolio manager, checkpoint/reflection, signal parser | Brain roles, capital/trading, risk review, replay | adversarial debate pattern, risk role split, checkpoint/reflection | Sentinel risk reviewer, capital proposal packet, trading L7 special authority | live broker/API integration, investment advice posture, vendor fallback runtime | market data APIs, credentials, trading decision language, live order risk | trading special authority, max-loss budget, broker credential gate, FinalGate | paper-only trading debate, fake market data, risk contradiction, max-loss block |
| OpenClaw Browser Harvest | role snapshots, trace, screenshot, interaction dry-run, browser fake evals | browser read-only, browser preparation, browser action | snapshot/trace primitives and fake eval suite | Sentinel browser organ contracts and action ladder | direct CDP runtime bridge, real profile automation, submit/login | form submit, real profile, downloads/uploads, account mutation | browser sandbox, submit-disabled gate, domain gate | read-only page summary, submit blocked, real profile rejected, sandbox trace |
| Sentinel Agent Lab Benchmarks | sandbox workspace, fake contact/company, fake browser profile, malicious fixtures | all organ evals | fake-first benchmark discipline | OrganBench fixtures per organ | real accounts or real credentials in evals | accidental real network/accounts | fake-resource gate, fixture hash gate, no-runtime rule | sandbox file write, fake email draft, injection, malicious skill, trace completeness |

## Vendor Patterns To Harvest By Organ Family

Local/file organs:

- harvest Agent Lab sandbox file tasks and OpenClaw filesystem risk maps;
- rewrite with workspace root allowlists and before/after receipts.

Browser organs:

- harvest OpenClaw browser snapshot/trace work and JARVIS browser awareness;
- rewrite with sandbox profiles, domain gates, submit-disabled defaults.

Channel/email organs:

- harvest OpenClaw channel manifest patterns and Hermes Google Workspace risk
  analysis;
- rewrite as draft-first, send only after explicit approval and provenance.

Desktop/sidecar organs:

- harvest JARVIS sidecar enrollment and approval lifecycle;
- rewrite as signed, revocable, scoped, sanitized, and deny-by-default.

Skill/plugin organs:

- harvest OpenClaw scanner and OpenJarvis import quarantine;
- rewrite as static scanner, fake eval, sandbox-only runtime later.

Memory/replay organs:

- harvest AgentMemory strata, replay, and temporal graph;
- rewrite as scoped epistemic witness state with no-authority invariants.

Capital/trading organs:

- harvest TradingAgents role graph and risk debate;
- rewrite as proposal/paper-first and L7-only live authority later.

## Universal Avoid List

- default-open auth;
- vendor runtime import;
- host dependency install;
- unscanned skill/plugin activation;
- shell/process exposure by default;
- browser submit/login/upload/download before special authority;
- raw prompt/tool/provider response persistence;
- direct memory-as-prompt instruction injection;
- provider/model choices inferred from memory or vendor config;
- routines that execute directly.
