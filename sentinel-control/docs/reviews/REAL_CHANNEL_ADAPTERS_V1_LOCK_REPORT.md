# Real Channel Adapters V1 Lock Report

Date: 2026-06-11

## Verdict

`REAL_CHANNEL_ADAPTERS_V1` is locked as a Sentinel-native local runtime
foundation.

```text
current_phase = REAL_CHANNEL_ADAPTERS_V1_LOCKED
previous_phase = LOCAL_MODEL_HARDWARE_AND_COST_ROUTER_V1_LOCKED
next_phase = PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1
roadmap_doctrine = product power under provable authority
```

The implementation adds real channel adapter reach as a governed adapter layer
over the existing channel organ and Sentinel runtime spine. It is not a
credential vault, not a provider-specific Telegram/Slack/Gmail connector, not a
remote plugin channel runtime, not ambient send authority, and not a new
authority path.

## Sentinel Components Reused

```text
MissionKernel / MissionRunStore = reused for mission-owned persistence, timeline, hash-chain verification
TelemetryKernel / TelemetryStore = reused for channel adapter events and metrics
ChannelDraftSendOrganV1 = reused for draft/send execution contract, rate ledger, receipt, FinalGate
MissionAuthorityEnvelope = reused as the only channel send authority source
operator redaction/safety utilities = reused for raw token, credential, prompt, provider response, reasoning blocking
PowerRuntime channel family doctrine = preserved; no direct organ bypass added
receipts / FinalGate / replay doctrine = preserved; replay never resends
```

No parallel mission store, channel runtime, authority system, telemetry system,
memory system, model router, worker runtime, skill runtime, or vendor runtime
was created.

## AgentLab Mechanisms Harvested

AgentLab was inspected as source-only reference. No vendor code, runtime,
dependency, service connection, connector bridge, account, or credential was
copied, installed, or run.

```text
OpenClaw = channel/session/gateway reach and approval-surface inspiration
Hermes / JARVIS = channel lifecycle visibility and operator-facing status patterns
OpenJarvis = proactive connector proposals as data, never authority
gptme / Agent Zero = local background status ergonomics and operator handoff thinking
oh-my-pi = minimized structured results and hash-anchored state discipline
```

All mechanisms were rewritten Sentinel-native as adapter descriptors, inbound
untrusted envelopes, outbound draft/approval/send records, injected transport,
receipts, telemetry, and replay.

## Runtime Added

```text
sentinel/operator/channel_adapter_models.py
sentinel/operator/channel_adapter.py
sentinel/operator/channel_adapter_replay.py
```

Implemented concepts:

```text
ChannelAdapterConfig
ChannelAdapterKind
ChannelProviderKind
ChannelCapabilityProfile
ChannelIdentityRef
ChannelRecipientPolicy
ChannelScopePolicy
ChannelRateLimitPolicy
ChannelApprovalPolicy
ChannelInboundEnvelope
ChannelInboundMessage
ChannelAttachmentRef
ChannelAttachmentQuarantine
ChannelLinkQuarantine
ChannelOutboundRequest
ChannelOutboundDraft
ChannelOutboundApproval
ChannelOutboundSendRequest
ChannelDeliveryResult
ChannelAdapterReceipt
ChannelAdapterFinalGateCertificate
ChannelAdapterReplayView
ChannelAdapterTelemetrySummary
ChannelConnectorRegistry
ChannelConnectorRuntime
ChannelAdapterReplayBuilder
```

## First Adapter Maturity

```text
first adapter = webhook-style explicit adapter descriptor
maturity = CLOSED / local same-process adapter foundation with injected transport
live external provider calls in tests = no
real provider-specific adapter = NOT_STARTED
durable channel credential/session broker = NOT_STARTED
```

The first adapter foundation can send through an explicit injected transport
only after mission authority, recipient policy, scope policy, rate policy,
operator approval, idempotency, kill/revocation/expiry checks, the existing
channel organ, receipts, FinalGate refs, telemetry, and replay records.

## Inbound Lifecycle

```text
inbound message = untrusted data
identity binding = unverified by default
raw text persistence = blocked; safe redacted text + text hash only
attachments = metadata-only refs quarantined
links = hash-only quarantine records
inbound authority creation = blocked
inbound direct execution = blocked
```

## Outbound Lifecycle

```text
draft = no transport call, no send attempted
approval = operator/operator_policy/manual_operator only
send = requires MissionAuthorityEnvelope
recipient/scope/rate/idempotency = enforced before transport call
revoked/expired/killed mission = blocked before transport call
transport = injected only
execution = ChannelDraftSendOrganV1
receipt = ChannelAdapterReceipt + reused channel organ receipt ref
FinalGate = ChannelAdapterFinalGateCertificate + reused channel organ FinalGate ref
replay = no resend
```

## Telemetry And Metrics

Added telemetry source surface:

```text
TelemetrySourceSurface.CHANNEL_ADAPTER
```

Added events:

```text
channel_adapter_registered
channel_adapter_rejected
channel_inbound_received
channel_inbound_quarantined
channel_identity_bound
channel_outbound_draft_created
channel_outbound_approval_recorded
channel_outbound_send_requested
channel_outbound_send_blocked
channel_outbound_sent
channel_outbound_failed
channel_duplicate_send_blocked
channel_revocation_detected
channel_kill_switch_triggered
channel_replay_built
```

Added metrics:

```text
channel_inbound_message_count
channel_outbound_draft_count
channel_outbound_send_count
channel_outbound_block_count
channel_approval_required_count
channel_rate_limit_block_count
channel_duplicate_send_block_count
channel_receipt_completeness
channel_delivery_success_rate
channel_replay_completeness
```

Telemetry remains data only. It cannot approve, execute, grant authority,
unlock credentials, become future permission, or hide from the operator.

## Authority Review

```text
MissionAuthorityEnvelope is the only send authority source = preserved
LLM output as send authority = blocked
memory as send authority = blocked
skill output as send authority = blocked
worker output as send authority = blocked
daemon/scheduler output as send authority = blocked
telemetry/receipt/FinalGate as send authority = blocked
unapproved send = blocked
direct organ bypass = blocked; runtime uses ChannelDraftSendOrganV1
provider fallback/AUTO = not introduced
new model/provider routing = not introduced
```

## CodeRabbit Advisory Review

```text
CodeRabbit used = no
review source = not available in this environment
finding summary = CodeRabbit unavailable in this environment; manual exhaustive audit performed instead
confirmation = CodeRabbit did not become authority
```

No CodeRabbit dependencies were installed and no tokens or secrets were exposed.

## Exhaustive Audit Findings

| Severity | Finding | Surface | Decision | Fix or rationale | Remaining limits |
| --- | --- | --- | --- | --- | --- |
| P0 | Channel send without mission authority | `ChannelConnectorRuntime.send_outbound` | fixed | requires `MissionAuthorityEnvelope`, matching mission id, allowed action/tool, non-revoked and non-expired state | none for V1 |
| P0 | Non-operator approval source | `ChannelOutboundApproval`, send path | fixed | only `operator`, `operator_policy`, or `manual_operator` sources validate | none |
| P0 | Replay re-sends channel message | `ChannelAdapterReplayBuilder` | fixed | replay only loads persisted artifacts and never calls transport | none |
| P1 | Duplicate send risk | idempotency path | fixed | successful sends persist idempotency hash; duplicates fail closed | V1 same run-root local store only |
| P1 | Raw recipient persistence | drafts/results/events | fixed | persisted recipient data is hash-only; raw recipients remain ephemeral same-process context | restart send requires future credential/session broker |
| P1 | Raw token/credential persistence | adapter metadata | fixed | raw token/credential keys and secret-like values are rejected | credential vault not started |
| P1 | Raw prompt/provider response/reasoning persistence | adapter/request metadata | fixed | raw prompt/provider response/reasoning keys are rejected unless hash-only | none |
| P1 | Event metadata scanner rejected send-like ids | channel sent event | fixed | event metadata uses safe hashes and dedicated receipt/finalgate ref fields | none |
| P2 | Provider-specific channel maturity could be overclaimed | docs/report | fixed | report states webhook-style injected transport foundation; Telegram/Slack/Gmail remain not started | real providers future |
| P2 | Durable outbound send after restart lacks raw recipients | runtime design | accepted limit | raw recipients are not durably stored by design; future broker must solve this safely | documented V1 limit |

No open P0/P1 or serious P2 findings remain.

## Tests And Checks

Targeted tests completed:

```text
py -3.13 -m pytest tests/test_real_channel_adapters_v1.py -q
16 passed

py -3.13 -m pytest tests/test_real_channel_adapters_v1.py tests/test_channel_draft_send_organ_v1.py tests/test_sentinel_power_runtime_v0.py tests/test_power_fabric_orchestration_demo.py tests/test_external_api_read_write_organ_v1.py tests/test_local_model_hardware_and_cost_router_v1.py tests/test_observability_telemetry_and_product_power_metrics_v1.py -q
passed

py -3.13 -m pytest tests/test_governed_skill_and_procedure_fabric_v1.py tests/test_model_amplification_execution_harness_v1.py tests/test_production_mission_daemon_and_scheduler_v1.py tests/test_mission_worker_fleet_authority_inheritance_v1.py tests/test_durable_mission_workflow_and_automatic_replan_v1.py tests/test_durable_mission_workflow_replan_gauntlet_v1.py -q
passed

py -3.13 -m pytest tests/test_llm_live_operator_models_v0.py tests/test_llm_live_operator_conversation_intake_v0.py tests/test_llm_live_operator_mission_kernel_v0.py tests/test_llm_live_operator_cockpit_flow_v0.py tests/test_llm_live_operator_power_runtime_bridge_v0.py tests/test_llm_live_operator_agentruntime_bridge_v0.py tests/test_llm_live_operator_replay_v0.py tests/test_agent_runtime.py tests/test_agent_event_bus.py tests/test_agent_evidence_chain.py tests/test_low_risk_execution_finalgate_receipts.py -q
passed
```

Additional final checks completed during lock:

```text
py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
OK

git diff --check
OK, CRLF normalization warnings only

coderabbit --version
unavailable in this environment; no install attempted and no token exposed

secret/raw prompt/provider response/reasoning scan on modified files
OK; only synthetic negative-test fixtures found in test_real_channel_adapters_v1.py

provider fallback/AUTO / provider override scan on modified files
OK; runtime rejects these fields and docs/tests contain only boundary assertions

direct organ bypass scan on modified files
OK; only intentional ChannelDraftSendOrganV1 reuse found, no direct dispatcher/provider path
```

## Files Created Or Updated

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/docs/reviews/REAL_CHANNEL_ADAPTERS_V1_LOCK_REPORT.md
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter.py
sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter_models.py
sentinel-control/services/sentinel-core/sentinel/operator/channel_adapter_replay.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/tests/test_real_channel_adapters_v1.py
```

## Next Phase

```text
PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1
```

Do not start Desktop Sidecar until this lock is committed, pushed, and verified
against `origin/main`.
