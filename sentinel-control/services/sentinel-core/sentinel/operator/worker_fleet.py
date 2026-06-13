from __future__ import annotations

import json
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.worker_models import (
    ChildAuthorityEnvelope,
    WorkerBudget,
    WorkerDeadline,
    WorkerEvidencePacket,
    WorkerExecutionContext,
    WorkerExecutionMode,
    WorkerFleetConfig,
    WorkerFleetRun,
    WorkerFleetRunStatus,
    WorkerMergeDecision,
    WorkerMergeOutcome,
    WorkerResult,
    WorkerResultContract,
    WorkerScope,
    WorkerSpawnRequest,
    WorkerTask,
    WorkerTaskStatus,
    WorkerConflictRecord,
)
from sentinel.telemetry import TelemetryMetricKind, TelemetrySnapshot


WorkerExecutor = Callable[[WorkerExecutionContext], WorkerResult]


class WorkerFleetRuntimeError(ValueError):
    pass


class WorkerFleetRuntime:
    def __init__(
        self,
        kernel: MissionKernel,
        *,
        config: WorkerFleetConfig | None = None,
        telemetry_sink: object | None = None,
        workflow_store: object | None = None,
        memory_adapter: object | None = None,
    ) -> None:
        self._kernel = kernel
        self._config = config or WorkerFleetConfig()
        self._telemetry_sink = telemetry_sink or getattr(kernel, "telemetry_sink", None)
        self._workflow_store = workflow_store
        self._memory_adapter = memory_adapter

    def run(
        self,
        *,
        mission_id: str,
        parent_envelope: MissionAuthorityEnvelope,
        spawn_request: WorkerSpawnRequest,
        worker_executor: WorkerExecutor,
        cancellation_token: Any | None = None,
    ) -> WorkerFleetRun:
        self._assert_supported_mission(mission_id)
        if spawn_request.mission_id != mission_id:
            raise WorkerFleetRuntimeError("worker spawn request mission mismatch")
        if spawn_request.config.require_certified_telemetry and not self._certified_mode():
            return self._blocked_run(
                mission_id,
                spawn_request=spawn_request,
                reason="telemetry_certified_mode_required",
            )
        self._emit_worker_spawn_requested(mission_id, spawn_request)
        run = WorkerFleetRun(
            mission_id=mission_id,
            spawn_request_id=spawn_request.request_id,
            status=WorkerFleetRunStatus.CREATED,
        )
        try:
            task_graph = list(spawn_request.tasks)
            if not task_graph:
                return self._finalize_run(self._blocked_run(mission_id, spawn_request=spawn_request, reason="worker_task_graph_empty"))
            self._kernel.store.append_event(
                mission_id,
                event_type="worker_spawn_requested",
                safe_summary="Worker fleet spawn requested.",
                metadata={
                    "worker_fleet_run_id": run.worker_fleet_run_id,
                    "task_count": len(task_graph),
                    "safe_reason": spawn_request.safe_reason,
                },
            )
            self._emit_worker_metric(mission_id, TelemetryMetricKind.WORKER_PARALLEL_EFFICIENCY, 0.0, "Worker fleet spawn requested.", {"task_count": len(task_graph)})
            results_by_task: dict[str, WorkerResult] = {}
            tasks_by_id = {task.task_id: task for task in task_graph}
            decisions_by_task: dict[str, WorkerMergeDecision] = {}
            conflict_records: list[WorkerConflictRecord] = []
            started_tasks: set[str] = set()
            completed_tasks: set[str] = set()
            pending_tasks = {task.task_id: task for task in task_graph}
            futures: dict[Future[WorkerResult], WorkerExecutionContext] = {}
            with ThreadPoolExecutor(max_workers=min(self._config.max_workers, max(1, len(task_graph)))) as pool:
                while pending_tasks or futures:
                    if cancellation_token is not None and getattr(cancellation_token, "is_cancelled", lambda: False)():
                        self._append_worker_event(
                            mission_id,
                            event_type="worker_killed",
                            safe_summary="Worker fleet killed by cancellation token.",
                            run_id=run.worker_fleet_run_id,
                        )
                        run.status = WorkerFleetRunStatus.KILLED
                        run.blocked_reason = "worker_killed"
                        self._stop_outstanding_futures(
                            mission_id=mission_id,
                            run_id=run.worker_fleet_run_id,
                            futures=futures,
                            reason="worker_killed",
                        )
                        break
                    ready_tasks = [
                        task
                        for task in pending_tasks.values()
                        if set(task.depends_on).issubset(completed_tasks)
                    ]
                    for task in ready_tasks:
                        child = self._derive_child_authority(
                            mission_id=mission_id,
                            parent_envelope=parent_envelope,
                            spawn_request=spawn_request,
                            task=task,
                            run_id=run.worker_fleet_run_id,
                        )
                        if child is None:
                            self._append_worker_event(
                                mission_id,
                                event_type="worker_authority_rejected",
                                safe_summary=f"Worker authority rejected for {task.task_id}.",
                                run_id=run.worker_fleet_run_id,
                                task_id=task.task_id,
                            )
                            run.status = WorkerFleetRunStatus.BLOCKED
                            run.blocked_reason = "worker_authority_derivation_failed"
                            pending_tasks = {}
                            self._stop_outstanding_futures(
                                mission_id=mission_id,
                                run_id=run.worker_fleet_run_id,
                                futures=futures,
                                reason="worker_authority_derivation_failed",
                            )
                            break
                        context = WorkerExecutionContext(
                            worker_id=f"{run.worker_fleet_run_id}:{task.task_id}",
                            task_id=task.task_id,
                            mission_id=mission_id,
                            parent_envelope_id=parent_envelope.id,
                            role=task.role,
                            execution_mode=task.execution_mode,
                            child_authority=child,
                            scope=task.scope,
                            budget=task.budget,
                            deadline=task.deadline,
                            result_contract=task.result_contract,
                            memory_context_refs=list(task.metadata.get("memory_context_refs", [])),
                            telemetry_snapshot_hash=stable_hash(self._telemetry_snapshot()),
                        )
                        run.workers.append(context)
                        run.child_authority_envelopes.append(child)
                        started_tasks.add(task.task_id)
                        pending_tasks.pop(task.task_id, None)
                        self._emit_worker_started(mission_id, run.worker_fleet_run_id, context)
                        futures[pool.submit(worker_executor, context)] = context
                    if run.status in {WorkerFleetRunStatus.BLOCKED, WorkerFleetRunStatus.KILLED}:
                        break
                    if not futures:
                        break
                    done, _ = wait(list(futures.keys()), return_when=FIRST_COMPLETED)
                    for future in done:
                        context = futures.pop(future)
                        try:
                            result = future.result()
                        except Exception as exc:  # noqa: BLE001
                            run.status = WorkerFleetRunStatus.FAILED
                            run.blocked_reason = f"worker_failed:{exc.__class__.__name__}"
                            self._append_worker_event(
                                mission_id,
                                event_type="worker_failed",
                                safe_summary=f"Worker {context.task_id} failed: {exc.__class__.__name__}.",
                                run_id=run.worker_fleet_run_id,
                                worker_id=context.worker_id,
                                task_id=context.task_id,
                            )
                            self._emit_worker_event(
                                mission_id,
                                event_type="worker_failed",
                                safe_summary=f"Worker {context.task_id} failed: {exc.__class__.__name__}.",
                                run_id=run.worker_fleet_run_id,
                                worker_id=context.worker_id,
                                task_id=context.task_id,
                            )
                            pending_tasks.clear()
                            self._stop_outstanding_futures(
                                mission_id=mission_id,
                                run_id=run.worker_fleet_run_id,
                                futures=futures,
                                reason="worker_failed",
                            )
                            break
                        normalized, validation_reasons = self._validate_worker_result(context, result)
                        if normalized is None:
                            rejected_result = result.with_hash()
                            reasons = validation_reasons or ["worker_result_contract_rejected"]
                            decision = WorkerMergeDecision(
                                worker_id=rejected_result.worker_id,
                                task_id=rejected_result.task_id,
                                outcome=WorkerMergeOutcome.REJECTED,
                                reasons=reasons,
                                result_hash=rejected_result.result_hash,
                                receipt_refs=rejected_result.evidence_packet.receipt_refs,
                                finalgate_certificate_refs=rejected_result.evidence_packet.finalgate_certificate_refs,
                                memory_feedback_refs=rejected_result.evidence_packet.memory_feedback_refs,
                            )
                            decisions_by_task[context.task_id] = decision
                            run.merge_decisions.append(decision)
                            self._emit_worker_result_rejected(mission_id, run.worker_fleet_run_id, rejected_result, reasons=reasons)
                            run.status = WorkerFleetRunStatus.BLOCKED
                            run.blocked_reason = "worker_result_contract_rejected"
                            pending_tasks.clear()
                            self._stop_outstanding_futures(
                                mission_id=mission_id,
                                run_id=run.worker_fleet_run_id,
                                futures=futures,
                                reason="worker_result_contract_rejected",
                            )
                            break
                        run.worker_results.append(normalized)
                        self._emit_worker_completed(mission_id, run.worker_fleet_run_id, normalized)
                        self._emit_worker_result_submitted(mission_id, run.worker_fleet_run_id, normalized)
                        completed_tasks.add(context.task_id)
                        decision = self._merge_worker_result(
                            mission_id=mission_id,
                            run=run,
                            task=context.task_id,
                            result=normalized,
                            task_def=tasks_by_id[context.task_id],
                            tasks_by_id=tasks_by_id,
                            conflict_records=conflict_records,
                            decisions_by_task=decisions_by_task,
                            results_by_task=results_by_task,
                        )
                        decisions_by_task[context.task_id] = decision
                        run.merge_decisions.append(decision)
                        results_by_task[context.task_id] = normalized
                        if decision.outcome is WorkerMergeOutcome.CONFLICT:
                            run.status = WorkerFleetRunStatus.BLOCKED
                            run.blocked_reason = "worker_conflict_detected"
                            pending_tasks.clear()
                            self._stop_outstanding_futures(
                                mission_id=mission_id,
                                run_id=run.worker_fleet_run_id,
                                futures=futures,
                                reason="worker_conflict_detected",
                            )
                            break
                        if decision.outcome is WorkerMergeOutcome.REJECTED:
                            run.status = WorkerFleetRunStatus.BLOCKED
                            run.blocked_reason = "worker_result_rejected"
                            pending_tasks.clear()
                            self._stop_outstanding_futures(
                                mission_id=mission_id,
                                run_id=run.worker_fleet_run_id,
                                futures=futures,
                                reason="worker_result_rejected",
                            )
                            break
                        if decision.outcome is WorkerMergeOutcome.NEEDS_RETRY:
                            run.status = WorkerFleetRunStatus.BLOCKED
                            run.blocked_reason = "worker_retry_required"
                            pending_tasks.clear()
                            self._stop_outstanding_futures(
                                mission_id=mission_id,
                                run_id=run.worker_fleet_run_id,
                                futures=futures,
                                reason="worker_retry_required",
                            )
                            break
                    if run.status in {WorkerFleetRunStatus.BLOCKED, WorkerFleetRunStatus.FAILED, WorkerFleetRunStatus.KILLED}:
                        break
            if run.status == WorkerFleetRunStatus.CREATED and pending_tasks == {} and not futures:
                run.status = WorkerFleetRunStatus.COMPLETED
            if run.status is WorkerFleetRunStatus.CREATED:
                run.status = WorkerFleetRunStatus.COMPLETED if len(run.worker_results) == len(task_graph) else WorkerFleetRunStatus.BLOCKED
                if run.status is WorkerFleetRunStatus.BLOCKED and run.blocked_reason is None:
                    run.blocked_reason = "worker_incomplete"
            run.conflict_records = conflict_records
            try:
                self._record_workflow_checkpoint(mission_id, spawn_request, run)
            except Exception as exc:  # noqa: BLE001
                run.status = WorkerFleetRunStatus.BLOCKED
                run.blocked_reason = "worker_workflow_checkpoint_failed"
                self._kernel.store.append_event(
                    mission_id,
                    event_type="worker_workflow_checkpoint_failed",
                    safe_summary=f"Worker workflow checkpoint failed: {exc.__class__.__name__}.",
                    metadata={
                        "worker_fleet_run_id": run.worker_fleet_run_id,
                        "workflow_id_hash": stable_hash(str(spawn_request.metadata.get("workflow_id", ""))),
                    },
                )
            run.updated_at = datetime.now(UTC)
            run = run.with_hash()
            self._persist_run(run)
            self._emit_run_metrics(mission_id, run, len(task_graph))
            self._kernel.store.append_event(
                mission_id,
                event_type=f"worker_fleet_{run.status.value}",
                safe_summary=f"Worker fleet run finished with status {run.status.value}.",
                metadata={
                    "worker_fleet_run_id": run.worker_fleet_run_id,
                    "spawn_request_id": run.spawn_request_id,
                    "blocked_reason": run.blocked_reason,
                    "worker_count": len(run.worker_results),
                },
                receipt_refs=_dedupe(ref for result in run.worker_results for ref in result.evidence_packet.receipt_refs),
                finalgate_certificate_refs=_dedupe(
                    ref for result in run.worker_results for ref in result.evidence_packet.finalgate_certificate_refs
                ),
                memory_feedback_refs=_dedupe(
                    ref for result in run.worker_results for ref in result.evidence_packet.memory_feedback_refs
                ),
            )
            return run
        finally:
            self._persist_run(run)

    def load_run(self, mission_id: str, worker_fleet_run_id: str) -> WorkerFleetRun:
        path = self._worker_fleet_path(mission_id, worker_fleet_run_id)
        return WorkerFleetRun.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_runs(self, mission_id: str) -> list[WorkerFleetRun]:
        root = self._worker_fleet_root(mission_id)
        if not root.exists():
            return []
        runs: list[WorkerFleetRun] = []
        for path in sorted(root.glob("*.json"), key=lambda item: item.name):
            runs.append(WorkerFleetRun.model_validate(__import__("json").loads(path.read_text(encoding="utf-8"))))
        return runs

    def _telemetry_snapshot(self) -> dict[str, Any]:
        sink = self._telemetry_sink
        if sink is None or not hasattr(sink, "certified_mode_status"):
            return {"certified_mode": False, "reasons": ["telemetry_unavailable"]}
        snapshot: TelemetrySnapshot = sink.certified_mode_status()
        return snapshot.model_dump(mode="json") if hasattr(snapshot, "model_dump") else dict(snapshot)

    def _certified_mode(self) -> bool:
        sink = self._telemetry_sink
        if sink is None or not hasattr(sink, "certified_mode_status"):
            return False
        snapshot = sink.certified_mode_status()
        return bool(getattr(snapshot, "certified_mode", False))

    def _assert_supported_mission(self, mission_id: str) -> None:
        if not self._kernel.store.verify_record(mission_id):
            raise WorkerFleetRuntimeError("mission record must verify before worker fleet can run")

    def _derive_child_authority(
        self,
        *,
        mission_id: str,
        parent_envelope: MissionAuthorityEnvelope,
        spawn_request: WorkerSpawnRequest,
        task: WorkerTask,
        run_id: str,
    ) -> ChildAuthorityEnvelope | None:
        scope = task.scope
        if not _scope_subset(scope.allowed_actions, parent_envelope.allowed_actions):
            return None
        if not _scope_subset(scope.allowed_tools, parent_envelope.allowed_tools):
            return None
        if not _scope_subset(scope.allowed_systems, parent_envelope.allowed_systems):
            return None
        if not _scope_subset(scope.allowed_paths, parent_envelope.allowed_paths):
            return None
        if not _scope_subset(scope.allowed_domains, parent_envelope.allowed_domains):
            return None
        if scope.provider_id is not None or scope.backend_id is not None or scope.model_id is not None:
            return None
        if scope.allow_worker_spawning:
            return None
        if task.execution_mode is WorkerExecutionMode.POWER_RUNTIME and not scope.allow_power_runtime:
            return None
        if task.execution_mode is WorkerExecutionMode.AGENT_RUNTIME and not scope.allow_agentruntime:
            return None
        child = ChildAuthorityEnvelope(
            parent_envelope_id=parent_envelope.id,
            mission_id=mission_id,
            worker_id=f"{run_id}:{task.task_id}",
            task_id=task.task_id,
            allowed_actions=_intersection(scope.allowed_actions, parent_envelope.allowed_actions),
            allowed_tools=_intersection(scope.allowed_tools, parent_envelope.allowed_tools),
            allowed_systems=_intersection(scope.allowed_systems, parent_envelope.allowed_systems),
            allowed_paths=_intersection(scope.allowed_paths, parent_envelope.allowed_paths),
            allowed_domains=_intersection(scope.allowed_domains, parent_envelope.allowed_domains),
            allowed_data_types=_intersection(scope.allowed_data_types, parent_envelope.allowed_data_types),
            credential_scope_hashes=_intersection(scope.credential_scope_hashes, _credential_scope_hashes(parent_envelope)),
            max_actions=min(task.budget.max_actions, parent_envelope.max_actions),
            max_cost_usd=min(task.budget.max_cost_usd, parent_envelope.max_cost_usd),
            timeout_seconds=min(task.deadline.timeout_seconds, parent_envelope.max_duration_minutes * 60),
            risk_appetite_score=min(parent_envelope.risk_appetite_score, 100.0),
            provider_id=None,
            backend_id=None,
            model_id=None,
            allow_power_runtime=bool(scope.allow_power_runtime and task.execution_mode is WorkerExecutionMode.POWER_RUNTIME),
            allow_agentruntime=bool(scope.allow_agentruntime and task.execution_mode is WorkerExecutionMode.AGENT_RUNTIME),
            allow_worker_spawning=False,
            strict_subset=_is_strict_subset(parent_envelope, scope, task),
        ).with_hash()
        if not child.verify_hash():
            return None
        self._emit_worker_authority_derived(mission_id, run_id, child)
        return child

    def _validate_worker_result(self, context: WorkerExecutionContext, result: WorkerResult) -> tuple[WorkerResult | None, list[str]]:
        if result.worker_id != context.worker_id or result.task_id != context.task_id:
            return None, ["worker_result_identity_mismatch"]
        if result.result_contract_id != context.result_contract.contract_id:
            return None, ["worker_result_contract_mismatch"]
        if result.status not in {
            WorkerTaskStatus.COMPLETED,
            WorkerTaskStatus.FAILED,
            WorkerTaskStatus.BLOCKED,
            WorkerTaskStatus.KILLED,
            WorkerTaskStatus.TIMEOUT,
            WorkerTaskStatus.BUDGET_EXHAUSTED,
        }:
            return None, ["worker_result_status_invalid"]
        if result.actions_used > context.budget.max_actions or result.cost_usd > context.budget.max_cost_usd:
            self._emit_worker_event(
                context.mission_id,
                run_id=context.child_authority.child_authority_id,
                event_type="worker_budget_exhausted",
                safe_summary=f"Worker {context.task_id} exceeded budget.",
                worker_id=context.worker_id,
                task_id=context.task_id,
            )
            return None, ["worker_budget_exhausted"]
        duration_seconds = max(0.0, (result.completed_at - result.started_at).total_seconds())
        if duration_seconds > context.deadline.timeout_seconds:
            self._emit_worker_event(
                context.mission_id,
                run_id=context.child_authority.child_authority_id,
                event_type="worker_timeout",
                safe_summary=f"Worker {context.task_id} exceeded deadline.",
                worker_id=context.worker_id,
                task_id=context.task_id,
            )
            return None, ["worker_timeout"]
        evidence_packet = result.evidence_packet
        if len(evidence_packet.evidence_refs) < context.result_contract.required_evidence_refs:
            return None, ["missing_required_evidence"]
        if context.result_contract.require_receipt_refs_for_execution and not evidence_packet.receipt_refs:
            return None, ["missing_required_receipt_refs"]
        if context.result_contract.require_finalgate_refs_for_execution and not evidence_packet.finalgate_certificate_refs:
            return None, ["missing_required_finalgate_refs"]
        return result.with_hash(), []

    def _merge_worker_result(
        self,
        *,
        mission_id: str,
        run: WorkerFleetRun,
        task: str,
        result: WorkerResult,
        task_def: WorkerTask,
        tasks_by_id: dict[str, WorkerTask],
        conflict_records: list[WorkerConflictRecord],
        decisions_by_task: dict[str, WorkerMergeDecision],
        results_by_task: dict[str, WorkerResult],
    ) -> WorkerMergeDecision:
        conflict_key = task_def.result_contract.conflict_key
        if result.evidence_packet.receipt_refs and result.evidence_packet.finalgate_certificate_refs:
            outcome = WorkerMergeOutcome.MERGED
            reasons: list[str] = []
        else:
            outcome = WorkerMergeOutcome.REJECTED
            reasons = ["missing_required_evidence"]
        if outcome is WorkerMergeOutcome.MERGED and conflict_key is not None:
            for prior_task_id, prior in results_by_task.items():
                prior_conflict_key = tasks_by_id[prior_task_id].result_contract.conflict_key
                if prior_conflict_key != conflict_key:
                    continue
                if prior.result_hash != result.result_hash:
                    outcome = WorkerMergeOutcome.CONFLICT
                    reasons = ["conflicting_worker_outputs"]
                    conflict_records.append(
                        WorkerConflictRecord(
                            conflict_key=conflict_key,
                            worker_ids=[prior.worker_id, result.worker_id],
                            result_hashes=[prior.result_hash, result.result_hash],
                            safe_summary="Conflicting worker outputs detected.",
                        )
                    )
                    self._emit_worker_conflict(mission_id, run.worker_fleet_run_id, conflict_key, prior.worker_id, result.worker_id)
                    break
        decision = WorkerMergeDecision(
            worker_id=result.worker_id,
            task_id=task,
            outcome=outcome,
            reasons=reasons,
            result_hash=result.result_hash,
            receipt_refs=result.evidence_packet.receipt_refs,
            finalgate_certificate_refs=result.evidence_packet.finalgate_certificate_refs,
            memory_feedback_refs=result.evidence_packet.memory_feedback_refs,
        )
        results_by_task[task] = result
        if decision.outcome is WorkerMergeOutcome.MERGED:
            self._emit_worker_result_merged(
                mission_id,
                run.worker_fleet_run_id,
                result,
            )
        else:
            self._emit_worker_result_rejected(
                mission_id,
                run.worker_fleet_run_id,
                result,
                reasons=reasons,
            )
        return decision

    def _blocked_run(self, mission_id: str, *, spawn_request: WorkerSpawnRequest, reason: str) -> WorkerFleetRun:
        run = WorkerFleetRun(
            mission_id=mission_id,
            spawn_request_id=spawn_request.request_id,
            status=WorkerFleetRunStatus.BLOCKED,
            blocked_reason=reason,
        )
        self._persist_run(run)
        self._kernel.store.append_event(
            mission_id,
            event_type="worker_spawn_blocked",
            safe_summary="Worker fleet spawn blocked.",
            metadata={"worker_fleet_run_id": run.worker_fleet_run_id, "reason": reason},
        )
        if self._certified_mode():
            self._emit_worker_spawn_blocked(mission_id, run.worker_fleet_run_id, "worker_spawn", "worker_spawn", reason)
        return run

    def _emit_run_metrics(self, mission_id: str, run: WorkerFleetRun, task_count: int) -> None:
        completed_count = sum(1 for result in run.worker_results if result.status is WorkerTaskStatus.COMPLETED)
        conflict_count = len(run.conflict_records)
        merged_count = sum(1 for decision in run.merge_decisions if decision.outcome is WorkerMergeOutcome.MERGED)
        useful_minutes = sum(
            max(0.0, (result.completed_at - result.started_at).total_seconds()) / 60.0
            for result in run.worker_results
        )
        total_cost = sum(result.cost_usd for result in run.worker_results)
        retry_count = sum(1 for decision in run.merge_decisions if decision.outcome is WorkerMergeOutcome.NEEDS_RETRY)
        self._emit_worker_metric(
            mission_id,
            TelemetryMetricKind.WORKER_COMPLETION_RATE,
            1.0 if run.status is WorkerFleetRunStatus.COMPLETED else 0.0,
            "Worker fleet completion rate sample.",
            {"worker_count": len(run.worker_results), "task_count": task_count},
        )
        self._emit_worker_metric(
            mission_id,
            TelemetryMetricKind.WORKER_CONFLICT_RATE,
            0.0 if task_count == 0 else round(conflict_count / task_count, 6),
            "Worker fleet conflict rate sample.",
            {"conflict_count": conflict_count, "task_count": task_count},
        )
        self._emit_worker_metric(
            mission_id,
            TelemetryMetricKind.WORKER_USEFUL_MINUTES,
            round(useful_minutes, 6),
            "Worker fleet useful minutes sample.",
            {"worker_count": len(run.worker_results)},
        )
        self._emit_worker_metric(
            mission_id,
            TelemetryMetricKind.WORKER_COST,
            round(total_cost, 6),
            "Worker fleet cost sample.",
            {"worker_count": len(run.worker_results)},
        )
        self._emit_worker_metric(
            mission_id,
            TelemetryMetricKind.WORKER_RETRY_RATE,
            0.0 if task_count == 0 else round(retry_count / task_count, 6),
            "Worker fleet retry rate sample.",
            {"retry_count": retry_count, "task_count": task_count},
        )
        self._emit_worker_metric(
            mission_id,
            TelemetryMetricKind.WORKER_MERGE_SUCCESS_RATE,
            0.0 if task_count == 0 else round(merged_count / task_count, 6),
            "Worker fleet merge success rate sample.",
            {"merged_count": merged_count, "task_count": task_count},
        )

    def _record_workflow_checkpoint(
        self,
        mission_id: str,
        spawn_request: WorkerSpawnRequest,
        run: WorkerFleetRun,
    ) -> None:
        if self._workflow_store is None:
            return
        workflow_id = spawn_request.metadata.get("workflow_id")
        if not workflow_id:
            return
        checkpoint = self._workflow_store.create_checkpoint(
            str(workflow_id),
            safe_reason=f"Worker fleet run finished with status {run.status.value}.",
            receipt_refs=_dedupe(ref for result in run.worker_results for ref in result.evidence_packet.receipt_refs),
            finalgate_certificate_refs=_dedupe(
                ref for result in run.worker_results for ref in result.evidence_packet.finalgate_certificate_refs
            ),
            memory_feedback_refs=_dedupe(
                ref for result in run.worker_results for ref in result.evidence_packet.memory_feedback_refs
            ),
        )
        self._kernel.store.append_event(
            mission_id,
            event_type="worker_workflow_checkpoint_created",
            safe_summary="Worker fleet checkpoint recorded in durable workflow.",
            metadata={
                "worker_fleet_run_id": run.worker_fleet_run_id,
                "workflow_id_hash": stable_hash(str(workflow_id)),
                "checkpoint_id": checkpoint.checkpoint_id,
            },
            receipt_refs=checkpoint.receipt_refs,
            finalgate_certificate_refs=checkpoint.finalgate_certificate_refs,
            memory_feedback_refs=checkpoint.memory_feedback_refs,
        )

    def _persist_run(self, run: WorkerFleetRun) -> None:
        path = self._worker_fleet_path(run.mission_id, run.worker_fleet_run_id)
        self._kernel.store.atomic_write_json(path, run.safe_model_dump())

    def _stop_outstanding_futures(
        self,
        *,
        mission_id: str,
        run_id: str,
        futures: dict[Future[WorkerResult], WorkerExecutionContext],
        reason: str,
    ) -> None:
        if not futures:
            return
        outstanding = list(futures.items())
        futures.clear()
        running: list[Future[WorkerResult]] = []
        for future, context in outstanding:
            cancelled = future.cancel()
            self._append_worker_event(
                mission_id,
                event_type="worker_killed",
                safe_summary=f"Worker {context.task_id} stopped after fleet terminal state: {reason}.",
                run_id=run_id,
                worker_id=context.worker_id,
                task_id=context.task_id,
            )
            self._emit_worker_event(
                mission_id,
                event_type="worker_killed",
                safe_summary=f"Worker {context.task_id} stopped after fleet terminal state.",
                run_id=run_id,
                worker_id=context.worker_id,
                task_id=context.task_id,
            )
            if not cancelled and not future.done():
                running.append(future)
        if running:
            wait(running)
        for future, context in outstanding:
            if future.cancelled():
                continue
            if future.done():
                try:
                    future.result()
                except Exception as exc:  # noqa: BLE001
                    self._append_worker_event(
                        mission_id,
                        event_type="worker_failed",
                        safe_summary=f"Stopped worker {context.task_id} failed while draining: {exc.__class__.__name__}.",
                        run_id=run_id,
                        worker_id=context.worker_id,
                        task_id=context.task_id,
                    )
                    self._emit_worker_event(
                        mission_id,
                        event_type="worker_failed",
                        safe_summary=f"Stopped worker {context.task_id} failed while draining: {exc.__class__.__name__}.",
                        run_id=run_id,
                        worker_id=context.worker_id,
                        task_id=context.task_id,
                    )

    def _worker_fleet_root(self, mission_id: str) -> Path:
        return self._kernel.store.mission_dir(mission_id, create=True) / "worker_fleet"

    def _worker_fleet_path(self, mission_id: str, worker_fleet_run_id: str) -> Path:
        return self._worker_fleet_root(mission_id) / f"{worker_fleet_run_id}.json"

    def _append_worker_event(self, mission_id: str, *, run_id: str, event_type: str, safe_summary: str, worker_id: str | None = None, task_id: str | None = None) -> None:
        self._kernel.store.append_event(
            mission_id,
            event_type=event_type,
            safe_summary=safe_summary,
            metadata={"worker_fleet_run_id": run_id, "worker_id": worker_id, "task_id": task_id},
        )

    def _emit_worker_event(self, mission_id: str, *, run_id: str, event_type: str, safe_summary: str, worker_id: str | None = None, task_id: str | None = None) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, f"record_{event_type}"):
            getattr(telemetry, f"record_{event_type}")(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=worker_id or "worker",
                task_id=task_id or "task",
                safe_summary=safe_summary,
            )

    def _emit_worker_spawn_requested(self, mission_id: str, spawn_request: WorkerSpawnRequest) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_spawn_requested"):
            telemetry.record_worker_spawn_requested(
                mission_id=mission_id,
                worker_fleet_run_id="pending",
                worker_id="fleet",
                task_id="spawn",
                safe_summary="Worker fleet spawn requested.",
                metadata={"request_id": spawn_request.request_id, "task_count": len(spawn_request.tasks)},
            )

    def _emit_worker_spawn_blocked(self, mission_id: str, run_id: str, worker_id: str, task_id: str, reason: str) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_spawn_blocked"):
            telemetry.record_worker_spawn_blocked(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=worker_id,
                task_id=task_id,
                safe_summary="Worker fleet spawn blocked.",
                metadata={"reason": reason},
            )

    def _emit_worker_authority_derived(self, mission_id: str, run_id: str, child: ChildAuthorityEnvelope) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_authority_derived"):
            telemetry.record_worker_authority_derived(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=child.worker_id,
                task_id=child.task_id,
                safe_summary="Child worker authority derived.",
                metadata={"child_authority_hash": child.authority_hash},
            )

    def _emit_worker_authority_rejected(self, mission_id: str, run_id: str, task_id: str, reason: str) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_authority_rejected"):
            telemetry.record_worker_authority_rejected(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=f"{run_id}:{task_id}",
                task_id=task_id,
                safe_summary="Worker authority rejected.",
                metadata={"reason": reason},
            )

    def _emit_worker_started(self, mission_id: str, run_id: str, context: WorkerExecutionContext) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_started"):
            telemetry.record_worker_started(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=context.worker_id,
                task_id=context.task_id,
                safe_summary="Worker started.",
                metadata={"mode": context.execution_mode.value},
            )

    def _emit_worker_completed(self, mission_id: str, run_id: str, result: WorkerResult) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_completed"):
            telemetry.record_worker_completed(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=result.worker_id,
                task_id=result.task_id,
                safe_summary="Worker completed.",
                metadata={"result_hash": result.result_hash},
                receipt_refs=result.evidence_packet.receipt_refs,
                finalgate_certificate_refs=result.evidence_packet.finalgate_certificate_refs,
                memory_feedback_refs=result.evidence_packet.memory_feedback_refs,
            )

    def _emit_worker_result_submitted(self, mission_id: str, run_id: str, result: WorkerResult) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_result_submitted"):
            telemetry.record_worker_result_submitted(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=result.worker_id,
                task_id=result.task_id,
                safe_summary="Worker result submitted.",
                metadata={"result_hash": result.result_hash},
                receipt_refs=result.evidence_packet.receipt_refs,
                finalgate_certificate_refs=result.evidence_packet.finalgate_certificate_refs,
                memory_feedback_refs=result.evidence_packet.memory_feedback_refs,
            )

    def _emit_worker_result_merged(self, mission_id: str, run_id: str, result: WorkerResult) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_result_merged"):
            telemetry.record_worker_result_merged(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=result.worker_id,
                task_id=result.task_id,
                safe_summary="Worker result merged.",
                metadata={"result_hash": result.result_hash},
                receipt_refs=result.evidence_packet.receipt_refs,
                finalgate_certificate_refs=result.evidence_packet.finalgate_certificate_refs,
                memory_feedback_refs=result.evidence_packet.memory_feedback_refs,
            )

    def _emit_worker_result_rejected(self, mission_id: str, run_id: str, result: WorkerResult, *, reasons: list[str]) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_result_rejected"):
            telemetry.record_worker_result_rejected(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                worker_id=result.worker_id,
                task_id=result.task_id,
                safe_summary="Worker result rejected.",
                metadata={"reasons": reasons, "result_hash": result.result_hash},
            )

    def _emit_worker_conflict(self, mission_id: str, run_id: str, conflict_key: str, worker_a: str, worker_b: str) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_conflict_detected"):
            telemetry.record_worker_conflict_detected(
                mission_id=mission_id,
                worker_fleet_run_id=run_id,
                safe_summary="Conflicting worker outputs detected.",
                metadata={"conflict_key": conflict_key, "worker_a": worker_a, "worker_b": worker_b},
            )

    def _emit_worker_metric(self, mission_id: str, metric_kind: TelemetryMetricKind, value: float, safe_summary: str, metadata: dict[str, Any]) -> None:
        telemetry = self._telemetry_sink
        if telemetry is not None and hasattr(telemetry, "record_worker_metric"):
            telemetry.record_worker_metric(
                mission_id,
                metric_kind,
                value,
                safe_summary=safe_summary,
                metadata=metadata,
            )


def _scope_subset(child: list[str], parent: list[str]) -> bool:
    return set(child).issubset(set(parent))


def _intersection(child: list[str], parent: list[str]) -> list[str]:
    return [item for item in child if item in set(parent)]


def _credential_scope_hashes(parent_envelope: MissionAuthorityEnvelope) -> list[str]:
    return [stable_hash(grant) for grant in parent_envelope.credential_grants]


def _is_strict_subset(parent: MissionAuthorityEnvelope, scope: WorkerScope, task: WorkerTask) -> bool:
    return (
        set(scope.allowed_actions) != set(parent.allowed_actions)
        or set(scope.allowed_tools) != set(parent.allowed_tools)
        or set(scope.allowed_systems) != set(parent.allowed_systems)
        or set(scope.allowed_paths) != set(parent.allowed_paths)
        or set(scope.allowed_domains) != set(parent.allowed_domains)
        or set(scope.allowed_data_types) != set(parent.allowed_data_types)
        or task.budget.max_actions < parent.max_actions
        or task.budget.max_cost_usd < parent.max_cost_usd
        or task.deadline.timeout_seconds < parent.max_duration_minutes * 60
        or task.scope.allow_power_runtime is False
        or task.scope.allow_agentruntime is False
    )


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
