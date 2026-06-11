# Realtime Voice And Ambient Operator V1 Research And Design

Date: 2026-06-11

Baseline:

```text
current_phase = LIVE_DESKTOP_OPERATOR_BACKEND_AND_SYSTEM_MONITORING_V1_LOCKED
previous_phase = PERMISSIONED_DESKTOP_SIDECAR_AND_VISUAL_GROUNDING_V1_LOCKED
next_phase = REALTIME_VOICE_AND_AMBIENT_OPERATOR_V1
HEAD = ba57aa41d722ffeff10ef0a4099b1d029cec6deb
roadmap_doctrine = product power under provable authority
```

## Verdict

Sentinel Voice V1 should be Sentinel-owned, not provider-owned.

The implementation should model both modern voice-agent architectures:

```text
Architecture A: native realtime speech-to-speech provider session
Architecture B: Audio -> VAD / turn detection -> STT -> Sentinel Kernel -> TTS -> output
```

V1 should implement Architecture B first with a fake/injected backend and
provider descriptors for Architecture A. This keeps the MissionKernel,
authority checks, confirmation, receipts, FinalGate, telemetry, and replay in
Sentinel-owned runtime state.

## Sources Studied

Official and primary sources:

- OpenAI Voice Agents guide:
  https://developers.openai.com/api/docs/guides/voice-agents
- OpenAI Realtime and audio guide:
  https://developers.openai.com/api/docs/guides/realtime
- OpenAI Agents SDK VoicePipeline reference:
  https://openai.github.io/openai-agents-python/ref/voice/pipeline/
- Google Gemini Live API overview:
  https://ai.google.dev/gemini-api/docs/live-api
- Gemini Live API WebSocket guide:
  https://ai.google.dev/gemini-api/docs/live-api/get-started-websocket
- Gemini Live API capabilities:
  https://ai.google.dev/gemini-api/docs/live-api/capabilities
- Gemini Live API session management:
  https://ai.google.dev/gemini-api/docs/live-api/session-management
- LiveKit Agents overview:
  https://docs.livekit.io/agents/
- LiveKit turn detection and interruption:
  https://docs.livekit.io/agents/logic/turns/
- LiveKit agent speech and audio:
  https://docs.livekit.io/agents/multimodality/audio/
- Pipecat pipeline and frame processing:
  https://docs.pipecat.ai/pipecat/learn/pipeline
- Pipecat frames:
  https://docs.pipecat.ai/api-reference/server/frames/overview
- Pipecat transports:
  https://docs.pipecat.ai/pipecat/learn/transports
- Pipecat context management:
  https://docs.pipecat.ai/pipecat/learn/context-management
- Deepgram endpointing and interim results:
  https://developers.deepgram.com/docs/understand-endpointing-interim-results
- Deepgram live streaming audio:
  https://developers.deepgram.com/docs/live-streaming-audio
- AssemblyAI realtime speech-to-text:
  https://www.assemblyai.com/products/streaming-speech-to-text
- AssemblyAI streaming model selection:
  https://assemblyai.com/docs/streaming/select-the-speech-model
- ElevenLabs streaming TTS:
  https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/streaming
- ElevenLabs realtime TTS WebSocket:
  https://elevenlabs.io/docs/eleven-api/guides/how-to/websockets/realtime-tts
- OpenAI Whisper:
  https://github.com/openai/whisper
- whisper.cpp realtime stream example:
  https://github.com/ggml-org/whisper.cpp
- Silero VAD:
  https://github.com/snakers4/silero-vad
- Piper local TTS:
  https://github.com/rhasspy/piper
- OHF Piper continuation:
  https://github.com/OHF-Voice/piper1-gpl

AgentLab source-only references:

- `agent-lab/AGENT_LAB_PLAN.md`
- `agent-lab/audits/AGENT_COMPARISON_MATRIX.md`
- `agent-lab/audits/final/2026-06-06_agent_lab_vendor_refresh_delta_report.md`
- `agent-lab/audits/final/2026-06-06_sentinel_competitive_power_delta_and_roadmap.md`

External web research was available. No vendor runtime was installed, no paid
API was called, no token was exposed, and no dependency was added during this
research pass.

## Vendor And System Synthesis

| Vendor / System | Architecture pattern | Useful mechanism | Sentinel-native adaptation | Risks | What not to copy | Implementation implication |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAI Realtime / Voice Agents | Speech-to-speech sessions and chained voice pipeline | WebRTC/WebSocket realtime sessions, tool calls, interruption, handoffs, STT-agent-TTS pipeline | Model provider descriptors and fake realtime events; Sentinel keeps tool execution and authority | Provider-owned tools can become hidden authority | Provider-native tool execution, raw prompt/provider response persistence, hidden assistant state | Implement both descriptors; make chained Sentinel-owned path V1 runtime |
| Gemini Live API | Low-latency audio/video/text session over WebSocket | Persistent session, streamed audio chunks, native audio output, session lifetime/compression concepts | Realtime session descriptor and replay-safe event refs | Multimodal provider session could hide actions or prompt material | Direct provider authority, provider key persistence, tool execution outside Sentinel | Store descriptor metadata only; no live Gemini call in tests |
| LiveKit Agents | Realtime room/participant voice agent orchestration | STT/LLM/TTS and realtime-model unification, turn detection, interruption modes, session lifecycle | TurnDetectionPolicy, BargeInPolicy, VoiceSession lifecycle | Production transport complexity and external service dependency | LiveKit runtime bridge or vendor agent server | Use concepts for turn/interruption state machines, not runtime |
| Pipecat | Pipeline of processors and frames | Transport input/output, frame types, STT/LLM/TTS chaining, context updates from actual spoken TTS | AudioFrameRef, StreamingTranscriptEvent, StreamingSpeechOutput, pipeline descriptor | Pipeline processors can become a second execution path | Dynamic pipeline execution, external service plugins | Use frame/event vocabulary and fake processors only |
| Deepgram | Streaming STT | Interim results, endpointing, speech_final, keepalive concepts | PartialTranscript, FinalTranscript, EndpointingDecision | Interim text can be mistaken for final command | Direct command execution from interim text | Partial transcripts are untrusted; only final transcript can create command envelope |
| AssemblyAI | Streaming STT for voice agents | Partial/final transcripts, low-latency websocket model, endpointing | Provider descriptor and transcript event lifecycle | Provider keys and raw audio streams | Credential probing or external streaming in tests | Descriptor only; no key storage |
| ElevenLabs | Streaming TTS/WebSocket TTS | Streaming audio output, chunked text input, context ids | TextToSpeechContract, StreamingSpeechOutput, SpeechPlaybackState | Voice cloning, raw generated audio retention, provider state | Voice cloning, persistent provider sessions as authority | V1 uses fake/injected output adapter |
| Whisper / whisper.cpp | Local STT | Local/offline transcription, realtime microphone examples in whisper.cpp | local_stt descriptor and privacy-first candidate | Local microphone capture and model install surface | Model download/server management in this phase | Descriptor only; future opt-in backend must be local and governed |
| Silero VAD | Local VAD | Lightweight CPU VAD and speech activity events | VoiceActivityDetector descriptor and fake VAD event lifecycle | False positives/negatives can trigger bad turns | Treating wake/VAD as command authority | VAD events are timing data only |
| Piper / Coqui-style local TTS | Local TTS | Local neural speech output | local_tts descriptor and fake output adapter | Voice cloning and raw audio retention | Cloning or unmanaged voice models | Descriptor only; V1 TTS fake/injected |
| JARVIS | Realtime voice plus desktop/sidecar/product flow | Semantic VAD, barge-in, session budgets, desktop coupling | Sentinel-owned voice runtime with desktop proposals | Voice auto-approval of actions | Provider or voice direct action integration | Voice commands create proposals/checkpoints only |
| Agent Zero / gptme | Local interactive long-running operator loops | Continuation, interruption, operator handoff | AmbientVoicePolicy and VoiceNotification | Ambient full-system authority | Ambient shell/desktop authority | Voice may notify and hand off, not execute |
| Hermes / DeerFlow / OpenClaw | Broad surface, channels, skills, long tasks | Interactive workflow continuity and multi-step control | Voice as transport over existing daemon/worker/skill/channel spine | Skill/channel execution from conversation | Vendor bridge, plugin authority, channel sends from voice | Voice-to-channel/skill/worker requests must checkpoint |

## Research Questions Answered

### 1. Should Sentinel Voice be owned by the LLM provider or Sentinel runtime?

Sentinel runtime. Providers may supply STT, TTS, or realtime speech sessions,
but Sentinel must own session state, authority, command envelopes, confirmation
policy, tool execution, receipts, FinalGate, telemetry, and replay. Provider
sessions are data sources and output sinks, not authority or execution owners.

### 2. What are the two primary architectures?

Architecture A is native realtime speech-to-speech: audio enters a provider
session and audio comes back from the same realtime model/session, often with
tool-call events and interruption support.

Architecture B is cascaded: audio input is converted through VAD/turn
detection and STT into text, Sentinel processes the text through cockpit,
MissionKernel, LLM/model contract, safety, and runtime paths, then TTS converts
Sentinel's response into audio output.

### 3. Which architecture should Sentinel V1 implement first?

Architecture B. It is less magical and more controllable. It also maps cleanly
to existing Sentinel layers: untrusted input -> safe command envelope ->
MissionKernel proposal/checkpoint -> authority validation -> existing runtime
path -> receipts/FinalGate -> spoken response.

Architecture A should exist in V1 only as descriptors and replay-safe event
models so future realtime providers can be admitted without redesign.

### 4. How does Sentinel support both local and API voice providers?

Through provider contracts and descriptors:

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

Descriptors are not executable backends. Live calls require a future explicit
locked provider integration and explicit user contract.

### 5. How does Sentinel prevent provider-owned authority?

Provider events can create only voice data objects:

```text
PartialTranscript
FinalTranscript
RealtimeSpeechEvent
VoiceCommandEnvelope
VoiceNotification
```

They cannot call tools, create authority, unlock credentials, or dispatch
organs. Any provider tool-call-like event is wrapped as
`RealtimeSpeechToolCallEnvelope` and blocked from execution until Sentinel
validates it as a proposal through MissionKernel and authority gates.

### 6. How does voice input become a VoiceCommandEnvelope instead of direct execution?

Audio and transcript data produce a hash-bound `VoiceCommandEnvelope` with:

- transcript hash and safe excerpt;
- command risk profile;
- intent candidates;
- source refs;
- confirmation policy;
- data-not-authority fields.

The envelope can produce a proposal/checkpoint. It cannot execute.

### 7. How are barge-in and interruption modeled?

`BargeInEvent` records user speech or kill-word overlap while Sentinel output
is playing. `InterruptionDecision` records whether playback should stop, pause,
or continue. In V1, fake/injected events interrupt a `StreamingSpeechOutput`
and persist safe metadata only.

### 8. How is turn detection modeled?

`TurnDetectionPolicy` defines VAD-only, STT endpointing, semantic, realtime
provider, or manual modes. `TurnDetectionResult` records speech start/end,
endpointing confidence, transcript refs, and whether a final transcript is
ready to create a command envelope.

### 9. How are voice modes separated?

```text
DISABLED = no voice input/output.
PUSH_TO_TALK = user-triggered input only.
WAKE_WORD = wake/kill word detection under explicit policy.
SESSION_VOICE = continuous voice conversation in an active session.
AMBIENT_LISTENER = limited mission/wake/kill/status listening under explicit policy.
AMBIENT_OPERATOR = Sentinel may speak scoped mission alerts.
FULL_VOICE_COPILOT = future modeled mode, not production-ready in V1.
```

Mode changes are state transitions with telemetry and replay. Ambient modes
require explicit `AmbientVoicePolicy`.

### 10. How does Voice connect to existing Sentinel systems?

Voice is a transport over:

```text
LLM cockpit
UserModelContract / LocalModelRouter
MissionKernel / MissionRunStore
MissionDaemonRuntime
WorkerFleetRuntime
GovernedSkillFabric
ModelAmplificationHarness
DesktopSidecar / LiveDesktopBackend
RealChannelAdapters
PersistentSemanticMemory
TelemetryKernel
PowerRuntime / AgentRuntime bridge
MissionAuthorityEnvelope
Gate
receipts
FinalGate
replay
```

Voice never bypasses those systems. Voice-to-desktop, voice-to-channel,
voice-to-daemon, voice-to-worker, and voice-to-skill surfaces are proposals or
notifications, not direct execution.

### 11. What is stored and what is not stored?

Stored by default:

- audio chunk hashes and refs;
- transcript hash;
- redacted transcript excerpt;
- VAD/turn/barge-in/kill-word metadata;
- command envelope safe metadata;
- confirmation result metadata;
- receipt refs;
- FinalGate refs;
- telemetry refs;
- sanitized memory refs.

Not stored by default:

- raw audio;
- raw full transcript;
- speaker biometrics;
- provider keys;
- raw prompts;
- raw provider responses;
- raw reasoning;
- credentials, tokens, seed phrases, recovery codes, or private conversation
  text.

### 12. How do we avoid raw audio/transcript/secret persistence?

All voice models use redacted safe serialization. Raw audio bytes and raw full
transcripts are excluded from persistence fields. Text is redacted before
safe dumps. Secret-like payloads are rejected in command/confirmation surfaces.
Replay stores hashes and safe refs only.

### 13. What is V1, what is explicitly not V1, and what is future?

V1:

- Sentinel-owned voice runtime models and fake/injected backend;
- provider descriptors for local/API/realtime speech systems;
- VAD, turn detection, partial/final transcript lifecycle;
- barge-in, interruption, kill-word behavior;
- VoiceCommandEnvelope and confirmation evidence model;
- ambient policy and notifications;
- voice-to-desktop proposal contracts;
- receipts, FinalGate, telemetry, replay.

Not V1:

- live OpenAI/Gemini/LiveKit/Pipecat provider integration;
- voice cloning;
- speaker biometric authentication;
- raw audio recorder;
- hidden always-on listener;
- provider-native tool execution;
- provider fallback/AUTO;
- credential vault;
- account/payment/security/device power.

Future:

- real opt-in microphone/speaker adapters;
- approved local STT/TTS backends;
- approved realtime speech provider sessions;
- full app/tray voice UX;
- durable credential vault integration after the next phase;
- voice product gauntlets across desktop, channel, daemon, and long missions.

## Architecture Decision

V1 implements a Sentinel-owned cascaded runtime:

```text
AudioInputAdapter / fake event source
-> AudioFrameRef / AudioChunkRef
-> VoiceActivityEvent
-> TurnDetectionResult
-> PartialTranscript / FinalTranscript
-> VoiceCommandEnvelope
-> VoiceSafetyScanResult
-> VoiceConfirmationRequest if needed
-> MissionKernel proposal/checkpoint metadata
-> existing authority/runtime path in future integration
-> VoiceOperatorResponse / VoiceNotification
-> TextToSpeechResult / StreamingSpeechOutput fake output
-> VoiceReceipt / VoiceFinalGateCertificate
-> TelemetryKernel
-> VoiceReplayView
```

Native speech-to-speech provider sessions are modeled as
`RealtimeSpeechSessionDescriptor` and `RealtimeSpeechEvent`, but they are not
allowed to execute tools or own session authority.

## Sentinel Implementation Plan

### Runtime files

```text
sentinel-control/services/sentinel-core/sentinel/operator/voice_models.py
sentinel-control/services/sentinel-core/sentinel/operator/voice_runtime.py
sentinel-control/services/sentinel-core/sentinel/operator/voice_replay.py
```

### Test file

```text
sentinel-control/services/sentinel-core/tests/test_realtime_voice_ambient_operator_v1.py
```

### Existing files to extend

```text
sentinel-control/services/sentinel-core/sentinel/operator/__init__.py
sentinel-control/services/sentinel-core/sentinel/telemetry/models.py
sentinel-control/services/sentinel-core/sentinel/telemetry/kernel.py
README.md
sentinel-control/docs/CURRENT_STATE_LOCK.md
sentinel-control/docs/roadmaps/SENTINEL_MASTER_ROADMAP_TO_COMPLETION.md
sentinel-control/docs/roadmaps/SENTINEL_POWER_KERNEL_AND_ACTUATOR_FABRIC_ROADMAP.md
```

## Authority And Privacy Boundaries

Voice is data:

```text
data_not_authority = true
authority_effect = none
can_grant_authority = false
can_execute = false
```

Hard blocks:

- no voice-created or voice-expanded MissionAuthorityEnvelope;
- no provider-owned tool authority;
- no direct organ calls;
- no hidden listener/recorder;
- no raw audio persistence by default;
- no raw full transcript persistence by default;
- no provider key persistence;
- no fallback/AUTO;
- no confirmation-as-authority;
- no wake-word-as-authority;
- no replay audio/action execution.

## Honest V1 Maturity

```text
voice runtime = local same-process foundation
audio backend = fake/injected only
provider support = descriptors/contracts only
ambient listening = policy-modeled only, no hidden recording
voice output = fake/injected streaming output records
speech-to-speech provider sessions = descriptor only
production microphone/speaker/runtime integration = NOT_STARTED
voice cloning / speaker auth = NOT_STARTED
credential vault = NOT_STARTED / next
```

This research/design pass is complete enough to proceed to TDD implementation.
