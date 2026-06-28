# SENTINEL_POWER_PACK2_MODEL_LED_WORKSPACE_WRITE_AND_PATCH_V1_REPORT

## Verdict

```text
POWER_PACK_2_MODEL_LED_WORKSPACE_WRITE_AND_PATCH_V1 = LOCALLY_IMPLEMENTED
commit_hash = recorded in final Codex response after local commit
provider_call = 0
push = not performed
```

The report does not self-embed the final Git commit hash because changing this
file to include its own commit hash changes the commit hash. The authoritative
hash is returned after the local commit is created.

## Accepted Starting State

```text
POWER_PACK_1_AGENT_LAB_STYLE_TASK_LOOP_V1 = LOCALLY_COMMITTED
authoritative_commit = c3654b0fe0e4dc17a3790e0b7290da434466a58d
report_metadata_reconciliation_commit = e1ddce4 docs: reconcile power pack 1 commit metadata
```

Power Pack 1 already provided:

```text
generic model-led loop
ActionEnvelope
ActionKernel
DecisionContextCompiler
LoopGuard
read_only_research + bounded_channel execution in one mission loop
background receipts
replay no-reexecute/no-resend representation
```

Power Pack 2 builds on that loop. It does not create a separate isolated
patching lane.

## Power Gained

Power Pack 2 adds model-led local workspace mutation inside an already granted
workspace authority:

```text
read_only observation
-> workspace_patch.apply_patch
-> workspace_patch.run_bounded_check
-> read_only verification/search
-> finish
```

The model can now drive a patch step through the generic task loop, and Sentinel
executes the patch only when the target is inside the approved workspace and
the file still matches the expected base hash.

## Architecture

### New Modules

```text
sentinel/operator/workspace_patch_models.py
sentinel/operator/workspace_patch_runtime.py
sentinel/operator/workspace_patch_replay.py
```

### Updated Modules

```text
sentinel/operator/decision_context.py
sentinel/operator/model_led_task_loop.py
```

### Test Coverage

```text
tests/operator/test_power_pack2_workspace_write_patch.py
```

## Workspace Patch Semantics

`workspace_patch.apply_patch` accepts a single declared target path and an
expected base hash.

Required properties:

```text
target path is workspace-relative
target resolves inside approved workspace
target is not a symlink escape
target is not a sensitive config/credential file
expected_base_hash matches current file bytes
patch applies cleanly by exact text replacement
patch writes only the declared target path
receipt records before_hash and after_hash
```

Rejected cases:

```text
path traversal
absolute outside path
symlink escape
multiple declared targets
sensitive targets such as .env / model-contract.json / authority-scope.json
credential-like patch content
raw provider / raw prompt / raw response / raw reasoning markers
```

## Bounded Verification Semantics

`workspace_patch.run_bounded_check` uses a command id plus argument list. It
does not accept ambient shell strings.

Current allowed command ids:

```text
fake_pass
python_compileall
pytest_file
```

The runtime rejects:

```text
raw command strings
unknown command ids
shell metacharacters
network-looking args
credential-looking args
path args escaping the workspace
```

Power Pack 2 tests use a local fake check runner. No shell, provider, network,
browser, desktop, or external credential is used.

Verification receipts record:

```text
command id
args
exit status
duration
stdout/stderr hashes
bounded redacted excerpts
result hash
receipt hash
```

## Generic Loop Integration

The generic loop now supports a mixed sequence:

```text
read_only_research:read_file_segment
workspace_patch:apply_patch
workspace_patch:run_bounded_check
read_only_research:search_text
sentinel_loop:finish
```

`DecisionContextCompiler` now includes:

```text
workspace_patch_summary
workspace_verification_summary
```

These summaries are bounded and safe:

```text
operation
status
receipt count
evidence count
bounded observation summary
result hash
```

They do not include raw file contents, raw provider output, hidden reasoning, or
credential material.

`LoopGuard` did not need a special-case path. Patch and check actions count as
material actions through the existing `ActionResult.material_action` contract.

## Receipt And Certificate Schema

New data-only artifacts:

```text
WorkspacePatchProposal
WorkspacePatchEvidence
WorkspacePatchReceipt
WorkspacePatchVerificationReceipt
WorkspacePatchFinalCertificate
WorkspacePatchReplayView
```

All new models preserve:

```text
data_not_authority = true
authority_effect = none
can_grant_authority = false
can_execute = false
```

Receipt and certificate hashes are computed from safe persisted payloads and
verified in the Power Pack 2 focused tests.

## Replay Proof

`WorkspacePatchReplayView.from_store(...)` reconstructs from persisted artifacts
and workspace fingerprint only.

It reports:

```text
patch_applications_delta = 0
verification_runs_delta = 0
workspace_mutations_delta = 0
receipt_writes_delta = 0
evidence_writes_delta = 0
finalgate_writes_delta = 0
artifact_hashes_stable = true
workspace_hash_stable = true
```

Replay does not reapply patches and does not rerun bounded checks.

## Workspace Final Diff Proof

The focused loop test starts with:

```text
README.md contains "TODO: old marker"
```

The model-led sequence applies exactly one hash-anchored replacement:

```text
TODO: old marker
-> TODO: model-led patch landed
```

Then the fake bounded check runs once, read-only search verifies the marker, and
the loop finishes. The workspace change is limited to the declared file.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py -q
result: 6 passed

py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
result: 7 passed

py -3.13 -m pytest tests/operator/test_connection_live_channel_action_pack5.py -q
result: 9 passed

py -3.13 -m pytest tests/test_real_model_read_only_operator_production_spine_v1.py -q
result: 48 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -q
result: 28 passed

py -3.13 -m compileall sentinel/operator/workspace_patch_models.py sentinel/operator/workspace_patch_runtime.py sentinel/operator/workspace_patch_replay.py sentinel/operator/model_led_task_loop.py sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/loop_guard.py
result: passed

git diff --check
result: passed
```

Targeted secret/raw-provider/fallback/provider-native scan:

```text
result = passed with benign matches only
benign matches = forbidden-label constants inside action/runtime scanners
```

## Confirmation

```text
provider call = 0
live external credential use = 0
browser/desktop/payment expansion = not added
ambient shell = not added
network = not added
provider-native tools = not introduced
fallback/AUTO = not introduced
push = not performed
```

## Recommended Next Power Pack

```text
POWER_PACK_3_SHELL_AND_CODE_EXECUTION_SANDBOX_V1
```

Reason:

Workspace patching now exists inside the generic model-led loop. The next
highest-leverage power muscle is bounded shell/code execution in a sandbox,
with receipts and replay no-rerun, not ambient shell.
