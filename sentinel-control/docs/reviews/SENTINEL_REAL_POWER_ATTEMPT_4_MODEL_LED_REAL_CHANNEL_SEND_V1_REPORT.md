# SENTINEL REAL POWER ATTEMPT 4 MODEL LED REAL CHANNEL SEND V1 REPORT

## Verdict

```text
REAL_POWER_ATTEMPT_4_MODEL_LED_REAL_CHANNEL_SEND_V1 = REAL_CHANNEL_TRANSPORT_CONFIG_MISSING
provider_calls = 0
channel_transport_calls = 0
```

This is a static preflight stop, not a consumed provider attempt.

This report was refreshed after the operator selected Telegram as the real channel and requested a rerun with process-scoped Telegram env vars. The current Codex process still does not contain the Telegram token/chat id env vars, so the attempt stopped again before any model/provider or channel transport call.

## Source

```text
source_commit = 1dc08db77f12e860b65590cc5e9f9b677d8083f2
pack_under_test = POWER_PACK_5_REAL_CHANNEL_TRANSPORT_SEND_V1
transport_bridge_commit = 1dc08db77f12e860b65590cc5e9f9b677d8083f2
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

Required Telegram config names:

```text
SENTINEL_TELEGRAM_BOT_TOKEN
SENTINEL_TELEGRAM_CHAT_ID
```

Safe facts only:

```text
SENTINEL_TELEGRAM_BOT_TOKEN present = false
SENTINEL_TELEGRAM_CHAT_ID present = false
```

Both Telegram env names are required for the current real channel transport builder.

## Stop Reason

```text
blocked_before_provider = true
blocked_before_channel_call = true
reason = REAL_CHANNEL_TRANSPORT_CONFIG_MISSING
```

The implementation now has a real Telegram Bot API transport seam, but no mission-scoped Telegram token/chat id is configured in the current Codex process.

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
SENTINEL_TELEGRAM_BOT_TOKEN
SENTINEL_TELEGRAM_CHAT_ID
```

The next rerun must occur in a process where both values are present. Replay must prove no resend.
