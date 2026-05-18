# Provider Implementation Order

Audit date: 2026-05-18

Mode: docs-only implementation-order verdict. No code, provider call, API key,
`.env`, runtime source, test, or state lock change was made by this document.

## Verdict

```text
PROVIDER_CATALOG_IMPLEMENTATION_CAN_START = YES
NEXT_PACK = Provider Catalog Core
AUTO_FALLBACK_ROUTING = OUT_OF_SCOPE
AUTO_MODEL_SELECTION = OUT_OF_SCOPE
PROVIDER_TOOL_EXECUTION = OUT_OF_SCOPE
```

The provider expansion path should start with catalog metadata and validation,
not with another provider adapter. Sentinel has enough evidence to know that
real provider execution works through Groq, but it does not yet have a durable
catalog that can safely encode provider differences.

## Recommended Pack Order

### Pack 1 - Provider Catalog Core

Goal:

```text
static provider catalog
secret-free provider profiles
supported backend/model constraints
recommendation metadata only
no provider calls
```

Files likely involved later:

```text
sentinel/agent/model_execution/catalog.py
sentinel/agent/model_execution/provider_profiles.py
tests/test_model_provider_catalog.py
```

Must prove:

- unknown provider rejected
- disabled provider rejected
- fake provider marker rejected
- catalog contains no secrets
- provider recommendation cannot execute
- selected provider/model remains authoritative
- fallback recommendation cannot execute

### Pack 2 - Generic OpenAI-Compatible Base Hardening

Goal:

```text
shared OpenAI-compatible HTTP request/response base
provider-specific policy profiles
no silent fallback
no provider-specific runtime branches
```

Candidate providers using this base:

```text
groq
openrouter
nvidia
deepseek
mistral
xai
openai_chat
ollama
lmstudio
```

Must prove:

- supported model mismatch rejected
- provider policy controls reasoning fields
- usage mapping is provider-profile driven
- timeouts are provider-profile driven
- raw prompt/response/reasoning never durable
- provider failure cannot fake success

### Pack 3 - Groq Profile Regression

Goal:

```text
keep Groq as first SUCCESS_VALIDATED regression provider
encode Groq profile in catalog
preserve existing runtime provider-agnostic path
```

Why first:

- Groq already produced `SUCCESS_VALIDATED`
- it is the current proof provider for real runtime model execution
- it can keep the pipeline honest while catalog rules are added

Do not:

- hardcode Groq in runtime
- turn Groq into a default provider
- route other provider failures to Groq automatically

### Pack 4 - DeepSeek Direct Compatible Adapter/Profile

Goal:

```text
first new hosted provider after catalog
OpenAI-compatible chat shape
explicit reasoning_content redaction
JSON output validation
```

Why:

- official docs expose a clear chat-completions shape
- `reasoning_content` and usage fields are explicit and testable
- it exercises reasoning redaction more strongly than a plain chat provider

Risks:

- thinking mode can produce sensitive reasoning fields
- JSON mode can run long if prompt does not explicitly request JSON
- model availability/rate limits must be skip-safe

### Pack 5 - Mistral Compatible/Native Profile

Goal:

```text
Mistral chat completions
structured output policy
function calling disabled by Sentinel
guardrail/safety fields treated as provider-specific metadata
```

Why:

- official docs expose clear chat completion and structured output behavior
- useful counterexample to OpenAI-like but not identical behavior

### Pack 6 - Native Provider Adapters

Recommended native order:

```text
openai_responses
anthropic_messages
gemini_generate_content
cohere_chat_v2
```

Why:

- these surfaces have distinct response/content-block structures
- forcing them through a chat-compatible base would hide important safety and
  redaction differences
- they need direct reasoning/thinking redaction policies

### Pack 7 - Diagnostic Providers

Providers:

```text
openrouter
nvidia
```

OpenRouter:

- keep diagnostic until routing/fallback knobs are pinned to "no auto-route"
- require tests that provider failure does not route to another upstream
- require reasoning/details redaction checks

NVIDIA:

- keep diagnostic until timeout/model availability behavior is stable
- require longer timeout profile and model-specific smoke tests
- distinguish hosted Integrate from local/container NIM

### Pack 8 - Local Runtimes

Providers:

```text
ollama
lmstudio
```

Why later:

- local providers need local-server discovery policy
- local model availability is not equivalent to hosted credential availability
- local prompts/responses are still sensitive and must be redacted
- LM Studio and Ollama may expose tools/MCP/local-agent surfaces that Sentinel
  must not bridge

## Generic Base vs Native Adapter Split

### Share Generic OpenAI-Compatible Base

```text
groq
openrouter
nvidia
deepseek
mistral
xai
openai_chat
ollama
lmstudio
```

Condition:

Each provider must have a `ProviderBackendProfile` defining:

- endpoint
- supported request fields
- unsupported request fields
- usage mapping
- reasoning redaction fields
- timeout profile
- retry policy
- structured output support
- tool-call handling policy

### Require Native Adapter

```text
openai_responses
anthropic
google_gemini
cohere
```

Reason:

These providers have native object models or response shapes that should remain
visible to Sentinel's validation and redaction layer.

## Recommended First Provider After Catalog

Primary recommendation:

```text
first_after_catalog = deepseek
backend_id = deepseek_chat_completions
reason = OpenAI-compatible shape plus explicit reasoning redaction requirements
```

Alternate if the project wants the least risk:

```text
first_after_catalog = groq_profile_hardening
reason = already SUCCESS_VALIDATED; best regression anchor
```

Recommended path:

```text
1. implement catalog core
2. encode Groq as validated catalog profile
3. implement shared OpenAI-compatible base hardening
4. add DeepSeek direct profile/adapter as first new hosted provider
```

## What Remains Out Of Scope

```text
automatic fallback routing
automatic model selection
provider marketplace plugins
provider-side tools
tool execution from model output
organ execution from model output
memory provider registration
gateway routes
channels
background provider services
action token budget closure
mission token budget closure
P6U
Brain/Science expansion
```

## Later Verification Commands

When implementation begins, expected commands:

```bash
python -m pytest tests/test_model_provider_catalog.py -q
python -m pytest tests/test_real_model_execution_backend.py -q
python -m pytest tests/test_runtime_model_execution_wiring.py -q -rs
python -m pytest tests/test_llm_backed_decision_cycle.py tests/test_agent_runtime.py -q
git diff --check
git status --short --untracked-files=all
```

No real provider call should be required for Provider Catalog Core. Real provider
tests remain skip-safe and provider-specific.

## Final Recommendation

```text
GO = Provider Catalog Core
NO_GO = new adapter before catalog
NO_GO = runtime fallback router
NO_GO = model auto-selection
```

Sentinel should now add the catalog as a strict metadata and policy layer. That
gives provider expansion a stable spine without weakening the core doctrine:
the user chooses the provider/model, Sentinel preserves that choice, and
provider output remains evidence to validate, not authority to execute.
