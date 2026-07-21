# SENTINEL_FIX_WINDOWS_SAFE_ARTIFACT_PATH_AND_END_TO_END_BROWSER_ANSWER_PROOF_TRUTH_V1

## Stage 0 Root-Cause Table

| Path | Code Evidence | V1 Artifact Evidence | Root Cause |
|---|---|---|---|
| A. Receipt path construction | `sentinel/operator/unified_execution_dispatcher.py::_product_action_kernel_artifact_path` writes `product_action_kernel/<collection>/<logical_ref>.json`; `sentinel/operator/browser_proof_index.py::_load_product_receipts` reconstructs that same long logical path. | V1 reported 4 material receipt readability misses under deep Windows doc/export roots. | Product receipts still use long nested physical filenames. There is no compact logical-id to physical-path mapping/index, so auditability depends on Windows path behavior and each reader using long-path helpers correctly. |
| B. Final answer transport | `ProductModelNativeDecisionClient._skill_to_action` passes `answer_claims` only when the model emits the exact list; `ModelLedProductActionKernelTaskLoop` accepts `finish` immediately after product receipts; `_safe_final_answer_payload` stores `safe_summary`, optional `answer_claims`, optional `public_evidence`. | Both Python missions had `browser_receipt_missing_count=0`, `public_evidence_count=2`, but `answer_claim_count=0` and `useful_answer_completion=false`. | The model sees only a compact proof-index summary, not a terminal answer contract. A natural `finish` can close the loop without a `final_answer`, `honest_blocker`, or claim cards. |
| C. Public evidence construction | `browser_proof_index._evidence_from_browser_receipt` creates evidence from receipt action metadata: source title falls back to `action_kind`; excerpt is `action status typed_outcome`. `redact_operator_text` then applies generic env-like redaction. | Python public evidence showed empty normalized URL, titles like `real_browser.search`, and excerpts like `real_browser.extract_evidence [REDACTED_SECRET]`. | The index was counting action metadata as public evidence. It did not classify human readability, and generic redaction erased harmless `key=value` action metadata as if it were a secret. |
| D. Completion semantics | `ModelLedProductActionKernelTaskLoop._complete` marks loop completed once `finish` is accepted; previous report runner counted `technical_completion` from loop status even when no action-level backend/evidence existed. | PyPI missions had `actual_backend_id=""`, `material_action_count=0`, `public_evidence_count=0`, `browser_failure_packet_seen=true`, but `technical_completion=true`. | Loop closeout, material browser success, evidence acquisition, answer presence, blocker honesty, and objective satisfaction were collapsed into one completion signal. |
| E. Blind evaluator serialization | V1 runner persisted `blind_evaluator_result.json` with provider/model IDs and `evaluator_response_hash` only. | `blind_evaluator_result.json` contained `evaluator_called=true` and response hash, but no verdict, claim counts, support counts, or useful-answer class. | The evaluator result was integrity metadata, not a structured safe verdict. It could not audit answer quality independently from raw provider output. |

## Implementation Boundary

This tranche will repair proof and answer transport only:

- compact product-action artifact layout with logical-id mapping;
- model-led `final_answer` / `honest_blocker` terminal contract;
- human-readable public evidence classification;
- separated completion truth metrics;
- structured safe blind evaluator result normalization.

It will not add browser sensor fusion, new browser cognition, provider calls, live browser runs, fixture reruns, or holdout consumption.

## Implementation Result

Verdict:

```text
FIX_WINDOWS_SAFE_ARTIFACT_PATH_AND_END_TO_END_BROWSER_ANSWER_PROOF_TRUTH_V1
= VALID_SUCCESS_LOCAL_PROOF_ONLY
```

Tier boundary:

```text
T1_LOCAL_DETERMINISTIC_CANDIDATE = proven
T2_LIVE_BODY_PROVEN = not run in this tranche
T3_REAL_MODEL_PRODUCT_PROVEN = not run in this tranche
Frozen V2 rerun = not run
```

This is intentionally not a browser capability success claim. It fixes the local proof/answer transport defects exposed by V1 and prepares the exact frozen V2 rerun gate.

## Files Changed

```text
sentinel/operator/unified_execution_dispatcher.py
sentinel/operator/browser_proof_index.py
sentinel/operator/mission_artifact_bundle.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/product_model_native_decision_client.py
tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py
tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py
tests/operator/test_power_cleanup_product_action_kernel_dispatch_adapter.py
```

## Stage 1: Windows-Safe Artifact Layout

Before:

```text
mission/<mission_id>/product_action_kernel/receipts/product_action_kernel_receipt_<uuid>.json
mission/<mission_id>/product_action_kernel/finalgate/product_action_kernel_finalgate_<uuid>.json
```

After:

```text
mission/<mission_id>/_pak/r/<content-addressed-ref>.json
mission/<mission_id>/_pak/fg/<content-addressed-ref>.json
mission/<mission_id>/_pak/index/r.json
mission/<mission_id>/_pak/index/fg.json
```

The logical receipt/finalgate IDs remain inside the payload and inside the `_pak/index` mapping. Readers now use compact layout first and legacy layout second. Collision handling rejects a physical-ref collision instead of silently overwriting proof.

Affected consumers updated:

```text
ProductActionKernel proof verifier
BrowserProofIndexBuilder
MissionArtifactBundleExporter
Pack9/adapter regression helpers
```

## Stage 2: Model-Led Final Answer Contract

`sentinel_loop.finish` now distinguishes terminal payloads:

```text
final_answer:
  answer_text
  answer_claims
  public_evidence
  uncertainty / unknowns / inference policy

honest_blocker:
  reason
  available_evidence_refs
  missing_evidence
```

For browser answer-seeking missions, a finish without either payload produces a recoverable observation:

```text
FINAL_ANSWER_PAYLOAD_INCOMPLETE
```

The next model turn receives the terminal contract and proof-index summary. Sentinel does not synthesize the answer for the model.

Boundary preserved:

```text
Non-browser product-route smoke missions and local app/workspace loops may still finish with legacy safe_summary.
Browser answer/evidence missions require final_answer or honest_blocker.
```

## Stage 3: Human-Auditable Public Evidence

Public evidence cards now record:

```text
normalized_public_url
source_title
source_origin
bounded_excerpt
evidence_human_readable
evidence_redaction_status
evidence_redaction_reason
source_identity_readable
evidence_supports_claim_candidate
digest
```

Operation-only cards such as `real_browser.extract_evidence` are no longer counted as human-readable public evidence. Actual secret-like values are redacted, while topic words such as password/login/token remain legal semantic text when they are not secret values.

## Stage 4: Honest Completion Semantics

Browser proof index now separates:

```text
loop_closed
browser_body_reached
material_browser_action_succeeded
evidence_acquired
final_answer_present
honest_blocker_present
mission_objective_satisfied
useful_answer_completion
```

A loop can close without objective satisfaction. Empty backend/material/evidence plus finish is not counted as useful answer completion.

## Stage 5: Structured Blind Evaluation

Added safe evaluator-result normalization with:

```text
evaluator_called
evaluator_provider
evaluator_model
evaluator_verdict
answer_present
evidence_present
factual_claim_count
supported_claim_count
unsupported_claim_count
contradicted_claim_count
inference_preserved
uncertainty_preserved
objective_satisfaction_score
useful_answer_classification
evaluator_failure_reason
response_hash
raw_output_persisted=false
```

The normalized result persists safe verdict fields instead of only a response hash. Raw evaluator output and reasoning remain excluded.

## Validation

Executed from:

```text
sentinel-control/services/sentinel-core
```

Commands:

```text
py -3.13 -m pytest tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py -q
Result: 13 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
Result: 12 passed

py -3.13 -m pytest tests/operator/test_power_pack6d_browser_skill_spine.py -q
Result: 106 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q
Result: 54 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
Result: 9 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_product_action_kernel_dispatch_adapter.py -q
Result: 5 passed

py -3.13 -m compileall -q sentinel
Result: passed

git diff --check
Result: passed with CRLF normalization warnings only
```

Targeted scan:

```text
No raw local path, raw browser material, raw DOM, cookie/session/profile material, provider reasoning, Cloak binary path, or live credential persistence was introduced.
Hits were limited to scanner marker constants, assertions that forbid raw material, and one synthetic secret-like test fixture used to prove redaction.
```

## Remaining Gaps

```text
No provider call was made.
No live Cloak/browser run was made.
The frozen V2 batch was not rerun.
Browser sensor fusion and cognition were not changed.
Answer quality is locally enforceable, not yet live-measured after this fix.
```

## Next Gate

Only after review of this local proof, the next authorized tranche may rerun the exact frozen V2 batch:

```text
BROWSER_RECEIPT_PERSISTENCE_AND_ANSWER_CLAIM_EVIDENCE_REAL_NON_HOLDOUT_PROOF_V2
```

The rerun should validate whether:

```text
material browser receipts remain readable under Windows;
BrowserProofIndex public evidence is human-auditable;
final answers or honest blockers are carried by the model;
claim-to-evidence cards are produced;
blind evaluator verdicts are structured and bounded;
proof infrastructure and browser quality are reported separately.
```
