# Sentinel Defect Risk Register

Status: deep audit companion
Scope: concrete code and logic findings from the defect-oriented review

## Summary

This register separates real defect candidates from general architecture gaps.

| ID | Severity | Finding | Status | Primary path |
| --- | --- | --- | --- | --- |
| C1 | Critical | User-selected provider is not represented in `UserModelContract` | Open | `sentinel/agent/model_contract.py` |
| C2 | Critical | `RealModelRequestBuilder` conflates backend and provider id | Open | `sentinel/agent/model_execution/coordinator.py` |
| C3 | Critical | Provider adapters do not enforce credential-handle/provider binding | Open | `sentinel/agent/model_execution/openai_compatible.py` |
| H1 | High | Raw model rationale can become durable result metadata | Open | `sentinel/agent/model_execution/validator.py` |
| H2 | High | Validator detects authority/tool/organ fields only at top level | Open | `sentinel/agent/model_execution/validator.py` |
| H3 | High | Provider error message is stored raw in diagnostics | Open | `sentinel/agent/model_execution/openai_compatible.py` |
| H4 | High | Model execution budget/retry policies are not enforced | Open | `sentinel/agent/model_execution/coordinator.py` |
| M1 | Medium | Provider registry duplicate ids overwrite silently | Open | `sentinel/agent/model_execution/registry.py` |
| M2 | Medium | Provider catalog does not constrain runtime execution | Open | `sentinel/agent/model_execution/catalog.py` |
| M3 | Medium | Provider profile success commit is stale after squash | Open | `sentinel/agent/model_execution/provider_profiles.py` |
| M4 | Medium | State lock and README underclaim runtime model execution | Open | `CURRENT_STATE_LOCK.md`, `README.md` |

## Reproduction Evidence

### C1 provider not in user contract

Command class: local Python introspection, no provider call.

Observed output:

```text
UserModelContract fields= ['alternative_model_recommendations', 'capability_profile', 'context_budget_policy', 'cost_profile', 'id', 'model_override_attempted', 'quality_expectation', 'selected_model', 'user_selected']
has_provider_id= False
has_backend_id= False
gpt_backend= openai
```

Risk:

Runtime preserves `selected_model`, but provider can be inferred by
`ModelCallOptimizer`. The doctrine says user chooses provider/model.

Required test:

```text
test_runtime_rejects_model_execution_when_provider_not_user_selected
```

### C2 backend/provider conflation

Code fact:

```text
RealModelRequestBuilder.build:
  provider_id = plan.backend
  backend = plan.backend
```

Risk:

Catalog uses both `provider_id` and `backend_id`; request building collapses
them.

Required test:

```text
test_request_builder_keeps_provider_id_and_backend_id_distinct
```

### C3 credential handle mismatch still calls provider

Command class: local Python with mocked `httpx.Client`, no provider call.

Observed output:

```text
call_count= 1
credential_provider_mismatch_rejected= False
```

Risk:

Provider executes if configured env var exists even when the supplied credential
handle belongs to a different provider/env source.

Required test:

```text
test_openai_compatible_rejects_mismatched_credential_handle_without_network
```

### H1 model rationale persists raw model text

Command class: local Python validator proof, no provider call.

Observed output:

```text
success= True
secret_persisted_in_result_json= True
```

Risk:

If model echoes prompt/key-like content in `rationale`, Sentinel persists it in
`LLMDecisionResult`.

Required test:

```text
test_validator_redacts_secret_like_rationale_before_durable_result
```

### H2 nested authority intent passes validation

Command class: local Python validator proof, no provider call.

Observed output:

```text
nested_authority_expansion_detected= False
nested_success= True
```

Risk:

Nested `tool_calls` or `organ_execution` under a proposal object can be marked
`SUCCESS_VALIDATED`.

Required test:

```text
test_validator_recursively_rejects_nested_tool_or_organ_intent
```

### H3 raw provider error text persists

Command class: local Python diagnostic proof, no provider call.

Observed output:

```text
provider_error_message = bad request around prompt SENTINEL_AUDIT_PROMPT_ECHO
raw_message_persisted = True
```

Risk:

Provider error bodies can echo prompts or request data.

Required test:

```text
test_openai_compatible_hashes_provider_error_message_that_echoes_prompt
```

### H4 policies not enforced

Code fact:

- `ModelExecutionBudgetPolicy` exists.
- `ModelRetryPolicy` exists.
- `RealModelRequest` stores policy ids.
- `ModelExecutionCoordinator.execute` does not enforce either policy.

Risk:

The runtime appears to have model budget/retry policy but does not enforce it.

Required tests:

```text
test_coordinator_rejects_request_over_model_execution_budget
test_coordinator_retries_only_configured_retryable_outcomes
test_receipt_records_actual_attempt_count
```

## Strategic Fix Pack Recommendation

Next pack name:

```text
sentinel-model-execution-contract-hardening
```

Scope:

1. User provider/model contract.
2. Provider/backend split in `ModelCallPlan` and `RealModelRequest`.
3. Credential-handle binding enforcement.
4. Model result text sanitizer.
5. Recursive model output authority scanner.
6. Real model execution budget/retry enforcement.
7. Provider registry duplicate rejection.
8. Catalog-backed provider execution constraints.

Do not start:

- new provider adapters;
- fallback routing;
- AUTO model selection;
- tool/organ execution from model output;
- P6U;
- Brain/Science live implementation.

## Why This Matters

Sentinel's strongest principle is not "it can call a model." It is "the model
is powerful intelligence inside a mission-governed authority system." The
findings above are exactly where that principle is currently weakest:

- provider choice is not fully authority-bound;
- model text can leak into durable metadata;
- validation can overclaim success;
- budget/retry policy can look stronger than it is.

Fixing these will raise Sentinel's real power safely. Adding more providers
before fixing them would multiply ambiguity.
