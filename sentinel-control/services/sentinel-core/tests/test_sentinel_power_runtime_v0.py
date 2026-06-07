from __future__ import annotations

from collections import Counter

import pytest

from sentinel.mission.cancellation import CancellationToken


def test_power_runtime_runs_dependency_order_and_records_timeline() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        PowerStepResult,
        PowerStepStatus,
        SentinelPowerRuntimeV0,
    )

    calls: list[str] = []

    def executor(step: PowerMissionStep, _context: dict[str, object]) -> PowerStepResult:
        calls.append(step.step_id)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[f"receipt:{step.step_id}"],
            finalgate_certificate_refs=[f"finalgate:{step.step_id}"],
            memory_feedback_refs=[f"memory:{step.step_id}"],
            safe_summary=f"{step.step_id} done",
        )

    plan = PowerMissionPlan(
        mission_id="mission_power_runtime_order",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="write_report",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                    depends_on=["observe"],
                ),
                PowerMissionStep(
                    step_id="observe",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind="observe",
                ),
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=executor,
    )

    assert result.status == "completed"
    assert calls == ["observe", "write_report"]
    assert result.receipt_refs == ["receipt:observe", "receipt:write_report"]
    assert result.finalgate_certificate_refs == ["finalgate:observe", "finalgate:write_report"]
    assert result.memory_feedback_refs == ["memory:observe", "memory:write_report"]
    assert result.timeline.verify_chain() is True
    assert [item.step_id for item in result.timeline.items if item.event_type == "step_started"] == [
        "observe",
        "write_report",
    ]


def test_power_runtime_rejects_unknown_dependencies_and_cycles() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        SentinelPowerRuntimeV0,
    )

    runtime = SentinelPowerRuntimeV0()
    missing_dep = PowerMissionPlan(
        mission_id="mission_missing_dep",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="b",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="local_artifact",
                    action_kind="create",
                    depends_on=["a"],
                )
            ]
        ),
    )
    missing_result = runtime.run(missing_dep, config=PowerRuntimeConfig(enabled=True))
    assert missing_result.status == "blocked"
    assert missing_result.blocked_reason == "unknown_dependency:a"

    cyclic = PowerMissionPlan(
        mission_id="mission_cycle",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="a",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="local_artifact",
                    action_kind="create",
                    depends_on=["b"],
                ),
                PowerMissionStep(
                    step_id="b",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="local_artifact",
                    action_kind="create",
                    depends_on=["a"],
                ),
            ]
        ),
    )
    cycle_result = runtime.run(cyclic, config=PowerRuntimeConfig(enabled=True))
    assert cycle_result.status == "blocked"
    assert cycle_result.blocked_reason == "cycle_detected"


def test_power_runtime_enforces_retry_budget() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        PowerStepResult,
        PowerStepStatus,
        SentinelPowerRuntimeV0,
    )

    attempts: Counter[str] = Counter()

    def executor(step: PowerMissionStep, _context: dict[str, object]) -> PowerStepResult:
        attempts[step.step_id] += 1
        if attempts[step.step_id] == 1:
            return PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.FAILED,
                blocked_reason="fixture_retry",
                safe_summary="first attempt failed",
            )
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:retry"],
            finalgate_certificate_refs=["finalgate:retry"],
            safe_summary="second attempt succeeded",
        )

    plan = PowerMissionPlan(
        mission_id="mission_retry",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="retry_step",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                    retry_budget=1,
                )
            ]
        ),
    )
    result = SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=executor,
    )

    assert result.status == "completed"
    assert attempts["retry_step"] == 2
    assert result.step_results[0].attempt_count == 2


def test_power_runtime_kill_switch_aborts_before_next_step() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        PowerStepResult,
        PowerStepStatus,
        SentinelPowerRuntimeV0,
    )

    token = CancellationToken()
    calls: list[str] = []

    def executor(step: PowerMissionStep, _context: dict[str, object]) -> PowerStepResult:
        calls.append(step.step_id)
        token.cancel()
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[f"receipt:{step.step_id}"],
            finalgate_certificate_refs=[f"finalgate:{step.step_id}"],
            safe_summary="first step done",
        )

    plan = PowerMissionPlan(
        mission_id="mission_kill",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="first",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="local_artifact",
                    action_kind="create",
                ),
                PowerMissionStep(
                    step_id="second",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="local_artifact",
                    action_kind="create",
                    depends_on=["first"],
                ),
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=executor,
        cancellation_token=token,
    )

    assert result.status == "aborted"
    assert calls == ["first"]
    assert result.step_results[-1].step_id == "second"
    assert result.step_results[-1].status == "aborted"
    assert result.blocked_reason == "kill_switch_cancelled"


def test_power_runtime_fails_closed_without_executor() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        SentinelPowerRuntimeV0,
    )

    plan = PowerMissionPlan(
        mission_id="mission_no_executor",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="api",
                    actuator_family=PowerActuatorFamily.EXTERNAL_API,
                    capability_level=PowerActuatorCapabilityLevel.L5,
                    organ_kind="external_api",
                    action_kind="get",
                )
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(plan, config=PowerRuntimeConfig(enabled=True))

    assert result.status == "blocked"
    assert result.step_results[0].blocked_reason == "power_runtime_executor_missing"
    assert result.receipt_refs == []
    assert result.authority_effect == "none"
    assert result.execution_effect == "none"


def test_power_runtime_sanitizes_non_result_executor_return() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        PowerRuntimeConfig,
        SentinelPowerRuntimeV0,
    )

    plan = PowerMissionPlan(
        mission_id="mission_invalid_executor_result",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="observe",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind="observe",
                )
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(
        plan,
        config=PowerRuntimeConfig(enabled=True),
        actuator_executor=lambda _step, _context: None,
    )

    assert result.status == "failed"
    assert result.step_results[0].blocked_reason == "executor_invalid_result"


def test_power_runtime_disabled_is_default_off() -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
        SentinelPowerRuntimeV0,
    )

    called = False

    def executor(_step: PowerMissionStep, _context: dict[str, object]):
        nonlocal called
        called = True
        raise AssertionError("executor must not be called while runtime is disabled")

    plan = PowerMissionPlan(
        mission_id="mission_default_off",
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="browser",
                    actuator_family=PowerActuatorFamily.BROWSER,
                    capability_level=PowerActuatorCapabilityLevel.L4,
                    organ_kind="browser_readonly",
                    action_kind="observe",
                )
            ]
        ),
    )

    result = SentinelPowerRuntimeV0().run(plan, actuator_executor=executor)

    assert result.status == "not_started"
    assert called is False
    assert result.step_results == []


@pytest.mark.parametrize(
    "unsafe_request",
    [
        {"provider_override": "x"},
        {"backend_override": "x"},
        {"model_override": "x"},
        {"raw_prompt": "hidden"},
        {"authorization": "Be" + "arer " + "sk-" + "test-" + "abcdefghijklmnopqrstuvwxyz123456"},
    ],
)
def test_power_runtime_rejects_provider_override_and_raw_secret_payloads(unsafe_request: dict[str, str]) -> None:
    from sentinel.power.runtime import (
        PowerActuatorCapabilityLevel,
        PowerActuatorFamily,
        PowerMissionGraph,
        PowerMissionPlan,
        PowerMissionStep,
    )

    with pytest.raises(ValueError):
        PowerMissionPlan(
            mission_id="mission_unsafe",
            graph=PowerMissionGraph(
                steps=[
                    PowerMissionStep(
                        step_id="unsafe",
                        actuator_family=PowerActuatorFamily.WORKSPACE,
                        capability_level=PowerActuatorCapabilityLevel.L2,
                        organ_kind="local_artifact",
                        action_kind="create",
                        request=unsafe_request,
                    )
                ]
            ),
        )
