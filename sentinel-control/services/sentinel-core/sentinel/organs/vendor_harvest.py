from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.organs.contracts import OrganPromotionLevel, OrganType, VendorHarvestReference
from sentinel.shared.models import SentinelModel


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


class HarvestSourceKind(StrEnum):
    FINAL_FORENSIC_REPORT = "final_forensic_report"
    EXTRACTION_TABLE = "extraction_table"
    ARCHITECTURE_LOCK = "architecture_lock"
    EXTERNAL_SOURCE_LEDGER = "external_source_ledger"


class HarvestPowerFamily(StrEnum):
    ACTION_KERNEL = "action_kernel"
    MEMORY_SKILL = "memory_skill"
    COST_ROUTING = "cost_routing"
    SIDECAR_DESKTOP = "sidecar_desktop"
    FINANCE_OPERATOR = "finance_operator"
    BROWSER_POWER = "browser_power"
    CHANNEL = "channel"
    EXTERNAL_API = "external_api"


class HarvestCandidateStatus(StrEnum):
    CONTRACT_CANDIDATE = "contract_candidate"
    REWRITE_ONLY = "rewrite_only"
    BLOCKED_RUNTIME = "blocked_runtime"


class AgentLabHarvestSource(SentinelModel):
    id: str = ""
    source_system: str
    source_kind: HarvestSourceKind
    local_path: str
    source_url: str | None = None
    source_commit: str | None = None
    evidence_refs: list[str]
    runtime_verified: bool = False
    vendor_code_approved: bool = False
    vendor_runtime_approved: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> AgentLabHarvestSource:
        if not self.local_path:
            raise ValueError("AgentLabHarvestSource requires local path.")
        if not self.evidence_refs:
            raise ValueError("AgentLabHarvestSource requires evidence refs.")
        if self.vendor_code_approved:
            raise ValueError("AgentLabHarvestSource cannot approve vendor code.")
        if self.vendor_runtime_approved:
            raise ValueError("AgentLabHarvestSource cannot approve vendor runtime.")
        if self.authority_expansion:
            raise ValueError("AgentLabHarvestSource cannot expand authority.")
        if not self.id:
            self.id = _stable_id(
                "hsrc",
                {
                    "source_system": self.source_system,
                    "source_kind": self.source_kind.value,
                    "local_path": self.local_path,
                    "source_url": self.source_url,
                    "source_commit": self.source_commit,
                    "evidence_refs": self.evidence_refs,
                },
            )
        return self


class OrganHarvestCandidate(SentinelModel):
    id: str = ""
    source: AgentLabHarvestSource
    power_family: HarvestPowerFamily
    organ_type: OrganType
    mechanism: str
    sentinel_rewrite: str
    target_phase: str
    target_promotion_level: OrganPromotionLevel = OrganPromotionLevel.L2_SENTINEL_CONTRACT
    status: HarvestCandidateStatus = HarvestCandidateStatus.CONTRACT_CANDIDATE
    required_controls: list[str]
    blocked_runtime_surfaces: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str]
    runtime_verified: bool = False
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> OrganHarvestCandidate:
        if not self.mechanism:
            raise ValueError("OrganHarvestCandidate requires mechanism.")
        if not self.sentinel_rewrite:
            raise ValueError("OrganHarvestCandidate requires Sentinel rewrite.")
        if not self.target_phase:
            raise ValueError("OrganHarvestCandidate requires target phase.")
        if not self.required_controls:
            raise ValueError("OrganHarvestCandidate requires required controls.")
        if not self.evidence_refs:
            raise ValueError("OrganHarvestCandidate requires evidence refs.")
        if self.vendor_code_copied:
            raise ValueError("OrganHarvestCandidate cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("OrganHarvestCandidate cannot bridge vendor runtime.")
        if self.authority_expansion:
            raise ValueError("OrganHarvestCandidate cannot expand authority.")
        if self.target_promotion_level != OrganPromotionLevel.L2_SENTINEL_CONTRACT:
            raise ValueError("P6B candidates must target L2 Sentinel contract only.")
        if not set(self.evidence_refs).issubset(set(self.source.evidence_refs)):
            raise ValueError("OrganHarvestCandidate evidence refs must come from its source.")
        if not self.id:
            self.id = _stable_id(
                "hcand",
                {
                    "source": self.source.id,
                    "power_family": self.power_family.value,
                    "organ_type": self.organ_type.value,
                    "sentinel_rewrite": self.sentinel_rewrite,
                    "target_phase": self.target_phase,
                    "evidence_refs": self.evidence_refs,
                },
            )
        return self

    def to_vendor_reference(self) -> VendorHarvestReference:
        return VendorHarvestReference(
            source_system=self.source.source_system,
            source_url=self.source.source_url,
            source_path=self.source.local_path,
            mechanism=self.mechanism,
            sentinel_rewrite=self.sentinel_rewrite,
            risk_notes=[*self.risk_notes, *self.blocked_runtime_surfaces],
            evidence_refs=list(self.evidence_refs),
            runtime_verified=self.runtime_verified,
            vendor_code_copied=False,
            vendor_runtime_bridge=False,
        )

    def record(self, event_bus: EventBus | None = None) -> OrganHarvestCandidate:
        if event_bus is None:
            return self
        event = event_bus.append(
            AgentEventType.ORGAN_HARVEST_CANDIDATE_CLASSIFIED,
            "Agent Lab harvest candidate classified as rewrite knowledge only.",
            payload={
                "candidate_id": self.id,
                "source_system": self.source.source_system,
                "power_family": self.power_family.value,
                "organ_type": self.organ_type.value,
                "sentinel_rewrite": self.sentinel_rewrite,
                "target_phase": self.target_phase,
                "target_promotion_level": self.target_promotion_level.value,
                "status": self.status.value,
                "runtime_verified": self.runtime_verified,
                "vendor_code_copied": False,
                "vendor_runtime_bridge": False,
                "authority_expansion": False,
            },
        )
        return self.model_copy(update={"trace_refs": [*self.trace_refs, event.id]})


class AgentLabOrganHarvestMatrix(SentinelModel):
    id: str = ""
    candidates: list[OrganHarvestCandidate]
    promotion_level: OrganPromotionLevel = OrganPromotionLevel.L2_SENTINEL_CONTRACT
    runtime_powers_added: int = 0
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> AgentLabOrganHarvestMatrix:
        if not self.candidates:
            raise ValueError("AgentLabOrganHarvestMatrix requires candidates.")
        if self.runtime_powers_added != 0:
            raise ValueError("AgentLabOrganHarvestMatrix cannot add runtime powers.")
        if self.vendor_code_copied:
            raise ValueError("AgentLabOrganHarvestMatrix cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("AgentLabOrganHarvestMatrix cannot bridge vendor runtime.")
        if self.authority_expansion:
            raise ValueError("AgentLabOrganHarvestMatrix cannot expand authority.")
        candidate_ids = [candidate.id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("AgentLabOrganHarvestMatrix cannot contain duplicate candidates.")
        if any(candidate.target_promotion_level != OrganPromotionLevel.L2_SENTINEL_CONTRACT for candidate in self.candidates):
            raise ValueError("AgentLabOrganHarvestMatrix only carries L2 contract candidates.")
        if not self.id:
            self.id = _stable_id("hmatrix", {"candidate_ids": candidate_ids})
        return self

    def vendor_references(self) -> list[VendorHarvestReference]:
        return [candidate.to_vendor_reference() for candidate in self.candidates]

    def by_power_family(self, family: HarvestPowerFamily) -> list[OrganHarvestCandidate]:
        return [candidate for candidate in self.candidates if candidate.power_family == family]

    def by_organ_type(self, organ_type: OrganType) -> list[OrganHarvestCandidate]:
        return [candidate for candidate in self.candidates if candidate.organ_type == organ_type]

    def record(self, event_bus: EventBus | None = None) -> AgentLabOrganHarvestMatrix:
        if event_bus is None:
            return self
        recorded = [candidate.record(event_bus) for candidate in self.candidates]
        event = event_bus.append(
            AgentEventType.ORGAN_HARVEST_MATRIX_BUILT,
            "Agent Lab organ harvest matrix built without runtime execution.",
            payload={
                "matrix_id": self.id,
                "candidate_count": len(recorded),
                "source_systems": sorted({candidate.source.source_system for candidate in recorded}),
                "runtime_powers_added": 0,
                "vendor_code_copied": False,
                "vendor_runtime_bridge": False,
                "authority_expansion": False,
            },
            trace_refs=[trace for candidate in recorded for trace in candidate.trace_refs],
        )
        return self.model_copy(update={"candidates": recorded, "trace_refs": [event.id]})


class AgentLabOrganHarvestClassifier:
    def build_default_matrix(self, *, event_bus: EventBus | None = None) -> AgentLabOrganHarvestMatrix:
        sources = _default_sources()
        by_system = {source.source_system: source for source in sources}
        candidates = [
            OrganHarvestCandidate(
                source=by_system["OpenClaw"],
                power_family=HarvestPowerFamily.ACTION_KERNEL,
                organ_type=OrganType.GENERIC,
                mechanism="Gateway/action kernel connecting plugins, browser, channels, shell, memory, and subagents.",
                sentinel_rewrite="SentinelActionKernel",
                target_phase="P6B/P7",
                required_controls=["authority_mapping", "risk_profile", "dry_run", "approval", "trace", "FinalGate"],
                blocked_runtime_surfaces=["shell_execution", "browser_submit", "channel_send", "dynamic_plugin_install"],
                risk_notes=["gateway blast radius", "external inputs near execution"],
                evidence_refs=["openclaw_final", "g9_synthesis", "superpower_table"],
            ),
            OrganHarvestCandidate(
                source=by_system["Hermes"],
                power_family=HarvestPowerFamily.MEMORY_SKILL,
                organ_type=OrganType.GENERIC,
                mechanism="Persistent memory, skill index, hooks, context compression, and delegated subagents.",
                sentinel_rewrite="SentinelMemorySkillSpec",
                target_phase="P7/P10",
                required_controls=["non_authoritative_memory", "skill_scan", "hook_fail_closed", "context_trust_labels"],
                blocked_runtime_surfaces=["memory_as_policy", "autonomous_skill_execution", "oauth_skill_setup", "fail_open_hooks"],
                risk_notes=["hidden prompt-shaping layer", "memory poisoning"],
                evidence_refs=["hermes_final", "g9_synthesis", "superpower_table"],
            ),
            OrganHarvestCandidate(
                source=by_system["OpenJarvis"],
                power_family=HarvestPowerFamily.COST_ROUTING,
                organ_type=OrganType.GENERIC,
                mechanism="Hardware/model routing, query complexity scoring, telemetry, learned routing, and skill import.",
                sentinel_rewrite="SentinelCostRouter",
                target_phase="P7/P9",
                required_controls=["budget_cap", "route_trace", "confidence", "manual_override", "proposal_only_learning"],
                blocked_runtime_surfaces=["host_shell_execution", "runtime_skill_sync", "open_by_default_capability_policy", "learned_config_autowrite"],
                risk_notes=["routing can accelerate unsafe execution", "skill import supply-chain risk"],
                evidence_refs=["openjarvis_final", "g9_synthesis", "superpower_table"],
            ),
            OrganHarvestCandidate(
                source=by_system["JARVIS"],
                power_family=HarvestPowerFamily.SIDECAR_DESKTOP,
                organ_type=OrganType.DESKTOP_SIDECAR,
                mechanism="Permissioned sidecar, desktop/browser awareness, approval lifecycle, and host action routing.",
                sentinel_rewrite="PermissionedSidecarManifest",
                target_phase="P6J/P9",
                required_controls=["signed_manifest", "path_scope", "screen_sanitizer", "approval", "kill_switch", "audit"],
                blocked_runtime_surfaces=["raw_shell", "clipboard_read", "screenshot_capture", "desktop_keystrokes", "arbitrary_cdp_evaluate"],
                risk_notes=["host-level authority", "privacy leakage"],
                evidence_refs=["jarvis_final", "g9_synthesis", "superpower_table"],
            ),
            OrganHarvestCandidate(
                source=by_system["financial-services"],
                power_family=HarvestPowerFamily.FINANCE_OPERATOR,
                organ_type=OrganType.FINANCE,
                mechanism="Financial domain procedures, analyst workflows, model audit patterns, and evaluation fixtures.",
                sentinel_rewrite="FinancialProcedureGraph",
                target_phase="P6G/P7/P8",
                required_controls=["human_review", "no_profit_guarantee", "risk_disclosure", "evidence_refs", "spend_special_authority"],
                blocked_runtime_surfaces=["payment_execution", "trade_execution", "investment_advice_without_review", "credential_access"],
                risk_notes=["financial harm", "regulated workflows"],
                evidence_refs=["financial_services_repo", "source_research_ledger", "power_harvest_map"],
            ),
            OrganHarvestCandidate(
                source=by_system["CloakBrowser"],
                power_family=HarvestPowerFamily.BROWSER_POWER,
                organ_type=OrganType.BROWSER,
                mechanism="Browser reliability, session continuity, fingerprint consistency, and detection-resilience diagnostics.",
                sentinel_rewrite="BrowserPowerGovernor",
                target_phase="P6C/P6K/P9",
                required_controls=["browser_compliance_gate", "misuse_classifier", "domain_policy", "receipts", "FinalGate"],
                blocked_runtime_surfaces=["fake_identity", "kyc_bypass", "credential_theft", "unauthorized_scraping", "access_control_evasion"],
                risk_notes=["high-power browser capability", "misuse objective must be blocked"],
                evidence_refs=["cloak_browser_repo", "source_research_ledger", "cloak_power_review"],
            ),
        ]
        matrix = AgentLabOrganHarvestMatrix(candidates=candidates)
        return matrix.record(event_bus)


def _default_sources() -> list[AgentLabHarvestSource]:
    return [
        AgentLabHarvestSource(
            source_system="OpenClaw",
            source_kind=HarvestSourceKind.FINAL_FORENSIC_REPORT,
            local_path="agent-lab/audits/final/openclaw_final_forensic_report.md",
            source_url="https://github.com/basetenlabs/openclaw-baseten.git",
            source_commit="a2288c2b09e621f89a915960398f58e200b3b69d",
            evidence_refs=["openclaw_final", "g9_synthesis", "superpower_table"],
        ),
        AgentLabHarvestSource(
            source_system="Hermes",
            source_kind=HarvestSourceKind.FINAL_FORENSIC_REPORT,
            local_path="agent-lab/audits/final/hermes_final_forensic_report.md",
            source_url="https://github.com/nousresearch/hermes-agent",
            source_commit="35c57cc46b88710a98c4d43107b87b4ab828e3eb",
            evidence_refs=["hermes_final", "g9_synthesis", "superpower_table"],
        ),
        AgentLabHarvestSource(
            source_system="OpenJarvis",
            source_kind=HarvestSourceKind.FINAL_FORENSIC_REPORT,
            local_path="agent-lab/audits/final/openjarvis_final_forensic_report.md",
            source_url="https://github.com/open-jarvis/OpenJarvis",
            source_commit="484d0f090b127a9b8a00f02d64c35428cb7be706",
            evidence_refs=["openjarvis_final", "g9_synthesis", "superpower_table"],
        ),
        AgentLabHarvestSource(
            source_system="JARVIS",
            source_kind=HarvestSourceKind.FINAL_FORENSIC_REPORT,
            local_path="agent-lab/audits/final/jarvis_final_forensic_report.md",
            source_url="https://github.com/vierisid/jarvis",
            source_commit="7b66f0d3c77a4d050d56ff98b5723fd00b9fb937",
            evidence_refs=["jarvis_final", "g9_synthesis", "superpower_table"],
        ),
        AgentLabHarvestSource(
            source_system="financial-services",
            source_kind=HarvestSourceKind.EXTERNAL_SOURCE_LEDGER,
            local_path="sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/16_FINANCIAL_SERVICES_HARVEST_MAP.md",
            source_url="https://github.com/anthropics/financial-services",
            evidence_refs=["financial_services_repo", "source_research_ledger", "power_harvest_map"],
        ),
        AgentLabHarvestSource(
            source_system="CloakBrowser",
            source_kind=HarvestSourceKind.EXTERNAL_SOURCE_LEDGER,
            local_path="sentinel-control/docs/architecture/SENTINEL_A_TO_Z_LOCK/17_CLOAK_BROWSER_POWER_REVIEW.md",
            source_url="https://github.com/CloakHQ/CloakBrowser",
            evidence_refs=["cloak_browser_repo", "source_research_ledger", "cloak_power_review"],
        ),
    ]
