# NVIDIA MiniMax Provider Diagnostic Audit

Audit date: 2026-05-18

Provider candidate:

```text
provider_id = nvidia
backend_id = nvidia_openai_compatible_chat
model_id = minimaxai/minimax-m2.7
base_url = https://integrate.api.nvidia.com/v1
credential_env = NVIDIA_API_KEY
```

## External Specification Check

NVIDIA's current MiniMax M2.7 reference says:

- Input context length: `204,800` tokens.
- API endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`.
- OpenAI-compatible chat completions shape.
- Model id: `minimaxai/minimax-m2.7`.

The timeout seen in Sentinel is not explained by output budget alone:

- `estimated_output_tokens = 80` timed out.
- `estimated_output_tokens = 200` timed out.
- The prompt was reduced to a tiny strict JSON response.

## Local Diagnostic Results

Sentinel-native NVIDIA adapter:

```text
transport = httpx
NVIDIA_API_KEY = loaded from ignored local .env into process environment only
real provider call ran = yes
latest observed outcome = TIMEOUT
SUCCESS_VALIDATED = not proven
```

Earlier standard-library transport:

```text
transport = urllib
real provider call ran = yes
observed outcome = TIMEOUT
SUCCESS_VALIDATED = not proven
```

OpenAI SDK comparison inside the Sentinel shell:

```text
transport = openai SDK
same base_url/model family
result = command-level timeout before completion
SUCCESS_VALIDATED = not proven in this process
```

User-reported external sample:

```text
transport = openai SDK
model = minimaxai/minimax-m2.7
result = succeeded outside this diagnostic run
```

## Current Root-Cause Hypotheses

Most likely:

1. NVIDIA free/trial endpoint latency or queueing instability.
2. Environment/network/proxy difference between the user's manual script context
   and the Sentinel test process.
3. MiniMax M2.7 route is available but slow enough that non-streaming tests are
   brittle.

Less likely:

1. Output-token budget is too low or too high. Tests timed out at 80 and 200.
2. Reasoning configuration. NVIDIA adapter does not send reasoning fields.
3. Prompt size. The diagnostic prompt is tiny.

## Sentinel Consequence

The adapter should remain skip-safe and non-locking:

```text
NVIDIA provider adapter = IMPLEMENTED_SKIP_SAFE
real provider SUCCESS_VALIDATED = not proven
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER = remains open
```

Do not convert `TIMEOUT`, `RATE_LIMIT`, or `PROVIDER_ERROR` into success. Do not
add fake fallback text.

## Next Diagnostic Options

Before claiming a real backend lock:

1. Run the same Sentinel test from the exact terminal where the user's manual
   OpenAI SDK script succeeds.
2. Add a streaming diagnostic adapter/test in a future narrow pass if NVIDIA's
   free endpoint responds faster with streamed chunks.
3. Try another NVIDIA free model with lower latency as a control provider.
4. Keep `minimaxai/minimax-m2.7` as a long-context candidate, not as the only
   lock blocker.

## Redaction

No raw `NVIDIA_API_KEY`, raw prompt body, raw Authorization header, or raw
provider response body is stored in this audit.
