# SENTINEL_BROWSER_OBSERVE_END_TO_END_RECEIPT_AND_PROOF_COMPLETENESS_V1_REPORT

## Verdict

```text
BROWSER_OBSERVE_END_TO_END_RECEIPT_AND_PROOF_COMPLETENESS_V1
= VALID_SUCCESS_LOCAL_DETERMINISTIC_INTEGRATION

proof_tier = T1_LOCAL_DETERMINISTIC_CANDIDATE
provider_calls = 0
real_browser_runs = 0
prompt_changed = no
mdn_rerun = no
```

This tranche is a deterministic proof of receipt and proof completeness for
the observe path. It is not a Browser Cortex generalization claim and not a
real-model browser-quality proof.

## Reproduced Path

```text
RuntimeHost
-> ProductActionKernel
-> real_browser.observe
-> Cloak-labeled runtime engine
-> terminal browser receipt
-> BrowserProofIndex
-> divergence trace
-> completion truth
```

The red test reproduced the proof gap:

```text
accepted real_browser.observe
-> engine.observe raised
-> ProductActionKernel receipt existed
-> BrowserProofIndex had browser_receipt_missing_count = 2
```

## Root Cause

`RealBrowserControlRuntime._observe` wrote a browser observation receipt only
after `engine.observe()` succeeded. An exception after browser action start
escaped to the outer runtime bridge, which produced a product-level recoverable
failure but no child browser terminal receipt.

The stable local exception was classified as:

```text
exception_class = RealBrowserControlRuntimeError
failure_code = real_browser_observe_snapshot_failed
failure_stage = browser_runtime_observe
raw_exception_text_persisted = false
raw_path_persisted = false
```

The raw exception text is intentionally not published in this report.

## Fix Summary

Implemented a generic observe terminal receipt contract:

```text
observation_success
typed_observation_failure
```

Every accepted `real_browser.observe` now writes exactly one terminal browser
receipt into the child `real_browser_control/receipts` collection.

On observe failure Sentinel now writes:

```text
runtime_failure_fact
model_visible_body_failure_packet
typed_observation_failure receipt
safe finalgate rejection for the browser action
ProductActionKernel receipt link through BrowserProofIndex
```

An observe failure is never represented as a successful observation.

## Receipt Schema Proof

The terminal observe receipt now exposes safe fields for:

```text
operation
status
failure_code
before_state_hash
after_state_hash
browser_environment_state_hash
root_browser_lease_id_hash
browser_engine_identity_hash
backend_context_identity_hash
page_identity_hash
selected_backend_id
actual_backend_id
session_backend_kind
freshness
typed_observation
evidence_delta
exception_class
exception_hash
receipt_hash
```

`BrowserProofIndex` now indexes these fields and links the terminal browser
receipt to the ProductActionKernel receipt through `product_receipt_ref`.

## Progress And Divergence Truth

Fixed the progress semantics:

```text
new failure receipt != material progress
new timestamp != material progress
progress-guard metadata != material progress
child browser handle churn != root browser progress
```

The divergence harness now:

```text
reads the current available_affordances packet shape
distinguishes decision_absent from suppressed_repeated_action
records suppressed repeated actions explicitly
uses typed_observation as a typed outcome source
selects the first observe-body failure as first causal divergence
exposes completion_truth in the trace
```

The progress guard now normalizes away internal recovery metadata and does not
count runtime failure facts as state/evidence progress.

## Terminal Blocker Canon

`honest_blocker_present = true` and `loop_closed = true` now require an evidenced
terminal blocker:

```text
status = blocked
final_reason present
browser receipt missing count = 0
readable terminal browser failure receipt present
```

A missing browser receipt cannot produce an honest blocker.

## Proof-Integrity Gate Subresults

The proof-integrity gate now publishes every subresult even when one fails:

```text
proof_index
safe_bundle
cleanup
material_browser_receipts
completion_ledger_consistency
blind_evaluator_consistency
replay_reconstruction
runtime_provenance
```

This does not make the verifier more permissive. Any contradiction still makes
the global proof gate fail.

## Gates

```text
PROOF_INFRASTRUCTURE_GATE = PASS_LOCAL_DETERMINISTIC
BROWSER_TASK_GATE = NOT_RUN_NO_REAL_BROWSER_OR_PROVIDER
SESSION_CONTINUITY_GATE = PASS_LOCAL_SAFE_IDENTITY_FIELDS_PRESENT
SESSION_RECOVERY_GATE = NOT_TRIGGERED
REPETITION_BOUND_GATE = PASS_LOCAL
HUMAN_EVIDENCE_GATE = NOT_APPLICABLE_NO_REAL_RESEARCH
FINAL_ANSWER_GATE = NOT_APPLICABLE_NO_REAL_RESEARCH
```

## Tests Run

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_observe_receipt_proof_completeness.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py::test_browser_proof_bundle_gate_global_failed_on_injected_contradiction sentinel-control/services/sentinel-core/tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py::test_browser_proof_bundle_gate_fails_unknown_runtime_provenance -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_pack6_real_browser_bounded_web_control.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_browser_cortex_progress_repetition_guard.py sentinel-control/services/sentinel-core/tests/operator/test_browser_cortex_divergence_harness.py -q
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_browse_search_routes_through_runtimehost_product_action_kernel sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_extract_routes_through_runtimehost_product_action_kernel sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_generic_extract_evidence_routes_through_runtimehost_product_action_kernel sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_browser_replay_does_not_reopen_research_reextract -q
```

The full Pack 4 file was attempted once and exceeded the local 240 second
timeout. A targeted Pack 4 subset passed after aligning its test helper with
the canonical ProductActionKernel artifact loader.

## Next Single Run Freeze

The next real run must start from a clean isolated worktree with no large
untracked artifact set. MDN is now a regression mission only, not a
generalization proof.

```text
NEXT_SINGLE_NON_HOLDOUT_MISSION_ID =
SQLITE_OFFICIAL_GENERATED_COLUMNS_DOCS_V1

target_origin = https://www.sqlite.org
authority = public_web_read_only
forbidden = login, account mutation, payment, contact, upload, download, credential access, provider-native tools, fallback/AUTO
max_provider_decisions = 10
max_material_actions = 16
fixture_backend = false
playwright_fallback = false
real_backend = cloak_browser
```

Mission objective:

```text
Find official SQLite documentation explaining generated columns and answer:
can a generated column be part of the PRIMARY KEY, and can it have a DEFAULT
value? Provide a short answer with human-readable evidence.
```

Rubric:

```text
official sqlite.org evidence only
answer must cite human-readable evidence cards
unsupported factual claims = 0
unknowns preserved when evidence is missing
technical completion and answer quality reported separately
proof-integrity gate must execute all subresults
replay no-react and cleanup must pass
```

## Remaining Gaps

```text
real Cloak observe/search quality not proven by this tranche
new non-holdout mission not yet executed
multi-site generalization not proven
MDN remains regression-only
next run requires clean isolated worktree
```
