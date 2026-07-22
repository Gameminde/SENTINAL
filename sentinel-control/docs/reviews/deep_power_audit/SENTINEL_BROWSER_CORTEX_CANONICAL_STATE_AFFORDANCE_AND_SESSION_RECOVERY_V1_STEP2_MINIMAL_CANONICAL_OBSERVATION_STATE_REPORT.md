# SENTINEL_BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1_STEP2_MINIMAL_CANONICAL_OBSERVATION_STATE_REPORT

Status: IMPLEMENTED_LOCAL_CANDIDATE
Date: 2026-07-22
Base commit before Step 2: 3e395a42b6e8dad73b65d9f980d790a530eb9d0c
Provider calls: 0
Live browser runs: 0
Frozen holdout used: no

## Hypothesis

The V8 divergence harness showed that the first causal browser failure was not the final budget exhaustion. The first causal divergence was:

```text
SESSION_FAILURE_WITHOUT_RECOVERY_AFFORDANCE
```

That means the next smallest useful correction is a model-visible operational state snapshot that answers:

```text
Where am I?
What can I do now?
What is missing for mission satisfaction?
```

The snapshot must be sourced from sensors, receipts or runtime context. Unknown values must stay unknown.

## Scope

This tranche only adds the minimal canonical observation state.

Implemented:

- `BrowserEnvironmentState.operational_snapshot`
- stable timestamp-free operational fingerprint
- per-field value, confidence, evidence refs, freshness, source and uncertainty reason
- currently executable affordance list derived from authority actions plus current observed state
- safe recoverable-error exposure without raw paths, cookies, DOM, selectors, URLs, provider output or session material
- product model browser decision frame exposure

Not implemented in this tranche:

- explicit affordance contracts for every browser skill
- session recovery state machine
- progress-based anti-repetition guard
- live Cloak proof
- real provider proof
- browser macro lane

## Doctrine Alignment

The research consensus was treated as architectural input, not as authority over the code. The implemented direction matches the current doctrine:

```text
MODEL = semantic judgment, strategy, interpretation, invention
SENTINEL = senses, state, affordances, runtime, evidence, authority and proof
```

The snapshot does not force a strategy. It gives the model compact evidence and executable affordance context.

The future seam remains:

```text
ExecutionIntent = SemanticActionProposal | BrowserMacroProposal
```

Only the semantic action path exists today. The browser macro lane remains future work and was not activated.

## Files Changed

```text
sentinel/operator/browser_environment_state.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel/operator/real_browser_control_runtime.py
tests/operator/test_browser_cortex_canonical_operational_state.py
```

## Behavior Before

`BrowserEnvironmentState` already carried a broad cognitive graph, but the product model context did not expose a compact operational snapshot with:

- root lease status
- page/body availability
- last action/state-change slots
- recoverable failure packet
- proof-missing progress summary
- current executable affordances
- stable operational fingerprint

This made the model see browser context as useful evidence, but not as a crisp operational body state.

## Behavior After

`BrowserEnvironmentState.safe_model_dump()` now includes:

```text
operational_snapshot.schema_version
operational_snapshot.fingerprint
operational_snapshot.fields.current_url
operational_snapshot.fields.page_title
operational_snapshot.fields.page_type
operational_snapshot.fields.session_lease_status
operational_snapshot.fields.page_body_available
operational_snapshot.fields.interactive_candidates
operational_snapshot.fields.public_evidence_inventory
operational_snapshot.fields.mission_progress
operational_snapshot.fields.last_action
operational_snapshot.fields.last_significant_state_change
operational_snapshot.fields.recoverable_error
operational_snapshot.fields.currently_executable_affordances
operational_snapshot.fields.provenance_and_freshness
```

Each field carries:

```text
value
confidence
evidence_refs
freshness
source
uncertainty_reason
```

The product browser decision frame now includes:

```text
browser_cognitive_decision_frame.operational_snapshot
browser_cognitive_decision_frame.currently_executable_affordances
```

## Safety And Power Notes

This change is not a refusal layer. It does not police topics.

It also does not turn state into authority:

```text
data_not_authority = true
authority_effect = none
can_grant_authority = false
can_execute = false
```

The individual affordance records name the `ProductActionKernel` dispatch contract. They are model-visible choices, not self-executing authority grants.

`finish` is intentionally not announced merely because candidate content exists. It is announced only when supplied mission progress marks the proof lane as finish-eligible through verified evidence plus summary, or through an honest terminal blocker.

## Local Proof

Added tests prove:

- unobserved raw URL stays `unknown` while origin hash remains available
- operational fingerprint ignores volatile IDs and changes only with operational state
- affordances are announced only when current state satisfies known preconditions
- `finish` is not advertised without proof-lane eligibility
- recoverable error codes survive as typed facts without raw material leakage
- the product model decision context receives the operational snapshot

## Validation

```text
py -3.13 -m pytest tests/operator/test_browser_cortex_canonical_operational_state.py -q
RESULT: 6 passed

py -3.13 -m pytest tests/operator/test_browser_cortex_pack1_environment_state_graph.py tests/operator/test_browser_cortex_integration_pack0_executable_truth_reconciliation.py -q
RESULT: 12 passed

py -3.13 -m pytest tests/operator/test_browser_cortex_divergence_harness.py -q
RESULT: 1 passed
```

```text
py -3.13 -m compileall -q sentinel
RESULT: passed

git diff --check
RESULT: passed

targeted scan for raw provider/reasoning/DOM/cookies/session/profile material/local path/binary path/fallback/provider-native markers
RESULT: benign defensive references only:
- raw DOM is mentioned only as excluded material.
- HTML markers are redacted by `_safe_text`.
- `session/profile` appears only in the report as a forbidden persistence category.
- ProductActionKernel authority wording is not a provider-native or fallback path.
```

## Remaining Gaps

Next sub-tranches should remain narrow:

1. Explicit browser affordance contracts:
   `observe`, `navigate`, `search`, `follow`, `inspect`, `extract_evidence`, `verify`, `recover_session`, `finish`.

2. Session recovery state machine:
   `ACTIVE`, `DEGRADED`, `RECOVERING`, `RECONNECTED`, `BLOCKED`, `CLOSED`.

3. Progress-based anti-repetition:
   normalized action plus state fingerprint plus evidence fingerprint.

4. One live mission only after the local loop proves session continuity, readable evidence and proof-integrity gate behavior.

## Verdict

```text
BROWSER_CORTEX_CANONICAL_STATE_STEP2_MINIMAL_OBSERVATION_STATE = IMPLEMENTED_LOCAL_CANDIDATE
PRODUCT_BROWSER_DECISION_CONTEXT_RECEIVES_OPERATIONAL_STATE = PROVEN_LOCAL
SESSION_RECOVERY_MACHINE = NOT_STARTED
ANTI_REPETITION_PROGRESS_GUARD = NOT_STARTED
LIVE_BROWSER_POWER = NOT_CLAIMED
REAL_MODEL_PRODUCT_POWER = NOT_CLAIMED
```
