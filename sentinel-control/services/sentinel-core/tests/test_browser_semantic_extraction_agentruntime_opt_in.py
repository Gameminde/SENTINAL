from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.organs.browser_preparation_organ_v1 import (
    BrowserPreparationActionClass,
    BrowserPreparationOrganV1,
    BrowserPreparationRequest,
    BrowserPreparationStep,
    BrowserPreparationTargetRef,
    L4BrowserPreparationExecutorContract,
)
from sentinel.agent.organs.browser_readonly_organ_v1 import (
    BrowserReadOnlyOrganV1,
    BrowserReadOnlyRequest,
    L4BrowserReadOnlyExecutorContract,
)
from sentinel.agent.organs.browser_semantic_extraction_organ_v1 import (
    BrowserSemanticExtractionAttemptStatus,
    BrowserSemanticExtractionFinalGateDecision,
    BrowserSemanticExtractionRequest,
    L4BrowserSemanticExtractionContract,
)
from sentinel.agent.organs.delegated_action_gate import (
    DelegatedActionAuthorityClass,
    DelegatedActionBudgetStatus,
    DelegatedActionBudgetSummary,
    DelegatedActionEvidenceStatus,
    DelegatedActionEvidenceSummary,
    DelegatedActionGateDecision,
    DelegatedActionGateResult,
    DelegatedActionGateSafetyValidationResult,
    DelegatedActionGateStatus,
    DelegatedActionGateTrace,
    DelegatedActionOrganContractStatus,
    DelegatedActionReceiptRequirement,
    DelegatedActionRiskClass,
    DelegatedActionLane,
)
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionStatus,
    render_organ_runtime_execution_result_as_untrusted_context,
)
from sentinel.agent.runtime import AgentRuntime
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.organs.browser.models import BrowserFetchedPage
from sentinel.shared.enums import MissionMode, MissionType


NOW = datetime(2026, 5, 21, 12, 30, tzinfo=UTC)


class FakeBrowserReadOnlyFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, request: BrowserReadOnlyRequest, final_url: str) -> BrowserFetchedPage:
        self.calls.append(final_url)
        return BrowserFetchedPage(
            final_url="https://example.com/research",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=(
                "<html><title>Research</title><body>"
                "Customers report slow onboarding. Pricing starts at $49 per month. "
                "A public case study reports 30 percent faster activation."
                "</body></html>"
            ),
        )


def _authority(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_browser_semantic_runtime",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser semantic runtime opt-in",
        mission_objective="Extract untrusted browser evidence candidates from existing browser observations.",
        success_criteria=["semantic extraction receipt exists", "claims remain unverified"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_readonly", "browser_preparation", "browser_semantic_extraction"],
        allowed_actions=["browser_read_public_page", "browser_prepare_plan", "browser_semantic_extract"],
        forbidden_actions=[
            "browser_submit",
            "browser_login",
            "upload_file",
            "download_file",
            "credential_access",
            "execute_javascript",
            "claim_verification_without_evidence_verifier",
        ],
        max_duration_minutes=30,
        max_actions=10,
        max_cost_usd=0.0,
    )


def _receipt_requirement(kind: str) -> DelegatedActionReceiptRequirement:
    if kind == "browser_readonly":
        fields = ["page_content_hash", "extracted_text_hash", "domain_policy_result", "forbidden_surface_absent"]
    elif kind == "browser_preparation":
        fields = ["target_binding_hashes", "proposed_step_hashes", "browser_backend_called", "forbidden_action_classes"]
    else:
        fields = [
            "semantic_evidence_card_hashes",
            "evidence_bound_claim_hashes",
            "source_readonly_receipt_refs",
            "prompt_injection_flags",
            "verified_claim_count",
        ]
    return DelegatedActionReceiptRequirement(
        required_receipt_fields=fields,
        receipt_refs=[f"receipt_gate_{kind}"],
        receipt_contract_hash=f"{kind}_receipt_contract_hash",
    )


def _lane(*, mission_id: str, kind: str, expires_at: datetime | None = None, **updates: Any) -> DelegatedActionLane:
    allowed = {
        "browser_readonly": ["browser_read_public_page"],
        "browser_preparation": ["browser_prepare_navigation", "browser_prepare_click_type_select"],
        "browser_semantic_extraction": ["browser_semantic_extract_evidence_candidates"],
    }[kind]
    base = {
        "lane_id": f"lane_{kind}",
        "mission_id": mission_id,
        "source_candidate_id": f"candidate_{kind}",
        "organ_kind": OrganProposalKind.BROWSER,
        "action_level": DelegatedActionLevel.L4,
        "allowed_substeps": allowed,
        "forbidden_substeps": ["submit", "login", "upload", "download", "credential", "javascript", "claim_verification"],
        "authority_class": DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        "risk_class": DelegatedActionRiskClass.MEDIUM,
        "budget_limit": {"remaining_action_count": 2, "remaining_evidence_cards": 6},
        "credential_scope": "none",
        "evidence_refs": [f"ev_{kind}"],
        "receipt_refs": [f"receipt_gate_{kind}"],
        "receipt_contract": _receipt_requirement(kind),
        "revocation_rule": "browser perception lane can be revoked before runtime use",
        "rollback_posture": "no external mutation; discard semantic receipt",
        "user_review_requirement": "required_before_future_browser_action",
        "FinalGate_checks": ["browser_perception_no_mutation", "claims_not_verified", "data_not_instruction"],
        "created_at": NOW,
        "expires_at": expires_at if expires_at is not None else NOW + timedelta(minutes=30),
        "ttl_seconds": 1800,
    }
    base.update(updates)
    return DelegatedActionLane(**base)


def _gate_result(*, mission_id: str, kind: str, decision: DelegatedActionGateDecision = DelegatedActionGateDecision.ALLOWED, lane: DelegatedActionLane | None = None) -> DelegatedActionGateResult:
    lane = lane if lane is not None else _lane(mission_id=mission_id, kind=kind)
    return DelegatedActionGateResult(
        mission_id=mission_id,
        status=DelegatedActionGateStatus.EVALUATED if decision is DelegatedActionGateDecision.ALLOWED else DelegatedActionGateStatus.BLOCKED,
        decision=decision,
        reasons=[],
        candidate_id=f"candidate_{kind}",
        lane=lane if decision is DelegatedActionGateDecision.ALLOWED else None,
        trace=DelegatedActionGateTrace(
            mission_id=mission_id,
            candidate_id=f"candidate_{kind}",
            decision=decision,
            authority_status=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
            budget_status=DelegatedActionBudgetStatus.PASSING,
            evidence_status=DelegatedActionEvidenceStatus.SUPPORTED,
            organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
            safe_summary="gate metadata for explicit browser semantic runtime opt-in",
        ),
        safety_validation=DelegatedActionGateSafetyValidationResult(),
        risk_class=DelegatedActionRiskClass.MEDIUM,
        budget_status=DelegatedActionBudgetSummary(status=DelegatedActionBudgetStatus.PASSING),
        evidence_status=DelegatedActionEvidenceSummary(
            status=DelegatedActionEvidenceStatus.SUPPORTED,
            evidence_refs=[f"ev_{kind}"],
            available_evidence_refs=[f"ev_{kind}"],
        ),
        organ_contract_status=DelegatedActionOrganContractStatus.PASSING,
        receipt_requirement=_receipt_requirement(kind),
        selected_provider_id="groq",
        selected_backend_id="groq_openai_compatible_chat",
        selected_model="openai/gpt-oss-20b",
    )


def _readonly_observation(mission_id: str = "mission_browser_semantic_runtime"):
    request = BrowserReadOnlyRequest(
        mission_id=mission_id,
        objective_summary="Observe public page before semantic extraction.",
        requested_url="https://example.com/research",
        allowed_domains=["example.com"],
        allowed_schemes=["https"],
        validity_scope=f"{mission_id}:web_evidence",
        authority_refs=["root_browser_semantic_runtime"],
        evidence_refs=["ev_browser_readonly"],
        receipt_refs=["receipt_gate_browser_readonly"],
        contract=L4BrowserReadOnlyExecutorContract(
            mission_id=mission_id,
            lane_id="lane_browser_readonly",
            gate_result_id="gate_browser_readonly",
            allowed_domains=["example.com"],
            allowed_schemes=["https"],
            max_page_bytes=100_000,
            max_extracted_text_bytes=8_000,
            max_redirects=2,
            max_render_seconds=5.0,
        ),
        delegated_lane=_lane(mission_id=mission_id, kind="browser_readonly"),
        include_dom_snapshot=True,
        include_ax_snapshot=True,
        current_time=NOW,
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    result = BrowserReadOnlyOrganV1(fetcher=FakeBrowserReadOnlyFetcher()).observe(request)
    assert result.accepted is True
    return result


def _prepared_observation(readonly_result: Any):
    receipt = readonly_result.receipt
    mission_id = receipt.mission_id
    target = BrowserPreparationTargetRef(
        ref_id="ref_pricing",
        role="link",
        name="Pricing",
        source_kind="ax",
        source_hash=receipt.ax_snapshot_hash,
        source_receipt_id=receipt.receipt_id,
    )
    request = BrowserPreparationRequest(
        mission_id=mission_id,
        objective_summary="Prepare a non-executing browser plan from read-only observation.",
        source_readonly_receipts=[receipt],
        source_dom_snapshot_hash=receipt.dom_snapshot_hash,
        source_ax_snapshot_hash=receipt.ax_snapshot_hash,
        candidate_goal="Inspect pricing evidence later.",
        allowed_preparation_classes=["navigate", "click", "type", "select", "hover", "wait"],
        forbidden_action_classes=["submit", "login", "upload", "download", "credential", "javascript"],
        target_refs=[target],
        proposed_steps=[
            BrowserPreparationStep(
                step_id="step_hover_pricing",
                action_class=BrowserPreparationActionClass.HOVER,
                target_ref_id=target.ref_id,
                safe_intent_summary="Prepare hover over pricing link.",
            )
        ],
        validity_scope=f"{mission_id}:browser_preparation",
        authority_refs=["root_browser_semantic_runtime"],
        evidence_refs=["ev_browser_preparation"],
        receipt_refs=["receipt_gate_browser_preparation"],
        contract=L4BrowserPreparationExecutorContract(
            mission_id=mission_id,
            lane_id="lane_browser_preparation",
            gate_result_id="gate_browser_preparation",
            source_readonly_receipt_refs=[receipt.receipt_id],
            max_candidate_targets=4,
            max_proposed_steps=4,
            max_plan_bytes=40_000,
        ),
        delegated_lane=_lane(mission_id=mission_id, kind="browser_preparation"),
        created_at=NOW,
        current_time=NOW,
        expires_at=NOW + timedelta(minutes=10),
    )
    result = BrowserPreparationOrganV1().prepare(request)
    assert result.accepted is True
    return result


def _semantic_request(mission_id: str = "mission_browser_semantic_runtime", **updates: Any) -> BrowserSemanticExtractionRequest:
    readonly_result = updates.pop("readonly_result", _readonly_observation(mission_id))
    preparation_result = updates.pop("preparation_result", _prepared_observation(readonly_result))
    base = {
        "mission_id": mission_id,
        "objective_summary": "Extract browser observation evidence candidates.",
        "source_readonly_receipts": [readonly_result.receipt],
        "source_preparation_receipts": [preparation_result.receipt],
        "safe_observation_summaries": {
            readonly_result.receipt.receipt_id: (
                "Customers report slow onboarding. Pricing starts at $49 per month. "
                "Case study reports 30 percent faster activation."
            )
        },
        "semantic_focus": ["pain", "pricing", "case_study"],
        "contradiction_refs": ["contradiction_prior_pricing"],
        "validity_scope": f"{mission_id}:browser_semantic_evidence",
        "authority_refs": ["root_browser_semantic_runtime"],
        "evidence_refs": ["ev_browser_semantic"],
        "receipt_refs": ["receipt_gate_browser_semantic_extraction"],
        "contract": L4BrowserSemanticExtractionContract(
            mission_id=mission_id,
            lane_id="lane_browser_semantic_extraction",
            gate_result_id="gate_browser_semantic_extraction",
            source_readonly_receipt_refs=[readonly_result.receipt.receipt_id],
            max_evidence_cards=6,
            max_claims_per_source=4,
        ),
        "delegated_lane": _lane(mission_id=mission_id, kind="browser_semantic_extraction"),
        "created_at": NOW,
        "current_time": NOW,
        "expires_at": NOW + timedelta(minutes=10),
    }
    base.update(updates)
    return BrowserSemanticExtractionRequest(**base)


def _browser_config(**updates: Any) -> OrganRuntimeExecutionConfig:
    base = {
        "enabled": True,
        "mode": OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L4],
        "allowed_organs": ["browser_readonly", "browser_preparation", "browser_semantic_extraction"],
        "allow_l2": False,
        "allow_l3": False,
        "allow_browser_readonly": True,
        "allow_browser_preparation": True,
        "allow_browser_semantic_extraction": True,
        "contract_version": "organ-runtime-browser-semantic-extraction-v1",
    }
    base.update(updates)
    return OrganRuntimeExecutionConfig(**base)


def _runtime(config: OrganRuntimeExecutionConfig | None = None) -> AgentRuntime:
    return AgentRuntime(organ_execution_config=config)


def _semantic_runtime_request(mission_id: str = "mission_browser_semantic_runtime", **updates: Any) -> OrganRuntimeExecutionRequest:
    gate_result = updates.pop("gate_result", _gate_result(mission_id=mission_id, kind="browser_semantic_extraction"))
    base = {
        "mission_id": mission_id,
        "action_level": DelegatedActionLevel.L4,
        "organ_kind": "browser_semantic_extraction",
        "authority_envelope": _authority(mission_id),
        "gate_result": gate_result,
        "delegated_lane": gate_result.lane,
        "browser_semantic_extraction_request": _semantic_request(mission_id),
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
        "current_time": NOW,
    }
    base.update(updates)
    return OrganRuntimeExecutionRequest(**base)


def test_browser_semantic_runtime_opt_in_disabled_by_default_blocks() -> None:
    result = AgentRuntime().execute_organ_runtime_request(_semantic_runtime_request())

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "organ_execution_disabled"
    assert result.receipt is None


def test_browser_semantic_runtime_works_when_explicitly_opted_in() -> None:
    result = _runtime(_browser_config()).execute_organ_runtime_request(_semantic_runtime_request())

    assert result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert result.action_level is DelegatedActionLevel.L4
    assert result.organ_kind == "browser_semantic_extraction"
    assert result.execution_effect == "none"
    assert result.receipt.attempt_status is BrowserSemanticExtractionAttemptStatus.EXTRACTED
    assert result.receipt.verified_claim_count == 0
    assert result.receipt.browser_backend_called is False
    assert result.finalgate_certificate.decision is BrowserSemanticExtractionFinalGateDecision.CERTIFIED_EXTRACTION_SUCCESS


def test_browser_semantic_runtime_can_be_disabled_by_config() -> None:
    result = _runtime(
        _browser_config(allow_browser_semantic_extraction=False, allowed_organs=["browser_readonly", "browser_preparation"])
    ).execute_organ_runtime_request(_semantic_runtime_request())

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "browser_semantic_extraction_disabled_by_config"


def test_browser_semantic_runtime_requires_readonly_source_receipt() -> None:
    request = _semantic_request(source_readonly_receipts=[], source_readonly_receipt_refs=[], safe_observation_summaries={})

    result = _runtime(_browser_config()).execute_organ_runtime_request(
        _semantic_runtime_request(browser_semantic_extraction_request=request)
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "browser_semantic_extraction_source_readonly_receipt_missing"


def test_browser_semantic_runtime_blocks_forbidden_payload() -> None:
    request = _semantic_runtime_request(metadata={"browser_submit": True, "execute_javascript": True, "credential": "nope"})

    result = _runtime(_browser_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_browser_semantic_runtime_blocks_l5_plus_actions() -> None:
    request = _semantic_runtime_request(action_level=DelegatedActionLevel.L5)

    result = _runtime(_browser_config()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "action_level_not_allowed"


def test_browser_semantic_runtime_preserves_selected_provider_backend_model() -> None:
    result = _runtime(_browser_config()).execute_organ_runtime_request(_semantic_runtime_request())

    assert result.selected_provider_id == "groq"
    assert result.selected_backend_id == "groq_openai_compatible_chat"
    assert result.selected_model == "openai/gpt-oss-20b"


def test_browser_semantic_runtime_result_rendering_is_data_not_instruction() -> None:
    result = _runtime(_browser_config()).execute_organ_runtime_request(_semantic_runtime_request())

    rendered = render_organ_runtime_execution_result_as_untrusted_context(result)

    assert "not instructions" in rendered
    assert "not Root Authority" in rendered
    assert "not permission" in rendered
    assert "data_not_instruction=true" in rendered
    assert "organ_kind=browser_semantic_extraction" in rendered


def test_browser_semantic_runtime_default_runtime_behavior_still_disabled() -> None:
    runtime = AgentRuntime()

    assert runtime._organ_execution_config.enabled is False
    assert runtime._organ_execution_config.mode is OrganRuntimeExecutionMode.DISABLED
