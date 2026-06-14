from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sentinel.agent import CoreFinalGateResult
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import OperatorAgentRuntimeBridge
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.shared.enums import MissionMode, MissionType
from sentinel.telemetry import TelemetryKernel


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
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
    )

    assert runtime.calls
    assert result.status == "completed"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED


def test_operator_agent_bridge_rejects_tampered_mission_record(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()
    record_path = kernel.store.run_root / mission_id / "record.json"
    payload = json.loads(record_path.read_text(encoding="utf-8"))
    payload["status"] = "completed"
    record_path.write_text(json.dumps(payload), encoding="utf-8")

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert runtime.calls == []
    assert result.status == "blocked"
    assert result.blocked_reason == "mission_record_tampered"


def test_operator_agent_bridge_rejects_revoked_or_expired_envelope(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()
    bridge = OperatorAgentRuntimeBridge(kernel, runtime=runtime)

    revoked = bridge.run(
        mission_id,
        envelope=_envelope(mission_id).model_copy(update={"revoked_at": datetime.now(UTC)}),
        user_input={},
    )
    expired = bridge.run(
        mission_id,
        envelope=_envelope(mission_id).model_copy(
            update={"created_at": datetime.now(UTC) - timedelta(hours=2), "max_duration_minutes": 1}
        ),
        user_input={},
    )

    assert runtime.calls == []
    assert revoked.blocked_reason == "mission_authority_envelope_inactive"
    assert expired.blocked_reason == "mission_authority_envelope_inactive"


def test_operator_agent_bridge_contains_runtime_failure(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    class FailingRuntime:
        def run(self, *_args, **_kwargs):
            raise RuntimeError("raw provider response should not escape")

    result = OperatorAgentRuntimeBridge(kernel, runtime=FailingRuntime()).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "agentruntime_bridge_failure"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_operator_agent_bridge_requires_accepted_finalgate_for_completion(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    class MissingFinalGateRuntime:
        def run(self, *_args, **_kwargs):
            return SimpleNamespace(success=True, final_gate_certification=None, artifact_paths=[])

    result = OperatorAgentRuntimeBridge(kernel, runtime=MissingFinalGateRuntime()).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert result.status == "blocked"
    assert result.blocked_reason == "agentruntime_finalgate_required"


def test_operator_agent_bridge_hashes_real_finalgate_without_identifier(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    class RealFinalGateRuntime:
        def run(self, *_args, **_kwargs):
            return SimpleNamespace(
                success=True,
                final_gate_certification=CoreFinalGateResult(accepted=True, checks=[]),
                artifact_paths=[],
            )

    result = OperatorAgentRuntimeBridge(kernel, runtime=RealFinalGateRuntime()).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert result.status == "completed"
    assert len(result.finalgate_certificate_refs) == 1
    assert result.finalgate_certificate_refs[0].startswith("finalgate:")


def test_operator_agent_bridge_default_off_without_runtime_config(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)

    result = OperatorAgentRuntimeBridge(kernel).run(mission_id, envelope=_envelope(mission_id), user_input={})

    assert result.status == "blocked"
    assert result.blocked_reason == "missing_agentruntime"
    assert kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_operator_agent_bridge_blocks_draft_mission_before_runtime_execution(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_agent",
        draft=MissionDraft(title="Draft agent bridge", objective="Must be explicitly started."),
    )
    runtime = RecordingRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        record.mission_id,
        envelope=_envelope(record.mission_id),
        user_input={},
    )

    assert runtime.calls == []
    assert result.status == "blocked"
    assert result.blocked_reason == "operator_mission_not_executable"
    assert kernel.store.load_record(record.mission_id).status is OperatorMissionStatus.DRAFT


def test_operator_agent_bridge_blocks_when_certified_telemetry_is_unavailable(tmp_path: Path) -> None:
    telemetry = TelemetryKernel(tmp_path / "telemetry", enabled=False)
    kernel = MissionKernel(run_root=tmp_path / "runs", telemetry_sink=telemetry)
    record = kernel.create_mission(
        session_id="session_agent",
        draft=MissionDraft(title="Agent bridge", objective="Requires certified telemetry."),
    )
    kernel.enqueue(record.mission_id)
    runtime = RecordingRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        record.mission_id,
        envelope=_envelope(record.mission_id),
        user_input={},
    )

    assert runtime.calls == []
    assert result.status == "blocked"
    assert result.blocked_reason == "telemetry_certified_mode_required"


def test_operator_agent_bridge_does_not_run_killed_mission(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    kernel.kill(mission_id)
    runtime = RecordingRuntime()

    result = OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
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
        envelope=_envelope(mission_id),
        user_input={"goal": "safe"},
    )

    assert result.finalgate_certificate_refs == ["finalgate:agent"]
    assert result.memory_feedback_refs == ["memory:agent"]
    assert kernel.store.load_events(mission_id)[-1].finalgate_certificate_refs == ["finalgate:agent"]
    assert kernel.store.load_events(mission_id)[-1].memory_feedback_refs == ["memory:agent"]


def test_operator_agent_bridge_does_not_enable_provider_fallback(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert "fallback" not in str(runtime.calls[0][2]).lower()
    assert "auto" not in str(runtime.calls[0][2]).lower()


def test_operator_agent_bridge_does_not_directly_dispatch_organs(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    runtime = RecordingRuntime()

    OperatorAgentRuntimeBridge(kernel, runtime=runtime).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={},
    )

    assert len(runtime.calls) == 1
