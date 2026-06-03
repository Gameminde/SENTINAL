from __future__ import annotations

from pathlib import Path

from sentinel.agent import AgentRuntime
from sentinel.agent.browser.neural.motor_proposal import MotorProposalArtifact
from sentinel.agent.browser.neural.models import stable_neural_hash
from sentinel.agent.organs.organ_dispatch import OrganDispatchStatus

from test_browser_runtime_agentruntime_full_browser_stack_lock import _model_contract, _runtime_mission
from test_browser_runtime_unification_l6_login_file_js_dispatch_lock import HTML, MISSION_ID, URL, _runtime_config


def _motor_proposal(proposal_id: str = "mprop_browser_open", action_kind: str = "open") -> dict[str, object]:
    payload = {
        "proposal_artifact_id": proposal_id,
        "mission_id": MISSION_ID,
        "organ_kind": "browser_session_manager",
        "action_level": "L5",
        "target_ref": "target_browser_open",
        "source_signal_refs": ["nsig_planner"],
        "source_evidence_refs": ["ev_browser_l6"],
        "required_authority": "L5_browser_operator",
        "risk_flags": [],
        "expected_receipt_type": "BrowserSessionReceipt",
        "verification_plan": {"expected": "receipt_and_finalgate_required"},
        "url": URL,
        "action_kind": action_kind,
        "allowed_domains": ["example.com"],
        "target_role": None,
        "target_name": None,
        "text": None,
    }
    proposal = MotorProposalArtifact(**payload, artifact_hash=stable_neural_hash(payload))
    return proposal.model_dump(mode="python")


def _brain_input(motor_proposals: list[dict[str, object]]) -> dict[str, object]:
    return {
        "mission_id": MISSION_ID,
        "objective_summary": "Route browser neural motor proposals through the Sentinel spine.",
        "user_model_contract": _model_contract().model_dump(mode="python"),
        "available_evidence_refs": ["ev_browser_l6"],
        "existing_proposal_artifacts": motor_proposals,
        "risk_flags": ["browser_neural_motor_proposal"],
    }


def _user_input(motor_proposals: list[dict[str, object]]) -> dict[str, object]:
    return {
        "organ_dispatch": {
            "brain_cognition_input": _brain_input(motor_proposals),
            "authority": {
                "root_authority_present": True,
                "allowed_action_levels": ["L5"],
                "allowed_organs": ["browser"],
                "max_risk": "high",
                "special_authority": True,
                "user_review_granted": True,
            },
            "budget": {
                "remaining_action_count": 3,
                "remaining_retries": 1,
                "remaining_tokens": 1000,
                "organ_budget_units": {"browser": 3},
            },
            "available_evidence_refs": ["ev_browser_l6"],
            "organ_contracts": {
                "browser": {
                    "available": True,
                    "allowed_action_levels": ["L5"],
                    "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                    "allowed_substeps": ["browser_session_open", "browser_session_close"],
                    "forbidden_substeps": ["payment", "browser_login", "upload_file", "download_file"],
                    "allowed_domains": ["example.com"],
                },
            },
        }
    }


def _config(tmp_path: Path, *, neural_enabled: bool):
    return _runtime_config(
        tmp_path,
        mode="browser_live_operator_only",
        allowed_action_levels=["L5"],
        allowed_organs=["browser_session_manager"],
        allow_browser_special_authority=False,
        brain_native_candidate_source_enabled=True,
        browser_neural_motor_proposal_source_enabled=neural_enabled,
        memory_feedback_enabled=True,
        temporary_candidate_bridge_enabled=False,
        browser_document_fixtures={URL: HTML},
        browser_accept_downloads=False,
        deny_credentials=True,
        contract_version="browser-neural-motor-dispatch-test-v1",
    )


def test_neural_motor_proposal_disabled_by_default(tmp_path: Path) -> None:
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, neural_enabled=False)).run(
        _runtime_mission(),
            user_input=_user_input([_motor_proposal()]),
    )

    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.status is OrganDispatchStatus.NO_CANDIDATES
    assert result.organ_dispatch_result.trace.executed_count == 0


def test_neural_motor_proposal_rejects_invalid_or_dangerous_action_kind() -> None:
    from sentinel.agent.browser.neural import motor_proposal_artifact_to_browser_step_candidate

    assert motor_proposal_artifact_to_browser_step_candidate(_motor_proposal("mprop_submit", "submit")) is None
    assert motor_proposal_artifact_to_browser_step_candidate(_motor_proposal("mprop_js", "evaluate_js")) is None
    assert motor_proposal_artifact_to_browser_step_candidate(_motor_proposal("mprop_unknown", "teleport")) is None


def test_neural_motor_proposal_enters_dispatcher_gate_runtime_when_enabled(tmp_path: Path) -> None:
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, neural_enabled=True)).run(
        _runtime_mission(),
            user_input=_user_input([
                _motor_proposal("mprop_browser_open", "open"),
                _motor_proposal("mprop_browser_close", "close"),
            ]),
    )

    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.status is OrganDispatchStatus.COMPLETED
    assert result.organ_dispatch_result.trace.executed_count == 2
    candidate = result.organ_dispatch_result.candidate_results[0]
    assert candidate.execution_result is not None
    assert candidate.execution_result.receipt is not None
    assert candidate.execution_result.finalgate_certificate is not None
    assert result.memory_feedback_result is not None
    assert result.replan_ready is True
    assert result.automatic_replan_executed is False
