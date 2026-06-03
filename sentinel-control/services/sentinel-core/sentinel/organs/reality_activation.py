from __future__ import annotations

import hashlib
import html.parser
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import Field, model_validator

from sentinel.organs.capital import (
    AdaptiveOperatingEnvelope,
    CapitalOpportunity,
    CapitalSignal,
    DynamicSpendPolicy,
    OpportunityPortfolio,
    SignalLedger,
    SpendDecisionTrace,
)
from sentinel.organs.channels import ChannelMessageDraft
from sentinel.organs.credentials import CredentialRef
from sentinel.organs.spend import (
    FakeSpendProvider,
    RefundCancelPath,
    SpendAuthorityEnvelope,
    SpendKillSwitch,
    SpendReceipt,
    SpendRequest,
    SubscriptionGuard,
)
from sentinel.organs.trading import (
    AssetPolicy,
    BrokerContract,
    MaxLossPolicy,
    PaperTradeProvider,
    PositionSizingPolicy,
    StopLossPolicy,
    TradeJournal,
    TradingReceipt,
    TradingSpecialAuthority,
)
from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RealityActivationReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("realrcpt"))
    mission_id: str
    organ: str
    action: str
    output_summary: dict[str, Any]
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    real_action: bool = True
    external_mutation: bool = False
    authority_expansion: bool = False
    receipt_hash: str = ""

    @model_validator(mode="after")
    def _validate(self) -> RealityActivationReceipt:
        if not self.evidence_refs:
            raise ValueError("RealityActivationReceipt requires evidence refs.")
        if self.external_mutation:
            raise ValueError("P6M reality activation cannot perform external mutation.")
        if self.authority_expansion:
            raise ValueError("RealityActivationReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("RealityActivationReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "organ": self.organ,
                "action": self.action,
                "output_summary": self.output_summary,
                "evidence_refs": self.evidence_refs,
                "trace_refs": self.trace_refs,
                "real_action": self.real_action,
            }
        )


class _TextAndLinksParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.links: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


class BrowserRealityReadResult(SentinelModel):
    url: str
    text: str
    links: list[str]
    receipt: RealityActivationReceipt


class RealityBrowserReader:
    def __init__(self, *, allowed_domains: list[str], fetcher: Callable[[str], str] | None = None, timeout_seconds: float = 10.0):
        self.allowed_domains = set(allowed_domains)
        self.fetcher = fetcher
        self.timeout_seconds = timeout_seconds

    def read_public_page(self, url: str, *, mission_id: str) -> BrowserRealityReadResult:
        domain = urlparse(url).hostname or ""
        if domain not in self.allowed_domains:
            raise ValueError(f"domain not allowlisted:{domain}")
        html_text = self.fetcher(url) if self.fetcher else self._fetch(url)
        parser = _TextAndLinksParser()
        parser.feed(html_text)
        text = " ".join(parser.text_parts)
        receipt = RealityActivationReceipt(
            mission_id=mission_id,
            organ="browser",
            action="browser_public_read",
            output_summary={"url": url, "domain": domain, "text_length": len(text), "link_count": len(parser.links)},
            evidence_refs=[f"browser:{url}"],
        )
        return BrowserRealityReadResult(url=url, text=text, links=parser.links, receipt=receipt)

    def _fetch(self, url: str) -> str:
        request = Request(url, method="GET", headers={"User-Agent": "SentinelRealityActivation/0.1"})
        with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310 - allowlisted read-only URL.
            return response.read().decode("utf-8", errors="replace")


class ExternalAPIRealityClient:
    def __init__(self, *, allowed_domains: list[str], transport: Callable[[str, str], dict[str, Any]] | None = None, timeout_seconds: float = 10.0):
        self.allowed_domains = set(allowed_domains)
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def request(self, method: str, url: str, *, mission_id: str) -> RealityActivationReceipt:
        method = method.upper()
        if method not in {"GET", "HEAD"}:
            raise ValueError("external API reality activation is read-only")
        domain = urlparse(url).hostname or ""
        if domain not in self.allowed_domains:
            raise ValueError(f"domain not allowlisted:{domain}")
        result = self.transport(method, url) if self.transport else self._request(method, url)
        return RealityActivationReceipt(
            mission_id=mission_id,
            organ="external_api",
            action="external_api_read_only",
            output_summary={
                "method": method,
                "url": url,
                "domain": domain,
                "status": result.get("status"),
                "body_length": len(str(result.get("body", ""))),
                "headers": result.get("headers", {}),
            },
            evidence_refs=[f"api:{method}:{url}"],
        )

    def _request(self, method: str, url: str) -> dict[str, Any]:
        request = Request(url, method=method, headers={"User-Agent": "SentinelRealityActivation/0.1"})
        with urlopen(request, timeout=self.timeout_seconds) as response:  # nosec B310 - allowlisted read-only URL.
            body = "" if method == "HEAD" else response.read().decode("utf-8", errors="replace")
            return {"status": response.status, "body": body, "headers": dict(response.headers.items())}


class StoredChannelDraft(SentinelModel):
    filename: str
    path: str
    receipt: RealityActivationReceipt


class LocalChannelDraftStore:
    def __init__(self, *, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, draft: ChannelMessageDraft, *, mission_id: str) -> StoredChannelDraft:
        filename = f"{draft.id}.json"
        path = (self.root / filename).resolve()
        if not _is_within_root(path, self.root):
            raise ValueError("draft store path escape")
        payload = draft.model_dump(mode="json")
        path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        receipt = RealityActivationReceipt(
            mission_id=mission_id,
            organ="channel",
            action="channel_local_draft_write",
            output_summary={"filename": filename, "path": str(path), "channel": draft.channel, "send_attempted": False},
            evidence_refs=draft.evidence_refs,
        )
        return StoredChannelDraft(filename=filename, path=str(path), receipt=receipt)


class ResolvedCredential(SentinelModel):
    credential_ref_id: str
    secret_value: str = Field(repr=False)
    receipt: RealityActivationReceipt


class EnvCredentialRefResolver:
    def __init__(self, *, allowed_env_vars: list[str]):
        self.allowed_env_vars = set(allowed_env_vars)

    def resolve(self, ref: CredentialRef, *, required_scope: str) -> ResolvedCredential:
        if ref.provider != "env":
            raise ValueError("only env credential refs are supported in P6M")
        if required_scope not in ref.scope_tags:
            raise ValueError(f"credential scope not allowed:{required_scope}")
        if ref.label not in self.allowed_env_vars:
            raise ValueError(f"env var not allowlisted:{ref.label}")
        value = os.environ.get(ref.label)
        if value is None:
            raise ValueError(f"env var missing:{ref.label}")
        receipt = RealityActivationReceipt(
            mission_id="credential_resolution",
            organ="credentials",
            action="credential_env_ref_resolved",
            output_summary={"credential_ref_id": ref.id, "provider": ref.provider, "label": ref.label, "secret_value": "[REDACTED]"},
            evidence_refs=ref.evidence_refs,
            real_action=True,
        )
        return ResolvedCredential(credential_ref_id=ref.id, secret_value=value, receipt=receipt)


class DesktopWorkspaceOperator:
    def __init__(self, *, root: str, mission_id: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.mission_id = mission_id

    def list_dir(self, relative_path: str = ".") -> RealityActivationReceipt:
        path = self._resolve(relative_path)
        entries = sorted(item.name for item in path.iterdir())
        return self._receipt("desktop_workspace_list_dir", {"path": str(path), "entries": entries})

    def read_file(self, relative_path: str) -> RealityActivationReceipt:
        path = self._resolve(relative_path)
        content = path.read_text(encoding="utf-8")
        return self._receipt(
            "desktop_workspace_read_file",
            {
                "path": str(path),
                "bytes": len(content.encode("utf-8")),
                "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            },
        )

    def write_file(self, relative_path: str, content: str) -> RealityActivationReceipt:
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return self._receipt("desktop_workspace_write_file", {"path": str(path), "bytes": len(content.encode("utf-8"))})

    def create_folder(self, relative_path: str) -> RealityActivationReceipt:
        path = self._resolve(relative_path)
        path.mkdir(parents=True, exist_ok=True)
        return self._receipt("desktop_workspace_create_folder", {"path": str(path)})

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if not _is_within_root(candidate, self.root):
            raise ValueError("workspace escape blocked")
        return candidate

    def _receipt(self, action: str, output_summary: dict[str, Any]) -> RealityActivationReceipt:
        return RealityActivationReceipt(
            mission_id=self.mission_id,
            organ="desktop",
            action=action,
            output_summary=output_summary,
            evidence_refs=[f"desktop:{action}"],
        )


class CapitalRealityAssessment(SentinelModel):
    signal_ledger: SignalLedger
    opportunity: CapitalOpportunity
    spend_trace: SpendDecisionTrace


class CapitalRealityIntegrator:
    def assess(self, receipts: list[RealityActivationReceipt], *, opportunity_name: str) -> CapitalRealityAssessment:
        if not receipts:
            raise ValueError("capital reality assessment requires receipts")
        ledger = SignalLedger()
        for receipt in receipts:
            signal = CapitalSignal(
                signal_type=receipt.organ,
                source=receipt.action,
                strength=0.5 if receipt.real_action else 0.0,
                summary=f"{receipt.organ}:{receipt.action}",
                evidence_refs=[receipt.id, *receipt.evidence_refs],
                trace_refs=receipt.trace_refs,
            )
            ledger = ledger.record(signal)
        opportunity = CapitalOpportunity(
            name=opportunity_name,
            category="reality_evidence",
            expected_profit_or_progress=100.0,
            expected_information_gain=min(1.0, 0.2 * len(receipts)),
            downside_risk=0.2,
            proposed_spend_usd=10.0,
            confidence=min(1.0, 0.25 * len(receipts)),
            evidence_refs=[receipt.id for receipt in receipts],
            signal_refs=ledger.signal_refs,
            objective_text=opportunity_name,
        )
        envelope = AdaptiveOperatingEnvelope(
            root_budget_max_usd=100.0,
            budget_remaining_usd=100.0,
            max_single_transaction_usd=10.0,
            sub_budgets={},
            exploration_fraction=0.2,
            stop_loss_usd=20.0,
            signal_refs=ledger.signal_refs,
            evidence_refs=[receipt.id for receipt in receipts],
        )
        spend_trace = DynamicSpendPolicy().propose(opportunity, envelope, ledger)
        return CapitalRealityAssessment(signal_ledger=ledger, opportunity=opportunity, spend_trace=spend_trace)


class MarketDataReceipt(SentinelModel):
    mission_id: str
    symbol: str
    price: float = Field(gt=0.0)
    volatility: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    receipt: RealityActivationReceipt


class ReadOnlyMarketDataProvider:
    def __init__(self, quotes: dict[str, dict[str, float]]):
        self.quotes = quotes

    def quote(self, symbol: str, *, mission_id: str) -> MarketDataReceipt:
        if symbol not in self.quotes:
            raise ValueError(f"market data missing:{symbol}")
        quote = self.quotes[symbol]
        receipt = RealityActivationReceipt(
            mission_id=mission_id,
            organ="trading",
            action="market_data_read_only",
            output_summary={"symbol": symbol, "price": quote["price"], "volatility": quote["volatility"], "confidence": quote["confidence"]},
            evidence_refs=[f"market_data:{symbol}"],
        )
        return MarketDataReceipt(mission_id=mission_id, symbol=symbol, price=quote["price"], volatility=quote["volatility"], confidence=quote["confidence"], receipt=receipt)


class TradingRealityPaperRunner:
    def paper_trade_from_market_data(
        self,
        market_data: MarketDataReceipt,
        *,
        authority: TradingSpecialAuthority,
        broker_contract: BrokerContract,
        asset_policy: AssetPolicy,
        position_sizing: PositionSizingPolicy,
        max_loss: MaxLossPolicy,
        stop_loss: StopLossPolicy,
        journal: TradeJournal,
    ) -> TradingReceipt:
        return PaperTradeProvider().paper_trade(
            authority=authority,
            broker_contract=broker_contract,
            asset_policy=asset_policy,
            position_sizing=position_sizing,
            max_loss=max_loss,
            stop_loss=stop_loss,
            journal=journal,
            symbol=market_data.symbol,
            asset_class=authority.allowed_asset_classes[0],
            side="buy",
            confidence=market_data.confidence,
            volatility=market_data.volatility,
            leverage=1.0,
            thesis="paper trade from read-only market data",
            evidence_refs=[market_data.receipt.id, *market_data.receipt.evidence_refs],
            trace_refs=[market_data.receipt.id],
        )


class SpendTestModeProvider:
    def __init__(self, *, test_mode_enabled: bool):
        self.test_mode_enabled = test_mode_enabled

    def execute(self, request: SpendRequest, authority: SpendAuthorityEnvelope) -> SpendReceipt:
        if not self.test_mode_enabled:
            raise ValueError("test mode provider disabled")
        receipt = FakeSpendProvider().execute(
            request,
            authority,
            kill_switch=SpendKillSwitch(mission_id=authority.mission_id),
            subscription_guard=SubscriptionGuard(),
            refund_cancel_path=RefundCancelPath(steps=["test_mode_no_real_charge"], evidence_refs=["test_mode"]),
            trace_refs=["test_mode_spend_trace"],
        )
        return receipt.model_copy(update={"provider_name": "test_mode_spend_provider"})


def _is_within_root(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True
