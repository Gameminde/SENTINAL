from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.voice_models import (
    AmbientVoicePolicy,
    AudioChunkRef,
    BargeInEvent,
    BargeInPolicy,
    EndpointingDecision,
    FinalTranscript,
    InterruptionDecision,
    PartialTranscript,
    SpeechPlaybackState,
    StreamingSpeechOutput,
    TextToSpeechRequest,
    TextToSpeechResult,
    TurnDetectionPolicy,
    TurnDetectionResult,
    VoiceCommandEnvelope,
    VoiceConfirmationPolicy,
    VoiceConfirmationRequest,
    VoiceConfirmationResult,
    VoiceDesktopActionProposal,
    VoiceFinalGateCertificate,
    VoiceFinalGateDecision,
    VoiceKillWordEvent,
    VoiceKillWordPolicy,
    VoiceMode,
    VoiceNotification,
    VoiceReceipt,
    VoiceRuntimeConfig,
    VoiceSafetyScanResult,
    VoiceSession,
    build_final_transcript,
    build_partial_transcript,
    scan_voice_text,
)
from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface


class VoiceRuntimeError(ValueError):
    """Raised when voice behavior would violate Sentinel runtime boundaries."""


class FakeInjectedVoiceBackend:
    """Fake/injected audio backend.

    This adapter never calls microphone, speaker, STT, TTS, realtime provider,
    or OS APIs by itself. Tests can inject a small object that records playback
    and interruption calls.
    """

    def __init__(self, transport: Any) -> None:
        self.transport = transport

    def play_output(self, text: str) -> dict[str, Any]:
        fn = getattr(self.transport, "play_output", None)
        return dict(fn(text) or {}) if fn else {"output_hash": stable_hash(text)}

    def interrupt_output(self, output_id: str) -> dict[str, Any]:
        fn = getattr(self.transport, "interrupt_output", None)
        return dict(fn(output_id) or {}) if fn else {"interrupted": True}


class VoiceRuntimeRegistry:
    def __init__(self, *, backends: dict[str, FakeInjectedVoiceBackend] | None = None) -> None:
        self._configs: dict[str, VoiceRuntimeConfig] = {}
        self._backends: dict[str, FakeInjectedVoiceBackend] = dict(backends or {})

    def register(self, config: VoiceRuntimeConfig, *, backend: FakeInjectedVoiceBackend | None = None) -> VoiceRuntimeConfig:
        self._configs[config.config_id] = config
        if backend is not None:
            self._backends[config.config_id] = backend
        return config

    def config(self, config_id: str) -> VoiceRuntimeConfig:
        try:
            return self._configs[config_id]
        except KeyError as exc:
            raise VoiceRuntimeError("voice_config_not_registered") from exc

    def backend(self, config_id: str) -> FakeInjectedVoiceBackend | None:
        return self._backends.get(config_id)


class VoiceRuntime:
    """Sentinel-owned voice runtime over MissionKernel and telemetry."""

    def __init__(self, kernel: MissionKernel, *, registry: VoiceRuntimeRegistry | None = None) -> None:
        self.kernel = kernel
        self.store = kernel.store
        self.registry = registry or VoiceRuntimeRegistry()

    def register_config(self, *, mission_id: str, config: VoiceRuntimeConfig) -> VoiceRuntimeConfig:
        self.store.load_record(mission_id)
        config = config.with_hash()
        self.registry.register(config, backend=self.registry.backend(config.config_id))
        self._write_json(mission_id, "configs", config.config_id, config.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_provider_descriptor_registered",
            "Voice provider descriptors registered; no live provider call enabled.",
            metadata={"config_id": config.config_id, "config_hash": config.config_hash, "provider_count": len(config.provider_contracts)},
        )
        return config

    def start_session(self, *, mission_id: str, config_id: str, envelope: MissionAuthorityEnvelope | None) -> VoiceSession:
        config = self._load_config(mission_id, config_id)
        self._assert_authority(mission_id, envelope)
        if config.default_mode in {VoiceMode.AMBIENT_LISTENER, VoiceMode.AMBIENT_OPERATOR, VoiceMode.FULL_VOICE_COPILOT}:
            self._assert_ambient_allowed(config.ambient_policy, config.default_mode)
        session = VoiceSession(config_id=config_id, mission_id=mission_id, mode=config.default_mode).with_hash()
        self._write_json(mission_id, "sessions", session.session_id, session.safe_model_dump())
        self._append_event(mission_id, "voice_runtime_started", "Voice runtime started for a Sentinel-owned session.", metadata={"config_id": config_id})
        self._append_event(mission_id, "voice_session_started", "Voice session started.", metadata={"session_id": session.session_id, "mode": session.mode.value})
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_SESSION_COUNT, 1, "Voice session count sample.", session_id=session.session_id)
        return session

    def load_session(self, *, mission_id: str, session_id: str) -> VoiceSession:
        return VoiceSession.model_validate_json((self._root(mission_id) / "sessions" / f"{session_id}.json").read_text(encoding="utf-8"))

    def record_audio_chunk(self, *, mission_id: str, session_id: str, raw_audio: bytes) -> AudioChunkRef:
        self._assert_session_live(mission_id, session_id)
        chunk = AudioChunkRef.from_bytes(session_id=session_id, raw_audio=raw_audio)
        self._write_json(mission_id, "audio_chunks", chunk.chunk_id, chunk.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_audio_input_started",
            "Voice audio input chunk recorded as hash-only metadata.",
            metadata={"session_id": session_id, "chunk_hash": chunk.chunk_hash, "audio_hash": chunk.audio_hash, "byte_count": chunk.byte_count},
        )
        return chunk

    def record_voice_activity(self, *, mission_id: str, session_id: str, event_type: str, audio_chunk_refs: list[str] | None = None) -> Any:
        from sentinel.operator.voice_models import VoiceActivityEvent

        self._assert_session_live(mission_id, session_id)
        event = VoiceActivityEvent(session_id=session_id, event_type=event_type, audio_chunk_refs=audio_chunk_refs or []).with_hash()
        self._write_json(mission_id, "activity", event.activity_event_id, event.safe_model_dump())
        self._append_event(mission_id, "voice_activity_detected", "Voice activity event detected.", metadata={"session_id": session_id, "activity_type": event.event_type})
        if event.event_type == "speech_started":
            self._append_event(mission_id, "voice_turn_started", "Voice turn started.", metadata={"session_id": session_id})
            self._record_metric(mission_id, TelemetryMetricKind.VOICE_TURN_COUNT, 1, "Voice turn count sample.", session_id=session_id)
        if event.event_type == "speech_ended":
            self._append_event(mission_id, "voice_turn_ended", "Voice turn ended.", metadata={"session_id": session_id})
        return event

    def record_partial_transcript(
        self,
        *,
        mission_id: str,
        session_id: str,
        text: str,
        audio_chunk_refs: list[str] | None = None,
    ) -> PartialTranscript:
        self._assert_session_live(mission_id, session_id)
        partial = build_partial_transcript(session_id=session_id, text=text, audio_chunk_refs=audio_chunk_refs)
        self._write_json(mission_id, "partial_transcripts", partial.transcript_event_id, partial.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_partial_transcript_created",
            "Voice partial transcript created as redacted metadata.",
            metadata={"session_id": session_id, "transcript_hash": partial.transcript_hash},
        )
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_PARTIAL_TRANSCRIPT_COUNT, 1, "Voice partial transcript count sample.", session_id=session_id)
        return partial

    def record_final_transcript(
        self,
        *,
        mission_id: str,
        session_id: str,
        text: str,
        audio_chunk_refs: list[str] | None = None,
        partial_refs: list[str] | None = None,
    ) -> FinalTranscript:
        self._assert_session_live(mission_id, session_id)
        final = build_final_transcript(session_id=session_id, text=text, audio_chunk_refs=audio_chunk_refs, partial_refs=partial_refs)
        self._write_json(mission_id, "final_transcripts", final.transcript_event_id, final.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_final_transcript_created",
            "Voice final transcript created as hash and redacted excerpt.",
            metadata={"session_id": session_id, "transcript_hash": final.transcript_hash},
        )
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_FINAL_TRANSCRIPT_COUNT, 1, "Voice final transcript count sample.", session_id=session_id)
        return final

    def detect_turn(
        self,
        *,
        mission_id: str,
        session_id: str,
        final_transcript: FinalTranscript,
        policy: TurnDetectionPolicy,
    ) -> TurnDetectionResult:
        self._assert_session_live(mission_id, session_id)
        result = TurnDetectionResult(
            session_id=session_id,
            policy=policy,
            endpointing_decision=EndpointingDecision(final_transcript_ready=True, reason=policy.mode.value),
            final_transcript_ref=final_transcript.transcript_event_id,
        ).with_hash()
        self._write_json(mission_id, "turns", result.turn_result_id, result.safe_model_dump())
        self._append_event(mission_id, "voice_turn_ended", "Voice turn detection completed.", metadata={"session_id": session_id, "turn_hash": result.result_hash})
        return result

    def start_speech_output(self, *, mission_id: str, session_id: str, text: str) -> StreamingSpeechOutput:
        session = self._assert_session_live(mission_id, session_id)
        safe = redact_operator_text(text[:180])
        request = TextToSpeechRequest(text=text, text_hash=text_hash(text), safe_excerpt=safe)
        raw = self._backend(session.config_id).play_output(text)
        result = TextToSpeechResult(request_id=request.request_id, output_ref_hash=str(raw.get("output_hash") or stable_hash(text)))
        output = StreamingSpeechOutput(
            session_id=session_id,
            text_hash=text_hash(text),
            safe_excerpt=safe,
            playback_state=SpeechPlaybackState.PLAYING,
            tts_result=result,
        ).with_hash()
        self._write_json(mission_id, "outputs", output.output_id, output.safe_model_dump())
        self._append_event(mission_id, "voice_output_started", "Voice output started through fake/injected backend.", metadata={"session_id": session_id, "output_hash": output.output_hash})
        return output

    def load_speech_output(self, *, mission_id: str, output_id: str) -> StreamingSpeechOutput:
        return StreamingSpeechOutput.model_validate_json((self._root(mission_id) / "outputs" / f"{output_id}.json").read_text(encoding="utf-8"))

    def complete_speech_output(self, *, mission_id: str, output_id: str) -> StreamingSpeechOutput:
        output = self.load_speech_output(mission_id=mission_id, output_id=output_id)
        updated = output.model_copy(update={"playback_state": SpeechPlaybackState.COMPLETED, "completed_at": datetime.now(UTC)}).with_hash()
        self._write_json(mission_id, "outputs", output_id, updated.safe_model_dump())
        receipt = self._receipt(mission_id, updated.session_id, "voice_output_completed", status="completed")
        finalgate = self._finalgate(mission_id, updated.session_id, VoiceFinalGateDecision.OUTPUT_COMPLETED, receipt, passed=True)
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_output_completed",
            "Voice output completed.",
            metadata={"session_id": updated.session_id},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_OUTPUT_COMPLETION_RATE, 1, "Voice output completion sample.", session_id=updated.session_id)
        return updated

    def handle_barge_in(
        self,
        *,
        mission_id: str,
        session_id: str,
        output_id: str,
        policy: BargeInPolicy,
        reason: str,
    ) -> InterruptionDecision:
        session = self._assert_session_live(mission_id, session_id)
        output = self.load_speech_output(mission_id=mission_id, output_id=output_id)
        if not policy.enabled:
            raise VoiceRuntimeError("voice_barge_in_disabled")
        self._backend(session.config_id).interrupt_output(output_id)
        event = BargeInEvent(session_id=session_id, output_id=output_id, reason=redact_operator_text(reason))
        decision = InterruptionDecision(session_id=session_id, output_id=output_id, barge_in_event=event, decision="stop_output").with_hash()
        updated = output.model_copy(update={"playback_state": SpeechPlaybackState.INTERRUPTED, "completed_at": datetime.now(UTC)}).with_hash()
        self._write_json(mission_id, "outputs", output_id, updated.safe_model_dump())
        self._write_json(mission_id, "barge_in", event.barge_in_event_id, event.safe_model_dump())
        self._write_json(mission_id, "interruptions", decision.decision_id, decision.safe_model_dump())
        self._append_event(mission_id, "voice_barge_in_detected", "Voice barge-in detected and output interrupted.", metadata={"session_id": session_id, "output_id": output_id})
        self._append_event(mission_id, "voice_output_interrupted", "Voice output interrupted.", metadata={"session_id": session_id, "output_id": output_id})
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_BARGE_IN_COUNT, 1, "Voice barge-in count sample.", session_id=session_id)
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_INTERRUPT_LATENCY, 0, "Voice interruption latency sample.", unit="milliseconds", session_id=session_id)
        return decision

    def detect_kill_word(
        self,
        *,
        mission_id: str,
        session_id: str,
        text: str,
        output_id: str | None = None,
        policy: VoiceKillWordPolicy | None = None,
    ) -> VoiceKillWordEvent:
        policy = policy or VoiceKillWordPolicy()
        lower = text.lower()
        matched_word = next((word for word in policy.kill_words if word and word in lower), None)
        event = VoiceKillWordEvent(session_id=session_id, matched=bool(matched_word), kill_word_hash=stable_hash(matched_word) if matched_word else None).with_hash()
        self._write_json(mission_id, "kill_words", event.kill_event_id, event.safe_model_dump())
        if event.matched:
            if output_id:
                output = self.load_speech_output(mission_id=mission_id, output_id=output_id)
                session = self.load_session(mission_id=mission_id, session_id=session_id)
                self._backend(session.config_id).interrupt_output(output_id)
                self._write_json(
                    mission_id,
                    "outputs",
                    output_id,
                    output.model_copy(update={"playback_state": SpeechPlaybackState.INTERRUPTED, "completed_at": datetime.now(UTC)}).with_hash().safe_model_dump(),
                )
            session = self.load_session(mission_id=mission_id, session_id=session_id)
            killed = session.model_copy(update={"state": "killed", "completed_at": datetime.now(UTC)}).with_hash()
            self._write_json(mission_id, "sessions", session_id, killed.safe_model_dump())
            self._append_event(mission_id, "voice_kill_word_detected", "Voice kill word detected; voice session killed.", metadata={"session_id": session_id})
            self._record_metric(mission_id, TelemetryMetricKind.VOICE_KILL_WORD_COUNT, 1, "Voice kill word count sample.", session_id=session_id)
        return event

    def create_command_envelope(
        self,
        *,
        mission_id: str,
        session_id: str,
        final_transcript: FinalTranscript,
        envelope: MissionAuthorityEnvelope | None,
    ) -> VoiceCommandEnvelope:
        self._assert_session_live(mission_id, session_id)
        self._assert_authority(mission_id, envelope)
        risk, scan, intents = scan_voice_text(final_transcript.text)
        receipt = self._receipt(
            mission_id,
            session_id,
            "voice_command_envelope_created",
            transcript_hash=final_transcript.transcript_hash,
            status="checkpoint_required" if risk.requires_checkpoint else "recorded",
        )
        finalgate = self._finalgate(mission_id, session_id, VoiceFinalGateDecision.COMMAND_ENVELOPED, receipt, passed=True)
        command = VoiceCommandEnvelope(
            session_id=session_id,
            mission_id=mission_id,
            final_transcript_ref=final_transcript.transcript_event_id,
            transcript_hash=final_transcript.transcript_hash,
            safe_excerpt=final_transcript.safe_excerpt,
            intent_candidates=intents,
            risk_profile=risk,
            safety_scan=scan,
            voice_receipt=receipt,
            finalgate_certificate=finalgate,
        ).with_hash()
        receipt = receipt.model_copy(update={"command_id": command.command_id}).with_hash()
        command = command.model_copy(update={"voice_receipt": receipt}).with_hash()
        self._write_json(mission_id, "commands", command.command_id, command.safe_model_dump())
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_command_envelope_created",
            "Voice command envelope created; it is data and not authority.",
            metadata={"session_id": session_id, "command_hash": command.command_hash, "requires_checkpoint": risk.requires_checkpoint},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_COMMAND_BLOCK_RATE, 1 if risk.requires_checkpoint else 0, "Voice command block/checkpoint sample.", session_id=session_id)
        return command

    def create_confirmation_request(
        self,
        *,
        mission_id: str,
        session_id: str,
        command_id: str,
        policy: VoiceConfirmationPolicy,
    ) -> VoiceConfirmationRequest:
        self._assert_session_live(mission_id, session_id)
        request = VoiceConfirmationRequest(session_id=session_id, command_id=command_id, policy=policy).with_hash()
        self._write_json(mission_id, "confirmation_requests", request.confirmation_id, request.safe_model_dump())
        self._append_event(mission_id, "voice_confirmation_required", "Voice confirmation requested as evidence, not authority.", metadata={"session_id": session_id, "command_id": command_id})
        self._record_metric(mission_id, TelemetryMetricKind.VOICE_CONFIRMATION_RATE, 1, "Voice confirmation required sample.", session_id=session_id)
        return request

    def complete_confirmation(
        self,
        *,
        mission_id: str,
        session_id: str,
        confirmation_id: str,
        approved: bool,
        spoken_text: str,
    ) -> VoiceConfirmationResult:
        self._assert_session_live(mission_id, session_id)
        result = VoiceConfirmationResult(
            confirmation_id=confirmation_id,
            approved=approved,
            spoken_text_hash=text_hash(spoken_text),
            safe_excerpt=redact_operator_text(spoken_text[:120]),
        ).with_hash()
        self._write_json(mission_id, "confirmations", result.result_id, result.safe_model_dump())
        receipt = self._receipt(mission_id, session_id, "voice_confirmation_completed", status="approved" if approved else "rejected")
        finalgate = self._finalgate(mission_id, session_id, VoiceFinalGateDecision.CONFIRMATION_RECORDED, receipt, passed=True)
        self._write_json(mission_id, "receipts", receipt.receipt_id, receipt.safe_model_dump())
        self._write_json(mission_id, "finalgate", finalgate.certificate_id, finalgate.safe_model_dump())
        self._append_event(
            mission_id,
            "voice_confirmation_completed",
            "Voice confirmation recorded as evidence, not authority.",
            metadata={"session_id": session_id, "approved": approved},
            receipt_refs=[receipt.receipt_id],
            finalgate_certificate_refs=[finalgate.certificate_id],
        )
        return result

    def create_ambient_notification(self, *, mission_id: str, session_id: str, category: str, safe_summary: str) -> VoiceNotification:
        session = self._assert_session_live(mission_id, session_id)
        config = self._load_config(mission_id, session.config_id)
        normalized = category.strip().lower()
        if normalized in config.ambient_policy.blocked_categories or normalized not in config.ambient_policy.allowed_proactive_categories:
            raise VoiceRuntimeError("ambient_voice_category_blocked")
        notification = VoiceNotification(session_id=session_id, category=normalized, safe_summary=safe_summary).with_hash()
        self._write_json(mission_id, "notifications", notification.notification_id, notification.safe_model_dump())
        self._append_event(mission_id, "voice_ambient_notification_created", "Voice ambient notification created under scoped policy.", metadata={"session_id": session_id, "category": normalized})
        return notification

    def create_desktop_action_proposal(self, *, mission_id: str, session_id: str, command_id: str, desktop_target_ref: str) -> VoiceDesktopActionProposal:
        self._assert_session_live(mission_id, session_id)
        proposal = VoiceDesktopActionProposal(session_id=session_id, command_id=command_id, desktop_target_ref=redact_operator_text(desktop_target_ref)).with_hash()
        self._write_json(mission_id, "desktop_proposals", proposal.proposal_id, proposal.safe_model_dump())
        self._append_event(mission_id, "voice_command_blocked", "Voice-to-desktop command converted to proposal only; no desktop action executed.", metadata={"session_id": session_id, "proposal_hash": proposal.proposal_hash})
        return proposal

    def request_integration_direct_execution(self, *, mission_id: str, session_id: str, source: str, action: str) -> None:
        self._assert_session_live(mission_id, session_id)
        raise VoiceRuntimeError("voice_integration_direct_execution_blocked")

    def execute_command_directly(self, *, mission_id: str, session_id: str, command_id: str) -> None:
        self._assert_session_live(mission_id, session_id)
        raise VoiceRuntimeError("voice_command_direct_execution_blocked")

    def _assert_session_live(self, mission_id: str, session_id: str) -> VoiceSession:
        session = self.load_session(mission_id=mission_id, session_id=session_id)
        if session.state == "killed":
            raise VoiceRuntimeError("voice_session_killed")
        return session

    def _assert_authority(self, mission_id: str, envelope: MissionAuthorityEnvelope | None) -> None:
        if envelope is None:
            raise VoiceRuntimeError("voice_authority_missing")
        if envelope.revoked_at is not None:
            raise VoiceRuntimeError("voice_authority_revoked")
        now = datetime.now(UTC)
        if envelope.expires_at <= now:
            raise VoiceRuntimeError("voice_authority_expired")
        if "voice_session" not in set(envelope.allowed_actions):
            raise VoiceRuntimeError("voice_action_not_authorized")
        if "voice_runtime" not in set(envelope.allowed_tools):
            raise VoiceRuntimeError("voice_tool_not_authorized")
        self.store.load_record(mission_id)

    def _assert_ambient_allowed(self, policy: AmbientVoicePolicy, mode: VoiceMode) -> None:
        if mode is VoiceMode.AMBIENT_LISTENER and not policy.ambient_listener_allowed:
            raise VoiceRuntimeError("ambient_voice_not_allowed")
        if mode is VoiceMode.AMBIENT_OPERATOR and not policy.ambient_operator_allowed:
            raise VoiceRuntimeError("ambient_voice_not_allowed")
        if mode is VoiceMode.FULL_VOICE_COPILOT and not (policy.ambient_listener_allowed and policy.ambient_operator_allowed):
            raise VoiceRuntimeError("ambient_voice_not_allowed")

    def _load_config(self, mission_id: str, config_id: str) -> VoiceRuntimeConfig:
        path = self._root(mission_id) / "configs" / f"{config_id}.json"
        if path.exists():
            config = VoiceRuntimeConfig.model_validate_json(path.read_text(encoding="utf-8"))
            if not config.verify_hash():
                raise VoiceRuntimeError("voice_config_hash_mismatch")
            return config
        return self.registry.config(config_id)

    def _backend(self, config_id: str) -> FakeInjectedVoiceBackend:
        backend = self.registry.backend(config_id)
        if backend is None:
            backend = FakeInjectedVoiceBackend(None)
        return backend

    def _receipt(
        self,
        mission_id: str,
        session_id: str,
        event_type: str,
        *,
        transcript_hash: str | None = None,
        status: str = "recorded",
    ) -> VoiceReceipt:
        return VoiceReceipt(
            mission_id=mission_id,
            session_id=session_id,
            event_type=event_type,
            transcript_hash=transcript_hash,
            policy_hash=stable_hash({"event_type": event_type, "mission_id": mission_id, "session_id": session_id}),
            status=status,
        ).with_hash()

    def _finalgate(
        self,
        mission_id: str,
        session_id: str,
        decision: VoiceFinalGateDecision,
        receipt: VoiceReceipt,
        *,
        passed: bool,
    ) -> VoiceFinalGateCertificate:
        return VoiceFinalGateCertificate(
            mission_id=mission_id,
            session_id=session_id,
            decision=decision,
            passed=passed,
            receipt_ref=receipt.receipt_id,
            safe_summary=f"Voice FinalGate decision: {decision.value}.",
        ).with_hash()

    def _append_event(
        self,
        mission_id: str,
        event_type: str,
        safe_summary: str,
        *,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
    ) -> None:
        self.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata=metadata or {},
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
        )

    def _record_metric(
        self,
        mission_id: str,
        metric_kind: TelemetryMetricKind,
        value: Any,
        safe_summary: str,
        *,
        unit: str | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        sink = self.store.telemetry_sink
        if sink is None or not hasattr(sink, "record_metric"):
            return
        sink.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                session_id=session_id,
                source_surface=TelemetrySourceSurface.VOICE_RUNTIME,
                domain=TelemetryDomain.PRODUCT_POWER,
                metric_kind=metric_kind,
                value=value,
                unit=unit,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )

    def _write_json(self, mission_id: str, category: str, name: str, payload: Any) -> None:
        directory = self._root(mission_id) / category
        directory.mkdir(parents=True, exist_ok=True)
        self.store.atomic_write_json(directory / f"{name}.json", payload)

    def _root(self, mission_id: str) -> Path:
        return self.store.mission_dir(mission_id, create=True) / "voice"
