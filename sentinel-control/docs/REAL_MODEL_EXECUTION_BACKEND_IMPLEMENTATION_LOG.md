# Real Model Execution Backend Implementation Log

## Current Status Overlay - 2026-05-18

This log preserves Pack A/B diagnostic history. Later commits have advanced the
system beyond the older "runtime wiring remains out of scope" statements:

```text
runtime_wiring_commit = 76ad92e runtime: wire model execution coordinator into agent runtime
real_runtime_validation_commit = 9647993 test: validate real runtime model execution
provider_catalog_commit = 7f0ddcb runtime: add model provider catalog
openai_compatible_base_commit = 4052be9 runtime: harden openai-compatible provider base
budget_closure_commit = 074ca1c runtime: enforce model execution budgets
```

Current truth:

```text
REAL_PROVIDER_ADAPTER_SUCCESS = CLOSED by Groq provider evidence
RUNTIME_MODEL_EXECUTION_WIRING = CLOSED by Wave 9 runtime validation
runtime_model_execution = WIRED
runtime_real_provider_validation = SUCCESS_VALIDATED through AgentRuntime.run
MODEL_EXECUTION_BUDGET_GOVERNANCE = CLOSED
P-C-RUNTIME-01-ACTIONBUDGET-DEFER = CLOSED
P-C-RUNTIME-01-MISSIONBUDGET-DEFER = CLOSED
provider_expansion_immediate = NO-GO
next_phase = CONTROLLED_LLM_ROLE_LOOP_SPEC
```

Implemented budget truth:

```text
action-level model budget preflight
mission-level model budget ledger
post-response budget overrun downgrade to BUDGET_REJECTED
safe budget summaries on ModelExecutionOutcome and runtime metadata
FinalGate model budget metadata contract
```

Still open:

```text
PRODUCTION_PROVIDER_ROUTING
fallback_routing = NOT_STARTED / NOT_APPROVED
AUTO_model_routing = NOT_STARTED / NOT_APPROVED
```

Historical notes below that say runtime wiring is out of scope are accurate for
their original pack, but no longer describe the current repository state.

## Pack A Status

`real_model_execution_backend_foundation = STRUCTURAL_READY`

Pack A implements the local model execution foundation only:

- Wave 0: inventory/backend boundary confirmed by implementation scope.
- Wave 1: data models for request, response, result, outcome, receipt, credentials, timeout, retry, and budget policies.
- Wave 2: provider protocol and disabled-by-default registry.
- Wave 3: environment credential resolver shape with secret-free handles.
- Wave 4: request builder from `ModelCallPlan`, `LLMDecisionFrame`, prompt text in memory, user model contract, and policies.
- Wave 5: provider response validator into `LLMDecisionResult`.
- Wave 6: deterministic model execution receipt shape.
- Wave 7.1: default-off coordinator.
- Wave 7.2: successful provider execution path remains deferred.
- Wave 7.3: no-execution boundaries for authority expansion and tool/organ execution.

## Boundaries Held

- No real provider adapter implemented.
- No real provider SDK imported.
- No real provider network call implemented.
- No API key requested, added, logged, or stored.
- No `.env` or environment file created or modified.
- No `AgentRuntime.run` wiring.
- No P6U work.
- No Brain/Science work.
- No new organ.
- No tool or organ execution from model output.
- No authority expansion.
- No fake backend accepted.
- No fake model response accepted as success.

## Redaction And Receipt Rules

- Request metadata stores `prompt_hash`, not the raw prompt body.
- Credential handles store provider, source type, source ref hash, and scopes only.
- Receipts store request, prompt, and response hashes plus sanitized model metadata.
- Receipts exclude raw prompt, raw credential values, and raw unsanitized response bodies.

## Open Deferrals

- `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` remains open.
- `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` remains open.
- `P-C-RUNTIME-01-MISSIONBUDGET-DEFER` remains open.

## Verification

Targeted Pack A verification:

```bash
python -m pytest tests/test_real_model_execution_backend.py -q
```

Result:

```text
12 passed
```

Additional required verification should be run before any commit:

```bash
python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q
git diff --check
git status --short --untracked-files=all
```

## Pack B Status

`openrouter_deepseek_provider_adapter = IMPLEMENTED_SKIP_SAFE`

Pack B implements Wave 8 only:

- OpenRouter chat-completions provider adapter.
- `provider_id = openrouter`
- `backend_id = openrouter_chat_completions`
- `default_model_id = deepseek/deepseek-v4-flash:free`
- `base_url = https://openrouter.ai/api/v1`
- `credential_env = OPENROUTER_API_KEY`
- Skip-safe real-provider integration test.

## Pack B Boundaries Held

- No `AgentRuntime.run` wiring.
- No Wave 9 runtime wiring.
- No P6U work.
- No Brain/Science work.
- No new organ.
- No provider SDK imported.
- Provider uses the standard-library HTTP client.
- No API key stored, logged, receipted, or written to docs.
- No `.env` file created or modified.
- No raw prompt stored in serializable metadata or receipts.
- No raw reasoning details stored in receipts, logs, traces, or durable metadata.
- No raw provider response stored in receipts.
- No fake backend accepted.
- No fake response accepted as success.
- No tool or organ execution from model output.
- No authority expansion.

## Pack B Reasoning Handling

The OpenRouter adapter requests:

```json
{"reasoning": {"exclude": true, "effort": "high"}}
```

If `reasoning`, `reasoning_content`, or `reasoning_details` appears anyway,
the adapter treats it as sensitive provider output and keeps only:

- `reasoning_enabled`
- `reasoning_excluded_requested`
- `reasoning_present`
- `reasoning_hash`

## Pack B Verification

Current local environment:

```text
OPENROUTER_API_KEY = absent
```

Targeted Pack B verification:

```bash
python -m pytest tests/test_real_model_execution_openrouter.py -q
```

Result:

```text
7 passed, 1 skipped
```

The skipped test is the real OpenRouter call when `OPENROUTER_API_KEY` is
absent in the process environment.

Manual real-provider attempt:

```text
OPENROUTER_API_KEY = present only as process environment variable
result = provider returned RATE_LIMIT
real model success = not proven
raw key durable leakage = not observed
raw prompt durable leakage = not observed
```

The real-provider test now treats provider-side `RATE_LIMIT`, `TIMEOUT`, and
`PROVIDER_ERROR` as honest non-locking provider outcomes after verifying receipt
redaction. It does not convert those outcomes into success.

## Pack B Provider-Error Diagnostic

Diagnostic pass:

```text
OPENROUTER_API_KEY = loaded from ignored local .env into process environment only
real provider call ran = yes
request variants tried = reasoning effort+exclude, reasoning exclude-only, no reasoning
latest observed provider outcome = PROVIDER_ERROR
previous observed provider outcome = TIMEOUT
SUCCESS_VALIDATED = not proven
```

Sanitized findings:

- Missing-credential skip path is not the blocker once `.env` is loaded.
- Reasoning shape is not proven to be the blocker because fallback variants also
  return non-success provider outcomes.
- The adapter now captures sanitized HTTP diagnostics when OpenRouter returns an
  HTTP error: status code, provider error type/code/message when available, or
  body hash otherwise.
- No raw Authorization header, API key, prompt, reasoning details, or provider
  response body is durably stored.

Current interpretation:

```text
provider route unavailable, provider-side error, timeout, or rate-limit remains
possible. No fake success is allowed. LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
remains open.
```

## NVIDIA MiniMax Provider Candidate

`nvidia_minimax_provider_adapter = IMPLEMENTED_SKIP_SAFE`

NVIDIA candidate:

```text
provider_id = nvidia
backend_id = nvidia_openai_compatible_chat
model_id = minimaxai/minimax-m2.7
base_url = https://integrate.api.nvidia.com/v1
credential_env = NVIDIA_API_KEY
```

Implementation notes:

- Uses `httpx`, which is already declared in `sentinel-core/pyproject.toml`.
- Does not use the OpenAI SDK directly.
- Reads `NVIDIA_API_KEY` only from process environment at execution time.
- Keeps `ProviderCredentialHandle` secret-free.
- Returns Pack A `ProviderModelResponse`.
- Does not import validator or receipt builder inside the provider.
- Does not wire `AgentRuntime.run`.
- Does not start Wave 9.

Real-provider attempt:

```text
NVIDIA_API_KEY = loaded from ignored local .env into process environment only
real provider call ran = yes
latest observed provider outcome = TIMEOUT
SUCCESS_VALIDATED = not proven
raw key durable leakage = not observed
raw prompt durable leakage = not observed
```

Current interpretation:

```text
The local Sentinel-native httpx adapter reaches the NVIDIA route but has not yet
obtained a validated model response before timeout. The user's separate OpenAI
SDK sample indicates the provider/model can work outside this adapter, so this
is an adapter/runtime transport behavior to continue diagnosing before any lock
claim. No fake success is allowed.
```

## Groq Provider Candidate

`groq_provider_adapter = REAL_SUCCESS_VALIDATED`

Groq candidate:

```text
provider_id = groq
backend_id = groq_openai_compatible_chat
model_id = openai/gpt-oss-20b
base_url = https://api.groq.com/openai/v1
credential_env = GROQ_API_KEY
```

Implementation notes:

- Uses `httpx`, which is already declared in `sentinel-core/pyproject.toml`.
- Reads `GROQ_API_KEY` only from process environment at execution time.
- Keeps `ProviderCredentialHandle` secret-free.
- Returns Pack A `ProviderModelResponse`.
- Does not import validator or receipt builder inside the provider.
- Does not wire `AgentRuntime.run`.
- Does not start Wave 9.

Real-provider result:

```text
GROQ_API_KEY = loaded from ignored local .env into process environment only
real provider call ran = yes
provider outcome = SUCCESS_VALIDATED
LLMDecisionResult validation = passed
receipt redaction = passed
raw key durable leakage = not observed
raw prompt durable leakage = not observed
```

Current interpretation:

```text
Groq is the first provider candidate in this sequence to prove a real
ModelCallPlan-compatible provider response can be validated into an
LLMDecisionResult without fake success. Runtime wiring remains out of scope.
```

## Open Deferrals After Pack B

- `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` remains open until real-provider
  integration evidence is run and reviewed.
- `P-C-RUNTIME-01-ACTIONBUDGET-DEFER` remains open.
- `P-C-RUNTIME-01-MISSIONBUDGET-DEFER` remains open.
