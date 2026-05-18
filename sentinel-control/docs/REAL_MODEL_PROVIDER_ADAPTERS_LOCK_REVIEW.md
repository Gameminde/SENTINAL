# Real Model Provider Adapters Lock Review

Review date: 2026-05-18

## Accepted Commit

```text
current squashed commit: runtime: add real model provider adapters
pre-squash local evidence hash: 39888c1 runtime: add real model provider adapters
```

## Review Verdict

```text
PACK_B_PROVIDER_ADAPTERS = ACCEPTED_AS_PROVIDER_LAYER_LOCK_CANDIDATE
```

This review accepts Pack B as proof that Sentinel can execute a real sanctioned
provider adapter path without fake success, without durable secret leakage, and
without runtime authority expansion.

It does not accept runtime model execution wiring yet.

## Provider Results

### Groq

```text
provider_id = groq
backend_id = groq_openai_compatible_chat
model_id = openai/gpt-oss-20b
outcome = SUCCESS_VALIDATED
LLMDecisionResult validation = passed
receipt/redaction = passed
fake success = no
```

Groq is the first provider candidate that proved the real provider execution
path through Sentinel's Pack A model execution foundation.

### OpenRouter

```text
provider_id = openrouter
backend_id = openrouter_chat_completions
model_id = deepseek/deepseek-v4-flash:free
status = diagnostic-only
observed outcomes = RATE_LIMIT, TIMEOUT, PROVIDER_ERROR
success overclaim = no
```

OpenRouter remains useful diagnostic evidence, but it is not a lock candidate
until a real `SUCCESS_VALIDATED` path is proven.

### NVIDIA MiniMax

```text
provider_id = nvidia
backend_id = nvidia_openai_compatible_chat
model_id = minimaxai/minimax-m2.7
status = diagnostic-only
observed outcome = TIMEOUT
success overclaim = no
```

NVIDIA MiniMax remains a powerful long-context candidate, but this test pass did
not prove a validated provider result inside Sentinel.

## What Is Proven

```text
ModelCallPlan-compatible request
-> real Groq provider call
-> ProviderModelResponse
-> LLMDecisionResult
-> safe receipt/redaction
```

Specifically proven:

- a real provider call can return usable model content
- model content can validate into `LLMDecisionResult`
- receipt metadata can remain secret-free
- raw prompt is not durably stored
- provider key is not durably stored
- provider output does not execute tools/organs
- provider output does not expand authority

## What Is Not Proven

The following remain unproven and must not be claimed:

- `AgentRuntime.run` real model execution wiring
- FinalGate over real model execution result in runtime
- action token-budget closure
- mission token-budget closure
- production-grade retry/rate-limit policy
- multi-provider fallback policy
- long-running provider stability
- OpenRouter production readiness
- NVIDIA MiniMax production readiness

## Deferral Recommendation

Do not close:

```text
P-C-RUNTIME-01-ACTIONBUDGET-DEFER
P-C-RUNTIME-01-MISSIONBUDGET-DEFER
```

For:

```text
LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER
```

Recommended split:

```text
REAL_PROVIDER_ADAPTER_SUCCESS = CLOSED by Groq evidence
RUNTIME_MODEL_EXECUTION_WIRING = OPEN until Wave 9
```

If the project does not support split deferrals yet, keep the original deferral
open and record Groq as lock-candidate evidence.

## Recommended Next Phase

```text
Pack C / Wave 9 runtime wiring review
```

Recommended next action is review and planning only, not immediate runtime
implementation.

Pack C should answer:

- where `ModelExecutionCoordinator` enters after `ModelCallPlan`
- how default-off behavior stays intact
- how `LLMDecisionResult` is attached to runtime result metadata
- how model execution receipts are referenced
- how FinalGate sees real model execution metadata
- how no tool/organ execution from model output is preserved
- whether `LLM-DECISION-CYCLE-MODEL-EXECUTION-DEFER` can be split

## Safety Confirmation

Confirmed by Pack B scope and tests:

- no provider key committed
- `.env` remains ignored
- no raw Bearer key committed
- no raw prompt durable storage
- no raw provider response durable storage
- no raw `reasoning_details` durable storage
- no tool execution from model output
- no organ execution from model output
- no authority expansion
- no P6U
- no Brain/Science expansion
- no `AgentRuntime.run` modification
- no `CURRENT_STATE_LOCK.md` modification
- no Wave 9 runtime wiring

## Final Lock Position

```text
provider_adapter_layer = LOCK_CANDIDATE_ACCEPTED
runtime_model_execution = NOT_STARTED
current_phase_lock = unchanged
```

Pack B is ready for a docs lock decision or a Pack C/Wave 9 design review. It
should not be used to claim full runtime model execution until runtime wiring is
implemented and verified.
