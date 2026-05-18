# Implementation Plan: Sentinel Real Model Execution Backend

## Current Implementation Status Overlay - 2026-05-18

This task list is retained as historical planning context. The actual repository
state now includes the foundation, provider adapters, runtime wiring, real
runtime validation, provider catalog, and OpenAI-compatible base hardening.

```text
foundation_commit = bcb35d2 runtime: add real model execution foundation
provider_adapter_commit = 187d251 runtime: add real model provider adapters
runtime_wiring_commit = 76ad92e runtime: wire model execution coordinator into agent runtime
real_runtime_validation_commit = 9647993 test: validate real runtime model execution
provider_catalog_commit = 7f0ddcb runtime: add model provider catalog
openai_compatible_base_commit = 4052be9 runtime: harden openai-compatible provider base
```

Current truth:

```text
runtime_model_execution = WIRED
runtime_real_provider_validation = SUCCESS_VALIDATED through AgentRuntime.run
provider_expansion_immediate = NO-GO
next_technical_pack = sentinel-model-execution-contract-hardening
```

Open:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
MODEL_EXECUTION_BUDGET_GOVERNANCE
PRODUCTION_PROVIDER_ROUTING
```

Do not use unchecked historical items below as current state. Use
`CURRENT_STATE_LOCK.md` for current phase truth.

## Overview

This plan is for a future implementation pass. The current task creates this
plan only; it does not implement code.

Anchor state:

```text
previous_phase = SENTINEL_LLM_BACKED_DECISION_CYCLE_LOCKED
runtime_commit = 6861ed4 (runtime: lock llm decision cycle seam)
pre_squash_runtime_evidence = fb526c1 (runtime: wire llm decision frame seam)
pre_squash_docs_evidence    = 0fb5df6 (docs: lock llm decision cycle state)
```

Goal:

```text
ModelCallPlan -> real provider request -> model response -> validated LLMDecisionResult
```

Hard boundaries:

- No fake model backend.
- No fake model response.
- No API key value in repo, docs, tests, events, logs, receipts, or traces.
- Real credentials only through environment variables or scoped credential refs.
- Provider execution disabled/default-off unless explicitly configured.
- No P6U.
- No Brain/Science expansion.
- No new organ.
- No authority expansion.
- No tool/organ execution from model output.
- No action token-budget closure.
- No mission token-budget closure.

## Tasks

- [ ] 0. Wave 0 - Inventory and backend proof
  - [ ] 0.1 Inspect locked decision-cycle seam
    - Read `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`.
    - Locate the `ModelCallPlan` metadata created by the previous phase.
    - Confirm no model execution backend is currently wired.
    - Record insertion point for future model execution after `ModelCallPlan`.
    - Do not modify code.

  - [ ] 0.2 Inspect model-cost and model-contract surfaces
    - Read `sentinel/agent/model_contract.py`.
    - Read `sentinel/agent/model_cost.py`.
    - Read `sentinel/perf/caches/model_call_optimizer.py`.
    - Record how user-selected model and cost profile must bind to execution.
    - Do not modify code.

  - [ ] 0.3 Inspect credential surfaces
    - Read existing credential/ref resolver modules if present.
    - Record whether scoped credential refs are safe to use.
    - If not available, mark credential refs deferred and use environment-only
      design for first implementation.
    - Do not read credential values.

  - [ ] 0.4 Confirm no fake backend path
    - Search for fake provider/model response helpers.
    - Any test stub must remain test-only and must not satisfy real backend
      lock criteria.
    - Record findings in implementation log.

- [ ] 1. Wave 1 - Data models
  - [ ] 1.1 Add request/response/result models
    - Create `sentinel/agent/model_execution/models.py`.
    - Define:
      - `RealModelRequest`
      - `ProviderModelResponse`
      - `LLMDecisionResult`
      - `ModelExecutionOutcome`
    - Include strict fields for hashes, provider IDs, token counts, refusal,
      validation, and redaction state.
    - Do not include raw credential value fields.
    - Do not include raw prompt body in serializable metadata.

  - [ ] 1.2 Add timeout/retry/budget policy models
    - Create `sentinel/agent/model_execution/policy.py`.
    - Define:
      - `ModelTimeoutPolicy`
      - `ModelRetryPolicy`
      - `ModelExecutionBudgetPolicy`
    - Include bounded values and validation.
    - Reject zero or unbounded total timeout.

  - [ ] 1.3 Add unit tests for models
    - Create `tests/test_real_model_execution_backend.py`.
    - Test model validation.
    - Test no raw credential/prompt fields exist on serializable metadata.

- [ ] 2. Wave 2 - Provider interface and registry
  - [ ] 2.1 Define provider protocol
    - Create `sentinel/agent/model_execution/provider.py`.
    - Define `RealModelProvider`.
    - One method only: `execute(request, *, timeout, credential)`.
    - No provider implementation yet unless using a real backend.

  - [ ] 2.2 Define provider registry
    - Create `sentinel/agent/model_execution/registry.py`.
    - Registry defaults disabled/empty.
    - Unknown provider rejected.
    - Disabled provider rejected.
    - Provider metadata contains no secrets.

  - [ ] 2.3 Test registry discipline
    - Unknown provider rejected.
    - Disabled provider rejected.
    - Fake provider marker rejected.
    - User-selected model cannot be silently overridden.

- [ ] 3. Wave 3 - Credential handling
  - [ ] 3.1 Define credential handle
    - Create `sentinel/agent/model_execution/credentials.py`.
    - Define `ProviderCredentialHandle`.
    - Include source type, provider ID, scope list, source ref hash.
    - Do not expose raw secret value.

  - [ ] 3.2 Add environment resolver
    - Resolve configured environment variable at execution time only.
    - Never log or receipt the value.
    - Missing variable returns `MISSING_CREDENTIAL`.
    - Exceptions must not include the value.

  - [ ] 3.3 Add credential redaction tests
    - Assert captured logs/events/receipts/result metadata do not contain raw
      credential-like values.
    - Assert missing credential does not create a fake response.

- [ ] 4. Wave 4 - Request builder
  - [ ] 4.1 Build `RealModelRequest` from `ModelCallPlan`
    - Create `sentinel/agent/model_execution/coordinator.py`.
    - Input:
      - `LLMDecisionFrame`
      - rendered prompt in memory only
      - `ModelCallPlan`
      - `UserModelContract`
      - timeout/retry/budget policies
    - Output:
      - `RealModelRequest`
    - Store prompt hash, not raw prompt body.

  - [ ] 4.2 Add request hash
    - Deterministic hash over sanitized metadata.
    - Exclude raw prompt body and raw credential value.

  - [ ] 4.3 Test request metadata
    - Prompt hash exists.
    - Request hash deterministic.
    - Raw prompt not serialized.
    - Selected model remains user-selected model.

- [ ] 5. Wave 5 - Response validation
  - [ ] 5.1 Add validator
    - Create `sentinel/agent/model_execution/validator.py`.
    - Parse provider output into `LLMDecisionResult`.
    - Reject invalid schema.
    - Reject authority-expanding fields.
    - Redact response text before any durable metadata.

  - [ ] 5.2 Test invalid and refusal paths
    - Provider refusal becomes `PROVIDER_REFUSAL`.
    - Invalid schema becomes `INVALID_RESPONSE_SCHEMA`.
    - Provider error does not become success.
    - No fake fallback response.

- [ ] 6. Wave 6 - Receipt shape
  - [ ] 6.1 Add model execution receipt
    - Create `sentinel/agent/model_execution/receipts.py`.
    - Include request hash, prompt hash, response hash, token/cost metadata,
      timeout/retry metadata, validation status, refusal/error class, trace refs,
      and deterministic receipt hash.
    - No raw prompt body.
    - No raw credential value.

  - [ ] 6.2 Test receipt replay metadata
    - Hash deterministic.
    - Missing or mutated metadata changes receipt hash.
    - Raw prompt/credential forbidden.

- [ ] 7. Wave 7 - Provider execution coordinator
  - [ ] 7.1 Add default-off coordinator
    - Coordinator takes provider registry and credential resolver as optional
      injections.
    - If absent, return disabled/deferred outcome.
    - No fake model response.

  - [ ] 7.2 Execute real provider when configured
    - Select enabled provider.
    - Resolve credential handle.
    - Apply timeout and retry policy.
    - Call provider once per attempt.
    - Validate response.
    - Produce receipt.

  - [ ] 7.3 Preserve no-execution boundaries
    - Do not execute tools.
    - Do not execute organs.
    - Do not start P6U.
    - Do not mutate browser/channel/spend/trading surfaces.

- [ ] 8. Wave 8 - Real provider adapter
  - [ ] 8.1 Choose first sanctioned provider
    - Implement only one real provider adapter first.
    - The adapter must be disabled unless explicitly configured.
    - It must read credentials only from environment or safe credential ref.
    - It must support timeout.
    - It must not log raw prompt, raw response, or credential values.

  - [ ] 8.2 Add skip-safe integration test
    - If configuration is absent, skip with a clear reason.
    - If configuration is present, call the real provider.
    - Fail if a fake response path is used.
    - Assert no raw credential appears in captured logs/events/receipts.

- [ ] 9. Wave 9 - Runtime wiring
  - [ ] 9.1 Wire coordinator after `ModelCallPlan`
    - Modify `AgentRuntime.run` only after the coordinator and tests exist.
    - Execution remains default-off unless coordinator and provider are injected.
    - Missing provider or credential returns deferred/rejected model execution
      metadata, not a fake response.

  - [ ] 9.2 Preserve FinalGate
    - `AgentRunResult` includes sanitized `LLMDecisionResult` metadata and model
      execution receipt refs.
    - FinalGate still certifies terminal result.
    - Model output cannot expand authority.

  - [ ] 9.3 Test default-off compatibility
    - Existing runtime tests pass with no provider configured.
    - `tests/test_llm_backed_decision_cycle.py` still passes.

- [ ] 10. Wave 10 - Safety and proof tests
  - [ ] 10.1 No fake backend tests
    - Fake provider marker rejected.
    - Fake response marker rejected.
    - Missing provider cannot produce success.

  - [ ] 10.2 No leakage tests
    - No raw credential value in logs/events/receipts/traces/result metadata.
    - No raw prompt body in logs/events/receipts/traces/result metadata.
    - No raw unsanitized response body in receipts unless explicitly allowed.

  - [ ] 10.3 No authority expansion tests
    - Model output cannot add tools/actions/organs.
    - Model output cannot change allowed domains, paths, budgets, or credentials.
    - FinalGate rejects authority expansion.

- [ ] 11. Wave 11 - Regression
  - [ ] 11.1 Run targeted model execution tests
    - `python -m pytest tests/test_real_model_execution_backend.py -q`
    - `python -m pytest tests/test_real_model_execution_skip_safe.py -q`

  - [ ] 11.2 Run neighbor tests
    - `python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q`

  - [ ] 11.3 Run performance bench
    - `python -m pytest tests/perf/bench -q`

  - [ ] 11.4 Run broader not-slow sweep
    - `python -m pytest -m "not slow" --ignore=tests/perf/hot_cold/test_phase_b_benchmarks.py -q`

  - [ ] 11.5 Run diff hygiene
    - `git diff --check`

- [ ] 12. Wave 12 - Final lock
  - [ ] 12.1 Update lock report
    - Update `sentinel-control/docs/CURRENT_STATE_LOCK.md` only after tests pass.
    - Record provider implemented or execution still deferred.
    - Record skip-safe provider integration result.
    - Record no raw credential value committed.
    - Record no raw prompt body logged or receipted.
    - Record model execution default-off.
    - Record no P6U, Brain/Science, new organ, channel send, browser mutation,
      spend, payment, trading, or credential-secret access.

  - [ ] 12.2 Deferral truth table
    - Close `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` only if real backend
      implementation and tests prove it.
    - Keep `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` open.
    - Keep `P-C-RUNTIME-01-MISSIONBUDGET-DEFER` open.

  - [ ] 12.3 Commit only after approval
    - Recommended commit message if implementation locks:
      - `runtime: add real model execution backend`

## Stop Conditions

Stop immediately and report if:

- a provider credential value would enter a file, log, event, receipt, trace, or
  test output
- implementation requires a fake provider response
- implementation requires tool or organ execution from model output
- implementation would close action or mission token-budget deferrals
- implementation starts P6U, Brain/Science, channel send, browser mutation,
  spend, payment, trading, or credential-secret access
- real-provider tests cannot be made skip-safe
- a provider adapter cannot enforce timeout and redaction
- any required test fails
