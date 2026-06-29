# SENTINEL REAL POWER ATTEMPT 4 MODEL LED REAL CHANNEL SEND V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_4_MODEL_LED_REAL_CHANNEL_SEND_V1 = REAL_CHANNEL_TRANSPORT_CONFIG_MISSING
provider_calls = 0
channel_transport_calls = 0
```

This is a static preflight stop, not a consumed provider attempt.

## Source

```text
source_commit = 1e21683b96f1d559fb07e1196fb4fa84d64d27ad
pack_under_test = POWER_PACK_5_REAL_CHANNEL_TRANSPORT_SEND_V1
```

## Provider Preflight

Safe facts only:

```text
provider_id = aliyun_dashscope
backend_id = aliyun_openai_compatible_chat
model_id = deepseek-v4-pro
provider_api_key_present = true
SENTINEL_ALIYUN_DASHSCOPE_BASE_URL present = true
SENTINEL_CERT_MODEL_BASE_URL present = true
endpoint_hash = 96fd7aa96afa8bb6bae02001907b8b4f598bfe3ca55b04ced7961ebf42e95497
fallback/AUTO = disabled
provider-native tools = disabled
```

No endpoint values, credential values, Authorization headers, raw prompts, raw provider output, raw reasoning, or provider wrapper payloads are printed or persisted in this report.

## Channel Transport Preflight

Required config names:

```text
SENTINEL_CHANNEL_WEBHOOK_URL
SENTINEL_CHANNEL_WEBHOOK_TOKEN
```

Safe facts only:

```text
SENTINEL_CHANNEL_WEBHOOK_URL present = false
SENTINEL_CHANNEL_WEBHOOK_TOKEN present = false
```

`SENTINEL_CHANNEL_WEBHOOK_URL` is required for the current real channel transport builder.
`SENTINEL_CHANNEL_WEBHOOK_TOKEN` is optional.

## Stop Reason

```text
blocked_before_provider = true
blocked_before_channel_call = true
reason = REAL_CHANNEL_TRANSPORT_CONFIG_MISSING
```

The implementation now has a real webhook transport seam, but no mission-scoped test destination endpoint is configured in the current process.

## Attempt Rules Check

```text
one_provider_mission_run = not_started
retry_after_provider_call = no
fallback/AUTO = no
provider-native_tools = no
raw_provider_output_persisted = no
raw_reasoning_persisted = no
credential_persisted = no
push = no
```

## Recommended Next Action

Configure a bounded test channel endpoint locally, process-scoped only, then rerun exactly once:

```text
REAL_POWER_ATTEMPT_4_MODEL_LED_REAL_CHANNEL_SEND_V1
```

Expected local process env names only:

```text
SENTINEL_CHANNEL_WEBHOOK_URL
SENTINEL_CHANNEL_WEBHOOK_TOKEN
```

If a local webhook receiver is used, it must behave as the bounded test destination and return a safe delivery id/ref. Replay must prove no resend.
