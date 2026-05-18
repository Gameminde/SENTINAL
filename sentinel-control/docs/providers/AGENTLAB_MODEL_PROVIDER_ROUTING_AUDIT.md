# AgentLab Model Provider Routing Audit

Audit date: 2026-05-18

Mode: source-only audit. No vendor runtime was executed. No provider was
called. No API key, `.env` file, Sentinel runtime source, or production test
was modified by this audit.

## Purpose

Sentinel already proved a real runtime model execution path through the locked
model execution stack:

```text
AgentRuntime.run
-> ModelCallPlan
-> ModelExecutionCoordinator
-> provider adapter
-> ProviderModelResponse
-> LLMDecisionResult
-> safe receipt metadata
-> FinalGate-certified AgentRunResult
```

This audit reviews AgentLab and the existing vendor audits before provider
expansion. The goal is to harvest mechanisms, not vendor code.

Core Sentinel doctrine for this audit:

- the user-selected model remains authoritative
- provider routing may recommend, but must not silently override
- provider routing cannot expand mission authority
- model output cannot execute tools or organs
- model output cannot bypass FinalGate
- `ProviderCredentialHandle` remains secret-free
- durable metadata must not store raw prompt, raw provider response, raw
  reasoning/thinking fields, or raw provider keys

## Sources Audited

Primary AgentLab audit sources:

- `agent-lab/audits/final/openclaw_final_forensic_report.md`
- `agent-lab/audits/final/jarvis_final_forensic_report.md`
- `agent-lab/audits/final/openjarvis_final_forensic_report.md`
- `agent-lab/audits/final/hermes_final_forensic_report.md`
- `agent-lab/audits/final/g9_cross_agent_synthesis.md`
- `agent-lab/audits/AGENT_COMPARISON_MATRIX.md`
- `agent-lab/audits/SUPER_AGENT_GENOME.md`
- `agent-lab/audits/openclaw_static_audit.md`
- `agent-lab/audits/openjarvis_cost_router_map.md`
- `agent-lab/sentinel_integration_notes/*.md`

Primary vendor/source snapshots:

- `agent-lab/vendors/openclaw/source/README.md`
- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md`
- `agent-lab/vendors/jarvis/source/config.example.yaml`
- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py`
- `agent-lab/vendors/hermes-agent/source/run_agent.py`
- `agent-lab/vendors/hermes-agent/source/model_tools.py`
- `agent-lab/adapters/local_model_router/README.md`

Primary Sentinel sources:

- `sentinel-control/docs/CURRENT_STATE_LOCK.md`
- `sentinel-control/docs/REAL_MODEL_PROVIDER_ADAPTERS_LOCK_REVIEW.md`
- `sentinel-control/docs/REAL_MODEL_EXECUTION_BACKEND_IMPLEMENTATION_LOG.md`
- `sentinel-control/docs/specs/sentinel-real-model-execution-backend/*.md`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/*.py`
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py`
- `sentinel-control/services/sentinel-core/tests/test_runtime_model_execution_wiring.py`

## Cross-Agent Summary

| Agent/system | Provider configuration | Model selection | Routing/fallback | Tool boundary | Sentinel decision |
| --- | --- | --- | --- | --- | --- |
| OpenClaw | Session/gateway/plugin shaped; provider/auth profile resolved by embedded runner. | Session model can be persisted with other session knobs. | Auth, rate-limit, timeout can rotate profile or fail over. | Tools are close to prompt/runtime and include browser, shell, messaging, sessions. | Reuse registry/control-plane ideas; reject model fallback that can silently change execution authority. |
| JARVIS | YAML config with primary provider, fallback list, and per-provider key/model fields. | User/config selects provider and model; LLMManager abstracts providers. | Automatic fallback is a core advertised feature. | Cross-provider tool/function calling is supported; orchestrator gates tool calls separately. | Reuse provider interface; do not copy automatic fallback or inline secret config. |
| OpenJarvis | TOML/dataclass config with local/cloud provider, model paths, engine, model, and fallback fields. | Hardware-aware recommendation picks engine/model by resources. | Fallback model exists; hardware scan can produce recommendations. | Not provider-routing specific; broader risk is skill import/execution. | Reuse advisory cost/local routing as recommendations only. |
| Hermes | AIAgent accepts base_url, provider, api_key, fallback_model, provider order, provider sort, and credential pool. | Provider/model are runtime constructor/config choices. | Rich retry/fallback behavior, credential-pool recovery, OpenRouter provider routing. | Tool definitions and function calls are central to the model loop. | Reuse timeout/error-classification lessons; reject direct tool execution from model output. |
| Sentinel current | UserModelContract + ModelCallPlan + ModelExecutionCoordinator + provider registry. | User-selected model is preserved; optimizer is advisory. | No silent fallback in runtime; provider errors remain honest outcomes. | LLMDecisionResult is metadata; output cannot execute tools/organs. | Preserve. Expand providers under this contract only. |

## OpenClaw Findings

### Provider/model configuration

OpenClaw documents model selection, auth profile rotation, and model failover in
its public README. The gateway persists per-session knobs including model,
thinking level, send policy, and group activation.

Evidence:

- `agent-lab/vendors/openclaw/source/README.md:39-42`
- `agent-lab/vendors/openclaw/source/README.md:169`
- `agent-lab/vendors/openclaw/source/README.md:245`
- `agent-lab/vendors/openclaw/source/README.md:268`

The forensic report says the embedded runner resolves workspace, model,
provider, and auth profile before attempting a run. On auth/rate-limit/timeout,
the path can rotate profile or fail over.

Evidence:

- `agent-lab/audits/final/openclaw_final_forensic_report.md:126`
- `agent-lab/audits/final/openclaw_final_forensic_report.md:131`
- `agent-lab/audits/final/openclaw_final_forensic_report.md:154`

### API keys and provider surfaces

The OpenClaw static audit lists broad model/search secret references, including
OpenAI, Anthropic, xAI, Gemini/Google, and search providers. It also observes
plugin IDs for provider/auth integrations and a plugin API that can register
providers, tools, hooks, HTTP routes, gateway methods, services, channels, and
commands.

Evidence:

- `agent-lab/audits/openclaw_static_audit.md:128`
- `agent-lab/audits/openclaw_static_audit.md:181`
- `agent-lab/audits/openclaw_static_audit.md:332`
- `agent-lab/audits/openclaw_static_audit.md:357`

### Streaming, tools, and model-to-action boundary

OpenClaw's strong point is orchestration across channels, sessions, tools,
browser, shell, messaging, and gateway. The same property is the primary risk:
model context, skills, plugins, and tool availability are close to real action.

Evidence:

- `agent-lab/audits/final/openclaw_final_forensic_report.md:24-29`
- `agent-lab/audits/final/openclaw_final_forensic_report.md:177`
- `agent-lab/audits/final/openclaw_final_forensic_report.md:187`
- `agent-lab/audits/final/openclaw_final_forensic_report.md:194`
- `agent-lab/audits/final/openclaw_final_forensic_report.md:255-257`

### Strengths

- Mature gateway/session model.
- Provider/auth profile shape is useful as a concept.
- Session-level model visibility is useful for traceability.
- Model failure routing is practical operationally.
- Scanner mindset for plugins/skills is directly valuable.

### Weaknesses and risks

- Provider failover can be behaviorally correct for chat but unsafe for
  mission-governed execution if it changes model capability, data route, cost,
  or jurisdiction without user approval.
- Plugin/provider registration is too close to runtime capability.
- Tool availability is model-visible; Sentinel must keep tool authority outside
  model-writable context.
- External channels and plugins can inject instructions into model context.
- Raw provider/auth profile handling is not shaped as Sentinel receipts.

### Sentinel reuse/avoid decision

Reuse:

- session-visible model metadata
- provider/auth profile concept as sanitized metadata only
- gateway-style control plane as a future provider-management UI concept
- scanner-driven provider/plugin admission

Avoid:

- vendor runtime bridge
- automatic provider failover without explicit selected-model contract update
- provider plugins that can register execution tools directly
- prompt-level tool policy as the actual authority boundary

## JARVIS Findings

### Provider/model configuration

JARVIS has an explicit LLM provider abstraction. Its docs advertise a unified
provider interface, automatic fallback, streaming, and cross-provider tool
calling. It supports Anthropic, OpenAI, and Ollama in docs, while config
examples also mention Groq, OpenRouter, and NVIDIA-compatible paths.

Evidence:

- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md:20-27`
- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md:37`
- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md:114-118`
- `agent-lab/vendors/jarvis/source/config.example.yaml:16-21`
- `agent-lab/vendors/jarvis/source/config.example.yaml:34-53`

The config file stores primary and fallback providers plus per-provider
key/model fields. It also notes that an environment variable can replace the
NVIDIA key field.

Evidence:

- `agent-lab/vendors/jarvis/source/config.example.yaml:24-31`
- `agent-lab/vendors/jarvis/source/config.example.yaml:44-48`

### Routing/fallback

JARVIS documents an LLMManager that registers providers, sets the primary
provider, and sets an ordered fallback chain. It also provides custom provider
extension examples.

Evidence:

- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md:340-351`
- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md:400-422`
- `agent-lab/vendors/jarvis/source/docs/LLM_PROVIDERS.md:513-516`

### Tool/function calling boundary

The final forensic report says the daemon wires LLM providers with an authority
engine, approval manager, deferred executor, sidecar manager, and workflow
engine. It also says the primary orchestrator gates tool calls through
authority checks and audit logging.

Evidence:

- `agent-lab/audits/final/jarvis_final_forensic_report.md:96`
- `agent-lab/audits/final/jarvis_final_forensic_report.md:105`
- `agent-lab/audits/final/jarvis_final_forensic_report.md:133`

The same report identifies a weakness: unknown tool fallback can map to
low-risk read behavior unless explicitly corrected.

Evidence:

- `agent-lab/audits/final/jarvis_final_forensic_report.md:595`

### Strengths

- Clean provider abstraction concept.
- Multi-provider setup with local Ollama path.
- Streaming and tool calling are first-class provider features.
- Tool calls are at least routed through a separate orchestrator/authority path.

### Weaknesses and risks

- Fallback is advertised as automatic and seamless, which conflicts with
  Sentinel's no-silent-override doctrine.
- Config examples include inline key fields; Sentinel should prefer env refs or
  scoped credential refs only.
- Provider errors are logged to console in docs, which requires careful
  redaction discipline.
- Unknown tool classification must fail closed, not downgrade to read.

### Sentinel reuse/avoid decision

Reuse:

- provider interface shape
- explicit provider registry and primary/fallback config as UI intent
- streaming abstraction later, after redaction and receipt policy
- local model provider category

Avoid:

- automatic fallback execution
- inline provider secrets in durable config
- cross-provider tool calling as immediate execution
- unknown tool fallback to a low-risk category

## OpenJarvis Findings

### Provider/model configuration

OpenJarvis has hardware-aware engine and model recommendation. It detects
hardware, recommends an engine, maps available memory to model tiers, and
generates config with default model, fallback model, local model path,
preferred engine, provider, temperature, and max tokens.

Evidence:

- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py:193`
- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py:209`
- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py:254`
- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py:529-535`
- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py:1706-1712`

Its cost router map emphasizes model tiering by memory, download estimates, and
accuracy/latency/cost/efficiency reward weights.

Evidence:

- `agent-lab/audits/openjarvis_cost_router_map.md:13-16`
- `agent-lab/vendors/openjarvis/source/src/openjarvis/core/config.py:672-674`
- `agent-lab/adapters/local_model_router/README.md:5-9`

### User-selected model support

OpenJarvis is recommendation-heavy. It can produce defaults from hardware, but
also exposes config fields for default and fallback model. The useful Sentinel
lesson is not "auto-pick the model"; it is "recommend a route with rationale
and measurable tradeoffs."

Evidence:

- `agent-lab/sentinel_integration_notes/openjarvis_to_sentinel.md:21-41`
- `agent-lab/sentinel_integration_notes/openjarvis_to_sentinel.md:75`

### Strengths

- Local-first and cost-aware model recommendation.
- Explicit hardware/resource signals.
- Cost/latency/efficiency included as routing criteria.
- Useful for future Sentinel provider recommendation and local model planning.

### Weaknesses and risks

- Hardware fit is not mission fit.
- Fallback can choose a model for capability/resource reasons but must not
  override user selection in Sentinel.
- Local model availability can drift and should be probed skip-safely.
- Recommendation should not mutate runtime config silently.

### Sentinel reuse/avoid decision

Reuse:

- advisory model/router recommendations
- local/cloud cost and latency estimates
- resource constraints in provider metadata
- route rationale in receipts

Avoid:

- auto-generated defaults as execution authority
- fallback model execution without user approval
- treating local model privacy/cost benefit as authority to use it

## Hermes Findings

### Provider/model configuration

Hermes exposes a broad AIAgent constructor with base URL, API key, provider,
model, provider allow/ignore/order/sort parameters, provider data collection,
stream callbacks, fallback model, credential pool, max tokens, and reasoning
config. It imports OpenAI-compatible client machinery and its own timeout,
retry, error-classification, usage-pricing, and prompt-caching utilities.

Evidence:

- `agent-lab/vendors/hermes-agent/source/run_agent.py:5-14`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:44-56`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:83-103`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:835-890`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:916-926`
- `agent-lab/audits/final/hermes_final_forensic_report.md:96`
- `agent-lab/audits/final/hermes_final_forensic_report.md:103`

### Routing/fallback/retry

Hermes has rich fallback and recovery paths: provider order/sort,
OpenRouter-specific provider preferences, credential-pool recovery, rate-limit
handling, provider fallback, retry backoff, and cache/cost accounting.

Evidence:

- `agent-lab/vendors/hermes-agent/source/run_agent.py:1120-1126`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:10746-10761`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:11011-11024`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:11350-11367`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:11501`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:12221-12242`
- `agent-lab/audits/final/hermes_final_forensic_report.md:642`
- `agent-lab/audits/final/hermes_final_forensic_report.md:778`

### Reasoning/prompt/response leakage and sanitization

Hermes contains several sanitizers for non-ASCII/surrogate failures, including
reasoning fields such as `reasoning_content` and `reasoning_details`. It also
has explicit recovery paths for provider-state-only fields and provider
diagnostics. This is valuable operational evidence: reasoning fields should be
treated as sensitive provider output and never durably stored raw in Sentinel.

Evidence:

- `agent-lab/vendors/hermes-agent/source/run_agent.py:390-444`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:489-501`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:654-718`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:10600-10613`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:10850-10868`
- `agent-lab/vendors/hermes-agent/source/run_agent.py:12170-12198`

### Tool/function calling boundary

Hermes provides model-facing tool definitions and a `handle_function_call`
dispatcher. Toolset filtering exists, but tools are part of the main model
conversation loop.

Evidence:

- `agent-lab/vendors/hermes-agent/source/model_tools.py:2-14`
- `agent-lab/vendors/hermes-agent/source/model_tools.py:200-224`
- `agent-lab/vendors/hermes-agent/source/model_tools.py:353-359`
- `agent-lab/vendors/hermes-agent/source/model_tools.py:367`
- `agent-lab/vendors/hermes-agent/source/model_tools.py:494`
- `agent-lab/audits/final/hermes_final_forensic_report.md:111`

### Strengths

- Strong operational handling of real provider weirdness.
- Rich error classification, retries, fallback, cost estimation, and cache
  telemetry.
- Reasoning-field and malformed-payload recovery experience is useful.
- Tool schema sanitization exists for provider compatibility.

### Weaknesses and risks

- Provider, memory, skills, plugins, tool hooks, and model loop are heavily
  interleaved.
- Fallback can change provider/model during a live run.
- API key can live as a runtime object attribute in vendor code; Sentinel's
  credential handle must remain secret-free.
- Reasoning/prompt/provider response sanitization is recovery-oriented, not a
  strict durable metadata policy.
- Model tool calls enter a dispatcher path; Sentinel must keep model output as
  decision metadata unless authority gates approve later actions.

### Sentinel reuse/avoid decision

Reuse:

- error taxonomy, retry-after/backoff ideas, and provider diagnostics
- reasoning-field sensitivity model
- provider-specific timeout/cache assumptions as telemetry, not policy
- tool schema compatibility tests, but not execution coupling

Avoid:

- fallback execution that changes selected model without explicit user consent
- storing raw provider response or reasoning fields for debugging
- allowing model tool calls to dispatch executors
- treating external memory/provider context as policy

## TradingAgents Note

TradingAgents is not a direct model-provider router target for this pack, but it
offers useful patterns for structured outputs, debate/risk roles, and data
vendor fallback. The useful Sentinel lesson is structured decision/result
schemas with risk review. The risky pattern is any direct translation from model
debate to action, especially in finance/trading contexts.

Evidence:

- `agent-lab/audits/tradingagents_static_audit.md:52-61`
- `agent-lab/audits/tradingagents_static_audit.md:86-111`
- `agent-lab/audits/tradingagents_capability_map.md:29`

## Sentinel Current Provider Layer

Sentinel's current provider architecture already differs from AgentLab in the
important ways:

- `RealModelRequestBuilder` rejects ModelCallPlan overrides of the
  user-selected model.
- `ModelExecutionCoordinator` uses a provider registry and credential resolver.
- Missing providers/credentials are honest non-success outcomes.
- Provider responses validate into `LLMDecisionResult`.
- Safe receipts contain hashes and metadata instead of raw prompt/key/provider
  response.
- `AgentRuntime.run` knows only `ModelExecutionCoordinator`, not Groq,
  OpenRouter, NVIDIA, or any other specific provider.

Evidence:

- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/coordinator.py:29-31`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/coordinator.py:73-118`
- `sentinel-control/services/sentinel-core/sentinel/agent/model_execution/credentials.py:20-31`
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py:165-168`
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py:2037-2059`
- `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py:2075-2081`
- `sentinel-control/services/sentinel-core/tests/test_runtime_model_execution_wiring.py`

The current lock docs still record the provider-adapter layer as locked and
runtime wiring as a separate Wave 9 concern. Local Wave 9 evidence exists in
runtime and tests, but this audit does not modify the state lock.

Evidence:

- `sentinel-control/docs/CURRENT_STATE_LOCK.md:10-24`
- `sentinel-control/docs/CURRENT_STATE_LOCK.md:61-89`
- `sentinel-control/docs/REAL_MODEL_PROVIDER_ADAPTERS_LOCK_REVIEW.md:93-139`

## Failure Modes Sentinel Should Avoid

| Failure mode | Seen in source family | Why it matters | Sentinel guardrail |
| --- | --- | --- | --- |
| Silent provider/model fallback | OpenClaw, JARVIS, Hermes, OpenJarvis | May change quality, cost, privacy route, jurisdiction, or reasoning behavior without user consent. | No execution fallback unless user updates selected model contract or approves an explicit fallback plan. |
| Inline raw key config | JARVIS examples, broad vendor configs | Durable config files become secret-bearing. | Env vars or scoped credential refs only; `ProviderCredentialHandle` stores hashes/metadata only. |
| Provider plugins registering tools | OpenClaw, Hermes provider/plugin ecosystems | Provider expansion can become capability expansion. | Provider adapters are model I/O only; no tool/organ registration. |
| Model output dispatching tools | Hermes/JARVIS/OpenClaw tool loops | Model text/tool calls become action. | `LLMDecisionResult` is metadata; action execution requires separate authority envelope and FinalGate path. |
| Prompt-level permission policy | OpenClaw/JARVIS prompts/templates | Instructions can be overridden or confused with authority. | MissionAuthorityEnvelope and FinalGate stay outside prompt. |
| Raw prompt/response/reasoning logging | Real-provider diagnostics in general | Provider debugging can leak sensitive content. | Hashes only in receipts/logs; sanitized diagnostic class/status only. |
| Reasoning field persistence | Hermes provider recovery cases | Thinking fields can contain sensitive or policy-like content. | `reasoning_present` and hash only, no raw durable storage. |
| Unknown tool fallback | JARVIS audit | New dangerous tools can be classified too low. | Unknown provider capability or tool action fails closed. |
| Cost explosion through retries/fallback | Hermes/OpenClaw/OpenJarvis | Long contexts and repeated calls can run away. | Bounded timeout/retry policy and future action/mission token budget closure. |
| Local model auto-route overreach | OpenJarvis | Local is cheaper/private but may be weaker or untrusted. | Local route is recommendation until selected by user. |

## Audit Verdict

```text
AGENTLAB_PROVIDER_ROUTING_AUDIT = COMPLETE
provider_expansion_readiness = GO_WITH_SENTINEL_NATIVE_GUARDRAILS
vendor_runtime_bridge = REJECTED
silent_provider_override = REJECTED
model_output_tool_execution = REJECTED
```

Sentinel should expand provider support, but only through the existing
provider-agnostic `ModelExecutionCoordinator` architecture. The next pack should
add provider catalog/registration and selected provider adapters, not a generic
auto-router that overrides the user-selected model.
