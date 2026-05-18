# Provider Expansion Pre-Implementation Verdict

Audit date: 2026-05-18

Mode: audit-only verdict. No code was implemented by this document. No tests,
runtime source, `.env`, provider key, or state lock were modified.

## Verdict

```text
PROVIDER_EXPANSION_PRE_IMPLEMENTATION = GO_WITH_GUARDRAILS
recommended_next_pack = PROVIDER_CATALOG_AND_ADAPTER_HARDENING
runtime_provider_router = NOT_APPROVED
silent_fallback = REJECTED
vendor_runtime_bridge = REJECTED
```

Provider expansion can start, but it should not start as a broad autonomous
router. Sentinel should first harden the provider catalog/adapter layer around
the existing `ModelExecutionCoordinator` and the user-selected model contract.

## Current Sentinel Position

Already proven:

```text
ModelCallPlan-compatible request
-> real provider call
-> ProviderModelResponse
-> LLMDecisionResult
-> safe receipt/redaction
```

Already validated by current local Wave 9 evidence:

```text
AgentRuntime.run
-> ModelCallPlan
-> ModelExecutionCoordinator
-> provider adapter
-> ProviderModelResponse
-> LLMDecisionResult
-> safe receipt metadata
-> FinalGate-certified AgentRunResult
```

Still not closed by this audit:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
production fallback/routing policy
production retry/rate-limit policy
streaming provider response policy
local model execution policy
provider management UI
```

## Recommended First Providers

### 1. Groq - keep as validated smoke provider

Decision:

```text
status = keep as first SUCCESS_VALIDATED evidence provider
adapter type = OpenAI-compatible chat adapter
role = regression/smoke provider, not hardcoded architecture
```

Why:

- already produced validated real-provider evidence
- small prompt tests are fast enough for skip-safe integration
- good first regression target for real provider path

Required next tests:

- provider unavailable maps to honest error
- missing credential never calls network
- model ID from user contract preserved
- no raw key/prompt/response/reasoning durable leakage

### 2. Generic OpenAI-compatible provider base - implement after catalog rules

Decision:

```text
status = recommended next engineering target
adapter type = generic base plus provider-specific policy profiles
```

Why:

- Groq, OpenRouter, NVIDIA Integrate, and many hosted providers share a chat
  completions shape
- AgentLab shows many provider systems converge on OpenAI-compatible APIs
- a common base reduces duplication only if provider differences stay explicit

Guardrails:

- no provider-specific fallback in base adapter
- no implicit reasoning capture
- no raw response storage
- provider policy profile must declare error mapping, usage mapping,
  reasoning field handling, timeout defaults, and supported request fields

### 3. OpenRouter - diagnostic/hardening candidate

Decision:

```text
status = diagnostic candidate, not production-ready
adapter type = OpenAI-compatible provider with special routing/reasoning policy
```

Why:

- useful multi-provider gateway
- AgentLab/Hermes evidence shows provider routing can be powerful
- existing Sentinel diagnostics observed non-success provider outcomes

Risks:

- provider routing/fallback can change underlying model/provider
- reasoning fields can appear unexpectedly
- rate limits/timeouts/provider errors are common
- no success overclaim allowed

Required before promotion:

- real `SUCCESS_VALIDATED` path
- route/provider metadata safe enough for receipts
- no raw reasoning fields
- no silent fallback to a different underlying provider

### 4. NVIDIA MiniMax - diagnostic/hardening candidate

Decision:

```text
status = diagnostic candidate, not production-ready
adapter type = OpenAI-compatible provider with long-context timeout policy
```

Why:

- potentially valuable long-context/free-tier candidate
- current adapter observed timeout, not success

Required before promotion:

- explain timeout/root cause
- tune request/timeout policy without weakening test safety
- prove validated response
- prove no raw prompt/key/response leakage

### 5. Local model adapter - future pack

Decision:

```text
status = future explicit provider pack
adapter type = native/local provider
```

Why:

- OpenJarvis local-first routing is useful for cost/privacy
- local provider availability and model fit are environment-dependent

Required boundaries:

- no auto-download
- no auto-execution
- no filesystem/model-path leakage
- user-selected local provider contract required

### 6. Native Anthropic/OpenAI/Gemini/xAI adapters - later

Decision:

```text
status = later provider packs
adapter type = native where protocol differs
```

Why:

- each has different request/response/tool/reasoning/usage semantics
- native adapters should follow catalog and redaction rules first

## Recommended Next Implementation Pack

Name:

```text
Provider Catalog And Adapter Hardening
```

Scope:

- Add a provider catalog/configuration model that maps provider IDs to:
  provider type, backend ID, base URL hash, supported model IDs, credential env
  ref hash, timeout policy, retry policy, reasoning handling, usage mapping,
  and real-provider test status.
- Keep catalog default-off.
- Keep provider/model selected by `UserModelContract`.
- Keep `ModelCallOptimizer` advisory only.
- Add generic OpenAI-compatible adapter base only if it reduces duplication
  without hiding provider-specific behavior.
- Add tests proving the catalog cannot silently override selected model.
- Add tests proving provider recommendations are not execution.

Out of scope for next pack:

- Wave 10 state lock unless implementation is reviewed
- autonomous provider router
- silent fallback
- streaming
- local model runtime
- new organs
- tool/function execution from model output
- action token-budget closure
- mission token-budget closure

## User-Selected Model Doctrine

Sentinel must enforce:

```text
selected_provider/model = user contract
optimizer_output = recommendation only
fallback_output = recommendation only
catalog_default = metadata only
provider_error = honest outcome, not auto-route permission
```

The only valid ways to change provider/model are:

1. user supplies a new model contract
2. user explicitly approves a fallback contract
3. a future authority-reviewed policy updates the selected contract with trace

No provider expansion pack may silently route from one provider/model to
another because of price, latency, quality, timeout, rate limit, or
availability.

## Key Handling Rule

Allowed:

- environment variable read at execution time
- scoped credential ref in future vault design
- credential source hash in receipts
- provider ID and model ID in receipts

Forbidden:

- raw provider key in repo
- raw provider key in docs
- raw provider key in tests
- raw provider key in events
- raw Authorization header in durable metadata
- raw key on `ProviderCredentialHandle`
- `.env` modification by provider expansion work

## Runtime Safety Rules

The runtime provider path must keep these properties:

- `AgentRuntime.run` remains provider-agnostic
- provider adapters are injected/configured, not imported into runtime branches
- model output validates into `LLMDecisionResult`
- model output cannot execute tools
- model output cannot execute organs
- model output cannot grant authority
- model output cannot expand scope
- FinalGate still certifies returned `AgentRunResult`
- provider errors/rate limits/timeouts remain honest outcomes
- raw prompt/provider response/reasoning/key never becomes durable metadata

## Required Tests For Provider Expansion

Provider catalog tests:

- unknown provider rejected
- disabled provider rejected
- fake provider marker rejected
- provider metadata secret-free
- supported model mismatch rejected
- catalog recommendation does not execute

Runtime doctrine tests:

- runtime contains no provider-specific branch
- user-selected model preserved
- optimizer recommendation cannot override selected model
- fallback recommendation cannot execute without approved contract
- provider failure does not fake success
- FinalGate still runs

Redaction tests:

- no raw key in result/log/receipt/docs
- no raw prompt in durable metadata
- no raw provider response in durable metadata
- no raw reasoning/thinking fields in durable metadata
- receipt hashes deterministic

Real-provider tests:

- skip safely when key absent
- run one tiny harmless prompt when key present
- fail if fake response substituted
- validate into `LLMDecisionResult`
- produce safe receipt

## GO/NO-GO

```text
provider_catalog_pack = GO
generic_openai_compatible_base = GO_AFTER_TESTS
new_provider_adapters = GO_ONE_PROVIDER_AT_A_TIME
automatic_fallback_router = NO_GO
runtime provider hardcoding = NO_GO
tool/function calling from provider output = NO_GO
local model auto-route = NO_GO
```

Recommended first implementation after this audit:

```text
Pack D1 - Provider Catalog And OpenAI-Compatible Adapter Hardening
```

Recommended commit shape:

```text
one implementation commit maximum
one final state/docs commit maximum if lock update is explicitly requested
no push until explicit approval
```

## Final Confirmation

This verdict does not:

- implement code
- modify tests
- modify `CURRENT_STATE_LOCK.md`
- modify `AgentRuntime.run`
- start Wave 10
- start P6U
- start Brain/Science expansion
- add providers
- call providers
- touch `.env`
- use API keys
