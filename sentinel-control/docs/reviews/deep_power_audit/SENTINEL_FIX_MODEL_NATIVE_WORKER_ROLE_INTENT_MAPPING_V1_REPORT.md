# SENTINEL_FIX_MODEL_NATIVE_WORKER_ROLE_INTENT_MAPPING_V1_REPORT

## Verdict

```text
FIX_MODEL_NATIVE_WORKER_ROLE_INTENT_MAPPING_V1 = IMPLEMENTED
```

## Why This Fix Was Needed

After `REAL_MONSTER_PRODUCT_ATTEMPT_5C` proved the unified product spine, Phase 2 requires meaningful delegated worker power. Before this fix, natural model replies such as:

```text
Delegate a code fixer worker...
Spawn a verifier worker...
Ask a report writer worker...
```

could collapse into the default `verifier` worker or, in one case, route to `run_check` because the word `check` outranked the worker intent.

That would risk a false Phase 2 proof: two decorative/default workers instead of distinct delegated roles.

## Behavior Changed

Model-native worker intent now maps natural role language into bounded worker roles:

```text
code fixer / implementation -> code_fixer
verifier / verify -> verifier
report writer / summarize -> report_writer
researcher / research -> researcher
browser operator -> browser_operator
```

The runtime still owns authority and execution. The model can request a role, but `WorkerOrchestrationRuntime` still delegates reduced child authority and blocks unsupported/high-risk worker requests.

## Files Changed

```text
sentinel/operator/product_model_native_decision_client.py
tests/operator/test_real_monster_product_model_native_decision_client.py
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_natural_worker_role_intent_maps_to_reduced_worker_role -q
4 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=10 --maxfail=1
38 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack5_multi_worker_long_task_orchestration.py -q --durations=10 --maxfail=1
6 passed

py -3.13 -m compileall -q sentinel
passed
```

## Hard Boundaries

Unchanged:

```text
payment / checkout / spend
credentials / secrets
login / account mutation
real external channel without grant
provider-native tools
fallback/AUTO
workspace escape
replay side effects
fake proof / proof tampering
```

## Next

Proceed to:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6_MULTI_WORKER_PRODUCT_BUILD_AND_VERIFY_V1
```

with reduced-authority multi-worker delegation as the target proof.
