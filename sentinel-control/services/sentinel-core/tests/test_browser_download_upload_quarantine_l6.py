from __future__ import annotations

from pathlib import Path

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_quarantine_l6"
URL = "https://example.com/files"
HTML = """
<html>
  <body>
    <main>
      <h1>File Console</h1>
      <input type="file" aria-label="Upload file" />
      <a href="data:text/plain,downloaded-report" download="report.txt">Download report</a>
    </main>
  </body>
</html>
"""


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_file_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser file quarantine mission",
        mission_objective="Upload and download only through quarantine roots.",
        success_criteria=["File quarantine receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_session_l5_live", "browser_download_upload_quarantine_l6"],
        allowed_actions=["browser_session_open", "browser_session_close", "browser_file_upload_quarantine", "browser_file_download_quarantine"],
        forbidden_actions=["payment_execution", "browser_js_evaluate_sandboxed"],
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
        accept_downloads=True,
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


def _contract(upload_root: Path, quarantine_root: Path):
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import BrowserFileQuarantineContract

    return BrowserFileQuarantineContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        approved_upload_root=str(upload_root),
        approved_download_quarantine_root=str(quarantine_root),
        allow_upload=True,
        allow_download=True,
    )


def test_l6_uploads_only_from_approved_root_with_file_hash(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
        BrowserFileQuarantineStatus,
    )

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    upload_file = upload_root / "payload.txt"
    upload_file.write_text("safe upload content", encoding="utf-8")
    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserFileQuarantineOrganL6().execute(
            BrowserFileQuarantineRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_contract(upload_root, quarantine_root),
                action_kind=BrowserFileQuarantineActionKind.UPLOAD,
                target_role="button",
                target_name="Upload file",
                local_upload_path=str(upload_file),
            ),
            session_manager=manager,
        )

        assert result.accepted is True
        assert result.status == BrowserFileQuarantineStatus.COMPLETED
        assert result.receipt.file_hash
        assert result.receipt.before_snapshot_hash
        assert result.receipt.after_snapshot_hash
        assert result.receipt.finalgate_verified is True
    finally:
        manager.close_all()


def test_l6_blocks_upload_outside_approved_root(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
    )

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")
    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserFileQuarantineOrganL6().execute(
            BrowserFileQuarantineRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_contract(upload_root, quarantine_root),
                action_kind=BrowserFileQuarantineActionKind.UPLOAD,
                target_role="button",
                target_name="Upload file",
                local_upload_path=str(outside_file),
            ),
            session_manager=manager,
        )

        assert result.accepted is False
        assert "upload_path_outside_approved_root" in result.reason
        assert result.execution_effect == "none"
    finally:
        manager.close_all()


def test_l6_downloads_only_to_quarantine_with_hash(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
    )

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserFileQuarantineOrganL6().execute(
            BrowserFileQuarantineRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_contract(upload_root, quarantine_root),
                action_kind=BrowserFileQuarantineActionKind.DOWNLOAD,
                target_role="link",
                target_name="Download report",
            ),
            session_manager=manager,
        )

        assert result.accepted is True
        assert result.receipt.quarantine_path_metadata
        assert result.receipt.file_hash
        assert (quarantine_root / "report.txt").exists()
        assert "downloaded-report" not in result.model_dump_json()
    finally:
        manager.close_all()


def test_l6_file_quarantine_blocks_provider_override_and_raw_secret_paths(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
    )

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    manager, session_id = _open_session(tmp_path)
    try:
        result = BrowserFileQuarantineOrganL6().execute(
            BrowserFileQuarantineRequest(
                mission=_mission(),
                url=URL,
                session_id=session_id,
                contract=_contract(upload_root, quarantine_root),
                action_kind=BrowserFileQuarantineActionKind.DOWNLOAD,
                target_role="link",
                target_name="Download report",
                operator_note="provider_override and api_key should be blocked",
            ),
            session_manager=manager,
        )

        assert result.accepted is False
        assert "unsafe_browser_file_quarantine_payload" in result.reason
        assert result.execution_effect == "none"
    finally:
        manager.close_all()
