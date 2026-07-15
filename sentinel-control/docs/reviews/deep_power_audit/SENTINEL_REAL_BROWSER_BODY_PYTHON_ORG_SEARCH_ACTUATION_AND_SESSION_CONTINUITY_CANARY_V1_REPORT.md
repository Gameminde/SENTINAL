# SENTINEL_REAL_BROWSER_BODY_PYTHON_ORG_SEARCH_ACTUATION_AND_SESSION_CONTINUITY_CANARY_V1_REPORT

## Verdict

```text
REAL_BROWSER_BODY_PYTHON_ORG_SEARCH_ACTUATION_AND_SESSION_CONTINUITY_CANARY_V1 = VALID_FAILED_BODY_SEARCH_ACTUATION_NOT_PROVEN
provider_calls = 0
fixture_backend = false
Playwright_fallback = false
runtime_modified_during_or_after_canary = false
real_model_mission_authorized = no
```

The canary restored the previously validated Cloak binary candidate, proved Cloak readiness, entered the RuntimeHost/ProductActionKernel browser path, observed the Python.org search page and exposed a fresh model-visible body failure packet. It did not prove real browser search actuation.

## Binary Provenance Restoration

The candidate was recovered from:

```text
source = cloakbrowser.binary_info()
```

The raw local binary path was not printed or persisted. The candidate matched the previously accepted safe provenance:

```text
candidate_count = 1
candidate_exists = true
path_hash = f3fad5133de1a876082e5a7f6be7c61cf083e2a4742c4cf44fcfa6cfe34d3a2e
path_hash_match = true
file_sha256 = 03f53661a5c47e7b0a661bee2bce8a0d302b7a60834c328df417561fa0636d80
file_hash_match = true
version = 146.0.7680.177.5
version_match = true
platform = windows-x64
tier = free
raw_path_printed = false
raw_path_persisted = false
```

The binary path was applied only as a process-scoped environment value for the canary process.

## Cloak Readiness

Before the canary, readiness passed:

```text
ready = true
provider_call_allowed = true
selected_backend_id = cloak_browser
actual_backend_id = cloak_browser
session_backend_kind = cloakbrowser
receipt_backend_match = true
profile_material_persisted = false
safe_url_origin_hash = e89a56b7e964e4b6055990b874700f32ecc5cc22c2f7226851bbf5d48c9577ac
```

No install, update, download, bootstrap or Playwright substitution was performed.

## Frozen Body-Only Mission

```text
target = public read-only Python.org search page
raw_target_url_persisted = false
objective = Path.glob-style Python documentation search
query_hash = 3ea5a03d7cfaf8268bc462e13ecfc5cf7cf91156c6ee1f211c5d63d87456f793
provider_calls = 0
```

Body-only action sequence attempted:

```text
real_browser.search
-> real_browser.extract_product_cards
-> real_browser.verify_extraction
-> sentinel_loop.finish
```

The first action reached product browser dispatch. The later actions did not execute because the run failed after the search action and then hit a second scanner boundary while trying to create the extraction mission.

## Mechanical Search Transition

Observed safe browser state before/after the failed search:

```text
page_kind = documentation_search_or_index
search_control_candidate_count = 1
selected_candidate_ref_hash = 4b33e17b39be6547c61aaf383e6fcdc6586fdf31e30608b5d97ab619738b200f
candidate_entity_kind_counts = api_symbol_result:6
entity_card_count = 6
novel_safe_entity_kind_preserved = true
```

Search actuation result:

```text
runtime_failure_fact.failure_code = real_browser_search_actuation_failed
runtime_failure_fact.failure_stage = search_control_actuation
material_effect_observed = false
input_written = not_proven
submission_attempted = not_proven
search_materiality_receipt_present = false
search_materially_successful = false
typed_search_outcome_recorded = failure_packet_only
```

The recovery evidence classified the observed browser-side failure signal as:

```text
failure_kinds = network_failure
planned_actions = WAIT_AND_REOBSERVE
```

This is not a search-success proof. The canary proves that the body can see the page and expose the failure; it does not prove that Cloak successfully wrote/submitted the query.

## Model-Visible Body Failure Feedback

The canary produced the required model-visible failure shape:

```text
model_visible_body_failure_packet_present = true
attempted_operation = real_browser.search
failure_stage = search_control_actuation
material_effect_observed = false
safe_current_page_state_summary.page_kind_guess = documentation_search_or_index
safe_current_page_state_summary.search_like_refs_count = 1
safe_current_page_state_summary.candidate_entity_kind_counts = api_symbol_result:6
available_affordances.recovery_actions =
  real_browser.extract_product_cards
  real_browser.verify_extraction
  real_browser.observe
contradictions = []
unknowns include search_control_executability_unconfirmed
```

The separate `runtime_failure_fact` remains authoritative. The model-visible packet is advisory body evidence only; it cannot grant authority, override receipts or fabricate material progress.

## Session Continuity

Session continuity was only partially proven because the search failed before extract/verify could run.

Safe continuity facts from the failure packet:

```text
root_lease_present = true
root_lease_ref_hash = 357d537493f51e406d7191ee871fd7d69c88f9641dc35d01071e52e053351d8c
root_lifecycle_state = active
root_open_count = 1
root_recovery_attempt_count = 0
child_mission_browser_session_ref_hash = f186e5aa928207f7cb91ab2d32b5d6e007656d11b972a8ca1b8fa48953e14888
child_session_refs_are_receipt_handles_not_engine_identity = true
browser_state_hash = b8cb1f63ea6e439da7f996b2f9e0918c7d9805d9a263904634af70fa42404ccf
browser_environment_state_hash = d29627a82ccef4d69a4dd722b5eac3b54ab1865867b056698f463da8619bcc0e
```

Not proven:

```text
root_lease_stable_across_observe_search_verify = not_proven
browser_engine_identity_stable_across_child_actions = not_proven
backend_context_identity_stable_across_child_actions = not_proven
verify_material_evidence = not_reached
```

Child workspace/session handles may differ by design. The underlying root lease was present for the failed search action, but extract/verify did not run, so full cross-action continuity remains open.

## Secondary Boundary Exposed

After the recoverable search failure, the loop attempted to create the extraction mission with `loop_context`. Mission creation blocked with:

```text
mission_execution_request_parameters: unsafe operator payload
```

Targeted scan of the transported safe browser context showed:

```text
blocked_path = $.browser_decision_frame.mission_objective
blocked_categories = external_action, forbidden_surface
```

The mission objective contained negative boundary wording such as no login, no download, no upload, no contact, no payment and no form submission. This is another topic-policing / semantic-data scanner false positive in a downstream `loop_context` path. It is separate from the Cloak search-actuation failure and was not patched in this canary tranche.

## Open-World Evidence

Open-world routing behaved correctly:

```text
commerce_product_coercion = false
entity_kind = api_symbol_result
entity_count = 6
documentation_objective_not_forced_to_product = true
unknown_or_future_entity_kinds_allowed = true
```

The page evidence was represented as API/documentation-like result entities, not product cards.

## Safety And Cleanup

```text
provider_calls = 0
raw_provider_output_persisted = false
provider_reasoning_persisted = false
raw_binary_path_persisted = false
Playwright_fallback = false
fixture_backend = false
authority_expansion = false
```

The canary generated temporary runtime artifacts under the local `tmp` tree while proving the failure. Those canary artifacts were removed after safe evidence extraction so only this report is intended to be committed.

## Final Classification

Primary failure:

```text
REAL_BROWSER_SEARCH_ACTUATION_FIX = NOT_LIVE_PROVEN
failure_class = SEARCH_CONTROL_ACTUATION_FAILED
```

Secondary failure:

```text
DOWNSTREAM_LOOP_CONTEXT_SCANNER_FALSE_POSITIVE = REPRODUCED
failure_class = TOPIC_POLICING_IN_SAFE_CONTEXT
```

Still open:

```text
ROOT_SESSION_CONTINUITY = NOT_FULLY_LIVE_PROVEN_ACROSS_SEARCH_EXTRACT_VERIFY
VERIFY_MATERIAL_EVIDENCE = NOT_REACHED
REAL_MODEL_PYTHON_ORG_V3 = NOT_AUTHORIZED
```

## Next Step

Do not run a real provider mission yet. The next implementation tranche should address:

```text
1. Real Cloak search actuation on Python.org search control.
2. Safe loop_context transport for extraction/verification without generic lexical topic policing.
3. Explicit root lease / engine / backend context identity receipts across search -> extract -> verify.
```

Only after a body-only canary proves search materiality and full cross-action continuity should a single real-model Python.org V3 mission be authorized.
