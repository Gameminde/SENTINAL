from __future__ import annotations

from pathlib import Path

from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    MissionRecord,
    OperatorMissionStatus,
)
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.store import MissionRunStore


class MissionKernel:
    def __init__(self, *, run_root: Path | str) -> None:
        self.store = MissionRunStore(run_root)

    def create_mission(
        self,
        *,
        session_id: str,
        draft: MissionDraft,
        authority_summary: MissionAuthoritySummary | None = None,
    ) -> MissionRecord:
        record = MissionRecord(
            session_id=session_id,
            draft=draft,
            authority_summary=authority_summary,
            run_dir=str(self.store.run_root),
        )
        return self.store.create_record(record)

    def list_missions(self) -> list[MissionRecord]:
        return self.store.list_records()

    def enqueue(self, mission_id: str) -> MissionRecord:
        record = self.store.update_record_status(mission_id, OperatorMissionStatus.QUEUED)
        self.store.append_event(mission_id, event_type="mission_queued", safe_summary="Mission queued.")
        return record

    def update_status(self, mission_id: str, status: OperatorMissionStatus, safe_summary: str) -> MissionRecord:
        record = self.store.update_record_status(mission_id, status)
        self.store.append_event(mission_id, event_type=f"mission_{status.value}", safe_summary=safe_summary)
        return record

    def pause(self, mission_id: str) -> MissionRecord:
        return self.update_status(mission_id, OperatorMissionStatus.PAUSED, "Mission paused.")

    def resume(self, mission_id: str) -> MissionRecord:
        return self.update_status(mission_id, OperatorMissionStatus.QUEUED, "Mission resumed.")

    def kill(self, mission_id: str) -> MissionRecord:
        return self.update_status(mission_id, OperatorMissionStatus.KILLED, "Mission killed.")

    def record_failure(self, mission_id: str, exc: BaseException) -> MissionRecord:
        safe_summary = f"{exc.__class__.__name__}: {redact_operator_text(str(exc))}"
        return self.update_status(mission_id, OperatorMissionStatus.FAILED, safe_summary)
