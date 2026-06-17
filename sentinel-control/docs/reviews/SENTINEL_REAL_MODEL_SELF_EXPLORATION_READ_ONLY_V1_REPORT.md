# Sentinel Real Model Self-Exploration Read-Only V1 Report

Status: SELF_EXPLORATION_FAILED

Date: 2026-06-16

## Verdict

The first controlled read-only self-exploration experiment was executed once and failed before producing a usable Stage A visible architecture report.

```text
verdict = SELF_EXPLORATION_FAILED
failure_category = STAGE_A_VISIBLE_REPORT_EMPTY
```

This does not evaluate DeepSeek's repository-understanding ability yet. It reveals a harness failure mode: the real provider call returned no valid visible Stage A report, and the runner initially raised before writing a durable failed-run record. The runner was corrected locally after the run so this failure mode is retained in future attempts. The provider run was not repeated.

## Frozen Policy

```text
experiment = REAL_MODEL_SENTINEL_SELF_EXPLORATION_AND_SYSTEM_AUDIT_READ_ONLY_V1
policy_hash = 64c959b0be2ae8ae92a95384ce212fea7dc72c0c56e9eaf4c5f509bf1bb441e5
max_model_calls = 2
max_files_read = 80
max_bytes_read = 220000
max_output_tokens_per_call = 4000
max_total_tokens = 80000
max_duration_seconds = 420
max_report_chars = 80000
provider_native_tools = false
fallback_auto = false
```

## Snapshot Identity

```text
HEAD = 781e28b945a52fd07e3d638335b496f9c1ee6980
origin/main = 781e28b945a52fd07e3d638335b496f9c1ee6980
dirty_worktree_fingerprint = c795b7a84b28259046552a49c76dce5287007faa9c7865d88d2b6fe6100c12b9
inventory_hash = 3eff7eae47cddd3dec986eb65eb9eaf1e2b202f93b3cdfc47cca7f23814ccdc6
accessible_file_inventory_hash = 5db8ec705ca9eb24da6e9f3719bb50e1d99ce781ef355ac08e3826452a2192d0
excluded_file_inventory_hash = 5645b5e076698931e8108475ec584292590699ddd8659083710dd0d33be9c4af
inventory_count = 51914
accessible_file_count = 732
stage_a_file_count = 726
stage_b_file_count = 732
```

The working tree was intentionally dirty before the experiment. The model was not given write access.

## Provider / Model

```text
provider_id = alibaba_model_studio_certification
backend_id = alibaba_model_studio_openai_compatible_chat
model_id = deepseek-v4-pro
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
credential = process-scoped environment variable only
```

No credential, authorization header, raw provider response, raw reasoning, or raw prompt is included in this report.

## Run Status

```text
output_root = sentinel-control/services/sentinel-core/w/self_exploration_read_only/20260616-174300
result = failed
stage_reached = Stage A provider call
stage_a_visible_report = empty / invalid
stage_b = not reached
architecture_coverage = not evaluated
valid_findings = 0
false_positives = 0
unsupported_claims = not evaluated
```

The output root contains a safe failed-run record:

```text
sentinel-control/services/sentinel-core/w/self_exploration_read_only/20260616-174300/self_exploration_report.json
```

## Harness Correction Made After Run

The runner now has a tested behavior for empty Stage A visible reports:

```text
provider response / invalid visible report
-> no retry
-> no Stage B
-> write failed-run record
-> classify STAGE_A_VISIBLE_REPORT_EMPTY
```

This is a generic harness correction. It does not add task-specific hints and does not weaken read-only enforcement.

## Local Tests

```text
py -3.13 -m pytest -q tests/test_self_exploration_read_only_v1.py
7 passed

py -3.13 -m pytest -q tests/test_openai_compatible_provider_base.py tests/test_mutation_artifact_transport_v2_micro_certification.py
23 passed

py -3.13 -m compileall -q sentinel
passed

git diff --check
only CRLF working-copy warnings on already modified tracked files
```

Local verification covered:

```text
write operations blocked
mutation lane inaccessible
commit/push blocked
non-provider network blocked
credential-like paths blocked
Stage A hides truth docs and previous audits
hidden rubric inaccessible to prompts
raw reasoning not persisted
bounded report safety scan
failed Stage A visible report persistence
```

## Secret / Persistence Scan

No provider key, authorization header, raw prompt, raw provider response, or raw reasoning was found in:

```text
sentinel-control/docs/reviews/SENTINEL_REAL_MODEL_SELF_EXPLORATION_READ_ONLY_V1_REPORT.md
sentinel-control/services/sentinel-core/w/self_exploration_read_only/20260616-174300/self_exploration_report.json
```

## Honest Interpretation

This experiment did not yet answer the core research question:

```text
Can a real model use Sentinel to understand Sentinel and produce useful evidence-backed findings?
```

The first real run instead found a harness/provider-output failure at the report-production boundary.

Possible causes:

```text
provider returned invalid/empty visible content
provider/channel behavior similar to the mutation-lane reasoning/content split
prompt framing failed to elicit a visible report
OpenAI-compatible adapter returned INVALID_RESPONSE_SCHEMA
```

Because the original failed call was not durably recorded with full safe call metadata, these remain hypotheses.

## Recommendation

```text
IMPROVE_READ_ONLY_EXPLORATION_HARNESS
```

Before another provider run:

```text
1. Record provider error class and safe response metadata for empty visible reports.
2. Add an explicit small smoke call for read-only audit visible-content behavior.
3. Keep Stage A / Stage B separation and read-only constraints unchanged.
4. Re-freeze policy and run exactly one fresh read-only exploration attempt.
```

Do not move to sandboxed finding reproduction yet. No model finding exists to reproduce.

## Confirmations

```text
read-only enforcement was runtime-level
no files were modified by the model
no patch generated or applied
previous audit conclusions hidden during independent discovery
hidden rubric inaccessible
no raw reasoning persisted
no fallback/AUTO
no provider-native tools
no score change
no commit/push
Browser, Wave 2, UX, and Security Testing not started
```
