from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import OperatorAgentRuntimeBridge
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.shared.enums import MissionMode, MissionType


def _envelope() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
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


def _kernel_with_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_agent",
        draft=MissionDraft(title="Agent bridge", objective="Use AgentRuntime public API."),
    )
    kernel.enqueue(record.mission_id)
    return kernel, record.mission_id


class RecordingRuntime:
    def __init__(self) -> None:
        self.calls = []

    def run(self, envelope, user_input, **kwargs):
        self.calls.append((envelope, user_input, kwargs))
        return SimpleNamespace(
            success=True,
            final_phase="completed",
            final_gate_certification=SimpleNamespace(id="finalgate:agent", accepted=True),
            memory_feedback_result=SimpleNamespace(memory_entry_refs=["memory:agent"]),
            artifact_paths=[],
        )


def test_operator_agent_bridge_uses_public_runtime_api(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(),
        user_input={"goal": "safe"},
    )

    assert runtime.calls
    assert result.status == "completed"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED


def test_operator_agent_bridge_default_off_without_runtime_config(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorAgentRuntimeBridge(kernel).run(mission_id, envelope=_envelope(), user_input={})

    assert result.status == "blocked"
    assert result.blocked_reason == "missing_agentruntime"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_operator_agent_bridge_does_not_run_killed_mission(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    kernel.kill(mission_id)
    runtime = RecordingRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(),
        user_input={},
    )

    assert runtime.calls == []
    assert result.status == "blocked"
    assert result.blocked_reason == "operator_mission_terminal"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.KILLED


def test_operator_agent_bridge_records_finalgate_memory_refs(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorAgentRuntimeBridge(kernel, runtime=RecordingRuntime()).run(
        mission_id,
        envelope=_envelope(),
        user_input={"goal": "safe"},
    )

    assert result.finalgate_certificate_refs == ["finalgate:agent"]
    assert result.memory_feedback_refs == ["memory:agent"]
    assert kernel.store.load_events(mission_id)[-1].finalgate_certificate_refs == ["finalgate:agent"]
    assert kernel.store.load_events(mission_id)[-1].memory_feedback_refs == ["memory:agent"]


def test_operator_agent_bridge_does_not_enable_provider_fallback(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(mission_id, envelope=_envelope(), user_input={})

    assert "fallback" not in str(runtime.calls[0][2]).lower()
    assert "auto" not in str(runtime.calls[0][2]).lower()


def test_operator_agent_bridge_does_not_directly_dispatch_organs(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(mission_id, envelope=_envelope(), user_input={})

    assert len(runtime.calls) == 1
