from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.operator.redaction import sanitize_operator_refs
from sentinel.shared.models import SentinelModel


class OperatorAgentRuntimeBridgeResult(SentinelModel):
    status: str
    blocked_reason: str | None = None
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    replan_ready: bool = False
    replan_packet_ref: str | None = None
    automatic_replan_executed: bool = False
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
    ) -> None:
        self._kernel = kernel
        self._runtime = runtime
        self._telemetry_sink = telemetry_sink or getattr(kernel, "telemetry_sink", None)

    def run(
        self,
        mission_id: str,
        *,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
        update_mission_status: bool = True,
    ) -> OperatorAgentRuntimeBridgeResult:
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
        if self._runtime is None:
            self._kernel.update_status(mission_id, OperatorMissionStatus.BLOCKED, "AgentRuntime bridge blocked: missing runtime.")
            self._kernel.store.append_event(
                mission_id,
                event_type="agentruntime_blocked",
                safe_summary="AgentRuntime bridge blocked because no runtime was explicitly configured.",
                metadata={"blocked_reason": "missing_agentruntime"},
            )
            return OperatorAgentRuntimeBridgeResult(status="blocked", blocked_reason="missing_agentruntime")

        runtime_result = self._runtime.run(envelope, user_input)
        finalgate_refs = _finalgate_refs(runtime_result)
        memory_refs = _memory_refs(runtime_result)
        receipt_refs = _receipt_refs(runtime_result)
        status = "completed" if bool(getattr(runtime_result, "success", False)) else "blocked"
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
            },
        )
        if self._telemetry_sink is not None and hasattr(self._telemetry_sink, "record_agentruntime_result"):
            self._telemetry_sink.record_agentruntime_result(mission_id, runtime_result)
        return OperatorAgentRuntimeBridgeResult(
            status=status,
            receipt_refs=receipt_refs,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
            replan_ready=bool(getattr(runtime_result, "replan_ready", False)),
            replan_packet_ref=replan_packet_ref,
        )


def _finalgate_refs(runtime_result: Any) -> list[str]:
    cert = getattr(runtime_result, "final_gate_certification", None)
    cert_id = getattr(cert, "id", None)
    return sanitize_operator_refs([cert_id] if cert_id else [])


def _memory_refs(runtime_result: Any) -> list[str]:
    memory = getattr(runtime_result, "memory_feedback_result", None)
    refs = getattr(memory, "memory_entry_refs", None)
    return sanitize_operator_refs(refs)


def _receipt_refs(runtime_result: Any) -> list[str]:
    refs = getattr(runtime_result, "receipt_refs", None)
    return sanitize_operator_refs(refs)
