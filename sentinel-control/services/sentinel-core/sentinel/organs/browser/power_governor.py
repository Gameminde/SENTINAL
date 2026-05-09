from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class BrowserPowerLevel(StrEnum):
    P0_NORMAL_RELIABILITY = "P0_normal_browser_reliability"
    P1_HUMAN_LIKE_OPERATION = "P1_human_like_operation"
    P2_FINGERPRINT_CONSISTENCY = "P2_fingerprint_consistency"
    P3_DETECTION_RESILIENCE_RESEARCH = "P3_detection_resilience_research"
    P4_SPECIAL_AUTHORITY_STEALTH = "P4_special_authority_stealth_operation"
    P5_FORBIDDEN_MISUSE_OBJECTIVE = "P5_forbidden_misuse_objective"


POWER_ORDER = {
    BrowserPowerLevel.P0_NORMAL_RELIABILITY: 0,
    BrowserPowerLevel.P1_HUMAN_LIKE_OPERATION: 1,
    BrowserPowerLevel.P2_FINGERPRINT_CONSISTENCY: 2,
    BrowserPowerLevel.P3_DETECTION_RESILIENCE_RESEARCH: 3,
    BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH: 4,
    BrowserPowerLevel.P5_FORBIDDEN_MISUSE_OBJECTIVE: 5,
}


class BrowserPowerRequest(SentinelModel):
    action: str
    requested_power: BrowserPowerLevel
    needed_power: BrowserPowerLevel | None = None
    objective_tags: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    domain_policy_allows: bool = True
    legal_compliance_allows: bool = True
    finalgate_available: bool = True

    @model_validator(mode="after")
    def _validate(self) -> BrowserPowerRequest:
        if not self.evidence_refs:
            raise ValueError("BrowserPowerRequest requires evidence refs.")
        return self


class BrowserPowerDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bpower"))
    action: str
    requested_power: BrowserPowerLevel
    selected_power: BrowserPowerLevel
    lane: AutonomyRiskLane
    allowed: bool
    dry_run_only: bool = True
    auto_executable: bool = False
    requires_special_authority: bool = False
    requires_authority_extension: bool = False
    blocked: bool = False
    reasons: list[str]
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    authority_expansion: bool = False


class BrowserPowerGovernor:
    SPECIAL_AUTHORITY_ACTIONS = {"browser_special_authority_review", "browser_stealth_operation"}
    SENSITIVE_ACTION_TERMS = {"submit", "form", "click_sensitive", "login", "upload"}

    def govern(self, request: BrowserPowerRequest, authority: OrganAuthorityEnvelope) -> BrowserPowerDecision:
        reasons: list[str] = []
        requested = request.requested_power
        selected = request.needed_power or requested
        if POWER_ORDER[selected] < POWER_ORDER[requested]:
            reasons.append("downgraded_to_lowest_needed_power")
        if BrowserPowerLevel.P5_FORBIDDEN_MISUSE_OBJECTIVE in {requested, selected}:
            return self._blocked(request, selected, "misuse_objective")
        if not request.legal_compliance_allows:
            return self._blocked(request, selected, "legal_compliance_denied")
        if not request.domain_policy_allows:
            return self._blocked(request, selected, "domain_policy_denied")
        if not request.finalgate_available:
            return self._blocked(request, selected, "finalgate_unavailable")
        if authority.errors:
            return BrowserPowerDecision(
                action=request.action,
                requested_power=requested,
                selected_power=selected,
                lane=AutonomyRiskLane.RED,
                allowed=False,
                dry_run_only=True,
                requires_authority_extension=True,
                blocked=False,
                reasons=[*reasons, "authority_errors_present", *authority.errors],
                evidence_refs=request.evidence_refs,
                trace_refs=[*request.trace_refs, *authority.trace_refs],
            )
        if selected == BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH and not self._has_special_authority(authority):
            return BrowserPowerDecision(
                action=request.action,
                requested_power=requested,
                selected_power=BrowserPowerLevel.P3_DETECTION_RESILIENCE_RESEARCH,
                lane=AutonomyRiskLane.RED,
                allowed=False,
                dry_run_only=True,
                requires_special_authority=True,
                requires_authority_extension=True,
                reasons=[*reasons, "p4_requires_special_authority", "downgraded_to_p3_research"],
                evidence_refs=request.evidence_refs,
                trace_refs=[*request.trace_refs, *authority.trace_refs],
            )
        if self._is_sensitive_action(request.action):
            return BrowserPowerDecision(
                action=request.action,
                requested_power=requested,
                selected_power=selected,
                lane=AutonomyRiskLane.ORANGE,
                allowed=False,
                dry_run_only=True,
                reasons=[*reasons, "sensitive_browser_action_requires_elevated_authority_or_future_promotion"],
                evidence_refs=request.evidence_refs,
                trace_refs=[*request.trace_refs, *authority.trace_refs],
            )
        lane = self._lane_for(selected)
        return BrowserPowerDecision(
            action=request.action,
            requested_power=requested,
            selected_power=selected,
            lane=lane,
            allowed=True,
            dry_run_only=True,
            auto_executable=lane == AutonomyRiskLane.BLUE and request.action == "browser_read_public_page",
            requires_special_authority=selected == BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH,
            reasons=reasons or ["browser_power_allowed_as_planning_or_locked_route"],
            evidence_refs=request.evidence_refs,
            trace_refs=[*request.trace_refs, *authority.trace_refs],
        )

    @staticmethod
    def _lane_for(power: BrowserPowerLevel) -> AutonomyRiskLane:
        if power == BrowserPowerLevel.P0_NORMAL_RELIABILITY:
            return AutonomyRiskLane.BLUE
        if power in {BrowserPowerLevel.P1_HUMAN_LIKE_OPERATION, BrowserPowerLevel.P2_FINGERPRINT_CONSISTENCY}:
            return AutonomyRiskLane.ORANGE
        if power in {BrowserPowerLevel.P3_DETECTION_RESILIENCE_RESEARCH, BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH}:
            return AutonomyRiskLane.RED
        return AutonomyRiskLane.BLACK

    @classmethod
    def _is_sensitive_action(cls, action: str) -> bool:
        normalized = action.lower()
        return any(term in normalized for term in cls.SENSITIVE_ACTION_TERMS)

    @classmethod
    def _has_special_authority(cls, authority: OrganAuthorityEnvelope) -> bool:
        return any(action in cls.SPECIAL_AUTHORITY_ACTIONS for action in authority.allowed_actions)

    @staticmethod
    def _blocked(request: BrowserPowerRequest, selected: BrowserPowerLevel, reason: str) -> BrowserPowerDecision:
        return BrowserPowerDecision(
            action=request.action,
            requested_power=request.requested_power,
            selected_power=selected,
            lane=AutonomyRiskLane.BLACK,
            allowed=False,
            dry_run_only=True,
            blocked=True,
            reasons=[reason],
            evidence_refs=request.evidence_refs,
            trace_refs=request.trace_refs,
        )
