from __future__ import annotations

import json
from pathlib import Path

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelLoopDecisionClient,
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopStatus,
)
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_spawn_worker_consumes_mission_workspace_worker_pool_handle(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack5_worker_pool_handle",
        mission_objective="Delegate a bounded research subtask, then finish.",
        decision_client=_spawn_worker_finish_client(),
        allowed_domains=("local.worker",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    action_mission_id = result.dispatch_results[0].mission_id
    manifest = _mission_workspace_manifest(host, action_mission_id)
    worker_pool = _handle(manifest, "worker_pool")
    worker_receipt = _first_json(host.kernel.store.mission_dir(action_mission_id) / "worker_fleet" / "receipts")

    assert worker_receipt["worker_pool_ref"] == worker_pool["safe_ref"]
    assert worker_receipt["mission_workspace_ref"] == manifest["manifest_id"]
    assert worker_receipt["mission_workspace_hash"] == manifest["manifest_hash"]
    assert worker_receipt["simple_skill"] == "spawn_worker"
    assert worker_receipt["internal_action_id"] == "worker_fleet.spawn_worker"
    assert worker_receipt["product_dispatch_owner"] == "product_action_kernel_adapter"
    assert worker_receipt["worker_role"] == "researcher"
    assert worker_receipt["authority_expanded"] is False


def test_spawn_worker_routes_through_runtimehost_product_action_kernel(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack5_worker_route",
        mission_objective="Run worker delegation through the product spine.",
        decision_client=_spawn_worker_finish_client(),
        allowed_domains=("local.worker",),
        max_model_calls=3,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert result.capability_sequence == (
        "worker_fleet:spawn_worker",
        "sentinel_loop:finish",
    )
    assert result.dispatch_results[0].adapter_id == "product_action_kernel_adapter"
    product_receipt = _product_receipt(host, result.dispatch_results[0].mission_id, result.product_receipt_refs[0])
    assert product_receipt["skill_id"] == "spawn_worker"
    assert product_receipt["capability_id"] == "worker_fleet"
    assert product_receipt["operation"] == "spawn_worker"
    assert product_receipt["backend_id"] == "worker_fleet_skill"
    assert product_receipt["organ_id"] == "worker_fleet_backend"


def test_worker_child_authority_is_reduced_subset_and_cannot_expand_scope(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack5_worker_reduced_authority",
        mission_objective="Delegate a verifier with less power than the parent.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="worker_fleet",
                    operation="spawn_worker",
                    params={
                        "role": "verifier",
                        "objective": "Verify the local receipt summary only.",
                        "delegated_skills": ["read", "run_check", "send_message"],
                        "max_actions": 1,
                    },
                ),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Worker verifier completed."},
                ),
            ]
        ),
        allowed_domains=("local.worker",),
        max_model_calls=3,
        max_material_actions=1,
    )

    worker_receipt = _first_json(host.kernel.store.mission_dir(result.dispatch_results[0].mission_id) / "worker_fleet" / "receipts")
    child = worker_receipt["child_authority"]
    assert result.status is ProductActionKernelTaskLoopStatus.COMPLETED
    assert child["strict_subset"] is True
    assert child["allow_worker_spawning"] is False
    assert child["allowed_tools"] == ["worker_fleet"]
    assert child["allowed_actions"] == ["worker_fleet.spawn_worker"]
    assert worker_receipt["requested_skill_scope"] == ["read", "run_check", "send_message"]
    assert worker_receipt["delegated_skill_scope"] == ["spawn_worker"]
    assert worker_receipt["authority_expanded"] is False


def test_worker_hard_boundaries_block_without_fake_receipt(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack5_worker_hard_stop",
        mission_objective="Worker hard boundaries stay hard.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="worker_fleet",
                    operation="spawn_worker",
                    params={
                        "role": "researcher",
                        "objective": "Contact supplier and start checkout.",
                        "delegated_skills": ["spawn_worker"],
                    },
                ),
            ]
        ),
        allowed_domains=("local.worker",),
        max_model_calls=1,
        max_material_actions=1,
    )

    assert result.status is ProductActionKernelTaskLoopStatus.BLOCKED
    assert result.blocked_reason == "worker_fleet_hard_boundary_requested"
    assert result.product_receipt_refs == ()
    assert result.dispatch_results[0].receipt_refs == []


def test_model_surface_exposes_spawn_worker_as_simple_skill(tmp_path: Path) -> None:
    frame = SentinelRuntimeHost(run_root=tmp_path / "runs").product_task_loop_entrypoint_frame()

    assert "spawn_worker" in frame["model_visible_skills"]
    assert "worker_fleet.spawn_worker" in frame["model_visible_available_actions"]
    assert frame["runtime_internal_action_map"]["spawn_worker"] == "worker_fleet.spawn_worker"
    assert "worker_fleet_backend" in frame["hidden_backend_bindings"]
    assert "WorkerFleetRuntime" not in json.dumps(frame["model_visible_skills"])
    assert frame["primary_model_language"] == "simple_mission_skills"


def test_worker_replay_does_not_respawn_or_reexecute(tmp_path: Path) -> None:
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)

    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack5_worker_replay",
        mission_objective="Spawn a worker and verify replay no-react.",
        decision_client=_spawn_worker_finish_client(),
        allowed_domains=("local.worker",),
        max_model_calls=3,
        max_material_actions=1,
    )
    replay = ProductActionKernelTaskLoopReplay.from_store(host.kernel.store, mission_ids=result.mission_ids)

    assert replay.reexecuted_actions is False
    assert replay.model_calls_delta == 0
    assert replay.product_dispatch_delta == 0
    assert replay.command_executions_delta == 0
    assert replay.channel_transport_sends_delta == 0
    assert replay.receipt_writes_delta == 0
    assert replay.finalgate_writes_delta == 0
    assert replay.artifact_hashes_stable is True


def _spawn_worker_finish_client() -> ProductActionKernelLoopDecisionClient:
    return ProductActionKernelLoopDecisionClient(
        [
            ActionEnvelope(
                capability_id="worker_fleet",
                operation="spawn_worker",
                params={
                    "role": "researcher",
                    "objective": "Summarize the local workspace evidence for the mission commander.",
                    "delegated_skills": ["read", "spawn_worker"],
                    "max_actions": 1,
                },
            ),
            ActionEnvelope(
                capability_id="sentinel_loop",
                operation="finish",
                params={"safe_summary": "Worker delegation completed."},
            ),
        ]
    )


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 5 worker orchestration\n", encoding="utf-8")
    return root


def _mission_workspace_manifest(host: SentinelRuntimeHost, mission_id: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "mission_workspace" / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _handle(manifest: dict[str, object], kind: str) -> dict[str, object]:
    for handle in manifest["handles"]:
        if handle["kind"] == kind:
            return handle
    raise AssertionError(f"missing handle {kind}")


def _product_receipt(host: SentinelRuntimeHost, mission_id: str, receipt_ref: str) -> dict[str, object]:
    path = host.kernel.store.mission_dir(mission_id) / "product_action_kernel" / "receipts" / f"{receipt_ref}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _first_json(directory: Path) -> dict[str, object]:
    files = sorted(directory.glob("*.json"))
    assert files
    return json.loads(files[0].read_text(encoding="utf-8"))
