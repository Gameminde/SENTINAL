from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.models import MissionEvent, MissionRecord, OperatorMissionStatus, utc_now
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.safety import reject_operator_control_payload


class MissionRunStore:
    def __init__(self, run_root: Path | str) -> None:
        self.run_root = Path(run_root).resolve()
        self.run_root.mkdir(parents=True, exist_ok=True)

    def create_record(self, record: MissionRecord) -> MissionRecord:
        mission_dir = self._mission_dir(record.mission_id, create=True)
        record = record.model_copy(update={"run_dir": str(mission_dir)})
        self._write_record(record)
        self.append_event(record.mission_id, event_type="mission_created", safe_summary="Mission created.")
        return record

    def load_record(self, mission_id: str) -> MissionRecord:
        path = self._mission_dir(mission_id) / "record.json"
        return MissionRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_records(self) -> list[MissionRecord]:
        records: list[MissionRecord] = []
        for child in sorted(self.run_root.iterdir(), key=lambda path: path.name):
            if not child.is_dir():
                continue
            record_path = child / "record.json"
            if record_path.exists():
                records.append(MissionRecord.model_validate(json.loads(record_path.read_text(encoding="utf-8"))))
        return sorted(records, key=lambda record: record.created_at)

    def update_record_status(self, mission_id: str, status: OperatorMissionStatus) -> MissionRecord:
        record = self.load_record(mission_id)
        updated = record.model_copy(update={"status": status, "updated_at": utc_now()})
        self._write_record(updated)
        return updated

    def append_event(
        self,
        mission_id: str,
        *,
        event_type: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> MissionEvent:
        metadata = metadata or {}
        reject_operator_control_payload(metadata, context="mission_event")
        events = self.load_events(mission_id)
        previous_hash = events[-1].event_hash if events else None
        event = MissionEvent(
            mission_id=mission_id,
            sequence=len(events),
            event_type=event_type,
            safe_summary=redact_operator_text(safe_summary),
            metadata=metadata,
            receipt_refs=list(receipt_refs or []),
            finalgate_certificate_refs=list(finalgate_certificate_refs or []),
            memory_feedback_refs=list(memory_feedback_refs or []),
            previous_hash=previous_hash,
            event_hash="",
        )
        event = event.model_copy(update={"event_hash": _hash_event(event)})
        path = self._mission_dir(mission_id) / "events.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True, default=str) + "\n")
        return event

    def load_events(self, mission_id: str) -> list[MissionEvent]:
        path = self._mission_dir(mission_id) / "events.jsonl"
        if not path.exists():
            return []
        return [
            MissionEvent.model_validate(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def verify_timeline(self, mission_id: str) -> bool:
        previous_hash: str | None = None
        for index, event in enumerate(self.load_events(mission_id)):
            if event.sequence != index:
                return False
            if event.previous_hash != previous_hash:
                return False
            if _hash_event(event) != event.event_hash:
                return False
            previous_hash = event.event_hash
        return True

    def _write_record(self, record: MissionRecord) -> None:
        path = self._mission_dir(record.mission_id, create=True) / "record.json"
        path.write_text(json.dumps(record.safe_model_dump(), sort_keys=True, indent=2, default=str), encoding="utf-8")

    def _mission_dir(self, mission_id: str, *, create: bool = False) -> Path:
        if not mission_id or any(sep in mission_id for sep in ("/", "\\")) or ".." in mission_id:
            raise ValueError("invalid mission id")
        path = (self.run_root / mission_id).resolve()
        if self.run_root not in path.parents and path != self.run_root:
            raise ValueError("mission path escapes run root")
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path


def _hash_event(event: MissionEvent) -> str:
    payload = event.model_dump(mode="json")
    payload["event_hash"] = ""
    return stable_hash(payload)
