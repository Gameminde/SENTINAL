from __future__ import annotations

from typing import Any

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.organs.browser_readonly_organ_v1 import (
    BrowserReadOnlyAttemptStatus,
    BrowserReadOnlyReceipt,
    BrowserReadOnlyRequest,
)
from sentinel.agent.organs.browser_semantic_extraction_organ_v1 import BrowserSemanticExtractionRequest
from sentinel.agent.organs.browser_session_manager_l5_live import BrowserSessionRequest
from sentinel.agent.organs.organ_dispatch import _organ_request_builders
from sentinel.agent.organs.organ_request_factory import OrganRequestBuildContext, OrganRequestFactory
from sentinel.agent.organs.organ_spec_registry import default_organ_spec_registry
from sentinel.agent.organs.proposal_bridge import (
    BrowserOrganCandidate,
    OrganCandidateAuthorityClass,
    OrganCandidateRiskClass,
    OrganProposalKind,
)
from sentinel.agent.organs.runtime_execution import (
    OrganRuntimeExecutionConfig,
    OrganRuntimeExecutionMode,
    OrganRuntimeExecutionRequest,
    OrganRuntimeExecutionStatus,
    execute_organ_runtime_request,
)
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


MISSION_ID = "mission_pack_f_request_factory"


def _mission(**updates: Any) -> MissionAuthorityEnvelope:
    data = {
        "id": MISSION_ID,
        "user_id": "user_pack_f",
        "mission_type": MissionType.GTM,
        "mission_title": "Pack F request factory",
        "mission_objective": "Build organ runtime requests through specs.",
        "success_criteria": ["request factory is consumed"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["public_web"],
        "allowed_tools": ["browser_session_l5_live"],
        "allowed_actions": ["browser_session_open", "browser_session_observe", "browser_session_close"],
        "forbidden_actions": ["credential_access", "payment", "browser_login"],
        "allowed_domains": ["example.com"],
        "max_duration_minutes": 10,
        "max_actions": 5,
        "max_cost_usd": 0.0,
    }
    data.update(updates)
    return MissionAuthorityEnvelope(**data)


def _candidate(level: DelegatedActionLevel = DelegatedActionLevel.L4) -> BrowserOrganCandidate:
    return BrowserOrganCandidate(
        candidate_id=f"candidate_{level.value.lower()}",
        mission_id=MISSION_ID,
        source_proposal_id=f"proposal_{level.value.lower()}",
        source_role_id="planner",
        organ_kind=OrganProposalKind.BROWSER,
        action_level_candidate=level,
        authority_class=OrganCandidateAuthorityClass.NEEDS_GATE,
        risk_class=OrganCandidateRiskClass.HIGH if level is DelegatedActionLevel.L5 else OrganCandidateRiskClass.LOW,
        evidence_refs=["ev_browser"],
        receipt_refs=["receipt_browser"],
        expected_outcome="Observe a bounded browser page.",
        rollback_posture="browser session can be closed",
        user_review_required=False,
        safe_summary="Browser request factory candidate.",
        params_hash="params_hash",
    )


def _readonly_receipt() -> BrowserReadOnlyReceipt:
    return BrowserReadOnlyReceipt(
        receipt_id="receipt_readonly_pack_f",
        mission_id=MISSION_ID,
        request_id="request_readonly_pack_f",
        lane_id="lane_browser",
        gate_result_id="gate_browser",
        attempt_status=BrowserReadOnlyAttemptStatus.OBSERVED,
        requested_url_hash="requested_url_hash",
        final_url_hash="final_url_hash",
        normalized_origin="https://example.com",
        domain_policy_result="allowed",
        content_type="text/html",
        status_code=200,
        page_content_hash="page_content_hash",
        extracted_text_hash="extracted_text_hash",
        dom_snapshot_hash="dom_snapshot_hash",
        ax_snapshot_hash="ax_snapshot_hash",
        source_confidence_score=0.9,
        safe_summary="Read-only browser page observed.",
    )


def _context(
    *,
    raw_candidate: dict[str, Any],
    level: DelegatedActionLevel = DelegatedActionLevel.L4,
    prior_receipts: list[BrowserReadOnlyReceipt] | None = None,
) -> OrganRequestBuildContext:
    return OrganRequestBuildContext(
        raw_candidate=raw_candidate,
        bridged_candidate=_candidate(level),
        gate_result=None,
        mission_id=MISSION_ID,
        organ_contracts={
            "browser": {
                "available": True,
                "allowed_domains": ["example.com"],
                "allowed_action_levels": [level.value],
                "required_receipt_fields": ["receipt_id", "finalgate_verified"],
                "allowed_substeps": ["browser_read_public_page", "browser_semantic_extract", "browser_session_open"],
            },
            "browser_readonly": {"available": True, "allowed_domains": ["example.com"]},
            "browser_semantic_extraction": {"available": True, "max_evidence_cards": 4},
            "browser_session_manager": {"available": True, "allowed_domains": ["example.com"], "max_steps": 4},
        },
        prior_candidate_results=[],
        authority_envelope=_mission(),
        source_readonly_receipts=prior_receipts or [],
    )


def test_request_factory_builds_browser_session_request_from_spec() -> None:
    factory = OrganRequestFactory(builders=_organ_request_builders())

    result = factory.build(
        "browser_session_manager_l5_live",
        _context(raw_candidate={"url": "https://example.com", "action_kind": "open"}, level=DelegatedActionLevel.L5),
    )

    assert result.accepted is True
    assert result.organ_id == "browser_session_manager"
    assert result.request_field == "browser_session_request"
    assert isinstance(result.sub_request, BrowserSessionRequest)
    assert result.runtime_request_kwargs() == {"browser_session_request": result.sub_request}


def test_request_factory_builds_browser_readonly_request_from_spec() -> None:
    factory = OrganRequestFactory(builders=_organ_request_builders())

    result = factory.build(
        "browser_readonly",
        _context(raw_candidate={"requested_url": "https://example.com/research"}),
    )

    assert result.accepted is True
    assert result.request_field == "browser_readonly_request"
    assert isinstance(result.sub_request, BrowserReadOnlyRequest)
    assert result.sub_request.requested_url == "https://example.com/research"


def test_request_factory_builds_browser_semantic_extraction_request_from_spec() -> None:
    factory = OrganRequestFactory(builders=_organ_request_builders())

    result = factory.build(
        "browser_semantic_extraction",
        _context(
            raw_candidate={
                "semantic_focus": ["price", "supplier"],
                "source_readonly_receipts": [_readonly_receipt().model_dump(mode="python")],
            },
            prior_receipts=[_readonly_receipt()],
        ),
    )

    assert result.accepted is True
    assert result.request_field == "browser_semantic_extraction_request"
    assert isinstance(result.sub_request, BrowserSemanticExtractionRequest)
    assert result.sub_request.source_readonly_receipts[0].receipt_id == "receipt_readonly_pack_f"


def test_runtime_execution_uses_spec_factory_for_known_organ() -> None:
    factory = OrganRequestFactory(builders=_organ_request_builders())
    build = factory.build(
        "browser_readonly",
        _context(raw_candidate={"requested_url": "https://example.com/research"}),
    )
    config = OrganRuntimeExecutionConfig(
        enabled=True,
        mode=OrganRuntimeExecutionMode.BROWSER_READONLY_PREPARATION_ONLY,
        allowed_action_levels=[DelegatedActionLevel.L4],
        allowed_organs=["browser_readonly"],
        allow_l2=False,
        allow_l3=False,
        allow_browser_readonly=True,
    )

    result = execute_organ_runtime_request(
        OrganRuntimeExecutionRequest(
            mission_id=MISSION_ID,
            action_level=DelegatedActionLevel.L4,
            organ_kind=build.organ_id,
            authority_envelope=_mission(),
            **build.runtime_request_kwargs(),
        ),
        config=config,
    )

    assert result.status in {OrganRuntimeExecutionStatus.BLOCKED, OrganRuntimeExecutionStatus.CERTIFIED}
    assert result.executor_result_summary["organ_spec_id"] == "browser_readonly"
    assert result.executor_result_summary["request_field"] == "browser_readonly_request"


def test_unknown_organ_blocks_with_unknown_organ_not_registered() -> None:
    factory = OrganRequestFactory(builders=_organ_request_builders())

    result = factory.build("parallel_unknown_organ", _context(raw_candidate={}))

    assert result.accepted is False
    assert result.blocked_reason == "unknown_organ_not_registered"


def test_locked_high_risk_organ_remains_non_dispatchable() -> None:
    registry = default_organ_spec_registry()

    spec = registry.require("browser_login_credential_session_broker")

    assert spec.default_dispatchable is False
    assert "credential_access" in spec.hard_stop_categories
    assert spec.locked_reason


def test_receipt_finalgate_replay_metadata_preserved_from_spec() -> None:
    registry = default_organ_spec_registry()
    spec = registry.require("browser_semantic_extraction")

    assert spec.receipt_kind == "browser_semantic_extraction_receipt"
    assert "browser_semantic_extraction_finalgate" in spec.proof_requirements
    assert "no_reextract_on_replay" in spec.replay_expectations
