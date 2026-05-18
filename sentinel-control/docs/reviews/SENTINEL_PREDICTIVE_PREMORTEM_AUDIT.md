# Sentinel Predictive Pre-Mortem Audit

Mode: docs-only audit addendum. No production source, tests, runtime wiring,
provider calls, provider keys, `.env`, or push.

Date: 2026-05-18

Method: prediction plus pre-mortem. This document asks: "Assume Sentinel fails
badly after the new model/provider/runtime work. What probably broke first, how
would it propagate, and what early invariant should have caught it?"

This audit is intentionally harsher than the previous discovery review. It
does not only map layers. It reviews failure angles across code, tests, docs,
state locks, model/provider control, Brain ambition, organs, and FinalGate.

## Executive Verdict

Sentinel's strongest real layer is not "LLM calls work." The strongest real
layer is the controlled chain:

```text
MissionAuthorityEnvelope
-> AgentRuntime.run
-> LLMDecisionFrame
-> PromptRender
-> ModelCallPlan
-> ModelExecutionCoordinator
-> ProviderModelResponse
-> LLMDecisionResult
-> safe receipt metadata
-> CoreFinalGate-certified AgentRunResult
```

The biggest remaining danger is not a single missing provider. It is contract
drift between the layers that decide, route, execute, validate, certify, and
document model power.

The most likely future failures are:

1. Provider/model identity drift: the user-selected model is preserved, but the
   selected provider/backend is still inferred by optimizer/runtime configuration
   rather than encoded as a first-class user contract.
2. Semantic model-output escape: the validator catches top-level authority
   fields, but hidden or nested tool/organ/action intent can still appear inside
   otherwise valid JSON.
3. Durable leakage through "safe enough" fields: raw model rationale, provider
   error messages, prompt echoes, or reasoning summaries can enter durable
   result/diagnostic structures even when the raw prompt field itself is
   excluded.
4. Budget illusion: token/cost policies exist as metadata, but action-level and
   mission-level enforcement remain open deferrals.
5. Catalog illusion: provider catalog entries are strong metadata, but the
   execution registry can still bypass catalog constraints unless runtime and
   registry are unified behind a single provider contract.
6. FinalGate overclaim: FinalGate certifies trace/shape/receipts, but it does
   not yet prove the truth quality of the model's rationale or evidence claims.
7. Brain/product ambition outruns runtime truth: Brain, browser, desktop,
   channel, and external API docs describe many staged powers; future packs can
   accidentally treat documented ambition as implemented authority.

Strategic recommendation:

```text
Do not continue broad provider expansion immediately.
Next pack should be contract hardening:
  UserModelContract provider/backend identity
  deep LLMDecisionResult sanitizer
  provider catalog -> registry enforcement
  model execution budget enforcement
  state lock truth repair
```

## Evidence Base

Primary code anchors:

- `sentinel-control/services/sentinel-core/sentinel/agent/model_contract.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/coordinator.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/models.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/validator.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/registry.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/catalog.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/openai_compatible.py`
- `sentinel-control/services/sentinel-core/sentinel/mission/scope_checker.py`
- `sentinel-control/services/sentinel-core/sentinel/mission/runner.py`
- `sentinel-control/services/sentinel-core/sentinel/organs/*`
- `sentinel-control/services/sentinel-core/tests/test_runtime_model_execution_wiring.py`
- `sentinel-control/services/sentinel-core/tests/test_real_model_execution_backend.py`
- `sentinel-control/services/sentinel-core/tests/test_model_provider_catalog.py`
- `sentinel-control/services/sentinel-core/tests/test_openai_compatible_provider_base.py`

Primary docs anchors:

- `sentinel-control/docs/reviews/SENTINEL_DEEP_CODE_LOGIC_AUDIT.md`
- `sentinel-control/docs/reviews/SENTINEL_TOTAL_SYSTEM_DISCOVERY_AUDIT.md`
- `sentinel-control/docs/reviews/SENTINEL_NEXT_STRATEGIC_ROADMAP_VERDICT.md`
- `sentinel-control/docs/providers/PROVIDER_EXPANSION_PRE_IMPLEMENTATION_VERDICT.md`
- `sentinel-control/docs/providers/PROVIDER_CATALOG_DESIGN.md`
- `sentinel-control/docs/providers/PROVIDER_IMPLEMENTATION_ORDER.md`
- `sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/09_SIMULATION_AND_PREMORTEM_SCENARIOS.md`
- `sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/08_ADVISORY_TO_EXECUTABLE_PROMOTION_LADDER.md`
- `sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/10_PRESERVATION_CONSTRAINTS.md`
- `sentinel-control/docs/brain/BRAIN_ARCHITECTURE.md`
- `sentinel-control/docs/brain/P5L_PREMORTEM_HARDENING_SCORECARD.md`
- `sentinel-control/docs/browser/P4H_X_R_BRAIN_LLM_PERCEPTION_CONTEXT.md`
- `sentinel-control/docs/browser/README.md`

## Pre-Mortem Premise

Assume Sentinel succeeds enough that users begin trusting it for real missions:
research, product launch work, code planning, browser workflows, desktop
workspace operations, provider-backed reasoning, and future channel/API organs.

Then assume something goes wrong. The failure is unlikely to begin as a loud
security bypass. It will probably begin as a quiet mismatch:

- a selected model without a selected provider;
- a provider profile not enforced by the actual execution registry;
- model JSON that validates but smuggles action intent;
- a receipt that is hash-correct but semantically shallow;
- a state lock that says a layer is still deferred after it is actually wired;
- a docs-only capability that a future implementation treats as ready power.

That is the level Sentinel must now defend.

## Prediction 1 - Provider Identity Drift

Prediction: if Sentinel adds more providers before hardening the user model
contract, a future runtime path will preserve the model string while calling the
wrong provider or backend.

Failure chain:

```text
User chooses model X
-> UserModelContract stores selected_model only
-> ModelCallOptimizer chooses backend string
-> RealModelRequestBuilder sets provider_id = plan.backend
-> registry executes provider matching that backend
-> result says selected model preserved
-> user-provider intent was never represented
```

Code anchors:

- `UserModelContract` has `selected_model`, but no selected provider or backend.
- `ModelCallOptimizer.plan(...)` returns `backend`.
- `RealModelRequestBuilder.build(...)` assigns `provider_id=plan.backend` and
  `backend=plan.backend`.
- Runtime accepts `selected_model_call_plan` only when `candidate_plan.model_id`
  matches `frame.user_selected_model`; it does not independently verify a
  user-selected provider.

Why this matters:

The project doctrine says "User chooses the provider/model." Current runtime
tests prove selected model preservation, not selected provider preservation as a
first-class contract.

Early warning signal:

- Tests assert `request.provider_id == "groq"` or `"unit_provider"` because the
  optimizer was configured with that backend, not because a user contract
  demanded it.
- Provider catalog can describe providers, but `UserModelContract` cannot yet
  bind one.

Required invariant:

```text
UserModelContract.selected_provider_id
UserModelContract.selected_backend_id
ModelCallPlan.provider_id == selected_provider_id
ModelCallPlan.backend_id == selected_backend_id
RealModelRequest.provider_id == selected_provider_id
RealModelRequest.backend == selected_backend_id
```

Recommended pack:

`MODEL_PROVIDER_CONTRACT_HARDENING`

## Prediction 2 - Nested Model-Output Escape

Prediction: future model outputs will pass validation while hiding action/tool
intent under nested keys such as `proposal.tool_calls`, `next.actions`, or
`plan.organs`.

Current validator behavior:

- `_AUTHORITY_EXPANSION_FIELDS` checks keys directly in the top-level
  `content` dict.
- `tool_requested` and `organ_requested` also inspect top-level keys.
- `_has_valid_schema` only requires `decision`, `rationale`, and
  `evidence_refs`.

Failure chain:

```text
Provider returns valid JSON
-> top-level fields look harmless
-> nested proposal contains tool/organ/action intent
-> validator returns SUCCESS_VALIDATED
-> AgentRunResult stores validated model result metadata
-> future planner or UI consumes nested recommendation as actionable
```

Concrete failure payload shape:

```json
{
  "decision": "continue",
  "rationale": "Proceed with the task.",
  "evidence_refs": ["e1"],
  "proposal": {
    "tool_calls": [
      {"name": "browser_submit_form", "target": "https://example.test"}
    ]
  }
}
```

Required invariant:

The validator must recursively scan model output for:

- tool calls;
- organ execution;
- authority grants;
- credential access;
- browser/desktop/channel/API execution intent;
- budget overrides;
- provider/model override;
- hidden action plans promoted as executable.

Recommended pack:

`LLM_RESULT_DEEP_SANITIZER_AND_RECURSIVE_AUTHORITY_SCAN`

## Prediction 3 - Durable Leakage Through Rationale And Diagnostics

Prediction: Sentinel will correctly exclude the raw prompt field but still store
prompt echoes, provider response text, reasoning details, or secret-like content
inside `rationale_summary`, provider error diagnostics, or model result JSON.

Current risk points:

- `LLMDecisionResult.rationale_summary` stores `content["rationale"]` directly.
- Provider HTTP diagnostics include `provider_error_message` truncated but not
  semantically redacted.
- `ProviderModelResponse.content` can contain provider-parsed content; receipts
  hash sanitized data, but result metadata may carry accepted text fields.

Failure chain:

```text
Prompt asks model to reason over sensitive context
-> provider echoes sensitive text in rationale or error body
-> validator maps rationale into LLMDecisionResult
-> runtime attaches model_execution.result to AgentRunResult metadata
-> state/log/report persists text that was never intended as durable evidence
```

Required invariant:

No durable result, receipt, event, state lock, log, or diagnostic may contain:

- raw prompt body;
- raw provider response body;
- raw reasoning/thinking fields;
- raw key;
- prompt echo;
- credential-shaped text;
- authority object body;
- unredacted provider error message.

Recommended pack:

`MODEL_RESULT_DURABLE_REDACTION_GATE`

## Prediction 4 - Budget Illusion Under Real Model Power

Prediction: once real runtime model execution is used for more than tiny tests,
Sentinel will consume excessive tokens or time because budget policy objects are
metadata, not hard enforcement at coordinator/runtime boundaries.

Known open deferrals:

- `P-C-RUNTIME-01-ACTIONBUDGET-DEFER`
- `P-C-RUNTIME-01-MISSIONBUDGET-DEFER`

Current code shape:

- `ModelExecutionBudgetPolicy` participates in request metadata.
- Runtime creates default per-call policies.
- Coordinator does not enforce multi-call/action/mission budget exhaustion.
- Provider-specific timeout profiles exist, but production retry/rate-limit
  policy is still open.

Failure chain:

```text
Future Brain loop asks for deep reasoning
-> model call succeeds repeatedly
-> each call individually looks valid
-> no mission-level token/cost depletion gate stops the loop
-> FinalGate certifies final shape
-> receipts prove calls happened but not that budget authority was respected
```

Required invariant:

Every model execution must spend against:

- frame budget;
- per-call output budget;
- action-level token/cost budget;
- mission-level token/cost budget;
- retry budget;
- wall-clock timeout budget.

Recommended pack:

`ACTION_AND_MISSION_MODEL_BUDGET_CLOSURE`

## Prediction 5 - Catalog Illusion

Prediction: future developers will assume the provider catalog constrains
runtime execution, while actual execution still depends on `ModelProviderRegistry`
and injected providers.

Current separation:

- `ProviderCatalog` validates metadata.
- `ModelProviderRegistry` executes enabled providers.
- `ProviderCatalog.require_enabled_provider(...)` is not the canonical gateway
  used by runtime/coordinator before provider execution.

Failure chain:

```text
Catalog says provider is diagnostic-only or disabled
-> registry contains enabled provider object
-> coordinator asks registry directly
-> provider executes
-> catalog status was never enforced
```

Required invariant:

Provider execution must pass through both:

```text
User-selected provider/backend/model contract
-> ProviderCatalog enabled/status/model/profile validation
-> ModelProviderRegistry provider instance lookup
-> provider execute
```

Recommended pack:

`CATALOG_REGISTRY_EXECUTION_GATE`

## Prediction 6 - Registry Replacement Or Shadowing

Prediction: duplicate provider IDs will shadow previous providers unless every
registry path rejects duplicate registration.

Current code:

- `ProviderCatalog` rejects duplicate provider IDs.
- `ModelProviderRegistry.register(...)` assigns into a dict and overwrites an
  existing provider with the same `provider_id`.

Failure chain:

```text
Provider A registered for provider_id=groq
-> later provider B registers same provider_id
-> provider B silently replaces A
-> tests still pass if B mimics expected model
-> production calls route to unexpected implementation
```

Required invariant:

`ModelProviderRegistry.register(...)` must reject duplicate `provider_id`
unless an explicit test-only replacement mode is enabled.

Recommended pack:

`PROVIDER_REGISTRY_IDENTITY_HARDENING`

## Prediction 7 - FinalGate Overclaim

Prediction: FinalGate will be treated as proof that the model's conclusion is
true, while it really certifies structural safety, terminal result consistency,
trace/receipt properties, and no forbidden authority expansion.

What FinalGate is strong at:

- terminal certification;
- rejecting untraceable or malformed result paths;
- artifact/receipt/mission binding checks;
- browser and organ-specific receipt contracts;
- downgrading unsafe runtime results to certified blocked outputs.

What it does not prove by itself:

- the model's rationale is true;
- evidence refs actually support the claim;
- the selected provider was the user's intended provider;
- the mission-level model budget was respected;
- the result is product-quality correct.

Failure chain:

```text
LLMDecisionResult says "continue" with weak evidence
-> receipt metadata is safe
-> AgentRunResult is FinalGate-certified
-> caller interprets certification as truth/quality approval
```

Required invariant:

Separate these verdicts everywhere:

```text
FinalGate structural certification
Evidence support verdict
Model result validation verdict
Budget compliance verdict
User authority verdict
Product quality verdict
```

Recommended pack:

`FINALGATE_TRUTH_SEMANTICS_BOUNDARY_DOC_AND_TESTS`

## Prediction 8 - Brain Role Confusion

Prediction: future Brain packs will introduce planner/critic/reviewer/debate
model roles, and one of those roles will accidentally be treated as an executor
or authority granter.

Evidence already exists that Sentinel knows this risk:

- `BRAIN_ARCHITECTURE.md` says model output is not authority.
- `agent_society.py` includes prohibited outputs such as `new_authority`,
  `runtime_execution`, and `agent_spawn`.
- `brainbench.py` has negative-case fields for authority expansion and forged
  traces.

The risk is not absence of doctrine. The risk is role explosion.

Failure chain:

```text
Planner model proposes action
-> critic model approves plan text
-> verifier model summarizes "safe"
-> orchestrator treats multi-model consensus as execution permission
-> authority envelope was never expanded by user
```

Required invariant:

Every model role output must have:

- role name;
- allowed output schema;
- prohibited output schema;
- authority effect = none;
- execution effect = none;
- required downstream gate before action.

Recommended pack:

`BRAIN_MODEL_ROLE_CONTRACTS`

## Prediction 9 - Organ Power Illusion

Prediction: staged organ capabilities will be misunderstood as live powers
because the repo contains rich browser/desktop/channel/API documentation and
some implemented L6-style local workspace paths.

Existing strong controls:

- `MissionScopeChecker.BLACK_ZONE_ACTIONS` blocks shell, desktop control,
  credential access, payment, email send, production mutation, and related
  dangerous actions.
- `safe_executors.py` drafts outreach without sending.
- Browser and desktop organs contain authority, receipt, and FinalGate patterns.

The risk:

Docs describe many promotion paths. A future product flow can accidentally call
the wrong lower-level helper and interpret "draft", "route", "receipt", or
"candidate" as "approved execution".

Failure chain:

```text
LLM suggests browser/channel/desktop action
-> product workflow maps suggestion to a draft or route object
-> route object resembles executable action
-> runner/organ adapter executes or simulates success
-> approval boundary is missed
```

Required invariant:

Every action-like object must carry one of:

```text
ADVISORY_ONLY
DRAFT_ONLY
DRY_RUN_ONLY
APPROVAL_REQUIRED
APPROVED_EXECUTION
EXECUTED
```

Recommended pack:

`ACTION_OBJECT_AUTHORITY_STATE_MACHINE`

## Prediction 10 - State Lock Drift Causes Wrong Next Work

Prediction: future agents will follow stale state locks or docs and start the
wrong next pack, especially around model execution status.

Observed drift in review docs:

- Some docs said runtime model execution was `NOT_WIRED` after Wave 9 had
  proven real runtime model execution.
- The broad `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` needs split handling:
  provider adapter success and runtime execution success are no longer the same
  as action/mission budget closure.

Failure chain:

```text
State lock says old phase status
-> next agent starts redundant implementation
-> docs and code diverge further
-> tests still pass but roadmap intent fragments
```

Required invariant:

State lock must be updated at the end of each pack with:

- exact current phase;
- exact latest implementation commit;
- exact proven runtime capability;
- exact unproven capability;
- exact deferrals;
- next allowed pack;
- forbidden packs.

Recommended pack:

`STATE_LOCK_TRUTH_REPAIR`

## Prediction 11 - Product Quality Gap Hidden By Safety Success

Prediction: Sentinel will be safe enough to not violate authority but still weak
as an agent because it does not yet use enough model intelligence loops.

Current LLM power:

- real runtime model execution works through Groq;
- structured `LLMDecisionResult` validation works;
- prompt/render/plan/coordinator path exists;
- provider catalog/base exists.

Underused LLM power:

- multi-step reasoning loops;
- planner/critic/verifier split;
- uncertainty calibration;
- long-context synthesis;
- model benchmark routing;
- code-review and implementation loops;
- vision/OCR/document reasoning;
- browser/desktop planning with non-executable proposals;
- evidence challenge loops;
- model-to-model debate under explicit role contracts.

Failure chain:

```text
System remains one-shot JSON decision engine
-> users expect full Mission OS intelligence
-> safe but shallow output disappoints
-> pressure rises to bypass gates for power
```

Required invariant:

Unlock model power with role contracts and non-executable intermediate outputs,
not by letting raw model output drive organs.

Recommended pack:

`CONTROLLED_MODEL_REASONING_LOOPS`

## Prediction 12 - Evidence Ref Theater

Prediction: model results will include `evidence_refs` that are syntactically
valid but not semantically tied to the actual evidence cards.

Current validator:

- accepts any list for `evidence_refs`;
- converts refs to strings;
- does not prove refs exist in the decision frame;
- does not prove the referenced evidence supports the rationale.

Failure chain:

```text
Model emits evidence_refs=["evidence_1"]
-> schema validates
-> result is SUCCESS_VALIDATED
-> receipt hash is stable
-> downstream treats evidence_refs as support
```

Required invariant:

For success:

- every model evidence ref must exist in the frame's evidence set;
- every required evidence count must be satisfied;
- unsupported or invented refs must downgrade to non-success;
- critical claims must be challengeable by evidence verifier.

Recommended pack:

`LLM_EVIDENCE_REF_BINDING`

## Prediction 13 - Provider Error Message Injection

Prediction: provider error bodies will contain hostile or sensitive text, and
Sentinel will preserve enough of that text in diagnostics to create an
injection/leakage channel.

Current code:

- `_http_error_diagnostic(...)` stores `provider_error_message` as a truncated
  string when provider error JSON has `error.message`.

Failure chain:

```text
Provider returns error.message containing prompt echo or instruction
-> diagnostic stores message text
-> result metadata includes provider diagnostics
-> later model/frame sees diagnostic as trusted context
```

Required invariant:

Provider diagnostics must store:

- status code;
- provider error type/code after safe whitelist;
- message hash;
- bounded classification;
- no raw message text by default.

Recommended pack:

`PROVIDER_ERROR_DIAGNOSTIC_REDACTION`

## Prediction 14 - Local Provider Boundary Collapse

Prediction: adding Ollama/LM Studio/local OpenAI-compatible providers will make
"no API key" look safer than it is, while local models can still see sensitive
prompts, run on a mutable local server, or differ from catalog assumptions.

Failure chain:

```text
Local provider marked credential-free
-> runtime sends prompt to local server
-> local server is untrusted or shared
-> raw prompts leave Sentinel process
-> no credential was leaked, but prompt confidentiality still failed
```

Required invariant:

Local providers need:

- endpoint allowlist;
- loopback-only by default;
- local server identity hash;
- model availability proof;
- prompt confidentiality warning;
- no automatic discovery execution.

Recommended pack:

`LOCAL_PROVIDER_SECURITY_BOUNDARY`

## Prediction 15 - Streaming Opens A New Leakage Surface

Prediction: streaming support will be added as a performance/user-experience
feature and will accidentally bypass the non-durable response rule.

Failure chain:

```text
Provider streams chunks
-> UI/log/debug hook captures chunks
-> raw chain-of-thought/reasoning/prompt echo appears in transcript
-> final receipt is clean but side-channel log leaks
```

Required invariant:

Streaming must have a separate policy:

- no raw chunk durable logging;
- chunk hash aggregation;
- reasoning chunk redaction;
- timeout and abort policy;
- final validator only sees bounded in-memory assembled content.

Recommended pack:

`STREAMING_PROVIDER_REDACTION_GATE`

## Prediction 16 - Approval Boundary Degrades Into UX Friction

Prediction: as Sentinel becomes more powerful, developers will be tempted to
remove approval gates because they slow product workflows, especially browser,
email, desktop, payment, and API mutation tasks.

Failure chain:

```text
User asks for autonomous workflow
-> model produces strong plan
-> existing authority envelope is broad but not explicit enough
-> approval step feels redundant
-> future code treats "mission requested" as "approved execution"
```

Required invariant:

Approval is not a UI preference. It is an authority transition:

```text
proposal -> preview -> explicit approval -> execution -> receipt -> FinalGate
```

Recommended pack:

`USER_APPROVAL_CONTRACTS_FOR_HIGH_POWER_ORGANS`

## Prediction 17 - Fake Runtime Success Reappears Through Tests

Prediction: future provider or runtime tests will introduce mocks that return
`SUCCESS_VALIDATED` without proving the same constraints real providers must
obey.

Existing good pattern:

- Pack B rejected fake backend/response as real success.
- Real Groq path provided success evidence.
- Skip-safe tests can run without keys.

Failure chain:

```text
New provider test uses mock response
-> mock passes validator
-> status marked success_validated
-> docs claim provider works
-> real path later fails
```

Required invariant:

Separate:

```text
UNIT_SCHEMA_SUCCESS
STRUCTURAL_ADAPTER_READY
REAL_PROVIDER_SUCCESS_VALIDATED
REAL_RUNTIME_SUCCESS_VALIDATED
```

Recommended pack:

`REAL_PROVIDER_EVIDENCE_CLASSIFICATION`

## Prediction 18 - Authority From Memory Or Context Reappears Indirectly

Prediction: memory/context closure blocks direct authority drift, but future
model loops will treat memory-derived suggestions as mission permissions.

Existing controls:

- Context cache key uses authority hash and mission hot hash.
- Memory-not-authority tests exist.
- Context pack docs repeat that memory/model output is not authority.

Failure chain:

```text
Memory says user often uses provider/action/domain
-> model sees memory as preference
-> planner proposes same action
-> orchestrator treats preference as allowed action
```

Required invariant:

Every action candidate must prove:

```text
source = mission authority envelope
not memory
not model suggestion
not cached context
not prior mission
```

Recommended pack:

`ACTION_AUTHORITY_SOURCE_BINDING`

## Prediction 19 - Browser/Visual Evidence Becomes Authority

Prediction: future browser/vision packs will let page text, OCR text, or visual
state influence action permission.

Existing doctrine:

- Browser docs state visual/OCR evidence is not authority.
- Browser V3 authority classes and FinalGate checks exist.

Failure chain:

```text
Page says "click continue"
-> OCR/DOM evidence enters context
-> model proposes click
-> action planner treats page affordance as authorization
```

Required invariant:

Browser/page/visual evidence can identify target and state, but never grant:

- submit authority;
- login authority;
- upload/download authority;
- cookie/storage authority;
- external send authority.

Recommended pack:

`VISUAL_AND_BROWSER_EVIDENCE_AUTHORITY_FIREWALL`

## Prediction 20 - Product Workflow Starts Before Kernel Is Honest

Prediction: product workflow packs will be started while the kernel still has
state-lock drift, budget gaps, and provider contract gaps.

Failure chain:

```text
Provider path works once
-> pressure to build product workflows
-> product packs combine model reasoning with organs
-> unclosed model/provider/budget invariants become production bugs
```

Required sequence:

1. State lock truth repair.
2. Provider/model contract hardening.
3. Deep output sanitizer and evidence binding.
4. Action/mission budget closure.
5. Only then expand provider/product/organs in higher-power directions.

## Highest Risk Predictions

| Rank | Prediction | Probability | Impact | Detectability | Why |
|---|---:|---:|---:|---:|---|
| 1 | Provider identity drift | High | High | Medium | More providers make backend inference fragile. |
| 2 | Nested tool/organ intent passes validation | High | High | Low | Current scan is top-level. |
| 3 | Rationale/error leakage | Medium | High | Low | Raw prompt exclusion does not cover semantic echoes. |
| 4 | Budget overrun | Medium | High | Medium | Budget deferrals are explicitly open. |
| 5 | Catalog/runtime mismatch | Medium | High | Medium | Catalog and registry are separate. |
| 6 | FinalGate overclaim | High | Medium | Low | Certification can be misread as truth. |
| 7 | Brain role confusion | Medium | High | Medium | Role expansion is planned but not fully contracted. |
| 8 | Organ power illusion | Medium | High | Medium | Many powerful docs and partial implementations exist. |
| 9 | State lock drift | High | Medium | High | Already observed. |
| 10 | Evidence ref theater | High | Medium | Low | Schema accepts refs without support proof. |

## Current Power Score Under Pre-Mortem Lens

| Dimension | Score | Reason |
|---|---:|---|
| Authority kernel | 8 | Strong envelope/scope/risk/FinalGate pattern, but provider identity and model-output semantics need hardening. |
| Real LLM runtime path | 7 | Real Groq runtime path proven, provider-agnostic runtime preserved. |
| Provider abstraction | 6 | Catalog/base exist, but catalog is not yet execution gate and provider contract is incomplete. |
| Model output safety | 5 | Top-level checks and receipt redaction exist, but deep semantic scan and evidence binding are weak. |
| Budget governance | 4 | Frame/per-call pieces exist; action/mission deferrals remain open. |
| Brain intelligence loops | 4 | Strong docs and some BrainBench structures; controlled multi-role model loops not live. |
| Organ execution power | 5 | Many gated organ surfaces and some local workspace power; high-power live paths remain staged. |
| Documentation truth | 5 | Rich docs, but drift and overclaim risk are real. |
| Product-ready autonomous power | 3 | Kernel is promising; workflows are not yet safe enough for broad autonomous product operation. |

## Pre-Mortem Root Causes

These are the underlying causes that can generate many surface failures:

1. Identity ambiguity:
   - model identity is stronger than provider/backend identity.
2. Schema shallowness:
   - valid JSON is not equal to safe decision.
3. Receipt narrowness:
   - hash-correct metadata is not equal to truth or support.
4. Budget incompleteness:
   - per-call success is not mission affordability.
5. Phase drift:
   - docs, locks, implementation logs, and tests can disagree.
6. Ambition pressure:
   - a Mission OS wants power, but power must be sequenced.

## What Should Not Happen Next

Do not immediately start:

- broad provider expansion;
- automatic provider routing;
- fallback provider execution;
- provider marketplace/plugin loading;
- tool/function calling from provider outputs;
- Brain multi-agent execution loops;
- browser login/session execution expansion;
- email/channel send;
- payment/spend/trading live execution;
- product workflow automation that consumes model decisions as action authority.

## What Should Happen Next

Recommended next three packs:

### Pack 1 - Provider/Model Contract Hardening

Goal: make user-selected provider/backend/model a first-class immutable contract.

Must include:

- `selected_provider_id`;
- `selected_backend_id`;
- provider/backend/model equality checks across frame, plan, request, registry,
  receipt, and result;
- no backend-as-provider conflation;
- duplicate registry provider rejection;
- catalog status enforced before registry execution.

### Pack 2 - Deep Model Result Safety

Goal: make `LLMDecisionResult` safe enough for durable runtime metadata.

Must include:

- recursive authority/tool/organ scan;
- rationale redaction/summarization;
- provider error message hashing;
- evidence ref binding;
- no prompt echo durability;
- no hidden action proposals;
- tests with nested adversarial payloads.

### Pack 3 - Action/Mission Budget Closure

Goal: make repeated model calls safe for real missions.

Must include:

- action-level token/cost budget;
- mission-level token/cost budget;
- retry budget enforcement;
- timeout budget enforcement;
- final receipt budget summary;
- FinalGate check for budget compliance metadata.

## Final Pre-Mortem Verdict

Sentinel is not weak. It is actually becoming strong enough that the weak points
are no longer obvious toy gaps. The real danger is a subtle one:

```text
safe structural success
mistaken for
safe intelligent autonomous execution
```

The next move should make the contracts sharper before adding more power.

Provider expansion can resume after provider identity, deep model-output safety,
and budget governance are strengthened.
