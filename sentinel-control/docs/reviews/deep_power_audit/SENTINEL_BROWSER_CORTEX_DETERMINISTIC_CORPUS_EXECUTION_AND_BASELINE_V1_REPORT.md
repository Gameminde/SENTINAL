# Sentinel Browser Cortex Deterministic Corpus Execution And Baseline V1 Report

Recorded at: 2026-07-13

```text
BROWSER_CORTEX_DETERMINISTIC_CORPUS_EXECUTION_AND_BASELINE_V1
= VALID_FAILED

baseline_target_commit = afe40f8
implementation_commit = e64dce3
corpus_version = browser_cortex_quality_corpus_v1
manifest_hash = 63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be
provider_call = NO
real_browser_run = NO
real_external_channel_send = NO
push = NO
```

## Verdict

This tranche makes the frozen deterministic Browser Cortex corpus executable
through the product spine and records the first permanent baseline.

The run is intentionally not inflated:

```text
executed_case_count = 24 / 24
pass_count = 21
fail_count = 3
verdict = VALID_FAILED
```

The baseline is valuable because it proves the machinery and exposes remaining
quality gaps before a real holdout run.

## Product-Spine Execution Path

Each deterministic case executes through:

```text
mission objective
-> model-facing product task-loop context
-> BrowserEnvironmentState / browser world-model cards
-> model decision client
-> canonical internal ActionEnvelope
-> RuntimeHost
-> ProductActionKernel dispatch adapter
-> real_browser_control runtime
-> deterministic Cloak/session fixture backend
-> browser receipts
-> post-action context
-> FinalGate / task-loop terminal certificate
-> replay no-react snapshot
```

This does not feed evaluator booleans directly into the quality result. The
runner evaluates runtime-observed receipts, context cards, search materiality,
semantic entities, FinalGate state, and replay state.

## Hashes And Versions

```text
manifest_hash = 63900f4198852ce755803f1284f8b65cab849d2b51cb9a02031c44203af7c4be
expected_labels_hash = 8dfbde54f9bf6deb3b1f0f808f123fad1c07543010ec108ed7e32fbb7d885668
fixture_bundle_hash = 58cd39305a2b4c9b5d661035f6e60a9ba4291cba171ae1ffca1e55b91f757592
runner_version = browser_cortex_deterministic_runner_v1
runtime_commit = afe40f8
```

The accepted manifest hash is preserved as the frozen V1 corpus hash. Expected
labels and fixture bundle hashes are separate so future runner/fixture changes
cannot silently mutate V1 expectations.

## Metrics

| Metric | Value | Gate |
|---|---:|---|
| executed_case_coverage | 1.0 | pass |
| search_control_identification_accuracy | 0.9167 | pass |
| search_materiality_precision | 1.0 | pass |
| search_materiality_recall | 0.9091 | pass |
| result_region_f1 | 0.9583 | pass |
| semantic_entity_coverage | 0.8333 | pass |
| recovery_success_rate | 0.4 | fail |
| uncertainty_accuracy | 0.5 | fail |
| replay_no_react_rate | 1.0 | pass |
| fill_only_false_success | 0 | pass |
| unsupported_claims | 0 | pass |
| raw_secret_exposure | 0 | pass |
| replay_side_effects | 0 | pass |
| site_specific_success_branches | 0 | pass |

The deterministic gate is not passed because recovery and uncertainty quality
remain below target, even though coverage, materiality precision/recall, result
region detection, field support invariants, and replay no-react are green.

## Per-Case Baseline

| Case | Pass | Failure class | Search control | Skill | Search state | Result region | Entities | FinalGate | Replay no-react |
|---|---|---|---|---|---|---|---:|---|---|
| det_conventional_search_form | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_multiple_search_fields | PASS | - | input:header_search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_spa_search | PASS | - | input:spa_search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_result_no_url | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_url_query_no_result | FAIL | MISSION_NOT_COMPLETED | input:search | browse_search | MATERIAL_SUCCESS | False | 0 | blocked | true |
| det_shadow_dom | PASS | - | shadow:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_iframe | PASS | - | frame:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_dynamic_loading | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_pagination | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_infinite_scroll | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_autocomplete | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_modal_overlay | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_localized_ui | FAIL | SEARCH_CONTROL_MISMATCH,SEARCH_MATERIALITY_MISMATCH,RESULT_REGION_MISMATCH | - | browse_search | - | False | 0 | blocked | true |
| det_negative_relevance | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_client_side_filter | PASS | - | input:filter | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_network_failure | PASS | - | input:search | browse_search | UNCERTAIN | False | 0 | blocked | true |
| det_stale_controls | FAIL | SEARCH_CONTROL_MISMATCH,SEARCH_MATERIALITY_MISMATCH | - | browse_search | - | True | 1 | accepted | true |
| det_structured_data | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_contradictory_price_currency | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_non_commerce | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_fill_only_false_success | PASS | - | input:search | browse_search | UNCERTAIN | False | 0 | blocked | true |
| det_result_region_without_navigation | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_search_button_only | PASS | - | input:search | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |
| det_filter_without_query | PASS | - | select:filter | browse_search | MATERIAL_SUCCESS | True | 2 | accepted | true |

## Baseline Artifact

Permanent JSON baseline:

```text
sentinel-control/docs/reviews/deep_power_audit/SENTINEL_BROWSER_CORTEX_DETERMINISTIC_CORPUS_EXECUTION_AND_BASELINE_V1_BASELINE.json
```

The artifact contains per-case fixture hash, objective, expected outcome,
observed search control, selected skill, action trace, pre/post environment
hashes, search progress, result-region observation, semantic entities, recovery
attempts, receipt refs, product receipt refs, FinalGate status, replay proof,
pass/fail, and failure class.

## Runtime Changes

```text
sentinel.operator.browser_cortex_deterministic_fixture
sentinel.operator.browser_cortex_deterministic_runner
sentinel.operator.runtime_host
sentinel.operator.browser_cortex_quality_gate
tests/operator/test_browser_cortex_deterministic_corpus_execution_baseline.py
```

Key implementation decisions:

```text
deterministic fixture backend declares cloak_browser / cloakbrowser
fixture backend is sessioned per corpus case during each baseline
baseline runner isolates RuntimeHost per case using short run-root names
runner aggregates browser context cards across dispatches
runner uses receipt/search-materiality evidence before evaluator classification
runner records local replay snapshot without re-executing actions
```

## Remaining Blockers

```text
det_url_query_no_result = material search without result region still ends blocked instead of clean uncertain completion
det_localized_ui = localized search control not selected/executed correctly
det_stale_controls = stale control recovery does not reach refreshed expected control/materiality
recovery_success_rate = 0.4 below 0.8 gate
uncertainty_accuracy = 0.5 below target
relevance_precision = not meaningful yet because deterministic objectives are generic and card relevance is mostly unknown
```

## Safety And Persistence Scan Scope

The baseline did not run a provider, a real browser, or a real external channel.
The generated corpus artifact contains safe hashes, refs, counts, summaries, and
semantic cards only.

Required persisted exclusions remain:

```text
raw provider output = not produced
raw provider reasoning = not produced
raw DOM = not persisted
screenshots = not persisted
cookies/session/profile material = not persisted
credential values = not persisted
provider-native tools = not used
fallback/AUTO = not used
```

## Recommended Decision

```text
DO_NOT_RUN_REAL_HOLDOUT_YET
NEXT = FIX_BROWSER_CORTEX_DETERMINISTIC_RECOVERY_AND_UNCERTAINTY_GAPS_V1
```

The next fix should target the three failed deterministic classes before any
real holdout quality run:

```text
url_query_no_result uncertain completion
localized search control actuation
stale control refresh/retry materiality
```
