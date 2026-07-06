# SENTINEL_FIX_MODEL_NATIVE_CANONICAL_PAYLOAD_REMAP_TO_SAFE_SKILLS_V1_REPORT

## Verdict

```text
FIX_MODEL_NATIVE_CANONICAL_PAYLOAD_REMAP_TO_SAFE_SKILLS_V1 = IMPLEMENTED
```

This fix closes the blocker exposed by:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_7B_REAL_TELEGRAM_PRODUCT_SPINE_ARTIFACT_BUNDLE_V1
```

## Problem

The model-native decision client accepted provider output containing:

```text
capability_id
operation
params
```

as raw internal `ActionEnvelope` language. That let model-supplied parameters approach mission creation and triggered:

```text
mission_execution_request_parameters: unsafe operator payload
```

The scanner was correct to block it. The model-facing contract was wrong.

## Runtime Change

File changed:

```text
sentinel/operator/product_model_native_decision_client.py
```

Before:

```text
known capability_id/operation payload -> __canonical__ -> raw ActionEnvelope params
```

After:

```text
known product capability_id/operation payload
-> simple skill
-> safe internal ActionEnvelope rebuilt from plans/grants/context
```

Mappings added:

```text
bounded_channel.send_message -> send_message
code_execution_sandbox.code_exec.run_profile -> run_check
workspace_patch.apply_patch -> patch/create_file
worker_fleet.spawn_worker -> spawn_worker
sentinel_loop.finish -> finish
real_browser_control.real_browser.search/open_result/inspect_result -> browse_search
real_browser_control.real_browser.extract_product_cards -> extract
```

Unknown canonical payloads remain on the compatibility path.

## Regression Test

File changed:

```text
tests/operator/test_real_monster_product_model_native_decision_client.py
```

Added:

```text
test_canonicalish_bounded_channel_output_is_remapped_through_granted_telegram_destination
```

The test proves:

```text
provider emits bounded_channel.send_message-like payload
model-supplied adapter is ignored
model-supplied authority/control fields are discarded
telegram destination comes from mission-level grant
ActionEnvelope remains internal runtime format
```

## Validation

Commands run:

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_canonicalish_bounded_channel_output_is_remapped_through_granted_telegram_destination -q
result = passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=15 --maxfail=1
result = 49 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q --durations=15 --maxfail=1
result = 23 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py tests/operator/test_power_pack5_real_channel_transport_send.py -q --durations=15 --maxfail=1
result = 27 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check -- sentinel-control/services/sentinel-core/sentinel/operator/product_model_native_decision_client.py sentinel-control/services/sentinel-core/tests/operator/test_real_monster_product_model_native_decision_client.py
result = passed
```

Targeted scan:

```text
secret values persisted = false
provider-native tools introduced = false
fallback/AUTO introduced = false
raw provider/reasoning persistence introduced = false
cookie/session persistence introduced = false
```

Scan hits were existing redaction-test strings and guard strings only.

## Hard Boundaries Preserved

```text
payment / checkout / spend = still blocked
credential or secret access = still blocked
login / account mutation = still blocked
contact supplier outside grant = still blocked
provider-native tools = still blocked
fallback/AUTO = still blocked
replay side effects = still blocked
```

## Next Real Proof

Prepared next attempt:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_7C_REAL_TELEGRAM_PRODUCT_SPINE_ARTIFACT_BUNDLE_V1
```

Target:

```text
real provider
-> model-native or canonical-ish send intent
-> safe skill remap
-> real Telegram send
-> finish
-> mission workspace artifact bundle
-> verifier accepted
-> replay no-resend
```
