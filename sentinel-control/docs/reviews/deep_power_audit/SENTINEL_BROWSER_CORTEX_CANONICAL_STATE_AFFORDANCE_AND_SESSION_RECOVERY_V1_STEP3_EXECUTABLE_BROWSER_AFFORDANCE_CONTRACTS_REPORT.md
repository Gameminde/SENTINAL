# SENTINEL_BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1_STEP3_EXECUTABLE_BROWSER_AFFORDANCE_CONTRACTS_REPORT

Status: IMPLEMENTED_LOCAL_CANDIDATE
Date: 2026-07-22
Base commit before Step 3: 2ab4a3ff0afe86fa5bee73c5cda64e0a0291fc23
Provider calls: 0
Live browser runs: 0
Frozen holdout used: no

## Hypothesis

The model should not primarily steer browser work through one compressed `browse_search` idea. It needs distinct browser affordances, while Sentinel keeps the internal `ActionEnvelope` and runtime ownership below the model.

The smallest coherent next step is to define one canonical browser affordance contract layer and feed it into `BrowserEnvironmentState.operational_snapshot`.

## Scope

Implemented:

- `browser_affordance_contracts.py`
- distinct cognitive affordance contracts:
  - `observe`
  - `navigate`
  - `search`
  - `follow`
  - `inspect`
  - `extract_evidence`
  - `verify`
  - `recover_session`
  - `finish`
- each executable affordance includes:
  - typed input contract
  - normalized result contract
  - receipt kind
  - state delta contract
  - evidence delta contract
  - recoverable failure classes
  - blocked failure classes
  - ProductActionKernel dispatch contract
  - model strategy role
- `BrowserEnvironmentState` now consumes the affordance compiler instead of constructing a weaker local list.
- product model context continues exposing `currently_executable_affordances` through `browser_cognitive_decision_frame`.

Not implemented:

- actual `real_browser.recover_session` runtime dispatch
- session recovery state machine
- progress-based anti-repetition
- browser macro/program lane
- live browser or provider proof

## Important Boundary

`recover_session` is defined as a future/known cognitive affordance, but it is not announced unless a real runtime action is registered in the available action set.

This preserves the rule:

```text
Never show the model a hand that Sentinel cannot actually execute.
```

## Model Amplification Doctrine

The contracts do not force a trajectory. They describe available body affordances.

```text
recommended actions = advisory
affordance contract = executable shape and proof expectation
ActionEnvelope = internal runtime language
ProductActionKernel = required dispatch owner
```

The model remains responsible for strategy, interpretation and alternate safe paths.

## Behavior Before

The browser state could say that search, extract or finish were available, but the model did not receive a uniform contract for:

- typed parameters
- success/recoverable/blocked result shape
- receipt ownership
- expected state delta
- expected evidence delta
- mechanical versus cognitive responsibility

## Behavior After

Each currently executable browser affordance in the operational snapshot now carries its own contract.

Example shape:

```text
skill
capability_id
operation
precondition_status
reason
typed_input_contract
normalized_result_contract
receipt_kind
state_delta_contract
evidence_delta_contract
recoverable_failure_classes
blocked_failure_classes
dispatch_contract = ProductActionKernel
model_strategy_role = affordance_not_forced_trajectory
```

## Local Proof

Added tests prove:

- all available browser cognitive affordances are distinct and ProductActionKernel-routed
- `navigate` maps to `real_browser.open`
- `follow` maps to `real_browser.open_result`
- `extract_evidence` maps to the generic open-world extraction action
- non-executable actions are hidden from the current affordance list
- `recover_session` is not exposed unless the runtime action is registered
- `finish` requires proof-lane eligibility
- the Product Loop model context receives typed affordance contracts

## Validation

```text
py -3.13 -m pytest tests/operator/test_browser_cortex_affordance_contracts.py tests/operator/test_browser_cortex_canonical_operational_state.py -q
RESULT: 10 passed

py -3.13 -m pytest tests/operator/test_browser_cortex_pack1_environment_state_graph.py tests/operator/test_browser_cortex_integration_pack0_executable_truth_reconciliation.py tests/operator/test_browser_cortex_divergence_harness.py -q
RESULT: 13 passed
```

```text
py -3.13 -m compileall -q sentinel
RESULT: passed

git diff --check
RESULT: passed

targeted scan for raw provider/reasoning/DOM/cookies/session/profile material/local path/binary path/fallback/provider-native/raw selector/raw URL markers
RESULT: benign defensive references only:
- raw URL is mentioned only as unknown/not exposed.
- raw DOM is mentioned only as excluded material.
- HTML markers are redacted by `_safe_text`.
- ProductActionKernel authority wording is not a provider-native or fallback path.
```

## Remaining Gaps

Next narrow sub-tranche:

```text
STEP4_SESSION_RECOVERY_STATE_MACHINE
```

It should add the real mechanical session states:

```text
ACTIVE
DEGRADED
RECOVERING
RECONNECTED
BLOCKED
CLOSED
```

And prove deterministic injected failures:

- body lost
- page detached
- root lease still alive
- bounded reconnect succeeds
- bounded reconnect exhausts
- previous evidence is either preserved or invalidated explicitly

## Verdict

```text
BROWSER_AFFORDANCE_CONTRACTS = IMPLEMENTED_LOCAL_CANDIDATE
MODEL_VISIBLE_BROWSER_AFFORDANCES_DISTINCT = PROVEN_LOCAL
PRODUCT_ACTIONKERNEL_DISPATCH_CONTRACT_EXPOSED = PROVEN_LOCAL
RECOVER_SESSION_RUNTIME = NOT_STARTED
LIVE_BROWSER_POWER = NOT_CLAIMED
REAL_MODEL_PRODUCT_POWER = NOT_CLAIMED
```
