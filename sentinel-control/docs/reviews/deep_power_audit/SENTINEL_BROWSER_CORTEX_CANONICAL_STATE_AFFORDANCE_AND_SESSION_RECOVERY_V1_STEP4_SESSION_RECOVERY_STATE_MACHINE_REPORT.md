# SENTINEL_BROWSER_CORTEX_CANONICAL_STATE_AFFORDANCE_AND_SESSION_RECOVERY_V1_STEP4_SESSION_RECOVERY_STATE_MACHINE_REPORT

Status: IMPLEMENTED_LOCAL_CANDIDATE
Date: 2026-07-22
Base commit before Step 4: 8d4d2895a03666e397c52b09c90f84158385958b
Provider calls: 0
Live browser runs: 0
Frozen holdout used: no

## Hypothesis

The root browser body already existed, but its lifecycle vocabulary was legacy and not precise enough for control-system reasoning. A recoverable page/session failure should degrade the root lease, attempt bounded mechanical recovery, then record an explicit recovery or block state.

The next useful correction is a small lease-level state machine, not a new browser cognition pack.

## Implemented State Machine

Canonical state vocabulary:

```text
ACTIVE
DEGRADED
RECOVERING
RECONNECTED
BLOCKED
CLOSED
```

The legacy `lifecycle_state` field is preserved for older reports and tests. The new authoritative browser body state is:

```text
browser_session_state
previous_browser_session_state
browser_session_state_history
last_state_transition_reason
last_failure_fingerprint
```

## Product Path Integration

The product path now marks the root browser lease as degraded when a receipt-backed body/session failure is observed:

```text
RuntimeHost
-> ProductActionKernelDispatchAdapter
-> _default_real_browser_executor
-> body failure detected
-> root lease DEGRADED
-> bounded recovery RECOVERING
-> recovered engine RECONNECTED
-> second body failure DEGRADED
-> body circuit breaker BLOCKED
```

This does not expose a new `recover_session` model action yet. It gives the existing product path an observable mechanical recovery state.

## Behavior Before

The lease used legacy lifecycle strings such as:

```text
created
active
recovering
active_after_recovery
closed
```

Those strings were enough for simple cleanup reports, but too weak for the Browser Cortex loop because the model needs to know whether the body is active, degraded, recovering, reconnected, blocked or closed.

## Behavior After

The lease card keeps the old field and adds the canonical control state:

```text
lifecycle_state = active_after_recovery
browser_session_state = RECONNECTED
previous_browser_session_state = RECOVERING
browser_session_state_history = [..., DEGRADED, RECOVERING, RECONNECTED]
```

When bounded recovery is exhausted:

```text
browser_session_state = BLOCKED
last_state_transition_reason = body_session_unavailable_after_bounded_recovery
```

When cleanup closes the root lease:

```text
lifecycle_state = closed
browser_session_state = CLOSED
global_context_lock_acquired = false
```

## Local Proof

Added tests prove:

- root lease records `DEGRADED -> RECOVERING -> RECONNECTED` after an injected body degradation
- recovery exhaustion transitions the root lease to `BLOCKED`
- cleanup preserves legacy `lifecycle_state = closed` and adds `browser_session_state = CLOSED`
- product path body-session failure marks the root lease `BLOCKED` in the body circuit breaker card before final cleanup

## Validation

```text
py -3.13 -m pytest tests/operator/test_browser_cortex_session_recovery_state_machine.py -q
RESULT: 4 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_cleanup_result_records_post_close_browser_lease_card tests/operator/test_browser_cortex_canonical_operational_state.py -q
RESULT: 7 passed
```

```text
py -3.13 -m pytest tests/operator/test_browser_cortex_affordance_contracts.py tests/operator/test_browser_cortex_canonical_operational_state.py tests/operator/test_browser_cortex_session_recovery_state_machine.py -q
RESULT: 14 passed

py -3.13 -m pytest tests/operator/test_browser_cortex_pack1_environment_state_graph.py tests/operator/test_browser_cortex_integration_pack0_executable_truth_reconciliation.py tests/operator/test_browser_cortex_divergence_harness.py -q
RESULT: 13 passed

py -3.13 -m compileall -q sentinel
RESULT: passed

git diff --check
RESULT: passed

targeted scan for raw provider/reasoning/DOM/cookies/session/profile material/local path/binary path/fallback/provider-native/raw selector/raw URL/secret value markers
RESULT: no hits in Step 4 changed files and report
```

## Remaining Gaps

Next narrow sub-tranche:

```text
STEP5_PROGRESS_BASED_ANTI_REPETITION_GUARD
```

It should use:

```text
normalized action
+ normalized params hash
+ state fingerprint
+ evidence fingerprint
```

Without meaningful progress:

```text
first repetition -> choose another affordance
second repetition -> observe or recover_session
third repetition -> honest blocker with attempt history
```

Still not implemented:

- public `real_browser.recover_session` dispatch route
- full live Cloak session recovery proof
- multi-site reliability proof
- real provider proof after these local control corrections

## Verdict

```text
BROWSER_ROOT_SESSION_STATE_MACHINE = IMPLEMENTED_LOCAL_CANDIDATE
ROOT_LEASE_RECOVERY_TRANSITIONS = PROVEN_LOCAL
PRODUCT_BODY_FAILURE_TO_BLOCKED_LEASE_CARD = PROVEN_LOCAL
RECOVER_SESSION_MODEL_ACTION = NOT_STARTED
LIVE_BROWSER_RECOVERY = NOT_CLAIMED
REAL_MODEL_PRODUCT_POWER = NOT_CLAIMED
```
