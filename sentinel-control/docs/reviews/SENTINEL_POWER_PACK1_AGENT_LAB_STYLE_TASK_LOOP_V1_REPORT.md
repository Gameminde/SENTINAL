# SENTINEL_POWER_PACK1_AGENT_LAB_STYLE_TASK_LOOP_V1_REPORT

Status: locally implemented.

Provider calls: 0.
Live external credential use: 0.
Push: not performed.
Browser/shell/workspace-write power: not added.

## Accepted Input State

Agent-Lab power import audit:

```text
SENTINEL_AGENT_LAB_POWER_IMPORT_AUDIT_V1 = ACCEPTED
AGENT_LAB_FOUND = true
recommended_next_pack = POWER_PACK_1_AGENT_LAB_STYLE_TASK_LOOP_V1
audit_commit = d64bed4 docs: audit agent-lab power import path
```

Pack 5 accepted state:

```text
CONNECTION_PACK_5_FIRST_LIVE_BOUNDED_CHANNEL_ACTION_V1 = LOCALLY_COMMITTED
commit = 34d0bde63b0ae1bb2e3b5cb33d4e33fba53aa00a
power = mission-level grant -> model/fake send_message -> local/fake channel transport -> receipt -> FinalGate -> replay no-resend
```

Doctrine applied:

```text
MAX POWER
MINIMUM USER FRICTION
MODEL LEADS
SENTINEL EXECUTES
RECEIPTS IN BACKGROUND
HARD STOP ONLY ON REAL DAMAGE
```

## Generic Loop Architecture

Pack 1 adds a generic, capability-agnostic model-led task loop. It is not a
read-only-specific loop and not a channel-specific loop.

Runtime shape:

```text
mission-level grant
-> model/fake decision client emits ActionEnvelope
-> LoopGuard checks budget/repetition/deadline
-> ActionKernel dispatches to a capability executor
-> existing capability runtime executes material action
-> existing capability runtime persists evidence/receipts/FinalGate
-> DecisionContextCompiler builds safe context from prior results
-> next decision receives bounded observation context
-> loop stops on finish, budget, kill, revocation, or guard block
-> replay reconstructs from artifacts without re-execution
```

Initial capabilities proven:

```text
read_only_research
bounded_channel local/fake send
```

No browser, shell, workspace write, desktop, network expansion, provider-native
tools, or fallback/AUTO behavior was added.

## Files Added

```text
sentinel/operator/action_kernel.py
sentinel/operator/decision_context.py
sentinel/operator/loop_guard.py
sentinel/operator/model_led_task_loop.py
tests/operator/test_power_pack1_model_led_task_loop.py
docs/reviews/SENTINEL_POWER_PACK1_AGENT_LAB_STYLE_TASK_LOOP_V1_REPORT.md
```

## Action Envelope Schema

The new `ActionEnvelope` is the model-to-runtime action contract:

```text
ActionEnvelope
  action_id
  capability_id
  operation
  target_ref
  params
  idempotency_key
  authority_ref
  decision_ref
  expected_receipt_type
```

It remains data, not authority:

```text
data_not_authority = true
authority_effect = none
can_grant_authority = false
can_execute = false
```

It rejects raw provider material, raw prompt/response/reasoning fields,
credential-like strings, fallback/AUTO markers, and provider-native tool
enablement markers before execution.

## Action Kernel Behavior

`ActionKernel` maps `capability_id` to an injected executor.

For Pack 1, tests bind:

```text
read_only_research -> ReadOnlyProductionSpineSession through first-receipt mode
bounded_channel -> ModelLedLiveChannelActionRuntime over ChannelConnectorRuntime
sentinel_loop.finish -> local non-material loop finish result
```

The kernel does not create authority, load credentials, call a provider, call
network, or register RuntimeHost adapters.

## Decision Context Behavior

`DecisionContextCompiler` emits safe decision context:

```text
mission objective
available actions
authority summary
previous receipt refs
bounded observation summaries
last action status
budget remaining
channel grant summary
read-only workspace summary
```

It does not include:

```text
raw provider output
raw reasoning
credentials
Authorization
unbounded file dumps
raw channel secrets
```

Focused proof:

```text
model/fake decision contexts after the first action contained last_action_status = completed
previous observations were visible before later actions
```

## Loop Guard Behavior

`LoopGuard` provides low-friction autonomy controls:

```text
max_model_calls
max_material_actions
max_same_action_hash
max_repeated_target
max_no_progress_turns
deadline_seconds
kill/revocation checks through ModelLedTaskLoop
```

It blocks repeated/no-progress behavior and material budget exhaustion without
per-action human approval.

## Cross-Capability Proof Path

The primary fake-provider test proves:

```text
read_only.list_directory "."
-> channel.send_message to granted local/fake channel
-> read_only.search_text "TODO"
-> finish
```

Observed proof:

```text
multiple actions across capabilities = yes
read-only runtime invoked = yes
channel runtime invoked = yes
channel transport sends = 1
model/fake decision calls = 4
material actions = 3
mission terminal status = completed
loop final certificate = accepted
```

## Channel Send No-Approval Proof

Pack 1 reuses Pack 5 channel runtime.

The channel send path uses:

```text
ModelLedLiveChannelActionRuntime
ChannelConnectorRuntime
ChannelAdapterConfig.approval_policy.approval_required_for_send = false
mission-level destination grant
```

Proof:

```text
per-message approval loop = absent
transport send = executed once
channel adapter receipt = persisted
channel FinalGate = persisted
replay no-resend = verified
```

Out-of-scope channel destination still blocks before transport.

## Replay No-Reexecute / No-Resend Proof

`ModelLedTaskLoopReplay.from_store(...)` reconstructs replay from mission
artifacts and events only.

Focused assertions prove:

```text
reexecuted_actions = false
model_calls_delta = 0
read_only_tool_calls_delta = 0
channel_transport_sends_delta = 0
receipt_writes_delta = 0
evidence_writes_delta = 0
FinalGate/certificate writes delta = 0
workspace_mutations_delta = 0
event_count_stable = true
artifact_hashes_stable = true
```

## Unsafe Rejection Proof

Focused tests prove:

```text
out-of-scope channel recipient blocks before transport
revoked authority blocks before action
kill switch blocks before action
repeated action loop guard blocks
max material action budget completes cleanly
raw provider/reasoning/credential/provider-native payload markers are rejected
```

## RuntimeHost Behavior

RuntimeHost behavior was not changed.

Pack 1 introduces no new `UnifiedExecutionAdapter` and no new RuntimeHost
adapter registration. The generic loop is an orchestrator over injected
executors and existing capability runtimes.

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
PASS: 7 passed

py -3.13 -m pytest tests/operator/test_connection_live_channel_action_pack5.py -q
PASS: 9 passed

py -3.13 -m pytest tests/operator/test_connection_inbound_readonly_pack4.py -q
PASS: 19 passed

py -3.13 -m pytest tests/operator/test_connection_identity_boundary_pack3.py -q
PASS: 18 passed

py -3.13 -m pytest tests/operator/test_connection_manifest_registry_pack2.py -q
PASS: 9 passed

py -3.13 -m pytest tests/test_real_model_read_only_operator_production_spine_v1.py -q
PASS: 48 passed

py -3.13 -m pytest tests/test_cli_runtime_host_product_wiring_pack1b.py -q
PASS: 28 passed

py -3.13 -m pytest tests/operator/test_product_nervous_system_pack3.py -q
PASS: 43 passed

py -3.13 -m compileall sentinel/operator/model_led_task_loop.py sentinel/operator/action_kernel.py sentinel/operator/decision_context.py sentinel/operator/loop_guard.py
PASS

git diff --check
PASS
```

Targeted scan:

```text
No persisted secret/provider material found.
Matches were limited to explicit forbidden marker constants and a negative test string.
No fallback/AUTO enablement found.
No provider-native tool enablement found.
```

## Power Gained

Before Pack 1:

```text
read-only autopilot = capability-specific
channel send = bounded but separate
model-led continuation across powers = absent
```

After Pack 1:

```text
generic model-led loop = present
cross-capability action envelope = present
read-only + channel send can run in one mission loop
safe observation context feeds the next model decision
loop guard replaces per-action approval spam
replay no-reexecute/no-resend is represented
```

## Remaining Next Power Packs

Recommended next pack:

```text
POWER_PACK_2_MODEL_LED_WORKSPACE_WRITE_AND_PATCH_V1
```

Why:

The generic loop now exists. The next highest visible user power is model-led
workspace mutation with hash-anchored patching, bounded tests, receipts, and
replay no-reapply.

Later packs:

```text
POWER_PACK_3_SHELL_AND_CODE_EXECUTION_SANDBOX_V1
POWER_PACK_4_BROWSER_COMPUTER_CONTROL_V1
POWER_PACK_5_REAL_CHANNEL_TRANSPORT_SEND_V1
```

## Commit

```text
commit = c3654b0fe0e4dc17a3790e0b7290da434466a58d
```

## Confirmation

```text
provider call = 0
source push = not performed
fallback/AUTO = not introduced
provider-native tools = not introduced
browser/shell/workspace-write = not added
new RuntimeHost adapter = not added
```


