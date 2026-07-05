# SENTINEL_FIX_REAL_PRODUCT_PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION_V1_REPORT

## Verdict

```text
FIX_REAL_PRODUCT_PROVIDER_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION_V1 = LOCALLY_COMMITTED_IMPLEMENTED_CANDIDATE
implementation_commit = 1652ca4
product_proven = no
push_performed = false
```

## Accepted Failure

```text
REAL_PRODUCT_ATTEMPT_3_USEFUL_MULTI_FILE_LOCAL_APP_CREATION_CHECK_VERIFY_V1 = VALID_FAILED
primary_failure_classification = PROVIDER_DECISION_FAILURE_EMPTY_VISIBLE_CONTENT_BEFORE_MATERIAL_ACTION
provider_calls = 1
material_actions = 0
```

Attempt 3 proved the real provider route was reached but returned no visible actionable decision content on the first turn. Sentinel correctly refused to transform that empty turn into a fake patch action.

## Root Cause

Before this fix:

```text
provider parsed payload reports empty visible content
ProductModelNativeDecisionClient can fall through to recommended skill
or a strict run wrapper blocks terminally before first material action
ModelLedProductActionKernelTaskLoop has no explicit pre-material recovery lane
```

That means the product spine had two bad options:

```text
fake progress from a recommendation
or terminal mission death before first material action
```

The Monster Runtime rule needs the third path:

```text
empty provider content before material action
-> typed recoverable observation
-> explicit counted recovery turn if the attempt contract allows it
```

## Runtime Changes

Files changed:

```text
sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py
sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py
sentinel-control/services/sentinel-core/sentinel/operator/runtime_host.py
sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py
```

Behavior added:

```text
empty_visible_content -> MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT
unsupported visible decision content -> MODEL_NATIVE_DECISION_VISIBLE_CONTENT_UNSUPPORTED
default behavior remains no silent retry
opt-in max_recoverable_model_decision_failures enables explicit pre-material recovery
recovery observations are exposed to the next model turn
recovery prompt asks for visible compact JSON skill content
model_call_count includes failed decision attempts
```

## No Fake Progress Proof

```text
empty provider content does not map to patch
empty provider content does not consume a material action
empty provider content does not create receipt
empty provider content does not create FinalGate success
```

## Recovery Proof

With opt-in recovery:

```text
turn 1 = MODEL_NATIVE_DECISION_EMPTY_VISIBLE_CONTENT
turn 2 context includes recoverable_decision_observations
turn 2 can emit material skill
turn 3 can finish after receipt
```

Default behavior:

```text
max_recoverable_model_decision_failures = 0
empty visible content blocks honestly
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_empty_visible_provider_content_blocks_instead_of_falling_back_to_patch tests/operator/test_real_monster_product_model_native_decision_client.py::test_product_loop_can_recover_once_from_empty_visible_content_before_material_action tests/operator/test_real_monster_product_model_native_decision_client.py::test_product_loop_default_blocks_empty_visible_content_before_material_action -q
result: 3 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q
result: 44 passed

py -3.13 -m compileall -q sentinel
result: passed

git diff --check
result: passed for touched files
```

Targeted unsafe-material scan:

```text
result = intentional guard constants and redaction regression tests only
provider_native_tools = false
fallback_AUTO = false
provider_prompt_or_response_body_persisted = false
credential_or_session_material_persisted = false
```

## Hard Boundaries Preserved

```text
payment = hard stop
credential access = hard stop
login/account mutation = hard stop
contact supplier/out-of-grant external send = hard stop
provider-native tools = disabled
fallback/AUTO = disabled
replay side effects = blocked by no-react replay contract
fake receipts = not introduced
```

## Remaining Product Truth

This fix is local/fake proven only.

It does not prove the real provider will now complete the multi-file app mission. It only gives the product loop an explicit recovery lane if the first provider turn is empty again.

## Next Prepared Real Attempt

```text
REAL_PRODUCT_ATTEMPT_3B_USEFUL_MULTI_FILE_LOCAL_APP_CREATION_CHECK_VERIFY_V1
```

Recommended 3B contract:

```text
one provider mission
no silent retry
max_recoverable_model_decision_failures = 1
provider_decision_calls counted including recovery
workspace_patch.apply_patch count >= 3
bounded check run
fake/local channel receipt
worker verifier receipt
sentinel_loop.finish
mission completed
artifact bundle accepted
offline verifier accepted
replay no-react
unsafe-material scan clean
```
