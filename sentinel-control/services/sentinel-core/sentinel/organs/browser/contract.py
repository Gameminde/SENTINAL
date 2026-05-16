from __future__ import annotations

from sentinel.shared.events import AgentEventType
from sentinel.organs.contracts import (
    REQUIRED_TRACE_EVENTS,
    ExternalOrganContract,
    OrganCapability,
    OrganPromotionLevel,
    OrganType,
    VendorHarvestReference,
)


def build_browser_organ_contract() -> ExternalOrganContract:
    return ExternalOrganContract(
        organ_name="browser_power_governor",
        organ_type=OrganType.BROWSER,
        version="0.1.0",
        description="Sentinel browser organ contract for governed reliability, observation, dry-run interaction, and future Cloak-like power classes.",
        promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        capabilities=[
            OrganCapability(
                name="p0_browser_reliability",
                description="Stable public browser observation and reliability profile planning.",
                actions=["browser_read_public_page", "browser_observe_public_page"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6b_cloak_browser", "p4_browser_locked_routes"],
            ),
            OrganCapability(
                name="p1_human_like_operation",
                description="Human-like interaction planning for future promoted browser routes.",
                actions=["browser_interaction_dry_run"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6b_cloak_browser"],
            ),
            OrganCapability(
                name="p2_fingerprint_consistency",
                description="Fingerprint/session consistency risk classification without stealth execution.",
                actions=["browser_fingerprint_review"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6b_cloak_browser"],
            ),
            OrganCapability(
                name="p3_detection_resilience_research",
                description="Bot-detection diagnostics and reliability scoring as research/dry-run only.",
                actions=["browser_detection_diagnostic"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6b_cloak_browser"],
            ),
            OrganCapability(
                name="p4_special_authority_stealth",
                description="Future special-authority stealth operation class; not executable in P6C.",
                actions=["browser_special_authority_review"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6b_cloak_browser"],
            ),
        ],
        supported_actions=[
            "browser_read_public_page",
            "browser_observe_public_page",
            "browser_interaction_dry_run",
            "browser_fingerprint_review",
            "browser_detection_diagnostic",
            "browser_special_authority_review",
            "browser_submit",
        ],
        authority_fields=["allowed_domains", "allowed_actions"],
        required_trace_events=sorted(
            {
                *REQUIRED_TRACE_EVENTS,
                AgentEventType.BROWSER_ORGAN_POWER_GOVERNED.value,
                AgentEventType.BROWSER_ORGAN_MISUSE_CLASSIFIED.value,
                AgentEventType.BROWSER_ORGAN_RECEIPT_RECORDED.value,
                AgentEventType.BROWSER_ORGAN_DETECTION_BENCH_RUN.value,
            }
        ),
        source_refs=[
            VendorHarvestReference(
                source_system="SentinelBrowserV3",
                source_path="sentinel-control/services/sentinel-core/sentinel/agent/browser",
                mechanism="Locked Sentinel browser routes and receipts.",
                sentinel_rewrite="BrowserPowerGovernor",
                evidence_refs=["p4_browser_locked_routes"],
            ),
            VendorHarvestReference(
                source_system="CloakBrowser",
                source_url="https://github.com/CloakHQ/CloakBrowser",
                source_path="sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/17_CLOAK_BROWSER_POWER_REVIEW.md",
                mechanism="Browser reliability, humanization, fingerprint consistency, and detection-resilience power taxonomy.",
                sentinel_rewrite="BrowserPowerGovernor",
                risk_notes=["misuse objectives are blocked, not capability existence"],
                evidence_refs=["p6b_cloak_browser", "cloak_power_review"],
            ),
        ],
    )
