# Sentinel Power Unification Pack 1: Direct Bypass Elimination V1

Status:

```text
POWER_UNIFICATION_PACK_1_DIRECT_BYPASS_ELIMINATION_V1 = IMPLEMENTED_CANDIDATE
product_proven = focused local product-spine proof only
provider_call = no
real_browser_run = no
real_external_channel_call = no
push = not performed
```

## Purpose

Cut the first direct-bypass cluster from the deep power audit without deleting
useful organs or opening high-risk surfaces.

Pack 1 targets the safe first layer:

```text
RuntimeHost / ProductActionKernel bounded channel
-> internal channel backend
-> ChannelDraftSendOrganV1
-> channel receipts / replay
```

The key correction is that an internal organ backend can still exist, but it
must not be confused with a product entrypoint. Product sends now stamp the
channel adapter receipt with the product dispatch owner. Direct compatibility
channel sends do not.

## Bypass Rows Addressed

| Bypass row | Pack 1 result |
|---|---|
| `BYPASS-CHANNEL-001` | Wrapped with explicit `ChannelDraftSendBackend` and product dispatch owner proof on ProductActionKernel path |
| `BYPASS-MUTATION-001` | Not migrated yet; now exposes `product_wire_status()` declaring the current L3 apply path as non-product-dispatchable |
| `BYPASS-CLI-001` / high-risk rows | Unchanged and still locked |

## Files Changed

```text
sentinel/operator/channel_adapter.py
sentinel/operator/channel_adapter_models.py
sentinel/operator/runtime_host.py
sentinel/operator/mutation_artifact_channel.py
tests/operator/test_power_unification_pack1_direct_bypass_elimination.py
```

## Behavior Before / After

Before:

```text
ProductActionKernel bounded_channel
-> ChannelConnectorRuntime
-> ChannelDraftSendOrganV1.execute
```

The path worked, but the lower channel receipt did not distinguish a product
dispatch from a direct compatibility call.

After:

```text
ProductActionKernel bounded_channel
-> ChannelConnectorRuntime(product_dispatch_owner=product_action_kernel_adapter)
-> ChannelDraftSendBackend
-> ChannelDraftSendOrganV1
```

Channel adapter receipts now include:

```text
backend_id = channel_draft_send_organ_backend
backend_owner = internal_channel_backend
product_dispatch_owner = product_action_kernel_adapter | null
```

This means:

```text
product path = product_dispatch_owner present
direct compatibility path = product_dispatch_owner null
```

## Mutation Status

`GovernedMutationArtifactChannel` remains a useful data plane and rollback
compatibility surface. Pack 1 does not replace its final L3 apply path because
that requires a proper workspace-patch bridge with rollback parity.

It now declares:

```text
product_dispatchable = false
classification = BYPASS_PRODUCT_WIRE
current_path = GovernedMutationArtifactChannel -> L3ReversibleWorkspaceExecutor
target_product_path = RuntimeHost -> ProductActionKernelDispatchAdapter -> workspace_patch
```

This prevents mutation artifacts from being cited as product-spine proof before
Pack 2/3 style workspace unification work actually wires them.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_unification_pack1_direct_bypass_elimination.py -q
4 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
12 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
3 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py -q
14 passed

py -3.13 -m pytest tests/operator/test_connection_live_channel_action_pack5.py -q
9 passed

py -3.13 -m pytest tests/test_governed_mutation_artifact_channel_v3.py -q
25 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py -q
6 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
9 passed

py -3.13 -m compileall sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter.py sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter_models.py sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py sentinel-control/services/sentinel-core/sentinel/operator/mutation_artifact_channel.py
passed

git diff --check
passed

targeted secret/raw-provider/provider-native/fallback/AUTO scan
benign hits only: existing sanitizer marker strings, existing webhook Authorization construction, and hard-stop prose in docs
```

## Hard Boundaries Preserved

Pack 1 does not enable:

```text
payment / checkout / spend
credential or secret access
login / account mutation
contact supplier or external send outside grant
destructive write outside authority
workspace escape
cookies/session/raw DOM/raw screenshot persistence
provider-native tools
fallback/AUTO
replay causing real side effects
proof tampering / fake receipt
```

Real channel transports remain blocked unless explicitly granted by the existing
bounded channel authority checks.

## Remaining Blockers

Still open from the Pack 0 census:

```text
BYPASS-MUTATION-001: final mutation artifact apply must route through workspace_patch product skill with rollback parity.
BYPASS-CERT-001 / BYPASS-CERT-002: certification harness remains internal and should not be product proof.
BYPASS-ORGRT-001 / BYPASS-ORGDISP-001: organ runtime branch paths still need product/spec ownership cuts.
BYPASS-BROWSER-001: Cloak/session backend still needs full product-spine browser ownership.
```

## Monster Runtime Scorecard Update

| Metric | Pack 1 update |
|---|---|
| `product_spine_coverage` | Improved for bounded channel proof; ProductActionKernel-owned channel receipts now carry product dispatch owner |
| `direct_bypass_count` | Baseline 20 rows remains; one P0 row is partially cut/wrapped |
| `dual_path_count` | Channel dual path is now distinguishable as product vs compatibility |
| `model_facing_primitive_leakage_count` | Unchanged |
| `recoverable_failure_continuation_coverage` | Unchanged |
| `real_provider_product_loop_proof` | Unchanged; no provider call |
| `replay_parity_coverage` | Preserved for channel and product loop |
| `browser_product_backend_coverage` | Unchanged |
| `agent_workspace_readiness` | Unchanged |
| `multi_worker_orchestration_readiness` | Unchanged |
| `signed_mission_artifact_readiness` | Unchanged |

## Recommended Next Action

Proceed to:

```text
POWER_UNIFICATION_PACK_2_SKILL_ONLY_MODEL_SURFACE_V1
```

But carry this explicit open item forward:

```text
mutation artifact final apply needs a product workspace_patch bridge before it can be counted as unified product write power.
```
