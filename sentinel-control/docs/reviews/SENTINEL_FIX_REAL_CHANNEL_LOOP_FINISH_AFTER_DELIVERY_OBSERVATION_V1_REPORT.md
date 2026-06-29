# SENTINEL_FIX_REAL_CHANNEL_LOOP_FINISH_AFTER_DELIVERY_OBSERVATION_V1_REPORT

## Attempt 4 Accepted Failure

`REAL_POWER_ATTEMPT_4_MODEL_LED_REAL_CHANNEL_SEND_V1` is accepted as
`VALID_FAILED_AFTER_REAL_TELEGRAM_SEND_NO_MODEL_FINISH`.

The run proved:

- real provider call = 1
- real Telegram transport call = 1
- real model chose `bounded_channel.send_message`
- Telegram `sendMessage` executed successfully
- channel adapter receipt and channel receipt were created
- replay no-resend proof passed
- token/chat id/API key/raw provider/raw reasoning persisted = no

The remaining blocker was loop completion, not Telegram transport.

## Root Cause

After the successful channel send, `DecisionContextCompiler` already considered
the channel objective satisfied. The loop did not open the finish-only material
budget turn for the real attempt because the loop only checked for the legacy
literal action name `finish` in `available_actions`.

The real channel attempt used the canonical action spelling:

```text
sentinel_loop.finish
```

So the material budget path closed with `model_led_task_loop_material_budget_reached`
instead of giving the model a delivery observation and one explicit finish turn.

## Context And Loop Changes

The fix keeps the Telegram transport unchanged and updates the generic
model-led task loop boundary:

- finish-only material-budget turns now accept canonical `sentinel_loop.finish`.
- legacy `finish` remains supported for existing tests/routes.
- after channel delivery, context uses
  `progress_state = channel_delivery_succeeded_needs_finish`.
- channel delivery context includes safe bounded metadata:
  `delivery_status`, `delivery_receipt_ref`, and `delivery_ref_hash`.
- if the model emits a non-finish action during the post-delivery finish-only
  turn, the loop blocks honestly with
  `MODEL_FINISH_REQUIRED_AFTER_CHANNEL_DELIVERY`.

No auto-finish was added. The model still has to emit `sentinel_loop.finish`.

## No Transport Broadening

This pack did not change Telegram send behavior, webhook behavior, endpoint
handling, credential handling, recipient policy, idempotency, or channel
authority checks.

## No Resend On Replay

The existing replay proof remains intact:

- replay does not call the channel transport
- replay does not resend
- replay does not write new receipts
- artifact hashes remain stable

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_pack5_real_channel_transport_send.py -q
result: passed, 11 tests

py -3.13 -m pytest tests/operator/test_power_pack4_browser_computer_control.py -q
result: passed, 6 tests

py -3.13 -m pytest tests/operator/test_power_pack3_code_execution_sandbox.py -q
result: passed, 19 tests

py -3.13 -m pytest tests/operator/test_power_pack2_workspace_write_patch.py -q
result: passed, 6 tests

py -3.13 -m pytest tests/operator/test_power_pack1_model_led_task_loop.py -q
result: passed, 7 tests

py -3.13 -m pytest tests/operator/test_connection_live_channel_action_pack5.py -q
result: passed, 9 tests

py -3.13 -m compileall sentinel/operator/channel_adapter.py sentinel/operator/channel_adapter_replay.py sentinel/operator/connection_live_channel_action_runtime.py sentinel/operator/decision_context.py sentinel/operator/action_kernel.py sentinel/operator/model_led_task_loop.py
result: passed

git diff --check
result: passed
```

## Targeted Scan

Changed-file scan found no API key, raw provider output, raw prompt, raw
response, raw reasoning, fallback/AUTO enablement, or provider-native tool
enablement. The only matches were existing test assertions proving
`Authorization`, `Bearer`, `raw_provider`, and `reasoning_content` are not
persisted.

## Git Status

Commit hash is recorded by the local commit containing this report.

## Confirmation

```text
provider call during fix = no
Telegram transport broadening = no
channel resend on replay = no
fallback/AUTO introduced = no
provider-native tools introduced = no
push = no
```
