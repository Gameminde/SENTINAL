from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeAlias

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash
from sentinel.shared.models import SentinelModel, new_id


class DelegatedActionLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    L7 = "L7"


class ProposalArtifactKind(StrEnum):
    MISSION_PLAN = "mission_plan"
    STRATEGY = "strategy"
    RESEARCH_PLAN = "research_plan"
    EVIDENCE_GAP = "evidence_gap"
    BROWSER_STEP_CANDIDATE = "browser_step_candidate"
    API_REQUEST_CANDIDATE = "api_request_candidate"
    CHANNEL_DRAFT_CANDIDATE = "channel_draft_candidate"
    FILE_OPERATION_CANDIDATE = "file_operation_candidate"
    CODE_PATCH_PLAN = "code_patch_plan"
    RISK_MITIGATION = "risk_mitigation"
    SELF_IMPROVEMENT = "self_improvement"
    FINAL_PACKET = "final_packet"


class ProposalArtifactStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_MORE_EVIDENCE = "needs_more_evidence"


class ProposalValidationResult(SentinelModel):
    valid: bool
    status: ProposalArtifactStatus
    reasons: list[str] = Field(default_factory=list)
    proposal_hash: str | None = None
    invented_evidence_refs: list[str] = Field(default_factory=list)
    missing_evidence: bool = False
    can_execute: bool = False
    can_grant_authority: bool = False


class ProposalArtifact(SentinelModel):
    proposal_id: str = Field(default_factory=lambda: new_id("proposal"))
    source_role_id: str
    mission_id: str
    objective_summary: str
    artifact_kind: ProposalArtifactKind
    action_level_candidate: DelegatedActionLevel
    authority_class: str
    risk_class: str
    budget_estimate: dict[str, Any]
    evidence_refs: list[str]
    receipt_refs: list[str]
    expected_outcome: str
    rollback_posture: str
    user_review_required: bool
    uncertainty: list[str]
    safe_summary: str
    created_from_role_loop_id: str | None = None
    safety_metadata: dict[str, Any] = Field(default_factory=dict)
    execution_effect: str = "proposal_only"
    can_execute: bool = False
    creates_delegated_lane: bool = False

    @model_validator(mode="after")
    def _keep_non_executing(self) -> ProposalArtifact:
        if self.can_execute:
            raise ValueError("Proposal artifacts cannot execute.")
        if self.execution_effect not in {"proposal_only", "none"}:
            raise ValueError("Proposal artifacts must remain proposal-only.")
        if self.creates_delegated_lane:
            raise ValueError("Proposal artifacts cannot create delegated lanes in this pack.")
        return self

    @property
    def proposal_hash(self) -> str:
        return stable_hash(self.safe_payload())

    def safe_payload(self) -> dict[str, Any]:
        return sanitize_metadata(
            {
                "proposal_id": self.proposal_id,
                "source_role_id": self.source_role_id,
                "mission_id": self.mission_id,
                "objective_summary": self.objective_summary,
                "artifact_kind": self.artifact_kind.value,
                "action_level_candidate": self.action_level_candidate.value,
                "authority_class": self.authority_class,
                "risk_class": self.risk_class,
                "budget_estimate": self.budget_estimate,
                "evidence_refs": self.evidence_refs,
                "receipt_refs": self.receipt_refs,
                "expected_outcome": self.expected_outcome,
                "rollback_posture": self.rollback_posture,
                "user_review_required": self.user_review_required,
                "uncertainty": self.uncertainty,
                "safe_summary": self.safe_summary,
                "created_from_role_loop_id": self.created_from_role_loop_id,
                "execution_effect": self.execution_effect,
                "can_execute": self.can_execute,
                "creates_delegated_lane": self.creates_delegated_lane,
            }
        )


class MissionPlanProposal(ProposalArtifact):
    pass


class StrategyProposal(ProposalArtifact):
    pass


class ResearchPlanProposal(ProposalArtifact):
    pass


class EvidenceGapProposal(ProposalArtifact):
    pass


class BrowserStepCandidate(ProposalArtifact):
    browser_action: str
    target_url_pattern: str
    submit: bool = False
    execute_now: bool = False

    @model_validator(mode="after")
    def _browser_is_candidate_only(self) -> BrowserStepCandidate:
        if self.submit or self.execute_now:
            raise ValueError("Browser candidates cannot submit or execute.")
        if self.artifact_kind is not ProposalArtifactKind.BROWSER_STEP_CANDIDATE:
            raise ValueError("BrowserStepCandidate requires browser_step_candidate artifact kind.")
        return self


class ApiRequestCandidate(ProposalArtifact):
    method: str
    endpoint_template: str
    request_body_schema: dict[str, Any] = Field(default_factory=dict)
    execute_now: bool = False

    @model_validator(mode="after")
    def _api_is_plan_only(self) -> ApiRequestCandidate:
        if self.execute_now:
            raise ValueError("API candidates are request plans only.")
        if self.artifact_kind is not ProposalArtifactKind.API_REQUEST_CANDIDATE:
            raise ValueError("ApiRequestCandidate requires api_request_candidate artifact kind.")
        return self


class ChannelDraftCandidate(ProposalArtifact):
    channel: str
    draft_subject: str
    draft_body_hash: str
    send_now: bool = False

    @model_validator(mode="after")
    def _channel_is_draft_only(self) -> ChannelDraftCandidate:
        if self.send_now:
            raise ValueError("Channel candidates are drafts only.")
        if self.artifact_kind is not ProposalArtifactKind.CHANNEL_DRAFT_CANDIDATE:
            raise ValueError("ChannelDraftCandidate requires channel_draft_candidate artifact kind.")
        return self


class FileOperationCandidate(ProposalArtifact):
    path_pattern: str
    operation: str
    would_mutate: bool = False

    @model_validator(mode="after")
    def _file_candidate_is_non_mutating(self) -> FileOperationCandidate:
        if self.would_mutate:
            raise ValueError("File candidates cannot mutate without a future delegated lane.")
        if self.artifact_kind is not ProposalArtifactKind.FILE_OPERATION_CANDIDATE:
            raise ValueError("FileOperationCandidate requires file_operation_candidate artifact kind.")
        return self


class CodePatchPlanProposal(ProposalArtifact):
    target_files: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=list)
    file_mutation: bool = False

    @model_validator(mode="after")
    def _code_patch_is_plan_only(self) -> CodePatchPlanProposal:
        if self.file_mutation:
            raise ValueError("Code patch plans cannot mutate files.")
        if self.artifact_kind is not ProposalArtifactKind.CODE_PATCH_PLAN:
            raise ValueError("CodePatchPlanProposal requires code_patch_plan artifact kind.")
        return self


class RiskMitigationProposal(ProposalArtifact):
    mitigation_steps: list[str] = Field(default_factory=list)


class SelfImprovementProposal(ProposalArtifact):
    improvement_area: str
    mutates_runtime: bool = False
    mutates_policy: bool = False
    mutates_authority: bool = False
    mutates_provider: bool = False
    mutates_organs: bool = False

    @model_validator(mode="after")
    def _self_improvement_is_proposal_only(self) -> SelfImprovementProposal:
        if (
            self.mutates_runtime
            or self.mutates_policy
            or self.mutates_authority
            or self.mutates_provider
            or self.mutates_organs
        ):
            raise ValueError("Self-improvement may propose only; it cannot mutate system authority or runtime.")
        if self.artifact_kind is not ProposalArtifactKind.SELF_IMPROVEMENT:
            raise ValueError("SelfImprovementProposal requires self_improvement artifact kind.")
        return self


ProposalLike: TypeAlias = (
    ProposalArtifact
    | MissionPlanProposal
    | StrategyProposal
    | ResearchPlanProposal
    | EvidenceGapProposal
    | BrowserStepCandidate
    | ApiRequestCandidate
    | ChannelDraftCandidate
    | FileOperationCandidate
    | CodePatchPlanProposal
    | RiskMitigationProposal
    | SelfImprovementProposal
)


class ProposalArtifactValidator:
    @classmethod
    def validate(
        cls,
        proposal: ProposalArtifact,
        *,
        available_evidence_refs: set[str] | list[str] | tuple[str, ...],
    ) -> ProposalValidationResult:
        proposal_hash = proposal.proposal_hash
        reasons: list[str] = []
        available = set(available_evidence_refs)
        invented_refs = sorted(set(proposal.evidence_refs) - available)

        if contains_forbidden_proposal_payload(proposal.model_dump(mode="json")):
            reasons.append("forbidden_executable_payload")
        if invented_refs:
            reasons.append("invented_evidence_ref")

        if reasons:
            return ProposalValidationResult(
                valid=False,
                status=ProposalArtifactStatus.REJECTED,
                reasons=reasons,
                proposal_hash=proposal_hash,
                invented_evidence_refs=invented_refs,
            )

        if not proposal.evidence_refs and proposal.action_level_candidate is not DelegatedActionLevel.L0:
            return ProposalValidationResult(
                valid=False,
                status=ProposalArtifactStatus.NEEDS_MORE_EVIDENCE,
                reasons=["missing_evidence"],
                proposal_hash=proposal_hash,
                missing_evidence=True,
            )

        return ProposalValidationResult(
            valid=True,
            status=ProposalArtifactStatus.VALIDATED,
            proposal_hash=proposal_hash,
        )


class ProposalReceipt(SentinelModel):
    proposal_id: str
    artifact_kind: ProposalArtifactKind
    source_role_id: str
    input_hash: str
    proposal_hash: str
    evidence_refs: list[str] = Field(default_factory=list)
    budget_estimate: dict[str, Any] = Field(default_factory=dict)
    validation_status: str
    verifier_status: str
    risk_class: str
    action_level_candidate: DelegatedActionLevel
    user_review_required: bool
    receipt_hash: str

    @classmethod
    def build(
        cls,
        *,
        proposal: ProposalArtifact,
        input_hash: str,
        validation_status: str,
        verifier_status: str,
    ) -> ProposalReceipt:
        payload = sanitize_metadata(
            {
                "proposal_id": proposal.proposal_id,
                "artifact_kind": proposal.artifact_kind.value,
                "source_role_id": proposal.source_role_id,
                "input_hash": input_hash,
                "proposal_hash": proposal.proposal_hash,
                "evidence_refs": proposal.evidence_refs,
                "budget_estimate": proposal.budget_estimate,
                "validation_status": validation_status,
                "verifier_status": verifier_status,
                "risk_class": proposal.risk_class,
                "action_level_candidate": proposal.action_level_candidate.value,
                "user_review_required": proposal.user_review_required,
            }
        )
        return cls(receipt_hash=stable_hash(payload), **payload)


def coerce_proposal_artifact(payload: dict[str, Any]) -> ProposalLike:
    kind_value = payload.get("artifact_kind")
    kind = ProposalArtifactKind(kind_value)
    model = _PROPOSAL_MODELS.get(kind, ProposalArtifact)
    return model.model_validate(payload)


def contains_forbidden_proposal_payload(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_PAYLOAD_KEYS and _truthy_payload(value):
                return True
            if contains_forbidden_proposal_payload(value):
                return True
        return False
    if isinstance(payload, list | tuple | set):
        return any(contains_forbidden_proposal_payload(value) for value in payload)
    if isinstance(payload, str):
        lowered = payload.lower()
        return any(marker in lowered for marker in _FORBIDDEN_PAYLOAD_TEXT)
    return False


def _truthy_payload(value: Any) -> bool:
    return value not in (None, False, "", [], {})


_PROPOSAL_MODELS: dict[ProposalArtifactKind, type[ProposalLike]] = {
    ProposalArtifactKind.MISSION_PLAN: MissionPlanProposal,
    ProposalArtifactKind.STRATEGY: StrategyProposal,
    ProposalArtifactKind.RESEARCH_PLAN: ResearchPlanProposal,
    ProposalArtifactKind.EVIDENCE_GAP: EvidenceGapProposal,
    ProposalArtifactKind.BROWSER_STEP_CANDIDATE: BrowserStepCandidate,
    ProposalArtifactKind.API_REQUEST_CANDIDATE: ApiRequestCandidate,
    ProposalArtifactKind.CHANNEL_DRAFT_CANDIDATE: ChannelDraftCandidate,
    ProposalArtifactKind.FILE_OPERATION_CANDIDATE: FileOperationCandidate,
    ProposalArtifactKind.CODE_PATCH_PLAN: CodePatchPlanProposal,
    ProposalArtifactKind.RISK_MITIGATION: RiskMitigationProposal,
    ProposalArtifactKind.SELF_IMPROVEMENT: SelfImprovementProposal,
    ProposalArtifactKind.FINAL_PACKET: ProposalArtifact,
}

_FORBIDDEN_PAYLOAD_KEYS = {
    "action_execution",
    "authority_expansion",
    "authority_grant",
    "backend_override",
    "browser_submit",
    "call_tool",
    "credential_access",
    "direct_action",
    "execute_now",
    "hidden_action_payload",
    "model_override",
    "organ_execution",
    "payment",
    "provider_override",
    "raw_prompt",
    "raw_provider_response",
    "raw_response",
    "reasoning",
    "reasoning_content",
    "reasoning_details",
    "send_email",
    "shell",
    "spend",
    "terminal",
    "thinking",
    "thinking_blocks",
    "thought_signature",
    "tool_calls",
    "trade",
}

_FORBIDDEN_PAYLOAD_TEXT = {
    "browser_submit",
    "credential access",
    "execute_now",
    "hidden_action_payload",
    "organ_execution",
    "payment",
    "provider override",
    "raw_response",
    "reasoning_details",
    "send_email",
    "shell/process",
    "tool_calls",
}
