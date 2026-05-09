from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    CapabilityFrontierBuilder,
    CrossOrganFrontierRunner,
    CurrentLimit,
    FailureMode,
    MaxSupportedAction,
    MissingRuntimeSurface,
    OrganFrontierStressHarness,
    PromotionCandidate,
    RequiredNextAdapter,
    RequiredLLMIntegration,
    RiskLaneFit,
)
from sentinel.organs.lanes import AutonomyRiskLane


def test_frontier_report_covers_all_p6m_existing_organs():
    report = CapabilityFrontierBuilder().build_default_report()

    assert report.phase == "P6N_EXISTING_ORGANS_CAPABILITY_FRONTIER"
    assert set(report.organs.keys()) == {
        "browser",
        "external_api",
        "channel",
        "credentials",
        "desktop",
        "capital",
        "trading",
        "spend",
    }
    assert all(entry.max_supported_actions for entry in report.organs.values())
    assert all(entry.current_limits for entry in report.organs.values())
    assert all(entry.failure_modes for entry in report.organs.values())
    assert all(entry.promotion_candidates for entry in report.organs.values())


def test_each_frontier_entry_has_required_limit_taxonomy():
    report = CapabilityFrontierBuilder().build_default_report()

    for entry in report.organs.values():
        assert all(isinstance(item, MaxSupportedAction) for item in entry.max_supported_actions)
        assert all(isinstance(item, CurrentLimit) for item in entry.current_limits)
        assert all(isinstance(item, FailureMode) for item in entry.failure_modes)
        assert all(isinstance(item, MissingRuntimeSurface) for item in entry.missing_runtime_surfaces)
        assert all(isinstance(item, PromotionCandidate) for item in entry.promotion_candidates)
        assert all(isinstance(item, RequiredNextAdapter) for item in entry.required_next_adapters)
        assert all(isinstance(item, RequiredLLMIntegration) for item in entry.required_llm_integrations)
        assert all(entry.required_evidence_or_receipt)
        assert isinstance(entry.risk_lane_fit, RiskLaneFit)


def test_browser_frontier_stresses_multiple_reads_and_failures():
    harness = OrganFrontierStressHarness()
    result = harness.stress_browser()

    assert len(result.receipts) == 2
    assert result.failure_modes["timeout_or_fetch_failure"] == "captured"
    assert result.failure_modes["non_allowlisted_url"] == "rejected"
    assert "no login" in result.limit_report.current_limits
    assert "no form submit" in result.limit_report.current_limits
    assert "no stealth/captcha/bypass" in result.limit_report.current_limits


def test_external_api_frontier_stresses_get_head_and_rejections():
    result = OrganFrontierStressHarness().stress_external_api()

    assert [receipt.output_summary["method"] for receipt in result.receipts] == ["GET", "HEAD"]
    assert result.failure_modes["POST"] == "rejected"
    assert result.failure_modes["non_allowlisted_domain"] == "rejected"
    assert result.failure_modes["timeout_or_error_response"] == "captured"
    assert "no mutation" in result.limit_report.current_limits
    assert "no paid API live mode" in result.limit_report.current_limits


def test_channel_credentials_and_desktop_frontiers_use_real_local_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_FRONTIER_KEY", "secret-value")
    harness = OrganFrontierStressHarness(tmp_root=str(tmp_path))

    channel = harness.stress_channel()
    credentials = harness.stress_credentials()
    desktop = harness.stress_desktop()

    assert len(channel.receipts) == 2
    assert all((tmp_path / "drafts" / receipt.output_summary["filename"]).exists() for receipt in channel.receipts)
    assert channel.failure_modes["live_send_path"] == "rejected"
    assert credentials.failure_modes["missing_env_ref"] == "rejected"
    assert credentials.failure_modes["wrong_scope"] == "rejected"
    assert credentials.failure_modes["revoked_grant"] == "rejected"
    assert "secret-value" not in str(credentials.receipts[0].model_dump())
    assert desktop.failure_modes["path_traversal"] == "rejected"
    assert desktop.failure_modes["outside_root_path"] == "rejected"
    assert desktop.failure_modes["shell_process_execution"] == "rejected"
    assert "workspace file ops work" in desktop.limit_report.can_do_now


def test_capital_trading_and_spend_frontiers_classify_runtime_gaps():
    harness = OrganFrontierStressHarness()

    capital = harness.stress_capital()
    trading = harness.stress_trading()
    spend = harness.stress_spend()

    assert capital.output_summary["signal_count"] >= 3
    assert capital.failure_modes["unbacked_signal_refs"] == "rejected"
    assert "cannot spend" in capital.limit_report.current_limits
    assert trading.output_summary["paper_trade"] is True
    assert trading.failure_modes["real_broker_execution"] == "rejected"
    assert trading.failure_modes["profit_guarantee"] == "rejected"
    assert spend.output_summary["test_mode_provider"] is True
    assert spend.failure_modes["hidden_subscription"] == "rejected"
    assert spend.failure_modes["real_provider_execution"] == "rejected"


def test_cross_organ_frontier_scenarios_and_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_FRONTIER_KEY", "secret-value")
    runner = CrossOrganFrontierRunner(tmp_root=str(tmp_path))

    report = runner.run()

    assert report.cross_organ_scenarios["browser_to_capital_to_spend_proposal"] == "passed"
    assert report.cross_organ_scenarios["api_to_capital_to_trading_paper_decision"] == "passed"
    assert report.cross_organ_scenarios["credential_ref_to_api_read_with_redacted_receipt"] == "passed"
    assert report.cross_organ_scenarios["desktop_report_to_channel_draft"] == "passed"
    assert report.cross_organ_scenarios["market_data_to_trading_to_capital_signal"] == "passed"
    assert report.what_sentinel_can_do_now
    assert report.what_sentinel_can_only_simulate
    assert report.what_sentinel_cannot_do_yet
    assert "misuse objectives" in report.what_is_blocked_as_misuse
    assert report.weakest_organ == "credentials"
    assert report.closest_to_production_scoped_execution == "desktop"
    assert "channel" in report.organs_needing_llm_runtime_first


def test_frontier_model_rejects_unbacked_empty_reports():
    with pytest.raises(ValueError, match="evidence refs"):
        MaxSupportedAction(action="x", lane=AutonomyRiskLane.BLUE, repeated=False, evidence_refs=[])
    with pytest.raises(ValueError, match="description"):
        FailureMode(name="empty", trigger="", observed_behavior="rejected", evidence_refs=["fixture"])
    with pytest.raises(ValueError, match="promotion target"):
        PromotionCandidate(from_level="L3", to_level="", reason="x", evidence_refs=["fixture"])

