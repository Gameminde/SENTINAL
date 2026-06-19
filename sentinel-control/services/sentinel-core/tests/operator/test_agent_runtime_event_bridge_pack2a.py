from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sentinel.agent import AgentEventType, AgentPhase
from sentinel.agent.event_bus import EventBus
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import OperatorAgentRuntimeBridge
from sentinel.operator.agent_event_bridge import AgentEventBridgePersistenceError
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.replay import MissionReplayBuilder
from sentinel.shared.enums import MissionMode, MissionType
from sentinel.shared.execution_events import AgentExecutionEvent, AgentExecutionEventKind


def test_agent_runtime_events_project_to_mission_store_in_source_order(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = DeterministicEventRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe", "raw_prompt": "do not persist this"},
        execution_request_id="mission_exec_req_pack2a",
        update_mission_status=False,
    )

    assert result.status == "completed"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.RUNNING
    projected = _projected_events(kernel, mission_id)
    kinds = [event.metadata["event_kind"] for event in projected]
    assert kinds == [
        AgentExecutionEventKind.RUNTIME_STARTED.value,
        AgentExecutionEventKind.PHASE_TRANSITION.value,
        AgentExecutionEventKind.RECEIPT_REFS_UPDATED.value,
        AgentExecutionEventKind.RUNTIME_COMPLETED.value,
    ]
    assert projected[0].sequence < projected[-1].sequence
    assert projected[0].metadata["mission_id"] == mission_id
    assert projected[0].metadata["run_id"] == kernel.store.load_record(mission_id).session_id
    assert projected[0].metadata["execution_request_id"] == "mission_exec_req_pack2a"
    assert projected[0].metadata["bridge_call_id"].startswith("agent_bridge_call_")
    assert projected[0].metadata["agent_run_id"].startswith("agent_run_")
    assert projected[1].metadata["phase_before"] == AgentPhase.INITIALIZED.value
    assert projected[1].metadata["phase_after"] == AgentPhase.EXECUTING.value
    assert projected[2].receipt_refs == ["receipt:agent"]
    assert projected[3].metadata["source_event_id"] == runtime.events[-1].id
    assert projected[3].metadata["source_event_hash"] == runtime.events[-1].event_hash
    serialized = "\n".join(event.model_dump_json() for event in projected)
    assert "raw_prompt" not in serialized
    assert "raw provider" not in serialized.lower()
    assert "reasoning" not in serialized.lower()
    assert runtime.event_bus is not None
    assert runtime.event_bus.verify_chain() is True


def test_agent_failed_projection_does_not_fabricate_product_success(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorAgentRuntimeBridge(kernel, runtime=DeterministicEventRuntime(final_kind="failed")).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "agentruntime_reported_failure"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED
    projected = _projected_events(kernel, mission_id)
    terminal = [event for event in projected if event.metadata["terminal"] is True]
    assert len(terminal) == 1
    assert terminal[0].metadata["event_kind"] == AgentExecutionEventKind.RUNTIME_FAILED.value
    assert "accepted" not in terminal[0].event_type.lower()


def test_agent_event_after_terminal_blocks_bridge_and_is_not_projected(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorAgentRuntimeBridge(kernel, runtime=DeterministicEventRuntime(emit_after_terminal=True)).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "AGENT_EVENT_SPINE_PERSISTENCE_FAILED"
    projected = _projected_events(kernel, mission_id)
    terminal = [event for event in projected if event.metadata["terminal"] is True]
    assert len(terminal) == 1
    assert all(event.metadata["event_kind"] != AgentExecutionEventKind.PHASE_TRANSITION.value for event in projected[projected.index(terminal[0]) + 1 :])


def test_duplicate_and_cross_mission_agent_events_are_rejected(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    duplicate = OperatorAgentRuntimeBridge(kernel, runtime=DeterministicEventRuntime(duplicate_source=True)).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )
    assert duplicate.status == "blocked"
    assert duplicate.blocked_reason == "AGENT_EVENT_SPINE_PERSISTENCE_FAILED"

    kernel2, mission_id2 = _kernel_with_mission(tmp_path / "second")
    cross = OperatorAgentRuntimeBridge(kernel2, runtime=DeterministicEventRuntime(cross_mission=True)).run(
        mission_id2,
        envelope=_envelope(mission_id2),
        user_input={},
    )
    assert cross.status == "blocked"
    assert cross.blocked_reason == "AGENT_EVENT_SPINE_PERSISTENCE_FAILED"


def test_critical_event_persistence_failure_blocks_safely(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    original_append = kernel.store.append_event

    def failing_append_event(mission_id_arg: str, *args: Any, **kwargs: Any):  # noqa: ANN401
        event_type = kwargs.get("event_type") if "event_type" in kwargs else args[0]
        if event_type == "agentruntime_execution_event_observed":
            raise OSError("raw persistence failure must not persist")
        return original_append(mission_id_arg, *args, **kwargs)

    monkeypatch.setattr(kernel.store, "append_event", failing_append_event)

    result = OperatorAgentRuntimeBridge(kernel, runtime=DeterministicEventRuntime()).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "AGENT_EVENT_SPINE_PERSISTENCE_FAILED"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED
    event_payload = "\n".join(event.model_dump_json() for event in kernel.store.load_events(mission_id))
    assert "raw persistence failure" not in event_payload


def test_replay_reads_projected_events_without_reexecuting_agent_runtime(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = DeterministicEventRuntime()

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
        update_mission_status=False,
    )
    call_count = runtime.call_count
    event_count = len(kernel.store.load_events(mission_id))

    replay = MissionReplayBuilder(kernel.store).build(mission_id)

    assert replay.mission_id == mission_id
    assert runtime.call_count == call_count
    assert len(kernel.store.load_events(mission_id)) == event_count


class DeterministicEventRuntime:
    def __init__(
        self,
        *,
        final_kind: str = "completed",
        emit_after_terminal: bool = False,
        duplicate_source: bool = False,
        cross_mission: bool = False,
    ) -> None:
        self.final_kind = final_kind
        self.emit_after_terminal = emit_after_terminal
        self.duplicate_source = duplicate_source
        self.cross_mission = cross_mission
        self.call_count = 0
        self.events = []
        self.event_bus: EventBus | None = None

    def run(
        self,
        envelope: MissionAuthorityEnvelope,
        user_input: dict[str, Any],
        *,
        execution_event_sink=None,
        execution_run_id: str,
        execution_request_id: str | None,
        bridge_call_id: str,
        agent_run_id: str,
    ):
        self.call_count += 1
        bus_mission_id = f"{envelope.id}_other" if self.cross_mission else envelope.id
        bus = EventBus(
            bus_mission_id,
            execution_event_sink=execution_event_sink,
            execution_run_id=execution_run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
        )
        self.event_bus = bus
        started = bus.append(
            AgentEventType.AGENT_INITIALIZED,
            "Agent runtime initialized with safe summary only.",
            phase_before=AgentPhase.CREATED,
            phase_after=AgentPhase.INITIALIZED,
            payload={"raw_prompt": "must stay out of operator projection", "reasoning": "must not persist"},
        )
        bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
            "Agent entered execution phase.",
            phase_before=AgentPhase.INITIALIZED,
            phase_after=AgentPhase.EXECUTING,
            trace_refs=["evidence:agent"],
        )
        bus.append(
            AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
            "Agent recorded safe receipt ref.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            trace_refs=["receipt:agent"],
        )
        if self.duplicate_source and execution_event_sink is not None:
            execution_event_sink.emit(
                AgentExecutionEvent.from_agent_event(
                    started,
                    run_id=execution_run_id,
                    execution_request_id=execution_request_id,
                    bridge_call_id=bridge_call_id,
                    agent_run_id=agent_run_id,
                )
            )
        if self.final_kind == "failed":
            final_event_type = AgentEventType.AGENT_FAILED
            final_phase = AgentPhase.FAILED
            success = False
            finalgate = SimpleNamespace(id="finalgate:agent_blocked", accepted=False)
        else:
            final_event_type = AgentEventType.AGENT_COMPLETED
            final_phase = AgentPhase.COMPLETED
            success = True
            finalgate = SimpleNamespace(id="finalgate:agent", accepted=True)
        bus.append(
            final_event_type,
            "Agent run terminal event.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=final_phase,
            payload={"success": success},
        )
        if self.emit_after_terminal:
            bus.append(
                AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
                "Late event after terminal must not project.",
                phase_before=final_phase,
                phase_after=AgentPhase.EXECUTING,
            )
        self.events = list(bus.events())
        return SimpleNamespace(
            success=success,
            final_phase=final_phase,
            final_gate_certification=finalgate,
            memory_feedback_result=SimpleNamespace(memory_entry_refs=[]),
            receipt_refs=["receipt:agent"] if success else [],
            artifact_paths=[],
        )


def _projected_events(kernel: MissionKernel, mission_id: str):
    return [
        event
        for event in kernel.store.load_events(mission_id)
        if event.event_type == "agentruntime_execution_event_observed"
    ]


def _kernel_with_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_agent",
        draft=MissionDraft(title="Agent bridge", objective="Use AgentRuntime public API."),
    )
    kernel.enqueue(record.mission_id)
    return kernel, record.mission_id


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="operator_user",
        mission_type=MissionType.GTM,
        mission_title="Operator agent bridge",
        mission_objective="Run through public AgentRuntime API.",
        success_criteria=["safe result"],
        mode=MissionMode.SAFE,
        allowed_systems=["local_workspace"],
        allowed_tools=["safe_file_writer"],
        allowed_actions=["generate_research_questions"],
        forbidden_actions=["payment", "send_email", "credential_access"],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=10,
        max_actions=5,
        max_cost_usd=0.01,
    )
