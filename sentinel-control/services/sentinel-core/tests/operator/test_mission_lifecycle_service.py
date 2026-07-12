from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequestState, MissionLifecycleService
from sentinel.operator.kernel import MissionKernel, MissionLifecycleError
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus


def test_lifecycle_persists_authority_and_execution_request_before_enqueue(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)

    result = lifecycle.create_mission(
        session_id="session_lifecycle",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
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
    assert result.execution_request.prepared is True

    events = kernel.store.load_events(result.record.mission_id)
    event_types = [event.event_type for event in events]
    assert event_types.index("mission_authority_envelope_issued") < event_types.index("mission_execution_request_prepared")
    assert event_types.index("mission_execution_request_prepared") < event_types.index("mission_queued")
    queued_event = next(event for event in events if event.event_type == "mission_queued")
    assert queued_event.metadata["execution_request_id"] == result.execution_request.request_id
    stored_request = lifecycle.load_execution_request(result.record.mission_id, result.execution_request.request_id)
    assert stored_request.verify_hash()
    assert stored_request == result.execution_request
    assert lifecycle.derive_request_state(result.record.mission_id, result.execution_request.request_id).state is MissionExecutionRequestState.QUEUED


def test_lifecycle_loads_execution_request_on_long_windows_path(tmp_path: Path) -> None:
    long_root = tmp_path / ("sentinel_browser_cortex_product_spine_" + ("x" * 5)) / "runs"
    kernel = MissionKernel(run_root=long_root)
    lifecycle = MissionLifecycleService(kernel)

    result = lifecycle.create_mission(
        session_id="session_lifecycle_long_path",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "."},
        workspace_ref="snapshot:unit",
        model_contract_ref="model_contract:unit",
    )
    request_path = (
        long_root
        / result.record.mission_id
        / "execution_requests"
        / f"{result.execution_request.request_id}.json"
    )

    assert len(str(request_path.resolve())) > 260
    assert lifecycle.load_execution_request(result.record.mission_id, result.execution_request.request_id) == result.execution_request
    assert lifecycle.latest_execution_request(result.record.mission_id) == result.execution_request
    assert lifecycle.list_execution_requests(result.record.mission_id) == [result.execution_request]


def test_lifecycle_does_not_enqueue_when_authority_issuance_fails(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)

    with pytest.raises(ValueError, match="authority_summary_action_outside_policy"):
        lifecycle.create_mission(
            session_id="session_lifecycle",
            draft=_draft(),
            authority_summary=_summary(allowed_actions=["export_report"]),
            approval_scope=_approval_scope(allowed_actions=["export_report"]),
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


def test_lifecycle_does_not_mark_request_queued_when_enqueue_fails(tmp_path: Path) -> None:
    class _FailingEnqueueKernel(MissionKernel):
        def enqueue(self, mission_id: str, *, metadata=None):  # noqa: ANN001
            raise MissionLifecycleError("synthetic enqueue failure")

    kernel = _FailingEnqueueKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)

    with pytest.raises(MissionLifecycleError, match="synthetic enqueue failure"):
        lifecycle.create_mission(
            session_id="session_lifecycle",
            draft=_draft(),
            authority_summary=_summary(),
            approval_scope=_approval_scope(),
            policy=_policy(),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={"workspace": "."},
            workspace_ref="snapshot:unit",
            model_contract_ref="model_contract:unit",
        )

    record = kernel.list_missions()[0]
    request = lifecycle.latest_execution_request(record.mission_id)
    assert record.status is OperatorMissionStatus.DRAFT
    assert request.prepared is True
    assert request.verify_hash()
    events = kernel.store.load_events(record.mission_id)
    assert "mission_queued" not in [event.event_type for event in events]
    failure_event = next(event for event in events if event.event_type == "mission_execution_request_enqueue_failed")
    assert failure_event.metadata["execution_request_id"] == request.request_id
    assert failure_event.metadata["failure_code"] == "mission_kernel_enqueue_failed"
    assert lifecycle.derive_request_state(record.mission_id, request.request_id).state is MissionExecutionRequestState.ORPHANED_PREPARED


def test_lifecycle_prepared_before_enqueue_derives_prepared_not_orphaned(tmp_path: Path) -> None:
    class _InspectingEnqueueKernel(MissionKernel):
        lifecycle: MissionLifecycleService
        observed_state: MissionExecutionRequestState | None = None

        def enqueue(self, mission_id: str, *, metadata=None):  # noqa: ANN001
            request_id = metadata["execution_request_id"]
            self.observed_state = self.lifecycle.derive_request_state(mission_id, request_id).state
            return super().enqueue(mission_id, metadata=metadata)

    kernel = _InspectingEnqueueKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)
    kernel.lifecycle = lifecycle

    result = lifecycle.create_mission(
        session_id="session_lifecycle",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "."},
        workspace_ref="snapshot:unit",
        model_contract_ref="model_contract:unit",
    )

    assert kernel.observed_state is MissionExecutionRequestState.PREPARED
    assert lifecycle.derive_request_state(result.record.mission_id, result.execution_request.request_id).state is MissionExecutionRequestState.QUEUED


def test_lifecycle_enqueue_failure_event_persistence_failure_leaves_request_prepared(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    class _FailingEnqueueKernel(MissionKernel):
        def enqueue(self, mission_id: str, *, metadata=None):  # noqa: ANN001
            raise MissionLifecycleError("synthetic enqueue failure")

    kernel = _FailingEnqueueKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)
    original_append_event = kernel.store.append_event

    def failing_append_event(mission_id, *args, **kwargs):  # noqa: ANN001
        event_type = kwargs.get("event_type") if "event_type" in kwargs else args[0]
        if event_type == "mission_execution_request_enqueue_failed":
            raise RuntimeError("synthetic enqueue failure event persistence failure")
        return original_append_event(mission_id, *args, **kwargs)

    monkeypatch.setattr(kernel.store, "append_event", failing_append_event)

    with pytest.raises(RuntimeError, match="synthetic enqueue failure event persistence failure"):
        lifecycle.create_mission(
            session_id="session_lifecycle",
            draft=_draft(),
            authority_summary=_summary(),
            approval_scope=_approval_scope(),
            policy=_policy(),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={"workspace": "."},
            workspace_ref="snapshot:unit",
            model_contract_ref="model_contract:unit",
        )

    record = kernel.list_missions()[0]
    request = lifecycle.latest_execution_request(record.mission_id)
    event_types = [event.event_type for event in kernel.store.load_events(record.mission_id)]
    assert "mission_queued" not in event_types
    assert "mission_execution_request_enqueue_failed" not in event_types
    assert lifecycle.derive_request_state(record.mission_id, request.request_id).state is MissionExecutionRequestState.PREPARED


def test_lifecycle_request_persistence_failure_leaves_no_request_or_enqueue(tmp_path: Path) -> None:
    class _FailingRequestPersistLifecycle(MissionLifecycleService):
        def _persist_execution_request(self, request):  # noqa: ANN001
            raise OSError("synthetic request persistence failure")

    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = _FailingRequestPersistLifecycle(kernel)

    with pytest.raises(OSError, match="synthetic request persistence failure"):
        lifecycle.create_mission(
            session_id="session_lifecycle",
            draft=_draft(),
            authority_summary=_summary(),
            approval_scope=_approval_scope(),
            policy=_policy(),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={"workspace": "."},
            workspace_ref="snapshot:unit",
            model_contract_ref="model_contract:unit",
        )

    record = kernel.list_missions()[0]
    assert record.status is OperatorMissionStatus.DRAFT
    assert lifecycle.list_execution_requests(record.mission_id) == []
    event_types = [event.event_type for event in kernel.store.load_events(record.mission_id)]
    assert "mission_execution_request_prepared" not in event_types
    assert "mission_queued" not in event_types


def test_lifecycle_request_prepared_event_failure_does_not_enqueue(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)
    original_append_event = kernel.store.append_event

    def failing_append_event(mission_id, *args, **kwargs):  # noqa: ANN001
        event_type = kwargs.get("event_type") if "event_type" in kwargs else args[0]
        if event_type == "mission_execution_request_prepared":
            raise RuntimeError("synthetic prepared event persistence failure")
        return original_append_event(mission_id, *args, **kwargs)

    monkeypatch.setattr(kernel.store, "append_event", failing_append_event)

    with pytest.raises(RuntimeError, match="synthetic prepared event persistence failure"):
        lifecycle.create_mission(
            session_id="session_lifecycle",
            draft=_draft(),
            authority_summary=_summary(),
            approval_scope=_approval_scope(),
            policy=_policy(),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={"workspace": "."},
            workspace_ref="snapshot:unit",
            model_contract_ref="model_contract:unit",
        )

    record = kernel.list_missions()[0]
    request = lifecycle.latest_execution_request(record.mission_id)
    assert record.status is OperatorMissionStatus.DRAFT
    assert request.prepared is True
    event_types = [event.event_type for event in kernel.store.load_events(record.mission_id)]
    assert "mission_execution_request_prepared" not in event_types
    assert "mission_queued" not in event_types
    assert lifecycle.derive_request_state(record.mission_id, request.request_id).state is MissionExecutionRequestState.PREPARED


def test_mark_request_claimed_appends_event_without_mutating_request_artifact(tmp_path: Path) -> None:
    kernel = MissionKernel(run_root=tmp_path / "runs")
    lifecycle = MissionLifecycleService(kernel)
    result = lifecycle.create_mission(
        session_id="session_lifecycle",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "."},
        workspace_ref="snapshot:unit",
        model_contract_ref="model_contract:unit",
    )
    before = lifecycle.load_execution_request(result.record.mission_id, result.execution_request.request_id)

    claimed = lifecycle.mark_request_claimed(result.record.mission_id, result.execution_request.request_id)

    after = lifecycle.load_execution_request(result.record.mission_id, result.execution_request.request_id)
    assert before == after
    assert claimed.state is MissionExecutionRequestState.CLAIMED
    assert lifecycle.derive_request_state(result.record.mission_id, result.execution_request.request_id).state is MissionExecutionRequestState.CLAIMED


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


def _approval_scope(*, allowed_actions: list[str] | None = None) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
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
