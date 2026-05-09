from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.organs.browser.power_governor import BrowserPowerLevel
from sentinel.shared.models import SentinelModel, new_id


class BrowserFingerprintRiskProfile(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bfprint"))
    requested_power: BrowserPowerLevel
    web_rtc_leak_prevention: bool = False
    timezone_proxy_locale_alignment: bool = False
    persistent_profile_realism: bool = False
    risk_score: float = Field(ge=0.0, le=100.0)
    requires_special_authority: bool = False
    evidence_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> BrowserFingerprintRiskProfile:
        if not self.evidence_refs:
            raise ValueError("BrowserFingerprintRiskProfile requires evidence refs.")
        if self.requested_power == BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH:
            self.requires_special_authority = True
            self.risk_score = max(self.risk_score, 85.0)
        return self
