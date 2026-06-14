from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.daemon_models import (
    DaemonCertifiedModeSnapshot,
    DaemonLease,
    DaemonLeaseOwner,
    DaemonQueueStatus,
    DaemonRecoveryPlan,
    DaemonStatusView,
    DaemonTickResult,
    DeadLetterReason,
    DeadLetterRecord,
    MissionDaemonConfig,
    daemon_utc_now,
)
from sentinel.operator.daemon_store import MissionDaemonStore
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.workflow_models import WorkflowStatus
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime


class MissionDaemonRuntimeError(RuntimeError):
    pass


class MissionDaemonRuntime:
    """Production local daemon supervisor over the existing MissionKernel spine.

    The daemon owns leases, heartbeats, queue supervision, recovery records, and
    scheduler handoff evidence. It never creates authority and never calls organs
    directly; runtime execution remains delegated to DurableMissionWorkflowRuntime,
    WorkerFleetRuntime, PowerRuntime, or AgentRuntime bridges that already enforce
    gates, receipts, FinalGate, telemetry, and replay.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        config: MissionDaemonConfig | None = None,
        workflow_runtime: DurableMissionWorkflowRuntime | None = None,
        worker_fleet_runtime: object | None = None,
    ) -> None:
        self.kernel = kernel
        self.config = config or MissionDaemonConfig()
        self.store = MissionDaemonStore(kernel.store)
        self.workflow_runtime = workflow_runtime or DurableMissionWorkflowRuntime(kernel)
        self.worker_fleet_runtime = worker_fleet_runtime
        self._started_at: datetime | None = None

    def certified_mode_snapshot(self) -> DaemonCertifiedModeSnapshot:
        telemetry = getattr(self.kernel, "telemetry_sink", None)
        if telemetry is None or not hasattr(telemetry, "certified_mode_status"):
            return DaemonCertifiedModeSnapshot(certified_mode=False, reasons=["telemetry_unavailable"])
        return DaemonCertifiedModeSnapshot.from_telemetry(telemetry.certified_mode_status())

    def start(self, *, mission_id: str | None = None) -> None:
        self._started_at = self._started_at or daemon_utc_now()
        if mission_id:
            self.store.append_event(
                mission_id,
                event_type="daemon_started",
                safe_summary="Mission daemon runtime started.",
                metadata={"owner_id": self.config.owner_id},
            )

    def stop(self, *, mission_id: str | None = None) -> None:
        if self._started_at is not None and mission_id:
            uptime = max(0.0, (daemon_utc_now() - self._started_at).total_seconds())
            self._record_daemon_metric(
                mission_id,
                metric_kind="daemon_uptime",
                value=uptime,
                unit="seconds",
                safe_summary="Daemon uptime sample.",
            )
            self._record_daemon_metric(
                mission_id,
                metric_kind="mission_background_useful_minutes",
                value=max(0.0, uptime / 60.0),
                unit="minutes",
                safe_summary="Mission background useful minutes sample.",
            )
        if mission_id:
            self.store.append_event(
                mission_id,
                event_type="daemon_stopped",
                safe_summary="Mission daemon runtime stopped.",
                metadata={"owner_id": self.config.owner_id},
            )

    def enqueue(
        self,
        mission_id: str,
        *,
        workflow_id: str | None = None,
        worker_fleet_run_id: str | None = None,
        safe_reason: str = "Mission queued for daemon supervision.",
        metadata: dict[str, Any] | None = None,
    ):
        return self.store.enqueue(
            mission_id,
            workflow_id=workflow_id,
            worker_fleet_run_id=worker_fleet_run_id,
            safe_reason=safe_reason,
            metadata=metadata,
        )

    def claim_lease(self, mission_id: str, *, now: datetime | None = None, allow_stale_takeover: bool = False) -> DaemonLease:
        self._require_certified_mode()
        now = now or daemon_utc_now()
        started = daemon_utc_now()
        try:
            lease = self.store.claim_lease(
                mission_id,
                owner=DaemonLeaseOwner(owner_id=self.config.owner_id),
                now=now,
                ttl_seconds=self.config.lease_ttl_seconds,
                allow_stale_takeover=allow_stale_takeover,
            )
            self._record_daemon_metric(
                mission_id,
                metric_kind="lease_claim_latency",
                value=max(0.0, (daemon_utc_now() - started).total_seconds()),
                unit="seconds",
                safe_summary="Daemon lease claim latency sample.",
            )
            if lease.takeover_of_owner_id:
                self._record_daemon_metric(
                    mission_id,
                    metric_kind="stale_lease_count",
                    value=1,
                    unit="count",
                    safe_summary="Stale lease takeover sample.",
                )
            return lease
        except ValueError as exc:
            raise MissionDaemonRuntimeError(str(exc)) from exc

    def renew_lease(self, mission_id: str, *, now: datetime | None = None) -> DaemonLease:
        self._require_certified_mode()
        try:
            return self.store.renew_lease(
                mission_id,
                owner_id=self.config.owner_id,
                now=now or daemon_utc_now(),
                ttl_seconds=self.config.lease_ttl_seconds,
            )
        except ValueError as exc:
            raise MissionDaemonRuntimeError(str(exc)) from exc

    def release_lease(self, mission_id: str, *, now: datetime | None = None) -> DaemonLease:
        try:
            return self.store.release_lease(mission_id, owner_id=self.config.owner_id, now=now or daemon_utc_now())
        except ValueError as exc:
            raise MissionDaemonRuntimeError(str(exc)) from exc

    def emit_heartbeat(
        self,
        mission_id: str,
        *,
        now: datetime | None = None,
        safe_summary: str = "Daemon heartbeat emitted.",
    ):
        self._require_certified_mode()
        try:
            heartbeat = self.store.emit_heartbeat(
                mission_id,
                owner_id=self.config.owner_id,
                now=now or daemon_utc_now(),
                safe_summary=safe_summary,
            )
            self._record_daemon_metric(
                mission_id,
                metric_kind="heartbeat_interval",
                value=self.config.heartbeat_interval_seconds,
                unit="seconds",
                safe_summary="Daemon heartbeat interval sample.",
            )
            return heartbeat
        except ValueError as exc:
            raise MissionDaemonRuntimeError(str(exc)) from exc

    def tick(
        self,
        mission_id: str,
        *,
        current_envelope: MissionAuthorityEnvelope,
        workflow_id: str | None = None,
        now: datetime | None = None,
        max_steps: int | None = None,
    ) -> DaemonTickResult:
        self._require_certified_mode()
        if not self.kernel.store.verify_record(mission_id):
            raise MissionDaemonRuntimeError("mission_record_tampered")
        now = now or datetime.now(UTC)
        started = datetime.now(UTC)
        try:
            self.store.require_owned_lease(mission_id, owner_id=self.config.owner_id, now=now)
        except ValueError as exc:
            raise MissionDaemonRuntimeError(str(exc)) from exc
        if current_envelope.id != mission_id:
            raise MissionDaemonRuntimeError("mission_authority_mismatch")
        self.store.append_event(
            mission_id,
            event_type="daemon_tick_started",
            safe_summary="Daemon tick started.",
            metadata={"workflow_id": workflow_id, "owner_id": self.config.owner_id},
        )
        mission = self.kernel.store.load_record(mission_id)
        authority_failure = self._authority_failure(current_envelope, now)
        if authority_failure is not None:
            reason, summary = authority_failure
            try:
                if reason is DeadLetterReason.AUTHORITY_REVOKED:
                    self.kernel.update_status(mission_id, OperatorMissionStatus.REVOKED, "Mission authority revoked before daemon tick.")
                else:
                    self.kernel.update_status(mission_id, OperatorMissionStatus.BLOCKED, "Mission authority expired before daemon tick.")
            except Exception:
                pass
            dead_letter = self.dead_letter(mission_id, reason=reason, safe_summary=summary, workflow_id=workflow_id)
            return self._complete_tick(
                mission_id,
                DaemonTickResult(
                    mission_id=mission_id,
                    status=DaemonQueueStatus.DEAD_LETTER,
                    executed=False,
                    workflow_id=workflow_id,
                    dead_letter_reason=dead_letter.reason,
                    safe_summary=summary,
                ),
                started_at=started,
            )
        if mission.status is OperatorMissionStatus.PAUSED:
            self.store.update_queue_status(mission_id, DaemonQueueStatus.PAUSED, safe_reason="Mission paused before daemon tick.")
            return self._complete_tick(
                mission_id,
                DaemonTickResult(
                    mission_id=mission_id,
                    status=DaemonQueueStatus.PAUSED,
                    executed=False,
                    workflow_id=workflow_id,
                    safe_summary="Mission paused; daemon did not execute.",
                ),
                started_at=started,
            )
        if mission.status is OperatorMissionStatus.KILLED:
            self.store.update_queue_status(mission_id, DaemonQueueStatus.KILLED, safe_reason="Mission killed before daemon tick.")
            return self._complete_tick(
                mission_id,
                DaemonTickResult(
                    mission_id=mission_id,
                    status=DaemonQueueStatus.KILLED,
                    executed=False,
                    workflow_id=workflow_id,
                    safe_summary="Mission killed; daemon did not execute.",
                ),
                started_at=started,
            )
        if workflow_id is None:
            queued = self.store.update_queue_status(
                mission_id,
                DaemonQueueStatus.RUNNING,
                safe_reason="Daemon tick verified lease and authority; no workflow id was supplied.",
            )
            return self._complete_tick(
                mission_id,
                DaemonTickResult(
                    mission_id=mission_id,
                    status=queued.status,
                    executed=False,
                    safe_summary="Daemon supervised mission without workflow execution.",
                ),
                started_at=started,
            )
        try:
            workflow_result = self.workflow_runtime.run_power_tick(
                workflow_id,
                current_envelope=current_envelope,
                max_steps=max_steps or self.config.max_tick_steps,
            )
        except Exception as exc:  # noqa: BLE001
            dead_letter = self.dead_letter(
                mission_id,
                reason=DeadLetterReason.RUNTIME_FAILURE,
                safe_summary=f"Daemon workflow tick failed safely: {exc.__class__.__name__}.",
                workflow_id=workflow_id,
            )
            self.store.append_event(
                mission_id,
                event_type="daemon_tick_failed",
                safe_summary="Daemon tick failed and created a dead-letter record.",
                metadata={"workflow_id": workflow_id, "dead_letter_id": dead_letter.dead_letter_id},
            )
            return DaemonTickResult(
                mission_id=mission_id,
                status=DaemonQueueStatus.DEAD_LETTER,
                executed=False,
                workflow_id=workflow_id,
                dead_letter_reason=dead_letter.reason,
                safe_summary="Daemon workflow tick failed safely.",
            )
        status = _queue_status_from_workflow(workflow_result.status)
        self.store.update_queue_status(
            mission_id,
            status,
            safe_reason=workflow_result.safe_summary,
            workflow_id=workflow_id,
        )
        return self._complete_tick(
            mission_id,
            DaemonTickResult(
                mission_id=mission_id,
                status=status,
                executed=True,
                workflow_id=workflow_id,
                latest_checkpoint_id=workflow_result.latest_checkpoint_id,
                receipt_refs=workflow_result.receipt_refs,
                finalgate_certificate_refs=workflow_result.finalgate_certificate_refs,
                memory_feedback_refs=workflow_result.memory_feedback_refs,
                safe_summary=workflow_result.safe_summary,
            ),
            started_at=started,
        )

    def recover(self, mission_id: str) -> DaemonRecoveryPlan:
        self.store.append_event(
            mission_id,
            event_type="daemon_recovery_started",
            safe_summary="Daemon recovery inspection started.",
            metadata={"owner_id": self.config.owner_id},
        )
        queue_record = self.store.load_queue_record(mission_id, missing_ok=True)
        active_lease = self.store.load_active_lease(mission_id, missing_ok=True)
        workflow_ok = True
        if queue_record and queue_record.workflow_id:
            workflow_ok = self.workflow_runtime.store.verify(queue_record.workflow_id)
        event_type = "daemon_recovery_completed" if workflow_ok else "daemon_recovery_failed"
        self.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary="Daemon recovery inspection completed." if workflow_ok else "Daemon recovery inspection failed.",
            metadata={"workflow_id": queue_record.workflow_id if queue_record else None},
        )
        if not workflow_ok and queue_record is not None:
            dead_letter = self.dead_letter(
                mission_id,
                reason=DeadLetterReason.UNRECOVERABLE_WORKFLOW,
                safe_summary="Workflow recovery failed; mission moved to dead-letter.",
                workflow_id=queue_record.workflow_id,
            )
            self.store.append_event(
                mission_id,
                event_type="operator_handoff_created",
                safe_summary="Operator handoff created after unrecoverable workflow inspection.",
                metadata={"dead_letter_id": dead_letter.dead_letter_id, "workflow_id": queue_record.workflow_id},
            )
            self._record_daemon_metric(
                mission_id,
                metric_kind="operator_handoff_count",
                value=1,
                unit="count",
                safe_summary="Operator handoff count sample.",
            )
            self._record_daemon_metric(
                mission_id,
                metric_kind="crash_recovery_success_rate",
                value=0,
                unit="ratio",
                safe_summary="Crash recovery failure sample.",
            )
        elif workflow_ok:
            self._record_daemon_metric(
                mission_id,
                metric_kind="crash_recovery_success_rate",
                value=1,
                unit="ratio",
                safe_summary="Crash recovery success sample.",
            )
        latest_checkpoint_id = None
        if queue_record and queue_record.workflow_id:
            try:
                latest_checkpoint_id = self.workflow_runtime.store.load(queue_record.workflow_id).latest_checkpoint_id
            except Exception:
                latest_checkpoint_id = None
        return DaemonRecoveryPlan(
            mission_id=mission_id,
            workflow_id=queue_record.workflow_id if queue_record else None,
            recovery_reason="Daemon recovery inspection completed." if workflow_ok else "Daemon recovery inspection failed.",
            safe_steps=[
                "restore queue state from mission store",
                "verify workflow checkpoints",
                "resume under valid lease",
            ]
            if workflow_ok
            else [
                "dead-letter unrecoverable mission",
                "handoff to operator",
            ],
            checkpoint_id=latest_checkpoint_id,
            lease_id=active_lease.lease_id if active_lease else None,
        )

    def dead_letter(
        self,
        mission_id: str,
        *,
        reason: DeadLetterReason,
        safe_summary: str,
        workflow_id: str | None = None,
        worker_fleet_run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DeadLetterRecord:
        record = self.store.create_dead_letter(
            mission_id,
            reason=reason,
            safe_summary=safe_summary,
            workflow_id=workflow_id,
            worker_fleet_run_id=worker_fleet_run_id,
            metadata=metadata,
        )
        self._record_daemon_metric(
            mission_id,
            metric_kind="dead_letter_rate",
            value=1,
            unit="count",
            safe_summary="Daemon dead-letter rate sample.",
            metadata={"reason": reason.value},
        )
        return record

    def status_view(self) -> DaemonStatusView:
        return DaemonStatusView(
            queue=self.store.list_queue(),
            leases=self.store.list_leases(),
            heartbeats=self.store.list_heartbeats(),
            dead_letters=self.store.list_dead_letters(),
            certified_mode=self.certified_mode_snapshot(),
        )

    def _require_certified_mode(self) -> None:
        if not self.config.require_certified_telemetry:
            return
        sink = getattr(self.kernel, "telemetry_sink", None)
        if sink is not None and hasattr(sink, "require_material_execution"):
            try:
                sink.require_material_execution("mission_daemon")
                return
            except Exception as exc:
                raise MissionDaemonRuntimeError("daemon_certified_telemetry_required:telemetry_unavailable") from exc
        snapshot = self.certified_mode_snapshot()
        if not snapshot.certified_mode:
            reason = ",".join(snapshot.reasons) or "telemetry_unavailable"
            raise MissionDaemonRuntimeError(f"daemon_certified_telemetry_required:{reason}")

    def _complete_tick(self, mission_id: str, result: DaemonTickResult, *, started_at: datetime) -> DaemonTickResult:
        latency = max(0.0, (datetime.now(UTC) - started_at).total_seconds())
        self.store.append_event(
            mission_id,
            event_type="daemon_tick_completed",
            safe_summary=result.safe_summary,
            metadata={
                "workflow_id": result.workflow_id,
                "status": result.status.value,
                "executed": result.executed,
                "latest_checkpoint_id": result.latest_checkpoint_id,
            },
            receipt_refs=result.receipt_refs,
            finalgate_certificate_refs=result.finalgate_certificate_refs,
            memory_feedback_refs=result.memory_feedback_refs,
        )
        self._record_daemon_metric(
            mission_id,
            metric_kind="daemon_tick_latency",
            value=latency,
            unit="seconds",
            safe_summary="Daemon tick latency sample.",
        )
        return result

    def _record_daemon_metric(
        self,
        mission_id: str,
        *,
        metric_kind: str,
        value: Any,
        unit: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        telemetry = getattr(self.kernel, "telemetry_sink", None)
        if telemetry is None or not hasattr(telemetry, "store"):
            return
        try:
            from sentinel.telemetry import TelemetryDomain, TelemetryMetricKind, TelemetryMetricSample, TelemetrySourceSurface

            telemetry.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_DAEMON,
                    domain=TelemetryDomain.OPERATIONAL,
                    metric_kind=TelemetryMetricKind(metric_kind),
                    value=value,
                    unit=unit,
                    safe_summary=safe_summary,
                    metadata=metadata or {},
                )
            )
        except Exception:
            return

    @staticmethod
    def _authority_failure(envelope: MissionAuthorityEnvelope, now: datetime) -> tuple[DeadLetterReason, str] | None:
        if envelope.revoked_at is not None:
            return DeadLetterReason.AUTHORITY_REVOKED, "Mission authority revoked; daemon failed closed."
        if now > envelope.resolved_expires_at():
            return DeadLetterReason.AUTHORITY_EXPIRED, "Mission authority expired; daemon failed closed."
        return None


def _queue_status_from_workflow(status: WorkflowStatus) -> DaemonQueueStatus:
    if status is WorkflowStatus.COMPLETED:
        return DaemonQueueStatus.COMPLETED
    if status is WorkflowStatus.PAUSED:
        return DaemonQueueStatus.PAUSED
    if status is WorkflowStatus.KILLED:
        return DaemonQueueStatus.KILLED
    if status in {WorkflowStatus.BLOCKED, WorkflowStatus.WAITING_USER, WorkflowStatus.WAITING_REPLAN}:
        return DaemonQueueStatus.BLOCKED
    if status is WorkflowStatus.FAILED:
        return DaemonQueueStatus.FAILED
    return DaemonQueueStatus.RUNNING
