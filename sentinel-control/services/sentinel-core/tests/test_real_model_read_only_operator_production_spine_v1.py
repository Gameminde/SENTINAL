from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.models import OperatorConversationState, OperatorMissionStatus, OperatorMode
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyActionKind,
    ReadOnlyDecision,
    ReadOnlyDecisionClient,
    ReadOnlyProductionSpineSession,
    ReadOnlySpineError,
)
from sentinel.shared.enums import MissionMode, MissionType


def test_fake_model_read_only_session_uses_cockpit_mission_kernel_receipts_finalgate_and_replay(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n\nProof-oriented local AI runtime.\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.QUEUED

    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(
                action=ReadOnlyActionKind.READ_FILE_SEGMENT,
                arguments={"path": "README.md", "start_line": 1, "line_count": 3},
            ),
            ReadOnlyDecision(
                action=ReadOnlyActionKind.FINISH_REPORT,
                operator_message="README was inspected through read-only evidence.",
            ),
        ]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run()
    replay = session.build_replay()

    assert result.status == "completed"
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED
    assert len(result.receipt_refs) == 3
    assert len(result.finalgate_refs) == 1
    assert result.finalgate_status == "accepted"
    assert replay.mission_id == mission_id
    assert replay.receipt_refs == result.receipt_refs
    assert replay.finalgate_refs == result.finalgate_refs
    assert replay.reexecuted is False
    assert replay.model_calls_before_replay == decision_client.call_count
    assert replay.model_calls_after_replay == decision_client.call_count
    assert replay.tool_calls_before_replay == session.tool_call_count
    assert replay.tool_calls_after_replay == session.tool_call_count
    assert decision_client.call_count == 3

    events = cockpit.kernel.store.load_events(mission_id)
    event_types = [event.event_type for event in events]
    assert "read_only_spine_session_started" in event_types
    assert event_types.count("read_only_spine_action_receipted") == 3
    assert event_types.count("read_only_spine_finalgate_certified") == 1


def test_killed_mission_blocks_before_model_or_tool_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    cockpit.handle("kill")

    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run()
    replay = session.build_replay()

    assert result.status == "blocked"
    assert result.blocked_reason == "operator_mission_terminal:killed"
    assert result.receipt_refs == []
    assert result.finalgate_status == "rejected"
    assert replay.receipt_refs == []
    assert replay.finalgate_refs == result.finalgate_refs
    assert decision_client.call_count == 0

    events = cockpit.kernel.store.load_events(mission_id)
    event_types = [event.event_type for event in events]
    assert "read_only_spine_blocked" in event_types
    assert "read_only_spine_action_receipted" not in event_types


def test_kill_after_model_response_blocks_before_action_receipt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = _KillingDecisionClient(
        cockpit,
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})],
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run()

    assert result.status == "blocked"
    assert result.blocked_reason == "operator_mission_terminal:killed"
    assert result.receipt_refs == []
    assert decision_client.call_count == 1
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types
    assert event_types.count("read_only_spine_finalgate_certified") == 1


def test_kill_after_tool_result_blocks_before_receipt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = _KillingAfterToolSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "operator_mission_terminal:killed"
    assert result.receipt_refs == []
    assert session.tool_call_count == 1
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


def test_authority_revoked_after_model_response_blocks_before_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    envelope = _authority_envelope(mission_id)
    decision_client = _RevokingAuthorityDecisionClient(
        envelope,
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})],
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(envelope=envelope)

    assert result.status == "blocked"
    assert result.blocked_reason == "mission_authority_envelope_inactive"
    assert decision_client.call_count == 1
    assert session.tool_call_count == 0
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


def test_uncertified_telemetry_blocks_before_model_or_tool_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    cockpit.kernel.telemetry_sink.mark_degraded("test_uncertified_telemetry")
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run()

    assert result.status == "blocked"
    assert result.blocked_reason == "telemetry_certified_mode_required"
    assert result.receipt_refs == []
    assert decision_client.call_count == 0


def test_write_action_is_rejected_by_decision_schema() -> None:
    with pytest.raises(ValidationError):
        ReadOnlyDecision.model_validate({"action": "write_file", "arguments": {"path": "README.md"}})


def test_read_only_session_can_be_mediated_by_existing_agentruntime_bridge(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_REPORT, operator_message="done"),
            ]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "completed"
    assert result.bridge_status == "completed"
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.COMPLETED
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "agentruntime_result" in event_types
    assert "read_only_spine_session_started" in event_types
    assert event_types.count("read_only_spine_finalgate_certified") == 1
    finalgate_events = [
        event for event in cockpit.kernel.store.load_events(mission_id)
        if event.event_type == "read_only_spine_finalgate_certified"
    ]
    assert result.finalgate_refs == finalgate_events[0].finalgate_certificate_refs


def test_read_file_segment_exposes_bounded_safe_excerpt_to_next_model_turn(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "src").mkdir()
    (workspace / "src" / "parser.py").write_text(
        "\n".join(
            [
                "def parse_event(raw):",
                "    return {'type': raw.get('kind'), 'payload': raw.get('payload')}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = _ExcerptAwareDecisionClient()
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "completed"
    assert decision_client.saw_excerpt is True


def test_read_file_segment_safe_excerpt_is_redacted_and_bounded(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.md").write_text(
        "API_KEY=sk-unit-secret-1234567890\n" + ("x" * 5_000),
        encoding="utf-8",
    )

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient([]),
    )
    observation = session._execute_read_only_action(
        ReadOnlyDecision(
            action=ReadOnlyActionKind.READ_FILE_SEGMENT,
            arguments={"path": "notes.md", "start_line": 1, "line_count": 2},
        )
    )

    assert "sk-unit-secret-1234567890" not in observation["safe_excerpt"]
    assert "[REDACTED_SECRET]" in observation["safe_excerpt"]
    assert observation["safe_excerpt_char_count"] == 4_000
    assert observation["safe_excerpt_truncated"] is True


@pytest.mark.parametrize(
    ("action", "arguments", "expected_failure"),
    [
        (ReadOnlyActionKind.READ_FILE_SEGMENT, {"path": "."}, "READ_TARGET_WRONG_KIND"),
        (ReadOnlyActionKind.LIST_DIRECTORY, {"path": "README.md"}, "READ_TARGET_WRONG_KIND"),
        (ReadOnlyActionKind.READ_FILE_SEGMENT, {"path": "missing.md"}, "READ_TARGET_NOT_FOUND"),
        (
            ReadOnlyActionKind.READ_FILE_SEGMENT,
            {"path": "README.md", "start_line": 0, "line_count": 1},
            "READ_SEGMENT_INVALID",
        ),
        (
            ReadOnlyActionKind.READ_FILE_SEGMENT,
            {"path": "README.md", "start_line": 1, "line_count": 0},
            "READ_SEGMENT_INVALID",
        ),
    ],
)
def test_read_only_domain_failures_are_typed_checkpointed_and_finalgated(
    tmp_path: Path,
    action: ReadOnlyActionKind,
    arguments: dict[str, object],
    expected_failure: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    session, result, replay = _run_blocked_session(
        tmp_path,
        workspace,
        ReadOnlyDecision(action=action, arguments=arguments),
    )

    _assert_blocked_terminal_proof(session, result, replay, expected_failure=expected_failure)
    checkpoint = _only_json_payload(session, "decision_checkpoints")
    assert checkpoint["canonical_action_name"] == action.value
    assert checkpoint["argument_key_names"] == sorted(arguments)
    assert checkpoint["parser_status"] == "parsed"
    assert checkpoint["canonicalization_status"] == "canonicalized"
    assert checkpoint["runtime_phase"] == "post_parse_pre_gate"
    assert "arguments" not in checkpoint
    failed_attempt = _only_json_payload(session, "failed_attempts")
    assert failed_attempt["failure_code"] == expected_failure
    assert failed_attempt["successful_action_receipt_ref"] is None


def test_snapshot_change_between_validation_and_read_is_typed_and_finalgated(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = _DeleteTargetBeforeReadSession(
        target,
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": "README.md"})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()

    _assert_blocked_terminal_proof(session, result, replay, expected_failure="SNAPSHOT_CHANGED")


def test_known_backend_exception_is_typed_without_generic_bridge_failure(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = _KnownBackendFailingSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()

    _assert_blocked_terminal_proof(session, result, replay, expected_failure="READ_BACKEND_FAILURE")


def test_unexpected_executor_exception_is_redacted_and_typed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = _UnexpectedExecutorFailingSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()

    _assert_blocked_terminal_proof(session, result, replay, expected_failure="READ_INTERNAL_RUNTIME_FAILURE")
    failed_attempt = _only_json_payload(session, "failed_attempts")
    assert failed_attempt["exception_class"] == "RuntimeError"
    assert "raw provider payload" not in json.dumps(failed_attempt)


def test_receipt_persistence_exception_produces_failed_attempt_and_rejected_finalgate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = _ReceiptPersistenceFailingSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()

    _assert_blocked_terminal_proof(session, result, replay, expected_failure="RECEIPT_PERSISTENCE_FAILED")
    assert _json_payloads(session, "receipts") == []
    assert len(_json_payloads(session, "failed_attempts")) == 1


def test_finalgate_persistence_exception_writes_emergency_terminal_record(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = _FinalGatePersistenceFailingSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": "missing.md"})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()

    assert result.status == "blocked"
    assert result.blocked_reason == "READ_TARGET_NOT_FOUND"
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED
    assert result.finalgate_refs == []
    emergency = _only_json_payload(session, "emergency_terminal")
    assert emergency["normal_finalgate_persistence_failed"] is True
    assert emergency["accepted"] is False
    assert emergency["mission_id"] == mission_id
    assert replay.emergency_terminal_count == 1
    assert replay.emergency_terminal_writes_before_replay == replay.emergency_terminal_writes_after_replay


def test_wrong_authority_envelope_blocks_before_read_only_runtime_call(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope("wrong_mission"))

    assert result.status == "blocked"
    assert result.bridge_status == "blocked"
    assert result.blocked_reason == "mission_identity_mismatch"
    assert decision_client.call_count == 0
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "agentruntime_blocked" in event_types
    assert "read_only_spine_action_receipted" not in event_types


def test_revoked_authority_envelope_blocks_before_read_only_runtime_call(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(
        envelope=_authority_envelope(mission_id).model_copy(update={"revoked_at": datetime.now(UTC)})
    )

    assert result.status == "blocked"
    assert result.bridge_status == "blocked"
    assert result.blocked_reason == "mission_authority_envelope_inactive"
    assert decision_client.call_count == 0


def test_expired_authority_envelope_blocks_before_read_only_runtime_call(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(
        envelope=_authority_envelope(mission_id).model_copy(
            update={"created_at": datetime.now(UTC) - timedelta(hours=2), "max_duration_minutes": 1}
        )
    )

    assert result.status == "blocked"
    assert result.bridge_status == "blocked"
    assert result.blocked_reason == "mission_authority_envelope_inactive"
    assert decision_client.call_count == 0


def test_terminal_report_with_unsupported_action_claim_is_rejected_by_finalgate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(
                    action=ReadOnlyActionKind.FINISH_REPORT,
                    operator_message="I wrote README.md and sent the report by email.",
                ),
            ]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.bridge_status == "blocked"
    assert result.blocked_reason == "terminal_report_unsupported_action_claim"
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert event_types.count("read_only_spine_finalgate_certified") == 1
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED


def test_empty_terminal_report_is_rejected_by_finalgate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_REPORT, operator_message="")]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "terminal_report_empty"
    assert result.receipt_refs == []


def test_terminal_report_with_unknown_evidence_ref_is_rejected_by_finalgate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(
                    action=ReadOnlyActionKind.FINISH_REPORT,
                    operator_message="Directory evidence supports the report.",
                    evidence_refs=["readonly_evidence_foreign"],
                ),
            ]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "terminal_report_unknown_evidence_ref"
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert event_types.count("read_only_spine_finalgate_certified") == 1
    assert "read_only_spine_action_receipted" in event_types


def test_model_decision_error_is_classified_without_tool_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=_FailingDecisionClient(),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.bridge_status == "blocked"
    assert result.blocked_reason == "model_decision_error"
    assert result.receipt_refs == []
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


def test_model_decision_timeout_is_classified_without_tool_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=_TimeoutDecisionClient(),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "model_decision_timeout"
    assert result.receipt_refs == []
    assert session.tool_call_count == 0
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


def test_authority_scope_narrowing_uses_gate_sequence_before_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )
    narrowed = _authority_envelope(mission_id).model_copy(update={"allowed_tools": []})

    result = session.run_via_agent_runtime(envelope=narrowed)

    assert result.status == "blocked"
    assert result.blocked_reason == "gate_sequence:out_of_scope:escalate"
    assert decision_client.call_count == 1
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types
    assert "read_only_spine_finalgate_certified" in event_types


def test_replay_records_zero_model_and_tool_call_delta(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [
            ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
            ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_REPORT, operator_message="done"),
        ]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )
    session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    replay = session.build_replay()

    assert replay.model_calls_after_replay - replay.model_calls_before_replay == 0
    assert replay.tool_calls_after_replay - replay.tool_calls_before_replay == 0
    assert replay.receipt_writes_after_replay - replay.receipt_writes_before_replay == 0
    assert replay.finalgate_writes_after_replay - replay.finalgate_writes_before_replay == 0


def test_replay_rejects_missing_receipt_artifact(tmp_path: Path) -> None:
    session, mission_id = _completed_read_only_session(tmp_path)
    receipt_path = _receipt_path(session, mission_id, session.build_replay().receipt_refs[0])
    receipt_path.unlink()

    with pytest.raises(ReadOnlySpineError, match="read_only_replay_missing_receipt"):
        session.build_replay()


def test_replay_rejects_tampered_receipt_hash(tmp_path: Path) -> None:
    session, mission_id = _completed_read_only_session(tmp_path)
    receipt_path = _receipt_path(session, mission_id, session.build_replay().receipt_refs[0])
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["status"] = "tampered"
    receipt_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ReadOnlySpineError, match="read_only_replay_receipt_hash_mismatch"):
        session.build_replay()


def test_replay_rejects_cross_mission_receipt_ref(tmp_path: Path) -> None:
    session, mission_id = _completed_read_only_session(tmp_path)
    receipt_path = _receipt_path(session, mission_id, session.build_replay().receipt_refs[0])
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["mission_id"] = "mission_foreign"
    payload["receipt_hash"] = ""
    receipt_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ReadOnlySpineError, match="read_only_replay_receipt_mission_mismatch"):
        session.build_replay()


def test_replay_rejects_tampered_finalgate_certificate(tmp_path: Path) -> None:
    session, mission_id = _completed_read_only_session(tmp_path)
    finalgate_path = _finalgate_path(session, mission_id, session.build_replay().finalgate_refs[0])
    payload = json.loads(finalgate_path.read_text(encoding="utf-8"))
    payload["accepted"] = False
    finalgate_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ReadOnlySpineError, match="read_only_replay_finalgate_hash_mismatch"):
        session.build_replay()


def test_replay_rejects_cross_mission_finalgate_certificate(tmp_path: Path) -> None:
    session, mission_id = _completed_read_only_session(tmp_path)
    finalgate_path = _finalgate_path(session, mission_id, session.build_replay().finalgate_refs[0])
    payload = json.loads(finalgate_path.read_text(encoding="utf-8"))
    payload["mission_id"] = "mission_foreign"
    finalgate_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ReadOnlySpineError, match="read_only_replay_finalgate_mission_mismatch"):
        session.build_replay()


def test_replay_rejects_injected_receipt_event_after_terminal_state(tmp_path: Path) -> None:
    session, mission_id = _completed_read_only_session(tmp_path)
    session.kernel.store.append_event(
        mission_id,
        event_type="read_only_spine_action_receipted",
        safe_summary="Injected stale receipt event.",
        receipt_refs=["readonly_receipt_injected"],
    )

    with pytest.raises(ReadOnlySpineError, match="read_only_replay_missing_receipt"):
        session.build_replay()


@pytest.mark.parametrize("unsafe_path", ["../outside.txt", "C:/Windows/win.ini", "//server/share/file.txt"])
def test_read_only_path_escape_is_blocked_before_receipt(tmp_path: Path, unsafe_path: str) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": unsafe_path})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.receipt_refs == []
    assert session.tool_call_count == 0
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


@pytest.mark.parametrize("sensitive_path", [".env", ".git/config"])
def test_read_only_sensitive_snapshot_path_is_blocked_before_receipt(tmp_path: Path, sensitive_path: str) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / sensitive_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("SECRET_TOKEN=do-not-read", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": sensitive_path})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "snapshot_sensitive_path_blocked"
    assert result.receipt_refs == []
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


def test_read_only_explicit_output_directory_exclusion_is_blocked_before_receipt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output_dir = workspace / "diagnostic_output"
    output_dir.mkdir()
    (output_dir / "internal_report.md").write_text("hidden rubric", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": "diagnostic_output/internal_report.md"})]
        ),
        excluded_paths=["diagnostic_output"],
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "snapshot_excluded_path_blocked"
    assert result.receipt_refs == []


def test_read_only_symlink_escape_is_blocked_before_receipt(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("outside", encoding="utf-8")
    link = workspace / "linked_outside"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable on this Windows environment")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": "linked_outside/secret.txt"})]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason in {
        "snapshot_path_escape_blocked",
        "gate_sequence:out_of_scope:escalate",
    }
    assert result.receipt_refs == []


def test_snapshot_drift_after_model_response_blocks_before_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = _DriftingDecisionClient(
        target,
        [ReadOnlyDecision(action=ReadOnlyActionKind.READ_FILE_SEGMENT, arguments={"path": "README.md"})],
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "SNAPSHOT_CHANGED"
    assert decision_client.call_count == 1
    assert session.tool_call_count == 0
    event_types = [event.event_type for event in cockpit.kernel.store.load_events(mission_id)]
    assert "read_only_spine_action_receipted" not in event_types


def test_deadline_exhausted_before_model_call_blocks_without_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
        deadline_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "deadline_exhausted"
    assert decision_client.call_count == 0
    assert session.tool_call_count == 0


def test_deadline_exhausted_after_model_response_blocks_before_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")
    times = [
        datetime.now(UTC),
        datetime.now(UTC),
        datetime.now(UTC),
        datetime.now(UTC) + timedelta(seconds=10),
    ]

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyDecisionClient(
        [ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."})]
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
        deadline_at=datetime.now(UTC) + timedelta(seconds=1),
        now_provider=lambda: times.pop(0) if times else datetime.now(UTC) + timedelta(seconds=10),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "blocked"
    assert result.blocked_reason == "deadline_exhausted"
    assert decision_client.call_count == 1
    assert session.tool_call_count == 0


def test_duplicate_read_only_observation_reuses_evidence_ref_and_marks_duplicate(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")

    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_REPORT, operator_message="done"),
            ]
        ),
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))

    assert result.status == "completed"
    evidence_dir = cockpit.kernel.store.mission_dir(mission_id) / "read_only_spine" / "evidence"
    assert len(list(evidence_dir.glob("*.json"))) == 1
    action_events = [
        event for event in cockpit.kernel.store.load_events(mission_id)
        if event.event_type == "read_only_spine_action_receipted"
    ]
    assert action_events[0].receipt_refs != action_events[1].receipt_refs
    assert action_events[0].metadata["evidence_refs"] == action_events[1].metadata["evidence_refs"]
    assert action_events[0].metadata["duplicate_evidence"] is False
    assert action_events[1].metadata["duplicate_evidence"] is True


def _started_cockpit(run_root: Path, *, telemetry_sink: object | None = None) -> LLMLiveOperatorCockpit:
    cockpit = LLMLiveOperatorCockpit(
        run_root=run_root,
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=_SequenceClient(_mission_output()),
        telemetry_sink=telemetry_sink,
    )
    draft = cockpit.handle("Inspect this repository in read-only mode.")
    assert draft.state is OperatorConversationState.AWAITING_START_CONFIRMATION
    started = cockpit.handle("start")
    assert started.state is OperatorConversationState.MISSION_QUEUED
    return cockpit


def _completed_read_only_session(tmp_path: Path) -> tuple[ReadOnlyProductionSpineSession, str]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Sentinel\n", encoding="utf-8")
    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient(
            [
                ReadOnlyDecision(action=ReadOnlyActionKind.LIST_DIRECTORY, arguments={"path": "."}),
                ReadOnlyDecision(action=ReadOnlyActionKind.FINISH_REPORT, operator_message="done"),
            ]
        ),
    )
    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    assert result.status == "completed"
    return session, mission_id


def _receipt_path(session: ReadOnlyProductionSpineSession, mission_id: str, receipt_ref: str) -> Path:
    return session.kernel.store.mission_dir(mission_id) / "read_only_spine" / "receipts" / f"{receipt_ref}.json"


def _finalgate_path(session: ReadOnlyProductionSpineSession, mission_id: str, finalgate_ref: str) -> Path:
    return session.kernel.store.mission_dir(mission_id) / "read_only_spine" / "finalgate" / f"{finalgate_ref}.json"


def _run_blocked_session(
    tmp_path: Path,
    workspace: Path,
    decision: ReadOnlyDecision,
) -> tuple[ReadOnlyProductionSpineSession, object, object]:
    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=ReadOnlyDecisionClient([decision]),
    )
    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()
    return session, result, replay


def _json_payloads(session: ReadOnlyProductionSpineSession, collection: str) -> list[dict[str, object]]:
    root = session.kernel.store.mission_dir(session.mission_id) / "read_only_spine" / collection
    if not root.exists():
        return []
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(root.glob("*.json"))
    ]


def _only_json_payload(session: ReadOnlyProductionSpineSession, collection: str) -> dict[str, object]:
    payloads = _json_payloads(session, collection)
    assert len(payloads) == 1
    return payloads[0]


def _assert_blocked_terminal_proof(
    session: ReadOnlyProductionSpineSession,
    result: object,
    replay: object,
    *,
    expected_failure: str,
) -> None:
    assert result.status == "blocked"
    assert result.blocked_reason == expected_failure
    assert result.receipt_refs == []
    assert result.finalgate_status == "rejected"
    assert session.kernel.store.load_record(session.mission_id).status is OperatorMissionStatus.BLOCKED
    events = session.kernel.store.load_events(session.mission_id)
    event_types = [event.event_type for event in events]
    assert event_types.count("mission_blocked") == 1
    assert event_types.count("read_only_spine_action_receipted") == 0
    assert event_types.count("read_only_spine_failed_attempt_recorded") == 1
    assert event_types.count("read_only_spine_finalgate_certified") == 1
    finalgate = _only_json_payload(session, "finalgate")
    assert finalgate["accepted"] is False
    assert finalgate["status"] == "blocked"
    assert finalgate["reason"] == expected_failure
    assert replay.reexecuted is False
    assert replay.model_calls_before_replay == replay.model_calls_after_replay
    assert replay.tool_calls_before_replay == replay.tool_calls_after_replay
    assert replay.receipt_writes_before_replay == replay.receipt_writes_after_replay
    assert replay.failed_attempt_writes_before_replay == replay.failed_attempt_writes_after_replay
    assert replay.finalgate_writes_before_replay == replay.finalgate_writes_after_replay


class _SequenceClient:
    def __init__(self, *outputs: dict[str, object]) -> None:
        self.outputs = list(outputs)
        self.requests: list[RealModelRequest] = []

    def complete(self, request: RealModelRequest) -> dict[str, object]:
        self.requests.append(request)
        return self.outputs.pop(0)


class _ExcerptAwareDecisionClient(ReadOnlyDecisionClient):
    def __init__(self) -> None:
        super().__init__([])
        self.saw_excerpt = False

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        self.call_count += 1
        observations = context.get("observations", [])
        if self.call_count == 1:
            return ReadOnlyDecision(
                action=ReadOnlyActionKind.READ_FILE_SEGMENT,
                arguments={"path": "src/parser.py", "start_line": 1, "line_count": 3},
            )
        latest = observations[-1]
        excerpt = latest.get("safe_excerpt")
        assert isinstance(excerpt, str)
        assert "parse_event" in excerpt
        assert "raw.get('kind')" in excerpt
        assert latest.get("safe_excerpt_truncated") is False
        self.saw_excerpt = True
        return ReadOnlyDecision(
            action=ReadOnlyActionKind.FINISH_REPORT,
            operator_message="The parser evidence was inspected through a bounded safe excerpt.",
            evidence_refs=[latest["evidence_ref"]],
        )


class _KillingDecisionClient(ReadOnlyDecisionClient):
    def __init__(self, cockpit: LLMLiveOperatorCockpit, decisions: list[ReadOnlyDecision]) -> None:
        super().__init__(decisions)
        self._cockpit = cockpit

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        decision = super().complete(context)
        self._cockpit.handle("kill")
        return decision


class _RevokingAuthorityDecisionClient(ReadOnlyDecisionClient):
    def __init__(self, envelope: MissionAuthorityEnvelope, decisions: list[ReadOnlyDecision]) -> None:
        super().__init__(decisions)
        self._envelope = envelope

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        decision = super().complete(context)
        self._envelope.revoked_at = datetime.now(UTC)
        return decision


class _KillingAfterToolSession(ReadOnlyProductionSpineSession):
    def _execute_read_only_action(self, decision: ReadOnlyDecision) -> dict[str, Any]:
        observation = super()._execute_read_only_action(decision)
        self.cockpit.handle("kill")
        return observation


class _DeleteTargetBeforeReadSession(ReadOnlyProductionSpineSession):
    def __init__(self, target: Path, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._target = target

    def _read_file_lines(self, path: Path) -> list[str]:
        self._target.unlink()
        return super()._read_file_lines(path)


class _KnownBackendFailingSession(ReadOnlyProductionSpineSession):
    def _list_directory_entries(self, path: Path) -> list[str]:
        raise OSError("backend unavailable")


class _UnexpectedExecutorFailingSession(ReadOnlyProductionSpineSession):
    def _list_directory_entries(self, path: Path) -> list[str]:
        raise RuntimeError("raw provider payload must not escape")


class _ReceiptPersistenceFailingSession(ReadOnlyProductionSpineSession):
    def _write_artifact(self, collection: str, item_id: str, payload: dict[str, Any]) -> None:
        if collection == "receipts":
            raise OSError("receipt store unavailable")
        super()._write_artifact(collection, item_id, payload)


class _FinalGatePersistenceFailingSession(ReadOnlyProductionSpineSession):
    def _write_artifact(self, collection: str, item_id: str, payload: dict[str, Any]) -> None:
        if collection == "finalgate":
            raise OSError("finalgate store unavailable")
        super()._write_artifact(collection, item_id, payload)


class _DriftingDecisionClient(ReadOnlyDecisionClient):
    def __init__(self, path: Path, decisions: list[ReadOnlyDecision]) -> None:
        super().__init__(decisions)
        self._path = path

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        decision = super().complete(context)
        self._path.write_text("# Sentinel\nchanged\n", encoding="utf-8")
        return decision


class _FailingDecisionClient(ReadOnlyDecisionClient):
    def __init__(self) -> None:
        super().__init__([])

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        del context
        self.call_count += 1
        raise RuntimeError("raw provider payload must not escape")


class _TimeoutDecisionClient(ReadOnlyDecisionClient):
    def __init__(self) -> None:
        super().__init__([])

    def complete(self, context: dict[str, Any]) -> ReadOnlyDecision:
        del context
        self.call_count += 1
        raise TimeoutError("provider timeout")


def _contract() -> UserModelContract:
    model = "fake-model"
    return UserModelContract(
        selected_provider_id="explicit_fake_provider",
        selected_backend_id="fake_backend",
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(model_name=model, context_window_tokens=32_000),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="read_only_spine_fake_model_gate",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _mission_output() -> dict[str, Any]:
    return {
        "reply": "Read-only mission drafted. Awaiting explicit start.",
        "intent": {"kind": "draft_mission", "text": "read-only repository inspection"},
        "mission_draft": {
            "title": "Read-only production spine inspection",
            "objective": "Inspect repository files without mutation and produce evidence-linked status.",
            "constraints": ["read-only", "no provider fallback", "no direct organ calls"],
            "expected_artifacts": ["read-only report", "receipts", "FinalGate certificate"],
        },
        "authority_summary": {
            "mission_id": "mission_read_only_spine",
            "allowed_actions": ["list_directory", "read_file_segment", "finish_report"],
            "forbidden_actions": ["write_file", "shell", "network", "credential_access"],
            "summary": "Read-only repository observation only.",
        },
    }


def _authority_envelope(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="operator_user",
        mission_type=MissionType.GTM,
        mission_title="Read-only production spine inspection",
        mission_objective="Inspect repository files through the production read-only spine.",
        success_criteria=["evidence-linked read-only report"],
        mode=MissionMode.SAFE,
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=["list_directory", "read_file_segment", "finish_report"],
        forbidden_actions=["write_file", "shell", "network", "credential_access"],
        allowed_paths=["."],
        max_duration_minutes=10,
        max_actions=10,
        max_cost_usd=0.0,
    )
