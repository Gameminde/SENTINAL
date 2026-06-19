from __future__ import annotations

from pathlib import Path

from sentinel.operator.authority_issuer import MissionAuthorityPolicy
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    OperatorConversationState,
    OperatorMode,
)
from sentinel.operator.runtime_host import RuntimeHostStatus, SentinelRuntimeHost


def test_runtime_host_start_shutdown_and_deterministic_daemon_pickup(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    started = host.start()
    assert started.status is RuntimeHostStatus.STARTED
    assert host.start().status is RuntimeHostStatus.STARTED

    mission = host.lifecycle.create_mission(
        session_id="session_host",
        draft=_draft(),
        authority_summary=_summary(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "."},
        workspace_ref="snapshot:host",
        model_contract_ref="model_contract:host",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.claimed is True
    assert pickup.execution_request_ref == mission.execution_request.request_id
    assert pickup.tick_result.executed is False
    queue_record = host.daemon.store.load_queue_record(mission.record.mission_id)
    assert queue_record.metadata["execution_request_id"] == mission.execution_request.request_id
    assert "daemon_lease_claimed" in [
        event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)
    ]

    stopped = host.shutdown()
    assert stopped.status is RuntimeHostStatus.STOPPED


def test_cockpit_can_start_mission_as_runtime_host_client(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    cockpit = LLMLiveOperatorCockpit(
        run_root=tmp_path / "unused",
        mode=OperatorMode.DETERMINISTIC_TEST,
        lifecycle_service=host.lifecycle,
    )
    cockpit.session.current_draft = _draft()
    cockpit.session.current_authority_summary = _summary()

    result = cockpit.handle("start")

    assert result.state is OperatorConversationState.MISSION_QUEUED
    assert result.mission_record is not None
    assert result.mission_record.mission_id in cockpit.active_mission_ids
    request = host.lifecycle.latest_execution_request(result.mission_record.mission_id)
    assert request.capability_id == "read_only_research"
    assert host.kernel.store.load_record(result.mission_record.mission_id).status.value == "queued"


def _draft() -> MissionDraft:
    return MissionDraft(
        title="Read-only repository inspection",
        objective="Inspect repository files without mutation.",
        expected_artifacts=["evidence-linked report"],
    )


def _summary() -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_report"],
        forbidden_actions=["write_file", "shell"],
        summary="Read-only authority only.",
    )


def _policy() -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_report"],
        forbidden_actions=["write_file", "shell"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=12,
        max_cost_usd=0.0,
    )
