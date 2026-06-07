from __future__ import annotations

import threading
from datetime import UTC, datetime

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import OperatorAgentRuntimeBridge
from sentinel.operator.kernel import MissionKernel, TERMINAL_MISSION_STATUSES
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.power_bridge import BoundPowerActuatorExecutor, OperatorPowerRuntimeBridge
from sentinel.operator.replan_guard import ReplanExecutionGuard
from sentinel.operator.workflow_models import (
    DurableWorkflowRecord,
    ReplanCandidate,
    ReplanDecision,
    ReplanDecisionKind,
    ReplanExecutionPolicy,
    ReplanExecutionTarget,
    WorkflowAuthoritySnapshot,
    WorkflowBranch,
    WorkflowBranchStatus,
    WorkflowRunResult,
    WorkflowStatus,
    WorkflowStepState,
)
from sentinel.operator.workflow_store import DurableWorkflowStore
from sentinel.power.runtime import (
    PowerMissionGraph,
    PowerMissionPlan,
    PowerStepResult,
    PowerStepStatus,
)


_WORKFLOW_EXECUTION_LOCKS: dict[str, threading.RLock] = {}
_WORKFLOW_EXECUTION_LOCKS_GUARD = threading.Lock()


class DurableMissionWorkflowRuntime:
    """Restartable workflow controller around existing Sentinel runtimes.

    This controller owns durable orchestration state only. It never calls an
    organ or actuator directly; all execution goes through the existing
    PowerRuntime or AgentRuntime operator bridges.
    """

    def __init__(
        self,
        kernel: MissionKernel,
        *,
        policy: ReplanExecutionPolicy | None = None,
    ) -> None:
        self.kernel = kernel
        self.policy = policy or ReplanExecutionPolicy()
        self.guard = ReplanExecutionGuard(self.policy)
        self.store = DurableWorkflowStore(kernel.store)

    def create_power_workflow(
        self,
        *,
        mission_id: str,
        envelope: MissionAuthorityEnvelope,
        plan: PowerMissionPlan,
        executor_contract_id: str,
        provider_id: str | None = None,
        backend_id: str | None = None,
        model_id: str | None = None,
        model_contract_hash: str | None = None,
    ) -> DurableWorkflowRecord:
        if mission_id != envelope.id or mission_id != plan.mission_id:
            raise ValueError("workflow mission identity mismatch")
        snapshot = WorkflowAuthoritySnapshot.from_runtime(
            envelope=envelope,
            plan=plan,
            executor_contract_id=executor_contract_id,
            provider_id=provider_id,
            backend_id=backend_id,
            model_id=model_id,
            model_contract_hash=model_contract_hash,
        )
        record = DurableWorkflowRecord.create(mission_id=mission_id, snapshot=snapshot, initial_plan=plan)
        saved = self.store.create(record=record, initial_plan=plan)
        self.store.create_checkpoint(saved.workflow_id, safe_reason="Initial durable workflow checkpoint.")
        return self.store.load(saved.workflow_id)

    def run_power_tick(
        self,
        workflow_id: str,
        *,
        current_envelope: MissionAuthorityEnvelope,
        actuator_executor: BoundPowerActuatorExecutor | None = None,
        max_steps: int = 1,
    ) -> WorkflowRunResult:
        lock = self._execution_lock(workflow_id)
        if not lock.acquire(blocking=False):
            return self._already_active_result(workflow_id)
        try:
            return self._run_power_tick(
                workflow_id,
                current_envelope=current_envelope,
                actuator_executor=actuator_executor,
                max_steps=max_steps,
            )
        finally:
            lock.release()

    def _run_power_tick(
        self,
        workflow_id: str,
        *,
        current_envelope: MissionAuthorityEnvelope,
        actuator_executor: BoundPowerActuatorExecutor | None = None,
        max_steps: int = 1,
    ) -> WorkflowRunResult:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        if not self.store.verify(workflow_id):
            return self._blocked_tamper_result(workflow_id)
        record = self.store.load(workflow_id)
        mission_record = self.kernel.store.load_record(record.mission_id)
        if mission_record.status is OperatorMissionStatus.PAUSED:
            return self._result(record, WorkflowStatus.PAUSED, safe_summary="Mission is paused; no runtime step executed.")
        if mission_record.status in TERMINAL_MISSION_STATUSES:
            status = WorkflowStatus.KILLED if mission_record.status is OperatorMissionStatus.KILLED else WorkflowStatus.BLOCKED
            return self._result(record, status, safe_summary="Mission is terminal; no runtime step executed.")
        if record.status in {WorkflowStatus.WAITING_REPLAN, WorkflowStatus.WAITING_USER}:
            return self._result(record, record.status, safe_summary="Workflow is waiting at a governed boundary.")

        branch = _current_branch(record)
        if branch.execution_target is not ReplanExecutionTarget.POWER_RUNTIME:
            return self._result(record, WorkflowStatus.BLOCKED, safe_summary="Current workflow branch is not a PowerRuntime branch.")
        plan = self.store.load_plan(workflow_id, branch.plan_hash)
        checkpoint = self._latest_checkpoint(record)
        states = list(checkpoint.step_states)
        completed_ids = {state.step_id for state in states if state.status is PowerStepStatus.SUCCEEDED}
        if completed_ids == {step.step_id for step in plan.graph.steps}:
            record = self._set_status(record, WorkflowStatus.COMPLETED)
            self.kernel.update_status(record.mission_id, OperatorMissionStatus.COMPLETED, "Durable workflow completed.")
            return self._result(record, WorkflowStatus.COMPLETED, safe_summary="Durable workflow completed.")
        guard_decision = self.guard.evaluate(
            snapshot=record.snapshot,
            current_envelope=current_envelope,
            candidate=_resume_candidate(record, checkpoint, plan),
            completed_action_count=record.completed_action_count,
            reserved_action_count=record.reserved_action_count,
            cost_used_usd=record.cost_used_usd,
            reserved_cost_usd=record.reserved_cost_usd,
            latest_checkpoint_id=record.latest_checkpoint_id or "",
        )
        if guard_decision.kind is not ReplanDecisionKind.AUTO_EXECUTE:
            return self._guard_failure(record, guard_decision, current_envelope, states)

        if mission_record.status is not OperatorMissionStatus.RUNNING:
            self.kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Durable workflow running.")

        executed = 0
        while executed < max_steps:
            current_mission = self.kernel.store.load_record(record.mission_id)
            if current_mission.status is OperatorMissionStatus.PAUSED:
                return self._result(
                    record,
                    WorkflowStatus.PAUSED,
                    safe_summary="Mission paused before the next governed runtime step.",
                )
            if current_mission.status in TERMINAL_MISSION_STATUSES:
                status = (
                    WorkflowStatus.KILLED
                    if current_mission.status is OperatorMissionStatus.KILLED
                    else WorkflowStatus.BLOCKED
                )
                record = self._set_status(record, status)
                return self._result(
                    record,
                    status,
                    safe_summary="Mission became terminal before the next governed runtime step.",
                )
            completed_ids = {state.step_id for state in states if state.status is PowerStepStatus.SUCCEEDED}
            if completed_ids == {step.step_id for step in plan.graph.steps}:
                record = self._set_status(record, WorkflowStatus.COMPLETED)
                self.kernel.update_status(record.mission_id, OperatorMissionStatus.COMPLETED, "Durable workflow completed.")
                return self._result(record, WorkflowStatus.COMPLETED, safe_summary="Durable workflow completed.")
            iteration_guard = self.guard.evaluate(
                snapshot=record.snapshot,
                current_envelope=current_envelope,
                candidate=_resume_candidate(record, checkpoint, plan),
                completed_action_count=record.completed_action_count,
                reserved_action_count=record.reserved_action_count,
                cost_used_usd=record.cost_used_usd,
                reserved_cost_usd=record.reserved_cost_usd,
                latest_checkpoint_id=record.latest_checkpoint_id or "",
            )
            if iteration_guard.kind is not ReplanDecisionKind.AUTO_EXECUTE:
                return self._guard_failure(record, iteration_guard, current_envelope, states)
            ready = next(
                (
                    step
                    for step in plan.graph.steps
                    if step.step_id not in completed_ids and all(dep in completed_ids for dep in step.depends_on)
                ),
                None,
            )
            if ready is None:
                record = self._set_status(record, WorkflowStatus.BLOCKED)
                self.kernel.update_status(record.mission_id, OperatorMissionStatus.BLOCKED, "Workflow dependency state blocked.")
                return self._result(record, WorkflowStatus.BLOCKED, safe_summary="Workflow dependency state is not resumable.")

            projected = PowerMissionPlan(
                mission_id=plan.mission_id,
                graph=PowerMissionGraph(steps=[ready.model_copy(update={"depends_on": []})]),
            )
            reserved_actions = 1 + ready.retry_budget
            reserved_cost_usd = ready.estimated_cost_usd * reserved_actions
            try:
                record = self.store.reserve_actions(
                    workflow_id,
                    action_count=reserved_actions,
                    estimated_cost_usd=reserved_cost_usd,
                )
            except ValueError:
                decision = ReplanDecision(
                    kind=ReplanDecisionKind.ESCALATE,
                    candidate_id=f"resume:{workflow_id}",
                    guard_failures=["action_budget_expansion"],
                    safe_summary="Workflow action budget could not reserve the next governed step.",
                )
                return self._guard_failure(record, decision, current_envelope, states)
            try:
                runtime_result = OperatorPowerRuntimeBridge(self.kernel).run(
                    record.mission_id,
                    projected,
                    envelope=current_envelope,
                    executor_binding=actuator_executor,
                    expected_executor_contract_id=record.snapshot.executor_contract_id,
                    update_mission_status=False,
                )
                step_result = runtime_result.step_results[-1] if runtime_result.step_results else PowerStepResult(
                    step_id=ready.step_id,
                    status=PowerStepStatus.BLOCKED,
                    blocked_reason=runtime_result.blocked_reason or "power_runtime_no_step_result",
                    safe_summary="PowerRuntime returned no durable step result.",
                )
            except Exception:
                step_result = PowerStepResult(
                    step_id=ready.step_id,
                    status=PowerStepStatus.FAILED,
                    blocked_reason="operator_power_bridge_failure",
                    safe_summary="Operator PowerRuntime bridge raised a sanitized failure.",
                )
            checkpoint = self.store.commit_step_result(
                workflow_id,
                safe_reason=f"Checkpoint after governed step {step_result.step_id}.",
                step_result=step_result,
                reserved_actions=reserved_actions,
                reserved_cost_usd=reserved_cost_usd,
            )
            record = self.store.load(workflow_id)
            states = list(checkpoint.step_states)
            state = next(item for item in states if item.step_id == step_result.step_id)
            if state.status is not PowerStepStatus.SUCCEEDED:
                record = self._set_status(record, WorkflowStatus.WAITING_REPLAN)
                self.kernel.pause(record.mission_id, origin="workflow_replan")
                self.kernel.store.append_event(
                    record.mission_id,
                    event_type="workflow_replan_required",
                    safe_summary="Durable workflow paused for a governed replan.",
                    metadata={
                        "workflow_id": workflow_id,
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "blocked_reason": state.blocked_reason,
                    },
                )
                return self._result(
                    record,
                    WorkflowStatus.WAITING_REPLAN,
                    latest_checkpoint_id=checkpoint.checkpoint_id,
                    receipt_refs=checkpoint.receipt_refs,
                    finalgate_refs=checkpoint.finalgate_certificate_refs,
                    memory_refs=checkpoint.memory_feedback_refs,
                    safe_summary="Workflow requires a governed replan.",
                )
            executed += 1

        return self._result(
            self.store.load(workflow_id),
            WorkflowStatus.ACTIVE,
            latest_checkpoint_id=checkpoint.checkpoint_id,
            receipt_refs=checkpoint.receipt_refs,
            finalgate_refs=checkpoint.finalgate_certificate_refs,
            memory_refs=checkpoint.memory_feedback_refs,
            safe_summary="Workflow tick completed at a durable checkpoint.",
        )

    def execute_replan(
        self,
        candidate: ReplanCandidate,
        *,
        current_envelope: MissionAuthorityEnvelope,
        actuator_executor: BoundPowerActuatorExecutor | None = None,
        agent_bridge: OperatorAgentRuntimeBridge | None = None,
    ) -> WorkflowRunResult:
        lock = self._execution_lock(candidate.workflow_id)
        if not lock.acquire(blocking=False):
            return self._already_active_result(candidate.workflow_id)
        try:
            return self._execute_replan(
                candidate,
                current_envelope=current_envelope,
                actuator_executor=actuator_executor,
                agent_bridge=agent_bridge,
            )
        finally:
            lock.release()

    def _execute_replan(
        self,
        candidate: ReplanCandidate,
        *,
        current_envelope: MissionAuthorityEnvelope,
        actuator_executor: BoundPowerActuatorExecutor | None = None,
        agent_bridge: OperatorAgentRuntimeBridge | None = None,
    ) -> WorkflowRunResult:
        if not self.store.verify(candidate.workflow_id):
            return self._blocked_tamper_result(candidate.workflow_id)
        record = self.store.load(candidate.workflow_id)
        if candidate.workflow_id != record.workflow_id or candidate.mission_id != record.mission_id:
            return self._result(record, WorkflowStatus.BLOCKED, safe_summary="Replan mission identity mismatch.")
        mission_record = self.kernel.store.load_record(record.mission_id)
        mission_status = mission_record.status
        if mission_status in TERMINAL_MISSION_STATUSES:
            status = WorkflowStatus.KILLED if mission_status is OperatorMissionStatus.KILLED else WorkflowStatus.BLOCKED
            record = self._set_status(record, status)
            return self._result(record, status, safe_summary="Terminal mission cannot accept a replan branch.")
        resume_internal_pause = (
            mission_status is OperatorMissionStatus.PAUSED
            and mission_record.pause_origin == "workflow_replan"
            and record.status is WorkflowStatus.WAITING_REPLAN
        )
        if mission_status is OperatorMissionStatus.PAUSED and not resume_internal_pause:
            return self._result(record, WorkflowStatus.PAUSED, safe_summary="Operator pause prevents automatic replan.")
        decision = self.guard.evaluate(
            snapshot=record.snapshot,
            current_envelope=current_envelope,
            candidate=candidate,
            completed_action_count=record.completed_action_count,
            reserved_action_count=record.reserved_action_count,
            cost_used_usd=record.cost_used_usd,
            reserved_cost_usd=record.reserved_cost_usd,
            latest_checkpoint_id=record.latest_checkpoint_id or "",
        )
        if record.automatic_replan_count >= self.policy.max_automatic_replans:
            decision = ReplanDecision(
                kind=ReplanDecisionKind.ESCALATE,
                candidate_id=candidate.candidate_id,
                guard_failures=["automatic_replan_budget_exhausted"],
                safe_summary="Automatic replan budget exhausted.",
            )
        if decision.kind is not ReplanDecisionKind.AUTO_EXECUTE:
            return self._escalate_replan(record, decision)

        branch_hash = (
            stable_hash(candidate.power_plan.model_dump(mode="json"))
            if candidate.power_plan is not None
            else str(candidate.agent_input_hash)
        )
        branches = [
            branch.model_copy(update={"status": WorkflowBranchStatus.SUPERSEDED})
            if branch.branch_id == record.current_branch_id
            else branch
            for branch in record.branches
        ]
        branch = WorkflowBranch(
            parent_branch_id=record.current_branch_id,
            source_checkpoint_id=candidate.source_checkpoint_id,
            plan_hash=branch_hash,
            execution_target=candidate.execution_target,
            safe_reason=candidate.reason,
        )
        branches.append(branch)
        if candidate.power_plan is None:
            return self._result(
                record,
                WorkflowStatus.BLOCKED,
                decision=decision,
                safe_summary="AgentRuntime automatic replan is not supported without a typed PowerRuntime plan.",
            )
        checkpoint = self.store.transition_to_power_branch(
            record.workflow_id,
            plan=candidate.power_plan,
            branch=branch,
            branches=branches,
            safe_reason="Automatic replan branch accepted inside existing authority.",
            record_updates={
                "status": WorkflowStatus.ACTIVE,
                "automatic_replan_count": record.automatic_replan_count + 1,
            },
        )
        record = self.store.load(record.workflow_id)
        self.kernel.store.append_event(
            record.mission_id,
            event_type="workflow_replan_auto_executing",
            safe_summary="Replan guard approved an automatic branch inside existing authority.",
            metadata={
                "workflow_id": record.workflow_id,
                "branch_id": branch.branch_id,
                "candidate_id": candidate.candidate_id,
                "source_checkpoint_id": candidate.source_checkpoint_id,
            },
        )
        if resume_internal_pause:
            self.kernel.resume(record.mission_id)

        if candidate.execution_target is ReplanExecutionTarget.POWER_RUNTIME:
            result = self.run_power_tick(
                record.workflow_id,
                current_envelope=current_envelope,
                actuator_executor=actuator_executor,
                max_steps=50,
            )
            return result.model_copy(update={"decision": decision})

        if agent_bridge is None:
            return self._result(
                self._set_status(self.store.load(record.workflow_id), WorkflowStatus.BLOCKED),
                WorkflowStatus.BLOCKED,
                decision=decision,
                safe_summary="AgentRuntime bridge missing; replan failed closed.",
            )
        agent_result = agent_bridge.run(
            record.mission_id,
            envelope=current_envelope,
            user_input=dict(candidate.agent_user_input or {}),
            update_mission_status=False,
        )
        checkpoint = self.store.create_checkpoint(
            record.workflow_id,
            safe_reason="Checkpoint after governed AgentRuntime replan continuation.",
            receipt_refs=agent_result.receipt_refs,
            finalgate_certificate_refs=agent_result.finalgate_certificate_refs,
            memory_feedback_refs=agent_result.memory_feedback_refs,
        )
        status = WorkflowStatus.COMPLETED if agent_result.status == "completed" else WorkflowStatus.WAITING_REPLAN
        record = self._set_status(self.store.load(record.workflow_id), status)
        operator_status = (
            OperatorMissionStatus.COMPLETED
            if status is WorkflowStatus.COMPLETED
            else OperatorMissionStatus.PAUSED
        )
        self.kernel.update_status(record.mission_id, operator_status, f"AgentRuntime workflow branch {status.value}.")
        return self._result(
            record,
            status,
            decision=decision,
            latest_checkpoint_id=checkpoint.checkpoint_id,
            receipt_refs=checkpoint.receipt_refs,
            finalgate_refs=checkpoint.finalgate_certificate_refs,
            memory_refs=checkpoint.memory_feedback_refs,
            safe_summary=f"AgentRuntime replan branch {status.value}.",
        )

    def _guard_failure(
        self,
        record: DurableWorkflowRecord,
        decision: ReplanDecision,
        envelope: MissionAuthorityEnvelope,
        states: list[WorkflowStepState],
    ) -> WorkflowRunResult:
        terminal = "mission_revoked" in decision.guard_failures or "mission_expired" in decision.guard_failures
        status = WorkflowStatus.BLOCKED if terminal else WorkflowStatus.WAITING_USER
        record = self._set_status(record, status)
        checkpoint = self.store.create_checkpoint(
            record.workflow_id,
            safe_reason="Resume guard stopped workflow before runtime execution.",
            step_states=states,
        )
        target = OperatorMissionStatus.REVOKED if "mission_revoked" in decision.guard_failures else OperatorMissionStatus.PAUSED
        self.kernel.update_status(record.mission_id, target, "Workflow resume guard stopped execution.")
        return self._result(
            record,
            status,
            decision=decision,
            latest_checkpoint_id=checkpoint.checkpoint_id,
            safe_summary="Workflow resume requires authority resolution.",
        )

    def _escalate_replan(self, record: DurableWorkflowRecord, decision: ReplanDecision) -> WorkflowRunResult:
        record = self._set_status(record, WorkflowStatus.WAITING_USER)
        checkpoint = self.store.create_checkpoint(
            record.workflow_id,
            safe_reason="Replan escalated to an operator checkpoint.",
            step_states=self._latest_checkpoint(record).step_states,
        )
        mission_status = self.kernel.store.load_record(record.mission_id).status
        if mission_status is not OperatorMissionStatus.PAUSED:
            self.kernel.pause(record.mission_id, origin="workflow_escalation")
        self.kernel.store.append_event(
            record.mission_id,
            event_type="workflow_replan_escalated",
            safe_summary="Replan did not execute because an authority guard required escalation.",
            metadata={
                "workflow_id": record.workflow_id,
                "candidate_id": decision.candidate_id,
                "guard_failures": decision.guard_failures,
                "checkpoint_id": checkpoint.checkpoint_id,
            },
        )
        return self._result(
            self.store.load(record.workflow_id),
            WorkflowStatus.WAITING_USER,
            decision=decision,
            latest_checkpoint_id=checkpoint.checkpoint_id,
            safe_summary="Replan escalated without execution.",
        )

    def _blocked_tamper_result(self, workflow_id: str) -> WorkflowRunResult:
        try:
            record = self.store.load(workflow_id)
        except (OSError, ValueError, KeyError):
            return WorkflowRunResult(
                workflow_id=workflow_id,
                mission_id="unknown",
                status=WorkflowStatus.BLOCKED,
                safe_summary="Workflow integrity verification failed.",
            )
        return self._result(record, WorkflowStatus.BLOCKED, safe_summary="Workflow integrity verification failed.")

    def _already_active_result(self, workflow_id: str) -> WorkflowRunResult:
        try:
            record = self.store.load(workflow_id)
        except (OSError, ValueError, KeyError):
            return self._blocked_tamper_result(workflow_id)
        return self._result(
            record,
            WorkflowStatus.ACTIVE,
            safe_summary="A governed workflow tick is already active; duplicate execution was not started.",
        )

    def _execution_lock(self, workflow_id: str) -> threading.RLock:
        key = f"{self.kernel.store.run_root}:{workflow_id}"
        with _WORKFLOW_EXECUTION_LOCKS_GUARD:
            return _WORKFLOW_EXECUTION_LOCKS.setdefault(key, threading.RLock())

    def _latest_checkpoint(self, record: DurableWorkflowRecord):
        if not record.latest_checkpoint_id:
            raise ValueError("durable workflow has no checkpoint")
        return self.store.load_checkpoint(record.workflow_id, record.latest_checkpoint_id)

    def _set_status(self, record: DurableWorkflowRecord, status: WorkflowStatus) -> DurableWorkflowRecord:
        if record.status is status:
            return record
        return self.store.update_record(
            record.model_copy(update={"status": status, "updated_at": datetime.now(UTC)}),
            expected_version=record.record_version,
        )

    @staticmethod
    def _result(
        record: DurableWorkflowRecord,
        status: WorkflowStatus,
        *,
        decision: ReplanDecision | None = None,
        latest_checkpoint_id: str | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_refs: list[str] | None = None,
        memory_refs: list[str] | None = None,
        safe_summary: str,
    ) -> WorkflowRunResult:
        return WorkflowRunResult(
            workflow_id=record.workflow_id,
            mission_id=record.mission_id,
            status=status,
            decision=decision,
            latest_checkpoint_id=latest_checkpoint_id or record.latest_checkpoint_id,
            receipt_refs=list(receipt_refs or []),
            finalgate_certificate_refs=list(finalgate_refs or []),
            memory_feedback_refs=list(memory_refs or []),
            safe_summary=safe_summary,
        )


def _current_branch(record: DurableWorkflowRecord) -> WorkflowBranch:
    return next(branch for branch in record.branches if branch.branch_id == record.current_branch_id)


def _resume_candidate(
    record: DurableWorkflowRecord,
    checkpoint,
    plan: PowerMissionPlan,
) -> ReplanCandidate:
    completed_ids = {state.step_id for state in checkpoint.step_states if state.status is PowerStepStatus.SUCCEEDED}
    pending_plan = PowerMissionPlan(
        mission_id=plan.mission_id,
        graph=PowerMissionGraph(steps=[step for step in plan.graph.steps if step.step_id not in completed_ids]),
    )
    return ReplanCandidate(
        workflow_id=record.workflow_id,
        mission_id=record.mission_id,
        source_checkpoint_id=checkpoint.checkpoint_id,
        mission_objective_hash=record.snapshot.mission_objective_hash,
        power_plan=pending_plan,
        executor_contract_id=record.snapshot.executor_contract_id,
        provider_id=record.snapshot.provider_id,
        backend_id=record.snapshot.backend_id,
        model_id=record.snapshot.model_id,
        model_contract_hash=record.snapshot.model_contract_hash,
        reason="resume existing governed workflow branch",
    )
