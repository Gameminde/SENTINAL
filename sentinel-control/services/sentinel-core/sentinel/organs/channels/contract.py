from __future__ import annotations

from sentinel.agent.events import AgentEventType
from sentinel.organs.contracts import (
    REQUIRED_TRACE_EVENTS,
    ExternalOrganContract,
    OrganCapability,
    OrganPromotionLevel,
    OrganType,
    VendorHarvestReference,
)


def build_channel_organ_contract() -> ExternalOrganContract:
    return ExternalOrganContract(
        organ_name="channel_organ",
        organ_type=OrganType.CHANNEL,
        version="0.1.0",
        description="Draft-first channel organ for inbound/outbound communications with send gates and receipts.",
        promotion_level=OrganPromotionLevel.L2_SENTINEL_CONTRACT,
        capabilities=[
            OrganCapability(
                name="channel_draft_generation",
                description="Create communication drafts without live sending.",
                actions=["channel_draft_create"],
                authority_fields=["allowed_actions", "allowed_domains"],
                evidence_refs=["p6a_external_organ_foundry"],
            ),
            OrganCapability(
                name="channel_send_gate",
                description="Evaluate send readiness and record rejection/proposal receipts without live sending.",
                actions=["channel_send_gate"],
                authority_fields=["allowed_actions", "allowed_domains"],
                evidence_refs=["p6a_external_organ_foundry"],
            ),
            OrganCapability(
                name="channel_inbound_context",
                description="Classify inbound messages as untrusted context, not authority.",
                actions=["channel_inbound_classify"],
                authority_fields=["allowed_actions"],
                evidence_refs=["p6a_external_organ_foundry"],
            ),
        ],
        supported_actions=[
            "channel_draft_create",
            "channel_send_gate",
            "channel_inbound_classify",
        ],
        authority_fields=["allowed_actions", "allowed_domains"],
        required_trace_events=sorted(
            {
                *REQUIRED_TRACE_EVENTS,
                AgentEventType.CHANNEL_DRAFT_CREATED.value,
                AgentEventType.CHANNEL_SEND_GATED.value,
                AgentEventType.CHANNEL_INBOUND_CLASSIFIED.value,
            }
        ),
        source_refs=[
            VendorHarvestReference(
                source_system="SentinelAtoZArchitecture",
                source_path="sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/14_PRODUCT_WORKFLOW_MAP.md",
                mechanism="Outbound prospecting and research-to-action workflows require draft-first channels.",
                sentinel_rewrite="ChannelOrganDraftFirst",
                evidence_refs=["architecture_product_workflow_map"],
            )
        ],
    )
