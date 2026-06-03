from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    DesktopDecisionFrameSlice,
    DesktopWorkspaceAuthority,
    DesktopWorkspaceKillSwitch,
    DesktopWorkspaceL6FinalGate,
    DesktopWorkspaceL6Receipt,
    WorkspaceContextCard,
    WorkspaceOperationAdapter,
    WorkspaceOperationBudget,
)


REQUIRED_BINDING_REFS = [
    "jarvis_sidecar_rpc_registry",
    "openjarvis_budget_timeout_discipline",
    "openclaw_action_kernel_preview",
    "hermes_context_compression",
    "sentinel_p6r_decision_frame",
]


def workspace_authority(tmp_path, *, operations: list[str] | None = None) -> DesktopWorkspaceAuthority:
    return DesktopWorkspaceAuthority(
        mission_id="mission_desktop_l6",
        root_authority_id="root_desktop_workspace",
        workspace_root=str(tmp_path),
        allowed_operations=operations or ["list_dir", "read_file", "write_file", "create_folder"],
        source_binding_refs=REQUIRED_BINDING_REFS,
        policy_hash="desktop_workspace_policy_v1",
        expires_at=datetime.now(UTC) + timedelta(minutes=30),
        evidence_refs=["p6s_agentlab_power_binding", "p6p_desktop_workspace_l6"],
    )


def test_workspace_authority_requires_agentlab_binding_and_scoped_root(tmp_path):
    authority = workspace_authority(tmp_path)

    assert authority.workspace_root == str(tmp_path.resolve())
    assert "jarvis_sidecar_rpc_registry" in authority.source_binding_refs
    assert authority.authority_expansion is False

    with pytest.raises(ValueError, match="AgentLab source binding"):
        DesktopWorkspaceAuthority(
            mission_id="mission_desktop_l6",
            root_authority_id="root",
            workspace_root=str(tmp_path),
            allowed_operations=["read_file"],
            source_binding_refs=["sentinel_only"],
            policy_hash="policy",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
            evidence_refs=["fixture"],
        )


def test_workspace_l6_file_ops_emit_path_proofs_receipts_and_rollback(tmp_path):
    adapter = WorkspaceOperationAdapter(authority=workspace_authority(tmp_path), budget=WorkspaceOperationBudget())

    created = adapter.create_folder("reports")
    written = adapter.write_file("reports/out.txt", "hello world")
    read = adapter.read_file("reports/out.txt")
    listed = adapter.list_dir("reports")

    assert (tmp_path / "reports" / "out.txt").read_text(encoding="utf-8") == "hello world"
    assert created.receipt.action == "desktop_workspace_create_folder_l6"
    assert written.receipt.action == "desktop_workspace_write_file_l6"
    assert read.raw_content == "hello world"
    assert "content" not in read.receipt.output_summary
    assert read.receipt.output_summary["content_hash"] == read.content_hash
    assert listed.receipt.output_summary["entries"] == ["out.txt"]
    assert written.receipt.path_containment_proof_ref.startswith("pathproof_")
    assert written.receipt.path_containment_proof_hash
    assert written.receipt.workspace_root == str(tmp_path.resolve())
    assert written.receipt.rollback_ref is not None
    assert written.receipt.receipt_hash == written.receipt.expected_hash()


def test_workspace_l6_rejects_path_escape_and_disallowed_operations(tmp_path):
    adapter = WorkspaceOperationAdapter(
        authority=workspace_authority(tmp_path, operations=["read_file"]),
        budget=WorkspaceOperationBudget(),
    )
    outside = tmp_path.parent / "outside.txt"

    with pytest.raises(ValueError, match="operation not allowed"):
        adapter.write_file("report.md", "blocked")
    with pytest.raises(ValueError, match="workspace escape"):
        adapter.read_file("../outside.txt")
    with pytest.raises(ValueError, match="workspace escape"):
        adapter.read_file(str(outside))


def test_workspace_context_card_is_compact_and_keeps_raw_content_out_of_frame(tmp_path):
    adapter = WorkspaceOperationAdapter(authority=workspace_authority(tmp_path), budget=WorkspaceOperationBudget())
    written = adapter.write_file("reports/secret.txt", "password=hunter2\n" * 20)
    read = adapter.read_file("reports/secret.txt")

    card = WorkspaceContextCard.from_receipts(
        mission_id="mission_desktop_l6",
        receipts=[written.receipt, read.receipt],
    )

    rendered = str(card.model_dump())
    assert card.raw_file_contents_included is False
    assert card.raw_workspace_tree_included is False
    assert card.receipt_refs == sorted([written.receipt.id, read.receipt.id])
    assert "reports/secret.txt" in card.changed_paths
    assert "hunter2" not in rendered
    assert "password=" not in rendered


def test_desktop_decision_frame_slice_exposes_only_workspace_tools(tmp_path):
    adapter = WorkspaceOperationAdapter(authority=workspace_authority(tmp_path), budget=WorkspaceOperationBudget())
    written = adapter.write_file("reports/out.txt", "signal")
    card = WorkspaceContextCard.from_receipts(mission_id="mission_desktop_l6", receipts=[written.receipt])

    frame_slice = DesktopDecisionFrameSlice.from_context_card(authority=adapter.authority, context_card=card)

    assert frame_slice.selected_tool_surface == [
        "create_folder",
        "list_dir",
        "read_file",
        "rollback_workspace_change",
        "write_file",
    ]
    assert frame_slice.authority_card["authority_expansion"] is False
    assert "shell" not in str(frame_slice.model_dump())
    assert "screenshot" not in str(frame_slice.model_dump())
    assert "clipboard" not in str(frame_slice.model_dump())


def test_finalgate_rejects_missing_rollback_missing_path_proof_and_authority_expansion(tmp_path):
    adapter = WorkspaceOperationAdapter(authority=workspace_authority(tmp_path), budget=WorkspaceOperationBudget())
    good = adapter.write_file("reports/out.txt", "signal").receipt

    finalgate = DesktopWorkspaceL6FinalGate()
    assert finalgate.verify(good).passed is True

    missing_rollback = good.model_copy(update={"rollback_ref": None})
    missing_path_proof = good.model_copy(update={"path_containment_proof_ref": ""})
    forged_path_proof_hash = good.model_copy(update={"path_containment_proof_hash": "forged"})
    expanded = good.model_copy(update={"authority_expansion": True})
    tampered_cost = good.model_copy(update={"cost_trace": good.cost_trace.model_copy(update={"bytes_written": 999})})

    assert finalgate.verify(missing_rollback).passed is False
    assert "rollback ref missing" in finalgate.verify(missing_rollback).failures
    assert finalgate.verify(missing_path_proof).passed is False
    assert "path containment proof missing" in finalgate.verify(missing_path_proof).failures
    assert finalgate.verify(forged_path_proof_hash).passed is False
    assert "path containment proof hash mismatch" in finalgate.verify(forged_path_proof_hash).failures
    assert finalgate.verify(expanded).passed is False
    assert "authority expansion detected" in finalgate.verify(expanded).failures
    assert finalgate.verify(tampered_cost).passed is False
    assert "receipt hash mismatch" in finalgate.verify(tampered_cost).failures


def test_kill_switch_blocks_workspace_mutation(tmp_path):
    kill_switch = DesktopWorkspaceKillSwitch(mission_id="mission_desktop_l6").trigger(reason="operator stop")
    adapter = WorkspaceOperationAdapter(
        authority=workspace_authority(tmp_path),
        budget=WorkspaceOperationBudget(),
        kill_switch=kill_switch,
    )

    with pytest.raises(ValueError, match="kill switch"):
        adapter.write_file("reports/out.txt", "blocked")


def test_workspace_budget_enforces_operation_count_and_byte_limits(tmp_path):
    adapter = WorkspaceOperationAdapter(
        authority=workspace_authority(tmp_path),
        budget=WorkspaceOperationBudget(max_operations=1, max_read_bytes=5, max_write_bytes=5),
    )

    adapter.create_folder("reports")
    with pytest.raises(ValueError, match="operation budget exceeded"):
        adapter.list_dir(".")

    fresh = WorkspaceOperationAdapter(
        authority=workspace_authority(tmp_path),
        budget=WorkspaceOperationBudget(max_operations=10, max_read_bytes=5, max_write_bytes=5),
    )
    with pytest.raises(ValueError, match="write byte budget exceeded"):
        fresh.write_file("reports/big.txt", "too many bytes")

    (tmp_path / "reports" / "big-read.txt").write_text("too many bytes", encoding="utf-8")
    with pytest.raises(ValueError, match="read byte budget exceeded"):
        fresh.read_file("reports/big-read.txt")


def test_workspace_l6_receipt_rejects_host_control_surfaces(tmp_path):
    with pytest.raises(ValueError, match="not allowed in Desktop Workspace L6"):
        DesktopWorkspaceL6Receipt(
            mission_id="mission_desktop_l6",
            action="desktop_workspace_write_file_l6",
            relative_path="reports/out.txt",
            resolved_path=str(tmp_path / "reports" / "out.txt"),
            output_summary={"bytes": 5},
            authority_refs=["root"],
            evidence_refs=["fixture"],
            trace_refs=["trace"],
            workspace_root=str(tmp_path),
            path_containment_proof_ref="pathproof_1",
            rollback_ref="rollback_1",
            live_host_control_enabled=True,
        )


def test_workspace_l6_receipt_rejects_forged_outside_root_proof(tmp_path):
    with pytest.raises(ValueError, match="outside workspace root"):
        DesktopWorkspaceL6Receipt(
            mission_id="mission_desktop_l6",
            action="desktop_workspace_read_file_l6",
            relative_path="../escape.txt",
            resolved_path=str(tmp_path.parent / "escape.txt"),
            output_summary={"bytes": 1},
            authority_refs=["root"],
            evidence_refs=["fixture"],
            trace_refs=["trace"],
            workspace_root=str(tmp_path),
            path_containment_proof_ref="pathproof_forged",
        )
