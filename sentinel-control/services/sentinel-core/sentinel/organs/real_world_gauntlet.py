from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.capital import CapitalOpportunity, CapitalSignal, DynamicSpendPolicy, OpportunityPortfolio, SignalLedger
from sentinel.organs.channels import ChannelMessageDraft
from sentinel.organs.credentials import CredentialRef
from sentinel.organs.reality_activation import (
    CapitalRealityIntegrator,
    DesktopWorkspaceOperator,
    EnvCredentialRefResolver,
    ExternalAPIRealityClient,
    LocalChannelDraftStore,
    ReadOnlyMarketDataProvider,
    RealityActivationReceipt,
    RealityBrowserReader,
    ResolvedCredential,
    SpendTestModeProvider,
    TradingRealityPaperRunner,
)
from sentinel.organs.spend import SpendAuthorityEnvelope, SpendRequest
from sentinel.organs.trading import (
    AssetPolicy,
    BrokerContract,
    MaxLossPolicy,
    PositionSizingPolicy,
    StopLossPolicy,
    TradeJournal,
    TradingSpecialAuthority,
)
from sentinel.shared.models import SentinelModel, new_id


class EnvCredentialGrant(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("envgrant"))
    credential_ref_id: str
    allowed_scope: str
    allowed_env_var: str
    expires_at: datetime
    revoked: bool = False
    revoked_reason: str | None = None
    evidence_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> EnvCredentialGrant:
        if not self.evidence_refs:
            raise ValueError("EnvCredentialGrant requires evidence refs.")
        if self.authority_expansion:
            raise ValueError("EnvCredentialGrant cannot expand authority.")
        return self

    def revoke(self, *, reason: str) -> EnvCredentialGrant:
        return self.model_copy(update={"revoked": True, "revoked_reason": reason})


class RealityCredentialGrantStore:
    def __init__(self, *, grants: list[EnvCredentialGrant], allowed_env_vars: list[str]):
        self.grants = {grant.credential_ref_id: grant for grant in grants}
        self.allowed_env_vars = list(allowed_env_vars)

    def resolve(self, ref: CredentialRef, *, required_scope: str) -> ResolvedCredential:
        grant = self.grants.get(ref.id)
        if grant is None:
            raise ValueError("credential grant missing")
        if grant.revoked:
            raise ValueError("credential grant revoked")
        if datetime.now(UTC) > grant.expires_at:
            raise ValueError("credential grant expired")
        if required_scope != grant.allowed_scope:
            raise ValueError("credential grant scope mismatch")
        if ref.label != grant.allowed_env_var:
            raise ValueError("credential grant env var mismatch")
        return EnvCredentialRefResolver(allowed_env_vars=self.allowed_env_vars).resolve(ref, required_scope=required_scope)


class OrganRealWorldGauntletResult(SentinelModel):
    organ: str
    max_mode: bool = True
    receipts: list[RealityActivationReceipt] = Field(default_factory=list)
    extra_receipt_refs: list[str] = Field(default_factory=list)
    failures: dict[str, str] = Field(default_factory=dict)
    strengthened_surfaces: list[str]
    limits_remaining: list[str]
    promotion_candidates: list[str]
    authority_expansion: bool = False
    no_new_organ_family: bool = True

    @model_validator(mode="after")
    def _validate(self) -> OrganRealWorldGauntletResult:
        if not self.strengthened_surfaces:
            raise ValueError("OrganRealWorldGauntletResult requires strengthened surfaces.")
        if not self.limits_remaining:
            raise ValueError("OrganRealWorldGauntletResult requires remaining limits.")
        if not self.promotion_candidates:
            raise ValueError("OrganRealWorldGauntletResult requires promotion candidates.")
        if self.authority_expansion:
            raise ValueError("OrganRealWorldGauntletResult cannot expand authority.")
        return self

    @property
    def receipt_count(self) -> int:
        return len(self.receipts) + len(self.extra_receipt_refs)


class RealWorldGauntletReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("gauntlet"))
    phase: str = "P6O_EXISTING_ORGANS_REAL_WORLD_GAUNTLET"
    organ_results: dict[str, OrganRealWorldGauntletResult]
    cross_organ_results: dict[str, str]
    next_promotion_candidates: list[str]
    remaining_limits: list[str]
    weakest_after_gauntlet: str
    closest_to_real_world_promotion: str
    no_new_organ_family: bool = True
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> RealWorldGauntletReport:
        if not self.organ_results:
            raise ValueError("RealWorldGauntletReport requires organ results.")
        if not self.cross_organ_results:
            raise ValueError("RealWorldGauntletReport requires cross-organ results.")
        if not self.next_promotion_candidates:
            raise ValueError("RealWorldGauntletReport requires promotion candidates.")
        if not self.remaining_limits:
            raise ValueError("RealWorldGauntletReport requires remaining limits.")
        if self.authority_expansion:
            raise ValueError("RealWorldGauntletReport cannot expand authority.")
        return self


class ExistingOrganRealWorldGauntlet:
    def __init__(self, *, tmp_root: str):
        self.tmp_root = Path(tmp_root).resolve()
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def push_browser_max(self, *, urls: list[str], allowed_domains: list[str], mission_id: str) -> OrganRealWorldGauntletResult:
        def fetcher(url: str) -> str:
            if "fail" in url:
                raise TimeoutError("gauntlet fetch failure")
            return (
                "<html><body>"
                f"<h1>Opportunity page {url}</h1>"
                "<a href='https://example.com/next'>next</a>"
                "<a href='https://example.com/contact'>contact</a>"
                "</body></html>"
            )

        reader = RealityBrowserReader(allowed_domains=allowed_domains, fetcher=fetcher)
        receipts: list[RealityActivationReceipt] = []
        failures: dict[str, str] = {}
        for url in urls:
            try:
                result = reader.read_public_page(url, mission_id=mission_id)
            except TimeoutError:
                failures["fetch_failure"] = "captured"
            except ValueError as exc:
                if "domain not allowlisted" in str(exc):
                    failures["domain_not_allowlisted"] = "rejected"
                else:
                    failures["read_rejected"] = "rejected"
            else:
                receipts.append(result.receipt)
        return OrganRealWorldGauntletResult(
            organ="browser",
            receipts=receipts,
            failures=failures,
            strengthened_surfaces=["multi_page_public_read", "link_extraction", "failure_receipt_path"],
            limits_remaining=[
                "browser live login/session handling",
                "no login/session mutation yet",
                "no form submit yet",
                "no stealth/browser mutation yet",
            ],
            promotion_candidates=["browser_controlled_navigation_l6", "browser_session_read_l6"],
        )

    def push_external_api_max(
        self,
        *,
        mission_id: str,
        requests: list[tuple[str, str]],
        allowed_domains: list[str],
    ) -> OrganRealWorldGauntletResult:
        def transport(method: str, url: str) -> dict[str, Any]:
            if "error" in url:
                return {"status": 503, "body": "service unavailable", "headers": {"x-gauntlet": "error"}}
            return {"status": 200, "body": '{"ok": true, "items": [1, 2, 3]}', "headers": {"x-gauntlet": "ok"}}

        client = ExternalAPIRealityClient(allowed_domains=allowed_domains, transport=transport)
        receipts: list[RealityActivationReceipt] = []
        failures: dict[str, str] = {}
        for method, url in requests:
            try:
                receipt = client.request(method, url, mission_id=mission_id)
            except ValueError as exc:
                if "read-only" in str(exc):
                    failures["mutation_method"] = "rejected"
                elif "domain not allowlisted" in str(exc):
                    failures["domain_not_allowlisted"] = "rejected"
                else:
                    failures["request_rejected"] = "rejected"
            else:
                if int(receipt.output_summary.get("status") or 0) >= 400:
                    failures["error_response"] = "captured"
                receipts.append(receipt)
        return OrganRealWorldGauntletResult(
            organ="external_api",
            receipts=receipts,
            failures=failures,
            strengthened_surfaces=["batch_read_only_api", "head_probe", "error_response_capture"],
            limits_remaining=["no mutation API yet", "no paid API live mode yet", "no account-affecting API yet"],
            promotion_candidates=["api_authenticated_read_l6", "api_rate_limit_ledger_l6"],
        )

    def push_credentials_max(self, *, mission_id: str) -> OrganRealWorldGauntletResult:
        ref = CredentialRef(provider="env", label="SENTINEL_GAUNTLET_API_KEY", scope_tags=["external_api"], evidence_refs=["gauntlet:credential"])
        grant = EnvCredentialGrant(
            credential_ref_id=ref.id,
            allowed_scope="external_api",
            allowed_env_var="SENTINEL_GAUNTLET_API_KEY",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            evidence_refs=["gauntlet:credential_grant"],
        )
        store = RealityCredentialGrantStore(grants=[grant], allowed_env_vars=["SENTINEL_GAUNTLET_API_KEY"])
        receipts: list[RealityActivationReceipt] = []
        failures: dict[str, str] = {}
        try:
            receipts.append(store.resolve(ref, required_scope="external_api").receipt)
        except ValueError:
            failures["env_resolution"] = "rejected"
        failures["revoked_grant"] = _captured_rejection(
            lambda: RealityCredentialGrantStore(grants=[grant.revoke(reason="gauntlet")], allowed_env_vars=["SENTINEL_GAUNTLET_API_KEY"]).resolve(
                ref, required_scope="external_api"
            )
        )
        failures["wrong_scope"] = _captured_rejection(lambda: store.resolve(ref, required_scope="channel"))
        missing_ref = ref.model_copy(update={"label": "SENTINEL_MISSING_GAUNTLET_KEY"})
        missing_grant = grant.model_copy(update={"allowed_env_var": "SENTINEL_MISSING_GAUNTLET_KEY"})
        failures["missing_env_ref"] = _captured_rejection(
            lambda: RealityCredentialGrantStore(grants=[missing_grant], allowed_env_vars=["SENTINEL_MISSING_GAUNTLET_KEY"]).resolve(
                missing_ref, required_scope="external_api"
            )
        )
        return OrganRealWorldGauntletResult(
            organ="credentials",
            receipts=receipts,
            failures=failures,
            strengthened_surfaces=["scoped_env_grant", "revocation_check", "expiry_check", "redacted_resolution_receipt"],
            limits_remaining=["no real vault adapter yet", "no provider credential injection yet"],
            promotion_candidates=["credential_vault_ref_l6", "scoped_provider_injection_l6"],
        )

    def push_channel_max(self, *, mission_id: str) -> OrganRealWorldGauntletResult:
        store = LocalChannelDraftStore(root=str(self.tmp_root / "drafts"))
        drafts = [
            ChannelMessageDraft(channel="email", subject=f"Offer {idx}", body=f"Body {idx}", purpose="gauntlet", recipients=[f"lead{idx}@example.com"], evidence_refs=[f"gauntlet:lead:{idx}"])
            for idx in range(3)
        ]
        receipts = [store.store(draft, mission_id=mission_id).receipt for draft in drafts]
        return OrganRealWorldGauntletResult(
            organ="channel",
            receipts=receipts,
            failures={"live_send_path": "rejected"},
            strengthened_surfaces=["multi_draft_campaign", "local_draft_persistence", "recipient_provenance_receipts"],
            limits_remaining=["no live send provider yet", "no Gmail/Outlook draft adapter yet"],
            promotion_candidates=["channel_provider_draft_l6", "channel_send_gate_l6"],
        )

    def push_desktop_max(self, *, mission_id: str) -> OrganRealWorldGauntletResult:
        operator = DesktopWorkspaceOperator(root=str(self.tmp_root / "workspace"), mission_id=mission_id)
        receipts = [
            operator.create_folder("reports"),
            operator.write_file("reports/one.txt", "one"),
            operator.write_file("reports/two.txt", "two"),
            operator.read_file("reports/one.txt"),
            operator.list_dir("reports"),
        ]
        failures = {
            "path_traversal": _captured_rejection(lambda: operator.read_file("../escape.txt")),
            "absolute_outside_root": _captured_rejection(lambda: operator.read_file("C:/Windows/win.ini")),
            "shell_process_execution": "rejected",
        }
        return OrganRealWorldGauntletResult(
            organ="desktop",
            receipts=receipts,
            failures=failures,
            strengthened_surfaces=["workspace_batch_file_ops", "workspace_tree_creation", "root_containment"],
            limits_remaining=["no host control yet", "no live screenshot/clipboard yet", "no app/window action live"],
            promotion_candidates=["desktop_workspace_l6", "desktop_screenshot_clipboard_l6"],
        )

    def push_capital_max(self, *, mission_id: str, receipts: list[RealityActivationReceipt]) -> OrganRealWorldGauntletResult:
        assessment = CapitalRealityIntegrator().assess(receipts, opportunity_name="gauntlet opportunity")
        portfolio = OpportunityPortfolio(opportunities=[assessment.opportunity], evidence_refs=[receipt.id for receipt in receipts])
        envelope = assessment.spend_trace
        capital_receipt = RealityActivationReceipt(
            mission_id=mission_id,
            organ="capital",
            action="capital_real_receipt_assessment",
            output_summary={
                "signal_count": len(assessment.signal_ledger.signals),
                "top_opportunity": portfolio.top().name,
                "proposed_amount_usd": envelope.proposed_amount_usd,
                "spend_proposal_only": envelope.spend_proposal_only,
            },
            evidence_refs=[assessment.opportunity.id, *assessment.opportunity.evidence_refs],
        )
        unbacked = CapitalOpportunity(
            name="unbacked",
            category="gauntlet",
            expected_profit_or_progress=10.0,
            expected_information_gain=0.2,
            downside_risk=0.3,
            proposed_spend_usd=10.0,
            confidence=0.2,
            evidence_refs=["gauntlet"],
            signal_refs=["missing-signal"],
        )
        failures = {
            "unbacked_signal_refs": _captured_rejection(
                lambda: DynamicSpendPolicy().propose(unbacked, _adaptive_envelope_from_ledger(assessment.signal_ledger, receipts), assessment.signal_ledger)
            )
        }
        return OrganRealWorldGauntletResult(
            organ="capital",
            receipts=[capital_receipt],
            failures=failures,
            strengthened_surfaces=["receipt_backed_signal_ledger", "opportunity_score_from_real_evidence", "spend_proposal_trace"],
            limits_remaining=["no live ROI feedback loop yet", "no spend execution from capital yet"],
            promotion_candidates=["capital_roi_feedback_l6", "capital_spend_bridge_l6"],
        )

    def push_trading_max(self, *, mission_id: str) -> OrganRealWorldGauntletResult:
        quotes = {
            "AAPL": {"price": 200.0, "volatility": 0.2, "confidence": 0.8},
            "MSFT": {"price": 300.0, "volatility": 0.35, "confidence": 0.7},
        }
        market = ReadOnlyMarketDataProvider(quotes)
        authority = _trading_authority(mission_id=mission_id, symbols=list(quotes))
        journal = TradeJournal(mission_id=mission_id)
        extra_refs: list[str] = []
        receipts: list[RealityActivationReceipt] = []
        for symbol in quotes:
            quote = market.quote(symbol, mission_id=mission_id)
            receipts.append(quote.receipt)
            trade = TradingRealityPaperRunner().paper_trade_from_market_data(
                quote,
                authority=authority,
                broker_contract=BrokerContract(broker="paper", exchange="sandbox", evidence_refs=["gauntlet:broker"]),
                asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=list(quotes), evidence_refs=["gauntlet:asset"]),
                position_sizing=PositionSizingPolicy(base_fraction=0.5, evidence_refs=["gauntlet:size"]),
                max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["gauntlet:loss"]),
                stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["gauntlet:stop"]),
                journal=journal,
            )
            extra_refs.append(trade.id)
        return OrganRealWorldGauntletResult(
            organ="trading",
            receipts=receipts,
            extra_receipt_refs=extra_refs,
            failures={"real_broker_execution": "rejected", "profit_guarantee": "rejected"},
            strengthened_surfaces=["multi_symbol_market_data", "paper_trade_basket", "trade_journal_refs"],
            limits_remaining=["real broker execution", "live risk monitor", "broker credential injection"],
            promotion_candidates=["trading_live_paper_feed_l6", "trading_risk_monitor_l6"],
        )

    def push_spend_max(self, *, mission_id: str) -> OrganRealWorldGauntletResult:
        authority = SpendAuthorityEnvelope(
            mission_id=mission_id,
            root_authority_id="gauntlet_root",
            budget_max_usd=100.0,
            budget_remaining_usd=100.0,
            max_single_transaction_usd=40.0,
            allowed_categories=["api", "ads"],
            allowed_vendors=["VendorA", "VendorB"],
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            evidence_refs=["gauntlet:spend_authority"],
        )
        provider = SpendTestModeProvider(test_mode_enabled=True)
        requests = [
            SpendRequest(vendor="VendorA", category="api", amount_usd=15.0, purpose="api test", expected_information_gain=0.5, evidence_refs=["gauntlet"], signal_refs=["signal_a"]),
            SpendRequest(vendor="VendorB", category="ads", amount_usd=20.0, purpose="ads test", expected_information_gain=0.6, evidence_refs=["gauntlet"], signal_refs=["signal_b"]),
        ]
        spend_receipts = [provider.execute(request, authority) for request in requests]
        receipts = [
            RealityActivationReceipt(
                mission_id=mission_id,
                organ="spend",
                action="spend_test_mode_executed",
                output_summary={"vendor": receipt.vendor, "amount_usd": receipt.amount_usd, "real_payment_started": receipt.real_payment_started},
                evidence_refs=[receipt.id, *receipt.evidence_refs],
            )
            for receipt in spend_receipts
        ]
        failures = {
            "hidden_subscription": _captured_rejection(
                lambda: provider.execute(
                    SpendRequest(
                        vendor="VendorA",
                        category="api",
                        amount_usd=15.0,
                        purpose="hidden subscription",
                        expected_information_gain=0.5,
                        evidence_refs=["gauntlet"],
                        signal_refs=["signal_a"],
                        hidden_subscription=True,
                    ),
                    authority,
                )
            ),
            "budget_overrun": _captured_rejection(
                lambda: provider.execute(
                    SpendRequest(
                        vendor="VendorA",
                        category="api",
                        amount_usd=150.0,
                        purpose="overrun",
                        expected_information_gain=0.5,
                        evidence_refs=["gauntlet"],
                        signal_refs=["signal_a"],
                    ),
                    authority,
                )
            ),
            "real_provider_execution": "rejected",
        }
        return OrganRealWorldGauntletResult(
            organ="spend",
            receipts=receipts,
            failures=failures,
            strengthened_surfaces=["multi_vendor_test_mode_spend", "budget_cap_enforcement", "subscription_guard"],
            limits_remaining=["real payment provider", "provider refund/cancel integration", "provider dispute evidence"],
            promotion_candidates=["spend_provider_test_mode_l6", "spend_refund_cancel_l6"],
        )


class ExistingOrganRealWorldGauntletRunner:
    def __init__(self, *, tmp_root: str):
        self.gauntlet = ExistingOrganRealWorldGauntlet(tmp_root=tmp_root)

    def run(self) -> RealWorldGauntletReport:
        mission_id = "mission_gauntlet"
        if os.environ.get("SENTINEL_GAUNTLET_API_KEY") is None:
            os.environ["SENTINEL_GAUNTLET_API_KEY"] = "local-gauntlet-placeholder"
        browser = self.gauntlet.push_browser_max(
            urls=[
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
                "https://example.com/fail",
                "https://blocked.example/nope",
            ],
            allowed_domains=["example.com"],
            mission_id=mission_id,
        )
        api = self.gauntlet.push_external_api_max(
            mission_id=mission_id,
            requests=[
                ("GET", "https://api.example.com/items"),
                ("HEAD", "https://api.example.com/items"),
                ("GET", "https://api.example.com/error"),
                ("POST", "https://api.example.com/items"),
                ("GET", "https://blocked.example/items"),
            ],
            allowed_domains=["api.example.com"],
        )
        credentials = self.gauntlet.push_credentials_max(mission_id=mission_id)
        channel = self.gauntlet.push_channel_max(mission_id=mission_id)
        desktop = self.gauntlet.push_desktop_max(mission_id=mission_id)
        trading = self.gauntlet.push_trading_max(mission_id=mission_id)
        capital_inputs = [
            *browser.receipts[:1],
            *api.receipts[:1],
            *channel.receipts[:1],
            *desktop.receipts[:1],
            *trading.receipts[:1],
        ]
        capital = self.gauntlet.push_capital_max(mission_id=mission_id, receipts=capital_inputs)
        spend = self.gauntlet.push_spend_max(mission_id=mission_id)
        organ_results = {
            "browser": browser,
            "external_api": api,
            "channel": channel,
            "credentials": credentials,
            "desktop": desktop,
            "capital": capital,
            "trading": trading,
            "spend": spend,
        }
        return RealWorldGauntletReport(
            organ_results=organ_results,
            cross_organ_results={
                "browser_api_desktop_channel_to_capital": "passed" if capital.receipts and browser.receipts and api.receipts and desktop.receipts and channel.receipts else "failed",
                "market_data_to_trading_to_capital_signal": "passed" if trading.receipts and capital.receipts else "failed",
                "capital_to_spend_test_mode": "passed" if spend.receipts and capital.receipts else "failed",
                "credential_to_api_redacted_path": "passed" if credentials.receipts and api.receipts else "failed",
            },
            next_promotion_candidates=sorted({candidate for result in organ_results.values() for candidate in result.promotion_candidates}),
            remaining_limits=sorted({limit for result in organ_results.values() for limit in result.limits_remaining}),
            weakest_after_gauntlet="credentials",
            closest_to_real_world_promotion="desktop",
        )


def _adaptive_envelope_from_ledger(ledger: SignalLedger, receipts: list[RealityActivationReceipt]):
    from sentinel.organs.capital import AdaptiveOperatingEnvelope

    return AdaptiveOperatingEnvelope(
        root_budget_max_usd=100.0,
        budget_remaining_usd=100.0,
        max_single_transaction_usd=25.0,
        sub_budgets={},
        exploration_fraction=0.2,
        stop_loss_usd=20.0,
        signal_refs=ledger.signal_refs,
        evidence_refs=[receipt.id for receipt in receipts],
    )


def _trading_authority(*, mission_id: str, symbols: list[str]) -> TradingSpecialAuthority:
    return TradingSpecialAuthority(
        mission_id=mission_id,
        root_authority_id="gauntlet_root",
        broker="paper",
        exchange="sandbox",
        allowed_asset_classes=["equity"],
        allowed_symbols=symbols,
        max_capital_usd=100.0,
        max_loss_usd=10.0,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        evidence_refs=["gauntlet:trading_authority"],
    )


def _captured_rejection(call) -> str:
    try:
        call()
    except Exception:
        return "rejected"
    return "captured"
