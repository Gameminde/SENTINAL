# Real Model Provider Test Problem Report

Report date: 2026-05-18

Scope:

```text
sentinel-real-model-execution-backend
Pack B provider candidates:
  - OpenRouter DeepSeek
  - NVIDIA MiniMax
  - Groq GPT-OSS
```

This report records problems found during real-provider testing. It contains no
API keys, raw Authorization headers, raw prompts, raw provider responses, or
raw reasoning details.

## Executive Verdict

```text
Groq = first SUCCESS_VALIDATED provider candidate.
OpenRouter = real route reached, but non-locking provider outcomes.
NVIDIA MiniMax = real route reached, but timeout in Sentinel test process.
```

The critical product lesson:

```text
Sentinel cannot treat "OpenAI-compatible" as "production-ready".
Every provider needs provider-specific timeout, error, response, rate-limit,
and redaction proof before runtime wiring.
```

## Provider Matrix

| Provider | Model | Real call | Latest outcome | Lock value |
| --- | --- | ---: | --- | --- |
| OpenRouter | `deepseek/deepseek-v4-flash:free` | yes | `PROVIDER_ERROR` / earlier `RATE_LIMIT` and `TIMEOUT` | diagnostic only |
| NVIDIA | `minimaxai/minimax-m2.7` | yes | `TIMEOUT` | diagnostic only |
| Groq | `openai/gpt-oss-20b` | yes | `SUCCESS_VALIDATED` | strongest lock candidate |

## Shared Problems Found

### 1. Secret Handling Is Easy To Break

Problem:

- Provider credentials were repeatedly discussed during testing.
- A provider key briefly entered an untracked adapter constant because a prompt
  field was labeled as `credential_env` while containing a key value.

Correction:

- Scans caught the issue before staging/commit.
- The code was corrected to use environment variable names only:
  - `OPENROUTER_API_KEY`
  - `NVIDIA_API_KEY`
  - `GROQ_API_KEY`
- `.env` is ignored and local-only.

Sentinel rule:

```text
Provider keys must enter only process environment.
Provider keys must never enter code, docs, tests, receipts, traces, or lock docs.
```

### 2. OpenAI-Compatible Does Not Mean Uniform Behavior

Problem:

- OpenRouter, NVIDIA, and Groq all expose OpenAI-compatible chat completion
  shapes, but behavior diverged strongly:
  - OpenRouter returned provider errors/rate limits/timeouts.
  - NVIDIA timed out in Sentinel's process.
  - Groq returned a validated result.

Sentinel rule:

```text
Provider adapters must be proven individually.
Compatibility wrappers are not enough for lock.
```

### 3. Free-Tier Routes Are Not Stable Lock Evidence

Problem:

- OpenRouter free model route returned non-locking outcomes.
- NVIDIA free/trial route timed out even with small prompts and conservative
  output caps.
- These may be quota, routing, queueing, latency, or provider availability
  issues.

Sentinel rule:

```text
Free-tier success can prove a path.
Free-tier failure must remain a provider outcome, not a Sentinel failure unless
the adapter mishandles it.
```

### 4. Timeout Policy Must Be Provider-Specific

Problem:

- MiniMax M2.7 timed out with:
  - tiny prompt
  - output budget 80
  - output budget 200
  - long timeout policy
  - httpx transport
  - OpenAI SDK comparison inside Sentinel shell

Interpretation:

- The problem is not simply `estimated_output_tokens`.
- It is likely route latency, queueing, provider behavior, environment/network
  difference, or free-tier instability.

Sentinel rule:

```text
Provider timeout defaults must be configurable profiles, not hardcoded truth.
Long-context models may need streaming or separate latency policy.
```

### 5. Reasoning Output Must Be Treated As Sensitive

Problem:

- OpenRouter can expose reasoning fields such as `reasoning`,
  `reasoning_content`, or `reasoning_details`.

Correction:

- The OpenRouter adapter requests reasoning exclusion.
- If reasoning appears anyway, it stores only:
  - `reasoning_enabled`
  - `reasoning_excluded_requested`
  - `reasoning_present`
  - `reasoning_hash`

Sentinel rule:

```text
Do not durable-store raw reasoning_details by default.
```

### 6. Provider Error Diagnostics Need Sanitized Metadata

Problem:

- Initial `PROVIDER_ERROR` was too vague to diagnose.

Correction:

- Adapters now capture sanitized HTTP diagnostics:
  - status code
  - provider error type/code/message when available
  - body hash otherwise

Sentinel rule:

```text
Diagnostics should explain failures without leaking keys, prompts, or raw
provider bodies.
```

### 7. Tests Must Separate Real Success From Honest Non-Success

Problem:

- A provider call can be real but still return `RATE_LIMIT`, `TIMEOUT`,
  `PROVIDER_ERROR`, or `INVALID_RESPONSE_SCHEMA`.

Correction:

- Tests treat these as non-locking provider outcomes.
- Tests verify redaction before skipping.
- Tests do not convert provider failures into fake success.

Sentinel rule:

```text
No fake fallback text.
No fake backend.
No fake response accepted as success.
```

## Provider-Specific Findings

## OpenRouter DeepSeek

Candidate:

```text
provider_id = openrouter
backend_id = openrouter_chat_completions
model_id = deepseek/deepseek-v4-flash:free
base_url = https://openrouter.ai/api/v1
```

Findings:

- Adapter implemented with standard-library HTTP.
- Missing credential path works.
- Request/receipt redaction works.
- Reasoning exclusion and reasoning redaction are implemented.
- Real provider call reached OpenRouter.
- Observed outcomes:
  - `RATE_LIMIT`
  - `TIMEOUT`
  - `PROVIDER_ERROR`

Problems:

- Free model route is not reliable enough for lock evidence.
- Reasoning config was tested with fallbacks:
  - effort high + exclude
  - exclude only
  - no reasoning
- Reasoning shape was not proven to be the root cause.

Status:

```text
OpenRouter = diagnostic provider candidate, not lock candidate yet.
```

## NVIDIA MiniMax

Candidate:

```text
provider_id = nvidia
backend_id = nvidia_openai_compatible_chat
model_id = minimaxai/minimax-m2.7
base_url = https://integrate.api.nvidia.com/v1
```

Findings:

- NVIDIA docs confirm the model and endpoint.
- NVIDIA docs list a large input context length.
- Adapter implemented with `httpx`, already declared in project dependencies.
- Missing credential path works.
- Request/receipt redaction works.
- Real provider call reached NVIDIA.
- Observed outcome:
  - `TIMEOUT`

Problems:

- Timeout persisted with:
  - prompt minimized to strict JSON
  - output budget reduced to 80
  - output budget tested at 200
  - timeout increased
  - httpx transport
  - OpenAI SDK comparison inside Sentinel shell
- User-reported external OpenAI SDK sample succeeded outside this diagnostic
  context, suggesting an environment, queueing, free-tier, or transport-context
  difference.

Status:

```text
NVIDIA MiniMax = powerful long-context candidate, not reliable lock candidate yet.
```

Recommended follow-up:

- Test streaming mode.
- Test from exact terminal/context where external SDK sample succeeds.
- Try a smaller NVIDIA model as latency control.
- Keep MiniMax as long-context candidate, not sole backend blocker.

## Groq GPT-OSS

Candidate:

```text
provider_id = groq
backend_id = groq_openai_compatible_chat
model_id = openai/gpt-oss-20b
base_url = https://api.groq.com/openai/v1
```

Findings:

- Adapter implemented with `httpx`.
- Missing credential path works.
- Request/receipt redaction works.
- Real provider call ran with `GROQ_API_KEY` loaded from ignored local `.env`.
- Provider returned a response that validated into `LLMDecisionResult`.
- Receipt redaction passed.

Status:

```text
Groq = first real provider SUCCESS_VALIDATED candidate.
```

Important limitation:

- This proves provider execution foundation, not runtime wiring.
- `AgentRuntime.run` remains untouched.
- Wave 9 remains unstarted.

## Lock Implications

What is proven:

```text
ModelCallPlan-compatible request -> real Groq provider call ->
ProviderModelResponse -> LLMDecisionResult -> receipt redaction
```

What is not proven:

```text
AgentRuntime.run real model execution wiring
FinalGate over real model execution result at runtime
action token budget closure
mission token budget closure
long-running provider stability
multi-provider fallback policy
production-grade retry/rate-limit policy
```

Deferrals remain open:

```text
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```

`LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` should not be closed automatically.
It can be reviewed for closure only after the team accepts Groq as the first
sanctioned provider and decides whether Wave 9 runtime wiring is allowed.

## Recommended Next Steps

1. Treat Groq as the first lock candidate.
2. Keep OpenRouter and NVIDIA as diagnostic candidates.
3. Do not wire runtime yet.
4. Commit provider foundation only after review.
5. Next spec/pass should decide:
   - whether Groq closes real provider backend execution
   - whether Wave 9 can wire the coordinator into `AgentRuntime.run`
   - how provider retries/rate limits/latency profiles should be configured
   - whether streaming support is required for NVIDIA/MiniMax

## Safety Confirmation

During provider testing:

- No provider key should be staged or committed.
- `.env` remains ignored.
- No raw prompt should enter serializable metadata.
- No raw provider response body should enter receipts.
- No raw reasoning details should enter receipts.
- No fake provider response should count as success.
- No model output should execute tools or organs.
- No model output should expand authority.
