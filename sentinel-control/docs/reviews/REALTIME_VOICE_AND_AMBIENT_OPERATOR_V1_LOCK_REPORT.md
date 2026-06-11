# Realtime Voice And Ambient Operator V1 Lock Report

Date: 2026-06-11

## Verdict

```text
REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1 = LOCKED
previous_phase = LIVE_DESKTOP_OPERATOR_BACKEND_AND_SYSTEM_MONITORING_V1_LOCKED
next_phase = DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1
roadmap_doctrine = product power under provable authority
```

Sentinel now has a Sentinel-owned realtime voice and ambient operator runtime
foundation. Voice is input/output and interaction over the existing Sentinel
runtime spine. It is not authority, not direct execution, not a provider-owned
assistant, not a hidden recorder, not a live provider integration, and not
provider fallback/AUTO.

## Research Summary

Created first:

```text
sentinel-control/docs/reviews/REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_RESEARCH_AND_DESIGN.md
```

Research conclusion:

```text
Sentinel owns the voice runtime.
The LLM may generate language.
A provider may provide STT/TTS/realtime speech.
Sentinel owns session state, authority, tools, receipts, FinalGate, telemetry,
replay, and execution.
```

The research compared speech-to-speech realtime sessions against a cascaded
`Audio -> VAD/turn detection -> STT -> Sentinel Kernel -> TTS` pipeline. V1
implements the cascaded Sentinel-owned path with fake/injected audio and models
speech-to-speech provider sessions as descriptor contracts only.

## Systems Studied

Official and primary-source systems studied:

- OpenAI Realtime / Voice Agents.
- OpenAI Agents SDK VoicePipeline.
- Google Gemini Live API.
- LiveKit Agents.
- Pipecat.
- Deepgram streaming STT.
- AssemblyAI streaming STT.
- ElevenLabs streaming TTS.
- Whisper / whisper.cpp.
- Silero VAD.
- Piper / Coqui-style local TTS posture.

No vendor runtime was installed, imported, bridged, or executed. No paid API was
called and no token was exposed.

## AgentLab Mechanisms Harvested

- JARVIS: semantic VAD, barge-in, voice session budgets, and desktop/voice
  coupling, rewritten as Sentinel-owned VAD, interruption, policy, and
  proposal-only desktop integration.
- Agent Zero and gptme: local operator continuation and task visibility,
  rewritten as `VoiceNotification`, `AmbientVoicePolicy`, and replayable voice
  lifecycle records.
- Hermes / DeerFlow / OpenClaw: long-running interactive workflow and broad
  product surface inspiration, rewritten as voice transport over existing
  MissionKernel, daemon, worker, skill, channel, and desktop boundaries.
- UI-TARS/JARVIS desktop coupling: voice-to-desktop command shape, rewritten as
  proposal/checkpoint data that cannot direct-control desktop.

No AgentLab or vendor code was copied.

## Runtime Added

Created:

```text
sentinel-control/services/sentinel-core/sentinel/operator/voice_models.py
sentinel-control/services/sentinel-core/sentinel/operator/voice_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/voice_replay.py
sentinel-control/services/sentinel-core/tests/test_realtime_voice_ambient_operator_v1.py
```

Updated:

```text
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

Core runtime concepts implemented:

```text
VoiceRuntime
VoiceRuntimeConfig
VoiceSession
VoiceMode
VoiceControlMode
VoiceProviderContract
VoiceProviderKind
VoiceModelContract
VoicePrivacyPolicy
AudioInputAdapter / AudioOutputAdapter / AudioTransportKind
AudioFrameRef / AudioStreamRef / AudioChunkRef
VoiceActivityDetector / VoiceActivityEvent
TurnDetectionPolicy / TurnDetectionResult / EndpointingDecision
BargeInPolicy / BargeInEvent / InterruptionDecision
SpeechToTextContract / SpeechToTextRequest / SpeechToTextResult
StreamingTranscriptEvent / PartialTranscript / FinalTranscript
TextToSpeechContract / TextToSpeechRequest / TextToSpeechResult
StreamingSpeechOutput / SpeechPlaybackState
RealtimeSpeechSessionContract / Descriptor / Event / ToolCallEnvelope
VoiceCommandEnvelope / VoiceIntentCandidate / VoiceCommandRiskProfile
VoiceConfirmationPolicy / Request / Result
VoiceKillWordPolicy / Event
VoiceNotification / AmbientVoicePolicy / AmbientVoiceEvent
VoiceOperatorPrompt / VoiceOperatorResponse
VoiceReceipt / VoiceFinalGateCertificate
VoiceReplayView / VoiceTelemetrySummary / VoiceSafetyScanResult
```

## Provider Architecture

Supported as descriptors only:

```text
local_stt
local_tts
api_stt
api_tts
realtime_speech_provider
openai_realtime_style_descriptor
gemini_live_style_descriptor
livekit_style_transport_descriptor
pipecat_style_pipeline_descriptor
```

Descriptor semantics:

```text
descriptor != executable backend
provider event != authority
provider tool-call-like event != execution
provider contract != provider key storage
realtime provider session != Sentinel session authority
```

The only executable V1 backend is fake/injected and local.

## Voice Modes

Implemented modes:

```text
DISABLED
PUSH_TO_TALK
WAKE_WORD
SESSION_VOICE
AMBIENT_LISTENER
AMBIENT_OPERATOR
FULL_VOICE_COPILOT
```

Ambient listener/operator modes require explicit `AmbientVoicePolicy`. Full
voice copilot remains modeled only and does not claim production readiness.

## Barge-In And Turn Detection

Implemented:

- `VoiceActivityEvent` for speech lifecycle.
- `TurnDetectionPolicy`, `EndpointingDecision`, and `TurnDetectionResult`.
- partial transcript events.
- final transcript events.
- `BargeInEvent` and `InterruptionDecision`.
- kill word detection that interrupts output and kills the voice session.

## Voice Command Authority Review

Voice flow:

```text
audio/transcript
-> VoiceCommandEnvelope
-> safety scan
-> intent/risk profile
-> proposal/checkpoint metadata
-> existing MissionKernel / authority / runtime path
```

Hard boundaries preserved:

- voice cannot create or expand `MissionAuthorityEnvelope`;
- voice cannot unlock credentials;
- voice cannot bypass MissionKernel, DesktopSidecar, PowerRuntime,
  AgentRuntime bridge, Gate, receipts, FinalGate, telemetry, or replay;
- transcript, voice identity, wake word, and confirmation are evidence only;
- dangerous commands require confirmation/checkpoint, not direct action.

## Desktop Integration

Voice-to-desktop commands create `VoiceDesktopActionProposal` records only.
Desktop action still requires:

```text
MissionAuthorityEnvelope
Desktop permission policy
control mode
app/window/region allowlist
sensitive-region check
kill/revocation
receipt
FinalGate
telemetry
replay
```

No voice code can direct-control desktop.

## Ambient Operator Policy

Implemented `AmbientVoicePolicy` for:

- allowed proactive categories;
- blocked categories;
- quiet hours shape;
- mission-only speech;
- privacy and retention posture.

Allowed examples include mission blocked, approval needed, desktop monitoring
alerts, worker/daemon handoffs, channel approval needed, and dangerous action
blocked. Hidden listening and unbounded ambient transcription remain blocked.

## Storage And Privacy Posture

Stored by default:

```text
audio hash/ref
transcript hash
redacted transcript excerpt
voice event metadata
turn timing metadata
barge-in event
confirmation metadata
receipt refs
FinalGate refs
telemetry refs
```

Blocked by default:

```text
raw audio
raw full transcript
speaker biometrics
provider keys
raw prompts
raw provider responses
raw reasoning
credentials/tokens/secrets
```

## Telemetry And Replay

Added voice telemetry events and product-power metrics through the existing
`TelemetryKernel`; no parallel telemetry system was created.

Replay reconstructs voice config, sessions, audio refs, VAD events, turn
decisions, transcripts, command envelopes, confirmations, notifications,
outputs, interruptions, kill events, desktop proposals, receipts, FinalGate
refs, and telemetry refs.

Replay flags prove:

```text
played_audio = false
recorded_microphone = false
called_provider = false
executed_actions = false
```

## CodeRabbit Advisory Review

CodeRabbit used: no.

`coderabbit --version` was unavailable in this environment. Per phase rules, no
unknown dependency was installed and no token/auth flow was started. Manual
Sentinel audit was performed instead. CodeRabbit did not become authority.

## Exhaustive Audit Findings

| Severity | Finding | File / Surface | Decision | Fix Or Rationale | Remaining Limits |
| --- | --- | --- | --- | --- | --- |
| P0 | Voice as authority | `voice_models.py`, `voice_runtime.py` | Passed | All voice models inherit data-not-authority fields; direct execution APIs raise | Authority UX remains outside voice |
| P0 | Provider-owned authority | Provider descriptors and realtime tool envelope | Passed | Provider contracts are descriptor-only; provider-native tool execution is blocked | Live providers remain future |
| P0 | Hidden always-on recorder | Runtime and privacy policy | Passed | No microphone adapter exists; raw audio persistence is blocked | Production audio adapter not started |
| P0 | Raw audio/transcript persistence | Audio/transcript models | Fixed | Audio is hash-only; transcript stores hash and redacted excerpt; long raw field names were removed from persistence | Future transcript retention needs explicit policy |
| P1 | Confirmation as authority | Confirmation models | Passed | Confirmation result is evidence only and `can_execute=false` | Future UX must display proposal before confirmation |
| P1 | Voice-to-desktop direct control | Desktop proposal path | Passed | Voice creates proposal-only records; direct integration execution raises | Live desktop adapter remains future |
| P1 | Replay audio/action replay | `voice_replay.py` | Passed | Replay loads JSON only and sets no-play/no-record/no-provider/no-action flags | No voice replay UI yet |
| P1 | Provider fallback/AUTO | Provider contracts | Passed | No fallback or live provider routing exists | Future provider integration must remain explicit |
| P1 | Telemetry bypass | Runtime event/metric path | Passed | MissionRunStore and TelemetryKernel are reused | Production telemetry cloud not started |
| P2 | Research overclaim | Research/design doc and roadmap | Passed | Docs clearly distinguish descriptors/fake backend from live provider runtime | Live provider performance not proven |
| P2 | Ambient operator scope | `AmbientVoicePolicy` | Passed | Ambient categories are allowlisted/blocklisted and policy-required | Wake-word engine not implemented |

No open P0/P1 or serious P2 findings remain.

## Honest V1 Limits

- Voice runtime is local same-process foundation.
- Audio backend is fake/injected only.
- Provider support is descriptor-only.
- No microphone, speaker, live STT, live TTS, WebRTC, WebSocket, or realtime
  provider call is implemented.
- No voice cloning, speaker biometrics, durable credential vault, account,
  payment, security, device power, provider fallback/AUTO, or vendor runtime
  integration exists.
- Ambient listener/operator are scoped policy shapes and safe notifications,
  not hidden always-on recording.

## Tests And Checks

Verification completed:

```text
py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_realtime_voice_ambient_operator_v1.py -q
15 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_live_desktop_operator_backend_system_monitoring_v1.py sentinel-control/services/sentinel-core/tests/test_permissioned_desktop_sidecar_visual_grounding_v1.py -q
33 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_real_channel_adapters_v1.py sentinel-control/services/sentinel-core/tests/test_local_model_hardware_and_cost_router_v1.py sentinel-control/services/sentinel-core/tests/test_governed_skill_and_procedure_fabric_v1.py sentinel-control/services/sentinel-core/tests/test_model_amplification_execution_harness_v1.py -q
50 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_production_mission_daemon_and_scheduler_v1.py sentinel-control/services/sentinel-core/tests/test_mission_worker_fleet_authority_inheritance_v1.py sentinel-control/services/sentinel-core/tests/test_observability_telemetry_and_product_power_metrics_v1.py -q
24 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_and_automatic_replan_v1.py sentinel-control/services/sentinel-core/tests/test_durable_mission_workflow_replan_gauntlet_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_integrations_v1.py sentinel-control/services/sentinel-core/tests/test_persistent_semantic_memory_gauntlet_v1.py -q
128 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_flow_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_power_runtime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_agentruntime_bridge_v0.py sentinel-control/services/sentinel-core/tests/test_llm_live_operator_cockpit_cli_v0.py -q
51 passed

py -3.13 -m pytest sentinel-control/services/sentinel-core/tests/test_sentinel_power_runtime_v0.py sentinel-control/services/sentinel-core/tests/test_agent_runtime.py sentinel-control/services/sentinel-core/tests/test_brain_to_organ_runtime_closed_loop.py sentinel-control/services/sentinel-core/tests/test_delegated_action_gate_model_v0.py sentinel-control/services/sentinel-core/tests/test_agent_core_final_gate.py sentinel-control/services/sentinel-core/tests/test_final_gate_determinism.py sentinel-control/services/sentinel-core/tests/test_final_gate_registry.py sentinel-control/services/sentinel-core/tests/test_final_gate_terminality.py -q
126 passed

py -3.13 -m pytest tests/test_browser_visual_grounding_ocr_v1.py tests/test_browser_organ_final_gate.py tests/test_gate_sequence_runtime_wiring.py tests/test_gate_sequence_integration.py -q
55 passed

py -3.13 -m compileall -q sentinel-control/services/sentinel-core/sentinel
OK

git diff --check
OK
```

Total verification count:

```text
482 targeted and regression tests passed
compileall OK
diff whitespace check OK
```

Modified-file scans were run for:

```text
secret/raw credential/token persistence
raw audio/full transcript/screenshot/OCR persistence
raw prompt/provider response/reasoning persistence
fallback/AUTO and provider-native tool paths
direct organ bypass
replay audio/action risks
```

Scan result:

```text
No real secret, credential, token, raw audio, raw provider response, raw
reasoning, fallback/AUTO, provider-native tool, direct organ bypass, replay
audio playback, provider call, or action replay implementation was found.
Expected hits were doctrinal BLOCKED text, validator error messages, and tests
that assert forbidden fields are not persisted.
```

## Files Created

```text
sentinel-control/docs/reviews/REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_RESEARCH_AND_DESIGN.md
sentinel-control/docs/reviews/REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1_LOCK_REPORT.md
sentinel-control/services/sentinel-core/sentinel/operator/voice_models.py
sentinel-control/services/sentinel-core/sentinel/operator/voice_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/voice_replay.py
sentinel-control/services/sentinel-core/tests/test_realtime_voice_ambient_operator_v1.py
```

## Files Updated

```text
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
```

## Next Phase

```text
DURABLE_CREDENTIAL_VAULT_AND_SECRET_BROKER_V1
```

Stop condition honored: Durable Credential Vault and Secret Broker was not
started.
