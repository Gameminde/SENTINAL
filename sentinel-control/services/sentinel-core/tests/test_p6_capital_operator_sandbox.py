from __future__ import annotations

import pytest

from sentinel.organs import (
    AdaptiveOperatingEnvelope,
    BudgetReallocator,
    CapitalOpportunity,
    CapitalRiskReview,
    CapitalSandboxReceipt,
    CapitalSignal,
    DynamicSpendPolicy,
    OpportunityPortfolio,
    SignalLedger,
    SpendDecisionTrace,
)


def signal(**overrides) -> CapitalSignal:
    data = {
        "signal_type": "roi",
        "source": "channel_reply_rate",
        "strength": 0.8,
        "summary": "Three replies from qualified prospects.",
        "evidence_refs": ["ev_signal"],
    }
    data.update(overrides)
    return CapitalSignal(**data)


def opportunity(**overrides) -> CapitalOpportunity:
    data = {
        "name": "AI landing page service",
        "category": "service_offer",
        "expected_profit_or_progress": 120.0,
        "expected_information_gain": 0.7,
        "downside_risk": 0.2,
        "proposed_spend_usd": 35.0,
        "confidence": 0.65,
        "evidence_refs": ["ev_offer"],
        "signal_refs": ["sig_roi"],
        "planned_browser_refs": ["browser_plan_1"],
        "planned_api_refs": ["api_plan_1"],
        "planned_channel_refs": ["draft_1"],
        "planned_credential_refs": ["credref_public_api"],
    }
    data.update(overrides)
    return CapitalOpportunity(**data)


def envelope(**overrides) -> AdaptiveOperatingEnvelope:
    data = {
        "root_budget_max_usd": 500.0,
        "budget_remaining_usd": 500.0,
        "max_single_transaction_usd": 25.0,
        "sub_budgets": {"exploration": 100.0, "ads": 50.0},
        "exploration_fraction": 0.4,
        "stop_loss_usd": 100.0,
        "signal_refs": ["sig_initial"],
        "evidence_refs": ["ev_authority"],
    }
    data.update(overrides)
    return AdaptiveOperatingEnvelope(**data)


def test_capital_opportunity_models_planned_inputs_without_real_spend():
    item = opportunity()

    assert item.live_spend_started is False
    assert item.spend_proposal_only is True
    assert item.planned_browser_refs == ["browser_plan_1"]
    assert item.planned_api_refs == ["api_plan_1"]
    assert item.planned_channel_refs == ["draft_1"]
    assert item.planned_credential_refs == ["credref_public_api"]


def test_signal_ledger_records_market_api_outreach_roi_and_risk_signals():
    ledger = SignalLedger().record(signal(signal_type="market")).record(signal(signal_type="api")).record(
        signal(signal_type="risk", strength=-0.4)
    )

    assert len(ledger.signals) == 3
    assert ledger.signal_refs
    assert ledger.average_strength() > 0


def test_budget_reallocator_moves_sandbox_budget_to_stronger_evidence():
    ledger = SignalLedger().record(signal(id="sig_roi", strength=0.9)).record(signal(id="sig_risk", strength=-0.1))
    portfolio = OpportunityPortfolio(
        opportunities=[
            opportunity(id="opp_good", name="good", category="outreach", signal_refs=["sig_roi"]),
            opportunity(id="opp_weak", name="weak", category="ads", expected_profit_or_progress=5.0, signal_refs=["sig_risk"]),
        ],
        evidence_refs=["ev_portfolio"],
    )

    updated = BudgetReallocator().reallocate(envelope(), portfolio, ledger)

    assert updated.sub_budgets["outreach"] > 0
    assert updated.max_single_transaction_usd > 25.0
    assert "sig_roi" in updated.signal_refs
    assert updated.authority_expansion is False


def test_dynamic_spend_change_requires_signal_refs():
    portfolio = OpportunityPortfolio(opportunities=[opportunity(signal_refs=[])], evidence_refs=["ev_portfolio"])

    with pytest.raises(ValueError, match="signal refs"):
        BudgetReallocator().reallocate(envelope(), portfolio, SignalLedger())


def test_profit_guarantee_claim_is_flagged():
    review = CapitalRiskReview.review(opportunity(objective_text="Guaranteed profit in 24 hours."))

    assert review.profit_guarantee_flagged is True
    assert "profit_guarantee_claim" in review.risk_flags


def test_dynamic_spend_policy_produces_proposal_not_live_spend():
    ledger = SignalLedger().record(signal(id="sig_roi"))
    trace = DynamicSpendPolicy().propose(opportunity(signal_refs=["sig_roi"]), envelope(), ledger)

    assert trace.spend_proposal_only is True
    assert trace.live_spend_started is False
    assert trace.proposed_amount_usd <= envelope().budget_remaining_usd
    assert trace.expected_information_gain > 0


def test_spend_decision_trace_requires_signal_refs_and_blocks_authority_expansion():
    with pytest.raises(ValueError, match="signal refs"):
        SpendDecisionTrace(
            opportunity_id="opp",
            proposed_amount_usd=10.0,
            expected_profit_or_progress=20.0,
            expected_information_gain=0.4,
            downside_risk=0.2,
            transaction_cost=10.0,
            authority_impact=0.0,
            signal_refs=[],
            evidence_refs=["ev"],
        )

    with pytest.raises(ValueError, match="cannot expand authority"):
        SpendDecisionTrace(
            opportunity_id="opp",
            proposed_amount_usd=10.0,
            expected_profit_or_progress=20.0,
            expected_information_gain=0.4,
            downside_risk=0.2,
            transaction_cost=10.0,
            authority_impact=1.0,
            signal_refs=["sig"],
            evidence_refs=["ev"],
            authority_expansion=True,
        )


def test_capital_sandbox_receipt_is_deterministic_and_non_executing():
    ledger = SignalLedger().record(signal(id="sig_roi"))
    trace = DynamicSpendPolicy().propose(opportunity(signal_refs=["sig_roi"]), envelope(), ledger)
    receipt = CapitalSandboxReceipt.create(
        mission_id="mission_p6g",
        trace=trace,
        portfolio_refs=["portfolio_1"],
        trace_refs=["trace_capital"],
    )

    assert receipt.execution_started is False
    assert receipt.live_spend_started is False
    assert receipt.receipt_hash == receipt.expected_hash()


def test_capital_sandbox_receipt_requires_trace_and_evidence_refs():
    trace = DynamicSpendPolicy().propose(opportunity(), envelope(), SignalLedger().record(signal(id="sig_roi")))

    with pytest.raises(ValueError, match="requires trace refs"):
        CapitalSandboxReceipt.create(mission_id="mission_p6g", trace=trace, portfolio_refs=[], trace_refs=[])

    with pytest.raises(ValueError, match="requires evidence refs"):
        opportunity(evidence_refs=[])
