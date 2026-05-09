from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


def _hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CapitalSignal(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("capsig"))
    signal_type: str
    source: str
    strength: float = Field(ge=-1.0, le=1.0)
    summary: str
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> CapitalSignal:
        if not self.evidence_refs:
            raise ValueError("CapitalSignal requires evidence refs.")
        return self


class SignalLedger(SentinelModel):
    signals: list[CapitalSignal] = Field(default_factory=list)

    @property
    def signal_refs(self) -> list[str]:
        return [signal.id for signal in self.signals]

    def record(self, signal: CapitalSignal) -> SignalLedger:
        return self.model_copy(update={"signals": [*self.signals, signal]})

    def average_strength(self) -> float:
        if not self.signals:
            return 0.0
        return sum(signal.strength for signal in self.signals) / len(self.signals)

    def strength_for(self, refs: list[str]) -> float:
        matched = [signal.strength for signal in self.signals if signal.id in refs]
        if not matched:
            return 0.0
        return sum(matched) / len(matched)


class CapitalOpportunity(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("capopp"))
    name: str
    category: str
    expected_profit_or_progress: float = Field(ge=0.0)
    expected_information_gain: float = Field(ge=0.0, le=1.0)
    downside_risk: float = Field(ge=0.0, le=1.0)
    proposed_spend_usd: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str]
    signal_refs: list[str] = Field(default_factory=list)
    planned_browser_refs: list[str] = Field(default_factory=list)
    planned_api_refs: list[str] = Field(default_factory=list)
    planned_channel_refs: list[str] = Field(default_factory=list)
    planned_credential_refs: list[str] = Field(default_factory=list)
    objective_text: str = ""
    spend_proposal_only: bool = True
    live_spend_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> CapitalOpportunity:
        if not self.evidence_refs:
            raise ValueError("CapitalOpportunity requires evidence refs.")
        if self.live_spend_started:
            raise ValueError("CapitalOpportunity cannot start live spend in P6G.")
        if self.authority_expansion:
            raise ValueError("CapitalOpportunity cannot expand authority.")
        return self

    @property
    def score(self) -> float:
        return (
            self.expected_profit_or_progress * 0.01
            + self.expected_information_gain
            + self.confidence
            - self.downside_risk
        )


class OpportunityPortfolio(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("capport"))
    opportunities: list[CapitalOpportunity]
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> OpportunityPortfolio:
        if not self.evidence_refs:
            raise ValueError("OpportunityPortfolio requires evidence refs.")
        return self

    def top(self) -> CapitalOpportunity:
        if not self.opportunities:
            raise ValueError("OpportunityPortfolio requires opportunities.")
        return max(self.opportunities, key=lambda item: item.score)


class AdaptiveOperatingEnvelope(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("capenv"))
    root_budget_max_usd: float = Field(ge=0.0)
    budget_remaining_usd: float = Field(ge=0.0)
    max_single_transaction_usd: float = Field(ge=0.0)
    sub_budgets: dict[str, float] = Field(default_factory=dict)
    exploration_fraction: float = Field(ge=0.0, le=1.0)
    stop_loss_usd: float = Field(ge=0.0)
    signal_refs: list[str]
    evidence_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> AdaptiveOperatingEnvelope:
        if self.budget_remaining_usd > self.root_budget_max_usd:
            raise ValueError("AdaptiveOperatingEnvelope budget remaining cannot exceed root budget.")
        if not self.signal_refs:
            raise ValueError("AdaptiveOperatingEnvelope requires signal refs.")
        if not self.evidence_refs:
            raise ValueError("AdaptiveOperatingEnvelope requires evidence refs.")
        if self.authority_expansion:
            raise ValueError("AdaptiveOperatingEnvelope cannot expand authority.")
        return self


class BudgetReallocator:
    def reallocate(
        self,
        envelope: AdaptiveOperatingEnvelope,
        portfolio: OpportunityPortfolio,
        ledger: SignalLedger,
    ) -> AdaptiveOperatingEnvelope:
        if not ledger.signal_refs:
            raise ValueError("Budget reallocation requires signal refs.")
        top = portfolio.top()
        if not top.signal_refs:
            raise ValueError("Budget reallocation requires opportunity signal refs.")
        strength = max(0.0, ledger.strength_for(top.signal_refs))
        if strength <= 0:
            raise ValueError("Budget reallocation requires positive signal refs.")
        allocation = round(min(envelope.budget_remaining_usd * 0.25, max(top.proposed_spend_usd, 1.0) * (1 + strength)), 2)
        new_sub_budgets = dict(envelope.sub_budgets)
        new_sub_budgets[top.category] = round(new_sub_budgets.get(top.category, 0.0) + allocation, 2)
        new_max = round(min(envelope.budget_remaining_usd, max(envelope.max_single_transaction_usd, allocation)), 2)
        return envelope.model_copy(
            update={
                "sub_budgets": new_sub_budgets,
                "max_single_transaction_usd": new_max,
                "signal_refs": sorted(set([*envelope.signal_refs, *top.signal_refs, *ledger.signal_refs])),
            }
        )


class SpendDecisionTrace(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("capspend"))
    opportunity_id: str
    proposed_amount_usd: float = Field(ge=0.0)
    expected_profit_or_progress: float = Field(ge=0.0)
    expected_information_gain: float = Field(ge=0.0, le=1.0)
    downside_risk: float = Field(ge=0.0, le=1.0)
    transaction_cost: float = Field(ge=0.0)
    authority_impact: float = Field(ge=0.0)
    signal_refs: list[str]
    evidence_refs: list[str]
    spend_proposal_only: bool = True
    live_spend_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SpendDecisionTrace:
        if not self.signal_refs:
            raise ValueError("SpendDecisionTrace requires signal refs.")
        if not self.evidence_refs:
            raise ValueError("SpendDecisionTrace requires evidence refs.")
        if self.live_spend_started:
            raise ValueError("SpendDecisionTrace cannot start live spend in P6G.")
        if self.authority_expansion:
            raise ValueError("SpendDecisionTrace cannot expand authority.")
        return self


class DynamicSpendPolicy:
    def propose(
        self,
        opportunity: CapitalOpportunity,
        envelope: AdaptiveOperatingEnvelope,
        ledger: SignalLedger,
    ) -> SpendDecisionTrace:
        if not opportunity.signal_refs:
            raise ValueError("DynamicSpendPolicy requires opportunity signal refs.")
        signal_strength = max(0.0, ledger.strength_for(opportunity.signal_refs))
        if signal_strength == 0 and ledger.signal_refs:
            signal_strength = max(0.0, ledger.average_strength())
        if signal_strength <= 0:
            raise ValueError("DynamicSpendPolicy requires positive signal refs.")
        proposed = round(
            min(
                opportunity.proposed_spend_usd * (1 + signal_strength),
                envelope.max_single_transaction_usd,
                envelope.budget_remaining_usd,
            ),
            2,
        )
        return SpendDecisionTrace(
            opportunity_id=opportunity.id,
            proposed_amount_usd=proposed,
            expected_profit_or_progress=opportunity.expected_profit_or_progress,
            expected_information_gain=opportunity.expected_information_gain,
            downside_risk=opportunity.downside_risk,
            transaction_cost=proposed,
            authority_impact=0.0,
            signal_refs=sorted(set([*opportunity.signal_refs, *ledger.signal_refs])),
            evidence_refs=list(opportunity.evidence_refs),
        )


class CapitalRiskReview(SentinelModel):
    opportunity_id: str
    profit_guarantee_flagged: bool = False
    risk_flags: list[str] = Field(default_factory=list)
    evidence_refs: list[str]

    @classmethod
    def review(cls, opportunity: CapitalOpportunity) -> CapitalRiskReview:
        text = f"{opportunity.name} {opportunity.objective_text}".lower()
        flags = []
        if "guaranteed profit" in text or "guarantee profit" in text or "risk-free profit" in text:
            flags.append("profit_guarantee_claim")
        if opportunity.downside_risk >= 0.8:
            flags.append("high_downside_risk")
        return cls(
            opportunity_id=opportunity.id,
            profit_guarantee_flagged="profit_guarantee_claim" in flags,
            risk_flags=flags,
            evidence_refs=list(opportunity.evidence_refs),
        )


class CapitalSandboxReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("caprcpt"))
    mission_id: str
    spend_decision_trace_id: str
    proposed_amount_usd: float
    portfolio_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    signal_refs: list[str]
    trace_refs: list[str]
    receipt_hash: str = ""
    spend_proposal_only: bool = True
    live_spend_started: bool = False
    execution_started: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> CapitalSandboxReceipt:
        if not self.evidence_refs:
            raise ValueError("CapitalSandboxReceipt requires evidence refs.")
        if not self.signal_refs:
            raise ValueError("CapitalSandboxReceipt requires signal refs.")
        if not self.trace_refs:
            raise ValueError("CapitalSandboxReceipt requires trace refs.")
        if self.live_spend_started or self.execution_started:
            raise ValueError("CapitalSandboxReceipt cannot start spend or execution.")
        if self.authority_expansion:
            raise ValueError("CapitalSandboxReceipt cannot expand authority.")
        expected = self.expected_hash()
        if self.receipt_hash and self.receipt_hash != expected:
            raise ValueError("CapitalSandboxReceipt hash mismatch.")
        if not self.receipt_hash:
            self.receipt_hash = expected
        return self

    @classmethod
    def create(
        cls,
        *,
        mission_id: str,
        trace: SpendDecisionTrace,
        portfolio_refs: list[str],
        trace_refs: list[str],
    ) -> CapitalSandboxReceipt:
        return cls(
            mission_id=mission_id,
            spend_decision_trace_id=trace.id,
            proposed_amount_usd=trace.proposed_amount_usd,
            portfolio_refs=portfolio_refs,
            evidence_refs=list(trace.evidence_refs),
            signal_refs=list(trace.signal_refs),
            trace_refs=trace_refs,
        )

    def expected_hash(self) -> str:
        return _hash(
            {
                "mission_id": self.mission_id,
                "spend_decision_trace_id": self.spend_decision_trace_id,
                "proposed_amount_usd": self.proposed_amount_usd,
                "portfolio_refs": self.portfolio_refs,
                "evidence_refs": self.evidence_refs,
                "signal_refs": self.signal_refs,
                "trace_refs": self.trace_refs,
            }
        )
