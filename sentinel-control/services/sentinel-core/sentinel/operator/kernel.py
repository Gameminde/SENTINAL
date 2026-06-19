from __future__ import annotations

from pathlib import Path

from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    MissionEvent,
    MissionRecord,
    OperatorMissionStatus,
)
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.store import MissionRunStore
from sentinel.memory.models import PersistentMemoryRetrievalResult


TERMINAL_MISSION_STATUSES = frozenset(
    {
        OperatorMissionStatus.KILLED,
        OperatorMissionStatus.COMPLETED,
        OperatorMissionStatus.FAILED,
        OperatorMissionStatus.BLOCKED,
        OperatorMissionStatus.REVOKED,
    }
)

VALID_MISSION_TRANSITIONS: dict[OperatorMissionStatus, frozenset[OperatorMissionStatus]] = {
    OperatorMissionStatus.DRAFT: frozenset(
        {
            OperatorMissionStatus.READY_TO_START,
            OperatorMissionStatus.QUEUED,
            OperatorMissionStatus.PAUSED,
            OperatorMissionStatus.CANCEL_REQUESTED,
            OperatorMissionStatus.KILLED,
            OperatorMissionStatus.FAILED,
            OperatorMissionStatus.BLOCKED,
            OperatorMissionStatus.REVOKED,
        }
    ),
    OperatorMissionStatus.READY_TO_START: frozenset(
        {
            OperatorMissionStatus.QUEUED,
            OperatorMissionStatus.PAUSED,
            OperatorMissionStatus.CANCEL_REQUESTED,
            OperatorMissionStatus.KILLED,
            OperatorMissionStatus.FAILED,
            OperatorMissionStatus.BLOCKED,
            OperatorMissionStatus.REVOKED,
        }
    ),
    OperatorMissionStatus.QUEUED: frozenset(
        {
            OperatorMissionStatus.RUNNING,
            OperatorMissionStatus.PAUSED,
            OperatorMissionStatus.CANCEL_REQUESTED,
            OperatorMissionStatus.KILLED,
            OperatorMissionStatus.FAILED,
            OperatorMissionStatus.BLOCKED,
            OperatorMissionStatus.REVOKED,
        }
    ),
    OperatorMissionStatus.RUNNING: frozenset(
        {
            OperatorMissionStatus.PAUSED,
            OperatorMissionStatus.CANCEL_REQUESTED,
            OperatorMissionStatus.KILLED,
            OperatorMissionStatus.COMPLETED,
            OperatorMissionStatus.FAILED,
            OperatorMissionStatus.BLOCKED,
            OperatorMissionStatus.REVOKED,
        }
    ),
    OperatorMissionStatus.PAUSED: frozenset(
        {
            OperatorMissionStatus.QUEUED,
            OperatorMissionStatus.CANCEL_REQUESTED,
            OperatorMissionStatus.KILLED,
            OperatorMissionStatus.FAILED,
            OperatorMissionStatus.BLOCKED,
            OperatorMissionStatus.REVOKED,
        }
    ),
    OperatorMissionStatus.CANCEL_REQUESTED: frozenset(
        {
            OperatorMissionStatus.KILLED,
            OperatorMissionStatus.FAILED,
            OperatorMissionStatus.BLOCKED,
            OperatorMissionStatus.REVOKED,
        }
    ),
    OperatorMissionStatus.KILLED: frozenset(),
    OperatorMissionStatus.COMPLETED: frozenset(),
    OperatorMissionStatus.FAILED: frozenset(),
    OperatorMissionStatus.BLOCKED: frozenset(),
    OperatorMissionStatus.REVOKED: frozenset(),
}


class MissionLifecycleError(ValueError):
    """Raised when a mission lifecycle transition is not explicitly allowed."""


class MissionKernel:
    def __init__(self, *, run_root: Path | str, telemetry_sink: object | None = None) -> None:
        self.store = MissionRunStore(run_root, telemetry_sink=telemetry_sink)
        self.telemetry_sink = self.store.telemetry_sink

    def create_mission(
        self,
        *,
        session_id: str,
        draft: MissionDraft,
        authority_summary: MissionAuthoritySummary | None = None,
        mission_id: str | None = None,
    ) -> MissionRecord:
        record_payload = {
            "session_id": session_id,
            "draft": draft,
            "authority_summary": authority_summary,
            "run_dir": str(self.store.run_root),
        }
        if mission_id is not None:
            record_payload["mission_id"] = mission_id
        record = MissionRecord(**record_payload)
        return self.store.create_record(record)

    def list_missions(self) -> list[MissionRecord]:
        return self.store.list_records()

    def enqueue(self, mission_id: str, *, metadata: dict[str, object] | None = None) -> MissionRecord:
        with self.store.locked():
            self._assert_transition_allowed(mission_id, OperatorMissionStatus.QUEUED)
            record = self.store.update_record_status(mission_id, OperatorMissionStatus.QUEUED)
            self.store.append_event(
                mission_id,
                event_type="mission_queued",
                safe_summary="Mission queued.",
                metadata=dict(metadata or {}),
            )
            return record

    def update_status(
        self,
        mission_id: str,
        status: OperatorMissionStatus,
        safe_summary: str,
        *,
        pause_origin: str | None = None,
    ) -> MissionRecord:
        with self.store.locked():
            self._assert_transition_allowed(mission_id, status)
            record = self.store.update_record_status(mission_id, status, pause_origin=pause_origin)
            self.store.append_event(mission_id, event_type=f"mission_{status.value}", safe_summary=safe_summary)
            return record

    def pause(self, mission_id: str, *, origin: str = "operator") -> MissionRecord:
        return self.update_status(
            mission_id,
            OperatorMissionStatus.PAUSED,
            "Mission paused.",
            pause_origin=origin,
        )

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

    def record_memory_retrieval(
        self,
        mission_id: str,
        retrieval: PersistentMemoryRetrievalResult,
    ) -> MissionEvent:
        return self.store.append_event(
            mission_id,
            event_type="persistent_memory_retrieved",
            safe_summary=f"Persistent memory recall returned {len(retrieval.hits)} scoped record(s).",
            metadata={
                "query_hash": retrieval.query_hash,
                "record_count": len(retrieval.hits),
                "data_not_instruction": True,
                "authority_effect": "none",
            },
            memory_feedback_refs=[hit.record_id for hit in retrieval.hits],
        )

    def _assert_transition_allowed(self, mission_id: str, target_status: OperatorMissionStatus) -> None:
        current = self.store.load_record(mission_id).status
        if target_status is current:
            return
        if target_status in VALID_MISSION_TRANSITIONS[current]:
            return
        self.store.append_event(
            mission_id,
            event_type="mission_transition_rejected",
            safe_summary="Mission lifecycle transition rejected by canonical policy.",
            metadata={
                "current_status": current.value,
                "target_status": target_status.value,
                "terminal_source": current in TERMINAL_MISSION_STATUSES,
            },
        )
        raise MissionLifecycleError(
            f"mission {mission_id} cannot transition from {current.value} to {target_status.value}"
        )
