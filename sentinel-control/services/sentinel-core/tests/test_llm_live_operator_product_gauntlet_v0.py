from __future__ import annotations

import json
from pathlib import Path

from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.mission.cancellation import CancellationToken
from sentinel.operator.cockpit import LLMLiveOperatorCockpit
from sentinel.operator.models import OperatorMode
from sentinel.operator.power_bridge import OperatorPowerRuntimeBridge
from sentinel.operator.replay import MissionReplayBuilder
from sentinel.power.runtime import (
    PowerActuatorCapabilityLevel,
    PowerActuatorFamily,
    PowerMissionGraph,
    PowerMissionPlan,
    PowerMissionStep,
    PowerRuntimeStatus,
    PowerStepResult,
    PowerStepStatus,
)


class SequencedOperatorModelClient:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = list(outputs)

    def complete(self, _request):
        if not self.outputs:
            return _clarification_output()
        return self.outputs.pop(0)


def test_gauntlet_greeting_business_start_timeline_replay(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_greeting_output(), _business_output()])

    greeting = cockpit.handle("Sentinel t'es la ?")
    draft = cockpit.handle("Je veux lancer un business de formation IA.")
    started = cockpit.handle("oui commence")
    events = cockpit.kernel.store.load_events(started.mission_record.mission_id)
    replay = MissionReplayBuilder(cockpit.kernel.store).build(started.mission_record.mission_id)

    assert "je suis la" in greeting.reply.lower()
    assert draft.mission_draft is not None
    assert draft.authority_summary is not None
    assert "mission lancee" in started.reply.lower()
    assert [event.event_type for event in events] == ["mission_created", "mission_queued"]
    assert replay.reexecuted_actions is False
    assert "Mission queued" in replay.safe_summary_text()


def test_gauntlet_vague_request_requires_clarification_and_no_execution(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_clarification_output()])

    turn = cockpit.handle("Fais un truc.")

    assert turn.clarification_questions
    assert cockpit.kernel.list_missions() == []


def test_gauntlet_llm_direct_organ_call_is_rejected(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(
        tmp_path,
        [
            {
                **_business_output(),
                "metadata": {"organ_execution": {"organ_kind": "browser_readonly"}},
            }
        ],
    )

    turn = cockpit.handle("Je veux lancer un business.")

    assert "rejected" in turn.reply.lower()
    assert turn.metadata["blocked_reason"] == "llm_operator_output_rejected"
    assert cockpit.kernel.list_missions() == []


def test_gauntlet_llm_authority_grant_is_rejected(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(
        tmp_path,
        [
            {
                **_business_output(),
                "authority_summary": {
                    "mission_id": "mission_bad",
                    "allowed_actions": ["research"],
                    "forbidden_actions": [],
                    "summary": "I grant root authority.",
                    "can_grant_authority": True,
                },
            }
        ],
    )

    turn = cockpit.handle("Je veux lancer un business.")

    assert "rejected" in turn.reply.lower()
    assert cockpit.kernel.list_missions() == []


def test_gauntlet_pause_resume_kill_flow(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_business_output()])
    cockpit.handle("Je veux lancer un business.")
    cockpit.handle("oui commence")

    paused = cockpit.handle("pause")
    resumed = cockpit.handle("resume")
    killed = cockpit.handle("kill")

    assert paused.reply == "Mission paused."
    assert resumed.reply == "Mission resumed."
    assert killed.reply == "Mission killed."
    assert cockpit.kernel.store.load_record(cockpit.active_mission_id).status.value == "killed"


def test_gauntlet_two_active_missions_require_disambiguation(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_business_output(title="Business one"), _business_output(title="Business two")])
    cockpit.handle("Je veux lancer un business.")
    cockpit.handle("oui commence")
    cockpit.handle("Je veux lancer un deuxieme business.")
    cockpit.handle("oui commence")

    status = cockpit.handle("status")

    assert "which mission" in status.reply.lower()


def test_gauntlet_secret_like_text_is_redacted_before_persistence(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_clarification_output()])

    turn = cockpit.handle("Authorization: Bearer secret_token_123456789")

    rendered = json.dumps(turn.safe_model_dump(), sort_keys=True)
    assert "secret_token" not in rendered
    assert "Bearer" not in rendered


def test_gauntlet_missing_executor_blocks_with_safe_replay(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_business_output()])
    cockpit.handle("Je veux lancer un business.")
    started = cockpit.handle("oui commence")
    mission_id = started.mission_record.mission_id

    result = OperatorPowerRuntimeBridge(cockpit.kernel).run(mission_id, _plan(mission_id))
    replay = MissionReplayBuilder(cockpit.kernel.store).build(mission_id)

    assert result.status is PowerRuntimeStatus.BLOCKED
    assert "blocked" in replay.terminal_explanation.lower()
    assert replay.reexecuted_actions is False


def test_gauntlet_power_runtime_refs_surface_in_replay(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_business_output()])
    cockpit.handle("Je veux lancer un business.")
    started = cockpit.handle("oui commence")
    mission_id = started.mission_record.mission_id

    OperatorPowerRuntimeBridge(cockpit.kernel).run(
        mission_id,
        _plan(mission_id),
        actuator_executor=lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            receipt_refs=["receipt:gauntlet"],
            finalgate_certificate_refs=["finalgate:gauntlet"],
            memory_feedback_refs=["memory:gauntlet"],
            safe_summary="gauntlet step done",
        ),
    )
    replay = MissionReplayBuilder(cockpit.kernel.store).build(mission_id)

    assert replay.receipt_refs == ["receipt:gauntlet"]
    assert replay.finalgate_certificate_refs == ["finalgate:gauntlet"]
    assert replay.memory_feedback_refs == ["memory:gauntlet"]


def test_gauntlet_kill_switch_aborts_remaining_power_steps(tmp_path: Path) -> None:
    cockpit = _llm_cockpit(tmp_path, [_business_output()])
    cockpit.handle("Je veux lancer un business.")
    started = cockpit.handle("oui commence")
    mission_id = started.mission_record.mission_id
    token = CancellationToken()
    token.cancel()

    result = OperatorPowerRuntimeBridge(cockpit.kernel).run(
        mission_id,
        _plan(mission_id),
        actuator_executor=lambda step, _context: PowerStepResult(
            step_id=step.step_id,
            status=PowerStepStatus.SUCCEEDED,
            safe_summary="should not run",
        ),
        cancellation_token=token,
    )

    assert result.status is PowerRuntimeStatus.ABORTED
    assert cockpit.kernel.store.load_record(mission_id).status.value == "killed"


def _llm_cockpit(tmp_path: Path, outputs: list[dict[str, object]]) -> LLMLiveOperatorCockpit:
    return LLMLiveOperatorCockpit(
        run_root=tmp_path,
        mode=OperatorMode.LLM_OPERATOR,
        user_model_contract=_contract(),
        model_client=SequencedOperatorModelClient(outputs),
    )


def _contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id="local_openai",
        selected_backend_id="ollama_openai_compatible",
        selected_model="qwen3.5:9b",
        cost_profile=ModelCostProfile(
            model_name="qwen3.5:9b",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=32_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="qwen3.5:9b",
            context_window_tokens=32_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=4_000,
            max_tool_schema_tokens=500,
            max_evidence_tokens=2_000,
            reserve_output_tokens=500,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="operator_v0",
            minimum_evidence_refs=0,
            retry_budget=0,
        ),
    )


def _greeting_output() -> dict[str, object]:
    return {
        "reply": "Oui, je suis la. Qu'est-ce que tu veux faire ?",
        "intent": {"kind": "greeting", "text": "hello"},
    }


def _business_output(*, title: str = "AI training business launch") -> dict[str, object]:
    return {
        "reply": "Tres bien. Je vais clarifier la mission avant de commencer.",
        "intent": {"kind": "draft_mission", "text": "launch AI training business"},
        "mission_draft": {
            "title": title,
            "objective": "Research the target market and prepare launch artifacts.",
            "constraints": ["no payment", "no real outbound send"],
            "expected_artifacts": ["market summary", "launch plan"],
        },
        "authority_summary": {
            "mission_id": "mission_llm",
            "allowed_actions": ["research", "draft", "create_report"],
            "forbidden_actions": ["payment", "send_email"],
            "summary": "Research and drafting only; no external send or payment.",
        },
    }


def _clarification_output() -> dict[str, object]:
    return {
        "reply": "J'ai besoin de clarifier la mission avant de commencer.",
        "intent": {"kind": "ask_clarification", "text": "clarify"},
        "clarification_questions": [
            {"prompt": "Quel est l'objectif concret ?", "field_name": "objective", "required": True},
        ],
    }


def _plan(mission_id: str) -> PowerMissionPlan:
    return PowerMissionPlan(
        mission_id=mission_id,
        graph=PowerMissionGraph(
            steps=[
                PowerMissionStep(
                    step_id="write_report",
                    actuator_family=PowerActuatorFamily.WORKSPACE,
                    capability_level=PowerActuatorCapabilityLevel.L3,
                    organ_kind="reversible_workspace",
                    action_kind="write",
                )
            ]
        ),
    )
