# Sentinel Deep Code And Logic Audit

Status: defect-oriented review
Scope: code, runtime logic, model execution, provider selection, authority boundaries, organ power, state locks
No code changes: yes
No provider calls: yes
No API keys used: yes
No push: yes

## Executive Finding

The previous total-system audit correctly mapped Sentinel, but it underreported
actual implementation defects. This pass treats Sentinel as code under review,
not just architecture.

The most important finding is this:

```text
Sentinel proves model execution through runtime, but the provider/model
contract is not yet strong enough to support the doctrine "user chooses the
provider/model" without ambiguity.
```

The current code preserves the user-selected model string, but it does not
model user-selected provider identity as a first-class contract field. Provider
choice comes from `ModelCallOptimizer.default_backend` or backend inference.
That means provider choice is still runtime/config selected, not user-contract
selected.

This is the biggest logic gap in the current model layer.

## Review Method

This audit inspected source paths and ran targeted non-provider tests and proof
snippets.

Source areas reviewed:

- `sentinel/agent/runtime.py`
- `sentinel/agent/model_contract.py`
- `sentinel/perf/caches/model_call_optimizer.py`
- `sentinel/agent/model_execution/coordinator.py`
- `sentinel/agent/model_execution/models.py`
- `sentinel/agent/model_execution/validator.py`
- `sentinel/agent/model_execution/openai_compatible.py`
- `sentinel/agent/model_execution/credentials.py`
- `sentinel/agent/model_execution/registry.py`
- `sentinel/agent/model_execution/catalog.py`
- `sentinel/agent/model_execution/provider_profiles.py`
- mission authority, scope, risk, safe executor, organ authority, organ receipt, browser, desktop, and event code paths

Targeted tests run:

```text
python -m pytest tests/test_openai_compatible_provider_base.py tests/test_model_provider_catalog.py -q
python -m pytest tests/test_runtime_model_execution_wiring.py -q -rs
python -m pytest tests/test_real_model_execution_backend.py -q
```

Result: all passed. These passing tests do not catch the logic defects below.

## Critical Findings

### C1 - User-selected provider is not actually part of `UserModelContract`

Severity: Critical

Files:

- `sentinel/agent/model_contract.py`
- `sentinel/perf/caches/model_call_optimizer.py`
- `sentinel/agent/model_execution/coordinator.py`
- `sentinel/agent/runtime.py`
- `tests/test_runtime_model_execution_wiring.py`

Observed code reality:

- `UserModelContract` contains `selected_model`.
- `UserModelContract` does not contain `provider_id`.
- `UserModelContract` does not contain `backend_id`.
- Runtime accepts `ModelCallPlan` when `candidate_plan.model_id == frame.user_selected_model`.
- Runtime does not check that `candidate_plan.backend` came from a user-selected provider contract.
- `ModelCallOptimizer._select_backend` infers `openai` for `gpt-*` and `anthropic` for `claude-*`.

Proof snippet result:

```text
UserModelContract fields= ['alternative_model_recommendations', 'capability_profile', 'context_budget_policy', 'cost_profile', 'id', 'model_override_attempted', 'quality_expectation', 'selected_model', 'user_selected']
has_provider_id= False
has_backend_id= False
gpt_backend= openai
```

Impact:

Sentinel's doctrine says the user chooses provider/model and Sentinel must not
silently choose another provider. Current code preserves model identity, but
provider identity can be inferred by optimizer/config. That is not enough for a
multi-provider Mission OS.

Why existing tests miss it:

- Tests assert `model_id` preservation.
- Tests assert no `groq` hardcoding in runtime.
- Tests do not require a user-selected provider contract.
- Tests use `ModelCallOptimizer(default_backend="groq")` or `"unit_provider"`,
  which makes backend act like provider id by convention.

Required fix direction:

- Add an explicit provider/backend contract to the user model layer or a paired
  `UserProviderContract`.
- Runtime must accept model execution only when both selected model and selected
  provider/backend match the user contract.
- Optimizer may recommend provider/backend alternatives only as metadata.
- Prefix-based provider inference must not execute unless the user contract
  explicitly selected that provider/backend.

### C2 - `RealModelRequestBuilder` conflates backend and provider identity

Severity: Critical

File:

- `sentinel/agent/model_execution/coordinator.py`

Observed code:

```text
provider_id = plan.backend
backend = plan.backend
```

But the provider catalog separates:

```text
provider_id = groq
backend_id = groq_openai_compatible_chat
```

Impact:

The request builder currently works only if `ModelCallPlan.backend` contains a
provider id, not a backend id. That conflicts with the catalog design and
provider docs, where backend id is distinct from provider id.

Failure modes:

- A correct catalog-shaped plan using `backend="groq_openai_compatible_chat"`
  would create `request.provider_id="groq_openai_compatible_chat"`, causing
  registry lookup failure.
- A future adapter pack may accidentally keep passing tests by using provider id
  in the backend field, while docs and catalog say otherwise.
- Provider governance cannot cleanly distinguish provider selection from backend
  profile selection.

Required fix direction:

- Split `ModelCallPlan.provider_id` and `ModelCallPlan.backend_id`.
- Make `RealModelRequest.provider_id` source from provider contract, not backend.
- Keep `backend` or `backend_id` as adapter profile metadata only.

### C3 - Provider credential handle is secret-free but not enforced by providers

Severity: Critical

Files:

- `sentinel/agent/model_execution/openai_compatible.py`
- `sentinel/agent/model_execution/credentials.py`

Observed code reality:

- `EnvironmentCredentialResolver` returns a secret-free
  `ProviderCredentialHandle`.
- `OpenAICompatibleChatProvider.execute(...)` ignores the handle's provider id
  and source hash when choosing which environment variable to read.
- The provider reads `os.environ.get(self.credential_env or "")` directly.

Proof snippet result:

```text
call_count= 1
credential_provider_mismatch_rejected= False
```

The proof passed a credential handle for `other_provider` into a provider
configured for `unit_provider`. The provider still made a call because the env
var from provider config existed.

Impact:

The credential handle is not yet a true binding proof. It proves the resolver
returned something, but provider execution does not verify:

- credential provider id matches provider id;
- credential env var hash matches configured env var;
- required scopes match;
- credential source type is allowed for that provider.

Required fix direction:

- Provider adapters must reject mismatched credential handles before reading env.
- `ProviderCredentialHandle` should expose a method such as
  `matches_env(provider_id, env_var_name, required_scopes)`.
- Provider tests must pass mismatched handles and assert no network call.

## High Findings

### H1 - Validated model rationale can durably store raw model output

Severity: High

Files:

- `sentinel/agent/model_execution/validator.py`
- `sentinel/agent/model_execution/models.py`
- `sentinel/agent/runtime.py`

Observed code:

- `LLMDecisionResult.rationale_summary` is set directly from
  `content["rationale"]`.
- Runtime stores `outcome.result.model_dump(mode="json")` in
  `llm_decision_cycle["model_execution"]["result"]`.
- There is no sanitizer applied to the model's rationale string.

Proof snippet result:

```text
success= True
secret_persisted_in_result_json= True
```

Impact:

If a model echoes raw prompt text, a credential-looking token, internal
reasoning, or provider response details inside `rationale`, Sentinel will store
it in durable runtime metadata.

This violates the stronger intent of:

- no raw prompt durable storage;
- no raw provider response durable storage;
- sanitized `LLMDecisionResult` only.

Existing tests miss it because they only use safe tiny rationale text.

Required fix direction:

- Add a `sanitize_model_text_for_durable_result(...)` chokepoint.
- Apply it to `decision`, `rationale`, `evidence_refs`, and provider error
  metadata before `LLMDecisionResult`.
- Add regression test where the model echoes a secret-like prompt string in
  rationale and assert result metadata does not contain it.

### H2 - Authority/tool/organ detection in `LLMDecisionResultValidator` is shallow

Severity: High

File:

- `sentinel/agent/model_execution/validator.py`

Observed code:

- `_AUTHORITY_EXPANSION_FIELDS` is checked only against top-level keys in
  `response.content`.
- The scan is not recursive.
- The scan is not case-insensitive.
- `decision` is not constrained to an approved decision enum.
- Evidence refs are not verified against the mission evidence set.

Proof snippet result:

```text
nested_authority_expansion_detected= False
nested_success= True
```

The proof used a valid top-level schema plus nested:

```json
{"proposal": {"tool_calls": [{"name": "send_email"}]}}
```

The validator returned `SUCCESS_VALIDATED`.

Impact:

Model output still cannot execute tools today, so this is not immediate
execution authority bypass. But it is a certification honesty bug: the result
can be marked success while containing nested action/tool/organ intent.

Required fix direction:

- Recursively scan model content for forbidden authority, tool, organ, secret,
  credential, browser mutation, send, spend, trading, and shell indicators.
- Make the scan case-insensitive and path-aware.
- Add allowed decision enum or controlled decision vocabulary.
- Treat unknown/nested action proposal content as non-success or proposal-only
  metadata, not `SUCCESS_VALIDATED`.

### H3 - Provider error diagnostics can store raw provider error message text

Severity: High

File:

- `sentinel/agent/model_execution/openai_compatible.py`

Observed code:

```text
diagnostic["provider_error_message"] = str(error.get("message", ""))[:240]
```

Proof snippet result:

```text
{'http_status': 429, 'provider_error_type': 'rate_limit', 'provider_error_code': 'x', 'provider_error_message': 'bad request around prompt SENTINEL_AUDIT_PROMPT_ECHO'}
raw_message_persisted= True
```

Impact:

Provider error bodies can echo prompts, request fragments, account details, or
other sensitive data. The current code stores the raw provider error message
instead of hashing or sanitizing it.

Required fix direction:

- Store `provider_error_message_hash`.
- Optionally store a redacted/truncated class if passed through the same
  sanitizer used for context payloads.
- Add tests where provider error echoes prompt text and assert no raw prompt is
  stored.

### H4 - Model execution budget and retry policies are metadata, not enforcement

Severity: High

Files:

- `sentinel/agent/model_execution/policy.py`
- `sentinel/agent/model_execution/coordinator.py`
- `sentinel/agent/runtime.py`

Observed code:

- `ModelExecutionBudgetPolicy` exists.
- `ModelRetryPolicy` exists.
- `RealModelRequest` stores policy ids.
- Coordinator does not enforce model budget.
- Coordinator does not retry based on retry policy.
- Runtime's `_default_model_execution_policies` returns policies, but execution
  uses coordinator-level timeout only.

Impact:

The system appears to have budget/retry policy objects, but the real execution
path does not enforce those policies. This matters before any iterative LLM
loop, because repeated model calls can multiply cost and latency without a true
mission/action budget closure.

Required fix direction:

- Coordinator must receive or resolve actual policy objects, not only request
  ids.
- Before provider call, reject when request token/cost estimate exceeds policy.
- Retry policy must be explicit, bounded, and only for safe outcome classes.
- Receipt must record actual attempts and the actual timeout/retry policy used.

## Medium Findings

### M1 - Provider registry silently overwrites duplicate provider ids

Severity: Medium

File:

- `sentinel/agent/model_execution/registry.py`

Proof snippet result:

```text
duplicate_overwrite_provider_class= Q
```

Impact:

If dynamic or test registration registers a second provider with the same id,
the previous provider is silently replaced. This is not currently exposed as a
runtime plugin system, but it is unsafe for future provider expansion.

Required fix direction:

- Reject duplicate provider ids unless an explicit replace flag is used in a
  test-only helper.

### M2 - Provider catalog does not constrain runtime execution

Severity: Medium

Files:

- `sentinel/agent/model_execution/catalog.py`
- `sentinel/agent/model_execution/provider_profiles.py`
- `sentinel/agent/model_execution/registry.py`
- `sentinel/agent/model_execution/coordinator.py`

Observed reality:

- Catalog has rich metadata and tests.
- Registry/coordinator do not consult the catalog in normal execution.
- Provider objects provide `supported_models`, but catalog status, backend
  profile, diagnostic-only state, timeout profile, and recommendation metadata
  do not directly constrain execution.

Impact:

The catalog is valuable but currently advisory. Future code could register a
provider object that contradicts catalog state unless an integration layer
enforces catalog constraints.

Required fix direction:

- Add a catalog-backed provider registration/build step.
- Coordinator should reject providers/models not enabled by explicit user
  provider contract and catalog policy.

### M3 - Provider profile success commit is stale after history cleanup

Severity: Medium

File:

- `sentinel/agent/model_execution/provider_profiles.py`

Observed code:

```text
success_commit="39888c1"
```

But history cleanup squashed provider adapter work into:

```text
187d251 runtime: add real model provider adapters
```

and runtime validation later appears in:

```text
9647993 test: validate real runtime model execution
```

Impact:

This can mislead future audits and state-lock automation.

Required fix direction:

- Replace with current durable evidence commit set or mark as historical
  pre-squash evidence hash.

### M4 - State lock and README still underclaim runtime model execution

Severity: Medium

Files:

- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `README.md`

Observed facts:

- `CURRENT_STATE_LOCK.md` still says runtime model execution is `NOT_WIRED`.
- `README.md` still says runtime model execution wiring is `NOT_WIRED`.
- Later commits prove runtime wiring, real runtime validation, provider catalog,
  and OpenAI-compatible base hardening.

Impact:

This is a project truth defect. Future agents may redo completed work or choose
the wrong next phase.

Required fix direction:

- Do a state truth consolidation pass after this audit is accepted.

## Logic Review By Power Surface

### LLM power

Real power:

- Runtime can execute a real selected model through a coordinator and validate
  an `LLMDecisionResult`.

Weakness:

- Provider identity is not user-contract selected.
- Result validation is too permissive.
- Durable result metadata can contain raw model rationale.
- Budget/retry policies are not real enforcement.

### Authority power

Real power:

- `MissionAuthorityEnvelope`, `MissionScopeChecker`, `RiskRouter`, FinalGate,
  organ authority, and receipts provide strong separation.

Weakness:

- Some docs imply more current power than code proves.
- Model execution metadata is not yet rich enough for FinalGate to judge model
  result quality beyond safe receipt shape.

### Organ power

Real power:

- Browser and desktop organ trees are large and guarded.
- Desktop L6 blocks shell/process/live host control.
- Browser L6 blocks many mutation and misuse surfaces.

Weakness:

- Product-level organ orchestration remains partial.
- Some organ docs can make broad external action feel closer than runtime proof
  supports.

### Provider power

Real power:

- Groq path is validated.
- Generic OpenAI-compatible base is hardened by tests.
- Catalog records many providers.

Weakness:

- Catalog is not execution authority.
- Provider failure cannot yet be made resilient without fallback policy.
- Diagnostic providers should not be promoted accidentally.

## Findings Ranked For Next Fix Pack

1. Add provider/backend to the user-selected model contract and runtime checks.
2. Split `ModelCallPlan.provider_id` from `backend_id`.
3. Bind credential handle to provider env source before network calls.
4. Sanitize model result text before durable metadata.
5. Recursively scan model output for authority/tool/organ/secret indicators.
6. Enforce model execution budget and retry policy or explicitly remove the
   appearance of enforcement.
7. Reject duplicate provider registry registration.
8. Wire catalog constraints into provider registration/execution.
9. Update state locks and README.
10. Add tests that prove every item above.

## Audit Verdict

Sentinel's architecture is directionally strong, but the current model layer is
not yet robust enough for broad provider expansion or deep model loops. The next
technical pack should be a model execution contract hardening pack, not another
provider adapter pack.
