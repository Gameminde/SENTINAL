# Design Document - Sentinel Real Model Execution Backend

## Current Implementation Status Overlay - 2026-05-18

This design mirror began as the docs-only plan for the first sanctioned real
model execution backend. The implementation has since advanced through Pack A,
Pack B, Wave 9, provider catalog, and OpenAI-compatible base hardening.

```text
runtime_model_execution = WIRED
runtime_real_provider_validation = SUCCESS_VALIDATED through AgentRuntime.run
provider_catalog = IMPLEMENTED
openai_compatible_base = HARDENED
model_execution_budget_governance = LOCKED by 074ca1c
provider_expansion_immediate = NO-GO
next_phase = CONTROLLED_LLM_ROLE_LOOP_SPEC
```

Validated chain:

```text
AgentRuntime.run
-> ModelCallPlan
-> ModelExecutionCoordinator
-> Groq provider adapter
-> ProviderModelResponse
-> LLMDecisionResult
-> safe receipt metadata
-> FinalGate-certified AgentRunResult
```

Closed by budget closure:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
MODEL_EXECUTION_BUDGET_GOVERNANCE
```

Still open:

```text
PRODUCTION_PROVIDER_ROUTING
fallback_routing = NOT_STARTED / NOT_APPROVED
AUTO_model_routing = NOT_STARTED / NOT_APPROVED
```

The historical design below remains useful context, but any statement that
model execution is not wired is superseded by this overlay and
`sentinel-control/docs/CURRENT_STATE_LOCK.md`.

## Overview

This design extends the locked LLM-backed decision-cycle seam from planning to
real provider execution.

Locked previous seam:

```text
Context -> LLMDecisionFrame -> PromptRender -> ModelCallPlan
```

This design adds:

```text
ModelCallPlan -> RealModelRequest -> provider.execute(...) -> ProviderModelResponse -> LLMDecisionResult
```

The design is default-off, provider-injected, credential-redacted, and
FinalGate-aware. It never lets model output grant authority or execute tools.

## Current Anchor State

```text
previous_phase = SENTINEL_LLM_BACKED_DECISION_CYCLE_LOCKED
runtime_commit = 6861ed4 (runtime: lock llm decision cycle seam)
pre_squash_runtime_evidence = fb526c1 (runtime: wire llm decision frame seam)
pre_squash_docs_evidence    = 0fb5df6 (docs: lock llm decision cycle state)
```

The previous phase leaves these deferrals open:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
```

This spec may close only `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER`, and only
if a real provider backend is implemented with skip-safe tests. It must not
close action or mission token-budget deferrals.

## Architecture

### Components

```text
AgentRuntime / decision-cycle seam
  -> LLMDecisionFrame
  -> prompt render wrapper
  -> ModelCallPlan
  -> ModelExecutionCoordinator
  -> ModelProviderRegistry
  -> RealModelProvider
  -> ProviderModelResponse
  -> LLMDecisionResultValidator
  -> ModelExecutionReceipt
  -> FinalGate-compatible result metadata
```

### Proposed Files for Future Implementation

This docs-only spec does not create implementation files. A future
implementation should use a narrow file layout:

```text
sentinel/agent/model_execution/__init__.py
sentinel/agent/model_execution/models.py
sentinel/agent/model_execution/provider.py
sentinel/agent/model_execution/registry.py
sentinel/agent/model_execution/credentials.py
sentinel/agent/model_execution/policy.py
sentinel/agent/model_execution/coordinator.py
sentinel/agent/model_execution/validator.py
sentinel/agent/model_execution/receipts.py
sentinel/agent/model_execution/redaction.py
tests/test_real_model_execution_backend.py
tests/test_real_model_execution_skip_safe.py
```

## Provider Interface

The provider interface should be minimal:

```python
class RealModelProvider(Protocol):
    provider_id: str
    backend_id: str
    enabled: bool

    def execute(
        self,
        request: RealModelRequest,
        *,
        timeout: ModelTimeoutPolicy,
        credential: ProviderCredentialHandle,
    ) -> ProviderModelResponse:
        ...
```

Rules:

- `execute(...)` is the only provider call.
- It receives a request envelope and a credential handle.
- It never receives raw mission authority as an authority-granting object.
- It returns raw provider response to the validator in memory only.
- The provider adapter must not log raw prompt, raw response, or credential
  values.

## Provider Registry

The registry owns provider selection:

```python
class ModelProviderRegistry:
    def get_enabled(provider_id: str) -> RealModelProvider: ...
    def register(provider: RealModelProvider) -> None: ...
```

Registry rules:

- Default empty or disabled.
- Unknown provider rejected.
- Disabled provider rejected.
- Provider metadata contains no secrets.
- Provider selection must be compatible with the user-selected model.
- `ModelCallOptimizer` recommendations remain advisory unless the user changes
  the selected model contract.

## Environment and Credential Handling

Credential sources:

```text
1. environment variable reference
2. scoped CredentialRef if existing credential layer exposes a safe read path
```

Credential handle shape:

```python
class ProviderCredentialHandle:
    source_type: Literal["env", "credential_ref"]
    source_ref_hash: str
    provider_id: str
    scopes: list[str]
    expires_at: datetime | None
```

The handle never exposes the raw secret in events, receipts, traces, lock docs,
or tests.

Environment variable design:

- The configuration may name which environment variable to read.
- The implementation must never print the value.
- The implementation must never include the value in exceptions.
- Missing variable yields `MISSING_CREDENTIAL`, not fake response.

## Request Construction

`RealModelRequest` is built only after a real `ModelCallPlan` exists.

Fields:

```text
request_id
mission_id
frame_id
frame_hash
prompt_hash
prompt_text_in_memory_only
selected_model
provider_id
backend_id
timeout_policy
retry_policy
budget_policy
expected_output_schema
trace_refs
```

Metadata may store:

```text
request_hash
prompt_hash
estimated_input_tokens
selected_model
provider_id
backend_id
timeout_ms
retry_limit
```

Metadata must not store:

```text
raw prompt body
raw credentials
raw file/browser/API/artifact bodies
raw provider response body unless sanitized and explicitly allowed
```

## Timeout Policy

`ModelTimeoutPolicy`:

```text
connect_timeout_ms
read_timeout_ms
total_timeout_ms
cancellation_token_ref
```

Rules:

- Total timeout must be bounded.
- Cancellation or authority expiry stops retries.
- Timeout outcome is recorded in receipt metadata.

## Retry Policy

`ModelRetryPolicy`:

```text
max_attempts
retryable_error_classes
backoff_strategy
jitter_enabled
```

Retryable:

```text
temporary provider unavailable
rate limit with bounded retry-after
transient network timeout
```

Non-retryable:

```text
missing credential
disabled provider
unknown provider
invalid response schema
authority expired
budget exceeded
credential revoked
provider refusal
```

## Token and Cost Accounting

Before call:

- estimate prompt input tokens
- compute projected cost from `UserModelContract.cost_profile`
- reject or defer if per-call budget is exceeded

After call:

- read provider token usage when available
- compute actual cost
- record estimated and actual token/cost metadata

This spec does not close:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```

## Provider Response Model

`ProviderModelResponse`:

```text
provider_id
backend_id
model_id
raw_text_in_memory_only
finish_reason
refusal_signal
usage_input_tokens
usage_output_tokens
latency_ms
provider_request_id_hash
provider_response_id_hash
```

Raw text remains in memory only until validation/redaction.

## LLMDecisionResult

`LLMDecisionResult` is the only model output accepted by Sentinel runtime.

Fields:

```text
result_id
mission_id
frame_id
frame_hash
model_id
provider_id
decision
rationale_summary
evidence_refs
confidence
uncertainty
refusal
error_class
validation_passed
redaction_applied
authority_expansion
raw_secret_leakage
```

Rules:

- No tool execution.
- No organ execution.
- No authority grant.
- No browser mutation.
- No channel send.
- No payment/spend/trading.
- No credential access.
- Invalid output becomes rejected/escalated metadata, not execution.

## Validation Schema

The validator should parse provider output into a strict schema:

```json
{
  "type": "object",
  "required": ["decision", "rationale", "evidence_refs"],
  "properties": {
    "decision": {"type": "string"},
    "rationale": {"type": "string"},
    "evidence_refs": {"type": "array", "items": {"type": "string"}},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "uncertainty": {"type": "string"}
  },
  "additionalProperties": false
}
```

If parsing fails:

```text
validation_passed = false
error_class = INVALID_RESPONSE_SCHEMA
no execution
```

## Receipt Shape

`ModelExecutionReceipt`:

```text
receipt_id
mission_id
frame_id
frame_hash
request_hash
prompt_hash
response_hash
provider_id
backend_id
model_id
credential_source_type
credential_source_ref_hash
timeout_ms
attempt_count
retry_count
input_tokens_estimated
input_tokens_reported
output_tokens_reported
estimated_cost_usd
actual_cost_usd
latency_ms
result_id
validation_status
refusal_status
error_class
redaction_status
trace_refs
receipt_hash
```

Never in receipt:

```text
raw prompt body
raw credential value
raw provider credential source value
raw model response body unless sanitized and explicitly allowed
```

## Trace Metadata

Trace metadata may include:

```text
provider_id
model_id
request_hash
prompt_hash
response_hash
token counts
cost
latency
timeout policy ID
retry count
validation status
receipt ID
```

Trace metadata must not include:

```text
raw prompt
raw model response
raw credential
raw request body
raw file/browser/API/artifact body
```

## FinalGate Implications

FinalGate should verify:

- no authority expansion from `LLMDecisionResult`
- no raw secret leakage flag
- receipt hash validity
- terminal result remains inside MissionAuthorityEnvelope

FinalGate should not become:

- model quality judge
- latency-budget gate
- provider router
- cost optimizer

## Refusal and Error Handling

Outcome classes:

```text
SUCCESS_VALIDATED
PROVIDER_REFUSAL
MISSING_CREDENTIAL
DISABLED_BACKEND
UNKNOWN_PROVIDER
TIMEOUT
RATE_LIMIT
BUDGET_REJECTED
INVALID_RESPONSE_SCHEMA
PROVIDER_ERROR
CREDENTIAL_REVOKED
AUTHORITY_EXPIRED
```

None of these may produce fake fallback text.

## Default-Off Behavior

Default runtime:

```text
provider registry absent or empty -> no provider call
provider disabled -> no provider call
credential missing -> no provider call
real-provider test key absent -> test skips, no fake call
```

## Test Strategy

Unit tests:

- provider registry rejects unknown/disabled providers
- provider interface rejects fake provider markers
- request metadata excludes raw prompt and credential values
- response validator rejects invalid schema
- receipt hash deterministic
- receipt excludes raw prompt and credential values

Integration tests:

- default-off runtime does not call provider
- missing credential returns missing credential outcome
- configured provider path invokes real provider adapter only when enabled
- model output becomes `LLMDecisionResult`, not tool execution
- FinalGate sees model result metadata and still certifies terminal result

Skip-safe provider tests:

- skip when required environment variable is absent
- fail if a fake response is substituted
- redact provider request/response diagnostics
- assert no raw credential value appears in captured logs/events/receipts

Regression:

```bash
python -m pytest tests/test_real_model_execution_backend.py -q
python -m pytest tests/test_real_model_execution_skip_safe.py -q
python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q
python -m pytest tests/perf/bench -q
python -m pytest -m "not slow" --ignore=tests/perf/hot_cold/test_phase_b_benchmarks.py -q
git diff --check
```

## Lock Criteria

The future implementation can lock only if:

1. At least one real provider backend exists or model execution remains
   explicitly deferred.
2. No fake backend exists.
3. No fake response exists.
4. Real-provider tests are skip-safe and honest.
5. No raw credential value leaks.
6. No raw prompt body is stored.
7. Raw model response is not receipted unless sanitized and explicitly allowed.
8. User-selected model remains authoritative.
9. Model output cannot execute tools or organs.
10. FinalGate remains terminal certification.
11. Action and mission token-budget deferrals remain open.
12. No P6U, Brain/Science, channel send, browser mutation, spend, payment,
    trading, or credential-secret access is started.
