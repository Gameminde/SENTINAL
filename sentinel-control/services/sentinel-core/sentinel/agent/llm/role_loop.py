from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import Field
from pydantic import ValidationError

from sentinel.agent.llm.evidence_verifier import EvidenceBindingVerdict, EvidenceVerifier
from sentinel.agent.llm.memory_bridge import (
    LivingMissionMemorySnapshot,
    MemoryBridgeInput,
    MemoryBridgeResult,
    RoleLoopMemoryBridge,
    SafeFeedbackSignal,
)
from sentinel.agent.llm.proposals import ProposalArtifactValidator, coerce_proposal_artifact
from sentinel.agent.model_contract import UserModelContract
from sentinel.agent.model_execution import ModelExecutionBudgetLedger, ModelExecutionBudgetPolicy
from sentinel.agent.model_execution.models import ModelExecutionOutcomeClass, ProviderModelResponse, RealModelRequest
from sentinel.agent.model_execution.redaction import sanitize_metadata, stable_hash, text_hash
from sentinel.shared.models import SentinelModel, new_id


class LLMRoleId(StrEnum):
    VISIONARY = "visionary"
    STRATEGIST = "strategist"
    RESEARCHER = "researcher"
    PLANNER = "planner"
    CRITIC = "critic"
    VERIFIER = "verifier"
    RISK_REVIEWER = "risk_reviewer"
    OPERATOR_PLANNER = "operator_planner"
    CODER_ADVISOR = "coder_advisor"
    SYNTHESIZER = "synthesizer"


class RoleLoopStatus(StrEnum):
    COMPLETED = "completed"
    ROLE_REJECTED = "role_rejected"
    ROLE_BUDGET_EXHAUSTED = "role_budget_exhausted"
    LOOP_BUDGET_EXHAUSTED = "loop_budget_exhausted"


class LLMRoleContract(SentinelModel):
    role_id: LLMRoleId
    purpose: str
    cognition_freedom_level: str
    delegated_operation_eligibility: str
    allowed_outputs: list[str] = Field(default_factory=list)
    forbidden_outputs: list[str] = Field(default_factory=list)
    proposal_schema: dict[str, Any] = Field(default_factory=dict)
    delegated_action_schema: dict[str, Any] = Field(default_factory=dict)
    evidence_requirements: list[str] = Field(default_factory=list)
    budget_policy: dict[str, Any] = Field(default_factory=dict)
    receipt_fields: list[str] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)
    failure_modes: list[str] = Field(default_factory=list)
    downgrade_behavior: str = ""
    authority_effect: str = "none"
    execution_effect: str = "none"
    provider_id: str | None = None
    backend_id: str | None = None
    model_id: str | None = None


class LLMRoleInputFrame(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("role_frame"))
    mission_id: str
    role_id: LLMRoleId
    selected_provider_id: str
    selected_backend_id: str
    selected_model: str
    mission_goal: str
    available_evidence_refs: list[str] = Field(default_factory=list)
    mission_memory_refs: list[str] = Field(default_factory=list)
    prior_role_receipt_ids: list[str] = Field(default_factory=list)
    reasoning_lenses: list[str] = Field(
        default_factory=lambda: ["mathematical", "physical", "electronic", "philosophical"]
    )
    prompt_hash: str


class LLMRoleOutput(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("role_output"))
    role_id: LLMRoleId
    provider_id: str
    backend_id: str
    model_id: str
    content: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    proposal_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    validation_status: str = "accepted"

    def safe_hash_payload(self) -> dict[str, Any]:
        return sanitize_metadata(
            {
                "role_id": self.role_id.value,
                "provider_id": self.provider_id,
                "backend_id": self.backend_id,
                "model_id": self.model_id,
                "content": self.content,
                "evidence_refs": self.evidence_refs,
                "proposal_artifacts": self.proposal_artifacts,
                "action_candidates": self.action_candidates,
                "uncertainty": self.uncertainty,
                "objections": self.objections,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "validation_status": self.validation_status,
            }
        )


class RoleLoopBudgetSummary(SentinelModel):
    compliant: bool = True
    decision: str = "within_budget"
    used_input_tokens: int = Field(default=0, ge=0)
    used_output_tokens: int = Field(default=0, ge=0)
    used_reasoning_tokens: int = Field(default=0, ge=0)
    used_total_tokens: int = Field(default=0, ge=0)
    used_retry_attempts: int = Field(default=0, ge=0)
    used_provider_time_seconds: float = Field(default=0.0, ge=0.0)
    entry_hashes: list[str] = Field(default_factory=list)

    @classmethod
    def from_ledger_summary(cls, summary: dict[str, Any] | None) -> RoleLoopBudgetSummary:
        summary = sanitize_metadata(summary or {})
        return cls(
            compliant=bool(summary.get("compliant", True)),
            decision=str(summary.get("decision", "within_budget")),
            used_input_tokens=_safe_int(summary.get("used_input_tokens")),
            used_output_tokens=_safe_int(summary.get("used_output_tokens")),
            used_reasoning_tokens=_safe_int(summary.get("used_reasoning_tokens")),
            used_total_tokens=_safe_int(summary.get("used_total_tokens")),
            used_retry_attempts=_safe_int(summary.get("used_retry_attempts")),
            used_provider_time_seconds=_safe_float(summary.get("used_provider_time_seconds")),
            entry_hashes=[str(item) for item in summary.get("entry_hashes", []) if item],
        )


class RoleLoopReceipt(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("role_receipt"))
    role_id: LLMRoleId
    provider_id: str
    backend_id: str
    model_id: str
    prompt_hash: str
    output_hash: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    budget_summary: RoleLoopBudgetSummary = Field(default_factory=RoleLoopBudgetSummary)
    validation_status: str
    loopback_reason: str | None = None
    receipt_hash: str

    @classmethod
    def build(
        cls,
        *,
        role_id: LLMRoleId,
        provider_id: str,
        backend_id: str,
        model_id: str,
        prompt_hash: str,
        output_hash: str | None,
        evidence_refs: list[str],
        budget_summary: RoleLoopBudgetSummary,
        validation_status: str,
        loopback_reason: str | None = None,
    ) -> RoleLoopReceipt:
        payload = sanitize_metadata(
            {
                "role_id": role_id.value,
                "provider_id": provider_id,
                "backend_id": backend_id,
                "model_id": model_id,
                "prompt_hash": prompt_hash,
                "output_hash": output_hash,
                "evidence_refs": evidence_refs,
                "budget_summary": budget_summary.model_dump(mode="json"),
                "validation_status": validation_status,
                "loopback_reason": loopback_reason,
            }
        )
        return cls(receipt_hash=stable_hash(payload), **payload)


class LLMRoleLoopPlan(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("role_loop_plan"))
    mission_id: str
    mission_goal: str
    user_model_contract: UserModelContract
    available_evidence_refs: list[str] = Field(default_factory=list)
    mission_memory_refs: list[str] = Field(default_factory=list)
    role_sequence: list[LLMRoleId] = Field(
        default_factory=lambda: [
            LLMRoleId.VISIONARY,
            LLMRoleId.STRATEGIST,
            LLMRoleId.RESEARCHER,
            LLMRoleId.PLANNER,
            LLMRoleId.CRITIC,
            LLMRoleId.VERIFIER,
            LLMRoleId.RISK_REVIEWER,
            LLMRoleId.SYNTHESIZER,
        ]
    )
    per_role_input_token_estimate: int = Field(default=120, ge=0)
    per_role_output_token_estimate: int = Field(default=80, ge=0)
    loopback_budget: int = Field(default=1, ge=0)
    raw_prompt_in_memory_only: str | None = Field(default=None, exclude=True, repr=False)


class LLMRoleLoopResult(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("role_loop_result"))
    mission_id: str
    status: RoleLoopStatus
    role_outputs: list[LLMRoleOutput] = Field(default_factory=list)
    receipts: list[RoleLoopReceipt] = Field(default_factory=list)
    budget_summary: RoleLoopBudgetSummary = Field(default_factory=RoleLoopBudgetSummary)
    final_packet: dict[str, Any] = Field(default_factory=dict)
    proposal_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)
    memory_bridge_result: MemoryBridgeResult | None = None
    living_memory_snapshot: LivingMissionMemorySnapshot | None = None
    feedback_signals: list[SafeFeedbackSignal] = Field(default_factory=list)
    memory_entry_refs: list[str] = Field(default_factory=list)
    blocked_role_id: LLMRoleId | None = None
    blocked_reason: str | None = None
    loopback_count: int = 0
    authority_effect: str = "none"
    execution_effect: str = "none"
    can_grant_authority: bool = False
    can_approve_execution: bool = False
    can_create_delegated_lane: bool = False
    can_override_provider_model: bool = False


class LLMRoleModelClient(Protocol):
    def complete_role(self, frame: LLMRoleInputFrame) -> LLMRoleOutput:
        ...


class LLMRoleLoopOrchestrator:
    def __init__(
        self,
        *,
        role_model_client: LLMRoleModelClient,
        role_contracts: dict[LLMRoleId, LLMRoleContract] | None = None,
        budget_ledger: ModelExecutionBudgetLedger | None = None,
        memory_bridge: RoleLoopMemoryBridge | None = None,
    ) -> None:
        self._role_model_client = role_model_client
        self._role_contracts = role_contracts or build_default_llm_role_contracts()
        self._budget_ledger = budget_ledger
        self._memory_bridge = memory_bridge

    def run(self, plan: LLMRoleLoopPlan) -> LLMRoleLoopResult:
        ledger = self._budget_ledger or ModelExecutionBudgetLedger(mission_id=plan.mission_id)
        role_outputs: list[LLMRoleOutput] = []
        receipts: list[RoleLoopReceipt] = []
        proposal_artifacts: list[dict[str, Any]] = []
        action_candidates: list[dict[str, Any]] = []
        loopback_count = 0
        selected_provider = plan.user_model_contract.selected_provider_id
        selected_backend = plan.user_model_contract.selected_backend_id
        selected_model = plan.user_model_contract.selected_model

        for role_id in plan.role_sequence:
            contract = self._role_contracts.get(role_id) or _default_role_contract(role_id)
            override_reason = _contract_override_reason(contract, plan.user_model_contract)
            prompt_hash = self._role_prompt_hash(plan=plan, role_id=role_id)
            if override_reason is not None:
                budget_summary = RoleLoopBudgetSummary.from_ledger_summary(ledger.safe_summary())
                receipts.append(
                    RoleLoopReceipt.build(
                        role_id=role_id,
                        provider_id=contract.provider_id or selected_provider,
                        backend_id=contract.backend_id or selected_backend,
                        model_id=contract.model_id or selected_model,
                        prompt_hash=prompt_hash,
                        output_hash=None,
                        evidence_refs=[],
                        budget_summary=budget_summary,
                        validation_status=override_reason,
                    )
                )
                return _result(
                    plan=plan,
                    status=RoleLoopStatus.ROLE_REJECTED,
                    role_outputs=role_outputs,
                    receipts=receipts,
                    budget_summary=budget_summary,
                    proposal_artifacts=proposal_artifacts,
                    action_candidates=action_candidates,
                    blocked_role_id=role_id,
                    blocked_reason=override_reason,
                    loopback_count=loopback_count,
                    memory_bridge=self._memory_bridge,
                )

            request = self._role_budget_request(plan=plan, role_id=role_id, prompt_hash=prompt_hash)
            budget_decision = ledger.preflight(request)
            if not budget_decision.allowed:
                summary = ledger.record_rejection(request=request, decision=budget_decision)
                budget_summary = RoleLoopBudgetSummary.from_ledger_summary(summary)
                status = (
                    RoleLoopStatus.LOOP_BUDGET_EXHAUSTED
                    if budget_decision.decision.startswith("mission_")
                    else RoleLoopStatus.ROLE_BUDGET_EXHAUSTED
                )
                receipts.append(
                    RoleLoopReceipt.build(
                        role_id=role_id,
                        provider_id=selected_provider,
                        backend_id=selected_backend,
                        model_id=selected_model,
                        prompt_hash=prompt_hash,
                        output_hash=None,
                        evidence_refs=[],
                        budget_summary=budget_summary,
                        validation_status=budget_decision.decision,
                    )
                )
                return _result(
                    plan=plan,
                    status=status,
                    role_outputs=role_outputs,
                    receipts=receipts,
                    budget_summary=budget_summary,
                    proposal_artifacts=proposal_artifacts,
                    action_candidates=action_candidates,
                    blocked_role_id=role_id,
                    blocked_reason=budget_decision.decision,
                    loopback_count=loopback_count,
                    memory_bridge=self._memory_bridge,
                )

            frame = LLMRoleInputFrame(
                mission_id=plan.mission_id,
                role_id=role_id,
                selected_provider_id=selected_provider,
                selected_backend_id=selected_backend,
                selected_model=selected_model,
                mission_goal=plan.mission_goal,
                available_evidence_refs=list(plan.available_evidence_refs),
                mission_memory_refs=list(plan.mission_memory_refs),
                prior_role_receipt_ids=[receipt.id for receipt in receipts],
                prompt_hash=prompt_hash,
            )
            output = self._role_model_client.complete_role(frame)
            validation_status = _validate_role_output(output=output, plan=plan, role_id=role_id)
            normalized_proposals: list[dict[str, Any]] = []
            normalized_candidates: list[dict[str, Any]] = []
            if validation_status == "accepted":
                structured_result = _normalize_structured_artifacts(
                    output=output,
                    available_evidence_refs=plan.available_evidence_refs,
                )
                if structured_result.validation_status != "accepted":
                    validation_status = structured_result.validation_status
                normalized_proposals = structured_result.proposal_artifacts
                normalized_candidates = structured_result.action_candidates
            output_hash = stable_hash(output.safe_hash_payload())
            response = ProviderModelResponse(
                provider_id=selected_provider,
                model_id=selected_model,
                content={"role_id": role_id.value, "output_hash": output_hash},
                input_tokens=output.input_tokens,
                output_tokens=output.output_tokens,
            )
            summary = ledger.record_response(
                request=request,
                response=response,
                outcome_class=ModelExecutionOutcomeClass.SUCCESS_VALIDATED
                if validation_status == "accepted"
                else ModelExecutionOutcomeClass.AUTHORITY_EXPANSION_REJECTED,
                attempts=1,
                provider_time_seconds=0.0,
            )
            budget_summary = RoleLoopBudgetSummary.from_ledger_summary(summary)
            loopback_reason = _loopback_reason(output)
            if loopback_reason and loopback_count < plan.loopback_budget:
                loopback_count += 1
            receipts.append(
                RoleLoopReceipt.build(
                    role_id=role_id,
                    provider_id=selected_provider,
                    backend_id=selected_backend,
                    model_id=selected_model,
                    prompt_hash=prompt_hash,
                    output_hash=output_hash,
                    evidence_refs=list(output.evidence_refs),
                    budget_summary=budget_summary,
                    validation_status=validation_status,
                    loopback_reason=loopback_reason,
                )
            )

            if validation_status != "accepted":
                return _result(
                    plan=plan,
                    status=RoleLoopStatus.ROLE_REJECTED,
                    role_outputs=role_outputs,
                    receipts=receipts,
                    budget_summary=budget_summary,
                    proposal_artifacts=proposal_artifacts,
                    action_candidates=action_candidates,
                    blocked_role_id=role_id,
                    blocked_reason=validation_status,
                    loopback_count=loopback_count,
                    memory_bridge=self._memory_bridge,
                )

            accepted_output = output.model_copy(update={"validation_status": validation_status})
            role_outputs.append(accepted_output)
            proposal_artifacts.extend(sanitize_metadata(normalized_proposals))
            action_candidates.extend(sanitize_metadata(normalized_candidates))

        return _result(
            plan=plan,
            status=RoleLoopStatus.COMPLETED,
            role_outputs=role_outputs,
            receipts=receipts,
            budget_summary=RoleLoopBudgetSummary.from_ledger_summary(ledger.safe_summary()),
            proposal_artifacts=proposal_artifacts,
            action_candidates=action_candidates,
            loopback_count=loopback_count,
            memory_bridge=self._memory_bridge,
        )

    def _role_prompt_hash(self, *, plan: LLMRoleLoopPlan, role_id: LLMRoleId) -> str:
        prompt_seed = "|".join(
            [
                plan.mission_id,
                role_id.value,
                plan.mission_goal,
                ",".join(plan.available_evidence_refs),
                text_hash(plan.raw_prompt_in_memory_only or ""),
            ]
        )
        return text_hash(prompt_seed)

    def _role_budget_request(self, *, plan: LLMRoleLoopPlan, role_id: LLMRoleId, prompt_hash: str) -> RealModelRequest:
        contract = plan.user_model_contract
        budget_policy = ModelExecutionBudgetPolicy(
            max_input_tokens=contract.context_budget_policy.max_decision_frame_tokens,
            max_output_tokens=contract.context_budget_policy.reserve_output_tokens,
            max_total_tokens=contract.context_budget_policy.max_decision_frame_tokens
            + contract.context_budget_policy.reserve_output_tokens,
            max_retry_attempts_per_action=max(1, contract.quality_expectation.retry_budget + 1),
            max_provider_time_seconds_per_action=7.0,
            max_total_estimated_usd=contract.cost_profile.project(
                input_tokens=plan.per_role_input_token_estimate,
                output_tokens=plan.per_role_output_token_estimate,
            ).total_estimated_usd,
        )
        timeout_policy = {
            "connect_timeout_seconds": 2.0,
            "read_timeout_seconds": 5.0,
            "total_timeout_seconds": 7.0,
        }
        retry_policy = {"max_attempts": max(1, contract.quality_expectation.retry_budget + 1)}
        metadata = sanitize_metadata(
            {
                "mission_id": plan.mission_id,
                "action_id": f"role_loop:{role_id.value}",
                "role_id": role_id.value,
                "timeout_policy": timeout_policy,
                "retry_policy": retry_policy,
                "budget_policy": budget_policy.model_dump(mode="json"),
            }
        )
        hash_payload = sanitize_metadata(
            {
                "provider_id": contract.selected_provider_id,
                "backend_id": contract.selected_backend_id,
                "model_id": contract.selected_model,
                "role_id": role_id.value,
                "prompt_hash": prompt_hash,
                "estimated_input_tokens": plan.per_role_input_token_estimate,
                "estimated_output_tokens": plan.per_role_output_token_estimate,
                "metadata": metadata,
            }
        )
        return RealModelRequest(
            provider_id=contract.selected_provider_id,
            model_id=contract.selected_model,
            backend_id=contract.selected_backend_id,
            backend=contract.selected_backend_id,
            runtime="role_loop",
            prompt_hash=prompt_hash,
            frame_hash=stable_hash({"mission_id": plan.mission_id, "role_id": role_id.value}),
            user_model_contract_id=contract.id,
            estimated_input_tokens=plan.per_role_input_token_estimate,
            estimated_output_tokens=plan.per_role_output_token_estimate,
            prompt_text_in_memory_only=plan.raw_prompt_in_memory_only,
            request_metadata=metadata,
            timeout_policy_id="role_loop_timeout",
            retry_policy_id="role_loop_retry",
            budget_policy_id=budget_policy.id,
            request_hash=stable_hash(hash_payload),
        )


def build_default_llm_role_contracts() -> dict[LLMRoleId, LLMRoleContract]:
    return {role_id: _default_role_contract(role_id) for role_id in LLMRoleId}


def _default_role_contract(role_id: LLMRoleId) -> LLMRoleContract:
    return LLMRoleContract(
        role_id=role_id,
        purpose=_ROLE_PURPOSES[role_id],
        cognition_freedom_level=_ROLE_FREEDOM[role_id],
        delegated_operation_eligibility="none_this_pack"
        if role_id
        not in {
            LLMRoleId.OPERATOR_PLANNER,
            LLMRoleId.CODER_ADVISOR,
            LLMRoleId.RESEARCHER,
            LLMRoleId.PLANNER,
        }
        else "proposal_only",
        allowed_outputs=["safe_cognition", "proposal_artifacts", "evidence_refs", "uncertainty"],
        forbidden_outputs=[
            "root_authority_expansion",
            "provider_model_override",
            "direct_organ_invocation",
            "direct_tool_call",
            "raw_credential_request",
            "hidden_execution_payload",
        ],
        proposal_schema={"required": ["authority_class", "risk_class", "budget_estimate", "evidence_refs"]},
        delegated_action_schema={"effect": "proposal_only"},
        evidence_requirements=["bind_to_available_evidence_refs_or_mark_uncertainty"],
        budget_policy={"per_role_budget": "existing_model_execution_budget"},
        receipt_fields=["role_id", "prompt_hash", "output_hash", "evidence_refs", "budget_used"],
        validation_rules=["no_authority_effect", "no_execution_effect", "same_user_selected_model"],
        failure_modes=["authority_drift", "budget_exhaustion", "invented_evidence", "hidden_action_payload"],
        downgrade_behavior="block_or_return_to_prior_role",
    )


_ROLE_PURPOSES = {
    LLMRoleId.VISIONARY: "Generate bold possibilities and opportunity hypotheses.",
    LLMRoleId.STRATEGIST: "Choose coherent route and tradeoffs.",
    LLMRoleId.RESEARCHER: "Identify evidence gaps and research needs.",
    LLMRoleId.PLANNER: "Convert strategy into proposal artifacts.",
    LLMRoleId.CRITIC: "Attack weak reasoning and surface objections.",
    LLMRoleId.VERIFIER: "Bind claims to evidence and uncertainty.",
    LLMRoleId.RISK_REVIEWER: "Classify authority, budget, and operational risk.",
    LLMRoleId.OPERATOR_PLANNER: "Translate plans into proposal-only organ/action candidates.",
    LLMRoleId.CODER_ADVISOR: "Plan code and project changes without mutation.",
    LLMRoleId.SYNTHESIZER: "Merge role outputs into final safe decision packet.",
}

_ROLE_FREEDOM = {
    LLMRoleId.VISIONARY: "maximum",
    LLMRoleId.STRATEGIST: "high",
    LLMRoleId.RESEARCHER: "high",
    LLMRoleId.PLANNER: "medium_high",
    LLMRoleId.CRITIC: "high",
    LLMRoleId.VERIFIER: "medium_high",
    LLMRoleId.RISK_REVIEWER: "medium",
    LLMRoleId.OPERATOR_PLANNER: "medium",
    LLMRoleId.CODER_ADVISOR: "high",
    LLMRoleId.SYNTHESIZER: "medium_high",
}


def _contract_override_reason(contract: LLMRoleContract, user_model: UserModelContract) -> str | None:
    if contract.provider_id is not None and contract.provider_id != user_model.selected_provider_id:
        return "role_provider_override_rejected"
    if contract.backend_id is not None and contract.backend_id != user_model.selected_backend_id:
        return "role_backend_override_rejected"
    if contract.model_id is not None and contract.model_id != user_model.selected_model:
        return "role_model_override_rejected"
    return None


def _validate_role_output(*, output: LLMRoleOutput, plan: LLMRoleLoopPlan, role_id: LLMRoleId) -> str:
    contract = plan.user_model_contract
    if output.provider_id != contract.selected_provider_id:
        return "role_provider_override_rejected"
    if output.backend_id != contract.selected_backend_id:
        return "role_backend_override_rejected"
    if output.model_id != contract.selected_model:
        return "role_model_override_rejected"
    if _contains_forbidden_intent(output.safe_hash_payload()):
        return "forbidden_model_output_intent"
    if role_id in {LLMRoleId.CRITIC, LLMRoleId.VERIFIER} and _contains_execution_approval(output.safe_hash_payload()):
        return "role_cannot_approve_execution"
    if role_id is LLMRoleId.OPERATOR_PLANNER and any(
        candidate.get("execution_effect") not in {None, "proposal_only", "none"}
        or candidate.get("creates_delegated_lane") is True
        for candidate in output.action_candidates
    ):
        return "operator_planner_must_remain_proposal_only"
    if role_id is LLMRoleId.CODER_ADVISOR and bool(output.content.get("file_mutation")):
        return "coder_advisor_cannot_mutate_files"
    if set(output.evidence_refs) - set(plan.available_evidence_refs):
        return "invented_evidence_refs"
    return "accepted"


class _StructuredArtifactResult(SentinelModel):
    validation_status: str = "accepted"
    proposal_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    action_candidates: list[dict[str, Any]] = Field(default_factory=list)


def _normalize_structured_artifacts(
    *,
    output: LLMRoleOutput,
    available_evidence_refs: list[str],
) -> _StructuredArtifactResult:
    proposal_artifacts: list[dict[str, Any]] = []
    action_candidates: list[dict[str, Any]] = []
    for payload in output.proposal_artifacts:
        normalized, validation_status = _normalize_one_artifact(
            payload=payload,
            available_evidence_refs=available_evidence_refs,
        )
        if validation_status != "accepted":
            return _StructuredArtifactResult(validation_status=validation_status)
        proposal_artifacts.append(normalized)
    for payload in output.action_candidates:
        normalized, validation_status = _normalize_one_artifact(
            payload=payload,
            available_evidence_refs=available_evidence_refs,
        )
        if validation_status != "accepted":
            return _StructuredArtifactResult(validation_status=validation_status)
        action_candidates.append(normalized)
    return _StructuredArtifactResult(
        proposal_artifacts=proposal_artifacts,
        action_candidates=action_candidates,
    )


def _normalize_one_artifact(
    *,
    payload: dict[str, Any],
    available_evidence_refs: list[str],
) -> tuple[dict[str, Any], str]:
    if "artifact_kind" not in payload:
        return sanitize_metadata(payload), "accepted"
    try:
        artifact = coerce_proposal_artifact(payload)
    except (ValueError, ValidationError):
        return {}, "invalid_proposal_artifact"
    validation = ProposalArtifactValidator.validate(
        artifact,
        available_evidence_refs=set(available_evidence_refs),
    )
    if not validation.valid:
        if "forbidden_executable_payload" in validation.reasons:
            return {}, "forbidden_model_output_intent"
        if "invented_evidence_ref" in validation.reasons:
            return {}, "invented_evidence_refs"
        if validation.missing_evidence:
            return {}, "proposal_missing_evidence"
        return {}, "invalid_proposal_artifact"
    return artifact.model_dump(mode="json"), "accepted"


_FORBIDDEN_INTENT_KEYS = {
    "tool_calls",
    "organ_execution",
    "execute_action",
    "action_execution",
    "authority_grant",
    "root_authority",
    "provider_override",
    "backend_override",
    "model_override",
    "credential_access",
    "credential_request",
    "browser_submit",
    "browser_login",
    "browser_upload",
    "browser_download",
    "send",
    "spend",
    "payment",
    "trading",
    "shell",
    "desktop_host_control",
    "hidden_action_payload",
    "raw_prompt",
    "raw_provider_response",
    "raw_response",
    "reasoning",
    "reasoning_content",
    "reasoning_details",
    "thinking",
    "thinking_blocks",
    "thought",
    "thought_signature",
}

_FORBIDDEN_TEXT = {
    "tool_call",
    "organ_execution",
    "authority_grant",
    "credential_access",
    "browser_submit",
    "browser_login",
    "browser_upload",
    "browser_download",
    "payment",
    "trading",
    "desktop host control",
}


def _contains_forbidden_intent(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).lower()
            if normalized in _FORBIDDEN_INTENT_KEYS and _truthy_intent_value(value):
                return True
            if _contains_forbidden_intent(value):
                return True
        return False
    if isinstance(payload, list | tuple | set):
        return any(_contains_forbidden_intent(item) for item in payload)
    if isinstance(payload, str):
        lowered = payload.lower()
        return any(item in lowered for item in _FORBIDDEN_TEXT)
    return False


def _truthy_intent_value(value: Any) -> bool:
    return value not in (None, False, "", [], {})


def _contains_execution_approval(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = str(key).lower()
            if normalized in {"approve_execution", "approved_execution", "execution_approved"} and bool(value):
                return True
            if _contains_execution_approval(value):
                return True
        return False
    if isinstance(payload, list | tuple | set):
        return any(_contains_execution_approval(item) for item in payload)
    return False


def _loopback_reason(output: LLMRoleOutput) -> str | None:
    if output.content.get("blocking_weakness") is True:
        return "critic_blocking_weakness"
    if output.content.get("authority_mismatch") is True:
        return "risk_authority_mismatch"
    if output.content.get("missing_evidence") is True:
        return "verifier_missing_evidence"
    return None


def _result(
    *,
    plan: LLMRoleLoopPlan,
    status: RoleLoopStatus,
    role_outputs: list[LLMRoleOutput],
    receipts: list[RoleLoopReceipt],
    budget_summary: RoleLoopBudgetSummary,
    proposal_artifacts: list[dict[str, Any]],
    action_candidates: list[dict[str, Any]],
    blocked_role_id: LLMRoleId | None = None,
    blocked_reason: str | None = None,
    loopback_count: int = 0,
    memory_bridge: RoleLoopMemoryBridge | None = None,
) -> LLMRoleLoopResult:
    safe_proposal_artifacts = sanitize_metadata(proposal_artifacts)
    safe_action_candidates = sanitize_metadata(action_candidates)
    final_packet = _final_packet(
        role_outputs=role_outputs,
        proposal_artifacts=safe_proposal_artifacts,
        action_candidates=safe_action_candidates,
        available_evidence_refs=plan.available_evidence_refs,
    )
    memory_bridge_result = _build_memory_bridge_result(
        memory_bridge=memory_bridge,
        plan=plan,
        status=status,
        role_outputs=role_outputs,
        receipts=receipts,
        budget_summary=budget_summary,
        final_packet=final_packet,
        proposal_artifacts=safe_proposal_artifacts,
        action_candidates=safe_action_candidates,
        blocked_reason=blocked_reason,
    )
    return LLMRoleLoopResult(
        mission_id=plan.mission_id,
        status=status,
        role_outputs=role_outputs,
        receipts=receipts,
        budget_summary=budget_summary,
        final_packet=final_packet,
        proposal_artifacts=safe_proposal_artifacts,
        action_candidates=safe_action_candidates,
        memory_bridge_result=memory_bridge_result,
        living_memory_snapshot=memory_bridge_result.snapshot if memory_bridge_result is not None else None,
        feedback_signals=memory_bridge_result.feedback_signals if memory_bridge_result is not None else [],
        memory_entry_refs=[
            entry.memory_id for entry in memory_bridge_result.memory_entries
        ]
        if memory_bridge_result is not None
        else [],
        blocked_role_id=blocked_role_id,
        blocked_reason=blocked_reason,
        loopback_count=loopback_count,
    )


def _build_memory_bridge_result(
    *,
    memory_bridge: RoleLoopMemoryBridge | None,
    plan: LLMRoleLoopPlan,
    status: RoleLoopStatus,
    role_outputs: list[LLMRoleOutput],
    receipts: list[RoleLoopReceipt],
    budget_summary: RoleLoopBudgetSummary,
    final_packet: dict[str, Any],
    proposal_artifacts: list[dict[str, Any]],
    action_candidates: list[dict[str, Any]],
    blocked_reason: str | None,
) -> MemoryBridgeResult | None:
    if memory_bridge is None:
        return None
    bridge_input = _memory_bridge_input(
        plan=plan,
        status=status,
        role_outputs=role_outputs,
        receipts=receipts,
        budget_summary=budget_summary,
        final_packet=final_packet,
        proposal_artifacts=proposal_artifacts,
        action_candidates=action_candidates,
        blocked_reason=blocked_reason,
    )
    return memory_bridge.build(bridge_input)


def _memory_bridge_input(
    *,
    plan: LLMRoleLoopPlan,
    status: RoleLoopStatus,
    role_outputs: list[LLMRoleOutput],
    receipts: list[RoleLoopReceipt],
    budget_summary: RoleLoopBudgetSummary,
    final_packet: dict[str, Any],
    proposal_artifacts: list[dict[str, Any]],
    action_candidates: list[dict[str, Any]],
    blocked_reason: str | None,
) -> MemoryBridgeInput:
    structured_artifacts = [artifact for artifact in [*proposal_artifacts, *action_candidates] if isinstance(artifact, dict)]
    evidence_summary = final_packet.get("evidence_verification_summary", {})
    missing_evidence = _memory_missing_evidence(final_packet=final_packet, blocked_reason=blocked_reason)
    invented_refs = _memory_invented_refs(evidence_summary=evidence_summary, blocked_reason=blocked_reason)
    contradictions = _memory_contradictions(role_outputs=role_outputs, evidence_summary=evidence_summary)
    blocked_intents = _memory_blocked_intents(blocked_reason)
    memory_items: list[dict[str, Any]] = []
    if status is RoleLoopStatus.COMPLETED:
        memory_items.extend(_receipt_memory_items(plan=plan, receipts=receipts))
        memory_items.extend(_role_output_memory_items(plan=plan, role_outputs=role_outputs, receipts=receipts))
        memory_items.extend(_proposal_memory_items(plan=plan, structured_artifacts=structured_artifacts))

    return MemoryBridgeInput(
        mission_id=plan.mission_id,
        loop_id=plan.id,
        memory_items=memory_items,
        role_loop_receipts=[
            sanitize_metadata(receipt.model_dump(mode="json", exclude={"prompt_hash"}))
            for receipt in receipts
        ],
        proposal_receipts=_proposal_receipts(plan=plan, structured_artifacts=structured_artifacts),
        evidence_verification_results=[evidence_summary] if evidence_summary else [],
        final_packet=sanitize_metadata(final_packet),
        budget_summaries=[budget_summary.model_dump(mode="json")],
        risk_flags=[str(flag) for flag in final_packet.get("risk_flags", [])],
        unresolved_objections=[str(item) for item in final_packet.get("unresolved_objections", [])],
        missing_evidence=missing_evidence,
        invented_evidence_refs=invented_refs,
        contradictions=contradictions,
        blocked_intents=blocked_intents,
        user_review_required=_memory_user_review_required(structured_artifacts),
        self_improvement_candidates=_memory_self_improvement_candidates(structured_artifacts),
    )


def _receipt_memory_items(*, plan: LLMRoleLoopPlan, receipts: list[RoleLoopReceipt]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for receipt in receipts:
        items.append(
            {
                "mission_id": plan.mission_id,
                "source_class": "receipt",
                "source_id": receipt.id,
                "source_lineage_id": receipt.receipt_hash,
                "source_scope": plan.mission_id,
                "validity_scope": plan.mission_id,
                "claim_status": "OBSERVED",
                "confidence": 0.55,
                "variance": 0.35,
                "evidence_refs": list(receipt.evidence_refs),
                "receipt_refs": [receipt.id],
                "safe_summary": f"Observed role-loop receipt for {receipt.role_id.value}.",
            }
        )
    return items


def _role_output_memory_items(
    *,
    plan: LLMRoleLoopPlan,
    role_outputs: list[LLMRoleOutput],
    receipts: list[RoleLoopReceipt],
) -> list[dict[str, Any]]:
    receipt_by_role = {receipt.role_id: receipt.id for receipt in receipts}
    items: list[dict[str, Any]] = []
    for output in role_outputs:
        items.append(
            {
                "mission_id": plan.mission_id,
                "source_class": "role_output",
                "source_id": output.id,
                "source_lineage_id": f"role_output:{output.role_id.value}",
                "source_scope": plan.mission_id,
                "validity_scope": plan.mission_id,
                "claim_status": "SUPPORTED",
                "confidence": 0.45,
                "variance": 0.45,
                "evidence_refs": list(output.evidence_refs),
                "receipt_refs": [receipt_by_role[output.role_id]] if output.role_id in receipt_by_role else [],
                "uncertainty": list(output.uncertainty),
                "safe_summary": f"Role output witness for {output.role_id.value}; evidence remains independently verified.",
            }
        )
    return items


def _proposal_memory_items(*, plan: LLMRoleLoopPlan, structured_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for artifact in structured_artifacts:
        proposal_id = str(artifact.get("proposal_id") or artifact.get("candidate_id") or stable_hash(artifact)[:16])
        items.append(
            {
                "mission_id": plan.mission_id,
                "source_class": "proposal_artifact",
                "source_id": proposal_id,
                "source_lineage_id": f"proposal:{proposal_id}",
                "source_scope": plan.mission_id,
                "validity_scope": plan.mission_id,
                "claim_status": "CLAIMED",
                "confidence": 0.4,
                "variance": 0.5,
                "evidence_refs": [str(ref) for ref in artifact.get("evidence_refs", [])],
                "receipt_refs": [str(ref) for ref in artifact.get("receipt_refs", [])],
                "uncertainty": [str(item) for item in artifact.get("uncertainty", [])],
                "safe_summary": str(artifact.get("safe_summary") or artifact.get("objective_summary") or "Proposal artifact witness."),
            }
        )
    return items


def _proposal_receipts(*, plan: LLMRoleLoopPlan, structured_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for artifact in structured_artifacts:
        proposal_id = str(artifact.get("proposal_id") or artifact.get("candidate_id") or stable_hash(artifact)[:16])
        payload = sanitize_metadata(
            {
                "proposal_id": proposal_id,
                "mission_id": plan.mission_id,
                "artifact_kind": artifact.get("artifact_kind"),
                "source_role_id": artifact.get("source_role_id"),
                "proposal_hash": stable_hash(artifact),
                "evidence_refs": artifact.get("evidence_refs", []),
                "receipt_refs": artifact.get("receipt_refs", []),
                "budget_estimate": artifact.get("budget_estimate", {}),
                "risk_class": artifact.get("risk_class"),
                "action_level_candidate": artifact.get("action_level_candidate"),
                "user_review_required": bool(artifact.get("user_review_required", False)),
                "validation_status": "accepted",
            }
        )
        receipts.append(payload)
    return receipts


def _memory_missing_evidence(*, final_packet: dict[str, Any], blocked_reason: str | None) -> list[str]:
    missing = [str(item) for item in final_packet.get("missing_evidence", []) if item]
    if blocked_reason in {"proposal_missing_evidence", "verifier_missing_evidence"}:
        missing.append(blocked_reason)
    return _dedupe(missing)


def _memory_invented_refs(*, evidence_summary: dict[str, Any], blocked_reason: str | None) -> list[str]:
    invented = [str(ref) for ref in evidence_summary.get("invented_evidence_refs", []) if ref]
    if blocked_reason == "invented_evidence_refs":
        invented.append(blocked_reason)
    return _dedupe(invented)


def _memory_contradictions(
    *,
    role_outputs: list[LLMRoleOutput],
    evidence_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    summary_contradictions = evidence_summary.get("contradictions", [])
    if isinstance(summary_contradictions, list):
        contradictions.extend(item for item in summary_contradictions if isinstance(item, dict))
    for output in role_outputs:
        role_contradictions = output.content.get("contradictions")
        if isinstance(role_contradictions, list):
            contradictions.extend(item for item in role_contradictions if isinstance(item, dict))
    return sanitize_metadata(contradictions)


def _memory_blocked_intents(blocked_reason: str | None) -> list[str]:
    if blocked_reason is None:
        return []
    lowered = blocked_reason.lower()
    indicators = {
        "forbidden",
        "override",
        "approve_execution",
        "cannot",
        "must_remain",
        "blocked",
        "authority",
        "execution",
    }
    return [blocked_reason] if any(indicator in lowered for indicator in indicators) else []


def _memory_user_review_required(structured_artifacts: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for artifact in structured_artifacts:
        if bool(artifact.get("user_review_required")):
            refs.append(str(artifact.get("proposal_id") or artifact.get("candidate_id") or "proposal"))
    return _dedupe(refs)


def _memory_self_improvement_candidates(structured_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for artifact in structured_artifacts:
        if str(artifact.get("artifact_kind", "")).lower() == "self_improvement":
            candidates.append(sanitize_metadata(artifact))
    return candidates


def _final_packet(
    *,
    role_outputs: list[LLMRoleOutput],
    proposal_artifacts: list[dict[str, Any]],
    action_candidates: list[dict[str, Any]],
    available_evidence_refs: list[str],
) -> dict[str, Any]:
    objections: list[str] = []
    uncertainty: list[str] = []
    evidence_refs: list[str] = []
    role_ids: list[str] = []
    for output in role_outputs:
        role_ids.append(output.role_id.value)
        objections.extend(str(item) for item in output.objections)
        content_objections = output.content.get("objections")
        if isinstance(content_objections, list):
            objections.extend(str(item) for item in content_objections)
        uncertainty.extend(str(item) for item in output.uncertainty)
        content_uncertainty = output.content.get("uncertainty")
        if isinstance(content_uncertainty, list):
            uncertainty.extend(str(item) for item in content_uncertainty)
        evidence_refs.extend(str(item) for item in output.evidence_refs)
    structured_artifacts = [
        artifact for artifact in [*proposal_artifacts, *action_candidates] if isinstance(artifact, dict)
    ]
    evidence_result = EvidenceVerifier(available_evidence_refs=set(available_evidence_refs)).verify_proposal_claims(
        structured_artifacts
    )
    risk_flags = _dedupe(
        [
            str(artifact.get("risk_class"))
            for artifact in structured_artifacts
            if str(artifact.get("risk_class", "")).lower() not in {"", "low"}
        ]
    )
    return sanitize_metadata(
        {
            "role_ids": role_ids,
            "objections": _dedupe(objections),
            "uncertainty": _dedupe(uncertainty),
            "evidence_refs": _dedupe(evidence_refs),
            "proposal_artifacts": structured_artifacts,
            "evidence_verification_summary": {
                "verdict": evidence_result.verdict.value,
                "status": evidence_result.status.value,
                "invented_evidence_refs": evidence_result.invented_evidence_refs,
                "missing_evidence": evidence_result.missing_evidence_claim_ids,
                "contradictions": evidence_result.contradictions,
                "can_grant_authority": evidence_result.can_grant_authority,
                "can_approve_execution": evidence_result.can_approve_execution,
            },
            "unresolved_objections": _dedupe(objections),
            "missing_evidence": evidence_result.missing_evidence_claim_ids,
            "risk_flags": risk_flags,
            "safe_next_step_recommendation": _safe_next_step(evidence_result.verdict, structured_artifacts),
            "authority_effect": "none",
            "execution_effect": "none",
        }
    )


def _safe_next_step(verdict: EvidenceBindingVerdict, structured_artifacts: list[dict[str, Any]]) -> str:
    if not structured_artifacts:
        return "continue_role_loop"
    if verdict in {
        EvidenceBindingVerdict.INVENTED_EVIDENCE_REF,
        EvidenceBindingVerdict.MISSING_EVIDENCE,
        EvidenceBindingVerdict.UNSUPPORTED_CLAIM,
    }:
        return "needs_more_evidence"
    if verdict is EvidenceBindingVerdict.CONTRADICTED:
        return "resolve_contradiction"
    return "submit_proposal_to_gate"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0
