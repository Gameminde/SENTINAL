from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

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
from sentinel.operator.read_only_model_clients import (
    ReadOnlyProviderDecisionClient,
    ReadOnlyProviderReportClient,
)
from sentinel.operator.read_only_operator_spine import (
    ReadOnlyActionKind,
    ReadOnlyProductionSpineSession,
    ReadOnlySpineError,
)
from sentinel.shared.enums import MissionMode, MissionType


def test_pack3_7_decision_prompt_is_json_only_with_action_skeletons_and_forbidden_controls() -> None:
    model = _SequenceModelClient(
        {"action": "list_directory", "arguments": {"path": "."}, "provider_response_hash": "hash_ok"}
    )
    telemetry = _RecordingTelemetry()
    client = ReadOnlyProviderDecisionClient(
        user_model_contract=_contract(),
        model_client=model,
        telemetry_sink=telemetry,
    )

    decision = client.complete(_context())

    prompt = model.requests[0].prompt_text_in_memory_only or ""
    assert decision.action is ReadOnlyActionKind.LIST_DIRECTORY
    assert "Return exactly one JSON object" in prompt
    assert "Do not wrap in Markdown" in prompt
    assert "read_only_research_decision_v1" in prompt
    assert '"action":"list_directory"' in prompt
    assert '"action":"search_text"' in prompt
    assert '"action":"read_file_segment"' in prompt
    assert '"action":"finish_exploration"' in prompt
    assert "workspace_ref" in prompt
    assert "model_contract_ref" in prompt
    assert "can_execute" in prompt
    assert telemetry.started_lanes == ["exploration_decision"]
    assert telemetry.completed_lanes == ["exploration_decision"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            {
                "provider_response_hash": "hash_empty_content",
                "visible_content_char_count": 0,
                "finish_reason": "stop",
                "output_truncated": False,
                "json_object_detected": False,
                "normalization_strategy": "empty_visible_content",
                "content_extraction_source": "choices[0].message.content",
            },
            {"json_object_detected": False, "normalization_strategy": "empty_visible_content"},
        ),
        (
            {
                "provider_response_hash": "hash_empty_object",
                "visible_content_char_count": 2,
                "finish_reason": "stop",
                "output_truncated": False,
                "json_object_detected": True,
                "normalization_strategy": "plain_json_object",
                "content_extraction_source": "choices[0].message.content",
            },
            {"json_object_detected": True, "normalization_strategy": "plain_json_object"},
        ),
    ],
)
def test_pack3_7_decision_schema_failures_have_safe_structure_diagnostics(
    raw: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    model = _SequenceModelClient(raw)
    telemetry = _RecordingTelemetry()
    client = ReadOnlyProviderDecisionClient(
        user_model_contract=_contract(),
        model_client=model,
        telemetry_sink=telemetry,
    )

    with pytest.raises(ReadOnlySpineError) as raised:
        client.complete(_context())

    diagnostics = raised.value.diagnostics
    assert diagnostics["protocol_version"] == "read_only_research_decision_v1"
    assert diagnostics["parse_stage"] == "read_only_decision_validation"
    assert diagnostics["provider_response_hash"] == raw["provider_response_hash"]
    assert diagnostics["visible_content_length"] == raw["visible_content_char_count"]
    assert diagnostics["finish_reason"] == "stop"
    assert diagnostics["output_truncated"] is False
    assert diagnostics["top_level_key_names"] == []
    assert "action" in diagnostics["missing_required_field_names"]
    assert diagnostics["unknown_field_names"] == []
    assert diagnostics["content_extraction_source"] == "choices[0].message.content"
    assert diagnostics["json_object_detected"] is expected["json_object_detected"]
    assert diagnostics["normalization_strategy"] == expected["normalization_strategy"]
    assert "raw" not in str(diagnostics).lower()
    assert telemetry.schema_invalid_lanes == ["exploration_decision"]


@pytest.mark.parametrize("unsafe_field", ["workspace_ref", "model_contract_ref", "authority", "budget", "can_execute"])
def test_pack3_7_model_owned_control_fields_are_rejected_before_actions(unsafe_field: str) -> None:
    model = _SequenceModelClient(
        {
            "action": "list_directory",
            "arguments": {"path": "."},
            unsafe_field: "model-owned-control",
            "provider_response_hash": "hash_control",
        }
    )
    client = ReadOnlyProviderDecisionClient(user_model_contract=_contract(), model_client=model)

    with pytest.raises(ReadOnlySpineError) as raised:
        client.complete(_context())

    diagnostics = raised.value.diagnostics
    assert unsafe_field in diagnostics["unknown_field_names"]
    assert "unknown_field" in diagnostics["validation_error_codes"]


def test_pack3_7_safe_provider_metadata_is_not_treated_as_decision_fields() -> None:
    model = _SequenceModelClient(
        {
            "action": "search_text",
            "arguments": {"query": "register", "path": "."},
            "provider_response_hash": "hash_valid",
            "visible_content_char_count": 64,
            "finish_reason": "stop",
            "output_truncated": False,
            "json_object_detected": True,
            "normalization_strategy": "single_markdown_json_fence",
            "content_extraction_source": "choices[0].message.content",
        }
    )
    client = ReadOnlyProviderDecisionClient(user_model_contract=_contract(), model_client=model)

    decision = client.complete(_context())

    assert decision.action is ReadOnlyActionKind.SEARCH_TEXT
    assert decision.arguments == {"query": "register", "path": "."}
    assert decision.can_execute is False
    assert decision.can_grant_authority is False


def test_pack3_7_report_lane_has_separate_provider_counter_and_telemetry() -> None:
    model = _SequenceModelClient(
        {
            "report_text": "Report cites evidence_ref_1 and does not claim mutation.",
            "evidence_refs": ["evidence_ref_1"],
            "provider_response_hash": "hash_report",
        }
    )
    telemetry = _RecordingTelemetry()
    client = ReadOnlyProviderReportClient(
        user_model_contract=_contract(),
        model_client=model,
        telemetry_sink=telemetry,
    )

    report = client.complete({"mission_id": "mission_1", "observations": [{"evidence_ref": "evidence_ref_1"}]})

    assert client.call_count == 1
    assert report.report_text.startswith("Report cites")
    assert model.requests[0].request_metadata["read_only_lane"] == "final_report"
    assert telemetry.started_lanes == ["final_report"]
    assert telemetry.completed_lanes == ["final_report"]


def test_pack3_7_invalid_provider_decision_blocks_with_rejected_finalgate_and_replay_purity(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("# Fixture\n", encoding="utf-8")
    cockpit = _started_cockpit(tmp_path / "runs")
    mission_id = cockpit.active_mission_id
    assert mission_id is not None
    decision_client = ReadOnlyProviderDecisionClient(
        user_model_contract=_contract(),
        model_client=_SequenceModelClient(
            {
                "provider_response_hash": "hash_bad_decision",
                "visible_content_char_count": 2,
                "json_object_detected": True,
                "normalization_strategy": "plain_json_object",
                "content_extraction_source": "choices[0].message.content",
            }
        ),
        telemetry_sink=cockpit.kernel.telemetry_sink,
    )
    session = ReadOnlyProductionSpineSession(
        cockpit=cockpit,
        mission_id=mission_id,
        snapshot_root=workspace,
        decision_client=decision_client,
    )

    result = session.run_via_agent_runtime(envelope=_authority_envelope(mission_id))
    replay = session.build_replay()

    assert result.status == "blocked"
    assert result.finalgate_status == "rejected"
    assert result.receipt_refs == []
    assert len(result.finalgate_refs) == 1
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.BLOCKED
    blocked_event = [
        event for event in cockpit.kernel.store.load_events(mission_id)
        if event.event_type == "read_only_spine_blocked"
    ][0]
    diagnostics = blocked_event.metadata["read_only_model_diagnostics"]
    assert diagnostics["parse_stage"] == "read_only_decision_validation"
    assert diagnostics["provider_response_hash"] == "hash_bad_decision"
    assert replay.reexecuted is False
    assert replay.model_calls_before_replay == decision_client.call_count
    assert replay.model_calls_after_replay == decision_client.call_count
    assert replay.receipt_writes_before_replay == replay.receipt_writes_after_replay
    assert replay.finalgate_writes_before_replay == replay.finalgate_writes_after_replay


class _SequenceModelClient:
    def __init__(self, *outputs: dict[str, Any]) -> None:
        self.outputs = list(outputs)
        self.requests: list[RealModelRequest] = []

    def complete(self, request: RealModelRequest) -> dict[str, Any]:
        self.requests.append(request)
        return self.outputs.pop(0)


class _RecordingTelemetry:
    def __init__(self) -> None:
        self.started_lanes: list[str] = []
        self.completed_lanes: list[str] = []
        self.schema_invalid_lanes: list[str] = []

    def record_model_call_started(self, request: RealModelRequest, **_: Any) -> None:
        self.started_lanes.append(str(request.request_metadata["read_only_lane"]))

    def record_model_call_completed(
        self,
        request: RealModelRequest,
        *,
        schema_invalid: bool = False,
        **_: Any,
    ) -> None:
        lane = str(request.request_metadata["read_only_lane"])
        if schema_invalid:
            self.schema_invalid_lanes.append(lane)
        else:
            self.completed_lanes.append(lane)


def _context() -> dict[str, Any]:
    return {
        "mission_id": "mission_pack3_7",
        "status": "running",
        "observations": [],
        "receipt_refs": [],
        "legal_actions": ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
    }


def _started_cockpit(run_root: Path) -> LLMLiveOperatorCockpit:
    cockpit = LLMLiveOperatorCockpit(
        run_root=run_root,
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=_SequenceModelClient(_mission_output()),
    )
    draft = cockpit.handle("Inspect this repository in read-only mode.")
    assert draft.state is OperatorConversationState.AWAITING_START_CONFIRMATION
    started = cockpit.handle("start")
    assert started.state is OperatorConversationState.MISSION_QUEUED
    return cockpit


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
