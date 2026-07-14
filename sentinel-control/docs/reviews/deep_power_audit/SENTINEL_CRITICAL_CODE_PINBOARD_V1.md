# SENTINEL_CRITICAL_CODE_PINBOARD_V1

## Purpose

This file pins the highest-importance Sentinel code files for the next Monster
Runtime work. It is not a new audit workstream. It is a navigation board for the
files that control product power, browser body reliability, receipts, replay,
authority, and the model-facing surface.

Use it with:

```text
SENTINEL_DEEP_POWER_AUDIT_V1_MASTER_REPORT.md
SENTINEL_BROWSER_ORGANS_TECHNOLOGY_AUDIT_V2.md
SENTINEL_BROWSER_CORTEX_REAL_CALIBRATION_ON_NON_HOLDOUT_SITES_V1_REPORT.md
SENTINEL_REAL_BROWSER_BODY_SESSION_LIFECYCLE_AND_ACTUATION_STABILITY_V1_STAGE0_REVIEW.md
sentinel-audit/deep-code-audit/*
```

Doctrine:

```text
MODEL = brain / strategy / adaptation
SENTINEL = body / senses / runtime / memory / proof / authority
```

The next code work must not spread randomly. Touch Tier 0 first, then Tier 1.

## Tier 0 - Monster Spine Files

These files are the critical path. A regression here breaks the whole product
runtime, not just one feature.

| Priority | File | Why It Is Critical | Current Attention |
|---|---|---|---|
| P0 | `sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py` | Central product entrypoint and route registration. Owns `RuntimeHost -> ProductActionKernelDispatchAdapter` wiring and currently creates the real browser runtime per dispatch. | Fix browser body/session ownership here or in a root-owned helper consumed here. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py` | Multi-turn model-led product loop. Creates child missions per material action and decides whether failures recover or terminalize. | Needs root-task browser lease/finally cleanup and body failure circuit breaker. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/operator/unified_execution_dispatcher.py` | ProductActionKernel dispatch, receipt writing, proof verification, FinalGate handoff. | Must keep receipts/replay intact while runtime resources move below it. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/operator/action_kernel.py` | Internal runtime language and executor bridge. | ActionEnvelope remains internal; do not expose internals back to the model. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/operator/mission_workspace_runtime.py` | Mission body handles for workspace, browser session, channel grants, worker pool, receipts, replay, artifacts. | Browser handle must become connected to real root-session ownership, not data-only decoration. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py` | Browser skill runtime, Cloak-first engine bridge, readiness probe, browser receipts, search/extract/verify semantics. | Immediate focus: lifecycle close/reuse, operational readiness, no repeated provider burn after body failure. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/agent/organs/browser_session_manager_l5_live.py` | Live L5 browser body: session open/observe/interact/close, snapshots, receipts, sanitizer. | Must be reused/root-owned correctly; actuation stays here, not model-facing. |
| P0 | `sentinel-control/services/sentinel-core/sentinel/organs/browser/cloak_backend.py` | Product-leading live browser backend. Creates persistent contexts and pages. | No silent Playwright fallback. Exact open/close ownership must be clear. |

## Tier 1 - Browser Cortex And Model Surface

These files decide what the model sees and whether Sentinel is a fluid body
instead of a brittle controller.

| Priority | File | Why It Is Critical | Current Attention |
|---|---|---|---|
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/browser_environment_state.py` | Unified browser world-state contract: page identity, controls, result regions, entities, blockers, uncertainty. | Must be fed by real Cloak/session state after lifecycle stabilizes. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/browser_world_model.py` | Browser perception/world model and candidate generation. | Candidate/evidence generator, not final semantic judge. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/browser_decision_frame.py` | Compact browser decision frame for model. | Keep skill-first; no raw Playwright/Cloak locator language as primary. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/browser_model_native_control_loop.py` | Natural/semi-structured model intent mapping to browser skills. | Preserve model freedom while mapping safe intent to executable skills. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py` | General model-facing decision context. | Must prioritize skill frames and recoverable observations without legacy primitive leakage. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/actionability_registry.py` | Declares executable model-visible actions versus internal primitives. | Must remain tied to real executors, not static wish lists. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/power_skill_registry.py` | Skill/backend/organ ownership map. | Important for deciding product backend truth and hidden organ bindings. |

## Tier 1 - Proof, Replay, And Mission Truth

These files make Sentinel more than a tool-calling agent. They are the truth
layer.

| Priority | File | Why It Is Critical | Current Attention |
|---|---|---|---|
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/store.py` | Mission run store, record/events/artifact writes, Windows path behavior. | Relevant to calibration top-level `FileNotFoundError`. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/kernel.py` | Mission lifecycle and event spine. | Must preserve lifecycle truth while long browser tasks stabilize. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/mission_artifact_bundle.py` | Exportable mission proof bundle. | Ensure browser/session receipts become verifiable without side effects. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_replay.py` | Browser replay/no-react proof. | Must prove no reopen/reclick/retype/reextract. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/agent/final_gate.py` | Agent-level final proof gate. | Avoid duplicate or contradictory proof ownership. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/organs/browser/final_gate.py` | Browser-specific final gate. | Candidate for consolidation under shared product proof semantics. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py` | Telemetry execution class and material proof expectations. | Keep degraded/unavailable telemetry honest; do not fake certified mode. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/telemetry/store.py` | Telemetry persistence and tamper/degraded behavior. | Watch for write failures masking mission truth. |

## Tier 1 - Product Limbs

These are major powered limbs already connected or partly connected to the
product spine.

| Priority | File | Why It Is Critical | Current Attention |
|---|---|---|---|
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/workspace_patch_runtime.py` | Workspace mutation limb. | Keep workspace-bounded writes strong and replay no-reapply. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/code_execution_sandbox_runtime.py` | Bounded code execution limb. | Keep sandbox/profile execution useful without shell expansion. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/connection_live_channel_action_runtime.py` | Bounded channel send limb. | Preserve mission grant -> send -> receipt -> replay no-resend. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/worker_orchestration_runtime.py` | Worker orchestration through product spine. | Needed for multi-worker long tasks after browser body stabilizes. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/worker_fleet.py` | Worker fleet backend. | Hidden backend; workers cannot expand authority. |
| P1 | `sentinel-control/services/sentinel-core/sentinel/operator/worker_replay.py` | Worker replay/no-respawn proof. | Required for signed mission artifact verifier. |

## Tier 2 - Legacy / Dual-Path / Bypass Watchlist

These files are important because they may bypass, duplicate, or confuse the
product spine. Do not delete blindly; classify and wrap deliberately.

| Priority | File | Why It Matters | Desired Direction |
|---|---|---|---|
| P2 | `sentinel-control/services/sentinel-core/sentinel/agent/organs/runtime_execution.py` | Branch-heavy organ execution and global browser managers. | Hidden backend only; no product bypass. |
| P2 | `sentinel-control/services/sentinel-core/sentinel/agent/organs/organ_dispatch.py` | Legacy organ dispatch surface. | Keep declarative/spec-owned where possible. |
| P2 | `sentinel-control/services/sentinel-core/sentinel/organs/registry.py` | Organ registry truth. | Align with product skill/backend registry. |
| P2 | `sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter.py` | Historical channel route. | Ensure product channel path owns dispatch/proof. |
| P2 | `sentinel-control/services/sentinel-core/sentinel/operator/mutation_artifact_channel.py` | Mutation artifact/channel bridge. | Avoid direct execution bypass. |
| P2 | `sentinel-control/services/sentinel-core/sentinel/operator/real_model_certification.py` | Large historical real-provider certification path. | Mine for evidence, but avoid making it the product spine. |
| P2 | `sentinel-control/services/sentinel-core/sentinel/agent/runtime.py` | Large agent runtime monolith. | Keep useful organs/backends; do not let it shadow ProductActionKernel. |

## Immediate Review Order

For `REAL_BROWSER_BODY_SESSION_LIFECYCLE_AND_ACTUATION_STABILITY_V1`, inspect and
change in this order:

```text
1. runtime_host.py
2. model_led_product_action_kernel_task_loop.py
3. real_browser_control_runtime.py
4. browser_session_manager_l5_live.py
5. cloak_backend.py
6. mission_workspace_runtime.py
7. unified_execution_dispatcher.py
8. real_browser_control_replay.py
9. store.py
```

Reason:

```text
The reproduced failure is lifecycle ownership:
root product task wants a continuous browser body,
but live Cloak contexts are created per child action and not explicitly closed
or reused by the root task.
```

## Monster Runtime Rule For These Files

When touching a pinned file, every change must answer:

```text
Does this remove a blocker?
Does this hide an internal primitive from the model?
Does this wire a dormant organ into the product spine?
Does this convert terminal in-scope failure into recovery?
Does this preserve hard stops for real damage?
Does this preserve receipts, replay and FinalGate truth?
```

If the answer is no to all of them, do not touch the file.
