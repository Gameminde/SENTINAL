from __future__ import annotations

import pytest

from sentinel.agent import EventBus
from sentinel.agent.events import AgentEventType
from sentinel.organs import (
    AgentLabImplementationAlignmentBuilder,
    AgentLabImplementationAlignmentEntry,
    AgentLabImplementationAlignmentMatrix,
    OrganPromotionLevel,
)


def build_matrix() -> AgentLabImplementationAlignmentMatrix:
    return AgentLabImplementationAlignmentBuilder().build_default_matrix()


def test_default_alignment_matrix_covers_every_p6c_to_p6i6_organ():
    matrix = build_matrix()

    assert matrix.phase == "P6J_AGENTLAB_IMPLEMENTATION_ALIGNMENT"
    assert matrix.runtime_powers_added == 0
    assert matrix.vendor_code_copied is False
    assert matrix.vendor_runtime_bridge is False
    assert matrix.authority_expansion is False
    assert {entry.organ_phase for entry in matrix.entries} == {
        "P6C_BROWSER_ORGAN_CONTRACT_REVIEW",
        "P6D_EXTERNAL_API_ORGAN_DRY_RUN",
        "P6E_CHANNEL_ORGAN_DRAFT_FIRST",
        "P6F_CREDENTIAL_VAULT_POLICY",
        "P6G_CAPITAL_OPERATOR_SANDBOX",
        "P6H_SPEND_RUNTIME_LIMITED",
        "P6I_TRADING_SPECIAL_AUTHORITY",
        "P6I6_TRADINGAGENTS_HARVEST",
    }


def test_every_alignment_entry_is_source_backed_and_rewritten():
    matrix = build_matrix()

    for entry in matrix.entries:
        assert entry.source_systems
        assert entry.vendor_patterns
        assert entry.sentinel_rewrites
        assert entry.evidence_refs
        assert entry.source_paths
        assert entry.current_sentinel_files
        assert entry.vendor_code_copied is False
        assert entry.vendor_runtime_bridge is False
        assert entry.authority_expansion is False


def test_browser_alignment_maps_openclaw_jarvis_and_cloak_power_governance():
    browser = build_matrix().by_phase("P6C_BROWSER_ORGAN_CONTRACT_REVIEW")

    assert {"OpenClaw", "JARVIS", "CloakBrowser"} <= set(browser.source_systems)
    assert "BrowserPowerGovernor" in browser.sentinel_rewrites
    assert "BrowserMisuseClassifier" in browser.sentinel_rewrites
    assert "BrowserDetectionBench" in browser.sentinel_rewrites
    assert "fake_identity" in browser.dangerous_surfaces
    assert "special_authority_gate" in browser.required_controls


def test_api_channel_credential_alignment_maps_expected_vendor_patterns():
    matrix = build_matrix()
    api = matrix.by_phase("P6D_EXTERNAL_API_ORGAN_DRY_RUN")
    channel = matrix.by_phase("P6E_CHANNEL_ORGAN_DRAFT_FIRST")
    credentials = matrix.by_phase("P6F_CREDENTIAL_VAULT_POLICY")

    assert {"OpenClaw", "OpenJarvis", "financial-services", "TradingAgents"} <= set(api.source_systems)
    assert "ExternalAPIAllowlist" in api.sentinel_rewrites
    assert "APICostEstimator" in api.sentinel_rewrites
    assert "TradingAgentsDataVendorRoute" in api.sentinel_rewrites

    assert {"OpenClaw", "Hermes", "JARVIS"} <= set(channel.source_systems)
    assert "ChannelSendGate" in channel.sentinel_rewrites
    assert "InboundChannelMessage" in channel.sentinel_rewrites

    assert {"JARVIS", "OpenClaw", "Hermes"} <= set(credentials.source_systems)
    assert "CredentialRef" in credentials.sentinel_rewrites
    assert "ScopedCredentialGrant" in credentials.sentinel_rewrites
    assert "CredentialTraceRedactor" in credentials.sentinel_rewrites


def test_capital_spend_and_trading_alignment_maps_finance_and_tradingagents():
    matrix = build_matrix()
    capital = matrix.by_phase("P6G_CAPITAL_OPERATOR_SANDBOX")
    spend = matrix.by_phase("P6H_SPEND_RUNTIME_LIMITED")
    trading = matrix.by_phase("P6I_TRADING_SPECIAL_AUTHORITY")
    tradingagents = matrix.by_phase("P6I6_TRADINGAGENTS_HARVEST")

    assert {"financial-services", "OpenJarvis", "Hermes", "TradingAgents"} <= set(capital.source_systems)
    assert "AdaptiveOperatingEnvelope" in capital.sentinel_rewrites
    assert "BudgetReallocator" in capital.sentinel_rewrites

    assert {"financial-services", "JARVIS", "OpenClaw"} <= set(spend.source_systems)
    assert "SpendAuthorityEnvelope" in spend.sentinel_rewrites
    assert "SpendKillSwitch" in spend.sentinel_rewrites

    assert {"TradingAgents", "financial-services"} <= set(trading.source_systems)
    assert "TradingSpecialAuthority" in trading.sentinel_rewrites
    assert "PaperTradeProvider" in trading.sentinel_rewrites

    assert tradingagents.source_systems == ["TradingAgents"]
    assert "TradingAgentsFirmPlan" in tradingagents.sentinel_rewrites
    assert "TradingOutcomeMemoryEntry" in tradingagents.sentinel_rewrites


def test_dangerous_surfaces_are_blocked_sandboxed_or_promotion_gated():
    matrix = build_matrix()

    for entry in matrix.entries:
        assert set(entry.dangerous_surfaces).issubset(set(entry.blocked_surfaces + entry.sandboxed_surfaces + entry.promotion_gated_surfaces))

    blocked = {surface for entry in matrix.entries for surface in entry.blocked_surfaces}
    gated = {surface for entry in matrix.entries for surface in entry.promotion_gated_surfaces}

    assert "vendor_runtime_bridge" in blocked
    assert "fake_identity" in blocked
    assert "credential_secret_read" in blocked
    assert "real_trading_execution" in gated
    assert "real_payment_execution" in gated
    assert "stealth_browser_operation" in gated


def test_matrix_rejects_missing_rewrite_vendor_bridge_and_authority_expansion():
    entry = build_matrix().entries[0]

    with pytest.raises(ValueError, match="Sentinel rewrites"):
        AgentLabImplementationAlignmentEntry(**entry.model_dump(exclude={"sentinel_rewrites"}), sentinel_rewrites=[])

    with pytest.raises(ValueError, match="vendor runtime"):
        AgentLabImplementationAlignmentEntry(**entry.model_dump(exclude={"vendor_runtime_bridge"}), vendor_runtime_bridge=True)

    with pytest.raises(ValueError, match="expand authority"):
        AgentLabImplementationAlignmentEntry(**entry.model_dump(exclude={"authority_expansion"}), authority_expansion=True)


def test_matrix_rejects_missing_phase_duplicate_phase_and_runtime_power():
    matrix = build_matrix()

    with pytest.raises(ValueError, match="required P6 phases"):
        AgentLabImplementationAlignmentMatrix(entries=matrix.entries[:-1])

    with pytest.raises(ValueError, match="duplicate organ phases"):
        AgentLabImplementationAlignmentMatrix(entries=[matrix.entries[0], matrix.entries[0], *matrix.entries[1:]])

    with pytest.raises(ValueError, match="runtime powers"):
        AgentLabImplementationAlignmentMatrix(entries=matrix.entries, runtime_powers_added=1)


def test_alignment_records_trace_without_execution():
    bus = EventBus("mission_p6j")

    matrix = AgentLabImplementationAlignmentBuilder().build_default_matrix(event_bus=bus)

    assert matrix.trace_refs
    assert bus.verify_chain() is True
    assert bus.events()[-1].event_type == AgentEventType.ORGAN_IMPLEMENTATION_ALIGNMENT_BUILT.value
    assert bus.events()[-1].payload["runtime_powers_added"] == 0
    assert bus.events()[-1].payload["authority_expansion"] is False


def test_alignment_preserves_promotion_ladder_not_forbidden_forever_doctrine():
    matrix = build_matrix()

    assert all(entry.current_promotion_level in OrganPromotionLevel for entry in matrix.entries)
    assert all(entry.target_promotion_level in OrganPromotionLevel for entry in matrix.entries)
    assert any("blocked_by_default_not_forbidden_forever" in entry.required_controls for entry in matrix.entries)
    assert matrix.next_phase == "P6K_ORGANBENCH_EXTERNAL_ORGAN_INTEGRATED_REVIEW"
