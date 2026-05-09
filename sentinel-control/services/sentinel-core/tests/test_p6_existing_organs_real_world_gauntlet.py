from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    CredentialRef,
    EnvCredentialGrant,
    ExistingOrganRealWorldGauntlet,
    ExistingOrganRealWorldGauntletRunner,
    RealWorldGauntletReport,
    RealityCredentialGrantStore,
)


def test_gauntlet_pushes_all_existing_organs_in_max_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_GAUNTLET_API_KEY", "secret-gauntlet-value")

    report = ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path)).run()

    assert report.phase == "P6O_EXISTING_ORGANS_REAL_WORLD_GAUNTLET"
    assert set(report.organ_results) == {
        "browser",
        "external_api",
        "channel",
        "credentials",
        "desktop",
        "capital",
        "trading",
        "spend",
    }
    assert all(result.max_mode for result in report.organ_results.values())
    assert report.organ_results["browser"].receipt_count >= 3
    assert report.organ_results["external_api"].receipt_count >= 3
    assert report.organ_results["channel"].receipt_count >= 3
    assert report.organ_results["desktop"].receipt_count >= 5
    assert report.organ_results["capital"].receipt_count >= 1
    assert report.organ_results["trading"].receipt_count >= 2
    assert report.organ_results["spend"].receipt_count >= 2
    assert report.no_new_organ_family is True
    assert report.authority_expansion is False
    assert "desktop_workspace_l6" in report.next_promotion_candidates
    assert "browser_controlled_navigation_l6" in report.next_promotion_candidates


def test_browser_max_crawl_reads_many_pages_records_failures_and_rejects_unallowlisted(tmp_path):
    report = ExistingOrganRealWorldGauntlet(tmp_root=str(tmp_path)).push_browser_max(
        urls=[
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
            "https://example.com/fail",
            "https://blocked.example/nope",
        ],
        allowed_domains=["example.com"],
        mission_id="mission_gauntlet",
    )

    assert report.organ == "browser"
    assert report.receipt_count == 3
    assert report.failures["fetch_failure"] == "captured"
    assert report.failures["domain_not_allowlisted"] == "rejected"
    assert "multi_page_public_read" in report.strengthened_surfaces
    assert "no login/session mutation yet" in report.limits_remaining


def test_external_api_batch_read_pushes_get_head_errors_and_blocks_mutation(tmp_path):
    result = ExistingOrganRealWorldGauntlet(tmp_root=str(tmp_path)).push_external_api_max(
        mission_id="mission_gauntlet",
        requests=[
            ("GET", "https://api.example.com/items"),
            ("HEAD", "https://api.example.com/items"),
            ("GET", "https://api.example.com/error"),
            ("POST", "https://api.example.com/items"),
            ("GET", "https://blocked.example/items"),
        ],
        allowed_domains=["api.example.com"],
    )

    assert result.receipt_count == 3
    assert result.failures["mutation_method"] == "rejected"
    assert result.failures["domain_not_allowlisted"] == "rejected"
    assert result.failures["error_response"] == "captured"
    assert "batch_read_only_api" in result.strengthened_surfaces


def test_credential_grant_store_enforces_scope_expiry_revocation_and_redaction(monkeypatch):
    monkeypatch.setenv("SENTINEL_GAUNTLET_API_KEY", "secret-gauntlet-value")
    ref = CredentialRef(
        provider="env",
        label="SENTINEL_GAUNTLET_API_KEY",
        scope_tags=["external_api"],
        evidence_refs=["gauntlet"],
    )
    grant = EnvCredentialGrant(
        credential_ref_id=ref.id,
        allowed_scope="external_api",
        allowed_env_var="SENTINEL_GAUNTLET_API_KEY",
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
        evidence_refs=["grant"],
    )
    store = RealityCredentialGrantStore(grants=[grant], allowed_env_vars=["SENTINEL_GAUNTLET_API_KEY"])

    resolved = store.resolve(ref, required_scope="external_api")

    assert resolved.secret_value == "secret-gauntlet-value"
    assert "secret-gauntlet-value" not in str(resolved.receipt.model_dump())
    assert resolved.receipt.output_summary["secret_value"] == "[REDACTED]"

    revoked = grant.revoke(reason="operator stop")
    with pytest.raises(ValueError, match="credential grant revoked"):
        RealityCredentialGrantStore(grants=[revoked], allowed_env_vars=["SENTINEL_GAUNTLET_API_KEY"]).resolve(ref, required_scope="external_api")

    expired = grant.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)})
    with pytest.raises(ValueError, match="credential grant expired"):
        RealityCredentialGrantStore(grants=[expired], allowed_env_vars=["SENTINEL_GAUNTLET_API_KEY"]).resolve(ref, required_scope="external_api")

    with pytest.raises(ValueError, match="credential grant scope mismatch"):
        store.resolve(ref, required_scope="channel")


def test_desktop_channel_capital_trading_spend_cross_organ_power_path(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_GAUNTLET_API_KEY", "secret-gauntlet-value")

    report = ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path)).run()

    assert report.cross_organ_results["browser_api_desktop_channel_to_capital"] == "passed"
    assert report.cross_organ_results["market_data_to_trading_to_capital_signal"] == "passed"
    assert report.cross_organ_results["capital_to_spend_test_mode"] == "passed"
    assert report.cross_organ_results["credential_to_api_redacted_path"] == "passed"
    assert report.weakest_after_gauntlet == "credentials"
    assert report.closest_to_real_world_promotion == "desktop"
    assert "browser live login/session handling" in report.remaining_limits
    assert "real payment provider" in report.remaining_limits
    assert "real broker execution" in report.remaining_limits


def test_gauntlet_report_rejects_empty_or_authority_expanding_results(tmp_path):
    with pytest.raises(ValueError, match="requires organ results"):
        RealWorldGauntletReport(
            organ_results={},
            cross_organ_results={},
            next_promotion_candidates=["desktop_workspace_l6"],
            remaining_limits=["x"],
            weakest_after_gauntlet="credentials",
            closest_to_real_world_promotion="desktop",
        )

    runner = ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path))
    report = runner.run()
    forged = report.model_copy(update={"authority_expansion": True})
    with pytest.raises(ValueError, match="cannot expand authority"):
        RealWorldGauntletReport(**forged.model_dump())
