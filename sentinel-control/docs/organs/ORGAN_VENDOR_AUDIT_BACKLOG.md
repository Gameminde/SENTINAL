# Organ Vendor Audit Backlog

Status: docs/spec lock

Date: 2026-05-19

## Purpose

This backlog defines future vendor audits per organ family. All audits are
source-only or fake-eval-only unless a later explicit lab plan authorizes a
sandboxed runtime.

No backlog item authorizes vendor runtime import, dependency install, account
connection, credential use, provider call, browser launch, sidecar launch,
shell execution, or plugin execution.

## Backlog Table

| Backlog item | Source location | Audit method | No-runtime rule | Extraction target | Sentinel rewrite target | Fake benchmark required |
| --- | --- | --- | --- | --- | --- | --- |
| OpenClaw browser gateway deep dive | `agent-lab/module-harvest/browser/openclaw/` and `agent-lab/vendors/openclaw/source/src/browser` | static source map, power-file read, fake browser fixtures | no browser launch, no real profile, no CDP runtime | snapshot, trace, interaction dry-run, submit detection | Browser Read-Only, Browser Preparation, Browser Action contracts | read-only summary, submit blocked, real profile rejected |
| OpenClaw channels/email deep dive | `agent-lab/vendors/openclaw/source/extensions/*`, Gmail hooks, channel skills | manifest scan, channel send path map | no channel login, no OAuth, no send | channel manifest, outbound action schema, contact risk | Channel Draft, Channel Send, Email Draft, Email Send | fake inbound injection, fake send blocked, provenance missing |
| OpenClaw skill/plugin system deep dive | `agent-lab/vendors/openclaw/source/skills`, `src/plugins`, scanner outputs | static scanner expansion | no plugin install, no skill execution | manifest fields, scripts, routes, services, secrets, commands | Skill Scanner, Skill Sandbox, Plugin Runtime later | malicious skill/plugin blocked, report consistency |
| JARVIS desktop sidecar deep dive | `agent-lab/vendors/jarvis/source/src/sidecar`, `sidecar/`, `src/actions/tools/desktop.ts` | sidecar capability map and fake RPC fixtures | no daemon, no sidecar, no desktop control | enrollment, capability manifest, screenshot/click/type paths | Desktop Sidecar Observe, Desktop Sidecar Action | token replay, screenshot secret, destructive click |
| JARVIS browser/automation deep dive | JARVIS webapp templates and browser action files | static template/action audit | no browser or app automation | app template schema, submit/send risks | Browser Preparation, Browser Action | fake submit blocked, template not instruction |
| OpenJarvis routing/skill import deep dive | `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py`, `skills/importer.py`, `cli/skill_cmd.py` | static config/import scanner | no `uv sync`, no CLI, no skill sync | hardware routing metrics, quarantine pattern, learned config writes | CostRouter later, Skill Import Scanner, ImprovementProposal | unscanned import blocked, learned config cannot apply |
| Hermes scheduled automation/task memory deep dive | `agent-lab/vendors/hermes-agent/source/run_agent.py`, `tools`, `agent/prompt_builder.py`, skills | static loop and skill hook audit | no Hermes runtime, no skill setup, no OAuth | scheduling, delegation, memory, skill index, hook points | Scheduler/Automation, Skill Index, Subagent budget | prompt injection context, OAuth scope expansion, subagent bypass |
| AgentMemory advanced retrieval/temporal graph later | `agent-lab/vendors/agentmemory/source/src/functions/*graph*`, retrieval modules | source-only model audit | no server, no MCP, no API | temporal graph, hybrid retrieval, access tracking | Temporal Graph / Replay Organ | contradiction survival, stale memory, self-generated evidence quarantine |
| TradingAgents debate/risk/checkpoint patterns | `agent-lab/vendors/tradingagents/source/tradingagents` | source-only role graph audit | no market API, no broker, no provider call | bull/bear debate, risk debate, checkpoint/reflection | Trading L7 Special Authority, Brain risk roles | fake market data, max-loss block, portfolio decision not authority |
| Agent Lab benchmark expansion | `agent-lab/benchmarks/*` | fake eval design | sandbox resources only | OrganBench fixtures and report schema | All organ fake evals | per-organ blocked/allowed fixtures |
| Vision/OCR/PDF vendor scan | OpenClaw image/PDF skills, JARVIS screenshot, future specimens | static scanner plus DLP fixture review | no external APIs, no OCR runtime without later plan | extraction schema, redaction requirements | Vision/OCR/PDF Extraction organs | screenshot secret, PDF injection, raw extraction blocked |
| DevOps/Cloud specimen scan | future high-value agents only after selection | source-only and dependency audit | no cloud login, no API call, no deploy | infrastructure action schemas and rollback plans | DevOps/Cloud Organ | fake plan/apply separation, production mutation blocked |

## Audit Method Standard

Every vendor audit must produce:

- source location;
- source commit or snapshot id;
- files inspected;
- commands intentionally not run;
- powerful mechanisms found;
- dangerous surfaces;
- Sentinel `TAKE`, `REWRITE`, `AVOID`;
- required gates;
- fake evals;
- rollback/disable requirements;
- final promotion decision.

## No-Runtime Rule

The default lab rule remains:

- clone/read source only;
- no dependency install;
- no vendor runtime;
- no server/MCP/viewer;
- no browser launch;
- no sidecar launch;
- no shell execution;
- no channel login;
- no OAuth flow;
- no provider call;
- no credentials;
- no `.env` access.

## Promotion Rule

A vendor-harvested pattern can move toward Sentinel implementation only after:

1. source audit;
2. capability map;
3. failure mode entry;
4. Sentinel rewrite target;
5. fake eval dataset;
6. static scanner or policy checker where relevant;
7. authority gate design;
8. receipt contract;
9. rollback/disable plan;
10. FinalGate posture.

## Immediate Next Audit Use

The next implementation pack remains:

```text
LOW_RISK_LOCAL_ARTIFACT_EXECUTOR_L2
```

Vendor backlog items inform later waves. They must not delay L2 unless the
future executor attempts to import vendor runtime, expose broad filesystem
access, or skip receipt/rollback proof.
