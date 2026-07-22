# SENTINEL_BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1_STAGE1_DIVERGENCE_HARNESS_REPORT

## Verdict

```text
BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1_STAGE1_DIVERGENCE_HARNESS
= IMPLEMENTED_LOCAL_CANDIDATE

runtime_changes = no browser/provider/runtime behavior change
provider_calls = 0
browser_runs = 0
holdout_used = no
site_specific_fix = no
```

Stage 1 created a bounded divergence harness that reconstructs one mission's decision/action/proof transitions from safe persisted artifacts. It does not re-execute effects, does not inspect raw browser material, and does not persist raw provider output.

## Scope

Selected V8 mission:

```text
task_id = docs_python_pathlib_glob
site = docs.python.org
V8 terminal status = blocked
V8 blocked_reason = MODEL_CALL_BUDGET_EXHAUSTED
provider_decision_count = 10
material_browser_receipt_count = 10
runtime_failure_fact_seen = true
browser_failure_packet_seen = true
repeated_identical_action_without_new_evidence_count = 1
```

Source artifacts consumed:

```text
safe_evidence_snapshot
safe_browser_proof_index
mission_ledger
```

The generated machine-readable trace is:

```text
SENTINEL_BROWSER_CORTEX_V8_DIVERGENCE_TRACE_DOCS_PYTHON_PATHLIB_GLOB_V1.json
```

## Harness Contract

For each provider decision, the harness records only safe structured fields:

```text
pre_state_fingerprint
model_state_presented shape
announced_affordances
raw_decision availability status
normalized decision/action envelope summary
ProductActionKernel action summary
material receipt summary
post_state_fingerprint
evidence_fingerprint before/after
session lease transition
progress/no-progress reason
finish eligibility
```

Raw decision text is deliberately unavailable in the trace because raw provider output is not persisted by design.

## First Causal Divergence

The first supported causal divergence is:

```text
decision_index = 6
classification = SESSION_FAILURE_WITHOUT_RECOVERY_AFFORDANCE
failure_code = real_browser_search_session_open_failed
material_effect_observed = false
session_transition = ACTIVE -> DEGRADED
announced_recovery_actions = []
```

Interpretation:

```text
The mission had already produced search/extract/verify/summarize activity.
The model then selected another search with the same safe parameter hash as the previous search turn.
The browser body reported BODY_SESSION_UNAVAILABLE.
The model-visible failure packet exposed no executable recovery affordance.
The loop later continued into extract/search churn and exhausted model-call budget.
```

This means the final `MODEL_CALL_BUDGET_EXHAUSTED` is downstream. The first causal gap is the missing canonical session-state/recovery affordance after a recoverable body failure.

## Decision Trace Summary

```text
decision 1  real_browser.search              completed  ACTIVE -> ACTIVE    progress = state_or_evidence_delta
decision 2  real_browser.extract_evidence    completed  ACTIVE -> ACTIVE    progress = evidence_delta
decision 3  real_browser.verify_extraction   completed  unknown -> unknown  progress = no_state_or_evidence_delta
decision 4  summarize_evidence               completed  unknown -> unknown  progress = no_state_or_evidence_delta
decision 5  real_browser.search              completed  ACTIVE -> ACTIVE    progress = state_or_evidence_delta
decision 6  real_browser.search              blocked    ACTIVE -> DEGRADED  failure = BODY_SESSION_UNAVAILABLE
decision 7  real_browser.extract_evidence    completed  ACTIVE -> ACTIVE    progress = evidence_delta
decision 8  real_browser.search              blocked    ACTIVE -> DEGRADED  failure = BODY_SESSION_UNAVAILABLE
decision 9  real_browser.extract_evidence    completed  ACTIVE -> ACTIVE    progress = evidence_delta
decision 10 real_browser.search              blocked    ACTIVE -> DEGRADED  failure = BODY_SESSION_UNAVAILABLE
```

The existing V8 proof artifacts add new failure receipts after session failures, so their raw evidence hash changes. For Browser Cortex progress, that must not be confused with objective progress. Stage 2 should separate:

```text
state/proof changed
objective evidence changed
failure evidence changed
finish eligibility changed
```

## Instrumentation Gaps Found

```text
full_model_presented_state_not_persisted
raw_decision_not_persisted_by_design
announced_affordances_unknown_without_failure_packet
```

These are acceptable for Stage 1, but they explain why the current artifacts cannot fully answer "what exact state did the model see?" before each decision. Stage 2 must provide a canonical compact browser state snapshot with executable affordances.

## Root Cause Hypothesis For Next Sub-Tranche

```text
The browser body can produce receipts and failure packets,
but the product loop does not yet maintain a canonical operational state
with executable affordances and session recovery state.

After BODY_SESSION_UNAVAILABLE, the model sees failure evidence but not a
strong recover_session/observe alternative. It can keep selecting browser
actions that depend on a degraded session.
```

## Next Correct Step

Proceed to Step 2 only:

```text
BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1_STEP2_MINIMAL_CANONICAL_OBSERVATION_STATE
```

Step 2 should implement the minimal observation snapshot requested by the operator:

```text
observed url/title hashes or unknown
page type or unknown
real lease state
page/body availability
interactive candidates
public evidence inventory
mission progress and missing evidence
last action
last meaningful state change
recoverable error
currently executable affordances
provenance and freshness
stable timestamp-free fingerprint
```

Do not implement recovery, anti-repetition, or a broader batch in the same commit.

## Validation

```text
py -3.13 -m pytest tests/operator/test_browser_cortex_divergence_harness.py -q
py -3.13 -m pytest tests/operator/test_browser_receipt_persistence_answer_claim_evidence.py -q
py -3.13 -m compileall -q sentinel
git diff --check
targeted scan for raw provider/browser/session material
```

Result:

```text
browser_cortex_divergence_harness = 1 passed
browser_receipt_persistence_answer_claim_evidence = 19 passed
compileall = passed
git diff --check = passed
targeted scan = only benign marker text found: raw_provider_output_not_persisted_by_design
```
