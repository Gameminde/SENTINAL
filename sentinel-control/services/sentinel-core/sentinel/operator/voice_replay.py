from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.store import MissionRunStore
from sentinel.operator.voice_models import (
    AudioChunkRef,
    FinalTranscript,
    InterruptionDecision,
    PartialTranscript,
    StreamingSpeechOutput,
    TurnDetectionResult,
    VoiceCommandEnvelope,
    VoiceConfirmationResult,
    VoiceDesktopActionProposal,
    VoiceKillWordEvent,
    VoiceNotification,
    VoiceReplayView,
    VoiceRuntimeConfig,
    VoiceSession,
    VoiceActivityEvent,
)


class VoiceReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str) -> VoiceReplayView:
        root = self._root(mission_id)
        configs = _load_many(root / "configs", VoiceRuntimeConfig)
        sessions = _load_many(root / "sessions", VoiceSession)
        audio_chunks = _load_many(root / "audio_chunks", AudioChunkRef)
        activity_events = _load_many(root / "activity", VoiceActivityEvent)
        partial_transcripts = _load_many(root / "partial_transcripts", PartialTranscript)
        final_transcripts = _load_many(root / "final_transcripts", FinalTranscript)
        turn_results = _load_many(root / "turns", TurnDetectionResult)
        command_envelopes = _load_many(root / "commands", VoiceCommandEnvelope)
        confirmations = _load_many(root / "confirmations", VoiceConfirmationResult)
        notifications = _load_many(root / "notifications", VoiceNotification)
        outputs = _load_many(root / "outputs", StreamingSpeechOutput)
        interruptions = _load_many(root / "interruptions", InterruptionDecision)
        kill_words = _load_many(root / "kill_words", VoiceKillWordEvent)
        desktop_proposals = _load_many(root / "desktop_proposals", VoiceDesktopActionProposal)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (
            configs,
            sessions,
            audio_chunks,
            partial_transcripts,
            final_transcripts,
            turn_results,
            command_envelopes,
            outputs,
            interruptions,
            kill_words,
            notifications,
            desktop_proposals,
        ):
            for item in collection:
                if hasattr(item, "verify_hash") and not item.verify_hash():
                    tampered = True
        events = [event for event in self._store.load_events(mission_id) if event.event_type.startswith("voice_")]
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        for command in command_envelopes:
            if command.voice_receipt is not None:
                receipt_refs.append(command.voice_receipt.receipt_id)
            if command.finalgate_certificate is not None:
                finalgate_refs.append(command.finalgate_certificate.certificate_id)
        for event in events:
            receipt_refs.extend(event.receipt_refs)
            finalgate_refs.extend(event.finalgate_certificate_refs)
        return VoiceReplayView(
            mission_id=mission_id,
            configs=configs,
            sessions=sessions,
            audio_chunks=audio_chunks,
            activity_events=activity_events,
            partial_transcripts=partial_transcripts,
            final_transcripts=final_transcripts,
            turn_results=turn_results,
            command_envelopes=command_envelopes,
            confirmations=confirmations,
            notifications=notifications,
            outputs=outputs,
            interruption_decisions=interruptions,
            kill_word_events=kill_words,
            desktop_proposals=desktop_proposals,
            receipt_refs=list(dict.fromkeys(receipt_refs)),
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            tampered=tampered,
            played_audio=False,
            recorded_microphone=False,
            called_provider=False,
            executed_actions=False,
        )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id) / "voice"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]
