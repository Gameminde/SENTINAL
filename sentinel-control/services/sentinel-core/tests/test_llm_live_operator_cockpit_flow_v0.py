from __future__ import annotations

from pathlib import Path

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.models import OperatorConversationState, OperatorMissionStatus, OperatorMode


def _contract() -> UserModelContract:
    model = "qwen3.5:9b"
    return UserModelContract(
        selected_provider_id="local_openai",
        selected_backend_id="ollama_openai_compatible",
        selected_model=model,
        cost_profile=ModelCostProfile(model_name=model, input_usd_per_1m=0.0, output_usd_per_1m=0.0, context_window_tokens=32_000),
        capability_profile=ModelCapabilityProfile(model_name=model, context_window_tokens=32_000),
        context_budget_policy=ContextBudgetPolicy(max_decision_frame_tokens=4_000, max_tool_schema_tokens=500, max_evidence_tokens=2_000, reserve_output_tokens=500),
        quality_expectation=QualityExpectationContract(expected_quality="cockpit_flow", minimum_evidence_refs=0, retry_budget=0),
    )


class SequenceClient:
    def __init__(self, *outputs: dict[str, object]) -> None:
        self.outputs = list(outputs)
        self.requests: list[RealModelRequest] = []

    def complete(self, request: RealModelRequest) -> dict[str, object]:
        self.requests.append(request)
        return self.outputs.pop(0)


def test_cockpit_creates_draft_from_llm_conversation(tmp_path: Path) -> None:
    cockpit = _cockpit(tmp_path, _mission_output())

    result = cockpit.handle("Je veux lancer un business de formation IA.")

    assert result.mission_draft is not None
    assert result.state is OperatorConversationState.AWAITING_START_CONFIRMATION


def test_cockpit_asks_clarification_before_start(tmp_path: Path) -> None:
    cockpit = LLMLiveOperatorCockpit(run_root=tmp_path, mode=OperatorMode.DETERMINISTIC_TEST)

    result = cockpit.handle("start")

    assert result.state is OperatorConversationState.ASKING_CLARIFICATIONS
    assert result.mission_record is None


def test_cockpit_requires_explicit_start_confirmation(tmp_path: Path) -> None:
    cockpit = _cockpit(tmp_path, _mission_output())

    draft_result = cockpit.handle("Je veux lancer un business de formation IA.")

    assert draft_result.mission_record is None
    assert cockpit.active_mission_id is None


def test_cockpit_start_creates_internal_mission(tmp_path: Path) -> None:
    cockpit = _cockpit(tmp_path, _mission_output())
    cockpit.handle("Je veux lancer un business de formation IA.")

    result = cockpit.handle("oui commence")

    assert result.mission_record is not None
    assert result.mission_record.status is OperatorMissionStatus.QUEUED
    assert cockpit.active_mission_id == result.mission_record.mission_id


def test_cockpit_pause_resume_kill_without_manual_id(tmp_path: Path) -> None:
    cockpit = _started_cockpit(tmp_path)
    mission_id = cockpit.active_mission_id

    assert cockpit.handle("pause").mission_record.status is OperatorMissionStatus.PAUSED
    assert cockpit.handle("resume").mission_record.status is OperatorMissionStatus.QUEUED
    assert cockpit.handle("kill").mission_record.status is OperatorMissionStatus.KILLED
    assert cockpit.kernel.store.load_record(mission_id).status is OperatorMissionStatus.KILLED


def test_cockpit_status_without_manual_id(tmp_path: Path) -> None:
    cockpit = _started_cockpit(tmp_path)

    result = cockpit.handle("status")

    assert "queued" in result.reply.lower()


def test_cockpit_disambiguates_multiple_active_missions(tmp_path: Path) -> None:
    cockpit = _started_cockpit(tmp_path)
    first = cockpit.active_mission_id
    second_record = cockpit.kernel.create_mission(
        session_id=cockpit.session.session_id,
        draft=cockpit.session.current_draft,
        authority_summary=cockpit.session.current_authority_summary,
    )
    cockpit.active_mission_ids = [first, second_record.mission_id]

    result = cockpit.handle("status")

    assert "which mission" in result.reply.lower()


def test_cockpit_never_grants_authority(tmp_path: Path) -> None:
    cockpit = _cockpit(tmp_path, _mission_output())

    result = cockpit.handle("Je veux lancer un business.")

    assert result.can_grant_authority is False
    assert result.authority_effect == "none"


def test_cockpit_never_executes_from_llm_output_directly(tmp_path: Path) -> None:
    cockpit = _cockpit(
        tmp_path,
        {
            **_mission_output(),
            "metadata": {"organ_execution": {"organ_kind": "browser_readonly"}},
        },
    )

    result = cockpit.handle("Je veux lancer un business.")

    assert result.can_execute is False
    assert result.mission_record is None
    assert "rejected" in result.reply.lower()


def _cockpit(tmp_path: Path, *outputs: dict[str, object]) -> LLMLiveOperatorCockpit:
    return LLMLiveOperatorCockpit(
        run_root=tmp_path,
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=SequenceClient(*outputs),
    )


def _started_cockpit(tmp_path: Path) -> LLMLiveOperatorCockpit:
    cockpit = _cockpit(tmp_path, _mission_output())
    cockpit.handle("Je veux lancer un business de formation IA.")
    cockpit.handle("oui commence")
    return cockpit


def _mission_output() -> dict[str, object]:
    return {
        "reply": "Tres bien. Mission prete. Je peux commencer ?",
        "intent": {"kind": "draft_mission", "text": "launch AI training business"},
        "mission_draft": {
            "title": "AI training business launch",
            "objective": "Research the target market and prepare launch artifacts.",
            "constraints": ["no payment", "no real outbound send"],
            "expected_artifacts": ["market summary", "launch plan"],
        },
        "authority_summary": {
            "mission_id": "mission_cockpit",
            "allowed_actions": ["research", "draft", "create_report"],
            "forbidden_actions": ["payment", "send_email"],
            "summary": "Research and drafting only.",
        },
    }
