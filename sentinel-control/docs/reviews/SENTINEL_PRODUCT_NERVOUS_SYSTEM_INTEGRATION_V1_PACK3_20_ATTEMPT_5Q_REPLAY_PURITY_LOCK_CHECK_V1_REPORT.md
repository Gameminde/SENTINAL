# SENTINEL_PRODUCT_NERVOUS_SYSTEM_INTEGRATION_V1_PACK3_20_ATTEMPT_5Q_REPLAY_PURITY_LOCK_CHECK_V1_REPORT

## Verdict

```text
PACK_3_20_ATTEMPT_5Q_REPLAY_PURITY_LOCK_CHECK_V1 = VERIFIED
material replay purity = VERIFIED
recommended_decision = START_PACK_4_MODEL_LED_POWER_RUNTIME
```

This was an audit-only lock check of the successful Attempt 5Q product receipt run.

No provider call was made. No runtime source behavior was changed. Pack 4 was not started. No push was performed.

## 5Q Canonical Proof Summary

```text
attempt = ATTEMPT_5Q
verdict = PRODUCT_FIRST_RECEIPT_ACHIEVED
route = product cockpit
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
endpoint = workspace-specific .maas.aliyuncs.com compatible-mode/v1
mission_status = completed
dispatch_closeout = completed
receipt_count = 1
receipt_action = list_directory
receipt_status = success
evidence_count = 1
FinalGate = accepted
FinalGate reason = first_material_receipt_run_mode
workspace_git_clean = true
repo_git_clean_before_report = true
```

Key refs:

```text
mission = mission_7648b6f2d060420caeb361ec258e7a22
request = mission_exec_req_b7c963f63c654d81af8defbf624b833e
decision = mission_exec_decision_6d1c3af9bc014346bc4c95c15c80c7d6
dispatch = dispatch_5529133ce03c4f28a2ea061d66fac933
receipt = readonly_receipt_ab84ac1c46ad40c7a99d9d61b68cbbb1
FinalGate = readonly_finalgate_f7d347168dd34defa93ef5b77a746317
evidence = readonly_evidence_ca12aeef4d67498aaad4276cd0b55050
```

## Artifact Paths Inspected

```text
run_root =
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5q-20260628-111037

mission_dir =
C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt5q-20260628-111037\runs\mission_7648b6f2d060420caeb361ec258e7a22

record =
...\record.json

events =
...\events.jsonl

request =
...\execution_requests\mission_exec_req_b7c963f63c654d81af8defbf624b833e.json

decision =
...\execution_decisions\mission_exec_decision_6d1c3af9bc014346bc4c95c15c80c7d6.json

dispatch closeout =
...\dispatch_closeout\dispatch_5529133ce03c4f28a2ea061d66fac933.json

receipt =
...\read_only_spine\receipts\readonly_receipt_ab84ac1c46ad40c7a99d9d61b68cbbb1.json

evidence =
...\read_only_spine\evidence\readonly_evidence_ca12aeef4d67498aaad4276cd0b55050.json

FinalGate =
...\read_only_spine\finalgate\readonly_finalgate_f7d347168dd34defa93ef5b77a746317.json
```

## Replay Method Used

Two existing replay surfaces were used with telemetry disabled for the replay construction:

```text
MissionReplayBuilder(kernel.store).build(mission_id)
ReadOnlyProductionSpineSession(...).build_replay()
```

The replay was constructed from persisted mission events and read-only artifacts only.

The replay did not call the provider, did not call the model decision lane, did not execute a tool, did not write a new receipt, did not write a new FinalGate, and did not transition MissionKernel state.

## Before / After Counts

```text
mission_events:        22 -> 22
telemetry_events:      25 -> 25
telemetry_metrics:      5 -> 5
receipts:              1 -> 1
evidence:              1 -> 1
FinalGate:             1 -> 1
dispatch_closeout:     1 -> 1
failed_attempts:       0 -> 0
emergency_terminal:    0 -> 0
execution_decisions:   1 -> 1
execution_requests:    1 -> 1
```

Replay deltas:

```text
provider calls delta = 0
read-only model calls delta = 0
tool calls delta = 0
receipt writes delta = 0
evidence writes delta = 0
FinalGate writes delta = 0
dispatch closeout writes delta = 0
MissionRunStore events delta = 0
telemetry events delta = 0
telemetry metrics delta = 0
workspace mutations delta = 0
```

Existing replay view facts:

```text
product_replay_tampered = false
product_replay_reexecuted_actions = false
read_only_replay_reexecuted = false
read_only_model_calls_before_after = 0 -> 0
read_only_tool_calls_before_after = 0 -> 0
read_only_status_before_after = completed -> completed
read_only_event_count_before_after = 22 -> 22
```

## Hash Stability

Receipt:

```text
receipt_ref = readonly_receipt_ab84ac1c46ad40c7a99d9d61b68cbbb1
receipt_hash = 162c3936a6f7e61164b3e2096e7cdf656f4f934a97d513c8b5b378cb116d1cf8
receipt_file_hash_stable = true
receipt_payload_hash_stable = true
```

FinalGate:

```text
finalgate_ref = readonly_finalgate_f7d347168dd34defa93ef5b77a746317
certificate_hash = 27fbebb74630283756b42cfa1e6634a8179eaf749892b1714f636a0577e147d3
finalgate_file_hash_stable = true
certificate_hash_stable = true
accepted = true
reason = first_material_receipt_run_mode
```

Mission record, event log, evidence artifact, and dispatch closeout file hashes were also stable across replay.

## Workspace And Repo Status

Workspace:

```text
path = C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click
HEAD before = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
HEAD after = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
git status before = clean
git status after = clean
workspace unchanged = true
```

Sentinel repo:

```text
repo = C:\Users\youcefcheriet\sentinal
HEAD = 5052d4c6be3df97a0541774d3355f7c6a4da3d11
git status before report = clean
```

After this report is written, the only expected repository change is this report artifact.

## Safety Scan

Scanned Attempt 5Q artifacts outside cloned repository content for:

```text
API key
Authorization
raw_prompt
raw_response
raw_reasoning
reasoning_content
provider wrapper payload
provider_wrapper_payload
fallback/AUTO enablement
provider-native tool enablement
key-shaped sk-* material
```

Result:

```text
API key persisted = false
Authorization persisted = false
raw_prompt persisted = false
raw_response persisted = false
raw_reasoning persisted = false
reasoning_content persisted = false
provider wrapper payload persisted = false
provider-native tool enablement = false
fallback/AUTO enablement = false
```

Benign negative policy strings found in `model-contract.json`:

```text
no provider-native tools
no fallback/AUTO
no_fallback
no_provider_native_tools
```

These are negative constraints, not fallback or provider-native tool enablement.

## Required Check Results

```text
1. replay does not re-execute provider call = PASS
2. replay does not re-execute tool action = PASS
3. receipt count before replay == after replay = PASS
4. evidence count before replay == after replay = PASS
5. FinalGate count before replay == after replay = PASS
6. dispatch closeout count before replay == after replay = PASS
7. mission terminal status remains completed = PASS
8. receipt hash remains stable = PASS
9. FinalGate certificate hash remains stable = PASS
10. workspace git HEAD unchanged = PASS
11. workspace git status clean = PASS
12. repo git status clean except allowed report artifact = PASS
13. no raw provider response/prompt/reasoning persisted = PASS
14. no credential/Authorization persisted = PASS
15. no provider-native tool use = PASS
16. no fallback/AUTO = PASS
```

## Conclusion

```text
material replay purity = VERIFIED
artifact immutability = VERIFIED
first real product receipt = LOCKED
recommended_decision = START_PACK_4_MODEL_LED_POWER_RUNTIME
```

Pack 3.20 confirms that Attempt 5Q is not just a successful one-shot receipt. Its product proof is replay-stable, artifact-stable, workspace-safe, and free of provider/credential material persistence.

Pack 4 was not implemented in this check.
