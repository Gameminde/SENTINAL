from __future__ import annotations

import pytest

from sentinel.agent import EventBus
from sentinel.organs import (
    AgentLabHarvestSource,
    AgentLabOrganHarvestClassifier,
    AgentLabOrganHarvestMatrix,
    HarvestPowerFamily,
    HarvestSourceKind,
    OrganHarvestCandidate,
    OrganPromotionLevel,
    OrganType,
)


def build_matrix() -> AgentLabOrganHarvestMatrix:
    return AgentLabOrganHarvestClassifier().build_default_matrix()


def test_default_harvest_matrix_is_deterministic_and_source_backed():
    first = build_matrix()
    second = build_matrix()

    assert first.id == second.id
    assert [candidate.id for candidate in first.candidates] == [candidate.id for candidate in second.candidates]
    assert len(first.candidates) == 6
    assert {candidate.source.source_system for candidate in first.candidates} == {
        "OpenClaw",
        "Hermes",
        "OpenJarvis",
        "JARVIS",
        "financial-services",
        "CloakBrowser",
    }
    assert all(candidate.evidence_refs for candidate in first.candidates)
    assert all(candidate.source.local_path for candidate in first.candidates)


def test_every_candidate_targets_l2_contract_without_runtime_power():
    matrix = build_matrix()

    assert matrix.promotion_level == OrganPromotionLevel.L2_SENTINEL_CONTRACT
    assert matrix.runtime_powers_added == 0
    assert matrix.vendor_code_copied is False
    assert matrix.vendor_runtime_bridge is False
    assert matrix.authority_expansion is False
    assert all(candidate.target_promotion_level == OrganPromotionLevel.L2_SENTINEL_CONTRACT for candidate in matrix.candidates)
    assert all(candidate.runtime_verified is False for candidate in matrix.candidates)


def test_required_power_families_are_classified():
    matrix = build_matrix()

    assert matrix.by_power_family(HarvestPowerFamily.ACTION_KERNEL)[0].sentinel_rewrite == "SentinelActionKernel"
    assert matrix.by_power_family(HarvestPowerFamily.MEMORY_SKILL)[0].sentinel_rewrite == "SentinelMemorySkillSpec"
    assert matrix.by_power_family(HarvestPowerFamily.COST_ROUTING)[0].sentinel_rewrite == "SentinelCostRouter"
    assert matrix.by_power_family(HarvestPowerFamily.SIDECAR_DESKTOP)[0].organ_type == OrganType.DESKTOP_SIDECAR
    assert matrix.by_power_family(HarvestPowerFamily.FINANCE_OPERATOR)[0].organ_type == OrganType.FINANCE
    assert matrix.by_power_family(HarvestPowerFamily.BROWSER_POWER)[0].organ_type == OrganType.BROWSER


def test_vendor_references_are_rewrite_knowledge_only():
    matrix = build_matrix()
    refs = matrix.vendor_references()

    assert len(refs) == len(matrix.candidates)
    assert all(ref.evidence_refs for ref in refs)
    assert all(ref.vendor_code_copied is False for ref in refs)
    assert all(ref.vendor_runtime_bridge is False for ref in refs)
    assert all(ref.runtime_verified is False for ref in refs)


def test_harvest_candidate_rejects_vendor_code_runtime_bridge_and_authority_expansion():
    source = AgentLabHarvestSource(
        source_system="x",
        source_kind=HarvestSourceKind.FINAL_FORENSIC_REPORT,
        local_path="agent-lab/audits/final/x.md",
        evidence_refs=["ev"],
    )

    base = {
        "source": source,
        "power_family": HarvestPowerFamily.ACTION_KERNEL,
        "organ_type": OrganType.GENERIC,
        "mechanism": "m",
        "sentinel_rewrite": "r",
        "target_phase": "P6B",
        "required_controls": ["authority_mapping"],
        "evidence_refs": ["ev"],
    }
    with pytest.raises(ValueError, match="vendor code"):
        OrganHarvestCandidate(**base, vendor_code_copied=True)
    with pytest.raises(ValueError, match="vendor runtime"):
        OrganHarvestCandidate(**base, vendor_runtime_bridge=True)
    with pytest.raises(ValueError, match="expand authority"):
        OrganHarvestCandidate(**base, authority_expansion=True)


def test_candidate_evidence_must_come_from_declared_source():
    source = AgentLabHarvestSource(
        source_system="x",
        source_kind=HarvestSourceKind.FINAL_FORENSIC_REPORT,
        local_path="agent-lab/audits/final/x.md",
        evidence_refs=["ev_a"],
    )

    with pytest.raises(ValueError, match="evidence refs must come from its source"):
        OrganHarvestCandidate(
            source=source,
            power_family=HarvestPowerFamily.ACTION_KERNEL,
            organ_type=OrganType.GENERIC,
            mechanism="m",
            sentinel_rewrite="r",
            target_phase="P6B",
            required_controls=["authority_mapping"],
            evidence_refs=["ev_b"],
        )


def test_matrix_rejects_runtime_power_vendor_bridge_and_duplicates():
    matrix = build_matrix()

    with pytest.raises(ValueError, match="runtime powers"):
        AgentLabOrganHarvestMatrix(candidates=matrix.candidates, runtime_powers_added=1)
    with pytest.raises(ValueError, match="vendor runtime"):
        AgentLabOrganHarvestMatrix(candidates=matrix.candidates, vendor_runtime_bridge=True)
    with pytest.raises(ValueError, match="duplicate candidates"):
        AgentLabOrganHarvestMatrix(candidates=[matrix.candidates[0], matrix.candidates[0]])


def test_evented_matrix_records_trace_without_execution():
    bus = EventBus("mission_p6b")

    matrix = AgentLabOrganHarvestClassifier().build_default_matrix(event_bus=bus)

    assert matrix.trace_refs
    assert all(candidate.trace_refs for candidate in matrix.candidates)
    assert bus.verify_chain() is True
    assert bus.events()[-1].event_type == "organ_harvest_matrix_built"
    assert bus.events()[-1].payload["runtime_powers_added"] == 0
    assert bus.events()[-1].payload["authority_expansion"] is False


def test_high_risk_runtime_surfaces_remain_blocked_as_findings_only():
    matrix = build_matrix()
    blocked = {surface for candidate in matrix.candidates for surface in candidate.blocked_runtime_surfaces}

    assert "shell_execution" in blocked
    assert "payment_execution" in blocked
    assert "trade_execution" in blocked
    assert "credential_access" in blocked
    assert "fake_identity" in blocked
    assert "raw_shell" in blocked
