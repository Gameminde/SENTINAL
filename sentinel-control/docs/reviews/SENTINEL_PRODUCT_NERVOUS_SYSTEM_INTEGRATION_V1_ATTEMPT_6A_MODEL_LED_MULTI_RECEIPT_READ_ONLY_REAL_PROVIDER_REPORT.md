# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_ATTEMPT_6A_MODEL_LED_MULTI_RECEIPT_READ_ONLY_REAL_PROVIDER_REPORT

## Verdict

```text
ATTEMPT_6A_MODEL_LED_MULTI_RECEIPT_READ_ONLY_REAL_PROVIDER = SUCCESS
success_threshold = MET
recommended_decision = START_PACK_4B_READ_ONLY_MISSION_SUMMARY_AND_OPERATOR_MEMORY_V1
```

Attempt 6A proved Pack 4A through the real product cockpit route with the real Aliyun / DeepSeek V4 Pro provider lane.

## Source And Git State

```text
source_commit = 396191ba1b20f16ffa32d8060a35c2e33705e08e
branch = experimental/real-model-lab-freeze-v1
git_status_before_run = clean
runtime_source_changes = none
push = not performed
```

After this report is written, the only expected repository change is this report artifact.

## Preflight Safe Facts

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_source = process_env:SENTINEL_ALIYUN_DASHSCOPE_BASE_URL
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
credential_present = true
provider-native tools disabled = true
fallback/AUTO disabled = true
Pack 4A flags available = true
input JSON UTF-8 without BOM = true
script nonempty turns = 2
approval turn = start
```

Workspace:

```text
workspace = C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
workspace_HEAD_before = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace_git_status_before = clean
workspace_fingerprint_before = 04ceeb6dcb7b2e4393a4131ecaace2f6e7df8e51eb68a01c6b87745db0c98248
workspace_inside_authority_scope = true
workspace_outside_run_root = true
```

Run root:

```text
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt6a-20260628-121442
```

## Command Shape

```powershell
py -3.13 -m sentinel.cli cockpit `
  --explicit-mission-bootstrap `
  --model-led-read-only-autopilot `
  --low-friction-read-only-power-mode `
  --max-material-receipts 3 `
  --max-provider-decision-calls 3 `
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

Execution:

```text
cli_exit_code = 0
one_CLI_execution = true
retry = false
```

## Product Route IDs

```text
mission = mission_f3582e10f05a48a78104fdb575c1a13f
request = mission_exec_req_6db3db5d8f5447a3ad4e52b2804141b5
decision = mission_exec_decision_eb725ea493524a2391d9eb93afc15250
dispatch = dispatch_9210d02eb182469494bc83839ad70c25
FinalGate = readonly_finalgate_dc5ab12459564dfc953c3f1ed01730ba
```

Execution options persisted on the immutable request:

```json
{
  "low_friction_read_only_power_mode": true,
  "max_material_receipts": 3,
  "max_provider_decision_calls": 3,
  "model_led_read_only_autopilot": true
}
```

## Provider And Tool Counts

```text
provider decision calls = 3
final report calls = 0
material tool calls = 3
decision checkpoints = 3
receipt count = 3
evidence count = 3
failed-attempt count = 0
dispatch closeout count = 1
FinalGate count = 1
```

Provider-call evidence source:

```text
telemetry token_usage metrics = 3
read_only_spine decision checkpoints = 3
model_call_index values = 1, 2, 3
```

## Action Sequence

Chronological material action sequence:

```text
1. list_directory target=.
2. read_file_segment target=pyproject.toml range=1..100
3. list_directory target=src
```

Safe evidence summaries:

```text
readonly_evidence_aa80723211f54daaa8fd26135b4bace5
  action = list_directory
  path = .
  entries_count = 16

readonly_evidence_cb5ecfe351db44b58cd3a334b754d2fa
  action = read_file_segment
  path = pyproject.toml
  range = start_line 1, line_count 100
  content_hash = 7bf2218d71ba6bd77787e42263fd88f47137c84998cbf77338722c8ad3838c32

readonly_evidence_83cae571a20149bd85def8bff92c927c
  action = list_directory
  path = src
  entries_count = 1
```

Gate actions:

```text
list_directory
read_file_segment
list_directory
```

All three passed the low-friction read-only Gate boundary before receipt creation.

## Receipts

Receipt refs:

```text
readonly_receipt_8bc8e23c08b14fa185e16758d0a305d5
readonly_receipt_001fe95bf15547a29aa16291a1340d86
readonly_receipt_f46e04df0b9e4fc690e2388be012cb3b
```

Receipt statuses:

```text
success
success
success
```

Receipt hashes:

```text
3b14728cadad59bdb7eecada518e7672ddc686e5fdba209857a88ec9a172e05b
7dfee0de1b794d74ae05e8ad1a72121a13940f5f54af3aeb2dd79513f31f1652
bc38a760b1f457bb76367ff30ff89275a53748142a5cabc01b3fe7f8ab56271a
```

## FinalGate And Mission Status

```text
FinalGate accepted = true
FinalGate status = accepted
FinalGate reason = model_led_read_only_autopilot_material_receipt_budget_reached
FinalGate certificate_hash = d7624e61428e58c13a65d0b7e1be9d491388f99c1bc2101666e227cf1ab5e0b1
dispatch closeout status = completed
dispatch closeout finalgate_status = accepted
mission status = completed
```

Final event sequence ended with:

```text
read_only_spine_finalgate_certified
read_only_spine_model_led_autopilot_terminal
agentruntime_execution_event_observed
agentruntime_result
mission_dispatch_closeout_persisted
mission_completed
```

## Workspace Before / After

```text
workspace_HEAD_before = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace_HEAD_after = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace_status_before = clean
workspace_status_after = clean
workspace_fingerprint_before = 04ceeb6dcb7b2e4393a4131ecaace2f6e7df8e51eb68a01c6b87745db0c98248
workspace_fingerprint_after = 04ceeb6dcb7b2e4393a4131ecaace2f6e7df8e51eb68a01c6b87745db0c98248
workspace unchanged = true
```

## Replay Purity Check

Existing replay surfaces used:

```text
MissionReplayBuilder(...).build(mission_id)
ReadOnlyProductionSpineSession(...).build_replay()
```

Replay deltas:

```text
mission_events:        28 -> 28
telemetry_events:      33 -> 33
telemetry_metrics:      9 -> 9
decision_checkpoints:   3 -> 3
receipts:               3 -> 3
evidence:               3 -> 3
FinalGate:              1 -> 1
dispatch_closeout:      1 -> 1
failed_attempts:        0 -> 0
```

Replay execution truth:

```text
product_replay_tampered = false
product_replay_reexecuted_actions = false
read_only_replay_reexecuted = false
read_only_model_calls_before_after = 0 -> 0
read_only_tool_calls_before_after = 0 -> 0
read_only_event_count_before_after = 28 -> 28
read_only_receipt_writes_before_after = 3 -> 3
read_only_finalgate_writes_before_after = 1 -> 1
mission_status_before_after = completed -> completed
artifact_hashes_stable = true
material replay purity held = true
```

## Safety Scan

Run artifacts were scanned for:

```text
API key
Authorization
raw_prompt
raw_response
raw_reasoning
reasoning_content
provider wrapper payload
provider_wrapper_payload
real fallback/AUTO enablement
real provider-native tool enablement
```

Result:

```text
unsafe matches = 0
API key persisted = false
Authorization persisted = false
raw provider response persisted = false
raw provider prompt persisted = false
raw reasoning persisted = false
provider wrapper payload persisted = false
real fallback/AUTO enablement = false
real provider-native tool enablement = false
```

Only benign negative/forbidden policy strings were found, such as no-fallback and provider-native-tool-forbidden style policy text.

## Success Threshold

```text
provider decision calls >= 2 = PASS (3)
material receipts >= 2 = PASS (3)
FinalGate accepted = PASS
mission completed = PASS
workspace unchanged = PASS
material replay purity held = PASS
no fallback/AUTO = PASS
no provider-native tools = PASS
no raw provider/reasoning/credential persistence = PASS
```

## Recommendation

```text
recommended_decision = START_PACK_4B_READ_ONLY_MISSION_SUMMARY_AND_OPERATOR_MEMORY_V1
```

Attempt 6A proves that Sentinel can now run a real provider in model-led multi-step read-only autopilot mode, execute multiple governed in-scope observations, receipt each one, accept FinalGate, complete the mission, and replay without material side effects.

## Confirmation

```text
one CLI execution = true
retry = false
source runtime changes = none
push = not performed
Pack 4B/write/shell/browser/network work = not started
credentials = process-scoped and removed after run
```
