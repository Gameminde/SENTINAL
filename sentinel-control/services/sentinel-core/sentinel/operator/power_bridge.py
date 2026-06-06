from __future__ import annotations

from sentinel.mission.cancellation import CancellationToken
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.power.runtime import (
    PowerActuatorExecutor,
    PowerMissionPlan,
    PowerMissionTimeline,
    PowerRuntimeConfig,
    PowerRuntimeResult,
    PowerRuntimeStatus,
    SentinelPowerRuntimeV0,
)


class OperatorPowerRuntimeBridge:
    def __init__(self, kernel: MissionKernel, *, runtime: SentinelPowerRuntimeV0 | None = None) -> None:
        self._kernel = kernel
        self._runtime = runtime or SentinelPowerRuntimeV0()

    def run(
        self,
        mission_id: str,
        plan: PowerMissionPlan,
        *,
        actuator_executor: PowerActuatorExecutor | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> PowerRuntimeResult:
        if plan.mission_id != mission_id:
            raise ValueError("power plan mission_id must match operator mission_id")
        terminal_reason = self._kernel.terminal_block_reason(mission_id)
        if terminal_reason is not None:
            return self._blocked_terminal_result(mission_id, terminal_reason)
        result = self._runtime.run(
            plan,
            config=PowerRuntimeConfig(enabled=True),
            actuator_executor=actuator_executor,
            cancellation_token=cancellation_token,
        )
        status = _operator_status(result.status)
        self._kernel.update_status(mission_id, status, f"PowerRuntime finished with status {result.status.value}.")
        self._kernel.store.append_event(
            mission_id,
            event_type="power_runtime_result",
            safe_summary=f"PowerRuntime result {result.status.value}.",
            receipt_refs=list(result.receipt_refs),
            finalgate_certificate_refs=list(result.finalgate_certificate_refs),
            memory_feedback_refs=list(result.memory_feedback_refs),
            metadata={"power_runtime_status": result.status.value},
        )
        return result

    def _blocked_terminal_result(self, mission_id: str, terminal_reason: str) -> PowerRuntimeResult:
        reason = "operator_mission_terminal"
        timeline = PowerMissionTimeline(mission_id=mission_id)
        timeline.record(
            "runtime_blocked",
            "Operator mission is terminal; PowerRuntime was not invoked.",
            blocked_reason=reason,
        )
        self._kernel.store.append_event(
            mission_id,
            event_type="power_runtime_blocked",
            safe_summary="PowerRuntime blocked because operator mission is terminal.",
            metadata={"drop_reason": "mission_closed", "mission_state": terminal_reason.rsplit(":", 1)[-1]},
        )
        return PowerRuntimeResult(
            mission_id=mission_id,
            status=PowerRuntimeStatus.BLOCKED,
            timeline=timeline,
            blocked_reason=reason,
        )


def _operator_status(status: PowerRuntimeStatus) -> OperatorMissionStatus:
    if status is PowerRuntimeStatus.COMPLETED:
        return OperatorMissionStatus.COMPLETED
    if status is PowerRuntimeStatus.ABORTED:
        return OperatorMissionStatus.KILLED
    if status is PowerRuntimeStatus.BLOCKED:
        return OperatorMissionStatus.BLOCKED
    return OperatorMissionStatus.FAILED
