from __future__ import annotations

from pydantic import Field

from sentinel.organs.external_api.request_plan import APIRequestPlan
from sentinel.shared.models import SentinelModel, new_id


class APIAllowlistDecision(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("apiallow"))
    vendor: str
    domain: str
    dry_run_allowed: bool = True
    live_allowed: bool
    errors: list[str] = Field(default_factory=list)
    authority_expansion: bool = False


class ExternalAPIAllowlist(SentinelModel):
    allowed_vendors: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)

    def evaluate(self, plan: APIRequestPlan) -> APIAllowlistDecision:
        errors: list[str] = []
        if plan.vendor not in self.allowed_vendors:
            errors.append(f"vendor_not_allowlisted:{plan.vendor}")
        if plan.domain not in self.allowed_domains:
            errors.append(f"domain_not_allowlisted:{plan.domain}")
        return APIAllowlistDecision(
            vendor=plan.vendor,
            domain=plan.domain,
            live_allowed=not errors,
            errors=errors,
        )
