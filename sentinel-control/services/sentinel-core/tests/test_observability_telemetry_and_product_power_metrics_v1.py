from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.agent_bridge import AgentEventProjectionMode, OperatorAgentRuntimeBridge
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.power_bridge import OperatorPowerRuntimeBridge
from sentinel.operator.workflow_replay import DurableWorkflowReplayBuilder
from sentinel.operator.workflow_runtime import DurableMissionWorkflowRuntime
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
)
from sentinel.telemetry import (
    TelemetryCertificationError,
    TelemetryDegradationPolicy,
    TelemetryDomain,
    TelemetryEventKind,
    TelemetryEventRecord,
    TelemetryExecutionClass,
    TelemetryKernel,
    TelemetryOperationalState,
    TelemetrySourceSurface,
    TelemetryStore,
    evaluate_telemetry_operation,
)


def test_telemetry_store_redacts_secrets_and_detects_tamper(tmp_path: Path) -> None:
    store = TelemetryStore(tmp_path / "telemetry")
    record = store.record_event(
        TelemetryEventRecord(
            mission_id="mission_telemetry",
            source_surface=TelemetrySourceSurface.MISSION_KERNEL,
            domain=TelemetryDomain.OPERATIONAL,
            event_kind=TelemetryEventKind.MISSION_STARTED,
            safe_summary="OPENAI_API_KEY=sk-test-1234567890",
            metadata={
                "notes": "OPENAI_API_KEY=sk-test-1234567890",
            },
        )
    )

    assert record.redaction_hit is True
    assert "[REDACTED_SECRET]" in record.safe_summary
    assert record.metadata["notes"] == "[REDACTED_SECRET]"
    assert store.verify_events() is True
    payload = (tmp_path / "telemetry" / "events.jsonl").read_text(encoding="utf-8")
    tampered = payload.replace(record.event_hash, "0" * len(record.event_hash), 1)
    (tmp_path / "telemetry" / "events.jsonl").write_text(tampered, encoding="utf-8")
    assert store.verify_events() is False
    assert store.snapshot().tampered is True


def test_mission_kernel_default_telemetry_records_mission_flow(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_telemetry",
        draft=_draft(),
        authority_summary=_authority_summary("mission_telemetry"),
    )
    kernel.enqueue(record.mission_id)
    kernel.update_status(record.mission_id, OperatorMissionStatus.RUNNING, "Mission running.")

    telemetry = kernel.telemetry_sink
    assert telemetry is not None
    snapshot = telemetry.certified_mode_status()
    assert snapshot.certified_mode is True
    assert snapshot.event_count >= 3
    kinds = {event.event_kind.value for event in telemetry.store.load_events()}
    assert "mission_created" in kinds
    assert "mission_queued" in kinds
    assert "mission_running" in kinds
    assert "mission_started" in kinds


def test_central_telemetry_degradation_policy_blocks_material_but_preserves_kill_and_explicit_read_only(
    tmp_path: Path,
) -> None:
    telemetry = TelemetryKernel(tmp_path / "telemetry", enabled=False)

    material = evaluate_telemetry_operation(
        telemetry,
        TelemetryExecutionClass.MATERIAL_MUTATION,
    )
    read_only = evaluate_telemetry_operation(
        telemetry,
        TelemetryExecutionClass.READ_ONLY_OBSERVATION,
        policy=TelemetryDegradationPolicy(allow_read_only_when_degraded=True),
    )
    kill = evaluate_telemetry_operation(
        telemetry,
        TelemetryExecutionClass.KILL_OR_REVOCATION,
    )

    assert material.evidence_ready is False
    assert material.state is TelemetryOperationalState.UNAVAILABLE
    assert read_only.evidence_ready is True
    assert read_only.state is TelemetryOperationalState.READ_ONLY_SAFE_MODE
    assert kill.evidence_ready is True
    assert kill.kill_and_revocation_available is True
    assert material.operator_visible is True
    with pytest.raises(TelemetryCertificationError, match="material_execution_requires_certified_telemetry"):
        telemetry.require_material_execution("workspace_mutation")


def test_telemetry_write_failure_degrades_certification_and_blocks_material_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = TelemetryKernel(tmp_path / "telemetry")

    def fail_write(*_args, **_kwargs):
        raise OSError("simulated telemetry disk failure")

    monkeypatch.setattr(telemetry.store, "_append_jsonl", fail_write)

    with pytest.raises(Exception, match="telemetry_write_failed"):
        telemetry.store.record_event(
            TelemetryEventRecord(
                mission_id="mission_telemetry_failure",
                source_surface=TelemetrySourceSurface.MISSION_KERNEL,
                domain=TelemetryDomain.OPERATIONAL,
                event_kind=TelemetryEventKind.MISSION_STARTED,
                safe_summary="Telemetry write must fail closed.",
            )
        )

    snapshot = telemetry.certified_mode_status()
    assert snapshot.certified_mode is False
    assert snapshot.operator_visible is True
    assert "telemetry_write_failed" in snapshot.reasons
    with pytest.raises(TelemetryCertificationError):
        telemetry.require_material_execution("channel_send")


def test_agent_bridge_records_replan_and_memory_telemetry(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    kernel.enqueue(mission_id)

    class FakeAgentRuntime:
        def run(self, envelope, user_input):
            return SimpleNamespace(
                success=True,
                status="completed",
                replan_ready=True,
                automatic_replan_executed=True,
                replan_packet={"branch": "replan"},
                receipt_refs=["receipt_1"],
                    final_gate_certification=SimpleNamespace(id="finalgate_1", accepted=True),
                memory_feedback_refs=["memory_1"],
                memory_feedback_result=SimpleNamespace(memory_entry_refs=["memory_1"]),
                brain_candidate_source_status="brain_ready",
            )

    result = OperatorAgentRuntimeBridge(
        kernel,
        runtime=FakeAgentRuntime(),
        projection_mode=AgentEventProjectionMode.LEGACY_EXPLICITLY_DISABLED,
    ).run(
        mission_id,
        envelope=_envelope(mission_id),
        user_input={"goal": "measure telemetry"},
    )

    assert result.status == "completed"
    telemetry_events = [event.event_kind.value for event in kernel.telemetry_sink.store.load_events()]
    telemetry_metrics = [metric.metric_kind.value for metric in kernel.telemetry_sink.store.load_metrics()]
    assert "replan_candidate_created" in telemetry_events
    assert "replan_executed" in telemetry_events
    assert "replan_success_rate" in telemetry_metrics
    assert "memory_recall_count" in telemetry_metrics


def test_power_workflow_and_replay_emit_telemetry(tmp_path: Path) -> None:
    kernel, mission_id = _kernel_with_mission(tmp_path)
    workflow_runtime = DurableMissionWorkflowRuntime(kernel)
    plan = _power_plan(mission_id)
    record = workflow_runtime.create_power_workflow(
        mission_id=mission_id,
        envelope=_envelope(mission_id),
        plan=plan,
        executor_contract_id="workspace-contract",
    )

    power_result = OperatorPowerRuntimeBridge(kernel).run(
        mission_id,
        plan,
        envelope=_envelope(mission_id),
    )

    assert power_result.status.value in {"blocked", "completed", "failed", "aborted"}
    replay = DurableWorkflowReplayBuilder(workflow_runtime.store).build(record.workflow_id)
    assert replay.tampered is False

    telemetry_events = [event.event_kind.value for event in kernel.telemetry_sink.store.load_events()]
    telemetry_metrics = [metric.metric_kind.value for metric in kernel.telemetry_sink.store.load_metrics()]
    assert "workflow_checkpoint_created" in telemetry_events
    assert "timeline_replay_completeness" in telemetry_metrics
    assert "mission_completion_rate" in telemetry_metrics


def _kernel_with_mission(tmp_path: Path) -> tuple[MissionKernel, str]:
    kernel = MissionKernel(run_root=tmp_path)
    record = kernel.create_mission(
        session_id="session_telemetry",
        draft=_draft(),
        authority_summary=_authority_summary("mission_telemetry"),
    )
    return kernel, record.mission_id


def _draft() -> MissionDraft:
    return MissionDraft(
        title="Telemetry product power",
        objective="Measure the telemetry spine across mission runtime surfaces.",
        constraints=["no payment", "no provider fallback"],
        expected_artifacts=["telemetry summary"],
    )


def _authority_summary(mission_id: str) -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id=mission_id,
        allowed_actions=["write"],
        forbidden_actions=["payment"],
        summary="Telemetry measurement only.",
    )


def _envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_telemetry",
        mission_title="Telemetry mission",
        mission_objective="Measure product power telemetry.",
        allowed_systems=["workspace"],
        allowed_tools=["workspace"],
        allowed_actions=["write"],
        allowed_paths=["data/generated_projects"],
        max_duration_minutes=60,
        max_actions=10,
        max_cost_usd=1.0,
        max_recipients=0,
    )


def _power_plan(mission_id: str) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="step_telemetry_write",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L2,
                    organ_kind="workspace",
                    action_kind="write",
                    request={"path": "data/generated_projects/telemetry.txt"},
                    estimated_cost_usd=0.0,
                    safe_summary="Write a telemetry artifact.",
                )
            ]
        ),
    )
