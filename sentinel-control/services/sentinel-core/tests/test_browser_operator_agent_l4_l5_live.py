from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_operator_live"
URL = "https://example.com/form"
HTML = """
<html>
  <head><title>Live Browser Operator</title></head>
  <body>
    <main>
      <h1>Build faster</h1>
      <input type="text" placeholder="Email" />
      <button>Continue</button>
    </main>
  </body>
</html>
"""


class FakeResolver:
    def __call__(self, host: str) -> list[str]:
        return ["93.184.216.34"] if host == "example.com" else []


def _envelope(*, l5: bool = False) -> MissionAuthorityEnvelope:
    tools = ["browser_readonly_public"]
    actions = ["browser_render_public_page"]
    if l5:
        tools.append("browser_public_operator_limited")
        actions.append("browser_interaction_limited")
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Live browser operator mission",
        mission_objective="Observe and operate an allowed public page.",
        success_criteria=["Browser receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web", "local_workspace"],
        allowed_tools=tools,
        allowed_actions=actions,
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
        max_actions=10,
        max_cost_usd=0.0,
    )


def _operator(tmp_path: Path):
    from sentinel.agent.organs.browser_operator_agent_l4_l5_live import BrowserOperatorAgentL4L5Live
    from sentinel.organs.browser.playwright_interaction_backend import PlaywrightLimitedInteractionBackend
    from sentinel.organs.browser.playwright_renderer import PlaywrightReadOnlyRenderer

    return BrowserOperatorAgentL4L5Live(
        capture_root=tmp_path / "browser",
        renderer=PlaywrightReadOnlyRenderer(document_fixtures={URL: HTML}),
        interaction_backend=PlaywrightLimitedInteractionBackend(document_fixtures={URL: HTML}),
        resolver=FakeResolver(),
    )


def test_live_l4_observe_uses_playwright_and_writes_evidence(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
        BrowserOperatorLiveActionKind,
        BrowserOperatorLiveContract,
        BrowserOperatorLiveRequest,
    )

    operator = _operator(tmp_path)
    result = operator.observe(
        BrowserOperatorLiveRequest(
            mission=_envelope(),
            action_kind=BrowserOperatorLiveActionKind.OBSERVE,
            url=URL,
            contract=BrowserOperatorLiveContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
            ),
        )
    )

    assert result.accepted is True
    assert result.action_level == "L4"
    assert result.receipt is not None
    assert result.receipt.screenshot_artifact_id
    assert result.receipt.before_snapshot_hash
    assert result.receipt.finalgate_verified is True
    assert result.receipt.execution_effect == "browser_public_observation"
    assert result.receipt.authority_effect == "none"
    assert list((tmp_path / "browser").rglob("*_screenshot.png"))


def test_live_l5_type_executes_from_hash_bound_observation(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
        BrowserOperatorLiveActionKind,
        BrowserOperatorLiveContract,
        BrowserOperatorLiveRequest,
    )

    operator = _operator(tmp_path)
    result = operator.execute(
        BrowserOperatorLiveRequest(
            mission=_envelope(l5=True),
            action_kind=BrowserOperatorLiveActionKind.TYPE,
            url=URL,
            target_role="textbox",
            target_name="Email",
            text="contact@example.com",
            contract=BrowserOperatorLiveContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allow_l5_interaction=True,
                allowed_action_kinds=[BrowserOperatorLiveActionKind.TYPE],
            ),
        )
    )

    assert result.accepted is True
    assert result.action_level == "L5"
    assert result.receipt is not None
    assert result.receipt.before_snapshot_hash
    assert result.receipt.after_snapshot_hash
    assert result.receipt.plan_hash
    assert result.receipt.executed_action_kinds == ["type"]
    assert result.receipt.finalgate_verified is True
    assert result.receipt.execution_effect == "browser_limited_interaction"
    assert list((tmp_path / "browser").rglob("*_after_screenshot.png"))


def test_live_l5_click_executes_from_hash_bound_observation(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
        BrowserOperatorLiveActionKind,
        BrowserOperatorLiveContract,
        BrowserOperatorLiveRequest,
    )

    operator = _operator(tmp_path)
    result = operator.execute(
        BrowserOperatorLiveRequest(
            mission=_envelope(l5=True),
            action_kind=BrowserOperatorLiveActionKind.CLICK,
            url=URL,
            target_role="button",
            target_name="Continue",
            contract=BrowserOperatorLiveContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allow_l5_interaction=True,
                allowed_action_kinds=[BrowserOperatorLiveActionKind.CLICK],
            ),
        )
    )

    assert result.accepted is True
    assert result.action_level == "L5"
    assert result.receipt is not None
    assert result.receipt.before_snapshot_hash
    assert result.receipt.after_snapshot_hash
    assert result.receipt.plan_hash
    assert result.receipt.executed_action_kinds == ["click"]
    assert result.receipt.finalgate_verified is True
    assert result.receipt.execution_effect == "browser_limited_interaction"


@pytest.mark.parametrize(
    "dangerous_action",
    ["submit", "login", "upload", "download", "javascript", "credential"],
)
def test_live_operator_blocks_non_promoted_dangerous_actions(
    tmp_path: Path, dangerous_action: str
) -> None:
    from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
        BrowserOperatorAgentL4L5Live,
        BrowserOperatorLiveContract,
        BrowserOperatorLiveRequest,
    )

    operator = BrowserOperatorAgentL4L5Live(capture_root=tmp_path / "browser", resolver=FakeResolver())

    result = operator.execute(
        BrowserOperatorLiveRequest.model_construct(
            mission=_envelope(l5=True),
            action_kind=dangerous_action,
            url=URL,
            contract=BrowserOperatorLiveContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allow_l5_interaction=True,
            ),
            data_not_instruction=True,
            authority_effect="none",
        )
    )

    assert result.accepted is False
    assert "not_promoted" in result.reason
    assert result.execution_effect == "none"


def test_live_l5_requires_explicit_mission_authority_and_contract(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_operator_agent_l4_l5_live import (
        BrowserOperatorLiveActionKind,
        BrowserOperatorLiveContract,
        BrowserOperatorLiveRequest,
    )

    result = _operator(tmp_path).execute(
        BrowserOperatorLiveRequest(
            mission=_envelope(l5=False),
            action_kind=BrowserOperatorLiveActionKind.CLICK,
            url=URL,
            target_role="button",
            target_name="Continue",
            contract=BrowserOperatorLiveContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allow_l5_interaction=True,
                allowed_action_kinds=[BrowserOperatorLiveActionKind.CLICK],
            ),
        )
    )

    assert result.accepted is False
    assert result.reason == "mission_authority_missing_l5_browser_permission"
    assert result.execution_effect == "none"


def test_cli_browser_observe_runs_existing_browser_engine(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from sentinel.cli import main

    mission_path = tmp_path / "mission.json"
    mission_path.write_text(
        json.dumps({"preset": "browser_perception", "mission": _envelope().model_dump(mode="json")}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "browser-observe",
            "--mission",
            str(mission_path),
            "--url",
            URL,
            "--run-root",
            str(tmp_path / "runs"),
            "--fixture-html",
            HTML,
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "browser_public_observation" in output
    assert list((tmp_path / "runs").rglob("*_screenshot.png"))


def test_cli_browser_act_type_runs_existing_limited_interaction_engine(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from sentinel.cli import main

    mission_path = tmp_path / "mission.json"
    mission_path.write_text(
        json.dumps({"preset": "operator_browser_l5_template", "mission": _envelope(l5=True).model_dump(mode="json")}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "browser-act",
            "--mission",
            str(mission_path),
            "--url",
            URL,
            "--run-root",
            str(tmp_path / "runs"),
            "--fixture-html",
            HTML,
            "--action",
            "type",
            "--target-role",
            "textbox",
            "--target-name",
            "Email",
            "--text",
            "contact@example.com",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "browser_limited_interaction" in output
    assert list((tmp_path / "runs").rglob("*_after_screenshot.png"))
