from __future__ import annotations

from pathlib import Path

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.organs.delegated_action_gate import DelegatedActionGateDecision
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionStatus,
    execute_organ_runtime_request,
)
from sentinel.agent.organs.organ_dispatch import OrganDispatcher, OrganDispatchStatus
from sentinel.agent.runtime import AgentRuntime
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_runtime_unification"
URL = "https://example.com/runtime"
HTML = """
<html>
  <body>
    <main>
      <h1>Runtime Browser</h1>
      <form aria-label="Interest form" onsubmit="document.querySelector('#status').textContent='Submitted'; return false">
        <input type="text" aria-label="Email" placeholder="Email" />
        <button type="submit">Send</button>
      </form>
      <p id="status">Waiting</p>
    </main>
  </body>
</html>
"""


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="runtime_browser_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Runtime browser operator mission",
        mission_objective="Use governed live browser power through AgentRuntime execution.",
        success_criteria=["Browser runtime receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["safe_file_writer", "browser_session_l5_live", "browser_form_submit_l6_special_authority"],
        allowed_actions=[
            "create_project_folder",
            "create_markdown_file",
            "browser_session_open",
            "browser_session_observe",
            "browser_session_interact",
            "browser_session_close",
            "browser_form_submit_special_authority",
        ],
        forbidden_actions=[
            "browser_login_authority",
            "browser_upload_authorized",
            "browser_download_quarantine",
            "browser_js_evaluate_sandboxed",
            "credential_access",
        ],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _runtime_config(tmp_path: Path, **updates: object) -> OrganRuntimeExecutionConfig:
    data = {
        "enabled": True,
        "organ_dispatch_enabled": True,
        "mode": OrganRuntimeExecutionMode.BROWSER_LIVE_OPERATOR_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L5],
        "allowed_organs": ["browser_session_manager"],
        "allow_l2": False,
        "allow_l3": False,
        "allow_browser_readonly": False,
        "allow_browser_preparation": False,
        "allow_browser_semantic_extraction": False,
        "allow_browser_live_operator": True,
        "browser_capture_root": str(tmp_path / "browser-captures"),
        "browser_engine": "playwright",
        "browser_document_fixtures": {URL: HTML},
        "deny_external_actions": False,
        "deny_network": False,
        "deny_browser": False,
        "deny_credentials": True,
        "deny_shell": True,
        "deny_channel": True,
        "deny_api": True,
        "contract_version": "browser-runtime-unification-test-v1",
    }
    data.update(updates)
    return OrganRuntimeExecutionConfig(**data)


def _runtime_config_l6(tmp_path: Path, **updates: object) -> OrganRuntimeExecutionConfig:
    data = {
        "enabled": True,
        "organ_dispatch_enabled": True,
        "mode": OrganRuntimeExecutionMode.BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L5, DelegatedActionLevel.L6],
        "allowed_organs": ["browser_session_manager", "browser_form_submit_special_authority"],
        "allow_l2": False,
        "allow_l3": False,
        "allow_browser_live_operator": True,
        "allow_browser_special_authority": True,
        "browser_capture_root": str(tmp_path / "browser-captures"),
        "browser_engine": "playwright",
        "browser_document_fixtures": {URL: HTML},
        "browser_persist_sessions": True,
        "deny_external_actions": False,
        "deny_network": False,
        "deny_browser": False,
        "deny_credentials": True,
        "deny_shell": True,
        "deny_channel": True,
        "deny_api": True,
        "contract_version": "browser-runtime-unification-l6-test-v1",
    }
    data.update(updates)
    return OrganRuntimeExecutionConfig(**data)


def _allowed_gate(level: DelegatedActionLevel = DelegatedActionLevel.L5):
    from sentinel.agent.organs.delegated_action_gate import (
        DelegatedActionAuthorityClass,
        DelegatedActionBudgetSummary,
        DelegatedActionBudgetStatus,
        DelegatedActionEvidenceSummary,
        DelegatedActionEvidenceStatus,
        DelegatedActionGateResult,
        DelegatedActionGateSafetyValidationResult,
        DelegatedActionGateStatus,
        DelegatedActionGateTrace,
        DelegatedActionLane,
        DelegatedActionLaneStatus,
        DelegatedActionOrganContractStatus,
        DelegatedActionReceiptRequirement,
        DelegatedActionRiskClass,
    )
    from sentinel.agent.organs.proposal_bridge import OrganProposalKind

    receipt_requirement = DelegatedActionReceiptRequirement(
        required_receipt_fields=["receipt_id", "finalgate_verified"],
        receipt_contract_hash="browser_runtime_receipt_contract_hash",
    )
    lane = DelegatedActionLane(
        lane_id="lane_browser_runtime_unification",
        mission_id=MISSION_ID,
        source_candidate_id="candidate_browser_runtime_unification",
        organ_kind=OrganProposalKind.BROWSER,
        action_level=level,
        allowed_substeps=["browser_session_open"],
        forbidden_substeps=["browser_submit", "browser_login", "credential"],
        authority_class=DelegatedActionAuthorityClass.SPECIAL_AUTHORITY,
        risk_class=DelegatedActionRiskClass.HIGH,
        receipt_contract=receipt_requirement,
        revocation_rule="mission_revocation_or_expiry",
        rollback_posture="browser session can be closed",
        user_review_requirement="granted_by_runtime_test_authority",
        FinalGate_checks=["receipt", "browser_session_finalgate"],
        lane_status=DelegatedActionLaneStatus.METADATA_ONLY,
    )
    return DelegatedActionGateResult(
        mission_id=MISSION_ID,
        status=DelegatedActionGateStatus.EVALUATED,
        decision=DelegatedActionGateDecision.ALLOWED,
        reasons=[],
        candidate_id="candidate_browser_runtime_unification",
        lane=lane,
        trace=DelegatedActionGateTrace(
            mission_id=MISSION_ID,
            candidate_id="candidate_browser_runtime_unification",
            decision=DelegatedActionGateDecision.ALLOWED,
            reasons=[],
            authority_status=DelegatedActionAuthorityClass.SPECIAL_AUTHORITY,
            budget_status=DelegatedActionBudgetStatus.PASSING,
            evidence_status=DelegatedActionEvidenceStatus.SUPPORTED,
            organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
            safe_summary="Browser L5 runtime test gate allowed.",
        ),
        safety_validation=DelegatedActionGateSafetyValidationResult(),
        risk_class=DelegatedActionRiskClass.HIGH,
        budget_status=DelegatedActionBudgetSummary(status=DelegatedActionBudgetStatus.PASSING),
        evidence_status=DelegatedActionEvidenceSummary(status=DelegatedActionEvidenceStatus.SUPPORTED),
        organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
        receipt_requirement=receipt_requirement,
    )


def test_power_lab_promotes_operator_browser_l5_template_to_executable_runtime_config(tmp_path: Path) -> None:
    from sentinel.power_lab import build_power_lab_runtime_config

    config = build_power_lab_runtime_config(
        "operator_browser_l5_template",
        enable_organ_dispatch=True,
    )

    assert config.enabled is True
    assert config.organ_dispatch_enabled is True
    assert config.mode is OrganRuntimeExecutionMode.BROWSER_LIVE_OPERATOR_ONLY
    assert DelegatedActionLevel.L5 in config.allowed_action_levels
    assert "browser_session_manager" in config.allowed_organs
    assert config.allow_browser_live_operator is True
    assert config.deny_credentials is True
    assert config.deny_shell is True
    assert config.deny_channel is True
    assert config.deny_api is True


def test_default_runtime_still_blocks_browser_l5_session_manager(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionRequest,
    )

    request = BrowserSessionRequest(
        mission=_mission(),
        url=URL,
        contract=BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"]),
        action_kind=BrowserSessionActionKind.OPEN,
    )

    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=_allowed_gate(),
            delegated_lane=_allowed_gate().lane,
            browser_session_request=request,
        )
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "organ_execution_disabled"
    assert not (tmp_path / "browser-captures").exists()


def test_browser_l6_runtime_templates_are_explicit_and_default_off_for_unrelated_surfaces() -> None:
    from sentinel.power_lab import PowerLabMissionRejected, build_power_lab_runtime_config

    submit_config = build_power_lab_runtime_config("browser_form_submit_l6_template", enable_organ_dispatch=True)
    assert submit_config.mode is OrganRuntimeExecutionMode.BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY
    assert "browser_form_submit_special_authority" in submit_config.allowed_organs
    assert submit_config.deny_credentials is True

    login_config = build_power_lab_runtime_config("browser_login_l6_template", enable_organ_dispatch=True)
    assert login_config.mode is OrganRuntimeExecutionMode.BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY
    assert "browser_login_credential_session_broker" in login_config.allowed_organs
    assert login_config.browser_ephemeral_credentials == {}
    assert login_config.deny_credentials is False

    file_config = build_power_lab_runtime_config("browser_file_quarantine_l6_template", enable_organ_dispatch=True)
    assert "browser_download_upload_quarantine" in file_config.allowed_organs
    assert file_config.browser_accept_downloads is True
    assert file_config.deny_credentials is True

    js_config = build_power_lab_runtime_config("browser_js_sandbox_l6_template", enable_organ_dispatch=True)
    assert "browser_js_sandbox_special_authority" in js_config.allowed_organs
    assert js_config.deny_shell is True
    assert js_config.deny_api is True

    try:
        build_power_lab_runtime_config("full_power_template", enable_organ_dispatch=True)
    except PowerLabMissionRejected as exc:
        assert "non-executing template" in str(exc)
    else:  # pragma: no cover - defensive clarity
        raise AssertionError("full_power_template unexpectedly became executable")


def test_browser_live_runtime_blocks_l6_submit_login_credential_surfaces(tmp_path: Path) -> None:
    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L6,
            organ_kind="browser_form_submit_special_authority",
            authority_envelope=_mission(),
            gate_result=_allowed_gate(DelegatedActionLevel.L6),
            delegated_lane=_allowed_gate(DelegatedActionLevel.L6).lane,
            metadata={
                "browser_submit": True,
                "browser_login": True,
                "credential": True,
            },
        ),
        config=_runtime_config(tmp_path),
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason in {"unsafe_runtime_execution_payload", "action_level_not_allowed"}
    assert result.execution_effect == "none"


def test_runtime_executes_browser_l5_session_manager_open_with_receipt_and_finalgate(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionRequest,
    )

    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
    )
    browser_request = BrowserSessionRequest(
        mission=_mission(),
        url=URL,
        contract=contract,
        action_kind=BrowserSessionActionKind.OPEN,
    )

    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=_allowed_gate(),
            delegated_lane=_allowed_gate().lane,
            browser_session_request=browser_request,
        ),
        config=_runtime_config(tmp_path),
    )

    assert result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert result.organ_kind == "browser_session_manager"
    assert result.execution_effect == "browser_session_opened"
    assert result.receipt is not None
    assert result.receipt.session_id
    assert result.finalgate_certificate is not None
    assert result.finalgate_certificate.certified is True
    assert (tmp_path / "browser-captures").exists()


def test_runtime_preserves_l5_browser_session_across_open_and_observe(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionRequest,
        BrowserSessionStatus,
    )

    config = _runtime_config(tmp_path, browser_persist_sessions=True)
    gate = _allowed_gate()
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    opened = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=gate,
            delegated_lane=gate.lane,
            browser_session_request=BrowserSessionRequest(
                mission=_mission(),
                url=URL,
                contract=contract,
                action_kind=BrowserSessionActionKind.OPEN,
            ),
        ),
        config=config,
    )
    observed = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=gate,
            delegated_lane=gate.lane,
            browser_session_request=BrowserSessionRequest(
                mission=_mission(),
                url=URL,
                contract=contract,
                session_id=opened.receipt.session_id,
                action_kind=BrowserSessionActionKind.OBSERVE,
            ),
        ),
        config=config,
    )
    closed = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=gate,
            delegated_lane=gate.lane,
            browser_session_request=BrowserSessionRequest(
                mission=_mission(),
                url=URL,
                contract=contract,
                session_id=opened.receipt.session_id,
                action_kind=BrowserSessionActionKind.CLOSE,
            ),
        ),
        config=config,
    )

    assert opened.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert observed.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert closed.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert observed.receipt.session_id == opened.receipt.session_id
    assert observed.receipt.status is BrowserSessionStatus.OBSERVED
    assert observed.execution_effect == "browser_session_observed"


def test_runtime_executes_l6_non_sensitive_form_submit_with_persisted_l5_session(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitContract,
        BrowserFormSubmitRequest,
        BrowserFormSubmitStatus,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionRequest,
    )

    config = _runtime_config_l6(tmp_path)
    open_gate = _allowed_gate(DelegatedActionLevel.L5)
    submit_gate = _allowed_gate(DelegatedActionLevel.L6)
    session_contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])
    opened = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=open_gate,
            delegated_lane=open_gate.lane,
            browser_session_request=BrowserSessionRequest(
                mission=_mission(),
                url=URL,
                contract=session_contract,
                action_kind=BrowserSessionActionKind.OPEN,
            ),
        ),
        config=config,
    )
    submitted = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L6,
            organ_kind="browser_form_submit_special_authority",
            authority_envelope=_mission(),
            gate_result=submit_gate,
            delegated_lane=submit_gate.lane,
            browser_form_submit_request=BrowserFormSubmitRequest(
                mission=_mission(),
                url=URL,
                session_id=opened.receipt.session_id,
                contract=BrowserFormSubmitContract(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allow_form_submit=True,
                ),
                target_role="button",
                target_name="Send",
                source_snapshot_hash=opened.receipt.before_snapshot_hash,
            ),
        ),
        config=config,
    )
    closed = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=open_gate,
            delegated_lane=open_gate.lane,
            browser_session_request=BrowserSessionRequest(
                mission=_mission(),
                url=URL,
                contract=session_contract,
                session_id=opened.receipt.session_id,
                action_kind=BrowserSessionActionKind.CLOSE,
            ),
        ),
        config=config,
    )

    assert opened.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert submitted.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert closed.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert submitted.receipt.status is BrowserFormSubmitStatus.SUBMITTED
    assert submitted.execution_effect == "browser_form_submitted"
    assert submitted.finalgate_certificate is not None
    assert submitted.finalgate_certificate.certified is True


def test_dispatcher_routes_browser_l5_session_manager_through_gate_to_runtime(tmp_path: Path) -> None:
    proposal = {
        "proposal_id": "proposal_browser_l5_runtime",
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "action_level_candidate": "L5",
        "authority_class": "needs_gate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l5"],
        "expected_outcome": "Open a governed live browser session.",
        "rollback_posture": "browser session can be closed",
        "user_review_required": False,
        "safe_summary": "Open a live browser session through the Sentinel runtime.",
        "browser_organ_kind": "browser_session_manager",
        "url": URL,
        "action_kind": "open",
        "allowed_domains": ["example.com"],
    }
    result = OrganDispatcher().dispatch(
        mission_id=MISSION_ID,
        action_candidates=[proposal],
        proposal_artifacts=[proposal],
        config=_runtime_config(tmp_path),
        authority={
            "root_authority_present": True,
            "allowed_action_levels": ["L5"],
            "allowed_organs": ["browser"],
            "max_risk": "high",
            "special_authority": True,
            "user_review_granted": True,
        },
        authority_envelope=_mission(),
        budget={"remaining_action_count": 5, "remaining_retries": 1, "remaining_tokens": 1000},
        available_evidence_refs=["ev_browser_l5"],
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_action_levels": ["L5"],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                "allowed_substeps": ["browser_session_open"],
                "forbidden_substeps": ["browser_submit", "browser_login", "credential"],
            },
        },
    )

    assert result.status is OrganDispatchStatus.COMPLETED
    candidate = result.candidate_results[0]
    assert candidate.gate_decision is DelegatedActionGateDecision.ALLOWED
    assert candidate.execution_result is not None
    assert candidate.execution_result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert candidate.execution_result.organ_kind == "browser_session_manager"
    assert candidate.execution_result.receipt.session_id


def test_dispatcher_routes_l5_open_then_l6_form_submit_through_runtime(tmp_path: Path) -> None:
    open_proposal = {
        "proposal_id": "proposal_browser_l5_open_for_submit",
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "action_level_candidate": "L5",
        "authority_class": "needs_gate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l6"],
        "expected_outcome": "Open a governed live browser session.",
        "rollback_posture": "browser session can be closed",
        "user_review_required": False,
        "safe_summary": "Open a live browser session before submit.",
        "browser_organ_kind": "browser_session_manager",
        "url": URL,
        "action_kind": "open",
        "allowed_domains": ["example.com"],
    }
    submit_proposal = {
        "proposal_id": "proposal_browser_l6_submit",
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "action_level_candidate": "L6",
        "authority_class": "special_authority",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l6"],
        "expected_outcome": "Submit one non-sensitive governed form.",
        "rollback_posture": "browser evidence before and after submit",
        "user_review_required": False,
        "safe_summary": "Submit the non-sensitive interest form through special authority.",
        "browser_organ_kind": "browser_form_submit_special_authority",
        "url": URL,
        "target_role": "button",
        "target_name": "Send",
        "allowed_domains": ["example.com"],
        "allow_form_submit": True,
    }
    close_proposal = {
        "proposal_id": "proposal_browser_l5_close_after_submit",
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "action_level_candidate": "L5",
        "authority_class": "needs_gate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l6"],
        "expected_outcome": "Close the governed browser session.",
        "rollback_posture": "browser session closed",
        "user_review_required": False,
        "safe_summary": "Close the browser session after submit.",
        "browser_organ_kind": "browser_session_manager",
        "url": URL,
        "action_kind": "close",
        "allowed_domains": ["example.com"],
    }

    result = OrganDispatcher().dispatch(
        mission_id=MISSION_ID,
        action_candidates=[open_proposal, submit_proposal, close_proposal],
        proposal_artifacts=[open_proposal, submit_proposal, close_proposal],
        config=_runtime_config_l6(tmp_path),
        authority={
            "root_authority_present": True,
            "allowed_action_levels": ["L5", "L6"],
            "allowed_organs": ["browser"],
            "max_risk": "high",
            "special_authority": True,
            "user_review_granted": True,
        },
        authority_envelope=_mission(),
        budget={"remaining_action_count": 5, "remaining_retries": 1, "remaining_tokens": 1000},
        available_evidence_refs=["ev_browser_l6"],
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_action_levels": ["L5", "L6"],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                "allowed_substeps": ["browser_session_open", "browser_form_submit_special_authority"],
                "forbidden_substeps": ["browser_login", "credential", "payment"],
            },
        },
    )

    assert result.status is OrganDispatchStatus.COMPLETED
    assert len(result.candidate_results) == 3
    assert result.candidate_results[0].execution_result.organ_kind == "browser_session_manager"
    submit_execution = result.candidate_results[1].execution_result
    assert submit_execution is not None
    assert submit_execution.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert submit_execution.organ_kind == "browser_form_submit_special_authority"
    assert submit_execution.execution_effect == "browser_form_submitted"
    close_execution = result.candidate_results[2].execution_result
    assert close_execution is not None
    assert close_execution.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert close_execution.execution_effect == "browser_session_closed"


def test_agentruntime_run_routes_browser_l5_session_manager_when_explicitly_opted_in(tmp_path: Path) -> None:
    proposal = {
        "proposal_id": "proposal_browser_l5_runtime_run",
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "action_level_candidate": "L5",
        "authority_class": "needs_gate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l5"],
        "expected_outcome": "Open a governed live browser session.",
        "rollback_posture": "browser session can be closed",
        "user_review_required": False,
        "safe_summary": "Open a live browser session through AgentRuntime.run.",
        "browser_organ_kind": "browser_session_manager",
        "url": URL,
        "action_kind": "open",
        "allowed_domains": ["example.com"],
    }
    runtime = AgentRuntime(
        project_root=tmp_path / "project",
        organ_execution_config=_runtime_config(tmp_path, temporary_candidate_bridge_enabled=True),
    )

    result = runtime.run(
        _mission(),
        user_input={
            "organ_dispatch": {
                "action_candidates": [proposal],
                "authority": {
                    "root_authority_present": True,
                    "allowed_action_levels": ["L5"],
                    "allowed_organs": ["browser"],
                    "max_risk": "high",
                    "special_authority": True,
                    "user_review_granted": True,
                },
                "budget": {
                    "remaining_action_count": 5,
                    "remaining_retries": 1,
                    "remaining_tokens": 1000,
                    "organ_budget_units": {"browser": 5},
                },
                "available_evidence_refs": ["ev_browser_l5"],
                "organ_contracts": {
                    "browser": {
                        "available": True,
                        "allowed_action_levels": ["L5"],
                        "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                        "allowed_substeps": ["browser_session_open"],
                        "forbidden_substeps": ["browser_submit", "browser_login", "credential"],
                    },
                },
            }
        },
        evidence_refs=["ev_browser_l5"],
    )

    assert result.organ_dispatch_result is not None
    dispatch = result.organ_dispatch_result
    assert dispatch.status is OrganDispatchStatus.COMPLETED
    execution = dispatch.candidate_results[0].execution_result
    assert execution is not None
    assert execution.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert execution.organ_kind == "browser_session_manager"
    assert result.automatic_replan_executed is False
