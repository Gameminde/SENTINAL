# Sentinel Power Unification Pack 0: Direct Bypass And Dual Path Census V1

Status:

```text
POWER_UNIFICATION_PACK_0_DIRECT_BYPASS_AND_DUAL_PATH_CENSUS_V1 = IMPLEMENTED_DOCS_ONLY
```

Runtime behavior changes:

```text
0
```

Provider calls:

```text
0
```

Real browser runs:

```text
0
```

Real external channel calls:

```text
0
```

Push:

```text
not performed
```

## Purpose

Convert the deep-code audit bypass findings into an executable migration table
for the Monster Runtime unification lane.

This pack does not delete code and does not change behavior. It tells the next
implementation pack exactly which product bypasses to remove, wrap, wire,
deprecate, keep internal, or keep locked.

## Inputs Read

Primary audit/control inputs:

```text
sentinel-audit/deep-code-audit/CONSOLIDATED_FINDINGS_SYNTHESIS.md
sentinel-audit/deep-code-audit/HOW_TO_FINISH_SENTINEL_UNIFICATION.md
sentinel-audit/deep-code-audit/LOGIC_FLOWS_AND_ENFORCEMENT_MAP.md
SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md
SENTINEL_GLOBAL_POWER_RECONNECTION_CORRECTION_PLAN_V1.md
SENTINEL_POWER_RECONNECTION_PACK_SEQUENCE_V1.md
SENTINEL_MONSTER_RUNTIME_OBJECTIVE_LOCK_V1.md
```

Targeted code evidence sampled:

```text
sentinel/operator/channel_adapter.py
sentinel/operator/mutation_artifact_channel.py
sentinel/operator/real_model_certification.py
sentinel/operator/runtime_connections.py
sentinel/operator/power_skill_registry.py
sentinel/operator/power_bridge.py
sentinel/power/runtime.py
sentinel/agent/organs/runtime_execution.py
sentinel/agent/organs/organ_dispatch.py
sentinel/agent/organs/browser_session_manager_l5_live.py
sentinel/organs/browser/navigation_l6.py
sentinel/organs/browser/controlled_runner.py
sentinel/cli.py
sentinel/mission/runner.py
sentinel/agent/organs/external_api_read_write_organ_v1.py
sentinel/organs/spend/runtime.py
sentinel/operator/worker_fleet.py
sentinel/memory/store.py
```

## Generated Artifact

Executable migration matrix:

```text
SENTINEL_POWER_UNIFICATION_PACK_0_DIRECT_BYPASS_AND_DUAL_PATH_CENSUS_V1.csv
```

Total rows:

```text
20
```

## Classification Counts

| Classification | Count | Meaning |
|---|---:|---|
| `BYPASS_WRAP_THROUGH_DISPATCHER` | 3 | Useful runtime exists, but product/operator entry should route through RuntimeHost/ProductActionKernel first |
| `BYPASS_PRODUCT_WIRE` | 5 | Dormant or parallel power should become a hidden backend for a product skill |
| `BYPASS_KEEP_INTERNAL` | 4 | Keep as harness/backend/internal compatibility, not product proof or model-facing route |
| `BYPASS_DEPRECATE` | 3 | Legacy route should be marked non-primary and gradually removed or moved behind compatibility wrappers |
| `BYPASS_LOCK_HIGH_RISK` | 5 | Real-damage surface remains hard-stopped until a future explicit special-authority mission |

## P0 Rows

| Bypass ID | Classification | Why P0 |
|---|---|---|
| `BYPASS-CHANNEL-001` | `BYPASS_WRAP_THROUGH_DISPATCHER` | Channel send has real-world side effects; product/operator sends should enter through ProductActionKernel |
| `BYPASS-MUTATION-001` | `BYPASS_PRODUCT_WIRE` | Workspace mutation must not bypass product receipts/replay/FinalGate |
| `BYPASS-ORGRT-003` | `BYPASS_LOCK_HIGH_RISK` | Browser form/download/upload/js special authorities must stay hard-stopped by default |
| `BYPASS-BROWSER-001` | `BYPASS_PRODUCT_WIRE` | Cloak/session should become product-leading browser backend, not a parallel organ path |
| `BYPASS-BROWSER-002` | `BYPASS_LOCK_HIGH_RISK` | L6 browser navigation can cross into login/payment/contact territory if opened broadly |
| `BYPASS-CLI-001` | `BYPASS_LOCK_HIGH_RISK` | CLI direct special browser organ calls must not become casual product paths |
| `BYPASS-EXTERNALAPI-001` | `BYPASS_LOCK_HIGH_RISK` | External API read/write needs credential lease and replay story before product dispatch |
| `BYPASS-SPEND-001` | `BYPASS_LOCK_HIGH_RISK` | Payment/spend is real damage and remains locked |

## High-Value Safe First Cuts

These are the best candidates for `POWER_UNIFICATION_PACK_1_DIRECT_BYPASS_ELIMINATION_V1`:

1. `BYPASS-CHANNEL-001`

   Wrap `ChannelConnectorRuntime` outbound send so product/operator sends go
   through the existing `bounded_channel` ProductActionKernel route. Keep
   `ChannelDraftSendOrganV1` as a backend implementation detail.

2. `BYPASS-MUTATION-001`

   Keep the mutation artifact data plane, but route the final apply step through
   the `workspace_patch` product skill rather than direct
   `L3ReversibleWorkspaceExecutor.execute`.

3. `BYPASS-CERT-001` / `BYPASS-CERT-002`

   Mark certification harnesses as harness-only and prevent their direct organ
   execution from being cited as product proof. Do not delete useful cert code
   in Pack 1.

4. `BYPASS-ORGRT-001`

   Make production organ runtime execution resolve through spec metadata and
   product dispatch where product-reachable. Keep low-level organ runtime as a
   backend/internal compatibility surface.

5. `BYPASS-CLI-001`

   Ensure direct CLI special-authority browser calls are explicit admin/harness
   paths or routed through RuntimeHost. Do not open browser special authorities.

## Current Product Spine Truth

Controlled proof now exists for:

```text
RuntimeHost
-> ModelLedProductActionKernelTaskLoop
-> ProductActionKernelDispatchAdapter
-> ProductActionKernel
-> code_execution_sandbox
-> bounded fake/local channel
-> receipts / FinalGate
-> replay no-react
```

Still not unified:

```text
channel_adapter direct organ backend
mutation artifact final apply
real_model_certification direct organ calls
agent organ runtime branch matrix
browser L5/L6 organ stack
PowerRuntime actuator path
GovernedSkillFabric isolated path
WorkerFleet as product mission commander
signed mission export verifier
```

## Monster Runtime Scorecard Update

| Metric | Pack 0 status |
|---|---|
| `product_spine_coverage` | unchanged by docs-only pack; controlled proof remains code + fake/local channel |
| `direct_bypass_count` | baseline established: 20 census rows |
| `dual_path_count` | baseline established: channel, mutation, certification, organ runtime, browser, PowerRuntime, SkillFabric, worker paths |
| `model_facing_primitive_leakage_count` | unchanged |
| `recoverable_failure_continuation_coverage` | unchanged |
| `real_provider_product_loop_proof` | unchanged |
| `replay_parity_coverage` | unchanged |
| `browser_product_backend_coverage` | unchanged; browser rows now explicitly tracked |
| `agent_workspace_readiness` | unchanged |
| `multi_worker_orchestration_readiness` | unchanged; worker row tracked |
| `signed_mission_artifact_readiness` | unchanged |

## Hard Stops Preserved

This census does not weaken:

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

## Recommended Next Action

Proceed to:

```text
POWER_UNIFICATION_PACK_1_DIRECT_BYPASS_ELIMINATION_V1
```

Pack 1 should be narrow but real:

```text
remove/wrap the highest-value safe bypasses
keep useful organs as backends
keep high-risk surfaces locked
prove product/operator paths call RuntimeHost/ProductActionKernel rather than direct organ.execute
```
