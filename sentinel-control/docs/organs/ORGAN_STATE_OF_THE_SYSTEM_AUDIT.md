# Organ State Of The System Audit

Status: audit lock

Date: 2026-05-19

Pack: `ORGAN_STATE_OF_THE_SYSTEM_AUDIT`

## Purpose

This report records the current Sentinel organ system before any further
execution expansion.

Sentinel's organ doctrine remains:

```text
Maximum power.
Maximum controllability.
Power is allowed.
Unsafe authority is not allowed.
```

This document is evidence and architecture only. It does not implement runtime
wiring, activate organs, modify `AgentRuntime`, import vendor runtimes, add
provider fallback, add AUTO routing, or weaken any safety contract.

## Evidence Base

Repository evidence inspected:

- `sentinel-control/services/sentinel-core/sentinel/agent/organs/*`
- `sentinel-control/services/sentinel-core/sentinel/organs/*`
- `sentinel-control/services/sentinel-core/sentinel/agent/browser/*`
- `sentinel-control/services/sentinel-core/sentinel/organs/browser/*`
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/controlled_capability.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/artifact_capture.py`
- `sentinel-control/services/sentinel-core/sentinel/mission/safe_executors.py`
- `sentinel-control/services/sentinel-core/sentinel/organs/reality_activation.py`
- `sentinel-control/services/sentinel-core/sentinel/capabilities/fixtures/static_catalog.py`
- `sentinel-control/docs/organs/*.md`
- `sentinel-control/docs/browser/*.md`
- `agent-lab/audits/*.md`
- `agent-lab/sentinel_integration_notes/*.md`
- `agent-lab/module-harvest/browser/openclaw/*.md`
- wider repository process/network surfaces under `RedditPulse/*`
- Sentinel web routes under `sentinel-control/apps/web/*`

## Current Top-Level State

Sentinel has three organ layers now:

1. `sentinel.agent.organs.*`: the new Brain-to-organ delegated execution chain.
2. `sentinel.organs.*`: earlier high-power organ families and L6 promotion work.
3. `sentinel.agent.browser.*` and `sentinel.organs.browser.*`: browser capability and browser V3 authority work.

The newest low-risk execution line is:

```text
BrainCognitionLoop
-> ProposalArtifact
-> OrganProposalBridge
-> DelegatedActionGate
-> DelegatedActionLane metadata
-> explicit L2/L3 executor contract
-> L2 or L3 executor
-> execution receipt
-> LowRiskFinalGate certificate
-> AgentRuntime.execute_organ_runtime_request() only when explicitly opted in
```

Default `AgentRuntime.run()` still remains separate from the new explicit
L2/L3 organ-runtime request method. That split is an important control
boundary.

## Current Organ Inventory

| Organ/system | Main paths | Category | Current status | Maturity | Active or dormant |
| --- | --- | --- | --- | --- | --- |
| Brain cognition loop | `sentinel/agent/brain/cognition_loop.py` | cognition orchestrator | implemented, non-executing | v0 safe cognition | active as explicit module |
| Role loop | `sentinel/agent/llm/role_loop.py` | LLM cognition | implemented strict single-model role loop | mature v0 | active when invoked |
| Proposal artifacts | `sentinel/agent/llm/proposals.py` | proposal schema | implemented non-executing proposal packets | mature v0 | active when invoked |
| Evidence verifier | `sentinel/agent/llm/evidence_verifier.py` | evidence binding | implemented evidence-bound verification | mature v0 | active when invoked |
| Memory bridge | `sentinel/agent/llm/memory_bridge.py` | memory | implemented no-authority witness memory | mature v0 | active when explicitly invoked |
| Hot context slots | `sentinel/agent/llm/memory_slots.py` | attention | implemented data-not-instruction slots | mature v0 | active when explicitly invoked |
| Safe memory retrieval | `sentinel/agent/llm/memory_retrieval.py` | retrieval | deterministic lexical plus metadata retrieval | mature v0 | active when explicitly invoked |
| Memory replay/checkpoints | `sentinel/agent/llm/memory_replay.py` | replay | implemented historical timeline/checkpoints | mature v0 | active when explicitly invoked |
| Organ proposal bridge | `sentinel/agent/organs/proposal_bridge.py` | organ candidates | maps safe proposals to organ candidates | mature v0 | active when invoked |
| Delegated action gate | `sentinel/agent/organs/delegated_action_gate.py` | gate | evaluates candidates and creates metadata-only lanes | mature v0 | active when invoked |
| L2 local artifact executor | `sentinel/agent/organs/local_artifact_executor.py` | local artifact | creates local draft/artifact under contract | implemented | active only through direct invocation or runtime opt-in |
| L3 reversible workspace executor | `sentinel/agent/organs/reversible_workspace_executor.py` | local reversible mutation | bounded text/json workspace mutation with before/after hash and rollback | implemented | active only through direct invocation or runtime opt-in |
| Low-risk FinalGate | `sentinel/agent/organs/low_risk_finalgate.py` | certification | certifies L2/L3 receipts, including blocked and rollback receipts | implemented | active when invoked |
| Organ runtime opt-in | `sentinel/agent/organs/runtime_execution.py`; `sentinel/agent/runtime.py` | runtime bridge | explicit L2/L3 local-only runtime request path | implemented | default disabled |
| Local controlled capability runner | `sentinel/agent/controlled_capability.py` | local artifact/tool runner | creates markdown/json artifacts through capability registry and artifact sandbox | implemented older path | active inside `AgentRuntime.run()` when direct tool calls are supplied |
| Artifact capture sandbox | `sentinel/agent/artifact_capture.py` | file capture | writes text/json/binary artifacts inside capture root with path containment | implemented | active in browser/local capability paths |
| Safe mission executors | `sentinel/mission/safe_executors.py` | local mission artifacts | writes generated GTM/research artifacts under `data/generated_projects` | implemented older path | active through `MissionRunner` |
| Browser controlled capability runner | `sentinel/organs/browser/controlled_runner.py`; re-exported through `sentinel/agent/browser` | browser | public read, render, limited interaction, V3 authorities | implemented older browser organ line | active inside `AgentRuntime.run()` when browser tool calls are allowed |
| Browser read/render/extract stack | `sentinel/organs/browser/live_fetch.py`, `rendered_snapshot.py`, `extraction.py`, `dom_snapshot.py`, `accessibility_snapshot.py`, `screenshot.py`, `pdf.py` | browser/perception | read-only and artifact-producing perception | implemented | active through browser runner |
| Browser limited interaction | `sentinel/organs/browser/interaction_dry_run.py`, `interaction_execution.py` | browser action | certified bounded click/type/fill/select/hover/wait plan execution | implemented | active when tool policy and backend allow |
| Browser V3 advanced authorities | `sentinel/organs/browser/form_submit.py`, `download_quarantine.py`, `upload_authorized.py`, `v3_advanced_authorities.py`, `v3_authority.py` | browser high power | governed submit/download/upload/private session/login/cookie/js/HAR authority surfaces | implemented as older high-power path | active only if corresponding backend and authority are supplied |
| Browser operator route | `sentinel/agent/browser/operator_runtime.py`, `sentinel/mission/runner.py` protocol | browser routing | optional route injected into runtime | implemented | dormant unless injected |
| Desktop workspace L6 | `sentinel/organs/desktop/workspace_l6.py` | desktop/workspace | L6 workspace list/read/write/create with authority, rollback refs, path containment, no host control | implemented | active by direct module use/tests |
| Desktop sidecar contract pieces | `sentinel/organs/desktop/*` | desktop | manifest, enrollment, sanitizer, fake sidecar, action preview/lifecycle, kill switch | partial/contracts/fake | mostly dormant |
| External API organ | `sentinel/organs/external_api/*` | API | request plan, allowlist, dry-run receipt, cost/privacy risk; dry-run `execute()` rejects | partial read-only/dry-run | active by direct module use/tests |
| Channel organ | `sentinel/organs/channels/*` | channel/email-like | draft, inbound/outbound metadata, compliance, rate limit, send gate, receipts; send gate always dry-run/not promoted | partial draft/gate | active by direct module use/tests |
| Credential organ | `sentinel/organs/credentials/*` | credentials | credential refs, scoped grants, vault policy, redaction, receipts, revocation | partial policy/ref only | active by direct module use/tests |
| Capital organ | `sentinel/organs/capital/sandbox.py` | capital reasoning | capital signal ledger and spend decision reasoning | partial sandbox | active by direct module use/tests |
| Spend organ | `sentinel/organs/spend/runtime.py` | spend/payment | fake provider, authority envelope, subscription guard, kill switch; real provider disabled | partial/test-mode only | active by direct module use/tests |
| Trading organ | `sentinel/organs/trading/*` | trading | special authority, paper trade provider, TradingAgents harvest roles | partial/paper only | active by direct module use/tests |
| Reality activation organ set | `sentinel/organs/reality_activation.py` | cross-organ reality | read-only browser/API, local drafts, env ref resolving, desktop workspace writes, market data, paper trade, test spend | high-power lab bridge | active by direct module use/tests, not default runtime |
| External organ contracts/registry | `sentinel/organs/contracts.py`, `registry.py`, `authority.py`, `dry_run.py`, `receipts.py`, `kill_switch.py`, `promotion_gate.py`, `lanes.py`, `risk.py`, `replay.py` | control plane | generic organ authority, dry-run, receipts, promotion, replay and risk model | implemented older control plane | active by direct module use/tests |
| Async organ scheduler | `sentinel/perf/sched/async_organ_scheduler.py`, `tool_call_queue.py` | scheduling/performance | schedules organ-shaped local tool calls if injected | implemented default-off | dormant unless injected |
| Tool/capability registry | `sentinel/capabilities/*`, `sentinel/agent/tool_call_protocol.py`, `tool_selector.py`, `capability_selector.py` | tool ecosystem | manifest policy, canonical tool-call parsing, approved/candidate/blocked fixtures | implemented | active in `AgentRuntime.run()` |
| Vendor harvest classifiers | `sentinel/organs/vendor_harvest.py`, `implementation_alignment.py`, `desktop/harvest.py`, `trading/tradingagents_harvest.py` | vendor lab | source-only harvest models | implemented as analysis code | active by direct module use/tests |
| Agent Lab scanners/benchmarks | `agent-lab/tools/openclaw_static_scanner`, `agent-lab/benchmarks/*` | lab tooling | scanner and fake benchmarks | lab-only | dormant unless run manually |

## Wider Repository Execution Surfaces

The full repository contains adjacent application code that is not approved as
Sentinel organ runtime but must be accounted for in a complete organ/power
audit.

| Surface | Paths | Category | Status | Risk |
| --- | --- | --- | --- | --- |
| RedditPulse report worker shell | `RedditPulse/app/src/app/api/scan/[id]/report/route.ts` | web-triggered process execution | route uses Node `exec(...)` around a generated Python report command | shell execution with provider/service env in child process |
| RedditPulse scan/enrich/discover workers | `RedditPulse/app/src/app/api/scan/route.ts`, `api/enrich/route.ts`, `api/discover/route.ts`, `app/src/lib/queue.ts` | web-triggered Python workers | use `spawn("python", [...])`, generally safer than shell interpolation | privileged env propagation, worker stdout/stderr leakage risk |
| RedditPulse admin scraper | `RedditPulse/app/src/lib/admin-data.ts`, `api/admin/jobs/run-scraper/route.ts` | admin command execution | reads `ADMIN_SCRAPER_COMMAND` and executes it after admin route gating | arbitrary configured command if admin/env boundary is compromised |
| RedditPulse validation/AI providers | `RedditPulse/validate_idea.py`, `run_scan.py`, `engine/*` | provider/API use | reads Gemini/Groq/OpenAI/Supabase/env keys when configured | provider calls and secret handling outside Sentinel organ law |
| Sentinel web mission status route | `sentinel-control/apps/web/app/api/missions/[missionId]/status/route.ts` | web state mutation | mutates status to paused/stopped/revoked without `getRequestUser` in the inspected route | authority/availability mutation if web app is exposed beyond trusted local mode |
| Sentinel web local/header auth mode | `sentinel-control/apps/web/lib/auth.ts` | web auth boundary | `SENTINEL_REQUIRE_AUTH=true` controls strict auth; local/header mode otherwise | deployment config can weaken route authority assumptions |

These surfaces are not Sentinel organ approvals. They are risk-bearing runtime
surfaces in the same repository and should either remain outside Sentinel's
organ body or be wrapped by Sentinel organ contracts before reuse.

## Active Runtime Entry Points

Current runtime entry points with side-effect relevance:

- `AgentRuntime.run(...)`: core mission runtime. It can build context, execute
  safe mission actions, execute controlled capability tool calls, and route
  browser tool calls through the older browser controlled runner when policy,
  manifest, budget, and optional backends allow.
- `AgentRuntime.execute_organ_runtime_request(...)`: explicit low-risk L2/L3
  local-only organ request path. Default config is disabled.
- `MissionRunner`: can run mission plans using `SafeMissionExecutors` under
  generated project roots.
- `BrowserControlledCapabilityRunner.run(...)`: can run browser read/render,
  limited interaction, and V3 authority classes when tool policy and backends
  are present.
- Direct module use in tests/lab: `DesktopWorkspaceOperator`,
  `RealityBrowserReader`, `ExternalAPIRealityClient`, `PaperTradeProvider`,
  `FakeSpendProvider`, `DesktopWorkspaceL6` adapters.

## Dormant Or Explicit-Only Surfaces

These are not default broad autonomous execution, but they exist as code or
contracts:

- browser form submit, upload, download, private session, login, cookie/storage,
  sandboxed JS, HAR capture;
- desktop sidecar observe/action model pieces;
- external API live-read planning and allowlist;
- channel provider draft/send gate model;
- credential vault policy and env-ref resolver;
- spend test-mode provider;
- paper trading provider;
- async organ scheduler;
- Agent Lab vendor scanners and fake benchmarks.

## Unsafe Direct Execution Surfaces

The repository already contains several powerful surfaces. They are not all
unsafe in implementation, but they are unsafe if promoted without the new
organ law:

- `BrowserFormSubmitExecutor` can submit public forms through a backend when
  authority exists.
- `BrowserUploadAuthorizedExecutor` can upload certified artifacts through a
  backend when authority exists.
- `BrowserLoginAuthorityExecutor` can perform vault-indirected login through a
  backend when authority exists.
- `BrowserJsEvaluateSandboxedExecutor` can run allowlisted browser script.
- `DesktopWorkspaceOperator.write_file()` in `reality_activation.py` writes
  under its root but is older than the new L3 FinalGate chain.
- `LocalChannelDraftStore.store()` writes local channel draft JSON.
- `EnvCredentialRefResolver.resolve()` can read allowlisted environment
  variables and returns a `ResolvedCredential` object with a secret value in
  memory, although receipts redact it.
- `RealityBrowserReader` and `ExternalAPIRealityClient` perform real network
  reads using `urlopen` when no fake transport/fetcher is supplied.
- `FakeSpendProvider` and `PaperTradeProvider` execute fake/test-mode capital
  actions; live providers are disabled by validators.
- `OrganExecutionReceipt.started(...)` models started execution for promoted
  organs after authority and kill-switch checks.
- `ArtifactCaptureSandbox.capture_binary(...)` writes binary artifacts under a
  capture root.
- `AgentRuntime.run()` can execute controlled tool calls from `user_input` when
  allowed by mission authority and capability policy.
- `RedditPulse` routes can start Python workers and one report route uses a
  shell command through Node `exec(...)`; these are outside Sentinel organ law
  and should not be harvested as-is.
- `RedditPulse` worker processes can receive provider, Supabase service, and
  encryption-key environment variables.
- The Sentinel web mission-status route is a state mutation path that should be
  treated as a web authority surface if the app is exposed beyond trusted
  localhost.

## Hidden Pathway Risks

These are the architecture seams that need continued hardening:

- Two organ control planes exist: newer `sentinel.agent.organs.*` and older
  `sentinel.organs.*`. Future packs must converge them or create adapters so
  capabilities do not bypass the newest gate/FinalGate/receipt model.
- Browser V3 power is mature but older than the low-risk L2/L3 gate chain.
  Browser promotion must bind it to the delegated-action gate and FinalGate
  contract, not only to capability registry policy.
- `AgentRuntime.run()` has direct controlled tool-call handling. It is gated,
  but future organ expansion must avoid adding powerful tool manifests that
  bypass organ candidate/gate/receipt contracts.
- Reality activation modules perform real read/write/test-mode actions through
  direct class calls. They should be treated as lab/prototype surfaces until
  wrapped by current organ interface standard.
- Vendor audit/benchmark folders contain intentionally dangerous fixture text
  and plugin/skill examples. They must remain lab data, not runtime input.
- Adjacent app code, especially `RedditPulse`, has process execution and
  provider-key propagation that do not follow Sentinel organ contracts. If any
  of that functionality becomes useful to Sentinel, it must be rewritten as
  sandboxed organ execution rather than imported.
- Sentinel web routes should be included in authority audits because web UI
  endpoints can pause, stop, revoke, approve, or trigger runtime work.

## Security Posture By Risk Vector

| Vector | Current posture | Residual risk |
| --- | --- | --- |
| Shell/process | Blocked in capability fixtures and low-risk executors; shell sandbox not implemented | Vendor fixtures and future test runner could reintroduce command execution |
| Browser injection | Browser docs and V3 gates exist; untrusted context posture exists | Browser output can still reach cognition if future prompt wiring treats it as instruction |
| Browser action | Strong browser code exists, including submit/upload/login authorities | Needs unified DelegatedActionGate and FinalGate binding before more runtime exposure |
| Credential exposure | Credential refs, redaction, policy, and secret-source blocks exist | Env resolver can hold secret in memory; future vault must avoid raw secret durability |
| Memory poisoning | Memory bridge/retrieval/replay are no-authority and data-not-instruction | Future Memory-to-prompt wiring is still the critical trap |
| Replay poisoning | Replay is historical data only | Future restore/rollback automation must not treat checkpoints as permission |
| Authority escalation | Many models validate `authority_expansion=false` | Parallel old and new control planes increase drift risk |
| Prompt injection | Scanners and data-not-instruction warnings exist | Browser/channel/skill/plugin ecosystems need uniform untrusted-context rendering |
| Plugin/skill supply chain | Agent Lab scanner exists; plugin runtime not integrated | Future plugin install/runtime is high critical and must be sandbox-first |
| Network/API | Browser/API read-only and V3 browser actions exist | API authenticated read and browser action need stricter per-organ contracts |
| Adjacent process execution | RedditPulse workers exist outside Sentinel organ law | Do not reuse without sandbox shell/test-runner contracts and env isolation |
| Web route authority | Sentinel web auth can be strict or local/header mode; one mission-status route mutates state without `getRequestUser` in inspected code | require route-level authority checks for any production-exposed control route |

## Implementation State Summary

Current Sentinel organ maturity is uneven but powerful:

- Low-risk local execution is the cleanest current chain: proposal, gate,
  explicit executor contract, receipt, rollback posture, FinalGate, runtime
  opt-in.
- Browser is the most capability-rich current organ family, with read, render,
  limited interaction, form submit, upload, download, private session, login,
  cookie/storage, sandboxed JS, and HAR capture models.
- Desktop, channel, API, credential, spend, and trading organs have strong
  control-plane pieces but are not yet unified under the newest L2/L3-style
  organ runtime chain.
- Vendor harvesting is mature as a lab discipline: OpenClaw, Hermes,
  OpenJarvis, JARVIS, AgentMemory, and TradingAgents are treated as capability
  mines, not runtime dependencies.
- The wider repo contains real process execution in adjacent app code. That
  power must be quarantined from Sentinel's organ body unless rewritten under
  Sentinel's executor, receipt, rollback, and FinalGate laws.

## Audit Conclusion

Sentinel already has a serious organ body. The main task is not inventing
organs from zero. The main task is unifying existing and latent organs under
one modern execution law:

```text
candidate -> gate -> lane metadata -> explicit executor contract -> receipt -> rollback/disable -> FinalGate -> replay
```

Anything outside that chain should be treated as prototype, lab-only,
proposal-only, or read-only until wrapped.
