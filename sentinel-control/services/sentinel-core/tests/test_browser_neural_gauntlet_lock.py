from __future__ import annotations


def test_gauntlet_contains_required_browser_neural_scenarios() -> None:
    from sentinel.agent.browser.neural.gauntlet import BrowserNeuralGauntlet

    names = {case.case_id for case in BrowserNeuralGauntlet.default_cases()}

    assert {
        "one_page_task_recovery",
        "multi_step_browser_mission",
        "stale_selector_recovery",
        "modal_overlay_recovery",
        "redirect_flow",
        "auth_wall_detection",
        "payment_boundary_detection",
        "download_quarantine_path",
        "js_sandbox_path",
        "invented_evidence_rejection",
        "memory_not_authority_regression",
    }.issubset(names)


def test_gauntlet_run_records_replayable_ledger_events(tmp_path) -> None:
    from sentinel.agent.browser.neural.gauntlet import BrowserNeuralGauntlet
    from sentinel.agent.browser.neural.ledger import BrowserNeuralReceiptLedger

    ledger = BrowserNeuralReceiptLedger(tmp_path / "gauntlet.jsonl")
    report = BrowserNeuralGauntlet.default().run(ledger=ledger, workflow_id="wf_gauntlet", run_id="run_1")

    assert report.case_count >= 11
    assert report.contract_invariant_passed_count == report.case_count
    assert report.passed_count == 0
    assert all(result.execution_path_proven is False for result in report.case_results)
    replay = ledger.replay()
    assert len(replay) == report.case_count
    assert {event.event_type for event in replay} == {"browser_neural_gauntlet_case"}


def test_gauntlet_boundary_cases_remain_non_executing() -> None:
    from sentinel.agent.browser.neural.gauntlet import BrowserNeuralGauntlet

    report = BrowserNeuralGauntlet.default().run()

    boundary = {case.case_id: case for case in report.case_results}
    assert "auth_wall" in boundary["auth_wall_detection"].risk_flags
    assert "payment_boundary" in boundary["payment_boundary_detection"].risk_flags
    assert all(case.can_execute is False for case in report.case_results)
    assert report.authority_effect == "none"


def test_gauntlet_report_does_not_claim_global_fabric_or_live_payment() -> None:
    from sentinel.agent.browser.neural.gauntlet import BrowserNeuralGauntlet

    report = BrowserNeuralGauntlet.default().run()

    assert report.global_neural_fabric_complete is False
    assert report.live_payment_execution_complete is False
    assert report.browser_neural_cortex_runtime_advisory_only is True


def test_gauntlet_pass_requires_stage_evidence_not_expected_path_only() -> None:
    from sentinel.agent.browser.neural.gauntlet import BrowserNeuralGauntlet

    gauntlet = BrowserNeuralGauntlet.default()
    first = gauntlet.cases[0]
    report = gauntlet.run(
        stage_evidence_refs_by_case={
            first.case_id: [f"stage_ev_{index}" for index, _ in enumerate(first.expected_path)]
        }
    )

    by_id = {result.case_id: result for result in report.case_results}
    assert by_id[first.case_id].passed is True
    assert by_id[first.case_id].execution_path_proven is True
    assert report.passed_count == 1
