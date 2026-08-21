# C6L Public Long-Horizon Multi-Model Mission V1 Preflight Report

## Verdict

```text
C6L_PUBLIC_LONG_HORIZON_MULTI_MODEL_MISSION_V1 = NOT_LAUNCHED
reason = PLANNED_SAME_ROOT_MULTI_MODEL_HANDOFF_NOT_PRODUCT_ROUTED
provider_calls = 0
browser_runs = 0
ProductActionKernel_dispatch = 0
FIXED_PROVEN = 0/65
```

The OpenCode free model routing was prepared offline, but the live C6L mission
was not launched because the current public product route accepts exactly one
provider/backend/model contract per root run.

## Transport Routing

```text
x-preview-f-free
-> provider_id = opencode_chat
-> backend_id = opencode_chat_completions
-> transport = OpenAI-compatible Chat Completions

muse-spark-1.2-contributor-free
-> provider_id = opencode
-> backend_id = opencode_responses
-> transport = OpenAI Responses API
```

`Ox Alpha Free` is treated as a display name only unless the API exposes a
matching model id. The routed model id for that free chat lane is
`x-preview-f-free`.

## First Causal Blocker

Current product path:

```text
/api/runs
-> runCanonicalProductMissionFromWeb
-> sentinel canonical-product-run
-> one UserModelContract
-> one ProductModelNativeDecisionClient
-> RootMissionRuntime.run(model_client=single_client)
```

The existing `ProviderMesh` supports explicit fallback after recoverable
provider failure. It does not yet support the requested planned milestone:

```text
Phase A evidence milestone
-> checkpoint same MissionRecord
-> planned provider/model handoff
-> Phase B resumes without replaying completed actions
```

Launching C6L now would either run only one model or silently reinterpret a
provider-failure mesh as a planned cognitive handoff. That would not satisfy the
acceptance criteria.

## Offline Validation

```text
py -3.13 -m pytest tests\test_real_model_execution_opencode.py -q
result = 10 passed, 1 skipped
```

## Next Required Implementation

Implement a product-routed planned handoff mechanism that remains provider
neutral:

```text
one root MissionRecord
-> milestone evaluator over evidence refs and remaining objectives
-> checkpoint with mission_state_hash and receipt root
-> second ProductModelNativeDecisionClient contract
-> no replay of already receipted browser actions
-> final answer returned through /api/runs
```

No C6L live provider call should be consumed until this route exists and passes
offline tests.
