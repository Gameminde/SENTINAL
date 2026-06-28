# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_ATTEMPT_6C_REAL_PROVIDER_AUTOPILOT_WITH_SUMMARY_MEMORY_TIMEOUT_TUNED

## Verdict

```text
ATTEMPT_6C_REAL_PROVIDER_AUTOPILOT_WITH_SUMMARY_MEMORY_TIMEOUT_TUNED = SUCCESS_THRESHOLD_MET
```

Recommended decision:

```text
START_CONNECTION_PACK_1_CONNECTION_SURFACE_AUDIT_V1
```

Attempt 6C proves Pack 4B with the real product route after Pack 4B.1 timeout tuning:

```text
real provider reached
model-led read-only autopilot active
provider decision calls = 3
governed read-only material actions = 3
receipts = 3
evidence artifacts = 3
mission summary artifact = 1
operator memory candidate artifact = 1
FinalGate accepted
mission completed
workspace unchanged
material replay purity held
```

## Source And Git

Source commit:

```text
473f356bb75d68842d6c1e88c6b2646d5357734c
```

Branch:

```text
experimental/real-model-lab-freeze-v1
```

Git status before run:

```text
clean, ahead of origin by 12
```

Git status after run before report creation:

```text
clean, ahead of origin by 12
```

This report is the only repository file created after the run.

## Run Root

```text
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt6c-20260628-151232
```

## Preflight Safe Facts

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = process_env:SENTINEL_ALIYUN_DASHSCOPE_BASE_URL
endpoint_hash = aec3b934d7d71744f60faa21da5f9e55e1efd715baa09306e784514497b9f271
endpoint_base_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
credential_present = true
provider-native tools disabled = true
fallback/AUTO disabled = true
Pack 4B.1 timeout flag available = true
workspace HEAD = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace clean = true
repo clean = true
```

No raw endpoint URL, API key, Authorization header, raw env value, raw prompt, raw provider response, raw reasoning, or provider wrapper payload is printed or persisted by this report.

## Command Shape

```powershell
py -3.13 -m sentinel.cli cockpit `
  --explicit-mission-bootstrap `
  --model-led-read-only-autopilot `
  --low-friction-read-only-power-mode `
  --generate-read-only-mission-summary `
  --write-operator-memory-candidate `
  --max-material-receipts 3 `
  --max-provider-decision-calls 3 `
  --provider-decision-timeout-seconds 90 `
  --run-root <RUN_ROOT>\runs `
  --model-contract <RUN_ROOT>\model-contract.json `
  --authority-scope <RUN_ROOT>\authority-scope.json `
  --workspace C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click `
  --script <RUN_ROOT>\mission-script.txt `
  --json
```

Not used:

```text
--stop-after-first-material-receipt
```

Exit code:

```text
0
```

Timeout value applied:

```text
provider_decision_timeout_seconds = 90
```

The persisted `MissionExecutionRequest.execution_options` included:

```text
generate_read_only_mission_summary
low_friction_read_only_power_mode
max_material_receipts
max_provider_decision_calls
model_led_read_only_autopilot
provider_decision_timeout_seconds
write_operator_memory_candidate
```

## IDs

```text
mission = mission_9cb154f651c146db87a254c05f16216f
request = mission_exec_req_9cce72dd71894007ae2d4ef2c7b70e0d
decision = mission_exec_decision_10d2715d6ec84874bd7e2d14a80aed56
dispatch = dispatch_d620f4383e8c48e5adf6ab62e8d092e5
FinalGate = readonly_finalgate_484d0f210065477dbdcf6c7466e7e0b5
```

## Counts

```text
provider decision calls = 3
final report calls = 0
material tool calls = 3
receipt count = 3
evidence count = 3
mission summary artifacts = 1
operator memory candidate artifacts = 1
FinalGate certificates = 1
dispatch closeouts = 1
```

Telemetry recorded three read-only decision selections for:

```text
provider = aliyun_dashscope
backend = aliyun_openai_compatible_chat
model = deepseek-v4-pro
```

Estimated token metrics:

```text
decision 1 estimated tokens = 2787
decision 2 estimated tokens = 2911
decision 3 estimated tokens = 2985
```

## Action Sequence

Safe trajectory:

```text
1. list_directory path=.
2. list_directory path=src
3. list_directory path=src/click
```

Receipt refs:

```text
readonly_receipt_b5db45175fbc471ebfdf7c1c76fa8395
readonly_receipt_be9adfb9b3eb4847bca36cbfb6172029
readonly_receipt_1009109918124960930a0c0109ffedde
```

Evidence refs:

```text
readonly_evidence_ac470152c31141d7b4df8e71e510a081
readonly_evidence_f6d6cce922c64061915555aeaf4ceff7
readonly_evidence_b0c2923ae29c4b8694dfce143ca37aa1
```

## Summary And Memory

Mission summary artifact:

```text
readonly_summary_5a44c4bed9a34730a827496a82a05dfc
```

Operator memory candidate:

```text
readonly_memory_candidate_1cece00d3094468697bcfc86cd65f821
```

Memory candidate non-authority flags:

```text
authority_granting = false
can_execute = false
can_grant_authority = false
data_not_authority = true
revocable = true
receipt_refs present = true
evidence_refs present = true
summary_ref present = true
workspace scoped = true
mission scoped = true
```

## FinalGate And Mission Status

FinalGate:

```text
status = accepted
accepted = true
reason = model_led_read_only_autopilot_material_receipt_budget_reached
certificate_hash = 9ff5de79ba747d88aab3d9260199e4f30d293a315b2e52f6aa6872471a67aa38
```

Mission status:

```text
completed
```

Dispatch closeout:

```text
completed
```

## Workspace

Workspace:

```text
C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
```

Before:

```text
HEAD = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
status = clean
fingerprint = 4c76dba88c6cd6fc740af494d84928470d60002a555670611bed3ac623183ced
```

After:

```text
HEAD = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
status = clean
fingerprint = 4c76dba88c6cd6fc740af494d84928470d60002a555670611bed3ac623183ced
```

Workspace unchanged:

```text
true
```

## Replay Purity

Replay method:

```text
ReadOnlyProductionSpineSession.build_replay()
```

Replay result:

```text
reexecuted = false
```

Replay deltas:

```text
provider calls delta = 0
model calls delta = 0
tool calls delta = 0
receipt writes delta = 0
evidence writes delta = 0
summary writes delta = 0
operator memory candidate writes delta = 0
FinalGate writes delta = 0
dispatch closeout writes delta = 0
decision checkpoint writes delta = 0
mission events delta = 0
telemetry events delta = 0
telemetry metrics delta = 0
workspace mutations delta = 0
```

Material replay purity:

```text
held
```

## Safety Scan

Scanned run artifacts outside cloned repository content for:

```text
API key
Authorization
raw_prompt
raw_response
raw_reasoning
reasoning_content
provider wrapper payload
fallback/AUTO enablement
provider-native tool enablement
```

Result:

```text
API key = not found
Authorization = not found
raw_prompt = not found
raw_response = not found
raw_reasoning = not found
reasoning_content = not found
provider wrapper payload = not found
provider-native tool enablement = not found
fallback/AUTO enablement = no real enablement found
```

Only benign negative metadata was detected in `model-contract.json`:

```text
no_fallback / no_provider_native_tools style contract notes
```

## Provider-Native Tools And Fallback

```text
provider-native tools disabled = true
fallback/AUTO disabled = true
no provider-native tool material persisted
no fallback/AUTO route used
```

## Outcome

Success threshold:

```text
provider decision calls >= 2 = true
material receipts >= 2 = true
mission summary artifact created = true
operator memory candidate artifact created = true
FinalGate accepted = true
mission completed = true
workspace unchanged = true
material replay purity held = true
no fallback/AUTO = true
no provider-native tools = true
no raw provider/reasoning/credential persistence = true
```

Recommended decision:

```text
START_CONNECTION_PACK_1_CONNECTION_SURFACE_AUDIT_V1
```

## Confirmation

```text
one CLI execution only = true
retry = false
source runtime/code changes before or during run = false
push = false
Pack 4C/connections/write/shell/browser/network work = not started
credentials process-scoped for execution and removed after run = true
```
