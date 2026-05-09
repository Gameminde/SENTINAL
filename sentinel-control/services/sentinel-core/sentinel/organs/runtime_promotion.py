from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.organs.real_world_gauntlet import OrganRealWorldGauntletResult, RealWorldGauntletReport
from sentinel.shared.models import SentinelModel, new_id


class RuntimePromotionCandidate(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("promote"))
    promotion_id: str
    organ: str
    surface: str
    priority_rank: int = Field(gt=0)
    from_level: str
    target_level: str
    decision: str
    reason: str
    evidence_refs: list[str]
    required_adapters: list[str]
    required_authority: list[str]
    required_receipts: list[str]
    rollback_or_disable_plan: list[str]
    required_finalgate: bool = True
    kill_switch_required: bool = True
    receipts_required: bool = True
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> RuntimePromotionCandidate:
        if self.from_level != "L5":
            raise ValueError("RuntimePromotionCandidate must start from L5.")
        if self.target_level != "L6":
            raise ValueError("RuntimePromotionCandidate must target L6.")
        if not self.evidence_refs:
            raise ValueError("RuntimePromotionCandidate requires evidence refs.")
        if not self.required_adapters:
            raise ValueError("RuntimePromotionCandidate requires adapters.")
        if not self.required_authority:
            raise ValueError("RuntimePromotionCandidate requires authority requirements.")
        if not self.required_receipts:
            raise ValueError("RuntimePromotionCandidate requires receipts.")
        if not self.rollback_or_disable_plan:
            raise ValueError("RuntimePromotionCandidate requires rollback or disable plan.")
        if not self.required_finalgate:
            raise ValueError("RuntimePromotionCandidate requires FinalGate.")
        if not self.kill_switch_required:
            raise ValueError("RuntimePromotionCandidate requires kill switch.")
        if not self.receipts_required:
            raise ValueError("RuntimePromotionCandidate requires receipts.")
        if self.authority_expansion:
            raise ValueError("RuntimePromotionCandidate cannot expand authority.")
        return self


class RuntimePromotionPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("promoplan"))
    phase: str = "P6P_EXISTING_ORGANS_RUNTIME_PROMOTION_PLAN"
    source_report_id: str
    candidates: list[RuntimePromotionCandidate]
    priority_order: list[str]
    next_build_block: str
    deferred_new_organ_families: list[str]
    unlockable_high_power_surfaces: list[str]
    deferred_high_power_surfaces: dict[str, str]
    black_lane_objectives: list[str]
    no_new_organ_family: bool = True
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> RuntimePromotionPlan:
        if not self.candidates:
            raise ValueError("RuntimePromotionPlan requires candidates.")
        if not self.priority_order:
            raise ValueError("RuntimePromotionPlan requires priority order.")
        if self.next_build_block not in self.priority_order:
            raise ValueError("next build block must be in priority order.")
        if not self.deferred_new_organ_families:
            raise ValueError("RuntimePromotionPlan requires deferred new organ families.")
        if not self.unlockable_high_power_surfaces:
            raise ValueError("RuntimePromotionPlan requires unlockable high-power surfaces.")
        if not self.deferred_high_power_surfaces:
            raise ValueError("RuntimePromotionPlan requires deferred high-power surfaces.")
        if not self.black_lane_objectives:
            raise ValueError("RuntimePromotionPlan requires Black Lane objectives.")
        if self.authority_expansion:
            raise ValueError("RuntimePromotionPlan cannot expand authority.")
        return self


class ExistingOrgansRuntimePromotionPlanner:
    def build(self, report: RealWorldGauntletReport) -> RuntimePromotionPlan:
        if report.authority_expansion:
            raise ValueError("P6P cannot build from authority-expanding report.")
        if report.phase != "P6O_EXISTING_ORGANS_REAL_WORLD_GAUNTLET":
            raise ValueError("P6P requires P6O gauntlet evidence.")
        candidates = [_candidate(spec, report.organ_results[spec["organ"]]) for spec in _CANDIDATE_SPECS]
        candidates = sorted(candidates, key=lambda item: item.priority_rank)
        return RuntimePromotionPlan(
            source_report_id=report.id,
            candidates=candidates,
            priority_order=[candidate.promotion_id for candidate in candidates],
            next_build_block=candidates[0].promotion_id,
            deferred_new_organ_families=["code_shell", "memory_self_improvement", "new_desktop_family"],
            unlockable_high_power_surfaces=[
                "real_payment_provider",
                "real_broker_execution",
                "live_channel_send",
                "browser_login_session",
                "desktop_screenshot_clipboard",
            ],
            deferred_high_power_surfaces={
                "real_payment_provider": "requires provider test-mode promotion and spend FinalGate",
                "real_broker_execution": "requires live paper feed, risk monitor, broker authority, and trading FinalGate",
                "live_channel_send": "requires provider draft promotion, recipient provenance, send gate, and channel FinalGate",
                "browser_login_session": "requires controlled navigation, session policy, domain authority, and browser FinalGate",
                "desktop_screenshot_clipboard": "requires sanitizer proof, sidecar authority, and desktop FinalGate",
            },
            black_lane_objectives=[
                "misuse objectives",
                "credential theft",
                "fake identity",
                "KYC bypass",
                "illegal spam",
                "unlawful evasion",
                "profit guarantees",
            ],
        )


def _candidate(spec: dict[str, object], result: OrganRealWorldGauntletResult) -> RuntimePromotionCandidate:
    evidence_refs = [receipt.id for receipt in result.receipts]
    evidence_refs.extend(result.extra_receipt_refs)
    if not evidence_refs:
        evidence_refs = [f"p6o:{result.organ}"]
    return RuntimePromotionCandidate(
        promotion_id=str(spec["promotion_id"]),
        organ=result.organ,
        surface=str(spec["surface"]),
        priority_rank=int(spec["priority_rank"]),
        from_level="L5",
        target_level="L6",
        decision=str(spec["decision"]),
        reason=str(spec["reason"]),
        evidence_refs=evidence_refs,
        required_adapters=list(spec["required_adapters"]),
        required_authority=list(spec["required_authority"]),
        required_receipts=list(spec["required_receipts"]),
        rollback_or_disable_plan=list(spec["rollback_or_disable_plan"]),
    )


_CANDIDATE_SPECS = [
    {
        "promotion_id": "desktop_workspace_l6",
        "organ": "desktop",
        "surface": "workspace batch file operations",
        "priority_rank": 1,
        "decision": "promote_next",
        "reason": "Desktop workspace ops are closest to production-scoped execution after P6O.",
        "required_adapters": ["workspace_operation_adapter", "workspace_receipt_adapter"],
        "required_authority": ["workspace_root", "allowed_path_policy", "mutation_scope"],
        "required_receipts": ["desktop_workspace_receipt", "path_containment_receipt"],
        "rollback_or_disable_plan": ["disable workspace mutations", "revert written workspace artifacts"],
    },
    {
        "promotion_id": "browser_controlled_navigation_l6",
        "organ": "browser",
        "surface": "controlled public navigation",
        "priority_rank": 2,
        "decision": "promote_next",
        "reason": "Browser already performs multi-page public reads and can progress to controlled navigation.",
        "required_adapters": ["controlled_navigation_adapter", "browser_receipt_aggregator"],
        "required_authority": ["allowed_domains", "navigation_action_scope", "timeout_budget"],
        "required_receipts": ["browser_navigation_receipt", "page_evidence_receipt"],
        "rollback_or_disable_plan": ["disable navigation adapter", "fall back to public read only"],
    },
    {
        "promotion_id": "api_authenticated_read_l6",
        "organ": "external_api",
        "surface": "authenticated read-only API",
        "priority_rank": 3,
        "decision": "promote_next",
        "reason": "API batch reads are stable; next power is authenticated read-only access through scoped refs.",
        "required_adapters": ["authenticated_read_only_adapter", "rate_limit_ledger"],
        "required_authority": ["allowed_vendor", "allowed_endpoint", "credential_ref_scope"],
        "required_receipts": ["api_response_receipt", "rate_limit_receipt", "credential_ref_receipt"],
        "rollback_or_disable_plan": ["disable authenticated adapter", "fall back to allowlisted unauthenticated reads"],
    },
    {
        "promotion_id": "channel_provider_draft_l6",
        "organ": "channel",
        "surface": "provider draft creation",
        "priority_rank": 4,
        "decision": "promote_next",
        "reason": "Local draft generation works; provider draft creation is the next non-send runtime step.",
        "required_adapters": ["gmail_or_outlook_draft_adapter", "recipient_provenance_adapter"],
        "required_authority": ["channel_provider", "draft_only_action", "recipient_source"],
        "required_receipts": ["provider_draft_receipt", "recipient_provenance_receipt"],
        "rollback_or_disable_plan": ["delete provider draft when possible", "disable provider draft adapter"],
    },
    {
        "promotion_id": "credential_vault_ref_l6",
        "organ": "credentials",
        "surface": "vault-backed credential references",
        "priority_rank": 5,
        "decision": "promote_next",
        "reason": "Credentials remain weakest; vault-backed refs are required before stronger provider organs.",
        "required_adapters": ["vault_ref_adapter", "grant_revocation_ledger"],
        "required_authority": ["credential_ref", "scope_grant", "expiry", "allowed_organ_action"],
        "required_receipts": ["credential_grant_receipt", "redaction_receipt"],
        "rollback_or_disable_plan": ["revoke scoped grant", "disable credential ref adapter"],
    },
    {
        "promotion_id": "capital_roi_feedback_l6",
        "organ": "capital",
        "surface": "live ROI feedback ingestion",
        "priority_rank": 6,
        "decision": "promote_next",
        "reason": "Capital can reason from receipts; next power is feedback from real outcomes.",
        "required_adapters": ["roi_feedback_adapter", "capital_receipt_aggregator"],
        "required_authority": ["allowed_signal_sources", "budget_context", "feedback_scope"],
        "required_receipts": ["roi_feedback_receipt", "capital_signal_receipt"],
        "rollback_or_disable_plan": ["disable ROI feedback adapter", "mark affected opportunities stale"],
    },
    {
        "promotion_id": "trading_live_paper_feed_l6",
        "organ": "trading",
        "surface": "live paper market feed",
        "priority_rank": 7,
        "decision": "promote_next",
        "reason": "Trading has paper baskets; next power is a live paper feed before broker execution.",
        "required_adapters": ["live_market_data_adapter", "trading_risk_monitor"],
        "required_authority": ["allowed_symbols", "broker_paper_scope", "max_loss_policy"],
        "required_receipts": ["market_feed_receipt", "paper_trade_receipt", "risk_monitor_receipt"],
        "rollback_or_disable_plan": ["disable feed adapter", "halt paper runner"],
    },
    {
        "promotion_id": "spend_provider_test_mode_l6",
        "organ": "spend",
        "surface": "real provider test mode",
        "priority_rank": 8,
        "decision": "promote_next",
        "reason": "Spend has multi-vendor fake/test mode; next power is provider test mode with no real charge.",
        "required_adapters": ["provider_test_mode_adapter", "refund_cancel_adapter"],
        "required_authority": ["spend_authority", "vendor_scope", "category_scope", "budget_cap"],
        "required_receipts": ["provider_test_receipt", "refund_cancel_receipt", "kill_switch_receipt"],
        "rollback_or_disable_plan": ["disable provider test adapter", "cancel/refund test objects"],
    },
]
