from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.contracts import ExternalOrganContract, OrganType
from sentinel.shared.models import SentinelModel, new_id


class OrganRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrganRiskProfile(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("orisk"))
    mission_id: str
    organ_id: str
    action: str
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: OrganRiskLevel
    requires_dry_run: bool = True
    requires_approval: bool = False
    requires_special_authority: bool = False
    misuse_objective_detected: bool = False
    reasons: list[str] = Field(default_factory=list)
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)


class OrganRiskProfiler:
    HIGH_IMPACT_ACTIONS = {
        "payment",
        "spend_money",
        "trade_order",
        "account_create",
        "send_message",
        "browser_submit",
        "desktop_control",
        "credential_access",
    }
    MISUSE_TERMS = {"fraud", "fake_identity", "kyc_bypass", "credential_theft", "spam", "unauthorized_scraping"}

    def profile(
        self,
        contract: ExternalOrganContract,
        authority: OrganAuthorityEnvelope,
        *,
        action: str,
        objective_tags: list[str] | None = None,
        event_bus: EventBus | None = None,
    ) -> OrganRiskProfile:
        tags = {tag.lower() for tag in objective_tags or []}
        reasons = []
        score = 10.0
        if action in self.HIGH_IMPACT_ACTIONS:
            score += 35.0
            reasons.append("high_impact_action")
        if contract.organ_type in {OrganType.BROWSER, OrganType.TRADING, OrganType.CAPITAL_OPERATOR, OrganType.DESKTOP_SIDECAR, OrganType.SHELL_SANDBOX}:
            score += 20.0
            reasons.append(f"high_power_organ:{contract.organ_type.value}")
        if authority.errors:
            score += 30.0
            reasons.append("authority_errors_present")
        misuse = bool(tags & self.MISUSE_TERMS)
        if misuse:
            score = 100.0
            reasons.append("misuse_objective_detected")
        risk_level = self._level(score)
        profile = OrganRiskProfile(
            mission_id=authority.mission_id,
            organ_id=contract.id,
            action=action,
            risk_score=min(score, 100.0),
            risk_level=risk_level,
            requires_approval=risk_level in {OrganRiskLevel.HIGH, OrganRiskLevel.CRITICAL},
            requires_special_authority=misuse or risk_level == OrganRiskLevel.CRITICAL,
            misuse_objective_detected=misuse,
            reasons=reasons or ["bounded_low_risk_organ_action"],
        )
        if event_bus is None:
            return profile
        event = event_bus.append(
            AgentEventType.ORGAN_RISK_PROFILED,
            "External organ risk profiled without execution.",
            payload={
                "risk_profile_id": profile.id,
                "organ_id": contract.id,
                "action": action,
                "risk_score": profile.risk_score,
                "risk_level": profile.risk_level.value,
                "requires_approval": profile.requires_approval,
                "requires_special_authority": profile.requires_special_authority,
                "misuse_objective_detected": profile.misuse_objective_detected,
                "authority_expansion": False,
            },
            trace_refs=list(authority.trace_refs),
        )
        return profile.model_copy(update={"trace_refs": [event.id]})

    @staticmethod
    def _level(score: float) -> OrganRiskLevel:
        if score >= 85:
            return OrganRiskLevel.CRITICAL
        if score >= 60:
            return OrganRiskLevel.HIGH
        if score >= 30:
            return OrganRiskLevel.MEDIUM
        return OrganRiskLevel.LOW
