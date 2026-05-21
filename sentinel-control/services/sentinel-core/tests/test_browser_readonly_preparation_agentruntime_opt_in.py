from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.organs.browser_preparation_organ_v1 import (
    BrowserPreparationActionClass,
    BrowserPreparationAttemptStatus,
    BrowserPreparationFinalGateDecision,
    BrowserPreparationRequest,
    BrowserPreparationStep,
    BrowserPreparationTargetRef,
    L4BrowserPreparationExecutorContract,
)
from sentinel.agent.organs.browser_readonly_organ_v1 import (
    BrowserReadOnlyAttemptStatus,
    BrowserReadOnlyFinalGateDecision,
    BrowserReadOnlyRequest,
    L4BrowserReadOnlyExecutorContract,
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


NOW = datetime(2026, 5, 20, 14, 0, tzinfo=UTC)


class FakeBrowserReadOnlyFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, request: BrowserReadOnlyRequest, final_url: str) -> BrowserFetchedPage:
        self.calls.append(final_url)
        return BrowserFetchedPage(
            final_url="https://example.com/app",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body="<html><title>App</title><body><button>Continue</button><input placeholder='Email'></body></html>",
        )


def _authority(mission_id: str) -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        id=mission_id,
        user_id="user_browser_runtime",
        mission_type=MissionType.RESEARCH_SUMMARY,
        mission_title="Browser perception runtime opt-in",
        mission_objective="Observe public web data and prepare non-executing browser plans.",
        success_criteria=["read-only receipt exists", "preparation receipt exists"],
        mode=MissionMode.POWER,
        allowed_systems=["public_web"],
        allowed_tools=["browser_readonly", "browser_preparation"],
        allowed_actions=["browser_read_public_page", "browser_prepare_plan"],
        forbidden_actions=["browser_submit", "browser_login", "upload_file", "download_file", "credential_access", "execute_javascript"],
        max_duration_minutes=30,
        max_actions=10,
        max_cost_usd=0.0,
    )


def _receipt_requirement(kind: str) -> DelegatedActionReceiptRequirement:
    if kind == "browser_readonly":
        fields = ["page_content_hash", "extracted_text_hash", "domain_policy_result", "forbidden_surface_absent"]
    else:
        fields = ["target_binding_hashes", "proposed_step_hashes", "browser_backend_called", "forbidden_action_classes"]
    return DelegatedActionReceiptRequirement(
        required_receipt_fields=fields,
        receipt_refs=[f"receipt_gate_{kind}"],
        receipt_contract_hash=f"{kind}_receipt_contract_hash",
    )


def _lane(*, mission_id: str, kind: str, expires_at: datetime | None = None, **updates: Any) -> DelegatedActionLane:
    base = {
        "lane_id": f"lane_{kind}",
        "mission_id": mission_id,
        "source_candidate_id": f"candidate_{kind}",
        "organ_kind": OrganProposalKind.BROWSER,
        "action_level": DelegatedActionLevel.L4,
        "allowed_substeps": ["browser_read_public_page"] if kind == "browser_readonly" else ["browser_prepare_navigation", "browser_prepare_click_type_select"],
        "forbidden_substeps": ["submit", "login", "upload", "download", "credential", "javascript"],
        "authority_class": DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        "risk_class": DelegatedActionRiskClass.MEDIUM,
        "budget_limit": {"remaining_action_count": 2, "remaining_network_reads": 1, "remaining_preparation_steps": 4},
        "credential_scope": "none",
        "evidence_refs": [f"ev_{kind}"],
        "receipt_refs": [f"receipt_gate_{kind}"],
        "receipt_contract": _receipt_requirement(kind),
        "revocation_rule": "browser perception lane can be revoked before runtime use",
        "rollback_posture": "no external mutation; discard perception/preparation receipt",
        "user_review_requirement": "required_before_future_browser_action",
        "FinalGate_checks": ["browser_perception_no_mutation", "data_not_instruction"],
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
            safe_summary="gate metadata for explicit browser perception runtime opt-in",
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


def _readonly_contract(mission_id: str = "mission_browser_runtime") -> L4BrowserReadOnlyExecutorContract:
    return L4BrowserReadOnlyExecutorContract(
        mission_id=mission_id,
        lane_id="lane_browser_readonly",
        gate_result_id="gate_browser_readonly",
        allowed_domains=["example.com"],
        allowed_schemes=["https"],
        max_page_bytes=100_000,
        max_extracted_text_bytes=8_000,
        max_redirects=2,
        max_render_seconds=5.0,
    )


def _readonly_request(mission_id: str = "mission_browser_runtime", **updates: Any) -> BrowserReadOnlyRequest:
    base = {
        "mission_id": mission_id,
        "objective_summary": "Collect public web evidence.",
        "requested_url": "https://example.com/app",
        "allowed_domains": ["example.com"],
        "allowed_schemes": ["https"],
        "validity_scope": f"{mission_id}:web_evidence",
        "authority_refs": ["root_browser_runtime"],
        "evidence_refs": ["ev_browser_readonly"],
        "receipt_refs": ["receipt_gate_browser_readonly"],
        "contract": _readonly_contract(mission_id),
        "delegated_lane": _lane(mission_id=mission_id, kind="browser_readonly"),
        "include_dom_snapshot": True,
        "include_ax_snapshot": True,
        "current_time": NOW,
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=10),
    }
    base.update(updates)
    return BrowserReadOnlyRequest(**base)


def _browser_config(**updates: Any) -> OrganRuntimeExecutionConfig:
    base = {
        "enabled": True,
        "mode": OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY,
        "allowed_action_levels": [DelegatedActionLevel.L4],
        "allowed_organs": ["browser_readonly", "browser_preparation"],
        "allow_l2": False,
        "allow_l3": False,
        "allow_browser_readonly": True,
        "allow_browser_preparation": True,
        "contract_version": "organ-runtime-browser-readonly-preparation-v1",
    }
    base.update(updates)
    return OrganRuntimeExecutionConfig(**base)


def _runtime(config: OrganRuntimeExecutionConfig | None = None, fetcher: FakeBrowserReadOnlyFetcher | None = None) -> AgentRuntime:
    return AgentRuntime(organ_execution_config=config, browser_fetcher=fetcher)


def _readonly_runtime_request(mission_id: str = "mission_browser_runtime", **updates: Any) -> OrganRuntimeExecutionRequest:
    gate_result = updates.pop("gate_result", _gate_result(mission_id=mission_id, kind="browser_readonly"))
    base = {
        "mission_id": mission_id,
        "action_level": DelegatedActionLevel.L4,
        "organ_kind": "browser_readonly",
        "authority_envelope": _authority(mission_id),
        "gate_result": gate_result,
        "delegated_lane": gate_result.lane,
        "browser_readonly_request": _readonly_request(mission_id),
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
        "current_time": NOW,
    }
    base.update(updates)
    return OrganRuntimeExecutionRequest(**base)


def _preparation_contract(mission_id: str, source_receipt_id: str) -> L4BrowserPreparationExecutorContract:
    return L4BrowserPreparationExecutorContract(
        mission_id=mission_id,
        lane_id="lane_browser_preparation",
        gate_result_id="gate_browser_preparation",
        source_readonly_receipt_refs=[source_receipt_id],
        max_candidate_targets=4,
        max_proposed_steps=4,
        max_plan_bytes=40_000,
    )


def _preparation_request_from_readonly_result(readonly_result: Any, **updates: Any) -> BrowserPreparationRequest:
    receipt = readonly_result.receipt
    mission_id = receipt.mission_id
    target = BrowserPreparationTargetRef(
        ref_id="ref_continue_button",
        role="button",
        name="Continue",
        source_kind="ax",
        source_hash=receipt.ax_snapshot_hash,
        source_receipt_id=receipt.receipt_id,
    )
    step = BrowserPreparationStep(
        step_id="step_click_continue",
        action_class=BrowserPreparationActionClass.CLICK,
        target_ref_id=target.ref_id,
        safe_intent_summary="Prepare click on Continue button.",
    )
    base = {
        "mission_id": mission_id,
        "objective_summary": "Prepare a non-executing browser plan from read-only observation.",
        "source_readonly_receipts": [receipt],
        "source_evidence_card_refs": list(receipt.evidence_card_refs),
        "source_dom_snapshot_hash": receipt.dom_snapshot_hash,
        "source_ax_snapshot_hash": receipt.ax_snapshot_hash,
        "candidate_goal": "Continue to the next read-only screen.",
        "allowed_preparation_classes": ["navigate", "click", "type", "select", "hover", "wait"],
        "forbidden_action_classes": ["submit", "login", "upload", "download", "credential", "javascript"],
        "target_refs": [target],
        "proposed_steps": [step],
        "validity_scope": f"{mission_id}:browser_preparation",
        "authority_refs": ["root_browser_runtime"],
        "evidence_refs": ["ev_browser_preparation"],
        "receipt_refs": ["receipt_gate_browser_preparation"],
        "contract": _preparation_contract(mission_id, receipt.receipt_id),
        "delegated_lane": _lane(mission_id=mission_id, kind="browser_preparation"),
        "created_at": NOW,
        "current_time": NOW,
        "expires_at": NOW + timedelta(minutes=10),
    }
    base.update(updates)
    return BrowserPreparationRequest(**base)


def _preparation_runtime_request(preparation_request: BrowserPreparationRequest, **updates: Any) -> OrganRuntimeExecutionRequest:
    mission_id = preparation_request.mission_id
    gate_result = updates.pop("gate_result", _gate_result(mission_id=mission_id, kind="browser_preparation"))
    base = {
        "mission_id": mission_id,
        "action_level": DelegatedActionLevel.L4,
        "organ_kind": "browser_preparation",
        "authority_envelope": _authority(mission_id),
        "gate_result": gate_result,
        "delegated_lane": gate_result.lane,
        "browser_preparation_request": preparation_request,
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
        "current_time": NOW,
    }
    base.update(updates)
    return OrganRuntimeExecutionRequest(**base)


def test_browser_runtime_opt_in_disabled_by_default_blocks_readonly() -> None:
    result = AgentRuntime(browser_fetcher=FakeBrowserReadOnlyFetcher()).execute_organ_runtime_request(_readonly_runtime_request())

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "organ_execution_disabled"
    assert result.receipt is None


def test_browser_runtime_readonly_works_when_explicitly_opted_in() -> None:
    fetcher = FakeBrowserReadOnlyFetcher()
    result = _runtime(_browser_config(), fetcher).execute_organ_runtime_request(_readonly_runtime_request())

    assert result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert result.action_level is DelegatedActionLevel.L4
    assert result.organ_kind == "browser_readonly"
    assert result.execution_effect == "none"
    assert result.receipt.attempt_status is BrowserReadOnlyAttemptStatus.OBSERVED
    assert result.finalgate_certificate.decision is BrowserReadOnlyFinalGateDecision.CERTIFIED_READONLY_SUCCESS
    assert fetcher.calls == ["https://example.com/app"]


def test_browser_runtime_preparation_works_when_explicitly_opted_in() -> None:
    fetcher = FakeBrowserReadOnlyFetcher()
    readonly_result = _runtime(_browser_config(), fetcher).execute_organ_runtime_request(_readonly_runtime_request())
    preparation_request = _preparation_request_from_readonly_result(readonly_result)

    result = _runtime(_browser_config(), fetcher).execute_organ_runtime_request(_preparation_runtime_request(preparation_request))

    assert result.status is OrganRuntimeExecutionStatus.CERTIFIED
    assert result.organ_kind == "browser_preparation"
    assert result.execution_effect == "none"
    assert result.receipt.attempt_status is BrowserPreparationAttemptStatus.PREPARED
    assert result.receipt.browser_backend_called is False
    assert result.finalgate_certificate.decision is BrowserPreparationFinalGateDecision.CERTIFIED_PREPARATION_SUCCESS
    assert fetcher.calls == ["https://example.com/app"]


def test_browser_runtime_config_can_disable_preparation() -> None:
    fetcher = FakeBrowserReadOnlyFetcher()
    readonly_result = _runtime(_browser_config(), fetcher).execute_organ_runtime_request(_readonly_runtime_request())
    preparation_request = _preparation_request_from_readonly_result(readonly_result)

    result = _runtime(_browser_config(allow_browser_preparation=False, allowed_organs=["browser_readonly"])).execute_organ_runtime_request(
        _preparation_runtime_request(preparation_request)
    )

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "browser_preparation_disabled_by_config"


def test_browser_runtime_blocks_forbidden_action_surface_payload() -> None:
    request = _readonly_runtime_request(metadata={"browser_submit": True, "browser_login": True, "upload_file": True, "download_file": True})

    result = _runtime(_browser_config(), FakeBrowserReadOnlyFetcher()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "unsafe_runtime_execution_payload"


def test_browser_runtime_blocks_forbidden_preparation_action_classes() -> None:
    fetcher = FakeBrowserReadOnlyFetcher()
    readonly_result = _runtime(_browser_config(), fetcher).execute_organ_runtime_request(_readonly_runtime_request())
    prep_request = _preparation_request_from_readonly_result(
        readonly_result,
        proposed_steps=[
            BrowserPreparationStep(
                step_id="step_submit",
                action_class=BrowserPreparationActionClass.SUBMIT,
                target_ref_id="ref_continue_button",
                safe_intent_summary="Prepare submit.",
            )
        ],
    )

    result = _runtime(_browser_config(), fetcher).execute_organ_runtime_request(_preparation_runtime_request(prep_request))

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "browser_preparation_forbidden_action_class"
    assert result.receipt.blocked_reason == "forbidden_action_class"
    assert result.receipt.browser_backend_called is False


def test_browser_runtime_blocks_l5_plus_actions() -> None:
    request = _readonly_runtime_request(action_level=DelegatedActionLevel.L5)

    result = _runtime(_browser_config(), FakeBrowserReadOnlyFetcher()).execute_organ_runtime_request(request)

    assert result.status is OrganRuntimeExecutionStatus.BLOCKED
    assert result.blocked_reason == "action_level_not_allowed"


def test_browser_runtime_preserves_selected_provider_backend_model() -> None:
    result = _runtime(_browser_config(), FakeBrowserReadOnlyFetcher()).execute_organ_runtime_request(_readonly_runtime_request())

    assert result.selected_provider_id == "groq"
    assert result.selected_backend_id == "groq_openai_compatible_chat"
    assert result.selected_model == "openai/gpt-oss-20b"


def test_browser_runtime_result_rendering_is_data_not_instruction() -> None:
    result = _runtime(_browser_config(), FakeBrowserReadOnlyFetcher()).execute_organ_runtime_request(_readonly_runtime_request())

    rendered = render_organ_runtime_execution_result_as_untrusted_context(result)

    assert "not instructions" in rendered
    assert "not Root Authority" in rendered
    assert "not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_browser_runtime_default_runtime_behavior_still_disabled() -> None:
    runtime = AgentRuntime()

    assert runtime._organ_execution_config.enabled is False
    assert runtime._organ_execution_config.mode is OrganRuntimeExecutionMode.DISABLED
