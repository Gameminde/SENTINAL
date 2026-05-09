from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.event_bus import EventBus
from sentinel.agent.events import AgentEventType
from sentinel.organs.contracts import OrganPromotionLevel, OrganType
from sentinel.shared.models import SentinelModel


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


REQUIRED_P6J_PHASES = {
    "P6C_BROWSER_ORGAN_CONTRACT_REVIEW",
    "P6D_EXTERNAL_API_ORGAN_DRY_RUN",
    "P6E_CHANNEL_ORGAN_DRAFT_FIRST",
    "P6F_CREDENTIAL_VAULT_POLICY",
    "P6G_CAPITAL_OPERATOR_SANDBOX",
    "P6H_SPEND_RUNTIME_LIMITED",
    "P6I_TRADING_SPECIAL_AUTHORITY",
    "P6I6_TRADINGAGENTS_HARVEST",
}


class AgentLabImplementationAlignmentEntry(SentinelModel):
    id: str = ""
    organ_phase: str
    organ_name: str
    organ_type: OrganType
    source_systems: list[str]
    source_paths: list[str]
    vendor_patterns: list[str]
    sentinel_rewrites: list[str]
    current_sentinel_files: list[str]
    high_power_surfaces: list[str] = Field(default_factory=list)
    authorized_surfaces: list[str] = Field(default_factory=list)
    evaluated_surfaces: list[str] = Field(default_factory=list)
    sandboxed_capability_surfaces: list[str] = Field(default_factory=list)
    capability_promotion_surfaces: list[str] = Field(default_factory=list)
    black_lane_blocked_objectives: list[str] = Field(default_factory=list)
    required_controls: list[str]
    evidence_refs: list[str]
    current_promotion_level: OrganPromotionLevel
    target_promotion_level: OrganPromotionLevel
    improvements_now: list[str] = Field(default_factory=list)
    deferred_improvements: list[str] = Field(default_factory=list)
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> AgentLabImplementationAlignmentEntry:
        if self.organ_phase not in REQUIRED_P6J_PHASES:
            raise ValueError(f"unknown P6J organ phase:{self.organ_phase}")
        if not self.source_systems:
            raise ValueError("AgentLabImplementationAlignmentEntry requires source systems.")
        if not self.source_paths:
            raise ValueError("AgentLabImplementationAlignmentEntry requires source paths.")
        if not self.vendor_patterns:
            raise ValueError("AgentLabImplementationAlignmentEntry requires vendor patterns.")
        if not self.sentinel_rewrites:
            raise ValueError("AgentLabImplementationAlignmentEntry requires Sentinel rewrites.")
        if not self.current_sentinel_files:
            raise ValueError("AgentLabImplementationAlignmentEntry requires current Sentinel files.")
        if not self.required_controls:
            raise ValueError("AgentLabImplementationAlignmentEntry requires controls.")
        if not self.evidence_refs:
            raise ValueError("AgentLabImplementationAlignmentEntry requires evidence refs.")
        handled = set(
            self.authorized_surfaces
            + self.evaluated_surfaces
            + self.sandboxed_capability_surfaces
            + self.capability_promotion_surfaces
        )
        if not set(self.high_power_surfaces).issubset(handled):
            missing = sorted(set(self.high_power_surfaces) - handled)
            raise ValueError(f"high-power surfaces must have a capability handling path:{','.join(missing)}")
        if not self.black_lane_blocked_objectives:
            raise ValueError("AgentLabImplementationAlignmentEntry requires Black Lane misuse objectives.")
        if self.vendor_code_copied:
            raise ValueError("AgentLabImplementationAlignmentEntry cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("AgentLabImplementationAlignmentEntry cannot bridge vendor runtime.")
        if self.authority_expansion:
            raise ValueError("AgentLabImplementationAlignmentEntry cannot expand authority.")
        if not self.id:
            self.id = _stable_id(
                "align",
                {
                    "organ_phase": self.organ_phase,
                    "source_systems": self.source_systems,
                    "sentinel_rewrites": self.sentinel_rewrites,
                    "evidence_refs": self.evidence_refs,
                },
            )
        return self


class AgentLabImplementationAlignmentMatrix(SentinelModel):
    id: str = ""
    phase: str = "P6J_AGENTLAB_IMPLEMENTATION_ALIGNMENT"
    previous_phase: str = "P6I6_FULL_LOCKED"
    next_phase: str = "P6K_ORGANBENCH_EXTERNAL_ORGAN_INTEGRATED_REVIEW"
    entries: list[AgentLabImplementationAlignmentEntry]
    runtime_powers_added: int = 0
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> AgentLabImplementationAlignmentMatrix:
        if not self.entries:
            raise ValueError("AgentLabImplementationAlignmentMatrix requires entries.")
        phases = [entry.organ_phase for entry in self.entries]
        if len(phases) != len(set(phases)):
            raise ValueError("AgentLabImplementationAlignmentMatrix cannot contain duplicate organ phases.")
        if set(phases) != REQUIRED_P6J_PHASES:
            missing = sorted(REQUIRED_P6J_PHASES - set(phases))
            extra = sorted(set(phases) - REQUIRED_P6J_PHASES)
            raise ValueError(f"AgentLabImplementationAlignmentMatrix must cover required P6 phases. missing={missing} extra={extra}")
        if self.runtime_powers_added != 0:
            raise ValueError("AgentLabImplementationAlignmentMatrix cannot add runtime powers.")
        if self.vendor_code_copied:
            raise ValueError("AgentLabImplementationAlignmentMatrix cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("AgentLabImplementationAlignmentMatrix cannot bridge vendor runtime.")
        if self.authority_expansion:
            raise ValueError("AgentLabImplementationAlignmentMatrix cannot expand authority.")
        if not self.id:
            self.id = _stable_id("alignmatrix", {"entry_ids": [entry.id for entry in self.entries]})
        return self

    def by_phase(self, phase: str) -> AgentLabImplementationAlignmentEntry:
        for entry in self.entries:
            if entry.organ_phase == phase:
                return entry
        raise KeyError(phase)

    def record(self, event_bus: EventBus | None = None) -> AgentLabImplementationAlignmentMatrix:
        if event_bus is None:
            return self
        event = event_bus.append(
            AgentEventType.ORGAN_IMPLEMENTATION_ALIGNMENT_BUILT,
            "P6 AgentLab implementation alignment matrix built without new execution powers.",
            payload={
                "matrix_id": self.id,
                "phase": self.phase,
                "entry_count": len(self.entries),
                "organ_phases": sorted(entry.organ_phase for entry in self.entries),
                "source_systems": sorted({source for entry in self.entries for source in entry.source_systems}),
                "runtime_powers_added": 0,
                "vendor_code_copied": False,
                "vendor_runtime_bridge": False,
                "authority_expansion": False,
            },
        )
        return self.model_copy(update={"trace_refs": [*self.trace_refs, event.id]})


class AgentLabImplementationAlignmentBuilder:
    def build_default_matrix(self, *, event_bus: EventBus | None = None) -> AgentLabImplementationAlignmentMatrix:
        matrix = AgentLabImplementationAlignmentMatrix(entries=_default_entries())
        return matrix.record(event_bus)


def _default_entries() -> list[AgentLabImplementationAlignmentEntry]:
    return [
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6C_BROWSER_ORGAN_CONTRACT_REVIEW",
            organ_name="Browser Organ",
            organ_type=OrganType.BROWSER,
            source_systems=["OpenClaw", "JARVIS", "CloakBrowser"],
            source_paths=[
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/audits/final/jarvis_final_forensic_report.md",
                "sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/17_CLOAK_BROWSER_POWER_REVIEW.md",
            ],
            vendor_patterns=[
                "OpenClaw browser/control-plane routing and approval lifecycle",
                "JARVIS browser/sidecar awareness and host-boundary lessons",
                "CloakBrowser controlled power classification P0-P5",
            ],
            sentinel_rewrites=[
                "BrowserReliabilityProfile",
                "BrowserSessionContinuityPolicy",
                "BrowserPowerGovernor",
                "BrowserMisuseClassifier",
                "BrowserDetectionBench",
                "BrowserComplianceGate",
            ],
            current_sentinel_files=[
                "sentinel/organs/browser/contract.py",
                "sentinel/organs/browser/power_governor.py",
                "sentinel/organs/browser/misuse_classifier.py",
                "sentinel/organs/browser/detection_bench.py",
            ],
            high_power_surfaces=["browser_session_continuity", "public_read_only_browsing", "fingerprint_consistency", "detection_resilience_research", "stealth_browser_operation"],
            authorized_surfaces=["browser_session_continuity", "public_read_only_browsing"],
            evaluated_surfaces=["fingerprint_consistency"],
            sandboxed_capability_surfaces=["detection_resilience_research"],
            capability_promotion_surfaces=["stealth_browser_operation"],
            black_lane_blocked_objectives=["fake_identity", "kyc_bypass", "credential_theft", "unauthorized_scraping", "unlawful_evasion"],
            required_controls=["authority_mapping", "browser_compliance_gate", "misuse_classifier", "special_authority_gate", "receipts", "FinalGate", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["openclaw_final", "jarvis_final", "cloak_power_review", "p6c_lock"],
            current_promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
            target_promotion_level=OrganPromotionLevel.L5_SANDBOX,
            improvements_now=["Confirm Cloak-like powers are classified, not deleted."],
            deferred_improvements=["BrowserFinalGateAdapter", "special-authority stealth sandbox"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6D_EXTERNAL_API_ORGAN_DRY_RUN",
            organ_name="External API Organ",
            organ_type=OrganType.EXTERNAL_API,
            source_systems=["OpenClaw", "OpenJarvis", "financial-services", "TradingAgents"],
            source_paths=[
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/audits/final/openjarvis_final_forensic_report.md",
                "sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md",
                "agent-lab/audits/tradingagents_capability_map.md",
            ],
            vendor_patterns=[
                "OpenClaw connector/plugin manifest shape",
                "OpenJarvis cost/rate/model routing lessons",
                "financial-services connector/data workflow procedures",
                "TradingAgents vendor fallback routing",
            ],
            sentinel_rewrites=["ExternalAPIAllowlist", "APICostEstimator", "APIPrivacyRiskClassifier", "ExternalAPIDryRunPlanner", "TradingAgentsDataVendorRoute"],
            current_sentinel_files=[
                "sentinel/organs/external_api/request_plan.py",
                "sentinel/organs/external_api/allowlist.py",
                "sentinel/organs/external_api/cost_estimator.py",
                "sentinel/organs/external_api/privacy_risk.py",
            ],
            high_power_surfaces=["live_external_api_call", "mutation_api", "paid_api", "vendor_fallback_route"],
            authorized_surfaces=[],
            evaluated_surfaces=["vendor_fallback_route"],
            sandboxed_capability_surfaces=["request_dry_run", "cost_estimation", "privacy_classification"],
            capability_promotion_surfaces=["live_external_api_call", "mutation_api", "paid_api"],
            black_lane_blocked_objectives=["credential_secret_read", "unlawful_data_access"],
            required_controls=["allowlist", "credential_ref_only", "cost_estimate", "privacy_risk", "dry_run_receipt", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["openclaw_final", "openjarvis_final", "financial_services_harvest", "tradingagents_capability_map", "p6d_lock"],
            current_promotion_level=OrganPromotionLevel.L4_DRY_RUN,
            target_promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            improvements_now=["Bind API vendor fallback pattern to dry-run routing."],
            deferred_improvements=["live read-only API sandbox with CredentialVaultPolicy"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6E_CHANNEL_ORGAN_DRAFT_FIRST",
            organ_name="Channel Organ",
            organ_type=OrganType.CHANNEL,
            source_systems=["OpenClaw", "Hermes", "JARVIS"],
            source_paths=[
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/audits/final/hermes_final_forensic_report.md",
                "agent-lab/audits/final/jarvis_final_forensic_report.md",
            ],
            vendor_patterns=[
                "OpenClaw channel adapters and outbound lifecycle",
                "Hermes context/memory reuse for messages",
                "JARVIS approval lifecycle and external-message templates",
            ],
            sentinel_rewrites=["ChannelMessageDraft", "ChannelSendGate", "InboundChannelMessage", "RecipientProvenance", "ChannelRateLimitPolicy"],
            current_sentinel_files=[
                "sentinel/organs/channels/draft.py",
                "sentinel/organs/channels/send_gate.py",
                "sentinel/organs/channels/inbound.py",
                "sentinel/organs/channels/compliance.py",
            ],
            high_power_surfaces=["live_send", "outbound_prospecting", "inbound_context_reuse"],
            authorized_surfaces=["inbound_context_reuse"],
            evaluated_surfaces=["outbound_prospecting"],
            sandboxed_capability_surfaces=["draft_generation", "send_gate_rejection_receipt"],
            capability_promotion_surfaces=["live_send"],
            black_lane_blocked_objectives=["illegal_spam", "spam", "deceptive_identity", "credential_capture"],
            required_controls=["draft_first", "recipient_provenance", "compliance_check", "rate_limit", "send_receipt", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["openclaw_final", "hermes_final", "jarvis_final", "p6e_lock"],
            current_promotion_level=OrganPromotionLevel.L4_DRY_RUN,
            target_promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            improvements_now=["Keep inbound channel content untrusted and non-authoritative."],
            deferred_improvements=["limited authorized send runtime"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6F_CREDENTIAL_VAULT_POLICY",
            organ_name="Credential Vault Policy",
            organ_type=OrganType.GENERIC,
            source_systems=["JARVIS", "OpenClaw", "Hermes"],
            source_paths=[
                "agent-lab/audits/final/jarvis_final_forensic_report.md",
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/audits/final/hermes_final_forensic_report.md",
            ],
            vendor_patterns=[
                "JARVIS vault/sidecar secret-risk surface",
                "OpenClaw plugin/channel credential risk",
                "Hermes external-account skill setup risk",
            ],
            sentinel_rewrites=["CredentialRef", "ScopedCredentialGrant", "CredentialVaultPolicy", "CredentialTraceRedactor", "revoke_credential_grant"],
            current_sentinel_files=[
                "sentinel/organs/credentials/credential_ref.py",
                "sentinel/organs/credentials/scoped_grant.py",
                "sentinel/organs/credentials/vault_policy.py",
                "sentinel/organs/credentials/redaction.py",
            ],
            high_power_surfaces=["credential_ref_registration", "trace_redaction", "scoped_credential_use"],
            authorized_surfaces=["credential_ref_registration", "trace_redaction"],
            evaluated_surfaces=[],
            sandboxed_capability_surfaces=[],
            capability_promotion_surfaces=["scoped_credential_use"],
            black_lane_blocked_objectives=["credential_secret_read", "memory_granted_secret", "prompt_granted_secret", "vendor_harvest_granted_secret"],
            required_controls=["credential_ref_only", "scoped_grant", "expiry", "redaction", "revocation", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["jarvis_final", "openclaw_final", "hermes_final", "p6f_lock"],
            current_promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
            target_promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            improvements_now=["Keep raw secrets out of prompts, memory, workspace, and harvest docs."],
            deferred_improvements=["real vault adapter behind Red Lane special authority"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6G_CAPITAL_OPERATOR_SANDBOX",
            organ_name="Capital Operator Sandbox",
            organ_type=OrganType.CAPITAL_OPERATOR,
            source_systems=["financial-services", "OpenJarvis", "Hermes", "TradingAgents"],
            source_paths=[
                "sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md",
                "agent-lab/audits/final/openjarvis_final_forensic_report.md",
                "agent-lab/audits/final/hermes_final_forensic_report.md",
                "agent-lab/audits/tradingagents_capability_map.md",
            ],
            vendor_patterns=[
                "financial-services procedure and analyst workflow maps",
                "OpenJarvis cost/budget routing",
                "Hermes durable outcome memory",
                "TradingAgents outcome memory and alpha reflection",
            ],
            sentinel_rewrites=["CapitalOpportunity", "SignalLedger", "AdaptiveOperatingEnvelope", "BudgetReallocator", "DynamicSpendPolicy", "CapitalRiskReview"],
            current_sentinel_files=["sentinel/organs/capital/sandbox.py"],
            high_power_surfaces=["opportunity_portfolio", "dynamic_budget_reallocation", "spend_proposal", "live_spend"],
            authorized_surfaces=["opportunity_portfolio"],
            evaluated_surfaces=["dynamic_budget_reallocation"],
            sandboxed_capability_surfaces=["signal_ledger", "spend_proposal"],
            capability_promotion_surfaces=["live_spend"],
            black_lane_blocked_objectives=["profit_guarantee", "budget_overrun", "unbacked_signal_reallocation"],
            required_controls=["signal_refs", "evidence_refs", "budget_caps", "risk_review", "proposal_only", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["financial_services_harvest", "openjarvis_final", "hermes_final", "tradingagents_capability_map", "p6g_lock", "p6i5_lock"],
            current_promotion_level=OrganPromotionLevel.L5_SANDBOX,
            target_promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            improvements_now=["Use TradingAgents outcome memory as future capital-learning input."],
            deferred_improvements=["CapitalAnalysisBench", "live spend promotion through P6H"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6H_SPEND_RUNTIME_LIMITED",
            organ_name="Spend Runtime Limited",
            organ_type=OrganType.CAPITAL_OPERATOR,
            source_systems=["financial-services", "JARVIS", "OpenClaw"],
            source_paths=[
                "sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md",
                "agent-lab/audits/final/jarvis_final_forensic_report.md",
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
            ],
            vendor_patterns=[
                "financial-services human review and no-transaction boundary",
                "JARVIS approval lifecycle and kill-switch lessons",
                "OpenClaw gateway/action receipt lessons",
            ],
            sentinel_rewrites=["SpendAuthorityEnvelope", "SpendRequest", "FakeSpendProvider", "SpendReceipt", "SubscriptionGuard", "RefundCancelPath", "SpendKillSwitch"],
            current_sentinel_files=["sentinel/organs/spend/runtime.py"],
            high_power_surfaces=["fake_spend_provider", "real_payment_execution", "subscription_purchase"],
            authorized_surfaces=[],
            evaluated_surfaces=[],
            sandboxed_capability_surfaces=["fake_spend_provider"],
            capability_promotion_surfaces=["real_payment_execution", "subscription_purchase"],
            black_lane_blocked_objectives=["hidden_subscription", "budget_overrun", "credential_secret_read"],
            required_controls=["root_authority_envelope", "vendor_category_caps", "receipt", "kill_switch", "refund_cancel_path", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["financial_services_harvest", "jarvis_final", "openclaw_final", "p6h_lock", "p6i5_lock"],
            current_promotion_level=OrganPromotionLevel.L5_SANDBOX,
            target_promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            improvements_now=["Keep fake provider as the only executable spend surface."],
            deferred_improvements=["real provider adapter only after OrganBench and special authority"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6I_TRADING_SPECIAL_AUTHORITY",
            organ_name="Trading Special Authority",
            organ_type=OrganType.TRADING,
            source_systems=["TradingAgents", "financial-services"],
            source_paths=[
                "agent-lab/audits/tradingagents_static_audit.md",
                "sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md",
            ],
            vendor_patterns=[
                "TradingAgents portfolio manager and risk debate",
                "financial-services evidence/review boundary for financial work",
            ],
            sentinel_rewrites=["TradingSpecialAuthority", "BrokerContract", "AssetPolicy", "PositionSizingPolicy", "MaxLossPolicy", "StopLossPolicy", "PaperTradeProvider", "TradingReceipt"],
            current_sentinel_files=[
                "sentinel/organs/trading/special_authority.py",
                "sentinel/organs/trading/tradingagents_harvest.py",
            ],
            high_power_surfaces=["paper_trade_provider", "real_trading_execution", "leverage"],
            authorized_surfaces=[],
            evaluated_surfaces=[],
            sandboxed_capability_surfaces=["paper_trade_provider"],
            capability_promotion_surfaces=["real_trading_execution", "leverage"],
            black_lane_blocked_objectives=["profit_guarantee", "unauthorized_asset", "missing_stop_loss"],
            required_controls=["special_authority", "broker_contract", "asset_policy", "max_loss", "stop_loss", "trade_journal", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["tradingagents_static_audit", "tradingagents_capability_map", "financial_services_harvest", "p6i_lock", "p6i5_lock"],
            current_promotion_level=OrganPromotionLevel.L5_SANDBOX,
            target_promotion_level=OrganPromotionLevel.L6_LIMITED_EXECUTION,
            improvements_now=["Bind paper provider to authority asset scope and max leverage."],
            deferred_improvements=["real broker adapter only after special authority and OrganBench"],
        ),
        AgentLabImplementationAlignmentEntry(
            organ_phase="P6I6_TRADINGAGENTS_HARVEST",
            organ_name="TradingAgents Harvest",
            organ_type=OrganType.TRADING,
            source_systems=["TradingAgents"],
            source_paths=[
                "agent-lab/audits/tradingagents_static_audit.md",
                "agent-lab/audits/tradingagents_capability_map.md",
                "agent-lab/sentinel_integration_notes/tradingagents_to_sentinel.md",
            ],
            vendor_patterns=[
                "trading desk role graph",
                "five-tier rating parser",
                "data vendor fallback routing",
                "outcome memory and alpha reflection",
            ],
            sentinel_rewrites=["TradingAgentsFirmPlan", "TradingAgentsRoleAssignment", "TradingAgentsSignalParser", "TradingAgentsDataVendorRoute", "TradingOutcomeMemoryEntry"],
            current_sentinel_files=["sentinel/organs/trading/tradingagents_harvest.py"],
            high_power_surfaces=["trading_firm_plan", "rating_parse", "data_vendor_fallback", "outcome_memory_entry", "live_api_call", "real_trading_execution"],
            authorized_surfaces=[],
            evaluated_surfaces=["data_vendor_fallback"],
            sandboxed_capability_surfaces=["trading_firm_plan", "rating_parse", "outcome_memory_entry"],
            capability_promotion_surfaces=["live_api_call", "real_trading_execution"],
            black_lane_blocked_objectives=["vendor_runtime_bridge", "investment_advice_without_authority"],
            required_controls=["source_only_audit", "sentinel_native_rewrite", "paper_only", "no_vendor_runtime", "blocked_by_default_not_forbidden_forever", "capability_promotion_path"],
            evidence_refs=["tradingagents_static_audit", "tradingagents_capability_map", "tradingagents_to_sentinel", "p6i6_lock"],
            current_promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
            target_promotion_level=OrganPromotionLevel.L5_SANDBOX,
            improvements_now=["Make TradingAgents an official P6J source."],
            deferred_improvements=["TradingAgents patterns inside OrganBench trading fixtures"],
        ),
    ]
