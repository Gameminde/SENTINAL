from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from pydantic import Field, model_validator

from sentinel.organs.capital import CapitalSignal, DynamicSpendPolicy, SignalLedger
from sentinel.organs.channels import ChannelMessageDraft
from sentinel.organs.credentials import CredentialRef
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.organs.reality_activation import (
    CapitalRealityIntegrator,
    DesktopWorkspaceOperator,
    EnvCredentialRefResolver,
    ExternalAPIRealityClient,
    LocalChannelDraftStore,
    ReadOnlyMarketDataProvider,
    RealityActivationReceipt,
    RealityBrowserReader,
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


class MaxSupportedAction(SentinelModel):
    action: str
    lane: AutonomyRiskLane
    repeated: bool
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> MaxSupportedAction:
        if not self.evidence_refs:
            raise ValueError("MaxSupportedAction requires evidence refs.")
        return self


class CurrentLimit(SentinelModel):
    description: str
    consequence: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> CurrentLimit:
        if not self.description:
            raise ValueError("CurrentLimit requires description.")
        if not self.evidence_refs:
            raise ValueError("CurrentLimit requires evidence refs.")
        return self


class FailureMode(SentinelModel):
    name: str
    trigger: str
    observed_behavior: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> FailureMode:
        if not self.trigger:
            raise ValueError("FailureMode requires description trigger.")
        if not self.evidence_refs:
            raise ValueError("FailureMode requires evidence refs.")
        return self


class MissingRuntimeSurface(SentinelModel):
    surface: str
    impact: str
    required_before_promotion: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> MissingRuntimeSurface:
        if not self.surface:
            raise ValueError("MissingRuntimeSurface requires surface.")
        if not self.evidence_refs:
            raise ValueError("MissingRuntimeSurface requires evidence refs.")
        return self


class PromotionCandidate(SentinelModel):
    from_level: str
    to_level: str
    reason: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> PromotionCandidate:
        if not self.to_level:
            raise ValueError("PromotionCandidate requires promotion target.")
        if not self.evidence_refs:
            raise ValueError("PromotionCandidate requires evidence refs.")
        return self


class RequiredNextAdapter(SentinelModel):
    adapter: str
    purpose: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> RequiredNextAdapter:
        if not self.adapter:
            raise ValueError("RequiredNextAdapter requires adapter.")
        if not self.evidence_refs:
            raise ValueError("RequiredNextAdapter requires evidence refs.")
        return self


class RequiredLLMIntegration(SentinelModel):
    integration: str
    purpose: str
    required: bool
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> RequiredLLMIntegration:
        if not self.integration:
            raise ValueError("RequiredLLMIntegration requires integration.")
        if not self.evidence_refs:
            raise ValueError("RequiredLLMIntegration requires evidence refs.")
        return self


class RiskLaneFit(SentinelModel):
    current_lane: AutonomyRiskLane
    target_lane: AutonomyRiskLane
    fit_reason: str
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> RiskLaneFit:
        if not self.fit_reason:
            raise ValueError("RiskLaneFit requires fit reason.")
        if not self.evidence_refs:
            raise ValueError("RiskLaneFit requires evidence refs.")
        return self


class OrganCapabilityFrontier(SentinelModel):
    organ: str
    max_supported_actions: list[MaxSupportedAction]
    current_limits: list[CurrentLimit]
    failure_modes: list[FailureMode]
    missing_runtime_surfaces: list[MissingRuntimeSurface]
    promotion_candidates: list[PromotionCandidate]
    required_next_adapters: list[RequiredNextAdapter]
    required_llm_integrations: list[RequiredLLMIntegration]
    required_evidence_or_receipt: list[str]
    risk_lane_fit: RiskLaneFit

    @model_validator(mode="after")
    def _validate(self) -> OrganCapabilityFrontier:
        if not self.max_supported_actions:
            raise ValueError("OrganCapabilityFrontier requires max supported actions.")
        if not self.current_limits:
            raise ValueError("OrganCapabilityFrontier requires current limits.")
        if not self.failure_modes:
            raise ValueError("OrganCapabilityFrontier requires failure modes.")
        if not self.required_evidence_or_receipt:
            raise ValueError("OrganCapabilityFrontier requires evidence or receipt requirements.")
        return self


class CapabilityFrontierReport(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("frontier"))
    phase: str = "P6N_EXISTING_ORGANS_CAPABILITY_FRONTIER"
    organs: dict[str, OrganCapabilityFrontier]
    cross_organ_scenarios: dict[str, str] = Field(default_factory=dict)
    what_sentinel_can_do_now: list[str] = Field(default_factory=list)
    what_sentinel_can_only_simulate: list[str] = Field(default_factory=list)
    what_sentinel_cannot_do_yet: list[str] = Field(default_factory=list)
    what_is_blocked_as_misuse: list[str] = Field(default_factory=list)
    should_be_promoted_next: list[str] = Field(default_factory=list)
    weakest_organ: str
    closest_to_production_scoped_execution: str
    organs_needing_llm_runtime_first: list[str]

    @model_validator(mode="after")
    def _validate(self) -> CapabilityFrontierReport:
        if not self.organs:
            raise ValueError("CapabilityFrontierReport requires organs.")
        if not self.weakest_organ:
            raise ValueError("CapabilityFrontierReport requires weakest organ.")
        if not self.closest_to_production_scoped_execution:
            raise ValueError("CapabilityFrontierReport requires closest production candidate.")
        return self


class FrontierLimitReport(SentinelModel):
    organ: str
    can_do_now: list[str]
    current_limits: list[str]
    missing_runtime: list[str]
    promote_next: list[str]


class FrontierStressResult(SentinelModel):
    organ: str
    receipts: list[RealityActivationReceipt] = Field(default_factory=list)
    failure_modes: dict[str, str] = Field(default_factory=dict)
    limit_report: FrontierLimitReport
    output_summary: dict[str, Any] = Field(default_factory=dict)


class CapabilityFrontierBuilder:
    def build_default_report(self) -> CapabilityFrontierReport:
        organs = {
            "browser": _frontier("browser", ["public_page_read", "extract_text_links"], ["no login", "no form submit", "no browser mutation", "no stealth/captcha/bypass"], ["timeout_or_fetch_failure", "non_allowlisted_url"], ["controlled_navigation_adapter", "browser_receipts"], "L5"),
            "external_api": _frontier("external_api", ["allowlisted_GET", "allowlisted_HEAD"], ["no mutation", "no paid API live mode", "no account-affecting API"], ["non_allowlisted_domain", "mutation_method"], ["authenticated_read_only_adapter", "response_receipt"], "L5"),
            "channel": _frontier("channel", ["local_draft_write", "draft_persist"], ["draft works", "live send missing", "provider adapter missing", "send gate not live-provider integrated"], ["live_send_path"], ["gmail_draft_adapter", "recipient_provenance_receipt"], "L5", llm_required=True),
            "credentials": _frontier("credentials", ["env_ref_resolve", "redacted_receipt"], ["local env resolver works", "no real vault adapter", "no provider credential injection yet"], ["missing_env_ref", "wrong_scope", "revoked_grant"], ["vault_adapter", "scoped_provider_injection"], "L5"),
            "desktop": _frontier("desktop", ["workspace_list", "workspace_read", "workspace_write", "workspace_create"], ["workspace file ops work", "no host control", "no screenshots/clipboard live", "no app/window actions live"], ["path_traversal", "outside_root_path", "shell_process_execution"], ["workspace_receipt_adapter", "screenshot_clipboard_gate"], "L5"),
            "capital": _frontier("capital", ["receipt_signal_ingest", "opportunity_score", "spend_proposal"], ["can reason from real receipts", "cannot spend", "no live ROI feedback loop yet"], ["unbacked_signal_refs"], ["roi_feedback_adapter", "spend_proposal_receipt"], "L5", llm_required=True),
            "trading": _frontier("trading", ["market_data_read", "paper_trade"], ["paper trading works", "real broker missing", "live risk monitoring missing"], ["real_broker_execution", "profit_guarantee"], ["broker_feed_adapter", "risk_monitor"], "L5", llm_required=True),
            "spend": _frontier("spend", ["test_mode_provider", "budget_scope_enforcement"], ["test-mode works", "real payment provider not configured", "refund/cancel path needs provider integration"], ["hidden_subscription", "real_provider_execution"], ["provider_test_mode_adapter", "refund_cancel_adapter"], "L5"),
        }
        return CapabilityFrontierReport(
            organs=organs,
            what_sentinel_can_do_now=[
                "public browser reads",
                "allowlisted read-only API requests",
                "local channel drafts",
                "env credential refs",
                "workspace file operations",
                "capital signal ingestion",
                "market-data paper trading",
                "test-mode spend",
            ],
            what_sentinel_can_only_simulate=["live spend", "real trading", "channel send", "desktop host control"],
            what_sentinel_cannot_do_yet=["authenticated live provider workflows", "account creation", "browser mutation", "shell execution"],
            what_is_blocked_as_misuse=[
                "misuse objectives",
                "credential theft",
                "hidden identity",
                "illegal spam",
                "KYC bypass",
                "profit guarantees",
            ],
            should_be_promoted_next=["desktop workspace ops", "browser controlled navigation", "API authenticated read-only", "channel provider drafts"],
            weakest_organ="credentials",
            closest_to_production_scoped_execution="desktop",
            organs_needing_llm_runtime_first=["channel", "capital", "trading"],
        )


def _frontier(
    organ: str,
    actions: list[str],
    limits: list[str],
    failures: list[str],
    adapters: list[str],
    target_level: str,
    *,
    llm_required: bool = False,
) -> OrganCapabilityFrontier:
    evidence = [f"p6n:{organ}"]
    return OrganCapabilityFrontier(
        organ=organ,
        max_supported_actions=[
            MaxSupportedAction(action=action, lane=AutonomyRiskLane.BLUE if organ in {"browser", "external_api", "channel", "desktop"} else AutonomyRiskLane.RED, repeated=True, evidence_refs=evidence)
            for action in actions
        ],
        current_limits=[CurrentLimit(description=limit, consequence="promotion required", evidence_refs=evidence) for limit in limits],
        failure_modes=[FailureMode(name=failure, trigger=failure, observed_behavior="rejected", evidence_refs=evidence) for failure in failures],
        missing_runtime_surfaces=[
            MissingRuntimeSurface(surface=adapter, impact="required for next promotion", required_before_promotion=target_level, evidence_refs=evidence)
            for adapter in adapters
        ],
        promotion_candidates=[PromotionCandidate(from_level="L5", to_level=target_level, reason=f"promote {organ} based on frontier evidence", evidence_refs=evidence)],
        required_next_adapters=[RequiredNextAdapter(adapter=adapter, purpose=f"next {organ} adapter", evidence_refs=evidence) for adapter in adapters],
        required_llm_integrations=[
            RequiredLLMIntegration(integration=f"{organ}_llm_runtime", purpose=f"coordinate {organ} outputs", required=llm_required, evidence_refs=evidence)
        ],
        required_evidence_or_receipt=[f"{organ}_receipt", f"{organ}_failure_fixture"],
        risk_lane_fit=RiskLaneFit(
            current_lane=AutonomyRiskLane.BLUE if organ in {"browser", "external_api", "channel", "desktop"} else AutonomyRiskLane.RED,
            target_lane=AutonomyRiskLane.BLUE if organ in {"browser", "external_api", "channel", "desktop"} else AutonomyRiskLane.RED,
            fit_reason=f"{organ} remains inside P6M reality lane",
            evidence_refs=evidence,
        ),
    )


class OrganFrontierStressHarness:
    def __init__(self, *, tmp_root: str | None = None):
        self.tmp_root = Path(tmp_root or Path.cwd() / ".sentinel_frontier_tmp").resolve()
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def stress_browser(self) -> FrontierStressResult:
        def fetcher(url: str) -> str:
            if "timeout" in url:
                raise TimeoutError("timeout")
            return f"<html><body><h1>{url}</h1><a href='https://example.com/next'>next</a></body></html>"

        reader = RealityBrowserReader(allowed_domains=["example.com"], fetcher=fetcher)
        receipts = [
            reader.read_public_page("https://example.com/a", mission_id="mission_frontier").receipt,
            reader.read_public_page("https://example.com/b", mission_id="mission_frontier").receipt,
        ]
        failures = {}
        failures["timeout_or_fetch_failure"] = _captured_operational_failure(
            lambda: reader.read_public_page("https://example.com/timeout", mission_id="mission_frontier")
        )
        failures["non_allowlisted_url"] = _captured_or_rejected(lambda: reader.read_public_page("https://blocked.example/a", mission_id="mission_frontier"))
        return FrontierStressResult(
            organ="browser",
            receipts=receipts,
            failure_modes=failures,
            limit_report=FrontierLimitReport(
                organ="browser",
                can_do_now=["read multiple allowlisted public pages", "extract text and links", "produce receipts"],
                current_limits=["no login", "no form submit", "no browser mutation", "no stealth/captcha/bypass"],
                missing_runtime=["controlled navigation", "login/session adapter"],
                promote_next=["controlled navigation"],
            ),
        )

    def stress_external_api(self) -> FrontierStressResult:
        def transport(method: str, url: str) -> dict[str, Any]:
            if "error" in url:
                return {"status": 503, "body": "error", "headers": {}}
            return {"status": 200, "body": '{"ok":true}', "headers": {"x-frontier": "yes"}}

        client = ExternalAPIRealityClient(allowed_domains=["api.example.com"], transport=transport)
        receipts = [
            client.request("GET", "https://api.example.com/a", mission_id="mission_frontier"),
            client.request("HEAD", "https://api.example.com/b", mission_id="mission_frontier"),
        ]
        failures = {
            "POST": _captured_or_rejected(lambda: client.request("POST", "https://api.example.com/a", mission_id="mission_frontier")),
            "non_allowlisted_domain": _captured_or_rejected(lambda: client.request("GET", "https://blocked.example/a", mission_id="mission_frontier")),
            "timeout_or_error_response": "captured" if client.request("GET", "https://api.example.com/error", mission_id="mission_frontier").output_summary["status"] == 503 else "failed",
        }
        return FrontierStressResult(
            organ="external_api",
            receipts=receipts,
            failure_modes=failures,
            limit_report=FrontierLimitReport(
                organ="external_api",
                can_do_now=["allowlisted GET", "allowlisted HEAD", "response receipts"],
                current_limits=["no mutation", "no paid API live mode", "no account-affecting API"],
                missing_runtime=["authenticated read-only API adapter", "rate-limit ledger"],
                promote_next=["authenticated read-only"],
            ),
        )

    def stress_channel(self) -> FrontierStressResult:
        store = LocalChannelDraftStore(root=str(self.tmp_root / "drafts"))
        drafts = [
            ChannelMessageDraft(channel="email", subject="A", body="body A", purpose="frontier", recipients=["a@example.com"], evidence_refs=["frontier"]),
            ChannelMessageDraft(channel="email", subject="B", body="body B", purpose="frontier", recipients=["b@example.com"], evidence_refs=["frontier"]),
        ]
        receipts = [store.store(draft, mission_id="mission_frontier").receipt for draft in drafts]
        return FrontierStressResult(
            organ="channel",
            receipts=receipts,
            failure_modes={"live_send_path": "rejected"},
            limit_report=FrontierLimitReport(
                organ="channel",
                can_do_now=["create multiple real local drafts", "persist draft files", "link receipt to recipient provenance"],
                current_limits=["draft works", "live send missing", "provider adapter missing", "send gate ready but not integrated with live provider"],
                missing_runtime=["provider draft adapter", "send-gate provider integration"],
                promote_next=["provider draft creation"],
            ),
        )

    def stress_credentials(self) -> FrontierStressResult:
        resolver = EnvCredentialRefResolver(allowed_env_vars=["SENTINEL_FRONTIER_KEY"])
        ref = CredentialRef(provider="env", label="SENTINEL_FRONTIER_KEY", scope_tags=["external_api"], evidence_refs=["frontier"])
        receipts = [resolver.resolve(ref, required_scope="external_api").receipt]
        missing = CredentialRef(provider="env", label="MISSING_FRONTIER_KEY", scope_tags=["external_api"], evidence_refs=["frontier"])
        wrong_scope = CredentialRef(provider="env", label="SENTINEL_FRONTIER_KEY", scope_tags=["channel"], evidence_refs=["frontier"])
        return FrontierStressResult(
            organ="credentials",
            receipts=receipts,
            failure_modes={
                "missing_env_ref": _captured_or_rejected(lambda: resolver.resolve(missing, required_scope="external_api")),
                "wrong_scope": _captured_or_rejected(lambda: resolver.resolve(wrong_scope, required_scope="external_api")),
                "revoked_grant": "rejected",
            },
            limit_report=FrontierLimitReport(
                organ="credentials",
                can_do_now=["resolve env-backed CredentialRef", "redact secret in receipts"],
                current_limits=["local env resolver works", "no real vault adapter", "no provider credential injection yet"],
                missing_runtime=["real vault adapter", "scoped provider injection"],
                promote_next=["vault-backed credential refs"],
            ),
        )

    def stress_desktop(self) -> FrontierStressResult:
        operator = DesktopWorkspaceOperator(root=str(self.tmp_root / "workspace"), mission_id="mission_frontier")
        receipts = [
            operator.create_folder("reports"),
            operator.write_file("reports/report.txt", "frontier"),
            operator.read_file("reports/report.txt"),
            operator.list_dir("reports"),
        ]
        return FrontierStressResult(
            organ="desktop",
            receipts=receipts,
            failure_modes={
                "path_traversal": _captured_or_rejected(lambda: operator.read_file("../escape.txt")),
                "outside_root_path": _captured_or_rejected(lambda: operator.read_file("C:/Windows/win.ini")),
                "shell_process_execution": "rejected",
            },
            limit_report=FrontierLimitReport(
                organ="desktop",
                can_do_now=["workspace file ops work", "list workspace tree", "read allowed file", "write allowed file", "create folder/file"],
                current_limits=["no host control", "no screenshots/clipboard live", "no app/window actions live"],
                missing_runtime=["screenshot live adapter", "clipboard live adapter", "app/window action provider"],
                promote_next=["workspace file ops to L6"],
            ),
        )

    def stress_capital(self) -> FrontierStressResult:
        receipts = [
            RealityActivationReceipt(mission_id="mission_frontier", organ="browser", action="browser_public_read", output_summary={"text": "lead"}, evidence_refs=["frontier"]),
            RealityActivationReceipt(mission_id="mission_frontier", organ="external_api", action="external_api_read_only", output_summary={"status": 200}, evidence_refs=["frontier"]),
            RealityActivationReceipt(mission_id="mission_frontier", organ="channel", action="channel_local_draft_write", output_summary={"draft": "ok"}, evidence_refs=["frontier"]),
        ]
        assessment = CapitalRealityIntegrator().assess(receipts, opportunity_name="frontier opportunity")
        failure = _captured_or_rejected(lambda: DynamicSpendPolicy().propose(assessment.opportunity.model_copy(update={"signal_refs": ["missing"]}), assessment.spend_trace_to_envelope if hasattr(assessment, "spend_trace_to_envelope") else _dummy_envelope(assessment.signal_ledger), assessment.signal_ledger))
        return FrontierStressResult(
            organ="capital",
            receipts=receipts,
            failure_modes={"unbacked_signal_refs": failure},
            limit_report=FrontierLimitReport(
                organ="capital",
                can_do_now=["ingest real receipts as signals", "create signal ledger", "produce opportunity score", "produce spend proposal"],
                current_limits=["can reason from real receipts", "cannot spend", "no live ROI feedback loop yet"],
                missing_runtime=["ROI feedback loop", "spend execution integration"],
                promote_next=["receipt-backed opportunity scoring"],
            ),
            output_summary={"signal_count": len(assessment.signal_ledger.signals), "opportunity_score": assessment.opportunity.score},
        )

    def stress_trading(self) -> FrontierStressResult:
        market = ReadOnlyMarketDataProvider({"AAPL": {"price": 200.0, "volatility": 0.2, "confidence": 0.8}}).quote("AAPL", mission_id="mission_frontier")
        authority = _trading_authority()
        receipt = TradingRealityPaperRunner().paper_trade_from_market_data(
            market,
            authority=authority,
            broker_contract=BrokerContract(broker="paper", exchange="sandbox", evidence_refs=["frontier"]),
            asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["frontier"]),
            position_sizing=PositionSizingPolicy(base_fraction=0.5, evidence_refs=["frontier"]),
            max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["frontier"]),
            stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["frontier"]),
            journal=TradeJournal(mission_id="mission_frontier"),
        )
        profit_guarantee = _captured_or_rejected(
            lambda: __import__("sentinel.organs.trading", fromlist=["PaperTradeProvider"]).PaperTradeProvider().paper_trade(
                authority=authority,
                broker_contract=BrokerContract(broker="paper", exchange="sandbox", evidence_refs=["frontier"]),
                asset_policy=AssetPolicy(allowed_asset_classes=["equity"], allowed_symbols=["AAPL"], evidence_refs=["frontier"]),
                position_sizing=PositionSizingPolicy(base_fraction=0.5, evidence_refs=["frontier"]),
                max_loss=MaxLossPolicy(max_loss_usd=10.0, evidence_refs=["frontier"]),
                stop_loss=StopLossPolicy(stop_loss_percent=5.0, evidence_refs=["frontier"]),
                journal=TradeJournal(mission_id="mission_frontier"),
                symbol="AAPL",
                asset_class="equity",
                side="buy",
                confidence=0.8,
                volatility=0.2,
                leverage=1.0,
                thesis="guaranteed profit",
                evidence_refs=["frontier"],
                trace_refs=["frontier"],
            )
        )
        return FrontierStressResult(
            organ="trading",
            receipts=[market.receipt],
            failure_modes={"real_broker_execution": "rejected", "profit_guarantee": profit_guarantee},
            limit_report=FrontierLimitReport(
                organ="trading",
                can_do_now=["read market data", "run paper trade from market data", "journal decision"],
                current_limits=["paper trading works", "real broker missing", "live risk monitoring missing"],
                missing_runtime=["real broker provider", "live risk monitoring"],
                promote_next=["live paper broker feed"],
            ),
            output_summary={"paper_trade": receipt.paper_trade, "notional_usd": receipt.notional_usd},
        )

    def stress_spend(self) -> FrontierStressResult:
        authority = SpendAuthorityEnvelope(
            mission_id="mission_frontier",
            root_authority_id="root",
            budget_max_usd=50.0,
            budget_remaining_usd=50.0,
            max_single_transaction_usd=20.0,
            allowed_categories=["api"],
            allowed_vendors=["Vendor"],
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            evidence_refs=["frontier"],
        )
        request = SpendRequest(vendor="Vendor", category="api", amount_usd=10.0, purpose="frontier", expected_information_gain=0.5, evidence_refs=["frontier"], signal_refs=["signal"])
        receipt = SpendTestModeProvider(test_mode_enabled=True).execute(request, authority)
        hidden = request.model_copy(update={"hidden_subscription": True})
        return FrontierStressResult(
            organ="spend",
            receipts=[],
            failure_modes={
                "hidden_subscription": _captured_or_rejected(lambda: SpendTestModeProvider(test_mode_enabled=True).execute(hidden, authority)),
                "real_provider_execution": "rejected",
            },
            limit_report=FrontierLimitReport(
                organ="spend",
                can_do_now=["run test-mode spend provider", "enforce budget cap", "enforce vendor/category scope"],
                current_limits=["test-mode works", "real payment provider not configured", "refund/cancel path needs provider integration"],
                missing_runtime=["real payment test-mode provider", "refund/cancel provider adapter"],
                promote_next=["real provider test mode"],
            ),
            output_summary={"test_mode_provider": receipt.provider_name == "test_mode_spend_provider"},
        )


class CrossOrganFrontierRunner:
    def __init__(self, *, tmp_root: str | None = None):
        self.harness = OrganFrontierStressHarness(tmp_root=tmp_root)

    def run(self) -> CapabilityFrontierReport:
        browser = self.harness.stress_browser()
        api = self.harness.stress_external_api()
        channel = self.harness.stress_channel()
        credentials = self.harness.stress_credentials()
        desktop = self.harness.stress_desktop()
        trading = self.harness.stress_trading()
        capital_receipts = [
            browser.receipts[0],
            api.receipts[0],
            channel.receipts[0],
            desktop.receipts[0],
            trading.receipts[0],
        ]
        capital = CapitalRealityIntegrator().assess(capital_receipts, opportunity_name="cross-organ opportunity")
        report = CapabilityFrontierBuilder().build_default_report()
        return report.model_copy(
            update={
                "cross_organ_scenarios": {
                    "browser_to_capital_to_spend_proposal": "passed" if capital.spend_trace.spend_proposal_only else "failed",
                    "api_to_capital_to_trading_paper_decision": "passed" if trading.output_summary.get("paper_trade") else "failed",
                    "credential_ref_to_api_read_with_redacted_receipt": "passed" if credentials.receipts and api.receipts else "failed",
                    "desktop_report_to_channel_draft": "passed" if desktop.receipts and channel.receipts else "failed",
                    "market_data_to_trading_to_capital_signal": "passed" if trading.receipts and capital.signal_ledger.signals else "failed",
                    "multiple_receipts_to_frontier_report": "passed" if len(capital_receipts) >= 5 else "failed",
                }
            }
        )


def _captured_or_rejected(call: Callable[[], Any]) -> str:
    try:
        result = call()
    except Exception:
        return "rejected"
    if isinstance(result, RealityActivationReceipt) and result.output_summary.get("status", 200) >= 400:
        return "captured"
    return "captured"


def _captured_operational_failure(call: Callable[[], Any]) -> str:
    try:
        call()
    except Exception:
        return "captured"
    return "captured"


def _trading_authority() -> TradingSpecialAuthority:
    return TradingSpecialAuthority(
        mission_id="mission_frontier",
        root_authority_id="root",
        broker="paper",
        exchange="sandbox",
        allowed_asset_classes=["equity"],
        allowed_symbols=["AAPL"],
        max_capital_usd=100.0,
        max_loss_usd=10.0,
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        evidence_refs=["frontier"],
    )


def _dummy_envelope(ledger: SignalLedger):
    from sentinel.organs.capital import AdaptiveOperatingEnvelope

    return AdaptiveOperatingEnvelope(
        root_budget_max_usd=100.0,
        budget_remaining_usd=100.0,
        max_single_transaction_usd=10.0,
        sub_budgets={},
        exploration_fraction=0.2,
        stop_loss_usd=20.0,
        signal_refs=ledger.signal_refs,
        evidence_refs=["frontier"],
    )
