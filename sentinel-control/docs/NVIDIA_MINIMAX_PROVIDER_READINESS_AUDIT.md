# NVIDIA MiniMax Provider Readiness Audit

Audit date: 2026-05-18

Pack B candidate:

```text
provider_id = nvidia
backend_id = nvidia_openai_compatible_chat
model_id = minimaxai/minimax-m2.7
base_url = https://integrate.api.nvidia.com/v1
credential_env = NVIDIA_API_KEY
```

This audit is docs-only for provider selection. No API key is recorded here.

## Source Checks

Primary sources checked:

- NVIDIA MiniMax M2.7 chat completions API reference:
  https://docs.api.nvidia.com/nim/reference/minimaxai-minimax-m2.7-infer
- NVIDIA MiniMax M2.7 model reference:
  https://docs.api.nvidia.com/nim/reference/minimaxai-minimax-m2.7
- NVIDIA LLM APIs catalog:
  https://docs.api.nvidia.com/nim/reference/llm-apis

The NVIDIA API reference lists `minimaxai/minimax-m2.7` and the
OpenAI-compatible chat completions endpoint under:

```text
https://integrate.api.nvidia.com/v1/chat/completions
```

## Scope Recommendation

Verdict:

```text
GO_WITH_GUARDRAILS
```

Allowed implementation:

- One NVIDIA MiniMax adapter only.
- Default-off outside explicit tests.
- Standard-library HTTP only; no provider SDK required.
- Read `NVIDIA_API_KEY` from ignored local `.env` into process environment.
- Preserve `RealModelRequest -> ProviderModelResponse -> LLMDecisionResult`.
- No `AgentRuntime.run` wiring.
- No P6U.
- No Brain/Science.
- No new organ.
- No fake response.
- No tool or organ execution from model output.

## Request Shape

Expected request body:

```json
{
  "model": "minimaxai/minimax-m2.7",
  "messages": [
    {"role": "user", "content": "<rendered prompt in memory only>"}
  ],
  "stream": false,
  "max_tokens": 200,
  "temperature": 0
}
```

The adapter may use `max_tokens` because NVIDIA's examples and OpenAI-compatible
client path accept it for chat completions.

## Redaction Rules

Durable metadata may include:

- provider id
- backend id
- model id
- request hash
- prompt hash
- response hash
- token counts
- outcome class

Durable metadata must not include:

- raw `NVIDIA_API_KEY`
- raw Authorization header
- raw prompt body
- raw provider response body
- raw model reasoning or hidden chain-of-thought fields

## Test Strategy

Unit tests:

- missing `NVIDIA_API_KEY` returns `MISSING_CREDENTIAL`
- no network call on missing credential
- request body uses the exact user-selected model
- serializable metadata excludes raw prompt and credential
- receipt excludes raw prompt and credential

Skip-safe real integration:

- if `NVIDIA_API_KEY` absent, skip
- if present, call real NVIDIA endpoint
- model = `minimaxai/minimax-m2.7`
- prompt asks for compact JSON only
- validate response through `LLMDecisionResultValidator`
- fail if fake response is substituted
- prove no key or prompt appears in receipt metadata

## Deferrals

Even if the real NVIDIA call succeeds, the following remain open until explicit
lock review:

```text
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```
