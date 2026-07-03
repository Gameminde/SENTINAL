# Sentinel Power Reconnection Pack Sequence V1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement each pack task-by-task. This document is a strategic implementation sequence, not runtime code.

**Goal:** Reconnect Sentinel's existing dormant power before building another browser-specific pack.

**Architecture:** Sentinel already has many organs, but only a small part is product-native and model-usable. The next work should reconnect the action plane, skill plane, authority plane, and proof plane so existing power becomes usable without exposing internal APIs to the model.

**Tech Stack:** Python, Sentinel operator runtime, model-led task loop, ActionKernel, DecisionContext, organ runtimes, browser/session organs, receipts, replay, FinalGate.

---

## Verdict

`POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1` is implemented as a local candidate.

6D is not global audit closure. It is the first browser vertical proof built after root reconnection Packs A-F.

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
correction re-audit third
pack approval/lock fourth
big-audit comparison fifth
audit status update sixth
commit seventh
```

This prevents the work from collapsing back into one visible symptom, such as browser locator failures, while the real issue is cross-system actionability and connection quality.

## Implementation Status

| Sequence item | Canonical implementation | Status | Commit | Notes |
|---|---|---|---|---|
| Pack A: Actionability Registry And Skill Exposure | `POWER_CORE_PACK_1_ACTIONABILITY_AND_SKILL_REGISTRY_V1` | accepted as foundation, not product-proven | `2172a14` | Introduced global `actionability_registry.py` and `DecisionContext.skill_exposure_frame`; full product value requires model decision path to consume `model_visible_*` as primary truth |
| Pack B: Recoverable Execution Contract | `POWER_RECONNECTION_PACK_B_RECOVERABLE_EXECUTION_CONTRACT_V1` | implemented candidate | `5fc3a0c` | Classified in-scope executor misses become recoverable observations; Pack A model-visible consumption remains Pack D scope |
| Pack C: Organ-To-Skill Wiring And Backend Selection | `POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1` | implemented candidate | `7bc8f6e` | Added data-only `power_skill_registry.py` and `browser_backend_selector.py`; skills now map to owner organs/backends without enabling new dispatch power |
| Pack D: Decision Context Skill Frame Simplification | `POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1` | implemented candidate | `6656585` | Added primary `skill_decision_frame`, `primary_model_*` recommendations, and legacy compatibility fields |
| Pack E: First Simplification Cut Organ Branch Matrix | `POWER_RECONNECTION_PACK_E_FIRST_SIMPLIFICATION_CUT_ORGAN_BRANCH_MATRIX_V1` | implemented candidate | `e389430` | Added data-only organ runtime specs consumed by dispatch/runtime; browser/session aliases resolve through spec registry; high-risk organs remain locked |
| Pack F: Sub-Request Builder Spec Cut | `POWER_RECONNECTION_PACK_F_SUB_REQUEST_BUILDER_SPEC_CUT_V1` | implemented candidate | `e404e98` | Added `OrganRequestFactory`; typed sub-request builders and request-field selection now flow through spec metadata while high-risk organs stay locked |
| Browser vertical: Skill Spine And Root Friction Removal | `POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1` | implemented candidate, not real-provider/browser product-proven | `b6614ae` | Model-facing browser path is skill-first; low-level primitives are internal/fallback; search actuation ranks refs and tries alternates; product extraction cards and verification receipts are proof-bearing; replay no-react is covered by fake/local tests |
| Browser vertical: Model Native Control Loop | `BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1` | implemented candidate, not real-provider/browser product-proven | `1cebea5` | Natural/semi-structured model browser intent now maps to canonical internal ActionEnvelope skills inside `ModelLedTaskLoop`; `metadata/reply` safe intent no longer has to become empty-action correction churn |
| Power friction cut: first stupid blockers | `POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1` | implemented candidate, not real-provider/browser product-proven | `400637710350d129683f9fa9124edf9d79262023` | Cuts the first 5F blocker cluster: visible cards beat stale open/search recommendations, safe ambiguous intent routes to extract/verify/finish, hidden/disabled refs recover, secret refs remain hard stops |
| Power friction cut: verified extraction completion lane | `POWER_FRICTION_CUT_PACK_2_VERIFIED_EXTRACTION_TO_COMPLETION_LANE_V1` | implemented candidate, not real-provider/browser product-proven | `102b1d0a68802dc6d25dd8b79ff33a33277ca34f` | Cuts the 5G post-verification blocker: verified extraction now routes to grounded evidence summary, summary plus verification routes to finish, and open/search/recovery churn is demoted after verification |
| Real attempt: verified extraction to summary finish | `REAL_POWER_ATTEMPT_5H_VERIFIED_EXTRACTION_TO_SUMMARY_FINISH_V1` | valid success for Pack 2 completion lane, not full product-relevance proof | `ca28239` | Real provider path completed extract_product_cards -> verify_extraction -> summarize_evidence -> finish with replay no-react and clean high-risk scan; remaining gap is search actuation plus relevant product extraction |
| Power friction cut: search actuation and relevant product extraction | `POWER_FRICTION_CUT_PACK_3_SEARCH_ACTUATION_AND_RELEVANT_PRODUCT_EXTRACTION_V1` | implemented candidate, not real-provider/browser product-proven | `97fe777208fc3bdf451975f6d2338f676f1d823a` | Adds 5H completion-lane evaluator, material search receipt proof, product relevance fields, under-5-EUR visible-evidence policy, grounded relevance summary, and finish gating on relevant product evidence |
| Browser dormant organ bridge: DevTools context | `SENTINEL_BROWSER_DEVTOOLS_CONTEXT_BRIDGE_V1` | implemented candidate, not real-provider/browser product-proven | `eea1170c5740721a48b3265213bbbe48112abd48` | Wires BrowserSessionManager L5 DevTools hash/count metadata into `RealBrowserControlRuntime` context cards; metadata failure becomes a safe unavailable card instead of a terminal browser-action blocker |
| Real attempt: Cloak-ready search relevance | `REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1` | valid failed, backend truth proven | report only | Proved pre-provider Cloak readiness, selected/actual backend match, BrowserSessionManager DevTools context, and no silent Playwright fallback; exposed relevance-quality, query-contamination, post-search churn, and profile cleanup gaps |
| Browser relevance cleanup fix | `FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1` | implemented candidate, not real-provider/browser product-proven | `380bbb7f13c4f68f4ffc0b17d3154571f428bf22` | Product-card extraction strips search-result intro text, recognizes multilingual eyewear terms, demotes repeated search after a search receipt, evaluates backend truth only from material backend receipts, and adds Cloak profile cleanup on runtime close |

New canonical next sequence:

```text
done POWER_RECONNECTION_PACK_A_ACTIONABILITY_REGISTRY_AND_SKILL_EXPOSURE_V1
done POWER_RECONNECTION_PACK_B_RECOVERABLE_EXECUTION_CONTRACT_V1
done POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1
done POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1
done POWER_RECONNECTION_PACK_E_FIRST_SIMPLIFICATION_CUT_ORGAN_BRANCH_MATRIX_V1
done POWER_RECONNECTION_PACK_F_SUB_REQUEST_BUILDER_SPEC_CUT_V1
done POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1
done BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1
done POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1
done POWER_FRICTION_CUT_PACK_2_VERIFIED_EXTRACTION_TO_COMPLETION_LANE_V1
done REAL_POWER_ATTEMPT_5H_VERIFIED_EXTRACTION_TO_SUMMARY_FINISH_V1
done POWER_FRICTION_CUT_PACK_3_SEARCH_ACTUATION_AND_RELEVANT_PRODUCT_EXTRACTION_V1
done REAL_POWER_ATTEMPT_5K_CLOAK_READY_SEARCH_RELEVANT_PRODUCT_EXTRACTION_V1
done FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1
next REAL_POWER_ATTEMPT_5L_CLOAK_RELEVANCE_QUALITY_AND_PROFILE_CLEANUP_V1
```

## Why 6D Was Delayed Until After A-F

Starting 6D before A-F would have fixed only the visible browser symptom:

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

Therefore 6D was allowed only after A-F reconnected actionability, recoverable execution, backend ownership, skill-first context, organ specs, and request construction. 6D now uses those foundations, but real Alibaba product proof is still pending.

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

Status:

```text
ACCEPTED_AS_FOUNDATION
commit = 2172a14
not_product_proven_until_model_decision_path_consumes_model_visible_fields = true
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

Mandatory opening audit before coding:

```text
verify where model_visible_* is consumed
verify whether legacy recommended actions still dominate model prompts/clients
verify whether primitive/unregistered actions can still bypass actionability registry
record whether full migration is in Pack B scope or explicitly deferred to Pack D
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

Status:

```text
IMPLEMENTED_CANDIDATE
commit = 5fc3a0c
in_scope_executor_timeout_to_recoverable_observation = true
hard_stop_boundaries_preserved = true
full_model_visible_migration_deferred_to_pack_d = true
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

Status:

```text
IMPLEMENTED_CANDIDATE
commit = 7bc8f6e
power_skill_backend_frame = true
CloakBrowser_preferred_when_available = true
Playwright_requires_explicit_compatibility_selection = true
RuntimeHost_adapter_registry_changed = false
Pack_D_required_for_primary_model_consumption = true
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

Status:

```text
IMPLEMENTED_CANDIDATE
commit = 6656585
decision_context_primary_truth = skill_decision_frame
primary_model_recommended_next_action = skill_frame_recommendation
legacy_recommended_next_action = compatibility_only
browser_low_level_primitives_demoted = true
Pack_E_required_for_branch_matrix_simplification = true
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
test_skill_binding_metadata_available_for_decision_context
test_recoverable_and_hard_stop_metadata_available_from_spec
test_safe_external_registry_export_names_specs_without_execution_power
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

Status:

```text
IMPLEMENTED_CANDIDATE
commit = e389430
organ_spec_registry_consumed_by_dispatch = true
organ_spec_registry_consumed_by_runtime = true
unknown_organ_blocks_honestly = true
high_risk_organs_default_dispatchable = false
Pack_F_required_for_sub_request_builder_branch_cut = completed
```

## Pack F: Sub-Request Builder Spec Cut

Name:

```text
POWER_RECONNECTION_PACK_F_SUB_REQUEST_BUILDER_SPEC_CUT_V1
```

Goal:

```text
Continue Pack E by moving typed sub-request field selection and builder lookup into spec/factory metadata instead of branch-heavy runtime organ id checks.
```

Primary files:

```text
sentinel/agent/organs/organ_dispatch.py
sentinel/agent/organs/organ_spec_registry.py
sentinel/agent/organs/runtime_execution.py
```

Definition of done:

```text
OrganDispatcher can select request_field and sub-request builder from spec metadata.
Existing receipts/FinalGate/replay remain unchanged.
Unknown or locked organ specs still block honestly.
```

Status:

```text
IMPLEMENTED_CANDIDATE
commit = e404e98
organ_request_factory_added = true
runtime_request_field_selection_spec_owned = true
proof_metadata_preserved = true
provider_call = no
real_browser_run = no
```

## Then Pack 6D

After Packs A-F:

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

## Inserted Sequence: Power Friction Cuts

`SENTINEL_BLOCKER_AND_POWER_FRICTION_AUDIT_V1` inserts a focused blocker-cut sequence before more broad capability expansion.

```text
POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1
POWER_FRICTION_CUT_PACK_2_VERIFIED_EXTRACTION_TO_COMPLETION_LANE_V1
POWER_FRICTION_CUT_PACK_3_SEARCH_ACTUATION_AND_RELEVANT_PRODUCT_EXTRACTION_V1
POWER_FRICTION_CUT_PACK_4_DORMANT_ORGANS_TO_SKILL_SPINE_V1 / SENTINEL_BROWSER_DEVTOOLS_CONTEXT_BRIDGE_V1
```

Pack 1 is the immediate next pack because it targets the live 5F failure mode:

```text
product cards visible
safe model-native intent consumed
but extraction was not triggered
```

The pack sequence rule remains:

```text
audit -> implement -> re-audit touched path -> update big audit -> commit -> next pack
```
