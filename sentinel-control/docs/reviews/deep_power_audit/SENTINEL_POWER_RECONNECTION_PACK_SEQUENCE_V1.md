# Sentinel Power Reconnection Pack Sequence V1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement each pack task-by-task. This document is a strategic implementation sequence, not runtime code.

**Goal:** Reconnect Sentinel's existing dormant power before building another browser-specific pack.

**Architecture:** Sentinel already has many organs, but only a small part is product-native and model-usable. The next work should reconnect the action plane, skill plane, authority plane, and proof plane so existing power becomes usable without exposing internal APIs to the model.

**Tech Stack:** Python, Sentinel operator runtime, model-led task loop, ActionKernel, DecisionContext, organ runtimes, browser/session organs, receipts, replay, FinalGate.

---

## Verdict

Do not start `POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1` yet.

6D is still the right browser destination, but it should come after root reconnection packs.

Current diagnosis:

```text
Sentinel has large power inventory.
Only around a small fraction is product-used.
The rest is split across organs, harnesses, direct demos, fake/local loops, and parallel browser stacks.
The next priority is reconnecting and simplifying the runtime spine.
```

## Living Sequence Rule

This sequence is now a live implementation guide. Each pack must be checked against the master deep power audit before implementation, and this file must be updated when a pack is completed, skipped, renamed, split, or superseded.

The rule is:

```text
audit comparison first
implementation second
audit status update third
commit fourth
```

This prevents the work from collapsing back into one visible symptom, such as browser locator failures, while the real issue is cross-system actionability and connection quality.

## Implementation Status

| Sequence item | Canonical implementation | Status | Commit | Notes |
|---|---|---|---|---|
| Pack A: Actionability Registry And Skill Exposure | `POWER_CORE_PACK_1_ACTIONABILITY_AND_SKILL_REGISTRY_V1` | committed | `2172a14` | Introduced global `actionability_registry.py` and `DecisionContext.skill_exposure_frame` |
| Pack B: Recoverable Execution Contract | pending | not started | - | Next likely core correction |
| Pack C: Organ-To-Skill Wiring And Backend Selection | pending | not started | - | Must wire dormant organs into product skills |
| Pack D: Decision Context Skill Frame Simplification | pending | not started | - | Should migrate model prompts/clients to `model_visible_*` |
| Pack E: First Simplification Cut Organ Branch Matrix | pending | not started | - | Should reduce duplicated organ dispatch branches |

New canonical next sequence:

```text
POWER_RECONNECTION_PACK_A_ACTIONABILITY_REGISTRY_AND_SKILL_EXPOSURE_V1
POWER_RECONNECTION_PACK_B_RECOVERABLE_EXECUTION_CONTRACT_V1
POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1
POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1
POWER_RECONNECTION_PACK_E_FIRST_SIMPLIFICATION_CUT_ORGAN_BRANCH_MATRIX_V1
then POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

## Why 6D Is Too Early

Starting 6D now would fix the visible browser symptom:

```text
Alibaba type_text locator timeout
```

But the audit shows deeper root problems:

```text
model-visible actions are not guaranteed executable
recoverable in-scope failures terminalize missions
organ power is split from product dispatcher
CloakBrowser exists but is not wired into the real_browser path
DecisionContext exposes low-level primitives instead of skills
proof/finish logic is pack-specific
```

Therefore 6D should be the first beneficiary of a reconnected core, not the place where every root fix gets improvised.

## Pack A: Actionability Registry And Skill Exposure

Name:

```text
POWER_RECONNECTION_PACK_A_ACTIONABILITY_REGISTRY_AND_SKILL_EXPOSURE_V1
```

Goal:

```text
Only expose model-facing actions that have a live executable plan.
```

Primary files:

```text
sentinel/operator/action_power_contract.py
sentinel/operator/action_kernel.py
sentinel/operator/decision_context.py
sentinel/operator/browser_action_candidates.py
sentinel/operator/browser_world_model.py
```

Create if needed:

```text
sentinel/operator/actionability_registry.py
sentinel/operator/skill_exposure_frame.py
tests/operator/test_power_reconnection_actionability_registry.py
```

Required behavior:

```text
Every action shown to the model has:
- canonical capability id
- canonical operation id
- executor registered yes/no
- authority compatible yes/no
- runtime backend available yes/no
- proof requirement
- recovery policy
```

Model-facing action exposure must not include:

```text
raw Playwright locator actions as preferred browser research actions
unregistered capability aliases
actions outside current mission authority
actions with missing backend
```

Acceptance tests:

```text
test_model_frame_exposes_only_registered_executable_actions
test_code_exec_alias_maps_to_code_execution_sandbox_or_is_hidden
test_real_browser_low_level_actions_are_internal_when_search_skill_available
test_channel_send_exposed_only_when transport_and_destination_grant_exist
test_unregistered_action_is_not_exposed_to_model
```

Validation:

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_actionability_registry.py -q
py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
```

Definition of done:

```text
DecisionContext can build model-facing frames from executable actionability, not from static wish lists.
```

## Pack B: Recoverable Execution Contract

Name:

```text
POWER_RECONNECTION_PACK_B_RECOVERABLE_EXECUTION_CONTRACT_V1
```

Goal:

```text
Separate real hard stops from normal in-scope runtime failures.
```

Primary files:

```text
sentinel/operator/action_kernel.py
sentinel/operator/action_power_contract.py
sentinel/operator/model_led_task_loop.py
sentinel/operator/decision_context.py
```

Create if needed:

```text
sentinel/operator/action_failure_policy.py
tests/operator/test_power_reconnection_recoverable_execution_contract.py
```

Hard stops:

```text
workspace escape
ungranted origin
credential access
payment/checkout
contact supplier/send external message outside grant
destructive write/delete outside grant
provider-native tools
fallback/AUTO
raw secret persistence risk
```

Recoverable observations:

```text
stale ref
locator timeout
hidden/disabled element
schema miss with visible content
alias mismatch
dynamic loading not captured
candidate not found
extractor too shallow
proof branch mismatch
```

Acceptance tests:

```text
test_in_scope_browser_locator_timeout_returns_recoverable_observation
test_unknown_ref_refreshes_actionability_frame
test_out_of_scope_origin_remains_hard_stop
test_credential_action_remains_hard_stop
test_loop_continues_after_recoverable_observation_until_recovery_budget
test_recovery_budget_exhaustion_blocks_honestly
```

Validation:

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
py -3.13 -m pytest tests/operator/test_power_pack5_real_channel_transport_send.py -q
```

Definition of done:

```text
ActionKernel no longer turns every executor exception into terminal mission death.
```

## Pack C: Organ-To-Skill Wiring And Backend Selection

Name:

```text
POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1
```

Goal:

```text
Wire existing organs into product skills instead of leaving them as parallel surfaces.
```

Primary files:

```text
sentinel/operator/runtime_host.py
sentinel/operator/runtime_connections.py
sentinel/operator/unified_execution_dispatcher.py
sentinel/operator/action_kernel.py
sentinel/agent/organs/browser_session_manager_l5_live.py
sentinel/organs/browser/cloak_backend.py
sentinel/operator/real_browser_control_runtime.py
```

Create if needed:

```text
sentinel/operator/power_skill_registry.py
sentinel/operator/browser_backend_selector.py
tests/operator/test_power_reconnection_organ_skill_wiring.py
```

Required wiring decisions:

```text
read_only_research -> evidence/read-only skill
workspace_patch -> workspace patch skill
code_execution_sandbox -> bounded code skill
bounded_channel -> channel send skill
real_browser_control -> browser skill frontend
BrowserSessionManagerL5Live + CloakBrowser -> live browser backend
Playwright -> explicit compatibility/test backend
```

Acceptance tests:

```text
test_skill_registry_lists_read_patch_code_channel_browser
test_browser_backend_selector_prefers_cloak_when_available
test_browser_backend_selector_does_not_silently_fallback_to_playwright
test_playwright_backend_requires_explicit_compatibility_selection
test_runtime_host_product_skills_match_registry_without_enabling_high_risk_surfaces
```

Validation:

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_organ_skill_wiring.py -q
py -3.13 -m pytest tests/test_browser_session_manager_l5_live.py -q
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
```

Definition of done:

```text
Existing organs become selectable backends under skills.
The model does not need to know which backend powers the skill.
```

## Pack D: DecisionContext Skill Frame Simplification

Name:

```text
POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1
```

Goal:

```text
Replace giant pack-specific DecisionContext branches with composable skill frames.
```

Primary files:

```text
sentinel/operator/decision_context.py
sentinel/operator/model_led_task_loop.py
sentinel/operator/browser_decision_frame.py
sentinel/operator/browser_world_model.py
```

Create if needed:

```text
sentinel/operator/skill_decision_frame.py
sentinel/operator/browser_skill_frame.py
sentinel/operator/workspace_skill_frame.py
sentinel/operator/channel_skill_frame.py
tests/operator/test_power_reconnection_decision_context_skill_frames.py
```

Required behavior:

```text
DecisionContext includes:
- mission objective
- current progress
- executable skills
- recent receipts
- recovery observations
- proof requirements
- finish availability
```

It must stop treating raw browser primitives as the primary browser research route.

Acceptance tests:

```text
test_browser_research_frame_prefers_search_extract_product_cards
test_low_level_browser_primitives_are_internal_when_skill_actions_available
test_workspace_patch_frame_requires_patch_plus_verification
test_channel_frame_requires_delivery_then_finish
test_finish_available_only_after_skill_proof
```

Validation:

```text
py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py -q
py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
```

Definition of done:

```text
The model sees skills and proof requirements, not internal runtime plumbing.
```

## Pack E: First Simplification Cut - Organ Branch Matrix

Name:

```text
POWER_RECONNECTION_PACK_E_FIRST_SIMPLIFICATION_CUT_ORGAN_BRANCH_MATRIX_V1
```

Goal:

```text
Reduce branch-heavy organ execution code without weakening power or proof.
```

Primary files:

```text
sentinel/agent/organs/organ_dispatch.py
sentinel/agent/organs/runtime_execution.py
sentinel/organs/registry.py
```

Create if needed:

```text
sentinel/agent/organs/organ_spec_registry.py
tests/test_organ_spec_registry_runtime_dispatch.py
```

Required behavior:

```text
Each organ declares:
- organ id
- request model
- runtime handler
- authority level
- proof requirements
- replay expectations
- hard stop categories
```

Acceptance tests:

```text
test_organ_spec_registry_replaces_browser_branch_lookup
test_runtime_execution_uses_spec_for_known_organ
test_unknown_organ_blocks_honestly
test_receipt_and_finalgate_requirements_preserved
test_no_new_high_risk_surface_dispatchable_by_default
```

Validation:

```text
py -3.13 -m pytest tests/test_organ_spec_registry_runtime_dispatch.py -q
py -3.13 -m pytest tests/test_agent_browser_operator_runtime_integration.py -q
py -3.13 -m pytest tests/test_browser_session_manager_l5_live.py -q
```

Definition of done:

```text
Adding a new organ no longer requires editing a large branch matrix in multiple places.
```

## Then Pack 6D

After Packs A-E:

```text
POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
```

6D should now be smaller and stronger:

```text
real_browser.search
real_browser.inspect_result
real_browser.open_result
real_browser.extract_product_cards
real_browser.verify_extraction
sentinel_loop.finish
```

6D acceptance:

```text
Alibaba does not die at type_text locator timeout.
The model pilots browser skill actions.
Sentinel handles ref resolution, focus, fill/type fallback, Enter/click search, wait, scroll, recapture, extraction, and recovery below the model.
```

## Commit Strategy

Each pack should be committed separately:

```text
docs: record power reconnection pack sequence
feat: add actionability registry
fix: classify recoverable action failures
feat: wire organs through power skill registry
refactor: compile decision context from skill frames
refactor: add organ spec registry
feat: add browser skill spine
```

No real provider run during Packs A-E.

Real provider/browser run only after 6D:

```text
REAL_POWER_ATTEMPT_5D_MODEL_LED_ALIBABA_BROWSER_SKILL_SPINE_V1
```

## Pack Sequence Acceptance Checklist

```text
existing power becomes more product-usable
model-facing API becomes simpler
low-level APIs move below skill boundary
recoverable failures stop killing missions
CloakBrowser session backend is wired where appropriate
Playwright stays explicit compatibility/test backend
receipts/replay/FinalGate remain intact
no new approval theater
no fake success
no provider-native tools
no fallback/AUTO
```
