from __future__ import annotations

import hashlib
from pathlib import Path

from sentinel.operator.authority_issuer import MissionAuthorityApprovalScope, MissionAuthorityPolicy
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequestState
from sentinel.operator.models import MissionAuthoritySummary, MissionDraft, OperatorMissionStatus
from sentinel.operator.power_skill_registry import build_default_power_skill_registry
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.unified_execution_dispatcher import load_product_action_kernel_artifact
from sentinel.operator.unified_execution_dispatcher import DispatchStatus
from sentinel.operator.workspace_patch_replay import WorkspacePatchReplayView


def test_runtimehost_registers_product_action_kernel_adapter_for_workspace_patch(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    assert "product_action_kernel_adapter" in host.adapter_registry.adapter_ids()

    connection = host.connection_registry.get("workspace_patch")
    assert connection.adapter_id == "product_action_kernel_adapter"
    assert connection.production_reachable is True
    assert connection.supported_operations == ("apply_patch",)

    skill = build_default_power_skill_registry(runtime_connection_registry=host.connection_registry).get("workspace_patch")
    assert skill.product_reachable is True
    assert skill.adapter_id == "product_action_kernel_adapter"
    assert skill.runtime_connection_id == "workspace_patch"
    assert skill.can_execute is False


def test_workspace_patch_product_dispatch_executes_through_runtimehost_action_kernel_adapter(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace, readme = _workspace(tmp_path)
    before_hash = _sha256_file(readme)
    mission = host.lifecycle.create_mission(
        session_id="session_pack7",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(workspace),
        policy=_policy(workspace),
        capability_id="workspace_patch",
        operation="apply_patch",
        parameters={
            "target_path": "README.md",
            "expected_base_hash": before_hash,
            "old_text": "TODO: replace me\n",
            "new_text": "Sentinel product dispatch patch worked.\n",
        },
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack7_fake",
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.COMPLETED
    assert result.dispatch_result.adapter_id == "product_action_kernel_adapter"
    assert host.kernel.store.load_record(mission.record.mission_id).status is OperatorMissionStatus.COMPLETED
    state = host.lifecycle.derive_request_state(mission.record.mission_id, mission.execution_request.request_id)
    assert state.state is MissionExecutionRequestState.COMPLETED
    assert readme.read_text(encoding="utf-8") == "# Fixture\n\nSentinel product dispatch patch worked.\n"

    product_receipt = _product_receipt(host, mission.record.mission_id, result.dispatch_result.receipt_refs[0])
    assert product_receipt["skill_id"] == "workspace_patch"
    assert product_receipt["backend_id"] == "workspace_patch_skill"
    assert product_receipt["authority_decision"] == "allowed"
    assert product_receipt["execution_status"] == "completed"
    assert product_receipt["material_action"] is True
    assert product_receipt["replay_behavior"] == "no_reexecute_on_replay"
    assert product_receipt["can_execute"] is False

    workspace_receipts = list(
        (host.kernel.store.mission_dir(mission.record.mission_id) / "workspace_patch" / "receipts").glob("*.json")
    )
    assert workspace_receipts, "workspace patch runtime receipt missing"
    replay = WorkspacePatchReplayView.from_store(
        host.kernel.store,
        mission_id=mission.record.mission_id,
        workspace_root=workspace,
    )
    assert replay.patch_applications_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.evidence_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def test_workspace_patch_requires_explicit_authority(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace, readme = _workspace(tmp_path)
    before_hash = _sha256_file(readme)
    mission = host.lifecycle.create_mission(
        session_id="session_pack7_no_auth",
        draft=_draft(),
        authority_summary=_summary(allowed_actions=["read_file_segment"]),
        approval_scope=_approval_scope(workspace, allowed_tools=["read_only_research"], allowed_actions=["read_file_segment"]),
        policy=_policy(workspace, allowed_tools=["read_only_research"], allowed_actions=["read_file_segment"]),
        capability_id="workspace_patch",
        operation="apply_patch",
        parameters={
            "target_path": "README.md",
            "expected_base_hash": before_hash,
            "old_text": "TODO: replace me\n",
            "new_text": "should not land\n",
        },
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack7_fake",
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "authority_incompatible_dispatch"
    assert "should not land" not in readme.read_text(encoding="utf-8")


def test_workspace_escape_blocks_without_patch_application(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace, readme = _workspace(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    mission = host.lifecycle.create_mission(
        session_id="session_pack7_escape",
        draft=_draft(),
        authority_summary=_summary(),
        approval_scope=_approval_scope(workspace),
        policy=_policy(workspace),
        capability_id="workspace_patch",
        operation="apply_patch",
        parameters={
            "target_path": str(outside),
            "expected_base_hash": _sha256_file(outside),
            "old_text": "outside\n",
            "new_text": "escaped\n",
        },
        workspace_ref=f"workspace:{workspace}",
        model_contract_ref="model_contract:pack7_fake",
    )

    result = host.pump_daemon_once(mission.record.mission_id)

    assert result.dispatch_result is not None
    assert result.dispatch_result.status is DispatchStatus.BLOCKED
    assert result.dispatch_result.blocked_reason == "workspace_patch_target_not_authorized"
    assert outside.read_text(encoding="utf-8") == "outside\n"
    assert "TODO: replace me" in readme.read_text(encoding="utf-8")


def test_high_risk_surfaces_remain_non_product_dispatchable(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")
    registry = build_default_power_skill_registry(runtime_connection_registry=host.connection_registry)

    browser = registry.get("real_browser_control")
    assert browser.product_reachable is True
    assert browser.dispatch_enabled is False
    assert browser.can_execute is False

    for skill_id in ("external_api", "account_authority", "financial_authority", "payment_authority"):
        binding = registry.get(skill_id)
        assert binding.product_reachable is False
        assert binding.dispatch_enabled is False
        assert binding.can_execute is False


def _draft() -> MissionDraft:
    return MissionDraft(
        title="RuntimeHost workspace patch",
        objective="Patch one file inside the granted workspace.",
        expected_artifacts=["product action receipt", "workspace patch receipt"],
    )


def _summary(*, allowed_actions: list[str] | None = None) -> MissionAuthoritySummary:
    return MissionAuthoritySummary(
        mission_id="pending",
        allowed_actions=allowed_actions or ["workspace_patch.apply_patch"],
        forbidden_actions=["payment", "credential_access", "contact_supplier", "shell"],
        summary="Hash-anchored workspace patch authority only.",
    )


def _approval_scope(
    workspace: Path,
    *,
    allowed_tools: list[str] | None = None,
    allowed_actions: list[str] | None = None,
) -> MissionAuthorityApprovalScope:
    return MissionAuthorityApprovalScope(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=allowed_tools or ["workspace_patch"],
        allowed_actions=allowed_actions or ["workspace_patch.apply_patch"],
        forbidden_actions=["payment", "credential_access", "contact_supplier", "shell"],
        allowed_paths=[str(workspace)],
        max_duration_minutes=5,
        max_actions=3,
        max_cost_usd=0.0,
    )


def _policy(
    workspace: Path,
    *,
    allowed_tools: list[str] | None = None,
    allowed_actions: list[str] | None = None,
) -> MissionAuthorityPolicy:
    return MissionAuthorityPolicy(
        user_id="operator_user",
        allowed_systems=["local_workspace"],
        allowed_tools=allowed_tools or ["workspace_patch"],
        allowed_actions=allowed_actions or ["workspace_patch.apply_patch"],
        forbidden_actions=["payment", "credential_access", "contact_supplier", "shell"],
        allowed_paths=[str(workspace)],
        max_duration_minutes=5,
        max_actions=3,
        max_cost_usd=0.0,
    )


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "workspace"
    root.mkdir()
    readme = root / "README.md"
    readme.write_text("# Fixture\n\nTODO: replace me\n", encoding="utf-8")
    return root, readme


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    receipt = load_product_action_kernel_artifact(host.kernel, mission_id, "receipts", receipt_ref)
    assert receipt is not None
    return receipt
