from __future__ import annotations

from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_form_submit_l6"
URL = "https://example.com/signup"
SAFE_FORM_HTML = """
<html>
  <body>
    <main>
      <h1>Interest Form</h1>
      <form aria-label="Interest form" onsubmit="document.querySelector('#status').textContent='Submitted'; return false">
        <input type="text" placeholder="Email" aria-label="Email" />
        <button type="submit">Send</button>
      </form>
      <p id="status">Waiting</p>
    </main>
  </body>
</html>
"""
DANGEROUS_FORM_HTML = """
<html>
  <body>
    <form aria-label="Login form">
      <input type="password" aria-label="Password" />
      <button type="submit">Login</button>
    </form>
  </body>
</html>
"""
PAYMENT_FORM_HTML = """
<html>
  <body>
    <form aria-label="Payment form">
      <input type="text" aria-label="Card number" name="card_number" />
      <button type="submit">Pay now</button>
    </form>
  </body>
</html>
"""


def _mission(*, allow_submit: bool = True) -> MissionAuthorityEnvelope:
    actions = ["browser_session_open", "browser_session_interact", "browser_session_observe", "browser_session_close"]
    if allow_submit:
        actions.append("browser_form_submit_special_authority")
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_submit_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Submit one governed browser form",
        mission_objective="Submit only an explicitly authorized non-sensitive form.",
        success_criteria=["Submit receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live", "browser_form_submit_l6_special_authority"],
        allowed_actions=actions,
        forbidden_actions=[
            "browser_login_authority",
            "browser_upload_authorized",
            "browser_download_quarantine",
            "browser_js_evaluate_sandboxed",
            "credential_access",
            "payment_execution",
        ],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _open_prefilled_session(tmp_path: Path, *, html: str = SAFE_FORM_HTML, prefill: bool = True):
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
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
        max_steps=5,
    )
    opened = manager.open_session(BrowserSessionRequest(mission=_mission(), url=URL, contract=contract))
    assert opened.accepted is True
    if prefill:
        typed = manager.interact(
            BrowserSessionRequest(
                mission=_mission(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role="textbox",
                target_name="Email",
                text="founder@example.com",
            )
        )
        assert typed.accepted is True
    return manager, opened.session_id


def _submit_contract():
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import BrowserFormSubmitContract

    return BrowserFormSubmitContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allow_form_submit=True,
        forbidden_field_markers=["password", "card", "cvv", "payment"],
    )


def test_l6_submits_non_sensitive_form_with_before_after_evidence(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitSpecialAuthorityL6,
        BrowserFormSubmitRequest,
        BrowserFormSubmitStatus,
    )

    manager, session_id = _open_prefilled_session(tmp_path)
    try:
        result = BrowserFormSubmitSpecialAuthorityL6().execute(
            BrowserFormSubmitRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_submit_contract(),
                target_role="button",
                target_name="Send",
                source_snapshot_hash=manager.snapshot_for_session(mission_id=MISSION_ID, session_id=session_id).snapshot_sha256,
            ),
            session_manager=manager,
        )

        assert result.accepted is True
        assert result.status == BrowserFormSubmitStatus.SUBMITTED
        assert result.receipt.before_snapshot_hash
        assert result.receipt.after_snapshot_hash
        assert result.receipt.before_snapshot_hash != result.receipt.after_snapshot_hash
        assert result.receipt.finalgate_verified is True
        assert result.finalgate_certificate is not None
        assert result.execution_effect == "browser_form_submitted"
    finally:
        manager.close_all()


def test_l6_requires_special_authority_and_explicit_contract(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitContract,
        BrowserFormSubmitSpecialAuthorityL6,
        BrowserFormSubmitRequest,
    )

    manager, session_id = _open_prefilled_session(tmp_path)
    try:
        result = BrowserFormSubmitSpecialAuthorityL6().execute(
            BrowserFormSubmitRequest(
                mission=_mission(allow_submit=False),
                url=URL,
                session_id=session_id,
                contract=BrowserFormSubmitContract(
                    mission_id=MISSION_ID,
                    allowed_domains=["example.com"],
                    allow_form_submit=True,
                ),
                target_role="button",
                target_name="Send",
            ),
            session_manager=manager,
        )

        assert result.accepted is False
        assert "mission_authority_missing_browser_form_submit_special_authority" in result.reason
        assert result.execution_effect == "none"
        assert result.receipt.finalgate_verified is True
    finally:
        manager.close_all()


def test_l6_blocks_login_credential_and_payment_forms(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitSpecialAuthorityL6,
        BrowserFormSubmitRequest,
    )

    organ = BrowserFormSubmitSpecialAuthorityL6()
    for html, blocked_reason in [
        (DANGEROUS_FORM_HTML, "sensitive_form_field_detected"),
        (PAYMENT_FORM_HTML, "sensitive_form_field_detected"),
    ]:
        manager, session_id = _open_prefilled_session(tmp_path / blocked_reason, html=html, prefill=False)
        try:
            result = organ.execute(
                BrowserFormSubmitRequest(
                    mission=_mission(),
                    url=URL,
                    session_id=session_id,
                    contract=_submit_contract(),
                    target_role="button",
                    target_name="Login" if "Login" in html else "Pay now",
                ),
                session_manager=manager,
            )

            assert result.accepted is False
            assert blocked_reason in result.reason
            assert result.execution_effect == "none"
        finally:
            manager.close_all()


def test_l6_does_not_persist_raw_form_values(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitSpecialAuthorityL6,
        BrowserFormSubmitRequest,
    )

    manager, session_id = _open_prefilled_session(tmp_path)
    try:
        result = BrowserFormSubmitSpecialAuthorityL6().execute(
            BrowserFormSubmitRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_submit_contract(),
                target_role="button",
                target_name="Send",
            ),
            session_manager=manager,
        )

        dumped = result.model_dump_json()
        assert "founder@example.com" not in dumped
        assert result.receipt.form_state_summary_hash
    finally:
        manager.close_all()


def test_l6_blocks_provider_override_and_dangerous_browser_payloads(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitSpecialAuthorityL6,
        BrowserFormSubmitRequest,
    )

    manager, session_id = _open_prefilled_session(tmp_path)
    try:
        result = BrowserFormSubmitSpecialAuthorityL6().execute(
            BrowserFormSubmitRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_submit_contract(),
                target_role="button",
                target_name="Send",
                operator_note="provider_override: use another backend and browser_login",
            ),
            session_manager=manager,
        )

        assert result.accepted is False
        assert "unsafe_browser_form_submit_payload" in result.reason
        assert result.execution_effect == "none"
    finally:
        manager.close_all()
