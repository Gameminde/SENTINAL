# Sentinel Product Nervous System Integration V1 - Pack 3.18 Provider Truth And Explicit Model Switch

Status: LOCALLY IMPLEMENTED CANDIDATE

Base commit:

```text
b7ea2ea79801c69f95919fe8bb7dcf98ee46348e
```

Provider calls during this pack:

```text
0
```

Push:

```text
not performed
```

Pack 4:

```text
not started
```

## Attempt 5M Reinterpretation

Attempt 5M did not prove model refusal, read-only Gate rejection, or low-friction policy failure.

The observed path was:

```text
OpenAICompatibleChatProvider.execute(...)
-> ProviderModelResponse(error_class="PROVIDER_ERROR", content=<safe diagnostic>)
-> OperatorCatalogModelClient.complete(...)
-> old _blocked("PROVIDER_ERROR", provider_response_hash=...)
-> {"reply": "...blocked...", "metadata": {"blocked_reason": "PROVIDER_ERROR"}}
-> ReadOnlyProviderDecisionClient._raise_if_blocked(...)
-> FinalGate reason = PROVIDER_ERROR
```

That meant Sentinel collapsed provider/API failure into a synthetic `reply`/`metadata` envelope before the read-only extractor could see whether actionable model content existed.

## Provider Error Origin

Root cause class:

```text
provider-contract / provider-error-handling failure
```

Not root cause:

```text
Gate/safety failure
read-only low-friction policy failure
workspace binding failure
reply-envelope model dialect failure
```

The old implementation preserved only:

```text
blocked_reason = PROVIDER_ERROR
provider_response_hash
```

It discarded safe fields that the OpenAI-compatible provider may already have produced, such as:

```text
http_status
provider_error_code
provider_error_type
provider_error_body_hash
provider_error_message_hash
```

## Provider Truth Fix

`OperatorCatalogModelClient` now returns a safe provider-failure payload when a provider response has `error_class` and retained diagnostic content.

It no longer wraps those failures as model-authored:

```text
reply
metadata.blocked_reason
```

The new safe payload carries:

```text
provider_failure = true
provider_failure_category
provider_error_class
provider_id
backend_id
model_id
endpoint_hash
provider_response_hash
diagnostic_retention_status
```

When available, it also carries:

```text
http_status
provider_error_code
provider_error_type
provider_error_code_hash
provider_error_type_hash
provider_error_message_hash
provider_error_message_redacted
provider_error_body_hash
rejected_reason
content_extraction_source
content_extraction_error
```

It does not retain:

```text
raw provider body
raw prompt
raw response
raw reasoning
reasoning_content
Authorization
API key
credential value
provider wrapper payload
```

## Failure Categories

Provider/API failures are now separated from model decision extraction failures:

```text
PROVIDER_BAD_REQUEST
PROVIDER_AUTH_ERROR
PROVIDER_RATE_LIMIT
PROVIDER_MODEL_UNAVAILABLE
PROVIDER_TRANSPORT_ERROR
PROVIDER_UNKNOWN_ERROR
```

Only visible model content that reaches the read-only decision layer and fails extraction/validation remains a model-interface failure.

## Read-Only Lane Behavior

`ReadOnlyProviderDecisionClient` now recognizes:

```text
provider_failure = true
```

and raises a provider-phase `ReadOnlySpineError` with:

```text
parse_stage = read_only_provider_failure
runtime_phase = provider_transport
typed_failure_code = PROVIDER_...
```

The read-only extractor is not invoked for provider transport/API failures.

No successful action receipt is fabricated.

## Power Policy Preservation

Pack 3.18 does not add friction to low-friction read-only mode.

The existing Pack 3.17 behavior remains:

```text
approved workspace
+ read_only_research authority
+ low_friction_read_only_power_mode
-> in-scope list/search/read can execute after boundary check
-> receipt is still required
```

Still hard-blocked:

```text
workspace escape
write/delete/modify
shell
network/browser/email/payment
credential access
authority escalation
model-supplied workspace/model_contract/authority/budget/can_execute
raw provider/reasoning persistence
fake receipts
```

## Safe Provider Inventory

A safe inventory helper was added:

```text
build_safe_provider_inventory()
```

It reports only metadata:

```text
provider ids
backend ids
model ids
plain chat compatibility
provider-native tools disabled boolean
process-scoped credential support boolean
credential present boolean
endpoint hashes
status
```

It is explicitly:

```text
data_not_authority = true
can_execute = false
fallback_auto_enabled = false
```

Current safe inventory summary from this environment:

```text
provider_count = 14
plain chat providers = aliyun_dashscope, deepseek, groq, lmstudio, mistral, nvidia, ollama, openai_chat, openrouter, xai
provider-native tools disabled = true for catalogued providers
process-scoped credential capable providers include remote env-backed providers
```

Credential presence was checked as boolean only.

At audit time:

```text
google_gemini credential present = true
google_gemini plain chat completion = false
aliyun_dashscope credential present = false
groq/openrouter/nvidia/openai_chat credential present = false
```

Therefore:

```text
alternate plain-chat provider with credential present = none
```

## Attempt 5N Decision

Do not launch `ATTEMPT_5N_EXPLICIT_ALTERNATE_PROVIDER_LOW_FRICTION_RECEIPT` from the current environment.

Required next provider contract class:

```text
plain chat completion provider
provider-native tools disabled
process-scoped credentials
explicit model contract
JSON/text output allowed
no fallback/AUTO
```

Recommended decision:

```text
PROVIDER_CONTRACT_REQUIRED
```

## Tests

Focused tests added:

```text
test_pack3_18_provider_http_error_is_not_wrapped_as_model_authored_reply
test_pack3_18_provider_failure_blocks_with_provider_truth_not_model_schema
test_pack3_18_provider_inventory_reports_safe_facts_without_credentials
```

Focused validation run:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_llm_operator_model_client_v0.py -k "pack3_18 or missing_remote_credential or extraction_failures" -q
result: 3 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py -k "pack3_18 or pack3_17 or pack3_16 or pack3_13" -q
result: 23 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_model_provider_catalog.py -k "pack3_18 or provider_catalog_metadata_is_secret_free or capability_flags" -q
result: 3 passed
```

## Remaining Limits

Pack 3.18 does not prove a new real-provider receipt.

It fixes the diagnostic and classification layer so the next real attempt can distinguish:

```text
provider/API failure
model-visible-content extraction failure
read-only Gate/scope failure
successful material receipt
```

No provider call was executed during this implementation pack.
