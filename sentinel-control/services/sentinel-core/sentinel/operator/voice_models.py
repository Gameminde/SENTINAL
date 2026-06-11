from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority, reject_operator_control_payload
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import scan_forbidden_payload_categorized


def voice_utc_now() -> datetime:
    return datetime.now(UTC)


class VoiceDataModel(SentinelModel):
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _voice_data_is_not_authority(self) -> VoiceDataModel:
        assert_data_not_authority(
            context=self.__class__.__name__,
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return redact_operator_value(self.model_dump(mode="json"))


class VoiceMode(StrEnum):
    DISABLED = "disabled"
    PUSH_TO_TALK = "push_to_talk"
    WAKE_WORD = "wake_word"
    SESSION_VOICE = "session_voice"
    AMBIENT_LISTENER = "ambient_listener"
    AMBIENT_OPERATOR = "ambient_operator"
    FULL_VOICE_COPILOT = "full_voice_copilot"


class VoiceControlMode(StrEnum):
    SENTINEL_OWNED_PIPELINE = "sentinel_owned_pipeline"
    REALTIME_PROVIDER_DESCRIPTOR = "realtime_provider_descriptor"


class VoiceProviderKind(StrEnum):
    LOCAL_STT = "local_stt"
    LOCAL_TTS = "local_tts"
    API_STT = "api_stt"
    API_TTS = "api_tts"
    REALTIME_SPEECH_PROVIDER = "realtime_speech_provider"
    OPENAI_REALTIME_STYLE_DESCRIPTOR = "openai_realtime_style_descriptor"
    GEMINI_LIVE_STYLE_DESCRIPTOR = "gemini_live_style_descriptor"
    LIVEKIT_STYLE_TRANSPORT_DESCRIPTOR = "livekit_style_transport_descriptor"
    PIPECAT_STYLE_PIPELINE_DESCRIPTOR = "pipecat_style_pipeline_descriptor"
    FAKE_INJECTED = "fake_injected"


class AudioTransportKind(StrEnum):
    CONTRACT_ONLY = "contract_only"
    FAKE_BACKEND = "fake_backend"
    INJECTED_TRANSPORT = "injected_transport"
    LOCAL_AUDIO_DESCRIPTOR = "local_audio_descriptor"
    REALTIME_PROVIDER_DESCRIPTOR = "realtime_provider_descriptor"


class AudioInputAdapter(VoiceDataModel):
    adapter_id: str = Field(default_factory=lambda: new_id("voice_audio_input"))
    transport: AudioTransportKind = AudioTransportKind.INJECTED_TRANSPORT
    descriptor_only: bool = True
    microphone_capture_allowed: bool = False

    @model_validator(mode="after")
    def _input_adapter_is_descriptor(self) -> AudioInputAdapter:
        if not self.descriptor_only or self.microphone_capture_allowed:
            raise ValueError("voice input adapter is descriptor/fake-only in v1")
        return self


class AudioOutputAdapter(VoiceDataModel):
    adapter_id: str = Field(default_factory=lambda: new_id("voice_audio_output"))
    transport: AudioTransportKind = AudioTransportKind.INJECTED_TRANSPORT
    descriptor_only: bool = True
    speaker_playback_allowed: bool = False

    @model_validator(mode="after")
    def _output_adapter_is_descriptor(self) -> AudioOutputAdapter:
        if not self.descriptor_only or self.speaker_playback_allowed:
            raise ValueError("voice output adapter is descriptor/fake-only in v1")
        return self


class TurnDetectionMode(StrEnum):
    MANUAL = "manual"
    VAD_ONLY = "vad_only"
    STT_ENDPOINTING = "stt_endpointing"
    VAD_AND_STT_ENDPOINTING = "vad_and_stt_endpointing"
    SEMANTIC = "semantic"
    REALTIME_PROVIDER_DESCRIPTOR = "realtime_provider_descriptor"


class SpeechPlaybackState(StrEnum):
    QUEUED = "queued"
    PLAYING = "playing"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class VoiceFinalGateDecision(StrEnum):
    SESSION_STARTED = "session_started"
    COMMAND_ENVELOPED = "command_enveloped"
    CONFIRMATION_RECORDED = "confirmation_recorded"
    NOTIFICATION_CREATED = "notification_created"
    OUTPUT_COMPLETED = "output_completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    KILLED = "killed"


class VoiceProviderContract(VoiceDataModel):
    provider_id: str
    provider_kind: VoiceProviderKind
    display_name: str
    descriptor_only: bool = True
    live_provider_call_allowed: bool = False
    provider_key: str | None = Field(default=None, exclude=True, repr=False)
    endpoint_ref_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    contract_hash: str = ""

    @model_validator(mode="after")
    def _provider_contract_is_descriptor(self) -> VoiceProviderContract:
        if self.provider_key:
            raise ValueError("voice provider key persistence is blocked; provider key must not be stored")
        if not self.descriptor_only or self.live_provider_call_allowed:
            raise ValueError("voice providers are descriptor-only in v1")
        if not self.provider_id.strip():
            raise ValueError("voice provider id is required")
        self.display_name = redact_operator_text(self.display_name)
        self.metadata = _sanitize_voice_payload(self.metadata, context="voice_provider_contract")
        return self

    def with_hash(self) -> VoiceProviderContract:
        payload = self.safe_model_dump()
        payload["contract_hash"] = ""
        return self.model_copy(update={"contract_hash": stable_hash(payload)})


class VoiceModelContract(VoiceDataModel):
    model_contract_id: str = Field(default_factory=lambda: new_id("voice_model_contract"))
    provider_id: str
    model_id: str | None = None
    descriptor_only: bool = True
    contract_hash: str = ""

    def with_hash(self) -> VoiceModelContract:
        payload = self.safe_model_dump()
        payload["contract_hash"] = ""
        return self.model_copy(update={"contract_hash": stable_hash(payload)})


class SpeechToTextContract(VoiceDataModel):
    provider_id: str
    descriptor_only: bool = True
    streaming: bool = True
    supports_partials: bool = True
    supports_endpointing: bool = True
    contract_hash: str = ""

    @model_validator(mode="after")
    def _stt_is_descriptor(self) -> SpeechToTextContract:
        if not self.descriptor_only:
            raise ValueError("voice STT contract is descriptor-only in v1")
        return self


class TextToSpeechContract(VoiceDataModel):
    provider_id: str
    descriptor_only: bool = True
    streaming: bool = True
    voice_clone_allowed: bool = False
    contract_hash: str = ""

    @model_validator(mode="after")
    def _tts_is_safe(self) -> TextToSpeechContract:
        if not self.descriptor_only:
            raise ValueError("voice TTS contract is descriptor-only in v1")
        if self.voice_clone_allowed:
            raise ValueError("voice cloning is not allowed in v1")
        return self


class VoicePrivacyPolicy(VoiceDataModel):
    persist_raw_audio: bool = False
    persist_full_transcript: bool = False
    persist_speaker_biometrics: bool = False
    persist_provider_response: bool = False
    retention_policy: str = "hash_and_redacted_excerpt_only"
    operator_visible: bool = True

    @model_validator(mode="after")
    def _privacy_defaults_are_safe(self) -> VoicePrivacyPolicy:
        if self.persist_raw_audio:
            raise ValueError("raw audio persistence is blocked by default in voice v1")
        if self.persist_full_transcript:
            raise ValueError("raw full transcript persistence is blocked by default in voice v1")
        if self.persist_speaker_biometrics:
            raise ValueError("speaker biometric persistence is blocked in voice v1")
        if self.persist_provider_response:
            raise ValueError("raw provider response persistence is blocked in voice v1")
        self.retention_policy = redact_operator_text(self.retention_policy)
        return self


class AmbientVoicePolicy(VoiceDataModel):
    ambient_listener_allowed: bool = False
    ambient_operator_allowed: bool = False
    allowed_proactive_categories: list[str] = Field(default_factory=lambda: ["mission_blocked", "approval_needed", "dangerous_action_blocked"])
    blocked_categories: list[str] = Field(default_factory=lambda: ["private_conversation", "credential_capture", "payment", "account_creation", "security_testing"])
    quiet_hours: list[str] = Field(default_factory=list)
    mission_only_speech: bool = True
    privacy_mode: str = "hash_and_redacted_excerpt_only"
    retention_policy: str = "hash_and_redacted_excerpt_only"

    @model_validator(mode="after")
    def _ambient_policy_is_safe(self) -> AmbientVoicePolicy:
        self.allowed_proactive_categories = [_safe_label(item) for item in self.allowed_proactive_categories]
        self.blocked_categories = [_safe_label(item) for item in self.blocked_categories]
        self.quiet_hours = [redact_operator_text(item) for item in self.quiet_hours]
        self.privacy_mode = redact_operator_text(self.privacy_mode)
        self.retention_policy = redact_operator_text(self.retention_policy)
        return self


class TurnDetectionPolicy(VoiceDataModel):
    mode: TurnDetectionMode = TurnDetectionMode.VAD_AND_STT_ENDPOINTING
    endpointing_ms: int = Field(default=600, ge=0)
    semantic_confidence_threshold: float = Field(default=0.7, ge=0, le=1)
    require_final_transcript: bool = True


class BargeInPolicy(VoiceDataModel):
    enabled: bool = True
    interrupt_output: bool = True
    min_confidence: float = Field(default=0.1, ge=0, le=1)


class VoiceConfirmationPolicy(VoiceDataModel):
    require_confirmation_for_dangerous: bool = True
    allowed_confirmation_sources: list[str] = Field(default_factory=lambda: ["operator", "manual_operator"])

    @model_validator(mode="after")
    def _confirmation_sources_are_operator(self) -> VoiceConfirmationPolicy:
        allowed = {"operator", "manual_operator", "operator_policy"}
        self.allowed_confirmation_sources = [source for source in self.allowed_confirmation_sources if source in allowed]
        if not self.allowed_confirmation_sources:
            raise ValueError("voice confirmation requires operator source")
        return self


class VoiceKillWordPolicy(VoiceDataModel):
    kill_words: list[str] = Field(default_factory=lambda: ["stop", "cancel", "kill", "stop sentinel"])
    interrupt_output: bool = True

    @model_validator(mode="after")
    def _kill_words_are_safe(self) -> VoiceKillWordPolicy:
        self.kill_words = [redact_operator_text(item).strip().lower() for item in self.kill_words if item.strip()]
        return self


class VoiceRuntimeConfig(VoiceDataModel):
    config_id: str
    default_mode: VoiceMode = VoiceMode.PUSH_TO_TALK
    allowed_modes: list[VoiceMode] = Field(default_factory=lambda: [VoiceMode.PUSH_TO_TALK])
    control_mode: VoiceControlMode = VoiceControlMode.SENTINEL_OWNED_PIPELINE
    provider_contracts: list[VoiceProviderContract] = Field(default_factory=list)
    voice_model_contract: VoiceModelContract | None = None
    stt_contract: SpeechToTextContract | None = None
    tts_contract: TextToSpeechContract | None = None
    privacy_policy: VoicePrivacyPolicy = Field(default_factory=VoicePrivacyPolicy)
    turn_detection_policy: TurnDetectionPolicy = Field(default_factory=TurnDetectionPolicy)
    barge_in_policy: BargeInPolicy = Field(default_factory=BargeInPolicy)
    confirmation_policy: VoiceConfirmationPolicy = Field(default_factory=VoiceConfirmationPolicy)
    ambient_policy: AmbientVoicePolicy = Field(default_factory=AmbientVoicePolicy)
    kill_word_policy: VoiceKillWordPolicy = Field(default_factory=VoiceKillWordPolicy)
    audio_transport: AudioTransportKind = AudioTransportKind.INJECTED_TRANSPORT
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=voice_utc_now)
    config_hash: str = ""

    @model_validator(mode="after")
    def _config_is_bounded(self) -> VoiceRuntimeConfig:
        if self.default_mode not in self.allowed_modes:
            raise ValueError("default voice mode must be explicitly allowed")
        if not self.config_id.strip():
            raise ValueError("voice config id is required")
        self.metadata = _sanitize_voice_payload(self.metadata, context="voice_runtime_config")
        return self

    def with_hash(self) -> VoiceRuntimeConfig:
        payload = self.safe_model_dump()
        payload["config_hash"] = ""
        return self.model_copy(update={"config_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["config_hash"]
        payload["config_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class VoiceSession(VoiceDataModel):
    session_id: str = Field(default_factory=lambda: new_id("voice_session"))
    config_id: str
    mission_id: str
    mode: VoiceMode
    state: str = "running"
    started_at: datetime = Field(default_factory=voice_utc_now)
    completed_at: datetime | None = None
    session_hash: str = ""

    def with_hash(self) -> VoiceSession:
        payload = self.safe_model_dump()
        payload["session_hash"] = ""
        return self.model_copy(update={"session_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["session_hash"]
        payload["session_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class AudioFrameRef(VoiceDataModel):
    frame_id: str = Field(default_factory=lambda: new_id("voice_audio_frame"))
    frame_hash: str
    byte_count: int = Field(default=0, ge=0)


class AudioStreamRef(VoiceDataModel):
    stream_id: str = Field(default_factory=lambda: new_id("voice_audio_stream"))
    transport: AudioTransportKind = AudioTransportKind.INJECTED_TRANSPORT
    stream_hash: str = ""


class AudioChunkRef(VoiceDataModel):
    chunk_id: str = Field(default_factory=lambda: new_id("voice_audio_chunk"))
    session_id: str
    audio_hash: str
    byte_count: int = Field(default=0, ge=0)
    raw_audio: bytes | None = Field(default=None, exclude=True, repr=False)
    raw_audio_persisted: bool = False
    created_at: datetime = Field(default_factory=voice_utc_now)
    chunk_hash: str = ""

    @model_validator(mode="after")
    def _raw_audio_blocked(self) -> AudioChunkRef:
        if self.raw_audio_persisted:
            raise ValueError("raw audio persistence is blocked in voice v1")
        return self

    @classmethod
    def from_bytes(cls, *, session_id: str, raw_audio: bytes) -> AudioChunkRef:
        return cls(
            session_id=session_id,
            audio_hash=hashlib.sha256(raw_audio).hexdigest(),
            byte_count=len(raw_audio),
            raw_audio=raw_audio,
        ).with_hash()

    def with_hash(self) -> AudioChunkRef:
        payload = self.safe_model_dump()
        payload["chunk_hash"] = ""
        return self.model_copy(update={"chunk_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["chunk_hash"]
        payload["chunk_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class VoiceActivityDetector(VoiceDataModel):
    detector_id: str = Field(default_factory=lambda: new_id("voice_activity_detector"))
    provider_kind: VoiceProviderKind = VoiceProviderKind.FAKE_INJECTED
    descriptor_only: bool = True


class VoiceActivityEvent(VoiceDataModel):
    activity_event_id: str = Field(default_factory=lambda: new_id("voice_activity"))
    session_id: str
    event_type: str
    confidence: float = Field(default=1.0, ge=0, le=1)
    audio_chunk_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=voice_utc_now)
    event_hash: str = ""

    @model_validator(mode="after")
    def _activity_event_is_safe(self) -> VoiceActivityEvent:
        self.event_type = _safe_label(self.event_type)
        self.audio_chunk_refs = sanitize_operator_refs(self.audio_chunk_refs)
        return self

    def with_hash(self) -> VoiceActivityEvent:
        payload = self.safe_model_dump()
        payload["event_hash"] = ""
        return self.model_copy(update={"event_hash": stable_hash(payload)})


class StreamingTranscriptEvent(VoiceDataModel):
    transcript_event_id: str = Field(default_factory=lambda: new_id("voice_transcript"))
    session_id: str
    transcript_hash: str
    safe_excerpt: str = ""
    audio_chunk_refs: list[str] = Field(default_factory=list)
    full_transcript_persisted: bool = False
    created_at: datetime = Field(default_factory=voice_utc_now)
    event_hash: str = ""

    @model_validator(mode="after")
    def _transcript_event_is_safe(self) -> StreamingTranscriptEvent:
        if self.full_transcript_persisted:
            raise ValueError("raw full transcript persistence is blocked in voice v1")
        self.safe_excerpt = redact_operator_text(self.safe_excerpt)
        self.audio_chunk_refs = sanitize_operator_refs(self.audio_chunk_refs)
        return self

    def with_hash(self) -> StreamingTranscriptEvent:
        payload = self.safe_model_dump()
        payload["event_hash"] = ""
        return self.model_copy(update={"event_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["event_hash"]
        payload["event_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class PartialTranscript(StreamingTranscriptEvent):
    text: str = Field(default="", exclude=True, repr=False)
    is_final: bool = False


class FinalTranscript(StreamingTranscriptEvent):
    text: str = Field(default="", exclude=True, repr=False)
    partial_refs: list[str] = Field(default_factory=list)
    is_final: bool = True

    @model_validator(mode="after")
    def _partial_refs_are_safe(self) -> FinalTranscript:
        self.partial_refs = sanitize_operator_refs(self.partial_refs)
        return self


class EndpointingDecision(VoiceDataModel):
    decision_id: str = Field(default_factory=lambda: new_id("voice_endpointing"))
    final_transcript_ready: bool = False
    confidence: float = Field(default=1.0, ge=0, le=1)
    reason: str = "stt_endpointing"
    decision_hash: str = ""


class TurnDetectionResult(VoiceDataModel):
    turn_result_id: str = Field(default_factory=lambda: new_id("voice_turn"))
    session_id: str
    policy: TurnDetectionPolicy
    endpointing_decision: EndpointingDecision
    final_transcript_ref: str | None = None
    result_hash: str = ""

    def with_hash(self) -> TurnDetectionResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})


class SpeechToTextRequest(VoiceDataModel):
    request_id: str = Field(default_factory=lambda: new_id("voice_stt_request"))
    audio_chunk_refs: list[str] = Field(default_factory=list)


class SpeechToTextResult(VoiceDataModel):
    result_id: str = Field(default_factory=lambda: new_id("voice_stt_result"))
    partial_refs: list[str] = Field(default_factory=list)
    final_ref: str | None = None


class TextToSpeechRequest(VoiceDataModel):
    request_id: str = Field(default_factory=lambda: new_id("voice_tts_request"))
    text: str = Field(default="", exclude=True, repr=False)
    text_hash: str
    safe_excerpt: str = ""


class TextToSpeechResult(VoiceDataModel):
    result_id: str = Field(default_factory=lambda: new_id("voice_tts_result"))
    request_id: str
    output_ref_hash: str
    safe_summary: str = "Voice TTS output prepared through fake/injected backend."


class StreamingSpeechOutput(VoiceDataModel):
    output_id: str = Field(default_factory=lambda: new_id("voice_output"))
    session_id: str
    text_hash: str
    safe_excerpt: str = ""
    playback_state: SpeechPlaybackState = SpeechPlaybackState.QUEUED
    tts_result: TextToSpeechResult | None = None
    started_at: datetime = Field(default_factory=voice_utc_now)
    completed_at: datetime | None = None
    output_hash: str = ""

    @model_validator(mode="after")
    def _output_safe(self) -> StreamingSpeechOutput:
        self.safe_excerpt = redact_operator_text(self.safe_excerpt)
        return self

    def with_hash(self) -> StreamingSpeechOutput:
        payload = self.safe_model_dump()
        payload["output_hash"] = ""
        return self.model_copy(update={"output_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["output_hash"]
        payload["output_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class RealtimeSpeechSessionContract(VoiceDataModel):
    contract_id: str = Field(default_factory=lambda: new_id("realtime_speech_contract"))
    provider_id: str
    descriptor_only: bool = True
    supports_tool_call_events: bool = True


class RealtimeSpeechSessionDescriptor(VoiceDataModel):
    descriptor_id: str = Field(default_factory=lambda: new_id("realtime_speech_descriptor"))
    provider_kind: VoiceProviderKind = VoiceProviderKind.REALTIME_SPEECH_PROVIDER
    contract: RealtimeSpeechSessionContract
    live_call_allowed: bool = False

    @model_validator(mode="after")
    def _no_live_call(self) -> RealtimeSpeechSessionDescriptor:
        if self.live_call_allowed:
            raise ValueError("live realtime voice provider calls are not allowed in v1")
        return self


class RealtimeSpeechEvent(VoiceDataModel):
    event_id: str = Field(default_factory=lambda: new_id("realtime_speech_event"))
    provider_event_type: str
    safe_summary: str
    provider_payload_hash: str


class RealtimeSpeechToolCallEnvelope(VoiceDataModel):
    envelope_id: str = Field(default_factory=lambda: new_id("realtime_speech_tool_call"))
    provider_id: str
    tool_name_hash: str
    blocked: bool = True
    safe_reason: str = "Provider-native tool execution is blocked; Sentinel must validate proposals."


class VoiceIntentCandidate(VoiceDataModel):
    intent_id: str = Field(default_factory=lambda: new_id("voice_intent"))
    kind: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    proposal_target: str | None = None


class VoiceCommandRiskProfile(VoiceDataModel):
    risk_lane: str = "low"
    requires_checkpoint: bool = False
    requires_confirmation: bool = False
    dangerous_terms: list[str] = Field(default_factory=list)


class VoiceSafetyScanResult(VoiceDataModel):
    scan_id: str = Field(default_factory=lambda: new_id("voice_safety_scan"))
    passed: bool = True
    requires_confirmation: bool = False
    reasons: list[str] = Field(default_factory=list)
    scan_hash: str = ""


class VoiceReceipt(VoiceDataModel):
    receipt_id: str = Field(default_factory=lambda: new_id("voice_receipt"))
    mission_id: str
    session_id: str
    event_type: str
    transcript_hash: str | None = None
    command_id: str | None = None
    policy_hash: str | None = None
    status: str = "recorded"
    telemetry_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=voice_utc_now)
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _receipt_is_safe(self) -> VoiceReceipt:
        self.event_type = _safe_label(self.event_type)
        self.status = _safe_label(self.status)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        return self

    def with_hash(self) -> VoiceReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["receipt_hash"]
        payload["receipt_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class VoiceFinalGateCertificate(VoiceDataModel):
    certificate_id: str = Field(default_factory=lambda: new_id("voice_finalgate"))
    mission_id: str
    session_id: str
    decision: VoiceFinalGateDecision
    passed: bool = True
    receipt_ref: str | None = None
    safe_summary: str = "Voice FinalGate certificate."
    created_at: datetime = Field(default_factory=voice_utc_now)
    certificate_hash: str = ""

    @model_validator(mode="after")
    def _certificate_is_safe(self) -> VoiceFinalGateCertificate:
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> VoiceFinalGateCertificate:
        payload = self.safe_model_dump()
        payload["certificate_hash"] = ""
        return self.model_copy(update={"certificate_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["certificate_hash"]
        payload["certificate_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class VoiceCommandEnvelope(VoiceDataModel):
    command_id: str = Field(default_factory=lambda: new_id("voice_command"))
    session_id: str
    mission_id: str
    final_transcript_ref: str
    transcript_hash: str
    safe_excerpt: str
    intent_candidates: list[VoiceIntentCandidate] = Field(default_factory=list)
    risk_profile: VoiceCommandRiskProfile = Field(default_factory=VoiceCommandRiskProfile)
    safety_scan: VoiceSafetyScanResult = Field(default_factory=VoiceSafetyScanResult)
    voice_receipt: VoiceReceipt | None = None
    finalgate_certificate: VoiceFinalGateCertificate | None = None
    created_at: datetime = Field(default_factory=voice_utc_now)
    command_hash: str = ""

    @model_validator(mode="after")
    def _command_safe(self) -> VoiceCommandEnvelope:
        self.safe_excerpt = redact_operator_text(self.safe_excerpt)
        return self

    def with_hash(self) -> VoiceCommandEnvelope:
        payload = self.safe_model_dump()
        payload["command_hash"] = ""
        return self.model_copy(update={"command_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["command_hash"]
        payload["command_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)


class VoiceConfirmationRequest(VoiceDataModel):
    confirmation_id: str = Field(default_factory=lambda: new_id("voice_confirm_req"))
    session_id: str
    command_id: str
    policy: VoiceConfirmationPolicy
    voice_confirmation_is_authority: bool = False
    request_hash: str = ""

    def with_hash(self) -> VoiceConfirmationRequest:
        payload = self.safe_model_dump()
        payload["request_hash"] = ""
        return self.model_copy(update={"request_hash": stable_hash(payload)})


class VoiceConfirmationResult(VoiceDataModel):
    result_id: str = Field(default_factory=lambda: new_id("voice_confirm_result"))
    confirmation_id: str
    approved: bool
    spoken_text_hash: str
    safe_excerpt: str
    voice_confirmation_is_authority: bool = False
    result_hash: str = ""

    def with_hash(self) -> VoiceConfirmationResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})


class BargeInEvent(VoiceDataModel):
    barge_in_event_id: str = Field(default_factory=lambda: new_id("voice_barge_in"))
    session_id: str
    output_id: str
    reason: str = "operator_spoke"
    event_hash: str = ""


class InterruptionDecision(VoiceDataModel):
    decision_id: str = Field(default_factory=lambda: new_id("voice_interruption"))
    session_id: str
    output_id: str
    barge_in_event: BargeInEvent
    decision: str = "stop_output"
    interrupted: bool = True
    decision_hash: str = ""

    def with_hash(self) -> InterruptionDecision:
        payload = self.safe_model_dump()
        payload["decision_hash"] = ""
        return self.model_copy(update={"decision_hash": stable_hash(payload)})


class VoiceKillWordEvent(VoiceDataModel):
    kill_event_id: str = Field(default_factory=lambda: new_id("voice_kill_word"))
    session_id: str
    matched: bool
    kill_word_hash: str | None = None
    raw_text_persisted: bool = False
    event_hash: str = ""

    @model_validator(mode="after")
    def _no_raw_text(self) -> VoiceKillWordEvent:
        if self.raw_text_persisted:
            raise ValueError("raw kill-word text persistence is blocked")
        return self

    def with_hash(self) -> VoiceKillWordEvent:
        payload = self.safe_model_dump()
        payload["event_hash"] = ""
        return self.model_copy(update={"event_hash": stable_hash(payload)})


class VoiceNotification(VoiceDataModel):
    notification_id: str = Field(default_factory=lambda: new_id("voice_notification"))
    session_id: str
    category: str
    safe_summary: str
    notification_hash: str = ""

    @model_validator(mode="after")
    def _notification_safe(self) -> VoiceNotification:
        self.category = _safe_label(self.category)
        self.safe_summary = redact_operator_text(self.safe_summary)
        return self

    def with_hash(self) -> VoiceNotification:
        payload = self.safe_model_dump()
        payload["notification_hash"] = ""
        return self.model_copy(update={"notification_hash": stable_hash(payload)})


class AmbientVoiceEvent(VoiceNotification):
    pass


class VoiceOperatorPrompt(VoiceDataModel):
    prompt_id: str = Field(default_factory=lambda: new_id("voice_operator_prompt"))
    safe_summary: str
    prompt_hash: str


class VoiceOperatorResponse(VoiceDataModel):
    response_id: str = Field(default_factory=lambda: new_id("voice_operator_response"))
    safe_summary: str
    response_hash: str


class VoiceDesktopActionProposal(VoiceDataModel):
    proposal_id: str = Field(default_factory=lambda: new_id("voice_desktop_proposal"))
    session_id: str
    command_id: str
    desktop_target_ref: str
    proposal_only: bool = True
    executed: bool = False
    requires_desktop_authority: bool = True
    proposal_hash: str = ""

    def with_hash(self) -> VoiceDesktopActionProposal:
        payload = self.safe_model_dump()
        payload["proposal_hash"] = ""
        return self.model_copy(update={"proposal_hash": stable_hash(payload)})


class VoiceTelemetrySummary(VoiceDataModel):
    session_count: int = 0
    turn_count: int = 0
    command_count: int = 0
    barge_in_count: int = 0


class VoiceReplayView(VoiceDataModel):
    mission_id: str
    configs: list[VoiceRuntimeConfig] = Field(default_factory=list)
    sessions: list[VoiceSession] = Field(default_factory=list)
    audio_chunks: list[AudioChunkRef] = Field(default_factory=list)
    activity_events: list[VoiceActivityEvent] = Field(default_factory=list)
    partial_transcripts: list[PartialTranscript] = Field(default_factory=list)
    final_transcripts: list[FinalTranscript] = Field(default_factory=list)
    turn_results: list[TurnDetectionResult] = Field(default_factory=list)
    command_envelopes: list[VoiceCommandEnvelope] = Field(default_factory=list)
    confirmations: list[VoiceConfirmationResult] = Field(default_factory=list)
    notifications: list[VoiceNotification] = Field(default_factory=list)
    outputs: list[StreamingSpeechOutput] = Field(default_factory=list)
    interruption_decisions: list[InterruptionDecision] = Field(default_factory=list)
    kill_word_events: list[VoiceKillWordEvent] = Field(default_factory=list)
    desktop_proposals: list[VoiceDesktopActionProposal] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    tampered: bool = False
    played_audio: bool = False
    recorded_microphone: bool = False
    called_provider: bool = False
    executed_actions: bool = False


def build_partial_transcript(*, session_id: str, text: str, audio_chunk_refs: list[str] | None = None) -> PartialTranscript:
    return PartialTranscript(
        session_id=session_id,
        text=text,
        transcript_hash=text_hash(text),
        safe_excerpt=_safe_excerpt(text),
        audio_chunk_refs=audio_chunk_refs or [],
    ).with_hash()


def build_final_transcript(
    *,
    session_id: str,
    text: str,
    audio_chunk_refs: list[str] | None = None,
    partial_refs: list[str] | None = None,
) -> FinalTranscript:
    return FinalTranscript(
        session_id=session_id,
        text=text,
        transcript_hash=text_hash(text),
        safe_excerpt=_safe_excerpt(text),
        audio_chunk_refs=audio_chunk_refs or [],
        partial_refs=partial_refs or [],
    ).with_hash()


def scan_voice_text(text: str) -> tuple[VoiceCommandRiskProfile, VoiceSafetyScanResult, list[VoiceIntentCandidate]]:
    lower = text.lower()
    dangerous_terms = [
        term
        for term in ("payment", "pay", "trading", "trade", "credential", "password", "account", "security", "delete", "send", "click")
        if term in lower
    ]
    scanner_result = scan_forbidden_payload_categorized({"voice_text": text})
    scanner_hit_paths = sorted({path for paths in scanner_result.values() for path in paths})
    requires = bool(dangerous_terms or scanner_hit_paths)
    risk = VoiceCommandRiskProfile(
        risk_lane="elevated" if requires else "low",
        requires_checkpoint=requires,
        requires_confirmation=requires,
        dangerous_terms=sorted(set(dangerous_terms)),
    )
    scan = VoiceSafetyScanResult(
        passed=not scanner_hit_paths,
        requires_confirmation=requires,
        reasons=sorted({*scanner_hit_paths, *dangerous_terms}) if requires else ["voice_command_clear"],
    )
    intents = [
        VoiceIntentCandidate(
            kind=_classify_intent(lower),
            confidence=0.8,
            proposal_target="desktop" if any(term in lower for term in ("click", "button", "monitor", "temperature", "pc")) else "mission",
        )
    ]
    return risk, scan, intents


def _classify_intent(lower: str) -> str:
    if any(term in lower for term in ("click", "button", "desktop", "monitor", "temperature", "cpu", "gpu")):
        return "desktop_proposal"
    if any(term in lower for term in ("pause", "resume", "kill", "stop", "status")):
        return "mission_control_proposal"
    if any(term in lower for term in ("send", "message", "email", "channel")):
        return "channel_proposal"
    return "operator_request"


def _safe_excerpt(text: str, limit: int = 180) -> str:
    return redact_operator_text(text[:limit])


def _safe_label(value: str | None) -> str:
    return redact_operator_text(str(value or "unknown")).strip().lower().replace(" ", "_")[:96]


def _sanitize_voice_payload(value: Any, *, context: str) -> Any:
    sanitized = redact_operator_value(value)
    reject_operator_control_payload(sanitized, context=context)
    return sanitized
