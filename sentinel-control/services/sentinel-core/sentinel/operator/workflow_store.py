from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, sanitize_operator_refs
from sentinel.operator.store import MissionRunStore
from sentinel.operator.workflow_models import (
    assert_workflow_plan_persistable,
    DurableWorkflowRecord,
    ReplanExecutionTarget,
    ResumeCursor,
    step_contract_hash_from_step,
    WorkflowBranch,
    WorkflowCheckpoint,
    WorkflowStepProof,
    WorkflowStepState,
    WorkflowStatus,
)
from sentinel.power.runtime import PowerMissionPlan, PowerStepResult, PowerStepStatus
from sentinel.shared.models import new_id


class DurableWorkflowStore:
    """Durable workflow extension inside the existing MissionRunStore root."""

    def __init__(self, mission_store: MissionRunStore) -> None:
        self.mission_store = mission_store

    def create(self, *, record: DurableWorkflowRecord, initial_plan: PowerMissionPlan) -> DurableWorkflowRecord:
        if record.mission_id != initial_plan.mission_id:
            raise ValueError("workflow plan mission mismatch")
        self.mission_store.load_record(record.mission_id)
        expected_plan_hash = stable_hash(initial_plan.model_dump(mode="json"))
        if record.initial_plan_hash != expected_plan_hash:
            raise ValueError("initial workflow plan hash mismatch")
        with self.mission_store.locked():
            paths = self._paths_for_mission(record.mission_id)
            if paths.record.exists():
                raise ValueError("workflow already exists for mission")
            self._write_plan(paths, initial_plan)
            self._write_record(paths, record.with_hash())
            self.mission_store.append_event(
                record.mission_id,
                event_type="durable_workflow_created",
                safe_summary="Durable mission workflow created inside the existing mission run.",
                metadata={"workflow_id": record.workflow_id, "plan_hash": expected_plan_hash},
            )
        return self.load(record.workflow_id)

    def load(self, workflow_id: str) -> DurableWorkflowRecord:
        paths = self._find_paths(workflow_id)
        return DurableWorkflowRecord.model_validate(json.loads(paths.record.read_text(encoding="utf-8")))

    def load_plan(self, workflow_id: str, plan_hash: str) -> PowerMissionPlan:
        paths = self._find_paths(workflow_id)
        path = paths.plans / f"{plan_hash}.json"
        plan = PowerMissionPlan.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if stable_hash(plan.model_dump(mode="json")) != plan_hash:
            raise ValueError("workflow plan hash mismatch")
        return plan

    def save_plan(self, workflow_id: str, plan: PowerMissionPlan) -> str:
        record = self.load(workflow_id)
        if plan.mission_id != record.mission_id:
            raise ValueError("workflow plan mission mismatch")
        paths = self._find_paths(workflow_id)
        return self._write_plan(paths, plan)

    def create_checkpoint(
        self,
        workflow_id: str,
        *,
        safe_reason: str,
        step_states: list[WorkflowStepState] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> WorkflowCheckpoint:
        with self.mission_store.locked():
            record = self.load(workflow_id)
            paths = self._find_paths(workflow_id)
            branch = next(branch for branch in record.branches if branch.branch_id == record.current_branch_id)
            return self._create_checkpoint_locked(
                record=record,
                paths=paths,
                branch=branch,
                safe_reason=safe_reason,
                step_states=list(step_states or []),
                receipt_refs=receipt_refs,
                finalgate_certificate_refs=finalgate_certificate_refs,
                memory_feedback_refs=memory_feedback_refs,
            )

    def reserve_actions(
        self,
        workflow_id: str,
        *,
        action_count: int,
        estimated_cost_usd: float = 0.0,
    ) -> DurableWorkflowRecord:
        if action_count < 1:
            raise ValueError("action reservation must be positive")
        if estimated_cost_usd < 0:
            raise ValueError("cost reservation cannot be negative")
        with self.mission_store.locked():
            record = self.load(workflow_id)
            if record.completed_action_count + record.reserved_action_count + action_count > record.snapshot.max_actions:
                raise ValueError("action budget exhausted")
            if record.cost_used_usd + record.reserved_cost_usd + estimated_cost_usd > record.snapshot.max_cost_usd:
                raise ValueError("cost budget exhausted")
            updated = record.model_copy(
                update={
                    "reserved_action_count": record.reserved_action_count + action_count,
                    "reserved_cost_usd": record.reserved_cost_usd + estimated_cost_usd,
                    "record_version": record.record_version + 1,
                    "updated_at": datetime.now(UTC),
                }
            ).with_hash()
            self._write_record(self._find_paths(workflow_id), updated)
            return updated

    def commit_step_result(
        self,
        workflow_id: str,
        *,
        step_result: PowerStepResult,
        reserved_actions: int,
        reserved_cost_usd: float,
        safe_reason: str,
    ) -> WorkflowCheckpoint:
        with self.mission_store.locked():
            record = self.load(workflow_id)
            if reserved_actions < 1 or record.reserved_action_count < reserved_actions:
                raise ValueError("workflow action reservation missing")
            if reserved_cost_usd < 0 or record.reserved_cost_usd < reserved_cost_usd:
                raise ValueError("workflow cost reservation missing")
            paths = self._find_paths(workflow_id)
            branch = next(branch for branch in record.branches if branch.branch_id == record.current_branch_id)
            if branch.execution_target is not ReplanExecutionTarget.POWER_RUNTIME:
                raise ValueError("workflow step proof requires PowerRuntime branch")
            plan = self.load_plan(workflow_id, branch.plan_hash)
            step = next((item for item in plan.graph.steps if item.step_id == step_result.step_id), None)
            if step is None:
                raise ValueError("workflow step proof does not match current plan")
            sanitized_result = step_result.model_copy(
                update={
                    "receipt_refs": sanitize_operator_refs(step_result.receipt_refs),
                    "finalgate_certificate_refs": sanitize_operator_refs(step_result.finalgate_certificate_refs),
                    "memory_feedback_refs": sanitize_operator_refs(step_result.memory_feedback_refs),
                    "blocked_reason": redact_operator_text(step_result.blocked_reason or "") or None,
                    "safe_summary": redact_operator_text(step_result.safe_summary),
                }
            )
            result_hash = stable_hash(sanitized_result.model_dump(mode="json"))
            proof = WorkflowStepProof(
                workflow_id=workflow_id,
                mission_id=record.mission_id,
                branch_id=branch.branch_id,
                plan_hash=branch.plan_hash,
                step_id=step.step_id,
                step_contract_hash=step_contract_hash_from_step(step),
                status=sanitized_result.status,
                attempt_count=sanitized_result.attempt_count,
                receipt_refs=sanitized_result.receipt_refs,
                finalgate_certificate_refs=sanitized_result.finalgate_certificate_refs,
                memory_feedback_refs=sanitized_result.memory_feedback_refs,
                blocked_reason=sanitized_result.blocked_reason,
                safe_summary=sanitized_result.safe_summary,
                result_hash=result_hash,
            ).with_hash()
            self.mission_store.atomic_write_json(
                paths.proofs / f"{proof.proof_id}.json",
                proof.model_dump(mode="json"),
            )
            state = WorkflowStepState(
                step_id=proof.step_id,
                status=proof.status,
                attempt_count=proof.attempt_count,
                proof_id=proof.proof_id,
                receipt_refs=proof.receipt_refs,
                finalgate_certificate_refs=proof.finalgate_certificate_refs,
                memory_feedback_refs=proof.memory_feedback_refs,
                blocked_reason=proof.blocked_reason,
                safe_summary=proof.safe_summary,
                result_hash=proof.result_hash,
            )
            previous_states = (
                self.load_checkpoint(workflow_id, record.latest_checkpoint_id).step_states
                if record.latest_checkpoint_id
                else []
            )
            states = [item for item in previous_states if item.step_id != state.step_id] + [state]
            actual_attempts = min(max(sanitized_result.attempt_count, 0), reserved_actions)
            return self._create_checkpoint_locked(
                record=record,
                paths=paths,
                branch=branch,
                safe_reason=safe_reason,
                step_states=states,
                record_updates={
                    "reserved_action_count": record.reserved_action_count - reserved_actions,
                    "completed_action_count": record.completed_action_count + actual_attempts,
                    "reserved_cost_usd": record.reserved_cost_usd - reserved_cost_usd,
                    "cost_used_usd": record.cost_used_usd + reserved_cost_usd,
                },
            )

    def transition_to_power_branch(
        self,
        workflow_id: str,
        *,
        plan: PowerMissionPlan,
        branch: WorkflowBranch,
        branches: list[WorkflowBranch],
        safe_reason: str,
        record_updates: dict,
    ) -> WorkflowCheckpoint:
        with self.mission_store.locked():
            record = self.load(workflow_id)
            paths = self._find_paths(workflow_id)
            plan_hash = self._write_plan(paths, plan)
            if plan_hash != branch.plan_hash:
                raise ValueError("replan branch plan hash mismatch")
            return self._create_checkpoint_locked(
                record=record,
                paths=paths,
                branch=branch,
                safe_reason=safe_reason,
                step_states=[],
                record_updates={
                    **record_updates,
                    "branches": branches,
                    "current_branch_id": branch.branch_id,
                },
            )

    def load_checkpoint(self, workflow_id: str, checkpoint_id: str) -> WorkflowCheckpoint:
        paths = self._find_paths(workflow_id)
        path = paths.checkpoints / f"{_safe_id(checkpoint_id)}.json"
        return WorkflowCheckpoint.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def load_proof(self, workflow_id: str, proof_id: str) -> WorkflowStepProof:
        paths = self._find_paths(workflow_id)
        path = paths.proofs / f"{_safe_id(proof_id)}.json"
        return WorkflowStepProof.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_checkpoints(self, workflow_id: str) -> list[WorkflowCheckpoint]:
        paths = self._find_paths(workflow_id)
        if not paths.checkpoints.exists():
            return []
        checkpoints = [
            WorkflowCheckpoint.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(paths.checkpoints.glob("*.json"), key=lambda item: item.name)
        ]
        return sorted(
            checkpoints,
            key=lambda checkpoint: (checkpoint.record_version, checkpoint.created_at, checkpoint.checkpoint_id),
        )

    def update_record(
        self,
        record: DurableWorkflowRecord,
        *,
        expected_version: int,
    ) -> DurableWorkflowRecord:
        with self.mission_store.locked():
            current = self.load(record.workflow_id)
            if current.record_version != expected_version:
                raise ValueError("stale workflow record version")
            current_payload = current.model_dump(mode="json")
            proposed_payload = record.model_dump(mode="json")
            for field in ("status", "updated_at", "record_version", "record_hash"):
                current_payload.pop(field, None)
                proposed_payload.pop(field, None)
            if proposed_payload != current_payload:
                if record.snapshot != current.snapshot:
                    raise ValueError("workflow authority snapshot immutable")
                raise ValueError("workflow record update may change status only")
            terminal = {
                WorkflowStatus.BLOCKED,
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.KILLED,
            }
            if current.status in terminal and record.status is not current.status:
                raise ValueError("terminal workflow status is immutable")
            updated = record.model_copy(
                update={"record_version": expected_version + 1, "updated_at": datetime.now(UTC)}
            ).with_hash()
            self._write_record(self._find_paths(record.workflow_id), updated)
            return updated

    def verify(self, workflow_id: str) -> bool:
        try:
            record = self.load(workflow_id)
            if not record.verify_hash():
                return False
            branches = {branch.branch_id: branch for branch in record.branches}
            current_branch = branches.get(record.current_branch_id)
            if current_branch is None or record.latest_checkpoint_id is None:
                return False
            latest = self.load_checkpoint(workflow_id, record.latest_checkpoint_id)
            if latest.branch_id != current_branch.branch_id or latest.plan_hash != current_branch.plan_hash:
                return False
            for branch in record.branches:
                if branch.execution_target is ReplanExecutionTarget.POWER_RUNTIME:
                    self.load_plan(workflow_id, branch.plan_hash)
            for checkpoint in self.list_checkpoints(workflow_id):
                if not checkpoint.verify_hash() or not checkpoint.resume_cursor.verify_hash():
                    return False
                if checkpoint.workflow_id != record.workflow_id or checkpoint.mission_id != record.mission_id:
                    return False
                if checkpoint.authority_fingerprint != record.snapshot.authority_fingerprint:
                    return False
                branch = branches.get(checkpoint.branch_id)
                if branch is None or checkpoint.plan_hash != branch.plan_hash:
                    return False
                if checkpoint.record_version > record.record_version:
                    return False
                prepared_event = next(
                    (
                        event
                        for event in self.mission_store.load_events(record.mission_id)
                        if event.event_hash == checkpoint.prepared_event_hash
                    ),
                    None,
                )
                if (
                    prepared_event is None
                    or prepared_event.event_type != "workflow_checkpoint_prepared"
                    or prepared_event.metadata.get("checkpoint_id") != checkpoint.checkpoint_id
                    or prepared_event.metadata.get("workflow_id") != checkpoint.workflow_id
                ):
                    return False
                self._validate_step_states(record, branch, checkpoint.step_states)
            return self.mission_store.verify_record(record.mission_id) and self.mission_store.verify_timeline(
                record.mission_id
            )
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False

    def _create_checkpoint_locked(
        self,
        *,
        record: DurableWorkflowRecord,
        paths: _WorkflowPaths,
        branch: WorkflowBranch,
        safe_reason: str,
        step_states: list[WorkflowStepState],
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
        record_updates: dict | None = None,
    ) -> WorkflowCheckpoint:
        plan = (
            self.load_plan(record.workflow_id, branch.plan_hash)
            if branch.execution_target is ReplanExecutionTarget.POWER_RUNTIME
            else None
        )
        self._validate_step_states(record, branch, step_states)
        completed = [state.step_id for state in step_states if state.status is PowerStepStatus.SUCCEEDED]
        pending = (
            [step.step_id for step in plan.graph.steps if step.step_id not in set(completed)]
            if plan is not None
            else []
        )
        checkpoint_id = new_id("workflow_checkpoint")
        cursor = ResumeCursor(
            workflow_id=record.workflow_id,
            branch_id=branch.branch_id,
            plan_hash=branch.plan_hash,
            checkpoint_id=checkpoint_id,
            completed_step_ids=completed,
            pending_step_ids=pending,
            authority_fingerprint=record.snapshot.authority_fingerprint,
        ).with_hash()
        prepared_event = self.mission_store.append_event(
            record.mission_id,
            event_type="workflow_checkpoint_prepared",
            safe_summary="Workflow checkpoint prepared for durable publication.",
            receipt_refs=_dedupe(
                [
                    *(ref for state in step_states for ref in state.receipt_refs),
                    *sanitize_operator_refs(receipt_refs or []),
                ]
            ),
            finalgate_certificate_refs=_dedupe(
                [
                    *(ref for state in step_states for ref in state.finalgate_certificate_refs),
                    *sanitize_operator_refs(finalgate_certificate_refs or []),
                ]
            ),
            memory_feedback_refs=_dedupe(
                [
                    *(ref for state in step_states for ref in state.memory_feedback_refs),
                    *sanitize_operator_refs(memory_feedback_refs or []),
                ]
            ),
            metadata={
                "workflow_id": record.workflow_id,
                "checkpoint_id": checkpoint_id,
                "branch_id": branch.branch_id,
                "plan_hash": branch.plan_hash,
            },
        )
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=record.workflow_id,
            mission_id=record.mission_id,
            branch_id=branch.branch_id,
            plan_hash=branch.plan_hash,
            authority_fingerprint=record.snapshot.authority_fingerprint,
            record_version=record.record_version + 1,
            safe_reason=redact_operator_text(safe_reason),
            step_states=step_states,
            resume_cursor=cursor,
            receipt_refs=_dedupe(
                [
                    *(ref for state in step_states for ref in state.receipt_refs),
                    *sanitize_operator_refs(receipt_refs or []),
                ]
            ),
            finalgate_certificate_refs=_dedupe(
                [
                    *(ref for state in step_states for ref in state.finalgate_certificate_refs),
                    *sanitize_operator_refs(finalgate_certificate_refs or []),
                ]
            ),
            memory_feedback_refs=_dedupe(
                [
                    *(ref for state in step_states for ref in state.memory_feedback_refs),
                    *sanitize_operator_refs(memory_feedback_refs or []),
                ]
            ),
            prepared_event_hash=prepared_event.event_hash,
        ).with_hash()
        self.mission_store.atomic_write_json(
            paths.checkpoints / f"{checkpoint.checkpoint_id}.json",
            checkpoint.model_dump(mode="json"),
        )
        updated = record.model_copy(
            update={
                **(record_updates or {}),
                "latest_checkpoint_id": checkpoint.checkpoint_id,
                "record_version": record.record_version + 1,
                "updated_at": datetime.now(UTC),
            }
        ).with_hash()
        self._write_record(paths, updated)
        telemetry_sink = getattr(self.mission_store, "telemetry_sink", None)
        if telemetry_sink is not None and hasattr(telemetry_sink, "record_workflow_checkpoint"):
            telemetry_sink.record_workflow_checkpoint(checkpoint)
        return checkpoint

    def _validate_step_states(
        self,
        record: DurableWorkflowRecord,
        branch: WorkflowBranch,
        states: list[WorkflowStepState],
    ) -> None:
        if not states:
            return
        if branch.execution_target is not ReplanExecutionTarget.POWER_RUNTIME:
            raise ValueError("durable step proof requires PowerRuntime branch")
        plan = self.load_plan(record.workflow_id, branch.plan_hash)
        steps = {step.step_id: step for step in plan.graph.steps}
        for state in states:
            if not state.proof_id or not state.result_hash:
                raise ValueError("durable step proof required")
            step = steps.get(state.step_id)
            if step is None:
                raise ValueError("durable step proof step not in current plan")
            try:
                proof = self.load_proof(record.workflow_id, state.proof_id)
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                raise ValueError("durable step proof missing or malformed") from exc
            if not proof.verify_hash():
                raise ValueError("durable step proof hash mismatch")
            expected = {
                "workflow_id": record.workflow_id,
                "mission_id": record.mission_id,
                "branch_id": branch.branch_id,
                "plan_hash": branch.plan_hash,
                "step_id": state.step_id,
                "step_contract_hash": step_contract_hash_from_step(step),
                "status": state.status,
                "attempt_count": state.attempt_count,
                "receipt_refs": state.receipt_refs,
                "finalgate_certificate_refs": state.finalgate_certificate_refs,
                "memory_feedback_refs": state.memory_feedback_refs,
                "blocked_reason": state.blocked_reason,
                "safe_summary": state.safe_summary,
                "result_hash": state.result_hash,
            }
            actual = {key: getattr(proof, key) for key in expected}
            if actual != expected:
                raise ValueError("durable step proof binding mismatch")

    def _write_plan(self, paths: _WorkflowPaths, plan: PowerMissionPlan) -> str:
        assert_workflow_plan_persistable(plan)
        plan_hash = stable_hash(plan.model_dump(mode="json"))
        self.mission_store.atomic_write_json(paths.plans / f"{plan_hash}.json", plan.model_dump(mode="json"))
        return plan_hash

    def _write_record(self, paths: _WorkflowPaths, record: DurableWorkflowRecord) -> None:
        self.mission_store.atomic_write_json(paths.record, record.model_dump(mode="json"))

    def _find_paths(self, workflow_id: str) -> _WorkflowPaths:
        _safe_id(workflow_id)
        for mission in self.mission_store.list_records():
            paths = self._paths_for_mission(mission.mission_id)
            if not paths.record.exists():
                continue
            try:
                payload = json.loads(paths.record.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("workflow_id") == workflow_id:
                return paths
        raise FileNotFoundError(f"workflow not found: {workflow_id}")

    def _paths_for_mission(self, mission_id: str) -> _WorkflowPaths:
        root = self.mission_store.mission_dir(mission_id, create=True) / "workflow"
        root.mkdir(parents=True, exist_ok=True)
        return _WorkflowPaths(
            root=root,
            record=root / "record.json",
            plans=root / "plans",
            checkpoints=root / "checkpoints",
            proofs=root / "proofs",
        )


class _WorkflowPaths:
    def __init__(self, *, root: Path, record: Path, plans: Path, checkpoints: Path, proofs: Path) -> None:
        self.root = root
        self.record = record
        self.plans = plans
        self.checkpoints = checkpoints
        self.proofs = proofs
        self.plans.mkdir(parents=True, exist_ok=True)
        self.checkpoints.mkdir(parents=True, exist_ok=True)
        self.proofs.mkdir(parents=True, exist_ok=True)


def _safe_id(value: str) -> str:
    if not value or any(separator in value for separator in ("/", "\\")) or ".." in value:
        raise ValueError("invalid workflow identifier")
    return value


def _dedupe(values) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))
