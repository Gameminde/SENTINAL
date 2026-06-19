from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import inspect
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_event_bridge import (
    AGENT_EVENT_SPINE_PERSISTENCE_FAILED,
    AgentEventBridgePersistenceError,
    OperatorAgentEventBridge,
)
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.redaction import sanitize_operator_refs
from sentinel.shared.events import EventBusAppendRejected, EventBusProjectionError
from sentinel.shared.models import SentinelModel, new_id
from sentinel.telemetry import TelemetryCertificationError


AGENT_EVENT_SINK_REQUIRED = "AGENT_EVENT_SINK_REQUIRED"


class AgentEventProjectionMode(StrEnum):
    REQUIRED = "required"
    LEGACY_EXPLICITLY_DISABLED = "legacy_explicitly_disabled"


class OperatorAgentRuntimeBridgeResult(SentinelModel):
    status: str
    blocked_reason: str | None = None
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    replan_ready: bool = False
    replan_packet_ref: str | None = None
    automatic_replan_executed: bool = False
    agent_event_projection_refs: list[str] = Field(default_factory=list)
    agent_event_projection_failure_code: str | None = None
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False


class OperatorAgentRuntimeBridge:
    def __init__(
        self,
        kernel: MissionKernel,
        *,
        runtime: Any | None = None,
        telemetry_sink: object | None = None,
        projection_mode: AgentEventProjectionMode | str = AgentEventProjectionMode.REQUIRED,
    ) -> None:
        self._kernel = kernel
        self._runtime = runtime
        self._telemetry_sink = telemetry_sink or getattr(kernel, "telemetry_sink", None)
        self._projection_mode = AgentEventProjectionMode(projection_mode)

    def run(
        self,
        mission_id: str,
        *,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
        execution_request_id: str | None = None,
        update_mission_status: bool = True,
    ) -> OperatorAgentRuntimeBridgeResult:
        if not self._kernel.store.verify_record(mission_id):
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason="mission_record_tampered")
        if envelope.id != mission_id:
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because mission identity did not match.",
                metadata={"blocked_reason": "mission_identity_mismatch"},
            )
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason="mission_identity_mismatch")
        terminal_reason = self._kernel.terminal_block_reason(mission_id)
        if terminal_reason is not None:
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because operator mission is terminal.",
                metadata={"drop_reason": "mission_closed", "mission_state": terminal_reason.rsplit(":", 1)[-1]},
            )
            return OperatorAgentRuntimeBridgeResult(
                status="blocked",
                blocked_reason="operator_mission_terminal",
            )
        if envelope.revoked_at is not None or datetime.now(UTC) > envelope.resolved_expires_at():
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because mission authority is inactive.",
                metadata={"blocked_reason": "mission_authority_envelope_inactive"},
            )
            return OperatorAgentRuntimeBridgeResult(
                status="blocked",
                blocked_reason="mission_authority_envelope_inactive",
            )
        record = self._kernel.store.load_record(mission_id)
        if record.status not in {OperatorMissionStatus.QUEUED, OperatorMissionStatus.RUNNING}:
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because mission is not executable.",
                metadata={"blocked_reason": "operator_mission_not_executable", "mission_state": record.status.value},
            )
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason="operator_mission_not_executable")
        if not _require_material_telemetry(self._telemetry_sink, "agentruntime_bridge"):
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because certified telemetry is unavailable.",
                metadata={"blocked_reason": "telemetry_certified_mode_required"},
            )
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason="telemetry_certified_mode_required")
        if self._runtime is None:
            self._kernel.update_status(mission_id, OperatorMissionStatus.BLOCKED, "AgentRuntime bridge blocked: missing runtime.")
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because no runtime was explicitly configured.",
                metadata={"blocked_reason": "missing_agentruntime"},
            )
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason="missing_agentruntime")
        runtime_accepts_sink = _runtime_accepts_execution_event_sink(self._runtime)
        if self._projection_mode is AgentEventProjectionMode.REQUIRED and not runtime_accepts_sink:
            if update_mission_status:
                self._kernel.update_status(
                    mission_id,
                    OperatorMissionStatus.BLOCKED,
                    "AgentRuntime bridge blocked: execution event sink required.",
                )
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because governed routes require event projection.",
                metadata={
                    "blocked_reason": AGENT_EVENT_SINK_REQUIRED,
                    "projection_mode": self._projection_mode.value,
                },
            )
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason=AGENT_EVENT_SINK_REQUIRED)

        if record.status is OperatorMissionStatus.QUEUED:
            self._kernel.update_status(mission_id, OperatorMissionStatus.RUNNING, "AgentRuntime bridge started mission execution.")
            record = self._kernel.store.load_record(mission_id)
        bridge_call_id = new_id("agent_bridge_call")
        agent_run_id = new_id("agent_run")
        agent_event_bridge = OperatorAgentEventBridge(
            store=self._kernel.store,
            mission_id=mission_id,
            run_id=record.session_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
        )
        try:
            runtime_result = _run_runtime_with_event_projection(
                self._runtime,
                envelope,
                user_input,
                agent_event_bridge=agent_event_bridge,
                projection_mode=self._projection_mode,
                runtime_accepts_sink=runtime_accepts_sink,
                execution_run_id=record.session_id,
                execution_request_id=execution_request_id,
                bridge_call_id=bridge_call_id,
                agent_run_id=agent_run_id,
            )
        except Exception as exc:  # noqa: BLE001
            blocked_reason = (
                exc.code
                if isinstance(exc, AgentEventBridgePersistenceError)
                else AGENT_EVENT_SPINE_PERSISTENCE_FAILED
                if isinstance(exc, (EventBusProjectionError, EventBusAppendRejected))
                else "agentruntime_bridge_failure"
            )
            safe_summary = (
                "AgentRuntime event spine persistence failed safely."
                if blocked_reason == AGENT_EVENT_SPINE_PERSISTENCE_FAILED
                else "AgentRuntime bridge contained a runtime failure."
            )
            if update_mission_status:
                self._kernel.update_status(
                    mission_id,
                    OperatorMissionStatus.BLOCKED,
                    "AgentRuntime bridge failed safely.",
                )
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary=safe_summary,
                metadata={
                    "blocked_reason": blocked_reason,
                    "bridge_call_id": bridge_call_id,
                    "agent_run_id": agent_run_id,
                    "agent_event_projection_count": agent_event_bridge.projected_count,
                },
            )
            agent_event_bridge.close()
            return OperatorAgentRuntimeBridgeResult(
                status="blocked",
                blocked_reason=blocked_reason,
                agent_event_projection_refs=list(agent_event_bridge.projected_event_ids),
                agent_event_projection_failure_code=blocked_reason
                if blocked_reason == AGENT_EVENT_SPINE_PERSISTENCE_FAILED
                else None,
            )
        agent_event_bridge.close()
        finalgate_refs = _finalgate_refs(runtime_result)
        memory_refs = _memory_refs(runtime_result)
        receipt_refs = _receipt_refs(runtime_result)
        runtime_success = bool(getattr(runtime_result, "success", False))
        finalgate = getattr(runtime_result, "final_gate_certification", None)
        finalgate_accepted = bool(getattr(finalgate, "accepted", False))
        status = "completed" if runtime_success and finalgate_accepted else "blocked"
        blocked_reason = None
        if status == "blocked":
            blocked_reason = "agentruntime_finalgate_required" if runtime_success else "agentruntime_reported_failure"
        if update_mission_status:
            operator_status = OperatorMissionStatus.COMPLETED if status == "completed" else OperatorMissionStatus.BLOCKED
            self._kernel.update_status(mission_id, operator_status, f"AgentRuntime finished with status {status}.")
        replan_packet = getattr(runtime_result, "replan_packet", None)
        replan_packet_ref = stable_hash(replan_packet) if isinstance(replan_packet, dict) else None
        self._kernel.store.append_event(
            mission_id,
            event_type="agentruntime_result",
            safe_summary=f"AgentRuntime result {status}.",
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
            metadata={
                "replan_ready": bool(getattr(runtime_result, "replan_ready", False)),
                "replan_packet_ref": replan_packet_ref,
                "automatic_replan_executed": False,
                "blocked_reason": blocked_reason,
                "bridge_call_id": bridge_call_id,
                "agent_run_id": agent_run_id,
                "execution_request_id": execution_request_id,
                "agent_event_projection_count": agent_event_bridge.projected_count,
                "agent_event_projection_degraded": False,
                "agent_event_projection_degradation_count": 0,
                "agent_event_projection_degradation_codes": [],
            },
        )
        if self._telemetry_sink is not None and hasattr(self._telemetry_sink, "record_agentruntime_result"):
            self._telemetry_sink.record_agentruntime_result(mission_id, runtime_result)
        return OperatorAgentRuntimeBridgeResult(
            status=status,
            blocked_reason=blocked_reason,
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
            replan_ready=bool(getattr(runtime_result, "replan_ready", False)),
            replan_packet_ref=replan_packet_ref,
            agent_event_projection_refs=list(agent_event_bridge.projected_event_ids),
        )


def _run_runtime_with_event_projection(
    runtime: Any,
    envelope: MissionAuthorityEnvelope,
    user_input: dict[str, Any],
    *,
    agent_event_bridge: OperatorAgentEventBridge,
    projection_mode: AgentEventProjectionMode,
    runtime_accepts_sink: bool,
    execution_run_id: str,
    execution_request_id: str | None,
    bridge_call_id: str,
    agent_run_id: str,
) -> Any:
    if projection_mode is AgentEventProjectionMode.LEGACY_EXPLICITLY_DISABLED:
        return runtime.run(envelope, user_input)
    if not runtime_accepts_sink:
        raise EventBusProjectionError(AGENT_EVENT_SINK_REQUIRED)
    return runtime.run(
        envelope,
        user_input,
        execution_event_sink=agent_event_bridge,
        execution_run_id=execution_run_id,
        execution_request_id=execution_request_id,
        bridge_call_id=bridge_call_id,
        agent_run_id=agent_run_id,
    )


def _runtime_accepts_execution_event_sink(runtime: Any) -> bool:
    try:
        signature = inspect.signature(runtime.run)
    except (TypeError, ValueError):
        return False
    return "execution_event_sink" in signature.parameters


def _finalgate_refs(runtime_result: Any) -> list[str]:
    cert = getattr(runtime_result, "final_gate_certification", None)
    cert_id = getattr(cert, "id", None)
    if cert_id:
        return sanitize_operator_refs([cert_id])
    if not bool(getattr(cert, "accepted", False)):
        return []
    payload = cert.model_dump(mode="json") if hasattr(cert, "model_dump") else cert
    return sanitize_operator_refs([f"finalgate:{stable_hash(payload)}"])


def _memory_refs(runtime_result: Any) -> list[str]:
    memory = getattr(runtime_result, "memory_feedback_result", None)
    refs = getattr(memory, "memory_entry_refs", None)
    return sanitize_operator_refs(refs)


def _receipt_refs(runtime_result: Any) -> list[str]:
    refs = getattr(runtime_result, "receipt_refs", None)
    return sanitize_operator_refs(refs)


def _require_material_telemetry(sink: object | None, operation: str) -> bool:
    if sink is None:
        return True
    try:
        if hasattr(sink, "require_material_execution"):
            sink.require_material_execution(operation)
        elif hasattr(sink, "require_certified_mode"):
            sink.require_certified_mode()
    except TelemetryCertificationError:
        return False
    except Exception:  # noqa: BLE001
        return False
    return True
