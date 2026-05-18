# Provider Catalog Design

Audit date: 2026-05-18

Mode: docs-only design. This document defines the provider catalog shape for a
future implementation pack. It does not implement code, call providers, require
API keys, or modify runtime behavior.

## Purpose

The provider catalog is a metadata layer that lets Sentinel know what a
provider/backend claims to support without letting the catalog execute anything.

```text
ProviderCatalog = metadata and policy
ProviderRegistry = enabled provider instances
ModelExecutionCoordinator = execution boundary
AgentRuntime.run = provider-agnostic caller
```

The catalog may support recommendations. Recommendations are advisory only and
must never override the user-selected provider/model.

## Non-Negotiable Invariants

```text
selected_provider_id comes from user contract / ModelCallPlan / RealModelRequest
selected_model_id comes from user contract / ModelCallPlan / RealModelRequest
catalog recommendation cannot execute
fallback recommendation cannot execute
provider failure cannot fake success
unknown provider rejected
disabled provider rejected
fake provider marker rejected
provider metadata is secret-free
raw prompt is not durable
raw provider response is not durable
raw reasoning/thinking is not durable
model output never executes tools/organs
model output never expands authority
FinalGate remains downstream certification boundary
```

## Catalog Object Model

### ProviderCatalogEntry

Recommended fields:

```text
provider_id: str
display_name: str
family: ProviderFamily
default_enabled: bool
status: active | diagnostic | local_only | planned | disabled
backends: list[ProviderBackendProfile]
credential_policy: ProviderCredentialPolicy
capability_flags: ProviderCapabilityFlags
recommendation: ProviderRecommendation | None
real_test_status: ProviderRealTestStatus
security_notes: list[str]
official_docs: list[str]
```

Rules:

- `provider_id` must be stable and lowercase.
- `default_enabled` must be false unless a provider is explicitly registered by
  the runtime setup.
- `official_docs` are links only, not scraped provider data.
- `security_notes` must not contain secrets, prompts, or provider responses.

### ProviderBackendProfile

Recommended fields:

```text
backend_id: str
family: ProviderFamily
endpoint_template: str
runtime: chat_completions | responses | messages | generate_content | local
supports_streaming: bool
supports_json_mode: bool
supports_json_schema: bool
supports_tools: bool
supports_reasoning_controls: bool
supports_usage: bool
usage_mapping: ProviderUsageMapping
timeout_profile: ProviderTimeoutProfile
retry_policy: ProviderRetryPolicy
reasoning_redaction_policy: ProviderReasoningRedactionPolicy
request_policy_notes: list[str]
response_policy_notes: list[str]
```

Rules:

- `endpoint_template` must not include credentials.
- `supports_tools` is descriptive only. It does not register tools with the
  provider or Sentinel.
- `supports_reasoning_controls` does not allow durable raw reasoning storage.

### ProviderCredentialPolicy

Recommended fields:

```text
credential_env_var: str | None
credential_source_type: env | local_none | scoped_ref
required_for_real_call: bool
secret_free_handle_required: bool
allowed_scopes: list[str]
missing_credential_outcome: MISSING_CREDENTIAL
```

Rules:

- Env var names are allowed metadata. Env var values are never catalog data.
- `ProviderCredentialHandle` remains secret-free.
- Local providers may declare `credential_env_var = None`, but local access still
  requires an explicit local enable flag in tests.

### ProviderTimeoutProfile

Recommended fields:

```text
connect_timeout_seconds: float
read_timeout_seconds: float
total_timeout_seconds: float
reasoning_timeout_multiplier: float
stream_idle_timeout_seconds: float | None
```

Rules:

- Reasoning-capable models may need a longer timeout profile.
- A timeout is an honest provider outcome, not a fallback trigger.

### ProviderRetryPolicy

Recommended fields:

```text
max_attempts: int
retryable_statuses: list[int]
retryable_outcomes: list[str]
backoff_strategy: none | fixed | exponential
jitter: bool
```

Rules:

- Initial catalog implementation should record policy only.
- Execution retries remain opt-in and must preserve receipt attempt counts.
- Retry must never change provider/model without explicit user authorization.

### ProviderReasoningRedactionPolicy

Recommended fields:

```text
raw_reasoning_fields: list[str]
request_reasoning_disable_fields: dict[str, object]
durable_reasoning_fields_allowed:
  - reasoning_enabled: bool
  - reasoning_present: bool
  - reasoning_hash: str | None
  - reasoning_token_count: int | None
```

Candidate raw reasoning field names:

```text
reasoning
reasoning_content
reasoning_details
thinking
thought
thought_signature
thinking_blocks
```

Rules:

- Raw reasoning is always sensitive provider output.
- Storing a hash is allowed only after raw value is discarded from durable
  metadata.
- Thought signatures are treated as sensitive and cannot become receipts.

### ProviderUsageMapping

Recommended fields:

```text
input_tokens_path: str | None
output_tokens_path: str | None
total_tokens_path: str | None
reasoning_tokens_path: str | None
cache_hit_tokens_path: str | None
cache_miss_tokens_path: str | None
cost_fields_supported: bool
```

Rules:

- Missing usage fields are allowed and should map to `None`.
- Provider-specific timing fields may be recorded only if secret-free.
- Raw provider payload is never stored to preserve usage.

### ProviderCapabilityFlags

Recommended fields:

```text
chat: bool
responses: bool
messages: bool
generate_content: bool
streaming: bool
json_mode: bool
json_schema: bool
tool_calling: bool
server_side_tools: bool
reasoning_controls: bool
local_runtime: bool
vision: bool
audio: bool
```

Rules:

- Flags do not grant execution authority.
- `tool_calling = true` means "provider supports it", not "Sentinel may expose
  tools".
- `server_side_tools = true` must default to disabled in Sentinel model
  execution.

### ProviderRealTestStatus

Recommended fields:

```text
status: not_started | skip_safe_only | success_validated | diagnostic_only | blocked
last_validated_model_id: str | None
last_validated_backend_id: str | None
success_evidence_commit: str | None
diagnostic_outcomes: list[str]
requires_env_var: str | None
```

Current known examples:

```text
groq = success_validated
openrouter = diagnostic_only
nvidia = diagnostic_only
openai/anthropic/gemini/xai/mistral/deepseek/cohere = not_started
ollama/lmstudio = not_started local
```

### ProviderRecommendation

Recommended fields:

```text
recommended_for: list[str]
avoid_for: list[str]
latency_class: low | medium | high | unknown
cost_class: low | medium | high | unknown
reliability_class: proven | diagnostic | unknown
notes: list[str]
```

Rules:

- Recommendation is metadata only.
- Recommendation cannot instantiate a provider.
- Recommendation cannot mutate a `ModelCallPlan`.
- Recommendation cannot override a `UserModelContract`.

## Provider Families

```text
OPENAI_COMPATIBLE_CHAT
OPENAI_NATIVE
ANTHROPIC_MESSAGES_NATIVE
GEMINI_NATIVE
XAI_COMPATIBLE_OR_NATIVE
MISTRAL_NATIVE_OR_COMPATIBLE
DEEPSEEK_COMPATIBLE
COHERE_NATIVE
LOCAL_OPENAI_COMPATIBLE
```

## Catalog Flow

Expected future flow:

```text
load static catalog entries
-> validate no secrets in catalog
-> runtime registers enabled provider instances explicitly
-> user-selected provider/model enters UserModelContract
-> ModelCallPlan preserves selection
-> RealModelRequest preserves selection
-> registry resolves exact provider_id/backend_id
-> coordinator executes only if provider is enabled and credential exists
-> validator maps ProviderModelResponse to LLMDecisionResult
-> receipt stores safe hashes and usage only
-> AgentRunResult receives safe metadata
-> FinalGate certifies result
```

Rejected flow:

```text
provider fails
-> catalog chooses another provider
-> model silently changes
-> request succeeds
```

That pattern is not Sentinel. It is silent routing and remains rejected.

## Later Test Requirements

Catalog implementation tests:

- unknown provider rejected
- disabled provider rejected
- fake provider marker rejected
- provider metadata secret-free
- supported model mismatch rejected
- catalog recommendation does not execute
- selected provider/model preserved
- fallback recommendation cannot execute without approved contract
- provider failure does not fake success
- raw key absent from metadata
- raw prompt absent from metadata
- raw provider response absent from metadata
- raw reasoning absent from metadata

Runtime integration regression tests:

- `AgentRuntime.run` remains provider-agnostic
- provider names do not appear in runtime branch logic
- `ModelCallOptimizer` cannot override selected model
- model output cannot execute tools/organs
- FinalGate still runs after model execution metadata is attached

Skip-safe real-provider tests:

- skip when credential env var is absent
- call only when the exact provider env var is present
- test prompt remains tiny and safe
- real provider outcome is either `SUCCESS_VALIDATED` or honest provider error
- no fake success path

## Implementation Guardrails

The catalog pack may add metadata and validation only. It must not add:

- new provider adapters
- automatic fallback routing
- automatic model selection
- provider SDK imports
- real provider calls
- API key handling beyond env var names
- provider tools
- organs
- memory providers
- channels
- gateway routes
- background services

## Design Verdict

```text
PROVIDER_CATALOG_DESIGN = READY
CATALOG_IS_EXECUTION_ROUTER = NO
CATALOG_RECOMMENDATION_EXECUTES = NO
USER_SELECTED_PROVIDER_MODEL_REMAINS_AUTHORITY = YES
```

The next implementation pack can build the provider catalog as a pure metadata
and validation layer before adding any new provider adapter.
