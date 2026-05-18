# OpenRouter DeepSeek Provider Readiness Audit

Audit date: 2026-05-18

Pack A anchor:

```text
9222dec runtime: add real model execution foundation
real_model_execution_backend_foundation = STRUCTURAL_READY
```

Pack B candidate:

```text
provider_id = openrouter
backend_id = openrouter_chat_completions
model_id = deepseek/deepseek-v4-flash:free
base_url = https://openrouter.ai/api/v1
credential_env = OPENROUTER_API_KEY
```

This audit is docs-only. No provider call was made. No API key value is recorded
in this file. Any key value supplied outside the repo was intentionally not used,
not stored, and not echoed.

## Source Checks

Primary sources checked:

- OpenRouter chat completions API reference:
  https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request
- OpenRouter API overview:
  https://openrouter.ai/docs/api/reference/overview
- OpenRouter quickstart:
  https://openrouter.ai/docs/quickstart
- OpenRouter reasoning tokens guide:
  https://openrouter.ai/docs/use-cases/reasoning-tokens
- OpenRouter DeepSeek V4 Flash free model page:
  https://openrouter.ai/deepseek/deepseek-v4-flash%3Afree

## 1. Provider Identity

Pack B should bind exactly one provider candidate:

```text
provider_id = openrouter
backend_id = openrouter_chat_completions
default_model_id = deepseek/deepseek-v4-flash:free
base_url = https://openrouter.ai/api/v1
chat_endpoint = /chat/completions
credential_env = OPENROUTER_API_KEY
```

The effective request URL is:

```text
https://openrouter.ai/api/v1/chat/completions
```

The OpenRouter model page currently lists
`deepseek/deepseek-v4-flash:free` as a free DeepSeek V4 Flash variant. Treat
availability, context size, free quota, and routing as provider-side mutable
facts, not Sentinel hardcoded truth.

## 2. API Compatibility

OpenRouter exposes an OpenAI-compatible chat-completions endpoint. The OpenAI
SDK can be pointed at `base_url = https://openrouter.ai/api/v1`, but Sentinel
Pack B should prefer a narrow adapter boundary around the already-created
`RealModelProvider` protocol rather than coupling the runtime to a vendor SDK.

Expected request shape:

```json
{
  "model": "deepseek/deepseek-v4-flash:free",
  "messages": [
    {"role": "system", "content": "<sentinel system guardrails>"},
    {"role": "user", "content": "<rendered prompt in memory only>"}
  ],
  "temperature": 0,
  "max_completion_tokens": 1024,
  "reasoning": {
    "effort": "high",
    "exclude": true
  }
}
```

Minimum required headers:

```text
Authorization: Bearer <OPENROUTER_API_KEY value from environment only>
Content-Type: application/json
```

Optional attribution headers may exist in OpenRouter docs, but Pack B should
defer them unless Sentinel has a tracked product/app identity policy:

```text
HTTP-Referer
X-OpenRouter-Title
```

Expected non-streaming response fields:

```text
id
object
created
model
choices[]
choices[].finish_reason
choices[].message.role
choices[].message.content
usage.prompt_tokens
usage.completion_tokens
usage.total_tokens
```

OpenRouter normalizes chat completion responses across providers. Sentinel
should still validate the response strictly because provider routing, fallback,
and model-specific behavior can change.

## 3. Reasoning Compatibility

OpenRouter supports a unified `reasoning` request parameter for models that
support reasoning. The DeepSeek V4 Flash free model page says reasoning efforts
`high` and `xhigh` are supported.

Pack B recommendation:

```json
{
  "reasoning": {
    "effort": "high",
    "exclude": true
  }
}
```

Rationale:

- Reasoning can be enabled for the model.
- `exclude: true` asks the provider not to return reasoning tokens.
- Sentinel should not durable-store chain-of-thought-like provider output.
- If a provider still returns `reasoning`, `reasoning_content`, or
  `reasoning_details`, the adapter must treat it as sensitive provider output.

Receipt/log/trace rule:

```text
do not store raw reasoning
do not store raw reasoning_details
do not store raw reasoning_content
record only:
  reasoning_enabled: bool
  reasoning_excluded_requested: bool
  reasoning_present: bool
  reasoning_hash: optional hash over redacted in-memory field
```

`reasoning_details` should be explicitly redacted/deferred in Sentinel receipts
by default. Pack B should not preserve raw reasoning blocks across turns. That
can be revisited only in a future spec with explicit evidence, redaction,
budget, and authority rules.

## 4. Pack B Adapter Scope

Allowed Pack B scope:

- Implement one OpenRouter adapter only.
- Keep adapter disabled/default-off unless explicitly configured.
- Use `provider_id = openrouter`.
- Use `backend_id = openrouter_chat_completions`.
- Read credential only from `OPENROUTER_API_KEY` at execution time.
- Use `RealModelRequest` as the only input.
- Return `ProviderModelResponse` only.
- Preserve user-selected model exactly.
- Enforce timeout policy.
- Validate response through existing Pack A validator.
- Produce Pack A receipt shape with hashes and sanitized metadata.
- Add skip-safe integration tests.

Forbidden in Pack B:

- No `AgentRuntime.run` wiring.
- No P6U.
- No new organ.
- No tool execution.
- No organ execution.
- No authority expansion.
- No silent model override.
- No durable raw prompt body.
- No durable raw response body unless sanitized and explicitly allowed.
- No raw `reasoning_details` in receipts, logs, traces, or lock docs.
- No fake backend satisfying real provider tests.
- No fake model response satisfying real provider tests.

## 5. Credential Strategy

Credential behavior:

```text
source = environment variable
env var = OPENROUTER_API_KEY
read time = execution time only
missing env = MISSING_CREDENTIAL
```

The adapter must never:

- print the key
- log the key
- receipt the key
- include the key in exceptions
- include the key in trace metadata
- include the key in test output
- write the key to an env file
- write the key to docs

The existing Pack A credential handle pattern is correct for Pack B:

```text
provider_id
source_type
source_ref_hash
scopes
```

No raw credential value should enter `ProviderCredentialHandle`,
`RealModelRequest`, `ProviderModelResponse`, `ModelExecutionOutcome`, or
`ModelExecutionReceipt`.

## 6. Request/Response Mapping

Sentinel request mapping:

```text
RealModelRequest.provider_id -> "openrouter"
RealModelRequest.backend_id -> "openrouter_chat_completions"
RealModelRequest.model_id -> user-selected model id
RealModelRequest.prompt_hash -> metadata only
rendered prompt -> in-memory request body only
```

OpenRouter request mapping:

```text
model -> RealModelRequest.model_id
messages -> in-memory prompt render, not durable metadata
max_completion_tokens -> budget/policy bound
temperature -> deterministic default unless user policy says otherwise
reasoning -> explicit Pack B reasoning policy
```

OpenRouter response mapping:

```text
choices[0].message.content -> ProviderModelResponse.raw_text_in_memory_only
choices[0].finish_reason -> finish_reason
usage.prompt_tokens -> usage_input_tokens
usage.completion_tokens -> usage_output_tokens
usage.total_tokens -> metadata only
id -> provider_response_id_hash, not raw durable id if treated as sensitive
model -> model_id
```

Reasoning mapping:

```text
message.reasoning -> sensitive, hash/redact only
message.reasoning_content -> sensitive, hash/redact only
message.reasoning_details -> sensitive, hash/redact only
```

## 7. Test Strategy

Unit tests without API key:

- registry rejects unknown provider
- registry rejects disabled provider
- registry rejects fake provider marker
- request metadata excludes raw prompt
- credential handle excludes raw credential
- OpenRouter adapter refuses missing `OPENROUTER_API_KEY`
- missing credential does not call network
- missing credential does not fake a response
- adapter request builder excludes raw prompt from serializable metadata
- adapter receipt excludes raw prompt, raw credential, and raw reasoning details
- no model override from OpenRouter routing metadata

Skip-safe integration test:

```text
if OPENROUTER_API_KEY is absent:
  skip with clear reason
if OPENROUTER_API_KEY is present:
  call https://openrouter.ai/api/v1/chat/completions
  model = deepseek/deepseek-v4-flash:free
  stream = false
  reasoning.exclude = true
  validate provider response
  fail if fake response is substituted
  prove no key leak in captured logs/results/receipts
  prove no raw prompt leak in serializable metadata
  prove no raw reasoning_details leak in durable artifacts
```

The integration test must not be required to pass without a key. It must be
honest: skip when absent, real provider call when present.

Suggested commands for Pack B after implementation:

```bash
python -m pytest tests/test_real_model_execution_backend.py -q
python -m pytest tests/test_real_model_execution_openrouter.py -q
python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q
git diff --check
git status --short --untracked-files=all
```

## 8. Risks

Free model rate limits:

- The `:free` model may have lower rate limits or variable latency.
- Tests must tolerate provider rate-limit errors as provider outcomes, not
  convert them into fake success.

Free model availability changes:

- `deepseek/deepseek-v4-flash:free` may be unavailable, renamed, quota-limited,
  or temporarily unrouted.
- Sentinel should keep model id configurable, but must not silently override the
  user-selected model.

OpenRouter routing/fallback differences:

- OpenRouter may route the same model id through different underlying providers.
- Provider routing metadata must not become Sentinel authority.

Reasoning leakage:

- Reasoning fields can be returned by default for some models.
- Pack B must request `reasoning.exclude = true` and redact/hash if reasoning
  appears anyway.

Response schema mismatch:

- OpenAI-compatible does not mean Sentinel-compatible.
- The adapter must treat malformed/missing `choices`, missing content, provider
  errors, and unexpected tool-call fields as validation outcomes.

Provider refusal/rate limit/timeout:

- These must map to structured outcome classes.
- They must never produce fallback model text.

Provider-specific `extra_body` behavior:

- If using an OpenAI-compatible SDK later, reasoning may need `extra_body`.
- If using raw HTTP, `reasoning` can be placed in the JSON body directly.
- Pack B should document whichever path it chooses.

## 9. GO/NO-GO Recommendation

Verdict:

```text
GO_WITH_GUARDRAILS
```

Pack B is the right next move because:

- OpenRouter gives a hosted OpenAI-compatible endpoint.
- The selected DeepSeek model exists on OpenRouter and has a free candidate
  route.
- The current Pack A foundation already has provider registry, credential
  handles, request hashing, validation, receipt hashing, and default-off
  coordinator boundaries.

Pack B must remain narrow:

```text
OpenRouter adapter + skip-safe real-provider test only
```

Pack B must not claim full Sentinel model execution lock unless:

- a real OpenRouter call succeeds when `OPENROUTER_API_KEY` is present
- missing key skips or returns `MISSING_CREDENTIAL`
- no fake response path can satisfy real-provider tests
- no raw key, prompt, response, or reasoning details enter durable artifacts
- no runtime wiring is started
- no deferral is closed prematurely

Still open after this audit:

```text
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```

Pack B can close only the first one, and only after Wave 8 real provider adapter
and skip-safe integration evidence are implemented and accepted.
