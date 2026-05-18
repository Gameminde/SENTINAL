# Official Provider Surface Audit

Audit date: 2026-05-18

Mode: docs-only provider catalog audit. No provider was called. No API key,
`.env`, runtime source, tests, or state lock file was modified by this audit.

## Sentinel Constraints Applied

```text
user_selected_model = authoritative
silent_provider_override = rejected
silent_model_override = rejected
automatic_fallback_routing = rejected for this phase
provider_error = honest outcome, not permission to reroute
model_output_executes_tools = no
model_output_executes_organs = no
model_output_grants_authority = no
durable_raw_prompt = no
durable_raw_provider_response = no
durable_raw_reasoning = no
durable_provider_key = no
```

The provider catalog must describe providers, backends, model support, and test
status. It must not become an execution router. Recommendations are metadata
only until an explicit user-selected contract authorizes a provider/model.

## Official Sources Audited

- OpenAI: Responses API, Chat Completions API, Structured Outputs.
  - https://platform.openai.com/docs/api-reference/responses/create
  - https://platform.openai.com/docs/api-reference/chat/create
  - https://platform.openai.com/docs/guides/structured-outputs
- Anthropic Claude: Messages API, examples, streaming, features overview.
  - https://docs.anthropic.com/en/api/messages
  - https://docs.anthropic.com/en/api/messages-examples
  - https://docs.anthropic.com/en/docs/build-with-claude
- Google Gemini: text generation, structured output, function calling, tokens.
  - https://ai.google.dev/gemini-api/docs/text-generation
  - https://ai.google.dev/gemini-api/docs/structured-output
  - https://ai.google.dev/gemini-api/docs/function-calling
  - https://ai.google.dev/gemini-api/docs/tokens
- xAI Grok: Chat Completions and Inference API reference.
  - https://docs.x.ai/docs/guides/chat-completions
  - https://docs.x.ai/docs/api-reference
- Mistral: Chat Completion API, structured outputs, function calling.
  - https://docs.mistral.ai/api
  - https://docs.mistral.ai/capabilities/structured_output/
  - https://docs.mistral.ai/capabilities/function_calling/
- DeepSeek: Chat Completion API, JSON output, tool calls.
  - https://api-docs.deepseek.com/api/create-chat-completion
  - https://api-docs.deepseek.com/guides/json_mode
  - https://api-docs.deepseek.com/guides/function_calling
- Cohere: v2 Chat API, tool use, structured outputs.
  - https://docs.cohere.com/v2/reference/chat
  - https://docs.cohere.com/v2/docs/tool-use
  - https://docs.cohere.com/v2/docs/structured-outputs
- Groq: OpenAI-compatible chat API, structured outputs, tool use.
  - https://console.groq.com/docs/api-reference
  - https://console.groq.com/docs/text-chat
  - https://console.groq.com/docs/structured-outputs
  - https://console.groq.com/docs/tool-use
- OpenRouter: chat completions, structured outputs, tools, reasoning tokens.
  - https://openrouter.ai/docs/api-reference/chat-completion
  - https://openrouter.ai/docs/features/structured-outputs
  - https://openrouter.ai/docs/features/tool-calling
  - https://openrouter.ai/docs/features/reasoning-tokens
- NVIDIA NIM / Integrate: NIM LLM OpenAI-compatible inference API.
  - https://docs.nvidia.com/nim/large-language-models/latest/reference/api-reference.html
- Local OpenAI-compatible runtimes: Ollama and LM Studio.
  - https://docs.ollama.com/api
  - https://docs.ollama.com/openai
  - https://lmstudio.ai/docs/api
  - https://lmstudio.ai/docs/app/api/endpoints/openai

## Provider Surface Matrix

| provider_id | family | recommended backend_id | official endpoint | auth | env var | generic base | priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| openai | OPENAI_NATIVE | openai_responses | `POST https://api.openai.com/v1/responses` | Bearer | `OPENAI_API_KEY` | no, native first | later |
| openai_chat | OPENAI_COMPATIBLE_CHAT | openai_chat_completions | `POST https://api.openai.com/v1/chat/completions` | Bearer | `OPENAI_API_KEY` | yes | later |
| anthropic | ANTHROPIC_MESSAGES_NATIVE | anthropic_messages | `POST https://api.anthropic.com/v1/messages` | `x-api-key` plus version header | `ANTHROPIC_API_KEY` | no | later |
| google_gemini | GEMINI_NATIVE | gemini_generate_content | `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `x-goog-api-key` | `GEMINI_API_KEY` | no | later |
| xai | XAI_COMPATIBLE_OR_NATIVE | xai_chat_completions | `POST https://api.x.ai/v1/chat/completions` | Bearer | `XAI_API_KEY` | yes for chat | later |
| mistral | MISTRAL_NATIVE_OR_COMPATIBLE | mistral_chat_completions | `POST https://api.mistral.ai/v1/chat/completions` | Bearer | `MISTRAL_API_KEY` | yes with profile | near |
| deepseek | DEEPSEEK_COMPATIBLE | deepseek_chat_completions | `POST https://api.deepseek.com/chat/completions` | Bearer | `DEEPSEEK_API_KEY` | yes with profile | near |
| cohere | COHERE_NATIVE | cohere_chat_v2 | `POST https://api.cohere.com/v2/chat` | Bearer | `COHERE_API_KEY` | no | later |
| groq | OPENAI_COMPATIBLE_CHAT | groq_openai_compatible_chat | `POST https://api.groq.com/openai/v1/chat/completions` | Bearer | `GROQ_API_KEY` | yes | now regression |
| openrouter | OPENAI_COMPATIBLE_CHAT | openrouter_chat_completions | `POST https://openrouter.ai/api/v1/chat/completions` | Bearer | `OPENROUTER_API_KEY` | yes with routing disabled | diagnostic later |
| nvidia | OPENAI_COMPATIBLE_CHAT | nvidia_openai_compatible_chat | `POST https://integrate.api.nvidia.com/v1/chat/completions` or NIM `/v1/chat/completions` | Bearer | `NVIDIA_API_KEY` | yes with timeout profile | diagnostic later |
| ollama | LOCAL_OPENAI_COMPATIBLE | ollama_openai_compatible_chat | `POST http://localhost:11434/v1/chat/completions` | none/local placeholder | none by default | yes local profile | later |
| lmstudio | LOCAL_OPENAI_COMPATIBLE | lmstudio_openai_compatible_chat | `POST http://localhost:1234/v1/chat/completions` | optional local token | `LMSTUDIO_API_KEY` optional | yes local profile | later |

## Provider Records

### OpenAI

- provider_id: `openai`
- provider family: `OPENAI_NATIVE` for Responses API, `OPENAI_COMPATIBLE_CHAT`
  for Chat Completions compatibility.
- recommended backend_id: `openai_responses` first; `openai_chat_completions`
  only for compatibility tests.
- request shape: `model`, `input` or conversation items for Responses; `model`
  and `messages` for Chat Completions; optional `stream`, tools, and structured
  output configuration.
- response shape: Responses output items or Chat Completion `choices`; usage
  metadata is returned by API response objects.
- structured output / JSON: Structured Outputs are supported through schema
  configuration. Sentinel must still validate `LLMDecisionResult` app-side.
- streaming: supported.
- tool/function calling: supported, but Sentinel must set tool exposure to none
  for model-decision execution until a later authority surface approves tools.
- reasoning/thinking fields: reasoning-capable models can expose reasoning
  metadata depending on endpoint and settings. Sentinel may store only
  `reasoning_present`, `reasoning_hash`, and token counts.
- redaction requirements: store request hash, prompt hash, response hash, usage
  counts, model id, and status only; never raw prompt, raw reasoning, raw key, or
  raw unsanitized response.
- timeout/rate-limit risks: standard hosted provider errors and rate limits.
- skip-safe test strategy: skip if `OPENAI_API_KEY` absent; if present, make a
  tiny structured request with tools disabled and assert no durable raw leakage.
- adapter recommendation: native Responses adapter later; generic chat base can
  support Chat Completions compatibility.

### Anthropic Claude

- provider_id: `anthropic`
- provider family: `ANTHROPIC_MESSAGES_NATIVE`
- recommended backend_id: `anthropic_messages`
- request shape: `model`, `max_tokens`, `messages`; Anthropic requires versioned
  request headers.
- response shape: message object with content blocks, stop reason, model id, and
  `usage.input_tokens` / `usage.output_tokens`.
- structured output / JSON: prompt-shaped JSON and tool-assisted structured
  output are documented; Sentinel should validate the final JSON app-side.
- streaming: supported via server-sent events.
- tool/function calling: supported through tool content blocks. Sentinel must not
  expose tools in model execution until the action authority surface exists.
- reasoning/thinking fields: extended thinking exists. Treat thinking content as
  sensitive provider output.
- redaction requirements: no raw thinking blocks, no raw prompt, no raw response.
- timeout/rate-limit risks: max token accounting affects rate limits.
- skip-safe test strategy: skip if `ANTHROPIC_API_KEY` absent; make a tiny
  messages request with tools omitted.
- adapter recommendation: native adapter required.

### Google Gemini

- provider_id: `google_gemini`
- provider family: `GEMINI_NATIVE`
- recommended backend_id: `gemini_generate_content`
- request shape: `contents` with `parts`, optional `system_instruction`, and
  `generationConfig`.
- response shape: candidates with content parts, finish reason, and
  `usageMetadata`.
- structured output / JSON: supported through response MIME type and schema
  configuration.
- streaming: supported by Gemini API guides.
- tool/function calling: supported through `functionDeclarations`, tool config,
  and function call parts.
- reasoning/thinking fields: Gemini thinking is available on supported models;
  thought signatures may appear in tool workflows. Treat as sensitive.
- redaction requirements: no durable thought signatures or raw thought content.
- timeout/rate-limit risks: model-specific context/output limits and quota.
- skip-safe test strategy: skip if `GEMINI_API_KEY` absent; use tiny
  `generateContent` request, no tools, schema if supported.
- adapter recommendation: native adapter required.

### xAI Grok

- provider_id: `xai`
- provider family: `XAI_COMPATIBLE_OR_NATIVE`
- recommended backend_id: `xai_chat_completions`
- request shape: OpenAI-compatible `model`, `messages`, optional `stream`,
  reasoning model timeout settings, and chat parameters.
- response shape: OpenAI-style chat completion with `choices`, `model`, and
  completion metadata.
- structured output / JSON: documented through xAI guides and compatible API
  surfaces; Sentinel should not assume full OpenAI schema parity without tests.
- streaming: supported.
- tool/function calling: supported in provider docs; keep disabled for Sentinel
  model execution.
- reasoning/thinking fields: Grok reasoning models may need longer timeouts;
  reasoning content must be redacted by default.
- redaction requirements: no raw reasoning, prompt, response, or key.
- timeout/rate-limit risks: reasoning models can require long timeouts.
- skip-safe test strategy: skip if `XAI_API_KEY` absent; run tiny no-tool chat
  request.
- adapter recommendation: can share generic OpenAI-compatible base with an xAI
  timeout/reasoning profile.

### Mistral

- provider_id: `mistral`
- provider family: `MISTRAL_NATIVE_OR_COMPATIBLE`
- recommended backend_id: `mistral_chat_completions`
- request shape: `model`, `messages`, `max_tokens`, `response_format`, `stream`,
  `tools`, `tool_choice`, `reasoning_effort`, and safety/guardrail fields.
- response shape: OpenAI-like `choices`, `message`, `finish_reason`, `model`,
  and `usage`.
- structured output / JSON: supports JSON mode and custom structured outputs;
  custom structure is preferred over loose JSON mode.
- streaming: supported.
- tool/function calling: supported, including parallel tool call controls.
- reasoning/thinking fields: reasoning effort exists for supported models.
- redaction requirements: no raw prompt, response, reasoning, or guardrail trace
  content in durable metadata.
- timeout/rate-limit risks: structured outputs and tools may increase latency.
- skip-safe test strategy: skip if `MISTRAL_API_KEY` absent; tiny no-tool
  structured-output request.
- adapter recommendation: can share generic OpenAI-compatible base with a
  Mistral policy profile.

### DeepSeek

- provider_id: `deepseek`
- provider family: `DEEPSEEK_COMPATIBLE`
- recommended backend_id: `deepseek_chat_completions`
- request shape: `model`, `messages`, optional `thinking`, `max_tokens`,
  `response_format`, `stream`, `tools`, and `tool_choice`.
- response shape: OpenAI-like chat completion with `choices`, `message.content`,
  optional `message.reasoning_content`, `tool_calls`, and usage fields including
  reasoning token details.
- structured output / JSON: JSON output is supported with
  `response_format: {"type": "json_object"}`; prompt must explicitly request
  JSON.
- streaming: supported.
- tool/function calling: supported; docs warn generated tool arguments still
  require application validation.
- reasoning/thinking fields: `reasoning_content` and reasoning token counts are
  explicit sensitive fields.
- redaction requirements: store only `reasoning_present`, optional hash, and
  token counts; never raw `reasoning_content`.
- timeout/rate-limit risks: thinking mode and JSON whitespace failure can cause
  long-running requests if prompts are not explicit.
- skip-safe test strategy: skip if `DEEPSEEK_API_KEY` absent; set tools none,
  structured JSON prompt, non-thinking or explicitly declared thinking policy.
- adapter recommendation: can share generic OpenAI-compatible base with
  DeepSeek-specific reasoning and JSON-mode redaction profile.

### Cohere

- provider_id: `cohere`
- provider family: `COHERE_NATIVE`
- recommended backend_id: `cohere_chat_v2`
- request shape: `model`, `messages`, `stream`, optional `tools`, `documents`,
  `response_format`, `max_tokens`, `safety_mode`, `thinking`, and
  `tool_choice`.
- response shape: `message.content` as typed content blocks, `finish_reason`,
  and `usage.tokens` / `usage.billed_units`.
- structured output / JSON: supports JSON object and optional JSON Schema on
  supported models, with limitations when combined with documents/tools.
- streaming: supported.
- tool/function calling: supported through tools and tool calls.
- reasoning/thinking fields: `thinking` configuration exists.
- redaction requirements: no raw reasoning, prompt, documents, provider response,
  or key in durable metadata.
- timeout/rate-limit risks: finish reasons include timeout and max token states.
- skip-safe test strategy: skip if `COHERE_API_KEY` absent; no tools/documents,
  tiny JSON request, app-side validation.
- adapter recommendation: native adapter required.

### Groq

- provider_id: `groq`
- provider family: `OPENAI_COMPATIBLE_CHAT`
- recommended backend_id: `groq_openai_compatible_chat`
- request shape: OpenAI-compatible `model`, `messages`, `max_completion_tokens`,
  `stream`, `response_format`, reasoning fields, and optional tools.
- response shape: OpenAI-like `choices`, `message.content`, `usage`, and Groq
  metadata.
- structured output / JSON: supports JSON mode and JSON Schema on supported
  models.
- streaming: supported.
- tool/function calling: supported. Sentinel must not expose tools for model
  execution in this provider path.
- reasoning/thinking fields: `include_reasoning`, `reasoning_effort`, and
  `reasoning_format` are documented; raw reasoning must remain off or redacted.
- redaction requirements: no raw prompt/response/reasoning/key; keep request and
  response hashes plus usage counts.
- timeout/rate-limit risks: model-specific support gaps and rate limits.
- skip-safe test strategy: existing Groq integration remains the primary
  success regression; skip if `GROQ_API_KEY` absent.
- adapter recommendation: keep as current validated provider and regression
  provider, not hardcoded runtime architecture.

### OpenRouter

- provider_id: `openrouter`
- provider family: `OPENAI_COMPATIBLE_CHAT`
- recommended backend_id: `openrouter_chat_completions`
- request shape: OpenAI-like `model`, `messages`, `max_tokens` or
  `max_completion_tokens`, `provider` routing preferences, `models`, plugins,
  `response_format`, `reasoning`, tools, metadata, and trace.
- response shape: OpenAI-like `choices`, `model`, `usage`, optional
  `openrouter_metadata`.
- structured output / JSON: supported for compatible models through
  `response_format` JSON Schema.
- streaming: supported.
- tool/function calling: supported.
- reasoning/thinking fields: reasoning configuration and reasoning-token
  features exist; raw reasoning details are sensitive.
- redaction requirements: disable provider routing/fallback by default in
  Sentinel; no raw prompt, raw reasoning, raw provider metadata containing
  upstream response details, or key.
- timeout/rate-limit risks: gateway route availability, upstream provider
  variability, rate limit, timeout, and provider error differences.
- skip-safe test strategy: skip if `OPENROUTER_API_KEY` absent; no silent
  fallback; report RATE_LIMIT/TIMEOUT/PROVIDER_ERROR honestly.
- adapter recommendation: share generic OpenAI-compatible base only after
  provider routing and fallback parameters are pinned to no auto-route.

### NVIDIA NIM / Integrate

- provider_id: `nvidia`
- provider family: `OPENAI_COMPATIBLE_CHAT`
- recommended backend_id: `nvidia_openai_compatible_chat`
- request shape: OpenAI-compatible chat completion with `model`, `messages`,
  `max_tokens`, and streaming options. NVIDIA NIM also exposes local/container
  `/v1/chat/completions`, `/v1/responses`, `/v1/models`, and health endpoints.
- response shape: OpenAI-compatible response from NIM/vLLM surfaces.
- structured output / JSON: depends on model and vLLM/OpenAI-compatible
  support; must be tested per model.
- streaming: supported by NIM endpoints.
- tool/function calling: supported by NIM LLM according to API reference.
- reasoning/thinking fields: provider/model-specific; treat all reasoning
  fields as sensitive.
- redaction requirements: no raw prompt, raw response, raw key, raw reasoning,
  or container metadata with secrets.
- timeout/rate-limit risks: hosted Integrate free endpoints can timeout; local
  NIM needs readiness checks and loaded model state.
- skip-safe test strategy: skip if `NVIDIA_API_KEY` absent for hosted Integrate;
  local NIM tests should skip if configured base URL is unavailable.
- adapter recommendation: share generic OpenAI-compatible base with a longer
  timeout profile and model-specific diagnostic status.

### Ollama

- provider_id: `ollama`
- provider family: `LOCAL_OPENAI_COMPATIBLE`
- recommended backend_id: `ollama_openai_compatible_chat`
- request shape: OpenAI-compatible `/v1/chat/completions` or native
  `/api/chat`; user-selected local model id is required.
- response shape: OpenAI-like for compatibility endpoint; native API differs.
- structured output / JSON: OpenAI compatibility docs list JSON mode and
  reasoning/thinking control for thinking models.
- streaming: supported.
- tool/function calling: tools are listed as supported in compatibility docs.
- reasoning/thinking fields: local thinking controls may exist; redact raw
  thinking.
- redaction requirements: local does not mean safe to log; redact prompt,
  response, and reasoning exactly like hosted providers.
- timeout/rate-limit risks: local model not loaded, daemon not running, slow CPU
  execution, model-specific schema limitations.
- skip-safe test strategy: skip unless `OLLAMA_BASE_URL` or explicit local
  enable flag is present and model id is provided by user contract.
- adapter recommendation: later, after local runtime sandbox policy and model
  availability checks.

### LM Studio

- provider_id: `lmstudio`
- provider family: `LOCAL_OPENAI_COMPATIBLE`
- recommended backend_id: `lmstudio_openai_compatible_chat`
- request shape: OpenAI-compatible `/v1/chat/completions`, `/v1/responses`, and
  `/v1/models` against local server, typically `http://localhost:1234/v1`.
- response shape: OpenAI-compatible response depending on loaded model and LM
  Studio server mode.
- structured output / JSON: docs advertise structured output support and
  OpenAI-compatible endpoints.
- streaming: supported by local chat/text generation docs.
- tool/function calling: LM Studio documents tool calling and local agents/MCP;
  Sentinel must not bridge those tools.
- reasoning/thinking fields: model-dependent; redact all raw thinking.
- redaction requirements: no local prompt/response/reasoning durability.
- timeout/rate-limit risks: local server not running, no loaded model, model
  context limit mismatch.
- skip-safe test strategy: skip unless `LMSTUDIO_BASE_URL` and a user-selected
  model are provided.
- adapter recommendation: later, after local server discovery and sandbox rules.

## Cross-Provider Findings

### Providers That Can Share A Generic OpenAI-Compatible Base

```text
openai_chat
xai
mistral
deepseek
groq
openrouter
nvidia
ollama
lmstudio
```

They can share request hashing, credential redaction, HTTP error mapping,
choice extraction, usage mapping, and `LLMDecisionResult` validation. They still
need provider profiles because structured output, reasoning fields, timeout
behavior, routing controls, and model support are not identical.

### Providers That Need Native Adapters

```text
openai_responses
anthropic
google_gemini
cohere
```

These providers have response structures, content-block models, thinking/tool
semantics, or usage shapes that should not be forced through a brittle
Chat-Completions-only abstraction.

### Provider Features Sentinel Must Decline By Default

```text
provider_tool_calling
server_side_tools
provider_plugins
auto_routing
fallback_model_lists
raw_reasoning_return
raw_trace_payloads
durable_prompt_logging
durable_response_logging
```

## Audit Verdict

```text
OFFICIAL_PROVIDER_SURFACE_AUDIT = COMPLETE
PROVIDER_CATALOG_IMPLEMENTATION = READY_WITH_GUARDRAILS
GENERIC_OPENAI_COMPATIBLE_BASE = APPROVED_AS_INTERNAL_ADAPTER_BASE
NATIVE_ADAPTERS = REQUIRED_FOR_OPENAI_RESPONSES_ANTHROPIC_GEMINI_COHERE
AUTO_FALLBACK_ROUTER = NOT_APPROVED
PROVIDER_EXPANSION_CAN_START = YES_AFTER_CATALOG
```

Provider expansion can start with a catalog implementation first. The first
implementation step should not add new provider calls. It should encode the
provider profile rules above and prove that recommendations, routing hints, and
capability flags cannot execute or override the user-selected provider/model.
