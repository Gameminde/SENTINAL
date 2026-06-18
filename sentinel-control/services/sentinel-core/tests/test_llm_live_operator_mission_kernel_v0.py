from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from sentinel.operator.kernel import (
    VALID_MISSION_TRANSITIONS,
    MissionKernel,
    MissionLifecycleError,
)
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


def test_store_atomic_write_uses_short_temp_name_for_deep_artifact_path(tmp_path: Path) -> None:
    store = MissionRunStore(tmp_path / "runs")
    filename = "artifact_" + ("x" * 48) + ".json"
    target_dir = store.run_root / "mission_deep" / "read_only_spine"
    while len(str(target_dir / filename)) < 230:
        target_dir = target_dir / "segment"
    target = target_dir / filename

    store.atomic_write_json(target, {"ok": True})

    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}


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


def test_kernel_killed_mission_cannot_resume(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    kernel.kill(record.mission_id)

    with pytest.raises(ValueError):
        kernel.resume(record.mission_id)
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.KILLED


def test_kernel_terminal_mission_cannot_be_requeued(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    kernel.enqueue(record.mission_id)
    kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Running.")
    kernel.update_status(record.mission_id, OperatorMissionStatus.COMPLETED, "Done.")

    with pytest.raises(ValueError):
        kernel.enqueue(record.mission_id)
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.COMPLETED


def test_kernel_transition_policy_is_explicit_for_every_status(tmp_path: Path) -> None:
    assert set(VALID_MISSION_TRANSITIONS) == set(OperatorMissionStatus)
    assert OperatorMissionStatus.COMPLETED not in VALID_MISSION_TRANSITIONS[OperatorMissionStatus.DRAFT]
    assert OperatorMissionStatus.RUNNING not in VALID_MISSION_TRANSITIONS[OperatorMissionStatus.KILLED]
    assert OperatorMissionStatus.COMPLETED not in VALID_MISSION_TRANSITIONS[OperatorMissionStatus.FAILED]
    assert OperatorMissionStatus.RUNNING not in VALID_MISSION_TRANSITIONS[OperatorMissionStatus.REVOKED]


@pytest.mark.parametrize(
    "terminal_status,target_status",
    [
        (OperatorMissionStatus.COMPLETED, OperatorMissionStatus.RUNNING),
        (OperatorMissionStatus.KILLED, OperatorMissionStatus.QUEUED),
        (OperatorMissionStatus.FAILED, OperatorMissionStatus.COMPLETED),
        (OperatorMissionStatus.REVOKED, OperatorMissionStatus.RUNNING),
        (OperatorMissionStatus.BLOCKED, OperatorMissionStatus.RUNNING),
    ],
)
def test_kernel_invalid_terminal_transition_fails_closed_with_safe_event(
    tmp_path: Path,
    terminal_status: OperatorMissionStatus,
    target_status: OperatorMissionStatus,
) -> None:
    kernel = MissionKernel(run_root=tmp_path / terminal_status.value)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(record.mission_id)
    kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Running.")
    kernel.update_status(record.mission_id, terminal_status, "Terminal.")

    with pytest.raises(MissionLifecycleError):
        kernel.update_status(record.mission_id, target_status, "Unsafe resurrection.")

    assert kernel.store.load_record(record.mission_id).status is terminal_status
    rejected = kernel.store.load_events(record.mission_id)[-1]
    assert rejected.event_type == "mission_transition_rejected"
    assert rejected.metadata["current_status"] == terminal_status.value
    assert rejected.metadata["target_status"] == target_status.value


def test_kernel_rejects_invalid_nonterminal_jump_without_state_mutation(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    with pytest.raises(MissionLifecycleError):
        kernel.update_status(record.mission_id, OperatorMissionStatus.COMPLETED, "Skipped lifecycle.")

    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.DRAFT
    assert kernel.store.load_events(record.mission_id)[-1].event_type == "mission_transition_rejected"


def test_kernel_completion_and_kill_race_has_one_terminal_winner(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(record.mission_id)
    kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Running.")

    def transition(target: OperatorMissionStatus) -> str:
        try:
            kernel.update_status(record.mission_id, target, f"Race to {target.value}.")
            return "accepted"
        except MissionLifecycleError:
            return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(transition, [OperatorMissionStatus.COMPLETED, OperatorMissionStatus.KILLED]))

    assert sorted(outcomes) == ["accepted", "rejected"]
    assert kernel.store.load_record(record.mission_id).status in {
        OperatorMissionStatus.COMPLETED,
        OperatorMissionStatus.KILLED,
    }
    assert any(event.event_type == "mission_transition_rejected" for event in kernel.store.load_events(record.mission_id))


def test_kernel_pause_resume_kill_and_revocation_transitions_are_explicit(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    paused = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(paused.mission_id)
    kernel.update_status(paused.mission_id, OperatorMissionStatus.RUNNING, "Running.")
    kernel.pause(paused.mission_id)
    kernel.resume(paused.mission_id)
    kernel.kill(paused.mission_id)
    assert kernel.store.load_record(paused.mission_id).status is OperatorMissionStatus.KILLED

    revoked = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(revoked.mission_id)
    kernel.update_status(revoked.mission_id, OperatorMissionStatus.RUNNING, "Running.")
    kernel.update_status(revoked.mission_id, OperatorMissionStatus.REVOKED, "Revoked.")
    assert kernel.store.load_record(revoked.mission_id).status is OperatorMissionStatus.REVOKED

    failed = kernel.create_mission(session_id="session_kernel", draft=_draft())
    kernel.enqueue(failed.mission_id)
    kernel.update_status(failed.mission_id, OperatorMissionStatus.RUNNING, "Running.")
    kernel.update_status(failed.mission_id, OperatorMissionStatus.FAILED, "Failed.")
    with pytest.raises(MissionLifecycleError):
        kernel.enqueue(failed.mission_id)


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


def test_kernel_redacts_secret_like_event_metadata(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(session_id="session_kernel", draft=_draft())

    kernel.store.append_event(
        record.mission_id,
        event_type="metadata_redaction",
        safe_summary="Metadata recorded.",
        metadata={"note": "Authorization: Bearer event_secret_123456789"},
    )
    rendered = (tmp_path / record.mission_id / "events.jsonl").read_text(encoding="utf-8")

    assert "Bearer" not in rendered
    assert "event_secret" not in rendered
    assert "[REDACTED_SECRET]" in rendered
