# PYTHON_ORG_POST_FINAL_FIX_REPEATED_RELIABILITY_V1_REPORT

## Verdict

```text
PYTHON_ORG_POST_FINAL_FIX_REPEATED_RELIABILITY_V1
= VALID_CALIBRATION_MEASURED_QUALITY_GATE_FAIL

attempts = 5
holdout_used = false
runtime_patch_during_batch = false
fixture_backend = false
Playwright_fallback = false
```

This batch was run only after preserving:

```text
v6_minimal_safe_bundle = sentinel-control/docs/reviews/deep_power_audit/evidence_bundles/PYTHON_ORG_V6_MINIMAL_SAFE_EVIDENCE_BUNDLE_V1.json
freeze_commit = d6a1664
```

Every attempted mission is included in the denominator.

## Safe Artifacts

```text
batch_id = python_org_reliability_v1_1784202364
safe_results = sentinel-control/docs/reviews/deep_power_audit/evidence_bundles/PYTHON_ORG_POST_FINAL_FIX_REPEATED_RELIABILITY_V1_SAFE_RESULTS.json
safe_results_hash = e065977a0669192cf10c1c3ed9d2d694c86f37d3e44f5c7c9166ebd87981e3e0
```

No raw provider output, private reasoning, raw DOM, raw URL, raw query, selectors, cookies, session values, profile material, secrets or raw binary path are included in the committed safe artifacts.

## Frozen Contract

```text
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
browser_backend = real Cloak
mission_count = 5
max_provider_decisions_per_mission = 10
max_material_actions_per_mission = 16
objective = find grounded official Python documentation explaining pathlib Path.glob and provide a short useful answer
```

Success required both:

```text
technical completion
useful grounded Path.glob answer supported by official evidence
```

Completed-with-irrelevant-evidence was not counted as success.

## Aggregate Results

Original run aggregate:

```text
attempt_count = 5
provider_decision_calls = [5, 5, 5, 5, 5]
material_action_counts = [4, 4, 4, 4, 4]
replay_no_react_rate = 1.0
cleanup_success_rate = 1.0
estimated_provider_cost_usd_total = 0.042034
batch_verdict = VALID_CALIBRATION_MEASURED_QUALITY_GATE_FAIL
```

Post-run safe analysis from dispatch closeouts:

```text
technical_closeout_success_count = 5/5
dispatch_search_materiality_success_count = 5/5
replay_no_react_count = 5/5
cleanup_success_count = 5/5
answer_quality_success_count = 0/5
browser_receipt_readable_total = 0
browser_receipt_missing_total = 15
```

## Attempt Summary

```text
attempt 1 = completed, closeout success, replay clean, cleanup clean, answer quality not proven, browser receipt files not independently readable
attempt 2 = completed, closeout success, replay clean, cleanup clean, answer quality not proven, browser receipt files not independently readable
attempt 3 = completed, closeout success, replay clean, cleanup clean, answer quality not proven, browser receipt files not independently readable
attempt 4 = completed, closeout success, replay clean, cleanup clean, answer quality not proven, browser receipt files not independently readable
attempt 5 = completed, closeout success, replay clean, cleanup clean, answer quality not proven, browser receipt files not independently readable
```

## What Passed

```text
real provider reached = 5/5
real product loop completed = 5/5
search/extract/verify/summarize/finish sequence = 5/5
dispatch closeout search materiality visible = 5/5
replay no-react = 5/5
post-close cleanup = 5/5
holdout untouched = true
```

This is strong evidence for the product spine and mission lifecycle.

## What Failed

### 1. Browser Receipt File Auditability

The batch result originally marked search materiality as failed because the aggregator could not independently read the real browser receipt files:

```text
browser_receipt_path_count = 15
browser_receipt_readable_count = 0
browser_receipt_missing_count = 15
```

The dispatch closeouts still carried safe context cards and showed materiality evidence, but independent receipt-file auditability failed.

Classification:

```text
BROWSER_RECEIPT_FILE_AUDITABILITY_GAP
```

This is not the same as search actuation failure. It is a proof persistence/auditability failure.

### 2. Answer Quality Not Independently Auditable

The model completed the loop, but the committed safe artifacts did not preserve enough normalized final answer claims to prove a useful grounded Path.glob explanation.

```text
answer_quality_success_count = 0/5
unsupported_claim_total = 0
problem = insufficient preserved answer claims, not detected hallucination
```

Classification:

```text
ANSWER_QUALITY_NOT_INDEPENDENTLY_AUDITABLE
```

## Capability Truth

```text
REAL_MODEL_PRODUCT_SPINE_PYTHON_ORG_T3 = REPEATED_COMPLETION_OBSERVED_5_OF_5
REPLAY_NO_REACT_LIVE = REPEATED_PROVEN_5_OF_5
POST_CLOSE_CLEANUP_LIVE = REPEATED_PROVEN_5_OF_5
SEARCH_MATERIALITY_DISPATCH_CLOSEOUT = OBSERVED_5_OF_5

INDEPENDENT_BROWSER_RECEIPT_AUDITABILITY = FAILED
INDEPENDENTLY_AUDITABLE_ANSWER_QUALITY = FAILED
MISSION_SUCCESS_RATE_BY_STRICT_GATE = 0_OF_5
MULTI_SITE_GENERALIZATION = NOT_PROVEN
HOLDOUT = LOCKED
```

## Next Required Fix

Do not rerun the same batch without fixing the general failure class.

Proceed next with:

```text
FIX_BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_CAPTURE_V1
```

Required behavior:

```text
1. Preserve independently readable safe browser receipt snapshots for each browser material action.
2. Ensure ProductActionKernel closeout and receipt refs resolve to committed/readable safe proof locations.
3. Preserve normalized final answer claims, not raw provider output.
4. Attach claim-to-evidence refs and support/contradiction/unknown status.
5. Keep raw provider output, private reasoning, raw DOM, raw URL, raw query, selectors, cookies, sessions and profile material out of persisted artifacts.
6. Re-run a new versioned reliability batch only after local proof.
```

## Final Batch Decision

```text
QUALITY_GATE_PASS = false
DO_NOT_RUN_MULTI_SITE_CALIBRATION_YET
DO_NOT_CONSUME_HOLDOUT
```
