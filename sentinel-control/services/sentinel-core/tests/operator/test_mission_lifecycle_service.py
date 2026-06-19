from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.operator.authority_issuer import MissionAuthorityPolicy
from sentinel.operator.mission_lifecycle_service import MissionLifecycleService
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus


def test_lifecycle_persists_authority_and_execution_request_before_enqueue(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)

    result = lifecycle.create_mission(
        session_id="session_lifecycle",
        draft=_draft(),
        authority_summary=_summary(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "."},
        workspace_ref="snapshot:unit",
        model_contract_ref="model_contract:unit",
    )

    assert result.record.status is OperatorMissionStatus.QUEUED
    assert result.authority_record.envelope_hash
    assert result.execution_request.verify_hash()
    assert result.execution_request.authority_envelope_ref == result.authority_record.envelope_id
    assert result.execution_request.capability_id == "read_only_research"

    events = kernel.store.load_events(result.record.mission_id)
    event_types = [event.event_type for event in events]
    assert event_types.index("mission_authority_envelope_issued") < event_types.index("mission_execution_request_persisted")
    assert event_types.index("mission_execution_request_persisted") < event_types.index("mission_queued")
    stored_request = lifecycle.load_execution_request(result.record.mission_id, result.execution_request.request_id)
    assert stored_request.verify_hash()


def test_lifecycle_does_not_enqueue_when_authority_issuance_fails(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)

    with pytest.raises(ValueError, match="authority_summary_action_outside_policy"):
        lifecycle.create_mission(
            session_id="session_lifecycle",
            draft=_draft(),
            authority_summary=_summary(allowed_actions=["shell"]),
            policy=_policy(allowed_actions=["list_directory"]),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={},
            workspace_ref="snapshot:unit",
            model_contract_ref="model_contract:unit",
        )

    records = kernel.list_missions()
    assert len(records) == 1
    assert records[0].status is OperatorMissionStatus.DRAFT
    assert "mission_queued" not in [event.event_type for event in kernel.store.load_events(records[0].mission_id)]


def _draft() -> MissionDraft:
    return MissionDraft(
        title="Read-only repository inspection",
        objective="Inspect repository files without mutation.",
        expected_artifacts=["evidence-linked report"],
    )


def _summary(*, allowed_actions: list[str] | None = None) -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=allowed_actions or ["list_directory", "read_file_segment", "search_text", "finish_report"],
        forbidden_actions=["write_file", "shell"],
        summary="Read-only authority only.",
    )


def _policy(*, allowed_actions: list[str] | None = None) -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=allowed_actions or ["list_directory", "read_file_segment", "search_text", "finish_report"],
        forbidden_actions=["write_file", "shell"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=12,
        max_cost_usd=0.0,
    )
