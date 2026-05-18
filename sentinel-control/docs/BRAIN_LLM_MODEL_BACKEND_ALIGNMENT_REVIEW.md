# Brain / LLM / Model Backend Alignment Review

Date: 2026-05-18
Status: Docs-only alignment review

## Verdict

The real model execution backend is aligned with Sentinel only if model output
remains a bounded decision artifact, not a source of authority or direct tool
execution.

Correct hierarchy:

```text
MissionAuthorityEnvelope = authority source
Brain L4 = cognitive controller
LLMDecisionFrame = compact decision context
ModelCallPlan = call planning metadata
RealModelRequest = sanitized provider request envelope
LLMDecisionResult = validated, authority-neutral model output
FinalGate = terminal certification
```

Incorrect hierarchy:

```text
model output -> authority
model output -> direct tool call
model output -> organ execution
provider response -> trusted state without validation
```

## Brain L4 Doctrine Fit

The Brain docs lock these invariants:

```text
Memory never grants authority.
Mission authority is immutable during a run.
Unknown tools do not execute.
Candidate tools do not execute.
Learning output is proposal-only.
Repair cannot expand authority.
POWER posture changes aggressiveness only inside already granted authority.
```

The model backend must inherit those invariants directly.

| Brain component | Existing responsibility | Backend implication |
| --- | --- | --- |
| ContextBuilder | Build context from mission, evidence, memory | Request builder may use frame/prompt hash, not raw context dump in durable metadata |
| ContextCompressor | Preserve trace/evidence refs while reducing context | Provider request must start from compact frame/prompt, not raw receipts/files/pages |
| ToolSelector | Classify tools under mission authority | Model result may cite or request, but cannot authorize tools |
| EffortRouter | Select effort from uncertainty/risk/budget | Model execution budget is a provider-call policy, not action/mission budget closure |
| PlannerBridge | Build plan from selected tools and verified facts | `LLMDecisionResult` can become input to later planning only after validation |
| ReviewLoop | Find problems before completion | Model response validation is a precondition before any use |
| CoreFinalGate | Certify trace, replay, receipts, scope | FinalGate checks invariants; it is not a model quality judge |

## Runtime Flow Placement

The current Brain runtime flow is:

```text
context_building
-> orienting
-> method_selecting
-> capability_selecting
-> tool_selecting
-> hypothesis_verifying
-> action_scoring
-> effort_routing
-> planning
...
-> final gate
```

The locked LLM decision-cycle seam adds a bounded LLM-facing step after
tool selection and before execution-sensitive work:

```text
selected runtime state
-> LLMDecisionFrame.build(...)
-> render_prompt_text()
-> ModelCallOptimizer.plan(...)
-> model execution deferred
```

Pack A should not move this boundary. It should create only the backend-side
objects that will later receive the `ModelCallPlan` and rendered prompt hash.

## LLMDecisionFrame Contract Fit

`LLMDecisionFrame` already carries the right shape:

```text
mission_card
authority_card
progress_card
top_k_evidence
selected_tool_surface
current_blockers
next_decision_options
required_output_schema
receipt_refs
user_selected_model
frame_hash
```

It already rejects the bad pattern:

```text
all receipts
all files
all browser pages
all API outputs
all tool schemas
raw secret material
raw authority expansion
```

The model backend must therefore receive:

```text
frame hash
prompt hash
sanitized call metadata
selected user model
provider/backend ID
timeout/retry/budget policy
```

It must not persist:

```text
raw prompt body
raw credential value
raw unsanitized provider response
raw mission authority as mutable authority object
raw browser/file/API bodies
```

## LLMDecisionResult Boundary

`LLMDecisionResult` should be the only accepted model-output object.

It may contain:

```text
decision label
rationale summary
cited evidence refs
uncertainty/confidence metadata
refusal status
error status
provider/model metadata
response hash
validation status
```

It must not contain or grant:

```text
new tools
new organs
new allowed paths/domains
new budgets
credential access
browser/session powers
payment/spend powers
trading execution
channel send authority
```

This keeps the model in the role Sentinel wants:

```text
reasoning partner, not authority source
```

## FinalGate Relationship

FinalGate should see model execution only as proof metadata:

```text
model execution receipt hash
authority_expansion = false
raw_secret_leakage = false
receipt hash valid
terminal result remains inside MissionAuthorityEnvelope
```

FinalGate should not become:

```text
model provider router
model quality judge
latency budget gate
cost optimizer
prompt compiler
```

That separation keeps the backend compatible with the Phase F FinalGate rule:
FinalGate verifies minimal cross-cutting invariants and receipt validity, while
benchmark/cost/gate logic stays in its own layer.

## Browser-LLM Lessons Applied

The Browser-LLM docs already prove the right pattern:

```text
ContextPack -> planner draft -> compiler -> authority check -> execution -> verifier -> FinalGate
```

The same shape should be used for model execution:

```text
LLMDecisionFrame -> model response draft -> LLMDecisionResultValidator
-> no authority expansion -> future planner/compiler boundary
```

The Browser docs also lock this rule:

```text
LLM may reason, rank, explain uncertainty, suggest next intent, and criticize proof.
LLM may not mint runtime refs, create authority, execute raw tool calls, or skip compiler/gate layers.
```

That should become a shared LLM backend rule, not only a browser rule.

## Alignment Score

| Dimension | Score | Reason |
| --- | ---: | --- |
| Brain authority compatibility | 9/10 | Pack A can preserve MissionAuthorityEnvelope as the only authority source |
| Context economy compatibility | 9/10 | Request metadata can use prompt/frame hashes rather than raw dumps |
| Model flexibility | 8/10 | User-selected model doctrine is already represented by `UserModelContract` and `ModelCallPlan` |
| Real execution readiness | 5/10 | Provider adapter and runtime wiring are intentionally not in Pack A |
| Proof/replay readiness | 8/10 | Receipt shape can be deterministic and hash-based |
| AgentLab competitiveness | 7/10 | Sentinel is stronger on authority/proof, weaker on live model/provider runtime |

Overall:

```text
alignment = strong for structural foundation
runtime maturity = incomplete until real provider and AgentRuntime wiring
```
