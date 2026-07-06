# SENTINEL_FIX_REAL_MONSTER_PRODUCT_ATTEMPT6_WORKER_AND_TEST_QUALITY_GATE_V1_REPORT

## Verdict

```text
FIX_REAL_MONSTER_PRODUCT_ATTEMPT6_WORKER_AND_TEST_QUALITY_GATE_V1 = LOCALLY_COMMITTED
implementation_commit = 2f8230e8c429ea7577121a41325c304fda98adea
```

## Accepted Failure Input

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6_MULTI_WORKER_PRODUCT_BUILD_AND_VERIFY_V1 = VALID_FAILED
```

Attempt 6 proved the product spine was live with the real provider, but failed the Phase 2 delegated production threshold:

```text
provider_decision_calls = 8
mission_status = completed
product_receipt_count = 7
bounded_channel_send = true
worker_receipt_count = 1
distinct_worker_role_count = 1
artifact_export_accepted = true
artifact_verifier_accepted = true
replay_no_react = true
safety_scan_high_risk_hit_count = 0
external_pytest_exit_code = 2
```

## Root Cause

Two product-quality blockers were exposed:

```text
1. A natural finish intent could bypass a still-live preferred sequence requirement,
   allowing finish before a second required worker.

2. Model-created root-level test files could coexist with canonical tests/test_app.py.
   The product loop checked only the canonical file, while a full workspace pytest
   later failed during collection.
```

This was not a provider, endpoint, credential, fallback, provider-native-tool, or artifact-export failure.

## Runtime Changes

Changed:

```text
sentinel/operator/product_model_native_decision_client.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
tests/operator/test_real_monster_product_model_native_decision_client.py
```

Behavior before:

```text
finish intent could become sentinel_loop.finish even when preferred sequence still required another worker
run_check/send/worker/finish intent could outrank pending workspace quality setup
root-level test files could remain collectible outside the product bounded check path
```

Behavior after:

```text
finish intent is rerouted to the next live preferred sequence skill when the sequence is incomplete
pending workspace quality plans outrank run_check/send/worker/finish
root-level test*.py plus canonical tests/test_app.py creates a pytest.ini product hygiene plan
pytest.ini constrains test collection to tests/
local Phase 2 proof completes with two distinct workers before finish
```

## Local 6B Proof

A focused local/fake mission now proves the fixed path:

```text
root-level malformed test file created
app.py created
README.md created
tests/test_app.py created
pytest.ini created with testpaths = tests
semantic pytest_file check passes
bounded fake/local channel sends
researcher worker spawns
report_writer worker spawns
sentinel_loop.finish emits
mission completes
replay no-react holds
```

Expected local sequence:

```text
workspace_patch:apply_patch
workspace_patch:apply_patch
workspace_patch:apply_patch
workspace_patch:apply_patch
workspace_patch:apply_patch
code_execution_sandbox:code_exec.run_profile
bounded_channel:send_message
worker_fleet:spawn_worker
worker_fleet:spawn_worker
sentinel_loop:finish
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_finish_intent_before_required_second_worker_routes_to_spawn_worker tests/operator/test_real_monster_product_model_native_decision_client.py::test_root_level_test_file_is_repair_plan_before_bounded_check -q
result = 2 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_phase2_quality_gate_handles_root_test_hygiene_and_two_workers_before_finish -q
result = 1 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=10 --maxfail=1
result = 43 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack5_multi_worker_long_task_orchestration.py tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q --durations=10 --maxfail=1
result = 16 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check
result = passed with CRLF warnings only
```

Targeted scan:

```text
secret hits = 0
raw provider/reasoning persistence = no
provider-native tools introduced = no
fallback/AUTO introduced = no
scan notes = only expected redaction-test marker strings were found
```

## Hard Boundaries Preserved

```text
provider-native tools disabled
fallback/AUTO disabled
real browser not run
real external channel not sent
worker authority remains reduced
authority expansion remains blocked
receipt/FinalGate/replay proof preserved
raw provider/reasoning/credential/session persistence not introduced
```

## Remaining Product Truth

This fix is local/focused proven. It does not by itself prove Phase 2 with the real provider.

Required next real attempt:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6B_MULTI_WORKER_QUALITY_GATED_PRODUCT_BUILD_V1
```

Success target:

```text
real provider drives product loop
semantic tests pass
bounded fake/local channel receipt exists
worker_receipts >= 2
distinct_worker_roles >= 2
worker_authority_expanded = false for every worker
artifact export accepted
offline verifier accepted
mission_status = completed
finish emitted after quality gates
replay_no_react = true
safety_scan_high_risk_hit_count = 0
```
