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


TERMINAL_MISSION_STATUSES = frozenset(
    {
        OperatorMissionStatus.KILLED,
        OperatorMissionStatus.COMPLETED,
        OperatorMissionStatus.FAILED,
        OperatorMissionStatus.BLOCKED,
        OperatorMissionStatus.REVOKED,
    }
)


class MissionLifecycleError(ValueError):
    """Raised when a mission lifecycle transition would reopen terminal work."""


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
        self._assert_transition_allowed(mission_id, OperatorMissionStatus.QUEUED)
        record = self.store.update_record_status(mission_id, OperatorMissionStatus.QUEUED)
        self.store.append_event(mission_id, event_type="mission_queued", safe_summary="Mission queued.")
        return record

    def update_status(self, mission_id: str, status: OperatorMissionStatus, safe_summary: str) -> MissionRecord:
        self._assert_transition_allowed(mission_id, status)
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

    def is_terminal(self, mission_id: str) -> bool:
        return self.store.load_record(mission_id).status in TERMINAL_MISSION_STATUSES

    def terminal_block_reason(self, mission_id: str) -> str | None:
        record = self.store.load_record(mission_id)
        if record.status not in TERMINAL_MISSION_STATUSES:
            return None
        return f"operator_mission_terminal:{record.status.value}"

    def _assert_transition_allowed(self, mission_id: str, target_status: OperatorMissionStatus) -> None:
        current = self.store.load_record(mission_id).status
        if current in TERMINAL_MISSION_STATUSES and target_status is not current:
            raise MissionLifecycleError(
                f"mission {mission_id} is terminal ({current.value}) and cannot transition to {target_status.value}"
            )
