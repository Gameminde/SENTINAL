from __future__ import annotations

from datetime import UTC, datetime, timedelta
from inspect import signature
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sentinel.agent.llm import DelegatedActionLevel
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
    L2LocalArtifactResult,
    L2LocalArtifactRollbackReceipt,
    render_l2_execution_receipt_as_untrusted_context,
)
from sentinel.agent.organs import local_artifact_executor as l2_module
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionMode
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.runtime import AgentRuntime


NOW = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)


def _contract(tmp_path: Path, **updates: Any) -> L2ExecutorContract:
    base = {
        "mission_id": "mission_l2",
        "lane_id": "lane_l2",
        "gate_result_id": "gate_result_l2",
        "allowed_workspace_root": str(tmp_path / "generated_root"),
        "allowed_artifact_subdir": "artifacts",
        "max_artifact_bytes": 4096,
        "allow_overwrite": False,
        "allow_rollback_cleanup": True,
        "receipt_required": True,
        "tombstone_required_for_cleanup": True,
        "finalgate_posture_required": True,
        "execution_enabled_for_l2": True,
        "contract_version": "l2-local-artifact-v0",
    }
    base.update(updates)
    return L2ExecutorContract(**base)


def _lane(**updates: Any) -> DelegatedActionLane:
    base = {
        "lane_id": "lane_l2",
        "mission_id": "mission_l2",
        "source_candidate_id": "candidate_l2",
        "organ_kind": OrganProposalKind.FILE_OPERATION,
        "action_level": DelegatedActionLevel.L2,
        "allowed_substeps": [
            "create_draft_file",
            "create_local_artifact",
            "create_generated_report",
            "create_metadata_artifact",
        ],
        "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit"],
        "authority_class": DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        "risk_class": DelegatedActionRiskClass.LOW,
        "budget_limit": {"remaining_action_count": 2, "remaining_artifact_bytes": 4096},
        "credential_scope": "none",
        "evidence_refs": ["ev_l2"],
        "receipt_refs": ["receipt_gate_l2"],
        "receipt_contract": DelegatedActionReceiptRequirement(
            required_receipt_fields=["artifact_hash", "path_metadata", "lane_id", "gate_result_id"],
            receipt_refs=["receipt_gate_l2"],
            receipt_contract_hash="receipt_contract_hash_l2",
        ),
        "revocation_rule": "lane can be revoked before local artifact execution",
        "rollback_posture": "delete generated artifact with tombstone",
        "user_review_requirement": "not_required_for_l2_local_artifact",
        "FinalGate_checks": ["local_only", "artifact_hash_present", "no_external_mutation"],
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=30),
        "ttl_seconds": 1800,
    }
    base.update(updates)
    return DelegatedActionLane(**base)


def _request(
    tmp_path: Path,
    *,
    target_relative_path: str = "report.md",
    content: str = "safe generated report",
    contract: L2ExecutorContract | None | object = None,
    delegated_lane: DelegatedActionLane | None = None,
    **updates: Any,
) -> L2LocalArtifactRequest:
    if contract is None:
        contract = _contract(tmp_path)
    base = {
        "mission_id": "mission_l2",
        "source_candidate_id": "candidate_l2",
        "action_kind": L2LocalArtifactActionKind.CREATE_GENERATED_REPORT,
        "target_relative_path": target_relative_path,
        "content": content,
        "metadata": {"title": "safe report"},
        "contract": contract,
        "delegated_lane": delegated_lane or _lane(),
        "budget_estimate": {"artifact_bytes": len(content.encode("utf-8")), "action_count": 1},
        "current_time": NOW,
    }
    base.update(updates)
    return L2LocalArtifactRequest(**base)


def _execute(tmp_path: Path, **updates: Any) -> L2LocalArtifactResult:
    return L2LocalArtifactExecutor().execute(_request(tmp_path, **updates))


def test_l2_creates_artifact_only_in_allowed_workspace(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="reports/mission.md", content="# Mission\nsafe local artifact")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.CREATED
    assert result.artifact_hash is not None
    assert result.artifact_path is not None
    artifact_path = Path(result.artifact_path)
    artifact_path.resolve().relative_to((tmp_path / "generated_root" / "artifacts").resolve())
    assert artifact_path.read_text(encoding="utf-8") == "# Mission\nsafe local artifact"
    assert result.receipt.execution_effect == "local_artifact_created"


def test_l2_cannot_write_outside_workspace(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="../escape.md")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert result.artifact_path is None
    assert result.receipt.rejection_reason is not None


def test_l2_blocks_parent_traversal(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="reports/../../escape.md")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "parent_traversal" in result.receipt.rejection_reason


def test_l2_blocks_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "generated_root"
    subdir = root / "artifacts"
    outside = tmp_path / "outside"
    subdir.mkdir(parents=True)
    outside.mkdir()
    link = subdir / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment.")

    result = _execute(tmp_path, target_relative_path="link/escape.md")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert not (outside / "escape.md").exists()


def test_l2_blocks_symlink_swap_after_validation_before_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "generated_root"
    subdir = root / "artifacts"
    outside = tmp_path / "outside"
    (subdir / "race").mkdir(parents=True)
    outside.mkdir()
    try:
        probe = subdir / "probe"
        probe.symlink_to(outside, target_is_directory=True)
        probe.unlink()
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment.")

    original_resolve = l2_module._resolve_target_path
    calls = {"count": 0}

    def racing_resolve(request: L2LocalArtifactRequest, contract: L2ExecutorContract):
        calls["count"] += 1
        if calls["count"] == 3:
            race_dir = subdir / "race"
            race_dir.rmdir()
            race_dir.symlink_to(outside, target_is_directory=True)
        return original_resolve(request, contract)

    monkeypatch.setattr(l2_module, "_resolve_target_path", racing_resolve)

    result = _execute(tmp_path, target_relative_path="race/escape.md", content="should not escape")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "path_changed_before_mutation" in result.receipt.rejection_reason
    assert not (outside / "escape.md").exists()


def test_l2_blocks_absolute_sensitive_path(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path=str(tmp_path / ".env"))

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "absolute_path" in result.receipt.rejection_reason


def test_l2_blocks_env_secret_paths(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="secrets/.env")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "sensitive_path" in result.receipt.rejection_reason


def test_l2_cannot_send_network_or_call_api(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"send_email": True, "network_call": "https://example.invalid"})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert result.receipt.execution_effect == "none"


def test_l2_cannot_use_credentials(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"credential": "credential_ref_should_not_be_used"})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_cannot_run_shell_terminal_or_process(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"shell": "echo no", "terminal": True, "process": True})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_receipt_contains_path_hash_metadata_only(tmp_path: Path) -> None:
    content = "receipt-safe content that must not be stored raw"
    result = _execute(tmp_path, target_relative_path="receipt.md", content=content)
    receipt_json = result.receipt.model_dump_json()

    assert result.receipt.artifact_hash is not None
    assert result.receipt.path_metadata["relative_path"] == "receipt.md"
    assert content not in receipt_json
    assert "raw_prompt" not in receipt_json
    assert "raw_response" not in receipt_json
    assert "reasoning" not in receipt_json


def test_l2_blocked_attempt_creates_receipt(tmp_path: Path) -> None:
    result = L2LocalArtifactExecutor().execute(
        _request(tmp_path, contract=object(), target_relative_path="blocked.md")
    )

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert result.receipt is not None
    assert result.receipt.execution_effect == "none"


def test_l2_rejects_raw_prompt_response_reasoning_or_key(tmp_path: Path) -> None:
    result = _execute(
        tmp_path,
        metadata={
            "raw_prompt": "do not store",
            "raw_response": "do not store",
            "reasoning": "hidden",
            "api_key": "gsk_" + "abcdefghijklmnopqrstuvwxyz",
        },
    )

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_rejects_secret_or_bearer_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, content="Bearer " + "abcdefghijklmnop1234567890")

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_rejects_hidden_tool_or_organ_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"tool_calls": [{"name": "browser"}], "organ_execution": True})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_rejects_authority_expansion_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"authority_expansion": {"new_scope": "all_files"}})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_rejects_provider_model_override_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"provider_override": "other", "model_override": "auto"})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_requires_executor_contract(tmp_path: Path) -> None:
    result = L2LocalArtifactExecutor().execute(
        {
            "mission_id": "mission_l2",
            "source_candidate_id": "candidate_l2",
            "action_kind": L2LocalArtifactActionKind.CREATE_LOCAL_ARTIFACT,
            "target_relative_path": "no-contract.md",
            "content": "safe",
            "metadata": {},
            "contract": None,
            "delegated_lane": _lane(),
            "budget_estimate": {},
            "current_time": NOW,
        }
    )

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "missing_executor_contract" in result.receipt.rejection_reason


def test_l2_requires_execution_enabled_for_l2_contract(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, execution_enabled_for_l2=False))

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "execution_not_enabled_for_l2" in result.receipt.rejection_reason


def test_l2_requires_matching_mission_id(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, mission_id="other_mission"))

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "mission_id_mismatch" in result.receipt.rejection_reason


def test_l2_requires_lane_id_and_gate_result_id(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, lane_id="", gate_result_id=""))

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "lane_id_missing" in result.receipt.rejection_reason
    assert "gate_result_id_missing" in result.receipt.rejection_reason


def test_l2_cannot_execute_if_gate_denied_or_lane_invalid(tmp_path: Path) -> None:
    invalid_lane = _lane(organ_kind=OrganProposalKind.API)
    result = _execute(tmp_path, delegated_lane=invalid_lane)

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "lane_organ_kind_incompatible" in result.receipt.rejection_reason


def test_l2_cannot_execute_if_lane_expired(tmp_path: Path) -> None:
    expired_lane = _lane(expires_at=NOW - timedelta(seconds=1))
    result = _execute(tmp_path, delegated_lane=expired_lane)

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED
    assert "lane_expired" in result.receipt.rejection_reason


def test_l2_cannot_create_delegated_lane(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"delegated_lane_creation": True})

    assert result.attempt_status is L2LocalArtifactAttemptStatus.BLOCKED


def test_l2_cannot_expand_authority(tmp_path: Path) -> None:
    payload = _execute(tmp_path).model_dump(mode="python")
    payload["can_grant_authority"] = True

    with pytest.raises(ValidationError):
        L2LocalArtifactResult(**payload)


def test_l2_rollback_deletes_generated_artifact_when_allowed(tmp_path: Path) -> None:
    executor = L2LocalArtifactExecutor()
    result = executor.execute(_request(tmp_path, target_relative_path="rollback.md"))

    rollback = executor.rollback(result, cleanup_reason="test cleanup")

    assert isinstance(rollback, L2LocalArtifactRollbackReceipt)
    assert rollback.attempt_status is L2LocalArtifactAttemptStatus.ROLLBACK_COMPLETED
    assert result.artifact_path is not None
    assert not Path(result.artifact_path).exists()


def test_l2_rollback_preserves_tombstone_audit_metadata(tmp_path: Path) -> None:
    executor = L2LocalArtifactExecutor()
    result = executor.execute(_request(tmp_path, target_relative_path="rollback-audit.md"))

    rollback = executor.rollback(result, cleanup_reason="audit cleanup")

    assert rollback.tombstone is not None
    tombstone_path = Path(rollback.tombstone.tombstone_path)
    assert tombstone_path.exists()
    tombstone_json = tombstone_path.read_text(encoding="utf-8")
    assert result.artifact_hash in tombstone_json
    assert "lane_l2" in tombstone_json
    assert "audit cleanup" in tombstone_json


def test_l2_rollback_unavailable_when_tombstone_cannot_be_written(tmp_path: Path) -> None:
    executor = L2LocalArtifactExecutor()
    result = executor.execute(_request(tmp_path, target_relative_path="rollback-blocked.md"))
    tombstone_dir_path = tmp_path / "generated_root" / "artifacts" / ".sentinel_tombstones"
    tombstone_dir_path.write_text("not a directory", encoding="utf-8")

    rollback = executor.rollback(result, cleanup_reason="cannot tombstone")

    assert rollback.attempt_status is L2LocalArtifactAttemptStatus.ROLLBACK_UNAVAILABLE
    assert result.artifact_path is not None
    assert Path(result.artifact_path).exists()


def test_l2_render_receipt_is_data_not_instruction(tmp_path: Path) -> None:
    result = _execute(tmp_path)

    rendered = render_l2_execution_receipt_as_untrusted_context(result.receipt)

    assert "not instructions" in rendered
    assert "not authority" in rendered
    assert "not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_l2_does_not_change_agent_runtime_default_behavior() -> None:
    runtime = AgentRuntime()

    assert "organ_execution_config" in signature(AgentRuntime).parameters
    assert runtime._organ_execution_config.enabled is False
    assert runtime._organ_execution_config.mode is OrganRuntimeExecutionMode.DISABLED


def test_l2_runtime_wiring_is_explicit_opt_in_only() -> None:
    runtime_source = Path(AgentRuntime.__module__.replace(".", "/"))
    assert runtime_source.name == "runtime"

    runtime = AgentRuntime()
    assert runtime._organ_execution_config.enabled is False
