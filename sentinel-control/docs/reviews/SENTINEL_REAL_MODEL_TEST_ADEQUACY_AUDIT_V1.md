# Sentinel Real-Model Test Adequacy Audit V1

Status: COMPLETED_WITH_NEW_NEGATIVE_TESTS
No provider call executed during this audit.

## Test Quality Verdict

The real-model harness tests were useful but too optimistic around exploration depth, duplicate evidence, secret-like content in allowed files, rejected report persistence, and provider metadata. This audit added negative tests that failed before remediation and passed after fixes.

## New Or Strengthened Tests

| Test area | Added or strengthened behavior |
|---|---|
| Duplicate evidence | duplicate content/targets are marked non-novel |
| Finish depth gate | finish blocks until generic categories are covered |
| Finish depth success | finish can pass with generic evidence categories |
| Windows paths | drive-letter and UNC targets are blocked |
| Journal safety | raw provider/secret-like journal fields are rejected |
| Snapshot content scanning | secret-like allowed files are not excerpted |
| Search index safety | secret-like files are not indexed |
| Stage A access | Stage B truth docs are not indexed during exploration |
| Unsafe report persistence | rejected report canary is absent from all output artifacts |
| Provider labels | unsafe finish reasons and error labels are redacted |
| Report-lane budget deadline | provider calls are blocked before Stage A/Stage B when the run-duration budget is exhausted |
| Failure-path snapshot verification | terminal closeout records snapshot verification and reclassifies drift as snapshot failure |

## Red/Green Evidence

The following defects were reproduced by tests before fixes:

- duplicate evidence treated as productive
- finish allowed or failed for the wrong reason instead of depth
- Stage B truth files indexed in Stage A
- allowed file content with secret-like text exposed
- unsafe rejected report text persisted
- raw provider material accepted in journal fields
- Windows absolute and UNC paths not blocked
- unsafe provider `finish_reason` and error labels persisted

After remediation, targeted tests passed locally.

## Python Optimization Mode

The sensitive suites were also run with `python -O`. They passed, but pytest emitted a warning that assert statements in non-test modules are ignored under optimization. This audit did not find a direct failure from that warning in the scoped suites, but future production code should not depend on bare `assert` for runtime safety checks.

## Remaining Test Gaps

| Gap | Risk | Recommendation |
|---|---|---|
| Stage B empty/reasoning-only metadata | future provider failures hard to classify | add local fake provider tests for empty, reasoning-only, timeout, truncated visible output |
| Semantic near-duplicate evidence | loops can continue with paraphrased duplicates | add fuzzy duplicate or coverage-driven loop tests |
| Context compression | stale facts may survive or required facts may drop | add compression loss tests before next long run |

## Targeted Local Suites Run During Audit

The audit ran:

```text
tests/operator/test_interactive_exploration.py
tests/test_self_exploration_read_only_v1.py
tests/test_openai_compatible_provider_base.py
tests/test_governed_mutation_artifact_channel_v3.py
tests/test_mutation_artifact_transport_v2_micro_certification.py
tests/test_real_model_behavioral_predictive_harness_audit.py
```

and the same sensitive exploration/provider subset under `python -O`.

## Adequacy Rating

For read-only real-model exploration hardening:

```text
ADEQUATE_FOR_NEXT_TARGETED_DIAGNOSTIC
```

For full Wave 1 certification:

```text
NOT_ADEQUATE_YET
```

Required before Wave 1 certification:

- holdout tasks
- same-model baseline comparison
- repeated runs
- segmented report-lane diagnostics
- production-spine proof path for tasks that claim receipts/FinalGate/replay
