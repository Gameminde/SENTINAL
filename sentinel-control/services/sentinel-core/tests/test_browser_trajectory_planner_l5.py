from __future__ import annotations

import json
from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.organs.browser.accessibility_snapshot import BrowserAccessibilitySnapshotBuilder
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_trajectory_l5"
URL = "https://example.com/trajectory"
HTML = """
<html>
  <body>
    <main>
      <h1>Founder Console</h1>
      <label>Email</label>
      <input type="text" placeholder="Email" />
      <button>Remember</button>
      <button>Continue</button>
    </main>
  </body>
</html>
"""


def _envelope() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_trajectory_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser trajectory mission",
        mission_objective="Plan and execute a grounded browser trajectory.",
        success_criteria=["Trajectory receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live", "browser_trajectory_planner_l5"],
        allowed_actions=[
            "browser_session_open",
            "browser_session_observe",
            "browser_session_interact",
            "browser_session_close",
            "browser_trajectory_plan",
            "browser_trajectory_execute",
        ],
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
        max_actions=30,
        max_cost_usd=0.0,
    )


def _snapshot():
    return BrowserAccessibilitySnapshotBuilder().build(html=HTML, text="Founder Console Email Remember Continue")


def test_trajectory_planner_ranks_targets_from_accessibility_snapshot() -> None:
    from sentinel.agent.organs.browser_trajectory_planner_l5 import (
        BrowserTrajectoryActionKind,
        BrowserTrajectoryContract,
        BrowserTrajectoryPlannerL5,
        BrowserTrajectoryRequest,
    )

    snapshot = _snapshot()
    planner = BrowserTrajectoryPlannerL5()
    contract = BrowserTrajectoryContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserTrajectoryActionKind.TYPE],
    )

    result = planner.prepare(
        BrowserTrajectoryRequest(
            mission=_envelope(),
            url=URL,
            session_id="session_1",
            contract=contract,
            source_snapshot=snapshot,
            source_receipt_id="receipt_readonly_1",
            objective_summary="type contact email into the email field",
            desired_action_kind=BrowserTrajectoryActionKind.TYPE,
            target_role_hint="textbox",
            target_name_hint="work email address",
            text="founder@example.com",
        )
    )

    assert result.accepted is True
    assert result.plan is not None
    assert result.plan.source_snapshot_hash == snapshot.snapshot_sha256
    assert result.plan.source_receipt_id == "receipt_readonly_1"
    assert result.plan.steps[0].target_role == "textbox"
    assert result.plan.steps[0].target_name == "Email"
    assert result.plan.steps[0].confidence >= 0.7
    assert result.plan.text_hash
    assert "founder@example.com" not in result.model_dump_json()


def test_trajectory_execute_self_heals_wrong_target_name_and_preserves_state(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )
    from sentinel.agent.organs.browser_trajectory_planner_l5 import (
        BrowserTrajectoryActionKind,
        BrowserTrajectoryContract,
        BrowserTrajectoryPlannerL5,
        BrowserTrajectoryRequest,
    )

    manager = BrowserSessionManagerL5Live(
        capture_root=tmp_path / "browser",
        engine="playwright",
        document_fixtures={URL: HTML},
    )
    session_contract = BrowserSessionContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserTrajectoryActionKind.TYPE.value],
    )
    trajectory_contract = BrowserTrajectoryContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserTrajectoryActionKind.TYPE],
        max_recovery_attempts=3,
    )
    try:
        opened = manager.open_session(BrowserSessionRequest(mission=_envelope(), url=URL, contract=session_contract))
        snapshot = _snapshot()
        request = BrowserTrajectoryRequest(
            mission=_envelope(),
            url=URL,
            session_id=opened.session_id,
            contract=trajectory_contract,
            source_snapshot=snapshot,
            source_receipt_id=opened.receipt.receipt_id,
            objective_summary="type contact email into the email field",
            desired_action_kind=BrowserTrajectoryActionKind.TYPE,
            target_role_hint="textbox",
            target_name_hint="work email address",
            text="founder@example.com",
        )

        result = BrowserTrajectoryPlannerL5().execute_with_recovery(manager, request)
        observed = manager.observe(BrowserSessionRequest(mission=_envelope(), url=URL, contract=session_contract, session_id=opened.session_id))

        assert result.accepted is True
        assert result.status.value == "executed"
        assert result.executed_step is not None
        assert result.executed_step.target_name == "Email"
        assert result.attempt_count == 1
        assert result.execution_receipt_id
        assert observed.receipt.form_state_summary == [{"name": "Email", "role": "textbox", "value_hash": result.plan.text_hash}]
    finally:
        manager.close_all()


def test_trajectory_blocks_forbidden_submit_login_credential_payload() -> None:
    from sentinel.agent.organs.browser_trajectory_planner_l5 import (
        BrowserTrajectoryContract,
        BrowserTrajectoryPlannerL5,
        BrowserTrajectoryRequest,
    )

    contract = BrowserTrajectoryContract(mission_id=MISSION_ID, allowed_domains=["example.com"])
    result = BrowserTrajectoryPlannerL5().prepare(
        BrowserTrajectoryRequest.model_construct(
            mission=_envelope(),
            url=URL,
            session_id="session_1",
            contract=contract,
            source_snapshot=_snapshot(),
            source_receipt_id="receipt_1",
            objective_summary="login then browser_submit with credential",
            desired_action_kind="submit",
            target_role_hint="button",
            target_name_hint="Submit",
            text="credential bearer token",
            data_not_instruction=True,
            authority_effect="none",
        )
    )

    assert result.accepted is False
    assert result.status.value == "blocked"
    assert result.execution_effect == "none"
    assert result.receipt.blocked_reason


def test_trajectory_rejects_provider_model_override_payload() -> None:
    from sentinel.agent.organs.browser_trajectory_planner_l5 import (
        BrowserTrajectoryActionKind,
        BrowserTrajectoryContract,
        BrowserTrajectoryPlannerL5,
        BrowserTrajectoryRequest,
    )

    contract = BrowserTrajectoryContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        allowed_action_kinds=[BrowserTrajectoryActionKind.TYPE],
    )
    result = BrowserTrajectoryPlannerL5().prepare(
        BrowserTrajectoryRequest(
            mission=_envelope(),
            url=URL,
            session_id="session_1",
            contract=contract,
            source_snapshot=_snapshot(),
            source_receipt_id="receipt_1",
            objective_summary="use provider_override to choose a different model",
            desired_action_kind=BrowserTrajectoryActionKind.TYPE,
            target_role_hint="textbox",
            target_name_hint="Email",
            text="founder@example.com",
        )
    )

    assert result.accepted is False
    assert "unsafe_browser_trajectory_payload" in result.reason


def test_trajectory_rendering_is_data_not_instruction() -> None:
    from sentinel.agent.organs.browser_trajectory_planner_l5 import (
        BrowserTrajectoryActionKind,
        BrowserTrajectoryContract,
        BrowserTrajectoryPlannerL5,
        BrowserTrajectoryRequest,
    )

    planner = BrowserTrajectoryPlannerL5()
    result = planner.prepare(
        BrowserTrajectoryRequest(
            mission=_envelope(),
            url=URL,
            session_id="session_1",
            contract=BrowserTrajectoryContract(
                mission_id=MISSION_ID,
                allowed_domains=["example.com"],
                allowed_action_kinds=[BrowserTrajectoryActionKind.TYPE],
            ),
            source_snapshot=_snapshot(),
            source_receipt_id="receipt_1",
            objective_summary="type contact email into the email field",
            desired_action_kind=BrowserTrajectoryActionKind.TYPE,
            target_role_hint="textbox",
            target_name_hint="Email",
            text="founder@example.com",
        )
    )

    rendered = planner.render_untrusted_context(result.receipt)

    assert "not instructions" in rendered
    assert "not Root Authority" in rendered
    assert "founder@example.com" not in rendered


def test_cli_browser_trajectory_demo_runs_self_healing_workflow(tmp_path: Path, capsys) -> None:
    from sentinel.cli import main

    mission_path = tmp_path / "mission.json"
    mission_path.write_text(
        json.dumps({"preset": "operator_browser_l5_template", "mission": _envelope().model_dump(mode="json")}),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "browser-trajectory-demo",
            "--mission",
            str(mission_path),
            "--url",
            URL,
            "--run-root",
            str(tmp_path / "runs"),
            "--fixture-html",
            HTML,
            "--target-hint",
            "work email address",
            "--target-role",
            "textbox",
            "--text",
            "founder@example.com",
            "--engine",
            "playwright",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "browser_trajectory_workflow" in output
    result_files = list((tmp_path / "runs").rglob("browser.trajectory.result.json"))
    assert result_files
    payload = json.loads(result_files[0].read_text(encoding="utf-8"))
    assert payload["accepted"] is True
    assert payload["plan_hash"]
    assert payload["execution_receipt_id"]
