# SENTINEL_MONSTER_RUNTIME_PHASE_3_LIVE_CHANNEL_PRODUCT_SPINE_PROMOTION_V1_REPORT

## Verdict

```text
SENTINEL_MONSTER_RUNTIME_PHASE_3_LIVE_CHANNEL_PRODUCT_SPINE_PROMOTION_V1
= LOCALLY_COMMITTED_IMPLEMENTED_CANDIDATE

implementation_commit = d7616f1 fix: promote telegram channel through product spine
product_proven_with_real_external_send = no
provider_call = no
real_channel_send = no
push = no
```

## Prior Product Truth

```text
REAL_MONSTER_PRODUCT_ATTEMPT_6E = VALID_SUCCESS
phase_2_delegated_product_runtime_proof = real-provider proven
capability path included workspace_patch, code_exec, fake/local bounded_channel, worker_fleet, finish
artifact export verifier = accepted
replay_no_react = true
```

Phase 3 begins live-surface promotion. This pack promotes the bounded Telegram channel path into the existing product spine. It does not claim a real Telegram send yet.

## Files Changed

```text
sentinel/operator/runtime_host.py
sentinel/operator/product_model_native_decision_client.py
sentinel/operator/model_led_product_action_kernel_task_loop.py
tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py
tests/operator/test_real_monster_product_model_native_decision_client.py
```

## Old Path

```text
model-native send_message
-> ProductModelNativeDecisionClient
-> bounded_channel.send_message
-> monster_fake_channel / webhook
-> local fake transport
```

RuntimeHost also rejected non-webhook channels as real transport unavailable. That was correct before explicit live-channel promotion, but it meant Telegram could not be used through the product spine.

## New Product Spine Path

```text
model-native send_message
-> ProductModelNativeDecisionClient
-> live_channel_destination_grants
-> internal ActionEnvelope bounded_channel.send_message
-> RuntimeHost
-> ProductActionKernelDispatchAdapter
-> ProductActionKernel
-> bounded_channel runtime executor
-> ChannelConnectorRuntime
-> TelegramBotChannelTransport
-> channel receipt / ProductActionKernel receipt / FinalGate
-> replay no-resend
```

ActionEnvelope remains internal runtime language. The model-facing skill is still `send_message`.

## Telegram Grant Requirements

Telegram is available only when all are true:

```text
channel = telegram
allowed_tools includes channel:telegram
allowed_domains includes telegram:configured-chat
SENTINEL_TELEGRAM_BOT_TOKEN present in process env
SENTINEL_TELEGRAM_CHAT_ID present in process env
```

If grant is missing:

```text
blocked_reason = bounded_channel_real_transport_not_authorized
```

If process config is missing:

```text
blocked_reason = bounded_channel_real_transport_config_missing
```

## No Silent Local Fallback

Telegram no longer silently maps to the fake local webhook path. If `channel=telegram`, the executor builds `TelegramBotChannelTransport` from process env or blocks before send. The local fake transport remains the default only for `channel=webhook`.

## Model-Native Mapping

When context includes:

```json
{"adapter_id":"telegram_live_adapter","channel":"telegram","destination_ref":"telegram:configured-chat"}
```

natural or semi-structured model intent such as:

```text
Send the live completion update now.
```

maps to internal:

```text
capability_id = bounded_channel
operation = send_message
adapter_id = telegram_live_adapter
channel = telegram
recipient = telegram:configured-chat
```

Model-supplied adapter/channel/recipient fields still cannot override the granted local channel when no live destination grant is present.

## Secret Persistence Boundary

The implementation uses env names only. Tests verify that raw test token/chat values are not persisted in JSON run artifacts.

Allowed persisted proof:

```text
delivery_ref = telegram:<message_id>
transport_kind = telegram_real_product_dispatch
destination ref = telegram:configured-chat
```

Forbidden persisted material:

```text
raw bot token
raw chat id
Authorization
Bearer token
raw provider reasoning
raw DOM/cookies/session/profile material
```

## Tests Run

```text
py -3.13 -m pytest tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py::test_bounded_channel_real_send_not_available_without_explicit_grant tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py::test_bounded_channel_telegram_routes_real_transport_with_explicit_grant tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py::test_bounded_channel_telegram_requires_process_config_before_send -q
result = 3 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py::test_metadata_reply_send_message_uses_granted_telegram_destination tests/operator/test_real_monster_product_model_native_decision_client.py::test_product_loop_routes_model_native_send_to_granted_telegram_transport -q
result = 2 passed

py -3.13 -m pytest tests/operator/test_power_cleanup_actionkernel_skill_parity_code_channel.py -q --durations=10 --maxfail=1
result = 16 passed

py -3.13 -m pytest tests/operator/test_power_pack5_real_channel_transport_send.py -q --durations=10 --maxfail=1
result = 11 passed

py -3.13 -m pytest tests/operator/test_real_monster_product_model_native_decision_client.py -q --durations=15 --maxfail=1
result = 48 passed

py -3.13 -m compileall -q sentinel
result = passed

git diff --check -- touched files
result = passed
```

Targeted scan:

```text
hits = env-name references and benign redaction-test strings only
raw credential values persisted = no evidence in touched files
raw provider reasoning persistence introduced = no
provider-native tools introduced = no
fallback/AUTO introduced = no
```

## Hard Boundaries Preserved

```text
payment / checkout / spend = unchanged hard stop
credentials / secrets = unchanged hard stop
login / account mutation = unchanged hard stop
contact supplier outside grant = unchanged hard stop
external send outside explicit grant = blocked
provider-native tools = not introduced
fallback/AUTO = not introduced
replay side effects = no-resend path preserved
fake proof / proof tampering = not introduced
```

## Remaining Gaps

```text
real Telegram send through product spine is not yet consumed
real provider-driven live send is not yet product-proven
external channel proof still needs one named real attempt
```

## Next Prepared Proof

```text
REAL_MONSTER_PRODUCT_ATTEMPT_7A_REAL_TELEGRAM_PRODUCT_SPINE_SEND_V1
```

Target proof:

```text
real provider decision
-> model-native send_message
-> ProductActionKernel
-> TelegramBotChannelTransport
-> one real Telegram send
-> ProductActionKernel receipt + channel receipt
-> sentinel_loop.finish
-> mission completed
-> replay no resend
-> artifact bundle verifier accepts exported proof
```

Do not run without an explicit real-attempt contract and process-scoped provider + Telegram env readiness.
