# SENTINEL_FIX_PRODUCT_TASK_LOOP_MISSION_WORKSPACE_BODY_FOR_CHANNEL_ONLY_RUNS_V1_REPORT

## Verdict

```text
FIX_PRODUCT_TASK_LOOP_MISSION_WORKSPACE_BODY_FOR_CHANNEL_ONLY_RUNS_V1 = IMPLEMENTED
```

This fix closes the artifact-export gap exposed by:

```text
REAL_MONSTER_PRODUCT_ATTEMPT_7A_REAL_TELEGRAM_PRODUCT_SPINE_SEND_V1
```

## 7A Failure Interpretation

7A proved:

```text
real provider -> ProductActionKernel task loop -> real Telegram send -> receipt -> finish -> replay no-resend
```

But artifact export failed:

```text
artifact_export_failure = ValueError
root_cause = channel-only product loop mission lacked mission_workspace/manifest.json
```

The signer/verifier layer expects a mission workspace body and artifact export handle. Channel-only product missions were producing channel and ProductActionKernel artifacts, but not the unified mission body.

## Runtime Change

File changed:

```text
sentinel/operator/model_led_product_action_kernel_task_loop.py
```

Before:

```text
ProductActionKernel task-loop missions prepared mission_workspace only indirectly when a backend needed it.
Channel-only missions could complete without a mission_workspace manifest.
MissionArtifactBundleExporter then failed on channel-only runs.
```

After:

```text
Every ProductActionKernel task-loop material mission prepares MissionWorkspaceRuntime before dispatch.
The mission_workspace manifest includes the artifact_export handle required by the bundle exporter.
Channel destination refs are recorded as hashes in the mission workspace manifest.
```

Additional correctness tightening:

```text
Telegram channel authority is no longer inferred solely from a model decision.
The loop adds channel:telegram only when the mission already has telegram:configured-chat in allowed_domains.
No silent model-created Telegram grant.
```

## Regression Test

File changed:

```text
tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py
```

Added:

```text
test_channel_only_product_loop_exports_mission_workspace_bundle
```

The test proves:

```text
bounded_channel.send_message -> finish
channel-only product loop
mission_workspace/manifest.json exists
artifact bundle export accepted
verifier_result accepted
replay no_channel_resend = true
```

## Validation

Commands run:

```text
py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py::test_channel_only_product_loop_exports_mission_workspace_bundle -q
result = passed

py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q --durations=10 --maxfail=1
result = 11 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q --durations=15 --maxfail=1
result = 12 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=15 --maxfail=1
result = 48 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py tests/operator/test_power_pack5_real_channel_transport_send.py -q --durations=15 --maxfail=1
result = 27 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py::test_channel_only_product_loop_exports_mission_workspace_bundle tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py::test_real_channel_transport_blocked_without_explicit_grant tests/operator/test_real_monster_product_model_native_decision_client.py::test_product_loop_routes_model_native_send_to_granted_telegram_transport -q
result = 3 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check -- sentinel-control/services/sentinel-core/sentinel/operator/model_led_product_action_kernel_task_loop.py sentinel-control/services/sentinel-core/tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py
result = passed
```

The first combined `pack10 + real_monster_model_native` validation command timed out at the tool level because the `real_monster` test file is slow. It was rerun as two separate commands and both passed.

Targeted scan over changed files:

```text
secret values persisted = false
provider-native tools introduced = false
fallback/AUTO introduced = false
raw provider/reasoning persistence introduced = false
cookie/session persistence introduced = false
```

The only scan hits were assertion strings in an existing redaction test.

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
REAL_MONSTER_PRODUCT_ATTEMPT_7B_REAL_TELEGRAM_PRODUCT_SPINE_ARTIFACT_BUNDLE_V1
```

Target:

```text
real provider
-> model-native send_message
-> real Telegram product-spine send
-> finish
-> mission_workspace manifest present
-> artifact bundle export accepted
-> verifier accepted
-> replay no-resend
```
