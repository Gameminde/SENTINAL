# OpenCode Muse Spark Provider Readiness Report

## Verdict

```text
OPENCODE_MUSE_SPARK_PROVIDER_READINESS = REAL_PROVIDER_REACHABLE_INTERMITTENT
provider_id = opencode
backend_id = opencode_responses
model_id = muse-spark-1.2-contributor-free
provider_calls = 1+
product_browser_runs = 0
raw_secret_persisted = false
```

OpenCode is registered as an explicit, non-silent provider candidate for the
canonical product route. The implementation uses a generic OpenAI Responses
adapter, not a Muse-specific parser.

## Route

```text
OperatorCatalogModelClient
-> ProviderCatalog(opencode)
-> OpenAIResponsesProvider
-> /v1/responses
-> ProviderModelResponse
-> ProductModelNativeDecisionClient / Intent Bridge
```

The default public product provider selection was moved to:

```text
provider_id = opencode
backend_id = opencode_responses
default_model_id = muse-spark-1.2-contributor-free
additional_free_model_id_seen_in_models_api = x-preview-f-free
```

The credential must be supplied only through:

```text
OPENCODE_API_KEY
```

No API key, raw prompt, raw provider response, reasoning, or Authorization
header is persisted by the adapter tests.

## Offline Proof

The tests prove:

- missing credential returns `MISSING_CREDENTIAL` without network;
- request body uses the exact free model id;
- endpoint is the OpenCode API Responses endpoint;
- `output_text` and nested `output[].content[].text` response shapes are
  accepted;
- `text/plain` successful responses are accepted as visible model text;
- HTTP errors are typed and sanitized;
- `OperatorCatalogModelClient` routes an OpenCode Responses backend without
  falling back to chat-completions;
- existing NVIDIA and OpenRouter provider tests remain green.

## Live Status

```text
real_opencode_call = PROVIDER_REACHABLE_AT_LEAST_ONCE
observed_live_instability = intermittent TIMEOUT
real_product_browser_mission = NOT_RUN
```

The real provider returned visible model text through the Responses route in a
single live provider-only test. Subsequent short probes observed intermittent
timeouts. The old strict JSON provider test was narrowed to provider
reachability because Sentinel's product route compiles free-form model
expression through the Intent Bridge instead of requiring provider-native JSON.

## Next Gate

To rerun the provider-only check:

```text
py -3.13 -m pytest tests\test_real_model_execution_opencode.py::test_opencode_real_provider_skip_safe -q
```

If that skip-safe provider call passes consistently, the next product
experiment may retry the public canonical SQLite mission with:

```text
provider = opencode
backend = opencode_responses
model = muse-spark-1.2-contributor-free
backend_browser = sentinel_chromium
```

To test the second free model ID observed from `/models`, set:

```text
SENTINEL_CANONICAL_MODEL_ID = x-preview-f-free
```

Do not use an unverified display name such as "Ox Alpha Free" as a model id.
If OpenCode later exposes that display name with a distinct API id, add the id
explicitly to the catalog first.

`FIXED_PROVEN` remains unchanged until a useful product mission completes with
receipts, proof root, evidence, final answer, replay and cleanup.
