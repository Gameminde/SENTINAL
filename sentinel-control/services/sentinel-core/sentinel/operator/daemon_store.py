from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.daemon_models import (
    DaemonHeartbeatRecord,
    DaemonLease,
    DaemonLeaseOwner,
    DaemonQueueRecord,
    DaemonQueueStatus,
    DeadLetterReason,
    DeadLetterRecord,
    daemon_utc_now,
    sanitize_daemon_metadata,
)
from sentinel.operator.redaction import redact_operator_text
from sentinel.operator.store import MissionRunStore


class MissionDaemonStore:
    def __init__(self, mission_store: MissionRunStore) -> None:
        self.mission_store = mission_store

    def enqueue(
        self,
        mission_id: str,
        *,
        workflow_id: str | None = None,
        worker_fleet_run_id: str | None = None,
        safe_reason: str = "Mission queued for daemon supervision.",
        metadata: dict[str, Any] | None = None,
    ) -> DaemonQueueRecord:
        with self.mission_store.locked():
            self.mission_store.load_record(mission_id)
            existing = self.load_queue_record(mission_id, missing_ok=True)
            record = DaemonQueueRecord(
                mission_id=mission_id,
                workflow_id=workflow_id,
                worker_fleet_run_id=worker_fleet_run_id,
                status=DaemonQueueStatus.QUEUED,
                safe_reason=safe_reason,
                metadata=metadata or {},
            )
            if existing is not None:
                record = record.model_copy(update={"queue_id": existing.queue_id, "queued_at": existing.queued_at})
            record = record.with_hash()
            self._write_json(self._paths(mission_id).queue, record.safe_model_dump())
            self.append_event(
                mission_id,
                event_type="daemon_queue_enqueued",
                safe_summary="Mission queued for daemon supervision.",
                metadata={"workflow_id": workflow_id, "worker_fleet_run_id": worker_fleet_run_id, **(metadata or {})},
            )
            return record

    def update_queue_status(
        self,
        mission_id: str,
        status: DaemonQueueStatus,
        *,
        safe_reason: str,
        workflow_id: str | None = None,
        worker_fleet_run_id: str | None = None,
    ) -> DaemonQueueRecord:
        with self.mission_store.locked():
            current = self.load_queue_record(mission_id, missing_ok=True) or DaemonQueueRecord(mission_id=mission_id)
            updated = current.model_copy(
                update={
                    "status": status,
                    "safe_reason": redact_operator_text(safe_reason),
                    "workflow_id": workflow_id if workflow_id is not None else current.workflow_id,
                    "worker_fleet_run_id": worker_fleet_run_id if worker_fleet_run_id is not None else current.worker_fleet_run_id,
                    "updated_at": daemon_utc_now(),
                }
            ).with_hash()
            self._write_json(self._paths(mission_id).queue, updated.safe_model_dump())
            return updated

    def load_queue_record(self, mission_id: str, *, missing_ok: bool = False) -> DaemonQueueRecord | None:
        path = self._paths(mission_id).queue
        if not path.exists():
            if missing_ok:
                return None
            raise FileNotFoundError(f"daemon queue record not found: {mission_id}")
        record = DaemonQueueRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if not record.verify_hash():
            raise ValueError("daemon queue record hash mismatch")
        return record

    def list_queue(self) -> list[DaemonQueueRecord]:
        records: list[DaemonQueueRecord] = []
        for mission in self.mission_store.list_records():
            record = self.load_queue_record(mission.mission_id, missing_ok=True)
            if record is not None:
                records.append(record)
        return sorted(records, key=lambda item: (item.queued_at, item.mission_id))

    def claim_lease(
        self,
        mission_id: str,
        *,
        owner: DaemonLeaseOwner,
        now,
        ttl_seconds: int,
        allow_stale_takeover: bool = False,
    ) -> DaemonLease:
        with self.mission_store.locked():
            self.mission_store.load_record(mission_id)
            current = self.load_active_lease(mission_id, missing_ok=True)
            takeover_owner: str | None = None
            takeover_proof_hash: str | None = None
            if current and current.owner.owner_id != owner.owner_id and not current.is_stale(now):
                self.append_event(
                    mission_id,
                    event_type="daemon_lease_rejected",
                    safe_summary="Daemon lease rejected because another owner is active.",
                    metadata={"active_owner_id": current.owner.owner_id, "candidate_owner_id": owner.owner_id},
                )
                raise ValueError("daemon_lease_owned_by_another_daemon")
            if current and current.owner.owner_id != owner.owner_id and current.is_stale(now):
                if not allow_stale_takeover:
                    self.append_event(
                        mission_id,
                        event_type="daemon_lease_rejected",
                        safe_summary="Daemon lease takeover rejected without stale proof.",
                        metadata={"active_owner_id": current.owner.owner_id, "candidate_owner_id": owner.owner_id},
                    )
                    raise ValueError("daemon_lease_takeover_requires_stale_proof")
                takeover_owner = current.owner.owner_id
                takeover_proof_hash = stable_hash(current.safe_model_dump())
                self.append_event(
                    mission_id,
                    event_type="daemon_lease_expired",
                    safe_summary="Stale daemon lease detected before takeover.",
                    metadata={"previous_owner_id": takeover_owner, "lease_id": current.lease_id},
                )
            lease = DaemonLease.create(
                mission_id=mission_id,
                owner=owner,
                now=now,
                ttl_seconds=ttl_seconds,
                takeover_of_owner_id=takeover_owner,
                stale_takeover_proof_hash=takeover_proof_hash,
            )
            paths = self._paths(mission_id)
            self._write_json(paths.active_lease, lease.safe_model_dump())
            self._write_json(paths.leases / f"{lease.lease_id}.json", lease.safe_model_dump())
            self.append_event(
                mission_id,
                event_type="daemon_lease_claimed",
                safe_summary="Daemon lease claimed.",
                metadata={
                    "lease_id": lease.lease_id,
                    "owner_id": owner.owner_id,
                    "takeover_of_owner_id": takeover_owner,
                },
            )
            return lease

    def renew_lease(self, mission_id: str, *, owner_id: str, now, ttl_seconds: int) -> DaemonLease:
        with self.mission_store.locked():
            current = self.require_owned_lease(mission_id, owner_id=owner_id, now=now)
            renewed = current.model_copy(
                update={
                    "expires_at": now + timedelta(seconds=ttl_seconds),
                    "heartbeat_deadline_at": now + timedelta(seconds=ttl_seconds),
                }
            ).with_hash()
            paths = self._paths(mission_id)
            self._write_json(paths.active_lease, renewed.safe_model_dump())
            self._write_json(paths.leases / f"{renewed.lease_id}.json", renewed.safe_model_dump())
            self.append_event(
                mission_id,
                event_type="daemon_lease_renewed",
                safe_summary="Daemon lease renewed.",
                metadata={"lease_id": renewed.lease_id, "owner_id": owner_id},
            )
            return renewed

    def release_lease(self, mission_id: str, *, owner_id: str, now) -> DaemonLease:
        with self.mission_store.locked():
            current = self.require_owned_lease(mission_id, owner_id=owner_id, now=now)
            released = current.model_copy(update={"released_at": now}).with_hash()
            paths = self._paths(mission_id)
            self._write_json(paths.active_lease, released.safe_model_dump())
            self._write_json(paths.leases / f"{released.lease_id}.json", released.safe_model_dump())
            self.append_event(
                mission_id,
                event_type="daemon_lease_released",
                safe_summary="Daemon lease released.",
                metadata={"lease_id": released.lease_id, "owner_id": owner_id},
            )
            return released

    def emit_heartbeat(self, mission_id: str, *, owner_id: str, now, safe_summary: str) -> DaemonHeartbeatRecord:
        with self.mission_store.locked():
            lease = self.require_owned_lease(mission_id, owner_id=owner_id, now=now)
            heartbeat = DaemonHeartbeatRecord(
                lease_id=lease.lease_id,
                mission_id=mission_id,
                owner_id=owner_id,
                emitted_at=now,
                safe_summary=safe_summary,
            ).with_hash()
            paths = self._paths(mission_id)
            self._write_json(paths.heartbeats / f"{heartbeat.heartbeat_id}.json", heartbeat.safe_model_dump())
            self.append_event(
                mission_id,
                event_type="daemon_heartbeat_emitted",
                safe_summary=heartbeat.safe_summary,
                metadata={"lease_id": lease.lease_id, "heartbeat_id": heartbeat.heartbeat_id, "owner_id": owner_id},
            )
            return heartbeat

    def require_owned_lease(self, mission_id: str, *, owner_id: str, now) -> DaemonLease:
        lease = self.load_active_lease(mission_id, missing_ok=True)
        if lease is None:
            raise ValueError("daemon_lease_required")
        if lease.owner.owner_id != owner_id:
            raise ValueError("daemon_lease_owned_by_another_daemon")
        if lease.is_stale(now):
            self.append_event(
                mission_id,
                event_type="daemon_lease_expired",
                safe_summary="Daemon lease expired before execution.",
                metadata={"lease_id": lease.lease_id, "owner_id": owner_id},
            )
            raise ValueError("daemon_lease_stale")
        if not lease.verify_hash():
            raise ValueError("daemon_lease_hash_mismatch")
        return lease

    def load_active_lease(self, mission_id: str, *, missing_ok: bool = False) -> DaemonLease | None:
        path = self._paths(mission_id).active_lease
        if not path.exists():
            if missing_ok:
                return None
            raise FileNotFoundError(f"daemon lease not found: {mission_id}")
        lease = DaemonLease.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if not lease.verify_hash():
            raise ValueError("daemon lease hash mismatch")
        return lease

    def list_leases(self) -> list[DaemonLease]:
        leases: list[DaemonLease] = []
        for mission in self.mission_store.list_records():
            paths = self._paths(mission.mission_id)
            for path in sorted(paths.leases.glob("*.json"), key=lambda item: item.name):
                lease = DaemonLease.model_validate(json.loads(path.read_text(encoding="utf-8")))
                if not lease.verify_hash():
                    raise ValueError("daemon lease hash mismatch")
                leases.append(lease)
        return leases

    def list_heartbeats(self) -> list[DaemonHeartbeatRecord]:
        heartbeats: list[DaemonHeartbeatRecord] = []
        for mission in self.mission_store.list_records():
            paths = self._paths(mission.mission_id)
            for path in sorted(paths.heartbeats.glob("*.json"), key=lambda item: item.name):
                heartbeat = DaemonHeartbeatRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
                if not heartbeat.verify_hash():
                    raise ValueError("daemon heartbeat hash mismatch")
                heartbeats.append(heartbeat)
        return heartbeats

    def create_dead_letter(
        self,
        mission_id: str,
        *,
        reason: DeadLetterReason,
        safe_summary: str,
        workflow_id: str | None = None,
        worker_fleet_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> DeadLetterRecord:
        with self.mission_store.locked():
            record = DeadLetterRecord(
                mission_id=mission_id,
                reason=reason,
                safe_summary=safe_summary,
                workflow_id=workflow_id,
                worker_fleet_run_id=worker_fleet_run_id,
                metadata=metadata or {},
                receipt_refs=receipt_refs or [],
                finalgate_certificate_refs=finalgate_certificate_refs or [],
                memory_feedback_refs=memory_feedback_refs or [],
            ).with_hash()
            paths = self._paths(mission_id)
            self._write_json(paths.dead_letters / f"{record.dead_letter_id}.json", record.safe_model_dump())
            self.update_queue_status(mission_id, DaemonQueueStatus.DEAD_LETTER, safe_reason=safe_summary, workflow_id=workflow_id, worker_fleet_run_id=worker_fleet_run_id)
            self.append_event(
                mission_id,
                event_type="daemon_dead_letter_created",
                safe_summary=safe_summary,
                metadata={"dead_letter_id": record.dead_letter_id, "reason": reason.value, **(metadata or {})},
                receipt_refs=record.receipt_refs,
                finalgate_certificate_refs=record.finalgate_certificate_refs,
                memory_feedback_refs=record.memory_feedback_refs,
            )
            self.append_event(
                mission_id,
                event_type="operator_notification_created",
                safe_summary="Operator notification created for daemon dead-letter state.",
                metadata={"dead_letter_id": record.dead_letter_id, "reason": reason.value},
            )
            return record

    def list_dead_letters(self) -> list[DeadLetterRecord]:
        records: list[DeadLetterRecord] = []
        for mission in self.mission_store.list_records():
            paths = self._paths(mission.mission_id)
            for path in sorted(paths.dead_letters.glob("*.json"), key=lambda item: item.name):
                record = DeadLetterRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
                if not record.verify_hash():
                    raise ValueError("daemon dead-letter hash mismatch")
                records.append(record)
        return records

    def list_dead_letters_for_mission(self, mission_id: str) -> list[DeadLetterRecord]:
        return [record for record in self.list_dead_letters() if record.mission_id == mission_id]

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
    ):
        return self.mission_store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=redact_operator_text(safe_summary),
            metadata=sanitize_daemon_metadata(metadata or {}),
            receipt_refs=receipt_refs or [],
            finalgate_certificate_refs=finalgate_certificate_refs or [],
            memory_feedback_refs=memory_feedback_refs or [],
        )

    def verify(self, mission_id: str) -> bool:
        try:
            record = self.load_queue_record(mission_id, missing_ok=True)
            if record is not None and not record.verify_hash():
                return False
            lease = self.load_active_lease(mission_id, missing_ok=True)
            if lease is not None and not lease.verify_hash():
                return False
            for dead_letter in self.list_dead_letters_for_mission(mission_id):
                if not dead_letter.verify_hash():
                    return False
            return self.mission_store.verify_timeline(mission_id)
        except (OSError, ValueError, json.JSONDecodeError):
            return False

    def _write_json(self, path: Path, payload: Any) -> None:
        self.mission_store.atomic_write_json(path, payload)

    def _paths(self, mission_id: str) -> _DaemonPaths:
        root = self.mission_store.mission_dir(mission_id, create=True) / "daemon"
        root.mkdir(parents=True, exist_ok=True)
        return _DaemonPaths(root)


class _DaemonPaths:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.queue = root / "queue.json"
        self.active_lease = root / "active_lease.json"
        self.leases = root / "leases"
        self.heartbeats = root / "heartbeats"
        self.dead_letters = root / "dead_letters"
        self.leases.mkdir(parents=True, exist_ok=True)
        self.heartbeats.mkdir(parents=True, exist_ok=True)
        self.dead_letters.mkdir(parents=True, exist_ok=True)
