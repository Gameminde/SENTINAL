from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.cli import _classify_cockpit_conversation
from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.models import OperatorConversationState, OperatorMode


class SequenceClient:
    def __init__(self, *outputs: dict[str, object]) -> None:
        self.outputs = list(outputs)
        self.requests: list[RealModelRequest] = []

    def complete(self, request: RealModelRequest) -> dict[str, object]:
        self.requests.append(request)
        if not self.outputs:
            raise AssertionError("unexpected provider call")
        return self.outputs.pop(0)


def test_valid_mission_understanding_v2_creates_draft_and_summary(tmp_path: Path) -> None:
    client = SequenceClient(_v2_draft())
    cockpit = _cockpit(tmp_path, client)

    result = cockpit.handle("Understand this repository deeply and produce a report.")

    assert result.state is OperatorConversationState.AWAITING_START_CONFIRMATION
    assert result.mission_draft is not None
    assert result.mission_draft.draft_id.startswith("mission_draft_")
    assert result.mission_draft.metadata["understanding_protocol"] == "cockpit_mission_understanding_v2"
    assert result.authority_summary is not None
    assert result.authority_summary.mission_id.startswith("mission_summary_")
    assert result.authority_summary.allowed_actions == [
        "list_directory",
        "read_file_segment",
        "search_text",
        "finish_exploration",
    ]
    assert result.authority_summary.metadata["capability_id"] == "read_only_research"
    assert result.can_execute is False
    assert result.can_grant_authority is False
    assert len(client.requests) == 1


def test_v2_unknown_capability_does_not_create_executable_draft(tmp_path: Path) -> None:
    client = SequenceClient({**_v2_draft(), "requested_capability": "browser_live_operator"})
    cockpit = _cockpit(tmp_path, client)

    result = cockpit.handle("Research this repository.")

    assert result.state is OperatorConversationState.ASKING_CLARIFICATIONS
    assert result.mission_draft is None
    assert result.authority_summary is None
    assert result.metadata["blocked_reason"] == "unsupported_requested_capability"


@pytest.mark.parametrize(
    "unsafe_field",
    [
        "mission_id",
        "authority_summary",
        "approval_scope",
        "allowed_actions",
        "allowed_paths",
        "can_execute",
        "credentials",
        "max_cost_usd",
        "model_contract_ref",
        "path",
        "workspace",
        "workspace_ref",
        "credential_grants",
    ],
)
def test_v2_rejects_model_supplied_control_or_authority_fields(
    tmp_path: Path,
    unsafe_field: str,
) -> None:
    client = SequenceClient({**_v2_draft(), unsafe_field: True})
    cockpit = _cockpit(tmp_path, client)

    result = cockpit.handle("Research this repository.")

    assert result.state is OperatorConversationState.UNDERSTANDING_REQUEST
    assert result.mission_draft is None
    diagnostics = result.metadata["structured_output_diagnostics"]
    assert unsafe_field in diagnostics["unknown_field_names"]
    assert "True" not in json.dumps(diagnostics)


def test_safe_diagnostics_expose_structure_without_values(tmp_path: Path) -> None:
    client = SequenceClient(
        {
            "protocol_version": "cockpit_mission_understanding_v2",
            "kind": "draft_mission",
            "reply": "missing title and objective",
            "requested_capability": "read_only_research",
            "objective": "secret_token_abcdefghijklmnopqrstuvwxyz",
        }
    )
    cockpit = _cockpit(tmp_path, client)

    result = cockpit.handle("Research this repository.")

    diagnostics = result.metadata["structured_output_diagnostics"]
    rendered = json.dumps(diagnostics, sort_keys=True)
    assert diagnostics["protocol_version"] == "cockpit_mission_understanding_v2"
    assert "title" in diagnostics["missing_required_field_names"]
    assert "secret_token" not in rendered
    assert "abcdefghijklmnopqrstuvwxyz" not in rendered


def test_v2_rejects_raw_reasoning_field(tmp_path: Path) -> None:
    client = SequenceClient({**_v2_draft(), "reasoning": "private chain of thought"})
    cockpit = _cockpit(tmp_path, client)

    result = cockpit.handle("Research this repository.")

    assert result.state is OperatorConversationState.UNDERSTANDING_REQUEST
    assert result.mission_draft is None
    diagnostics = result.metadata["structured_output_diagnostics"]
    assert "reasoning" in diagnostics["unknown_field_names"]
    assert "private chain" not in json.dumps(diagnostics)


def test_approval_after_valid_v2_draft_queues_without_second_provider_call(tmp_path: Path) -> None:
    client = SequenceClient(_v2_draft())
    cockpit = _cockpit(tmp_path, client, approval_scope=_approval_scope())
    cockpit.handle("Research this repository.")

    result = cockpit.handle("Oui, commence cette mission avec le périmètre et l’autorité approuvés.")

    assert result.state is OperatorConversationState.MISSION_QUEUED
    assert result.mission_record is not None
    assert len(client.requests) == 1


def test_approval_without_valid_draft_does_not_start_or_call_provider(tmp_path: Path) -> None:
    client = SequenceClient(_v2_draft())
    cockpit = _cockpit(tmp_path, client, approval_scope=_approval_scope())

    result = cockpit.handle("Oui, commence cette mission avec le périmètre et l’autorité approuvés.")

    assert result.state is OperatorConversationState.ASKING_CLARIFICATIONS
    assert result.mission_record is None
    assert client.requests == []


def test_authority_actions_are_intersection_of_capability_and_approval_scope(tmp_path: Path) -> None:
    client = SequenceClient(_v2_draft())
    scope = _approval_scope(actions=["list_directory", "search_text", "write_file"])
    cockpit = _cockpit(tmp_path, client, approval_scope=scope)

    result = cockpit.handle("Research this repository.")

    assert result.authority_summary is not None
    assert result.authority_summary.allowed_actions == ["list_directory", "search_text"]
    assert "write_file" in result.authority_summary.forbidden_actions


def test_script_outcome_classification_does_not_treat_exit_as_mission_created() -> None:
    assert _classify_cockpit_conversation([]) == "conversation_completed"
    assert _classify_cockpit_conversation(
        [{"state": "understanding_request", "metadata": {}, "mission_record": None}]
    ) == "mission_not_created"
    assert _classify_cockpit_conversation(
        [{"mission_record": {"status": "queued"}, "metadata": {}}]
    ) == "mission_queued"
    assert _classify_cockpit_conversation(
        [{"mission_record": {"status": "queued"}, "metadata": {"daemon_pickup": {"claimed": True}}}]
    ) == "mission_dispatched"


def _cockpit(
    tmp_path: Path,
    client: SequenceClient,
    *,
    approval_scope: MissionAuthorityApprovalScope | None = None,
) -> LLMLiveOperatorCockpit:
    return LLMLiveOperatorCockpit(
        run_root=tmp_path,
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=client,
        authority_approval_scope=approval_scope,
    )


def _contract() -> UserModelContract:
    model = "deepseek-v4-pro"
    return UserModelContract(
        selected_provider_id="aliyun_dashscope",
        selected_backend_id="aliyun_openai_compatible_chat",
        selected_model=model,
        cost_profile=ModelCostProfile(
            model_name=model,
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=64_000,
        ),
        capability_profile=ModelCapabilityProfile(model_name=model, context_window_tokens=64_000),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=8_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=4_000,
            reserve_output_tokens=800,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="pack3_product_vertical_slice",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _v2_draft() -> dict[str, object]:
    return {
        "protocol_version": "cockpit_mission_understanding_v2",
        "kind": "draft_mission",
        "reply": "Mission draft ready for approval.",
        "title": "Repository architecture research",
        "objective": "Map packages, command registration, execution flow, and architecture risks.",
        "constraints": ["read-only", "no mutation"],
        "expected_artifacts": ["evidence-linked technical report"],
        "requested_capability": "read_only_research",
        "clarification_questions": [],
    }


def _approval_scope(actions: list[str] | None = None) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=["read_only_observation"],
        allowed_actions=actions
        or ["list_directory", "read_file_segment", "search_text", "finish_exploration"],
        forbidden_actions=["write_file", "shell", "credential_access", "payment", "send_email"],
        allowed_paths=["."],
        max_duration_minutes=20,
        max_actions=12,
        max_cost_usd=0.0,
    )
