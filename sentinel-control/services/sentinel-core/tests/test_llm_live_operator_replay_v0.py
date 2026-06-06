from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.replay import MissionReplayBuilder


def _recorded_kernel(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_replay",
        draft=MissionDraft(title="Replay mission", objective="Build replay view."),
    )
    kernel.enqueue(record.mission_id)
    kernel.store.append_event(
        record.mission_id,
        event_type="step_completed",
        safe_summary="Step completed.",
        receipt_refs=["receipt:1"],
        finalgate_certificate_refs=["finalgate:1"],
        memory_feedback_refs=["memory:1"],
    )
    return kernel, record.mission_id


def test_replay_reconstructs_mission_timeline(tmp_path: Path) -> None:
    kernel, mission_id = _recorded_kernel(tmp_path)

    replay = MissionReplayBuilder(kernel.store).build(mission_id)

    assert replay.mission_id == mission_id
    assert replay.tampered is False
    assert [event.event_type for event in replay.events] == [
        "mission_created",
        "mission_queued",
        "step_completed",
    ]


def test_replay_does_not_reexecute_actions(tmp_path: Path) -> None:
    kernel, mission_id = _recorded_kernel(tmp_path)

    replay = MissionReplayBuilder(kernel.store).build(mission_id)

    assert replay.reexecuted_actions is False
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.QUEUED


def test_replay_detects_tampering(tmp_path: Path) -> None:
    kernel, mission_id = _recorded_kernel(tmp_path)
    events_path = tmp_path / mission_id / "events.jsonl"
    events_path.write_text(events_path.read_text(encoding="utf-8").replace("Step completed.", "Changed."), encoding="utf-8")

    replay = MissionReplayBuilder(kernel.store).build(mission_id)

    assert replay.tampered is True


def test_replay_links_receipts_finalgate_memory(tmp_path: Path) -> None:
    kernel, mission_id = _recorded_kernel(tmp_path)

    replay = MissionReplayBuilder(kernel.store).build(mission_id)

    assert replay.receipt_refs == ["receipt:1"]
    assert replay.finalgate_certificate_refs == ["finalgate:1"]
    assert replay.memory_feedback_refs == ["memory:1"]


def test_replay_redacts_sensitive_payloads(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_replay",
        draft=MissionDraft(title="Replay secret", objective="No secrets."),
    )
    kernel.store.append_event(
        record.mission_id,
        event_type="failed",
        safe_summary="Authorization: Bearer secret_token_123456789",
    )

    replay = MissionReplayBuilder(kernel.store).build(record.mission_id)
    rendered = replay.safe_summary_text()

    assert "Bearer" not in rendered
    assert "secret_token" not in rendered


def test_replay_explains_blocked_or_killed_mission(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_replay",
        draft=MissionDraft(title="Replay killed", objective="Kill it."),
    )
    kernel.kill(record.mission_id)

    replay = MissionReplayBuilder(kernel.store).build(record.mission_id)

    assert "killed" in replay.terminal_explanation.lower()
