# Requirements Document - Sentinel Real Model Execution Backend

## Current Implementation Status Overlay - 2026-05-18

This tracked mirror preserves the original spec text below, but the current
repository truth is newer than the original docs-only creation task.

```text
runtime_model_execution = WIRED
runtime_real_provider_validation = SUCCESS_VALIDATED through AgentRuntime.run
provider_catalog = IMPLEMENTED
openai_compatible_base = HARDENED
provider_expansion_immediate = NO-GO
next_technical_pack = sentinel-model-execution-contract-hardening
```

Closed evidence:

```text
REAL_PROVIDER_ADAPTER_SUCCESS = CLOSED by Groq provider evidence
RUNTIME_MODEL_EXECUTION_WIRING = CLOSED by Wave 9 runtime validation
```

Open:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
MODEL_EXECUTION_BUDGET_GOVERNANCE
PRODUCTION_PROVIDER_ROUTING
```

The pre-squash evidence hashes in the historical text below are retained as
historical local evidence, not current commit anchors.

## Introduction

This specification follows the locked `sentinel-llm-backed-decision-cycle`
phase.

Current locked state:

```text
current_phase = SENTINEL_LLM_BACKED_DECISION_CYCLE_LOCKED
anchor_commit = 6861ed4 (runtime: lock llm decision cycle seam)
pre_squash_runtime_evidence = fb526c1 (runtime: wire llm decision frame seam)
pre_squash_docs_evidence    = 0fb5df6 (docs: lock llm decision cycle state)
```

The previous phase already produces:

```text
Context -> LLMDecisionFrame -> PromptRender -> ModelCallPlan
```

This spec designs the first sanctioned real model execution backend:

```text
ModelCallPlan -> real provider request -> model response -> validated LLMDecisionResult
```

This is a docs-only spec. It does not implement code, tests, runtime wiring, or
provider calls.

## Explicit Non-Goals

- No code implementation in this spec creation task.
- No production source modification.
- No test modification.
- No `CURRENT_STATE_LOCK.md` modification.
- No P6U.
- No Brain/Science expansion.
- No new organ.
- No new product power.
- No action token-budget closure.
- No mission token-budget closure.
- No real tool execution from model output.
- No autonomous multi-agent runtime.
- No channel send.
- No browser mutation.
- No payment, spend, or trading.
- No credential secret access.
- No raw prompt body in logs, receipts, events, traces, or lock docs.
- No raw provider credential values anywhere.
- No fake model response.
- No fake provider backend.

## Glossary

- **Provider backend**: A sanctioned adapter that sends a model request to a
  real configured model provider and returns a provider response.
- **Provider registry**: A deterministic lookup table mapping allowed backend
  IDs to provider implementations and credential requirements.
- **Model execution request**: The sanitized request envelope produced from a
  `ModelCallPlan`, prompt hash, prompt text in memory only, model contract,
  timeout policy, retry policy, and budget policy.
- **LLMDecisionResult**: The validated, sanitized, authority-neutral model
  output contract returned to `AgentRuntime` for future decision handling.
- **Execution receipt**: A metadata receipt proving model request/response
  hashes, provider ID, model ID, token/cost accounting, timeout/retry outcome,
  validation status, and redaction status without storing raw secrets or raw
  prompt body.

## Requirements

### Requirement 1: Docs-Only Spec Boundary

**User Story:** As a Sentinel maintainer, I want this task to create only the
Kiro spec files, so that model execution is designed before runtime code lands.

#### Acceptance Criteria

1. THE task SHALL create only `requirements.md`, `design.md`, and `tasks.md`
   under `.kiro/specs/sentinel-real-model-execution-backend/`.
2. THE task SHALL NOT modify production source.
3. THE task SHALL NOT modify tests.
4. THE task SHALL NOT modify `CURRENT_STATE_LOCK.md`.
5. THE task SHALL NOT stage, commit, or push.
6. THE task SHALL run `git diff --check`.
7. THE task SHALL run `git status --short --untracked-files=all`.

### Requirement 2: Real Backend Only, No Fake Execution

**User Story:** As a Sentinel operator, I want model execution to use only real
sanctioned providers, so that the system never confuses stubs with model
capability.

#### Acceptance Criteria

1. THE implementation SHALL NOT create a fake provider backend.
2. THE implementation SHALL NOT create a fake model response.
3. THE implementation SHALL NOT treat deterministic local role helpers as real
   model execution.
4. THE implementation SHALL require a real provider adapter before closing
   `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER`.
5. IF no real provider is configured, THEN model execution SHALL be skipped or
   rejected with an explicit deferred/unconfigured result, not simulated.

### Requirement 3: Provider Interface

**User Story:** As a Sentinel developer, I want a narrow provider interface, so
that multiple model providers can be configured without leaking secrets or
expanding authority.

#### Acceptance Criteria

1. THE implementation SHALL define a provider protocol for one operation:
   execute a model request and return a provider response.
2. THE provider protocol SHALL accept only a sanctioned request envelope.
3. THE provider protocol SHALL return structured metadata and response content
   for validation.
4. THE provider protocol SHALL NOT receive mission authority objects directly
   unless they are reduced to sanitized policy metadata.
5. THE provider protocol SHALL NOT receive credential values through logs,
   events, receipts, traces, or model metadata.
6. THE provider protocol SHALL support timeout and cancellation.

### Requirement 4: Provider Registry

**User Story:** As a Sentinel reviewer, I want a provider registry, so that
backend selection is explicit and auditable.

#### Acceptance Criteria

1. THE implementation SHALL define a provider registry keyed by provider ID.
2. THE registry SHALL be default-empty or default-disabled.
3. THE registry SHALL reject unknown provider IDs.
4. THE registry SHALL reject providers that are not explicitly enabled.
5. THE registry SHALL NOT allow `ModelCallOptimizer` to silently override the
   user-selected model.
6. THE registry SHALL record provider capability metadata without provider
   secrets.

### Requirement 5: Credential and Environment Handling

**User Story:** As a Sentinel operator, I want provider credentials loaded only
through environment variables or scoped credential refs, so that secrets never
enter repo files or durable traces.

#### Acceptance Criteria

1. THE implementation SHALL support credentials from environment variables.
2. THE implementation MAY support scoped `CredentialRef` resolution when the
   existing credential layer exposes a safe read path.
3. THE implementation SHALL NOT store raw credential values in repo files.
4. THE implementation SHALL NOT store raw credential values in docs, tests,
   logs, events, receipts, traces, or lock reports.
5. THE implementation SHALL redact credential-like values before any diagnostic
   metadata leaves the provider adapter.
6. Tests that require a real provider credential SHALL skip safely when the
   credential is absent.
7. Skip-safe tests SHALL still verify that no fake response is used.

### Requirement 6: Request Construction

**User Story:** As a Sentinel maintainer, I want model requests constructed from
the locked decision-cycle outputs, so that no raw mission dump bypasses
`LLMDecisionFrame`.

#### Acceptance Criteria

1. THE implementation SHALL start from `ModelCallPlan`.
2. THE implementation SHALL use the rendered prompt produced by the locked
   prompt-render path in memory only.
3. THE implementation SHALL store `prompt_hash` and token counts in metadata.
4. THE implementation SHALL NOT store raw prompt body in receipts, events,
   logs, traces, or lock docs.
5. THE implementation SHALL include model ID, provider ID, timeout policy,
   retry policy, request hash, prompt hash, expected output schema, and budget
   envelope in the request metadata.
6. THE implementation SHALL preserve the user-selected model as authoritative.
7. IF the optimizer recommends a different model, THEN the recommendation SHALL
   remain advisory unless the user explicitly selects that model.

### Requirement 7: Timeout and Retry Policy

**User Story:** As a Sentinel operator, I want bounded model calls, so that
provider execution cannot hang or retry unboundedly.

#### Acceptance Criteria

1. THE implementation SHALL define a timeout policy per provider request.
2. THE implementation SHALL define retry limits.
3. THE implementation SHALL classify retryable and non-retryable errors.
4. THE implementation SHALL NOT retry after authority expiry, cancellation, or
   budget exhaustion.
5. THE implementation SHALL record retry count and final outcome in metadata.
6. THE implementation SHALL NOT include raw prompt or raw response bodies in
   retry logs or receipts.

### Requirement 8: Token and Cost Accounting

**User Story:** As a Sentinel operator, I want model calls accounted for before
and after execution, so that model execution remains budget-bound.

#### Acceptance Criteria

1. THE implementation SHALL estimate prompt input tokens before the call.
2. THE implementation SHALL record provider-reported input/output token counts
   when available.
3. THE implementation SHALL compute cost from the selected model cost profile.
4. THE implementation SHALL record estimated and actual cost metadata.
5. THE implementation SHALL reject or defer calls that exceed configured
   per-call budget.
6. THE implementation SHALL NOT close action token-budget deferral.
7. THE implementation SHALL NOT close mission token-budget deferral.

### Requirement 9: Response Validation

**User Story:** As a Sentinel reviewer, I want every model response validated
against an output schema, so that model text cannot directly become authority or
execution.

#### Acceptance Criteria

1. THE implementation SHALL define `LLMDecisionResult`.
2. THE implementation SHALL validate provider responses into
   `LLMDecisionResult`.
3. THE result SHALL include sanitized decision, rationale summary, cited
   evidence refs, uncertainty/confidence metadata, refusal status, and error
   status.
4. THE result SHALL NOT grant tools, actions, organs, browser powers, payment
   powers, channel-send powers, or credential powers.
5. THE result SHALL NOT execute tools.
6. THE result SHALL NOT call organs.
7. IF validation fails, THEN the result SHALL be rejected or escalated without
   execution.

### Requirement 10: Refusal and Error Handling

**User Story:** As a Sentinel operator, I want refusals and provider errors
handled cleanly, so that bad model calls produce traceable outcomes without
pretending success.

#### Acceptance Criteria

1. THE implementation SHALL classify provider refusal, provider error, timeout,
   rate limit, invalid response, budget rejection, missing credential, and
   disabled backend.
2. THE implementation SHALL produce structured error/refusal metadata.
3. THE implementation SHALL NOT retry non-retryable errors.
4. THE implementation SHALL NOT convert provider errors into successful
   decisions.
5. THE implementation SHALL NOT fake a fallback response.
6. THE implementation SHALL support escalation or deferred status when model
   execution cannot complete.

### Requirement 11: Redaction and Trace Metadata

**User Story:** As a Sentinel reviewer, I want traces to prove model execution
without exposing secrets, prompts, or raw bodies.

#### Acceptance Criteria

1. THE implementation SHALL record provider ID, model ID, request hash, prompt
   hash, response hash, token counts, cost, latency, timeout policy, retry
   count, validation status, refusal/error class, and receipt ID.
2. THE implementation SHALL NOT record raw prompt body in trace metadata.
3. THE implementation SHALL NOT record raw credential values in trace metadata.
4. THE implementation SHALL NOT record raw model response body unless the
   response is sanitized and explicitly allowed by the receipt policy.
5. THE implementation SHALL use existing event families where possible.
6. THE implementation SHALL justify any new event type if one is unavoidable.

### Requirement 12: Model Execution Receipt Shape

**User Story:** As a Sentinel maintainer, I want a deterministic receipt shape,
so model calls can be audited without leaking sensitive payloads.

#### Acceptance Criteria

1. THE implementation SHALL define a model execution receipt.
2. THE receipt SHALL include mission ID, frame ID/hash, prompt hash, request
   hash, response hash, provider ID, model ID, backend ID, timeout/retry
   metadata, token/cost metadata, validation verdict, and trace refs.
3. THE receipt SHALL include credential source metadata only as redacted
   source type and scope, not secret value.
4. THE receipt SHALL include deterministic receipt hash.
5. THE receipt SHALL be replay-verifiable from stored metadata and hashes.
6. THE receipt SHALL NOT contain raw prompt body.
7. THE receipt SHALL NOT contain raw credential value.
8. THE receipt SHALL NOT contain raw model response body unless explicitly
   sanitized and allowed.

### Requirement 13: FinalGate Relationship

**User Story:** As a Sentinel reviewer, I want model execution results to remain
under FinalGate, so model output cannot bypass terminal certification.

#### Acceptance Criteria

1. THE implementation SHALL define how `LLMDecisionResult` and model execution
   receipts are presented to FinalGate.
2. THE implementation SHALL NOT make FinalGate evaluate latency budgets or
   model quality scores as authority.
3. THE implementation SHALL require FinalGate-compatible proof that no
   authority expansion occurred.
4. THE implementation SHALL reject final results containing raw secrets.
5. THE implementation SHALL preserve existing `AgentRuntime` terminal
   certification.

### Requirement 14: Default-Off Runtime

**User Story:** As a Sentinel maintainer, I want real model execution disabled
unless explicitly configured, so existing tests and runtime behavior remain
compatible.

#### Acceptance Criteria

1. THE provider registry SHALL default to no enabled provider or disabled
   execution.
2. THE runtime SHALL not call a provider unless configured.
3. Missing provider configuration SHALL not create fake responses.
4. Missing credentials SHALL yield skip/defer/reject behavior, not simulation.
5. Existing default-off runtime behavior SHALL remain compatible when no
   provider backend is injected.

### Requirement 15: Tests and Verification

**User Story:** As a Sentinel maintainer, I want tests that prove real-provider
discipline without requiring credentials on normal CI.

#### Acceptance Criteria

1. THE implementation SHALL include unit tests for provider interface and
   registry behavior.
2. THE implementation SHALL include tests proving no fake backend is accepted.
3. THE implementation SHALL include tests proving no fake response is accepted.
4. THE implementation SHALL include tests proving missing credentials are
   handled without provider calls.
5. THE implementation SHALL include tests proving raw credentials do not appear
   in logs, events, receipts, traces, or result metadata.
6. THE implementation SHALL include tests proving raw prompt body is not stored
   in logs, events, receipts, traces, or lock docs.
7. THE implementation SHALL include skip-safe real-provider integration tests.
8. Real-provider tests SHALL skip when required environment configuration is
   absent.
9. Skip-safe tests SHALL fail if a fake response path is used in place of a
   skipped real provider.
10. THE implementation SHALL run targeted runtime tests, model execution tests,
    Phase F bench tests, and `git diff --check` before lock.

### Requirement 16: Final Lock Criteria

**User Story:** As a Sentinel reviewer, I want a truthful lock report, so that
the model backend is not overstated.

#### Acceptance Criteria

1. THE lock report SHALL state which providers are implemented.
2. THE lock report SHALL state whether any real provider integration test ran
   or skipped.
3. THE lock report SHALL state that no raw credential values were committed.
4. THE lock report SHALL state that no raw prompt body is logged or receipted.
5. THE lock report SHALL state whether model execution is default-off.
6. THE lock report SHALL state that action and mission token-budget deferrals
   remain open.
7. THE lock report SHALL state that no tool/organ execution from model output
   was added.
8. THE lock report SHALL state that no P6U, Brain/Science, channel send,
   browser mutation, spend, payment, trading, or credential-secret work was
   started.
