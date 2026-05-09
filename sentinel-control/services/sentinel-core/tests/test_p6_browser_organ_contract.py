from __future__ import annotations

import pytest

from sentinel.mission import MissionAuthorityEnvelope
from sentinel.agent.events import AgentEventType
from sentinel.organs import (
    AutonomyRiskLane,
    BrowserActionPlanReceipt,
    BrowserDetectionBench,
    BrowserDetectionBenchCase,
    BrowserFingerprintRiskProfile,
    BrowserMisuseClassifier,
    BrowserPowerGovernor,
    BrowserPowerLevel,
    BrowserPowerRequest,
    BrowserSessionContinuityPolicy,
    ExternalOrganRegistry,
    OrganAuthorityEvaluator,
    build_browser_organ_contract,
)
from sentinel.shared.enums import MissionMode, MissionType


def mission(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_p6c",
        "mission_type": MissionType.RESEARCH_SUMMARY,
        "mission_title": "P6C browser organ",
        "mission_objective": "Normalize browser powers without adding execution.",
        "success_criteria": ["contract registered"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["public_web"],
        "allowed_tools": ["browser_organ"],
        "allowed_actions": ["browser_read_public_page", "browser_observe_public_page", "browser_interaction_dry_run"],
        "forbidden_actions": ["credential_access", "account_create", "payment", "trade_order"],
        "allowed_domains": ["example.com"],
        "max_actions": 10,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def authority_for(action: str, **mission_overrides):
    env = mission(**mission_overrides)
    contract = build_browser_organ_contract()
    authority = OrganAuthorityEvaluator().evaluate(
        env,
        contract,
        requested_actions=[action],
        requested_tools=["browser_organ"],
        requested_domains=["example.com"],
    )
    return env, contract, authority


def test_browser_organ_contract_registers_through_external_registry():
    contract = build_browser_organ_contract()
    registry = ExternalOrganRegistry().register(contract)

    assert registry.get("browser_power_governor").organ_type.value == "browser"
    assert contract.execution_enabled is False
    assert {capability.name for capability in contract.capabilities} >= {
        "p0_browser_reliability",
        "p1_human_like_operation",
        "p2_fingerprint_consistency",
        "p3_detection_resilience_research",
        "p4_special_authority_stealth",
    }
    assert AgentEventType.BROWSER_ORGAN_POWER_GOVERNED.value in contract.required_trace_events
    assert AgentEventType.BROWSER_ORGAN_MISUSE_CLASSIFIED.value in contract.required_trace_events
    assert AgentEventType.BROWSER_ORGAN_RECEIPT_RECORDED.value in contract.required_trace_events


def test_browser_power_levels_include_p0_to_p5_and_p5_is_misuse_not_deletion():
    values = {level.value for level in BrowserPowerLevel}

    assert "P0_normal_browser_reliability" in values
    assert "P4_special_authority_stealth_operation" in values
    assert "P5_forbidden_misuse_objective" in values
    misuse = BrowserMisuseClassifier().classify(objective_tags=["fake_identity"])
    assert misuse.blocked is True
    assert misuse.capability_deleted is False
    assert misuse.power_level == BrowserPowerLevel.P5_FORBIDDEN_MISUSE_OBJECTIVE


def test_power_governor_downgrades_when_stronger_power_is_not_needed():
    _, _, authority = authority_for("browser_read_public_page")
    request = BrowserPowerRequest(
        action="browser_read_public_page",
        requested_power=BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH,
        needed_power=BrowserPowerLevel.P0_NORMAL_RELIABILITY,
        evidence_refs=["ev_need"],
    )

    decision = BrowserPowerGovernor().govern(request, authority)

    assert decision.allowed is True
    assert decision.selected_power == BrowserPowerLevel.P0_NORMAL_RELIABILITY
    assert decision.lane == AutonomyRiskLane.BLUE
    assert decision.auto_executable is True
    assert "downgraded_to_lowest_needed_power" in decision.reasons


def test_p4_special_authority_is_gated_and_downgraded_to_research_without_authority():
    _, _, authority = authority_for("browser_detection_diagnostic", allowed_actions=["browser_detection_diagnostic"])
    request = BrowserPowerRequest(
        action="browser_detection_diagnostic",
        requested_power=BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH,
        evidence_refs=["ev_stealth"],
    )

    decision = BrowserPowerGovernor().govern(request, authority)

    assert decision.allowed is False
    assert decision.selected_power == BrowserPowerLevel.P3_DETECTION_RESILIENCE_RESEARCH
    assert decision.requires_special_authority is True
    assert decision.requires_authority_extension is True


def test_browser_misuse_classifier_blocks_black_lane_objectives():
    decision = BrowserMisuseClassifier().classify(objective_text="Use browser for KYC bypass and credential theft")

    assert decision.blocked is True
    assert decision.lane == AutonomyRiskLane.BLACK
    assert {"kyc_bypass", "credential_theft"}.issubset(set(decision.matched_terms))


def test_read_only_public_browsing_is_blue_lane_when_authorized_and_traced():
    _, _, authority = authority_for("browser_read_public_page")
    request = BrowserPowerRequest(
        action="browser_read_public_page",
        requested_power=BrowserPowerLevel.P0_NORMAL_RELIABILITY,
        evidence_refs=["ev_public"],
        trace_refs=["trace_policy"],
    )

    decision = BrowserPowerGovernor().govern(request, authority)
    receipt = BrowserActionPlanReceipt.create(
        mission_id=authority.mission_id,
        decision=decision,
        preview={"url": "https://example.com"},
        trace_refs=["trace_receipt"],
    )

    assert decision.lane == AutonomyRiskLane.BLUE
    assert decision.auto_executable is True
    assert receipt.execution_started is False
    assert receipt.plan_hash == receipt.expected_hash()


def test_submit_and_sensitive_actions_remain_dry_run_without_new_execution_power():
    _, _, authority = authority_for("browser_submit", allowed_actions=["browser_submit"])
    request = BrowserPowerRequest(
        action="browser_submit",
        requested_power=BrowserPowerLevel.P1_HUMAN_LIKE_OPERATION,
        evidence_refs=["ev_submit"],
    )

    decision = BrowserPowerGovernor().govern(request, authority)

    assert decision.allowed is False
    assert decision.dry_run_only is True
    assert decision.lane == AutonomyRiskLane.ORANGE


def test_cloak_like_fingerprint_power_is_classified_and_gated_not_discarded():
    profile = BrowserFingerprintRiskProfile(
        requested_power=BrowserPowerLevel.P4_SPECIAL_AUTHORITY_STEALTH,
        web_rtc_leak_prevention=True,
        timezone_proxy_locale_alignment=True,
        persistent_profile_realism=True,
        risk_score=10.0,
        evidence_refs=["ev_cloak"],
    )

    assert profile.requires_special_authority is True
    assert profile.risk_score >= 85.0


def test_session_policy_blocks_credential_storage_in_p6c():
    with pytest.raises(ValueError, match="credential storage"):
        BrowserSessionContinuityPolicy(
            persistent_profile_allowed=True,
            credential_storage_allowed=True,
            allowed_domains=["example.com"],
            evidence_refs=["ev_session"],
        )


def test_detection_bench_is_deterministic_and_non_executing():
    case = BrowserDetectionBenchCase(
        name="fingerprint diagnostic",
        diagnostic="check WebRTC/IP leak posture",
        expected_safe_power=BrowserPowerLevel.P3_DETECTION_RESILIENCE_RESEARCH.value,
        evidence_refs=["ev_diag"],
    )

    report = BrowserDetectionBench().run([case])

    assert report.case_count == 1
    assert report.passed is True
    assert report.authority_expansion is False


def test_browser_receipt_requires_trace_and_evidence_refs():
    _, _, authority = authority_for("browser_read_public_page")
    request = BrowserPowerRequest(
        action="browser_read_public_page",
        requested_power=BrowserPowerLevel.P0_NORMAL_RELIABILITY,
        evidence_refs=["ev_public"],
    )
    decision = BrowserPowerGovernor().govern(request, authority)

    with pytest.raises(ValueError, match="requires trace refs"):
        BrowserActionPlanReceipt.create(mission_id=authority.mission_id, decision=decision, preview={}, trace_refs=[])
