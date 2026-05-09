from __future__ import annotations

import pytest

from sentinel.organs import (
    ExistingOrganRealWorldGauntletRunner,
    ExistingOrgansRuntimePromotionPlanner,
    RuntimePromotionCandidate,
    RuntimePromotionPlan,
)


def test_runtime_promotion_plan_consumes_p6o_gauntlet_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_GAUNTLET_API_KEY", "secret-value")
    gauntlet = ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path)).run()

    plan = ExistingOrgansRuntimePromotionPlanner().build(gauntlet)

    assert plan.phase == "P6P_EXISTING_ORGANS_RUNTIME_PROMOTION_PLAN"
    assert plan.source_report_id == gauntlet.id
    assert plan.no_new_organ_family is True
    assert plan.authority_expansion is False
    assert plan.priority_order[:3] == [
        "desktop_workspace_l6",
        "browser_controlled_navigation_l6",
        "api_authenticated_read_l6",
    ]
    assert len(plan.candidates) >= 8
    assert all(candidate.evidence_refs for candidate in plan.candidates)
    assert all(candidate.required_receipts for candidate in plan.candidates)


def test_runtime_promotion_plan_ranks_existing_organs_not_new_code_shell(tmp_path):
    gauntlet = ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path)).run()
    plan = ExistingOrgansRuntimePromotionPlanner().build(gauntlet)

    promoted = {candidate.promotion_id: candidate for candidate in plan.candidates}

    assert promoted["desktop_workspace_l6"].priority_rank == 1
    assert promoted["desktop_workspace_l6"].organ == "desktop"
    assert promoted["desktop_workspace_l6"].decision == "promote_next"
    assert "code_shell" not in {candidate.organ for candidate in plan.candidates}
    assert plan.next_build_block == "desktop_workspace_l6"
    assert plan.deferred_new_organ_families == ["code_shell", "memory_self_improvement", "new_desktop_family"]


def test_each_promotion_candidate_has_adapter_authority_finalgate_and_rollback(tmp_path):
    plan = ExistingOrgansRuntimePromotionPlanner().build(ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path)).run())

    for candidate in plan.candidates:
        assert isinstance(candidate, RuntimePromotionCandidate)
        assert candidate.from_level == "L5"
        assert candidate.target_level == "L6"
        assert candidate.required_adapters
        assert candidate.required_authority
        assert candidate.required_finalgate is True
        assert candidate.rollback_or_disable_plan
        assert candidate.kill_switch_required is True
        assert candidate.receipts_required is True


def test_high_power_surfaces_are_unlockable_but_real_payment_broker_and_live_send_deferred(tmp_path):
    plan = ExistingOrgansRuntimePromotionPlanner().build(ExistingOrganRealWorldGauntletRunner(tmp_root=str(tmp_path)).run())

    assert "real_payment_provider" in plan.unlockable_high_power_surfaces
    assert "real_broker_execution" in plan.unlockable_high_power_surfaces
    assert "live_channel_send" in plan.unlockable_high_power_surfaces
    assert plan.deferred_high_power_surfaces["real_payment_provider"] == "requires provider test-mode promotion and spend FinalGate"
    assert plan.deferred_high_power_surfaces["real_broker_execution"] == "requires live paper feed, risk monitor, broker authority, and trading FinalGate"
    assert plan.deferred_high_power_surfaces["live_channel_send"] == "requires provider draft promotion, recipient provenance, send gate, and channel FinalGate"
    assert "misuse objectives" in plan.black_lane_objectives
    assert "credential theft" in plan.black_lane_objectives


def test_runtime_promotion_plan_rejects_empty_authority_expanding_or_unbacked_candidates():
    with pytest.raises(ValueError, match="requires candidates"):
        RuntimePromotionPlan(
            source_report_id="empty",
            candidates=[],
            priority_order=[],
            next_build_block="desktop_workspace_l6",
            deferred_new_organ_families=["code_shell"],
            unlockable_high_power_surfaces=["real_payment_provider"],
            deferred_high_power_surfaces={"real_payment_provider": "requires promotion"},
            black_lane_objectives=["misuse objectives"],
        )

    with pytest.raises(ValueError, match="evidence refs"):
        RuntimePromotionCandidate(
            promotion_id="x",
            organ="desktop",
            surface="workspace",
            priority_rank=1,
            from_level="L5",
            target_level="L6",
            decision="promote_next",
            reason="x",
            evidence_refs=[],
            required_adapters=["adapter"],
            required_authority=["authority"],
            required_receipts=["receipt"],
            rollback_or_disable_plan=["disable"],
        )

    with pytest.raises(ValueError, match="cannot expand authority"):
        RuntimePromotionCandidate(
            promotion_id="x",
            organ="desktop",
            surface="workspace",
            priority_rank=1,
            from_level="L5",
            target_level="L6",
            decision="promote_next",
            reason="x",
            evidence_refs=["ev"],
            required_adapters=["adapter"],
            required_authority=["authority"],
            required_receipts=["receipt"],
            rollback_or_disable_plan=["disable"],
            authority_expansion=True,
        )
