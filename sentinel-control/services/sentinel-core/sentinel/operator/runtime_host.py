from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from sentinel.operator.authority_issuer import MissionAuthorityEnvelopeIssuer
from sentinel.operator.daemon_models import MissionDaemonConfig, daemon_utc_now
from sentinel.operator.daemon_runtime import MissionDaemonRuntime
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.mission_execution_coordinator import MissionExecutionCoordinator
from sentinel.operator.mission_lifecycle_service import MissionLifecycleService
from sentinel.operator.runtime_connections import RuntimeConnectionRegistry, build_default_runtime_connection_registry
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime
from sentinel.shared.models import SentinelModel


class RuntimeHostStatus(StrEnum):
    CREATED = "created"
    STARTED = "started"
    STOPPED = "stopped"


class RuntimeHostStatusView(SentinelModel):
    status: RuntimeHostStatus
    started: bool
    daemon_available: bool
    connection_count: int
    active_mission_count: int = 0
    host: object = Field(exclude=True)


class RuntimeHostDaemonPumpResult(SentinelModel):
    mission_id: str
    execution_request_ref: str
    claimed: bool
    tick_result: object = Field(exclude=True)


class SentinelRuntimeHost:
    """Process-level owner for Pack 1 operator runtime infrastructure."""

    def __init__(
        self,
        *,
        run_root: Path | str,
        telemetry_sink: object | None = None,
        daemon_config: MissionDaemonConfig | None = None,
        connection_registry: RuntimeConnectionRegistry | None = None,
    ) -> None:
        self.kernel = MissionKernel(run_root=run_root, telemetry_sink=telemetry_sink)
        self.connection_registry = connection_registry or build_default_runtime_connection_registry()
        self.coordinator = MissionExecutionCoordinator(self.connection_registry)
        self.authority_issuer = MissionAuthorityEnvelopeIssuer(self.kernel)
        self.workflow_runtime = DurableMissionWorkflowRuntime(self.kernel)
        self.daemon = MissionDaemonRuntime(
            self.kernel,
            config=daemon_config or MissionDaemonConfig(require_certified_telemetry=False),
            workflow_runtime=self.workflow_runtime,
        )
        self.lifecycle = MissionLifecycleService(
            self.kernel,
            authority_issuer=self.authority_issuer,
            daemon_runtime=self.daemon,
        )
        self._status = RuntimeHostStatus.CREATED

    def start(self) -> RuntimeHostStatusView:
        if self._status is RuntimeHostStatus.STARTED:
            return self.status()
        self.daemon.start()
        self._status = RuntimeHostStatus.STARTED
        return self.status()

    def shutdown(self) -> RuntimeHostStatusView:
        if self._status is RuntimeHostStatus.STOPPED:
            return self.status()
        self.daemon.stop()
        self._status = RuntimeHostStatus.STOPPED
        return self.status()

    def status(self) -> RuntimeHostStatusView:
        return RuntimeHostStatusView(
            status=self._status,
            started=self._status is RuntimeHostStatus.STARTED,
            daemon_available=self.daemon is not None,
            connection_count=len(self.connection_registry.connections),
            active_mission_count=len(self.kernel.list_missions()),
            host=self,
        )

    def pump_daemon_once(self, mission_id: str) -> RuntimeHostDaemonPumpResult:
        if self._status is not RuntimeHostStatus.STARTED:
            raise RuntimeError("runtime_host_not_started")
        request = self.lifecycle.latest_execution_request(mission_id)
        envelope = self.authority_issuer.resolve_active(mission_id)
        self.daemon.claim_lease(mission_id, now=daemon_utc_now())
        claimed_request = self.lifecycle.mark_request_claimed(mission_id, request.request_id)
        tick_result = self.daemon.tick(
            mission_id,
            current_envelope=envelope,
            workflow_id=None,
            now=daemon_utc_now(),
        )
        return RuntimeHostDaemonPumpResult(
            mission_id=mission_id,
            execution_request_ref=claimed_request.request_id,
            claimed=True,
            tick_result=tick_result,
        )


__all__ = [
    "RuntimeHostDaemonPumpResult",
    "RuntimeHostStatus",
    "RuntimeHostStatusView",
    "SentinelRuntimeHost",
]
