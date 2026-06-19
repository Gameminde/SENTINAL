from __future__ import annotations

from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.power_bridge import BoundPowerActuatorExecutor
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
    PowerMissionTimeline,
    PowerRuntimeResult,
    PowerRuntimeStatus,
    PowerStepResult,
    PowerStepStatus,
)


def test_workflow_uses_injected_power_bridge_factory(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    record = kernel.create_mission(
        session_id="session_workflow",
        draft=MissionDraft(
            title="Workflow bridge factory",
            objective="Verify bridge factory injection.",
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="pending",
            allowed_actions=["observe"],
            forbidden_actions=["payment"],
            summary="Observe only.",
        ),
    )
    kernel.enqueue(record.mission_id)
    envelope = _envelope(record.mission_id)
    calls: list[dict[str, object]] = []

    class _FactoryBridge:
        def run(self, mission_id, plan, **kwargs):
            calls.append({"mission_id": mission_id, "telemetry_sink": getattr(kernel, "telemetry_sink", None), **kwargs})
            return PowerRuntimeResult(
                mission_id=mission_id,
                status=PowerRuntimeStatus.COMPLETED,
                step_results=[
                    PowerStepResult(
                        step_id="observe",
                        status=PowerStepStatus.SUCCEEDED,
                        receipt_refs=["receipt:factory"],
                        finalgate_certificate_refs=["finalgate:factory"],
                        safe_summary="Factory bridge step succeeded.",
                    )
                ],
                timeline=PowerMissionTimeline(mission_id=mission_id),
                receipt_refs=["receipt:factory"],
                finalgate_certificate_refs=["finalgate:factory"],
            )

    runtime = DurableMissionWorkflowRuntime(
        kernel,
        power_bridge_factory=lambda kernel_arg: _FactoryBridge(),
    )
    workflow = runtime.create_power_workflow(
        mission_id=record.mission_id,
        envelope=envelope,
        plan=_plan(record.mission_id),
        executor_contract_id="executor:factory",
    )

    result = runtime.run_power_tick(
        workflow.workflow_id,
        current_envelope=envelope,
        actuator_executor=BoundPowerActuatorExecutor(
            contract_id="executor:factory",
            executor=lambda step, context: PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.SUCCEEDED,
                receipt_refs=["unused"],
                finalgate_certificate_refs=["unused"],
            ),
        ),
        max_steps=2,
    )

    assert result.status is PowerRuntimeStatus.COMPLETED or result.status.value == "completed"
    assert calls
    assert calls[0]["mission_id"] == record.mission_id
    assert calls[0]["update_mission_status"] is False
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.COMPLETED


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="operator_user",
        mission_title="Workflow bridge factory",
        mission_objective="Verify bridge factory injection.",
        allowed_systems=["browser"],
        allowed_tools=["browser_readonly"],
        allowed_actions=["observe"],
        forbidden_actions=["payment"],
        allowed_domains=["example.com"],
        max_actions=4,
        max_cost_usd=1.0,
    )


def _plan(mission_id: str) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="observe",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind="observe",
                    request={"url": "https://example.com"},
                )
            ]
        ),
    )
