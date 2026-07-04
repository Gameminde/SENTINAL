from __future__ import annotations

import json
import os
from pathlib import Path

from sentinel.operator.action_kernel import ActionEnvelope
from sentinel.operator.mission_artifact_bundle import (
    MissionArtifactBundleExporter,
    MissionArtifactBundleVerifier,
)
from sentinel.operator.model_led_product_action_kernel_task_loop import ProductActionKernelLoopDecisionClient
from sentinel.operator.runtime_host import SentinelRuntimeHost


def test_mission_artifact_bundle_export_contains_manifest_authority_skills_receipts_finalgate(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)

    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Export a code, channel, and worker product mission.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )

    bundle = _load_bundle(export.bundle_dir)
    assert export.accepted is True
    assert export.local_integrity_seal
    assert set(bundle) >= {
        "mission_manifest",
        "authority_envelope",
        "model_visible_skills",
        "decision_summaries",
        "skill_action_trace",
        "product_action_kernel_receipts",
        "skill_specific_receipts",
        "finalgate_certificates",
        "worker_receipts",
        "replay_proof",
        "artifact_hashes",
        "hard_boundary_events",
        "mission_summary",
        "verifier_result",
    }
    assert bundle["mission_manifest"]["integrity_model"] == "local_hash_chain"
    assert len(bundle["product_action_kernel_receipts"]["receipts"]) == 3
    assert len(bundle["finalgate_certificates"]["certificates"]) == 3
    assert len(bundle["worker_receipts"]["receipts"]) == 1
    assert bundle["verifier_result"]["accepted"] is True


def test_artifact_bundle_uses_mission_workspace_artifact_export_handle(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)

    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Export from the mission workspace body.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    owner_mission_dir = host.kernel.store.mission_dir(str(export.bundle_manifest["owner_mission_id"]))
    manifest = _read_path_json(owner_mission_dir / "mission_workspace" / "manifest.json")
    artifact_export = _handle(manifest, "artifact_export")

    assert Path(export.bundle_dir).resolve().parent == (owner_mission_dir / artifact_export["relative_path"]).resolve()
    assert export.bundle_manifest["artifact_export_ref"] == artifact_export["safe_ref"]
    assert export.bundle_manifest["artifact_export_hash"]


def test_verifier_accepts_valid_code_channel_worker_bundle(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Verify a valid product mission bundle.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )

    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert verified.accepted is True
    assert verified.failure_codes == ()
    assert verified.replay_no_react is True
    assert verified.local_integrity_seal == export.local_integrity_seal


def test_verifier_rejects_missing_product_action_kernel_receipt(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Reject missing product receipts.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    payload = _read_json(export.bundle_dir, "product_action_kernel_receipts.json")
    payload["receipts"].pop()
    _write_json(export.bundle_dir, "product_action_kernel_receipts.json", payload)

    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert verified.accepted is False
    assert "missing_product_action_kernel_receipt" in verified.failure_codes


def test_verifier_rejects_finalgate_receipt_mismatch(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Reject mismatched FinalGate receipts.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    payload = _read_json(export.bundle_dir, "finalgate_certificates.json")
    payload["certificates"][0]["receipt_refs"] = ["product_action_kernel_receipt_forged"]
    _write_json(export.bundle_dir, "finalgate_certificates.json", payload)

    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert verified.accepted is False
    assert "finalgate_receipt_mismatch" in verified.failure_codes


def test_verifier_rejects_worker_authority_expansion(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Reject worker authority expansion.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    payload = _read_json(export.bundle_dir, "worker_receipts.json")
    payload["receipts"][0]["authority_expanded"] = True
    payload["receipts"][0]["child_authority"]["strict_subset"] = False
    _write_json(export.bundle_dir, "worker_receipts.json", payload)

    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert verified.accepted is False
    assert "worker_authority_expansion" in verified.failure_codes


def test_verifier_replay_proves_no_code_rerun_no_channel_resend_no_worker_respawn(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)

    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Verify replay no-react proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    replay = _read_json(export.bundle_dir, "replay_proof.json")

    assert replay["no_code_rerun"] is True
    assert replay["no_channel_resend"] is True
    assert replay["no_worker_respawn"] is True
    assert replay["no_new_receipts"] is True


def test_verifier_rejects_new_receipt_written_during_replay(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Reject replay receipt mutation.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )
    replay = _read_json(export.bundle_dir, "replay_proof.json")
    replay["receipt_writes_delta"] = 1
    replay["no_new_receipts"] = False
    _write_json(export.bundle_dir, "replay_proof.json", replay)

    verified = MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir)

    assert verified.accepted is False
    assert "replay_receipt_write_delta" in verified.failure_codes


def test_export_redacts_raw_provider_reasoning_dom_cookies_session_profile_material(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)
    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Scan exported mission bundle.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
    )

    persisted = "\n".join(_read_text(path) for path in Path(export.bundle_dir).glob("*.json"))
    lowered = persisted.lower()

    forbidden = (
        "raw_provider",
        "raw_prompt",
        "raw_response",
        "raw_reasoning",
        "reasoning_content",
        "raw_dom",
        "cookie:",
        "session_token",
        "profile_material",
        "authorization",
        "bearer ",
    )
    assert not any(marker in lowered for marker in forbidden)


def test_pack6_boundary_events_are_exported_without_expanding_power(tmp_path: Path) -> None:
    host, result = _run_code_channel_worker_mission(tmp_path)

    export = MissionArtifactBundleExporter(host.kernel.store).export_product_loop(
        loop_result=result,
        mission_objective="Export hard boundary proof.",
        model_visible_skills=tuple(host.product_task_loop_entrypoint_frame()["model_visible_skills"]),
        hard_boundary_events=[
            {"category": "payment", "status": "blocked"},
            {"category": "login", "status": "blocked"},
            {"category": "credentials", "status": "blocked"},
            {"category": "contact_supplier", "status": "blocked"},
        ],
    )
    hard_boundaries = _read_json(export.bundle_dir, "hard_boundary_events.json")

    assert {event["category"] for event in hard_boundaries["events"]} == {
        "payment",
        "login",
        "credentials",
        "contact_supplier",
    }
    assert MissionArtifactBundleVerifier.verify_bundle(export.bundle_dir).accepted is True


def _run_code_channel_worker_mission(tmp_path: Path):
    host = SentinelRuntimeHost(run_root=tmp_path / "runs").start().host
    workspace = _workspace(tmp_path)
    result = host.run_product_action_kernel_task_loop(
        workspace_root=workspace,
        session_id="session_pack6_bundle",
        mission_objective="Run code, send a bounded local channel message, delegate a worker, and finish.",
        decision_client=ProductActionKernelLoopDecisionClient(
            [
                ActionEnvelope(
                    capability_id="code_execution_sandbox",
                    operation="code_exec.run_profile",
                    params={"profile_id": "fake_pass", "args": ["."]},
                    idempotency_key="pack6-code",
                ),
                ActionEnvelope(
                    capability_id="bounded_channel",
                    operation="send_message",
                    params={
                        "adapter_id": "pack6_fake_channel",
                        "channel": "webhook",
                        "body": "Safe bounded Pack 6 channel dispatch.",
                        "recipients": ["founder@example.com"],
                        "recipient_provenance": {"founder@example.com": "mission_level_destination_grant"},
                        "evidence_refs": ["evidence:pack6_product_loop"],
                        "idempotency_key": "pack6-send-1",
                    },
                    idempotency_key="pack6-channel",
                ),
                ActionEnvelope(
                    capability_id="worker_fleet",
                    operation="spawn_worker",
                    params={
                        "role": "verifier",
                        "objective": "Verify the local bundle proof.",
                        "delegated_skills": ["read", "spawn_worker"],
                        "max_actions": 1,
                    },
                    idempotency_key="pack6-worker",
                ),
                ActionEnvelope(
                    capability_id="sentinel_loop",
                    operation="finish",
                    params={"safe_summary": "Pack 6 product loop completed."},
                    idempotency_key="pack6-finish",
                ),
            ]
        ),
        allowed_domains=("local.worker", "example.com"),
        max_model_calls=5,
        max_material_actions=3,
    )
    return host, result


def _workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "README.md").write_text("# Pack 6 signed mission artifacts\n", encoding="utf-8")
    return root


def _load_bundle(bundle_dir: str) -> dict[str, object]:
    return {
        path.stem: _read_path_json(path)
        for path in Path(bundle_dir).glob("*.json")
    }


def _read_json(bundle_dir: str, name: str) -> dict[str, object]:
    return _read_path_json(Path(bundle_dir) / name)


def _write_json(bundle_dir: str, name: str, payload: dict[str, object]) -> None:
    with open(_filesystem_path(Path(bundle_dir) / name), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True))


def _handle(manifest: dict[str, object], kind: str) -> dict[str, object]:
    for handle in manifest["handles"]:
        if handle["kind"] == kind:
            return handle
    raise AssertionError(f"missing handle {kind}")


def _read_path_json(path: Path) -> dict[str, object]:
    return json.loads(_read_text(path))


def _read_text(path: Path) -> str:
    with open(_filesystem_path(path), encoding="utf-8") as handle:
        return handle.read()


def _filesystem_path(path: Path) -> str:
    rendered = str(path)
    if os.name != "nt" or rendered.startswith("\\\\?\\"):
        return rendered
    if rendered.startswith("\\\\"):
        return "\\\\?\\UNC\\" + rendered[2:]
    return "\\\\?\\" + rendered
