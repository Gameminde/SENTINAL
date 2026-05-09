from __future__ import annotations

from sentinel.organs.authority import OrganAuthorityEnvelope
from sentinel.organs.external_api.allowlist import APIAllowlistDecision
from sentinel.organs.external_api.cost_estimator import APICostEstimate
from sentinel.organs.external_api.privacy_risk import APIPrivacyRiskProfile
from sentinel.organs.external_api.receipts import ExternalAPIRequestReceipt
from sentinel.organs.external_api.request_plan import APIRequestPlan


class ExternalAPIDryRunPlanner:
    def create_receipt(
        self,
        plan: APIRequestPlan,
        authority: OrganAuthorityEnvelope,
        *,
        allowlist: APIAllowlistDecision,
        cost_estimate: APICostEstimate,
        privacy_risk: APIPrivacyRiskProfile,
        trace_refs: list[str],
    ) -> ExternalAPIRequestReceipt:
        future_live_allowed = (
            plan.lane.value == "blue"
            and allowlist.live_allowed
            and not authority.errors
            and privacy_risk.risk_level in {"low", "medium"}
        )
        if plan.lane.value != "blue" or plan.paid_api or plan.mutation or plan.account_affecting:
            future_live_allowed = False
        return ExternalAPIRequestReceipt(
            mission_id=authority.mission_id,
            organ_id=authority.organ_id,
            action=plan.action,
            vendor=plan.vendor,
            domain=plan.domain,
            method=plan.method,
            path=plan.path,
            lane=plan.lane.value,
            preview={
                "query_params": plan.query_params,
                "body_summary": plan.body_summary,
                "credential_ref": plan.credential_ref,
                "allowlist_live_allowed": allowlist.live_allowed,
                "allowlist_errors": allowlist.errors,
                "estimated_cost_usd": cost_estimate.estimated_cost_usd,
                "estimated_latency_ms": cost_estimate.estimated_latency_ms,
                "rate_limit_per_minute": cost_estimate.rate_limit_per_minute,
                "privacy_risk_level": privacy_risk.risk_level,
                "privacy_reasons": privacy_risk.reasons,
                "authority_errors": authority.errors,
            },
            evidence_refs=list(plan.evidence_refs),
            trace_refs=[*plan.trace_refs, *authority.trace_refs, *trace_refs],
            future_live_allowed=future_live_allowed,
        )

    def execute(self, plan: APIRequestPlan, authority: OrganAuthorityEnvelope) -> None:
        raise ValueError("P6D does not execute external API requests.")
