from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.organs.browser_readonly_organ_v1 import (
    BrowserReadOnlyAttemptStatus,
    BrowserReadOnlyOrganV1,
    BrowserReadOnlyRequest,
    L4BrowserReadOnlyExecutorContract,
)
from sentinel.agent.organs.delegated_action_gate import (
    DelegatedActionAuthorityClass,
    DelegatedActionLane,
    DelegatedActionReceiptRequirement,
    DelegatedActionRiskClass,
)
from sentinel.agent.organs.local_artifact_executor import (
    L2ExecutorContract,
    L2LocalArtifactActionKind,
    L2LocalArtifactAttemptStatus,
    L2LocalArtifactExecutor,
    L2LocalArtifactRequest,
)
from sentinel.agent.organs.organ_dispatch import _build_l2_executor_contract
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.proposal_bridge import FileOperationOrganCandidate, OrganCandidateAuthorityClass, OrganCandidateRiskClass
from sentinel.agent.organs.delegated_action_gate import _budget_exhausted
from sentinel.shared.safety_scanner import scan_forbidden_payload_categorized
from sentinel.agent.organs.reversible_workspace_executor import (
    L3ExecutorContract,
    L3ReversibleWorkspaceExecutor,
    L3WorkspaceActionKind,
    L3WorkspaceAttemptStatus,
    L3WorkspaceRequest,
)
from sentinel.agent.model_execution.redaction import text_hash
from sentinel.shared.events import AgentEventType, EventBus, TraceIntegrityError
from sentinel.organs.browser.models import BrowserFetchedPage


NOW = datetime(2026, 5, 26, 12, 0, tzinfo=UTC)


def _browser_contract(**updates: Any) -> L4BrowserReadOnlyExecutorContract:
    base = {
        "mission_id": "mission_browser_audit",
        "lane_id": "lane_browser_audit",
        "gate_result_id": "gate_browser_audit",
        "allowed_domains": ["example.com"],
        "allowed_schemes": ["https"],
        "max_render_seconds": 0.05,
        "receipt_required": True,
        "finalgate_posture_required": True,
        "execution_enabled_for_l4_readonly": True,
    }
    base.update(updates)
    return L4BrowserReadOnlyExecutorContract(**base)


def _browser_lane(**updates: Any) -> DelegatedActionLane:
    base = {
        "lane_id": "lane_browser_audit",
        "mission_id": "mission_browser_audit",
        "source_candidate_id": "candidate_browser_audit",
        "organ_kind": OrganProposalKind.BROWSER,
        "action_level": DelegatedActionLevel.L4,
        "allowed_substeps": ["browser_read_public_page"],
        "forbidden_substeps": ["submit", "login", "upload", "download", "credential", "js"],
        "authority_class": DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        "risk_class": DelegatedActionRiskClass.MEDIUM,
        "budget_limit": {"remaining_action_count": 1},
        "credential_scope": "none",
        "evidence_refs": ["ev_browser_audit"],
        "receipt_refs": ["receipt_gate_browser_audit"],
        "receipt_contract": DelegatedActionReceiptRequirement(
            required_receipt_fields=["page_content_hash", "extracted_text_hash"],
            receipt_refs=["receipt_gate_browser_audit"],
            receipt_contract_hash="browser_audit_receipt_contract_hash",
        ),
        "revocation_rule": "lane can be revoked before observation",
        "rollback_posture": "no mutation",
        "user_review_requirement": "not_required_for_readonly",
        "FinalGate_checks": ["browser_readonly_no_mutation"],
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=5),
        "ttl_seconds": 300,
    }
    base.update(updates)
    return DelegatedActionLane(**base)


def _browser_request(**updates: Any) -> BrowserReadOnlyRequest:
    base = {
        "mission_id": "mission_browser_audit",
        "objective_summary": "Collect public evidence.",
        "requested_url": "https://example.com/research",
        "allowed_domains": ["example.com"],
        "allowed_schemes": ["https"],
        "validity_scope": "mission_browser_audit:web",
        "authority_refs": ["root_browser_audit"],
        "evidence_refs": ["ev_browser_audit"],
        "receipt_refs": ["receipt_gate_browser_audit"],
        "contract": _browser_contract(),
        "delegated_lane": _browser_lane(),
        "max_render_seconds": 0.05,
        "created_at": NOW,
        "current_time": NOW,
        "expires_at": NOW + timedelta(minutes=5),
    }
    base.update(updates)
    return BrowserReadOnlyRequest(**base)


def _browser_page() -> BrowserFetchedPage:
    return BrowserFetchedPage(
        final_url="https://example.com/research",
        status_code=200,
        content_type="text/html; charset=utf-8",
        body="<html><title>Research</title><body>Safe public evidence.</body></html>",
    )


def test_browser_readonly_request_id_is_deterministic_from_content_not_time() -> None:
    first = _browser_request(created_at=NOW, current_time=NOW, expires_at=NOW + timedelta(minutes=5))
    second = _browser_request(
        created_at=NOW + timedelta(hours=1),
        current_time=NOW + timedelta(hours=1),
        expires_at=NOW + timedelta(hours=2),
    )

    assert first.request_id == second.request_id


def test_browser_readonly_preflight_does_not_mutate_dict_contract_or_lane() -> None:
    contract = _browser_contract().model_dump(mode="python")
    lane = _browser_lane().model_dump(mode="python")
    request = BrowserReadOnlyRequest.model_construct(
        request_id="broreq_constructed",
        mission_id="mission_browser_audit",
        objective_summary="Collect public evidence.",
        requested_url="https://example.com/research",
        allowed_domains=["example.com"],
        allowed_schemes=["https"],
        validity_scope="mission_browser_audit:web",
        authority_refs=["root_browser_audit"],
        evidence_refs=["ev_browser_audit"],
        receipt_refs=["receipt_gate_browser_audit"],
        contract=contract,
        delegated_lane=lane,
        max_render_seconds=0.05,
        created_at=NOW,
        current_time=NOW,
        expires_at=NOW + timedelta(minutes=5),
        metadata={},
        network_budget={},
        redirect_policy={},
        render_policy={},
        extraction_policy={},
        source_confidence_policy={},
    )

    result = BrowserReadOnlyOrganV1(fetcher=lambda _req, _url: _browser_page()).observe(request)

    assert result.attempt_status is BrowserReadOnlyAttemptStatus.OBSERVED
    assert isinstance(request.contract, dict)
    assert isinstance(request.delegated_lane, dict)


def test_browser_readonly_fetch_timeout_blocks_without_hanging() -> None:
    def slow_fetcher(_request: BrowserReadOnlyRequest, _url: str) -> BrowserFetchedPage:
        time.sleep(0.25)
        return _browser_page()

    started = time.monotonic()
    result = BrowserReadOnlyOrganV1(fetcher=slow_fetcher).observe(_browser_request())
    elapsed = time.monotonic() - started

    assert elapsed < 0.20
    assert result.attempt_status is BrowserReadOnlyAttemptStatus.FAILED
    assert result.receipt.blocked_reason == "browser_readonly_fetch_timeout"


def test_eventbus_append_uses_fast_path_when_chain_not_dirty(monkeypatch: pytest.MonkeyPatch) -> None:
    bus = EventBus("mission_eventbus_audit")
    bus.append(AgentEventType.AGENT_INITIALIZED, "initialized")

    calls = 0
    original = bus._assert_chain_integrity

    def spy() -> None:
        nonlocal calls
        calls += 1
        original()

    monkeypatch.setattr(bus, "_assert_chain_integrity", spy)
    for index in range(5):
        bus.append(AgentEventType.CONTEXT_BUILT, f"context {index}")

    assert calls == 0
    assert bus.verify_chain() is True


def test_eventbus_dirty_private_list_still_detects_tamper_on_next_append() -> None:
    bus = EventBus("mission_eventbus_dirty_audit")
    first = bus.append(AgentEventType.AGENT_INITIALIZED, "initialized")
    bus.append(AgentEventType.CONTEXT_BUILT, "context")
    bus._events[0] = first.model_copy(update={"summary": "tampered"})

    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.AGENT_BLOCKED, "after tamper")


def _l2_contract(tmp_path: Path) -> L2ExecutorContract:
    return L2ExecutorContract(
        mission_id="mission_l2_audit",
        lane_id="lane_l2_audit",
        gate_result_id="gate_l2_audit",
        allowed_workspace_root=str(tmp_path / "generated_root"),
        allowed_artifact_subdir="artifacts",
        max_artifact_bytes=4096,
        allow_overwrite=False,
        allow_rollback_cleanup=True,
        receipt_required=True,
        tombstone_required_for_cleanup=True,
        finalgate_posture_required=True,
        execution_enabled_for_l2=True,
        contract_version="l2-local-artifact-v0",
    )


def _l2_lane() -> DelegatedActionLane:
    return DelegatedActionLane(
        lane_id="lane_l2_audit",
        mission_id="mission_l2_audit",
        source_candidate_id="candidate_l2_audit",
        organ_kind=OrganProposalKind.FILE_OPERATION,
        action_level=DelegatedActionLevel.L2,
        allowed_substeps=["create_local_artifact"],
        forbidden_substeps=["send", "network", "api", "shell", "browser_submit"],
        authority_class=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        risk_class=DelegatedActionRiskClass.LOW,
        budget_limit={"remaining_action_count": 1},
        credential_scope="none",
        evidence_refs=["ev_l2_audit"],
        receipt_refs=["receipt_gate_l2_audit"],
        receipt_contract=DelegatedActionReceiptRequirement(
            required_receipt_fields=["artifact_hash", "path_metadata"],
            receipt_refs=["receipt_gate_l2_audit"],
            receipt_contract_hash="l2_audit_receipt_contract_hash",
        ),
        revocation_rule="lane can be revoked",
        rollback_posture="delete with tombstone",
        user_review_requirement="not_required",
        FinalGate_checks=["local_only"],
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        ttl_seconds=300,
    )


def test_l2_blocks_symlink_component_even_before_escape_write(tmp_path: Path) -> None:
    root = tmp_path / "generated_root"
    artifact_dir = root / "artifacts"
    outside = tmp_path / "outside"
    artifact_dir.mkdir(parents=True)
    outside.mkdir()
    link = artifact_dir / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment.")

    request = L2LocalArtifactRequest(
        mission_id="mission_l2_audit",
        source_candidate_id="candidate_l2_audit",
        action_kind=L2LocalArtifactActionKind.CREATE_LOCAL_ARTIFACT,
        target_relative_path="link/escape.md",
        content="should not escape",
        metadata={},
        contract=_l2_contract(tmp_path),
        delegated_lane=_l2_lane(),
        budget_estimate={"artifact_bytes": 17, "action_count": 1},
        current_time=NOW,
    )
    result = L2LocalArtifactExecutor().execute(request)

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "symlink_component" in (result.receipt.rejection_reason or "")
    assert not (outside / "escape.md").exists()


def _l3_contract(tmp_path: Path) -> L3ExecutorContract:
    return L3ExecutorContract(
        mission_id="mission_l3_audit",
        lane_id="lane_l3_audit",
        gate_result_id="gate_l3_audit",
        allowed_workspace_root=str(tmp_path / "workspace_root"),
        allowed_workspace_subdir="work",
        max_file_bytes=4096,
        max_patch_bytes=2048,
        allow_overwrite=True,
        allow_delete=False,
        tombstone_required_for_delete=True,
        rollback_required=True,
        rollback_must_be_tested_before_mutation=True,
        receipt_required=True,
        finalgate_posture_required=True,
        execution_enabled_for_l3=True,
        contract_version="l3-reversible-workspace-v0",
    )


def _l3_lane() -> DelegatedActionLane:
    return DelegatedActionLane(
        lane_id="lane_l3_audit",
        mission_id="mission_l3_audit",
        source_candidate_id="candidate_l3_audit",
        organ_kind=OrganProposalKind.FILE_OPERATION,
        action_level=DelegatedActionLevel.L3,
        allowed_substeps=["replace_text_file"],
        forbidden_substeps=["send", "network", "api", "shell", "browser_submit"],
        authority_class=DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        risk_class=DelegatedActionRiskClass.MEDIUM,
        budget_limit={"remaining_action_count": 1},
        credential_scope="none",
        evidence_refs=["ev_l3_audit"],
        receipt_refs=["receipt_gate_l3_audit"],
        receipt_contract=DelegatedActionReceiptRequirement(
            required_receipt_fields=["before_hash", "after_hash", "path_metadata"],
            receipt_refs=["receipt_gate_l3_audit"],
            receipt_contract_hash="l3_audit_receipt_contract_hash",
        ),
        revocation_rule="lane can be revoked",
        rollback_posture="restore before snapshot",
        user_review_requirement="not_required",
        FinalGate_checks=["local_only", "rollback_ready"],
        created_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
        ttl_seconds=300,
    )


def test_l3_blocks_symlink_component_even_when_before_hash_matches_external_file(tmp_path: Path) -> None:
    root = tmp_path / "workspace_root"
    workspace = root / "work"
    outside = tmp_path / "outside"
    workspace.mkdir(parents=True)
    outside.mkdir()
    link = workspace / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment.")
    outside_file = outside / "escape.md"
    outside_file.write_text("outside\n", encoding="utf-8")
    before_hash = text_hash("outside\n")

    request = L3WorkspaceRequest(
        mission_id="mission_l3_audit",
        source_candidate_id="candidate_l3_audit",
        action_kind=L3WorkspaceActionKind.REPLACE_TEXT_FILE,
        target_relative_path="link/escape.md",
        content="mutated\n",
        before_hash=before_hash,
        metadata={},
        metadata_patch={},
        contract=_l3_contract(tmp_path),
        delegated_lane=_l3_lane(),
        budget_estimate={"patch_bytes": 8, "action_count": 1},
        current_time=NOW,
    )
    result = L3ReversibleWorkspaceExecutor().execute(request)

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "symlink_component" in (result.receipt.rejection_reason or "")
    assert outside_file.read_text(encoding="utf-8") == "outside\n"


def test_dispatch_contract_builder_does_not_swallow_programmer_type_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_contract_constructor(**_kwargs: Any) -> L2ExecutorContract:
        raise TypeError("programmer bug should surface")

    monkeypatch.setattr(
        "sentinel.agent.organs.organ_dispatch.L2ExecutorContract",
        broken_contract_constructor,
    )

    with pytest.raises(TypeError, match="programmer bug"):
        _build_l2_executor_contract(
            lane=None,
            mission_id="mission_dispatch_audit",
            organ_contracts={
                "local_artifact": {
                    "allowed_workspace_root": "generated",
                    "allowed_artifact_subdir": "artifacts",
                }
            },
        )


def test_delegated_gate_budget_parser_treats_malformed_budget_as_exhausted() -> None:
    candidate = FileOperationOrganCandidate(
        candidate_id="candidate_budget_audit",
        mission_id="mission_budget_audit",
        source_proposal_id="proposal_budget_audit",
        action_level_candidate=DelegatedActionLevel.L2,
        authority_class=OrganCandidateAuthorityClass.NEEDS_GATE,
        risk_class=OrganCandidateRiskClass.LOW,
        budget_estimate={"action_count": 1},
        evidence_refs=["ev_budget"],
        receipt_refs=["receipt_budget"],
        expected_outcome="Create a local artifact.",
        rollback_posture="delete with tombstone",
        user_review_required=False,
        safe_summary="Budget malformed should block safely.",
        params_hash="params_budget_hash",
    )

    assert _budget_exhausted({"remaining_action_count": "unlimited"}, candidate) is True


def test_delegated_gate_explicit_zero_retries_is_exhausted() -> None:
    candidate = FileOperationOrganCandidate(
        candidate_id="candidate_retry_budget_audit",
        mission_id="mission_budget_audit",
        source_proposal_id="proposal_retry_budget_audit",
        action_level_candidate=DelegatedActionLevel.L2,
        authority_class=OrganCandidateAuthorityClass.NEEDS_GATE,
        risk_class=OrganCandidateRiskClass.LOW,
        budget_estimate={"action_count": 1},
        evidence_refs=["ev_budget"],
        receipt_refs=["receipt_budget"],
        expected_outcome="Create a local artifact.",
        rollback_posture="delete with tombstone",
        user_review_required=False,
        safe_summary="Zero retries should block retry-dependent execution.",
        params_hash="params_retry_budget_hash",
    )

    assert (
        _budget_exhausted(
            {
                "remaining_action_count": 1,
                "remaining_retries": 0,
                "remaining_tokens": 1000,
            },
            candidate,
        )
        is True
    )


def test_safety_scanner_prefers_safe_model_dump_over_raw_model_dump() -> None:
    class CredentialBearingProbe:
        def safe_model_dump(self) -> dict[str, str]:
            return {"safe_ref": "credential_handle_only"}

        def model_dump(self, *_args: Any, **_kwargs: Any) -> dict[str, str]:
            raise AssertionError("raw model_dump must not be called for scanner payloads")

    result = scan_forbidden_payload_categorized({"probe": CredentialBearingProbe()})

    assert result["all"] == []
