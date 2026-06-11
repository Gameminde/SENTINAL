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

    def record_metric(self, sample: TelemetryMetricSample) -> TelemetryMetricSample:
        return self.store.record_metric(sample)

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
                    "mission_event_type_hash": stable_hash(event.event_type),
                    "mission_event_family": _mission_event_family(event.event_type),
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

    def record_worker_spawn_requested(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_SPAWN_REQUESTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_spawn_blocked(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_SPAWN_BLOCKED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_authority_derived(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.AUTHORITY,
                event_kind=TelemetryEventKind.WORKER_AUTHORITY_DERIVED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_authority_rejected(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.AUTHORITY,
                event_kind=TelemetryEventKind.WORKER_AUTHORITY_REJECTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_started(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_STARTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_completed(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_COMPLETED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
                receipt_refs=sanitize_telemetry_refs(receipt_refs or []),
                finalgate_certificate_refs=sanitize_telemetry_refs(finalgate_certificate_refs or []),
                memory_feedback_refs=sanitize_telemetry_refs(memory_feedback_refs or []),
            )
        )

    def record_worker_failed(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_FAILED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_result_submitted(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_RESULT_SUBMITTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
                receipt_refs=sanitize_telemetry_refs(receipt_refs or []),
                finalgate_certificate_refs=sanitize_telemetry_refs(finalgate_certificate_refs or []),
                memory_feedback_refs=sanitize_telemetry_refs(memory_feedback_refs or []),
            )
        )

    def record_worker_result_merged(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
        receipt_refs: list[str] | None = None,
        finalgate_certificate_refs: list[str] | None = None,
        memory_feedback_refs: list[str] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_RESULT_MERGED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
                receipt_refs=sanitize_telemetry_refs(receipt_refs or []),
                finalgate_certificate_refs=sanitize_telemetry_refs(finalgate_certificate_refs or []),
                memory_feedback_refs=sanitize_telemetry_refs(memory_feedback_refs or []),
            )
        )

    def record_worker_result_rejected(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_RESULT_REJECTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_conflict_detected(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_CONFLICT_DETECTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, **(metadata or {})},
            )
        )

    def record_worker_killed(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_KILLED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_budget_exhausted(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_BUDGET_EXHAUSTED,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_timeout(
        self,
        *,
        mission_id: str,
        worker_fleet_run_id: str,
        worker_id: str,
        task_id: str,
        safe_summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> TelemetryEventRecord:
        return self.store.record_event(
            TelemetryEventRecord(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                event_kind=TelemetryEventKind.WORKER_TIMEOUT,
                safe_summary=safe_summary,
                metadata={"worker_fleet_run_id": worker_fleet_run_id, "worker_id": worker_id, "task_id": task_id, **(metadata or {})},
            )
        )

    def record_worker_metric(self, mission_id: str, metric_kind: TelemetryMetricKind, value: Any, *, safe_summary: str, metadata: dict[str, Any] | None = None) -> TelemetryMetricSample:
        return self.store.record_metric(
            TelemetryMetricSample(
                mission_id=mission_id,
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.WORKER,
                metric_kind=metric_kind,
                value=value,
                unit="ratio" if "rate" in metric_kind.value or "efficiency" in metric_kind.value else "count",
                safe_summary=safe_summary,
                metadata=metadata or {},
            )
        )

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
                    metadata={
                        "mission_event_type_hash": stable_hash(event.event_type),
                        "mission_event_family": _mission_event_family(event.event_type),
                        "redaction_detected": True,
                    },
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
        "worker_spawn_requested": TelemetryEventKind.WORKER_SPAWN_REQUESTED,
        "worker_spawn_blocked": TelemetryEventKind.WORKER_SPAWN_BLOCKED,
        "worker_started": TelemetryEventKind.WORKER_STARTED,
        "worker_completed": TelemetryEventKind.WORKER_COMPLETED,
        "worker_failed": TelemetryEventKind.WORKER_FAILED,
        "worker_killed": TelemetryEventKind.WORKER_KILLED,
        "worker_timeout": TelemetryEventKind.WORKER_TIMEOUT,
        "worker_budget_exhausted": TelemetryEventKind.WORKER_BUDGET_EXHAUSTED,
        "worker_authority_derived": TelemetryEventKind.WORKER_AUTHORITY_DERIVED,
        "worker_authority_rejected": TelemetryEventKind.WORKER_AUTHORITY_REJECTED,
        "worker_result_submitted": TelemetryEventKind.WORKER_RESULT_SUBMITTED,
        "worker_result_merged": TelemetryEventKind.WORKER_RESULT_MERGED,
        "worker_result_rejected": TelemetryEventKind.WORKER_RESULT_REJECTED,
        "worker_conflict_detected": TelemetryEventKind.WORKER_CONFLICT_DETECTED,
        "daemon_queue_enqueued": TelemetryEventKind.MISSION_QUEUED,
        "daemon_started": TelemetryEventKind.DAEMON_STARTED,
        "daemon_stopped": TelemetryEventKind.DAEMON_STOPPED,
        "daemon_tick_started": TelemetryEventKind.DAEMON_TICK_STARTED,
        "daemon_tick_completed": TelemetryEventKind.DAEMON_TICK_COMPLETED,
        "daemon_tick_failed": TelemetryEventKind.DAEMON_TICK_FAILED,
        "daemon_lease_claimed": TelemetryEventKind.DAEMON_LEASE_CLAIMED,
        "daemon_lease_rejected": TelemetryEventKind.DAEMON_LEASE_REJECTED,
        "daemon_lease_renewed": TelemetryEventKind.DAEMON_LEASE_RENEWED,
        "daemon_lease_expired": TelemetryEventKind.DAEMON_LEASE_EXPIRED,
        "daemon_lease_released": TelemetryEventKind.DAEMON_LEASE_RELEASED,
        "daemon_heartbeat_emitted": TelemetryEventKind.DAEMON_HEARTBEAT_EMITTED,
        "daemon_heartbeat_missed": TelemetryEventKind.DAEMON_HEARTBEAT_MISSED,
        "daemon_recovery_started": TelemetryEventKind.DAEMON_RECOVERY_STARTED,
        "daemon_recovery_completed": TelemetryEventKind.DAEMON_RECOVERY_COMPLETED,
        "daemon_recovery_failed": TelemetryEventKind.DAEMON_RECOVERY_FAILED,
        "daemon_dead_letter_created": TelemetryEventKind.DAEMON_DEAD_LETTER_CREATED,
        "scheduler_trigger_evaluated": TelemetryEventKind.SCHEDULER_TRIGGER_EVALUATED,
        "scheduler_proposal_created": TelemetryEventKind.SCHEDULER_PROPOSAL_CREATED,
        "scheduler_proposal_rejected": TelemetryEventKind.SCHEDULER_PROPOSAL_REJECTED,
        "operator_handoff_created": TelemetryEventKind.OPERATOR_HANDOFF_CREATED,
        "operator_notification_created": TelemetryEventKind.OPERATOR_NOTIFICATION_CREATED,
        "harness_session_started": TelemetryEventKind.HARNESS_SESSION_STARTED,
        "harness_session_completed": TelemetryEventKind.HARNESS_SESSION_COMPLETED,
        "harness_session_failed": TelemetryEventKind.HARNESS_SESSION_FAILED,
        "harness_context_pack_created": TelemetryEventKind.HARNESS_CONTEXT_PACK_CREATED,
        "harness_context_pack_rejected": TelemetryEventKind.HARNESS_CONTEXT_PACK_REJECTED,
        "harness_artifact_read": TelemetryEventKind.HARNESS_ARTIFACT_READ,
        "harness_edit_proposed": TelemetryEventKind.HARNESS_EDIT_PROPOSED,
        "harness_edit_verified": TelemetryEventKind.HARNESS_EDIT_VERIFIED,
        "harness_edit_rejected": TelemetryEventKind.HARNESS_EDIT_REJECTED,
        "harness_kernel_started": TelemetryEventKind.HARNESS_KERNEL_STARTED,
        "harness_kernel_completed": TelemetryEventKind.HARNESS_KERNEL_COMPLETED,
        "harness_kernel_failed": TelemetryEventKind.HARNESS_KERNEL_FAILED,
        "harness_tool_output_minimized": TelemetryEventKind.HARNESS_TOOL_OUTPUT_MINIMIZED,
        "harness_worker_requested": TelemetryEventKind.HARNESS_WORKER_REQUESTED,
        "harness_worker_completed": TelemetryEventKind.HARNESS_WORKER_COMPLETED,
        "harness_worker_rejected": TelemetryEventKind.HARNESS_WORKER_REJECTED,
        "harness_conflict_detected": TelemetryEventKind.HARNESS_CONFLICT_DETECTED,
        "harness_merge_completed": TelemetryEventKind.HARNESS_MERGE_COMPLETED,
        "harness_merge_rejected": TelemetryEventKind.HARNESS_MERGE_REJECTED,
        "skill_manifest_registered": TelemetryEventKind.SKILL_MANIFEST_REGISTERED,
        "skill_manifest_rejected": TelemetryEventKind.SKILL_MANIFEST_REJECTED,
        "skill_scan_started": TelemetryEventKind.SKILL_SCAN_STARTED,
        "skill_scan_completed": TelemetryEventKind.SKILL_SCAN_COMPLETED,
        "skill_quarantined": TelemetryEventKind.SKILL_QUARANTINED,
        "skill_evaluation_started": TelemetryEventKind.SKILL_EVALUATION_STARTED,
        "skill_evaluation_completed": TelemetryEventKind.SKILL_EVALUATION_COMPLETED,
        "skill_approved": TelemetryEventKind.SKILL_APPROVED,
        "skill_promoted": TelemetryEventKind.SKILL_PROMOTED,
        "skill_revoked": TelemetryEventKind.SKILL_REVOKED,
        "skill_execution_requested": TelemetryEventKind.SKILL_EXECUTION_REQUESTED,
        "skill_execution_blocked": TelemetryEventKind.SKILL_EXECUTION_BLOCKED,
        "skill_execution_started": TelemetryEventKind.SKILL_EXECUTION_STARTED,
        "skill_execution_completed": TelemetryEventKind.SKILL_EXECUTION_COMPLETED,
        "skill_execution_failed": TelemetryEventKind.SKILL_EXECUTION_FAILED,
        "procedure_step_started": TelemetryEventKind.PROCEDURE_STEP_STARTED,
        "procedure_step_completed": TelemetryEventKind.PROCEDURE_STEP_COMPLETED,
        "procedure_step_failed": TelemetryEventKind.PROCEDURE_STEP_FAILED,
        "procedure_rollback_required": TelemetryEventKind.PROCEDURE_ROLLBACK_REQUIRED,
        "procedure_replay_built": TelemetryEventKind.PROCEDURE_REPLAY_BUILT,
        "model_router_candidate_registered": TelemetryEventKind.MODEL_ROUTER_CANDIDATE_REGISTERED,
        "model_router_candidate_rejected": TelemetryEventKind.MODEL_ROUTER_CANDIDATE_REJECTED,
        "model_router_hardware_snapshot_created": TelemetryEventKind.MODEL_ROUTER_HARDWARE_SNAPSHOT_CREATED,
        "model_router_runtime_probe_started": TelemetryEventKind.MODEL_ROUTER_RUNTIME_PROBE_STARTED,
        "model_router_runtime_probe_completed": TelemetryEventKind.MODEL_ROUTER_RUNTIME_PROBE_COMPLETED,
        "model_router_simulation_started": TelemetryEventKind.MODEL_ROUTER_SIMULATION_STARTED,
        "model_router_simulation_completed": TelemetryEventKind.MODEL_ROUTER_SIMULATION_COMPLETED,
        "model_router_decision_created": TelemetryEventKind.MODEL_ROUTER_DECISION_CREATED,
        "model_router_decision_rejected": TelemetryEventKind.MODEL_ROUTER_DECISION_REJECTED,
        "model_router_approval_recorded": TelemetryEventKind.MODEL_ROUTER_APPROVAL_RECORDED,
        "model_router_binding_created": TelemetryEventKind.MODEL_ROUTER_BINDING_CREATED,
        "model_router_binding_rejected": TelemetryEventKind.MODEL_ROUTER_BINDING_REJECTED,
        "model_router_fallback_blocked": TelemetryEventKind.MODEL_ROUTER_FALLBACK_BLOCKED,
        "model_router_policy_rejected": TelemetryEventKind.MODEL_ROUTER_POLICY_REJECTED,
        "channel_adapter_registered": TelemetryEventKind.CHANNEL_ADAPTER_REGISTERED,
        "channel_adapter_rejected": TelemetryEventKind.CHANNEL_ADAPTER_REJECTED,
        "channel_inbound_received": TelemetryEventKind.CHANNEL_INBOUND_RECEIVED,
        "channel_inbound_quarantined": TelemetryEventKind.CHANNEL_INBOUND_QUARANTINED,
        "channel_identity_bound": TelemetryEventKind.CHANNEL_IDENTITY_BOUND,
        "channel_outbound_draft_created": TelemetryEventKind.CHANNEL_OUTBOUND_DRAFT_CREATED,
        "channel_outbound_approval_recorded": TelemetryEventKind.CHANNEL_OUTBOUND_APPROVAL_RECORDED,
        "channel_outbound_send_requested": TelemetryEventKind.CHANNEL_OUTBOUND_SEND_REQUESTED,
        "channel_outbound_send_blocked": TelemetryEventKind.CHANNEL_OUTBOUND_SEND_BLOCKED,
        "channel_outbound_sent": TelemetryEventKind.CHANNEL_OUTBOUND_SENT,
        "channel_outbound_failed": TelemetryEventKind.CHANNEL_OUTBOUND_FAILED,
        "channel_duplicate_send_blocked": TelemetryEventKind.CHANNEL_DUPLICATE_SEND_BLOCKED,
        "channel_revocation_detected": TelemetryEventKind.CHANNEL_REVOCATION_DETECTED,
        "channel_kill_switch_triggered": TelemetryEventKind.CHANNEL_KILL_SWITCH_TRIGGERED,
        "channel_replay_built": TelemetryEventKind.CHANNEL_REPLAY_BUILT,
        "desktop_sidecar_registered": TelemetryEventKind.DESKTOP_SIDECAR_REGISTERED,
        "desktop_sidecar_rejected": TelemetryEventKind.DESKTOP_SIDECAR_REJECTED,
        "desktop_observation_requested": TelemetryEventKind.DESKTOP_OBSERVATION_REQUESTED,
        "desktop_observation_blocked": TelemetryEventKind.DESKTOP_OBSERVATION_BLOCKED,
        "desktop_observation_completed": TelemetryEventKind.DESKTOP_OBSERVATION_COMPLETED,
        "desktop_screenshot_captured": TelemetryEventKind.DESKTOP_SCREENSHOT_CAPTURED,
        "desktop_screenshot_redacted": TelemetryEventKind.DESKTOP_SCREENSHOT_REDACTED,
        "desktop_sensitive_region_detected": TelemetryEventKind.DESKTOP_SENSITIVE_REGION_DETECTED,
        "desktop_grounding_requested": TelemetryEventKind.DESKTOP_GROUNDING_REQUESTED,
        "desktop_grounding_completed": TelemetryEventKind.DESKTOP_GROUNDING_COMPLETED,
        "desktop_grounding_failed": TelemetryEventKind.DESKTOP_GROUNDING_FAILED,
        "desktop_action_proposed": TelemetryEventKind.DESKTOP_ACTION_PROPOSED,
        "desktop_action_preview_created": TelemetryEventKind.DESKTOP_ACTION_PREVIEW_CREATED,
        "desktop_action_approval_required": TelemetryEventKind.DESKTOP_ACTION_APPROVAL_REQUIRED,
        "desktop_action_approved": TelemetryEventKind.DESKTOP_ACTION_APPROVED,
        "desktop_action_blocked": TelemetryEventKind.DESKTOP_ACTION_BLOCKED,
        "desktop_action_started": TelemetryEventKind.DESKTOP_ACTION_STARTED,
        "desktop_action_completed": TelemetryEventKind.DESKTOP_ACTION_COMPLETED,
        "desktop_action_failed": TelemetryEventKind.DESKTOP_ACTION_FAILED,
        "desktop_kill_switch_triggered": TelemetryEventKind.DESKTOP_KILL_SWITCH_TRIGGERED,
        "desktop_revocation_detected": TelemetryEventKind.DESKTOP_REVOCATION_DETECTED,
        "desktop_replay_built": TelemetryEventKind.DESKTOP_REPLAY_BUILT,
        "live_desktop_backend_registered": TelemetryEventKind.LIVE_DESKTOP_BACKEND_REGISTERED,
        "live_desktop_backend_rejected": TelemetryEventKind.LIVE_DESKTOP_BACKEND_REJECTED,
        "desktop_operator_session_started": TelemetryEventKind.DESKTOP_OPERATOR_SESSION_STARTED,
        "desktop_operator_session_completed": TelemetryEventKind.DESKTOP_OPERATOR_SESSION_COMPLETED,
        "desktop_operator_session_failed": TelemetryEventKind.DESKTOP_OPERATOR_SESSION_FAILED,
        "desktop_operator_mode_changed": TelemetryEventKind.DESKTOP_OPERATOR_MODE_CHANGED,
        "desktop_system_snapshot_requested": TelemetryEventKind.DESKTOP_SYSTEM_SNAPSHOT_REQUESTED,
        "desktop_system_snapshot_completed": TelemetryEventKind.DESKTOP_SYSTEM_SNAPSHOT_COMPLETED,
        "desktop_system_snapshot_blocked": TelemetryEventKind.DESKTOP_SYSTEM_SNAPSHOT_BLOCKED,
        "desktop_monitoring_session_started": TelemetryEventKind.DESKTOP_MONITORING_SESSION_STARTED,
        "desktop_monitoring_tick_completed": TelemetryEventKind.DESKTOP_MONITORING_TICK_COMPLETED,
        "desktop_monitoring_session_stopped": TelemetryEventKind.DESKTOP_MONITORING_SESSION_STOPPED,
        "desktop_process_snapshot_created": TelemetryEventKind.DESKTOP_PROCESS_SNAPSHOT_CREATED,
        "desktop_window_snapshot_created": TelemetryEventKind.DESKTOP_WINDOW_SNAPSHOT_CREATED,
        "desktop_hardware_metric_snapshot_created": TelemetryEventKind.DESKTOP_HARDWARE_METRIC_SNAPSHOT_CREATED,
        "desktop_live_action_planned": TelemetryEventKind.DESKTOP_LIVE_ACTION_PLANNED,
        "desktop_live_action_blocked": TelemetryEventKind.DESKTOP_LIVE_ACTION_BLOCKED,
        "desktop_live_action_started": TelemetryEventKind.DESKTOP_LIVE_ACTION_STARTED,
        "desktop_live_action_completed": TelemetryEventKind.DESKTOP_LIVE_ACTION_COMPLETED,
        "desktop_live_action_failed": TelemetryEventKind.DESKTOP_LIVE_ACTION_FAILED,
        "desktop_live_action_kill_blocked": TelemetryEventKind.DESKTOP_LIVE_ACTION_KILL_BLOCKED,
        "desktop_benchmark_started": TelemetryEventKind.DESKTOP_BENCHMARK_STARTED,
        "desktop_benchmark_completed": TelemetryEventKind.DESKTOP_BENCHMARK_COMPLETED,
        "desktop_benchmark_failed": TelemetryEventKind.DESKTOP_BENCHMARK_FAILED,
        "desktop_service_shape_created": TelemetryEventKind.DESKTOP_SERVICE_SHAPE_CREATED,
        "desktop_tray_shape_created": TelemetryEventKind.DESKTOP_TRAY_SHAPE_CREATED,
    }
    return mapping.get(event_type, TelemetryEventKind.ORGAN_CALLED)


def _mission_event_family(event_type: str) -> str:
    if event_type.startswith("desktop_"):
        return "desktop_sidecar"
    if event_type.startswith("live_desktop_"):
        return "desktop_sidecar"
    if event_type.startswith("channel_"):
        return "channel_adapter"
    if event_type.startswith("model_router_"):
        return "model_router"
    if event_type.startswith("skill_") or event_type.startswith("procedure_"):
        return "skill_fabric"
    if event_type.startswith("harness_"):
        return "amplification_harness"
    if event_type.startswith("worker_"):
        return "worker_fleet"
    if event_type.startswith("daemon_") or event_type.startswith("scheduler_"):
        return "mission_daemon"
    if event_type.startswith("workflow_"):
        return "workflow"
    if event_type.startswith("mission_"):
        return "mission"
    return "mission_store"


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
    if event_kind in {
        TelemetryEventKind.WORKER_SPAWN_REQUESTED,
        TelemetryEventKind.WORKER_SPAWN_BLOCKED,
        TelemetryEventKind.WORKER_STARTED,
        TelemetryEventKind.WORKER_COMPLETED,
        TelemetryEventKind.WORKER_FAILED,
        TelemetryEventKind.WORKER_KILLED,
        TelemetryEventKind.WORKER_TIMEOUT,
        TelemetryEventKind.WORKER_BUDGET_EXHAUSTED,
        TelemetryEventKind.WORKER_AUTHORITY_DERIVED,
        TelemetryEventKind.WORKER_AUTHORITY_REJECTED,
        TelemetryEventKind.WORKER_RESULT_SUBMITTED,
        TelemetryEventKind.WORKER_RESULT_MERGED,
        TelemetryEventKind.WORKER_RESULT_REJECTED,
        TelemetryEventKind.WORKER_CONFLICT_DETECTED,
    }:
        return TelemetryDomain.WORKER
    if event_kind in {
        TelemetryEventKind.DAEMON_STARTED,
        TelemetryEventKind.DAEMON_STOPPED,
        TelemetryEventKind.DAEMON_TICK_STARTED,
        TelemetryEventKind.DAEMON_TICK_COMPLETED,
        TelemetryEventKind.DAEMON_TICK_FAILED,
        TelemetryEventKind.DAEMON_LEASE_CLAIMED,
        TelemetryEventKind.DAEMON_LEASE_REJECTED,
        TelemetryEventKind.DAEMON_LEASE_RENEWED,
        TelemetryEventKind.DAEMON_LEASE_EXPIRED,
        TelemetryEventKind.DAEMON_LEASE_RELEASED,
        TelemetryEventKind.DAEMON_HEARTBEAT_EMITTED,
        TelemetryEventKind.DAEMON_HEARTBEAT_MISSED,
        TelemetryEventKind.DAEMON_RECOVERY_STARTED,
        TelemetryEventKind.DAEMON_RECOVERY_COMPLETED,
        TelemetryEventKind.DAEMON_RECOVERY_FAILED,
        TelemetryEventKind.DAEMON_DEAD_LETTER_CREATED,
        TelemetryEventKind.SCHEDULER_TRIGGER_EVALUATED,
        TelemetryEventKind.SCHEDULER_PROPOSAL_CREATED,
        TelemetryEventKind.SCHEDULER_PROPOSAL_REJECTED,
        TelemetryEventKind.OPERATOR_HANDOFF_CREATED,
        TelemetryEventKind.OPERATOR_NOTIFICATION_CREATED,
    }:
        return TelemetryDomain.OPERATIONAL
    if event_kind in {
        TelemetryEventKind.HARNESS_SESSION_STARTED,
        TelemetryEventKind.HARNESS_SESSION_COMPLETED,
        TelemetryEventKind.HARNESS_SESSION_FAILED,
        TelemetryEventKind.HARNESS_CONTEXT_PACK_CREATED,
        TelemetryEventKind.HARNESS_CONTEXT_PACK_REJECTED,
        TelemetryEventKind.HARNESS_ARTIFACT_READ,
        TelemetryEventKind.HARNESS_EDIT_PROPOSED,
        TelemetryEventKind.HARNESS_EDIT_VERIFIED,
        TelemetryEventKind.HARNESS_EDIT_REJECTED,
        TelemetryEventKind.HARNESS_KERNEL_STARTED,
        TelemetryEventKind.HARNESS_KERNEL_COMPLETED,
        TelemetryEventKind.HARNESS_KERNEL_FAILED,
        TelemetryEventKind.HARNESS_TOOL_OUTPUT_MINIMIZED,
        TelemetryEventKind.HARNESS_WORKER_REQUESTED,
        TelemetryEventKind.HARNESS_WORKER_COMPLETED,
        TelemetryEventKind.HARNESS_WORKER_REJECTED,
        TelemetryEventKind.HARNESS_CONFLICT_DETECTED,
        TelemetryEventKind.HARNESS_MERGE_COMPLETED,
        TelemetryEventKind.HARNESS_MERGE_REJECTED,
        TelemetryEventKind.SKILL_MANIFEST_REGISTERED,
        TelemetryEventKind.SKILL_MANIFEST_REJECTED,
        TelemetryEventKind.SKILL_SCAN_STARTED,
        TelemetryEventKind.SKILL_SCAN_COMPLETED,
        TelemetryEventKind.SKILL_QUARANTINED,
        TelemetryEventKind.SKILL_EVALUATION_STARTED,
        TelemetryEventKind.SKILL_EVALUATION_COMPLETED,
        TelemetryEventKind.SKILL_APPROVED,
        TelemetryEventKind.SKILL_PROMOTED,
        TelemetryEventKind.SKILL_REVOKED,
        TelemetryEventKind.SKILL_EXECUTION_REQUESTED,
        TelemetryEventKind.SKILL_EXECUTION_BLOCKED,
        TelemetryEventKind.SKILL_EXECUTION_STARTED,
        TelemetryEventKind.SKILL_EXECUTION_COMPLETED,
        TelemetryEventKind.SKILL_EXECUTION_FAILED,
        TelemetryEventKind.PROCEDURE_STEP_STARTED,
        TelemetryEventKind.PROCEDURE_STEP_COMPLETED,
        TelemetryEventKind.PROCEDURE_STEP_FAILED,
        TelemetryEventKind.PROCEDURE_ROLLBACK_REQUIRED,
        TelemetryEventKind.PROCEDURE_REPLAY_BUILT,
        TelemetryEventKind.MODEL_ROUTER_CANDIDATE_REGISTERED,
        TelemetryEventKind.MODEL_ROUTER_CANDIDATE_REJECTED,
        TelemetryEventKind.MODEL_ROUTER_HARDWARE_SNAPSHOT_CREATED,
        TelemetryEventKind.MODEL_ROUTER_RUNTIME_PROBE_STARTED,
        TelemetryEventKind.MODEL_ROUTER_RUNTIME_PROBE_COMPLETED,
        TelemetryEventKind.MODEL_ROUTER_SIMULATION_STARTED,
        TelemetryEventKind.MODEL_ROUTER_SIMULATION_COMPLETED,
        TelemetryEventKind.MODEL_ROUTER_DECISION_CREATED,
        TelemetryEventKind.MODEL_ROUTER_DECISION_REJECTED,
        TelemetryEventKind.MODEL_ROUTER_APPROVAL_RECORDED,
        TelemetryEventKind.MODEL_ROUTER_BINDING_CREATED,
        TelemetryEventKind.MODEL_ROUTER_BINDING_REJECTED,
        TelemetryEventKind.MODEL_ROUTER_FALLBACK_BLOCKED,
        TelemetryEventKind.MODEL_ROUTER_POLICY_REJECTED,
    }:
        return TelemetryDomain.PRODUCT_POWER
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
