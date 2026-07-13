# Sentinel Browser Cortex Quality Corpus And Search Understanding Gate V1 Report

Recorded at: 2026-07-13

```text
BROWSER_CORTEX_QUALITY_CORPUS_AND_SEARCH_UNDERSTANDING_GATE_V1
= IMPLEMENTED_CANDIDATE_LOCAL_CORPUS_PROOF

real_provider_call = NO
real_browser_run = NO
push = NO
valid_success_claim = NO
```

## Accepted Input State

```text
REAL_POWER_ATTEMPT_BROWSER_CORTEX_ALIBABA_V17_AFTER_NEGATIVE_RELEVANCE_COMPLETION_AND_REPLAY_HASHING
= VALID_SUCCESS

BROWSER_CORTEX_SEARCH_QUALITY_AND_ENVIRONMENT_UNDERSTANDING_V1
= IMPLEMENTED_CANDIDATE_LOCAL_PROOF
```

V17 proves the product loop can complete through real provider, model-native
browser skill, ProductActionKernel, Cloak/session, search, extraction,
verification, grounded summary, finish, FinalGate, and replay no-react.

This gate does not claim deep browser intelligence or real-world search quality.
It builds the local proof machinery needed before another real holdout run.

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/browser_cortex_quality_gate.py
sentinel-control/services/sentinel-core/sentinel/operator/decision_context.py
sentinel-control/services/sentinel-core/sentinel/operator/skill_decision_frame.py
sentinel-control/services/sentinel-core/sentinel/operator/real_browser_control_runtime.py
sentinel-control/services/sentinel-core/tests/operator/test_browser_cortex_quality_corpus_and_search_understanding_gate.py
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6d_browser_skill_spine.py
sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py
```

## Data Flow Consumption Proof

The new focused test proves counterfactual decision consumption:

```text
same recent browser operation shape
different BrowserEnvironmentState
-> different primary model recommendation
```

Observed local proof:

```text
candidate cards visible
-> primary_model_recommended_next_action = real_browser_control.real_browser.extract_product_cards

search controls visible and no cards
-> primary_model_recommended_next_action = real_browser_control.real_browser.search
```

This fixes the prior gap where BrowserEnvironmentState existed as context but
did not dominate the living model-facing recommendation path.

## Redaction Correction

`DecisionContextCompiler` now preserves safe cognitive `state_fields.value`
payloads while still dropping sensitive browser values from cookie, storage, and
session paths.

Before:

```text
any key named value could be removed
```

After:

```text
state_fields.result_regions.value survives
state_fields.search_controls.value survives
cookie/storage/session raw values are still removed
```

## Frozen Corpus

Implemented in:

```text
sentinel.operator.browser_cortex_quality_gate.build_browser_cortex_quality_corpus
```

Corpus facts:

```text
corpus_version = browser_cortex_quality_corpus_v1
baseline_commit = fdf963e875cbe7c90e689625d3c3711f730d3da4
deterministic_case_count = 24
real_world_holdout_task_count = 20
real_world_public_site_count = 5
manifest_hash = 63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be
```

Deterministic coverage includes:

```text
conventional_search_form
multiple_search_fields
spa
result_no_url
url_query_no_result
shadow_dom
iframe
dynamic_loading
pagination
infinite_scroll
autocomplete
modal_overlay
localized_ui
empty_results
negative_relevance
client_side_filter
network_failure
stale_controls
structured_data
contradictory_price_currency
non_commerce
fill_only_false_success_trap
```

Real-world holdout sites are recorded as safe site names only:

```text
alibaba.com
wikipedia.org
github.com
arxiv.org
books.toscrape.com
```

No real browser/network execution was performed for the holdout set in this
implementation tranche.

## Search Understanding

Added `derive_search_progress_state` with these states:

```text
NOT_ATTEMPTED
INPUT_WRITTEN
SUBMISSION_OBSERVED
REQUEST_PROGRESS
RESULT_STATE_CHANGED
QUERY_REFLECTED
MATERIAL_SUCCESS
UNCERTAIN
FAILED
```

Search materiality now distinguishes:

```text
input_written
submission_attempted
request_observed
navigation_or_state_changed
result_region_changed
query_reflected
search_materially_successful
search_materially_uncertain
search_progress
```

Important invariant:

```text
INPUT_WRITTEN + QUERY_REFLECTED alone never equals MATERIAL_SUCCESS
```

The runtime receipt now embeds a compact `search_progress` object alongside the
existing search materiality booleans.

## Semantic Entity Graph

Added `SemanticResultEntity` for general browser results and commerce product
extensions.

Core fields:

```text
entity_id
entity_type
title
canonical_url
rank
attributes
evidence_refs
confidence
freshness
contradictions
uncertainty_reason
```

Commerce fields:

```text
price_value
currency
price_range
unit_basis
moq
shipping_qualification
supplier_or_store
availability
relevance_to_objective
```

Unknown price/currency/MOQ/supplier fields remain `unknown`; contradictions are
preserved instead of silently resolved.

## Evaluator

Added `evaluate_browser_cortex_quality` with local metrics:

```text
search_control_identification_accuracy
search_materiality_precision
search_materiality_recall
result_region_f1
semantic_entity_coverage
relevance_precision
repeated_action_rate
invariant_counts
invariants_passed
```

Invariant counters include:

```text
fill_only_false_success
unsupported_claims
raw_secret_exposure
replay_side_effects
repeated_actions
```

The local tests prove a fill-only false success trap is rejected and counted as
an invariant failure.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_browser_cortex_quality_corpus_and_search_understanding_gate.py -q
6 passed

py -3.13 -m pytest tests/operator/test_browser_cortex_pack3_model_browser_native_memory.py -q
4 passed

py -3.13 -m pytest tests/operator/test_power_reconnection_decision_context_skill_frames.py -q
9 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
95 passed

py -3.13 -m pytest tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
14 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
18 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack3_agent_workspace_runtime.py -q
5 passed

py -3.13 -m compileall -q sentinel
passed

git diff --check
passed, line-ending warnings only
```

## Targeted Scan

The targeted scan found only:

```text
intentional redaction code markers
negative assertion strings in tests
synthetic secret-like test fixture text
```

No raw provider output, provider reasoning, raw DOM, cookies, session/profile
material, fallback/AUTO, or provider-native tool enablement was added.

## Honest Verdict

```text
verdict = IMPLEMENTED_CANDIDATE_LOCAL_CORPUS_PROOF
real_quality_gate_thresholds_passed = NOT_MEASURED
real_holdout_run = NOT_RUN
deep_browser_intelligence = NOT_CLAIMED
strong_search_quality = NOT_CLAIMED
```

This tranche proves the local quality-gate machinery and state-consumption path.
It does not prove real browser search quality.

## Remaining Gaps

```text
real holdout corpus execution is not run
search control ranking is represented/evaluable but not yet benchmarked on real sites
materiality precision/recall are local evaluator machinery, not measured quality
semantic extraction is modeled and tested locally, not certified across the holdout corpus
recovery policy metrics are not yet populated from real browser attempts
```

## Next Prepared Proof

```text
BROWSER_CORTEX_REAL_HOLDOUT_QUALITY_GATE_V1
```

The next proof should run the frozen holdout tasks through the product browser
spine and report metrics against the corpus without editing labels after seeing
results.
