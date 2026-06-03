from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

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


def _open_session(tmp_path: Path, *, html: str = HTML):
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


def _contract(upload_root: Path, quarantine_root: Path, **updates):
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import BrowserFileQuarantineContract

    payload = {
        "mission_id": MISSION_ID,
        "allowed_domains": ["example.com"],
        "approved_upload_root": str(upload_root),
        "approved_download_quarantine_root": str(quarantine_root),
        "allow_upload": True,
        "allow_download": True,
    }
    payload.update(updates)
    return BrowserFileQuarantineContract(**payload)


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


def test_l6_download_blocks_executable_extension_and_removes_artifact(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
    )

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    html = HTML.replace('download="report.txt"', 'download="payload.exe"')
    manager, session_id = _open_session(tmp_path, html=html)
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

        assert result.accepted is False
        assert result.execution_effect == "none"
        assert not (quarantine_root / "payload.exe").exists()
    finally:
        manager.close_all()


def test_l6_download_blocks_size_overflow_and_removes_temp_artifact(tmp_path: Path) -> None:
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
                contract=_contract(upload_root, quarantine_root, max_file_bytes=1),
                action_kind=BrowserFileQuarantineActionKind.DOWNLOAD,
                target_role="link",
                target_name="Download report",
            ),
            session_manager=manager,
        )

        assert result.accepted is False
        assert result.execution_effect == "none"
        assert not (quarantine_root / "report.txt").exists()
        assert list(quarantine_root.glob("*.part")) == []
    finally:
        manager.close_all()


def test_l6_download_save_as_failure_removes_temp_artifact(tmp_path: Path, monkeypatch: Any) -> None:
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionManagerL5Live,
        _LiveBrowserSession,
    )

    class FailingDownload:
        suggested_filename = "report.txt"

        def save_as(self, path: str) -> None:
            Path(path).write_text("partial", encoding="utf-8")
            raise RuntimeError("save_as_failed")

    class DownloadContext:
        value = FailingDownload()

        def __enter__(self) -> "DownloadContext":
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    class FakeLocator:
        def click(self, timeout: int) -> None:
            return None

    class FakePage:
        url = URL

        def expect_download(self, timeout: int) -> DownloadContext:
            return DownloadContext()

    class FakeEngineSession:
        backend_kind = "fake-download-backend"
        profile_dir = tmp_path / "profile"
        page = FakePage()

        def close(self) -> None:
            return None

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    manager = BrowserSessionManagerL5Live(capture_root=tmp_path / "browser", engine="playwright", backend=object())
    session = _LiveBrowserSession(
        session_id="session_download_failure",
        mission_id=MISSION_ID,
        url=URL,
        engine_session=FakeEngineSession(),
    )
    manager._sessions[session.session_id] = session
    monkeypatch.setattr(manager, "_snapshot", lambda page, timeout_ms: SimpleNamespace(snapshot_sha256="snapshot_hash"))
    monkeypatch.setattr(
        manager,
        "_write_screenshot",
        lambda session, label, capture_screenshot, timeout_ms: {"artifact_id": f"{label}_artifact", "path": None},
    )
    monkeypatch.setattr(manager, "_role_locator", lambda page, target_role, target_name, target_nth: FakeLocator())

    with pytest.raises(RuntimeError, match="save_as_failed"):
        manager.download_file_quarantine_special_authority(
            mission_id=MISSION_ID,
            session_id=session.session_id,
            target_role="link",
            target_name="Download report",
            quarantine_root=quarantine_root,
        )

    assert not (quarantine_root / "report.txt").exists()
    assert list(quarantine_root.glob("*.part")) == []


def test_l6_download_does_not_overwrite_existing_quarantine_file(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
    )

    upload_root = tmp_path / "uploads"
    quarantine_root = tmp_path / "downloads"
    upload_root.mkdir()
    quarantine_root.mkdir()
    existing = quarantine_root / "report.txt"
    existing.write_text("existing", encoding="utf-8")
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

        assert result.accepted is False
        assert result.execution_effect == "none"
        assert existing.read_text(encoding="utf-8") == "existing"
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
