from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.agent.organs.delegated_action_gate import (
    DelegatedActionAuthorityClass,
    DelegatedActionLane,
    DelegatedActionReceiptRequirement,
    DelegatedActionRiskClass,
)
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.reversible_workspace_executor import (
    L3ExecutorContract,
    L3ReversibleWorkspaceExecutor,
    L3WorkspaceActionKind,
    L3WorkspaceAttemptStatus,
    L3WorkspaceRequest,
)
from sentinel.agent.organs.sandbox_shell_code_organ_v1 import (
    ShellCodeSandboxOrganV1,
    ShellCodeSandboxRequest,
    ShellCodeSandboxStatus,
)
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.models import MissionDraft, OperatorMissionStatus
from sentinel.operator.replay import MissionReplayBuilder
from sentinel.shared.enums import MissionMode, MissionType


NOW = datetime(2026, 6, 14, 8, 0, tzinfo=UTC)
BROWSER_URL = "https://example.com/wave1"
RESEARCH_URL = "https://example.com/research"
FILES_URL = "https://example.com/files"
LOGIN_URL = "https://example.com/login"

MAIN_HTML = """
<html>
  <body>
    <main>
      <h1>Wave One Console</h1>
      <form aria-label="Interest form"
            onsubmit="document.querySelector('#status').textContent='Submitted'; return false">
        <input type="text" aria-label="Project name" />
        <button type="submit">Submit request</button>
      </form>
      <p id="status">Waiting</p>
      <div id="target-zone"><button>Old target</button></div>
      <button onclick="document.querySelector('#target-zone').innerHTML='<button>New target</button>'">
        Move target
      </button>
    </main>
  </body>
</html>
"""
RESEARCH_HTML = """
<html><body><main><h1>Research Evidence</h1><p>Controlled finding: 42</p></main></body></html>
"""
FILES_HTML = """
<html>
  <body>
    <main>
      <h1>Controlled Files</h1>
      <input type="file" aria-label="Upload file" />
      <a href="data:text/plain,wave-one-download" download="wave-one.txt">Download result</a>
    </main>
  </body>
</html>
"""
LOGIN_HTML = """
<html><body><main><h1>Login checkpoint</h1><input type="password" aria-label="Password" /></main></body></html>
"""


def _workspace_contract(root: Path, mission_id: str) -> L3ExecutorContract:
    return L3ExecutorContract(
        mission_id=mission_id,
        lane_id=f"lane:{mission_id}",
        gate_result_id=f"gate:{mission_id}",
        allowed_workspace_root=str(root.parent),
        allowed_workspace_subdir=root.name,
        max_file_bytes=16_384,
        max_patch_bytes=8_192,
        allow_overwrite=True,
        allow_delete=False,
        tombstone_required_for_delete=True,
        rollback_required=True,
        rollback_must_be_tested_before_mutation=True,
        receipt_required=True,
        finalgate_posture_required=True,
        execution_enabled_for_l3=True,
        contract_version="wave1-reversible-workspace",
    )


def _workspace_lane(mission_id: str) -> DelegatedActionLane:
    return DelegatedActionLane(
        lane_id=f"lane:{mission_id}",
        mission_id=mission_id,
        source_candidate_id=f"candidate:{mission_id}",
        organ_kind=OrganProposalKind.FILE_OPERATION,
        action_level=DelegatedActionLevel.L3,
        allowed_substeps=["replace_text_file"],
        forbidden_substeps=["send", "network", "api", "shell", "browser_submit"],
        authority_class=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        risk_class=DelegatedActionRiskClass.MEDIUM,
        budget_limit={"remaining_action_count": 12, "remaining_patch_bytes": 8_192},
        credential_scope="none",
        evidence_refs=[f"evidence:{mission_id}"],
        receipt_refs=[f"receipt:gate:{mission_id}"],
        receipt_contract=DelegatedActionReceiptRequirement(
            required_receipt_fields=["before_hash", "after_hash", "path_metadata", "lane_id", "gate_result_id"],
            receipt_refs=[f"receipt:gate:{mission_id}"],
            receipt_contract_hash=f"receipt-contract:{mission_id}",
        ),
        revocation_rule="lane can be revoked before reversible local workspace execution",
        rollback_posture="restore previous text content from before snapshot",
        user_review_requirement="not_required_for_l3_reversible_workspace",
        FinalGate_checks=["local_only", "before_hash", "after_hash", "rollback_ready"],
        created_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        ttl_seconds=3600,
    )


def _workspace_request(
    root: Path,
    mission_id: str,
    relative_path: str,
    content: str,
    before_hash: str,
) -> L3WorkspaceRequest:
    return L3WorkspaceRequest(
        mission_id=mission_id,
        source_candidate_id=f"candidate:{mission_id}",
        action_kind=L3WorkspaceActionKind.REPLACE_TEXT_FILE,
        target_relative_path=relative_path,
        content=content,
        before_hash=before_hash,
        metadata={"title": "Wave 1 controlled repair"},
        contract=_workspace_contract(root, mission_id),
        delegated_lane=_workspace_lane(mission_id),
        budget_estimate={"patch_bytes": len(content.encode("utf-8")), "action_count": 1},
        current_time=NOW,
    )


def _create_coding_fixture(root: Path) -> dict[str, str]:
    files = {
        "src/__init__.py": "",
        "src/pricing.py": "def double(amount: int) -> int:\n    return amount\n",
        "src/report.py": "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"total={double(amount)}\"\n",
        "src/pricing_legacy.py": "def double(amount: int) -> int:\n    return amount * 100\n",
        "tests/test_pricing.py": "from src.report import render\n\n\ndef test_render_total():\n    assert render(7) == \"TOTAL=14\"\n",
        "USER_NOTES.md": "Keep this unrelated user change.\n",
    }
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return files


def _record_result(kernel: MissionKernel, mission_id: str, event_type: str, result: Any) -> None:
    receipt = getattr(result, "receipt", None)
    finalgate = getattr(result, "finalgate_certificate", None)
    kernel.store.append_event(
        mission_id,
        event_type=event_type,
        safe_summary=f"Wave 1 benchmark recorded {event_type}.",
        metadata={"accepted": bool(getattr(result, "accepted", True)), "status": str(getattr(result, "status", ""))},
        receipt_refs=[receipt.receipt_id] if receipt is not None else [],
        finalgate_certificate_refs=[finalgate.certificate_id] if finalgate is not None else [],
    )


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, ceil(len(ordered) * 0.95) - 1)]


def test_wave1_coding_workspace_vertical_gauntlet_repeats_five_times(tmp_path: Path) -> None:
    shell = ShellCodeSandboxOrganV1()
    workspace = L3ReversibleWorkspaceExecutor()
    durations: list[float] = []

    for iteration in range(5):
        started = perf_counter()
        run_root = tmp_path / f"coding_run_{iteration}" / "runs"
        repo_root = tmp_path / f"coding_run_{iteration}" / "repo"
        originals = _create_coding_fixture(repo_root)
        kernel = MissionKernel(run_root=run_root)
        mission = kernel.create_mission(
            session_id=f"wave1-coding-{iteration}",
            draft=MissionDraft(
                title="Repair controlled pricing fixture",
                objective="Inspect, repair, test, resume safely, and prove rollback.",
            ),
        )
        kernel.enqueue(mission.mission_id)

        structure = sorted(path.relative_to(repo_root).as_posix() for path in repo_root.rglob("*") if path.is_file())
        assert "src/pricing.py" in structure
        assert "src/pricing_legacy.py" in structure
        assert "tests/test_pricing.py" in structure

        failing = shell.execute(
            ShellCodeSandboxRequest(
                mission_id=mission.mission_id,
                project_root=repo_root,
                command=["python", "-m", "pytest", "tests/test_pricing.py", "-q"],
            )
        )
        assert failing.status is ShellCodeSandboxStatus.FAILED
        assert failing.receipt is not None and failing.receipt.exit_code != 0
        assert failing.finalgate_certificate is not None and failing.finalgate_certificate.passed
        _record_result(kernel, mission.mission_id, "wave1_coding_induced_test_failure", failing)

        pricing_path = repo_root / "src/pricing.py"
        report_path = repo_root / "src/report.py"
        pricing_result = workspace.execute(
            _workspace_request(
                repo_root,
                mission.mission_id,
                "src/pricing.py",
                "def double(amount: int) -> int:\n    return amount * 2\n",
                text_hash(originals["src/pricing.py"]),
            )
        )
        report_result = workspace.execute(
            _workspace_request(
                repo_root,
                mission.mission_id,
                "src/report.py",
                "from .pricing import double\n\n\ndef render(amount: int) -> str:\n    return f\"TOTAL={double(amount)}\"\n",
                text_hash(originals["src/report.py"]),
            )
        )
        assert pricing_result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
        assert report_result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
        assert pricing_result.before_hash != pricing_result.after_hash
        assert report_result.before_hash != report_result.after_hash
        assert (repo_root / "USER_NOTES.md").read_text(encoding="utf-8") == originals["USER_NOTES.md"]
        _record_result(kernel, mission.mission_id, "wave1_coding_workspace_edit", pricing_result)
        _record_result(kernel, mission.mission_id, "wave1_coding_workspace_edit", report_result)

        stale_resume = workspace.execute(
            _workspace_request(
                repo_root,
                mission.mission_id,
                "src/pricing.py",
                "def double(amount: int) -> int:\n    return amount * 2\n",
                text_hash(originals["src/pricing.py"]),
            )
        )
        assert stale_resume.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
        assert "before_hash_mismatch" in stale_resume.receipt.rejection_reason
        assert pricing_path.read_text(encoding="utf-8") == "def double(amount: int) -> int:\n    return amount * 2\n"
        _record_result(kernel, mission.mission_id, "wave1_coding_resume_duplicate_blocked", stale_resume)

        targeted = shell.execute(
            ShellCodeSandboxRequest(
                mission_id=mission.mission_id,
                project_root=repo_root,
                command=["python", "-m", "pytest", "tests/test_pricing.py", "-q"],
            )
        )
        regression = shell.execute(
            ShellCodeSandboxRequest(
                mission_id=mission.mission_id,
                project_root=repo_root,
                command=["python", "-m", "pytest", "-q"],
            )
        )
        assert targeted.status is ShellCodeSandboxStatus.SUCCEEDED
        assert regression.status is ShellCodeSandboxStatus.SUCCEEDED
        _record_result(kernel, mission.mission_id, "wave1_coding_targeted_test_passed", targeted)
        _record_result(kernel, mission.mission_id, "wave1_coding_regression_passed", regression)

        report_rollback = workspace.rollback(report_result, rollback_reason="Wave 1 rollback proof")
        pricing_rollback = workspace.rollback(pricing_result, rollback_reason="Wave 1 rollback proof")
        assert report_rollback.rollback_success is True
        assert pricing_rollback.rollback_success is True
        assert report_path.read_text(encoding="utf-8") == originals["src/report.py"]
        assert pricing_path.read_text(encoding="utf-8") == originals["src/pricing.py"]
        kernel.store.append_event(
            mission.mission_id,
            event_type="wave1_coding_rollback_completed",
            safe_summary="Wave 1 coding fixture restored to its original content.",
            receipt_refs=[report_rollback.rollback_receipt_id, pricing_rollback.rollback_receipt_id],
        )

        kernel.update_status(mission.mission_id, OperatorMissionStatus.COMPLETED, "Wave 1 coding benchmark completed.")
        replay = MissionReplayBuilder(kernel.store).build(mission.mission_id)
        assert replay.tampered is False
        assert replay.reexecuted_actions is False
        assert replay.receipt_refs
        assert replay.finalgate_certificate_refs
        assert kernel.store.verify_timeline(mission.mission_id)
        assert kernel.telemetry_sink.require_certified_mode().certified_mode is True
        durations.append(perf_counter() - started)

    print(
        "wave1_coding_repeatability "
        f"passes=5 failures=0 median_seconds={median(durations):.3f} p95_seconds={_p95(durations):.3f} "
        "silent_success=0 duplicate_material_side_effects=0 cross_mission_contamination=0"
    )


def _browser_envelope(mission_id: str, *, revoked: bool = False) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="wave1-browser-operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Wave 1 controlled browser task",
        mission_objective="Complete controlled browser tasks with proof and no cross-mission leakage.",
        success_criteria=["Controlled browser task receipts exist"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=[
            "browser_session_l5_live",
            "browser_form_submit_l6_special_authority",
            "browser_download_upload_quarantine_l6",
        ],
        allowed_actions=[
            "browser_session_open",
            "browser_session_observe",
            "browser_session_interact",
            "browser_session_close",
            "browser_form_submit_special_authority",
            "browser_file_upload_quarantine",
            "browser_file_download_quarantine",
        ],
        forbidden_actions=["payment_execution", "account_creation", "captcha_bypass", "credential_access"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=50,
        max_cost_usd=0.0,
        revoked_at=NOW if revoked else None,
    )


def test_wave1_controlled_live_browser_gauntlet_repeats_ten_times(tmp_path: Path) -> None:
    from sentinel.agent.organs.browser_download_upload_quarantine_l6 import (
        BrowserFileQuarantineActionKind,
        BrowserFileQuarantineContract,
        BrowserFileQuarantineOrganL6,
        BrowserFileQuarantineRequest,
    )
    from sentinel.agent.organs.browser_form_submit_special_authority_l6 import (
        BrowserFormSubmitContract,
        BrowserFormSubmitRequest,
        BrowserFormSubmitSpecialAuthorityL6,
    )
    from sentinel.agent.organs.browser_session_manager_l5_live import (
        BrowserSessionActionKind,
        BrowserSessionContract,
        BrowserSessionManagerL5Live,
        BrowserSessionRequest,
    )

    fixtures = {
        BROWSER_URL: MAIN_HTML,
        RESEARCH_URL: RESEARCH_HTML,
        FILES_URL: FILES_HTML,
        LOGIN_URL: LOGIN_HTML,
    }
    durations: list[float] = []
    for iteration in range(10):
        started = perf_counter()
        root = tmp_path / f"browser_run_{iteration}"
        kernel = MissionKernel(run_root=root / "runs")
        mission = kernel.create_mission(
            session_id=f"wave1-browser-{iteration}",
            draft=MissionDraft(title="Controlled browser task", objective="Complete and prove a live controlled task."),
        )
        kernel.enqueue(mission.mission_id)
        envelope = _browser_envelope(mission.mission_id)
        contract = BrowserSessionContract(
            mission_id=mission.mission_id,
            allowed_domains=["example.com"],
            allowed_action_kinds=[
                BrowserSessionActionKind.TYPE,
                BrowserSessionActionKind.CLICK,
                BrowserSessionActionKind.OPEN_TAB,
                BrowserSessionActionKind.SWITCH_TAB,
                BrowserSessionActionKind.CLOSE_TAB,
            ],
            max_steps=40,
            max_tabs=4,
        )
        manager = BrowserSessionManagerL5Live(
            capture_root=root / "captures",
            engine="playwright",
            document_fixtures=fixtures,
            accept_downloads=True,
        )
        try:
            opened = manager.open_session(BrowserSessionRequest(mission=envelope, url=BROWSER_URL, contract=contract))
            assert opened.accepted is True
            _record_result(kernel, mission.mission_id, "wave1_browser_opened", opened)

            typed = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.TYPE,
                    target_role="textbox",
                    target_name="Project name",
                    text="Wave One",
                )
            )
            assert typed.accepted is True

            submitted = BrowserFormSubmitSpecialAuthorityL6().execute(
                BrowserFormSubmitRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    session_id=str(opened.session_id),
                    contract=BrowserFormSubmitContract(
                        mission_id=mission.mission_id,
                        allowed_domains=["example.com"],
                        allow_form_submit=True,
                    ),
                    target_role="button",
                    target_name="Submit request",
                    source_snapshot_hash=manager.snapshot_for_session(
                        mission_id=mission.mission_id,
                        session_id=str(opened.session_id),
                    ).snapshot_sha256,
                ),
                session_manager=manager,
            )
            assert submitted.accepted is True
            _record_result(kernel, mission.mission_id, "wave1_browser_form_submitted", submitted)

            research_tab = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=RESEARCH_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.OPEN_TAB,
                )
            )
            assert research_tab.accepted is True and research_tab.receipt.tab_count == 2
            switched = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.SWITCH_TAB,
                    tab_id=opened.receipt.tab_id,
                )
            )
            assert switched.accepted is True and switched.receipt.form_state_summary == typed.receipt.form_state_summary

            files_tab = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=FILES_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.OPEN_TAB,
                )
            )
            assert files_tab.accepted is True
            upload_root = root / "uploads"
            quarantine_root = root / "downloads"
            upload_root.mkdir()
            upload_file = upload_root / "input.txt"
            upload_file.write_text("controlled upload", encoding="utf-8")
            file_contract = BrowserFileQuarantineContract(
                mission_id=mission.mission_id,
                allowed_domains=["example.com"],
                approved_upload_root=str(upload_root),
                approved_download_quarantine_root=str(quarantine_root),
                allow_upload=True,
                allow_download=True,
            )
            file_organ = BrowserFileQuarantineOrganL6()
            uploaded = file_organ.execute(
                BrowserFileQuarantineRequest(
                    mission=envelope,
                    url=FILES_URL,
                    session_id=str(opened.session_id),
                    contract=file_contract,
                    action_kind=BrowserFileQuarantineActionKind.UPLOAD,
                    target_role="button",
                    target_name="Upload file",
                    local_upload_path=str(upload_file),
                ),
                session_manager=manager,
            )
            downloaded = file_organ.execute(
                BrowserFileQuarantineRequest(
                    mission=envelope,
                    url=FILES_URL,
                    session_id=str(opened.session_id),
                    contract=file_contract,
                    action_kind=BrowserFileQuarantineActionKind.DOWNLOAD,
                    target_role="link",
                    target_name="Download result",
                ),
                session_manager=manager,
            )
            assert uploaded.accepted is True
            assert downloaded.accepted is True
            assert (quarantine_root / "wave-one.txt").exists()
            _record_result(kernel, mission.mission_id, "wave1_browser_upload_completed", uploaded)
            _record_result(kernel, mission.mission_id, "wave1_browser_download_completed", downloaded)

            main_again = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.SWITCH_TAB,
                    tab_id=opened.receipt.tab_id,
                )
            )
            assert main_again.accepted is True
            moved = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.CLICK,
                    target_role="button",
                    target_name="Move target",
                )
            )
            stale_target = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.CLICK,
                    target_role="button",
                    target_name="Old target",
                    timeout_ms=500,
                )
            )
            recovered = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=BROWSER_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.CLICK,
                    target_role="button",
                    target_name="New target",
                )
            )
            assert moved.accepted is True
            assert stale_target.accepted is False
            assert recovered.accepted is True
            _record_result(kernel, mission.mission_id, "wave1_browser_stale_target_detected", stale_target)
            _record_result(kernel, mission.mission_id, "wave1_browser_changed_target_recovered", recovered)

            login_tab = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=LOGIN_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.OPEN_TAB,
                )
            )
            assert login_tab.accepted is True
            login_checkpoint = manager.interact(
                BrowserSessionRequest(
                    mission=envelope,
                    url=LOGIN_URL,
                    contract=contract,
                    session_id=opened.session_id,
                    action_kind=BrowserSessionActionKind.TYPE,
                    target_role="textbox",
                    target_name="Password",
                    text="credential input must not execute",
                )
            )
            assert login_checkpoint.accepted is False
            assert login_checkpoint.reason == "credential_input_not_promoted_in_browser_session_v1"

            revoked = manager.observe(
                BrowserSessionRequest(
                    mission=_browser_envelope(mission.mission_id, revoked=True),
                    url=LOGIN_URL,
                    contract=contract,
                    session_id=opened.session_id,
                )
            )
            assert revoked.accepted is False
            assert revoked.reason == "mission_authority_revoked"
            _record_result(kernel, mission.mission_id, "wave1_browser_revocation_blocked", revoked)

            closed = manager.close_session(
                BrowserSessionRequest(mission=envelope, url=LOGIN_URL, contract=contract, session_id=opened.session_id)
            )
            assert closed.accepted is True
            after_close = manager.observe(
                BrowserSessionRequest(mission=envelope, url=LOGIN_URL, contract=contract, session_id=opened.session_id)
            )
            assert after_close.accepted is False
            assert after_close.reason == "browser_session_missing_or_closed"
            _record_result(kernel, mission.mission_id, "wave1_browser_closed", closed)

            next_mission = kernel.create_mission(
                session_id=f"wave1-browser-next-{iteration}",
                draft=MissionDraft(title="Fresh browser task", objective="Prove no stale session state leaks."),
            )
            kernel.enqueue(next_mission.mission_id)
            next_envelope = _browser_envelope(next_mission.mission_id)
            next_contract = contract.model_copy(update={"mission_id": next_mission.mission_id})
            next_opened = manager.open_session(
                BrowserSessionRequest(mission=next_envelope, url=BROWSER_URL, contract=next_contract)
            )
            next_observed = manager.observe(
                BrowserSessionRequest(
                    mission=next_envelope,
                    url=BROWSER_URL,
                    contract=next_contract,
                    session_id=next_opened.session_id,
                )
            )
            assert next_opened.accepted is True
            assert len(next_observed.receipt.form_state_summary) == 1
            assert next_observed.receipt.form_state_summary[0]["name"] == "Project name"
            assert next_observed.receipt.form_state_summary[0]["value_hash"] != typed.receipt.form_state_summary[0]["value_hash"]
            manager.close_session(
                BrowserSessionRequest(
                    mission=next_envelope,
                    url=BROWSER_URL,
                    contract=next_contract,
                    session_id=next_opened.session_id,
                )
            )

            kernel.update_status(mission.mission_id, OperatorMissionStatus.COMPLETED, "Wave 1 browser benchmark completed.")
            replay = MissionReplayBuilder(kernel.store).build(mission.mission_id)
            assert replay.tampered is False
            assert replay.reexecuted_actions is False
            assert replay.receipt_refs
            assert replay.finalgate_certificate_refs
            assert kernel.store.verify_timeline(mission.mission_id)
            assert kernel.telemetry_sink.require_certified_mode().certified_mode is True
            durations.append(perf_counter() - started)
        finally:
            manager.close_all()

    print(
        "wave1_browser_repeatability "
        f"passes=10 failures=0 median_seconds={median(durations):.3f} p95_seconds={_p95(durations):.3f} "
        "silent_success=0 duplicate_material_side_effects=0 cross_mission_contamination=0"
    )
