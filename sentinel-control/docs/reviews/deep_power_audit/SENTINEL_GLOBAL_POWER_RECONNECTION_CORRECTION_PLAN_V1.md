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
| implemented candidate | `POWER_RECONNECTION_PACK_C_ORGAN_TO_SKILL_WIRING_AND_BACKEND_SELECTION_V1` | `7bc8f6e` | P1: powerful organs are underconnected and backend ownership is invisible to model-facing skills | focused proof: skills map to organ/backend truth without enabling new RuntimeHost adapters |
| implemented candidate | `POWER_RECONNECTION_PACK_D_DECISION_CONTEXT_SKILL_FRAME_SIMPLIFICATION_V1` | `6656585` | P0/P1: DecisionContext exposes primitive/static actions instead of skill truth | focused proof: `skill_decision_frame` is primary model truth and legacy primitive recommendations are demoted |
| implemented candidate | `POWER_RECONNECTION_PACK_E_FIRST_SIMPLIFICATION_CUT_ORGAN_BRANCH_MATRIX_V1` | `e389430` | P2: organ dispatch/runtime branch matrices tax power and make organ wiring fragile | focused proof: organ spec registry is consumed by dispatch/runtime, unknown organs block honestly, high-risk specs stay locked |
| implemented candidate | `POWER_RECONNECTION_PACK_F_SUB_REQUEST_BUILDER_SPEC_CUT_V1` | `e404e98` | P2: typed organ sub-request builders and runtime request-field selection remained branch-heavy | focused proof: `OrganRequestFactory` builds typed requests from spec aliases/request fields; unknown organs block honestly; proof metadata is preserved |
| implemented candidate | `POWER_PACK_6D_BROWSER_SKILL_SPINE_AND_ROOT_FRICTION_REMOVAL_V1` | `b6614ae` | P0/P1 browser vertical: model-facing browser actionability still preferred fragile primitives and locator misses could kill in-scope work | focused proof: browser decision frames expose skill actions; `real_browser.search` robustly tries ranked search refs and alternates; product-card extraction/verification receipts satisfy proof; replay is no-react |
| implemented candidate | `BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1` | `1cebea5` | P0: model-visible action protocol is too cage-like and useful `metadata/reply` intent collapses into `empty_action_envelope` | focused proof: natural/semi-structured browser intent maps to internal ActionEnvelope skills; hard boundary intents block; replay/no-react still holds |
| implemented candidate | `POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1` | `400637710350d129683f9fa9124edf9d79262023` | P0 blocker audit rows BF-BROWSER-001/002/003/007/008/009, BF-CORE-013, BF-PROOF-001 | focused proof: visible cards route to extract/verify/finish, open/search are demoted after cards exist, hidden/disabled refs recover, secret refs hard stop, FinalGate blocked truth is avoided while recovery succeeds |
| implemented candidate | `POWER_FRICTION_CUT_PACK_2_VERIFIED_EXTRACTION_TO_COMPLETION_LANE_V1` | `102b1d0a68802dc6d25dd8b79ff33a33277ca34f` | P0: 5G proved visible cards can reach extract/verify, but verified extraction did not dominate summary/finish | focused proof: verified extraction routes to grounded evidence summary, summary plus verification routes to finish, and open/search/recovery churn is demoted after verification |
| product-proven subpath | `REAL_POWER_ATTEMPT_5H_VERIFIED_EXTRACTION_TO_SUMMARY_FINISH_V1` | `ca28239` | P0: Pack 2 needed real-provider proof on bounded Alibaba | focused proof: real model loop reached extract_product_cards -> verify_extraction -> summarize_evidence -> finish, mission completed, replay no-react, high-risk scan clean |
| implemented candidate | `POWER_FRICTION_CUT_PACK_3_SEARCH_ACTUATION_AND_RELEVANT_PRODUCT_EXTRACTION_V1` | `97fe777208fc3bdf451975f6d2338f676f1d823a` | P0: 5H completed from visible cards but did not prove real search actuation or relevant glasses-under-5-EUR product quality | focused proof: search success records material receipt, search failure with relevant cards routes to extraction, cards carry relevance/price-support fields, grounded summary preserves uncertainty, and finish requires relevant product evidence |
| implemented candidate | `SENTINEL_BROWSER_DEVTOOLS_CONTEXT_BRIDGE_V1` | `eea1170c5740721a48b3265213bbbe48112abd48` | P1: DevTools/session browser intelligence existed in organs but was not surfaced to the browser skill context | focused proof: BrowserSessionManager L5 hash/count DevTools metadata now appears in `browser_devtools_context`; metadata failure becomes a safe unavailable card instead of terminal browser-action failure |
| implemented candidate | `FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1` | `380bbb7f13c4f68f4ffc0b17d3154571f428bf22` | P0/P1: 5K proved Cloak backend truth but exposed search-query contamination, multilingual product relevance misses, repeated post-search churn, and profile material cleanup gaps | focused proof: product-card extraction strips search-result intros, recognizes multilingual eyewear terms, demotes repeated search after a search receipt, evaluates backend truth only from material backend receipts, and cleans Cloak profile material on runtime close |
| valid failed | `REAL_POWER_ATTEMPT_5L_CLOAK_RELEVANCE_QUALITY_AND_PROFILE_CLEANUP_V1` | `64477eb9bfbafa735fe422379a60a5cd23bfc012` | P0/P1: real run showed browser micro-fix loop still leaves global actionability/finish friction | product truth: Cloak backend match and replay no-react held; search material/relevance completion still failed, so work pivots to global cleanup |
| implemented candidate | `POWER_CLEANUP_PACK_1_MODEL_FACING_EXECUTABLE_SKILL_TRUTH_V1` | `0bbe148` | P0: model-visible action not guaranteed executable; BF-CORE-003, BF-CORE-013, BF-BROWSER-007, BF-AUTH-001 | focused proof: `ModelLedTaskLoop` validates direct model decisions against actionability truth before dispatch; hidden/internal and unknown actions recover with visible skill recommendations; locked high-risk actions hard-stop clearly |
| implemented candidate | `POWER_CLEANUP_PACK_2_RECOVERABLE_OBSERVATION_DOMINATES_LOOP_GUARD_AND_FINALGATE_V1` | `34867bf` | P0: recoverable in-scope miss becomes mission death; BF-CORE-001, BF-CORE-006, BF-CORE-008, BF-PROOF-001 | focused proof: recoverable observations with live next actions or refreshed candidates reset no-progress accounting; empty recoveries still block honestly |
| implemented candidate | `POWER_CLEANUP_PACK_7_RUNTIMEHOST_SAFE_SKILL_PRODUCT_REGISTRATION_V1` | `0535d6f` | P0/P1: RuntimeHost product dispatch was read-only centered | focused proof: `workspace_patch.apply_patch` routes through `ProductActionKernelDispatchAdapter` with explicit authority, parameter hash sidecar, ProductActionKernel receipt, workspace patch receipt, FinalGate, and replay no-react while high-risk surfaces remain closed |
| implemented candidate | `POWER_CLEANUP_PACK_8_ACTIONKERNEL_SKILL_PARITY_FOR_CODE_AND_CHANNEL_V1` | `c1cf6d4a2cf8ba7680b907a42ccac4c41f99706e` | P0/P1: code execution and bounded channel send existed as loop/local organs but were not RuntimeHost product-dispatchable skills | focused proof: code execution and bounded fake/local channel send now route through the product ActionKernel adapter with explicit authority, ProductActionKernel receipts, skill/backend registry parity, recoverable timeout/missing-transport lanes, and preserved hard stops for network, real channel, high-risk, fallback/AUTO, and provider-native tools |
| valid success | `REAL_POWER_ATTEMPT_PRODUCT_ACTION_KERNEL_CODE_AND_CHANNEL_DISPATCH_V1` | pending docs commit | P0/P1: Pack 8 needed product-like controlled proof beyond unit tests | controlled proof: RuntimeHost executed code execution and fake/local bounded channel send through ProductActionKernel with product receipts, skill-specific receipts, accepted FinalGate certificates, replay no-execute/no-resend, and hard-stop proofs for network code args, real channel transport, known non-product, unknown skill, and high-risk surfaces |

Current next proof:

```text
START_POWER_CLEANUP_PACK_9_MODEL_LED_PRODUCT_ACTIONKERNEL_MULTI_SKILL_TASK_LOOP_V1
```

Pack B did not ignore Pack A: it audited `model_visible_*` consumption and found the full model decision migration still belongs to Pack D. Pack C wired dormant organs into product skills without bypassing the new actionability and recoverable-execution contracts. Pack D made skill/backend frames the primary model decision truth while keeping legacy fields as compatibility only. Pack E created the first declarative organ runtime spec cut and wired it into dispatch/runtime. Pack F cut typed sub-request field selection/building into `OrganRequestFactory`. Pack 6D consumed A-F for a vertical browser proof. `BROWSER_MODEL_NATIVE_CONTROL_LOOP_V1` corrects the 5E protocol cage by letting the loop consume model-native browser intent and translate it into internal skills. `POWER_FRICTION_CUT_PACK_1_REMOVE_STUPID_BLOCKERS_V1` cut the first 5F blocker cluster so visible product/result cards and safe intent route to extraction and verification instead of stale open/search/raw primitive paths. `POWER_FRICTION_CUT_PACK_2_VERIFIED_EXTRACTION_TO_COMPLETION_LANE_V1` cuts the 5G post-verification blocker so verified extraction routes to summary and finish instead of search/recovery churn. `REAL_POWER_ATTEMPT_5H_VERIFIED_EXTRACTION_TO_SUMMARY_FINISH_V1` proves that completion lane with a real provider and bounded Alibaba page. `POWER_FRICTION_CUT_PACK_3_SEARCH_ACTUATION_AND_RELEVANT_PRODUCT_EXTRACTION_V1` cuts the next local blocker by requiring material search evidence where possible and by making product relevance/under-5-EUR support first-class proof. `SENTINEL_BROWSER_DEVTOOLS_CONTEXT_BRIDGE_V1` connects BrowserSessionManager L5 DevTools hash/count metadata into the browser skill context so a dormant browser organ becomes model-visible power without raw browser material or a new terminal blocker. 5K then proved Cloak/session backend truth but exposed relevance-quality and profile cleanup gaps. `FIX_CLOAK_BROWSER_RELEVANT_SEARCH_RESULT_QUALITY_AND_PROFILE_CLEANUP_V1` cut those local gaps, but 5L still failed on search material/relevance quality. `POWER_CLEANUP_PACK_1_MODEL_FACING_EXECUTABLE_SKILL_TRUTH_V1` pivots back to the root audit by enforcing executable model-facing skill truth before dispatch across surfaces. `POWER_CLEANUP_PACK_2_RECOVERABLE_OBSERVATION_DOMINATES_LOOP_GUARD_AND_FINALGATE_V1` keeps useful recoverable observations alive in the loop instead of letting no-progress accounting terminalize them. `POWER_CLEANUP_PACK_7_RUNTIMEHOST_SAFE_SKILL_PRODUCT_REGISTRATION_V1` cuts the read-only RuntimeHost bottleneck for one bounded local skill: `workspace_patch.apply_patch` now routes through the product dispatcher with receipts and replay no-react proof. `POWER_CLEANUP_PACK_8_ACTIONKERNEL_SKILL_PARITY_FOR_CODE_AND_CHANNEL_V1` extends that product-native route to bounded code execution and fake/local bounded channel send without opening real external channel power by default. `REAL_POWER_ATTEMPT_PRODUCT_ACTION_KERNEL_CODE_AND_CHANNEL_DISPATCH_V1` proves those two routes together in one controlled RuntimeHost attempt with replay no-react and hard-boundary checks.

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
| Workspace patch | yes | product-dispatch local-only | First safe non-read-only RuntimeHost product skill via `ProductActionKernelDispatchAdapter` |
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

Now it becomes valid after Packs A-F.

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

## Living Update: Blocker And Power Friction Audit V1

After `REAL_POWER_ATTEMPT_5F`, the next correction layer is not another broad security/control pack. The new blocker audit classifies every major blocker as:

```text
KEEP_HARD_STOP
DELETE
DEMOTE_TO_WARNING
CONVERT_TO_RECOVERY
MOVE_BELOW_MODEL
REPLACE_WITH_SKILL_ROUTING
KEEP_BUT_REQUIRE_CLEAR_AUTHORITY
```

The control rule for this plan is now:

```text
Each implementation pack must cut a named blocker row from SENTINEL_BLOCKER_AND_POWER_FRICTION_MATRIX_V1.csv.
Each pack must preserve the listed hard stops and update the matrix/control docs after validation.
```

Immediate next implementation pack:

```text
POWER_CLEANUP_PACK_7_RUNTIMEHOST_SAFE_SKILL_PRODUCT_REGISTRATION_V1
```

First targets:

```text
register one safe non-read-only skill through ProductActionKernelDispatchAdapter
prove RuntimeHost can route that skill without read_only_research_adapter gravity
preserve authority compatibility checks before ActionKernel execution
verify generic product receipt/finalgate proof through UnifiedExecutionDispatcher
keep high-risk browser/payment/contact/credential surfaces non-dispatchable
```

## Living Update: Power Cleanup Packs 1-3

The global reconnection plan now tracks the cleanup sequence that follows the blocker audit.

| Pack | Status | Commit | What It Reconnected |
|---|---|---:|---|
| `POWER_CLEANUP_PACK_1_MODEL_FACING_EXECUTABLE_SKILL_TRUTH_V1` | implemented | `0bbe148` | model-visible actions now validate against executable skill truth before runtime dispatch |
| `POWER_CLEANUP_PACK_2_RECOVERABLE_OBSERVATION_DOMINATES_LOOP_GUARD_AND_FINALGATE_V1` | implemented | `34867bf` | useful recovery observations count as loop progress instead of immediate no-progress death |
| `POWER_CLEANUP_PACK_3_SKILL_BACKEND_ORGAN_REGISTRY_CONSOLIDATION_V1` | implemented | `c6d0f0a` | power skill backend frame now consumes organ spec receipt/proof/replay/recovery/hard-stop metadata |
| `POWER_CLEANUP_PACK_4_READ_ONLY_SPINE_DEMOTION_TO_EVIDENCE_SKILL_V1` | implemented | `7f7ac92` | read-only is model-facing supporting evidence, not the central product path |
| `POWER_CLEANUP_PACK_5_PRODUCT_DISPATCHER_SKILL_NATIVE_ROUTING_V1` | implemented | `ad9a9d3` | coordinator now distinguishes known non-product skills from unknown capabilities |
| `POWER_CLEANUP_PACK_6_PRODUCT_ACTION_KERNEL_DISPATCH_ADAPTER_V1` | implemented | `4d8cdb0` | bounded product dispatch can now execute explicit ActionKernel skills with generic receipt/finalgate proof |

Pack 3 is not a new power surface. It makes the existing power map more truthful:

```text
skill -> backend -> organ specs -> receipts/proof/replay/recovery/hard stops
```

Pack 6 is still not a blanket power unlock:

```text
adapter is injectable
default RuntimeHost registration is unchanged
high-risk browser/payment/contact/credential surfaces remain locked
recoverable executor misses block honestly with receipt evidence but no accepted fake FinalGate
```

The next cleanup target is:

```text
POWER_CLEANUP_PACK_7_RUNTIMEHOST_SAFE_SKILL_PRODUCT_REGISTRATION_V1
```

Reason:

```text
product dispatch now has a bounded generic ActionKernel adapter,
but RuntimeHost has not yet registered a first non-read-only safe skill through it.
The next cut should prove a safe skill can become product-reachable without opening high-risk surfaces.
```
