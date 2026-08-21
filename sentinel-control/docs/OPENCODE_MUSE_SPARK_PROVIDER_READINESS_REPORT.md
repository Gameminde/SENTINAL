# OpenCode Muse Spark Provider Readiness Report

## Verdict

```text
OPENCODE_MUSE_SPARK_PROVIDER_READINESS = IMPLEMENTED_OFFLINE_CANDIDATE
provider_id = opencode
backend_id = opencode_responses
model_id = muse-spark-1.2-contributor-free
provider_calls = 0
product_browser_runs = 0
raw_secret_persisted = false
```

OpenCode is now registered as an explicit, non-silent provider candidate for the
canonical product route. The implementation uses a generic OpenAI Responses
adapter, not a Muse-specific parser.

## Route

```text
OperatorCatalogModelClient
-> ProviderCatalog(opencode)
-> OpenAIResponsesProvider
-> /zen/v1/responses
-> ProviderModelResponse
-> ProductModelNativeDecisionClient / Intent Bridge
```

The default public product provider selection was moved to:

```text
provider_id = opencode
backend_id = opencode_responses
model_id = muse-spark-1.2-contributor-free
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
- endpoint is the OpenCode Zen Responses endpoint;
- `output_text` and nested `output[].content[].text` response shapes are
  accepted;
- HTTP errors are typed and sanitized;
- `OperatorCatalogModelClient` routes an OpenCode Responses backend without
  falling back to chat-completions;
- existing NVIDIA and OpenRouter provider tests remain green.

## Live Status

```text
real_opencode_call = NOT_RUN
reason = OPENCODE_API_KEY not present in process/user environment during this commit
```

A real call can be run only after `OPENCODE_API_KEY` is set in the process
environment. Do not paste the raw key into source, reports, shell history, or
committed artifacts.

## Next Gate

After the key is set locally:

```text
py -3.13 -m pytest tests\test_real_model_execution_opencode.py::test_opencode_real_provider_skip_safe -q
```

If that skip-safe provider call passes, the next product experiment may retry
the public canonical SQLite mission with:

```text
provider = opencode
backend = opencode_responses
model = muse-spark-1.2-contributor-free
backend_browser = sentinel_chromium
```

`FIXED_PROVEN` remains unchanged until a useful product mission completes with
receipts, proof root, evidence, final answer, replay and cleanup.
