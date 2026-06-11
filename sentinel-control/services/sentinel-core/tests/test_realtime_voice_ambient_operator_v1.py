from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.voice_models import (
    AmbientVoicePolicy,
    AudioTransportKind,
    BargeInPolicy,
    SpeechPlaybackState,
    SpeechToTextContract,
    TextToSpeechContract,
    TurnDetectionMode,
    TurnDetectionPolicy,
    VoiceConfirmationPolicy,
    VoiceControlMode,
    VoiceFinalGateDecision,
    VoiceKillWordPolicy,
    VoiceMode,
    VoicePrivacyPolicy,
    VoiceProviderContract,
    VoiceProviderKind,
    VoiceRuntimeConfig,
)
from sentinel.operator.voice_replay import VoiceReplayBuilder
from sentinel.operator.voice_runtime import FakeInjectedVoiceBackend, VoiceRuntime, VoiceRuntimeError, VoiceRuntimeRegistry
from sentinel.telemetry.models import TelemetryEventKind, TelemetryMetricKind


def test_voice_runtime_session_creation_modes_and_provider_descriptors(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))

    assert config.default_mode is VoiceMode.SESSION_VOICE
    assert VoiceMode.PUSH_TO_TALK in config.allowed_modes
    assert VoiceMode.AMBIENT_OPERATOR in config.allowed_modes
    assert VoiceMode.FULL_VOICE_COPILOT in config.allowed_modes
    assert config.provider_contracts[0].provider_kind is VoiceProviderKind.OPENAI_REALTIME_STYLE_DESCRIPTOR
    assert config.provider_contracts[0].descriptor_only is True
    assert config.provider_contracts[0].live_provider_call_allowed is False
    assert config.stt_contract.descriptor_only is True
    assert config.tts_contract.descriptor_only is True
    assert session.mode is VoiceMode.SESSION_VOICE
    assert session.state == "running"
    assert runtime.store.verify_timeline(mission_id)

    with pytest.raises(ValueError, match="provider key"):
        VoiceProviderContract(
            provider_id="bad",
            provider_kind=VoiceProviderKind.API_STT,
            display_name="Bad provider",
            descriptor_only=True,
            provider_key="blocked-provider-key-material",
        )


def test_fake_audio_backend_vad_turn_and_transcript_lifecycle_blocks_raw_persistence(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))

    chunk = runtime.record_audio_chunk(
        mission_id=mission_id,
        session_id=session.session_id,
        raw_audio=("fake raw microphone bytes with " + "TOKEN=" + "blocked-value").encode("utf-8"),
    )
    vad_start = runtime.record_voice_activity(mission_id=mission_id, session_id=session.session_id, event_type="speech_started")
    partial = runtime.record_partial_transcript(
        mission_id=mission_id,
        session_id=session.session_id,
        text="Sentinel, monitor",
        audio_chunk_refs=[chunk.chunk_id],
    )
    final = runtime.record_final_transcript(
        mission_id=mission_id,
        session_id=session.session_id,
        text="Sentinel, monitor my PC temperature while I work. " + "OPENAI" + "_API_KEY=" + "blocked-value",
        audio_chunk_refs=[chunk.chunk_id],
        partial_refs=[partial.transcript_event_id],
    )
    turn = runtime.detect_turn(
        mission_id=mission_id,
        session_id=session.session_id,
        final_transcript=final,
        policy=TurnDetectionPolicy(mode=TurnDetectionMode.STT_ENDPOINTING),
    )

    assert backend.live_call_count == 0
    assert chunk.raw_audio_persisted is False
    assert chunk.audio_hash
    assert vad_start.event_type == "speech_started"
    assert partial.safe_excerpt == "Sentinel, monitor"
    assert final.transcript_hash
    assert "OPENAI" + "_API_KEY" not in final.safe_excerpt
    assert turn.endpointing_decision.final_transcript_ready is True
    persisted = _mission_text(runtime, mission_id)
    assert "fake raw microphone bytes" not in persisted
    assert "blocked-value" not in persisted
    assert "raw_full_transcript" not in persisted


def test_barge_in_interrupts_speech_output_and_records_decision(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))
    output = runtime.start_speech_output(
        mission_id=mission_id,
        session_id=session.session_id,
        text="I am watching the desktop render and will notify you if it fails.",
    )

    interruption = runtime.handle_barge_in(
        mission_id=mission_id,
        session_id=session.session_id,
        output_id=output.output_id,
        policy=BargeInPolicy(enabled=True),
        reason="operator_spoke",
    )
    updated = runtime.load_speech_output(mission_id=mission_id, output_id=output.output_id)

    assert output.playback_state is SpeechPlaybackState.PLAYING
    assert interruption.decision == "stop_output"
    assert updated.playback_state is SpeechPlaybackState.INTERRUPTED
    assert backend.output_interruptions == 1


def test_kill_word_interrupts_output_and_blocks_future_voice_events(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))
    output = runtime.start_speech_output(mission_id=mission_id, session_id=session.session_id, text="Continuing mission status.")

    event = runtime.detect_kill_word(
        mission_id=mission_id,
        session_id=session.session_id,
        text="Sentinel stop now",
        output_id=output.output_id,
        policy=VoiceKillWordPolicy(kill_words=["stop now", "kill"]),
    )

    assert event.matched is True
    assert event.kill_word_hash
    assert event.raw_text_persisted is False
    assert runtime.load_session(mission_id=mission_id, session_id=session.session_id).state == "killed"
    with pytest.raises(VoiceRuntimeError, match="voice_session_killed"):
        runtime.record_voice_activity(mission_id=mission_id, session_id=session.session_id, event_type="speech_started")


def test_voice_command_envelope_is_not_authority_and_dangerous_commands_checkpoint(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))
    final = runtime.record_final_transcript(
        mission_id=mission_id,
        session_id=session.session_id,
        text="Click that payment button and send it now",
    )

    command = runtime.create_command_envelope(
        mission_id=mission_id,
        session_id=session.session_id,
        final_transcript=final,
        envelope=_envelope(mission_id),
    )
    confirmation = runtime.create_confirmation_request(
        mission_id=mission_id,
        session_id=session.session_id,
        command_id=command.command_id,
        policy=VoiceConfirmationPolicy(require_confirmation_for_dangerous=True),
    )
    result = runtime.complete_confirmation(
        mission_id=mission_id,
        session_id=session.session_id,
        confirmation_id=confirmation.confirmation_id,
        approved=True,
        spoken_text="yes",
    )

    assert command.data_not_authority is True
    assert command.can_execute is False
    assert command.can_grant_authority is False
    assert command.risk_profile.requires_checkpoint is True
    assert command.safety_scan.requires_confirmation is True
    assert confirmation.voice_confirmation_is_authority is False
    assert result.voice_confirmation_is_authority is False
    assert result.can_execute is False
    with pytest.raises(VoiceRuntimeError, match="voice_command_direct_execution_blocked"):
        runtime.execute_command_directly(mission_id=mission_id, session_id=session.session_id, command_id=command.command_id)


def test_ambient_listener_requires_policy_and_voice_to_desktop_is_proposal_only(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config(mode=VoiceMode.AMBIENT_OPERATOR))

    with pytest.raises(VoiceRuntimeError, match="ambient_voice_not_allowed"):
        runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))

    config = runtime.register_config(
        mission_id=mission_id,
        config=_voice_config(
            mode=VoiceMode.AMBIENT_OPERATOR,
            ambient_policy=AmbientVoicePolicy(
                ambient_listener_allowed=True,
                ambient_operator_allowed=True,
                allowed_proactive_categories=["desktop_monitoring_alert", "mission_blocked"],
                quiet_hours=[],
            ),
        ),
    )
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))
    notification = runtime.create_ambient_notification(
        mission_id=mission_id,
        session_id=session.session_id,
        category="desktop_monitoring_alert",
        safe_summary="GPU temperature threshold exceeded.",
    )
    final = runtime.record_final_transcript(mission_id=mission_id, session_id=session.session_id, text="Click that button")
    command = runtime.create_command_envelope(
        mission_id=mission_id,
        session_id=session.session_id,
        final_transcript=final,
        envelope=_envelope(mission_id),
    )
    proposal = runtime.create_desktop_action_proposal(
        mission_id=mission_id,
        session_id=session.session_id,
        command_id=command.command_id,
        desktop_target_ref="desktop_region:launch_button",
    )

    assert notification.category == "desktop_monitoring_alert"
    assert proposal.proposal_only is True
    assert proposal.executed is False
    assert proposal.requires_desktop_authority is True


@pytest.mark.parametrize("source", ["desktop", "daemon", "worker", "channel", "skill", "memory", "provider_tool"])
def test_voice_integrations_cannot_direct_execute(tmp_path: Path, source: str) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))

    with pytest.raises(VoiceRuntimeError, match="voice_integration_direct_execution_blocked"):
        runtime.request_integration_direct_execution(
            mission_id=mission_id,
            session_id=session.session_id,
            source=source,
            action="execute",
        )


def test_voice_replay_reconstructs_without_audio_playback_provider_calls_or_actions(tmp_path: Path) -> None:
    runtime, mission_id, backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))
    chunk = runtime.record_audio_chunk(mission_id=mission_id, session_id=session.session_id, raw_audio=b"hello")
    final = runtime.record_final_transcript(mission_id=mission_id, session_id=session.session_id, text="What is the status?", audio_chunk_refs=[chunk.chunk_id])
    command = runtime.create_command_envelope(mission_id=mission_id, session_id=session.session_id, final_transcript=final, envelope=_envelope(mission_id))
    output = runtime.start_speech_output(mission_id=mission_id, session_id=session.session_id, text="Here is the current status.")
    runtime.complete_speech_output(mission_id=mission_id, output_id=output.output_id)
    before = (backend.live_call_count, backend.output_play_count, backend.output_interruptions)

    replay = VoiceReplayBuilder(runtime.store).build(mission_id)

    assert replay.configs
    assert replay.sessions
    assert replay.audio_chunks
    assert replay.final_transcripts
    assert replay.command_envelopes[0].command_id == command.command_id
    assert replay.played_audio is False
    assert replay.recorded_microphone is False
    assert replay.called_provider is False
    assert replay.executed_actions is False
    assert (backend.live_call_count, backend.output_play_count, backend.output_interruptions) == before


def test_voice_telemetry_records_events_and_metrics(tmp_path: Path) -> None:
    runtime, mission_id, _backend = _runtime(tmp_path)
    config = runtime.register_config(mission_id=mission_id, config=_voice_config())
    session = runtime.start_session(mission_id=mission_id, config_id=config.config_id, envelope=_envelope(mission_id))
    runtime.record_voice_activity(mission_id=mission_id, session_id=session.session_id, event_type="speech_started")
    final = runtime.record_final_transcript(mission_id=mission_id, session_id=session.session_id, text="Pause the mission")
    runtime.create_command_envelope(mission_id=mission_id, session_id=session.session_id, final_transcript=final, envelope=_envelope(mission_id))
    output = runtime.start_speech_output(mission_id=mission_id, session_id=session.session_id, text="Mission paused.")
    runtime.handle_barge_in(mission_id=mission_id, session_id=session.session_id, output_id=output.output_id, policy=BargeInPolicy(enabled=True), reason="operator_spoke")

    snapshot = runtime.store.telemetry_sink.store.snapshot()
    assert snapshot.event_counts_by_kind[TelemetryEventKind.VOICE_SESSION_STARTED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.VOICE_ACTIVITY_DETECTED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.VOICE_FINAL_TRANSCRIPT_CREATED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.VOICE_COMMAND_ENVELOPE_CREATED.value] >= 1
    assert snapshot.event_counts_by_kind[TelemetryEventKind.VOICE_BARGE_IN_DETECTED.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.VOICE_SESSION_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.VOICE_FINAL_TRANSCRIPT_COUNT.value] >= 1
    assert snapshot.metric_counts_by_kind[TelemetryMetricKind.VOICE_BARGE_IN_COUNT.value] >= 1


class FakeVoiceTransport:
    def __init__(self) -> None:
        self.live_call_count = 0
        self.output_play_count = 0
        self.output_interruptions = 0

    def play_output(self, text: str) -> dict[str, Any]:
        self.output_play_count += 1
        return {"output_hash": f"out-{len(text)}"}

    def interrupt_output(self, output_id: str) -> dict[str, Any]:
        self.output_interruptions += 1
        return {"interrupted": True, "output_id": output_id}


def _runtime(tmp_path: Path) -> tuple[VoiceRuntime, str, FakeVoiceTransport]:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_voice",
        draft=MissionDraft(
            title="Use realtime voice",
            objective="Control Sentinel through a governed voice runtime.",
            constraints=["no hidden recorder", "no voice authority", "no provider-native tools"],
            expected_artifacts=["voice receipt", "voice replay"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="voice_mission",
            allowed_actions=["voice_session", "voice_input", "voice_output", "voice_notify", "voice_confirm"],
            forbidden_actions=["credential_unlock", "payment", "trading", "provider_tool_execution"],
            summary="Voice can talk and propose, not execute.",
        ),
    )
    backend = FakeVoiceTransport()
    runtime = VoiceRuntime(
        kernel,
        registry=VoiceRuntimeRegistry(backends={"voice_fake": FakeInjectedVoiceBackend(backend)}),
    )
    return runtime, record.mission_id, backend


def _voice_config(
    *,
    mode: VoiceMode = VoiceMode.SESSION_VOICE,
    ambient_policy: AmbientVoicePolicy | None = None,
) -> VoiceRuntimeConfig:
    return VoiceRuntimeConfig(
        config_id="voice_fake",
        default_mode=mode,
        allowed_modes=[
            VoiceMode.DISABLED,
            VoiceMode.PUSH_TO_TALK,
            VoiceMode.WAKE_WORD,
            VoiceMode.SESSION_VOICE,
            VoiceMode.AMBIENT_LISTENER,
            VoiceMode.AMBIENT_OPERATOR,
            VoiceMode.FULL_VOICE_COPILOT,
        ],
        control_mode=VoiceControlMode.SENTINEL_OWNED_PIPELINE,
        provider_contracts=[
            VoiceProviderContract(
                provider_id="openai_realtime_descriptor",
                provider_kind=VoiceProviderKind.OPENAI_REALTIME_STYLE_DESCRIPTOR,
                display_name="OpenAI realtime descriptor",
                descriptor_only=True,
            ),
            VoiceProviderContract(
                provider_id="local_stt_descriptor",
                provider_kind=VoiceProviderKind.LOCAL_STT,
                display_name="Local STT descriptor",
                descriptor_only=True,
            ),
        ],
        stt_contract=SpeechToTextContract(provider_id="local_stt_descriptor", descriptor_only=True),
        tts_contract=TextToSpeechContract(provider_id="local_tts_descriptor", descriptor_only=True),
        privacy_policy=VoicePrivacyPolicy(),
        turn_detection_policy=TurnDetectionPolicy(mode=TurnDetectionMode.VAD_AND_STT_ENDPOINTING),
        ambient_policy=ambient_policy or AmbientVoicePolicy(),
        audio_transport=AudioTransportKind.INJECTED_TRANSPORT,
    )


def _envelope(mission_id: str, *, revoked: bool = False, expired: bool = False) -> MissionAuthorityEnvelope:
    now = datetime.now(UTC)
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_youcef",
        mission_title="Realtime voice mission",
        mission_objective="Use voice as Sentinel cockpit transport.",
        allowed_tools=["voice_runtime", "voice_fake", "mission_kernel"],
        allowed_actions=["voice_session", "voice_input", "voice_output", "voice_notify", "voice_confirm"],
        forbidden_actions=["credential_unlock", "payment", "trading", "account_creation", "provider_tool_execution"],
        allowed_domains=[],
        max_actions=50,
        created_at=now - timedelta(minutes=10) if expired else now,
        expires_at=now - timedelta(minutes=1) if expired else now + timedelta(minutes=30),
        revoked_at=now if revoked else None,
    )


def _mission_text(runtime: VoiceRuntime, mission_id: str) -> str:
    root = runtime.store.mission_dir(mission_id)
    return "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.json*"))
