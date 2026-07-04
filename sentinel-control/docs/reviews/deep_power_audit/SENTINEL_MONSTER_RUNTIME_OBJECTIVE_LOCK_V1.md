# Sentinel Monster Runtime Objective Lock V1

Status: objective/control lock.
Runtime behavior changes: 0.
Provider calls: 0.
Real browser runs: 0.
Real external channel calls: 0.
Push: not performed.

## Purpose

This document is the final north-star control lock for Sentinel's power
unification work.

The objective is not to add another isolated capability. The objective is to
turn Sentinel into a model-led operating runtime:

```text
one mission grant
-> model-led multi-step task loop
-> RuntimeHost
-> ProductActionKernel
-> skill runtimes / organs as hidden backends
-> receipts + replay + FinalGate
-> hard stop only real damage
```

Canonical doctrine:

```text
MODEL = brain / strategy / adaptation
SENTINEL = body / runtime / skills / memory / proof / boundaries
```

## Operating Laws

1. One product spine.

   Product execution should converge on:

   ```text
   RuntimeHost
   -> ModelLedProductActionKernelTaskLoop
   -> UnifiedExecutionDispatcher / ProductActionKernelDispatchAdapter
   -> ProductActionKernel
   -> skill runtime or organ backend
   -> receipt
   -> replay / FinalGate
   ```

2. Simple model-facing skills.

   The model should see mission skills such as:

   ```text
   read
   patch
   run_check
   browse_search
   extract
   send_message
   spawn_worker
   remember
   finish
   ```

   The model should not need to reason about:

   ```text
   ActionEnvelope internals
   Playwright or Cloak locators
   organ request fields
   Gate or FinalGate modes
   backend selector internals
   legacy primitive recommendations
   ```

3. ActionEnvelope remains internal.

   Model-native intent may be translated into canonical internal action
   envelopes. The envelope is a runtime language, not the user's product
   experience and not the model's primary thinking surface.

4. Organs become hidden backends.

   Existing organs are valuable. Do not delete useful organs to simplify
   appearances. Wire them under product skills, classify them as internal or
   locked when needed, and remove direct product bypasses.

5. Recover by default inside granted scope.

   Normal in-scope runtime misses should become recoverable observations:

   ```text
   stale ref
   timeout
   schema miss
   backend candidate failed
   dynamic loading
   hidden non-secret element
   proof not yet satisfied
   ```

6. Hard stop only real damage.

   These remain hard stops unless a future explicit special-authority mission
   grants them:

   ```text
   payment / checkout / spend
   credential or secret access
   login / account mutation
   contact supplier or external send outside grant
   destructive write outside authority
   workspace escape
   cookies / session / raw DOM / raw screenshot persistence
   provider-native tools
   fallback/AUTO
   replay causing real side effects
   proof tampering / fake receipt
   ```

7. Receipts, replay, and FinalGate stay in the background.

   Proof should be strong and mostly invisible to the model. Sentinel should
   not become a compliance dashboard that controls every model step.

## Monster Runtime Scorecard

Every future pack must update this scorecard or explicitly state why it is
unchanged:

| Metric | Current baseline | Desired direction |
|---|---|---|
| `product_spine_coverage` | RuntimeHost product task-loop entrypoint is controlled-proven for code execution, bounded fake/local channel send, browser high-level skills, and worker orchestration | Increase until all production skills route through the product spine |
| `direct_bypass_count` | Pack 0 census baseline: 20 direct bypass / dual-path rows | Decrease toward zero for product/operator execution |
| `dual_path_count` | Pack 0 confirms channel, mutation, certification, organ runtime, browser, PowerRuntime, SkillFabric, worker, and memory dual paths | Decrease by wiring organs as backends |
| `model_facing_primitive_leakage_count` | Reduced by skill frames, Pack 10, Pack 4 browser unification, and Pack 5 worker `spawn_worker` surface | Decrease; model sees skills first |
| `recoverable_failure_continuation_coverage` | Improved by Pack B and cleanup packs | Increase across all product skills |
| `real_provider_product_loop_proof` | Controlled RuntimeHost product loop proven; real provider was not used | Keep separate from controlled proof and prove later only under a named real-provider contract |
| `replay_parity_coverage` | Strong read-only, improving for code/channel/workspace/browser/worker local receipts | Increase to all product skills |
| `browser_product_backend_coverage` | Pack 4 routes browser high-level skills through the product spine with local/fake Cloak-session backend proof | Prove on real bounded browser missions later |
| `agent_workspace_readiness` | Pack 3 adds the mission workspace body; Pack 4 consumes browser_session and Pack 5 consumes worker_pool | Continue consuming this body for workers, artifacts, memory, and replay |
| `multi_worker_orchestration_readiness` | Pack 5 adds product-spine `spawn_worker` with reduced child authority and local worker receipt proof | Add real model-led worker delegation and long-running orchestration later |
| `signed_mission_artifact_readiness` | Pack 6 plus `REAL_POWER_ATTEMPT_SIGNED_MISSION_ARTIFACTS_AND_REPLAY_VERIFIER_V1` prove local hash-chain bundle export and offline verifier on a named controlled product mission | Add real-provider/real-app bundles and external signing later only when real key infrastructure exists |

No pack is accepted unless it does at least one of:

```text
removes a blocker
hides an internal primitive
wires a dormant organ into the product spine
converts a terminal failure into recovery
proves a product route with receipts/replay
updates the living audit truth
```

## Canonical Execution Sequence

1. `SENTINEL_MONSTER_RUNTIME_OBJECTIVE_LOCK_V1`

   This document. Docs/control only.

2. `REAL_POWER_ATTEMPT_PRODUCT_TASK_LOOP_RUNTIMEHOST_ENTRYPOINT_V1`

   Controlled local proof completed. Pack 10 is more than local structure:

   ```text
   controlled model decision
   -> RuntimeHost product task-loop entrypoint
   -> ModelLedProductActionKernelTaskLoop
   -> ProductActionKernel
   -> code/workspace/fake-local channel skills
   -> receipts
   -> finish
   -> replay no-react
   ```

3. `POWER_UNIFICATION_PACK_0_DIRECT_BYPASS_AND_DUAL_PATH_CENSUS_V1`

   Completed docs-only. Converts deep-code-audit bypass findings into an
   executable migration table:

   ```text
   BYPASS_REMOVE
   BYPASS_WRAP_THROUGH_DISPATCHER
   BYPASS_PRODUCT_WIRE
   BYPASS_KEEP_INTERNAL
   BYPASS_DEPRECATE
   BYPASS_LOCK_HIGH_RISK
   ```

4. `POWER_UNIFICATION_PACK_1_DIRECT_BYPASS_ELIMINATION_V1`

   Start wrapping/removing highest-value safe product bypasses. Do not delete
   useful organs; convert them into backends.

5. `POWER_UNIFICATION_PACK_2_SKILL_ONLY_MODEL_SURFACE_V1`

   Make simple skills the only primary model-facing interface.

6. `POWER_UNIFICATION_PACK_3_AGENT_WORKSPACE_RUNTIME_V1`

   Build the bounded mission workspace as Sentinel's product body:

   ```text
   workspace files
   scratch memory
   code sandbox
   browser session handle
   channel destination grants
   worker pool
   receipt ledger
   replay ledger
   artifact export directory
   ```

7. `POWER_UNIFICATION_PACK_4_BROWSER_L5_L6_PRODUCT_BACKEND_V1`

   Move browser live power under the product skill spine. Cloak/session should
   be the live backend when available. Playwright remains explicit
   compatibility/test backend.

8. `POWER_UNIFICATION_PACK_5_MULTI_WORKER_LONG_TASK_ORCHESTRATION_V1`

   Add model-led worker orchestration with strict child authority.

9. `POWER_UNIFICATION_PACK_6_SIGNED_MISSION_ARTIFACTS_AND_REPLAY_VERIFIER_V1`

   Export independently verifiable mission artifacts:

   ```text
   authority envelope
   decision summaries
   skill actions
   receipts
   FinalGate certificates
   worker receipts
   artifact hashes
   replay proof
   mission summary
   ```

## Required Per-Pack Validation

Every implementation pack must run or justify not running:

```text
focused unit tests for changed behavior
product-spine integration test
replay no-react test
hard-boundary regression test
compileall for touched Sentinel modules
git diff --check
targeted scan for raw provider/reasoning/credential/session/cookie/DOM persistence
```

Every real attempt must report:

```text
model/provider decision calls
skills emitted
receipts created
FinalGate/certificate status
mission status
replay no-react proof
hard-boundary scan
raw material persistence scan
selected backend vs actual backend where relevant
```

## Audit Integration

This lock is a control layer over:

```text
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_GLOBAL_POWER_RECONNECTION_CORRECTION_PLAN_V1.md
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_POWER_RECONNECTION_PACK_SEQUENCE_V1.md
sentinel-audit/deep-code-audit/*
```

The deep-code audit adds an important correction:

```text
Sentinel's strongest gap is no longer missing organs.
The gap is incomplete unification:
direct bypasses, dual paths, skills-as-framing, browser/organs not fully product-spine-owned.
```

## Living Update: Power Unification Pack 1

`POWER_UNIFICATION_PACK_1_DIRECT_BYPASS_ELIMINATION_V1` is implemented as the
first direct-bypass cut.

What changed:

```text
bounded_channel product path now stamps channel adapter receipts with:
backend_id = channel_draft_send_organ_backend
backend_owner = internal_channel_backend
product_dispatch_owner = product_action_kernel_adapter
```

Direct compatibility channel calls keep:

```text
product_dispatch_owner = null
```

This means the channel organ remains useful as a backend, but only the
RuntimeHost/ProductActionKernel route can be counted as product proof.

Mutation artifact apply remains open:

```text
GovernedMutationArtifactChannel.product_wire_status().product_dispatchable = false
```

## Previous Next Action Now Completed

```text
POWER_UNIFICATION_PACK_2_SKILL_ONLY_MODEL_SURFACE_V1
```

Carry forward:

```text
mutation artifact final apply still needs workspace_patch product wiring with rollback parity.
```

## Living Update: Power Unification Pack 2

`POWER_UNIFICATION_PACK_2_SKILL_ONLY_MODEL_SURFACE_V1` is implemented as the
first model-surface cut.

What changed:

```text
DecisionContext.primary_model_surface = model_visible_skills
DecisionContext.primary_model_language = simple_mission_skills
DecisionContext.action_envelope_language = internal_runtime_only
RuntimeHost.product_task_loop_entrypoint_frame now exposes model_visible_skills
ModelLedProductActionKernelTaskLoop context now exposes model_visible_skills
```

The compatibility canonical-action fields remain available for existing
extractors and tests, but the declared primary model surface is now:

```text
read
patch
run_check
browse_search
extract
send_message
finish
```

`spawn_worker` and `remember` stay absent until their product routes exist.

Scorecard delta:

```text
model_facing_primitive_leakage_count = reduced
product_spine_coverage = unchanged
direct_bypass_count = unchanged
dual_path_count = unchanged
real_provider_product_loop_proof = unchanged
```

## Current Next Action

```text
POWER_UNIFICATION_PACK_4_BROWSER_L5_L6_PRODUCT_BACKEND_V1
```

Carry forward:

```text
Future real-provider product loops must prove the provider consumes the simple skill surface and mission workspace body rather than old compatibility canonical-action fields or scattered per-skill workspace state.
```

## Living Update: Power Unification Pack 3

`POWER_UNIFICATION_PACK_3_AGENT_WORKSPACE_RUNTIME_V1` is implemented as the
first product-body foundation.

Implementation commit:

```text
761748d feat: add mission workspace runtime body
```

What changed:

```text
RuntimeHost.mission_workspace_entrypoint_frame
RuntimeHost.prepare_mission_workspace
MissionWorkspaceRuntime
MissionWorkspaceManifest
MissionWorkspaceHandle
```

The mission workspace body now owns safe handles for:

```text
workspace_files
scratch_memory
code_sandbox
browser_session
channel_destination_grants
worker_pool
receipt_ledger
replay_ledger
artifact_export
```

This is data/control-plane only. It does not register a new dispatcher adapter,
enable live external power, call a provider, open a browser, or send a channel
message.

Scorecard delta:

```text
agent_workspace_readiness = increased
product_spine_coverage = structurally improved, product execution unchanged
direct_bypass_count = unchanged
dual_path_count = unchanged
model_facing_primitive_leakage_count = unchanged from Pack 2
real_provider_product_loop_proof = unchanged
replay_parity_coverage = unchanged, but replay ledger handle now exists in the mission body
browser_product_backend_coverage = unchanged, but browser session handle now exists for Pack 4
multi_worker_orchestration_readiness = increased structurally via worker_pool handle
signed_mission_artifact_readiness = increased structurally via artifact_export handle
```

## Living Update: Power Unification Pack 4

`POWER_UNIFICATION_PACK_4_BROWSER_L5_L6_PRODUCT_BACKEND_V1` is implemented as
a local/fake browser product backend proof.

Implementation commit:

```text
d1f2a0d180af337b26cc30c509e78e0822b28c0b feat: route browser through product spine
```

What changed:

```text
real_browser_control registered as a product RuntimeConnectionProfile
RuntimeHost ProductActionKernelDispatchAdapter owns browser high-level routes
ModelLedProductActionKernelTaskLoop exposes browser high-level skills
MissionWorkspaceRuntime browser_session handle is consumed by browser receipts
RealBrowserActionReceipt records product owner, workspace, session, backend truth, and replay behavior
local fake Cloak/session backend proves selected_backend_id == actual_backend_id == cloak_browser
Playwright compatibility requires explicit selection
```

Power gained:

```text
browser is no longer only a special stack outside the product spine
browser high-level search/extract/verify can be dispatched like code/channel/patch
direct browser calls cannot be counted as product proof
raw browser primitives stay hidden from the primary model surface
```

Scorecard delta:

```text
product_spine_coverage = improved
direct_bypass_count = reduced for browser product proof
dual_path_count = reduced
model_facing_primitive_leakage_count = reduced
replay_parity_coverage = improved locally
browser_product_backend_coverage = improved with local/fake Cloak-session backend
agent_workspace_readiness = consumed
real_provider_product_loop_proof = unchanged
multi_worker_orchestration_readiness = unchanged
signed_mission_artifact_readiness = unchanged
```

Next:

```text
POWER_UNIFICATION_PACK_5_MULTI_WORKER_LONG_TASK_ORCHESTRATION_V1
```

## Living Update: Power Unification Pack 5

`POWER_UNIFICATION_PACK_5_MULTI_WORKER_LONG_TASK_ORCHESTRATION_V1` is
implemented as a local/fake worker product-spine proof.

Implementation commit:

```text
a3b0f23723a650032bc2ea1efd587e7d115e0a08 feat: route worker orchestration through product spine
```

What changed:

```text
worker_fleet.spawn_worker registered as a RuntimeHost ProductActionKernel route
model-visible simple skill = spawn_worker
WorkerOrchestrationRuntime consumes the MissionWorkspace worker_pool handle
WorkerFleetRuntime is hidden backend, not a model-facing product path
worker receipts record mission workspace, worker pool, reduced child scope, and replay behavior
child workers cannot expand authority or cross hard boundaries
```

Power gained:

```text
worker orchestration is no longer only dormant structure or local harness logic
future long tasks can delegate to reduced-authority workers through the product spine
worker receipt/replay truth is attached to the same mission body as code/channel/browser
```

Scorecard delta:

```text
product_spine_coverage = improved
direct_bypass_count = reduced for worker orchestration product proof
dual_path_count = reduced
model_facing_primitive_leakage_count = reduced
replay_parity_coverage = improved locally
agent_workspace_readiness = consumed via worker_pool
multi_worker_orchestration_readiness = improved
real_provider_product_loop_proof = unchanged
browser_product_backend_coverage = unchanged
signed_mission_artifact_readiness = unchanged
```

Next:

```text
VISION_FINALE_SENTINEL_100_PERCENT_STRATEGY_DISCUSSION
```

## Living Update: Power Unification Pack 6

`POWER_UNIFICATION_PACK_6_SIGNED_MISSION_ARTIFACTS_AND_REPLAY_VERIFIER_V1`
is implemented as a local/fake product-spine artifact export and offline
verifier proof.

Implementation commit:

```text
7bb5e4b0f6300629bbd04e345aa38efe012349ea feat: export verifiable mission artifact bundles
```

What changed:

```text
MissionArtifactBundleExporter writes a bundle under mission_workspace/artifact_exports
MissionArtifactBundleVerifier verifies only exported JSON, not live runtime state
local_integrity_seal records a deterministic hash-chain integrity proof
external_signature = not_claimed
worker receipts are checked for reduced authority/no expansion
replay proof is checked for no code rerun, no channel resend, no worker respawn, no new receipt/finalgate writes
raw provider/reasoning/DOM/cookie/session/profile markers are rejected
```

Power gained:

```text
Sentinel can now act, receipt, replay, and export a locally verifiable mission proof bundle.
The proof lane consumes the unified mission body instead of creating another special export path.
```

Scorecard delta:

```text
signed_mission_artifact_readiness = improved substantially
replay_parity_coverage = improved through offline verifier checks
agent_workspace_readiness = consumed via artifact_export
multi_worker_orchestration_readiness = improved through worker receipt verification
real_provider_product_loop_proof = unchanged
```

## Living Update: Signed Mission Artifact Verifier Proof

`REAL_POWER_ATTEMPT_SIGNED_MISSION_ARTIFACTS_AND_REPLAY_VERIFIER_V1`
completed the current Monster Runtime phase in controlled/local mode.

```text
verdict = CONTROLLED_VALID_SUCCESS
provider_decision_calls = 0
controlled_model_decision_calls = 4
capability_sequence = code_execution_sandbox -> bounded_channel -> worker_fleet -> sentinel_loop.finish
mission_status = completed
bundle_id = mission_artifact_bundle_9f489d344d218fea
verifier_accepted = true
replay_no_react = true
raw_material_scan_hit_count = 0
```

Scorecard delta:

```text
signed_mission_artifact_readiness = controlled product proof passed
replay_parity_coverage = named bundle verifier proof passed
agent_workspace_readiness = artifact_export consumed in named proof
multi_worker_orchestration_readiness = worker receipt verified in named bundle
real_provider_product_loop_proof = unchanged
```

Stop condition:

```text
No new implementation pack should start before the VISION_FINALE_SENTINEL_100_PERCENT strategy discussion.
```
