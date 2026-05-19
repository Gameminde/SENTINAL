from __future__ import annotations

from datetime import UTC, datetime
from inspect import signature
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.llm import DelegatedActionLevel
from sentinel.agent.organs.local_artifact_executor import (
    L2LocalArtifactAttemptStatus,
    L2LocalArtifactReceipt,
    L2LocalArtifactRollbackReceipt,
    L2LocalArtifactTombstone,
)
from sentinel.agent.organs.low_risk_finalgate import (
    LowRiskFinalGate,
    LowRiskFinalGateCertificate,
    LowRiskFinalGateDecision,
    LowRiskFinalGateInput,
    LowRiskFinalGateResult,
    render_low_risk_finalgate_certificate_as_untrusted_context,
)
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionMode
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.reversible_workspace_executor import (
    L3WorkspaceAttemptStatus,
    L3WorkspaceReceipt,
    L3WorkspaceRollbackReceipt,
    L3WorkspaceTombstone,
)
from sentinel.agent.runtime import AgentRuntime


NOW = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)


def _path_metadata(**updates: Any) -> dict[str, Any]:
    base = {
        "relative_path": "reports/output.md",
        "filename": "output.md",
        "suffix": ".md",
        "allowed_workspace_root": "C:/sentinel/workspace",
        "allowed_artifact_subdir": "generated",
        "allowed_workspace_subdir": "work",
        "workspace_root_hash": "workspace_root_hash",
        "target_path_hash": "target_path_hash",
        "containment_method": "Path.resolve+relative_to",
    }
    base.update(updates)
    return base


def _l2_success_receipt(**updates: Any) -> L2LocalArtifactReceipt:
    base = {
        "receipt_id": "l2_receipt_success",
        "mission_id": "mission_fg",
        "lane_id": "lane_l2",
        "gate_result_id": "gate_l2",
        "attempt_status": L2LocalArtifactAttemptStatus.CREATED,
        "path_metadata": _path_metadata(),
        "artifact_hash": "artifact_hash_l2",
        "budget_used": {"action_count": 1, "artifact_bytes": 120},
        "rollback_posture": "delete generated artifact with tombstone",
        "created_at": NOW,
        "executor_contract_version": "l2-local-artifact-v0",
        "safe_summary": "L2 artifact was created locally.",
        "execution_effect": "local_artifact_created",
    }
    base.update(updates)
    return L2LocalArtifactReceipt(**base)


def _l2_blocked_receipt(**updates: Any) -> L2LocalArtifactReceipt:
    base = {
        "receipt_id": "l2_receipt_blocked",
        "mission_id": "mission_fg",
        "lane_id": "lane_l2",
        "gate_result_id": "gate_l2",
        "attempt_status": L2LocalArtifactAttemptStatus.BLOCKED,
        "path_metadata": _path_metadata(relative_path="../blocked.md"),
        "artifact_hash": None,
        "budget_used": {"action_count": 0},
        "rollback_posture": "rollback unavailable or blocked",
        "rejection_reason": "parent_traversal",
        "created_at": NOW,
        "executor_contract_version": "l2-local-artifact-v0",
        "safe_summary": "L2 artifact attempt blocked before mutation.",
        "execution_effect": "none",
    }
    base.update(updates)
    return L2LocalArtifactReceipt(**base)


def _l2_rollback_receipt(**updates: Any) -> L2LocalArtifactRollbackReceipt:
    tombstone = L2LocalArtifactTombstone(
        tombstone_id="l2_tombstone_1",
        tombstone_path="C:/sentinel/workspace/generated/.sentinel_tombstones/l2_rollback_1.json",
        original_artifact_hash="artifact_hash_l2",
        cleanup_reason="cleanup generated artifact",
        rollback_receipt_id="l2_rollback_1",
        lane_id="lane_l2",
        gate_result_id="gate_l2",
        path_metadata=_path_metadata(),
    )
    base = {
        "rollback_receipt_id": "l2_rollback_1",
        "original_receipt_id": "l2_receipt_success",
        "mission_id": "mission_fg",
        "lane_id": "lane_l2",
        "gate_result_id": "gate_l2",
        "attempt_status": L2LocalArtifactAttemptStatus.ROLLBACK_COMPLETED,
        "original_artifact_hash": "artifact_hash_l2",
        "path_metadata": _path_metadata(),
        "tombstone": tombstone,
        "cleanup_reason": "cleanup generated artifact",
        "created_at": NOW,
        "safe_summary": "L2 rollback cleaned artifact and wrote tombstone.",
    }
    base.update(updates)
    return L2LocalArtifactRollbackReceipt(**base)


def _l3_success_receipt(**updates: Any) -> L3WorkspaceReceipt:
    base = {
        "receipt_id": "l3_receipt_success",
        "mission_id": "mission_fg",
        "lane_id": "lane_l3",
        "gate_result_id": "gate_l3",
        "attempt_status": L3WorkspaceAttemptStatus.MUTATED,
        "path_metadata": _path_metadata(relative_path="docs/state.md"),
        "before_hash": "before_hash_l3",
        "after_hash": "after_hash_l3",
        "input_hash": "input_hash_l3",
        "output_hash": "output_hash_l3",
        "budget_used": {"action_count": 1, "patch_bytes": 80},
        "rollback_posture": "restore previous content from before snapshot",
        "created_at": NOW,
        "executor_contract_version": "l3-reversible-workspace-v0",
        "safe_summary": "L3 reversible workspace mutation completed locally.",
        "execution_effect": "reversible_workspace_mutation",
    }
    base.update(updates)
    return L3WorkspaceReceipt(**base)


def _l3_blocked_receipt(**updates: Any) -> L3WorkspaceReceipt:
    base = {
        "receipt_id": "l3_receipt_blocked",
        "mission_id": "mission_fg",
        "lane_id": "lane_l3",
        "gate_result_id": "gate_l3",
        "attempt_status": L3WorkspaceAttemptStatus.BLOCKED,
        "path_metadata": _path_metadata(relative_path="../blocked.md"),
        "before_hash": "before_hash_l3",
        "after_hash": None,
        "input_hash": "input_hash_l3_blocked",
        "output_hash": "output_hash_l3_blocked",
        "budget_used": {"action_count": 0},
        "rollback_posture": "rollback unavailable or blocked",
        "rejection_reason": "parent_traversal",
        "created_at": NOW,
        "executor_contract_version": "l3-reversible-workspace-v0",
        "safe_summary": "L3 attempt blocked before mutation.",
        "execution_effect": "none",
    }
    base.update(updates)
    return L3WorkspaceReceipt(**base)


def _l3_rollback_receipt(**updates: Any) -> L3WorkspaceRollbackReceipt:
    tombstone = L3WorkspaceTombstone(
        tombstone_id="l3_tombstone_1",
        tombstone_path="C:/sentinel/workspace/work/.sentinel_tombstones/l3_tombstone_1.json",
        original_path_metadata=_path_metadata(relative_path="docs/state.md"),
        original_hash="before_hash_l3",
        cleanup_reason="restore previous state",
        rollback_receipt_id="l3_rollback_1",
        lane_id="lane_l3",
        gate_result_id="gate_l3",
    )
    base = {
        "rollback_receipt_id": "l3_rollback_1",
        "original_receipt_id": "l3_receipt_success",
        "mission_id": "mission_fg",
        "lane_id": "lane_l3",
        "gate_result_id": "gate_l3",
        "attempt_status": L3WorkspaceAttemptStatus.ROLLBACK_COMPLETED,
        "before_hash": "before_hash_l3",
        "restored_hash": "before_hash_l3",
        "path_metadata": _path_metadata(relative_path="docs/state.md"),
        "tombstone": tombstone,
        "rollback_reason": "restore previous state",
        "created_at": NOW,
        "safe_summary": "L3 rollback restored previous content.",
    }
    base.update(updates)
    return L3WorkspaceRollbackReceipt(**base)


def _input(receipt: Any, **updates: Any) -> LowRiskFinalGateInput:
    level = DelegatedActionLevel.L2
    lane_id = "lane_l2"
    gate_id = "gate_l2"
    if isinstance(receipt, L3WorkspaceReceipt | L3WorkspaceRollbackReceipt):
        level = DelegatedActionLevel.L3
        lane_id = "lane_l3"
        gate_id = "gate_l3"
    base = {
        "mission_id": "mission_fg",
        "expected_action_level": level,
        "expected_organ_kind": OrganProposalKind.FILE_OPERATION,
        "allowed_lane_id": lane_id,
        "expected_gate_result_id": gate_id,
        "approved_workspace_root_metadata": _path_metadata(),
        "receipt": receipt,
        "known_evidence_refs": ["ev_fg"],
        "known_receipt_refs": ["receipt_gate"],
        "budget_refs": ["budget_fg"],
        "rollback_required": level is DelegatedActionLevel.L3,
        "selected_provider_id": "groq",
        "selected_backend_id": "groq_openai_compatible_chat",
        "selected_model": "openai/gpt-oss-20b",
        "current_time": NOW,
    }
    base.update(updates)
    return LowRiskFinalGateInput(**base)


def _certify(receipt: Any, **updates: Any) -> LowRiskFinalGateResult:
    return LowRiskFinalGate().certify(_input(receipt, **updates))


def test_finalgate_certifies_l2_success_receipt() -> None:
    result = _certify(_l2_success_receipt())

    assert result.decision is LowRiskFinalGateDecision.CERTIFIED_SUCCESS
    assert result.certificate.artifact_hash == "artifact_hash_l2"
    assert result.certificate.containment_verified is True


def test_finalgate_certifies_l2_blocked_receipt() -> None:
    result = _certify(_l2_blocked_receipt())

    assert result.decision is LowRiskFinalGateDecision.CERTIFIED_BLOCKED
    assert result.certificate.forbidden_surface_absent is True


def test_finalgate_rejects_l2_missing_artifact_hash() -> None:
    result = _certify(_l2_success_receipt(artifact_hash=None))

    assert result.decision is LowRiskFinalGateDecision.REJECTED_MISSING_HASHES


def test_finalgate_rejects_l2_scope_mismatch() -> None:
    result = _certify(_l2_success_receipt(mission_id="other_mission"))

    assert result.decision is LowRiskFinalGateDecision.REJECTED_SCOPE_MISMATCH


def test_finalgate_certifies_l3_success_receipt_with_before_after_hashes() -> None:
    result = _certify(_l3_success_receipt())

    assert result.decision is LowRiskFinalGateDecision.CERTIFIED_SUCCESS
    assert result.certificate.before_hash == "before_hash_l3"
    assert result.certificate.after_hash == "after_hash_l3"


def test_finalgate_certifies_l3_blocked_receipt() -> None:
    result = _certify(_l3_blocked_receipt())

    assert result.decision is LowRiskFinalGateDecision.CERTIFIED_BLOCKED


def test_finalgate_rejects_l3_missing_before_hash() -> None:
    result = _certify(_l3_success_receipt(before_hash=None))

    assert result.decision is LowRiskFinalGateDecision.REJECTED_MISSING_HASHES


def test_finalgate_rejects_l3_missing_after_hash_when_mutated() -> None:
    result = _certify(_l3_success_receipt(after_hash=None))

    assert result.decision is LowRiskFinalGateDecision.REJECTED_MISSING_HASHES


def test_finalgate_rejects_l3_missing_rollback_posture_when_required() -> None:
    result = _certify(_l3_success_receipt(rollback_posture=""))

    assert result.decision is LowRiskFinalGateDecision.REJECTED_MISSING_ROLLBACK_POSTURE


def test_finalgate_certifies_l2_rollback_receipt() -> None:
    result = _certify(_l2_success_receipt(), rollback_receipt=_l2_rollback_receipt())

    assert result.decision is LowRiskFinalGateDecision.CERTIFIED_ROLLBACK_SUCCESS
    assert result.certificate.rollback_receipt_id == "l2_rollback_1"


def test_finalgate_certifies_l3_rollback_receipt() -> None:
    result = _certify(_l3_success_receipt(), rollback_receipt=_l3_rollback_receipt())

    assert result.decision is LowRiskFinalGateDecision.CERTIFIED_ROLLBACK_SUCCESS
    assert result.certificate.rollback_receipt_id == "l3_rollback_1"


def test_finalgate_rejects_unsafe_receipt_raw_prompt_response_reasoning_or_key() -> None:
    receipt = _l2_success_receipt().model_dump(mode="python")
    receipt.update({"raw_prompt": "no", "raw_response": "no", "reasoning": "hidden", "api_key": "gsk_" + "abcdefghijklmnopqrstuvwxyz"})

    result = _certify(receipt)

    assert result.decision is LowRiskFinalGateDecision.REJECTED_UNSAFE_RECEIPT


def test_finalgate_rejects_secret_or_bearer_payload() -> None:
    receipt = _l2_success_receipt().model_dump(mode="python")
    receipt["safe_summary"] = "Bearer " + "abcdefghijklmnop1234567890"

    result = _certify(receipt)

    assert result.decision is LowRiskFinalGateDecision.REJECTED_UNSAFE_RECEIPT


def test_finalgate_rejects_hidden_tool_or_organ_payload() -> None:
    receipt = _l2_success_receipt().model_dump(mode="python")
    receipt["tool_calls"] = [{"name": "browser"}]
    receipt["organ_execution"] = True

    result = _certify(receipt)

    assert result.decision is LowRiskFinalGateDecision.REJECTED_UNSAFE_RECEIPT


def test_finalgate_rejects_authority_expansion_payload() -> None:
    receipt = _l2_success_receipt().model_dump(mode="python")
    receipt["authority_expansion"] = {"new_scope": "all"}

    result = _certify(receipt)

    assert result.decision is LowRiskFinalGateDecision.REJECTED_UNSAFE_RECEIPT


def test_finalgate_rejects_provider_model_override_payload() -> None:
    receipt = _l2_success_receipt().model_dump(mode="python")
    receipt["provider_override"] = "other"
    receipt["model_override"] = "auto"

    result = _certify(receipt)

    assert result.decision is LowRiskFinalGateDecision.REJECTED_PROVIDER_MODEL_OVERRIDE


def test_finalgate_rejects_forbidden_external_surfaces() -> None:
    receipt = _l2_success_receipt().model_dump(mode="python")
    receipt["send_email"] = True
    receipt["browser_submit"] = True

    result = _certify(receipt)

    assert result.decision is LowRiskFinalGateDecision.REJECTED_FORBIDDEN_SURFACE


def test_finalgate_certificate_has_authority_effect_none() -> None:
    result = _certify(_l2_success_receipt())

    assert result.certificate.authority_effect == "none"


def test_finalgate_certificate_has_execution_effect_none() -> None:
    result = _certify(_l3_success_receipt())

    assert result.certificate.execution_effect == "none"


def test_finalgate_cannot_grant_authority() -> None:
    payload = _certify(_l2_success_receipt()).certificate.model_dump(mode="python")
    payload["can_grant_authority"] = True

    with pytest.raises(ValidationError):
        LowRiskFinalGateCertificate(**payload)


def test_finalgate_cannot_approve_future_execution() -> None:
    payload = _certify(_l2_success_receipt()).certificate.model_dump(mode="python")
    payload["can_approve_future_execution"] = True

    with pytest.raises(ValidationError):
        LowRiskFinalGateCertificate(**payload)


def test_finalgate_cannot_create_delegated_lane() -> None:
    payload = _certify(_l2_success_receipt()).certificate.model_dump(mode="python")
    payload["can_create_delegated_lane"] = True

    with pytest.raises(ValidationError):
        LowRiskFinalGateCertificate(**payload)


def test_finalgate_cannot_execute() -> None:
    payload = _certify(_l2_success_receipt()).model_dump(mode="python")
    payload["can_execute"] = True

    with pytest.raises(ValidationError):
        LowRiskFinalGateResult(**payload)


def test_finalgate_certificate_hash_is_deterministic() -> None:
    first = _certify(_l3_success_receipt())
    second = _certify(_l3_success_receipt())

    assert first.certificate.certificate_hash == second.certificate.certificate_hash
    assert first.certificate.certificate_id == second.certificate.certificate_id


def test_finalgate_rendering_is_data_not_instruction() -> None:
    certificate = _certify(_l2_success_receipt()).certificate

    rendered = render_low_risk_finalgate_certificate_as_untrusted_context(certificate)

    assert "not instructions" in rendered
    assert "not Root Authority" in rendered
    assert "not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_finalgate_does_not_change_agent_runtime_default_behavior() -> None:
    runtime = AgentRuntime()

    assert "organ_execution_config" in signature(AgentRuntime).parameters
    assert runtime._organ_execution_config.enabled is False
    assert runtime._organ_execution_config.mode is OrganRuntimeExecutionMode.DISABLED


def test_finalgate_runtime_wiring_is_explicit_opt_in_only() -> None:
    runtime = AgentRuntime()

    assert runtime._organ_execution_config.enabled is False
