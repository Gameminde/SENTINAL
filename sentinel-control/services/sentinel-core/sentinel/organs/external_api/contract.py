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


def build_external_api_organ_contract() -> ExternalOrganContract:
    return ExternalOrganContract(
        organ_name="external_api_organ",
        organ_type=OrganType.EXTERNAL_API,
        version="0.1.0",
        description="Dry-run external API organ for request planning, allowlist checks, cost estimates, privacy risk, and deterministic receipts.",
        promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        capabilities=[
            OrganCapability(
                name="api_read_request_planning",
                description="Plan read-only external API requests without live execution.",
                actions=["api_read_request_plan"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6a_external_organ_foundry"],
            ),
            OrganCapability(
                name="api_paid_request_planning",
                description="Plan paid API use as dry-run only until future promotion.",
                actions=["api_paid_request_plan"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6a_external_organ_foundry"],
            ),
            OrganCapability(
                name="api_mutation_request_planning",
                description="Plan mutation/account-affecting API use as Orange/Red Lane dry-run only.",
                actions=["api_mutation_request_plan", "api_account_affecting_request_plan"],
                authority_fields=["allowed_domains", "allowed_actions"],
                evidence_refs=["p6a_external_organ_foundry"],
            ),
        ],
        supported_actions=[
            "api_read_request_plan",
            "api_paid_request_plan",
            "api_mutation_request_plan",
            "api_account_affecting_request_plan",
        ],
        authority_fields=["allowed_domains", "allowed_actions"],
        required_trace_events=sorted(
            {
                *REQUIRED_TRACE_EVENTS,
                AgentEventType.EXTERNAL_API_REQUEST_PLANNED.value,
                AgentEventType.EXTERNAL_API_DRY_RUN_RECORDED.value,
            }
        ),
        source_refs=[
            VendorHarvestReference(
                source_system="SentinelAtoZArchitecture",
                source_path="sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/06_SENTINEL_SYSTEM_ARCHITECTURE_A_TO_Z.md",
                mechanism="External API organ contract promoted from architecture lock.",
                sentinel_rewrite="ExternalAPIOrganDryRun",
                evidence_refs=["architecture_a_to_z_lock"],
            )
        ],
    )
