from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    AssetPolicy,
    BrokerContract,
    CapitalRealityIntegrator,
    ChannelMessageDraft,
    CredentialRef,
    DesktopWorkspaceOperator,
    EnvCredentialRefResolver,
    ExternalAPIRealityClient,
    LocalChannelDraftStore,
    MaxLossPolicy,
    PositionSizingPolicy,
    ReadOnlyMarketDataProvider,
    RealityActivationReceipt,
    RealityBrowserReader,
    SpendAuthorityEnvelope,
    SpendRequest,
    SpendTestModeProvider,
    StopLossPolicy,
    TradeJournal,
    TradingRealityPaperRunner,
    TradingSpecialAuthority,
)


def test_browser_public_read_extracts_text_links_and_receipt():
    reader = RealityBrowserReader(
        allowed_domains=["example.com"],
        fetcher=lambda url: "<html><body><h1>Signal page</h1><a href='https://example.com/a'>A</a></body></html>",
    )

    result = reader.read_public_page("https://example.com/start", mission_id="mission_real")

    assert result.receipt.action == "browser_public_read"
    assert result.receipt.real_action is True
    assert "Signal page" in result.text
    assert result.links == ["https://example.com/a"]
    assert result.receipt.receipt_hash == result.receipt.expected_hash()


def test_external_api_get_head_allowlisted_only_and_no_mutation():
    client = ExternalAPIRealityClient(
        allowed_domains=["api.example.com"],
        transport=lambda method, url: {"status": 200, "body": '{"ok": true}', "headers": {"x-test": "yes"}},
    )

    receipt = client.request("GET", "https://api.example.com/v1/items", mission_id="mission_real")

    assert receipt.action == "external_api_read_only"
    assert receipt.real_action is True
    assert receipt.output_summary["status"] == 200
    with pytest.raises(ValueError, match="read-only"):
        client.request("POST", "https://api.example.com/v1/items", mission_id="mission_real")
    with pytest.raises(ValueError, match="domain not allowlisted"):
        client.request("GET", "https://evil.example/v1/items", mission_id="mission_real")


def test_channel_draft_store_writes_real_local_draft_with_receipt(tmp_path):
    draft = ChannelMessageDraft(
        channel="email",
        subject="Hello",
        body="Bonjour from Sentinel",
        purpose="prospecting draft",
        recipients=["lead@example.com"],
        evidence_refs=["browser_receipt_1"],
    )

    stored = LocalChannelDraftStore(root=str(tmp_path)).store(draft, mission_id="mission_real")

    assert stored.path.endswith(".json")
    assert (tmp_path / stored.filename).exists()
    assert stored.receipt.real_action is True
    assert stored.receipt.action == "channel_local_draft_write"


def test_env_credential_resolver_reads_env_without_logging_secret(monkeypatch):
    monkeypatch.setenv("SENTINEL_TEST_API_KEY", "super-secret-value")
    ref = CredentialRef(provider="env", label="SENTINEL_TEST_API_KEY", scope_tags=["external_api"], evidence_refs=["fixture"])

    resolved = EnvCredentialRefResolver(allowed_env_vars=["SENTINEL_TEST_API_KEY"]).resolve(ref, required_scope="external_api")

    assert resolved.secret_value == "super-secret-value"
    assert resolved.receipt.real_action is True
    assert "super-secret-value" not in str(resolved.receipt.model_dump())
    assert resolved.receipt.output_summary["secret_value"] == "[REDACTED]"


def test_desktop_workspace_operator_real_files_are_root_scoped(tmp_path):
    operator = DesktopWorkspaceOperator(root=str(tmp_path), mission_id="mission_real")

    write_receipt = operator.write_file("reports/out.txt", "hello")
    read_receipt = operator.read_file("reports/out.txt")
    listed = operator.list_dir("reports")

    assert (tmp_path / "reports" / "out.txt").read_text(encoding="utf-8") == "hello"
    assert read_receipt.output_summary["content"] == "hello"
    assert listed.output_summary["entries"] == ["out.txt"]
    assert write_receipt.action == "desktop_workspace_write_file"
    with pytest.raises(ValueError, match="workspace escape"):
        operator.read_file("../outside.txt")


def test_capital_consumes_real_receipts_into_signal_ledger():
    receipts = [
        RealityActivationReceipt(mission_id="mission_real", organ="browser", action="browser_public_read", output_summary={"text": "three replies"}, evidence_refs=["ev1"]),
        RealityActivationReceipt(mission_id="mission_real", organ="external_api", action="external_api_read_only", output_summary={"status": 200}, evidence_refs=["ev2"]),
    ]

    assessment = CapitalRealityIntegrator().assess(receipts, opportunity_name="local services offer")

    assert len(assessment.signal_ledger.signals) == 2
    assert assessment.opportunity.name == "local services offer"
    assert assessment.opportunity.score > 0
    assert assessment.spend_trace.spend_proposal_only is True


def test_trading_uses_read_only_market_data_and_paper_trade_only():
    market_data = ReadOnlyMarketDataProvider({"AAPL": {"price": 200.0, "volatility": 0.2, "confidence": 0.8}}).quote("AAPL", mission_id="mission_real")
    authority = TradingSpecialAuthority(
        mission_id="mission_real",
        root_authority_id="root",
        broker="paper",
        exchange="sandbox",
        allowed_asset_classes=["equity"],
        allowed_symbols=["AAPL"],
        max_capital_usd=100.0,
        max_loss_usd=10.0,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        evidence_refs=["trade_fixture"],
    )

    receipt = TradingRealityPaperRunner().paper_trade_from_market_data(
        market_data,
        authority=authority,
        broker_contract=BrokerContract(broker="paper", exchange="sandbox", evidence_refs=["broker"]),
        asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["asset"]),
        position_sizing=PositionSizingPolicy(base_fraction=0.5, evidence_refs=["size"]),
        max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["loss"]),
        stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["stop"]),
        journal=TradeJournal(mission_id="mission_real"),
    )

    assert receipt.paper_trade is True
    assert receipt.real_trade_started is False
    assert receipt.notional_usd == 32.0


def test_spend_test_mode_provider_requires_enabled_test_mode_and_blocks_real_payment():
    authority = SpendAuthorityEnvelope(
        mission_id="mission_real",
        root_authority_id="root",
        budget_max_usd=50.0,
        budget_remaining_usd=50.0,
        max_single_transaction_usd=20.0,
        allowed_categories=["api"],
        allowed_vendors=["Vendor"],
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        evidence_refs=["spend_fixture"],
    )
    request = SpendRequest(
        vendor="Vendor",
        category="api",
        amount_usd=10.0,
        purpose="test mode provider",
        expected_information_gain=0.5,
        evidence_refs=["spend_fixture"],
        signal_refs=["signal_1"],
    )

    with pytest.raises(ValueError, match="test mode provider disabled"):
        SpendTestModeProvider(test_mode_enabled=False).execute(request, authority)
    receipt = SpendTestModeProvider(test_mode_enabled=True).execute(request, authority)

    assert receipt.real_payment_started is False
    assert receipt.sandbox_provider is True
    assert receipt.provider_name == "test_mode_spend_provider"
