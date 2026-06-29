# SENTINEL REAL POWER ATTEMPT 4 MODEL LED REAL CHANNEL SEND V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_4 = VALID_FAILED_AFTER_REAL_TELEGRAM_SEND_NO_MODEL_FINISH
```

This is a consumed one-shot real-provider attempt. It proved the real bounded
Telegram send path, but it did not meet the full success threshold because the
model did not emit an explicit `sentinel_loop.finish` after delivery.

## Source

```text
source_commit = 562b265d7469b66d7b9ec5762248f43d27dedfc0
run_root = C:\Users\youcef cheriet\.sentinel-runs\real-power-attempts\real-power-attempt4-20260629-121834
```

## Safe Preflight Facts

```json
{
  "aliyun_base_url_present": true,
  "cert_base_url_present": true,
  "endpoint_hash": "96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497",
  "provider_key_present": true,
  "telegram_bot_token_present": true,
  "telegram_chat_id_present": true
}
```

## Provider And Transport

```text
provider = aliyun_dashscope / aliyun_openai_compatible_chat / deepseek-v4-pro
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
provider_decision_calls = 1
channel_transport_call_count = 1
token/chat_id values persisted = no
```

## Actions Chosen By Real Model

```text
bounded_channel:send_message
```

## Event Sequence

```text
mission_created
-> mission_queued
-> channel_adapter_registered
-> model_led_task_loop_started
-> mission_running
-> channel_outbound_draft_created
-> channel_outbound_send_requested
-> channel_outbound_sent
-> model_led_task_loop_action_completed
-> mission_completed
-> model_led_task_loop_completed
```

## Receipts And Finish

```json
{
  "blocked_reason": null,
  "delivery_ref_hashes": [
    "95702399fe2af038f6fe0dcf6f354c6e76eaca8e84d821834f867c8ffd10d793"
  ],
  "finalgate_refs": [
    "channel_adapter_finalgate_d2e47915920b44f9aba868cf465c4393",
    "channel_finalgate_04d018e8f66e4a4283bac85247042c08"
  ],
  "finish": false,
  "loop_status": "completed",
  "mission_status": "completed",
  "receipt_refs": [
    "channel_adapter_receipt_fc946b9c77e94a3fb2fde1871c402c29",
    "channel_receipt_25286411eb2f42d7a6432a5d31e422ae"
  ]
}
```

The final model-led loop certificate was accepted with:

```text
reason = model_led_task_loop_material_budget_reached
```

That is honest completion with a real receipt, not model-finish completion.

## Replay No-Resend Proof

```json
{
  "artifact_hashes_stable": true,
  "channel_reexecuted_actions": false,
  "channel_send_delta": 0,
  "finalgate_writes_delta": 0,
  "receipt_writes_delta": 0
}
```

## Safety Scan

```json
{
  "hit_count": 0,
  "hits": []
}
```

## Recommended Decision

```text
FIX_REAL_CHANNEL_LOOP_FINISH_AFTER_DELIVERY_OBSERVATION_V1
```

The transport/send path itself is not the blocker. The remaining blocker is
that the real run used one provider decision to send successfully, then stopped
by material budget instead of giving the model a delivery observation and
requiring/receiving an explicit `sentinel_loop.finish`.

## Confirmation

```text
one provider mission run = yes if provider_decision_calls > 0 else not_started
retry after provider call = no
fallback/AUTO = no
provider-native tools = no
raw provider output/reasoning persistence = no
token/chat_id persistence = no
push = no
```
