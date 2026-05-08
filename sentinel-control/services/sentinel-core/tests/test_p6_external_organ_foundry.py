from __future__ import annotations

import pytest

from sentinel.agent import EventBus
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs import (
    ExternalOrganContract,
    ExternalOrganRegistry,
    OrganAuthorityEnvelope,
    OrganAuthorityEvaluator,
    OrganCapability,
    OrganDryRunReceipt,
    OrganExecutionReceipt,
    OrganKillSwitch,
    OrganPromotionGate,
    OrganPromotionLevel,
    OrganReplayRecord,
    OrganRiskLevel,
    OrganRiskProfiler,
    OrganType,
    VendorHarvestReference,
)
from sentinel.shared.enums import MissionMode, MissionType


def mission(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_p6a",
        "mission_type": MissionType.RESEARCH_SUMMARY,
        "mission_title": "P6A organ foundry",
        "mission_objective": "Plan external organ contracts without external execution.",
        "success_criteria": ["Contract exists", "Dry-run exists"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace", "public_web"],
        "allowed_tools": ["browser_organ", "safe_file_writer"],
        "allowed_actions": ["browser_read_public_page", "write_trace"],
        "forbidden_actions": ["payment", "trade_order", "credential_access", "account_create"],
        "allowed_domains": ["example.com"],
        "allowed_accounts": [],
        "max_actions": 12,
        "max_cost_usd": 2.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def harvest_ref() -> VendorHarvestReference:
    return VendorHarvestReference(
        source_system="CloakBrowser",
        source_url="https://github.com/CloakHQ/CloakBrowser",
        mechanism="Playwright-compatible browser reliability and fingerprint controls.",
        sentinel_rewrite="BrowserPowerGovernor",
        risk_notes=["misuse objectives require classification"],
        evidence_refs=["src_cloak_readme"],
    )


def browser_contract(**overrides) -> ExternalOrganContract:
    data = {
        "organ_name": "browser_power_governor",
        "organ_type": OrganType.BROWSER,
        "description": "Classifies and governs browser powers without direct execution.",
        "promotion_level": OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        "capabilities": [
            OrganCapability(
                name="browser_reliability",
                description="Plan browser reliability profiles.",
                actions=["browser_read_public_page"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["src_cloak_readme"],
            )
        ],
        "supported_actions": ["browser_read_public_page", "browser_submit"],
        "authority_fields": ["allowed_domains", "allowed_actions"],
        "source_refs": [harvest_ref()],
    }
    data.update(overrides)
    return ExternalOrganContract(**data)


def capital_contract(**overrides) -> ExternalOrganContract:
    data = {
        "organ_name": "capital_operator_contract",
        "organ_type": OrganType.CAPITAL_OPERATOR,
        "description": "Classifies capital operator powers without spend execution.",
        "promotion_level": OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        "capabilities": [
            OrganCapability(
                name="capital_planning",
                description="Plan capital allocation without execution.",
                actions=["spend_money", "trade_order"],
                authority_fields=["allowed_actions"],
                evidence_refs=["src_financial_services"],
            )
        ],
        "supported_actions": ["spend_money", "trade_order"],
        "authority_fields": ["allowed_actions"],
        "source_refs": [
            VendorHarvestReference(
                source_system="financial-services",
                source_url="https://github.com/anthropics/financial-services",
                mechanism="Financial workflow patterns and risk controls.",
                sentinel_rewrite="CapitalOperatorMode",
                evidence_refs=["src_financial_services"],
            )
        ],
    }
    data.update(overrides)
    return ExternalOrganContract(**data)


def test_contract_registers_without_execution():
    bus = EventBus("mission_p6a")
    contract = browser_contract()

    registry = ExternalOrganRegistry().register(contract, event_bus=bus)

    assert registry.get("browser_power_governor").id == contract.id
    assert contract.execution_enabled is False
    assert bus.verify_chain() is True
    assert bus.events()[-1].payload["execution_enabled"] is False


def test_contract_rejects_vendor_code_or_runtime_bridge():
    with pytest.raises(ValueError, match="vendor code"):
        browser_contract(vendor_code_copied=True)
    with pytest.raises(ValueError, match="vendor runtime"):
        browser_contract(vendor_runtime_bridge=True)
    with pytest.raises(ValueError, match="requires source refs"):
        browser_contract(source_refs=[])


def test_contract_requires_authority_risk_dry_run_trace_and_kill_switch_compatibility():
    with pytest.raises(ValueError, match="authority mapping"):
        browser_contract(authority_fields=[])
    with pytest.raises(ValueError, match="risk profile schema"):
        browser_contract(required_risk_profile_fields=[])
    with pytest.raises(ValueError, match="dry-run receipt schema"):
        browser_contract(required_dry_run_fields=[])
    with pytest.raises(ValueError, match="execution receipt schema"):
        browser_contract(required_receipt_fields=[])
    with pytest.raises(ValueError, match="trace event compatibility"):
        browser_contract(required_trace_events=[])
    with pytest.raises(ValueError, match="kill-switch compatibility"):
        browser_contract(kill_switch_required=False)
    with pytest.raises(ValueError, match="FinalGate compatibility"):
        browser_contract(final_gate_required=False)


def test_authority_envelope_is_subset_of_root_mission_authority():
    env = mission()
    contract = browser_contract()

    authority = OrganAuthorityEvaluator().evaluate(
        env,
        contract,
        requested_actions=["browser_read_public_page"],
        requested_tools=["browser_organ"],
        requested_domains=["example.com"],
    )

    assert authority.errors == []
    assert authority.allowed_actions == ["browser_read_public_page"]
    assert authority.execution_authorized is False
    assert authority.dry_run_only is True
    assert authority.authority_expansion is False


def test_authority_rejects_out_of_scope_actions_and_domains():
    env = mission()
    contract = browser_contract()

    authority = OrganAuthorityEvaluator().evaluate(
        env,
        contract,
        requested_actions=["browser_submit"],
        requested_tools=["browser_organ"],
        requested_domains=["evil.example"],
    )

    assert "action_outside_root_authority:browser_submit" in authority.errors
    assert "domain_outside_root_authority:evil.example" in authority.errors
    assert authority.allowed_actions == []


def test_black_zone_payment_trading_account_and_credential_actions_are_blocked_by_default():
    env = mission(
        allowed_tools=["capital_organ"],
        allowed_actions=["spend_money", "trade_order", "account_create", "credential_access"],
        forbidden_actions=[],
    )
    contract = capital_contract(supported_actions=["spend_money", "trade_order", "account_create", "credential_access"])

    authority = OrganAuthorityEvaluator().evaluate(
        env,
        contract,
        requested_actions=["spend_money", "trade_order", "account_create", "credential_access"],
        requested_tools=["capital_organ"],
    )

    assert "black_zone_action_blocked_by_default:spend_money" in authority.errors
    assert "black_zone_action_blocked_by_default:trade_order" in authority.errors
    assert "black_zone_action_blocked_by_default:account_create" in authority.errors
    assert "black_zone_action_blocked_by_default:credential_access" in authority.errors
    assert authority.execution_authorized is False
    assert authority.allowed_actions == []


def test_signals_workspace_memory_and_expected_profit_cannot_expand_authority():
    env = mission(allowed_actions=["browser_read_public_page"])
    contract = browser_contract()

    authority = OrganAuthorityEvaluator().evaluate(
        env,
        contract,
        requested_actions=["browser_submit"],
        context_signals={"roi_signal": "strong", "allowed_actions": ["browser_submit"]},
        workspace_context={"claim": "submit is useful"},
        memory_context={"past_success": True},
        expected_profit=1000.0,
    )

    assert "action_outside_root_authority:browser_submit" in authority.errors
    assert authority.authority_expansion is False
    assert authority.allowed_actions == []


def test_risk_profile_detects_misuse_objective_without_discarding_capability():
    env = mission(allowed_actions=["browser_read_public_page", "browser_submit"])
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_submit"])

    profile = OrganRiskProfiler().profile(contract, authority, action="browser_submit", objective_tags=["fake_identity"])

    assert profile.misuse_objective_detected is True
    assert profile.risk_level == OrganRiskLevel.CRITICAL
    assert profile.requires_special_authority is True
    assert "misuse_objective_detected" in profile.reasons


def test_dry_run_receipt_requires_evidence_and_never_executes():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")

    receipt = OrganDryRunReceipt.create(
        authority,
        risk,
        reason="Preview browser evidence capture.",
        preview={"url": "https://example.com"},
        evidence_refs=["ev_browser_need"],
    )

    assert receipt.preview_hash
    assert receipt.execution_started is False
    with pytest.raises(ValueError, match="requires evidence refs"):
        OrganDryRunReceipt.create(authority, risk, reason="bad", preview={}, evidence_refs=[])


def test_dry_run_receipt_rejects_forged_preview_hash():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")
    receipt = OrganDryRunReceipt.create(authority, risk, reason="Preview.", preview={"url": "https://example.com"}, evidence_refs=["ev"])

    forged = receipt.model_copy(update={"preview_hash": "forged"})
    with pytest.raises(ValueError, match="preview hash mismatch"):
        OrganReplayRecord.replay(env.id, dry_run_receipts=[forged])


def test_execution_receipt_cannot_start_before_l6():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")
    dry_run = OrganDryRunReceipt.create(authority, risk, reason="Preview.", preview={"url": "https://example.com"}, evidence_refs=["ev"])

    planned = OrganExecutionReceipt.planned_only(dry_run, promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT, output_summary="No execution.")
    assert planned.execution_started is False

    with pytest.raises(ValueError, match="before L6"):
        OrganExecutionReceipt(
            mission_id=dry_run.mission_id,
            organ_id=dry_run.organ_id,
            action=dry_run.action,
            dry_run_receipt_id=dry_run.id,
            promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
            output_summary="bad",
            execution_started=True,
            execution_completed=True,
            trace_refs=["trace_1"],
        )


def test_dry_run_only_authority_cannot_create_started_execution_receipt():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")
    dry_run = OrganDryRunReceipt.create(authority, risk, reason="Preview.", preview={"url": "https://example.com"}, evidence_refs=["ev"])
    kill_switch = OrganKillSwitch(mission_id=env.id, organ_id=contract.id)

    with pytest.raises(ValueError, match="not execution authorized"):
        OrganExecutionReceipt.started(
            dry_run,
            authority,
            kill_switch,
            promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            output_summary="blocked",
            trace_refs=["trace_1"],
        )


def test_kill_switch_blocks_execution_shaped_requests():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    executable_authority = OrganAuthorityEnvelope(
        id=authority.id,
        mission_id=authority.mission_id,
        root_authority_id=authority.root_authority_id,
        organ_id=authority.organ_id,
        organ_name=authority.organ_name,
        allowed_actions=authority.allowed_actions,
        allowed_tools=authority.allowed_tools,
        allowed_domains=authority.allowed_domains,
        allowed_accounts=authority.allowed_accounts,
        allowed_paths=authority.allowed_paths,
        max_actions=authority.max_actions,
        max_cost_usd=authority.max_cost_usd,
        execution_authorized=True,
        dry_run_only=False,
    )
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")
    dry_run = OrganDryRunReceipt.create(authority, risk, reason="Preview.", preview={"url": "https://example.com"}, evidence_refs=["ev"])
    kill_switch = OrganKillSwitch(mission_id=env.id, organ_id=contract.id).trigger(reason="risk spike")

    with pytest.raises(ValueError, match="kill switch"):
        OrganExecutionReceipt.started(
            dry_run,
            executable_authority,
            kill_switch,
            promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            output_summary="blocked",
            trace_refs=["trace_1"],
        )


def test_promotion_gate_requires_fake_eval_dry_run_receipts_and_finalgate_for_execution_levels():
    contract = browser_contract()

    decision = OrganPromotionGate().evaluate(contract, target_level=OrganPromotionLevel.L6_LIMITED_EXECUTION)

    assert decision.accepted is False
    assert "fake_eval_required" in decision.errors
    assert "dry_run_schema_required" in decision.errors
    assert "receipt_schema_required" in decision.errors
    assert "kill_switch_required" in decision.errors
    assert "eval_dataset_required" in decision.errors
    assert "risk_map_required" in decision.errors
    assert "failure_modes_required" in decision.errors
    assert "rollback_disable_plan_required" in decision.errors
    assert "final_gate_adapter_required" in decision.errors
    assert decision.execution_enabled is False


def test_promotion_gate_accepts_l3_with_fake_eval():
    contract = browser_contract()

    decision = OrganPromotionGate().evaluate(
        contract,
        target_level=OrganPromotionLevel.L3_FAKE_EVAL,
        fake_eval_passed=True,
        eval_dataset_present=True,
    )

    assert decision.accepted is True
    assert decision.execution_enabled is False


def test_kill_switch_disables_organ_execution():
    bus = EventBus("mission_p6a")

    switch = OrganKillSwitch(mission_id="mission_p6a", organ_id="organ_browser").trigger(reason="risk spike", event_bus=bus)

    assert switch.triggered is True
    assert switch.execution_allowed is False
    assert bus.verify_chain() is True


def test_replay_requires_execution_receipts_to_reference_dry_runs():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")
    dry_run = OrganDryRunReceipt.create(authority, risk, reason="Preview.", preview={"url": "https://example.com"}, evidence_refs=["ev"])
    execution = OrganExecutionReceipt.planned_only(dry_run, promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT, output_summary="No execution.")

    replay = OrganReplayRecord.replay(env.id, dry_run_receipts=[dry_run], execution_receipts=[execution])

    assert replay.accepted is True
    assert replay.errors == []


def test_evented_execution_receipt_preserves_hash_and_trace_chain():
    env = mission()
    bus = EventBus(env.id)
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"], event_bus=bus)
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page", event_bus=bus)
    dry_run = OrganDryRunReceipt.create(
        authority,
        risk,
        reason="Preview.",
        preview={"url": "https://example.com"},
        evidence_refs=["ev"],
        event_bus=bus,
    )

    execution = OrganExecutionReceipt.planned_only(
        dry_run,
        promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        output_summary="No execution.",
        event_bus=bus,
    )
    replay = OrganReplayRecord.replay(env.id, dry_run_receipts=[dry_run], execution_receipts=[execution])

    assert replay.accepted is True
    assert execution.receipt_hash == execution.expected_receipt_hash()
    assert bus.verify_chain() is True


def test_replay_rejects_forged_execution_receipts():
    env = mission()
    contract = browser_contract()
    authority = OrganAuthorityEvaluator().evaluate(env, contract, requested_actions=["browser_read_public_page"])
    risk = OrganRiskProfiler().profile(contract, authority, action="browser_read_public_page")
    dry_run = OrganDryRunReceipt.create(authority, risk, reason="Preview.", preview={"url": "https://example.com"}, evidence_refs=["ev"])
    execution = OrganExecutionReceipt.planned_only(dry_run, promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT, output_summary="No execution.")
    forged = execution.model_copy(update={"receipt_hash": "forged"})

    with pytest.raises(ValueError, match="hash mismatch"):
        OrganReplayRecord.replay(env.id, dry_run_receipts=[dry_run], execution_receipts=[forged])


def test_vendor_harvest_reference_requires_evidence_and_blocks_vendor_bridge():
    with pytest.raises(ValueError, match="requires evidence refs"):
        VendorHarvestReference(source_system="x", mechanism="m", sentinel_rewrite="r", evidence_refs=[])
    with pytest.raises(ValueError, match="runtime bridges"):
        VendorHarvestReference(source_system="x", mechanism="m", sentinel_rewrite="r", evidence_refs=["ev"], vendor_runtime_bridge=True)
