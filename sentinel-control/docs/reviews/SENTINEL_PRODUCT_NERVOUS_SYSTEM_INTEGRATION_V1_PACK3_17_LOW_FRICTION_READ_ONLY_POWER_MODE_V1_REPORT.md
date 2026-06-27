# SENTINEL PRODUCT NERVOUS SYSTEM INTEGRATION V1
# PACK 3.17 LOW-FRICTION READ-ONLY POWER MODE V1 REPORT

## Verdict

```text
PACK_3_17_LOW_FRICTION_READ_ONLY_POWER_MODE_V1 = LOCALLY IMPLEMENTED CANDIDATE
provider calls = 0
Pack 4 started = no
push performed = no
```

## Why Safety Was Too Friction-Heavy

The Pack 3 route had become structurally safe but product-fragile: too much of the runtime treated harmless in-workspace read-only activity as if it were a high-risk escalation. That makes real model-led exploration stall before useful work exists.

The corrected product principle is:

```text
upfront user-approved workspace + read-only mission authority
-> model chooses in-scope read-only actions
-> Sentinel executes and receipts material observations
-> Sentinel blocks only authority-boundary violations
```

This pack does not remove Gate, FinalGate, receipts, replay, kill/revocation, or proof verification. It adds an explicit low-friction mode for the already-approved first-receipt read-only product path.

## New Power Policy

The new request-bound execution option is:

```text
execution_options.low_friction_read_only_power_mode = true
```

It is accepted only with:

```text
capability_id = read_only_research
operation = inspect_repository
execution_options.stop_after_first_material_receipt = true
```

The CLI exposes it as:

```text
--low-friction-read-only-power-mode
```

and rejects it unless it is paired with:

```text
--explicit-mission-bootstrap
--stop-after-first-material-receipt
```

## What Becomes Low-Friction

Inside the approved workspace and authority envelope, these actions can proceed without another human approval step:

```text
list_directory
search_text
read_file_segment
finish_exploration
```

The spine now records a structure-only event after Gate passes and before the receipt:

```text
event_type = read_only_low_friction_gate_passed
human_escalation_required = false
authority_boundary = approved_workspace_read_only
gate_sequence_passed = true
receipt_required = true
```

This event is proof of reduced friction, not proof of execution success. The receipt remains the proof of material action.

## What Remains Hard-Blocked

The mode does not grant additional authority. The following remain blocked:

```text
path traversal outside workspace
absolute outside paths
write_file
delete_file
shell
network
browser_click
send_email
payment
credential_access
model-supplied workspace/model_contract/authority/budget/can_execute
raw provider response/prompt/reasoning persistence
fake receipts
workspace mutation
```

## Receipt Proof

Focused tests prove that, with the explicit option enabled, each in-scope material read-only action can produce a receipt without report-lane or human re-approval:

```text
list_directory -> receipt
search_text -> receipt
read_file_segment -> receipt
decision_client.call_count = 1
report_client.call_count = 0
read_only_low_friction_gate_passed precedes read_only_spine_action_receipted
```

## Unsafe Rejection Proof

Focused tests prove the mode does not weaken authority boundaries:

```text
../outside path -> BLOCKED, no receipt
absolute outside path -> BLOCKED, no receipt
write/delete/shell/credential/network/browser/email/payment tools -> BLOCKED, no receipt
```

Existing Pack 3.7/3.10/3.13/3.16 decision-boundary tests continue to reject unsafe model-owned control fields and raw reasoning/provider material.

## Replay Proof

The unsafe-tool regression slice verifies that blocked low-friction attempts preserve replay material purity:

```text
reexecuted = false
receipt writes before replay == after replay
FinalGate writes before replay == after replay
```

The existing Pack 3 replay and first-receipt tests remain in the focused validation set.

## Remaining Real-Provider Risk

Pack 3.17 does not prove a new real-provider receipt. It removes one product-friction layer once a canonical read-only decision has been extracted and validated.

The next real-provider attempt should still target:

```text
real provider
-> extracted canonical ReadOnlyDecision
-> Gate accepted
-> material read-only action
-> receipt
-> workspace unchanged
-> replay material purity held
```

If that first real receipt appears, Pack 4 can be discussed. If it blocks before receipt, the blocker should be classified as model-interface, Gate/scope, or runtime execution based on retained safe diagnostics.

## Validation

Initial RED evidence:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py -k "pack3_17" sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py -k "low_friction" -q
result = failed before implementation
reason = unsupported execution option and missing CLI flag
```

Post-implementation focused validation:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py -q
result = PASS, 99 passed
```

```text
py -3.13 -O -m pytest sentinel-control/services/sentinel-core/tests/operator/test_product_nervous_system_pack3.py -k "pack3_17 or pack3_15" sentinel-control/services/sentinel-core/tests/operator/test_read_only_research_decision_protocol_pack3_7.py -k "pack3_17 or pack3_16 or pack3_13" sentinel-control/services/sentinel-core/tests/test_cli_runtime_host_product_wiring_pack1b.py -k "low_friction or first_material_receipt" -q
result = PASS, 11 passed
note = pytest emitted the expected Python -O assertion-rewrite warning
```

```text
py -3.13 -m compileall -q <touched runtime modules>
result = PASS
```

```text
git diff --check
result = PASS
note = Git reported CRLF normalization warnings only
```

Targeted raw-provider/secret/fallback/provider-native scan:

```text
result = PASS with benign matches only
benign matches = diagnostic deny-list field names and tests that assert raw/reasoning fields are rejected
```
