from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from sentinel.agent import AgentEventType, AgentPhase, AgentRuntime
from sentinel.agent.event_bus import EventBus
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionConfig, OrganRuntimeExecutionMode
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import AgentEventProjectionMode, OperatorAgentRuntimeBridge
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
        AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED.value,
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
    assert projected[2].metadata["source_event_id"] == runtime.events[-1].id
    assert projected[2].metadata["source_event_hash"] == runtime.events[-1].event_hash
    serialized = "\n".join(event.model_dump_json() for event in projected)
    assert "raw_prompt" not in serialized
    assert "raw provider" not in serialized.lower()
    assert "reasoning" not in serialized.lower()
    assert runtime.event_bus is not None
    assert runtime.event_bus.verify_chain() is True


def test_governed_route_blocks_runtime_without_explicit_event_sink_support(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = NoSinkRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "AGENT_EVENT_SINK_REQUIRED"
    assert runtime.call_count == 0
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_explicit_legacy_mode_is_required_to_execute_without_event_sink(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = NoSinkRuntime()

    result = OperatorAgentRuntimeBridge(
        kernel,
        runtime=runtime,
        projection_mode=AgentEventProjectionMode.LEGACY_EXPLICITLY_DISABLED,
    ).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
        update_mission_status=False,
    )

    assert result.status == "completed"
    assert result.blocked_reason is None
    assert runtime.call_count == 1
    assert result.agent_event_projection_refs == []


def test_var_keyword_runtime_is_not_treated_as_sink_capable(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = VarKeywordRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "AGENT_EVENT_SINK_REQUIRED"
    assert runtime.call_count == 0


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
    runtime = DeterministicEventRuntime(emit_after_terminal=True)

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
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
    assert runtime.event_bus is not None
    source_events = runtime.event_bus.events()
    assert source_events[-1].event_type is AgentEventType.AGENT_COMPLETED


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


def test_event_bus_rejects_source_append_after_terminal_before_mutation() -> None:
    bus = EventBus("mission_terminal_latch")
    bus.append(
        AgentEventType.AGENT_COMPLETED,
        "terminal",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.COMPLETED,
    )
    before_count = len(bus.events())

    with pytest.raises(RuntimeError, match="terminal"):
        bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
            "late",
            phase_before=AgentPhase.COMPLETED,
            phase_after=AgentPhase.EXECUTING,
        )

    assert len(bus.events()) == before_count
    assert bus.events()[-1].event_type is AgentEventType.AGENT_COMPLETED


def test_event_bus_latches_projection_failure_and_rejects_later_source_append() -> None:
    sink = FailingSink()
    bus = EventBus(
        "mission_projection_latch",
        execution_event_sink=sink,
        execution_run_id="run_projection_latch",
        bridge_call_id="bridge_projection_latch",
        agent_run_id="agent_projection_latch",
    )

    with pytest.raises(RuntimeError, match="projection"):
        bus.append(
            AgentEventType.AGENT_INITIALIZED,
            "start",
            phase_before=AgentPhase.CREATED,
            phase_after=AgentPhase.INITIALIZED,
        )
    before_count = len(bus.events())

    with pytest.raises(RuntimeError, match="projection"):
        bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
            "late",
            phase_before=AgentPhase.INITIALIZED,
            phase_after=AgentPhase.EXECUTING,
        )

    assert before_count == 1
    assert len(bus.events()) == before_count


def test_projection_summaries_are_deterministic_and_do_not_copy_source_text() -> None:
    sink = CapturingSink()
    bus = EventBus(
        "mission_summary",
        execution_event_sink=sink,
        execution_run_id="run_summary",
        bridge_call_id="bridge_summary",
        agent_run_id="agent_summary",
    )

    bus.append(
        AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
        "raw_prompt https://example.test C:\\secret\\file.txt provider_response",
        phase_before=AgentPhase.INITIALIZED,
        phase_after=AgentPhase.EXECUTING,
    )

    assert len(sink.events) == 1
    assert sink.events[0].event_kind is AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED
    assert sink.events[0].safe_summary == "Agent runtime controlled capability executed."
    serialized = sink.events[0].model_dump_json()
    assert "raw_prompt" not in serialized
    assert "example.test" not in serialized
    assert "secret" not in serialized.lower()
    assert "provider_response" not in serialized


def test_unsupported_source_event_creates_no_product_projection() -> None:
    sink = CapturingSink()
    bus = EventBus(
        "mission_unsupported",
        execution_event_sink=sink,
        execution_run_id="run_unsupported",
        bridge_call_id="bridge_unsupported",
        agent_run_id="agent_unsupported",
    )

    bus.append(
        AgentEventType.CONTEXT_BUILT,
        "internal context detail must remain source-only",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
    )

    assert len(bus.events()) == 1
    assert sink.events == []


def test_projection_refs_are_bounded_and_sanitized() -> None:
    sink = CapturingSink()
    bus = EventBus(
        "mission_refs",
        execution_event_sink=sink,
        execution_run_id="run_refs",
        bridge_call_id="bridge_refs",
        agent_run_id="agent_refs",
    )

    bus.append(
        AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
        "receipt refs",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
        trace_refs=[
            "receipt:ok",
            "receipt:another",
            "https://example.test/receipt",
            "C:\\secret\\receipt",
            "receipt:contains whitespace",
            "raw_prompt",
            "evidence:ok",
            "evidence:another",
            "evidence:third",
            "evidence:fourth",
            "evidence:fifth",
            "evidence:sixth",
            "evidence:seventh",
            "evidence:eighth",
            "evidence:ninth",
        ],
    )

    assert len(sink.events) == 1
    projected = sink.events[0]
    assert projected.event_kind is AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED
    assert projected.receipt_refs == ["receipt:ok", "receipt:another"]
    assert projected.evidence_refs == [
        "evidence:ok",
        "evidence:another",
        "evidence:third",
        "evidence:fourth",
        "evidence:fifth",
        "evidence:sixth",
        "evidence:seventh",
        "evidence:eighth",
    ]
    serialized = projected.model_dump_json()
    assert "example.test" not in serialized
    assert "secret" not in serialized.lower()
    assert "raw_prompt" not in serialized


def test_every_pack2a_projection_is_truthfully_critical() -> None:
    sink = CapturingSink()
    bus = EventBus(
        "mission_critical",
        execution_event_sink=sink,
        execution_run_id="run_critical",
        bridge_call_id="bridge_critical",
        agent_run_id="agent_critical",
    )

    bus.append(
        AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
        "evidence",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
        trace_refs=["evidence:critical"],
    )

    assert len(sink.events) == 1
    assert sink.events[0].event_kind is AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED
    assert sink.events[0].critical is True


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


def test_pack2b_material_activity_projects_real_emitters_with_source_order(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = MaterialActivityRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
        execution_request_id="mission_exec_req_pack2b_material",
        update_mission_status=False,
    )

    assert result.status == "completed"
    projected = _projected_events(kernel, mission_id)
    kinds = [event.metadata["event_kind"] for event in projected]
    assert kinds == [
        "runtime_started",
        "worker_started",
        "controlled_capability_executed",
        "artifact_captured",
        "runtime_completed",
    ]
    material = projected[1:-1]
    assert [event.metadata["activity_kind"] for event in material] == kinds[1:-1]
    assert [event.metadata["source_sequence"] for event in projected] == sorted(
        event.metadata["source_sequence"] for event in projected
    )
    projected_source_events = [
        event
        for event in runtime.events
        if event.event_type is not AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED
    ]
    assert [event.metadata["source_sequence"] for event in projected] == [
        event.sequence for event in projected_source_events
    ]
    assert all(event.metadata["source_ledger"] == "agent_runtime_event_bus" for event in projected)
    assert projected[2].metadata["capability_refs"] == ["capability:local_file"]
    assert projected[3].metadata["artifact_refs"] == ["artifact:captured"]
    assert all("receipt:organ" not in event.receipt_refs for event in projected)
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.RUNNING
    serialized = "\n".join(event.model_dump_json() for event in projected)
    assert "https://example.test" not in serialized
    assert "C:\\secret" not in serialized
    assert "raw_prompt" not in serialized
    assert "provider_response" not in serialized
    assert "reasoning" not in serialized.lower()


def test_pack2b_material_projection_rejects_nonmonotonic_source_sequence(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorAgentRuntimeBridge(kernel, runtime=NonMonotonicMaterialRuntime()).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
        update_mission_status=False,
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "AGENT_EVENT_SPINE_PERSISTENCE_FAILED"
    projected = _projected_events(kernel, mission_id)
    assert [event.metadata["event_kind"] for event in projected] == ["runtime_started", "worker_started"]
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.RUNNING


def test_pack2b_unsupported_browser_and_memory_source_events_remain_source_only() -> None:
    sink = CapturingSink()
    bus = EventBus(
        "mission_pack2b_source_only",
        execution_event_sink=sink,
        execution_run_id="run_pack2b_source_only",
        bridge_call_id="bridge_pack2b_source_only",
        agent_run_id="agent_pack2b_source_only",
    )

    bus.append(
        AgentEventType.BROWSER_EVIDENCE_COLLECTED,
        "Browser result https://example.test should stay source-only in Pack 2B.",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.ORGAN_DISPATCHING,
        trace_refs=["browser:evidence"],
    )
    bus.append(
        AgentEventType.LEARNING_PROPOSED,
        "Memory feedback proposal should stay source-only in Pack 2B.",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.LEARNING_PROPOSING,
        trace_refs=["memory:proposal"],
    )

    assert len(bus.events()) == 2
    assert sink.events == []


def test_pack2b1_canonical_agentruntime_projects_real_worker_and_controlled_activity(
    tmp_path: Path,
) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AgentRuntime(project_root=tmp_path / "runtime")

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_runtime_envelope(mission_id),
        user_input={
            "idea": "Sentinel SPINE",
            "tool_calls": [
                {
                    "tool_id": "safe_local_markdown_tool",
                    "action": "create_markdown_file",
                    "capability": "local_markdown_write",
                    "arguments": {
                        "path": "runtime/decision.md",
                        "content": "# Decision\n\nThis content must stay out of product projections.",
                    },
                }
            ],
        },
        execution_request_id="mission_exec_req_pack2b1_canonical",
        update_mission_status=False,
    )

    assert result.status == "completed"
    projected = _projected_events(kernel, mission_id)
    metadata = [event.metadata for event in projected]
    kinds = [item["event_kind"] for item in metadata]
    assert AgentExecutionEventKind.WORKER_STARTED.value in kinds
    assert AgentExecutionEventKind.WORKER_COMPLETED.value in kinds
    assert AgentExecutionEventKind.CONTROLLED_CAPABILITY_EXECUTED.value in kinds
    assert AgentExecutionEventKind.ARTIFACT_CAPTURED.value in kinds
    worker_closed = next(item for item in metadata if item["event_kind"] == "worker_completed")
    assert worker_closed["activity_outcome"] == "succeeded"
    assert worker_closed["safe_summary"] == "Agent worker lifecycle closed successfully."
    artifact = next(item for item in metadata if item["event_kind"] == "artifact_captured")
    assert artifact["ref_verification_status"] == "unverified_source_refs"
    assert artifact["artifact_refs"] or artifact["source_event_type"] == "artifact_captured"
    serialized = "\n".join(event.model_dump_json() for event in projected)
    assert "This content must stay out" not in serialized
    assert "raw_prompt" not in serialized
    assert "provider_response" not in serialized
    assert "reasoning" not in serialized.lower()
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.RUNNING


def test_pack2b1_canonical_agentruntime_projects_failed_worker_without_success(
    tmp_path: Path,
) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AgentRuntime(project_root=tmp_path / "runtime")
    definition = runtime.worker_coordinator.runner.registry.get(MissionType.GTM)

    def fail_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("raw executor exception must not escape")

    definition.executor.execute = fail_execute

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_runtime_envelope(mission_id),
        user_input={"idea": "Sentinel SPINE"},
        execution_request_id="mission_exec_req_pack2b1_worker_failed",
        update_mission_status=False,
    )

    assert result.status == "blocked"
    projected = _projected_events(kernel, mission_id)
    worker_closed = [
        event.metadata
        for event in projected
        if event.metadata["event_kind"] == AgentExecutionEventKind.WORKER_COMPLETED.value
    ]
    assert worker_closed
    assert worker_closed[-1]["activity_outcome"] == "failed"
    assert worker_closed[-1]["safe_summary"] == "Agent worker lifecycle closed with failure."
    assert "raw executor exception" not in "\n".join(event.model_dump_json() for event in projected)
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.RUNNING


def test_pack2b1_canonical_agentruntime_projects_real_organ_dispatch_skipped(
    tmp_path: Path,
) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AgentRuntime(
        project_root=tmp_path / "runtime",
        organ_execution_config=_organ_skipped_config(),
    )

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_runtime_envelope(mission_id),
        user_input={"idea": "Sentinel SPINE"},
        execution_request_id="mission_exec_req_pack2b1_organ_skip",
        update_mission_status=False,
    )

    assert result.status == "completed"
    metadata = [event.metadata for event in _projected_events(kernel, mission_id)]
    dispatch = [item for item in metadata if item["event_kind"] == AgentExecutionEventKind.ORGAN_DISPATCH_SKIPPED.value]
    assert dispatch
    assert dispatch[-1]["activity_outcome"] == "skipped"
    assert dispatch[-1]["ref_verification_status"] == "unverified_source_refs"


def test_pack2b1_mission_trace_timeline_projects_safe_material_milestones(
    tmp_path: Path,
) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AgentRuntime(project_root=tmp_path / "runtime")

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_runtime_envelope(mission_id),
        user_input={"idea": "Sentinel SPINE"},
        execution_request_id="mission_exec_req_pack2b1_timeline",
        update_mission_status=False,
    )

    projected = _projected_events(kernel, mission_id)
    metadata = [event.metadata for event in projected]
    timeline = [item for item in metadata if item["source_ledger"] == "mission_trace_timeline"]
    assert timeline
    kinds = {item["event_kind"] for item in timeline}
    assert "action_routed" in kinds
    assert "action_executed" in kinds
    assert "mission_runner_completed" in kinds
    assert all(item["source_event_id"].startswith("mev_") for item in timeline)
    assert all(item["ref_verification_status"] == "unverified_source_refs" for item in timeline)
    assert any(item["action_refs"] for item in timeline)
    serialized = "\n".join(event.model_dump_json() for event in projected)
    assert "data/generated_projects" not in serialized
    assert "folder_path" not in serialized
    assert "Trace exists" not in serialized


def test_pack2b1_mission_trace_blocked_action_projects_without_raw_error(
    tmp_path: Path,
) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = AgentRuntime(project_root=tmp_path / "runtime")
    definition = runtime.worker_coordinator.runner.registry.get(MissionType.GTM)

    def fail_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("sensitive target C:\\secret\\boom.txt")

    definition.executor.execute = fail_execute

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_runtime_envelope(mission_id),
        user_input={"idea": "Sentinel SPINE"},
        execution_request_id="mission_exec_req_pack2b1_timeline_block",
        update_mission_status=False,
    )

    projected = _projected_events(kernel, mission_id)
    blocked = [
        event.metadata
        for event in projected
        if event.metadata["source_ledger"] == "mission_trace_timeline"
        and event.metadata["event_kind"] == "action_blocked"
    ]
    assert blocked
    assert blocked[-1]["activity_outcome"] == "blocked"
    serialized = "\n".join(event.model_dump_json() for event in projected)
    assert "sensitive target" not in serialized
    assert "C:\\secret" not in serialized
    assert "raw executor exception" not in serialized


def test_pack2b1_ghost_projection_families_are_not_claimed_without_canonical_reach() -> None:
    sink = CapturingSink()
    bus = EventBus(
        "mission_pack2b1_unclaimed",
        execution_event_sink=sink,
        execution_run_id="run_pack2b1_unclaimed",
        bridge_call_id="bridge_pack2b1_unclaimed",
        agent_run_id="agent_pack2b1_unclaimed",
    )

    bus.append(
        AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
        "Organ receipt source event remains source-only until canonical reach is proven.",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
        trace_refs=["receipt:organ"],
    )
    bus.append(
        AgentEventType.ARTIFACT_CAPTURE_DUPLICATE,
        "Duplicate artifact source event remains source-only in Pack 2B.1.",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
        trace_refs=["artifact:dupe"],
    )
    bus.append(
        AgentEventType.ARTIFACT_CAPTURE_INDEX_WRITTEN,
        "Index-written source event remains source-only in Pack 2B.1.",
        phase_before=AgentPhase.EXECUTING,
        phase_after=AgentPhase.EXECUTING,
        trace_refs=["artifact:index"],
    )

    assert len(bus.events()) == 3
    assert sink.events == []


class CapturingSink:
    def __init__(self) -> None:
        self.events: list[AgentExecutionEvent] = []

    def emit(self, event: AgentExecutionEvent) -> None:
        self.events.append(event)


class FailingSink:
    def emit(self, event: AgentExecutionEvent) -> None:
        raise RuntimeError("projection persistence unavailable")


class NoSinkRuntime:
    def __init__(self) -> None:
        self.call_count = 0

    def run(self, envelope: MissionAuthorityEnvelope, user_input: dict[str, Any]):
        self.call_count += 1
        return SimpleNamespace(
            success=True,
            final_phase=AgentPhase.COMPLETED,
            final_gate_certification=SimpleNamespace(id="finalgate:legacy", accepted=True),
            memory_feedback_result=SimpleNamespace(memory_entry_refs=[]),
            receipt_refs=["receipt:legacy"],
            artifact_paths=[],
        )


class VarKeywordRuntime:
    def __init__(self) -> None:
        self.call_count = 0

    def run(self, envelope: MissionAuthorityEnvelope, user_input: dict[str, Any], **kwargs: Any):
        self.call_count += 1
        return SimpleNamespace(
            success=True,
            final_phase=AgentPhase.COMPLETED,
            final_gate_certification=SimpleNamespace(id="finalgate:kwargs", accepted=True),
            memory_feedback_result=SimpleNamespace(memory_entry_refs=[]),
            receipt_refs=["receipt:kwargs"],
            artifact_paths=[],
        )


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


class MaterialActivityRuntime:
    def __init__(self) -> None:
        self.call_count = 0
        self.events = []

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
        bus = EventBus(
            envelope.id,
            execution_event_sink=execution_event_sink,
            execution_run_id=execution_run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
        )
        bus.append(
            AgentEventType.AGENT_INITIALIZED,
            "Agent runtime initialized.",
            phase_before=AgentPhase.CREATED,
            phase_after=AgentPhase.INITIALIZED,
        )
        bus.append(
            AgentEventType.WORKER_STARTED,
            "Worker started with raw_prompt that must not project.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={"task_id": "task_secret", "project_path": "C:\\secret\\repo"},
            trace_refs=["worker:mission"],
        )
        bus.append(
            AgentEventType.CONTROLLED_CAPABILITY_EXECUTED,
            "Capability executed https://example.test provider_response.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={"arguments": {"path": "C:\\secret\\out.md"}, "reasoning": "no"},
            trace_refs=["capability:local_file", "evidence:policy"],
        )
        bus.append(
            AgentEventType.ARTIFACT_CAPTURED,
            "Artifact captured.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            payload={"relative_path": "secret.md", "sha256": "abc"},
            trace_refs=["artifact:captured", "evidence:artifact"],
        )
        bus.append(
            AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED,
            "Organ receipt recorded.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            trace_refs=["receipt:organ", "organ:browser"],
        )
        bus.append(
            AgentEventType.AGENT_COMPLETED,
            "Agent completed.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.COMPLETED,
        )
        self.events = list(bus.events())
        return SimpleNamespace(
            success=True,
            final_phase=AgentPhase.COMPLETED,
            final_gate_certification=SimpleNamespace(id="finalgate:material", accepted=True),
            memory_feedback_result=SimpleNamespace(memory_entry_refs=[]),
            receipt_refs=["receipt:organ"],
            artifact_paths=[],
        )


class NonMonotonicMaterialRuntime(MaterialActivityRuntime):
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
        bus = EventBus(
            envelope.id,
            execution_event_sink=execution_event_sink,
            execution_run_id=execution_run_id,
            execution_request_id=execution_request_id,
            bridge_call_id=bridge_call_id,
            agent_run_id=agent_run_id,
        )
        bus.append(
            AgentEventType.AGENT_INITIALIZED,
            "Agent runtime initialized.",
            phase_before=AgentPhase.CREATED,
            phase_after=AgentPhase.INITIALIZED,
        )
        bus.append(
            AgentEventType.WORKER_STARTED,
            "Worker started.",
            phase_before=AgentPhase.EXECUTING,
            phase_after=AgentPhase.EXECUTING,
            trace_refs=["worker:mission"],
        )
        self.events = list(bus.events())
        if execution_event_sink is not None:
            stale_source = self.events[1].model_copy(update={"sequence": 1})
            execution_event_sink.emit(
                AgentExecutionEvent.from_agent_event(
                    stale_source,
                    run_id=execution_run_id,
                    execution_request_id=execution_request_id,
                    bridge_call_id=bridge_call_id,
                    agent_run_id=agent_run_id,
                )
            )
        return SimpleNamespace(
            success=True,
            final_phase=AgentPhase.COMPLETED,
            final_gate_certification=SimpleNamespace(id="finalgate:material", accepted=True),
            memory_feedback_result=SimpleNamespace(memory_entry_refs=[]),
            receipt_refs=[],
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


def _runtime_envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="operator_user",
        mission_type=MissionType.GTM,
        mission_title="Operator agent runtime canonical path",
        mission_objective="Run through real AgentRuntime material execution path.",
        success_criteria=["GTM files exist", "Trace exists"],
        mode=MissionMode.POWER,
        allowed_systems=["local_workspace"],
        allowed_tools=["safe_file_writer", "safe_local_markdown_tool"],
        allowed_actions=[
            "create_project_folder",
            "create_markdown_file",
            "export_json",
            "generate_gtm_pack",
            "generate_landing_copy",
            "generate_outreach_drafts_without_sending",
            "create_watchlist",
            "generate_research_questions",
            "write_trace",
        ],
        forbidden_actions=["send_email", "run_shell_command", "browser_submit_form", "credential_access"],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=30,
        max_actions=20,
        max_cost_usd=1.0,
    )


def _organ_skipped_config() -> OrganRuntimeExecutionConfig:
    return OrganRuntimeExecutionConfig(
        enabled=True,
        organ_dispatch_enabled=True,
        temporary_candidate_bridge_enabled=True,
        mode=OrganRuntimeExecutionMode.L2_L3_LOCAL_ONLY,
        allowed_action_levels=["L2", "L3"],
        allowed_organs=["local_artifact", "reversible_workspace"],
        allow_l2=True,
        allow_l3=True,
    )
