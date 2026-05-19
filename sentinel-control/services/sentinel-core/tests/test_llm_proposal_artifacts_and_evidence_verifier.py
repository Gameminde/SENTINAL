from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.llm import (
    ApiRequestCandidate,
    BrowserStepCandidate,
    ChannelDraftCandidate,
    CodePatchPlanProposal,
    DelegatedActionLevel,
    EvidenceBindingVerdict,
    EvidenceBoundClaim,
    EvidenceVerifier,
    FileOperationCandidate,
    LLMRoleId,
    LLMRoleLoopOrchestrator,
    LLMRoleLoopPlan,
    LLMRoleOutput,
    ProposalArtifact,
    ProposalArtifactKind,
    ProposalArtifactStatus,
    ProposalArtifactValidator,
    ProposalReceipt,
    RoleLoopStatus,
    SelfImprovementProposal,
)
from sentinel.agent.model_contract import (
    ContextBudgetPolicy,
    ModelCapabilityProfile,
    QualityExpectationContract,
    UserModelContract,
)
from sentinel.agent.model_cost import ModelCostProfile


SECRET_VALUE = "unit-test-proposal-token-not-real"
RAW_PROMPT_FRAGMENT = "raw proposal prompt " + SECRET_VALUE


def _base_proposal_fields(**updates: Any) -> dict[str, Any]:
    base = {
        "source_role_id": LLMRoleId.PLANNER,
        "mission_id": "mission_proposals",
        "objective_summary": "Create a non-executing plan artifact.",
        "artifact_kind": ProposalArtifactKind.MISSION_PLAN,
        "action_level_candidate": DelegatedActionLevel.L1,
        "authority_class": "mission_plan_only",
        "risk_class": "low",
        "budget_estimate": {"model_tokens": 120, "organ_calls": 0},
        "evidence_refs": ["ev_1"],
        "receipt_refs": ["role_receipt_1"],
        "expected_outcome": "A safe proposal for later review.",
        "rollback_posture": "reject_proposal",
        "user_review_required": False,
        "uncertainty": ["No execution lane exists yet."],
        "created_from_role_loop_id": "role_loop_1",
        "safe_summary": "Non-executing mission plan proposal.",
    }
    base.update(updates)
    return base


def _proposal(**updates: Any) -> ProposalArtifact:
    return ProposalArtifact(**_base_proposal_fields(**updates))


def _model_contract() -> UserModelContract:
    return UserModelContract(
        selected_provider_id="groq",
        selected_backend_id="groq_openai_compatible_chat",
        selected_model="openai/gpt-oss-20b",
        cost_profile=ModelCostProfile(
            model_name="openai/gpt-oss-20b",
            input_usd_per_1m=0.0,
            output_usd_per_1m=0.0,
            context_window_tokens=128_000,
        ),
        capability_profile=ModelCapabilityProfile(
            model_name="openai/gpt-oss-20b",
            context_window_tokens=128_000,
            supports_tool_calling=False,
        ),
        context_budget_policy=ContextBudgetPolicy(
            max_decision_frame_tokens=2_000,
            max_tool_schema_tokens=250,
            max_evidence_tokens=1_000,
            reserve_output_tokens=200,
        ),
        quality_expectation=QualityExpectationContract(
            expected_quality="proposal_artifacts",
            minimum_evidence_refs=1,
            retry_budget=0,
        ),
    )


class ProposalRoleClient:
    def __init__(self, output: LLMRoleOutput) -> None:
        self.output = output
        self.calls: list[Any] = []

    def complete_role(self, frame) -> LLMRoleOutput:
        self.calls.append(frame)
        return self.output.model_copy(
            update={
                "role_id": frame.role_id,
                "provider_id": frame.selected_provider_id,
                "backend_id": frame.selected_backend_id,
                "model_id": frame.selected_model,
            }
        )


def test_proposal_artifact_requires_authority_risk_budget_evidence_fields() -> None:
    with pytest.raises(ValidationError):
        ProposalArtifact(
            source_role_id=LLMRoleId.PLANNER,
            mission_id="mission_proposals",
            objective_summary="missing required fields",
            artifact_kind=ProposalArtifactKind.MISSION_PLAN,
            action_level_candidate=DelegatedActionLevel.L1,
        )

    artifact = _proposal()
    assert artifact.authority_class == "mission_plan_only"
    assert artifact.risk_class == "low"
    assert artifact.budget_estimate["model_tokens"] == 120
    assert artifact.evidence_refs == ["ev_1"]


def test_proposal_artifact_is_non_executing() -> None:
    artifact = _proposal()
    result = ProposalArtifactValidator.validate(artifact, available_evidence_refs={"ev_1"})

    assert result.valid is True
    assert result.status is ProposalArtifactStatus.VALIDATED
    assert artifact.execution_effect == "proposal_only"
    assert artifact.can_execute is False


def test_browser_candidate_cannot_submit_or_execute() -> None:
    browser = BrowserStepCandidate(
        **_base_proposal_fields(
            artifact_kind=ProposalArtifactKind.BROWSER_STEP_CANDIDATE,
            source_role_id=LLMRoleId.OPERATOR_PLANNER,
        ),
        browser_action="prepare_form",
        target_url_pattern="https://example.invalid/*",
    )
    assert browser.execution_effect == "proposal_only"

    with pytest.raises(ValidationError):
        BrowserStepCandidate(
            **_base_proposal_fields(
                artifact_kind=ProposalArtifactKind.BROWSER_STEP_CANDIDATE,
                source_role_id=LLMRoleId.OPERATOR_PLANNER,
            ),
            browser_action="submit_form",
            target_url_pattern="https://example.invalid/*",
            submit=True,
        )


def test_api_candidate_is_request_plan_only() -> None:
    candidate = ApiRequestCandidate(
        **_base_proposal_fields(
            artifact_kind=ProposalArtifactKind.API_REQUEST_CANDIDATE,
            source_role_id=LLMRoleId.OPERATOR_PLANNER,
        ),
        method="GET",
        endpoint_template="https://api.example.invalid/read",
        request_body_schema={},
    )

    assert candidate.execution_effect == "proposal_only"
    assert candidate.can_execute is False


def test_channel_candidate_is_draft_only() -> None:
    draft = ChannelDraftCandidate(
        **_base_proposal_fields(
            artifact_kind=ProposalArtifactKind.CHANNEL_DRAFT_CANDIDATE,
            source_role_id=LLMRoleId.OPERATOR_PLANNER,
        ),
        channel="email",
        draft_subject="Draft only",
        draft_body_hash="draft_hash_1",
    )
    assert draft.send_now is False

    with pytest.raises(ValidationError):
        ChannelDraftCandidate(
            **_base_proposal_fields(
                artifact_kind=ProposalArtifactKind.CHANNEL_DRAFT_CANDIDATE,
                source_role_id=LLMRoleId.OPERATOR_PLANNER,
            ),
            channel="email",
            draft_subject="No direct send",
            draft_body_hash="draft_hash_2",
            send_now=True,
        )


def test_file_candidate_cannot_mutate_without_future_lane() -> None:
    with pytest.raises(ValidationError):
        FileOperationCandidate(
            **_base_proposal_fields(
                artifact_kind=ProposalArtifactKind.FILE_OPERATION_CANDIDATE,
                source_role_id=LLMRoleId.OPERATOR_PLANNER,
            ),
            path_pattern="sentinel-control/**/*.py",
            operation="write",
            would_mutate=True,
        )


def test_code_patch_plan_does_not_modify_files() -> None:
    plan = CodePatchPlanProposal(
        **_base_proposal_fields(
            artifact_kind=ProposalArtifactKind.CODE_PATCH_PLAN,
            source_role_id=LLMRoleId.CODER_ADVISOR,
        ),
        target_files=["sentinel/agent/llm/proposals.py"],
        test_plan=["pytest tests/test_llm_proposal_artifacts_and_evidence_verifier.py -q"],
    )

    assert plan.file_mutation is False
    assert plan.execution_effect == "proposal_only"


def test_self_improvement_proposal_cannot_mutate_runtime_or_policy() -> None:
    with pytest.raises(ValidationError):
        SelfImprovementProposal(
            **_base_proposal_fields(
                artifact_kind=ProposalArtifactKind.SELF_IMPROVEMENT,
                source_role_id=LLMRoleId.SYNTHESIZER,
            ),
            improvement_area="role_contract",
            mutates_runtime=True,
        )


def test_proposal_recursive_scan_rejects_hidden_tool_or_organ_payload() -> None:
    artifact = _proposal(
        safety_metadata={"nested": {"tool_calls": [{"name": "browser_submit"}]}},
    )

    result = ProposalArtifactValidator.validate(artifact, available_evidence_refs={"ev_1"})

    assert result.valid is False
    assert result.status is ProposalArtifactStatus.REJECTED
    assert "forbidden_executable_payload" in result.reasons


def test_evidence_verifier_rejects_invented_evidence_ref() -> None:
    verifier = EvidenceVerifier(available_evidence_refs={"ev_1"})
    result = verifier.verify_claims(
        [EvidenceBoundClaim(claim_id="claim_1", claim_summary="Supported?", evidence_refs=["ev_fake"])]
    )

    assert result.verdict is EvidenceBindingVerdict.INVENTED_EVIDENCE_REF
    assert result.invented_evidence_refs == ["ev_fake"]


def test_evidence_verifier_marks_missing_evidence() -> None:
    verifier = EvidenceVerifier(available_evidence_refs={"ev_1"})
    result = verifier.verify_claims(
        [EvidenceBoundClaim(claim_id="claim_critical", claim_summary="Needs proof", critical=True)]
    )

    assert result.verdict is EvidenceBindingVerdict.MISSING_EVIDENCE
    assert result.missing_evidence_claim_ids == ["claim_critical"]


def test_evidence_verifier_preserves_contradictions() -> None:
    verifier = EvidenceVerifier(available_evidence_refs={"ev_1", "ev_2"})
    result = verifier.verify_claims(
        [
            EvidenceBoundClaim(
                claim_id="claim_contra",
                claim_summary="Conflicted",
                evidence_refs=["ev_1"],
                contradicted_by_refs=["ev_2"],
                uncertainty=["source disagreement"],
            )
        ]
    )

    assert result.verdict is EvidenceBindingVerdict.CONTRADICTED
    assert result.contradictions == [{"claim_id": "claim_contra", "evidence_refs": ["ev_2"]}]
    assert result.uncertainty == ["source disagreement"]


def test_verifier_pass_cannot_grant_authority() -> None:
    verifier = EvidenceVerifier(available_evidence_refs={"ev_1"})
    result = verifier.verify_claims(
        [EvidenceBoundClaim(claim_id="claim_1", claim_summary="Supported", evidence_refs=["ev_1"])]
    )

    assert result.verdict is EvidenceBindingVerdict.SUPPORTED
    assert result.can_grant_authority is False
    assert result.can_approve_execution is False


def test_role_loop_outputs_proposal_artifacts_without_execution() -> None:
    artifact = _proposal()
    client = ProposalRoleClient(
        LLMRoleOutput(
            role_id=LLMRoleId.PLANNER,
            provider_id="placeholder",
            backend_id="placeholder",
            model_id="placeholder",
            content={"summary": "proposal only"},
            evidence_refs=["ev_1"],
            proposal_artifacts=[artifact.model_dump(mode="json")],
            input_tokens=12,
            output_tokens=8,
        )
    )
    result = LLMRoleLoopOrchestrator(role_model_client=client).run(
        LLMRoleLoopPlan(
            mission_id="mission_proposals",
            mission_goal="Create proposal artifacts.",
            user_model_contract=_model_contract(),
            role_sequence=[LLMRoleId.PLANNER],
            available_evidence_refs=["ev_1"],
            mission_memory_refs=["role_receipt_1"],
            raw_prompt_in_memory_only=RAW_PROMPT_FRAGMENT,
        )
    )

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.proposal_artifacts[0]["artifact_kind"] == ProposalArtifactKind.MISSION_PLAN.value
    assert result.proposal_artifacts[0]["execution_effect"] == "proposal_only"
    assert result.final_packet["evidence_verification_summary"]["verdict"] == EvidenceBindingVerdict.SUPPORTED.value
    assert result.final_packet["safe_next_step_recommendation"] == "submit_proposal_to_gate"


def test_operator_planner_outputs_candidates_only() -> None:
    candidate = BrowserStepCandidate(
        **_base_proposal_fields(
            artifact_kind=ProposalArtifactKind.BROWSER_STEP_CANDIDATE,
            source_role_id=LLMRoleId.OPERATOR_PLANNER,
        ),
        browser_action="navigate",
        target_url_pattern="https://example.invalid/*",
    )
    client = ProposalRoleClient(
        LLMRoleOutput(
            role_id=LLMRoleId.OPERATOR_PLANNER,
            provider_id="placeholder",
            backend_id="placeholder",
            model_id="placeholder",
            content={"candidate_count": 1},
            evidence_refs=["ev_1"],
            action_candidates=[candidate.model_dump(mode="json")],
            input_tokens=12,
            output_tokens=8,
        )
    )

    result = LLMRoleLoopOrchestrator(role_model_client=client).run(
        LLMRoleLoopPlan(
            mission_id="mission_proposals",
            mission_goal="Draft browser candidate only.",
            user_model_contract=_model_contract(),
            role_sequence=[LLMRoleId.OPERATOR_PLANNER],
            available_evidence_refs=["ev_1"],
        )
    )

    assert result.status is RoleLoopStatus.COMPLETED
    assert result.action_candidates[0]["artifact_kind"] == ProposalArtifactKind.BROWSER_STEP_CANDIDATE.value
    assert result.action_candidates[0]["can_execute"] is False


def test_proposal_receipts_do_not_store_raw_prompt_response_reasoning_or_key() -> None:
    artifact = _proposal(
        safe_summary="Safe summary without raw prompt.",
        safety_metadata={"diagnostic_hash": "abc123"},
    )
    receipt = ProposalReceipt.build(
        proposal=artifact,
        input_hash="input_hash_1",
        validation_status="validated",
        verifier_status=EvidenceBindingVerdict.SUPPORTED.value,
    )

    dumped = receipt.model_dump_json()
    assert RAW_PROMPT_FRAGMENT not in dumped
    assert SECRET_VALUE not in dumped
    assert "raw_prompt" not in dumped
    assert "raw_response" not in dumped
    assert "reasoning_details" not in dumped
    assert "hidden_action_payload" not in dumped
