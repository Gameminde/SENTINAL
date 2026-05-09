from __future__ import annotations

from pydantic import Field

from sentinel.organs.browser.power_governor import BrowserPowerLevel
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class BrowserMisuseDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bmisuse"))
    blocked: bool
    lane: AutonomyRiskLane
    power_level: BrowserPowerLevel
    matched_terms: list[str] = Field(default_factory=list)
    reason: str
    capability_deleted: bool = False


class BrowserMisuseClassifier:
    MISUSE_TERMS = {
        "fraud",
        "fake_identity",
        "kyc_bypass",
        "credential_theft",
        "illegal_spam",
        "spam",
        "unauthorized_scraping",
        "unlawful_evasion",
        "access_control_evasion",
    }

    def classify(self, *, objective_tags: list[str] | None = None, objective_text: str = "") -> BrowserMisuseDecision:
        tags = {tag.lower().replace(" ", "_") for tag in objective_tags or []}
        text = objective_text.lower().replace(" ", "_")
        matched = sorted(term for term in self.MISUSE_TERMS if term in tags or term in text)
        if matched:
            return BrowserMisuseDecision(
                blocked=True,
                lane=AutonomyRiskLane.BLACK,
                power_level=BrowserPowerLevel.P5_FORBIDDEN_MISUSE_OBJECTIVE,
                matched_terms=matched,
                reason="Browser misuse objective blocked while preserving legitimate capability classification.",
            )
        return BrowserMisuseDecision(
            blocked=False,
            lane=AutonomyRiskLane.BLUE,
            power_level=BrowserPowerLevel.P0_NORMAL_RELIABILITY,
            reason="No browser misuse objective detected.",
        )
