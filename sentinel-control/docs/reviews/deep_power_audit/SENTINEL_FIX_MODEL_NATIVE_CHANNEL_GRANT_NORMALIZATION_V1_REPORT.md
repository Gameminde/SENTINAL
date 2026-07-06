# SENTINEL_FIX_MODEL_NATIVE_CHANNEL_GRANT_NORMALIZATION_V1_REPORT

## Verdict

```text
FIX_MODEL_NATIVE_CHANNEL_GRANT_NORMALIZATION_V1 = LOCALLY_COMMITTED
implementation_commit = 9c69c2c
```

## 5B Failure Interpreted

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5B_USEFUL_APP_ARTIFACT_EXPORT_V1 = VALID_FAILED
primary_failure_classification = MODEL_SUPPLIED_CHANNEL_FIELD_OVERRIDES_GRANTED_LOCAL_CHANNEL
```

5B proved:

```text
real provider reached
useful number analyzer app created
semantic pytest passed = 3 passed
product receipts before channel = 4
```

5B failed because the model supplied a channel payload field:

```text
channel = bounded_local_channel
```

The model may author message content, but Sentinel must own the granted local/fake transport fields.

## Runtime Change

Updated:

```text
sentinel/operator/product_model_native_decision_client.py
```

Before:

```text
_channel_params copied model params first and used setdefault for adapter/channel/recipients.
```

After:

```text
model-supplied body/message/text may become bounded message body
adapter_id = monster_fake_channel is runtime-owned
channel = webhook is runtime-owned
recipients = founder@example.com is runtime-owned
recipient_provenance = mission_level_destination_grant is runtime-owned
evidence_refs and idempotency_key are runtime-owned
```

## Regression Test

Updated:

```text
tests/operator/test_real_monster_product_model_native_decision_client.py
```

Added:

```text
test_model_supplied_channel_fields_cannot_override_granted_local_channel
```

The red failure showed:

```text
actual adapter_id = untrusted_adapter
expected adapter_id = monster_fake_channel
```

The green behavior preserves the model-authored message while stripping model-authored transport/destination fields.

## Validation

```text
py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_model_supplied_channel_fields_cannot_override_granted_local_channel -q
1 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_metadata_reply_natural_send_message_maps_to_bounded_channel -q
1 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=10 --maxfail=1
34 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_pack10_product_task_loop_runtimehost_entrypoint.py -q --durations=10 --maxfail=1
12 passed

py -3.13 -m pytest tests/operator/test_power_unification_pack6_signed_mission_artifacts_and_replay_verifier.py -q --durations=10 --maxfail=1
10 passed

py -3.13 -m compileall -q sentinel
passed

git diff --check
passed
```

Targeted scan:

```text
hits = benign test assertions for attacker@example.com and forbidden raw reasoning test strings
credential_values_persisted = no
raw_provider_reasoning_persisted = no
provider_native_tools = disabled
fallback_AUTO = disabled
```

## Hard Boundaries Preserved

The fix tightens the channel authority boundary. It does not weaken:

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

```text
REAL_MONSTER_PRODUCT_ATTEMPT_5C_CHANNEL_GRANT_NORMALIZED_USEFUL_APP_EXPORT_V1
```

Expected proof:

```text
real provider
-> useful number analyzer app
-> semantic pytest passes
-> bounded fake/local channel receipt
-> worker verifier receipt
-> finish
-> artifact export accepted
-> verifier accepted
-> replay no-react
```
