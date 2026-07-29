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
real provider mission. A post-review corrective pass widened terminalization,
centralized workspace route registration, bounded workspace search, and made
provider auth diagnostics specific without storing raw secrets.

The live mission still could not complete because the configured provider
credential is present but not authorized for the selected model/workspace route:

```text
safe_cause = model_or_workspace_unauthorized_http_403
```

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

## Post-Review Corrective Pass

```text
base_checkpoint = a4538e3d36b677c8f49952117d1c6b8950a470a8
ledger_checkpoint_truth = synchronized to a4538e3d
provider_failure_diagnosis = model_or_workspace_unauthorized_http_403
FIXED_PROVEN_COUNT = 0
```

Corrections applied:

```text
model-client-missing fence = persistent terminal MissionRecord
provider/normalization fence = persistent terminal MissionRecord with safe detail
dispatch/workspace/receipt/proof/cleanup fence = typed safe failure path
workspace.search escape probes = symlink/junction outside-root skip
workspace.search limits = max files + max bytes + safe I/O skip counters
capability executor registry = callable-backed route table
model-visible schema = generated from executable capability graph
authority gate = enforced centrally before each registered effect
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

This attempt used the then-current `SENTINEL_CERT_MODEL_API_KEY` value and
stopped before any model-native decision.

### V4/V5 Corrective Diagnosis

```text
provider = aliyun_dashscope/glm-5.2
mission_record_before_provider = true
provider_decision_count = 1
material_actions = 0
terminal_state = blocked
cleanup = true
failure_code = canonical_provider_failure_PROVIDER_AUTH_ERROR_model_or_workspace_unauthorized_http_403
classification = VALID_INFRA_BLOCKED_PROVIDER_AUTH_ERROR
raw_secret_persisted = false
```

This distinguishes the current blocker from a missing local key. The credential
exists in the local environment, the provider/backend route is constructed, and
the provider rejected access with `403`.

### V6/V7/V8 Explicit Credential And Model Checks

```text
V6 = glm-5.2 with operator-supplied CSV key
V7 = deepseek-v4-pro with operator-supplied CSV key
V8 = deepseek-v4-pro with older User-env key

provider = aliyun_dashscope
backend = aliyun_openai_compatible_chat
provider_decision_count_each = 1
material_actions_each = 0
terminal_state_each = blocked
cleanup_each = true
failure_code_each = canonical_provider_failure_PROVIDER_AUTH_ERROR_model_or_workspace_unauthorized_http_403
raw_secret_persisted = false
```

The two tested credential values were distinct by safe hash prefix. Both
configured models returned `403`, so the current blocker is classified as a
common provider/model/workspace entitlement block rather than a Sentinel
normalization, workspace, or receipt dispatch defect.

### V9/V10/V11 Default Workspace Qwen Checks

Official Alibaba Cloud Model Studio documentation says the Singapore
OpenAI-compatible endpoint uses:

```text
https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1
```

and the first-call Qwen example uses:

```text
model = qwen-plus
```

The operator-provided Default Workspace CSV was tested process-scoped only.

```text
direct qwen-plus smoke = HTTP 200
content_matches_expected = true
raw_secret_persisted = false
```

The first Sentinel `qwen-plus` product run reached the provider but failed
normalization because Qwen returned a compact registered affordance shape:

```text
{"operation": "workspace.search", "arguments": {...}}
```

The adapter was corrected to accept exact registered affordance operations
without accepting arbitrary capabilities.

The second Sentinel `qwen-plus` product run reached the real provider and
executed material workspace receipts:

```text
provider = aliyun_dashscope/qwen-plus
provider_decision_count = 8
material_actions = 7
model_native_decisions_accepted = true
workspace_receipts_created = 7
terminal_state = blocked
final_reason = MODEL_DECISION_FAILED
blocked_reason_detail = canonical_provider_blocked_TIMEOUT
model_selected_finish = false
receipt_artifacts_verified = false
cleanup = true
```

This is meaningful progress, but it is not `FIXED_PROVEN`: the mission repeated
zero-result workspace searches and timed out before a grounded finish. DeepSeek
with the same Default Workspace key and endpoint returned:

```text
failure_code = canonical_provider_failure_PROVIDER_BAD_REQUEST_http_400
provider_decision_count = 1
material_actions = 0
```

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
ledger_synced_checkpoint = 0701297e6f3e5f236f4f51acc1539e62f099be72
fixed_proven_count = 0
P0 fixed / 15 = 0/15
P1 fixed / 44 = 0/44
P2 fixed / 6 = 0/6
total FIXED_PROVEN / 65 = 0/65
status_counts = CONFIRMED_CURRENT:9, IMPLEMENTING:8, OPEN:48
P0-07 = IMPLEMENTING
canonical_core_vertical_product_tranche = VALID_INFRA_BLOCKED_PROVIDER_AUTH_ERROR
```

No P0 is closed.

First candidates waiting for `FIXED_PROVEN` proof:

```text
P0-01 = public product route reached provider, but no model-native workspace effect yet
C-P0-01 = RootMissionRuntime owns local canonical workspace route, but no real mission completion yet
C-P0-06 = executable capability graph drives schema/dispatch locally, but full organ graph remains future
P0-07 = MissionKernel receipt timeline proof root exists locally, but external append-only proof is missing
```

## Next

The immediate blocker is provider credential/authorization, not Browser Organ
or workspace execution:

```text
PROVIDER_AUTH_ERROR
safe_cause = qwen_plus_authenticated_deepseek_http_400
classification = QWEN_AUTHENTICATED_DEEPSEEK_BAD_REQUEST
```

The immediate next blocker is no longer provider authentication for every
model. `qwen-plus` authenticates and executes the product route. The next
canonical-core issue is product-loop progress and proof completion:

```text
repeated zero-result workspace.search
no model-selected finish
receipt_artifacts_verified = false
provider timeout before terminal answer
```

After this is corrected, rerun the same canonical product workspace vertical
slice with `qwen-plus`. If it reaches grounded finish with verified receipts,
the next required work is:

```text
physical provider cancellation
-> physical sandbox
```

Do not return to Browser Organ for this foundation tranche.
