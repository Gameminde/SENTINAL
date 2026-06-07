from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import fmean
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.memory.models import PersistentMemoryRetrievalResult
from sentinel.operator.models import MissionEvent
from sentinel.operator.replay import MissionReplayView
from sentinel.operator.workflow_models import WorkflowCheckpoint, WorkflowReplayView
from sentinel.power.runtime import PowerMissionTimeline, PowerMissionTimelineItem, PowerRuntimeResult, PowerRuntimeStatus
from sentinel.telemetry.models import (
    TelemetryDomain,
    TelemetryEventKind,
    TelemetryEventRecord,
    TelemetryMetricKind,
    TelemetryMetricSample,
    TelemetrySnapshot,
    TelemetrySourceSurface,
)
from sentinel.telemetry.redaction import sanitize_telemetry_refs, sanitize_telemetry_value
from sentinel.telemetry.store import TelemetryStore


class TelemetryCertificationError(RuntimeError):
    pass


class TelemetryKernel:
    def __init__(self, root: str | Any, *, enabled: bool = True) -> None:
        self.store = TelemetryStore(root, enabled=enabled)
        self._mission_started_at: dict[str, datetime] = {}
        self._replan_started_at: dict[str, datetime] = {}
        self._model_call_started_at: dict[str, datetime] = {}

    def certified_mode_status(self) -> TelemetrySnapshot:
        return self.store.certified_mode_status()

    def require_certified_mode(self) -> TelemetrySnapshot:
        status = self.certified_mode_status()
        if not status.certified_mode:
            reason = ", ".join(status.reasons) or "telemetry_unavailable"
            raise TelemetryCertificationError(f"certified_mode_required:{reason}")
        return status

    def record_mission_event(self, event: MissionEvent) -> TelemetryEventRecord:
        telemetry_kind = _map_mission_event_kind(event.event_type)
        record = self.store.record_event(
            TelemetryEventRecord(
                mission_id=event.mission_id,
                workflow_id=getattr(event, "workflow_id", None),
                session_id=getattr(event, "session_id", None),
                source_surface=TelemetrySourceSurface.MISSION_STORE,
                domain=_domain_for_event(telemetry_kind),
                event_kind=telemetry_kind,
                safe_summary=event.safe_summary,
                metadata={
                    "mission_event_type": event.event_type,
                    "sequence": event.sequence,
                    "created_at": event.created_at.isoformat(),
                    **event.metadata,
                },
                receipt_refs=event.receipt_refs,
                finalgate_certificate_refs=event.finalgate_certificate_refs,
                memory_feedback_refs=event.memory_feedback_refs,
            )
        )
        self._derive_mission_metrics(event, record)
        return record

    def record_model_call_started(
        self,
        request: RealModelRequest,
        *,
        session_id: str | None = None,
        frame_hash: str | None = None,
    ) -> TelemetryEventRecord:
        self._model_call_started_at[request.id] = datetime.now(UTC)
        record = self.store.record_event(
            TelemetryEventRecord(
                mission_id=None,
                session_id=session_id,
                source_surface=TelemetrySourceSurface.LLM_OPERATOR,
                domain=TelemetryDomain.LLM,
                event_kind=TelemetryEventKind.MODEL_CALL_STARTED,
                safe_summary="LLM model call started.",
                metadata={
                    "request_id": request.id,
                    "provider_id": request.provider_id,
                    "backend_id": request.backend_id,
                    "model_id": request.model_id,
                    "runtime": request.runtime,
                    "prompt_hash": request.prompt_hash,
                    "frame_hash": frame_hash or request.frame_hash,
                    "request_hash": request.request_hash,
                    "user_model_contract_id": request.user_model_contract_id,
                },
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=None,
                session_id=session_id,
                source_surface=TelemetrySourceSurface.LLM_OPERATOR,
                domain=TelemetryDomain.LLM,
                metric_kind=TelemetryMetricKind.PROVIDER_BACKEND_MODEL_SELECTED,
                value={
                    "provider_id": request.provider_id,
                    "backend_id": request.backend_id,
                    "model_id": request.model_id,
                },
                safe_summary="Selected LLM provider/backend/model.",
                metadata={"request_id": request.id, "request_hash": request.request_hash},
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=None,
                session_id=session_id,
                source_surface=TelemetrySourceSurface.LLM_OPERATOR,
                domain=TelemetryDomain.LLM,
                metric_kind=TelemetryMetricKind.TOKEN_USAGE,
                value=request.estimated_input_tokens + request.estimated_output_tokens,
                unit="tokens",
                safe_summary="Estimated LLM token usage.",
                metadata={
                    "request_id": request.id,
                    "estimated_input_tokens": request.estimated_input_tokens,
                    "estimated_output_tokens": request.estimated_output_tokens,
                },
            )
        )
        return record

    def record_model_call_completed(
        self,
        request: RealModelRequest,
        *,
        decision: Any | None = None,
        provider_response_hash: str | None = None,
        reasoning_hash: str | None = None,
        session_id: str | None = None,
        blocked_reason: str | None = None,
        schema_invalid: bool = False,
    ) -> TelemetryEventRecord:
        if schema_invalid:
            event_kind = TelemetryEventKind.MODEL_SCHEMA_INVALID
            safe_summary = "LLM operator structured output failed schema validation."
        else:
            event_kind = TelemetryEventKind.MODEL_CALL_COMPLETED
            safe_summary = "LLM model call completed."
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=None,
                session_id=session_id,
                source_surface=TelemetrySourceSurface.LLM_OPERATOR,
                domain=TelemetryDomain.LLM,
                event_kind=event_kind,
                safe_summary=safe_summary,
                metadata={
                    "request_id": request.id,
                    "provider_id": request.provider_id,
                    "backend_id": request.backend_id,
                    "model_id": request.model_id,
                    "request_hash": request.request_hash,
                    "provider_response_hash": provider_response_hash,
                    "reasoning_hash": reasoning_hash,
                    "blocked_reason": blocked_reason,
                    "decision_kind": getattr(getattr(decision, "intent", None), "kind", None),
                },
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=None,
                session_id=session_id,
                source_surface=TelemetrySourceSurface.LLM_OPERATOR,
                domain=TelemetryDomain.LLM,
                metric_kind=TelemetryMetricKind.LLM_SCHEMA_FAILURE_RATE,
                value=1 if schema_invalid or blocked_reason else 0,
                unit="ratio",
                safe_summary="LLM structured-output failure rate sample.",
                metadata={"request_id": request.id, "schema_invalid": schema_invalid, "blocked_reason": blocked_reason},
            )
        )
        return event

    def record_power_runtime_result(self, result: PowerRuntimeResult, *, mission_id: str | None = None) -> list[TelemetryEventRecord]:
        mission_id = mission_id or result.mission_id
        events: list[TelemetryEventRecord] = []
        events.extend(self._record_power_timeline(result, mission_id=mission_id))
        terminal_kind = {
            PowerRuntimeStatus.COMPLETED: TelemetryEventKind.MISSION_COMPLETED,
            PowerRuntimeStatus.FAILED: TelemetryEventKind.MISSION_FAILED,
            PowerRuntimeStatus.BLOCKED: TelemetryEventKind.MISSION_BLOCKED,
            PowerRuntimeStatus.ABORTED: TelemetryEventKind.MISSION_KILLED,
            PowerRuntimeStatus.NOT_STARTED: TelemetryEventKind.MISSION_BLOCKED,
        }[result.status]
        events.append(
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                    domain=TelemetryDomain.PRODUCT_POWER,
                    event_kind=terminal_kind,
                    safe_summary=f"PowerRuntime finished with status {result.status.value}.",
                    metadata={
                        "power_runtime_status": result.status.value,
                        "blocked_reason_hash": _hash_optional(result.blocked_reason),
                        "step_count": len(result.step_results),
                    },
                    receipt_refs=sanitize_telemetry_refs(result.receipt_refs),
                    finalgate_certificate_refs=sanitize_telemetry_refs(result.finalgate_certificate_refs),
                    memory_feedback_refs=sanitize_telemetry_refs(result.memory_feedback_refs),
                )
            )
        )
        if result.status is PowerRuntimeStatus.COMPLETED:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                    domain=TelemetryDomain.PRODUCT_POWER,
                    metric_kind=TelemetryMetricKind.MISSION_COMPLETION_RATE,
                    value=1,
                    unit="ratio",
                    safe_summary="Completed mission sample.",
                    metadata={"status": result.status.value},
                )
            )
        else:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                    domain=TelemetryDomain.PRODUCT_POWER,
                    metric_kind=TelemetryMetricKind.MISSION_COMPLETION_RATE,
                    value=0,
                    unit="ratio",
                    safe_summary="Incomplete mission sample.",
                    metadata={"status": result.status.value, "blocked_reason_hash": _hash_optional(result.blocked_reason)},
                )
            )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                domain=TelemetryDomain.PRODUCT_POWER,
                metric_kind=TelemetryMetricKind.RECEIPT_COMPLETENESS,
                value=_completeness_ratio(
                    [*result.receipt_refs, *result.finalgate_certificate_refs],
                    expected=len(result.step_results) or 1,
                ),
                unit="ratio",
                safe_summary="PowerRuntime proof completeness sample.",
                metadata={
                    "receipt_count": len(result.receipt_refs),
                    "finalgate_count": len(result.finalgate_certificate_refs),
                    "step_count": len(result.step_results),
                },
            )
        )
        if result.status is PowerRuntimeStatus.COMPLETED:
            useful_seconds = _timeline_time_to_useful_seconds(result.timeline)
            if useful_seconds is not None:
                self.store.record_metric(
                    TelemetryMetricSample(
                        mission_id=mission_id,
                        source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                        domain=TelemetryDomain.PRODUCT_POWER,
                        metric_kind=TelemetryMetricKind.TIME_TO_USEFUL_RESULT,
                        value=useful_seconds,
                        unit="seconds",
                        safe_summary="Time to useful result sample.",
                        metadata={"status": result.status.value},
                    )
                )
                self.store.record_metric(
                    TelemetryMetricSample(
                        mission_id=mission_id,
                        source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                        domain=TelemetryDomain.PRODUCT_POWER,
                        metric_kind=TelemetryMetricKind.AUTONOMOUS_USEFUL_MINUTES,
                        value=round(useful_seconds / 60.0, 6),
                        unit="minutes",
                        safe_summary="Autonomous useful minutes sample.",
                        metadata={"status": result.status.value},
                    )
                )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                domain=TelemetryDomain.PRODUCT_POWER,
                metric_kind=TelemetryMetricKind.TIMELINE_REPLAY_COMPLETENESS,
                value=1 if result.timeline.verify_chain() else 0,
                unit="ratio",
                safe_summary="PowerRuntime timeline replay completeness sample.",
                metadata={"status": result.status.value},
            )
        )
        return events

    def record_agentruntime_result(self, mission_id: str, result: Any) -> list[TelemetryEventRecord]:
        events: list[TelemetryEventRecord] = []
        replan_ready = bool(getattr(result, "replan_ready", False))
        automatic_replan_executed = bool(getattr(result, "automatic_replan_executed", False))
        memory_refs = _agentruntime_memory_refs(result)
        receipt_refs = sanitize_telemetry_refs(getattr(result, "receipt_refs", []))
        finalgate_refs = _agentruntime_finalgate_refs(result)
        replan_packet_ref = getattr(result, "replan_packet_ref", None) or _hash_optional(getattr(result, "replan_packet", None))
        brain_status = getattr(result, "brain_candidate_source_status", None)
        if replan_ready:
            events.append(
                self.store.record_event(
                    TelemetryEventRecord(
                        mission_id=mission_id,
                        source_surface=TelemetrySourceSurface.AGENT_RUNTIME,
                        domain=TelemetryDomain.REPLAN,
                        event_kind=TelemetryEventKind.REPLAN_CANDIDATE_CREATED,
                        safe_summary="AgentRuntime produced a replan-ready result.",
                        metadata={
                            "replan_ready": replan_ready,
                            "automatic_replan_executed": automatic_replan_executed,
                            "replan_packet_ref": replan_packet_ref,
                            "brain_candidate_source_status": brain_status,
                        },
                        receipt_refs=receipt_refs,
                        finalgate_certificate_refs=finalgate_refs,
                        memory_feedback_refs=memory_refs,
                    )
                )
            )
        if automatic_replan_executed:
            event_kind = TelemetryEventKind.REPLAN_EXECUTED
            metric_value = 1
        else:
            event_kind = TelemetryEventKind.REPLAN_REJECTED if replan_ready else TelemetryEventKind.REPLAN_ESCALATED
            metric_value = 0
        events.append(
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.AGENT_RUNTIME,
                    domain=TelemetryDomain.REPLAN,
                    event_kind=event_kind,
                    safe_summary="AgentRuntime replan outcome recorded.",
                    metadata={
                        "status": getattr(result, "status", None),
                        "success": bool(getattr(result, "success", False)),
                        "replan_ready": replan_ready,
                        "automatic_replan_executed": automatic_replan_executed,
                        "replan_packet_ref": replan_packet_ref,
                        "brain_candidate_source_status": brain_status,
                    },
                    receipt_refs=receipt_refs,
                    finalgate_certificate_refs=finalgate_refs,
                    memory_feedback_refs=memory_refs,
                )
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.AGENT_RUNTIME,
                domain=TelemetryDomain.REPLAN,
                metric_kind=TelemetryMetricKind.REPLAN_SUCCESS_RATE,
                value=metric_value,
                unit="ratio",
                safe_summary="AgentRuntime replan success sample.",
                metadata={"replan_ready": replan_ready, "automatic_replan_executed": automatic_replan_executed},
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.AGENT_RUNTIME,
                domain=TelemetryDomain.MEMORY,
                metric_kind=TelemetryMetricKind.MEMORY_RECALL_COUNT,
                value=len(memory_refs),
                unit="count",
                safe_summary="AgentRuntime memory feedback count sample.",
                metadata={"memory_feedback_refs": memory_refs},
            )
        )
        return events

    def record_workflow_checkpoint(
        self,
        checkpoint: WorkflowCheckpoint,
        *,
        source_surface: TelemetrySourceSurface = TelemetrySourceSurface.WORKFLOW_STORE,
    ) -> TelemetryEventRecord:
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=checkpoint.mission_id,
                workflow_id=checkpoint.workflow_id,
                source_surface=source_surface,
                domain=TelemetryDomain.WORKFLOW,
                event_kind=TelemetryEventKind.WORKFLOW_CHECKPOINT_CREATED,
                safe_summary="Workflow checkpoint created.",
                metadata={
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "branch_id": checkpoint.branch_id,
                    "plan_hash": checkpoint.plan_hash,
                    "record_version": checkpoint.record_version,
                    "prepared_event_hash": checkpoint.prepared_event_hash,
                },
                receipt_refs=sanitize_telemetry_refs(checkpoint.receipt_refs),
                finalgate_certificate_refs=sanitize_telemetry_refs(checkpoint.finalgate_certificate_refs),
                memory_feedback_refs=sanitize_telemetry_refs(checkpoint.memory_feedback_refs),
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=checkpoint.mission_id,
                workflow_id=checkpoint.workflow_id,
                source_surface=source_surface,
                domain=TelemetryDomain.WORKFLOW,
                metric_kind=TelemetryMetricKind.WORKFLOW_CHECKPOINT_LATENCY,
                value=_checkpoint_latency_seconds(checkpoint),
                unit="seconds",
                safe_summary="Workflow checkpoint latency sample.",
                metadata={"checkpoint_id": checkpoint.checkpoint_id, "record_version": checkpoint.record_version},
            )
        )
        return event

    def record_memory_recall(self, mission_id: str, retrieval: PersistentMemoryRetrievalResult) -> TelemetryEventRecord:
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.MEMORY,
                event_kind=TelemetryEventKind.MEMORY_RECALL_USED,
                safe_summary=f"Persistent memory recall returned {len(retrieval.hits)} hit(s).",
                metadata={
                    "query_hash": retrieval.query_hash,
                    "candidate_count": retrieval.candidate_count,
                    "hit_count": len(retrieval.hits),
                    "quarantined_record_ids": sanitize_telemetry_refs(retrieval.quarantined_record_ids),
                },
                memory_feedback_refs=sanitize_telemetry_refs([hit.record_id for hit in retrieval.hits]),
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.MEMORY,
                metric_kind=TelemetryMetricKind.MEMORY_RECALL_COUNT,
                value=len(retrieval.hits),
                unit="count",
                safe_summary="Memory recall count sample.",
                metadata={"query_hash": retrieval.query_hash, "candidate_count": retrieval.candidate_count},
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.MEMORY,
                metric_kind=TelemetryMetricKind.MEMORY_RECALL_UTILITY,
                value=_memory_recall_utility(retrieval),
                unit="score",
                safe_summary="Memory recall utility sample.",
                metadata={"hit_count": len(retrieval.hits), "query_hash": retrieval.query_hash},
            )
        )
        return event

    def record_replay_view(self, replay: MissionReplayView | WorkflowReplayView, *, source_surface: TelemetrySourceSurface = TelemetrySourceSurface.REPLAY) -> TelemetryEventRecord:
        if isinstance(replay, MissionReplayView):
            mission_id = replay.mission_id
            workflow_id = None
            tampered = replay.tampered
            receipt_refs = replay.receipt_refs
            finalgate_refs = replay.finalgate_certificate_refs
            memory_refs = replay.memory_feedback_refs
        else:
            mission_id = replay.mission_id
            workflow_id = replay.workflow_id
            tampered = replay.tampered
            receipt_refs = []
            finalgate_refs = []
            memory_refs = []
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                workflow_id=workflow_id,
                source_surface=source_surface,
                domain=TelemetryDomain.PRODUCT_POWER,
                event_kind=TelemetryEventKind.MISSION_STARTED if not tampered else TelemetryEventKind.MISSION_BLOCKED,
                safe_summary="Replay view built.",
                metadata={"tampered": tampered, "reexecuted_actions": False},
                receipt_refs=sanitize_telemetry_refs(receipt_refs),
                finalgate_certificate_refs=sanitize_telemetry_refs(finalgate_refs),
                memory_feedback_refs=sanitize_telemetry_refs(memory_refs),
            )
        )
        self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                workflow_id=workflow_id,
                source_surface=source_surface,
                domain=TelemetryDomain.PRODUCT_POWER,
                metric_kind=TelemetryMetricKind.TIMELINE_REPLAY_COMPLETENESS,
                value=0 if tampered else 1,
                unit="ratio",
                safe_summary="Replay completeness sample.",
                metadata={"tampered": tampered},
            )
        )
        return event

    def record_operator_interruption(self, *, session_id: str, command: str) -> TelemetryMetricSample:
        return self.store.record_metric(
            TelemetryMetricSample(
                session_id=session_id,
                source_surface=TelemetrySourceSurface.COCKPIT,
                domain=TelemetryDomain.OPERATIONAL,
                metric_kind=TelemetryMetricKind.OPERATOR_INTERRUPTION_COUNT,
                value=1,
                unit="count",
                safe_summary="Operator interruption observed.",
                metadata={"command": command},
            )
        )

    def record_gate_decision(
        self,
        *,
        mission_id: str,
        allowed: bool,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        source_surface: TelemetrySourceSurface = TelemetrySourceSurface.MISSION_KERNEL,
    ) -> TelemetryEventRecord:
        event_kind = TelemetryEventKind.GATE_ALLOWED if allowed else TelemetryEventKind.GATE_BLOCKED
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=source_surface,
                domain=TelemetryDomain.SAFETY,
                event_kind=event_kind,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )
        if not allowed:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=source_surface,
                    domain=TelemetryDomain.SAFETY,
                    metric_kind=TelemetryMetricKind.GATE_REJECT_COUNT,
                    value=1,
                    unit="count",
                    safe_summary="Gate rejection count sample.",
                    metadata=metadata or {},
                )
            )
        return event

    def record_finalgate_decision(
        self,
        *,
        mission_id: str,
        passed: bool,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        source_surface: TelemetrySourceSurface = TelemetrySourceSurface.MISSION_KERNEL,
    ) -> TelemetryEventRecord:
        event_kind = TelemetryEventKind.FINALGATE_PASSED if passed else TelemetryEventKind.FINALGATE_FAILED
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=source_surface,
                domain=TelemetryDomain.SAFETY,
                event_kind=event_kind,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )
        if not passed:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=source_surface,
                    domain=TelemetryDomain.SAFETY,
                    metric_kind=TelemetryMetricKind.FINALGATE_REJECT_COUNT,
                    value=1,
                    unit="count",
                    safe_summary="FinalGate rejection count sample.",
                    metadata=metadata or {},
                )
            )
        return event

    def record_organ_call(
        self,
        *,
        mission_id: str,
        organ_kind: str,
        action_kind: str,
        safe_summary: str,
        success: bool,
        source_surface: TelemetrySourceSurface = TelemetrySourceSurface.POWER_RUNTIME,
        metadata: dict[str, Any] | None = None,
        latency_seconds: float | None = None,
    ) -> TelemetryEventRecord:
        event_kind = TelemetryEventKind.ORGAN_CALLED if success else TelemetryEventKind.ORGAN_FAILED
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=source_surface,
                domain=TelemetryDomain.ORGAN,
                event_kind=event_kind,
                safe_summary=safe_summary,
                metadata={"organ_kind": organ_kind, "action_kind": action_kind, **(metadata or {})},
            )
        )
        if latency_seconds is not None:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=source_surface,
                    domain=TelemetryDomain.ORGAN,
                    metric_kind=TelemetryMetricKind.ORGAN_LATENCY,
                    value=max(0.0, float(latency_seconds)),
                    unit="seconds",
                    safe_summary="Organ latency sample.",
                    metadata={"organ_kind": organ_kind, "action_kind": action_kind, **(metadata or {})},
                )
            )
        return event

    def record_memory_recall_rejected(
        self,
        *,
        mission_id: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.MEMORY,
                event_kind=TelemetryEventKind.MEMORY_RECALL_REJECTED,
                safe_summary="Persistent memory recall was rejected.",
                metadata={"reason": reason, **(metadata or {})},
            )
        )

    def record_credential_access_denied(
        self,
        *,
        mission_id: str,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.SAFETY,
                event_kind=TelemetryEventKind.CREDENTIAL_ACCESS_DENIED,
                safe_summary="Credential access denied.",
                metadata={"reason": reason, **(metadata or {})},
            )
        )

    def record_kill_switch_triggered(
        self,
        *,
        mission_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        latency_seconds: float | None = None,
    ) -> TelemetryEventRecord:
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.SAFETY,
                event_kind=TelemetryEventKind.KILL_SWITCH_TRIGGERED,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )
        if latency_seconds is not None:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.SAFETY,
                    metric_kind=TelemetryMetricKind.KILL_SWITCH_LATENCY,
                    value=max(0.0, float(latency_seconds)),
                    unit="seconds",
                    safe_summary="Kill switch latency sample.",
                    metadata=metadata or {},
                )
            )
        return event

    def record_revocation_detected(
        self,
        *,
        mission_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        latency_seconds: float | None = None,
    ) -> TelemetryEventRecord:
        event = self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.AUTHORITY,
                event_kind=TelemetryEventKind.REVOCATION_DETECTED,
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )
        if latency_seconds is not None:
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.AUTHORITY,
                    metric_kind=TelemetryMetricKind.REVOCATION_LATENCY,
                    value=max(0.0, float(latency_seconds)),
                    unit="seconds",
                    safe_summary="Revocation latency sample.",
                    metadata=metadata or {},
                )
            )
        return event

    def record_browser_neural_ledger_event(
        self,
        *,
        workflow_id: str,
        run_id: str,
        event_type: str,
        actor_or_neuron_id: str,
        refs: dict[str, Any],
        state: dict[str, Any],
        call_id: str | None = None,
    ) -> TelemetryEventRecord:
        sanitized_refs, _, _ = sanitize_telemetry_value(refs, path="$.refs")
        sanitized_state, _, _ = sanitize_telemetry_value(state, path="$.state")
        return self.store.record_event(
            TelemetryEventRecord(
                workflow_id=workflow_id,
                source_surface=TelemetrySourceSurface.BROWSER_LEDGER,
                domain=TelemetryDomain.ORGAN,
                event_kind=TelemetryEventKind.ORGAN_CALLED,
                safe_summary=f"Browser neural ledger event {event_type} recorded.",
                metadata={
                    "run_id": run_id,
                    "call_id": call_id,
                    "event_type": event_type,
                    "actor_or_neuron_id": actor_or_neuron_id,
                    "refs": sanitized_refs,
                    "state": sanitized_state,
                },
            )
        )

    def _derive_mission_metrics(self, event: MissionEvent, telemetry_event: TelemetryEventRecord) -> None:
        if event.event_type == "mission_running":
            self._mission_started_at.setdefault(event.mission_id, event.created_at)
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=event.mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.OPERATIONAL,
                    event_kind=TelemetryEventKind.MISSION_STARTED,
                    safe_summary="Mission entered running state.",
                    metadata={"mission_event_hash": event.event_hash},
                )
            )
        if event.event_type == "mission_paused":
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=event.mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.OPERATIONAL,
                    metric_kind=TelemetryMetricKind.OPERATOR_INTERRUPTION_COUNT,
                    value=1,
                    unit="count",
                    safe_summary="Mission pause interruption count sample.",
                    metadata={"mission_event_hash": event.event_hash},
                )
            )
        if event.event_type == "mission_resumed":
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=event.mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.OPERATIONAL,
                    event_kind=TelemetryEventKind.MISSION_RESUMED,
                    safe_summary="Mission resumed.",
                    metadata={"mission_event_hash": event.event_hash},
                )
            )
        if event.event_type == "mission_killed":
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=event.mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.SAFETY,
                    event_kind=TelemetryEventKind.KILL_SWITCH_TRIGGERED,
                    safe_summary="Mission kill switch triggered.",
                    metadata={"mission_event_hash": event.event_hash},
                )
            )
        if event.event_type == "mission_revoked":
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=event.mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.AUTHORITY,
                    event_kind=TelemetryEventKind.REVOCATION_DETECTED,
                    safe_summary="Mission authority revocation detected.",
                    metadata={"mission_event_hash": event.event_hash},
                )
            )
        if event.event_type == "persistent_memory_retrieved":
            self.store.record_metric(
                TelemetryMetricSample(
                    mission_id=event.mission_id,
                    source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                    domain=TelemetryDomain.MEMORY,
                    metric_kind=TelemetryMetricKind.MEMORY_RECALL_COUNT,
                    value=int(event.metadata.get("record_count", len(event.memory_feedback_refs))),
                    unit="count",
                    safe_summary="Mission memory recall count sample.",
                    metadata={"query_hash": event.metadata.get("query_hash")},
                )
            )
        if _mission_event_has_redaction(event):
            self.store.record_event(
                TelemetryEventRecord(
                    mission_id=event.mission_id,
                    workflow_id=getattr(event, "workflow_id", None),
                    session_id=getattr(event, "session_id", None),
                    source_surface=TelemetrySourceSurface.MISSION_STORE,
                    domain=TelemetryDomain.SAFETY,
                    event_kind=TelemetryEventKind.SECRET_REDACTION_HIT,
                    safe_summary="Telemetry payload required redaction.",
                    metadata={"mission_event_type": event.event_type, "redaction_detected": True},
                )
            )

    def _record_power_timeline(self, result: PowerRuntimeResult, *, mission_id: str) -> list[TelemetryEventRecord]:
        events: list[TelemetryEventRecord] = []
        start_times: dict[str, datetime] = {}
        for item in result.timeline.items:
            if item.event_type == "step_started" and item.step_id:
                start_times[item.step_id] = item.timestamp
            if item.event_type == "runtime_not_started":
                events.append(
                    self.store.record_event(
                        TelemetryEventRecord(
                            mission_id=mission_id,
                            source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                            domain=TelemetryDomain.OPERATIONAL,
                            event_kind=TelemetryEventKind.MISSION_BLOCKED,
                            safe_summary=item.safe_summary,
                            metadata={"timeline_event_type": item.event_type, "blocked_reason": item.blocked_reason},
                        )
                    )
                )
                continue
            if item.event_type == "runtime_blocked":
                events.append(
                    self.record_gate_decision(
                        mission_id=mission_id,
                        allowed=False,
                        safe_summary=item.safe_summary,
                        metadata={
                            "timeline_event_type": item.event_type,
                            "blocked_reason_hash": _hash_optional(item.blocked_reason),
                        },
                        source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                    )
                )
                continue
            if item.event_type == "step_started":
                events.append(
                    self.store.record_event(
                        TelemetryEventRecord(
                            mission_id=mission_id,
                            source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                            domain=TelemetryDomain.WORKFLOW,
                            event_kind=TelemetryEventKind.STEP_STARTED,
                            safe_summary=item.safe_summary,
                            metadata={"step_id": item.step_id},
                            receipt_refs=sanitize_telemetry_refs(item.receipt_refs),
                            finalgate_certificate_refs=sanitize_telemetry_refs(item.finalgate_certificate_refs),
                            memory_feedback_refs=sanitize_telemetry_refs(item.memory_feedback_refs),
                        )
                    )
                )
                continue
            if item.event_type in {"step_succeeded", "step_blocked", "step_failed", "step_aborted"}:
                event_kind = {
                    "step_succeeded": TelemetryEventKind.STEP_COMPLETED,
                    "step_blocked": TelemetryEventKind.STEP_FAILED,
                    "step_failed": TelemetryEventKind.STEP_FAILED,
                    "step_aborted": TelemetryEventKind.STEP_FAILED,
                }[item.event_type]
                success = item.event_type == "step_succeeded"
                events.append(
                    self.store.record_event(
                        TelemetryEventRecord(
                            mission_id=mission_id,
                            source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                            domain=TelemetryDomain.WORKFLOW,
                            event_kind=event_kind,
                            safe_summary=item.safe_summary,
                            metadata={
                                "step_id": item.step_id,
                                "timeline_event_type": item.event_type,
                                "blocked_reason_hash": _hash_optional(item.blocked_reason),
                            },
                            receipt_refs=sanitize_telemetry_refs(item.receipt_refs),
                            finalgate_certificate_refs=sanitize_telemetry_refs(item.finalgate_certificate_refs),
                            memory_feedback_refs=sanitize_telemetry_refs(item.memory_feedback_refs),
                        )
                    )
                )
                if item.step_id in start_times and item.timestamp.tzinfo is not None:
                    latency = max(0.0, (item.timestamp - start_times[item.step_id]).total_seconds())
                    self.store.record_metric(
                        TelemetryMetricSample(
                            mission_id=mission_id,
                            source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                            domain=TelemetryDomain.WORKFLOW,
                            metric_kind=TelemetryMetricKind.STEP_LATENCY,
                            value=latency,
                            unit="seconds",
                            safe_summary="PowerRuntime step latency sample.",
                            metadata={"step_id": item.step_id, "timeline_event_type": item.event_type},
                        )
                    )
                    self.store.record_metric(
                        TelemetryMetricSample(
                            mission_id=mission_id,
                            source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                            domain=TelemetryDomain.ORGAN,
                            metric_kind=TelemetryMetricKind.ORGAN_LATENCY,
                            value=latency,
                            unit="seconds",
                            safe_summary="PowerRuntime organ latency sample.",
                            metadata={"step_id": item.step_id, "timeline_event_type": item.event_type},
                        )
                    )
                if item.event_type in {"step_blocked", "step_failed", "step_aborted"}:
                    self.record_gate_decision(
                        mission_id=mission_id,
                        allowed=False,
                        safe_summary=item.safe_summary,
                        metadata={
                            "step_id": item.step_id,
                            "timeline_event_type": item.event_type,
                            "blocked_reason_hash": _hash_optional(item.blocked_reason),
                        },
                        source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                    )
                if item.event_type == "step_aborted":
                    self.record_kill_switch_triggered(
                        mission_id=mission_id,
                        safe_summary="Kill switch aborted a PowerRuntime step.",
                        metadata={"step_id": item.step_id},
                    )
                if success:
                    self.record_finalgate_decision(
                        mission_id=mission_id,
                        passed=bool(item.finalgate_certificate_refs),
                        safe_summary="PowerRuntime step completed with FinalGate proof." if item.finalgate_certificate_refs else "PowerRuntime step completed without FinalGate proof.",
                        metadata={"step_id": item.step_id, "timeline_event_type": item.event_type},
                        source_surface=TelemetrySourceSurface.POWER_RUNTIME,
                    )
                continue
        return events


def _map_mission_event_kind(event_type: str) -> TelemetryEventKind:
    mapping = {
        "mission_created": TelemetryEventKind.MISSION_CREATED,
        "mission_queued": TelemetryEventKind.MISSION_QUEUED,
        "mission_running": TelemetryEventKind.MISSION_RUNNING,
        "mission_completed": TelemetryEventKind.MISSION_COMPLETED,
        "mission_failed": TelemetryEventKind.MISSION_FAILED,
        "mission_killed": TelemetryEventKind.MISSION_KILLED,
        "mission_paused": TelemetryEventKind.MISSION_PAUSED,
        "mission_resumed": TelemetryEventKind.MISSION_RESUMED,
        "mission_blocked": TelemetryEventKind.MISSION_BLOCKED,
        "durable_workflow_created": TelemetryEventKind.WORKFLOW_CREATED,
        "workflow_checkpoint_prepared": TelemetryEventKind.WORKFLOW_CHECKPOINT_CREATED,
        "workflow_replan_required": TelemetryEventKind.REPLAN_REJECTED,
        "workflow_replan_auto_executing": TelemetryEventKind.REPLAN_EXECUTED,
        "workflow_replan_escalated": TelemetryEventKind.REPLAN_ESCALATED,
        "power_runtime_result": TelemetryEventKind.STEP_COMPLETED,
        "power_runtime_blocked": TelemetryEventKind.GATE_BLOCKED,
        "agentruntime_result": TelemetryEventKind.REPLAN_CANDIDATE_CREATED,
        "agentruntime_blocked": TelemetryEventKind.REPLAN_REJECTED,
        "persistent_memory_retrieved": TelemetryEventKind.MEMORY_RECALL_USED,
    }
    return mapping.get(event_type, TelemetryEventKind.ORGAN_CALLED)


def _domain_for_event(event_kind: TelemetryEventKind) -> TelemetryDomain:
    if event_kind in {
        TelemetryEventKind.MISSION_CREATED,
        TelemetryEventKind.MISSION_STARTED,
        TelemetryEventKind.MISSION_QUEUED,
        TelemetryEventKind.MISSION_RUNNING,
        TelemetryEventKind.MISSION_COMPLETED,
        TelemetryEventKind.MISSION_FAILED,
        TelemetryEventKind.MISSION_KILLED,
        TelemetryEventKind.MISSION_PAUSED,
        TelemetryEventKind.MISSION_RESUMED,
        TelemetryEventKind.MISSION_BLOCKED,
    }:
        return TelemetryDomain.OPERATIONAL
    if event_kind in {
        TelemetryEventKind.WORKFLOW_CREATED,
        TelemetryEventKind.WORKFLOW_CHECKPOINT_CREATED,
        TelemetryEventKind.WORKFLOW_CHECKPOINT_FAILED,
        TelemetryEventKind.WORKFLOW_RESUMED,
        TelemetryEventKind.REPLAN_CANDIDATE_CREATED,
        TelemetryEventKind.REPLAN_EXECUTED,
        TelemetryEventKind.REPLAN_ESCALATED,
        TelemetryEventKind.REPLAN_REJECTED,
        TelemetryEventKind.STEP_STARTED,
        TelemetryEventKind.STEP_COMPLETED,
        TelemetryEventKind.STEP_FAILED,
    }:
        return TelemetryDomain.WORKFLOW
    if event_kind in {
        TelemetryEventKind.MODEL_CALL_STARTED,
        TelemetryEventKind.MODEL_CALL_COMPLETED,
        TelemetryEventKind.MODEL_SCHEMA_INVALID,
    }:
        return TelemetryDomain.LLM
    if event_kind in {
        TelemetryEventKind.MEMORY_RECALL_USED,
        TelemetryEventKind.MEMORY_RECALL_REJECTED,
    }:
        return TelemetryDomain.MEMORY
    if event_kind in {
        TelemetryEventKind.GATE_ALLOWED,
        TelemetryEventKind.GATE_BLOCKED,
        TelemetryEventKind.FINALGATE_PASSED,
        TelemetryEventKind.FINALGATE_FAILED,
        TelemetryEventKind.KILL_SWITCH_TRIGGERED,
        TelemetryEventKind.REVOCATION_DETECTED,
        TelemetryEventKind.SECRET_REDACTION_HIT,
        TelemetryEventKind.CREDENTIAL_ACCESS_DENIED,
    }:
        return TelemetryDomain.SAFETY
    if event_kind in {
        TelemetryEventKind.ORGAN_CALLED,
        TelemetryEventKind.ORGAN_FAILED,
    }:
        return TelemetryDomain.ORGAN
    return TelemetryDomain.PRODUCT_POWER


def _completeness_ratio(values: Iterable[Any], *, expected: int) -> float:
    items = [value for value in values if value is not None and str(value)]
    if expected <= 0:
        return 1.0 if items else 0.0
    return round(min(1.0, len(items) / expected), 6)


def _checkpoint_latency_seconds(checkpoint: WorkflowCheckpoint) -> float:
    current = datetime.now(UTC)
    if checkpoint.created_at.tzinfo is None:
        return 0.0
    return max(0.0, (current - checkpoint.created_at).total_seconds())


def _memory_recall_utility(result: PersistentMemoryRetrievalResult) -> float:
    if not result.hits:
        return 0.0
    return round(fmean(hit.retrieval_score for hit in result.hits), 6)


def _agentruntime_memory_refs(result: Any) -> list[str]:
    refs = getattr(result, "memory_feedback_refs", None)
    if refs is None:
        memory_result = getattr(result, "memory_feedback_result", None)
        refs = getattr(memory_result, "memory_entry_refs", [])
    return sanitize_telemetry_refs(refs)


def _agentruntime_finalgate_refs(result: Any) -> list[str]:
    refs = getattr(result, "finalgate_certificate_refs", None)
    if refs is None:
        cert = getattr(result, "final_gate_certification", None)
        cert_id = getattr(cert, "id", None)
        refs = [cert_id] if cert_id else []
    return sanitize_telemetry_refs(refs)


def _hash_optional(value: Any | None) -> str | None:
    if value is None:
        return None
    sanitized, _, _ = sanitize_telemetry_value(value, path="$.optional")
    return stable_hash(sanitized)


def _timeline_time_to_useful_seconds(timeline: PowerMissionTimeline) -> float | None:
    start: datetime | None = None
    for item in timeline.items:
        if item.event_type == "step_started" and item.timestamp.tzinfo is not None and start is None:
            start = item.timestamp
        if start is not None and item.event_type == "step_succeeded" and item.timestamp.tzinfo is not None:
            return max(0.0, (item.timestamp - start).total_seconds())
    return None


def _mission_event_has_redaction(event: MissionEvent) -> bool:
    payload = json.dumps(event.model_dump(mode="json"), sort_keys=True, default=str)
    return "[REDACTED_SECRET]" in payload or "redacted_ref:" in payload or "[REDACTED_HASH:" in payload
