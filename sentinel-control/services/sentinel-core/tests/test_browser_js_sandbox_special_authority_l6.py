from __future__ import annotations

from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_js_sandbox_l6"
URL = "https://example.com/app"
HTML = """
<html>
  <body>
    <main>
      <h1>Sandbox Console</h1>
      <p id="status">Waiting</p>
      <button>Ready</button>
    </main>
  </body>
</html>
"""
SAFE_SCRIPT = "() => { document.querySelector('#status').textContent = 'Sandboxed'; return document.body.innerText; }"


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_js_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser JS sandbox mission",
        mission_objective="Run one bounded page-side JS snippet.",
        success_criteria=["JS sandbox receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live", "browser_js_sandbox_special_authority_l6"],
        allowed_actions=["browser_session_open", "browser_session_close", "browser_js_sandbox_special_authority"],
        forbidden_actions=["payment_execution"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _open_session(tmp_path: Path):
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"], max_steps=5)
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


def _contract():
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import BrowserJSSandboxContract

    return BrowserJSSandboxContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allow_js_sandbox=True,
        max_script_bytes=2_000,
    )


def test_l6_js_sandbox_executes_bounded_dom_script_with_hashes(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import (
        BrowserJSSandboxOrganL6,
        BrowserJSSandboxRequest,
        BrowserJSSandboxStatus,
    )

    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserJSSandboxOrganL6().execute(
            BrowserJSSandboxRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_contract(),
                script=SAFE_SCRIPT,
                intent_summary="Update page status and return visible text.",
            ),
            session_manager=manager,
        )

        assert result.accepted is True
        assert result.status == BrowserJSSandboxStatus.EXECUTED
        assert result.receipt.script_hash
        assert result.receipt.result_hash
        assert result.receipt.before_snapshot_hash
        assert result.receipt.after_snapshot_hash
        assert result.execution_effect == "browser_js_sandbox_executed"
    finally:
        manager.close_all()


def test_l6_js_sandbox_does_not_persist_raw_script_or_result(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import BrowserJSSandboxOrganL6, BrowserJSSandboxRequest

    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserJSSandboxOrganL6().execute(
            BrowserJSSandboxRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_contract(),
                script=SAFE_SCRIPT,
                intent_summary="Update page status and return visible text.",
            ),
            session_manager=manager,
        )

        dumped = result.model_dump_json()
        assert SAFE_SCRIPT not in dumped
        assert "Sandboxed" not in dumped
    finally:
        manager.close_all()


def test_l6_js_sandbox_blocks_network_storage_cookie_submit_and_credentials(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import BrowserJSSandboxOrganL6, BrowserJSSandboxRequest

    bad_scripts = [
        "() => fetch('/x')",
        "() => document.cookie",
        "() => localStorage.setItem('x','y')",
        "() => document.querySelector('form').submit()",
        "() => ({ api_key: 'x' })",
    ]
    manager, session_id = _open_session(tmp_path)
    try:
        for script in bad_scripts:
            result = BrowserJSSandboxOrganL6().execute(
                BrowserJSSandboxRequest(
                    mission=_mission(),
                    url=URL,
                    session_id=session_id,
                    contract=_contract(),
                    script=script,
                    intent_summary="unsafe",
                ),
                session_manager=manager,
            )

            assert result.accepted is False
            assert "unsafe_browser_js_sandbox_payload" in result.reason or "forbidden_js_surface" in result.reason
            assert result.execution_effect == "none"
    finally:
        manager.close_all()


def test_l6_js_sandbox_blocks_obfuscated_network_and_constructor_bypass(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import BrowserJSSandboxOrganL6, BrowserJSSandboxRequest

    bad_scripts = [
        "() => globalThis['fetch']('/x')",
        "() => window[`fetch`]('/x')",
        "() => this['XMLHttpRequest']",
        "() => document['cookie']",
        "() => globalThis['localStorage'].getItem('x')",
        "() => ({}).constructor.constructor('return 7')()",
    ]
    manager, session_id = _open_session(tmp_path)
    try:
        for script in bad_scripts:
            result = BrowserJSSandboxOrganL6().execute(
                BrowserJSSandboxRequest(
                    mission=_mission(),
                    url=URL,
                    session_id=session_id,
                    contract=_contract(),
                    script=script,
                    intent_summary="bounded inspection",
                ),
                session_manager=manager,
            )

            assert result.accepted is False
            assert result.reason == "forbidden_js_surface"
            assert result.execution_effect == "none"
    finally:
        manager.close_all()


def test_l6_js_sandbox_requires_special_authority(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_js_sandbox_special_authority_l6 import BrowserJSSandboxOrganL6, BrowserJSSandboxRequest

    mission = _mission().model_copy(update={"allowed_actions": ["browser_session_open", "browser_session_close"]})
    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserJSSandboxOrganL6().execute(
            BrowserJSSandboxRequest(
                mission=mission,
                url=URL,
                session_id=session_id,
                contract=_contract(),
                script=SAFE_SCRIPT,
                intent_summary="Update page status.",
            ),
            session_manager=manager,
        )

        assert result.accepted is False
        assert "mission_authority_missing_browser_js_sandbox_special_authority" in result.reason
        assert result.execution_effect == "none"
    finally:
        manager.close_all()
