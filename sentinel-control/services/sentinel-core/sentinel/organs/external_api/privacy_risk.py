from __future__ import annotations

from pydantic import Field

from sentinel.organs.external_api.request_plan import APIRequestPlan
from sentinel.shared.models import SentinelModel, new_id


PERSONAL_DATA_TERMS = {
    "email",
    "email_address",
    "phone",
    "phone_number",
    "name",
    "address",
    "ip_address",
    "customer_id",
}
SENSITIVE_DATA_TERMS = {"ssn", "health", "financial_account", "credential", "password"}


class APIPrivacyRiskProfile(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("apipriv"))
    risk_level: str
    contains_personal_data: bool = False
    contains_sensitive_data: bool = False
    data_categories: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class APIPrivacyRiskClassifier:
    def classify(self, plan: APIRequestPlan) -> APIPrivacyRiskProfile:
        categories = {category.lower() for category in plan.data_categories}
        contains_personal = bool(categories & PERSONAL_DATA_TERMS)
        contains_sensitive = bool(categories & SENSITIVE_DATA_TERMS)
        reasons = []
        risk_level = "low"
        if contains_personal:
            risk_level = "high"
            reasons.append("personal_data_detected")
        if contains_sensitive:
            risk_level = "critical"
            reasons.append("sensitive_data_detected")
        if plan.account_affecting and risk_level == "low":
            risk_level = "medium"
            reasons.append("account_affecting_api")
        return APIPrivacyRiskProfile(
            risk_level=risk_level,
            contains_personal_data=contains_personal,
            contains_sensitive_data=contains_sensitive,
            data_categories=plan.data_categories,
            reasons=reasons or ["public_or_low_privacy_data"],
        )
