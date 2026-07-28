from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.operator.models import MissionAuthoritySummary, MissionDraft
from sentinel.operator.runtime_host import SentinelRuntimeHost
from sentinel.operator.store import _path_exists


def test_runtimehost_exposes_mission_workspace_product_body_frame(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs")

    frame = host.mission_workspace_entrypoint_frame()

    assert frame["entrypoint_id"] == "mission_workspace_runtime"
    assert frame["primary_role"] == "product_body"
    assert frame["runtime_owner"] == "RuntimeHost -> MissionWorkspaceRuntime"
    assert frame["can_execute"] is False
    assert frame["can_grant_authority"] is False
    assert frame["data_not_authority"] is True
    assert frame["owned_handles"] == [
        "workspace_files",
        "scratch_memory",
        "code_sandbox",
        "browser_session",
        "channel_destination_grants",
        "worker_pool",
        "receipt_ledger",
        "replay_ledger",
        "artifact_export",
    ]
    assert "payment" in frame["hard_boundaries"]
    assert "credential_access" in frame["hard_boundaries"]


def test_prepare_mission_workspace_creates_one_bounded_product_body(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _mission(host)

    manifest = host.prepare_mission_workspace(
        mission_id=mission.mission_id,
        workspace_root=workspace,
        allowed_domains=("bounded.example",),
        channel_destination_refs=("telegram:test-chat",),
    )

    assert manifest["mission_id"] == mission.mission_id
    assert manifest["workspace_root_hash"]
    assert manifest["workspace_root_ref"].startswith("workspace_root_hash:")
    assert manifest["data_not_authority"] is True
    assert manifest["authority_effect"] == "none"
    assert manifest["can_execute"] is False
    assert manifest["can_grant_authority"] is False
    assert manifest["product_spine_entrypoint"] == "RuntimeHost -> MissionWorkspaceRuntime -> ProductActionKernel"

    handles = {handle["kind"]: handle for handle in manifest["handles"]}
    assert set(handles) == {
        "workspace_files",
        "scratch_memory",
        "code_sandbox",
        "browser_session",
        "channel_destination_grants",
        "worker_pool",
        "receipt_ledger",
        "replay_ledger",
        "artifact_export",
    }
    assert all(handle["can_execute"] is False for handle in handles.values())
    assert all(handle["data_not_authority"] is True for handle in handles.values())
    assert handles["code_sandbox"]["backend_binding"] == "code_execution_sandbox"
    assert handles["browser_session"]["backend_binding"] == "browser_control"
    assert handles["channel_destination_grants"]["backend_binding"] == "bounded_channel"
    assert handles["worker_pool"]["backend_binding"] == "worker_fleet"


def test_mission_workspace_manifest_is_persisted_without_raw_sensitive_material(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _mission(host)

    manifest = host.prepare_mission_workspace(
        mission_id=mission.mission_id,
        workspace_root=workspace,
        allowed_domains=("bounded.example",),
        channel_destination_refs=("telegram:test-chat",),
    )

    manifest_path = Path(manifest["manifest_path"])
    assert manifest_path.exists()
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    rendered = json.dumps(persisted, sort_keys=True).lower()

    assert persisted["manifest_hash"] == manifest["manifest_hash"]
    assert str(workspace.resolve()).lower() not in rendered
    assert "telegram:test-chat" not in rendered
    assert "authorization" not in rendered
    assert "bearer " not in rendered
    assert "api_key" not in rendered
    assert "session_token" not in rendered
    assert "cookie" not in rendered


def test_prepare_mission_workspace_rejects_missing_or_file_workspace_root(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    mission = _mission(host)

    with pytest.raises(ValueError, match="mission_workspace_root_not_found"):
        host.prepare_mission_workspace(mission_id=mission.mission_id, workspace_root=tmp_path / "missing")

    file_root = tmp_path / "not-a-directory.txt"
    file_root.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="mission_workspace_root_not_directory"):
        host.prepare_mission_workspace(mission_id=mission.mission_id, workspace_root=file_root)


def test_prepare_mission_workspace_does_not_register_new_dispatch_or_live_power(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    mission = _mission(host)
    adapters_before = sorted(host.adapter_registry.adapter_ids())
    connections_before = sorted(connection.connection_id for connection in host.connection_registry.connections)

    manifest = host.prepare_mission_workspace(mission_id=mission.mission_id, workspace_root=workspace)

    assert sorted(host.adapter_registry.adapter_ids()) == adapters_before
    assert sorted(connection.connection_id for connection in host.connection_registry.connections) == connections_before
    assert manifest["registered_new_dispatch_adapter"] is False
    assert manifest["live_external_power_enabled"] is False


def test_prepare_mission_workspace_survives_long_windows_run_path(tmp_path: Path) -> None:
    long_run_root = tmp_path
    for index in range(5):
        long_run_root = long_run_root / f"sentinel_runtime_segment_{index}_{'x' * 36}"
    host = SentinelRuntimeHost(run_root=long_run_root).start().host
    workspace = _workspace(tmp_path)
    mission = _mission(host)

    manifest = host.prepare_mission_workspace(
        mission_id=mission.mission_id,
        workspace_root=workspace,
        allowed_domains=("bounded.example",),
    )

    assert manifest["mission_id"] == mission.mission_id
    assert {handle["kind"] for handle in manifest["handles"]} == {
        "workspace_files",
        "scratch_memory",
        "code_sandbox",
        "browser_session",
        "channel_destination_grants",
        "worker_pool",
        "receipt_ledger",
        "replay_ledger",
        "artifact_export",
    }
    assert _path_exists(Path(manifest["manifest_path"]))


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Mission workspace\n", encoding="utf-8")
    return root


def _mission(host: SentinelRuntimeHost):
    return host.kernel.create_mission(
        session_id="session_power_unification_pack3",
        draft=MissionDraft(
            title="Pack 3 mission workspace",
            objective="Create one bounded mission workspace body.",
            expected_artifacts=["mission workspace manifest"],
        ),
        authority_summary=MissionAuthoritySummary(
            mission_id="pending",
            allowed_actions=["workspace_patch", "code_execution_sandbox", "bounded_channel"],
            forbidden_actions=["payment", "credential_access", "browser_login"],
            summary="Pack 3 workspace body authority summary.",
        ),
    )
