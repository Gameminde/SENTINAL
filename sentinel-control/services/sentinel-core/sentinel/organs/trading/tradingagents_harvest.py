from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


class TradingDecisionRating(StrEnum):
    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


class TradingRolePurpose(StrEnum):
    MARKET_TECHNICAL_ANALYSIS = "market_technical_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    NEWS_MACRO_ANALYSIS = "news_macro_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    BULL_THESIS = "bull_thesis"
    BEAR_THESIS = "bear_thesis"
    RESEARCH_SYNTHESIS = "research_synthesis"
    TRANSACTION_PROPOSAL = "transaction_proposal"
    AGGRESSIVE_RISK = "aggressive_risk"
    NEUTRAL_RISK = "neutral_risk"
    CONSERVATIVE_RISK = "conservative_risk"
    PORTFOLIO_FINAL_DECISION = "portfolio_final_decision"


ANALYST_ROLE_PURPOSES: dict[str, TradingRolePurpose] = {
    "market": TradingRolePurpose.MARKET_TECHNICAL_ANALYSIS,
    "social": TradingRolePurpose.SENTIMENT_ANALYSIS,
    "news": TradingRolePurpose.NEWS_MACRO_ANALYSIS,
    "fundamentals": TradingRolePurpose.FUNDAMENTAL_ANALYSIS,
}

TRADINGAGENTS_ALLOWED_VENDORS = {"alpha_vantage", "yfinance"}
TRADINGAGENTS_METHOD_CATEGORIES: dict[str, str] = {
    "get_stock_data": "core_stock_apis",
    "get_indicators": "technical_indicators",
    "get_fundamentals": "fundamental_data",
    "get_balance_sheet": "fundamental_data",
    "get_cashflow": "fundamental_data",
    "get_income_statement": "fundamental_data",
    "get_news": "news_data",
    "get_global_news": "news_data",
    "get_insider_transactions": "news_data",
}


class TradingAgentsRoleAssignment(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("trole"))
    role: str
    purpose: TradingRolePurpose
    mission_id: str
    symbol: str
    evidence_refs: list[str]
    source_refs: list[str]
    allowed_tools: list[str] = Field(default_factory=list)
    output_contract: str

    @model_validator(mode="after")
    def _validate(self) -> TradingAgentsRoleAssignment:
        if not self.evidence_refs:
            raise ValueError("TradingAgentsRoleAssignment requires evidence refs.")
        if not self.source_refs:
            raise ValueError("TradingAgentsRoleAssignment requires source refs.")
        return self


class TradingAgentsFirmPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tfirm"))
    mission_id: str
    symbol: str
    role_assignments: list[TradingAgentsRoleAssignment]
    selected_analysts: list[str]
    max_debate_rounds: int = Field(ge=1)
    max_risk_discuss_rounds: int = Field(ge=1)
    structured_decision_required: bool = True
    checkpoint_resume_planned: bool = True
    paper_only: bool = True
    real_trade_started: bool = False
    vendor_runtime_bridge: bool = False
    vendor_code_copied: bool = False
    authority_expansion: bool = False
    evidence_refs: list[str]
    source_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> TradingAgentsFirmPlan:
        if not self.role_assignments:
            raise ValueError("TradingAgentsFirmPlan requires role assignments.")
        if not self.evidence_refs:
            raise ValueError("TradingAgentsFirmPlan requires evidence refs.")
        if not self.source_refs:
            raise ValueError("TradingAgentsFirmPlan requires source refs.")
        if self.real_trade_started:
            raise ValueError("TradingAgentsFirmPlan cannot start real trading.")
        if self.vendor_runtime_bridge:
            raise ValueError("TradingAgentsFirmPlan cannot bridge vendor runtime.")
        if self.vendor_code_copied:
            raise ValueError("TradingAgentsFirmPlan cannot copy vendor code.")
        if self.authority_expansion:
            raise ValueError("TradingAgentsFirmPlan cannot expand authority.")
        return self


class TradingAgentsSignalParser:
    _ratings = {rating.value.lower(): rating for rating in TradingDecisionRating}

    def parse_rating(self, text: str, default: TradingDecisionRating = TradingDecisionRating.HOLD) -> TradingDecisionRating:
        for line in text.splitlines():
            lowered = line.lower()
            if "rating" not in lowered:
                continue
            for token in lowered.replace("**", "").replace(":", " ").replace("-", " ").split():
                if token in self._ratings:
                    return self._ratings[token]

        for token in text.lower().replace("**", "").replace(":", " ").replace("-", " ").split():
            clean = token.strip(".,;")
            if clean in self._ratings:
                return self._ratings[clean]
        return default


class TradingAgentsDataVendorRoute(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tvendor"))
    method: str
    category: str
    primary_vendor: str
    fallback_vendors: list[str]
    dry_run_only: bool = True
    live_api_called: bool = False
    credential_ref: str | None = None
    raw_credential: str | None = None
    evidence_refs: list[str]
    source_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> TradingAgentsDataVendorRoute:
        if self.method not in TRADINGAGENTS_METHOD_CATEGORIES:
            raise ValueError(f"method_not_supported:{self.method}")
        if self.category != TRADINGAGENTS_METHOD_CATEGORIES[self.method]:
            raise ValueError(f"category_mismatch:{self.method}:{self.category}")
        vendors = [self.primary_vendor, *self.fallback_vendors]
        unknown = [vendor for vendor in vendors if vendor not in TRADINGAGENTS_ALLOWED_VENDORS]
        if unknown:
            raise ValueError(f"vendor_not_allowed:{','.join(sorted(set(unknown)))}")
        if not self.fallback_vendors or self.fallback_vendors[0] != self.primary_vendor:
            raise ValueError("TradingAgentsDataVendorRoute fallback chain must start with primary vendor.")
        if self.raw_credential is not None:
            raise ValueError("TradingAgentsDataVendorRoute cannot contain raw credential material.")
        if self.live_api_called:
            raise ValueError("TradingAgentsDataVendorRoute cannot call live APIs in harvest mode.")
        if self.authority_expansion:
            raise ValueError("TradingAgentsDataVendorRoute cannot expand authority.")
        if not self.evidence_refs:
            raise ValueError("TradingAgentsDataVendorRoute requires evidence refs.")
        if not self.source_refs:
            raise ValueError("TradingAgentsDataVendorRoute requires source refs.")
        return self


class TradingOutcomeMemoryEntry(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("toutcome"))
    symbol: str
    trade_date: str
    rating: TradingDecisionRating
    decision_text: str
    raw_return: float | None = None
    benchmark_return: float | None = None
    alpha_return: float | None = None
    holding_days: int | None = None
    reflection: str | None = None
    pending: bool = True
    internal_memory_only: bool = True
    real_trade_started: bool = False
    evidence_refs: list[str]
    source_refs: list[str]
    authority_expansion: bool = False

    @classmethod
    def record_resolved(
        cls,
        *,
        symbol: str,
        trade_date: str,
        rating: TradingDecisionRating,
        decision_text: str,
        raw_return: float,
        benchmark_return: float,
        holding_days: int,
        reflection: str,
        evidence_refs: list[str],
        source_refs: list[str],
    ) -> TradingOutcomeMemoryEntry:
        return cls(
            symbol=symbol,
            trade_date=trade_date,
            rating=rating,
            decision_text=decision_text,
            raw_return=raw_return,
            benchmark_return=benchmark_return,
            alpha_return=round(raw_return - benchmark_return, 10),
            holding_days=holding_days,
            reflection=reflection,
            pending=False,
            evidence_refs=evidence_refs,
            source_refs=source_refs,
        )

    @model_validator(mode="after")
    def _validate(self) -> TradingOutcomeMemoryEntry:
        if not self.evidence_refs:
            raise ValueError("TradingOutcomeMemoryEntry requires evidence refs.")
        if not self.source_refs:
            raise ValueError("TradingOutcomeMemoryEntry requires source refs.")
        if self.real_trade_started:
            raise ValueError("TradingOutcomeMemoryEntry cannot start real trading.")
        if self.authority_expansion:
            raise ValueError("TradingOutcomeMemoryEntry cannot expand authority.")
        if not self.pending and self.alpha_return is None:
            raise ValueError("Resolved TradingOutcomeMemoryEntry requires alpha return.")
        return self


class TradingAgentsVendorPattern(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("tpattern"))
    pattern_name: str
    source_files: list[str]
    sentinel_rewrite: str
    extracted_power: str
    risk_controls: list[str]
    evidence_refs: list[str]
    vendor_runtime_bridge: bool = False
    vendor_code_copied: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> TradingAgentsVendorPattern:
        if not self.source_files:
            raise ValueError("TradingAgentsVendorPattern requires source files.")
        if not self.risk_controls:
            raise ValueError("TradingAgentsVendorPattern requires risk controls.")
        if not self.evidence_refs:
            raise ValueError("TradingAgentsVendorPattern requires evidence refs.")
        if self.vendor_runtime_bridge:
            raise ValueError("TradingAgentsVendorPattern cannot bridge vendor runtime.")
        if self.vendor_code_copied:
            raise ValueError("TradingAgentsVendorPattern cannot copy vendor code.")
        if self.authority_expansion:
            raise ValueError("TradingAgentsVendorPattern cannot expand authority.")
        return self


class TradingAgentsHarvestIntegrator:
    def build_firm_plan(
        self,
        *,
        mission_id: str,
        symbol: str,
        selected_analysts: list[str] | None = None,
        max_debate_rounds: int = 1,
        max_risk_discuss_rounds: int = 1,
        evidence_refs: list[str],
        source_refs: list[str],
    ) -> TradingAgentsFirmPlan:
        analysts = ["market", "social", "news", "fundamentals"] if selected_analysts is None else selected_analysts
        if not analysts:
            raise ValueError("selected analysts cannot be empty")
        unknown = [analyst for analyst in analysts if analyst not in ANALYST_ROLE_PURPOSES]
        if unknown:
            raise ValueError(f"unknown analyst:{','.join(unknown)}")

        assignments = [
            self._role(
                role=f"{analyst}_analyst",
                purpose=ANALYST_ROLE_PURPOSES[analyst],
                mission_id=mission_id,
                symbol=symbol,
                evidence_refs=evidence_refs,
                source_refs=source_refs,
                allowed_tools=self._tools_for_analyst(analyst),
                output_contract=f"{analyst}_report",
            )
            for analyst in analysts
        ]
        assignments.extend(
            [
                self._role("bull_researcher", TradingRolePurpose.BULL_THESIS, mission_id, symbol, evidence_refs, source_refs, [], "bull_argument"),
                self._role("bear_researcher", TradingRolePurpose.BEAR_THESIS, mission_id, symbol, evidence_refs, source_refs, [], "bear_argument"),
                self._role("research_manager", TradingRolePurpose.RESEARCH_SYNTHESIS, mission_id, symbol, evidence_refs, source_refs, [], "structured_research_plan"),
                self._role("trader", TradingRolePurpose.TRANSACTION_PROPOSAL, mission_id, symbol, evidence_refs, source_refs, [], "structured_trader_proposal"),
                self._role("aggressive_risk_analyst", TradingRolePurpose.AGGRESSIVE_RISK, mission_id, symbol, evidence_refs, source_refs, [], "aggressive_risk_argument"),
                self._role("conservative_risk_analyst", TradingRolePurpose.CONSERVATIVE_RISK, mission_id, symbol, evidence_refs, source_refs, [], "conservative_risk_argument"),
                self._role("neutral_risk_analyst", TradingRolePurpose.NEUTRAL_RISK, mission_id, symbol, evidence_refs, source_refs, [], "neutral_risk_argument"),
                self._role("portfolio_manager", TradingRolePurpose.PORTFOLIO_FINAL_DECISION, mission_id, symbol, evidence_refs, source_refs, [], "structured_portfolio_decision"),
            ]
        )
        return TradingAgentsFirmPlan(
            mission_id=mission_id,
            symbol=symbol,
            role_assignments=assignments,
            selected_analysts=analysts,
            max_debate_rounds=max_debate_rounds,
            max_risk_discuss_rounds=max_risk_discuss_rounds,
            evidence_refs=evidence_refs,
            source_refs=source_refs,
        )

    def plan_data_vendor_route(
        self,
        *,
        method: str,
        category: str,
        primary_vendor: str,
        available_vendors: list[str],
        evidence_refs: list[str],
        source_refs: list[str],
    ) -> TradingAgentsDataVendorRoute:
        fallback = [primary_vendor]
        fallback.extend(vendor for vendor in available_vendors if vendor != primary_vendor)
        return TradingAgentsDataVendorRoute(
            method=method,
            category=category,
            primary_vendor=primary_vendor,
            fallback_vendors=fallback,
            evidence_refs=evidence_refs,
            source_refs=source_refs,
        )

    def _role(
        self,
        role: str,
        purpose: TradingRolePurpose,
        mission_id: str,
        symbol: str,
        evidence_refs: list[str],
        source_refs: list[str],
        allowed_tools: list[str],
        output_contract: str,
    ) -> TradingAgentsRoleAssignment:
        return TradingAgentsRoleAssignment(
            role=role,
            purpose=purpose,
            mission_id=mission_id,
            symbol=symbol,
            evidence_refs=evidence_refs,
            source_refs=source_refs,
            allowed_tools=allowed_tools,
            output_contract=output_contract,
        )

    def _tools_for_analyst(self, analyst: str) -> list[str]:
        return {
            "market": ["get_stock_data", "get_indicators"],
            "social": ["get_news"],
            "news": ["get_news", "get_global_news", "get_insider_transactions"],
            "fundamentals": ["get_fundamentals", "get_balance_sheet", "get_cashflow", "get_income_statement"],
        }[analyst]
