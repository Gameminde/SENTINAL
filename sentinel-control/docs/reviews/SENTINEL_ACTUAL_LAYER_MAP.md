# Sentinel Actual Layer Map

Date: 2026-05-18
Mode: docs-only audit map.

## Layer Map

| Layer | Purpose | Status | Score | Proof files/tests | Limits |
| --- | --- | --- | ---: | --- | --- |
| Repo compass and roadmap | North star, phase sequence, promotion ladder | Locked but partially stale | 6 | `docs/architecture/SENTINEL_A_TO_Z_LOCK/*` | Needs reconciliation with latest model/runtime commits |
| Product shell | Product identity, Mission OS framing, README state | Partial/stale | 4 | `README.md`, `docs/product/*`, `docs/mission-os/*` | README current state is stale |
| Evidence and CueIdea bridge | Source evidence for GTM and research workflows | Implemented legacy + bridge docs | 5 | `RedditPulse/`, `sentinel/cueidea_bridge/*`, mission-os evidence docs | Not audited deeply in this pass |
| Mission authority | Source of allowed systems/actions/tools/paths/budgets | Implemented and central | 8 | `mission/models.py`, scope/risk/budget tests | Token budgets still open for action/mission LLM spend |
| Mission runtime | Controlled plan execution, revocation, trace, artifacts | Implemented | 7 | `mission/runner.py`, `test_mission_*`, kill-switch tests | Mostly local/artifact oriented |
| AgentRuntime | Canonical cognitive loop and terminal result | Implemented | 8 | `agent/runtime.py`, `test_agent_runtime.py`, runtime model tests | Large file, many responsibilities |
| Context economy | Cache keys, compression, context budgets | Locked/implemented | 8 | perf cache tests, context closure docs | Action/mission token budget deferrals remain |
| Brain L4 internal cognition | Entropy, agent count, society, workspace, belief, debate, resourcefulness, procedures, BrainBench | Locked as internal cognitive stack | 7 | `docs/brain/P5*_LOCK_VERDICT.md`, brain tests | Not full external multi-agent execution |
| Decision frame/prompt/model plan | Build structured LLM frame and plan model call | Implemented | 7 | `decision_frame.py`, `ModelCallOptimizer`, `test_llm_backed_decision_cycle.py` | Still mostly one-pass |
| Real model execution | Execute selected model through coordinator/provider | Implemented and tested | 7 | `model_execution/*`, `test_runtime_model_execution_wiring.py` | Lock docs stale; provider set limited |
| Provider catalog | Secret-free provider metadata and constraints | Implemented | 7 | `catalog.py`, `provider_profiles.py`, `test_model_provider_catalog.py` | Recommendations cannot execute; no router |
| Generic OpenAI-compatible base | Shared safe adapter behavior | Implemented/hardened | 7 | `openai_compatible.py`, `test_openai_compatible_provider_base.py` | Native providers not implemented |
| Provider adapters | Groq/OpenRouter/NVIDIA adapters | Partial | 6 | `groq.py`, `openrouter.py`, `nvidia.py`, provider tests | Groq validated; OpenRouter/NVIDIA diagnostic |
| Provider credentials | Secret-free handles and env resolver | Implemented | 7 | `credentials.py`, credential tests | No vault UI; env-based first |
| Receipts and redaction | Prove request/result without raw secrets | Implemented | 8 | `receipts.py`, `redaction.py`, receipt tests | Must keep raw reasoning out as providers expand |
| FinalGate | Terminal safety certification | Strongly implemented | 9 | `final_gate.py`, `final_gate_registry.py`, final gate tests | Model-execution-specific gate semantics still basic |
| Trace/replay/event bus | Runtime proof and replay | Implemented | 8 | `event_bus.py`, `replay.py`, trace tests | Event taxonomy large |
| Capabilities registry | Declare and select eligible tools | Implemented | 7 | `capabilities/*`, `tool_selector.py`, registry tests | Product surfaces not all executable |
| Browser organ | Browser perception, V3 authority, navigation, evidence, interaction | Substantial, staged | 6 | `organs/browser/*`, browser docs/tests | Production browser mutation still gated |
| Desktop organ | Workspace/sidecar control model | Staged | 5 | `organs/desktop/*`, P6S docs/tests | Real desktop sidecar not broadly active |
| External API organ | API dry run/request planning | Partial | 4 | `organs/external_api/*`, P6D docs/tests | P6U API auth read not started here |
| Channel organ | Draft/send compliance model | Partial | 4 | `organs/channels/*`, P6E docs/tests | Live send gated |
| Credential organ | Scoped refs, vault policy, redaction | Partial | 5 | `organs/credentials/*`, P6F docs/tests | No broad secret-management product |
| Spend/capital/trading organs | High-risk special authority models | Partial/sandbox | 4 | `organs/spend/*`, `organs/trading/*`, P6G/P6I docs/tests | Not production execution powers |
| Firewall/execution package | Approval/dry-run/risk and local executors | Implemented foundation | 6 | `firewall/*`, `execution/*` | Narrow product workflows |
| Performance runtime | Bench harness, caches, hot/cold, scheduler | Locked | 7 | perf docs/tests, Phase F | Backlog remains |
| AgentLab | Research and vendor pattern mine | Docs/audit asset | 6 | `agent-lab/audits/*`, integration notes | Vendor code not runtime source |
| UI/frontend | Mission OS product UI direction | Early/docs | 3 | product docs | Not current runtime power |

## Actual Control Flow

The live core flow is:

```text
MissionAuthorityEnvelope
-> AgentRuntime.run
-> AgentContext / compressed context
-> CognitiveCycle and deterministic selectors
-> LLMDecisionFrame and PromptRender if model contract exists
-> ModelCallPlan
-> optional ModelExecutionCoordinator
-> validated LLMDecisionResult and receipt
-> PlannerBridge / WorkerCoordinator / MissionRunner when execution path opens
-> trace, replay, certification
-> CoreFinalGate
-> AgentRunResult
```

The live mission execution flow is:

```text
MissionAuthorityEnvelope
-> MissionRegistry definition
-> planner creates MissionPlan
-> AutonomyEngine chooses route
-> SafeMissionExecutors or browser operator route
-> MissionBudgetController
-> MissionTraceTimeline
-> MissionRunResult
```

The intended future Mission OS flow is much larger:

```text
Brain roles
-> model-backed planner/critic/verifier loops
-> authority-gated organ proposals
-> user approval / special authority
-> controlled browser/desktop/API/channel/spend/trading execution
-> replay/receipts/FinalGate
```

## Locked Layers

| Lock family | Current audit status |
| --- | --- |
| Architecture A-to-Z | Locked compass, but older than model execution packs |
| Brain P5A-P5L | Internally locked as cognition/control, no external execution |
| Performance Phase F | Locked benchmark regression gates |
| Context cache runtime closure | Locked for cache key and default-off injection, with remaining token budget deferrals |
| LLM decision-cycle seam | Locked and now implemented in runtime |
| Real provider adapter layer | Locked in docs, but state lock predates Wave 9 and later catalog/base hardening |
| P6 organs through P6T-B | Many staged locks documented; not freshly re-run here |

## Actual Open Gates

- `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`
- `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`
- Broad `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` needs split handling:
  provider adapter success and runtime wiring are now proven, but lock docs are
  stale.
- Production retry/rate-limit/fallback policy.
- Streaming response policy.
- Native provider adapters.
- Full Brain live model-role loops.
- P6U API authenticated read.
- Mission OS UI/product workflow integration.

## Code-Level Layer Expansion

The map below is the practical execution map discovered from source, not just
architecture vocabulary.

| Executable layer | Primary code area | Can it act today? | Authority source | Proof/limit |
| --- | --- | --- | --- | --- |
| Runtime orchestrator | `sentinel/agent/runtime.py` | Yes, orchestrates context, LLM frame, optional model execution, result certification | `MissionAuthorityEnvelope` plus runtime invariants | Provider-agnostic; no provider-specific branch should appear here. |
| Final certification | `sentinel/agent/final_gate.py`, registry | Yes, certifies final `AgentRunResult` | FinalGate checks and receipts | Certifies metadata and blocks/downgrades rejected outcomes; not an executor. |
| Model execution coordinator | `sentinel/agent/model_execution/coordinator.py` | Yes, if injected and credential/provider exist | `UserModelContract` and `ModelCallPlan` | Converts provider response into validated result and receipt; no fallback routing. |
| Provider adapters | `sentinel/agent/model_execution/*` | Yes for implemented adapters under tests | Env credential at execution time | Groq has validated success; OpenRouter/NVIDIA are diagnostic-only evidence. |
| Provider catalog | `catalog.py`, `provider_profiles.py` | No execution | Metadata only | Describes providers and recommendations; recommendations cannot execute. |
| Model optimizer | `model_optimizer.py` | Advisory planning | User-selected model contract | Recommendation cannot override selected model in runtime. |
| Context economy | `context_builder.py`, `context_compressor.py`, cache key files | Yes, builds and compresses runtime context | Cache key and envelope-derived hashes | Context cannot expand authority. |
| Mission runner | `sentinel/mission/runner.py` | Yes, mission loop and lifecycle | Mission authority and cancellation | Stronger for local/generated artifact flows than broad external action. |
| Scope/risk checker | `scope_checker.py`, `risk_router.py` | Yes, blocks or routes decisions | Mission envelope and policy | Black-zone actions and path containment are explicit. |
| Local safe executors | `safe_executors.py` | Yes, narrow local file/artifact actions | Generated project root and allowed actions | Drafts only; no send, spend, trading, production mutation. |
| Organ authority | `sentinel/organs/authority.py` | Yes, evaluates organ authority | Root authority subset | Memory/context/profit cannot expand authority. |
| Browser organ | `sentinel/organs/browser/*` | Partial | Browser authority and route safety | Navigation/read planning strong; mutation/login/payment/send blocked or proposal-only. |
| Desktop organ | `sentinel/organs/desktop/*` | Partial L6 workspace | Workspace authority | Workspace file ops only; host control blocked. |
| Channel/API/spend/trading | `sentinel/organs/*`, docs | Mostly planned/dry-run/gated | Future explicit authority | Not broad live power in current audit. |
| Event ledger | `sentinel/shared/events.py` | Yes, records events | Hash chain, event schemas | Proves order/integrity; does not grant authority. |
| Brain layer | docs plus agent modules | Partial | Mission authority, not Brain itself | Strong doctrine; live multi-role Brain not fully built. |
| AgentLab corpus | `agent-lab/*` | No Sentinel runtime action | None | Pattern mine and failure index only; no vendor runtime bridge. |

## Runtime Authority Graph

```text
User mission request
-> MissionAuthorityEnvelope
-> AgentRuntime context and decision frame
-> selected model contract
-> optional model execution coordinator
-> LLMDecisionResult as evidence/decision metadata
-> scope/risk/organ gates for any future action
-> FinalGate-certified AgentRunResult
```

Two things are intentionally absent from this graph:

- model output as an authority source;
- provider catalog recommendation as an execution path.

## Where The System Is Deeper Than It Looks

- The organ tree is large enough to make Sentinel feel close to a broad-world
  agent, but much of it is deliberately gated by promotion levels, receipts,
  and no-live-execution defaults.
- The model execution layer is real enough to prove a provider-backed runtime
  path, but not yet deep enough to act as a full Brain.
- The Brain docs are conceptually mature, but the current executable Brain is
  still mostly a controlled runtime-plus-model-decision seam, not an autonomous
  society of model roles.
