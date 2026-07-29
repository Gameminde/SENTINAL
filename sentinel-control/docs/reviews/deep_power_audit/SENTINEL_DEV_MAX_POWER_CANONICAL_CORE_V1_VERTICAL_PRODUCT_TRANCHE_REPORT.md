# SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE_REPORT

## Verdict

```text
SENTINEL_DEV_MAX_POWER_CANONICAL_CORE_V1_VERTICAL_PRODUCT_TRANCHE
= VALID_REAL_MODEL_PRODUCT_COMPLETED_QWEN_FIXTURE

FIXED_PROVEN_COUNT = 1
REAL_PROVIDER_REACHED = yes
PROVIDER_AUTHENTICATED = true
REAL_MODEL_DECISION_ACCEPTED = yes
MATERIAL_WORKSPACE_ACTIONS = 1
MODEL_SELECTED_FINISH = true
RECEIPT_INTEGRITY_VERIFIED = true
```

The tranche improved the canonical core product path locally, then attempted a
real provider mission. A post-review corrective pass widened terminalization,
centralized workspace route registration, bounded workspace search, and made
provider auth diagnostics specific without storing raw secrets.

The latest controlled live `qwen-plus` mission authenticated and completed a
known-solvable workspace task through the canonical product route:

```text
classification = VALID_REAL_MODEL_PRODUCT_COMPLETED_QWEN_FIXTURE
provider authenticated = true
model-native decisions accepted = true
workspace actions = 1
model-selected finish = true
receipt integrity verified = true
```

This closes only `P0-01` as `FIXED_PROVEN`. It does not close `C-P0-01`,
`C-P0-06`, or `P0-07`.

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

This attempt used a process-scoped operator credential and stopped before any
model-native decision.

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

The credential attempts are tracked by opaque attempt IDs only. GLM and the
earlier DeepSeek attempts returned `403`, so those specific model/workspace
routes remain secondary compatibility or entitlement blockers.

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

### V12/V13 Controlled Qwen Fixture

The controlled workspace fixture verified the known North Star document before
provider consumption:

```text
precondition relative path = docs/SENTINEL_COGNITIVE_OPERATING_SYSTEM_NORTH_STAR_V1.md
precondition sha256 = a2546aff55bee134cc38b2d42287333350b0412c7f827d8001fa3c2e3370bccc
absolute path persisted = false
```

V12 proved the real model route and model-selected finish but exposed a real
receipt verifier defect under long Windows paths:

```text
provider = aliyun_dashscope/qwen-plus
provider_decision_count = 2
material_actions = 1
mission_status = completed
receipt_artifacts_verified = false
root_cause = canonical receipt verification used normal Path.exists/read_text on a MAX_PATH-length artifact path
```

The defect was fixed with a long-path regression test. V13 then replayed the
same controlled mission on a new root:

```text
runtime_head = b721ce62343316bcdbe9c792af8a0967c8ae1680
provider = aliyun_dashscope/qwen-plus
provider_decision_count = 2
material_actions = 1
model_native_decisions_accepted = true
model_selected_finish = true
mission_status = completed
receipt_artifacts_verified = true
proof_root_persisted = true
record_hash_verified = true
kernel_timeline_verified = true
cleanup = true
raw_secret_persisted = false
raw_provider_material_persisted = false
```

Final answer:

```text
MODEL is responsible for brain, reasoning, imagination, semantic judgment,
strategy, exploration, and invention. SENTINEL is responsible for digital body,
senses, canonical state, runtime, memory, skills, execution boundaries,
evidence, receipts, replay, kill, and revocation.
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
Real provider authenticated = PASS_QWEN_PLUS
Real model decision accepted = PASS
Material workspace effect via real model = PASS
Model-selected finish = PASS
Receipt integrity verified = PASS
FIXED_PROVEN = P0-01_ONLY
```

## Ledger Truth

```text
ledger_synced_checkpoint = b721ce62343316bcdbe9c792af8a0967c8ae1680
fixed_proven_count = 1
P0 fixed / 15 = 1/15
P1 fixed / 44 = 0/44
P2 fixed / 6 = 0/6
total FIXED_PROVEN / 65 = 1/65
status_counts = CONFIRMED_CURRENT:9, FIXED_PROVEN:1, IMPLEMENTING:7, OPEN:48
P0-01 = FIXED_PROVEN
P0-07 = IMPLEMENTING
canonical_core_vertical_product_tranche = VALID_REAL_MODEL_PRODUCT_COMPLETED_QWEN_FIXTURE
```

Only `P0-01` is closed.

First candidates waiting for `FIXED_PROVEN` proof:

```text
P0-01 = closed for the canonical public workspace product vertical slice
C-P0-01 = RootMissionRuntime owns local canonical workspace route, but no real mission completion yet
C-P0-06 = executable capability graph drives schema/dispatch locally, but full organ graph remains future
P0-07 = MissionKernel receipt timeline proof root exists locally, but external append-only proof is missing
```

## Next

The immediate blocker is no longer provider authentication for every model.
`qwen-plus` authenticates and executes workspace effects. DeepSeek remains a
secondary compatibility issue:

```text
classification = VALID_REAL_MODEL_PRODUCT_COMPLETED_QWEN_FIXTURE
qwen-plus = authenticated, model-native, material workspace action, model-selected finish, receipt integrity verified
deepseek-v4-pro = HTTP 400 before model decision
```

The immediate next blockers are no longer the Qwen product loop or receipt
integrity for this controlled workspace slice. The next canonical-core stages
remain:

```text
physical provider cancellation
physical sandbox boundary
external append-only proof authenticity
full organ graph migration
```

After the `P0-01` closure, the next required work is:

```text
physical provider cancellation
-> physical sandbox
```

Do not return to Browser Organ for this foundation tranche.
