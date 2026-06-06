from __future__ import annotations

from pathlib import Path

from sentinel.mission.cancellation import CancellationToken
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.power_bridge import OperatorPowerRuntimeBridge
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
    PowerRuntimeStatus,
    PowerStepResult,
    PowerStepStatus,
)


def _kernel_with_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_power",
        draft=MissionDraft(title="Power mission", objective="Run governed PowerRuntime plan."),
    )
    kernel.enqueue(record.mission_id)
    return kernel, record.mission_id


def _plan(mission_id: str) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="write_report",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                )
            ]
        ),
    )


def test_cockpit_mission_runs_power_runtime_plan(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    def executor(step, _context):
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:power"],
            finalgate_certificate_refs=["finalgate:power"],
            memory_feedback_refs=["memory:power"],
            safe_summary="done",
        )

    result = OperatorPowerRuntimeBridge(kernel).run(mission_id, _plan(mission_id), actuator_executor=executor)

    assert result.status is PowerRuntimeStatus.COMPLETED
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED


def test_cockpit_mission_blocks_missing_executor(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(mission_id, _plan(mission_id))

    assert result.status is PowerRuntimeStatus.BLOCKED
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_cockpit_mission_records_receipts_finalgate_memory(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        actuator_executor=lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:1"],
            finalgate_certificate_refs=["finalgate:1"],
            memory_feedback_refs=["memory:1"],
            safe_summary="done",
        ),
    )

    events = kernel.store.load_events(mission_id)
    assert result.receipt_refs == ["receipt:1"]
    assert result.finalgate_certificate_refs == ["finalgate:1"]
    assert result.memory_feedback_refs == ["memory:1"]
    assert events[-1].receipt_refs == ["receipt:1"]
    assert events[-1].finalgate_certificate_refs == ["finalgate:1"]
    assert events[-1].memory_feedback_refs == ["memory:1"]


def test_cockpit_mission_kill_switch_aborts_power_plan(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    token = CancellationToken()
    token.cancel()

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        actuator_executor=lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            safe_summary="should not run",
        ),
        cancellation_token=token,
    )

    assert result.status is PowerRuntimeStatus.ABORTED
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.KILLED


def test_cockpit_mission_power_bridge_does_not_run_killed_mission(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    kernel.kill(mission_id)
    calls: list[str] = []

    def executor(step, _context):
        calls.append(step.step_id)
        return PowerStepResult(step_id=step.step_id, status=PowerStepStatus.SUCCEEDED, safe_summary="should not run")

    result = OperatorPowerRuntimeBridge(kernel).run(mission_id, _plan(mission_id), actuator_executor=executor)

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "operator_mission_terminal"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.KILLED


def test_cockpit_memory_refs_context_only_not_authority(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        actuator_executor=lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            memory_feedback_refs=["memory:context"],
            safe_summary="done",
        ),
    )

    assert result.can_grant_authority is False
    assert result.can_approve_future_execution is False


def test_cockpit_does_not_call_organs_directly(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []

    def injected_executor(step, _context):
        calls.append(step.organ_kind)
        return PowerStepResult(step_id=step.step_id, status=PowerStepStatus.SUCCEEDED, safe_summary="done")

    OperatorPowerRuntimeBridge(kernel).run(mission_id, _plan(mission_id), actuator_executor=injected_executor)

    assert calls == ["reversible_workspace"]
