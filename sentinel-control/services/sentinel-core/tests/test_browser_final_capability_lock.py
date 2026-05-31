from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_browser_final_capability_lock_docs_mark_roadmap_complete() -> None:
    readme = _read("README.md")
    current = _read("sentinel-control/docs/CURRENT_STATE_LOCK.md")
    roadmap = _read("sentinel-control/docs/organs/ORGAN_EXECUTION_EXPANSION_ROADMAP.md")

    assert "current_phase = BROWSER_FINAL_CAPABILITY_LOCKED" in readme
    assert "current_phase = BROWSER_FINAL_CAPABILITY_LOCKED" in current
    assert "current_phase = BROWSER_FINAL_CAPABILITY_LOCKED" in roadmap
    assert "BROWSER_CONTROLLED_EXTENSION_AND_WEBMCP_BRIDGE_L7 [DONE]" in roadmap
    assert "16. BROWSER_FINAL_CAPABILITY_LOCK [DONE]" in roadmap


def test_browser_final_capability_lock_imports_all_browser_power_surfaces() -> None:
    from sentinel.agent.organs import (
        BrowserAccountCreationOrganL7,
        BrowserBenchmarkGauntletOrgan,
        BrowserBoundaryManagerL6L7,
        BrowserExtensionBridgeOrganL7,
        BrowserFileQuarantineOrganL6,
        BrowserFormSubmitSpecialAuthorityL6,
        BrowserInputParityOrganL5L6,
        BrowserJSSandboxOrganL6,
        BrowserMultiStepTaskOrchestratorV1,
        BrowserOperatorAgentL4L5Live,
        BrowserPaymentSpendOrganL7,
        BrowserReplayStudioOrganV1,
        BrowserSessionManagerL5Live,
    )

    assert BrowserOperatorAgentL4L5Live.organ_id == "browser_operator_agent_l4_l5_live_v1"
    assert BrowserSessionManagerL5Live.organ_id == "browser_session_manager_l5_live_v1"
    assert BrowserMultiStepTaskOrchestratorV1.organ_id == "browser_multi_step_task_orchestrator_v1"
    assert BrowserFormSubmitSpecialAuthorityL6.organ_id == "browser_form_submit_special_authority_l6_v1"
    assert BrowserFileQuarantineOrganL6.organ_id == "browser_download_upload_quarantine_l6_v1"
    assert BrowserJSSandboxOrganL6.organ_id == "browser_js_sandbox_special_authority_l6_v1"
    assert BrowserInputParityOrganL5L6.organ_id == "browser_devtools_input_parity_l5_l6"
    assert BrowserBenchmarkGauntletOrgan.organ_id == "browser_benchmark_gauntlet_web_arena_style"
    assert BrowserBoundaryManagerL6L7.organ_id == "browser_boundary_manager_l6_l7"
    assert BrowserPaymentSpendOrganL7.organ_id == "browser_payment_spend_special_authority_l7"
    assert BrowserAccountCreationOrganL7.organ_id == "browser_account_creation_special_authority_l7"
    assert BrowserReplayStudioOrganV1.organ_id == "browser_observability_replay_studio_v1"
    assert BrowserExtensionBridgeOrganL7.organ_id == "browser_controlled_extension_webmcp_bridge_l7"


def test_browser_final_capability_lock_keeps_high_power_organs_out_of_default_runtime_execution() -> None:
    runtime_execution = _read("sentinel-control/services/sentinel-core/sentinel/agent/organs/runtime_execution.py")
    runtime = _read("sentinel-control/services/sentinel-core/sentinel/agent/runtime.py")

    forbidden_runtime_organs = [
        "BrowserFormSubmitSpecialAuthorityL6",
        "BrowserLoginCredentialSessionBrokerL6",
        "BrowserFileQuarantineOrganL6",
        "BrowserJSSandboxOrganL6",
        "BrowserPaymentSpendOrganL7",
        "BrowserAccountCreationOrganL7",
        "BrowserExtensionBridgeOrganL7",
    ]
    for name in forbidden_runtime_organs:
        assert name not in runtime_execution
        assert name not in runtime
    assert "organ_dispatch_enabled: bool = False" in runtime_execution


def test_browser_final_capability_lock_report_records_remaining_live_adapter_gaps() -> None:
    report = _read("sentinel-control/docs/reviews/BROWSER_FINAL_CAPABILITY_LOCK_REPORT.md")

    assert "Browser roadmap status = LOCKED" in report
    assert "Live extension adapter = NOT_STARTED" in report
    assert "Live MCP adapter = NOT_STARTED" in report
    assert "Generic default-on dangerous execution = REJECTED" in report
    assert "Power surface contracts/receipts/FinalGate = CLOSED" in report


def test_browser_final_capability_lock_has_no_raw_secret_or_default_authority_claims() -> None:
    report = _read("sentinel-control/docs/reviews/BROWSER_FINAL_CAPABILITY_LOCK_REPORT.md")

    assert "raw credential persistence = NOT_STARTED" in report
    assert "default runtime dangerous wiring = NOT_STARTED" in report
    assert "receipt grants future authority" not in report.lower()
    assert "finalgate grants future authority" not in report.lower()
