from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.mission.cancellation import CancellationToken
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.power_bridge import BoundPowerActuatorExecutor, OperatorPowerRuntimeBridge
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
from sentinel.telemetry import TelemetryKernel


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
                    request={"path": "data/generated_projects/report.md"},
                )
            ]
        ),
    )


def _envelope(mission_id: str, **updates) -> MissionAuthorityEnvelope:
    payload = {
        "id": mission_id,
        "user_id": "operator_power",
        "mission_title": "Power mission",
        "mission_objective": "Run governed PowerRuntime plan.",
        "allowed_systems": ["workspace"],
        "allowed_tools": ["reversible_workspace"],
        "allowed_actions": ["write"],
        "allowed_paths": ["data/generated_projects"],
    }
    payload.update(updates)
    return MissionAuthorityEnvelope(**payload)


def _binding(executor):
    return BoundPowerActuatorExecutor(contract_id="executor:governed:v1", executor=executor)


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

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id),
        executor_binding=_binding(executor),
    )

    assert result.status is PowerRuntimeStatus.COMPLETED
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED


def test_cockpit_mission_blocks_missing_executor(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(mission_id, _plan(mission_id), envelope=_envelope(mission_id))

    assert result.status is PowerRuntimeStatus.BLOCKED
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_cockpit_mission_records_receipts_finalgate_memory(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id),
        executor_binding=_binding(lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:1"],
            finalgate_certificate_refs=["finalgate:1"],
            memory_feedback_refs=["memory:1"],
            safe_summary="done",
        )),
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
        envelope=_envelope(mission_id),
        executor_binding=_binding(lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            safe_summary="should not run",
        )),
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

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id),
        executor_binding=_binding(executor),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "operator_mission_terminal"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.KILLED


def test_cockpit_memory_refs_context_only_not_authority(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id),
        executor_binding=_binding(lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            memory_feedback_refs=["memory:context"],
            safe_summary="done",
        )),
    )

    assert result.can_grant_authority is False
    assert result.can_approve_future_execution is False


def test_cockpit_does_not_call_organs_directly(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []

    def injected_executor(step, _context):
        calls.append(step.organ_kind)
        return PowerStepResult(step_id=step.step_id, status=PowerStepStatus.SUCCEEDED, safe_summary="done")

    OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id),
        executor_binding=_binding(injected_executor),
    )

    assert calls == ["reversible_workspace"]


def test_power_bridge_fails_closed_without_authority_envelope(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        actuator_executor=lambda step, _context: calls.append(step.step_id),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "mission_authority_envelope_required"


def test_power_bridge_blocks_draft_mission_before_material_execution(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_power",
        draft=MissionDraft(title="Draft power mission", objective="Must be explicitly started."),
    )
    calls: list[str] = []

    result = OperatorPowerRuntimeBridge(kernel).run(
        record.mission_id,
        _plan(record.mission_id),
        envelope=_envelope(record.mission_id),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "operator_mission_not_executable"
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.DRAFT


def test_power_bridge_blocks_material_execution_when_certified_telemetry_is_unavailable(tmp_path: Path) -> None:
    telemetry = TelemetryKernel(tmp_path / "telemetry", enabled=False)
    kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=telemetry)
    record = kernel.create_mission(
        session_id="session_power",
        draft=MissionDraft(title="Power mission", objective="Requires certified telemetry."),
    )
    kernel.enqueue(record.mission_id)
    calls: list[str] = []

    result = OperatorPowerRuntimeBridge(kernel).run(
        record.mission_id,
        _plan(record.mission_id),
        envelope=_envelope(record.mission_id),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "telemetry_certified_mode_required"


def test_power_bridge_rejects_plan_outside_authority_envelope(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    payment_plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="payment",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L7,
                    organ_kind="payment_organ",
                    action_kind="payment_capture",
                )
            ]
        ),
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        payment_plan,
        envelope=_envelope(mission_id),
        actuator_executor=lambda step, _context: calls.append(step.step_id),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_target_path_outside_authority_envelope(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    escaped = _plan(mission_id).model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[
                    _plan(mission_id).graph.steps[0].model_copy(
                        update={"request": {"path": "outside/report.md"}}
                    )
                ]
            )
        }
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        escaped,
        envelope=_envelope(mission_id),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_workspace_action_without_concrete_target(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    targetless = _plan(mission_id).model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[
                    _plan(mission_id).graph.steps[0].model_copy(update={"request": {}})
                ]
            )
        }
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        targetless,
        envelope=_envelope(mission_id),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_plan_exceeding_envelope_action_budget(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                _plan(mission_id).graph.steps[0].model_copy(
                    update={"step_id": "write_a", "retry_budget": 1}
                ),
                _plan(mission_id).graph.steps[0].model_copy(update={"step_id": "write_b"}),
            ]
        ),
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        plan,
        envelope=_envelope(mission_id, max_actions=2),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_generic_l7_even_when_action_is_listed(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    payment = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="payment",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L7,
                    organ_kind="payment_organ",
                    action_kind="payment_capture",
                )
            ]
        ),
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        payment,
        envelope=_envelope(
            mission_id,
            allowed_systems=["external_api"],
            allowed_tools=["payment_organ"],
            allowed_actions=["payment_capture"],
        ),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_generic_compound_irreversible_action(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    delete_plan = _plan(mission_id).model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[
                    _plan(mission_id).graph.steps[0].model_copy(
                        update={"action_kind": "delete_file"}
                    )
                ]
            )
        }
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        delete_plan,
        envelope=_envelope(mission_id, allowed_actions=["delete_file"]),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_noncanonical_target_key(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="read_external",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="external_api_read",
                    action_kind="read",
                    request={"target_url": "https://outside.example.net/private"},
                )
            ]
        ),
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        plan,
        envelope=_envelope(
            mission_id,
            allowed_systems=["external_api"],
            allowed_tools=["external_api_read"],
            allowed_actions=["read"],
            allowed_domains=["api.example.com"],
        ),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_enforces_recipient_budget(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="draft_message",
                    actuator_family=PowerActuatorFamily.CHANNEL,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="channel_draft",
                    action_kind="prepare_draft",
                    request={"recipients": ["first@example.com", "second@example.com"]},
                )
            ]
        ),
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        plan,
        envelope=_envelope(
            mission_id,
            allowed_systems=["channel"],
            allowed_tools=["channel_draft"],
            allowed_actions=["prepare_draft"],
            allowed_accounts=["first@example.com", "second@example.com"],
            max_recipients=1,
        ),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_revoked_or_expired_envelope(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    bridge = OperatorPowerRuntimeBridge(kernel)
    binding = _binding(lambda step, _context: calls.append(step.step_id))

    revoked = bridge.run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id, revoked_at=datetime.now(UTC)),
        executor_binding=binding,
    )
    expired = bridge.run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(
            mission_id,
            created_at=datetime.now(UTC) - timedelta(hours=2),
            max_duration_minutes=1,
        ),
        executor_binding=binding,
    )

    assert calls == []
    assert revoked.blocked_reason == "mission_authority_envelope_inactive"
    assert expired.blocked_reason == "mission_authority_envelope_inactive"


def test_power_bridge_enforces_cumulative_mission_budget(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    bridge = OperatorPowerRuntimeBridge(kernel)
    envelope = _envelope(mission_id, max_actions=1)
    binding = _binding(
        lambda step, _context: (
            calls.append(step.step_id)
            or PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.SUCCEEDED,
                receipt_refs=["receipt:budget"],
                finalgate_certificate_refs=["finalgate:budget"],
                safe_summary="done",
            )
        )
    )

    first = bridge.run(
        mission_id,
        _plan(mission_id),
        envelope=envelope,
        executor_binding=binding,
        update_mission_status=False,
    )
    second = bridge.run(
        mission_id,
        _plan(mission_id),
        envelope=envelope,
        executor_binding=binding,
        update_mission_status=False,
    )

    assert first.status is PowerRuntimeStatus.COMPLETED
    assert calls == ["write_report"]
    assert second.status is PowerRuntimeStatus.BLOCKED
    assert second.blocked_reason == "mission_power_budget_exhausted"


def test_power_bridge_enforces_cumulative_mission_cost_budget(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    bridge = OperatorPowerRuntimeBridge(kernel)
    plan = _plan(mission_id).model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[_plan(mission_id).graph.steps[0].model_copy(update={"estimated_cost_usd": 0.6})]
            )
        }
    )
    binding = _binding(
        lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:cost"],
            finalgate_certificate_refs=["finalgate:cost"],
            safe_summary="done",
        )
    )
    envelope = _envelope(mission_id, max_cost_usd=1.0)

    first = bridge.run(
        mission_id,
        plan,
        envelope=envelope,
        executor_binding=binding,
        update_mission_status=False,
    )
    second = bridge.run(
        mission_id,
        plan,
        envelope=envelope,
        executor_binding=binding,
        update_mission_status=False,
    )

    assert first.status is PowerRuntimeStatus.COMPLETED
    assert second.status is PowerRuntimeStatus.BLOCKED
    assert second.blocked_reason == "mission_power_budget_exhausted"


def test_power_bridge_commits_actual_retry_cost_not_reserved_worst_case(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    bridge = OperatorPowerRuntimeBridge(kernel)
    plan = _plan(mission_id).model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[
                    _plan(mission_id).graph.steps[0].model_copy(
                        update={"estimated_cost_usd": 0.4, "retry_budget": 1}
                    )
                ]
            )
        }
    )
    binding = _binding(
        lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:cost"],
            finalgate_certificate_refs=["finalgate:cost"],
            safe_summary="done",
        )
    )
    envelope = _envelope(mission_id, max_actions=4, max_cost_usd=0.8)

    first = bridge.run(mission_id, plan, envelope=envelope, executor_binding=binding, update_mission_status=False)
    no_retry_plan = plan.model_copy(
        update={
            "graph": PowerMissionGraph(
                steps=[plan.graph.steps[0].model_copy(update={"retry_budget": 0})]
            )
        }
    )
    second = bridge.run(
        mission_id,
        no_retry_plan,
        envelope=envelope,
        executor_binding=binding,
        update_mission_status=False,
    )
    third = bridge.run(
        mission_id,
        no_retry_plan,
        envelope=envelope,
        executor_binding=binding,
        update_mission_status=False,
    )

    assert first.status is PowerRuntimeStatus.COMPLETED
    assert second.status is PowerRuntimeStatus.COMPLETED
    assert third.blocked_reason == "mission_power_budget_exhausted"


def test_power_bridge_rejects_hidden_api_mutation_request(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    calls: list[str] = []
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="hidden_mutation",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="external_api",
                    action_kind="request",
                    request={
                        "url": "https://api.example.com/items",
                        "method": "POST",
                        "mutation_authority_ref": "authority:fake",
                    },
                )
            ]
        ),
    )

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        plan,
        envelope=_envelope(
            mission_id,
            allowed_systems=["external_api"],
            allowed_tools=["external_api"],
            allowed_actions=["request"],
            allowed_domains=["api.example.com"],
        ),
        executor_binding=_binding(lambda step, _context: calls.append(step.step_id)),
    )

    assert calls == []
    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"


def test_power_bridge_rejects_success_without_receipt_and_finalgate_proof(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        _plan(mission_id),
        envelope=_envelope(mission_id),
        executor_binding=_binding(
            lambda step, _context: PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.SUCCEEDED,
                safe_summary="unproved success",
            )
        ),
    )

    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "executor_success_proof_missing"


def test_power_bridge_rejects_empty_plan(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        PowerMissionPlan(mission_id=mission_id, graph=PowerMissionGraph(steps=[])),
        envelope=_envelope(mission_id),
        executor_binding=_binding(lambda step, _context: step),
    )

    assert result.status is PowerRuntimeStatus.BLOCKED
    assert result.blocked_reason == "power_plan_outside_authority"
