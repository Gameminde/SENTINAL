# AgentLab To Sentinel Provider Design Matrix

Audit date: 2026-05-18

Mode: source-only design matrix. This file maps audited AgentLab mechanisms to
Sentinel-native provider expansion decisions. It is not an implementation plan
and does not authorize provider calls, tool execution, or runtime authority
expansion.

## Matrix

| Mechanism | Source agent/system | Sentinel-native rewrite | Decision | Reason | Required tests | Redaction rule | Authority boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Provider registry / manager | JARVIS `LLMManager`; Sentinel `ModelProviderRegistry` | Keep Sentinel registry as the execution selector; providers expose metadata, enabled state, supported models, and one execute method. | Keep | This matches Pack A/B and avoids provider-specific runtime branches. | Unknown provider rejected; disabled provider rejected; fake provider marker rejected; runtime has no provider names. | Provider metadata cannot include keys, raw prompts, raw responses, or raw reasoning. | Registry grants model I/O only, never tools/organs. |
| Primary provider plus fallback list | JARVIS config, OpenClaw failover, Hermes fallback model | Store fallback candidates as recommendations requiring explicit user approval or contract update before execution. | Modify | Automatic fallback conflicts with user-selected model doctrine. | Primary failure records honest outcome; fallback is not called automatically; approved fallback changes selected contract. | Fallback reason stored as error class/status/hash only. | Fallback cannot expand scope, tools, spend, data route, or authority. |
| Session-visible model setting | OpenClaw session config/status | Keep selected model/provider in runtime metadata and receipts. | Keep | Users and reviewers need visible proof of which model ran. | AgentRunResult metadata includes selected provider/model; no raw prompt. | Store provider/model IDs, request hash, receipt hash only. | Metadata is evidence, not authority. |
| Auth profile / credential profile | OpenClaw auth profile rotation; Hermes credential pool | Represent as `ProviderCredentialHandle` or future scoped credential ref with source hash and scopes only. | Modify | Profile concept is useful, but raw credentials must not enter durable state. | Missing credential returns `MISSING_CREDENTIAL`; handle serialization excludes secret; no key in logs/results. | Never store env var value, Authorization header, or provider token. | Credential ref allows provider call only; does not grant mission action authority. |
| OpenAI-compatible adapter family | JARVIS OpenAI/Ollama docs; Hermes OpenRouter/OpenAI-compatible path; Sentinel Groq/OpenRouter/NVIDIA adapters | Add generic OpenAI-compatible adapter base only after adapter differences are codified by tests. | Modify | Many providers share chat completions shape, but error/reasoning/usage fields differ. | Unit tests for request shape, response mapping, timeout, refusal, malformed response, reasoning redaction. | Raw response body remains memory-only; durable metadata uses hashes. | Adapter maps model output to `ProviderModelResponse` only. |
| Native provider adapters | JARVIS Anthropic/OpenAI/Ollama; future Sentinel native providers | Use native adapters only where protocol differs materially from OpenAI-compatible chat. | Keep | Some providers need native request/response handling. | Native provider tests must prove no silent model override and skip-safe real calls. | Same redaction contract as all providers. | Native adapter cannot expose extra tool/organ power. |
| Hardware-aware local routing | OpenJarvis `recommend_engine`/`recommend_model`; AgentLab local router notes | Add advisory `ProviderRecommendation` or router plan, not automatic execution. | Modify | Useful for cost/privacy/latency, dangerous if it overrides user selection. | Recommendation generated but not executed; selected model unchanged; user approval required to change. | Recommendation metadata excludes local file paths unless sanitized. | Recommendation cannot grant use of local hardware or files. |
| Cost-aware route scoring | OpenJarvis cost router map; Hermes usage pricing | Keep as advisory model-call planning and future budget gate input. | Modify | Cost is safety-relevant, but not authority. | Estimated cost recorded; unknown cost becomes conservative; budget exceed returns non-success. | Store estimates and hashes, not prompt text. | Cost router cannot select a different model silently. |
| Provider-specific retry/backoff | Hermes retry/backoff and error classification | Add bounded retry policy per provider, disabled/default conservative until tested. | Modify | Real providers need retries, but retries can multiply cost and leakage risk. | Retry count bounded; only retry timeout/rate-limit/provider-unavailable classes; no retry for schema/authority errors. | Retry diagnostics sanitized; no raw response/key. | Retry cannot change provider/model unless approved fallback. |
| Rate-limit handling | Hermes credential pool/fallback; OpenClaw failover | Return honest `RATE_LIMIT` outcome, optionally produce recommendation for later provider switch. | Modify | Rate limit is not license to override selected model. | Rate limit outcome does not fake success; optional recommendation is not executed. | Store status class, retry-after seconds if safe, and provider hash. | No authority expansion. |
| Streaming | JARVIS streaming; Hermes stream callbacks; OpenClaw streaming/chunking | Defer full streaming until receipt/redaction policy can handle incremental chunks. | Park | Streaming complicates durable leakage and partial result validation. | Stream chunks not stored raw; final assembled response validates before metadata attach. | Raw stream chunks never durable by default. | Partial stream cannot trigger actions. |
| Tool/function calling | JARVIS cross-provider tools; Hermes tool dispatcher; OpenClaw tools | Reject provider tool execution in model execution layer. Future tool proposals must be typed outputs and routed to separate authority gates. | Reject for provider layer | Model execution should produce `LLMDecisionResult`, not actions. | Provider response with tool/organ execution fields rejected; runtime controlled-capability results unchanged. | Tool-call arguments from model output are not stored raw unless separately sanitized. | MissionAuthorityEnvelope and FinalGate remain the only authority path. |
| JSON/structured output | JARVIS JSON mode; TradingAgents structured decisions; Sentinel validator | Keep strict `LLMDecisionResult` validation as the only accepted runtime model result. | Keep | Structured output is how Sentinel prevents free-form text from becoming action. | Invalid schema rejected; authority-expanding fields rejected; refusal mapped. | Store validated fields only; raw source text memory-only. | Valid result is evidence/decision metadata, not execution authority. |
| Reasoning fields | Hermes reasoning sanitization and OpenRouter diagnostics | Treat reasoning/thinking fields as sensitive. Store boolean/hash only when needed. | Keep | Reasoning can contain secrets, policy text, or provider-internal content. | `reasoning_details`, `reasoning_content`, `thinking` absent from durable metadata; hash-only if present. | No raw reasoning fields in logs, receipts, traces, docs. | Reasoning never modifies authority. |
| Prompt/context trust labels | OpenClaw final report; Hermes prompt/context scanning | Keep trust labels in decision frame and prompt rendering; do not let vendor docs/memory become policy. | Keep | Prompt injection risk is recurrent across agents. | Untrusted content marked; sanitizer chokepoints prove no raw secret; policy prompt separate. | Prompt body not durable; prompt hash only. | Prompt content cannot grant powers. |
| External memory providers | Hermes memory provider plugins | Reject provider plugins in model provider layer; future memory providers require separate manifest/spec. | Reject for provider layer | Memory providers can inject context and tools. | Model provider adapter cannot register memory tools or context providers. | Memory hits use source/trust metadata and no secrets. | Memory is context only, never authority. |
| Plugin provider registration | OpenClaw plugin registry providers; Hermes plugins | Reject dynamic provider plugins for now. Add providers through reviewed Sentinel adapters only. | Reject | Dynamic plugin loading is too close to execution. | New provider adapter requires tests, docs, skip-safe real test, and no secret leak scan. | Provider metadata only; no plugin code in receipts. | Provider adapter cannot add tools, routes, services, or organs. |
| Gateway/control-plane model UI | OpenClaw gateway/session model | Park for future UI/admin layer. | Park | Useful once providers are managed interactively. | UI can show selected model and recommendations; changing model creates signed contract update. | UI must not display keys or raw prompts. | UI cannot grant model/tool authority without envelope update. |
| Local model support | JARVIS Ollama, OpenJarvis local engines | Add later as explicit provider adapters selected by user. | Modify | Important for privacy/cost, but local runtimes can leak files or execute code depending on engine. | Local provider disabled by default; no auto-pull/download; skip-safe local availability tests. | Local model paths sanitized; no raw local prompt logs. | Local provider does model I/O only. |
| Provider diagnostics | Hermes provider hints; Sentinel diagnostic docs | Keep sanitized diagnostics as docs/log metadata; no raw provider body. | Keep | Real providers fail often; honest diagnostics prevent fake success. | HTTP status/error class stored; body hash only; no key/prompt/response leak. | Hash/class/status only. | Diagnostics cannot trigger fallback/action. |
| Unknown capability handling | JARVIS unknown tool fallback finding | Fail closed for unknown provider capabilities and unknown model output fields. | Keep as strict rule | Unknown should not downgrade to low risk. | Unknown provider capability rejected; extra authority/tool fields rejected. | Unknown fields not durably stored raw. | Unknown cannot execute. |

## Sentinel-Native Provider Expansion Shape

The next provider expansion should preserve the current separation:

```text
UserModelContract
-> ModelCallOptimizer recommendation
-> ModelCallPlan
-> ModelExecutionCoordinator
-> ModelProviderRegistry
-> selected provider adapter
-> ProviderModelResponse
-> LLMDecisionResult
-> ModelExecutionReceipt
-> AgentRunResult metadata
-> FinalGate certification
```

Required invariants:

- `AgentRuntime.run` must remain provider-agnostic.
- Provider adapters cannot register tools, organs, gateway routes, memory
  providers, background services, or channels.
- Provider selection comes from the user-selected contract and approved plan.
- Fallback is a recommendation until explicitly approved.
- Provider-specific request/response details remain inside adapters.
- Raw prompt, raw provider response, raw reasoning, and raw keys stay out of
  durable metadata.

## Provider Expansion Test Requirements

Every future provider pack must add tests for:

- unknown provider rejected
- disabled provider rejected
- missing credential returns honest non-success
- user-selected model preserved exactly
- optimizer recommendation cannot override selected model
- provider error/rate-limit/timeout does not fake success
- invalid response schema rejected
- authority-expanding model output rejected
- model output cannot execute tools/organs
- raw key absent from result/log/receipt/docs
- raw prompt absent from durable metadata
- raw provider response absent from durable metadata
- raw reasoning fields absent from durable metadata
- real-provider integration skip-safe when key absent
- real-provider integration proves non-fake success when key present

## Recommended Rewrite Decisions

Keep immediately:

- provider registry and coordinator
- strict selected-model preservation
- OpenAI-compatible provider adapter pattern
- safe receipt shape
- provider diagnostic report shape
- `LLMDecisionResult` validator

Modify before adopting:

- fallback routing
- local model recommendation
- streaming
- retry/rate-limit policy
- cost-based route scoring
- provider capability discovery

Reject in provider layer:

- vendor runtime bridges
- dynamic provider plugins
- model tool/function calls that directly execute
- provider adapters that add organs or tools
- raw key or raw prompt config
- automatic provider/model override

Park for later specs:

- streaming
- local model runtime pack
- provider management UI
- multi-provider fallback with explicit user approval
- action and mission token-budget closure
