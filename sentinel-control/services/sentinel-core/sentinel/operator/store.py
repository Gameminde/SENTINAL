from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.models import MissionEvent, MissionRecord, OperatorMissionStatus, utc_now
from sentinel.operator.redaction import (
    redact_operator_text,
    redact_operator_value,
    sanitize_operator_refs,
)
from sentinel.operator.safety import reject_operator_control_payload


_STORE_LOCKS: dict[str, threading.RLock] = {}
_STORE_LOCKS_GUARD = threading.Lock()


def _filesystem_path(path: Path) -> str:
    rendered = str(path)
    if os.name != "nt" or rendered.startswith("\\\\?\\"):
        return rendered
    if rendered.startswith("\\\\"):
        return "\\\\?\\UNC\\" + rendered[2:]
    return "\\\\?\\" + rendered


def _mkdir_path(path: Path) -> None:
    os.makedirs(_filesystem_path(path), exist_ok=True)


def _path_exists(path: Path) -> bool:
    return os.path.exists(_filesystem_path(path))


def _read_text_file(path: Path) -> str:
    with open(_filesystem_path(path), encoding="utf-8") as handle:
        return handle.read()


def _read_bytes_file(path: Path) -> bytes:
    with open(_filesystem_path(path), "rb") as handle:
        return handle.read()


def _iter_child_paths(root: Path) -> list[Path]:
    if not _path_exists(root):
        return []
    return [root / name for name in os.listdir(_filesystem_path(root))]


def _iter_descendant_file_paths(root: Path) -> list[Path]:
    if not _path_exists(root):
        return []
    paths: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(_filesystem_path(root)):
        current = Path(dirpath)
        for filename in filenames:
            paths.append(current / filename)
    return paths


class MissionRunStore:
    def __init__(self, run_root: Path | str, *, telemetry_sink: Any | None = None) -> None:
        self.run_root = Path(run_root).resolve()
        _mkdir_path(self.run_root)
        if telemetry_sink is None:
            from sentinel.telemetry import TelemetryKernel

            telemetry_sink = TelemetryKernel(self.run_root / "telemetry")
        self._telemetry_sink = telemetry_sink
        self.telemetry_sink = self._telemetry_sink
        with _STORE_LOCKS_GUARD:
            self._lock = _STORE_LOCKS.setdefault(str(self.run_root), threading.RLock())

    def create_record(self, record: MissionRecord) -> MissionRecord:
        mission_dir = self._mission_dir(record.mission_id, create=True)
        record = record.model_copy(update={"run_dir": str(mission_dir)}).with_hash()
        self._write_record(record)
        self.append_event(record.mission_id, event_type="mission_created", safe_summary="Mission created.")
        return record

    def load_record(self, mission_id: str) -> MissionRecord:
        path = self._mission_dir(mission_id) / "record.json"
        record = MissionRecord.model_validate(json.loads(_read_text_file(path)))
        if not record.verify_hash():
            raise ValueError("mission record hash mismatch")
        return record

    def list_records(self) -> list[MissionRecord]:
        records: list[MissionRecord] = []
        for child in sorted(_iter_child_paths(self.run_root), key=lambda path: path.name):
            if not child.is_dir():
                continue
            record_path = child / "record.json"
            if _path_exists(record_path):
                record = MissionRecord.model_validate(json.loads(_read_text_file(record_path)))
                if not record.verify_hash():
                    raise ValueError("mission record hash mismatch")
                records.append(record)
        return sorted(records, key=lambda record: record.created_at)

    def update_record_status(
        self,
        mission_id: str,
        status: OperatorMissionStatus,
        *,
        pause_origin: str | None = None,
    ) -> MissionRecord:
        with self._lock:
            record = self.load_record(mission_id)
            updated = record.model_copy(
                update={
                    "status": status,
                    "pause_origin": pause_origin if status is OperatorMissionStatus.PAUSED else None,
                    "updated_at": utc_now(),
                }
            ).with_hash()
            self._write_record(updated)
            return updated

    def reserve_power_budget(
        self,
        mission_id: str,
        *,
        action_count: int,
        estimated_cost_usd: float,
        max_actions: int,
        max_cost_usd: float,
    ) -> MissionRecord:
        if action_count < 0 or estimated_cost_usd < 0:
            raise ValueError("power budget reservation invalid")
        with self._lock:
            record = self.load_record(mission_id)
            if record.power_actions_used + record.power_actions_reserved + action_count > max_actions:
                raise ValueError("mission power action budget exhausted")
            if record.power_cost_used_usd + record.power_cost_reserved_usd + estimated_cost_usd > max_cost_usd:
                raise ValueError("mission power cost budget exhausted")
            updated = record.model_copy(
                update={
                    "power_actions_reserved": record.power_actions_reserved + action_count,
                    "power_cost_reserved_usd": record.power_cost_reserved_usd + estimated_cost_usd,
                    "updated_at": utc_now(),
                }
            ).with_hash()
            self._write_record(updated)
            return updated

    def commit_power_budget(
        self,
        mission_id: str,
        *,
        reserved_actions: int,
        reserved_cost_usd: float,
        actual_actions: int,
        actual_cost_usd: float,
    ) -> MissionRecord:
        if actual_actions < 0 or actual_actions > reserved_actions:
            raise ValueError("mission power action debit invalid")
        if actual_cost_usd < 0 or actual_cost_usd > reserved_cost_usd:
            raise ValueError("mission power cost debit invalid")
        with self._lock:
            record = self.load_record(mission_id)
            if record.power_actions_reserved < reserved_actions or record.power_cost_reserved_usd < reserved_cost_usd:
                raise ValueError("mission power budget reservation missing")
            updated = record.model_copy(
                update={
                    "power_actions_reserved": record.power_actions_reserved - reserved_actions,
                    "power_cost_reserved_usd": record.power_cost_reserved_usd - reserved_cost_usd,
                    "power_actions_used": record.power_actions_used + max(actual_actions, 0),
                    "power_cost_used_usd": record.power_cost_used_usd + max(actual_cost_usd, 0.0),
                    "updated_at": utc_now(),
                }
            ).with_hash()
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
        with self._lock:
            metadata = redact_operator_value(metadata or {})
            reject_operator_control_payload(
                _mission_event_safety_payload(event_type=event_type, metadata=metadata),
                context="mission_event",
            )
            events = self.load_events(mission_id)
            previous_hash = events[-1].event_hash if events else None
            event = MissionEvent(
                mission_id=mission_id,
                sequence=len(events),
                event_type=event_type,
                safe_summary=redact_operator_text(safe_summary),
                metadata=metadata,
                receipt_refs=sanitize_operator_refs(receipt_refs or []),
                finalgate_certificate_refs=sanitize_operator_refs(finalgate_certificate_refs or []),
                memory_feedback_refs=sanitize_operator_refs(memory_feedback_refs or []),
                previous_hash=previous_hash,
                event_hash="",
            )
            event = event.model_copy(update={"event_hash": _hash_event(event)})
            path = self._mission_dir(mission_id) / "events.jsonl"
            with open(_filesystem_path(path), "a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True, default=str) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            if self._telemetry_sink is not None and hasattr(self._telemetry_sink, "record_mission_event"):
                try:
                    self._telemetry_sink.record_mission_event(event)
                except Exception:
                    if hasattr(self._telemetry_sink, "mark_degraded"):
                        self._telemetry_sink.mark_degraded("mission_event_forwarding_failed")
            return event

    def load_events(self, mission_id: str) -> list[MissionEvent]:
        path = self._mission_dir(mission_id) / "events.jsonl"
        if not _path_exists(path):
            return []
        return [
            MissionEvent.model_validate(json.loads(line))
            for line in _read_text_file(path).splitlines()
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

    def verify_record(self, mission_id: str) -> bool:
        try:
            return self.load_record(mission_id).verify_hash()
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False

    def _write_record(self, record: MissionRecord) -> None:
        path = self._mission_dir(record.mission_id, create=True) / "record.json"
        self.atomic_write_json(path, record.with_hash().safe_model_dump())

    def mission_dir(self, mission_id: str, *, create: bool = False) -> Path:
        return self._mission_dir(mission_id, create=create)

    @contextmanager
    def locked(self):
        with self._lock:
            yield

    def atomic_write_json(self, path: Path, payload: Any) -> None:
        path = path.resolve()
        if self.run_root not in path.parents:
            raise ValueError("write path escapes run root")
        _mkdir_path(path.parent)
        rendered = json.dumps(payload, sort_keys=True, indent=2, default=str)
        with self._lock:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=_filesystem_path(path.parent),
                prefix=".tmp.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = handle.name
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, _filesystem_path(path))

    def _mission_dir(self, mission_id: str, *, create: bool = False) -> Path:
        if not mission_id or any(sep in mission_id for sep in ("/", "\\")) or ".." in mission_id:
            raise ValueError("invalid mission id")
        path = (self.run_root / mission_id).resolve()
        if self.run_root not in path.parents and path != self.run_root:
            raise ValueError("mission path escapes run root")
        if create:
            _mkdir_path(path)
        return path


def _hash_event(event: MissionEvent) -> str:
    payload = event.model_dump(mode="json")
    payload["event_hash"] = ""
    return stable_hash(payload)


def _mission_event_safety_payload(*, event_type: str, metadata: dict[str, Any]) -> dict[str, Any]:
    if (
        event_type == "agentruntime_execution_event_observed"
        and isinstance(metadata.get("terminal"), bool)
    ):
        payload = dict(metadata)
        # In this event family, "terminal" is a runtime-state label, not a
        # shell/terminal action surface. Keep it stored, but scan the rest.
        payload.pop("terminal", None)
        return payload
    return metadata
