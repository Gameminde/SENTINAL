from __future__ import annotations

from pydantic import Field

from sentinel.organs.browser.misuse_classifier import BrowserMisuseDecision
from sentinel.organs.browser.power_governor import BrowserPowerDecision
from sentinel.shared.models import SentinelModel, new_id


class BrowserComplianceDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bcomp"))
    accepted: bool
    reasons: list[str]
    selected_power: str
    authority_expansion: bool = False


class BrowserComplianceGate:
    def evaluate(self, power: BrowserPowerDecision, misuse: BrowserMisuseDecision) -> BrowserComplianceDecision:
        if misuse.blocked:
            return BrowserComplianceDecision(
                accepted=False,
                reasons=["misuse_objective_blocked", *misuse.matched_terms],
                selected_power=misuse.power_level.value,
            )
        if power.blocked or not power.allowed:
            return BrowserComplianceDecision(
                accepted=False,
                reasons=list(power.reasons),
                selected_power=power.selected_power.value,
            )
        return BrowserComplianceDecision(
            accepted=True,
            reasons=["browser_power_compliance_accepted"],
            selected_power=power.selected_power.value,
        )
