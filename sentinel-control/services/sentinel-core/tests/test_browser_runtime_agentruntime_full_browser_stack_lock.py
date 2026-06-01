from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sentinel.agent import AgentRuntime
from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile
from sentinel.agent.organs.organ_dispatch import OrganDispatchStatus
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionMode
from sentinel.mission.models import MissionAuthorityEnvelope

from test_browser_runtime_unification_l6_login_file_js_dispatch_lock import (
    HTML,
    LOGIN_HTML,
    MISSION_ID,
    PASS_REF,
    PASSWORD_VALUE,
    URL,
    USERNAME_VALUE,
    USER_REF,
    _mission,
    _runtime_config,
)


NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _model_contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id="groq",
        selected_backend_id="groq_openai_compatible_chat",
        selected_model="openai/gpt-oss-20b",
        cost_profile=ModelCostProfile(
            model_name="openai/gpt-oss-20b",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="openai/gpt-oss-20b",
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=250,
            max_evidence_tokens=1_000,
            reserve_output_tokens=200,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="browser_full_stack_native_candidate_source",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


def _common_candidate() -> dict[str, Any]:
    return {
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l6"],
        "rollback_posture": "browser evidence and explicit close",
        "user_review_required": False,
        "allowed_domains": ["example.com"],
    }


def _open_candidate(proposal_id: str = "brain_open") -> dict[str, Any]:
    return {
        **_common_candidate(),
        "proposal_id": proposal_id,
        "action_level_candidate": "L5",
        "authority_class": "needs_gate",
        "expected_outcome": "Open governed browser session.",
        "safe_summary": "Open a browser session through Brain-native AgentRuntime path.",
        "browser_organ_kind": "browser_session_manager",
        "url": URL,
        "action_kind": "open",
    }


def _close_candidate(proposal_id: str = "brain_close") -> dict[str, Any]:
    return {
        **_common_candidate(),
        "proposal_id": proposal_id,
        "action_level_candidate": "L5",
        "authority_class": "needs_gate",
        "expected_outcome": "Close governed browser session.",
        "safe_summary": "Close the browser session through Brain-native AgentRuntime path.",
        "browser_organ_kind": "browser_session_manager",
        "url": URL,
        "action_kind": "close",
    }


def _login_candidate() -> dict[str, Any]:
    return {
        **_common_candidate(),
        "proposal_id": "brain_login_l6",
        "action_level_candidate": "L6",
        "authority_class": "special_authority",
        "expected_outcome": "Login with scoped credential refs and no raw credential persistence.",
        "safe_summary": "Login through the L6 credential session broker.",
        "browser_organ_kind": "browser_login_credential_session_broker",
        "url": URL,
        "username_credential_ref_id": USER_REF,
        "password_credential_ref_id": PASS_REF,
        "username_target_name": "Email",
        "password_target_name": "Password",
        "submit_target_name": "Sign in",
        "allow_login": True,
    }


def _download_candidate(tmp_path: Path) -> dict[str, Any]:
    return {
        **_common_candidate(),
        "proposal_id": "brain_download_l6",
        "action_level_candidate": "L6",
        "authority_class": "special_authority",
        "expected_outcome": "Quarantine a browser download.",
        "safe_summary": "Download through quarantine only.",
        "browser_organ_kind": "browser_download_upload_quarantine",
        "url": URL,
        "file_action_kind": "download",
        "target_name": "Download report",
        "approved_upload_root": str(tmp_path / "uploads"),
        "approved_download_quarantine_root": str(tmp_path / "downloads"),
        "allow_download": True,
    }


def _js_candidate() -> dict[str, Any]:
    return {
        **_common_candidate(),
        "proposal_id": "brain_js_l6",
        "action_level_candidate": "L6",
        "authority_class": "special_authority",
        "expected_outcome": "Read a DOM field through the constrained JS sandbox.",
        "safe_summary": "Execute hash-only JS sandbox query.",
        "browser_organ_kind": "browser_js_sandbox_special_authority",
        "url": URL,
        "script": "() => document.querySelector('#status').textContent",
        "intent_summary": "Read a safe local DOM field.",
        "allow_js_sandbox": True,
    }


def _brain_input(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mission_id": MISSION_ID,
        "objective_summary": "Run the promoted browser stack from native Brain proposal artifacts.",
        "user_model_contract": _model_contract().model_dump(mode="python"),
        "available_evidence_refs": ["ev_browser_l6"],
        "existing_proposal_artifacts": candidates,
        "risk_flags": ["browser_special_authority"],
        "current_time": NOW,
    }


def _user_input(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "organ_dispatch": {
            "brain_cognition_input": _brain_input(candidates),
            "action_candidates": [
                {
                    **_open_candidate("temporary_fallback_must_not_execute"),
                    "url": "https://example.com/fallback",
                }
            ],
            "authority": {
                "root_authority_present": True,
                "allowed_action_levels": ["L5", "L6"],
                "allowed_organs": ["browser"],
                "max_risk": "high",
                "special_authority": True,
                "user_review_granted": True,
            },
            "budget": {
                "remaining_action_count": 10,
                "remaining_retries": 1,
                "remaining_tokens": 1000,
                "organ_budget_units": {"browser": 10},
            },
            "available_evidence_refs": ["ev_browser_l6"],
            "organ_contracts": {
                "browser": {
                    "available": True,
                    "allowed_action_levels": ["L5", "L6"],
                    "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                    "allowed_substeps": [
                        "browser_session_open",
                        "browser_login_credential_session",
                        "browser_file_download_quarantine",
                        "browser_js_sandbox_special_authority",
                        "browser_session_close",
                    ],
                    "forbidden_substeps": ["payment"],
                },
            },
        }
    }


def _config(tmp_path: Path, *, html: str) -> Any:
    return _runtime_config(
        tmp_path,
        browser_document_fixtures={URL: html},
        brain_native_candidate_source_enabled=True,
        memory_feedback_enabled=True,
        temporary_candidate_bridge_enabled=False,
    )


def _runtime_mission() -> MissionAuthorityEnvelope:
    data = _mission().model_dump(mode="python")
    data["allowed_tools"] = [
        *data.get("allowed_tools", []),
        "safe_file_writer",
        "safe_local_markdown_tool",
        "browser_readonly_public",
    ]
    data["allowed_actions"] = [
        *data.get("allowed_actions", []),
        "create_project_folder",
        "create_markdown_file",
        "browser_read_public_page",
    ]
    return MissionAuthorityEnvelope(**data)


def test_agentruntime_brain_native_routes_l6_login_stack_without_temporary_bridge(tmp_path: Path) -> None:
    candidates = [_open_candidate(), _login_candidate(), _close_candidate()]
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, html=LOGIN_HTML)).run(
        _runtime_mission(),
        user_input=_user_input(candidates),
        evidence_refs=["ev_browser_l6"],
    )

    assert result.brain_candidate_source_status == "CLOSED"
    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.status is OrganDispatchStatus.COMPLETED
    assert [
        item.execution_result.organ_kind
        for item in result.organ_dispatch_result.candidate_results
        if item.execution_result is not None
    ] == [
        "browser_session_manager",
        "browser_login_credential_session_broker",
        "browser_session_manager",
    ]
    dumped = result.model_dump_json()
    assert USERNAME_VALUE not in dumped
    assert PASSWORD_VALUE not in dumped
    assert "temporary_fallback_must_not_execute" not in dumped
    assert result.memory_feedback_path == "CLOSED"
    assert result.replan_ready is True
    assert result.automatic_replan_executed is False


def test_agentruntime_brain_native_routes_file_quarantine_and_js_sandbox_stack(tmp_path: Path) -> None:
    candidates = [_open_candidate(), _download_candidate(tmp_path), _js_candidate(), _close_candidate()]
    result = AgentRuntime(project_root=tmp_path / "project", organ_execution_config=_config(tmp_path, html=HTML)).run(
        _runtime_mission(),
        user_input=_user_input(candidates),
        evidence_refs=["ev_browser_l6"],
    )

    assert result.brain_candidate_source_status == "CLOSED"
    assert result.organ_dispatch_result is not None
    assert result.organ_dispatch_result.status is OrganDispatchStatus.COMPLETED
    assert [
        item.execution_result.organ_kind
        for item in result.organ_dispatch_result.candidate_results
        if item.execution_result is not None
    ] == [
        "browser_session_manager",
        "browser_download_upload_quarantine",
        "browser_js_sandbox_special_authority",
        "browser_session_manager",
    ]
    assert result.memory_feedback_path == "CLOSED"
    assert result.replan_packet is not None
    assert result.replan_packet["status"] == "CLOSED"
    assert result.replan_packet["receipt_refs"]
    assert result.replan_packet["finalgate_certificate_refs"]
    assert result.automatic_replan_executed is False
