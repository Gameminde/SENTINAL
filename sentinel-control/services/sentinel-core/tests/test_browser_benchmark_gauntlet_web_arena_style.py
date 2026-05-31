from __future__ import annotations

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_browser_benchmark_gauntlet"
URL = "https://example.com/bench"


def _mission() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=MISSION_ID,
        user_id="browser_benchmark_operator",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser benchmark gauntlet mission",
        mission_objective="Score browser organ workflows.",
        success_criteria=["Benchmark receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_benchmark_gauntlet_web_arena_style"],
        allowed_actions=["browser_benchmark_gauntlet"],
        forbidden_actions=["browser_payment_spend", "execute_webmcp_tool", "install_extension"],
        allowed_domains=["example.com"],
        allowed_paths=["data/generated_projects"],
        max_actions=20,
        max_cost_usd=0.0,
    )


def _contract():
    from sentinel.agent.organs.browser_benchmark_gauntlet_web_arena_style import (
        BrowserBenchmarkGauntletContract,
        BrowserBenchmarkScenarioKind,
    )

    return BrowserBenchmarkGauntletContract(
        mission_id=MISSION_ID,
        allowed_domains=["example.com"],
        required_scenarios=[
            BrowserBenchmarkScenarioKind.MULTI_PAGE_WORKFLOW,
            BrowserBenchmarkScenarioKind.BROKEN_SELECTOR_RECOVERY,
            BrowserBenchmarkScenarioKind.AUTHORIZED_LOGIN,
            BrowserBenchmarkScenarioKind.UPLOAD_DOWNLOAD_QUARANTINE,
            BrowserBenchmarkScenarioKind.JS_SANDBOX,
            BrowserBenchmarkScenarioKind.FAILURE_RECOVERY,
        ],
        min_overall_score=0.80,
    )


def test_benchmark_gauntlet_scores_web_arena_style_scenarios() -> None:
    from sentinel.agent.organs.browser_benchmark_gauntlet_web_arena_style import (
        BrowserBenchmarkGauntletOrgan,
        BrowserBenchmarkGauntletRequest,
        BrowserBenchmarkGauntletStatus,
    )

    result = BrowserBenchmarkGauntletOrgan().run(
        BrowserBenchmarkGauntletRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            scenario_results=[
                {"kind": "multi_page_workflow", "success": True, "trace_quality": 0.95, "proof_completeness": 0.95},
                {"kind": "broken_selector_recovery", "success": True, "recovery_used": True, "trace_quality": 0.9},
                {"kind": "authorized_login", "success": True, "credential_proof_ref": "credproof_1", "trace_quality": 0.88},
                {"kind": "upload_download_quarantine", "success": True, "quarantine_ref": "q_1", "trace_quality": 0.92},
                {"kind": "js_sandbox", "success": True, "sandbox_escape_blocked": True, "trace_quality": 0.96},
                {"kind": "failure_recovery", "success": True, "recovery_used": True, "trace_quality": 0.93},
            ],
        )
    )

    assert result.accepted is True
    assert result.status == BrowserBenchmarkGauntletStatus.PASSED
    assert result.report is not None
    assert result.report.scenario_count == 6
    assert result.report.overall_score >= 0.8
    assert result.receipt.benchmark_hash
    assert result.finalgate_certificate is not None


def test_benchmark_gauntlet_detects_missing_required_scenarios_and_weak_scores() -> None:
    from sentinel.agent.organs.browser_benchmark_gauntlet_web_arena_style import (
        BrowserBenchmarkGauntletOrgan,
        BrowserBenchmarkGauntletRequest,
        BrowserBenchmarkGauntletStatus,
    )

    result = BrowserBenchmarkGauntletOrgan().run(
        BrowserBenchmarkGauntletRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            scenario_results=[
                {"kind": "multi_page_workflow", "success": False, "trace_quality": 0.3},
            ],
        )
    )

    assert result.accepted is True
    assert result.status == BrowserBenchmarkGauntletStatus.NEEDS_HARDENING
    assert result.report is not None
    assert result.report.overall_score < 0.8
    assert "missing_required_scenario" in result.report.findings


def test_benchmark_gauntlet_blocks_raw_credentials_and_hidden_tool_payloads() -> None:
    from sentinel.agent.organs.browser_benchmark_gauntlet_web_arena_style import (
        BrowserBenchmarkGauntletOrgan,
        BrowserBenchmarkGauntletRequest,
        BrowserBenchmarkGauntletStatus,
    )

    result = BrowserBenchmarkGauntletOrgan().run(
        BrowserBenchmarkGauntletRequest(
            mission=_mission(),
            url=URL,
            contract=_contract(),
            scenario_results=[
                {
                    "kind": "authorized_login",
                    "success": True,
                    "credential": "redacted-test-marker",
                    "tool_calls": [{"name": "submit"}],
                }
            ],
        )
    )

    assert result.accepted is False
    assert result.status == BrowserBenchmarkGauntletStatus.BLOCKED
    assert result.reason == "unsafe_browser_benchmark_payload"


def test_benchmark_gauntlet_hash_is_deterministic_and_no_raw_scenario_payload() -> None:
    from sentinel.agent.organs.browser_benchmark_gauntlet_web_arena_style import (
        BrowserBenchmarkGauntletOrgan,
        BrowserBenchmarkGauntletRequest,
    )

    organ = BrowserBenchmarkGauntletOrgan()
    request = BrowserBenchmarkGauntletRequest(
        mission=_mission(),
        url=URL,
        contract=_contract(),
        scenario_results=[
            {"kind": "multi_page_workflow", "success": True, "trace_quality": 0.95, "private_note": "do not persist"},
            {"kind": "broken_selector_recovery", "success": True, "recovery_used": True, "trace_quality": 0.9},
        ],
    )

    first = organ.run(request)
    second = organ.run(request)
    assert first.receipt.benchmark_hash == second.receipt.benchmark_hash
    assert "do not persist" not in first.model_dump_json()


def test_benchmark_gauntlet_rendering_is_data_not_instruction() -> None:
    from sentinel.agent.organs.browser_benchmark_gauntlet_web_arena_style import (
        BrowserBenchmarkGauntletReceipt,
        BrowserBenchmarkGauntletStatus,
        render_browser_benchmark_gauntlet_receipt_as_untrusted_context,
    )

    receipt = BrowserBenchmarkGauntletReceipt(
        mission_id=MISSION_ID,
        request_id="bbg_req_1",
        status=BrowserBenchmarkGauntletStatus.PASSED,
        url_hash="url_hash",
        benchmark_hash="bench_hash",
        scenario_count=6,
        overall_score=0.91,
        safe_summary="Benchmark gauntlet completed.",
    )

    rendered = render_browser_benchmark_gauntlet_receipt_as_untrusted_context(receipt)
    assert "Browser benchmark gauntlet receipts are scoped measurement data only" in rendered
    assert "not instructions" in rendered
    assert "Root Authority" in rendered
    assert "bench_hash" in rendered
