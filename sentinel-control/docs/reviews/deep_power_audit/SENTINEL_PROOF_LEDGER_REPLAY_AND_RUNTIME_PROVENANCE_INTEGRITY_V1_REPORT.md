# Sentinel Proof Ledger Replay And Runtime Provenance Integrity V1

## Verdict

```text
PROOF_LEDGER_REPLAY_AND_RUNTIME_PROVENANCE_INTEGRITY_V1
= IMPLEMENTED_LOCAL_CANDIDATE
```

This is a proof-integrity tranche only. It does not claim Browser Cortex
intelligence, search quality, session fluidity, or multi-site browser success.

## Audit Before Implementation

Existing useful pieces found:

```text
BrowserProofIndexBuilder
classify_browser_completion_truth
normalize_blind_evaluator_result
CrashSafeBoundedLiveRunEvidenceSink
ProductActionKernelTaskLoopReplay
BrowserProofIndex readable reports V5-V8
```

Main wiring defect:

```text
batch proof gates could be computed from counters:
safe bundle exists
proof index readable
missing receipt count = 0
replay no-react counter = true
cleanup = true

without requiring consistency with:
BrowserProofIndex.completion_truth
mission ledger fields
blind evaluator verdict
runtime provenance
real artifact-history replay reconstruction
```

This allowed a V5-style false positive shape where proof infrastructure could
look passed even when the ledger or evaluator contradicted canonical completion
truth.

## Changes

Added:

```text
sentinel/operator/browser_proof_integrity.py
```

It provides:

```text
browser_completion_ledger_from_index
build_runtime_provenance
evaluate_browser_proof_integrity_gate
```

The completion ledger is now only a projection of:

```text
BrowserProofIndex.completion_truth
```

It is not a second completion evaluator.

Updated:

```text
sentinel/operator/browser_proof_index.py
```

Browser proof indexes now include:

```text
completion_ledger
runtime_provenance
```

`completion_truth` now also records receipt readability/missing counts so the
ledger does not need to derive completion status from parallel report counters.

Updated:

```text
sentinel/operator/model_led_product_action_kernel_task_loop.py
```

`ProductActionKernelTaskLoopReplay.from_store` now reports:

```text
replay_mode = artifact_history_reconstruction
history_reconstructed = true
effect_reexecution_attempted = false
artifact_history_hash
artifact_history_event_count
material_receipt_history_count
finalgate_history_count
browser_proof_index_history_count
```

This replaces the old pseudo before/after read with a stated reconstruction of
the persisted artifact history. It still does not re-execute effects.

## False Positive Regression

Added a regression for the V5-style false positive:

```text
proof index completion_truth says:
  technical_completion = false
  useful_answer_completion = false

stale ledger claims:
  technical_completion = true
  useful_answer_completion = true

gate result:
  passed = false
  ledger_mismatch:technical_completion
  ledger_mismatch:useful_answer_completion
```

## Runtime Provenance

Each browser proof index now records safe provenance:

```text
git_head
runtime_source_tree_hash
git_dirty
tracked_dirty_file_count
untracked_file_count
dirty_state_hash
corpus_manifest_hash
runtime_corpus_hash
runtime_provenance_hash
raw_paths_persisted = false
```

Raw local paths are not persisted.

## Validation

```text
py -3.13 -m pytest tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py -q
result: 17 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q
result: 12 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q
result: 58 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q
result: 11 passed

py -3.13 -m compileall -q sentinel
result: passed

git diff --check
result: passed, CRLF normalization warnings only

targeted scan for provider keys/raw provider/raw DOM/cookies/session/binary path
result: no actionable sensitive-material hits after synthetic test fixture cleanup
```

## Remaining Truth

This tranche closes only proof-integrity plumbing:

```text
ledger must derive from completion_truth
ledger/index/evaluator contradiction fails the gate
runtime provenance is recorded
replay is declared as artifact-history reconstruction, not effect replay
```

It does not fix:

```text
collapsed browser affordances
BrowserEnvironmentState sensory weakness
BODY_SESSION_UNAVAILABLE during recovery
repetition without evidence delta
multi-site answer quality
```

## Next Correct Tranche

Proceed next with:

```text
BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1
```

Do not rerun a six-mission batch until the first causal divergence in state,
affordance, session continuity, or progress signal is addressed locally and
with a single live proof.
