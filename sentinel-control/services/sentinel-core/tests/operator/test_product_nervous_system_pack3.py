from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequestState
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyDecision,
    ReadOnlyActionKind,
    ReadOnlyDecisionClient,
    ReadOnlyProductionSpineSession,
    ReadOnlyReportClient,
)
from sentinel.operator.replay import MissionReplayBuilder
from sentinel.operator.runtime_host import RuntimeHostStatus, SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import (
    DispatchStatus,
    ReadOnlyResearchAdapter,
    UnifiedExecutionAdapter,
    UnifiedExecutionDispatcher,
    UnifiedExecutionAdapterRegistry,
)


def test_pack3_product_route_executes_read_only_research_end_to_end(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "register", "path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": "src/commands.py", "start_line": 1, "line_count": 20}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
        report_text="Report cites {refs}: command registration risk is concentrated in src/commands.py.",
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.claimed is True
    assert pickup.dispatch_result is not None
    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert pickup.dispatch_result.adapter_id == "read_only_research_adapter"
    assert pickup.dispatch_result.receipt_refs
    assert pickup.dispatch_result.finalgate_refs
    assert pickup.dispatch_result.artifact_refs
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED
    state = host.lifecycle.derive_request_state(mission.record.mission_id, mission.execution_request.request_id)
    assert state.state is MissionExecutionRequestState.COMPLETED

    events = host.kernel.store.load_events(mission.record.mission_id)
    event_types = [event.event_type for event in events]
    assert event_types.index("mission_execution_request_claimed") < event_types.index("mission_dispatch_decision_persisted")
    assert event_types.index("mission_dispatch_decision_persisted") < event_types.index("mission_dispatch_started")
    assert event_types.index("mission_dispatch_started") < event_types.index("read_only_spine_session_started")
    assert event_types.index("read_only_spine_action_receipted") < event_types.index("read_only_report_generation_started")
    assert event_types.index("read_only_report_generation_completed") < event_types.index("read_only_spine_finalgate_certified")
    assert event_types.index("read_only_spine_finalgate_certified") < event_types.index("mission_dispatch_closeout_persisted")
    assert event_types.index("mission_dispatch_closeout_persisted") < event_types.index("mission_completed")

    replay_before_events = len(host.kernel.store.load_events(mission.record.mission_id))
    replay = MissionReplayBuilder(host.kernel.store).build(mission.record.mission_id)
    assert replay.reexecuted_actions is False
    assert len(host.kernel.store.load_events(mission.record.mission_id)) == replay_before_events

    assert _workspace_snapshot(workspace) == {
        "README.md": "# Fixture\nThis repo has command registration.\n",
        "secret": "directory",
        "secret/.env": "TOKEN=do-not-read\n",
        "src": "directory",
        "src/commands.py": "def register_commands(registry):\n    registry.add('inspect')\n",
        "src/runtime.py": "def run():\n    return 'ok'\n",
        "notes.md": "Architecture risk: command registration has no owner comment.\n",
        "link_escape": "symlink",
        "sentinel_internal": "directory",
        "sentinel_internal/blocked.md": "excluded\n",
    }


def test_pack3_14_approved_workspace_scope_allows_adapter_routed_read_only_receipts(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "register", "path": "."}),
            ReadOnlyDecision(
                action=ReadOnlyActionKind.READ_FILE_SEGMENT,
                arguments={"path": "src/commands.py", "start_line": 1, "line_count": 2},
            ),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
        report_text="Report cites {refs}: read-only adapter-routed workspace scope completed.",
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_14",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert pickup.dispatch_result.receipt_refs
    assert pickup.dispatch_result.finalgate_status == "accepted"
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED
    assert mission.authority.envelope.allowed_tools == ["read_only_research_adapter"]
    assert mission.authority.envelope.allowed_paths == [str(workspace.resolve())]
    receipts = _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")
    assert {receipt["action"] for receipt in receipts} >= {
        "list_directory",
        "search_text",
        "read_file_segment",
    }


def test_pack3_14_snapshot_root_alias_reaches_receipt_under_approved_workspace_scope(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "snapshot_root"}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_14_alias",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    receipts = _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")
    assert any(receipt["action"] == "list_directory" for receipt in receipts)


@pytest.mark.parametrize("path_value", ["../outside", str(Path("..") / "outside")])
def test_pack3_14_path_escape_still_blocks_without_fake_receipt(
    tmp_path: Path,
    path_value: str,
) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": path_value}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_14_escape",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.BLOCKED
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts") == []
    failed = _json_payloads(host, mission.record.mission_id, "read_only_spine", "failed_attempts")
    assert len(failed) == 1
    assert failed[0]["successful_action_receipt_ref"] is None


def test_pack3_14_absolute_outside_path_still_blocks_without_fake_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": str(outside.resolve())}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_14_absolute_escape",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts") == []
    failed = _json_payloads(host, mission.record.mission_id, "read_only_spine", "failed_attempts")
    assert len(failed) == 1
    assert failed[0]["successful_action_receipt_ref"] is None


def test_pack3_15_first_receipt_mode_stops_after_one_material_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "register", "path": "."}),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: should not be called.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_15",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={"stop_after_first_material_receipt": True},
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert decision_client.call_count == 1
    assert report_client.call_count == 0
    assert pickup.dispatch_result.finalgate_status == "accepted"
    assert len(pickup.dispatch_result.receipt_refs) == 1
    assert len(_json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")) == 1
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "reports") == []
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED
    assert _terminal_event_types(host, mission.record.mission_id) == ["mission_completed"]
    events = [event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)]
    assert "read_only_report_generation_started" not in events
    assert "read_only_spine_first_material_receipt_terminal" in events


def test_pack3_15_default_behavior_continues_after_first_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: default still reports.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert decision_client.call_count == 2
    assert report_client.call_count == 1
    assert len(_json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")) == 2
    events = [event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)]
    assert "read_only_report_generation_started" in events
    assert "read_only_spine_first_material_receipt_terminal" not in events


def test_pack3_15_first_receipt_mode_gate_denial_creates_no_fake_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "../outside"}),
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: should not be called.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_15_denied",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={"stop_after_first_material_receipt": True},
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert decision_client.call_count == 1
    assert report_client.call_count == 0
    assert pickup.dispatch_result.receipt_refs == []
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts") == []
    failed = _json_payloads(host, mission.record.mission_id, "read_only_spine", "failed_attempts")
    assert len(failed) == 1
    assert failed[0]["successful_action_receipt_ref"] is None


@pytest.mark.parametrize(
    ("decision", "expected_action"),
    [
        (
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            "list_directory",
        ),
        (
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "register", "path": "."}),
            "search_text",
        ),
        (
            ReadOnlyDecision(
                action=ReadOnlyActionKind.READ_FILE_SEGMENT,
                arguments={"path": "src/commands.py", "start_line": 1, "line_count": 2},
            ),
            "read_file_segment",
        ),
    ],
)
def test_pack3_17_low_friction_read_only_actions_execute_with_receipts_without_escalation(
    tmp_path: Path,
    decision: ReadOnlyDecision,
    expected_action: str,
) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient([decision, ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION)])
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: should not be called.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_17_low_friction",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "stop_after_first_material_receipt": True,
            "low_friction_read_only_power_mode": True,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert pickup.dispatch_result.finalgate_status == "accepted"
    assert decision_client.call_count == 1
    assert report_client.call_count == 0
    receipts = _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")
    assert len(receipts) == 1
    assert receipts[0]["action"] == expected_action
    events = host.kernel.store.load_events(mission.record.mission_id)
    low_friction_events = [
        event for event in events
        if event.event_type == "read_only_low_friction_gate_passed"
    ]
    assert len(low_friction_events) == 1
    assert low_friction_events[0].metadata["action"] == expected_action
    assert low_friction_events[0].metadata["human_escalation_required"] is False
    assert low_friction_events[0].metadata["authority_boundary"] == "approved_workspace_read_only"
    event_types = [event.event_type for event in events]
    assert event_types.index("read_only_low_friction_gate_passed") < event_types.index("read_only_spine_action_receipted")


@pytest.mark.parametrize("path_value", ["../outside", str(Path("..") / "outside")])
def test_pack3_17_low_friction_path_traversal_still_blocks_without_fake_receipt(
    tmp_path: Path,
    path_value: str,
) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": path_value}),
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
        ],
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_17_traversal_block",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "stop_after_first_material_receipt": True,
            "low_friction_read_only_power_mode": True,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.receipt_refs == []
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts") == []
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.BLOCKED


def test_pack3_17_low_friction_absolute_outside_path_still_blocks_without_fake_receipt(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": str(outside.resolve())}),
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
        ],
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3_17_absolute_block",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "stop_after_first_material_receipt": True,
            "low_friction_read_only_power_mode": True,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.receipt_refs == []
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts") == []


def test_pack3_17_low_friction_requires_first_receipt_read_only_route(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(tmp_path)
    host.start()

    with pytest.raises(ValueError, match="low_friction_read_only_power_mode"):
        host.lifecycle.create_mission(
            session_id="session_pack3_17_requires_first_receipt",
            draft=_draft(),
            authority_summary=_summary(),
            approval_scope=_attempt5j_approval_scope(workspace),
            policy=_policy(),
            capability_id="read_only_research",
            operation="inspect_repository",
            parameters={"workspace": "fixture"},
            workspace_ref=f"workspace:{workspace}",
            model_contract_ref="model_contract:fake_read_only_research",
            execution_options={"low_friction_read_only_power_mode": True},
        )


def test_pack3_17_default_strict_route_does_not_enter_low_friction_mode(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
    )
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    events = [event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)]
    assert "read_only_low_friction_gate_passed" not in events


def test_pack4a_model_led_autopilot_produces_three_receipts_without_report_lane_and_replays_pure(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    decision_client = _ContextRecordingDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "register", "path": "."}),
            ReadOnlyDecision(
                action=ReadOnlyActionKind.READ_FILE_SEGMENT,
                arguments={"path": "src/commands.py", "start_line": 1, "line_count": 2},
            ),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: should not be called.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack4a_autopilot",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "model_led_read_only_autopilot": True,
            "low_friction_read_only_power_mode": True,
            "max_material_receipts": 3,
            "max_provider_decision_calls": 3,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert pickup.dispatch_result.finalgate_status == "accepted"
    assert decision_client.call_count == 3
    assert report_client.call_count == 0
    receipts = _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")
    evidence = _json_payloads(host, mission.record.mission_id, "read_only_spine", "evidence")
    finalgate = _json_payloads(host, mission.record.mission_id, "read_only_spine", "finalgate")
    assert {receipt["action"] for receipt in receipts} == {"list_directory", "search_text", "read_file_segment"}
    assert len(evidence) == 3
    assert finalgate[0]["accepted"] is True
    assert finalgate[0]["reason"] == "model_led_read_only_autopilot_material_receipt_budget_reached"
    assert len(decision_client.contexts) == 3
    assert len(decision_client.contexts[1]["observations"]) == 1
    assert len(decision_client.contexts[2]["observations"]) == 2
    events = host.kernel.store.load_events(mission.record.mission_id)
    event_types = [event.event_type for event in events]
    receipt_event_actions = [
        event.metadata["action"]
        for event in events
        if event.event_type == "read_only_spine_action_receipted"
    ]
    assert receipt_event_actions == ["list_directory", "search_text", "read_file_segment"]
    assert event_types.count("read_only_low_friction_gate_passed") == 3
    assert "read_only_report_generation_started" not in event_types
    assert "read_only_spine_model_led_autopilot_terminal" in event_types
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED

    replay_before = _replay_counter_snapshot(host, mission.record.mission_id, decision_client, report_client)
    replay = ReadOnlyProductionSpineSession(
        cockpit=SimpleNamespace(kernel=host.kernel),
        mission_id=mission.record.mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient([]),
        low_friction_read_only_power_mode=True,
        model_led_read_only_autopilot=True,
        max_material_receipts=3,
        max_provider_decision_calls=3,
    ).build_replay()
    replay_after = _replay_counter_snapshot(host, mission.record.mission_id, decision_client, report_client)
    assert replay.reexecuted is False
    assert replay_before == replay_after
    assert _workspace_snapshot(workspace)["src/commands.py"] == "def register_commands(registry):\n    registry.add('inspect')\n"


def test_pack4a_finish_exploration_completes_without_fake_material_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: should not be called.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack4a_finish",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "model_led_read_only_autopilot": True,
            "low_friction_read_only_power_mode": True,
            "max_material_receipts": 3,
            "max_provider_decision_calls": 3,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert decision_client.call_count == 2
    assert report_client.call_count == 0
    receipts = _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")
    finalgate = _json_payloads(host, mission.record.mission_id, "read_only_spine", "finalgate")
    assert len(receipts) == 1
    assert receipts[0]["action"] == "list_directory"
    assert finalgate[0]["accepted"] is True
    assert finalgate[0]["reason"] == "model_led_read_only_autopilot_finish_exploration"


def test_pack4a_provider_decision_budget_stops_after_existing_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "register", "path": "."}),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: should not be called.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack4a_decision_budget",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "model_led_read_only_autopilot": True,
            "low_friction_read_only_power_mode": True,
            "max_material_receipts": 3,
            "max_provider_decision_calls": 1,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert decision_client.call_count == 1
    assert report_client.call_count == 0
    receipts = _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")
    finalgate = _json_payloads(host, mission.record.mission_id, "read_only_spine", "finalgate")
    assert len(receipts) == 1
    assert finalgate[0]["reason"] == "model_led_read_only_autopilot_provider_decision_budget_reached"


def test_pack4a_autopilot_unsafe_path_blocks_before_receipt(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "../outside"}),
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
        ]
    )
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: ReadOnlyReportClient(),
    )
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack4a_scope_block",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_attempt5j_approval_scope(workspace),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
        execution_options={
            "model_led_read_only_autopilot": True,
            "low_friction_read_only_power_mode": True,
            "max_material_receipts": 3,
            "max_provider_decision_calls": 3,
        },
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert decision_client.call_count == 1
    assert _json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts") == []
    assert _terminal_event_types(host, mission.record.mission_id) == ["mission_blocked"]


def test_pack3_coordinator_decision_is_persisted_before_adapter_execution(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    adapter = _AssertingAdapter()
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        adapter_registry=UnifiedExecutionAdapterRegistry({"read_only_research_adapter": adapter}),
    )
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.blocked_reason == "proof_receipt_missing"
    assert adapter.decision_file_existed_before_execution is True
    decision_payload = adapter.decision_payload_before_execution
    assert decision_payload["can_execute"] is False
    assert decision_payload["data_not_authority"] is True
    assert decision_payload["adapter_id"] == "read_only_research_adapter"
    assert "callable" not in json.dumps(decision_payload).lower()
    assert "runtime instance" not in json.dumps(decision_payload).lower()


def test_pack3_1_valid_persisted_receipts_report_and_finalgate_are_verified_before_completion(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(tmp_path)
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    mission_id = mission.record.mission_id
    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert host.kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED
    assert len(_json_payloads(host, mission_id, "dispatch_closeout")) == 1
    assert len(_json_payloads(host, mission_id, "read_only_spine", "receipts")) >= 2
    assert len(_json_payloads(host, mission_id, "read_only_spine", "reports")) == 1
    assert len(_json_payloads(host, mission_id, "read_only_spine", "finalgate")) == 1
    assert _terminal_event_types(host, mission_id)[-1] == "mission_completed"


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        ("fake_receipt", "proof_receipt_missing"),
        ("tamper_receipt", "proof_receipt_hash_mismatch"),
        ("missing_report", "proof_report_missing"),
        ("tamper_report", "proof_report_hash_mismatch"),
        ("fake_finalgate", "proof_finalgate_missing"),
        ("reject_finalgate", "proof_finalgate_rejected"),
    ],
)
def test_pack3_1_invalid_persisted_proof_blocks_completion(
    tmp_path: Path,
    mutator: str,
    expected_reason: str,
) -> None:
    workspace = _workspace(tmp_path)
    adapter = _MutatingProofAdapter(mutator)
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        adapter_registry=UnifiedExecutionAdapterRegistry({"read_only_research_adapter": adapter}),
    )
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.blocked_reason == expected_reason
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.BLOCKED
    assert len(_json_payloads(host, mission.record.mission_id, "dispatch_closeout")) == 1
    assert _terminal_event_types(host, mission.record.mission_id)[-1] == "mission_blocked"


def test_pack3_unknown_adapter_blocks_before_runtime_execution(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = SentinelRuntimeHost(run_root=tmp_path / "runs", adapter_registry=UnifiedExecutionAdapterRegistry({}))
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.blocked_reason == "unknown_adapter"
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.BLOCKED
    assert not (host.kernel.store.mission_dir(mission.record.mission_id) / "read_only_spine").exists()
    certificates = _json_payloads(host, mission.record.mission_id, "dispatch_terminal_certificates")
    assert len(certificates) == 1
    assert certificates[0]["accepted"] is False
    assert certificates[0]["reason_code"] == "unknown_adapter"
    assert len(_json_payloads(host, mission.record.mission_id, "read_only_spine", "receipts")) == 0
    assert _terminal_event_types(host, mission.record.mission_id)[-1] == "mission_blocked"


def test_pack3_1_success_and_failure_have_exact_terminal_counts(tmp_path: Path) -> None:
    success_workspace = _workspace(tmp_path / "success")
    success_host = _host(tmp_path / "success")
    success_host.start()
    success_mission = _create_mission(success_host, success_workspace)
    success_pickup = success_host.pump_daemon_once(success_mission.record.mission_id)

    assert success_pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert _terminal_certificate_count(success_host, success_mission.record.mission_id) == 1
    assert _terminal_event_types(success_host, success_mission.record.mission_id) == ["mission_completed"]
    assert _event_count(success_host, success_mission.record.mission_id, "mission_dispatch_started") == 1
    assert len(_json_payloads(success_host, success_mission.record.mission_id, "dispatch_closeout")) == 1

    failure_workspace = _workspace(tmp_path / "failure")
    failure_host = SentinelRuntimeHost(run_root=tmp_path / "failure" / "runs", adapter_registry=UnifiedExecutionAdapterRegistry({}))
    failure_host.start()
    failure_mission = _create_mission(failure_host, failure_workspace)
    failure_pickup = failure_host.pump_daemon_once(failure_mission.record.mission_id)

    assert failure_pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert _terminal_certificate_count(failure_host, failure_mission.record.mission_id) == 1
    assert _terminal_event_types(failure_host, failure_mission.record.mission_id) == ["mission_blocked"]
    assert _event_count(failure_host, failure_mission.record.mission_id, "mission_dispatch_started") == 0
    assert len(_json_payloads(failure_host, failure_mission.record.mission_id, "dispatch_closeout")) == 1


def test_pack3_1_replay_has_zero_execution_and_write_deltas(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ]
    )
    report_client = ReadOnlyReportClient(report_template="Report cites {refs}: replay proof.")
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: decision_client,
        read_only_report_client_factory=lambda _request, _authority: report_client,
    )
    host.start()
    mission = _create_mission(host, workspace)
    pickup = host.pump_daemon_once(mission.record.mission_id)
    before = _replay_counter_snapshot(host, mission.record.mission_id, decision_client, report_client)

    replay = MissionReplayBuilder(host.kernel.store).build(mission.record.mission_id)

    after = _replay_counter_snapshot(host, mission.record.mission_id, decision_client, report_client)
    assert pickup.dispatch_result.status is DispatchStatus.COMPLETED
    assert replay.reexecuted_actions is False
    assert after == before


def test_pack3_1_dispatcher_revalidates_expired_authority_itself(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    adapter = _CountingAdapter()
    host = SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        adapter_registry=UnifiedExecutionAdapterRegistry({"read_only_research_adapter": adapter}),
    )
    host.start()
    mission = _create_mission(host, workspace)
    request = host.lifecycle.latest_execution_request(mission.record.mission_id)
    expired = mission.authority.envelope.model_copy(update={"expires_at": mission.authority.envelope.created_at})

    result = host.dispatcher.dispatch(request=request, authority=expired)

    assert result.status is DispatchStatus.BLOCKED
    assert result.blocked_reason == "authority_inactive"
    assert adapter.execute_count == 0
    assert _terminal_event_types(host, mission.record.mission_id)[-1] == "mission_blocked"


def test_pack3_1_llm_product_host_requires_provider_execution_factories(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="read_only_provider_execution_factories_required"):
        SentinelRuntimeHost(run_root=tmp_path / "runs", require_read_only_model_clients=True)


def test_pack3_unauthorized_capability_blocks_before_execution(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(tmp_path)
    host.start()
    mission = host.lifecycle.create_mission(
        session_id="session_pack3",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="browser_live_operator",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.blocked_reason in {"connection_not_product_reachable", "operation_not_supported"}
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.BLOCKED


def test_pack3_revoked_authority_blocks_before_dispatch(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(tmp_path)
    host.start()
    mission = _create_mission(host, workspace)
    host.authority_issuer.revoke(
        mission.record.mission_id,
        envelope_ref=mission.authority_record.envelope_id,
        reason="operator revoked before dispatch",
    )

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result is None
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.REVOKED
    assert "mission_dispatch_started" not in [event.event_type for event in host.kernel.store.load_events(mission.record.mission_id)]


def test_pack3_report_lane_rejects_unknown_evidence_and_mutation_claims(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
        report_text="I modified the repository using ev_unknown.",
        evidence_refs=["ev_unknown"],
    )
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.finalgate_status == "rejected"
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.BLOCKED
    events = host.kernel.store.load_events(mission.record.mission_id)
    assert any(event.event_type == "read_only_spine_failed_attempt_recorded" for event in events)


def test_pack3_sensitive_and_excluded_paths_remain_blocked(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    host = _host(
        tmp_path,
        decisions=[
            ReadOnlyDecision(action=ReadOnlyActionKind.SEARCH_TEXT, arguments={"query": "TOKEN", "path": "secret"}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
        ],
    )
    host.start()
    mission = _create_mission(host, workspace)

    pickup = host.pump_daemon_once(mission.record.mission_id)

    assert pickup.dispatch_result.status is DispatchStatus.BLOCKED
    assert pickup.dispatch_result.finalgate_status == "rejected"
    evidence_root = host.kernel.store.mission_dir(mission.record.mission_id) / "read_only_spine" / "evidence"
    if evidence_root.exists():
        assert "TOKEN" not in "\n".join(path.read_text(encoding="utf-8") for path in evidence_root.glob("*.json"))


def _host(
    tmp_path: Path,
    *,
    decisions: list[ReadOnlyDecision] | None = None,
    report_text: str = "Report cites {refs}: architecture risk identified.",
    evidence_refs: list[str] | None = None,
) -> SentinelRuntimeHost:
    return SentinelRuntimeHost(
        run_root=tmp_path / "runs",
        read_only_decision_client_factory=lambda _request, _authority: ReadOnlyDecisionClient(
            decisions
            or [
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
            ]
        ),
        read_only_report_client_factory=lambda _request, _authority: ReadOnlyReportClient(
            report_template=report_text,
            forced_evidence_refs=evidence_refs,
        ),
    )


def _create_mission(host: SentinelRuntimeHost, workspace: Path):
    return host.lifecycle.create_mission(
        session_id="session_pack3",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(),
        policy=_policy(),
        capability_id="read_only_research",
        operation="inspect_repository",
        parameters={"workspace": "fixture"},
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:fake_read_only_research",
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    (root / "src").mkdir(parents=True)
    (root / "secret").mkdir()
    (root / "sentinel_internal").mkdir()
    (root / "README.md").write_text("# Fixture\nThis repo has command registration.\n", encoding="utf-8")
    (root / "src" / "commands.py").write_text("def register_commands(registry):\n    registry.add('inspect')\n", encoding="utf-8")
    (root / "src" / "runtime.py").write_text("def run():\n    return 'ok'\n", encoding="utf-8")
    (root / "secret" / ".env").write_text("TOKEN=do-not-read\n", encoding="utf-8")
    (root / "notes.md").write_text("Architecture risk: command registration has no owner comment.\n", encoding="utf-8")
    (root / "sentinel_internal" / "blocked.md").write_text("excluded\n", encoding="utf-8")
    try:
        (root / "link_escape").symlink_to(tmp_path / "outside.txt")
    except OSError:
        (root / "link_escape").write_text("symlink", encoding="utf-8")
    return root


def _workspace_snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[rel] = "symlink"
        elif path.is_dir():
            result[rel] = "directory"
        else:
            result[rel] = path.read_text(encoding="utf-8")
    return result


def _draft() -> MissionDraft:
    return MissionDraft(
        title="Read-only repository inspection",
        objective="Inspect a disposable repository and produce an evidence-linked technical report.",
        expected_artifacts=["evidence-linked report"],
    )


def _summary() -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell", "browser_click", "credential_access"],
        summary="Read-only repository research only.",
    )


def _policy() -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell", "browser_click", "credential_access"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=12,
        max_cost_usd=0.0,
    )


def _approval_scope() -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell", "browser_click", "credential_access"],
        allowed_paths=["."],
        max_duration_minutes=15,
        max_actions=12,
        max_cost_usd=0.0,
    )


def _attempt5j_approval_scope(workspace: Path) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_research_adapter"],
        allowed_actions=["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell", "browser_click", "credential_access", "delete_file"],
        allowed_paths=[str(workspace.resolve())],
        max_duration_minutes=15,
        max_actions=12,
        max_cost_usd=0.0,
    )


class _ContextRecordingDecisionClient(ReadOnlyDecisionClient):
    def __init__(self, decisions: list[ReadOnlyDecision]) -> None:
        super().__init__(decisions)
        self.contexts: list[dict[str, Any]] = []

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        self.contexts.append(json.loads(json.dumps(context, sort_keys=True, default=str)))
        return super().complete(context)


class _AssertingAdapter(UnifiedExecutionAdapter):
    adapter_id = "read_only_research_adapter"
    capability_id = "read_only_research"
    operation = "inspect_repository"

    def __init__(self) -> None:
        self.decision_file_existed_before_execution = False
        self.decision_payload_before_execution: dict[str, Any] = {}

    def execute(self, request, decision, authority, context):
        path = context.decision_store.decision_path(request.mission_id, decision.decision_id)
        self.decision_file_existed_before_execution = path.exists()
        self.decision_payload_before_execution = json.loads(path.read_text(encoding="utf-8"))
        return context.completed_result(
            request=request,
            decision=decision,
            adapter_id=self.adapter_id,
            receipt_refs=["receipt_fake"],
            finalgate_refs=["finalgate_fake"],
            artifact_refs=["artifact_fake"],
        )


class _MutatingProofAdapter(ReadOnlyResearchAdapter):
    def __init__(self, mutator: str) -> None:
        super().__init__(
            decision_client_factory=lambda _request, _authority: ReadOnlyDecisionClient(
                [
                    ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                    ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_EXPLORATION),
                ]
            ),
            report_client_factory=lambda _request, _authority: ReadOnlyReportClient(
                report_template="Report cites {refs}: proof verifier target.",
            ),
        )
        self.mutator = mutator

    def execute(self, request, decision, authority, context):  # noqa: ANN001, ANN201
        result = super().execute(request, decision, authority, context)
        mission_dir = context.kernel.store.mission_dir(request.mission_id)
        if self.mutator == "fake_receipt":
            return result.model_copy(update={"receipt_refs": ["missing_receipt_ref"]})
        if self.mutator == "tamper_receipt":
            receipt_path = mission_dir / "read_only_spine" / "receipts" / f"{result.receipt_refs[0]}.json"
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["status"] = "tampered"
            receipt_path.write_text(json.dumps(payload), encoding="utf-8")
        elif self.mutator == "missing_report":
            report_path = mission_dir / "read_only_spine" / "reports" / f"{result.artifact_refs[0]}.json"
            report_path.unlink()
        elif self.mutator == "tamper_report":
            report_path = mission_dir / "read_only_spine" / "reports" / f"{result.artifact_refs[0]}.json"
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            payload["safe_report"] = "tampered report"
            report_path.write_text(json.dumps(payload), encoding="utf-8")
        elif self.mutator == "fake_finalgate":
            return result.model_copy(update={"finalgate_refs": ["missing_finalgate_ref"]})
        elif self.mutator == "reject_finalgate":
            finalgate_path = mission_dir / "read_only_spine" / "finalgate" / f"{result.finalgate_refs[0]}.json"
            payload = json.loads(finalgate_path.read_text(encoding="utf-8"))
            payload["accepted"] = False
            payload["status"] = "blocked"
            payload["certificate_hash"] = ""
            from sentinel.agent.model_execution.redaction import stable_hash

            payload["certificate_hash"] = stable_hash(payload)
            finalgate_path.write_text(json.dumps(payload), encoding="utf-8")
        return result


class _CountingAdapter(UnifiedExecutionAdapter):
    adapter_id = "read_only_research_adapter"
    capability_id = "read_only_research"
    operation = "inspect_repository"

    def __init__(self) -> None:
        self.execute_count = 0

    def execute(self, request, decision, authority, context):  # noqa: ANN001, ANN201
        self.execute_count += 1
        return context.completed_result(
            request=request,
            decision=decision,
            adapter_id=self.adapter_id,
            receipt_refs=["receipt_fake"],
            finalgate_refs=["finalgate_fake"],
            artifact_refs=["artifact_fake"],
        )


def _json_payloads(host: SentinelRuntimeHost, mission_id: str, *parts: str) -> list[dict[str, Any]]:
    root = host.kernel.store.mission_dir(mission_id) / Path(*parts)
    if not root.exists():
        return []
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(root.glob("*.json"))]


def _event_count(host: SentinelRuntimeHost, mission_id: str, event_type: str) -> int:
    return sum(1 for event in host.kernel.store.load_events(mission_id) if event.event_type == event_type)


def _terminal_event_types(host: SentinelRuntimeHost, mission_id: str) -> list[str]:
    mission_terminal_types = {"mission_completed", "mission_blocked", "mission_failed", "mission_killed", "mission_revoked"}
    return [
        event.event_type
        for event in host.kernel.store.load_events(mission_id)
        if event.event_type in mission_terminal_types
    ]


def _terminal_certificate_count(host: SentinelRuntimeHost, mission_id: str) -> int:
    return len(_json_payloads(host, mission_id, "read_only_spine", "finalgate")) + len(
        _json_payloads(host, mission_id, "dispatch_terminal_certificates")
    )


def _replay_counter_snapshot(
    host: SentinelRuntimeHost,
    mission_id: str,
    decision_client: ReadOnlyDecisionClient,
    report_client: ReadOnlyReportClient,
) -> dict[str, object]:
    return {
        "coordinator_calls": getattr(host.coordinator, "call_count", None),
        "decision_client_calls": decision_client.call_count,
        "report_client_calls": report_client.call_count,
        "events": len(host.kernel.store.load_events(mission_id)),
        "receipt_writes": len(_json_payloads(host, mission_id, "read_only_spine", "receipts")),
        "failed_attempt_writes": len(_json_payloads(host, mission_id, "read_only_spine", "failed_attempts")),
        "report_artifact_writes": len(_json_payloads(host, mission_id, "read_only_spine", "reports")),
        "finalgate_writes": len(_json_payloads(host, mission_id, "read_only_spine", "finalgate")),
        "dispatch_decision_writes": len(_json_payloads(host, mission_id, "execution_decisions")),
        "dispatch_closeout_writes": len(_json_payloads(host, mission_id, "dispatch_closeout")),
        "dispatch_terminal_writes": len(_json_payloads(host, mission_id, "dispatch_terminal_certificates")),
        "mission_status": host.kernel.store.load_record(mission_id).status.value,
        "timeline_ok": host.kernel.store.verify_timeline(mission_id),
    }
