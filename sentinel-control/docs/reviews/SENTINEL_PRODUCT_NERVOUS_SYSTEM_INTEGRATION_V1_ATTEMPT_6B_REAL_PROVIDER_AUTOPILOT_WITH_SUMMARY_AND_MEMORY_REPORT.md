# Sentinel Product Nervous System Integration V1
# Attempt 6B - Real Provider Autopilot With Summary And Memory

## Verdict

```text
ATTEMPT_6B_REAL_PROVIDER_AUTOPILOT_WITH_SUMMARY_AND_MEMORY = VALID_FAILED_AFTER_FIRST_RECEIPT_TIMEOUT
```

Pack 4B was exercised through the real product cockpit route, but the success threshold was not met.

The route produced one governed read-only material receipt, then blocked on the second provider decision call with:

```text
blocked_reason = TIMEOUT
FinalGate accepted = false
MissionKernel = blocked
```

No mission summary artifact or operator memory candidate artifact was created because the autopilot did not reach successful closeout.

## Source And Git

```text
source_commit = da219efd33f76d0e9e0cb4309677696d527fb773
branch = experimental/real-model-lab-freeze-v1
git status before run = clean, ahead 10
source changes before/during run = none
push = not performed
```

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
Pack 4B flags available = true
workspace HEAD = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace status before = clean
input JSON files = UTF-8 without BOM
strict JSON load = true
script nonempty turns = 2
approval turn = start
```

No raw endpoint URL, API key, Authorization header, raw prompt, raw response, raw reasoning, or provider wrapper payload was printed or persisted in this report.

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
  --run-root <RUN_ROOT>\runs `
  --model-contract <RUN_ROOT>\model-contract.json `
  --authority-scope <RUN_ROOT>\authority-scope.json `
  --workspace C:\Users\youcefcheriet\sentinel-workspaces\attempt5b-click `
  --script <RUN_ROOT>\mission-script.txt `
  --json
```

`--stop-after-first-material-receipt` was not used.

## Run IDs

```text
run_root = C:\Users\youcef cheriet\.sentinel-runs\product-vertical-slice\attempt6b-20260628-131433
mission = mission_ad9abf23f9af41fa9e8d34f5957ae5cc
routing decision persisted = yes
dispatch closeout = dispatch_cee65ce9e7154ed8968261fc53700100
receipt = readonly_receipt_b6714066152a4d14b6411f54f3f54bb6
evidence = readonly_evidence_f9926538881b424790e8f0746e696872
FinalGate = readonly_finalgate_594a9187516c476a85454744f6abe80f
```

## Counts

```text
provider decision calls = 2
final report calls = 0
material tool calls = 1
receipt count = 1
evidence count = 1
failed-attempt count = 1
mission summary artifacts = 0
operator memory candidate artifacts = 0
FinalGate certificates = 1
dispatch closeouts = 1
MissionKernel terminal transitions = 1
```

## Action Sequence

```text
1. list_directory
   target_kind = approved workspace root
   status = success
   receipt = readonly_receipt_b6714066152a4d14b6411f54f3f54bb6
   evidence = readonly_evidence_f9926538881b424790e8f0746e696872

2. second read-only decision call
   status = blocked
   reason = TIMEOUT
   no material action executed
   no fake receipt created
```

No file contents, raw provider output, raw visible content, raw prompt, or reasoning were returned in this report.

## FinalGate And Mission Status

```text
FinalGate status = blocked
FinalGate accepted = false
FinalGate reason = TIMEOUT
FinalGate receipt_refs = [readonly_receipt_b6714066152a4d14b6411f54f3f54bb6]
FinalGate artifact_refs = []

MissionKernel status = blocked
dispatch closeout status = blocked
dispatch closeout blocked_reason = TIMEOUT
```

This is an honest blocked closeout after one real receipt, not a false success.

## Summary And Memory Candidate Status

```text
mission summary artifact created = false
operator memory candidate artifact created = false
```

Reason:

```text
Pack 4B artifact generation occurs only after successful material-receipt autopilot closeout.
The run blocked on the second provider decision call before closeout.
```

Memory candidate requirement status:

```text
authority_granting = not applicable
can_execute = not applicable
can_grant_authority = not applicable
data_not_authority = not applicable
revocable = not applicable
receipt_refs present = not applicable
evidence_refs present = not applicable
summary_ref present = not applicable
workspace scoped = not applicable
mission scoped = not applicable
```

## Workspace Before And After

```text
workspace HEAD before = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace HEAD after = 8a1b1a33d739be05b7e91251e3c0dde77c5e152f
workspace status before = clean
workspace status after = clean
workspace fingerprint before = 04ceeb6dcb7b2e4393a4131ecaace2f6e7df8e51eb68a01c6b87745db0c98248
workspace fingerprint after = 04ceeb6dcb7b2e4393a4131ecaace2f6e7df8e51eb68a01c6b87745db0c98248
workspace unchanged = true
```

## Replay Purity Check

Replay was executed once after terminal closeout.

```text
replay_reexecuted = false
provider calls delta = 0
model calls delta = 0
tool calls delta = 0
receipt writes delta = 0
evidence writes delta = 0
summary writes delta = 0
operator memory candidate writes delta = 0
FinalGate writes delta = 0
dispatch closeout writes delta = 0
MissionRunStore events delta = 0
workspace mutations delta = 0
```

Material replay purity held for the artifacts that exist.

## Safety Scan

Run artifact scans outside cloned repository content returned:

```text
API key / Authorization / Bearer token = not found
raw_prompt / raw_response / raw_reasoning / reasoning_content = not found
provider wrapper payload markers = not found
fallback/AUTO enablement = not found
provider-native tool enablement = not found
```

## Strategic Interpretation

Attempt 6B confirms:

```text
real product route still reaches Aliyun / DeepSeek
Pack 4B CLI flags are active
first material action still executes under model-led autopilot
receipt/evidence/FinalGate/replay remain honest
workspace stays unchanged
```

Attempt 6B does not prove Pack 4B real-provider summary/memory closeout because:

```text
provider decision call 2 timed out
material receipts = 1, below threshold
summary artifacts = 0
operator memory candidate artifacts = 0
MissionKernel = blocked
```

## Recommended Decision

```text
TUNE_READ_ONLY_AUTOPILOT_PROVIDER_DECISION_TIMEOUT_V1
```

This should be a narrow timeout/budget tuning step for the read-only decision lane, not a schema, Gate, endpoint, credential, summary, memory, or provider-switch pack.

## Confirmation

```text
one CLI execution only = true
retry = false
source changes before/during run = false
provider-native tools = false
fallback/AUTO = false
push = false
Pack 4C / connections / write / shell / browser / network work = not started
```
