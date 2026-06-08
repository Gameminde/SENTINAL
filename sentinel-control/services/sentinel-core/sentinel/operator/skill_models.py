from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.redaction import redact_operator_text, redact_operator_value, sanitize_operator_refs
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import (
    OrganSafetyScanCategory,
    merge_scan_results,
    scan_forbidden_payload_categorized,
)
from sentinel.telemetry.redaction import sanitize_telemetry_value


def skill_utc_now() -> datetime:
    return datetime.now(UTC)


class SkillLifecycleStatus(StrEnum):
    DRAFT = "draft"
    SCANNED = "scanned"
    QUARANTINED = "quarantined"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    PROMOTED = "promoted"
    REVOKED = "revoked"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


class SkillScanDecision(StrEnum):
    PASS = "pass"
    QUARANTINE = "quarantine"
    BLOCK = "block"


class SkillExecutionStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    REVOKED = "revoked"


class SkillFabricConfig(SentinelModel):
    require_existing_mission: bool = True
    require_approved_skill: bool = True
    require_receipts_for_execution: bool = True
    require_finalgate_for_execution: bool = True
    allow_eval_only_scanned_skills: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _config_is_data(self) -> SkillFabricConfig:
        _assert_skill_data_only(self, "skill_fabric_config")
        return self


class SkillProvenance(SentinelModel):
    source_kind: str
    source_ref: str
    content_hash: str
    vendor_specimen: bool = False
    created_at: datetime = Field(default_factory=skill_utc_now)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _provenance_is_data(self) -> SkillProvenance:
        _assert_skill_data_only(self, "skill_provenance")
        self.source_kind = _safe_identifier(self.source_kind, "source_kind")
        self.source_ref = redact_operator_text(self.source_ref)
        return self


class SkillDeclaredAuthority(SentinelModel):
    action: str
    tool: str | None = None
    domain: str | None = None
    path: str | None = None
    max_actions: int = Field(default=1, ge=0)
    max_cost_usd: float = Field(default=0.0, ge=0.0)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _authority_decl_is_data(self) -> SkillDeclaredAuthority:
        _assert_skill_data_only(self, "skill_declared_authority")
        self.action = _safe_action(self.action)
        self.tool = _safe_identifier(self.tool, "tool") if self.tool else None
        self.domain = redact_operator_text(self.domain) if self.domain else None
        self.path = _safe_logical_path(self.path) if self.path else None
        return self


class SkillDeclaredSideEffect(SentinelModel):
    effect_kind: str
    reversible: bool = True
    rollback_hint: str | None = None
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _side_effect_is_data(self) -> SkillDeclaredSideEffect:
        _assert_skill_data_only(self, "skill_declared_side_effect")
        self.effect_kind = _safe_identifier(self.effect_kind, "effect_kind")
        self.rollback_hint = redact_operator_text(self.rollback_hint) if self.rollback_hint else None
        return self


class SkillInputContract(SentinelModel):
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _input_contract_is_data(self) -> SkillInputContract:
        _assert_skill_data_only(self, "skill_input_contract")
        self.required_fields = [_safe_identifier(field, "required_field") for field in self.required_fields]
        self.optional_fields = [_safe_identifier(field, "optional_field") for field in self.optional_fields]
        return self


class SkillOutputContract(SentinelModel):
    required_fields: list[str] = Field(default_factory=list)
    require_evidence_refs: bool = True
    require_safe_summary: bool = True
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _output_contract_is_data(self) -> SkillOutputContract:
        _assert_skill_data_only(self, "skill_output_contract")
        self.required_fields = [_safe_identifier(field, "required_field") for field in self.required_fields]
        return self


class SkillEvidenceRequirement(SentinelModel):
    requirement: str
    minimum_refs: int = Field(default=1, ge=0)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _evidence_requirement_is_data(self) -> SkillEvidenceRequirement:
        _assert_skill_data_only(self, "skill_evidence_requirement")
        self.requirement = redact_operator_text(self.requirement)
        return self


class SkillRiskProfile(SentinelModel):
    risk_lane: str = "low"
    max_risk_score: float = Field(default=10.0, ge=0.0, le=100.0)
    requires_operator_confirmation: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _risk_is_data(self) -> SkillRiskProfile:
        _assert_skill_data_only(self, "skill_risk_profile")
        self.risk_lane = _safe_identifier(self.risk_lane, "risk_lane")
        return self


class SkillRollbackPosture(SentinelModel):
    posture: str
    reversible: bool = True
    rollback_steps: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _rollback_is_data(self) -> SkillRollbackPosture:
        _assert_skill_data_only(self, "skill_rollback_posture")
        self.posture = redact_operator_text(self.posture)
        self.rollback_steps = [redact_operator_text(step) for step in self.rollback_steps]
        _reject_skill_control_payload({"posture": self.posture, "rollback_steps": self.rollback_steps}, context="skill_rollback_posture")
        return self


class ProcedureStep(SentinelModel):
    step_id: str
    title: str
    action_kind: str
    safe_summary: str
    requested_tools: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _step_is_data(self) -> ProcedureStep:
        _assert_skill_data_only(self, "procedure_step")
        self.step_id = _safe_identifier(self.step_id, "step_id")
        self.title = redact_operator_text(self.title)
        self.action_kind = _safe_action(self.action_kind)
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.requested_tools = [_safe_identifier(tool, "requested_tool") for tool in self.requested_tools]
        self.evidence_requirements = [redact_operator_text(requirement) for requirement in self.evidence_requirements]
        self.metadata = _sanitize_skill_payload(self.metadata, context="procedure_step")
        _reject_procedure_direct_runtime(self)
        return self


class ProcedureGraph(SentinelModel):
    steps: list[ProcedureStep] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _graph_is_valid(self) -> ProcedureGraph:
        _assert_skill_data_only(self, "procedure_graph")
        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen:
                raise ValueError(f"duplicate procedure step id: {step.step_id}")
            seen.add(step.step_id)
        for step in self.steps:
            if any(dep not in seen for dep in step.depends_on):
                raise ValueError(f"procedure step {step.step_id} has unknown dependency")
            if step.step_id in step.depends_on:
                raise ValueError("procedure step cannot depend on itself")
        return self


class ProcedureManifest(SentinelModel):
    procedure_id: str
    version: str
    title: str
    safe_summary: str
    graph: ProcedureGraph
    rollback_posture: SkillRollbackPosture
    metadata: dict[str, Any] = Field(default_factory=dict)
    manifest_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="before")
    @classmethod
    def _coerce_nested(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if isinstance(data.get("graph"), dict) and "steps" in data["graph"]:
                data = {**data, "graph": ProcedureGraph.model_validate(data["graph"])}
            if isinstance(data.get("rollback_posture"), dict):
                data = {**data, "rollback_posture": SkillRollbackPosture.model_validate(data["rollback_posture"])}
        return data

    @model_validator(mode="after")
    def _procedure_is_data(self) -> ProcedureManifest:
        _assert_skill_data_only(self, "procedure_manifest")
        self.procedure_id = _safe_identifier(self.procedure_id, "procedure_id")
        self.version = _safe_version(self.version)
        self.title = redact_operator_text(self.title)
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.metadata = _sanitize_skill_payload(self.metadata, context="procedure_manifest")
        if not self.manifest_hash:
            payload = self.safe_model_dump()
            payload["manifest_hash"] = ""
            self.manifest_hash = stable_hash(payload)
        return self

    def with_hash(self) -> ProcedureManifest:
        payload = self.safe_model_dump()
        payload["manifest_hash"] = ""
        return self.model_copy(update={"manifest_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["manifest_hash"]
        payload["manifest_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "version": self.version,
            "title": self.title,
            "safe_summary": self.safe_summary,
            "graph": self.graph.model_dump(mode="json"),
            "rollback_posture": self.rollback_posture.model_dump(mode="json"),
            "metadata": self.metadata,
            "manifest_hash": self.manifest_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class SkillManifest(SentinelModel):
    skill_id: str
    version: str
    name: str
    safe_summary: str
    provenance: SkillProvenance
    declared_authority: list[SkillDeclaredAuthority]
    declared_side_effects: list[SkillDeclaredSideEffect]
    input_contract: SkillInputContract
    output_contract: SkillOutputContract
    evidence_requirements: list[SkillEvidenceRequirement]
    risk_profile: SkillRiskProfile
    procedure: ProcedureManifest
    metadata: dict[str, Any] = Field(default_factory=dict)
    memory_refs_are_authority: bool = False
    receipts_are_authority: bool = False
    manifest_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="before")
    @classmethod
    def _coerce_nested(cls, data: Any) -> Any:
        if isinstance(data, dict):
            mapping = {
                "provenance": SkillProvenance,
                "input_contract": SkillInputContract,
                "output_contract": SkillOutputContract,
                "risk_profile": SkillRiskProfile,
                "procedure": ProcedureManifest,
            }
            data = dict(data)
            for key, model in mapping.items():
                if isinstance(data.get(key), dict):
                    data[key] = model.model_validate(data[key])
        return data

    @model_validator(mode="after")
    def _manifest_is_data(self) -> SkillManifest:
        _assert_skill_data_only(self, "skill_manifest")
        self.skill_id = _safe_identifier(self.skill_id, "skill_id")
        self.version = _safe_version(self.version)
        self.name = redact_operator_text(self.name)
        self.safe_summary = redact_operator_text(self.safe_summary)
        if not self.declared_authority:
            raise ValueError("skill manifest requires declared authority")
        if not self.declared_side_effects:
            raise ValueError("skill manifest requires declared side effects")
        if not self.evidence_requirements:
            raise ValueError("skill manifest requires evidence requirements")
        if self.memory_refs_are_authority:
            raise ValueError("skill memory cannot become authority")
        if self.receipts_are_authority:
            raise ValueError("skill receipt/finalgate refs cannot become authority")
        self.metadata = _sanitize_skill_payload(self.metadata, context="skill_manifest")
        _reject_skill_provider_override(self.metadata, context="skill_manifest")
        if not self.manifest_hash:
            payload = self.safe_model_dump()
            payload["manifest_hash"] = ""
            self.manifest_hash = stable_hash(payload)
        return self

    def with_hash(self) -> SkillManifest:
        payload = self.safe_model_dump()
        payload["manifest_hash"] = ""
        return self.model_copy(update={"manifest_hash": stable_hash(payload)})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["manifest_hash"]
        payload["manifest_hash"] = ""
        return bool(stored) and stored == stable_hash(payload)

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "name": self.name,
            "safe_summary": self.safe_summary,
            "provenance": self.provenance.model_dump(mode="json"),
            "declared_authority": [item.model_dump(mode="json") for item in self.declared_authority],
            "declared_side_effects": [item.model_dump(mode="json") for item in self.declared_side_effects],
            "input_contract": self.input_contract.model_dump(mode="json"),
            "output_contract": self.output_contract.model_dump(mode="json"),
            "evidence_requirements": [item.model_dump(mode="json") for item in self.evidence_requirements],
            "risk_profile": self.risk_profile.model_dump(mode="json"),
            "procedure": self.procedure.safe_model_dump(),
            "metadata": self.metadata,
            "memory_refs_are_authority": self.memory_refs_are_authority,
            "receipts_are_authority": self.receipts_are_authority,
            "manifest_hash": self.manifest_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class SkillLifecycleRecord(SentinelModel):
    lifecycle_id: str = Field(default_factory=lambda: new_id("skill_lifecycle"))
    mission_id: str
    skill_id: str
    version: str
    status: SkillLifecycleStatus
    reason: str
    created_at: datetime = Field(default_factory=skill_utc_now)
    lifecycle_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _lifecycle_is_data(self) -> SkillLifecycleRecord:
        _assert_skill_data_only(self, "skill_lifecycle_record")
        self.skill_id = _safe_identifier(self.skill_id, "skill_id")
        self.version = _safe_version(self.version)
        self.reason = redact_operator_text(self.reason)
        if not self.lifecycle_hash:
            payload = self.safe_model_dump()
            payload["lifecycle_hash"] = ""
            self.lifecycle_hash = stable_hash(payload)
        return self

    def with_hash(self) -> SkillLifecycleRecord:
        payload = self.safe_model_dump()
        payload["lifecycle_hash"] = ""
        return self.model_copy(update={"lifecycle_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "lifecycle_id": self.lifecycle_id,
            "mission_id": self.mission_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "status": self.status.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "lifecycle_hash": self.lifecycle_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class SkillScannerResult(SentinelModel):
    scanner_result_id: str = Field(default_factory=lambda: new_id("skill_scan"))
    mission_id: str
    skill_id: str
    version: str
    status: SkillLifecycleStatus
    decision: SkillScanDecision
    findings: list[str] = Field(default_factory=list)
    scanner_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _scan_is_data(self) -> SkillScannerResult:
        _assert_skill_data_only(self, "skill_scanner_result")
        self.skill_id = _safe_identifier(self.skill_id, "skill_id")
        self.version = _safe_version(self.version)
        self.findings = [redact_operator_text(finding) for finding in self.findings]
        if not self.scanner_hash:
            payload = self.safe_model_dump()
            payload["scanner_hash"] = ""
            self.scanner_hash = stable_hash(payload)
        return self

    def with_hash(self) -> SkillScannerResult:
        payload = self.safe_model_dump()
        payload["scanner_hash"] = ""
        return self.model_copy(update={"scanner_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "scanner_result_id": self.scanner_result_id,
            "mission_id": self.mission_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "status": self.status.value,
            "decision": self.decision.value,
            "findings": self.findings,
            "scanner_hash": self.scanner_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class SkillQuarantineRecord(SentinelModel):
    quarantine_id: str = Field(default_factory=lambda: new_id("skill_quarantine"))
    mission_id: str
    skill_id: str
    version: str
    reasons: list[str]
    created_at: datetime = Field(default_factory=skill_utc_now)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _quarantine_is_data(self) -> SkillQuarantineRecord:
        _assert_skill_data_only(self, "skill_quarantine_record")
        self.reasons = [redact_operator_text(reason) for reason in self.reasons]
        return self


class SkillSandboxEvaluation(SentinelModel):
    evaluation_id: str = Field(default_factory=lambda: new_id("skill_eval"))
    mission_id: str
    skill_id: str
    version: str
    status: SkillLifecycleStatus = SkillLifecycleStatus.EVALUATED
    dry_run_only: bool = True
    passed: bool = False
    findings: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _evaluation_is_data(self) -> SkillSandboxEvaluation:
        _assert_skill_data_only(self, "skill_sandbox_evaluation")
        if not self.dry_run_only:
            raise ValueError("skill evaluation must remain dry-run only in V1")
        self.findings = [redact_operator_text(finding) for finding in self.findings]
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        return self


class SkillScorecard(SentinelModel):
    scorecard_id: str = Field(default_factory=lambda: new_id("skill_score"))
    mission_id: str
    skill_id: str
    version: str
    scan_passed: bool
    evaluation_passed: bool
    rollback_ready: bool
    authority_declared: bool
    side_effects_declared: bool
    evidence_declared: bool
    status: SkillLifecycleStatus = SkillLifecycleStatus.EVALUATED
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _scorecard_is_data(self) -> SkillScorecard:
        _assert_skill_data_only(self, "skill_scorecard")
        return self


class SkillApprovalRecord(SentinelModel):
    approval_id: str = Field(default_factory=lambda: new_id("skill_approval"))
    mission_id: str
    skill_id: str
    version: str
    approved_by: str
    status: SkillLifecycleStatus = SkillLifecycleStatus.APPROVED
    created_at: datetime = Field(default_factory=skill_utc_now)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _approval_is_data(self) -> SkillApprovalRecord:
        _assert_skill_data_only(self, "skill_approval_record")
        self.approved_by = redact_operator_text(self.approved_by)
        return self


class SkillPromotionRecord(SentinelModel):
    promotion_id: str = Field(default_factory=lambda: new_id("skill_promotion"))
    mission_id: str
    skill_id: str
    version: str
    promoted_by: str
    status: SkillLifecycleStatus = SkillLifecycleStatus.PROMOTED
    created_at: datetime = Field(default_factory=skill_utc_now)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _promotion_is_data(self) -> SkillPromotionRecord:
        _assert_skill_data_only(self, "skill_promotion_record")
        self.promoted_by = redact_operator_text(self.promoted_by)
        return self


class SkillRevocationRecord(SentinelModel):
    revocation_id: str = Field(default_factory=lambda: new_id("skill_revocation"))
    mission_id: str
    skill_id: str
    version: str
    revoked_by: str
    reason: str = "operator_revoked"
    status: SkillLifecycleStatus = SkillLifecycleStatus.REVOKED
    created_at: datetime = Field(default_factory=skill_utc_now)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _revocation_is_data(self) -> SkillRevocationRecord:
        _assert_skill_data_only(self, "skill_revocation_record")
        self.revoked_by = redact_operator_text(self.revoked_by)
        self.reason = redact_operator_text(self.reason)
        return self


class SkillExecutionRequest(SentinelModel):
    request_id: str = Field(default_factory=lambda: new_id("skill_exec_req"))
    mission_id: str
    skill_id: str
    version: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "operator"
    parent_envelope_id: str | None = None
    status: SkillExecutionStatus = SkillExecutionStatus.REQUESTED
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _request_is_data(self) -> SkillExecutionRequest:
        _assert_skill_data_only(self, "skill_execution_request")
        self.inputs = _sanitize_skill_payload(self.inputs, context="skill_execution_request")
        self.requested_by = redact_operator_text(self.requested_by)
        return self


class SkillExecutionPlan(SentinelModel):
    plan_id: str = Field(default_factory=lambda: new_id("skill_plan"))
    mission_id: str
    skill_id: str
    version: str
    procedure_id: str
    step_ids: list[str]
    declared_actions: list[str]
    rollback_posture: SkillRollbackPosture
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _plan_is_data(self) -> SkillExecutionPlan:
        _assert_skill_data_only(self, "skill_execution_plan")
        self.step_ids = [_safe_identifier(step_id, "step_id") for step_id in self.step_ids]
        self.declared_actions = [_safe_action(action) for action in self.declared_actions]
        return self


class SkillExecutionReceipt(SentinelModel):
    receipt_id: str = Field(default_factory=lambda: new_id("skill_receipt"))
    mission_id: str
    skill_id: str
    version: str
    procedure_run_id: str
    status: SkillExecutionStatus
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    receipt_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _receipt_is_data(self) -> SkillExecutionReceipt:
        _assert_skill_data_only(self, "skill_execution_receipt")
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        if not self.receipt_hash:
            payload = self.safe_model_dump()
            payload["receipt_hash"] = ""
            self.receipt_hash = stable_hash(payload)
        return self

    def with_hash(self) -> SkillExecutionReceipt:
        payload = self.safe_model_dump()
        payload["receipt_hash"] = ""
        return self.model_copy(update={"receipt_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "mission_id": self.mission_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "procedure_run_id": self.procedure_run_id,
            "status": self.status.value,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "receipt_hash": self.receipt_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class SkillExecutionResult(SentinelModel):
    result_id: str = Field(default_factory=lambda: new_id("skill_exec_result"))
    mission_id: str
    skill_id: str
    version: str
    procedure_run_id: str
    status: SkillExecutionStatus
    safe_summary: str
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    result_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _result_is_data(self) -> SkillExecutionResult:
        _assert_skill_data_only(self, "skill_execution_result")
        self.safe_summary = redact_operator_text(self.safe_summary)
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.blocked_reason = redact_operator_text(self.blocked_reason) if self.blocked_reason else None
        if not self.result_hash:
            payload = self.safe_model_dump()
            payload["result_hash"] = ""
            self.result_hash = stable_hash(payload)
        return self

    def with_hash(self) -> SkillExecutionResult:
        payload = self.safe_model_dump()
        payload["result_hash"] = ""
        return self.model_copy(update={"result_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "mission_id": self.mission_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "procedure_run_id": self.procedure_run_id,
            "status": self.status.value,
            "safe_summary": self.safe_summary,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "evidence_refs": self.evidence_refs,
            "blocked_reason": self.blocked_reason,
            "result_hash": self.result_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ProcedureRun(SentinelModel):
    procedure_run_id: str = Field(default_factory=lambda: new_id("procedure_run"))
    mission_id: str
    skill_id: str
    version: str
    procedure_id: str
    status: SkillExecutionStatus = SkillExecutionStatus.REQUESTED
    step_results: list[dict[str, Any]] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    rollback_posture: SkillRollbackPosture
    created_at: datetime = Field(default_factory=skill_utc_now)
    updated_at: datetime = Field(default_factory=skill_utc_now)
    run_hash: str = ""
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _run_is_data(self) -> ProcedureRun:
        _assert_skill_data_only(self, "procedure_run")
        self.step_results = _sanitize_skill_payload(self.step_results, context="procedure_run_step_results")
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        if not self.run_hash:
            payload = self.safe_model_dump()
            payload["run_hash"] = ""
            self.run_hash = stable_hash(payload)
        return self

    def with_hash(self) -> ProcedureRun:
        payload = self.safe_model_dump()
        payload["run_hash"] = ""
        return self.model_copy(update={"run_hash": stable_hash(payload)})

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "procedure_run_id": self.procedure_run_id,
            "mission_id": self.mission_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "procedure_id": self.procedure_id,
            "status": self.status.value,
            "step_results": self.step_results,
            "receipt_refs": self.receipt_refs,
            "finalgate_certificate_refs": self.finalgate_certificate_refs,
            "memory_feedback_refs": self.memory_feedback_refs,
            "evidence_refs": self.evidence_refs,
            "rollback_posture": self.rollback_posture.model_dump(mode="json"),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "run_hash": self.run_hash,
            "authority_effect": self.authority_effect,
            "data_not_authority": self.data_not_authority,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }


class ProcedureTelemetrySummary(SentinelModel):
    mission_id: str
    skill_id: str
    procedure_run_id: str
    event_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _summary_is_data(self) -> ProcedureTelemetrySummary:
        _assert_skill_data_only(self, "procedure_telemetry_summary")
        self.event_refs = sanitize_operator_refs(self.event_refs)
        self.metric_refs = sanitize_operator_refs(self.metric_refs)
        return self


class ProcedureReplayView(SentinelModel):
    mission_id: str
    skill_id: str | None = None
    version: str | None = None
    procedure_run_id: str | None = None
    manifest_version: str | None = None
    scan_result_refs: list[str] = Field(default_factory=list)
    lifecycle_events: list[str] = Field(default_factory=list)
    procedure_step_events: list[str] = Field(default_factory=list)
    receipt_refs: list[str] = Field(default_factory=list)
    finalgate_certificate_refs: list[str] = Field(default_factory=list)
    memory_feedback_refs: list[str] = Field(default_factory=list)
    telemetry_refs: list[str] = Field(default_factory=list)
    rollback_posture: str | None = None
    timeline_valid: bool = True
    reexecuted_actions: bool = False
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _replay_is_data(self) -> ProcedureReplayView:
        _assert_skill_data_only(self, "procedure_replay_view")
        self.receipt_refs = sanitize_operator_refs(self.receipt_refs)
        self.finalgate_certificate_refs = sanitize_operator_refs(self.finalgate_certificate_refs)
        self.memory_feedback_refs = sanitize_operator_refs(self.memory_feedback_refs)
        self.telemetry_refs = sanitize_operator_refs(self.telemetry_refs)
        return self


class CompiledTrajectoryProcedure(SentinelModel):
    trajectory_id: str
    skill_id: str
    version: str
    required_browser_authority: list[str]
    target_ref_hashes: list[str]
    evidence_refs: list[str]
    boundary_conditions: list[str] = Field(default_factory=list)
    authority_effect: str = "none"
    data_not_authority: bool = True
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _trajectory_is_guarded_data(self) -> CompiledTrajectoryProcedure:
        _assert_skill_data_only(self, "compiled_trajectory_procedure")
        self.trajectory_id = _safe_identifier(self.trajectory_id, "trajectory_id")
        self.skill_id = _safe_identifier(self.skill_id, "skill_id")
        self.version = _safe_version(self.version)
        self.required_browser_authority = [_safe_identifier(item, "browser_authority") for item in self.required_browser_authority]
        self.target_ref_hashes = sanitize_operator_refs(self.target_ref_hashes)
        self.evidence_refs = sanitize_operator_refs(self.evidence_refs)
        self.boundary_conditions = [redact_operator_text(condition).lower() for condition in self.boundary_conditions]
        blocked = {"login", "payment", "account", "kyc", "captcha", "credential", "submit"}
        if blocked.intersection(set(self.boundary_conditions)):
            raise ValueError("browser trajectory crosses sensitive boundary")
        if any(item in {"browser_login", "browser_payment", "browser_submit"} for item in self.required_browser_authority):
            raise ValueError("browser trajectory crosses sensitive boundary")
        return self


def _assert_skill_data_only(value: Any, context: str) -> None:
    assert_data_not_authority(
        context=context,
        authority_effect=getattr(value, "authority_effect", "none"),
        data_not_authority=getattr(value, "data_not_authority", True),
        can_grant_authority=getattr(value, "can_grant_authority", False),
        can_execute=getattr(value, "can_execute", False),
    )


def _sanitize_skill_payload(payload: Any, *, context: str) -> Any:
    sanitized = redact_operator_value(payload)
    sanitized, _, _ = sanitize_telemetry_value(sanitized, path="$")
    _reject_skill_control_payload(sanitized, context=context)
    _reject_skill_provider_override(sanitized, context=context)
    return sanitized


def _reject_skill_control_payload(payload: Any, *, context: str) -> None:
    scan = scan_forbidden_payload_categorized(payload, path="$")
    blocked = list(scan[OrganSafetyScanCategory.ALL.value])
    text = repr(payload).lower()
    if "authority_grant" in text or "authority grant" in text:
        raise ValueError(f"{context}: skill manifest cannot request authority")
    if blocked:
        if scan[OrganSafetyScanCategory.AUTHORITY_EXPANSION.value]:
            raise ValueError(f"{context}: skill manifest cannot request authority")
        if scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]:
            raise ValueError(f"{context}: skill manifest cannot override provider/backend/model")
        raise ValueError(f"{context}: unsafe skill payload")


def _reject_skill_provider_override(payload: Any, *, context: str) -> None:
    scan = scan_forbidden_payload_categorized(payload, path="$")
    if scan[OrganSafetyScanCategory.PROVIDER_OVERRIDE.value]:
        raise ValueError(f"{context}: skill manifest cannot override provider/backend/model")
    text = repr(payload).lower()
    if "fallback/auto" in text or "fallback_auto" in text or '"auto"' in text or "'auto'" in text:
        raise ValueError(f"{context}: skill manifest cannot request provider fallback/AUTO")


def _reject_procedure_direct_runtime(step: ProcedureStep) -> None:
    text = " ".join(
        [
            step.action_kind,
            " ".join(step.requested_tools),
            repr(step.metadata),
            step.safe_summary,
        ]
    ).lower()
    blocked = (
        "organ_dispatcher",
        "direct_organ",
        "runtime_dispatch",
        "delegated_action_gate",
        "missionauthorityenvelope(",
        "import sentinel.agent.organs",
        "dynamic_import",
        "remote_plugin",
    )
    if any(item in text for item in blocked):
        raise ValueError("procedure step cannot call runtime directly")


def _safe_identifier(value: str, field_name: str) -> str:
    value = redact_operator_text(str(value)).strip()
    if not value:
        raise ValueError(f"{field_name} required")
    if any(part in value for part in ("/", "\\", "..", "\x00")):
        raise ValueError(f"{field_name} unsafe")
    return value


def _safe_version(value: str) -> str:
    text = _safe_identifier(value, "version")
    if len(text) > 64:
        raise ValueError("version too long")
    return text


def _safe_action(value: str) -> str:
    text = _safe_identifier(value, "action")
    scan = scan_forbidden_payload_categorized(text, path="$")
    forbidden = merge_scan_results(scan)[OrganSafetyScanCategory.ALL.value]
    if forbidden and text not in {"read", "analyze", "draft", "write", "workspace_write", "browser_observe_public"}:
        raise ValueError("action unsafe")
    if any(ch in text for ch in (";", "|", "&", "$", "`", "\n", "\r")):
        raise ValueError("action unsafe")
    return text


def _safe_logical_path(value: str) -> str:
    text = redact_operator_text(str(value)).replace("\\", "/").strip()
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("skill path escapes scope")
    return path.as_posix()
