from __future__ import annotations

import pytest

from sentinel.agent.events import AgentEventType
from sentinel.organs import (
    TradingAgentsDataVendorRoute,
    TradingAgentsFirmPlan,
    TradingAgentsHarvestIntegrator,
    TradingAgentsSignalParser,
    TradingAgentsVendorPattern,
    TradingDecisionRating,
    TradingOutcomeMemoryEntry,
)


def test_tradingagents_firm_plan_maps_full_trading_desk_roles():
    plan = TradingAgentsHarvestIntegrator().build_firm_plan(
        mission_id="mission_trade_harvest",
        symbol="NVDA",
        selected_analysts=["market", "news", "fundamentals"],
        max_debate_rounds=2,
        max_risk_discuss_rounds=1,
        evidence_refs=["ev_tradingagents_readme", "ev_tradingagents_graph"],
        source_refs=["agent-lab/vendors/tradingagents/source/tradingagents/graph/setup.py"],
    )

    roles = {assignment.role for assignment in plan.role_assignments}

    assert isinstance(plan, TradingAgentsFirmPlan)
    assert {"market_analyst", "news_analyst", "fundamentals_analyst"} <= roles
    assert {"bull_researcher", "bear_researcher", "research_manager"} <= roles
    assert {"trader", "aggressive_risk_analyst", "neutral_risk_analyst", "conservative_risk_analyst"} <= roles
    assert "portfolio_manager" in roles
    assert plan.paper_only is True
    assert plan.real_trade_started is False
    assert plan.authority_expansion is False
    assert AgentEventType.TRADING_FIRM_PLAN_CREATED.value == "trading_firm_plan_created"


def test_tradingagents_firm_plan_rejects_empty_analyst_set_and_unknown_analyst():
    integrator = TradingAgentsHarvestIntegrator()

    with pytest.raises(ValueError, match="selected analysts"):
        integrator.build_firm_plan(
            mission_id="mission",
            symbol="AAPL",
            selected_analysts=[],
            evidence_refs=["ev"],
            source_refs=["src"],
        )

    with pytest.raises(ValueError, match="unknown analyst"):
        integrator.build_firm_plan(
            mission_id="mission",
            symbol="AAPL",
            selected_analysts=["market", "astrology"],
            evidence_refs=["ev"],
            source_refs=["src"],
        )


def test_signal_parser_uses_tradingagents_five_tier_scale_without_llm():
    parser = TradingAgentsSignalParser()

    assert parser.parse_rating("**Rating**: Overweight\nBuild gradually.") == TradingDecisionRating.OVERWEIGHT
    assert parser.parse_rating("No edge visible.") == TradingDecisionRating.HOLD
    assert parser.parse_rating("Rating: **Sell**\nExit.") == TradingDecisionRating.SELL
    assert AgentEventType.TRADING_SIGNAL_PARSED.value == "trading_signal_parsed"


def test_vendor_route_uses_primary_plus_fallback_without_live_execution_or_credentials():
    route = TradingAgentsHarvestIntegrator().plan_data_vendor_route(
        method="get_stock_data",
        category="core_stock_apis",
        primary_vendor="alpha_vantage",
        available_vendors=["alpha_vantage", "yfinance"],
        evidence_refs=["ev_vendor"],
        source_refs=["agent-lab/vendors/tradingagents/source/tradingagents/dataflows/interface.py"],
    )

    assert isinstance(route, TradingAgentsDataVendorRoute)
    assert route.fallback_vendors == ["alpha_vantage", "yfinance"]
    assert route.dry_run_only is True
    assert route.live_api_called is False
    assert route.credential_ref is None
    assert AgentEventType.TRADING_DATA_VENDOR_ROUTED.value == "trading_data_vendor_routed"


def test_vendor_route_blocks_raw_credentials_and_unknown_vendor():
    with pytest.raises(ValueError, match="raw credential"):
        TradingAgentsDataVendorRoute(
            method="get_stock_data",
            category="core_stock_apis",
            primary_vendor="alpha_vantage",
            fallback_vendors=["alpha_vantage", "yfinance"],
            evidence_refs=["ev"],
            source_refs=["src"],
            raw_credential="secret",
        )

    with pytest.raises(ValueError, match="vendor_not_allowed"):
        TradingAgentsHarvestIntegrator().plan_data_vendor_route(
            method="get_stock_data",
            category="core_stock_apis",
            primary_vendor="unknown_vendor",
            available_vendors=["unknown_vendor", "yfinance"],
            evidence_refs=["ev"],
            source_refs=["src"],
        )


def test_outcome_memory_computes_alpha_and_remains_internal():
    entry = TradingOutcomeMemoryEntry.record_resolved(
        symbol="NVDA",
        trade_date="2026-01-15",
        rating=TradingDecisionRating.BUY,
        decision_text="Rating: Buy",
        raw_return=0.08,
        benchmark_return=0.03,
        holding_days=5,
        reflection="Directional call worked; keep evidence threshold.",
        evidence_refs=["ev_outcome"],
        source_refs=["agent-lab/vendors/tradingagents/source/tradingagents/agents/utils/memory.py"],
    )

    assert entry.alpha_return == pytest.approx(0.05)
    assert entry.pending is False
    assert entry.internal_memory_only is True
    assert entry.real_trade_started is False
    assert AgentEventType.TRADING_OUTCOME_MEMORY_RECORDED.value == "trading_outcome_memory_recorded"


def test_harvest_pattern_is_rewrite_not_vendor_bridge():
    pattern = TradingAgentsVendorPattern(
        pattern_name="bull_bear_research_debate",
        source_files=[
            "agent-lab/vendors/tradingagents/source/tradingagents/agents/researchers/bull_researcher.py",
            "agent-lab/vendors/tradingagents/source/tradingagents/agents/researchers/bear_researcher.py",
        ],
        sentinel_rewrite="TradingAgentsFirmPlan debate role assignments",
        extracted_power="balanced adversarial investment thesis generation",
        risk_controls=["no vendor runtime import", "no live execution", "paper-only trading authority"],
        evidence_refs=["ev_bull_bear"],
    )

    assert pattern.vendor_runtime_bridge is False
    assert pattern.vendor_code_copied is False
    assert pattern.authority_expansion is False
    assert AgentEventType.TRADINGAGENTS_PATTERN_HARVESTED.value == "tradingagents_pattern_harvested"
