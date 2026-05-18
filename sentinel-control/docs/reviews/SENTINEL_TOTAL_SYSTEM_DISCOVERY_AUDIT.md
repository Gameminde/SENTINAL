# Sentinel Total System Discovery Audit

Date: 2026-05-18
Mode: docs-only audit. No production source, tests, runtime wiring, provider
calls, API keys, `.env`, P6U, Brain/Science implementation, or provider packs
were touched by this review.

## Executive Answer

Sentinel today is a mission-governed agent runtime and Mission OS kernel. It is
not just GTM automation. The implemented center is:

```text
MissionAuthorityEnvelope
-> AgentRuntime cognitive pipeline
-> context/cache/model-decision seam
-> optional real model execution coordinator
-> controlled local mission execution
-> trace, receipts, replay, review, FinalGate certification
```

Sentinel's real power today is controlled local artifact generation, authority
bounded planning/execution, traceable mission runs, strong final certification,
context/cache discipline, and a proven real model execution path through the
runtime using Groq as evidence. Its intended power is much larger: controlled
browser, desktop, channel, external API, credential, spend/trading, long-horizon
mission, and Brain L4/Mission OS workflows. Many of those powers exist as
contracts, docs, tests, organ modules, and promotion gates, but not all are
integrated into a fully automatic end-to-end product system.

The most important audit finding is a state-doc drift:

```text
README.md and CURRENT_STATE_LOCK.md still say runtime model execution is NOT_WIRED.
Current code and later commits prove runtime model execution is wired and tested.
```

The actual latest code state includes:

- `76ad92e runtime: wire model execution coordinator into agent runtime`
- `9647993 test: validate real runtime model execution`
- `7f0ddcb runtime: add model provider catalog`
- `4052be9 runtime: harden openai-compatible provider base`

The lock docs need consolidation before the project starts another high-power
pack.

## Discovery Sources Audited

This audit inspected the repository map, architecture docs, lock docs, specs,
Brain docs, provider docs, runtime source, mission source, organ/browser source,
AgentLab audit material, and test topology. Key audited sources:

- `README.md`
- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `sentinel-control/docs/POST_CLEANUP_HANDOFF.md`
- `sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/*`
- `sentinel-control/docs/brain/*`
- `sentinel-control/docs/browser/*`
- `sentinel-control/docs/organs/*`
- `sentinel-control/docs/providers/*`
- `sentinel-control/docs/specs/sentinel-real-model-execution-backend/*`
- `.kiro/specs/*`
- `agent-lab/audits/*`
- `agent-lab/audits/final/*`
- `agent-lab/sentinel_integration_notes/*`
- `sentinel-control/services/sentinel-core/sentinel/agent/*`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/*`
- `sentinel-control/services/sentinel-core/sentinel/mission/*`
- `sentinel-control/services/sentinel-core/sentinel/organs/*`
- `sentinel-control/services/sentinel-core/sentinel/firewall/*`
- `sentinel-control/services/sentinel-core/sentinel/execution/*`
- `sentinel-control/services/sentinel-core/tests/*`

Repository scale seen during discovery:

```text
repo files discovered by rg --files: 1626
sentinel-core tests discovered: 166
major Kiro specs discovered: 5
```

## What Sentinel Is Today

Sentinel is currently a controlled agent substrate with these implemented
traits:

1. Mission authority is explicit.
   `MissionAuthorityEnvelope` carries user, objective, allowed systems, tools,
   actions, paths, domains, accounts, browser grants, costs, duration, max
   actions, revocation, and kill-switch posture.

2. Runtime cognition is deterministic and staged.
   `AgentRuntime.run` moves through context building, compression, orientation,
   method/capability/tool selection, hypothesis verification, action scoring,
   planning, review, execution, repair, success evaluation, learning proposal,
   and terminal certification.

3. Execution is bounded.
   `MissionRunner` runs planned mission steps through `SafeMissionExecutors`,
   budget checks, route decisions, revocation polling, browser route rejection,
   traces, and artifact receipts.

4. FinalGate is real and broad.
   `CoreFinalGate` certifies trace, replay, phase contract, tool policy,
   learning approval, mission trace integrity, mission result consistency,
   global action budget, artifact paths, risk route decisions, controlled
   capability receipts, LLM context pack contract, browser contracts, and
   optional project scope.

5. LLM path is no longer docs-only.
   `AgentRuntime.run` builds `LLMDecisionFrame`, renders prompt text, creates
   a `ModelCallPlan`, optionally calls `ModelExecutionCoordinator`, stores safe
   metadata, and still returns a FinalGate-certified `AgentRunResult`.

6. Model execution is provider-agnostic in runtime.
   Runtime knows the coordinator and request builder, not Groq/OpenRouter/NVIDIA
   branches. Tests assert no Groq string appears in `runtime.py`.

7. Provider layer is real but still young.
   Groq is proven as `SUCCESS_VALIDATED`; OpenRouter and NVIDIA are diagnostic;
   provider catalog and OpenAI-compatible base are implemented and tested.

8. Brain L4 is internally locked as a cognitive/control model.
   P5A-P5L docs and tests prove planning, entropy, agent count, society,
   workspace, belief, debate routing, epistemic action, resourcefulness,
   procedures, BrainBench, and integrated pre-mortem hardening. External
   execution by Brain remains intentionally not implemented.

9. Organs exist as gated power surfaces.
   Browser, desktop, channels, external API, credentials, spend, trading, and
   capital organ modules exist. Lock docs show staged promotion. The audit did
   not re-run every organ test, so these are recorded as documented and tested
   by their lock artifacts, not freshly re-certified here.

10. AgentLab is a research forge, not runtime dependency.
    OpenClaw, JARVIS, Hermes, OpenJarvis, TradingAgents and related audits feed
    design patterns. Sentinel doctrine rejects vendor runtime bridging, silent
    fallback, dynamic provider plugins, and direct model-to-action execution.

## What Sentinel Is Not Yet

Sentinel is not yet the final fully autonomous Mission OS. Current gaps:

- No fully updated state lock for Wave 9/provider catalog/base hardening.
- Action token budget and mission token budget deferrals remain open.
- Brain L4 modules are mostly internal/proposal/certification layers, not a
  full multi-agent runtime with real model roles.
- Runtime model execution is proven, but not yet a deep iterative
  planner/critic/verifier loop.
- Provider catalog is metadata and policy, not a model router.
- No silent fallback, AUTO model selection, or production multi-provider retry
  policy is approved.
- Browser/desktop/channel/API/spend/trading powers remain gated by organ
  authority, tests, and lock docs. They should not be treated as globally
  available runtime powers.
- Real provider tests are skip-safe and key-dependent; full CI can pass without
  exercising every hosted provider.
- Product/UI layer remains less mature than core runtime and proof layers.

## Major Contradictions And Stale Documents

| Area | Current document claim | Current implementation evidence | Audit verdict |
| --- | --- | --- | --- |
| Runtime model execution | `CURRENT_STATE_LOCK.md` and `README.md` say `NOT_WIRED` | `AgentRuntime.run` calls `ModelExecutionCoordinator` after a selected `ModelCallPlan`; `test_runtime_model_execution_wiring.py` proves real Groq runtime path | Stale lock docs |
| LLM model execution deferral | Broad `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` remains open | Real provider adapter and runtime path are proven, but action/mission budgets remain open | Split deferral needed |
| Real model spec tasks | Mirror spec tasks still unchecked in places | Implementation commits moved beyond the original plan | Spec task status stale |
| Post-cleanup handoff | Contains old cleanup/tree state | Repo later moved into provider/runtime work | Historical only |
| README snapshot | Says provider adapter layer locked, runtime not wired | Later commits prove Wave 9 and provider catalog/base hardening | Needs update |

## Sentinel <-> AI Model Power Interaction Review

### Current Model Interaction Path

Sentinel interacts with AI models through this actual path:

```text
AgentRuntime.run
-> LLMDecisionFrame.build(...)
-> render_prompt_text()
-> ModelCallOptimizer.plan(...)
-> RealModelRequestBuilder.build(...)
-> ModelExecutionCoordinator.execute(...)
-> provider registry
-> RealModelProvider adapter
-> ProviderModelResponse
-> LLMDecisionResultValidator
-> ModelExecutionReceipt
-> safe llm_decision_cycle metadata
-> CoreFinalGate certification of AgentRunResult
```

Authority does not come from the model. Provider/model selection comes from the
user model contract and selected plan. Optimizer output can become a
recommendation only when it differs from the user-selected model.

### Why Sentinel Uses AI Models

The repo's intended model roles include:

- planner
- reasoner
- critic
- verifier
- researcher
- strategist
- coder
- product analyst
- risk reviewer
- context compressor
- evidence interpreter
- mission decomposer
- organ/action proposer
- self-review agent
- multi-agent debate participant
- creativity engine
- multimodal interpreter
- future browser/desktop/email/API assistant

Today, only the structured decision/result lane is proven end-to-end through a
real provider. Brain L4 contains many structural roles for debate, belief,
resourcefulness, procedures, and pre-mortems, but these are not yet full live
LLM role loops.

### Model Powers Currently Unlocked

| Model power | Current status | Proof |
| --- | --- | --- |
| Real provider call | Proven with Groq | Provider adapter tests and implementation logs |
| Runtime real model execution | Proven through `AgentRuntime.run` | `test_runtime_model_execution_wiring.py` |
| Structured result validation | Implemented | `LLMDecisionResultValidator` |
| Safe receipts | Implemented | `build_model_execution_receipt` and redaction tests |
| Provider metadata catalog | Implemented | `catalog.py`, `provider_profiles.py`, `test_model_provider_catalog.py` |
| Generic OpenAI-compatible base | Implemented/hardened | `openai_compatible.py`, `test_openai_compatible_provider_base.py` |
| FinalGate after model path | Proven on returned result | Runtime tests assert accepted certification |
| No direct tool/organ execution from model output | Proven in tests | Runtime wiring tests |

### Model Powers Still Locked Or Underused

- Deep multi-step reasoning loops.
- Planner/critic/verifier role separation backed by real models.
- Multi-agent debate with real model participants.
- Long-context synthesis over large evidence sets.
- Browser task planning driven by model reasoning but executed only after organ
  authority gates.
- Desktop workflow planning.
- API action planning.
- Code generation and refactor loops.
- Vision, OCR, image/video understanding.
- Memory-aware reasoning beyond bounded context cards.
- Hypothesis generation with evidence challenges.
- Autonomous research strategy.
- Model-to-model collaboration.
- Cheap/strong model task splitting.
- Strict/flex/auto model policy contracts.
- Fallback contracts with explicit user authority.
- Confidence calibration and uncertainty reporting.
- Model performance benchmarking across tasks and providers.

### Wasted Model Capability

The biggest waste today is that Sentinel mostly uses the LLM as a single-pass
structured decision producer. That is safe, but shallow. The architecture is
ready for richer model power because authority, receipt, and FinalGate layers
already exist; the missing piece is controlled multi-role model loops that
never own execution authority.

### How To Unlock Model Power Without Chaos

Keep the non-negotiables:

- model output never grants authority
- model output never executes tools/organs directly
- model output never bypasses FinalGate
- model output never silently changes provider/model
- raw prompt/provider response/reasoning/key never becomes durable metadata
- recommendations are not execution
- fallback/AUTO routing requires explicit contract
- execution remains controlled by Sentinel authority layers

Then add power as proposal/verification loops first:

```text
planner model proposes
critic model attacks
verifier model checks evidence
Sentinel authority layer decides whether any action is even eligible
organ runtime executes only inside explicit envelope
FinalGate certifies terminal state
receipts prove what happened
```

### LLM Power Scores

| Dimension | Score | Rationale |
| --- | ---: | --- |
| Current LLM power | 4.2 / 10 | Real runtime provider path exists, but mostly single-pass JSON decision |
| LLM interaction maturity | 5.5 / 10 | Strong redaction, contract, receipt, FinalGate boundaries; weak role loops |
| Provider substrate | 6.5 / 10 | Catalog/base/Groq evidence strong; native providers/fallback/streaming incomplete |
| Authority separation around LLM | 8.0 / 10 | Model output is bounded and cannot execute tools/organs |
| Model reasoning exploitation | 3.0 / 10 | Debate/review/long-context/vision/coding loops are mostly future |

Biggest risk if unleashed too fast: the model becomes an implicit authority
source, especially through fallback routing, tool calls, or provider-native
tools.

Biggest opportunity if unleashed correctly: Sentinel becomes a controlled
intelligence harness where models do deep reasoning, criticism, and planning,
while Sentinel owns authority, execution, receipts, and certification.

## Current System Power Summary

Overall current power score: 5.8 / 10.

This is high for governance and proof, moderate for local execution, emerging
for real model intelligence, and incomplete for broad-world action.

Strongest existing layer: authority/proof/certification stack
(`MissionAuthorityEnvelope`, trace, receipts, replay, FinalGate).

Weakest critical layer: live strategic model cognition beyond one-pass
decision/result validation.

Biggest illusion/risk: old lock docs make the project look less advanced in
runtime model execution than it is, while organ docs can make broad external
power look more product-ready than it is.

Biggest real power: a real model can now pass through the runtime and still be
bounded by Sentinel's authority and FinalGate contract.

## Code-Level Discovery Addendum

This addendum answers the deeper question: not just what the docs say, but what
the repository can actually do by source path and test evidence.

### Repository Surface Actually Inspected

| Area | Evidence shape | Audit conclusion |
| --- | --- | --- |
| `sentinel-control/services/sentinel-core/sentinel/agent` | 120 Python files, about 22k lines | Largest implemented layer. Runtime, cognitive cycle, FinalGate, model execution, context economy, Brain-like helpers, and provider plumbing live here. |
| `sentinel-control/services/sentinel-core/sentinel/organs` | 107 Python files, about 21k lines | Large organ substrate exists, especially browser, desktop, API, channel, spend, and trading safety scaffolds. Actual execution is deliberately staged and gated. |
| `sentinel-control/services/sentinel-core/sentinel/perf` | 33 Python files, about 7.8k lines | Benchmark harness and Phase F regression machinery are real code, not just docs. |
| `sentinel-control/services/sentinel-core/sentinel/mission` | 22 Python files, about 2.6k lines | Mission authority, scope, runner, budget, reviewer, success evaluator, cancellation, and gate sequence are implemented. |
| `sentinel-control/services/sentinel-core/tests` | 166 Python test files | The repo has broad tests. Runtime/model execution tests are real. Some older lock docs cite historical counts that are now stale. |
| `sentinel-control/docs/brain` | 49 docs, about 4.1k lines | Brain architecture is heavily specified and partially implemented through runtime/cognition, but full live Brain society is not yet implemented. |
| `sentinel-control/docs/browser` | 209 docs, about 11.9k lines | Browser ambition and audits are deep. Code proves guarded navigation/route layers, not broad browser autonomy. |
| `sentinel-control/docs/providers` | Provider audits and design docs | Provider catalog, OpenAI-compatible hardening, and Groq runtime success are now ahead of some state locks. |
| `agent-lab` | Large vendor corpus plus curated forensic audits | Pattern mine and failure index only. Sentinel must not bridge vendor runtimes directly. |

### Runtime Truth

The current runtime is no longer just a non-model sandbox. It has a real
model-decision seam:

```text
AgentRuntime.run
-> context build and cache key derivation
-> LLMDecisionFrame.build(...)
-> frame budget enforcement if governor injected
-> prompt rendering through cache wrapper
-> ModelCallOptimizer.plan as recommendation or exact selected plan only
-> RealModelRequestBuilder.build(...)
-> ModelExecutionCoordinator.execute(...)
-> ProviderModelResponse
-> LLMDecisionResultValidator
-> ModelExecutionReceipt
-> AgentRunResult metadata
-> CoreFinalGate certification
```

Important runtime facts:

- `AgentRuntime.run` remains provider-agnostic. Provider-specific names are kept outside runtime.
- Model execution is optional and default-off. If there is no `UserModelContract`, no selected model plan, or no coordinator, runtime falls back to current behavior or records a safe deferred metadata path.
- ModelCallOptimizer cannot silently override the selected model. Runtime only accepts a candidate plan if its `model_id` equals the user-selected model; otherwise the candidate is advisory metadata.
- Model output is not an execution authority. It becomes a validated `LLMDecisionResult` and safe metadata, not a tool call, organ call, scope grant, or mission authority update.
- FinalGate still certifies the returned `AgentRunResult`; runtime downgrades rejected intended results to a certified `BLOCKED` result instead of letting a rejected result pass.

### Authority Truth

Sentinel has multiple authority chokepoints. No single one is the whole safety
model.

| Chokepoint | Code/docs proof | Current role |
| --- | --- | --- |
| `MissionAuthorityEnvelope` | mission and agent runtime references | Root mission authority. Other layers must not expand it. |
| `MissionScopeChecker` | black-zone action lists, path containment | Blocks high-risk action families and out-of-scope path mutation. |
| `RiskRouter.route` | mission risk routing | Converts scope and risk facts into allow/block/review decisions. |
| `CoreFinalGate` | final gate registry and tests | Certifies final run result and receipt/final metadata. |
| `OrganAuthorityEvaluator` | organ authority code/tests | Prevents organ layer from expanding root authority. |
| `OrganExecutionReceipt` | organ receipt checks | Requires L6 or above and authority/kill-switch/receipt evidence. |
| `EventBus` hash chain | `sentinel.shared.events` | Gives append-only event ordering and tamper evidence, not authority by itself. |
| Provider credential handles | model execution package | Keep credentials out of durable data; providers read env at execution time. |

The old `check_authority` helper is intentionally a stub and raises
`NotImplementedError`. That is not a missing safety layer by itself; the repo
documents canonical enforcement through the risk router, scope checker, organ
authority evaluator, and runtime boundaries.

### Execution Truth

Sentinel has many planned powers, but implemented mutation is narrow:

- `safe_executors.py` can create local generated project folders/files, GTM artifacts, JSON exports, outreach drafts without sending, watchlists, research-question files, and trace files under controlled generated paths.
- Browser code includes navigation and route-safety layers, but dangerous browser actions such as login/session mutation/form submit/post/publish/send and payment are proposal-only or blocked/quarantined in the audited layers.
- Desktop workspace L6 can read/write/list/create/rollback within workspace authority, while shell/process/terminal/screenshot/clipboard/click/type/window control are blocked.
- External API, channel send, spend, and trading families contain plans, gates, and dry-run/approval structures. The audit does not find proof that they should be treated as unrestricted live powers.
- Model output currently cannot directly call any of those actions. It is validated decision metadata that must still pass Sentinel authority layers.

### Stale Or Contradictory Truth

The largest current inconsistency is state-lock drift:

- `CURRENT_STATE_LOCK.md` and `README.md` still describe runtime model execution as not wired or Wave 9 open.
- The commit history and tests show later work: runtime wiring, real runtime model execution validation, provider catalog, and OpenAI-compatible provider base hardening.
- Some provider docs still carry pre-squash local commit hashes or say the old broad model-execution deferral is open without splitting provider success from runtime wiring.

This is not a runtime bug, but it is a serious project truth bug. It can cause
future agents to start the wrong phase, redo work, or underclaim the current
system.

### Critical AI Model Power Interface

The model is not just an API dependency. It is Sentinel's raw intelligence
engine. Today that engine is connected in a deliberately narrow way:

```text
model intelligence
-> structured decision/result
-> Sentinel validation
-> safe receipt metadata
-> FinalGate-certified runtime result
```

This is correct for first contact, but shallow relative to Sentinel's final
ambition. The LLM is currently used mostly as a single-pass structured decision
source. The architecture is ready for more, but has not yet unlocked:

- iterative planner/critic/verifier loops;
- model-role specialization;
- long-context synthesis;
- browser/desktop/API plan generation with authority review;
- memory-aware reasoning;
- self-review and self-correction;
- model capability benchmarking and selection policies;
- uncertainty calibration;
- multimodal/OCR/screen reasoning;
- multi-model debate and evidence challenge.

The safe unlock path is not to let models execute. It is to let models think
more deeply while Sentinel keeps execution authority:

```text
planner model proposes
critic model challenges
verifier model checks evidence
Sentinel authority decides what may be attempted
organs execute only under envelope and gate
FinalGate certifies final state
receipts prove what happened
```

### Audit Bottom Line

Sentinel today is a controlled agent kernel with real model execution evidence,
strong authority doctrine, strong proof scaffolding, and broad organ ambition.
It is not yet the final Mission OS. The next urgent work is not another
provider adapter and not broad organ execution. The next urgent work is to
consolidate truth, then unlock deeper model cognition under the existing
authority envelope.
