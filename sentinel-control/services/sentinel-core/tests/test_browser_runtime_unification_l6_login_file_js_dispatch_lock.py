from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sentinel.agent.llm.proposals import DelegatedActionLevel
from sentinel.agent.organs.delegated_action_gate import DelegatedActionGateDecision
from sentinel.agent.organs.organ_dispatch import OrganDispatchStatus, OrganDispatcher
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionStatus,
    execute_organ_runtime_request,
)
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.organs.credentials.foundation import CredentialGrant
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_l6_runtime_unification"
URL = "https://example.com/l6"
USER_REF = "cred_user_ref"
PASS_REF = "cred_pass_ref"
USERNAME_VALUE = "operator@example.com"
PASSWORD_VALUE = "not-persisted-runtime-secret"
HTML = """
<html>
  <body>
    <main>
      <h1>Runtime L6 Browser</h1>
      <form aria-label="Login form" onsubmit="document.querySelector('#status').textContent='Signed in'; return false">
        <input type="text" placeholder="Email" aria-label="Email" />
        <input type="password" placeholder="Password" aria-label="Password" />
        <button type="submit">Sign in</button>
      </form>
      <input type="file" aria-label="Upload file" />
      <a href="data:text/plain,downloaded-report" download="report.txt">Download report</a>
      <p id="status">Waiting</p>
    </main>
  </body>
</html>
"""
LOGIN_HTML = """
<html>
  <body>
    <main>
      <h1>Runtime L6 Login</h1>
      <form aria-label="Login form" onsubmit="document.querySelector('#status').textContent='Signed in'; return false">
        <input type="text" placeholder="Email" aria-label="Email" />
        <input type="password" placeholder="Password" aria-label="Password" />
        <button type="submit">Sign in</button>
      </form>
      <p id="status">Waiting</p>
    </main>
  </body>
</html>
"""


def _credential_grant(ref_id: str) -> CredentialGrant:
    return CredentialGrant(
        mission_id=MISSION_ID,
        credential_ref_id=ref_id,
        allowed_organs=["browser_login_credential_session_broker_l6"],
        allowed_action_levels=["L6"],
        domain_scope=["example.com"],
        action_scope=["browser_login_credential_session"],
        max_use_count=3,
        expires_at=datetime.now(UTC).replace(year=datetime.now(UTC).year + 1),
        evidence_refs=["cred_evidence_ref"],
    )


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="runtime_browser_l6_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Runtime browser L6 promotion mission",
        mission_objective="Run explicit L6 browser special-authority organs through the canonical runtime.",
        success_criteria=["L6 runtime receipts exist"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=[
            "browser_session_l5_live",
            "browser_login_credential_session_broker_l6",
            "browser_download_upload_quarantine_l6",
            "browser_js_sandbox_special_authority_l6",
        ],
        allowed_actions=[
            "browser_session_open",
            "browser_session_close",
            "browser_login_credential_session",
            "browser_file_upload_quarantine",
            "browser_file_download_quarantine",
            "browser_js_sandbox_special_authority",
        ],
        forbidden_actions=["payment_execution"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        credential_grants=[
            _credential_grant(USER_REF).model_dump(mode="python"),
            _credential_grant(PASS_REF).model_dump(mode="python"),
        ],
        max_actions=30,
        max_cost_usd=0.0,
    )


def _runtime_config(tmp_path: Path, **updates: object) -> OrganRuntimeExecutionConfig:
    upload_root = tmp_path / "uploads"
    download_root = tmp_path / "downloads"
    upload_root.mkdir(exist_ok=True)
    download_root.mkdir(exist_ok=True)
    data = {
        "enabled": True,
        "organ_dispatch_enabled": True,
        "mode": OrganRuntimeExecutionMode.BROWSER_L5_L6_SPECIAL_AUTHORITY_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L5, DelegatedActionLevel.L6],
        "allowed_organs": [
            "browser_session_manager",
            "browser_login_credential_session_broker",
            "browser_download_upload_quarantine",
            "browser_js_sandbox_special_authority",
        ],
        "allow_l2": False,
        "allow_l3": False,
        "allow_browser_live_operator": True,
        "allow_browser_special_authority": True,
        "browser_capture_root": str(tmp_path / "browser-captures"),
        "browser_engine": "playwright",
        "browser_document_fixtures": {URL: HTML},
        "browser_persist_sessions": True,
        "browser_accept_downloads": True,
        "browser_ephemeral_credentials": {USER_REF: USERNAME_VALUE, PASS_REF: PASSWORD_VALUE},
        "deny_external_actions": False,
        "deny_network": False,
        "deny_browser": False,
        "deny_credentials": False,
        "deny_shell": True,
        "deny_channel": True,
        "deny_api": True,
        "contract_version": "browser-l6-runtime-unification-test-v1",
    }
    data.update(updates)
    return OrganRuntimeExecutionConfig(**data)


def _gate(level: DelegatedActionLevel):
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
        receipt_contract_hash="browser_l6_runtime_receipt_contract_hash",
    )
    lane = DelegatedActionLane(
        lane_id="lane_browser_l6_runtime_unification",
        mission_id=MISSION_ID,
        source_candidate_id="candidate_browser_l6_runtime_unification",
        lane_status=DelegatedActionLaneStatus.METADATA_ONLY,
        action_level=level,
        organ_kind=OrganProposalKind.BROWSER,
        authority_class=DelegatedActionAuthorityClass.SPECIAL_AUTHORITY,
        risk_class=DelegatedActionRiskClass.HIGH,
        receipt_contract=receipt_requirement,
        revocation_rule="mission_revocation_or_expiry",
        rollback_posture="browser session can be closed",
        user_review_requirement="granted_by_runtime_test_authority",
        allowed_substeps=["browser_session_open"],
        forbidden_substeps=["payment"],
        FinalGate_checks=["receipt", "browser_l6_finalgate"],
    )
    return DelegatedActionGateResult(
        mission_id=MISSION_ID,
        status=DelegatedActionGateStatus.EVALUATED,
        decision=DelegatedActionGateDecision.ALLOWED,
        reasons=[],
        candidate_id="candidate_browser_l6_runtime_unification",
        lane=lane,
        trace=DelegatedActionGateTrace(
            mission_id=MISSION_ID,
            candidate_id="candidate_browser_l6_runtime_unification",
            decision=DelegatedActionGateDecision.ALLOWED,
            reasons=[],
            authority_status=DelegatedActionAuthorityClass.SPECIAL_AUTHORITY,
            budget_status=DelegatedActionBudgetStatus.PASSING,
            evidence_status=DelegatedActionEvidenceStatus.SUPPORTED,
            organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
            safe_summary="Browser L6 runtime test gate allowed.",
        ),
        safety_validation=DelegatedActionGateSafetyValidationResult(),
        risk_class=DelegatedActionRiskClass.HIGH,
        budget_status=DelegatedActionBudgetSummary(status=DelegatedActionBudgetStatus.PASSING),
        evidence_status=DelegatedActionEvidenceSummary(status=DelegatedActionEvidenceStatus.SUPPORTED),
        organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
        receipt_requirement=receipt_requirement,
    )


def _open_request():
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionRequest,
    )

    return BrowserSessionRequest(
        mission=_mission(),
        url=URL,
        contract=BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"]),
        action_kind=BrowserSessionActionKind.OPEN,
    )


def test_runtime_blocks_l6_login_file_js_without_explicit_organs(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import BrowserJSSandboxContract, BrowserJSSandboxRequest

    config = _runtime_config(
        tmp_path,
        allowed_organs=["browser_session_manager"],
        browser_accept_downloads=False,
        deny_credentials=True,
    )
    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L6,
            organ_kind="browser_js_sandbox_special_authority",
            authority_envelope=_mission(),
            gate_result=_gate(DelegatedActionLevel.L6),
            delegated_lane=_gate(DelegatedActionLevel.L6).lane,
            browser_js_sandbox_request=BrowserJSSandboxRequest(
                mission=_mission(),
                url=URL,
                session_id="missing",
                contract=BrowserJSSandboxContract(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allow_js_sandbox=True,
                ),
                script="() => document.title",
                intent_summary="Read a safe page title.",
            ),
        ),
        config=config,
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "organ_not_allowed"


def test_runtime_executes_l6_login_with_ephemeral_credentials_without_persisting_values(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionContract,
        BrowserLoginCredentialSessionRequest,
        BrowserLoginCredentialSessionStatus,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionActionKind, BrowserSessionRequest

    config = _runtime_config(tmp_path, browser_document_fixtures={URL: LOGIN_HTML})
    open_gate = _gate(DelegatedActionLevel.L5)
    l6_gate = _gate(DelegatedActionLevel.L6)
    opened = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=open_gate,
            delegated_lane=open_gate.lane,
            browser_session_request=_open_request(),
        ),
        config=config,
    )
    try:
        login = execute_organ_runtime_request(
            OrganRuntimeExecutionRequest(
                mission_id=MISSION_ID,
                action_level=DelegatedActionLevel.L6,
                organ_kind="browser_login_credential_session_broker",
                authority_envelope=_mission(),
                gate_result=l6_gate,
                delegated_lane=l6_gate.lane,
                browser_login_request=BrowserLoginCredentialSessionRequest(
                    mission=_mission(),
                    url=URL,
                    session_id=opened.receipt.session_id,
                    contract=BrowserLoginCredentialSessionContract(
                        mission_id=MISSION_ID,
                        allowed_domains=["example.com"],
                        username_credential_ref_id=USER_REF,
                        password_credential_ref_id=PASS_REF,
                        allow_login=True,
                    ),
                    username_target_name="Email",
                    password_target_name="Password",
                    submit_target_name="Sign in",
                ),
            ),
            config=config,
        )

        dumped = login.model_dump_json()
        assert login.status is OrganRuntimeExecutionStatus.CERTIFIED
        assert login.organ_kind == "browser_login_credential_session_broker"
        assert login.receipt.status is BrowserLoginCredentialSessionStatus.LOGGED_IN
        assert login.execution_effect == "browser_credential_session_established"
        assert USERNAME_VALUE not in dumped
        assert PASSWORD_VALUE not in dumped
    finally:
        execute_organ_runtime_request(
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
                    contract=_open_request().contract,
                    session_id=opened.receipt.session_id,
                    action_kind=BrowserSessionActionKind.CLOSE,
                ),
            ),
            config=config,
        )


def test_runtime_executes_l6_file_download_quarantine_and_js_sandbox(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineContract,
        BrowserFileQuarantineRequest,
    )
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import (
        BrowserJSSandboxContract,
        BrowserJSSandboxRequest,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionActionKind, BrowserSessionRequest

    config = _runtime_config(tmp_path)
    open_gate = _gate(DelegatedActionLevel.L5)
    l6_gate = _gate(DelegatedActionLevel.L6)
    opened = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L5,
            organ_kind="browser_session_manager",
            authority_envelope=_mission(),
            gate_result=open_gate,
            delegated_lane=open_gate.lane,
            browser_session_request=_open_request(),
        ),
        config=config,
    )
    try:
        download = execute_organ_runtime_request(
            OrganRuntimeExecutionRequest(
                mission_id=MISSION_ID,
                action_level=DelegatedActionLevel.L6,
                organ_kind="browser_download_upload_quarantine",
                authority_envelope=_mission(),
                gate_result=l6_gate,
                delegated_lane=l6_gate.lane,
                browser_file_quarantine_request=BrowserFileQuarantineRequest(
                    mission=_mission(),
                    url=URL,
                    session_id=opened.receipt.session_id,
                    contract=BrowserFileQuarantineContract(
                        mission_id=MISSION_ID,
                        allowed_domains=["example.com"],
                        approved_upload_root=str(tmp_path / "uploads"),
                        approved_download_quarantine_root=str(tmp_path / "downloads"),
                        allow_download=True,
                    ),
                    action_kind=BrowserFileQuarantineActionKind.DOWNLOAD,
                    target_role="link",
                    target_name="Download report",
                ),
            ),
            config=config,
        )
        js = execute_organ_runtime_request(
            OrganRuntimeExecutionRequest(
                mission_id=MISSION_ID,
                action_level=DelegatedActionLevel.L6,
                organ_kind="browser_js_sandbox_special_authority",
                authority_envelope=_mission(),
                gate_result=l6_gate,
                delegated_lane=l6_gate.lane,
                browser_js_sandbox_request=BrowserJSSandboxRequest(
                    mission=_mission(),
                    url=URL,
                    session_id=opened.receipt.session_id,
                    contract=BrowserJSSandboxContract(
                        mission_id=MISSION_ID,
                        allowed_domains=["example.com"],
                        allow_js_sandbox=True,
                    ),
                    script="() => document.querySelector('#status').textContent",
                    intent_summary="Read a local DOM status string without network or storage.",
                ),
            ),
            config=config,
        )

        assert download.status is OrganRuntimeExecutionStatus.CERTIFIED
        assert download.execution_effect == "browser_file_download_quarantined"
        assert download.receipt.file_hash
        assert js.status is OrganRuntimeExecutionStatus.CERTIFIED
        assert js.execution_effect == "browser_js_sandbox_executed"
        assert js.receipt.script_hash
        assert "downloaded-report" not in download.model_dump_json()
    finally:
        execute_organ_runtime_request(
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
                    contract=_open_request().contract,
                    session_id=opened.receipt.session_id,
                    action_kind=BrowserSessionActionKind.CLOSE,
                ),
            ),
            config=config,
        )


def test_dispatcher_routes_open_file_js_close_through_runtime(tmp_path: Path) -> None:
    upload_file = tmp_path / "uploads" / "payload.txt"
    upload_file.parent.mkdir(exist_ok=True)
    upload_file.write_text("safe upload", encoding="utf-8")
    candidates = [
        {
            "proposal_id": "proposal_open",
            "source_role_id": "planner",
            "artifact_kind": "browser_step_candidate",
            "action_level_candidate": "L5",
            "authority_class": "needs_gate",
            "risk_class": "high",
            "budget_estimate": {"action_count": 1},
            "evidence_refs": ["ev_browser_l6"],
            "expected_outcome": "Open session.",
            "rollback_posture": "close session",
            "user_review_required": False,
            "safe_summary": "Open browser session.",
            "browser_organ_kind": "browser_session_manager",
            "url": URL,
            "action_kind": "open",
            "allowed_domains": ["example.com"],
        },
        {
            "proposal_id": "proposal_download",
            "source_role_id": "planner",
            "artifact_kind": "browser_step_candidate",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "risk_class": "high",
            "budget_estimate": {"action_count": 1},
            "evidence_refs": ["ev_browser_l6"],
            "expected_outcome": "Download to quarantine.",
            "rollback_posture": "hash-only receipt",
            "user_review_required": False,
            "safe_summary": "Download a file into quarantine.",
            "browser_organ_kind": "browser_download_upload_quarantine",
            "url": URL,
            "file_action_kind": "download",
            "target_role": "link",
            "target_name": "Download report",
            "approved_upload_root": str(tmp_path / "uploads"),
            "approved_download_quarantine_root": str(tmp_path / "downloads"),
            "allow_download": True,
            "allowed_domains": ["example.com"],
        },
        {
            "proposal_id": "proposal_js",
            "source_role_id": "planner",
            "artifact_kind": "browser_step_candidate",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "risk_class": "high",
            "budget_estimate": {"action_count": 1},
            "evidence_refs": ["ev_browser_l6"],
            "expected_outcome": "Read DOM status through JS sandbox.",
            "rollback_posture": "hash-only JS receipt",
            "user_review_required": False,
            "safe_summary": "Run constrained JS sandbox.",
            "browser_organ_kind": "browser_js_sandbox_special_authority",
            "url": URL,
            "script": "() => document.querySelector('#status').textContent",
            "intent_summary": "Read a safe local DOM field.",
            "allow_js_sandbox": True,
            "allowed_domains": ["example.com"],
        },
        {
            "proposal_id": "proposal_close",
            "source_role_id": "planner",
            "artifact_kind": "browser_step_candidate",
            "action_level_candidate": "L5",
            "authority_class": "needs_gate",
            "risk_class": "high",
            "budget_estimate": {"action_count": 1},
            "evidence_refs": ["ev_browser_l6"],
            "expected_outcome": "Close session.",
            "rollback_posture": "session closed",
            "user_review_required": False,
            "safe_summary": "Close browser session.",
            "browser_organ_kind": "browser_session_manager",
            "url": URL,
            "action_kind": "close",
            "allowed_domains": ["example.com"],
        },
    ]

    result = OrganDispatcher().dispatch(
        mission_id=MISSION_ID,
        action_candidates=candidates,
        proposal_artifacts=candidates,
        config=_runtime_config(tmp_path),
        authority={
            "root_authority_present": True,
            "allowed_action_levels": ["L5", "L6"],
            "allowed_organs": ["browser"],
            "max_risk": "high",
            "special_authority": True,
            "user_review_granted": True,
        },
        authority_envelope=_mission(),
        budget={"remaining_action_count": 10, "remaining_retries": 1, "remaining_tokens": 1000},
        available_evidence_refs=["ev_browser_l6"],
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_action_levels": ["L5", "L6"],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                    "allowed_substeps": [
                        "browser_session_open",
                        "browser_file_download_quarantine",
                        "browser_js_sandbox_special_authority",
                        "browser_session_close",
                ],
                "forbidden_substeps": ["payment"],
            },
        },
    )

    assert result.status is OrganDispatchStatus.COMPLETED
    assert [item.execution_result.organ_kind for item in result.candidate_results] == [
        "browser_session_manager",
        "browser_download_upload_quarantine",
        "browser_js_sandbox_special_authority",
        "browser_session_manager",
    ]
    assert PASSWORD_VALUE not in result.model_dump_json()


def test_dispatcher_routes_open_login_close_through_runtime_without_secret_persistence(tmp_path: Path) -> None:
    common = {
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l6"],
        "rollback_posture": "browser evidence",
        "user_review_required": False,
        "allowed_domains": ["example.com"],
    }
    candidates = [
        {
            **common,
            "proposal_id": "proposal_login_open",
            "action_level_candidate": "L5",
            "authority_class": "needs_gate",
            "expected_outcome": "Open login session.",
            "safe_summary": "Open browser session.",
            "browser_organ_kind": "browser_session_manager",
            "url": URL,
            "action_kind": "open",
        },
        {
            **common,
            "proposal_id": "proposal_login_l6",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "expected_outcome": "Login with scoped refs.",
            "safe_summary": "Login through ephemeral refs.",
            "browser_organ_kind": "browser_login_credential_session_broker",
            "url": URL,
            "username_credential_ref_id": USER_REF,
            "password_credential_ref_id": PASS_REF,
            "username_target_name": "Email",
            "password_target_name": "Password",
            "submit_target_name": "Sign in",
            "allow_login": True,
        },
        {
            **common,
            "proposal_id": "proposal_login_close",
            "action_level_candidate": "L5",
            "authority_class": "needs_gate",
            "expected_outcome": "Close login session.",
            "safe_summary": "Close browser session.",
            "browser_organ_kind": "browser_session_manager",
            "url": URL,
            "action_kind": "close",
        },
    ]

    result = OrganDispatcher().dispatch(
        mission_id=MISSION_ID,
        action_candidates=candidates,
        proposal_artifacts=candidates,
        config=_runtime_config(tmp_path, browser_document_fixtures={URL: LOGIN_HTML}),
        authority={
            "root_authority_present": True,
            "allowed_action_levels": ["L5", "L6"],
            "allowed_organs": ["browser"],
            "max_risk": "high",
            "special_authority": True,
            "user_review_granted": True,
        },
        authority_envelope=_mission(),
        budget={"remaining_action_count": 10, "remaining_retries": 1, "remaining_tokens": 1000},
        available_evidence_refs=["ev_browser_l6"],
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_action_levels": ["L5", "L6"],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                "allowed_substeps": [
                    "browser_session_open",
                    "browser_login_credential_session",
                    "browser_session_close",
                ],
                "forbidden_substeps": ["payment"],
            },
        },
    )

    assert result.status is OrganDispatchStatus.COMPLETED
    assert [item.execution_result.organ_kind for item in result.candidate_results] == [
        "browser_session_manager",
        "browser_login_credential_session_broker",
        "browser_session_manager",
    ]
    dumped = result.model_dump_json()
    assert USERNAME_VALUE not in dumped
    assert PASSWORD_VALUE not in dumped


def test_dispatcher_string_false_does_not_enable_l6_login_js_or_download(tmp_path: Path) -> None:
    common = {
        "source_role_id": "planner",
        "artifact_kind": "browser_step_candidate",
        "risk_class": "high",
        "budget_estimate": {"action_count": 1},
        "evidence_refs": ["ev_browser_l6"],
        "rollback_posture": "browser evidence",
        "user_review_required": False,
        "allowed_domains": ["example.com"],
    }
    candidates = [
        {
            **common,
            "proposal_id": "proposal_false_open",
            "action_level_candidate": "L5",
            "authority_class": "needs_gate",
            "expected_outcome": "Open browser session.",
            "safe_summary": "Open browser session.",
            "browser_organ_kind": "browser_session_manager",
            "url": URL,
            "action_kind": "open",
        },
        {
            **common,
            "proposal_id": "proposal_false_login",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "expected_outcome": "Login should remain disabled.",
            "safe_summary": "String false must not enable login.",
            "browser_organ_kind": "browser_login_credential_session_broker",
            "url": URL,
            "username_credential_ref_id": USER_REF,
            "password_credential_ref_id": PASS_REF,
            "username_target_name": "Email",
            "password_target_name": "Password",
            "submit_target_name": "Sign in",
            "allow_login": "false",
        },
        {
            **common,
            "proposal_id": "proposal_false_download",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "expected_outcome": "Download should remain disabled.",
            "safe_summary": "String false must not enable download.",
            "browser_organ_kind": "browser_download_upload_quarantine",
            "url": URL,
            "file_action_kind": "download",
            "target_role": "link",
            "target_name": "Download report",
            "approved_upload_root": str(tmp_path / "uploads"),
            "approved_download_quarantine_root": str(tmp_path / "downloads"),
            "allow_download": "false",
        },
        {
            **common,
            "proposal_id": "proposal_false_js",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "expected_outcome": "JS should remain disabled.",
            "safe_summary": "String false must not enable JS.",
            "browser_organ_kind": "browser_js_sandbox_special_authority",
            "url": URL,
            "script": "() => document.title",
            "intent_summary": "Read page title.",
            "allow_js_sandbox": "false",
        },
    ]

    result = OrganDispatcher().dispatch(
        mission_id=MISSION_ID,
        action_candidates=candidates,
        proposal_artifacts=candidates,
        config=_runtime_config(tmp_path, browser_document_fixtures={URL: LOGIN_HTML}),
        authority={
            "root_authority_present": True,
            "allowed_action_levels": ["L5", "L6"],
            "allowed_organs": ["browser"],
            "max_risk": "high",
            "special_authority": True,
            "user_review_granted": True,
        },
        authority_envelope=_mission(),
        budget={"remaining_action_count": 10, "remaining_retries": 1, "remaining_tokens": 1000},
        available_evidence_refs=["ev_browser_l6"],
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_action_levels": ["L5", "L6"],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                "allowed_substeps": [
                    "browser_session_open",
                    "browser_login_credential_session",
                    "browser_file_download_quarantine",
                    "browser_js_sandbox_special_authority",
                ],
                "forbidden_substeps": ["payment"],
            },
        },
    )

    blocked_reasons = [
        item.execution_result.blocked_reason
        for item in result.candidate_results
        if item.execution_result is not None and item.execution_result.blocked_reason
    ]

    assert "browser_login_contract_disabled" in blocked_reasons
    assert "browser_download_upload_quarantine_contract_does_not_allow_download" in blocked_reasons
    assert "browser_js_sandbox_contract_disabled" in blocked_reasons


def test_dispatcher_invalid_file_action_kind_fails_closed(tmp_path: Path) -> None:
    candidates = [
        {
            "proposal_id": "proposal_open_invalid_file",
            "source_role_id": "planner",
            "artifact_kind": "browser_step_candidate",
            "action_level_candidate": "L5",
            "authority_class": "needs_gate",
            "risk_class": "high",
            "budget_estimate": {"action_count": 1},
            "evidence_refs": ["ev_browser_l6"],
            "expected_outcome": "Open browser session.",
            "rollback_posture": "close session",
            "user_review_required": False,
            "safe_summary": "Open browser session.",
            "browser_organ_kind": "browser_session_manager",
            "url": URL,
            "action_kind": "open",
            "allowed_domains": ["example.com"],
        },
        {
            "proposal_id": "proposal_invalid_file_action",
            "source_role_id": "planner",
            "artifact_kind": "browser_step_candidate",
            "action_level_candidate": "L6",
            "authority_class": "special_authority",
            "risk_class": "high",
            "budget_estimate": {"action_count": 1},
            "evidence_refs": ["ev_browser_l6"],
            "expected_outcome": "Invalid file action must not downgrade to download.",
            "rollback_posture": "blocked",
            "user_review_required": False,
            "safe_summary": "Invalid file action.",
            "browser_organ_kind": "browser_download_upload_quarantine",
            "url": URL,
            "file_action_kind": "teleport",
            "target_role": "link",
            "target_name": "Download report",
            "approved_upload_root": str(tmp_path / "uploads"),
            "approved_download_quarantine_root": str(tmp_path / "downloads"),
            "allow_download": True,
            "allowed_domains": ["example.com"],
        },
    ]

    result = OrganDispatcher().dispatch(
        mission_id=MISSION_ID,
        action_candidates=candidates,
        proposal_artifacts=candidates,
        config=_runtime_config(tmp_path),
        authority={
            "root_authority_present": True,
            "allowed_action_levels": ["L5", "L6"],
            "allowed_organs": ["browser"],
            "max_risk": "high",
            "special_authority": True,
            "user_review_granted": True,
        },
        authority_envelope=_mission(),
        budget={"remaining_action_count": 10, "remaining_retries": 1, "remaining_tokens": 1000},
        available_evidence_refs=["ev_browser_l6"],
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_action_levels": ["L5", "L6"],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                "allowed_substeps": ["browser_session_open", "browser_file_download_quarantine"],
                "forbidden_substeps": ["payment"],
            },
        },
    )

    execution_results = [item.execution_result for item in result.candidate_results if item.execution_result is not None]
    assert execution_results[0].organ_kind == "browser_session_manager"
    assert execution_results[1].organ_kind == "browser"
    assert execution_results[1].blocked_reason == "failed_to_build_sub_request_for_browser_download_upload_quarantine"
