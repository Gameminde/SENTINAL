from __future__ import annotations

import time
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.workflow_models import DurableWorkflowRecord, WorkflowAuthoritySnapshot
from sentinel.operator.workflow_store import DurableWorkflowStore
from sentinel.operator.worker_fleet import WorkerFleetRuntime
from sentinel.operator.worker_models import (
    WorkerBudget,
    WorkerDeadline,
    WorkerEvidencePacket,
    WorkerExecutionMode,
    WorkerFleetConfig,
    WorkerFleetRunStatus,
    WorkerMergeOutcome,
    WorkerResult,
    WorkerResultContract,
    WorkerRole,
    WorkerScope,
    WorkerSpawnRequest,
    WorkerTask,
    WorkerTaskStatus,
)
from sentinel.operator.worker_replay import WorkerFleetReplayBuilder
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
)
from sentinel.telemetry import TelemetryKernel


def test_child_authority_is_strict_subset_and_cannot_expand_parent_envelope(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)
    parent = _parent_envelope(mission_id)

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=parent,
        spawn_request=_spawn_request(mission_id, task=_task("worker_read", actions=["read"], tools=["workspace"])),
        worker_executor=_successful_executor,
    )

    assert run.status is WorkerFleetRunStatus.COMPLETED
    child = run.child_authority_envelopes[0]
    assert child.parent_envelope_id == parent.id
    assert child.worker_id == run.workers[0].worker_id
    assert set(child.allowed_actions) == {"read"}
    assert set(child.allowed_actions).issubset(set(parent.allowed_actions))
    assert child.max_actions < parent.max_actions
    assert child.max_cost_usd < parent.max_cost_usd
    assert child.strict_subset is True

    expanded = runtime.run(
        mission_id=mission_id,
        parent_envelope=parent,
        spawn_request=_spawn_request(
            mission_id,
            task=_task("worker_expand", actions=["share"], tools=["workspace"]),
        ),
        worker_executor=_successful_executor,
    )

    assert expanded.status is WorkerFleetRunStatus.BLOCKED
    assert expanded.blocked_reason == "worker_authority_derivation_failed"
    assert expanded.worker_results == []


def test_worker_fleet_requires_verified_telemetry_in_certified_mode(tmp_path: Path) -> None:
    telemetry = TelemetryKernel(tmp_path / "telemetry", enabled=False)
    kernel, mission_id = _kernel_with_mission(tmp_path, telemetry_sink=telemetry)
    runtime = WorkerFleetRuntime(kernel)

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_read")),
        worker_executor=_successful_executor,
    )

    assert run.status is WorkerFleetRunStatus.BLOCKED
    assert run.blocked_reason == "telemetry_certified_mode_required"
    assert any(event.event_type == "worker_spawn_blocked" for event in kernel.store.load_events(mission_id))


def test_worker_context_has_no_direct_organ_path_and_merge_records_telemetry(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)

    def executor(context):
        assert not hasattr(context, "organ_dispatcher")
        assert not hasattr(context, "power_executor")
        assert not hasattr(context, "credential_provider")
        assert context.child_authority.allowed_actions == ["read"]
        return _worker_result(context, safe_summary="Worker produced scoped evidence.")

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_read", actions=["read"])),
        worker_executor=executor,
    )

    assert run.status is WorkerFleetRunStatus.COMPLETED
    assert [decision.outcome for decision in run.merge_decisions] == [WorkerMergeOutcome.MERGED]
    event_kinds = [event.event_kind.value for event in kernel.telemetry_sink.store.load_events()]
    assert "worker_started" in event_kinds
    assert "worker_completed" in event_kinds
    assert "worker_result_submitted" in event_kinds
    assert "worker_result_merged" in event_kinds


def test_worker_result_contract_rejects_missing_evidence_and_authority_requests(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)

    def missing_evidence_executor(context):
        return _worker_result(
            context,
            safe_summary="Worker has a claim but no evidence.",
            evidence_refs=[],
        )

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_no_evidence")),
        worker_executor=missing_evidence_executor,
    )

    assert run.status is WorkerFleetRunStatus.BLOCKED
    assert run.merge_decisions[0].outcome is WorkerMergeOutcome.REJECTED
    assert "missing_required_evidence" in run.merge_decisions[0].reasons

    with pytest.raises(ValueError, match="worker result cannot request authority"):
        WorkerResult(
            worker_id="worker_bad",
            task_id="task_bad",
            status=WorkerTaskStatus.COMPLETED,
            result_contract_id="contract_bad",
            safe_summary="I need root authority.",
            output={"authority_grant": "root"},
            evidence_packet=WorkerEvidencePacket(evidence_refs=["evidence_1"]),
        )


def test_conflicting_worker_outputs_are_detected_and_not_blindly_merged(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)
    task_a = _task("worker_a", conflict_key="market_size")
    task_b = _task("worker_b", conflict_key="market_size")

    def executor(context):
        return _worker_result(
            context,
            safe_summary=f"Worker {context.task_id} completed.",
            output={"answer": context.task_id},
        )

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=task_a, extra_tasks=[task_b]),
        worker_executor=executor,
    )

    assert run.status is WorkerFleetRunStatus.BLOCKED
    assert any(decision.outcome is WorkerMergeOutcome.CONFLICT for decision in run.merge_decisions)
    assert run.conflict_records
    assert run.conflict_records[0].conflict_key == "market_size"


def test_worker_replay_reconstructs_without_reexecution(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)
    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_replay")),
        worker_executor=_successful_executor,
    )

    replay = WorkerFleetReplayBuilder(kernel.store).build(mission_id, run.worker_fleet_run_id)

    assert replay.tampered is False
    assert replay.reexecuted_actions is False
    assert replay.worker_fleet_run_id == run.worker_fleet_run_id
    assert replay.child_authority_envelopes[0].strict_subset is True
    assert replay.merge_decisions[0].outcome is WorkerMergeOutcome.MERGED
    assert replay.receipt_refs == ["receipt_worker"]
    assert replay.finalgate_certificate_refs == ["finalgate_worker"]


def test_worker_memory_and_secret_outputs_are_scoped_and_sanitized(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)

    def executor(context):
        return _worker_result(
            context,
            safe_summary="OPENAI_API_KEY=sk-test-1234567890",
            output={"notes": "Bearer raw-token-value"},
            memory_feedback_refs=["memory_worker"],
        )

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_memory")),
        worker_executor=executor,
    )

    assert run.status is WorkerFleetRunStatus.COMPLETED
    payload = kernel.store.mission_dir(mission_id).joinpath("worker_fleet", f"{run.worker_fleet_run_id}.json").read_text(encoding="utf-8")
    assert "sk-test-1234567890" not in payload
    assert "raw-token-value" not in payload
    assert "memory_worker" in payload
    assert run.worker_results[0].evidence_packet.memory_feedback_refs == ["memory_worker"]


def test_worker_exception_path_does_not_persist_raw_exception_or_secret(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)

    def executor(_context):
        raise RuntimeError("Bearer raw-worker-secret")

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_exception")),
        worker_executor=executor,
    )

    payload = kernel.store.mission_dir(mission_id).joinpath("worker_fleet", f"{run.worker_fleet_run_id}.json").read_text(encoding="utf-8")
    assert run.status is WorkerFleetRunStatus.FAILED
    assert run.blocked_reason == "worker_failed:RuntimeError"
    assert "raw-worker-secret" not in payload
    assert "raw-worker-secret" not in "\n".join(event.safe_summary for event in kernel.store.load_events(mission_id))


def test_worker_fleet_records_outstanding_future_cancellation_after_authority_failure(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)
    parent = _parent_envelope(mission_id)
    fast_task = _task("worker_fast")
    slow_task = _task("worker_slow")
    blocked_task = _task("worker_blocked_child", actions=["share"])
    blocked_task = blocked_task.model_copy(update={"depends_on": ["worker_fast"]})
    executed: list[str] = []

    def executor(context):
        executed.append(context.task_id)
        if context.task_id == "worker_slow":
            time.sleep(0.1)
        return _worker_result(context, safe_summary=f"{context.task_id} completed.")

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=parent,
        spawn_request=WorkerSpawnRequest(
            mission_id=mission_id,
            requested_by="operator",
            tasks=[fast_task, slow_task, blocked_task],
            safe_reason="Prove outstanding workers are handled when a child is blocked.",
            config=WorkerFleetConfig(max_workers=3),
        ),
        worker_executor=executor,
    )

    events = kernel.store.load_events(mission_id)
    assert run.status is WorkerFleetRunStatus.BLOCKED
    assert run.blocked_reason == "worker_authority_derivation_failed"
    assert "worker_slow" in executed
    assert any(
        event.event_type == "worker_killed"
        and event.metadata.get("task_id") == "worker_slow"
        for event in events
    )


def test_power_runtime_worker_requires_explicit_authorization(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)
    power_task = _task(
        "worker_power",
        mode=WorkerExecutionMode.POWER_RUNTIME,
        actions=["write"],
        tools=["workspace"],
        allow_power_runtime=False,
    )

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=power_task),
        worker_executor=_successful_executor,
    )

    assert run.status is WorkerFleetRunStatus.BLOCKED
    assert run.blocked_reason == "worker_authority_derivation_failed"
    assert any(
        event.event_type == "worker_authority_rejected"
        for event in kernel.store.load_events(mission_id)
    )


def test_worker_budget_and_provider_override_fail_closed(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = WorkerFleetRuntime(kernel)

    def over_budget_executor(context):
        return _worker_result(
            context,
            safe_summary="Worker exceeded its bounded action budget.",
            actions_used=context.budget.max_actions + 1,
        )

    budget_run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(mission_id, task=_task("worker_budget")),
        worker_executor=over_budget_executor,
    )

    assert budget_run.status is WorkerFleetRunStatus.BLOCKED
    assert budget_run.merge_decisions[0].outcome is WorkerMergeOutcome.REJECTED
    assert "worker_budget_exhausted" in budget_run.merge_decisions[0].reasons
    assert "worker_budget_exhausted" in [event.event_kind.value for event in kernel.telemetry_sink.store.load_events()]

    provider_run = runtime.run(
        mission_id=mission_id,
        parent_envelope=_parent_envelope(mission_id),
        spawn_request=_spawn_request(
            mission_id,
            task=_task("worker_model_scope", provider_id="unauthorized-provider"),
        ),
        worker_executor=_successful_executor,
    )

    assert provider_run.status is WorkerFleetRunStatus.BLOCKED
    assert provider_run.blocked_reason == "worker_authority_derivation_failed"
    assert provider_run.worker_results == []


def test_worker_fleet_records_durable_workflow_checkpoint_when_bound(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    workflow_store = DurableWorkflowStore(kernel.store)
    parent = _parent_envelope(mission_id)
    plan = _workflow_plan(mission_id)
    workflow = workflow_store.create(
        record=DurableWorkflowRecord.create(
            mission_id=mission_id,
            snapshot=WorkflowAuthoritySnapshot.from_runtime(
                envelope=parent,
                plan=plan,
                executor_contract_id="executor:worker-fleet:v1",
            ),
            initial_plan=plan,
        ),
        initial_plan=plan,
    )
    runtime = WorkerFleetRuntime(kernel, workflow_store=workflow_store)

    run = runtime.run(
        mission_id=mission_id,
        parent_envelope=parent,
        spawn_request=_spawn_request(
            mission_id,
            task=_task("worker_workflow_checkpoint"),
            metadata={"workflow_id": workflow.workflow_id},
        ),
        worker_executor=_successful_executor,
    )

    checkpoints = workflow_store.list_checkpoints(workflow.workflow_id)
    assert run.status is WorkerFleetRunStatus.COMPLETED
    assert checkpoints[-1].receipt_refs == ["receipt_worker"]
    assert checkpoints[-1].finalgate_certificate_refs == ["finalgate_worker"]
    assert workflow_store.verify(workflow.workflow_id) is True
    assert any(
        event.event_type == "worker_workflow_checkpoint_created"
        for event in kernel.store.load_events(mission_id)
    )


def _kernel_with_mission(
    tmp_path: Path,
    *,
    telemetry_sink: object | None = None,
) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path, telemetry_sink=telemetry_sink)
    record = kernel.create_mission(
        session_id="session_worker",
        draft=MissionDraft(
            title="Worker fleet mission",
            objective="Coordinate bounded worker tasks.",
            constraints=["no authority expansion"],
            expected_artifacts=["worker summary"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="mission_worker",
            allowed_actions=["read", "write", "verify"],
            forbidden_actions=["payment"],
            summary="Worker fleet authority summary.",
        ),
    )
    return kernel, record.mission_id


def _parent_envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_worker",
        mission_title="Worker fleet mission",
        mission_objective="Coordinate bounded worker tasks.",
        allowed_systems=["workspace", "browser"],
        allowed_tools=["workspace", "browser"],
        allowed_actions=["read", "write", "verify"],
        forbidden_actions=["payment", "credential_unlock"],
        allowed_paths=["data/generated_projects"],
        allowed_domains=["example.com"],
        allowed_data_types=["public"],
        max_duration_minutes=60,
        max_actions=10,
        max_cost_usd=5.0,
        max_recipients=0,
        risk_appetite_score=20.0,
    )


def _task(
    task_id: str,
    *,
    actions: list[str] | None = None,
    tools: list[str] | None = None,
    mode: WorkerExecutionMode = WorkerExecutionMode.RESEARCH,
    conflict_key: str | None = None,
    allow_power_runtime: bool = True,
    provider_id: str | None = None,
) -> WorkerTask:
    return WorkerTask(
        task_id=task_id,
        role=WorkerRole.RESEARCHER,
        execution_mode=mode,
        objective=f"Complete {task_id}.",
        scope=WorkerScope(
            allowed_actions=list(actions or ["read"]),
            allowed_tools=list(tools or ["workspace"]),
            allowed_systems=["workspace"],
            allowed_paths=["data/generated_projects"],
            allowed_domains=[],
            allowed_data_types=["public"],
            allow_power_runtime=allow_power_runtime,
            provider_id=provider_id,
        ),
        budget=WorkerBudget(max_actions=2, max_cost_usd=0.5),
        deadline=WorkerDeadline(timeout_seconds=30),
        result_contract=WorkerResultContract(
            required_evidence_refs=1,
            require_receipt_refs_for_execution=False,
            require_finalgate_refs_for_execution=False,
            conflict_key=conflict_key,
        ),
    )


def _spawn_request(
    mission_id: str,
    *,
    task: WorkerTask,
    extra_tasks: list[WorkerTask] | None = None,
    metadata: dict | None = None,
) -> WorkerSpawnRequest:
    return WorkerSpawnRequest(
        mission_id=mission_id,
        requested_by="operator",
        tasks=[task, *(extra_tasks or [])],
        safe_reason="Decompose mission into scoped workers.",
        metadata=metadata or {},
    )


def _successful_executor(context) -> WorkerResult:
    return _worker_result(context, safe_summary="Worker completed with evidence.")


def _worker_result(
    context,
    *,
    status: WorkerTaskStatus = WorkerTaskStatus.COMPLETED,
    safe_summary: str,
    output: dict | None = None,
    evidence_refs: list[str] | None = None,
    memory_feedback_refs: list[str] | None = None,
    actions_used: int = 0,
    cost_usd: float = 0.0,
) -> WorkerResult:
    return WorkerResult(
        worker_id=context.worker_id,
        task_id=context.task_id,
        status=status,
        result_contract_id=context.result_contract.contract_id,
        safe_summary=safe_summary,
        output=output or {"answer": "scoped result"},
        evidence_packet=WorkerEvidencePacket(
            evidence_refs=evidence_refs if evidence_refs is not None else ["evidence_worker"],
            receipt_refs=["receipt_worker"],
            finalgate_certificate_refs=["finalgate_worker"],
            memory_feedback_refs=memory_feedback_refs or [],
        ),
        actions_used=actions_used,
        cost_usd=cost_usd,
    )


def _workflow_plan(mission_id: str) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="worker_read",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="workspace",
                    action_kind="read",
                    request={"path": "data/generated_projects"},
                )
            ]
        ),
    )
