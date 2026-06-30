# Sentinel Global Power Reconnection Correction Plan V1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan pack-by-pack. Do not start implementation until the user accepts the pack sequence.

**Goal:** Reconnect Sentinel's existing power across the whole system, not only browser, so the model can use real capabilities through simple skills while receipts, authority, replay, and hard stops remain in the background.

**Architecture:** Sentinel currently has strong organs and proof systems, but the intelligence plane, actionability plane, authority plane, and proof plane are not consistently joined. The correction is to introduce a product skill spine and actionability contract that every power surface uses, then simplify duplicated and branch-heavy paths.

**Tech Stack:** Python, Sentinel operator runtime, AgentRuntime, PowerRuntime, ActionKernel, ModelLedTaskLoop, DecisionContext, MissionAuthorityEnvelope, runtime host/dispatcher, organs, receipts, replay, FinalGate.

---

## Living Plan Rule

This plan is the global correction contract until the reconnection work is complete.

Every future pack must explicitly answer:

```text
which audit finding does this fix?
which connection plane changes?
which module owns the correction?
which old friction or duplicate path is removed, hidden, or marked internal?
what power becomes easier for the model?
what real-damage hard stops remain intact?
what audit tables/docs need to be updated?
```

If a proposed pack only fixes a local symptom and does not map back to one of the audit findings, it should be rejected or reframed before coding.

Per-pack governance loop:

```text
open pack audit
implement correction
re-audit correction
approve/lock pack
compare against big audit
update audit/control docs
start next pack only after state is current
```

## Correction Progress Ledger

| Date state | Correction | Commit | Audit mapping | Product proof state |
|---|---|---|---|
| locked | Deep power audit and generated inventories | `6ad17cd` | Baseline map of code, organs, connections, simplification candidates | control document |
| foundation accepted | `POWER_CORE_PACK_1_ACTIONABILITY_AND_SKILL_REGISTRY_V1` | `2172a14` | P0: model-visible action not guaranteed executable | not product-proven until decision clients consume `model_visible_*` as primary truth |
| implemented candidate | `POWER_RECONNECTION_PACK_B_RECOVERABLE_EXECUTION_CONTRACT_V1` | `5fc3a0c` | P0: recoverable in-scope runtime miss becomes mission death | focused proof: in-scope executor timeout becomes recoverable observation and loop continues |
| implemented candidate | `POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1` | `pending_followup_ledger` | P1: powerful organs are underconnected and backend ownership is invisible to model-facing skills | focused proof: skills map to organ/backend truth without enabling new RuntimeHost adapters |

Current next correction:

```text
POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1
```

Pack B did not ignore Pack A: it audited `model_visible_*` consumption and found the full model decision migration still belongs to Pack D. Pack C wired dormant organs into product skills without bypassing the new actionability and recoverable-execution contracts. Pack D must now make the skill/backend frames primary model decision truth.

## Correction To Previous Focus

The previous response over-focused on browser because Alibaba was the most recent visible failure.

That was too narrow.

Browser is a symptom. The system-level problem is:

```text
Sentinel has many powerful organs,
but only a small fraction is product-native,
and the model is often shown fragile internal actions instead of reliable skills.
```

The full audit found problems across:

```text
product dispatch
action/executor aliases
recoverable failure handling
loop truth and finish logic
read-only dominance
workspace patch integration
code execution loop integration
channel send idempotency/generalization
browser stack fragmentation
external API / desktop / voice / finance lockout and readiness
replay proof parity
FinalGate/proof duplication
organ dispatch branch matrices
monolithic certification/runtime files
```

Therefore the next work must be a global reconnection sequence, not a browser-only pack.

## Situation Summary

### What Sentinel Has

| Power / subsystem | Exists? | Product-used today? | Main issue |
|---|---:|---:|---|
| Real model provider route | yes | yes | Works when endpoint/credential correct |
| Read-only research product route | yes | yes | Too central; should become one skill, not the whole product center |
| Workspace patch | yes | partial | Works in power loop, not fully product-dispatch native |
| Code execution sandbox | yes | partial | Works in loop; alias/context and verification path fragile |
| Channel send | yes | partial | Real Telegram proven; general product wiring/idempotency still fragile |
| Browser control | yes | partial | Many organs, but latest real path bypasses stronger Cloak/session organs |
| External API | yes | no | Bounded organ exists, not product-active |
| Desktop / voice | yes | no | Mostly fake/injected/control-plane readiness |
| Credential vault | yes | no materialized power | Safe metadata/lease concepts, not real credential materializer |
| Finance/account/payment | yes | locked | Should remain special authority only |
| Receipts / replay / FinalGate | yes | yes | Strongest on read-only; uneven on newer power surfaces |

### What Sentinel Uses Well

```text
cockpit -> mission -> dispatcher -> read_only_research_adapter -> receipts -> FinalGate -> replay
```

### What Sentinel Uses Poorly

```text
workspace_patch
code_execution_sandbox
channel_send
browser_control
external_api
desktop
voice
credentialed browser
```

They exist, but are scattered across harnesses, opt-in demos, organ routes, fake/local paths, or special authority packs.

## Responsibility Map

| Component | Real responsibility | Current failure |
|---|---|---|
| `ActionKernel` | Execute canonical skill/action envelopes | Does not universally prove action is currently visible/executable/authorized; wraps many errors as terminal |
| `ModelLedTaskLoop` | Let model drive multi-step work | Terminalizes recoverable in-scope misses; has pack-specific finish/proof branches |
| `DecisionContext` | Tell model what it can do next | Exposes primitive/static actions, not always live executable skills |
| `RuntimeHost` / dispatcher | Product-native power dispatch | Default path is read-only centered |
| `RuntimeConnectionRegistry` | Visibility of connections | Registry readiness is not execution readiness |
| `MissionAuthorityEnvelope` / issuer | Grant bounded authority | Strong, but actionability and alias layers do not always align with it |
| `ReadOnlyProductionSpine` | Proven read-only evidence path | Too dominant; should be one evidence skill in a larger spine |
| `WorkspacePatchRuntime` | Apply bounded patches | Works, but product integration and replay parity need strengthening |
| `CodeExecutionSandboxRuntime` | Run bounded code/checks | Works, but alias/context/verification path can break real loops |
| `ConnectionLiveChannelActionRuntime` / channel adapter | Send bounded messages | Real send proven; idempotency ledger and product generalization need work |
| Browser organs | Operate web/computer surface | Power is split across many stacks; Cloak/session organ not wired into Pack 6 path |
| Replay modules | Prove no re-execution | New power surfaces weaker than read-only replay validation |
| FinalGate | Certify truth | Proof ownership duplicated and sometimes certifies blocked truth after avoidable runtime failures |
| Telemetry kernel | Material truth and events | Boilerplate-heavy and can slow new power surfaces |

## Problem Taxonomy

### P0: Model-visible action is not guaranteed executable

Symptoms:

```text
model sees action
alias differs from executor
executor missing or backend missing
ref/action stale
authority envelope does not match visible operation name
mission blocks
```

Affected surfaces:

```text
read_only aliases
code_exec vs code_execution_sandbox
real_browser primitive refs
channel_transport vs bounded_channel names
browser_live_operator route visibility
```

Correction:

```text
global actionability registry + skill exposure frame
```

### P0: Recoverable in-scope runtime miss becomes mission death

Symptoms:

```text
locator timeout
hidden/disabled element
stale ref
schema mismatch with visible content
patch hash stale
temporary dynamic page miss
```

should become:

```text
recoverable observation -> refreshed context -> next action/recovery
```

not:

```text
ActionKernelError -> FinalGate blocked -> mission death
```

Correction:

```text
recoverable execution contract
```

### P1: Product dispatcher is too read-only centered

Read-only was the first proven product route. Good.

But now it is blocking architecture gravity:

```text
workspace patch
code exec
channel send
browser
```

must become product skills, not side harnesses.

Correction:

```text
product power skill registry + dispatcher integration
```

### P1: Loop truth can be wrong

Problems found:

```text
material budget can complete without proof
finish/proof logic is pack-specific
browser proof forces assert_text
wait_for_text cannot satisfy completion
extraction alone can satisfy control mission
```

Correction:

```text
mission-type proof policy + objective truth contract
```

### P1: Replay proof parity is uneven

Read-only replay is strong.

Newer surfaces often check:

```text
counts
deltas
hash stability
```

but not always:

```text
receipt schema validity
mission id linkage
FinalGate linkage
receipt hash validity
artifact model validity
```

Correction:

```text
power replay validator suite
```

### P1: Organ power is split from skill power

Examples:

```text
CloakBrowser exists but Pack 6 real_browser path uses PlaywrightRealBrowserEngine.
Browser recovery organs exist but recent loop still blocks on locator timeout.
Channel send exists but product generalization still needs exact grant/transport wiring.
External API organ exists but not product-active.
```

Correction:

```text
organ-to-skill wiring layer
```

### P2: Codebase simplification debt slows power

Hotspots:

```text
real_model_certification.py = 4773 lines
agent/runtime.py = 3250 lines
agent/final_gate.py = 3033 lines
agent/organs/runtime_execution.py = 2438 lines
read_only_operator_spine.py = 2266 lines
organs/browser/final_gate.py = 1964 lines
organ_dispatch.py = 1839 lines
```

Correction:

```text
phase extraction, spec registry, proof owner merge, telemetry descriptors
```

## Global Pack Sequence

### Pack 0: Audit Lock And Truth Commit

Name:

```text
POWER_CORE_PACK_0_DEEP_AUDIT_LOCK_AND_TRUTH_BASELINE_V1
```

Goal:

```text
Commit the audit artifacts and establish this plan as canonical before code changes.
```

Files:

```text
sentinel-control/docs/reviews/deep_power_audit/*
```

Validation:

```text
git diff --check -- sentinel-control/docs/reviews/deep_power_audit
targeted secret scan on sentinel-control/docs/reviews/deep_power_audit
```

Do not run provider.

### Pack 1: Actionability And Skill Registry

Name:

```text
POWER_CORE_PACK_1_ACTIONABILITY_AND_SKILL_REGISTRY_V1
```

Goal:

```text
Create one source of truth for what the model can see and what is truly executable now.
```

Primary files:

```text
sentinel/operator/action_power_contract.py
sentinel/operator/action_kernel.py
sentinel/operator/decision_context.py
sentinel/operator/runtime_connections.py
sentinel/operator/runtime_host.py
```

Likely create:

```text
sentinel/operator/actionability_registry.py
sentinel/operator/power_skill_registry.py
tests/operator/test_power_core_actionability_registry.py
```

Must cover:

```text
read_only_research
workspace_patch
code_execution_sandbox
bounded_channel
real_browser_control
external_api
desktop/voice locked state
finance/account/payment locked state
```

Core invariant:

```text
No action is shown to the model unless:
executor exists
backend available or explicitly fake/local
authority compatible
proof requirement known
recovery policy known
```

Tests:

```text
test_registry_exposes_only_executable_actions
test_read_only_aliases_resolve_to_one_canonical_skill
test_code_exec_alias_resolves_to_code_execution_sandbox
test_channel_send_exposed_only_with_transport_and_destination_grant
test_browser_low_level_primitives_hidden_when_skill_exists
test_external_api_locked_until_authority_and_backend
test_high_risk_surfaces_keep_locked
```

### Pack 2: Recoverable Runtime Contract

Name:

```text
POWER_CORE_PACK_2_RECOVERABLE_RUNTIME_CONTRACT_V1
```

Goal:

```text
Hard stop only on real damage. In-scope runtime failure becomes recovery.
```

Primary files:

```text
sentinel/operator/action_kernel.py
sentinel/operator/action_power_contract.py
sentinel/operator/model_led_task_loop.py
sentinel/operator/decision_context.py
```

Likely create:

```text
sentinel/operator/action_failure_policy.py
tests/operator/test_power_core_recoverable_runtime_contract.py
```

Hard stop classes:

```text
authority_scope_violation
credential_or_secret_access
payment_checkout_or_trade
external_send_outside_grant
workspace_escape
destructive_ungranted_write
provider_native_tool_use
fallback_auto_route
raw_material_persistence_risk
```

Recoverable classes:

```text
stale_ref
hidden_or_disabled_target
locator_timeout
dynamic_loading
schema_shape_miss
alias_mismatch
backend_candidate_failed
proof_not_yet_satisfied
```

Tests:

```text
test_stale_ref_becomes_recoverable_observation
test_locator_timeout_becomes_recoverable_observation
test_schema_miss_with_visible_content_becomes_recovery
test_workspace_escape_remains_hard_stop
test_credential_request_remains_hard_stop
test_loop_continues_after_recoverable_observation
test_recovery_budget_blocks_honestly_without_fake_success
```

### Pack 3: Product Dispatch Power Wiring

Name:

```text
POWER_CORE_PACK_3_PRODUCT_DISPATCH_POWER_WIRING_V1
```

Goal:

```text
Promote proven power skills from harness/loop/demo into product-native dispatch.
```

Primary files:

```text
sentinel/operator/runtime_host.py
sentinel/operator/runtime_connections.py
sentinel/operator/unified_execution_dispatcher.py
sentinel/operator/mission_execution_coordinator.py
```

Surface targets:

```text
read_only_research remains connected
workspace_patch becomes product skill
code_execution_sandbox becomes product skill
bounded_channel becomes product skill
real_browser_control becomes product skill frontend
external_api remains locked/readiness only
desktop/voice/finance remain locked/readiness only
```

Tests:

```text
test_product_dispatch_lists_read_patch_code_channel_browser_skills
test_default_read_only_route_still_works
test_workspace_patch_skill_dispatches_only_with_authority
test_code_exec_skill_dispatches_only_with_profile_authority
test_channel_skill_dispatches_only_with_destination_grant
test_browser_skill_dispatches_only_with_origin_scope
test_high_risk_surfaces_not_product_dispatchable
```

### Pack 4: DecisionContext Skill Frames

Name:

```text
POWER_CORE_PACK_4_DECISION_CONTEXT_SKILL_FRAMES_V1
```

Goal:

```text
Stop presenting internal APIs. Present mission skills and proof state.
```

Primary files:

```text
sentinel/operator/decision_context.py
sentinel/operator/model_led_task_loop.py
sentinel/operator/browser_decision_frame.py
sentinel/operator/browser_world_model.py
```

Likely create:

```text
sentinel/operator/skill_decision_frame.py
sentinel/operator/read_only_skill_frame.py
sentinel/operator/workspace_patch_skill_frame.py
sentinel/operator/code_execution_skill_frame.py
sentinel/operator/channel_skill_frame.py
sentinel/operator/browser_skill_frame.py
tests/operator/test_power_core_decision_context_skill_frames.py
```

Skill frame schema:

```text
mission_objective
current_progress
available_skills
recommended_next_skills
recent_receipts
recoverable_observations
proof_requirements
finish_available
hard_stop_boundaries
```

Tests:

```text
test_read_only_frame_recommends_evidence_skill
test_workspace_patch_frame_requires_patch_and_verification
test_code_exec_frame_requires_run_and_bounded_check
test_channel_frame_requires_send_then_finish
test_browser_frame_recommends_search_extract_not_type_text
test_finish_available_only_after_required_proof
```

### Pack 5: Objective Truth And Proof Policy

Name:

```text
POWER_CORE_PACK_5_OBJECTIVE_TRUTH_AND_PROOF_POLICY_V1
```

Goal:

```text
Mission completion must mean objective proof, not budget exhaustion.
```

Primary files:

```text
sentinel/operator/model_led_task_loop.py
sentinel/operator/decision_context.py
sentinel/operator/loop_guard.py
sentinel/operator/*_replay.py
```

Likely create:

```text
sentinel/operator/objective_proof_policy.py
tests/operator/test_power_core_objective_truth_policy.py
```

Proof policy by surface:

| Surface | Required proof |
|---|---|
| Read-only research | evidence receipt or report/evidence refs |
| Workspace patch | patch receipt plus readback/check receipt |
| Code execution | execution receipt plus bounded check receipt |
| Channel send | delivery receipt plus finish/no-resend replay |
| Browser research | extraction/product card or wait/assert proof |
| Browser control | material state change plus proof |
| External API | dry-run/response receipt; mutation locked |

Tests:

```text
test_material_budget_without_proof_blocks_or_enters_proof_lane
test_patch_only_does_not_complete_without_verification
test_code_exec_without_check_does_not_complete
test_channel_delivery_then_finish_completes
test_browser_extraction_can_satisfy_research_but_not_control_without_action
test_wait_for_text_can_satisfy_browser_proof_when_policy_allows
```

### Pack 6: Replay And Receipt Parity

Name:

```text
POWER_CORE_PACK_6_REPLAY_AND_RECEIPT_PARITY_V1
```

Goal:

```text
Every power surface gets read-only-grade replay truth.
```

Primary files:

```text
sentinel/operator/read_only_operator_spine.py
sentinel/operator/workspace_patch_replay.py
sentinel/operator/code_execution_sandbox_runtime.py
sentinel/operator/browser_control_replay.py
sentinel/operator/real_browser_control_replay.py
sentinel/operator/connection_live_channel_action_runtime.py
sentinel/operator/channel_adapter_models.py
```

Likely create:

```text
sentinel/operator/power_replay_validator.py
tests/operator/test_power_core_replay_receipt_parity.py
```

Required replay invariants:

```text
no provider call delta
no tool/action delta
no patch apply delta
no code execution delta
no channel resend
no browser reopen/reclick/retype
no receipt write delta
receipt schema valid
receipt hash stable
mission id linkage valid
FinalGate linkage valid
workspace/browser/channel material state stable
```

### Pack 7: Organ-To-Skill Wiring

Name:

```text
POWER_CORE_PACK_7_ORGAN_TO_SKILL_WIRING_V1
```

Goal:

```text
Turn existing organs into backends for skills.
```

Primary organ families:

```text
browser organs
channel organs
external_api organs
desktop organs
credential organs
financial/account organs
```

Primary files:

```text
sentinel/organs/registry.py
sentinel/agent/organs/organ_dispatch.py
sentinel/agent/organs/runtime_execution.py
sentinel/operator/power_skill_registry.py
```

Likely create:

```text
sentinel/operator/organ_skill_binding.py
tests/operator/test_power_core_organ_skill_wiring.py
```

Rules:

```text
An organ can be KEEP_LOCKED while still visible as non-dispatchable.
An organ can be WIRE only if it has authority, backend, receipt, replay story.
An organ can be HIDE if it is compatibility/internal.
An organ can be MERGE if duplicated ownership exists.
```

### Pack 8: First Code Simplification Cut

Name:

```text
POWER_CORE_PACK_8_FIRST_CODE_SIMPLIFICATION_CUT_V1
```

Goal:

```text
Reduce code that taxes power without deleting useful organs.
```

Targets:

```text
organ_dispatch.py
runtime_execution.py
agent/runtime.py phase extraction
real_model_certification.py harness split
FinalGate browser proof owner merge
telemetry descriptor-driven events
```

Do not start by deleting large files.

Start by extracting:

```text
spec registries
phase engines
shared receipt/proof primitives
```

Tests:

```text
existing browser/channel/workspace/code/read-only focused suites
compileall touched modules
git diff --check
targeted secret/raw-provider/provider-native/fallback scan
```

## Surface-Specific Follow-Ups After Core Packs

### Browser Pack

Name:

```text
POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

Now it becomes valid after Packs 1-7.

### Workspace + Code Pack

Name:

```text
POWER_PACK_WORKSPACE_CODE_PRODUCT_NATIVE_LOOP_V1
```

Goal:

```text
real model can patch, run bounded check, verify, finish through product dispatch.
```

### Channel Pack

Name:

```text
POWER_PACK_REAL_CHANNEL_GENERALIZED_DESTINATION_SCOPE_V1
```

Goal:

```text
generalize Telegram/local webhook success into bounded destination skill without per-message approval.
```

### External API Pack

Name:

```text
POWER_PACK_EXTERNAL_API_BOUNDED_DRY_RUN_TO_READ_ACTION_V1
```

Goal:

```text
safe read/dry-run API action with receipts, no mutation.
```

### Desktop/Voice Pack

Name:

```text
POWER_PACK_DESKTOP_VOICE_OBSERVE_FIRST_SKILLS_V1
```

Goal:

```text
observe/summarize only first, no desktop mutation yet.
```

### Credential Pack

Name:

```text
POWER_PACK_CREDENTIAL_LEASE_MATERIALIZER_V1
```

Goal:

```text
scoped lease execution without persisting raw credential values.
```

Only after product skill spine and replay parity are solid.

## What Not To Do

Do not:

```text
start browser 6D immediately
add more security-only manifest packs
add more docs that don't unlock action
delete CloakBrowser/session organs
delete receipts/replay/FinalGate
let model pilot Playwright/runtime internals
make product dispatcher read-only-only forever
call a fake/local harness product proof
mark budget exhaustion as success without objective proof
```

## Recommended Immediate Next Action

```text
POWER_CORE_PACK_0_DEEP_AUDIT_LOCK_AND_TRUTH_BASELINE_V1
```

Then:

```text
POWER_CORE_PACK_1_ACTIONABILITY_AND_SKILL_REGISTRY_V1
```

This is the correct starting point because every other power surface depends on it.
