from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_session_live"
URL = "https://example.com/session"
HTML = """
<html>
  <head><title>Session Browser</title></head>
  <body>
    <main>
      <h1>Operator Console</h1>
      <input type="text" placeholder="Email" />
      <button>Remember</button>
    </main>
  </body>
</html>
"""


def _envelope() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_session_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Live browser session mission",
        mission_objective="Operate one governed public browser session.",
        success_criteria=["Session receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live"],
        allowed_actions=["browser_session_open", "browser_session_observe", "browser_session_interact", "browser_session_close"],
        forbidden_actions=[
            "browser_submit_form",
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


def test_live_browser_session_persists_form_state_across_steps(tmp_path: Path) -> None:
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
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.TYPE, BrowserSessionActionKind.CLICK],
        max_steps=5,
    )

    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))
        typed = manager.interact(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role="textbox",
                target_name="Email",
                text="founder@example.com",
            )
        )
        observed = manager.observe(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
            )
        )
        closed = manager.close_session(
            BrowserSessionRequest(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
            )
        )
        assert opened.accepted is True
        assert typed.accepted is True
        assert observed.accepted is True
        assert closed.accepted is True
        assert typed.receipt.before_snapshot_hash
        assert typed.receipt.after_snapshot_hash
        assert typed.finalgate_certificate is not None
        assert typed.receipt.finalgate_certificate_id == typed.finalgate_certificate.certificate_id
        assert typed.receipt.finalgate_verified is True
        assert typed.receipt.session_id == opened.session_id
        assert observed.receipt.form_state_summary_hash == typed.receipt.form_state_summary_hash
        assert observed.receipt.form_state_summary == [{"name": "Email", "role": "textbox", "value_hash": typed.receipt.typed_text_hash}]
        assert closed.receipt.closed is True
        assert list((tmp_path / "browser").rglob("*_screenshot.png"))
    finally:
        manager.close_all()


def test_cloakbrowser_backend_is_primary_and_uses_persistent_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sentinel.organs.browser.cloak_backend import CloakBrowserSessionBackend

    calls: list[dict[str, object]] = []

    class _FakeResponse:
        status = 200

    class _FakePage:
        def route(self, *_args: object, **_kwargs: object) -> None:
            return None

        def goto(self, url: str, **kwargs: object) -> _FakeResponse:
            calls.append({"url": url, **kwargs})
            return _FakeResponse()

    class _FakeContext:
        def new_page(self) -> _FakePage:
            return _FakePage()

        def close(self) -> None:
            calls.append({"closed": True})

    def _launch_persistent_context(user_data_dir: str, **kwargs: object) -> _FakeContext:
        calls.append({"user_data_dir": user_data_dir, **kwargs})
        return _FakeContext()

    monkeypatch.setitem(
        sys.modules,
        "cloakbrowser",
        types.SimpleNamespace(launch_persistent_context=_launch_persistent_context),
    )

    backend = CloakBrowserSessionBackend(headless=True, humanize=True, stealth_args=True)
    session = backend.open_context(
        profile_dir=tmp_path / "profile",
        url=URL,
        timeout_ms=5_000,
        viewport_width=1440,
        viewport_height=1000,
    )

    assert session.backend_kind == "cloakbrowser"
    assert calls[0]["user_data_dir"] == str(tmp_path / "profile")
    assert calls[0]["humanize"] is True
    assert calls[0]["stealth_args"] is True
    assert calls[0]["accept_downloads"] is False
    assert calls[0]["viewport"] == {"width": 1440, "height": 1000}
    session.close()
    assert calls[-1] == {"closed": True}


def test_default_engine_is_cloak_and_never_silently_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    monkeypatch.setitem(sys.modules, "cloakbrowser", None)
    manager = BrowserSessionManagerL5Live(capture_root=tmp_path / "browser", document_fixtures={URL: HTML})
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])

    result = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))

    assert result.accepted is False
    assert result.receipt.backend_kind == "cloakbrowser"
    assert result.reason.startswith("cloakbrowser_not_installed")


def test_live_browser_session_blocks_non_promoted_dangerous_actions(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(mission_id=MISSION_ID, allowed_domains=["example.com"])
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))

        result = manager.interact(
            BrowserSessionRequest.model_construct(
                mission=_envelope(),
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind="submit",
                data_not_instruction=True,
                authority_effect="none",
            )
        )

        assert result.accepted is False
        assert "not_promoted" in result.reason
        assert result.execution_effect == "none"
        assert result.finalgate_certificate is not None
        assert result.receipt.finalgate_verified is True
    finally:
        manager.close_all()


def test_live_browser_session_requires_mission_authority(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    mission = _envelope().model_copy(update={"allowed_actions": ["browser_session_open"]})
    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserSessionActionKind.TYPE],
    )
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=contract))

        result = manager.interact(
            BrowserSessionRequest(
                mission=mission,
                url=URL,
                contract=contract,
                session_id=opened.session_id,
                action_kind=BrowserSessionActionKind.TYPE,
                target_role="textbox",
                target_name="Email",
                text="founder@example.com",
            )
        )

        assert result.accepted is False
        assert result.reason == "mission_authority_missing_browser_session_interact"
    finally:
        manager.close_all()


def test_cli_browser_session_demo_runs_multi_step_workflow(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from sentinel.cli import main

    mission_path = tmp_path / "mission.json"
    mission_path.write_text(
        json.dumps({"preset": "operator_browser_l5_template", "mission": _envelope().model_dump(mode="json")}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "browser-session-demo",
            "--mission",
            str(mission_path),
            "--url",
            URL,
            "--run-root",
            str(tmp_path / "runs"),
            "--fixture-html",
            HTML,
            "--target-role",
            "textbox",
            "--target-name",
            "Email",
            "--text",
            "founder@example.com",
            "--engine",
            "playwright",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "browser_session_workflow" in output
    assert list((tmp_path / "runs").rglob("browser.session.result.json"))
    assert list((tmp_path / "runs").rglob("*_screenshot.png"))
