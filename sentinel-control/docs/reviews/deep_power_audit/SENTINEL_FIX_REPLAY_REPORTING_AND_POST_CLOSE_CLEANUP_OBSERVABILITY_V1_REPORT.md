# SENTINEL_FIX_REPLAY_REPORTING_AND_POST_CLOSE_CLEANUP_OBSERVABILITY_V1_REPORT

## Verdict

```text
SENTINEL_FIX_REPLAY_REPORTING_AND_POST_CLOSE_CLEANUP_OBSERVABILITY_V1
= IMPLEMENTED_LOCAL_CANDIDATE

trigger = Python.org V5 golden vertical slice observability gaps
live_retry = not run in this tranche
push = not performed
```

## Trigger

V5 completed the real provider + real Cloak golden vertical slice, but exposed two proof hygiene gaps:

```text
replay wrapper rendering = safe ValidationError payload
cleanup_result.browser_lease_card = captured before resource_scope.close()
```

These did not invalidate the V5 mission, but they weakened Sentinel's proof layer for repeated live missions.

## Behavior Before

```text
ProductActionKernelTaskLoopReplay had from_store only.
Ad hoc live wrappers could accidentally instantiate it with host=... and get ValidationError.

RuntimeHost cleanup payload captured browser_lease_card before close.
cleanup_completed could be true while browser_lease_card still showed lifecycle_state=active.
```

## Behavior After

```text
ProductActionKernelTaskLoopReplay.from_host(host, mission_ids=...) routes to host.kernel.store.
ProductActionKernelTaskLoopReplay.safe_model_dump() returns bounded JSON-safe proof data.

RuntimeHost records cleanup_result.browser_lease_card after resource_scope.close().
Post-close cleanup evidence now shows closed lifecycle and released global context lock in local proof.
```

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py
```

## Tests Added

```text
test_replay_from_host_serializes_for_live_reporting
test_cleanup_result_records_post_close_browser_lease_card
```

Both tests failed before the implementation:

```text
ProductActionKernelTaskLoopReplay.from_host = missing
cleanup browser_lease_card.lifecycle_state = active
```

Both pass after the implementation.

## Validation

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_replay_from_host_serializes_for_live_reporting sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py::test_cleanup_result_records_post_close_browser_lease_card -q
result = 2 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack4_browser_l5_l6_product_backend.py -q
result = 31 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_crash_safe_bounded_live_run_evidence_sink.py -q
result = 4 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q
result = 9 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
result = passed

git diff --check
result = passed with CRLF warnings only

targeted scan for secrets/raw provider/provider-native/fallback/raw browser material
result = 0 hits
```

## Hard Boundaries Preserved

```text
authority expansion = unchanged
provider-native tools = not enabled
fallback/AUTO = not enabled
raw provider output/reasoning = not persisted
raw DOM/cookies/session/profile material = not persisted
replay side effects = not enabled
```

## Capability Truth

```text
REPLAY_REPORTING_JSON_SAFE_LOCAL = PROVEN
POST_CLOSE_CLEANUP_LEASE_CARD_LOCAL = PROVEN
LIVE_RETRY_AFTER_OBSERVABILITY_FIX = pending
MULTI_SITE_GENERALIZATION = not proven
FROZEN_HOLDOUT_GENERALIZATION = not proven
```

## Next Proof

Before broad calibration, run a small repeated non-holdout Python.org proof tranche to confirm:

```text
replay report serializes cleanly
cleanup event captures post-close lease state
real Cloak search/extract/verify/summary/finish remains stable
```
