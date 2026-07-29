# SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE_REPORT

## Verdict

```text
SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE
= VALID_INFRA_BLOCKED_PROVIDER_AUTH_ERROR

FIXED_PROVEN_COUNT = 0
REAL_PROVIDER_REACHED = yes
REAL_MODEL_DECISION_ACCEPTED = no
MATERIAL_WORKSPACE_ACTIONS = 0
```

The tranche improved the canonical core product path locally, then attempted a
real provider mission. The live mission could not complete because the only
configured real provider credential was rejected by the provider.

This is not claimed as `FIXED_PROVEN`.

## Implemented Product Path

```text
public CLI request
-> MissionKernel MissionRecord created before provider
-> model decision request
-> DecisionProtocol + DecisionOrigin
-> CanonicalState projection with recent observations
-> executable workspace capability graph
-> workspace list/read/search route
-> typed CanonicalEffectReceipt
-> MissionKernel receipt artifacts
-> mission_kernel_receipt_timeline_v1 proof root
-> terminal mission state
-> cleanup event
```

`ActionEnvelope` remains accepted only through the legacy adapter protocol:

```text
DecisionProtocol.LEGACY_ACTION_ENVELOPE_ADAPTER_V1
```

The model-facing/current canonical decision path is:

```text
DecisionProtocol.MODEL_NATIVE_CANONICAL_JSON_V1
DecisionOrigin.MODEL_SELECTED
```

## Files Changed

```text
sentinel/operator/canonical_core.py
sentinel/cli.py
tests/operator/test_sentinel_dev_max_power_canonical_core_v1.py
docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_FINDING_LEDGER.json
docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_METHODOLOGY_RECONCILIATION_REPORT.md
docs/reviews/deep_power_audit/SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE_REPORT.md
```

## Local Proof

Local deterministic tests prove:

```text
MissionRecord durable before first model turn = true
DecisionProtocol persisted = true
DecisionOrigin persisted = true
CanonicalState recent_observations reaches next turn = true
workspace.list/read/search executable route = true
receipt artifacts written = true
proof root written = true
record hash verified = true
kernel timeline verified = true
cleanup event written = true
provider/normalization failure terminalizes mission = true
```

The product proof root now uses:

```text
integrity_model = mission_kernel_receipt_timeline_v1
authentic_external_ledger = false
proof_gaps = external_append_only_signer_missing
```

Therefore `P0-07` is `IMPLEMENTING`, not `FIXED_PROVEN`.

## Real Provider Attempts

### V1 DeepSeek

```text
provider = aliyun_dashscope/deepseek-v4-pro
mission_record_before_provider = true
terminal_state = not correctly persisted before fix
material_actions = 0
classification = VALID_FAILED_OBSERVABILITY_BEFORE_FIX
```

The first attempt exposed that provider/decision exceptions could leave the
mission record in `running`. This was corrected locally with a regression test.

### V2 DeepSeek

```text
provider = aliyun_dashscope/deepseek-v4-pro
mission_record_before_provider = true
provider_decision_count = 1
material_actions = 0
terminal_state = blocked
cleanup = true
classification = VALID_FAILED_MODEL_DECISION_FAILED
```

This run terminalized correctly, but the failure code was not yet specific
enough. The failure telemetry was improved locally.

### V3 GLM

```text
provider = aliyun_dashscope/glm-5.2
mission_record_before_provider = true
provider_decision_count = 1
material_actions = 0
terminal_state = blocked
cleanup = true
failure_code = canonical_provider_failure_PROVIDER_AUTH_ERROR
classification = VALID_INFRA_BLOCKED_PROVIDER_AUTH_ERROR
```

Only `SENTINEL_CERT_MODEL_API_KEY` is configured locally. No other cataloged
real provider credential is present in the process or user environment.

## Gates

```text
MissionRecord durable before provider = PASS
DecisionProtocol local = PASS
DecisionOrigin local = PASS
CanonicalState projection local = PASS
Executable workspace route local = PASS
Typed effect receipt local = PASS
Kernel proof root local = PASS_WITH_EXTERNAL_SIGNER_GAP
Terminal state after provider failure = PASS
Cleanup after provider failure = PASS
Real provider authenticated = FAIL
Real model decision accepted = FAIL
Material workspace effect via real model = NOT_REACHED
FIXED_PROVEN = NO
```

## Ledger Truth

```text
fixed_proven_count = 0
status_counts = CONFIRMED_CURRENT:9, IMPLEMENTING:8, OPEN:48
P0-07 = IMPLEMENTING
canonical_core_vertical_product_tranche = VALID_INFRA_BLOCKED_PROVIDER_AUTH_ERROR
```

No P0 is closed.

## Next

The immediate blocker is provider credential/authorization, not Browser Organ
or workspace execution:

```text
PROVIDER_AUTH_ERROR
```

After a valid provider credential is restored, rerun the same canonical product
workspace vertical slice once. If it accepts a model decision and completes a
workspace action, the next required work is:

```text
physical provider cancellation
-> physical sandbox
```

Do not return to Browser Organ for this foundation tranche.
