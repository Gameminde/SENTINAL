from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.daemon_models import DaemonLeaseOwner, daemon_utc_now
from sentinel.operator.daemon_runtime import MissionDaemonRuntimeError
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequestState
from sentinel.operator.models import (
    MissionAuthoritySummary,
    MissionDraft,
    OperatorMissionStatus,
    OperatorConversationState,
    OperatorMode,
)
from sentinel.operator.runtime_host import RuntimeHostStatus, SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import DispatchStatus


def test_runtime_host_start_shutdown_and_deterministic_daemon_pickup(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")
    workspace = _workspace(tmp_path)

    started = host.start()
    assert started.status is RuntimeHostStatus.STARTED
    assert host.start().status is RuntimeHostStatus.STARTED

    mission = host.lifecycle.create_mission(
        session_id="session_host",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={"workspace": "."},
            workspace_ref=f"workspace:{workspace}",
            model_contract_ref="model_contract:host",
        )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.claimed is True
    assert pickup.execution_request_ref == mission.execution_request.request_id
    assert pickup.tick_result is None
    assert pickup.dispatch_result is not None
    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED
    state = host.lifecycle.derive_request_state(mission.record.mission_id, mission.execution_request.request_id)
    assert state.state is MissionExecutionRequestState.COMPLETED
    queue_record = host.daemon.store.load_queue_record(mission.record.mission_id)
    assert queue_record.metadata["execution_request_id"] == mission.execution_request.request_id
    events = [event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)]
    assert "daemon_lease_claimed" in events
    assert "mission_dispatch_decision_persisted" in events
    assert "mission_dispatch_closeout_persisted" in events

    stopped = host.shutdown()
    assert stopped.status is RuntimeHostStatus.STOPPED


def test_runtime_host_daemon_claim_failure_does_not_mark_request_claimed(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_host",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "."},
        workspace_ref="snapshot:host",
        model_contract_ref="model_contract:host",
    )

    host.daemon.store.claim_lease(
        mission.record.mission_id,
        owner=DaemonLeaseOwner(owner_id="competing_daemon"),
        now=daemon_utc_now(),
        ttl_seconds=60,
    )

    with pytest.raises(MissionDaemonRuntimeError, match="daemon_lease_owned_by_another_daemon"):
        host.pump_daemon_once(mission.record.mission_id)

    state = host.lifecycle.derive_request_state(mission.record.mission_id, mission.execution_request.request_id)
    assert state.state is MissionExecutionRequestState.QUEUED
    assert "mission_execution_request_claimed" not in [
        event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)
    ]
    assert host.daemon.store.list_leases()[0].owner.owner_id == "competing_daemon"


def test_cockpit_can_start_mission_as_runtime_host_client(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    approval_scope = _approval_scope()
    cockpit = LLMLiveOperatorCockpit(
        run_root=tmp_path / "unused",
        mode=OperatorMode.DETERMINISTIC_TEST,
        lifecycle_service=host.lifecycle,
        authority_approval_scope=approval_scope,
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


def test_lifecycle_backed_cockpit_missing_explicit_approval_scope_blocks_before_mission_creation(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    cockpit = LLMLiveOperatorCockpit(
        run_root=tmp_path / "unused",
        mode=OperatorMode.DETERMINISTIC_TEST,
        lifecycle_service=host.lifecycle,
    )
    cockpit.session.current_draft = _draft()
    cockpit.session.current_authority_summary = _summary()

    result = cockpit.handle("start")

    assert result.state is OperatorConversationState.ASKING_CLARIFICATIONS
    assert result.metadata["blocked_reason"] == "explicit_authority_approval_scope_required"
    assert host.kernel.list_missions() == []


def test_lifecycle_backed_cockpit_preserves_explicit_scope_and_policy_only_narrows(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    approval_scope = _approval_scope(
        allowed_actions=["list_directory", "read_file_segment", "search_text"],
        max_actions=12,
    )
    authority_summary = _summary(allowed_actions=["list_directory", "read_file_segment", "search_text"])
    authority_summary = authority_summary.model_copy(update={"metadata": {"max_actions": 4}})
    cockpit = LLMLiveOperatorCockpit(
        run_root=tmp_path / "unused",
        mode=OperatorMode.DETERMINISTIC_TEST,
        lifecycle_service=host.lifecycle,
        authority_approval_scope=approval_scope,
    )
    cockpit.session.current_draft = _draft()
    cockpit.session.current_authority_summary = authority_summary

    result = cockpit.handle("start")

    assert result.state is OperatorConversationState.MISSION_QUEUED
    assert result.mission_record is not None
    active = host.authority_issuer.resolve_active(result.mission_record.mission_id)
    record = host.authority_issuer.list_records(result.mission_record.mission_id)[-1]
    assert record.authority_approval_scope_hash == approval_scope.approval_scope_hash
    assert active.allowed_actions == ["list_directory", "read_file_segment", "search_text"]
    assert active.allowed_systems == ["local_workspace"]
    assert active.allowed_tools == ["read_only_observation"]
    assert active.allowed_paths == ["."]
    assert active.allowed_domains == []
    assert active.allowed_accounts == []
    assert active.allowed_data_types == []
    assert active.browser_v3_authority_grants == []
    assert active.credential_grants == []
    assert active.max_actions == 4


def _draft() -> MissionDraft:
    return MissionDraft(
        title="Read-only repository inspection",
        objective="Inspect repository files without mutation.",
        expected_artifacts=["evidence-linked report"],
    )


def _summary(*, allowed_actions: list[str] | None = None) -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=allowed_actions or ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell"],
        summary="Read-only authority only.",
    )


def _policy() -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=12,
        max_cost_usd=0.0,
    )


def _approval_scope(*, allowed_actions: list[str] | None = None, max_actions: int = 12) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=allowed_actions or ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=max_actions,
        max_cost_usd=0.0,
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("Fixture repository for read-only research.\n", encoding="utf-8")
    return root
