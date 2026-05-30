from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.organs.credentials.foundation import CredentialGrant, CredentialGrantStatus
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_login_l6"
URL = "https://example.com/login"
USER_REF = "cred_user_ref"
PASS_REF = "cred_pass_ref"
USERNAME_VALUE = "founder@example.com"
PASSWORD_VALUE = "not-persisted-passphrase"
LOGIN_HTML = """
<html>
  <body>
    <main>
      <h1>Login</h1>
      <form aria-label="Login form" onsubmit="document.querySelector('#status').textContent='Signed in'; return false">
        <input type="text" placeholder="Email" aria-label="Email" />
        <input type="password" placeholder="Password" aria-label="Password" />
        <button type="submit">Sign in</button>
      </form>
      <p id="status">Signed out</p>
    </main>
  </body>
</html>
"""
PAYMENT_LOGIN_HTML = """
<html>
  <body>
    <form aria-label="Login and pay">
      <input type="text" aria-label="Email" />
      <input type="password" aria-label="Password" />
      <input type="text" aria-label="Card number" name="card_number" />
      <button type="submit">Sign in</button>
    </form>
  </body>
</html>
"""


def _credential_grant(ref_id: str, *, status: CredentialGrantStatus = CredentialGrantStatus.ACTIVE, expires_at: datetime | None = None) -> CredentialGrant:
    return CredentialGrant(
        mission_id=MISSION_ID,
        credential_ref_id=ref_id,
        allowed_organs=["browser_login_credential_session_broker_l6"],
        allowed_action_levels=["L6"],
        domain_scope=["example.com"],
        action_scope=["browser_login_credential_session"],
        max_use_count=3,
        status=status,
        revoked_at=datetime.now(UTC) if status is CredentialGrantStatus.REVOKED else None,
        expires_at=expires_at,
        evidence_refs=["cred_evidence_ref"],
    )


def _mission(*, grants: list[CredentialGrant] | None = None, allow_login: bool = True) -> MissionAuthorityEnvelope:
    actions = ["browser_session_open", "browser_session_close"]
    if allow_login:
        actions.append("browser_login_credential_session")
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_login_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Login through governed browser session",
        mission_objective="Use scoped credential refs for one governed browser login.",
        success_criteria=["Login receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live", "browser_login_credential_session_broker_l6"],
        allowed_actions=actions,
        forbidden_actions=[
            "browser_upload_authorized",
            "browser_download_quarantine",
            "browser_js_evaluate_sandboxed",
            "payment_execution",
        ],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        credential_grants=[grant.model_dump(mode="python") for grant in ((_credential_grant(USER_REF), _credential_grant(PASS_REF)) if grants is None else grants)],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _open_session(tmp_path: Path, *, html: str = LOGIN_HTML):
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: html},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        max_steps=5,
    )
    opened = manager.open_session(
        BrowserSessionRequest(
            mission=_mission(),
            url=URL,
            contract=contract,
            action_kind=BrowserSessionActionKind.OPEN,
        )
    )
    assert opened.accepted is True
    return manager, opened.session_id


def _login_contract():
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import BrowserLoginCredentialSessionContract

    return BrowserLoginCredentialSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        username_credential_ref_id=USER_REF,
        password_credential_ref_id=PASS_REF,
        allow_login=True,
    )


def _credential_provider():
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import EphemeralBrowserCredentialProvider

    return EphemeralBrowserCredentialProvider({USER_REF: USERNAME_VALUE, PASS_REF: PASSWORD_VALUE})


def test_l6_login_uses_scoped_credential_refs_and_preserves_evidence(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionBrokerL6,
        BrowserLoginCredentialSessionRequest,
        BrowserLoginCredentialSessionStatus,
    )

    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserLoginCredentialSessionBrokerL6().execute(
            BrowserLoginCredentialSessionRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_login_contract(),
                username_target_role="textbox",
                username_target_name="Email",
                password_target_role="textbox",
                password_target_name="Password",
                submit_target_role="button",
                submit_target_name="Sign in",
            ),
            session_manager=manager,
            credential_provider=_credential_provider(),
        )

        assert result.accepted is True
        assert result.status == BrowserLoginCredentialSessionStatus.LOGGED_IN
        assert result.receipt.before_snapshot_hash
        assert result.receipt.after_snapshot_hash
        assert result.receipt.username_proof_id
        assert result.receipt.password_proof_id
        assert result.receipt.finalgate_verified is True
        assert result.execution_effect == "browser_credential_session_established"
    finally:
        manager.close_all()


def test_l6_login_does_not_persist_raw_credentials(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionBrokerL6,
        BrowserLoginCredentialSessionRequest,
    )

    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserLoginCredentialSessionBrokerL6().execute(
            BrowserLoginCredentialSessionRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_login_contract(),
                username_target_role="textbox",
                username_target_name="Email",
                password_target_role="textbox",
                password_target_name="Password",
                submit_target_role="button",
                submit_target_name="Sign in",
            ),
            session_manager=manager,
            credential_provider=_credential_provider(),
        )

        dumped = result.model_dump_json()
        assert USERNAME_VALUE not in dumped
        assert PASSWORD_VALUE not in dumped
        assert result.receipt.username_credential_ref_id == USER_REF
        assert result.receipt.password_credential_ref_id == PASS_REF
    finally:
        manager.close_all()


def test_l6_login_blocks_missing_revoked_and_expired_grants(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionBrokerL6,
        BrowserLoginCredentialSessionRequest,
    )

    expired = _credential_grant(PASS_REF, expires_at=datetime.now(UTC) - timedelta(seconds=1))
    revoked = _credential_grant(USER_REF, status=CredentialGrantStatus.REVOKED)
    for grants, reason in [
        ([], "credential_grant_missing"),
        ([revoked, _credential_grant(PASS_REF)], "credential_grant_revoked"),
        ([_credential_grant(USER_REF), expired], "credential_grant_expired"),
    ]:
        manager, session_id = _open_session(tmp_path / reason)
        try:
            result = BrowserLoginCredentialSessionBrokerL6().execute(
                BrowserLoginCredentialSessionRequest(
                    mission=_mission(grants=grants),
                    url=URL,
                    session_id=session_id,
                    contract=_login_contract(),
                    username_target_role="textbox",
                    username_target_name="Email",
                    password_target_role="textbox",
                    password_target_name="Password",
                    submit_target_role="button",
                    submit_target_name="Sign in",
                ),
                session_manager=manager,
                credential_provider=_credential_provider(),
            )

            assert result.accepted is False
            assert reason in result.reason
            assert result.execution_effect == "none"
        finally:
            manager.close_all()


def test_l6_login_blocks_payment_upload_or_provider_override(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionBrokerL6,
        BrowserLoginCredentialSessionRequest,
    )

    manager, session_id = _open_session(tmp_path, html=PAYMENT_LOGIN_HTML)
    try:
        result = BrowserLoginCredentialSessionBrokerL6().execute(
            BrowserLoginCredentialSessionRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_login_contract(),
                username_target_role="textbox",
                username_target_name="Email",
                password_target_role="textbox",
                password_target_name="Password",
                submit_target_role="button",
                submit_target_name="Sign in",
                operator_note="provider_override should not be possible",
            ),
            session_manager=manager,
            credential_provider=_credential_provider(),
        )

        assert result.accepted is False
        assert "unsafe_browser_login_payload" in result.reason
        assert result.execution_effect == "none"
    finally:
        manager.close_all()


def test_l6_login_blocks_sensitive_page_even_with_safe_note(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_login_credential_session_broker_l6 import (
        BrowserLoginCredentialSessionBrokerL6,
        BrowserLoginCredentialSessionRequest,
    )

    manager, session_id = _open_session(tmp_path, html=PAYMENT_LOGIN_HTML)
    try:
        result = BrowserLoginCredentialSessionBrokerL6().execute(
            BrowserLoginCredentialSessionRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_login_contract(),
                username_target_role="textbox",
                username_target_name="Email",
                password_target_role="textbox",
                password_target_name="Password",
                submit_target_role="button",
                submit_target_name="Sign in",
            ),
            session_manager=manager,
            credential_provider=_credential_provider(),
        )

        assert result.accepted is False
        assert "sensitive_non_login_field_detected" in result.reason
        assert result.execution_effect == "none"
    finally:
        manager.close_all()
