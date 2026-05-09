from __future__ import annotations

import pytest

from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs import (
    APICostEstimator,
    APIPrivacyRiskClassifier,
    APIRequestPlan,
    AutonomyRiskLane,
    ExternalAPIAllowlist,
    ExternalAPIDryRunPlanner,
    ExternalAPIRequestReceipt,
    ExternalOrganRegistry,
    OrganAuthorityEvaluator,
    build_external_api_organ_contract,
)
from sentinel.shared.enums import MissionMode, MissionType


def mission(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_p6d",
        "mission_type": MissionType.RESEARCH_SUMMARY,
        "mission_title": "P6D external API organ",
        "mission_objective": "Plan external API requests without live execution.",
        "success_criteria": ["dry-run request receipt"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["public_web", "external_api"],
        "allowed_tools": ["external_api_organ"],
        "allowed_actions": ["api_read_request_plan", "api_paid_request_plan", "api_mutation_request_plan"],
        "forbidden_actions": ["credential_access", "payment", "trade_order", "account_create"],
        "allowed_domains": ["api.example.com"],
        "max_actions": 8,
        "max_cost_usd": 3.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def authority_for(action: str, **mission_overrides):
    env = mission(**mission_overrides)
    contract = build_external_api_organ_contract()
    authority = OrganAuthorityEvaluator().evaluate(
        env,
        contract,
        requested_actions=[action],
        requested_tools=["external_api_organ"],
        requested_domains=["api.example.com"],
    )
    return env, contract, authority


def read_plan(**overrides) -> APIRequestPlan:
    data = {
        "vendor": "ExampleAPI",
        "domain": "api.example.com",
        "method": "GET",
        "path": "/v1/public/company",
        "action": "api_read_request_plan",
        "query_params": {"q": "sentinel"},
        "data_categories": ["public_company_data"],
        "evidence_refs": ["ev_api_need"],
    }
    data.update(overrides)
    return APIRequestPlan(**data)


def test_external_api_contract_registers_without_execution():
    contract = build_external_api_organ_contract()
    registry = ExternalOrganRegistry().register(contract)

    registered = registry.get("external_api_organ")
    assert registered.organ_type.value == "external_api"
    assert registered.execution_enabled is False
    assert "api_read_request_plan" in registered.supported_actions


def test_request_plan_is_dry_run_shape_and_never_executes():
    plan = read_plan()

    assert plan.execution_started is False
    assert plan.live_execution_requested is False
    assert plan.method == "GET"
    assert plan.lane == AutonomyRiskLane.BLUE


def test_allowlist_required_for_future_live_use_but_dry_run_can_plan():
    plan = read_plan(domain="api.not-allowed.example")
    decision = ExternalAPIAllowlist(allowed_vendors=["ExampleAPI"], allowed_domains=["api.example.com"]).evaluate(plan)

    assert decision.dry_run_allowed is True
    assert decision.live_allowed is False
    assert "domain_not_allowlisted:api.not-allowed.example" in decision.errors


def test_cost_estimator_records_cost_latency_and_rate_limit():
    plan = read_plan(estimated_unit_cost_usd=0.03, expected_calls=10)

    estimate = APICostEstimator().estimate(plan)

    assert estimate.estimated_cost_usd == 0.3
    assert estimate.estimated_latency_ms > 0
    assert estimate.rate_limit_per_minute > 0
    assert estimate.paid_api is True


def test_privacy_classifier_flags_personal_or_sensitive_data():
    plan = read_plan(data_categories=["email_address", "phone_number", "public_company_data"])

    profile = APIPrivacyRiskClassifier().classify(plan)

    assert profile.risk_level == "high"
    assert profile.contains_personal_data is True
    assert "personal_data_detected" in profile.reasons


def test_api_dry_run_receipt_is_deterministic_and_non_executing():
    _, _, authority = authority_for("api_read_request_plan")
    plan = read_plan()
    allowlist = ExternalAPIAllowlist(allowed_vendors=["ExampleAPI"], allowed_domains=["api.example.com"]).evaluate(plan)
    cost = APICostEstimator().estimate(plan)
    privacy = APIPrivacyRiskClassifier().classify(plan)

    receipt = ExternalAPIDryRunPlanner().create_receipt(
        plan,
        authority,
        allowlist=allowlist,
        cost_estimate=cost,
        privacy_risk=privacy,
        trace_refs=["trace_api_plan"],
    )

    assert receipt.execution_started is False
    assert receipt.request_hash == receipt.expected_hash()
    assert receipt.authority_expansion is False


def test_read_only_api_can_be_blue_lane_when_authorized():
    _, _, authority = authority_for("api_read_request_plan")
    plan = read_plan(method="GET")

    receipt = ExternalAPIDryRunPlanner().create_receipt(
        plan,
        authority,
        allowlist=ExternalAPIAllowlist(allowed_vendors=["ExampleAPI"], allowed_domains=["api.example.com"]).evaluate(plan),
        cost_estimate=APICostEstimator().estimate(plan),
        privacy_risk=APIPrivacyRiskClassifier().classify(plan),
        trace_refs=["trace_api_blue"],
    )

    assert receipt.lane == AutonomyRiskLane.BLUE.value
    assert receipt.future_live_allowed is True


def test_paid_mutation_and_account_affecting_api_remain_dry_run_until_future_promotion():
    _, _, authority = authority_for("api_mutation_request_plan")
    plan = read_plan(
        method="POST",
        action="api_mutation_request_plan",
        path="/v1/accounts/update",
        body_summary={"operation": "update account setting"},
        paid_api=True,
        account_affecting=True,
    )

    receipt = ExternalAPIDryRunPlanner().create_receipt(
        plan,
        authority,
        allowlist=ExternalAPIAllowlist(allowed_vendors=["ExampleAPI"], allowed_domains=["api.example.com"]).evaluate(plan),
        cost_estimate=APICostEstimator().estimate(plan),
        privacy_risk=APIPrivacyRiskClassifier().classify(plan),
        trace_refs=["trace_api_orange"],
    )

    assert receipt.lane == AutonomyRiskLane.RED.value
    assert receipt.future_live_allowed is False
    assert receipt.execution_started is False


def test_raw_credentials_are_blocked_and_credential_ref_is_placeholder_only():
    with pytest.raises(ValueError, match="raw credential"):
        read_plan(headers={"Authorization": "Bearer sk-live-secret"})

    plan = read_plan(credential_ref="credref_market_data_readonly")
    assert plan.credential_ref == "credref_market_data_readonly"
    assert plan.raw_secret_present is False


def test_no_real_external_api_execution_in_p6d():
    _, _, authority = authority_for("api_read_request_plan")
    plan = read_plan()

    with pytest.raises(ValueError, match="P6D does not execute external API requests"):
        ExternalAPIDryRunPlanner().execute(plan, authority)


def test_api_receipt_requires_trace_and_evidence_refs():
    _, _, authority = authority_for("api_read_request_plan")
    plan = read_plan()
    allowlist = ExternalAPIAllowlist(allowed_vendors=["ExampleAPI"], allowed_domains=["api.example.com"]).evaluate(plan)
    cost = APICostEstimator().estimate(plan)
    privacy = APIPrivacyRiskClassifier().classify(plan)

    with pytest.raises(ValueError, match="requires trace refs"):
        ExternalAPIDryRunPlanner().create_receipt(
            plan,
            authority,
            allowlist=allowlist,
            cost_estimate=cost,
            privacy_risk=privacy,
            trace_refs=[],
        )

    with pytest.raises(ValueError, match="requires evidence refs"):
        ExternalAPIRequestReceipt(
            mission_id=authority.mission_id,
            organ_id=authority.organ_id,
            action=plan.action,
            vendor=plan.vendor,
            domain=plan.domain,
            method=plan.method,
            path=plan.path,
            lane=AutonomyRiskLane.BLUE.value,
            preview={},
            evidence_refs=[],
            trace_refs=["trace_api"],
        )
