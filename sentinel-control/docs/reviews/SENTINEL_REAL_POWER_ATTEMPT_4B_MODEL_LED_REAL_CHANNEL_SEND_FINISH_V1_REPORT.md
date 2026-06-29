# SENTINEL_REAL_POWER_ATTEMPT_4B_MODEL_LED_REAL_CHANNEL_SEND_FINISH_V1_REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_4B = SUCCESS
```

## Provider And Transport

```json
{
  "channel_transport_call_count": 1,
  "endpoint_hash": "96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497",
  "provider_decision_calls": 2,
  "provider_decision_calls_basis": "inferred from two persisted model_led_task_loop_action_completed events; post-run safe_result write crashed after mission completion",
  "provider_used": {
    "backend_id": "aliyun_openai_compatible_chat",
    "model_id": "deepseek-v4-pro",
    "provider_id": "aliyun_dashscope"
  },
  "transport_config_present": {
    "telegram_bot_token": true,
    "telegram_chat_id": true
  }
}
```

## Actions And Receipts

```json
{
  "actions_chosen": [
    "bounded_channel:send_message",
    "sentinel_loop:finish"
  ],
  "adapter_finalgate_passed": true,
  "delivery_ref_hashes": [
    "268e9be38d7afa5db0aa987438c21600069ad5e17dad816cc805ebf5bb890029"
  ],
  "finalgate_refs": [
    "channel_adapter_finalgate_efd0a312d4fb4a06ae636220d29ac8c4",
    "channel_finalgate_320a4823700a4076a3fce9ad3a3bb46d",
    "model_led_loop_finalgate_5927a55076054412b897f1e4f4b31e2f"
  ],
  "finish": true,
  "loop_finalgate_reason": "model_led_task_loop_finish",
  "loop_finalgate_status": "completed",
  "mission_status": "completed",
  "receipt_refs": [
    "channel_adapter_receipt_02b88b7865f04123bccbbe07886d3d7a",
    "channel_receipt_065bb603bf5642f2be73abbab4dfa4df"
  ]
}
```

## Event Sequence

```text
mission_created
mission_queued
channel_adapter_registered
model_led_task_loop_started
mission_running
channel_outbound_draft_created
channel_outbound_send_requested
channel_outbound_sent
model_led_task_loop_action_completed
model_led_task_loop_action_completed
mission_completed
model_led_task_loop_completed
```

## Replay No-Resend Proof

```json
{
  "artifact_hashes_stable": true,
  "channel_reexecuted_actions": false,
  "channel_send_delta": 0,
  "finalgate_writes_delta": 0,
  "model_calls_delta": 0,
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

## Post-Run Note

inline harness crashed while creating safe_result.json after mission completion; this recovered report is built from persisted safe mission artifacts without rerun

## Recommended Decision

```text
START_POWER_PACK_6_REAL_BROWSER_BOUNDED_WEB_CONTROL_V1
```

## Confirmation

```text
one provider mission run = yes
retry after provider call = no
fallback/AUTO = no
provider-native tools = no
raw provider output/reasoning persistence = no
token/chat_id persistence = no
source changes after provider run = no
push = no
```
