from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    OperatorMissionStatus,
)
from sentinel.operator.store import MissionRunStore


def _draft() -> MissionDraft:
    return MissionDraft(
        title="AI training business launch",
        objective="Research the market and prepare launch artifacts.",
        constraints=["no payment", "no real send"],
        expected_artifacts=["market summary", "launch plan"],
    )


def _authority() -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="mission_kernel",
        allowed_actions=["research", "draft"],
        forbidden_actions=["payment", "send_email"],
        summary="Research and draft only.",
    )


def test_kernel_creates_mission_record_from_draft(tmp_path: Path) -> None:
    record = MissionKernel(run_root=tmp_path).create_mission(
        session_id="session_kernel",
        draft=_draft(),
        authority_summary=_authority(),
    )

    assert record.status is OperatorMissionStatus.DRAFT
    assert record.draft.title == "AI training business launch"
    assert record.authority_summary is not None
    assert (tmp_path / record.mission_id / "record.json").exists()


def test_kernel_persists_and_loads_record(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    loaded = MissionRunStore(tmp_path).load_record(record.mission_id)

    assert loaded.mission_id == record.mission_id
    assert loaded.draft.objective == record.draft.objective


def test_kernel_lists_missions(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    first = kernel.create_mission(session_id="session_kernel", draft=_draft())
    second = kernel.create_mission(session_id="session_kernel", draft=_draft())

    mission_ids = [record.mission_id for record in kernel.list_missions()]

    assert mission_ids == [first.mission_id, second.mission_id]


def test_kernel_rejects_path_escape(tmp_path: Path) -> None:
    store = MissionRunStore(tmp_path)

    with pytest.raises(ValueError):
        store.load_record("../escape")


def test_kernel_appends_hash_chained_events(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(record.mission_id)
    kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Mission running.")

    events = kernel.store.load_events(record.mission_id)

    assert [event.sequence for event in events] == [0, 1, 2]
    assert events[0].previous_hash is None
    assert events[1].previous_hash == events[0].event_hash
    assert kernel.store.verify_timeline(record.mission_id) is True


def test_kernel_detects_tampered_timeline(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(record.mission_id)
    events_path = tmp_path / record.mission_id / "events.jsonl"
    text = events_path.read_text(encoding="utf-8")
    events_path.write_text(text.replace("Mission queued.", "Tampered."), encoding="utf-8")

    assert kernel.store.verify_timeline(record.mission_id) is False


def test_kernel_status_transitions(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    kernel.enqueue(record.mission_id)
    kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Running.")
    kernel.update_status(record.mission_id, OperatorMissionStatus.COMPLETED, "Done.")

    loaded = kernel.store.load_record(record.mission_id)
    assert loaded.status is OperatorMissionStatus.COMPLETED


def test_kernel_pause_resume_kill_persisted(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    kernel.pause(record.mission_id)
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.PAUSED
    kernel.resume(record.mission_id)
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.QUEUED
    kernel.kill(record.mission_id)
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.KILLED


def test_kernel_records_failure_without_raw_exception_leak(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    kernel.record_failure(record.mission_id, RuntimeError("Bearer secret_token_123456789"))
    rendered = (tmp_path / record.mission_id / "events.jsonl").read_text(encoding="utf-8")

    assert "Bearer" not in rendered
    assert "secret_token" not in rendered
    assert "RuntimeError" in rendered


def test_kernel_no_raw_secret_persistence(tmp_path: Path) -> None:
    draft = MissionDraft(
        title="Secret test",
        objective="Use Authorization: Bearer secret_token_123456789",
    )
    record = MissionKernel(run_root=tmp_path).create_mission(session_id="session_kernel", draft=draft)

    rendered = (tmp_path / record.mission_id / "record.json").read_text(encoding="utf-8")

    assert "Bearer" not in rendered
    assert "secret_token" not in rendered


def test_kernel_no_raw_prompt_or_provider_response_persistence(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    with pytest.raises(ValueError):
        kernel.store.append_event(
            record.mission_id,
            event_type="unsafe",
            safe_summary="unsafe",
            metadata={"raw_prompt": "do not persist", "provider_response": "raw"},
        )
