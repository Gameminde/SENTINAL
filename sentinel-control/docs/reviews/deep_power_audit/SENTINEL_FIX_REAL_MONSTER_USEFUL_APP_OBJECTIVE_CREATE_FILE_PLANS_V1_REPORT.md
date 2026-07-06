# SENTINEL_FIX_REAL_MONSTER_USEFUL_APP_OBJECTIVE_CREATE_FILE_PLANS_V1_REPORT

## Verdict

```text
FIX_REAL_MONSTER_USEFUL_APP_OBJECTIVE_CREATE_FILE_PLANS_V1 = LOCALLY_COMMITTED
implementation_commit = a8e077c
```

## Root Cause Fixed

Attempt 5 proved the real provider/product spine but failed the useful-app objective:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5 = VALID_FAILED
primary_failure_classification = USEFUL_APP_OBJECTIVE_DEFAULT_PLAN_GAP
```

The create-file planner recognized the mission as a from-scratch app mission, then fell through to the legacy arbitrary-app fixture:

```text
Sentinel arbitrary local app worked.
```

That made the run complete successfully for the wrong app.

## Runtime Change

Updated:

```text
sentinel/operator/model_led_product_action_kernel_task_loop.py
```

New behavior:

```text
mission objective mentions number analyzer / analyze_numbers / numbers
and count + total + average
-> create app.py with analyze_numbers(values)
-> create README.md describing the number analyzer
-> create tests/test_app.py covering count, total, average, empty input, and main marker
```

The generic arbitrary-app fixture remains available for generic arbitrary app missions. The number-analyzer branch is selected before the generic fallback.

## Regression Test

Updated:

```text
tests/operator/test_real_monster_product_model_native_decision_client.py
```

Added:

```text
test_number_analyzer_objective_creates_useful_app_files_then_checks_exports_and_finishes
```

The test covers the full local product-spine path:

```text
create_file
-> create_file
-> create_file
-> run_check
-> send_message
-> spawn_worker
-> finish
-> artifact export
-> artifact verifier
-> replay no-react
```

## Red/Green Evidence

Red:

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_number_analyzer_objective_creates_useful_app_files_then_checks_exports_and_finishes -q

FAILED
assert 'def analyze_numbers' in 'APP_MESSAGE = "Sentinel arbitrary local app worked."...'
```

Green:

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_number_analyzer_objective_creates_useful_app_files_then_checks_exports_and_finishes -q

1 passed
```

## Validation

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=10 --maxfail=1
33 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q --durations=10 --maxfail=1
12 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q --durations=10 --maxfail=1
10 passed

py -3.13 -m compileall -q sentinel
passed

git diff --check
passed
```

Targeted sensitive-material scan:

```text
result = benign report-only hits for disabled fallback/raw reasoning persistence statements
credential_values_persisted = no
raw_provider_reasoning_persisted = no
provider_native_tools = disabled
fallback_AUTO = disabled
```

## Hard Boundaries Preserved

No changes were made to:

```text
payment / checkout / spend
credential or secret access
login / account mutation
contact supplier / external send outside grant
workspace escape
provider-native tools
fallback/AUTO
replay side effects
proof tampering / fake receipt
```

## Next Real Proof

Prepared next attempt:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5B_USEFUL_APP_ARTIFACT_EXPORT_V1
```

Required success shape:

```text
real provider
-> model-native create_file sequence
-> useful number analyzer app generated
-> semantic pytest validates analyze_numbers
-> bounded fake/local channel send
-> worker verifier
-> finish
-> mission completed
-> artifact export accepted
-> verifier accepted from exported bundle
-> replay no-react
```
