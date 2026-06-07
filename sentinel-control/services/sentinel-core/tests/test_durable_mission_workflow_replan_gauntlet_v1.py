from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import OperatorAgentRuntimeBridge
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.power_bridge import BoundPowerActuatorExecutor
from sentinel.operator.workflow_models import (
    ReplanCandidate,
    ReplanDecisionKind,
    ReplanExecutionTarget,
    WorkflowBranch,
    WorkflowBranchStatus,
    WorkflowStepState,
    WorkflowStatus,
)
from sentinel.operator.workflow_replay import DurableWorkflowReplayBuilder
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
    PowerStepResult,
    PowerStepStatus,
)


def _kernel_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    mission = kernel.create_mission(
        session_id="session_durable",
        draft=MissionDraft(
            title="Durable workflow",
            objective="Research the approved market and prepare a report.",
        ),
    )
    kernel.enqueue(mission.mission_id)
    return kernel, mission.mission_id


def _envelope(mission_id: str, **updates) -> MissionAuthorityEnvelope:
    base = {
        "id": mission_id,
        "user_id": "user_durable",
        "mission_title": "Durable workflow",
        "mission_objective": "Research the approved market and prepare a report.",
        "allowed_systems": ["browser", "workspace"],
        "allowed_tools": ["browser_readonly", "reversible_workspace"],
        "allowed_actions": ["observe", "write"],
        "forbidden_actions": ["payment", "send_email"],
        "allowed_paths": ["data/generated_projects"],
        "allowed_domains": ["example.com"],
        "max_actions": 8,
        "max_cost_usd": 5.0,
        "max_recipients": 0,
        "risk_appetite_score": 35.0,
    }
    base.update(updates)
    return MissionAuthorityEnvelope(**base)


def _plan(mission_id: str, *, alternate: bool = False, domain: str = "example.com") -> PowerMissionPlan:
    selector = "#alternate" if alternate else "#primary"
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
                    request={"url": f"https://{domain}/research", "selector": selector},
                ),
                PowerMissionStep(
                    step_id="write_report",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                    request={"path": "data/generated_projects/report.md"},
                    depends_on=["observe"],
                ),
            ]
        ),
    )


def _executor(calls: list[str]):
    def execute(step, _context):
        calls.append(step.step_id)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[f"receipt:{step.step_id}:{len(calls)}"],
            finalgate_certificate_refs=[f"finalgate:{step.step_id}:{len(calls)}"],
            memory_feedback_refs=[f"memory:{step.step_id}:{len(calls)}"],
            safe_summary=f"{step.step_id} completed",
        )

    return execute


def _bound(executor):
    return BoundPowerActuatorExecutor(contract_id="executor:governed:v1", executor=executor)


def _runtime(tmp_path: Path):
    kernel, mission_id = _kernel_mission(tmp_path)
    runtime = DurableMissionWorkflowRuntime(kernel)
    envelope = _envelope(mission_id)
    record = runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=envelope,
        plan=_plan(mission_id),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
    )
    return kernel, runtime, envelope, record


def test_power_workflow_checkpoints_and_resume_does_not_repeat_certified_step(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []

    first = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
        max_steps=1,
    )
    resumed = DurableMissionWorkflowRuntime(MissionKernel(run_root=tmp_path)).run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
        max_steps=5,
    )

    assert first.status is WorkflowStatus.ACTIVE
    assert resumed.status is WorkflowStatus.COMPLETED
    assert calls == ["observe", "write_report"]
    assert len(runtime.store.list_checkpoints(record.workflow_id)) >= 2


def test_automatic_replan_executes_equivalent_branch_inside_authority(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.FAILED,
            blocked_reason="transient_timeout",
            safe_summary="transient timeout",
        )),
        max_steps=1,
    )
    latest = runtime.store.load(record.workflow_id).latest_checkpoint_id
    calls: list[str] = []
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(latest),
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, alternate=True),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="retry equivalent authorized branch after transient timeout",
    )

    result = runtime.execute_replan(
        candidate,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
    )

    assert result.decision.kind is ReplanDecisionKind.AUTO_EXECUTE
    assert result.status is WorkflowStatus.COMPLETED
    assert calls == ["observe", "write_report"]
    assert runtime.store.load(record.workflow_id).automatic_replan_count == 1


def test_replan_scope_expansion_creates_user_checkpoint_without_execution(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    latest = runtime.store.load(record.workflow_id).latest_checkpoint_id
    calls: list[str] = []
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(latest),
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, domain="outside.example.net"),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="try a new endpoint",
    )

    result = runtime.execute_replan(
        candidate,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
    )

    assert result.decision.kind is ReplanDecisionKind.ESCALATE
    assert result.status is WorkflowStatus.WAITING_USER
    assert calls == []
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.PAUSED


def test_pause_kill_and_revocation_stop_before_next_runtime_step(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []
    kernel.pause(record.mission_id)

    paused = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
    )
    kernel.resume(record.mission_id)
    revoked = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope.model_copy(update={"revoked_at": envelope.created_at}),
        actuator_executor=_bound(_executor(calls)),
    )

    assert paused.status is WorkflowStatus.PAUSED
    assert revoked.status is WorkflowStatus.BLOCKED
    assert calls == []


def test_agent_replan_is_escalated_until_a_typed_action_plan_exists(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    latest = runtime.store.load(record.workflow_id).latest_checkpoint_id
    calls: list[tuple[str, dict]] = []

    class FakeAgentRuntime:
        def run(self, received_envelope, user_input):
            calls.append((received_envelope.id, user_input))
            return SimpleNamespace(
                success=True,
                final_gate_certification=SimpleNamespace(id="finalgate:agent"),
                memory_feedback_result=SimpleNamespace(memory_entry_refs=["memory:agent"]),
                replan_packet={"status": "CLOSED", "mission_id": received_envelope.id},
                replan_ready=True,
                automatic_replan_executed=False,
            )

    safe_input = {
        "mission_id": record.mission_id,
        "source_replan_packet": "replan:source",
        "use_memory_feedback_refs": ["memory:agent"],
        "automatic_replan_executed": False,
    }
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(latest),
        mission_objective=envelope.mission_objective,
        execution_target=ReplanExecutionTarget.AGENT_RUNTIME,
        agent_user_input=safe_input,
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="continue from the existing replan packet",
        source_replan_packet_ref="replan:source",
    )

    result = runtime.execute_replan(
        candidate,
        current_envelope=envelope,
        agent_bridge=OperatorAgentRuntimeBridge(kernel, runtime=FakeAgentRuntime()),
    )

    assert result.decision.kind is ReplanDecisionKind.ESCALATE
    assert "agent_runtime_replan_requires_typed_plan" in result.decision.guard_failures
    assert calls == []
    assert result.can_grant_authority is False


def test_workflow_replay_reconstructs_without_reexecution(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []
    runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
        max_steps=1,
    )

    replay = DurableWorkflowReplayBuilder(runtime.store).build(record.workflow_id)

    assert replay.reexecuted_actions is False
    assert replay.tampered is False
    assert calls == ["observe"]


def test_agent_bridge_rejects_envelope_mission_identity_mismatch(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    calls: list[str] = []

    class FakeAgentRuntime:
        def run(self, received_envelope, user_input):
            calls.append(received_envelope.id)
            return SimpleNamespace(success=True)

    result = OperatorAgentRuntimeBridge(kernel, runtime=FakeAgentRuntime()).run(
        mission_id,
        envelope=_envelope("mission_other"),
        user_input={"mission_id": mission_id},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "mission_identity_mismatch"
    assert calls == []


def test_retry_attempts_consume_action_budget_and_resume_only_counts_pending_steps(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    envelope = _envelope(mission_id, max_actions=2)
    retry_plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[_plan(mission_id).graph.steps[0].model_copy(update={"retry_budget": 1})]
        ),
    )
    runtime = DurableMissionWorkflowRuntime(kernel)
    record = runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=envelope,
        plan=retry_plan,
        executor_contract_id="executor:governed:v1",
    )
    calls: list[str] = []

    def fail_then_succeed(step, _context):
        calls.append(step.step_id)
        if len(calls) == 1:
            return PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.FAILED,
                blocked_reason="transient_timeout",
                safe_summary="transient timeout",
            )
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:retry"],
            finalgate_certificate_refs=["finalgate:retry"],
            safe_summary="retry succeeded",
        )

    first = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(fail_then_succeed),
        max_steps=1,
    )
    completed = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(fail_then_succeed),
        max_steps=1,
    )

    assert first.status is WorkflowStatus.ACTIVE
    assert completed.status is WorkflowStatus.COMPLETED
    assert runtime.store.load(record.workflow_id).completed_action_count == 2
    assert calls == ["observe", "observe"]


def test_malformed_workflow_record_fails_closed_without_raw_exception(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    record_path = tmp_path / record.mission_id / "workflow" / "record.json"
    record_path.write_text("{malformed", encoding="utf-8")

    result = runtime.run_power_tick(record.workflow_id, current_envelope=envelope)

    assert result.status is WorkflowStatus.BLOCKED
    assert result.mission_id == "unknown"
    assert "malformed" not in result.safe_summary.lower()


def test_replay_of_malformed_workflow_record_reports_tamper_without_reexecution(tmp_path: Path) -> None:
    _kernel, runtime, _envelope_value, record = _runtime(tmp_path)
    record_path = tmp_path / record.mission_id / "workflow" / "record.json"
    record_path.write_text("{malformed", encoding="utf-8")

    replay = DurableWorkflowReplayBuilder(runtime.store).build(record.workflow_id)

    assert replay.tampered is True
    assert replay.reexecuted_actions is False
    assert replay.record is None


def test_kill_during_tick_stops_before_next_power_step(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []

    def kill_after_first_step(step, _context):
        calls.append(step.step_id)
        kernel.kill(record.mission_id)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[f"receipt:{step.step_id}"],
            finalgate_certificate_refs=[f"finalgate:{step.step_id}"],
            safe_summary="step completed before kill was observed",
        )

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(kill_after_first_step),
        max_steps=5,
    )

    assert calls == ["observe"]
    assert result.status is WorkflowStatus.KILLED


def test_raw_secret_like_refs_and_summaries_are_not_persisted(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    raw_secret = "Bearer abcdefghijklmnopqrstuvwxyz"

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[raw_secret],
            finalgate_certificate_refs=[raw_secret],
            memory_feedback_refs=[raw_secret],
            safe_summary=f"completed with {raw_secret}",
        )),
        max_steps=1,
    )
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / record.mission_id).rglob("*")
        if path.is_file()
    )

    assert raw_secret not in persisted
    assert raw_secret not in str(result.model_dump(mode="json"))


def test_revocation_during_tick_stops_before_next_power_step(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []

    def revoke_after_first_step(step, _context):
        calls.append(step.step_id)
        envelope.revoked_at = envelope.created_at
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[f"receipt:{step.step_id}"],
            finalgate_certificate_refs=[f"finalgate:{step.step_id}"],
            safe_summary="step completed before revocation was observed",
        )

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(revoke_after_first_step),
        max_steps=5,
    )

    assert calls == ["observe"]
    assert result.status is WorkflowStatus.BLOCKED


def test_stale_replan_creates_operator_checkpoint_without_execution(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id="workflow_checkpoint_stale",
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, alternate=True),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="stale continuation",
    )

    result = runtime.execute_replan(
        candidate,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
    )

    assert result.status is WorkflowStatus.WAITING_USER
    assert result.decision is not None
    assert "stale_replan_checkpoint" in result.decision.guard_failures
    assert calls == []


def test_replan_does_not_create_branch_after_kill(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    kernel.kill(record.mission_id)
    before = runtime.store.load(record.workflow_id)
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(before.latest_checkpoint_id),
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, alternate=True),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="must not revive killed work",
    )

    result = runtime.execute_replan(candidate, current_envelope=envelope, actuator_executor=_bound(_executor([])))
    after = runtime.store.load(record.workflow_id)

    assert result.status is WorkflowStatus.KILLED
    assert after.automatic_replan_count == before.automatic_replan_count
    assert after.branches == before.branches


def test_replan_does_not_resume_an_operator_pause(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    kernel.pause(record.mission_id)
    before = runtime.store.load(record.workflow_id)
    calls: list[str] = []
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(before.latest_checkpoint_id),
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, alternate=True),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="must not override operator pause",
    )

    result = runtime.execute_replan(candidate, current_envelope=envelope, actuator_executor=_bound(_executor(calls)))
    after = runtime.store.load(record.workflow_id)

    assert result.status is WorkflowStatus.PAUSED
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.PAUSED
    assert after.automatic_replan_count == before.automatic_replan_count
    assert calls == []


def test_workflow_checkpoints_are_listed_in_version_order(tmp_path: Path) -> None:
    _kernel, runtime, _envelope_value, record = _runtime(tmp_path)
    runtime.store.create_checkpoint(record.workflow_id, safe_reason="second")
    runtime.store.create_checkpoint(record.workflow_id, safe_reason="third")
    checkpoint_dir = tmp_path / record.mission_id / "workflow" / "checkpoints"
    checkpoint_files = list(checkpoint_dir.glob("*.json"))
    parsed = [(path, runtime.store.load_checkpoint(record.workflow_id, path.stem)) for path in checkpoint_files]
    for index, (path, checkpoint) in enumerate(sorted(parsed, key=lambda item: item[1].record_version, reverse=True)):
        path.rename(checkpoint_dir / f"{index:03d}.json")

    checkpoints = runtime.store.list_checkpoints(record.workflow_id)

    assert [checkpoint.record_version for checkpoint in checkpoints] == sorted(
        checkpoint.record_version for checkpoint in checkpoints
    )


def test_parallel_ticks_do_not_execute_the_same_step_twice(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    calls: list[str] = []
    calls_lock = threading.Lock()

    def blocking_executor(step, _context):
        with calls_lock:
            calls.append(step.step_id)
        entered.set()
        release.wait(timeout=5)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=[f"receipt:{step.step_id}"],
            finalgate_certificate_refs=[f"finalgate:{step.step_id}"],
            safe_summary="step completed",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            runtime.run_power_tick,
            record.workflow_id,
            current_envelope=envelope,
            actuator_executor=_bound(blocking_executor),
            max_steps=1,
        )
        assert entered.wait(timeout=5)
        second = pool.submit(
            DurableMissionWorkflowRuntime(MissionKernel(run_root=tmp_path)).run_power_tick,
            record.workflow_id,
            current_envelope=envelope,
            actuator_executor=_bound(blocking_executor),
            max_steps=1,
        )
        second_result = second.result(timeout=5)
        release.set()
        first_result = first.result(timeout=5)

    assert calls == ["observe"]
    assert first_result.status is WorkflowStatus.ACTIVE
    assert second_result.status is WorkflowStatus.ACTIVE
    assert "already active" in second_result.safe_summary.lower()


def test_mission_lifecycle_transition_holds_store_lock(tmp_path: Path, monkeypatch) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    lock_held = False
    original_update = kernel.store.update_record_status

    @contextmanager
    def tracked_lock():
        nonlocal lock_held
        lock_held = True
        try:
            yield
        finally:
            lock_held = False

    def asserting_update(target_mission_id, status, **kwargs):
        assert lock_held is True
        return original_update(target_mission_id, status, **kwargs)

    monkeypatch.setattr(kernel.store, "locked", tracked_lock)
    monkeypatch.setattr(kernel.store, "update_record_status", asserting_update)

    kernel.pause(mission_id)


def test_mission_event_append_fsyncs_before_return(tmp_path: Path, monkeypatch) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    calls: list[int] = []

    monkeypatch.setattr("sentinel.operator.store.os.fsync", lambda descriptor: calls.append(descriptor))

    kernel.store.append_event(mission_id, event_type="durability_probe", safe_summary="Durability probe.")

    assert calls


def test_forged_checkpoint_proof_cannot_skip_dependency(tmp_path: Path) -> None:
    _kernel, runtime, _envelope_value, record = _runtime(tmp_path)

    with pytest.raises(ValueError, match="durable step proof"):
        runtime.store.create_checkpoint(
            record.workflow_id,
            safe_reason="forged proof must not become permission",
            step_states=[
                WorkflowStepState(
                    step_id="observe",
                    status=PowerStepStatus.SUCCEEDED,
                    receipt_refs=["receipt:forged"],
                    finalgate_certificate_refs=["finalgate:forged"],
                    result_hash="result:forged",
                    proof_id="proof:forged",
                )
            ],
        )


def test_current_branch_must_match_latest_checkpoint(tmp_path: Path) -> None:
    _kernel, runtime, _envelope_value, record = _runtime(tmp_path)
    current = runtime.store.load(record.workflow_id)
    original = next(branch for branch in current.branches if branch.branch_id == current.current_branch_id)
    forged = WorkflowBranch(
        parent_branch_id=original.branch_id,
        source_checkpoint_id=current.latest_checkpoint_id,
        plan_hash=original.plan_hash,
        status=WorkflowBranchStatus.ACTIVE,
        safe_reason="forged branch without checkpoint",
    )
    with pytest.raises(ValueError, match="status only"):
        runtime.store.update_record(
            current.model_copy(
                update={
                    "branches": [
                        original.model_copy(update={"status": WorkflowBranchStatus.SUPERSEDED}),
                        forged,
                    ],
                    "current_branch_id": forged.branch_id,
                }
            ),
            expected_version=current.record_version,
        )

    assert runtime.store.verify(record.workflow_id) is True


def test_action_attempt_budget_is_reserved_before_executor_call(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    envelope = _envelope(mission_id, max_actions=3)
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[_plan(mission_id).graph.steps[0].model_copy(update={"retry_budget": 2})]
        ),
    )
    observed_reserved_counts: list[int] = []

    def executor(step, _context):
        workflow = runtime.store.load(record.workflow_id)
        observed_reserved_counts.append(workflow.reserved_action_count)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:reserved"],
            finalgate_certificate_refs=["finalgate:reserved"],
            safe_summary="reserved execution",
        )

    runtime = DurableMissionWorkflowRuntime(kernel)
    record = runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=envelope,
        plan=plan,
        executor_contract_id="executor:governed:v1",
    )
    runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(executor),
        max_steps=1,
    )

    assert observed_reserved_counts == [3]
    stored = runtime.store.load(record.workflow_id)
    assert stored.reserved_action_count == 0
    assert stored.completed_action_count == 1


def test_typed_step_cost_is_reserved_before_execution_and_debited_after_checkpoint(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    envelope = _envelope(mission_id, max_cost_usd=1.0)
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[_plan(mission_id).graph.steps[0].model_copy(update={"estimated_cost_usd": 0.25})]
        ),
    )
    observed_reserved_costs: list[float] = []

    def executor(step, _context):
        observed_reserved_costs.append(runtime.store.load(record.workflow_id).reserved_cost_usd)
        return PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:cost"],
            finalgate_certificate_refs=["finalgate:cost"],
            safe_summary="costed step completed",
        )

    runtime = DurableMissionWorkflowRuntime(kernel)
    record = runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=envelope,
        plan=plan,
        executor_contract_id="executor:governed:v1",
    )
    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(executor),
        max_steps=1,
    )

    stored = runtime.store.load(record.workflow_id)
    assert result.status is WorkflowStatus.ACTIVE
    assert observed_reserved_costs == [0.25]
    assert stored.reserved_cost_usd == 0.0
    assert stored.cost_used_usd == 0.25


def test_typed_step_cost_reservation_covers_retry_worst_case(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    envelope = _envelope(mission_id, max_cost_usd=0.5)
    plan = PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                _plan(mission_id).graph.steps[0].model_copy(
                    update={"estimated_cost_usd": 0.25, "retry_budget": 2}
                )
            ]
        ),
    )
    calls: list[str] = []
    runtime = DurableMissionWorkflowRuntime(kernel)
    record = runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=envelope,
        plan=plan,
        executor_contract_id="executor:governed:v1",
    )

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
        max_steps=1,
    )

    assert calls == []
    assert result.status is WorkflowStatus.WAITING_USER
    assert result.decision is not None
    assert "action_budget_expansion" not in result.decision.guard_failures
    assert "cost_budget_expansion" in result.decision.guard_failures


def test_mismatched_bound_executor_contract_fails_closed(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    calls: list[str] = []
    binding = BoundPowerActuatorExecutor(contract_id="executor:other", executor=_executor(calls))

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=binding,
        max_steps=1,
    )

    assert calls == []
    assert result.status is WorkflowStatus.WAITING_REPLAN
    checkpoint = runtime.store.load_checkpoint(record.workflow_id, str(result.latest_checkpoint_id))
    assert checkpoint.step_states[-1].blocked_reason == "executor_contract_mismatch"


def test_replan_branch_transition_failure_leaves_previous_branch_current(tmp_path: Path, monkeypatch) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    before = runtime.store.load(record.workflow_id)
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(before.latest_checkpoint_id),
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, alternate=True),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="crash-consistency probe",
    )
    original_write = runtime.store.mission_store.atomic_write_json

    def fail_checkpoint_write(path, payload):
        if "checkpoints" in path.parts:
            raise OSError("simulated checkpoint write failure")
        return original_write(path, payload)

    monkeypatch.setattr(runtime.store.mission_store, "atomic_write_json", fail_checkpoint_write)

    with pytest.raises(OSError, match="simulated checkpoint"):
        runtime.execute_replan(
            candidate,
            current_envelope=envelope,
            actuator_executor=_bound(_executor([])),
        )

    after = runtime.store.load(record.workflow_id)
    assert after.current_branch_id == before.current_branch_id
    assert after.latest_checkpoint_id == before.latest_checkpoint_id
    assert runtime.store.verify(record.workflow_id) is True


def test_bridge_exception_becomes_safe_failed_proof_and_releases_reservation(tmp_path: Path, monkeypatch) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)

    def raise_bridge_failure(*_args, **_kwargs):
        raise RuntimeError("Bearer raw_bridge_secret_123456789")

    monkeypatch.setattr("sentinel.operator.workflow_runtime.OperatorPowerRuntimeBridge.run", raise_bridge_failure)

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor([])),
        max_steps=1,
    )
    stored = runtime.store.load(record.workflow_id)
    persisted = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / record.mission_id).rglob("*")
        if path.is_file()
    )

    assert result.status is WorkflowStatus.WAITING_REPLAN
    assert stored.reserved_action_count == 0
    assert stored.reserved_cost_usd == 0.0
    assert "raw_bridge_secret" not in persisted


def test_tamper_block_does_not_rehash_and_launder_record(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    record_path = tmp_path / record.mission_id / "workflow" / "record.json"
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["status"] = WorkflowStatus.COMPLETED.value
    record_path.write_text(json.dumps(payload), encoding="utf-8")

    assert runtime.store.verify(record.workflow_id) is False
    result = runtime.run_power_tick(record.workflow_id, current_envelope=envelope)

    assert result.status is WorkflowStatus.BLOCKED
    assert runtime.store.verify(record.workflow_id) is False


def test_replay_of_malformed_checkpoint_reports_tamper(tmp_path: Path) -> None:
    _kernel, runtime, _envelope_value, record = _runtime(tmp_path)
    checkpoint_path = next((tmp_path / record.mission_id / "workflow" / "checkpoints").glob("*.json"))
    checkpoint_path.write_text("{malformed", encoding="utf-8")

    replay = DurableWorkflowReplayBuilder(runtime.store).build(record.workflow_id)

    assert replay.tampered is True
    assert replay.reexecuted_actions is False


def test_agent_bridge_secret_refs_are_not_persisted(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    raw_secret = "Bearer agentruntime_secret_123456789"

    class FakeAgentRuntime:
        def run(self, received_envelope, user_input):
            return SimpleNamespace(
                success=True,
                receipt_refs=[raw_secret],
                final_gate_certification=SimpleNamespace(id=raw_secret),
                memory_feedback_result=SimpleNamespace(memory_entry_refs=[raw_secret]),
            )

    result = OperatorAgentRuntimeBridge(kernel, runtime=FakeAgentRuntime()).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )
    persisted = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*") if path.is_file())

    assert raw_secret not in persisted
    assert raw_secret not in str(result.model_dump(mode="json"))


def test_mission_record_tamper_cannot_resurrect_killed_workflow(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    kernel.kill(record.mission_id)
    record_path = tmp_path / record.mission_id / "record.json"
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["status"] = OperatorMissionStatus.RUNNING.value
    record_path.write_text(json.dumps(payload), encoding="utf-8")
    calls: list[str] = []

    result = runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
    )

    assert calls == []
    assert result.status is WorkflowStatus.BLOCKED
    assert runtime.store.verify(record.workflow_id) is False


def test_empty_replan_cannot_auto_complete_mission(tmp_path: Path) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(record.latest_checkpoint_id),
        mission_objective=envelope.mission_objective,
        power_plan=PowerMissionPlan(mission_id=record.mission_id, graph=PowerMissionGraph(steps=[])),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="empty branch must not complete",
    )

    result = runtime.execute_replan(candidate, current_envelope=envelope, actuator_executor=_bound(_executor([])))

    assert result.status is WorkflowStatus.WAITING_USER
    assert result.decision is not None
    assert "empty_replan_plan" in result.decision.guard_failures


def test_explicit_pause_after_internal_replan_pause_is_not_auto_resumed(tmp_path: Path) -> None:
    kernel, runtime, envelope, record = _runtime(tmp_path)
    runtime.run_power_tick(
        record.workflow_id,
        current_envelope=envelope,
        actuator_executor=_bound(
            lambda step, _context: PowerStepResult(
                step_id=step.step_id,
                status=PowerStepStatus.FAILED,
                blocked_reason="transient_timeout",
                safe_summary="transient timeout",
            )
        ),
    )
    kernel.pause(record.mission_id)
    current = runtime.store.load(record.workflow_id)
    calls: list[str] = []
    candidate = ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=str(current.latest_checkpoint_id),
        mission_objective=envelope.mission_objective,
        power_plan=_plan(record.mission_id, alternate=True),
        executor_contract_id="executor:governed:v1",
        provider_id="ollama",
        backend_id="ollama_openai_compatible",
        model_id="qwen3",
        reason="must respect explicit operator pause",
    )

    result = runtime.execute_replan(
        candidate,
        current_envelope=envelope,
        actuator_executor=_bound(_executor(calls)),
    )

    assert calls == []
    assert result.status is WorkflowStatus.PAUSED
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.PAUSED


def test_workflow_rejects_common_secret_forms_before_persistence(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_mission(tmp_path)
    runtime = DurableMissionWorkflowRuntime(kernel)
    envelope = _envelope(mission_id)
    with pytest.raises(ValueError, match="power runtime payload rejected"):
        secret_plan = _plan(mission_id).model_copy(
            update={
                "graph": PowerMissionGraph(
                    steps=[
                        _plan(mission_id).graph.steps[0].model_copy(
                            update={
                                "request": {
                                    "url": "https://example.com/research?access_token=raw_oauth_value_123456"
                                }
                            }
                        )
                    ]
                )
            }
        )
        runtime.create_power_workflow(
            mission_id=mission_id,
            envelope=envelope,
            plan=secret_plan,
            executor_contract_id="executor:governed:v1",
        )
    assert "raw_oauth_value_123456" not in "\n".join(
        path.read_text(encoding="utf-8") for path in tmp_path.rglob("*") if path.is_file()
    )


@pytest.mark.parametrize(
    "secret_reason",
    [
        "access_token=raw_access_value_123456",
        "refresh_token=raw_refresh_value_123456",
        "session_token=raw_session_value_123456",
        "sessionid=raw_session_id_123456",
        "Cookie: raw_cookie_value_123456",
        "x-api-key=raw_api_value_123456",
    ],
)
def test_replan_candidate_rejects_common_secret_reason_forms(
    tmp_path: Path,
    secret_reason: str,
) -> None:
    _kernel, runtime, envelope, record = _runtime(tmp_path)

    with pytest.raises(ValueError, match="secret-like"):
        ReplanCandidate(
            workflow_id=record.workflow_id,
            mission_id=record.mission_id,
            source_checkpoint_id=str(record.latest_checkpoint_id),
            mission_objective=envelope.mission_objective,
            power_plan=_plan(record.mission_id, alternate=True),
            executor_contract_id="executor:governed:v1",
            provider_id="ollama",
            backend_id="ollama_openai_compatible",
            model_id="qwen3",
            reason=secret_reason,
        )


def test_checkpoint_event_failure_does_not_publish_checkpoint_or_record(tmp_path: Path, monkeypatch) -> None:
    _kernel, runtime, _envelope_value, record = _runtime(tmp_path)
    before = runtime.store.load(record.workflow_id)
    checkpoint_count = len(runtime.store.list_checkpoints(record.workflow_id))
    original_append = runtime.store.mission_store.append_event

    def fail_checkpoint_event(mission_id, *, event_type, **kwargs):
        if event_type == "workflow_checkpoint_prepared":
            raise OSError("simulated checkpoint event failure")
        return original_append(mission_id, event_type=event_type, **kwargs)

    monkeypatch.setattr(runtime.store.mission_store, "append_event", fail_checkpoint_event)

    with pytest.raises(OSError, match="checkpoint event"):
        runtime.store.create_checkpoint(record.workflow_id, safe_reason="must remain unpublished")

    after = runtime.store.load(record.workflow_id)
    assert after.latest_checkpoint_id == before.latest_checkpoint_id
    assert after.record_version == before.record_version
    assert len(runtime.store.list_checkpoints(record.workflow_id)) == checkpoint_count
    assert runtime.store.verify(record.workflow_id) is True
