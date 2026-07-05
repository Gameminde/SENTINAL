# SENTINEL_FIX_REAL_PRODUCT_RUN_CHECK_BOUNDED_PLAN_OWNS_PROFILE_V1_REPORT

## Verdict

```text
FIX_REAL_PRODUCT_RUN_CHECK_BOUNDED_PLAN_OWNS_PROFILE_V1 = LOCALLY_COMMITTED
implementation_commit = f235154 fix: keep product run checks bounded
provider_call_during_fix = no
real_browser_run = no
push = no
```

## 4E Failure Interpretation

4E failed because `run_check` still allowed model-supplied low-level parameters to override the bounded runtime check plan.

This is not product power. The model should not pilot shell/check backend internals.

Correct contract:

```text
model says run_check
Sentinel chooses the bounded check profile
ActionEnvelope remains internal
raw shell profile does not leak through model-facing skill
```

## Fix

When `_bounded_check_plan` exists, `ProductModelNativeDecisionClient` now ignores model-supplied `profile_id` / `args` and emits the bounded internal check plan.

If no bounded check plan exists, legacy safe defaults remain:

```text
profile_id = fake_pass
args = .
```

## Files Changed

```text
sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py
sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_run_check_uses_bounded_plan_over_model_raw_shell_params -q
result = passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=10 --maxfail=1
result = 32 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q --durations=10 --maxfail=1
result = 12 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack9_product_actionkernel_task_loop.py -q --durations=10 --maxfail=1
result = 3 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check
result = passed with CRLF warnings only
```

Targeted scan:

```text
high_risk_hits = test redaction assertions and hard-boundary strings only
```

## Hard Boundaries Preserved

Raw shell remains blocked as a product backend if it is ever reached directly. This fix prevents the model-facing `run_check` skill from requesting that backend when a bounded plan exists.

## Next Real Attempt

```text
REAL_PRODUCT_ATTEMPT_4F_SEMANTIC_CHANNEL_WORKER_FINISH_V1
```

Success requires:

```text
semantic pytest passes
bounded channel send occurs
worker verifier dispatch occurs
finish emitted
mission completed
replay no-react
artifact scan clean
```

