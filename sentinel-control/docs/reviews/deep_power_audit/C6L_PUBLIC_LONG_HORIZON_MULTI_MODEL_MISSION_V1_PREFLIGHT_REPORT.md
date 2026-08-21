# C6L Public Long-Horizon Multi-Model Mission V1 Preflight Report

## Verdict

```text
C6L_PUBLIC_LONG_HORIZON_MULTI_MODEL_MISSION_V1 = ARMED_LOCAL_HANDOFF_CANDIDATE
previous_blocker = PLANNED_SAME_ROOT_MULTI_MODEL_HANDOFF_NOT_PRODUCT_ROUTED
current_status = PLANNED_SAME_ROOT_MULTI_MODEL_HANDOFF_PRODUCT_ROUTED_LOCAL
provider_calls = 0
browser_runs = 0
ProductActionKernel_dispatch = 0
FIXED_PROVEN = 0/65
```

The OpenCode free model routing was prepared offline, but the live C6L mission
was not launched in this tranche. The initial blocker was repaired locally:
`canonical-product-run` can now accept an explicit Phase B provider contract and
route both phases through one root `MissionRecord`.

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

## Product Handoff Route

Current product path:

```text
/api/runs
-> runCanonicalProductMissionFromWeb
-> sentinel canonical-product-run
-> Phase A ProductModelNativeDecisionClient
-> ProviderMesh planned handoff
-> Phase B ProductModelNativeDecisionClient
-> RootMissionRuntime.run(model_client=single_client)
```

The existing `ProviderMesh` still supports explicit fallback after recoverable
provider failure. It now also supports the small planned handoff required for
C6L:

```text
Phase A material/evidence progress
-> checkpoint same MissionRecord
-> planned provider/model handoff
-> Phase B resumes without replaying completed actions
```

The handoff is visible to the second model as safe state/observation data and
is persisted as `canonical_provider_mesh_planned_handoff`.

## Offline Validation

```text
py -3.13 -m pytest tests\test_real_model_execution_opencode.py -q
result = 10 passed, 1 skipped

py -3.13 -m pytest tests\operator\test_sentinel_dev_max_power_canonical_core_v1.py::test_public_product_cli_can_plan_same_root_provider_handoff -q
result = passed

py -3.13 -m pytest tests\operator\test_sentinel_single_spine_c5_physical_browser_boundary.py::test_provider_mesh_planned_handoff_resumes_same_mission_without_replaying_browser_receipt -q
result = passed

npm run build
result = passed
```

## Next Required Implementation

Before live C6L, freeze the exact mission body and launch one public product
run with:

```text
Phase A = opencode_chat / x-preview-f-free
Phase B = opencode / muse-spark-1.2-contributor-free
backend = sentinel_chromium
target_origin = sqlite.org
```

The live run is still not executed here; `FIXED_PROVEN` remains `0/65` until a
useful product mission completes with receipts, proof root, final answer and
cleanup.
