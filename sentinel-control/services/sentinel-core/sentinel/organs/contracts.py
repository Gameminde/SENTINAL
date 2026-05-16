from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


class OrganType(StrEnum):
    BROWSER = "browser"
    EXTERNAL_API = "external_api"
    CHANNEL = "channel"
    ACCOUNT_OPS = "account_ops"
    CAPITAL_OPERATOR = "capital_operator"
    TRADING = "trading"
    DESKTOP_SIDECAR = "desktop_sidecar"
    SHELL_SANDBOX = "shell_sandbox"
    FINANCE = "finance"
    GENERIC = "generic"


class OrganPromotionLevel(StrEnum):
    L0_VENDOR_OBSERVATION = "L0_vendor_observation"
    L1_EXTRACTION_MATRIX = "L1_extraction_matrix"
    L2_SENTINEL_CONTRACT = "L2_sentinel_contract"
    L3_FAKE_EVAL = "L3_fake_eval"
    L4_DRY_RUN = "L4_dry_run"
    L5_SANDBOX = "L5_sandbox"
    L6_LIMITED_EXECUTION = "L6_limited_execution"
    L7_PRODUCTION_SCOPED_EXECUTION = "L7_production_scoped_execution"
    L8_CONTINUOUS_ORGANBENCH_MONITORING = "L8_continuous_organbench_monitoring"


PROMOTION_ORDER = {
    OrganPromotionLevel.L0_VENDOR_OBSERVATION: 0,
    OrganPromotionLevel.L1_EXTRACTION_MATRIX: 1,
    OrganPromotionLevel.L2_SENTINEL_CONTRACT: 2,
    OrganPromotionLevel.L3_FAKE_EVAL: 3,
    OrganPromotionLevel.L4_DRY_RUN: 4,
    OrganPromotionLevel.L5_SANDBOX: 5,
    OrganPromotionLevel.L6_LIMITED_EXECUTION: 6,
    OrganPromotionLevel.L7_PRODUCTION_SCOPED_EXECUTION: 7,
    OrganPromotionLevel.L8_CONTINUOUS_ORGANBENCH_MONITORING: 8,
}


REQUIRED_DRY_RUN_FIELDS = {"reason", "preview", "risk_profile_id", "authority_id", "evidence_refs"}
REQUIRED_RECEIPT_FIELDS = {"dry_run_receipt_id", "trace_refs", "output_summary", "receipt_hash"}
REQUIRED_RISK_PROFILE_FIELDS = {"risk_score", "risk_level", "reasons", "requires_dry_run"}
REQUIRED_TRACE_EVENTS = {
    AgentEventType.ORGAN_CONTRACT_REGISTERED.value,
    AgentEventType.ORGAN_AUTHORITY_EVALUATED.value,
    AgentEventType.ORGAN_RISK_PROFILED.value,
    AgentEventType.ORGAN_DRY_RUN_RECORDED.value,
    AgentEventType.ORGAN_EXECUTION_RECEIPT_RECORDED.value,
    AgentEventType.ORGAN_PROMOTION_EVALUATED.value,
    AgentEventType.ORGAN_KILL_SWITCH_TRIGGERED.value,
}


class VendorHarvestReference(SentinelModel):
    id: str = ""
    source_system: str
    source_url: str | None = None
    source_path: str | None = None
    mechanism: str
    sentinel_rewrite: str
    risk_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    runtime_verified: bool = False
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> VendorHarvestReference:
        if not self.evidence_refs:
            raise ValueError("VendorHarvestReference requires evidence refs.")
        if self.vendor_code_copied:
            raise ValueError("Vendor code cannot be copied into Sentinel organ harvest references.")
        if self.vendor_runtime_bridge:
            raise ValueError("Vendor runtime bridges are not authorized by organ harvest references.")
        if not self.id:
            self.id = _stable_id(
                "vhref",
                {
                    "source_system": self.source_system,
                    "source_url": self.source_url,
                    "source_path": self.source_path,
                    "mechanism": self.mechanism,
                    "sentinel_rewrite": self.sentinel_rewrite,
                    "evidence_refs": self.evidence_refs,
                },
            )
        return self

    def record(self, event_bus: EventBus | None = None) -> VendorHarvestReference:
        if event_bus is None:
            return self
        event = event_bus.append(
            AgentEventType.ORGAN_HARVEST_REFERENCE_RECORDED,
            "Vendor harvest reference recorded as rewrite knowledge only.",
            payload={
                "reference_id": self.id,
                "source_system": self.source_system,
                "mechanism": self.mechanism,
                "sentinel_rewrite": self.sentinel_rewrite,
                "runtime_verified": self.runtime_verified,
                "vendor_code_copied": False,
                "vendor_runtime_bridge": False,
                "authority_expansion": False,
            },
        )
        return self.model_copy(update={"trace_refs": [*self.trace_refs, event.id]})


class OrganCapability(SentinelModel):
    name: str
    description: str
    actions: list[str] = Field(default_factory=list)
    authority_fields: list[str] = Field(default_factory=list)
    promotion_required: OrganPromotionLevel = OrganPromotionLevel.L2_SENTINEL_CONTRACT
    evidence_refs: list[str] = Field(default_factory=list)


class ExternalOrganContract(SentinelModel):
    id: str = ""
    organ_name: str
    organ_type: OrganType = OrganType.GENERIC
    version: str = "0.1.0"
    description: str
    promotion_level: OrganPromotionLevel = OrganPromotionLevel.L2_SENTINEL_CONTRACT
    capabilities: list[OrganCapability] = Field(default_factory=list)
    supported_actions: list[str] = Field(default_factory=list)
    authority_fields: list[str] = Field(default_factory=list)
    required_dry_run_fields: list[str] = Field(default_factory=lambda: sorted(REQUIRED_DRY_RUN_FIELDS))
    required_receipt_fields: list[str] = Field(default_factory=lambda: sorted(REQUIRED_RECEIPT_FIELDS))
    required_risk_profile_fields: list[str] = Field(default_factory=lambda: sorted(REQUIRED_RISK_PROFILE_FIELDS))
    required_trace_events: list[str] = Field(default_factory=lambda: sorted(REQUIRED_TRACE_EVENTS))
    source_refs: list[VendorHarvestReference] = Field(default_factory=list)
    authority_mapping_required: bool = True
    risk_profile_required: bool = True
    fake_eval_required: bool = True
    dry_run_required: bool = True
    kill_switch_required: bool = True
    final_gate_required: bool = True
    execution_enabled: bool = False
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> ExternalOrganContract:
        if not self.supported_actions:
            raise ValueError("ExternalOrganContract requires supported actions.")
        if not self.capabilities:
            raise ValueError("ExternalOrganContract requires capabilities.")
        if self.authority_mapping_required and not self.authority_fields:
            raise ValueError("ExternalOrganContract requires authority mapping fields.")
        if self.risk_profile_required and not set(self.required_risk_profile_fields).issuperset(REQUIRED_RISK_PROFILE_FIELDS):
            raise ValueError("ExternalOrganContract requires risk profile schema fields.")
        if self.dry_run_required and not set(self.required_dry_run_fields).issuperset(REQUIRED_DRY_RUN_FIELDS):
            raise ValueError("ExternalOrganContract requires dry-run receipt schema fields.")
        if not set(self.required_receipt_fields).issuperset(REQUIRED_RECEIPT_FIELDS):
            raise ValueError("ExternalOrganContract requires execution receipt schema fields.")
        if not set(self.required_trace_events).issuperset(REQUIRED_TRACE_EVENTS):
            raise ValueError("ExternalOrganContract requires trace event compatibility.")
        if not self.kill_switch_required:
            raise ValueError("ExternalOrganContract requires kill-switch compatibility.")
        if not self.final_gate_required:
            raise ValueError("ExternalOrganContract requires FinalGate compatibility.")
        if not self.source_refs:
            raise ValueError("ExternalOrganContract requires source refs.")
        supported = set(self.supported_actions)
        authority_fields = set(self.authority_fields)
        for capability in self.capabilities:
            if not capability.evidence_refs:
                raise ValueError("OrganCapability requires evidence refs.")
            if not set(capability.actions).issubset(supported):
                raise ValueError("OrganCapability actions must be supported by the organ contract.")
            if not set(capability.authority_fields).issubset(authority_fields):
                raise ValueError("OrganCapability authority fields must be declared by the organ contract.")
        if self.vendor_code_copied:
            raise ValueError("ExternalOrganContract cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("ExternalOrganContract cannot authorize vendor runtime bridges.")
        if self.authority_expansion:
            raise ValueError("ExternalOrganContract cannot expand authority.")
        if self.execution_enabled and PROMOTION_ORDER[self.promotion_level] < PROMOTION_ORDER[OrganPromotionLevel.L6_LIMITED_EXECUTION]:
            raise ValueError("Organ execution cannot be enabled before L6 limited execution.")
        if not self.id:
            self.id = _stable_id(
                "organ",
                {
                    "organ_name": self.organ_name,
                    "organ_type": self.organ_type.value,
                    "version": self.version,
                    "supported_actions": sorted(self.supported_actions),
                },
            )
        return self
