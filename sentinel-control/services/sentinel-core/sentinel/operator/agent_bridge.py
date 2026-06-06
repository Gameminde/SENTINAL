from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import OperatorMissionStatus
from sentinel.shared.models import SentinelModel


class OperatorAgentRuntimeBridgeResult(SentinelModel):
    status: str
    blocked_reason: str | None = None
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False


class OperatorAgentRuntimeBridge:
    def __init__(self, kernel: MissionKernel, *, runtime: Any | None = None) -> None:
        self._kernel = kernel
        self._runtime = runtime

    def run(
        self,
        mission_id: str,
        *,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
    ) -> OperatorAgentRuntimeBridgeResult:
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
        status = "completed" if bool(getattr(runtime_result, "success", False)) else "blocked"
        operator_status = OperatorMissionStatus.COMPLETED if status == "completed" else OperatorMissionStatus.BLOCKED
        self._kernel.update_status(mission_id, operator_status, f"AgentRuntime finished with status {status}.")
        self._kernel.store.append_event(
            mission_id,
            event_type="agentruntime_result",
            safe_summary=f"AgentRuntime result {status}.",
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
        )
        return OperatorAgentRuntimeBridgeResult(
            status=status,
            finalgate_certificate_refs=finalgate_refs,
            memory_feedback_refs=memory_refs,
        )


def _finalgate_refs(runtime_result: Any) -> list[str]:
    cert = getattr(runtime_result, "final_gate_certification", None)
    cert_id = getattr(cert, "id", None)
    return [str(cert_id)] if cert_id else []


def _memory_refs(runtime_result: Any) -> list[str]:
    memory = getattr(runtime_result, "memory_feedback_result", None)
    refs = getattr(memory, "memory_entry_refs", None)
    return [str(ref) for ref in refs] if isinstance(refs, list) else []
