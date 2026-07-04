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
| `product_spine_coverage` | RuntimeHost has Pack 10 product task-loop entrypoint; broader power still partial | Increase until all production skills route through the product spine |
| `direct_bypass_count` | Known bypasses remain in channel, mutation, certification, and organ paths | Decrease toward zero for product/operator execution |
| `dual_path_count` | Unified/product paths and organ/direct paths both exist | Decrease by wiring organs as backends |
| `model_facing_primitive_leakage_count` | Reduced by skill frames and Pack 10, but legacy/browser primitives still exist | Decrease; model sees skills first |
| `recoverable_failure_continuation_coverage` | Improved by Pack B and cleanup packs | Increase across all product skills |
| `real_provider_product_loop_proof` | Not yet proven for Pack 10 RuntimeHost entrypoint | Prove next |
| `replay_parity_coverage` | Strong read-only, improving for code/channel/workspace | Increase to all product skills |
| `browser_product_backend_coverage` | Browser remains split across organ and product paths | Increase after agent workspace/bypass work |
| `agent_workspace_readiness` | Not first-class product body yet | Build before full browser promotion |
| `multi_worker_orchestration_readiness` | WorkerFleet exists, not product-led mission commander path | Add after workspace runtime |
| `signed_mission_artifact_readiness` | Receipts/certs exist, export verifier not complete | Add final verifier/export lane |

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

   Prove Pack 10 is more than local structure:

   ```text
   real/controlled model decision
   -> RuntimeHost product task-loop entrypoint
   -> ModelLedProductActionKernelTaskLoop
   -> ProductActionKernel
   -> code/workspace/fake-local channel skills
   -> receipts
   -> finish
   -> replay no-react
   ```

3. `POWER_UNIFICATION_PACK_0_DIRECT_BYPASS_AND_DUAL_PATH_CENSUS_V1`

   Convert deep-code-audit bypass findings into an executable migration table:

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

## Current Next Action

```text
REAL_POWER_ATTEMPT_PRODUCT_TASK_LOOP_RUNTIMEHOST_ENTRYPOINT_V1
```

This is the next product truth test. If it fails, fix the exposed product-spine
blocker before starting more broad unification work.
