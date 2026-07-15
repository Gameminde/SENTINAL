# SENTINEL_FIX_BROWSER_SEARCH_ACTUATION_AND_OPEN_WORLD_EVIDENCE_ROUTING_V1_REPORT

## Verdict

```text
FIX_BROWSER_SEARCH_ACTUATION_AND_OPEN_WORLD_EVIDENCE_ROUTING_V1 = IMPLEMENTED_LOCAL_CANDIDATE
MODEL_VISIBLE_BODY_FAILURE_AND_RECOVERY_FEEDBACK_V1 = IMPLEMENTED_LOCAL_CANDIDATE
provider_calls = 0
live_browser_provider_runs = 0
frozen_holdout_used = no
python_org_v2_rerun = no
push = not_performed
```

This tranche fixes the body-feedback and open-world evidence routing failure exposed by the accepted Python.org V2 result. It does not claim a new real-model proof. The next real mission remains blocked until the live Cloak body canary is available again.

## Accepted V2 Failure

```text
REAL_MODEL_LIVE_CLOAK_SINGLE_NON_HOLDOUT_MISSION_PYTHON_ORG_V2 = honest_failure
```

The V2 trace showed a real model, real Cloak backend and typed query path, but useful browser search completion did not happen. The key product lesson was not to patch Python.org selectors. The body must expose safe structured mechanical failure evidence to the next model decision so the model can reason about recovery, missing evidence and missing capability.

## Stage 0 Body Reproduction

Stage 0 reproduced the failure class without provider calls and without a live browser by running a Python.org-like fake search-actuation-failure engine through the product RuntimeHost path.

Initial reproduction before implementation:

```text
stage0_status = blocked
stage0_blocked_reason = real_browser_search_actuation_failed
engine_count = 1
engine_search_attempts = 2
child_mission_count = 2
capability_sequence = real_browser.search, real_browser.search
model_visible_body_failure_packet = absent
```

Code and artifact inspection found:

```text
root_browser_engine_reuse = likely true in the product resource scope
child_browser_session_refs_differ = yes, because child mission workspace handles differ
search_control_discovery_failure = not proven as sole cause
ref_freshness_failure = possible
submit_materiality_failure = likely
session_replacement_as_root_cause = not reproduced in fake body path
page_kind_search_results_after_failed_search = caused by weak world-model page-kind/card heuristics
product_shaped_extraction_for_documentation = caused by weak commerce signal detection
```

The concrete product gap reproduced:

```text
recoverable material browser failure -> next model context lacks structured body-state and failure evidence
```

## Implementation

Updated:

```text
sentinel/operator/real_browser_control_runtime.py
sentinel/operator/runtime_host.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/product_model_native_decision_client.py
sentinel/operator/browser_world_model.py
sentinel/operator/browser_environment_state.py
sentinel/operator/action_kernel.py
```

Added regression coverage:

```text
tests/operator/test_browser_search_actuation_open_world_feedback.py
```

## Body Failure Feedback Contract

Recoverable browser actuation failures now carry three separate model-context objects:

```text
runtime_failure_fact
model_visible_body_failure_packet
model_blocker_assessment_schema
```

`runtime_failure_fact` is the authoritative receipt-backed mechanical truth. It records the attempted operation, typed outcome, failure stage, material-effect status, session continuity and evidence refs.

`model_visible_body_failure_packet` is safe structured state for the next model turn. It includes:

```text
attempted_operation
typed_outcome
failure_stage
material_effect_observed
objective_progress
session_continuity
safe_current_page_state_summary
available_affordances
recovery_attempts_already_executed
retry_material_action_budget_remaining
evidence_refs
contradictions
unknowns
```

`model_blocker_assessment_schema` asks the next normal provider decision for advisory diagnosis fields:

```text
perceived_blocker
concise_failure_interpretation
proposed_next_strategy
required_evidence
missing_capability
objective_satisfied
confidence
```

No extra diagnostic provider call is introduced. The next normal provider turn receives the safe packet and may interpret it. The advisory assessment cannot override receipts, grant authority, fabricate evidence, force one recovery path, or expose raw DOM, cookies, sessions, secrets or provider reasoning.

## Open-World Evidence Routing

The world model now distinguishes commerce evidence from documentation/API/article evidence. Commerce entities are only created when commerce evidence exists. Documentation pages and API-like results can now appear as open-world cards instead of fake product candidates.

New card fields:

```text
entity_family
entity_kind
evidence_refs
extra_attributes
relationships
```

Supported first open-world kinds:

```text
documentation_result
api_symbol_result
article_result
search_result
unknown_result
```

Unknown and future entity kinds remain allowed. The model remains the semantic judge; Sentinel supplies evidence, relationships, confidence, contradictions and unknowns.

## Completion Semantics

Action sequence completion is no longer treated as mission completion for open-world browser research. Browser evidence summary now supports:

```text
grounded_objective_satisfaction
truthful_terminal_blocker
missing_evidence
missing_capability
unsupported_claims = 0
```

Documentation/API results produce an open-world evidence summary, not a product summary. Product relevance remains product-specific and cannot be inferred from ordinary documentation text.

## Post-Implementation Stage 0 Proof

The provider-free body reproduction now proves model-visible failure feedback and open-world routing:

```text
stage0_after_status = blocked
stage0_after_blocked_reason = model_led_product_action_kernel_decision_exhausted
engine_count = 1
search_attempts = 1
runtime_failure_fact = real_browser_search_actuation_failed / search_control_actuation
model_visible_body_failure_packet_present = true
material_effect_observed = false
session_root_present = true
page_kind = documentation_search_or_index
card_kinds = api_symbol_result, api_symbol_result, api_symbol_result
```

The remaining blocked status is expected for the Stage 0 harness because it intentionally stops after body feedback instead of running a provider finish path.

## Live Body Canary Status

The required live body-only canary could not run because the local Cloak binary override is absent in the current process/user environment.

Safe readiness result:

```text
ready = false
provider_call_allowed = false
selected_backend_id = cloak_browser
actual_backend_id =
failure_code = CLOAK_LOCAL_BINARY_OVERRIDE_REQUIRED
profile_material_persisted = false
```

No provider call was made. No Python.org V2 rerun was made. No Playwright fallback was used.

## Validation

Focused tests:

```text
py -3.13 -m pytest tests/operator/test_browser_search_actuation_open_world_feedback.py -q
result = 3 passed
```

Adjacent regressions:

```text
py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 26 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
result = 97 passed

py -3.13 -m pytest tests/operator/test_model_native_browser_search_typed_parameter_boundary.py -q
result = 34 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
result = 14 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
result = 9 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_recoverable_execution_contract.py -q
result = 2 passed

py -3.13 -m pytest tests/operator/test_browser_cortex_pack1_environment_state_graph.py -q
result = 4 passed
```

Static validation:

```text
py -3.13 -m compileall -q sentinel/operator/browser_world_model.py sentinel/operator/browser_environment_state.py sentinel/operator/real_browser_control_runtime.py sentinel/operator/runtime_host.py sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel/operator/product_model_native_decision_client.py sentinel/operator/action_kernel.py
result = passed

git diff --check
result = passed
```

Targeted persistence scan:

```text
raw provider output persisted = no new hit
provider reasoning persisted = no new hit
raw DOM persisted = no new hit
cookie/session/profile material persisted = no new hit
secret value persisted = no new hit
provider-native/fallback/AUTO introduced = no
```

The scan returned existing guardrail strings in surrounding tests and runtime safeguards, but no new raw credential, cookie, session, DOM, binary path or provider-reasoning persistence was introduced by this tranche.

## Hard Boundaries Preserved

```text
authority self-grant = blocked
trusted runtime key override = blocked
raw secrets = blocked/redacted by existing gates
provider-native tools = not introduced
fallback/AUTO = not introduced
Playwright fallback = not used
raw DOM/cookies/session/profile material = not persisted
receipts remain authoritative over model assessment
model assessment cannot grant authority
```

## Remaining Blockers

```text
live_body_canary = blocked until CLOAKBROWSER_BINARY_PATH is restored in process scope
python_org_v2_rerun = not authorized until live body canary passes
search materiality quality = still unproven in real provider path after this fix
open_world_entity_kinds = initial implementation, not a full ontology and intentionally extensible
```

## Next Prepared Step

Restore the previously validated process-scoped Cloak binary override without printing or persisting the raw path, then run the live body-only canary. Only after that can a single real-model non-holdout mission be authorized again.
