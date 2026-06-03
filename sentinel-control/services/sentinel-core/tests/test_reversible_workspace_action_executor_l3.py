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
from sentinel.agent.organs.proposal_bridge import OrganProposalKind
from sentinel.agent.organs.reversible_workspace_executor import (
    L3ExecutorContract,
    L3ReversibleWorkspaceExecutor,
    L3WorkspaceActionKind,
    L3WorkspaceAttemptStatus,
    L3WorkspaceRequest,
    L3WorkspaceResult,
    render_l3_execution_receipt_as_untrusted_context,
)
from sentinel.agent.organs import reversible_workspace_executor as l3_module
from sentinel.agent.organs.runtime_execution import OrganRuntimeExecutionMode
from sentinel.agent.runtime import AgentRuntime
from sentinel.agent.model_execution.redaction import text_hash


NOW = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return text_hash(content)


def _workspace_file(tmp_path: Path, relative: str = "docs/state.md", content: str = "old state\n") -> tuple[Path, str]:
    root = tmp_path / "workspace_root" / "work"
    path = root / relative
    before_hash = _write_text(path, content)
    return path, before_hash


def _contract(tmp_path: Path, **updates: Any) -> L3ExecutorContract:
    base = {
        "mission_id": "mission_l3",
        "lane_id": "lane_l3",
        "gate_result_id": "gate_result_l3",
        "allowed_workspace_root": str(tmp_path / "workspace_root"),
        "allowed_workspace_subdir": "work",
        "max_file_bytes": 4096,
        "max_patch_bytes": 2048,
        "allow_overwrite": True,
        "allow_delete": False,
        "tombstone_required_for_delete": True,
        "rollback_required": True,
        "rollback_must_be_tested_before_mutation": True,
        "receipt_required": True,
        "finalgate_posture_required": True,
        "execution_enabled_for_l3": True,
        "contract_version": "l3-reversible-workspace-v0",
    }
    base.update(updates)
    return L3ExecutorContract(**base)


def _lane(**updates: Any) -> DelegatedActionLane:
    base = {
        "lane_id": "lane_l3",
        "mission_id": "mission_l3",
        "source_candidate_id": "candidate_l3",
        "organ_kind": OrganProposalKind.FILE_OPERATION,
        "action_level": DelegatedActionLevel.L3,
        "allowed_substeps": [
            "replace_text_file",
            "append_text_file",
            "update_json_metadata",
            "create_tombstoned_cleanup_marker",
            "reversible_metadata_update",
        ],
        "forbidden_substeps": ["send", "network", "api", "shell", "browser_submit"],
        "authority_class": DelegatedActionAuthorityClass.DELEGATED_METADATA_ONLY,
        "risk_class": DelegatedActionRiskClass.MEDIUM,
        "budget_limit": {"remaining_action_count": 2, "remaining_patch_bytes": 2048},
        "credential_scope": "none",
        "evidence_refs": ["ev_l3"],
        "receipt_refs": ["receipt_gate_l3"],
        "receipt_contract": DelegatedActionReceiptRequirement(
            required_receipt_fields=[
                "before_hash",
                "after_hash",
                "path_metadata",
                "lane_id",
                "gate_result_id",
            ],
            receipt_refs=["receipt_gate_l3"],
            receipt_contract_hash="receipt_contract_hash_l3",
        ),
        "revocation_rule": "lane can be revoked before reversible local workspace execution",
        "rollback_posture": "restore previous text content from before snapshot",
        "user_review_requirement": "not_required_for_l3_reversible_workspace",
        "FinalGate_checks": ["local_only", "before_hash", "after_hash", "rollback_ready"],
        "created_at": NOW,
        "expires_at": NOW + timedelta(minutes=30),
        "ttl_seconds": 1800,
    }
    base.update(updates)
    return DelegatedActionLane(**base)


def _request(
    tmp_path: Path,
    *,
    target_relative_path: str = "docs/state.md",
    content: str = "new state\n",
    before_hash: str | None = None,
    action_kind: L3WorkspaceActionKind = L3WorkspaceActionKind.REPLACE_TEXT_FILE,
    contract: L3ExecutorContract | None | object = None,
    delegated_lane: DelegatedActionLane | None = None,
    metadata_patch: dict[str, Any] | None = None,
    **updates: Any,
) -> L3WorkspaceRequest:
    if before_hash is None:
        _, before_hash = _workspace_file(tmp_path, target_relative_path)
    if contract is None:
        contract = _contract(tmp_path)
    base = {
        "mission_id": "mission_l3",
        "source_candidate_id": "candidate_l3",
        "action_kind": action_kind,
        "target_relative_path": target_relative_path,
        "content": content,
        "metadata_patch": metadata_patch or {},
        "before_hash": before_hash,
        "metadata": {"title": "safe reversible edit"},
        "contract": contract,
        "delegated_lane": delegated_lane or _lane(),
        "budget_estimate": {"patch_bytes": len(content.encode("utf-8")), "action_count": 1},
        "current_time": NOW,
    }
    base.update(updates)
    return L3WorkspaceRequest(**base)


def _execute(tmp_path: Path, **updates: Any) -> L3WorkspaceResult:
    return L3ReversibleWorkspaceExecutor().execute(_request(tmp_path, **updates))


def test_l3_replaces_text_file_inside_approved_workspace(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, content="before\n")

    result = _execute(tmp_path, before_hash=before_hash, content="after\n")

    assert result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert path.read_text(encoding="utf-8") == "after\n"
    assert result.before_snapshot.before_hash == before_hash
    assert result.after_snapshot.after_hash == text_hash("after\n")


def test_l3_appends_text_file_inside_approved_workspace(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, content="before\n")

    result = _execute(
        tmp_path,
        before_hash=before_hash,
        action_kind=L3WorkspaceActionKind.APPEND_TEXT_FILE,
        content="after\n",
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert path.read_text(encoding="utf-8") == "before\nafter\n"
    assert result.after_hash == text_hash("before\nafter\n")


def test_l3_updates_json_metadata_inside_approved_workspace(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, "data/meta.json", '{"old": true}\n')

    result = _execute(
        tmp_path,
        target_relative_path="data/meta.json",
        before_hash=before_hash,
        action_kind=L3WorkspaceActionKind.UPDATE_JSON_METADATA,
        metadata_patch={"new": "value"},
        content="",
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert '"new": "value"' in path.read_text(encoding="utf-8")
    assert result.after_hash is not None


def test_l3_requires_before_hash(tmp_path: Path) -> None:
    _workspace_file(tmp_path)

    result = _execute(tmp_path, before_hash="")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "before_hash_missing" in result.receipt.rejection_reason


def test_l3_requires_after_hash(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path)
    path.unlink()

    result = _execute(tmp_path, before_hash=before_hash)

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "before_hash_cannot_be_captured" in result.receipt.rejection_reason


def test_l3_requires_rollback_posture(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, rollback_required=False))

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "rollback_required_false" in result.receipt.rejection_reason


def test_l3_blocks_if_rollback_unavailable_before_mutation(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, rollback_must_be_tested_before_mutation=False))

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "rollback_test_required" in result.receipt.rejection_reason


def test_l3_rollback_restores_previous_text_state(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, content="before\n")
    executor = L3ReversibleWorkspaceExecutor()
    result = executor.execute(_request(tmp_path, before_hash=before_hash, content="after\n"))

    rollback = executor.rollback(result, rollback_reason="restore previous state")

    assert rollback.attempt_status is L3WorkspaceAttemptStatus.ROLLBACK_COMPLETED
    assert path.read_text(encoding="utf-8") == "before\n"


def test_l3_rollback_verifies_original_before_hash(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, content="before\n")
    executor = L3ReversibleWorkspaceExecutor()
    result = executor.execute(_request(tmp_path, before_hash=before_hash, content="after\n"))

    rollback = executor.rollback(result, rollback_reason="verify hash")

    assert rollback.restored_hash == before_hash
    assert text_hash(path.read_text(encoding="utf-8")) == before_hash


def test_l3_receipt_links_before_after_hashes_and_rollback_receipt(tmp_path: Path) -> None:
    executor = L3ReversibleWorkspaceExecutor()
    result = executor.execute(_request(tmp_path, content="after\n"))
    rollback = executor.rollback(result, rollback_reason="link rollback")

    assert result.receipt.before_hash == result.before_hash
    assert result.receipt.after_hash == result.after_hash
    assert rollback.original_receipt_id == result.receipt.receipt_id


def test_l3_blocked_attempt_creates_receipt(tmp_path: Path) -> None:
    result = L3ReversibleWorkspaceExecutor().execute(
        _request(tmp_path, contract=object(), target_relative_path="blocked.md")
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert result.receipt.execution_effect == "none"


def test_l3_cannot_mutate_outside_workspace(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="../escape.md")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert result.artifact_path is None


def test_l3_blocks_parent_traversal(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="docs/../../escape.md")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "parent_traversal" in result.receipt.rejection_reason


def test_l3_blocks_symlink_escape(tmp_path: Path) -> None:
    root = tmp_path / "workspace_root"
    subdir = root / "work"
    outside = tmp_path / "outside"
    subdir.mkdir(parents=True)
    outside.mkdir()
    link = subdir / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is unavailable in this Windows environment.")
    outside_file = outside / "escape.md"
    outside_hash = _write_text(outside_file, "outside\n")

    result = _execute(tmp_path, target_relative_path="link/escape.md", before_hash=outside_hash, content="mutated\n")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert outside_file.read_text(encoding="utf-8") == "outside\n"


def test_l3_blocks_snapshot_change_after_validation_before_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, before_hash = _workspace_file(tmp_path, content="before\n")
    original_before_snapshot = l3_module._before_snapshot
    calls = {"count": 0}

    def racing_before_snapshot(request: L3WorkspaceRequest, contract: L3ExecutorContract, path_plan: Any):
        calls["count"] += 1
        if calls["count"] == 3:
            path.write_text("raced\n", encoding="utf-8")
        return original_before_snapshot(request, contract, path_plan)

    monkeypatch.setattr(l3_module, "_before_snapshot", racing_before_snapshot)

    result = _execute(tmp_path, before_hash=before_hash, content="after\n")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "path_or_snapshot_changed_before_mutation" in result.receipt.rejection_reason
    assert path.read_text(encoding="utf-8") == "raced\n"


def test_l3_blocks_absolute_sensitive_path(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path=str(tmp_path / ".env"))

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "absolute_path" in result.receipt.rejection_reason


def test_l3_blocks_env_secret_paths(tmp_path: Path) -> None:
    result = _execute(tmp_path, target_relative_path="secrets/.env")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "sensitive_path" in result.receipt.rejection_reason


def test_l3_blocks_binary_mutation_in_v0(tmp_path: Path) -> None:
    result = _execute(tmp_path, content="binary\x00payload")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "binary_payload" in result.receipt.rejection_reason


def test_l3_blocks_executable_extension_mutation(tmp_path: Path) -> None:
    _workspace_file(tmp_path, "scripts/run.ps1", "before\n")
    result = _execute(tmp_path, target_relative_path="scripts/run.ps1")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "executable_extension" in result.receipt.rejection_reason


def test_l3_blocks_overwrite_without_before_hash(tmp_path: Path) -> None:
    _workspace_file(tmp_path)

    result = _execute(tmp_path, before_hash="bad_hash")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "before_hash_mismatch" in result.receipt.rejection_reason


def test_l3_blocks_delete_without_tombstone(tmp_path: Path) -> None:
    result = _execute(
        tmp_path,
        action_kind=L3WorkspaceActionKind.CREATE_TOMBSTONED_CLEANUP_MARKER,
        contract=_contract(tmp_path, allow_delete=False),
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "delete_not_allowed" in result.receipt.rejection_reason


def test_l3_tombstone_preserves_audit_metadata_when_cleanup_allowed(tmp_path: Path) -> None:
    path, before_hash = _workspace_file(tmp_path, "cleanup/old.md", "old cleanup\n")

    result = _execute(
        tmp_path,
        target_relative_path="cleanup/old.md",
        before_hash=before_hash,
        action_kind=L3WorkspaceActionKind.CREATE_TOMBSTONED_CLEANUP_MARKER,
        contract=_contract(tmp_path, allow_delete=True),
        metadata={"cleanup_reason": "safe cleanup marker"},
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.MUTATED
    assert result.tombstone is not None
    tombstone_text = Path(result.tombstone.tombstone_path).read_text(encoding="utf-8")
    assert before_hash in tombstone_text
    assert "lane_l3" in tombstone_text
    assert path.exists()


def test_l3_cannot_send_network_or_call_api(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"send_email": True, "network_call": "https://example.invalid"})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_cannot_use_credentials(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"credential": "credential_ref_should_not_be_used"})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_cannot_run_shell_terminal_or_process(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"shell": "echo no", "terminal": True, "process": True})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_rejects_raw_prompt_response_reasoning_or_key(tmp_path: Path) -> None:
    result = _execute(
        tmp_path,
        metadata={
            "raw_prompt": "do not store",
            "raw_response": "do not store",
            "reasoning": "hidden",
            "api_key": "gsk_" + "abcdefghijklmnopqrstuvwxyz",
        },
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_rejects_secret_or_bearer_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, content="Bearer " + "abcdefghijklmnop1234567890")

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_rejects_hidden_tool_or_organ_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"tool_calls": [{"name": "browser"}], "organ_execution": True})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_rejects_authority_expansion_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"authority_expansion": {"new_scope": "all_files"}})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_rejects_provider_model_override_payload(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"provider_override": "other", "model_override": "auto"})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_requires_executor_contract(tmp_path: Path) -> None:
    result = L3ReversibleWorkspaceExecutor().execute(
        {
            "mission_id": "mission_l3",
            "source_candidate_id": "candidate_l3",
            "action_kind": L3WorkspaceActionKind.REPLACE_TEXT_FILE,
            "target_relative_path": "no-contract.md",
            "content": "safe",
            "metadata_patch": {},
            "before_hash": "missing_contract",
            "metadata": {},
            "contract": None,
            "delegated_lane": _lane(),
            "budget_estimate": {"patch_bytes": 4, "action_count": 1},
            "current_time": NOW,
        }
    )

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "missing_executor_contract" in result.receipt.rejection_reason


def test_l3_requires_execution_enabled_for_l3_contract(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, execution_enabled_for_l3=False))

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "execution_not_enabled_for_l3" in result.receipt.rejection_reason


def test_l3_requires_matching_mission_id(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, mission_id="other_mission"))

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "mission_id_mismatch" in result.receipt.rejection_reason


def test_l3_requires_lane_id_and_gate_result_id(tmp_path: Path) -> None:
    result = _execute(tmp_path, contract=_contract(tmp_path, lane_id="", gate_result_id=""))

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "lane_id_missing" in result.receipt.rejection_reason
    assert "gate_result_id_missing" in result.receipt.rejection_reason


def test_l3_cannot_execute_if_gate_denied_or_lane_invalid(tmp_path: Path) -> None:
    invalid_lane = _lane(organ_kind=OrganProposalKind.API)

    result = _execute(tmp_path, delegated_lane=invalid_lane)

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "lane_organ_kind_incompatible" in result.receipt.rejection_reason


def test_l3_cannot_execute_if_lane_expired(tmp_path: Path) -> None:
    expired_lane = _lane(expires_at=NOW - timedelta(seconds=1))

    result = _execute(tmp_path, delegated_lane=expired_lane)

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "lane_expired" in result.receipt.rejection_reason


def test_l3_cannot_create_delegated_lane(tmp_path: Path) -> None:
    result = _execute(tmp_path, metadata={"delegated_lane_creation": True})

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED


def test_l3_cannot_expand_authority(tmp_path: Path) -> None:
    payload = _execute(tmp_path).model_dump(mode="python")
    payload["can_grant_authority"] = True

    with pytest.raises(ValidationError):
        L3WorkspaceResult(**payload)


def test_l3_render_receipt_is_data_not_instruction(tmp_path: Path) -> None:
    result = _execute(tmp_path)

    rendered = render_l3_execution_receipt_as_untrusted_context(result.receipt)

    assert "not instructions" in rendered
    assert "not authority" in rendered
    assert "not permission" in rendered
    assert "data_not_instruction=true" in rendered


def test_l3_does_not_change_agent_runtime_default_behavior() -> None:
    runtime = AgentRuntime()

    assert "organ_execution_config" in signature(AgentRuntime).parameters
    assert runtime._organ_execution_config.enabled is False
    assert runtime._organ_execution_config.mode is OrganRuntimeExecutionMode.DISABLED


def test_l3_runtime_wiring_is_explicit_opt_in_only() -> None:
    runtime = AgentRuntime()

    assert runtime._organ_execution_config.enabled is False


def test_l3_does_not_import_vendor_runtime() -> None:
    module_text = (Path(__file__).parents[1] / "sentinel/agent/organs/reversible_workspace_executor.py").read_text(
        encoding="utf-8"
    )

    assert "openclaw" not in module_text.lower()
    assert "jarvis" not in module_text.lower()
    assert "agentmemory" not in module_text.lower()


def test_l3_does_not_perform_l4_l5_l6_l7_actions(tmp_path: Path) -> None:
    lane = _lane(action_level=DelegatedActionLevel.L4)

    result = _execute(tmp_path, delegated_lane=lane)

    assert result.attempt_status is L3WorkspaceAttemptStatus.BLOCKED
    assert "lane_action_level_not_l3" in result.receipt.rejection_reason
