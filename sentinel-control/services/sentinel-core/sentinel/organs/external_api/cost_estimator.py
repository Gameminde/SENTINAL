from __future__ import annotations

from pydantic import Field

from sentinel.organs.external_api.request_plan import APIRequestPlan
from sentinel.shared.models import SentinelModel, new_id


class APICostEstimate(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("apicost"))
    estimated_cost_usd: float = Field(ge=0.0)
    estimated_latency_ms: int = Field(ge=0)
    rate_limit_per_minute: int = Field(ge=1)
    expected_calls: int = Field(ge=1)
    paid_api: bool
    reasons: list[str] = Field(default_factory=list)


class APICostEstimator:
    def estimate(self, plan: APIRequestPlan) -> APICostEstimate:
        cost = round(plan.estimated_unit_cost_usd * plan.expected_calls, 4)
        latency = 150 + min(plan.expected_calls * 25, 2000)
        rate_limit = 60 if plan.lane.value == "blue" else 20
        reasons = ["estimated_from_request_plan"]
        if plan.paid_api:
            reasons.append("paid_api")
        return APICostEstimate(
            estimated_cost_usd=cost,
            estimated_latency_ms=latency,
            rate_limit_per_minute=rate_limit,
            expected_calls=plan.expected_calls,
            paid_api=plan.paid_api,
            reasons=reasons,
        )
