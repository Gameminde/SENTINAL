from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.model_led_product_action_kernel_task_loop import (
    ProductActionKernelTaskLoopReplay,
    ProductActionKernelTaskLoopResult,
)
from sentinel.operator.safety import assert_data_not_authority
from sentinel.operator.store import MissionRunStore
from sentinel.shared.models import SentinelModel


BUNDLE_SCHEMA_VERSION = "mission-artifact-bundle/v1"
_HASH_CHAIN_EXCLUDED = {"artifact_hashes", "mission_manifest", "verifier_result"}


class MissionArtifactBundleExportResult(SentinelModel):
    bundle_id: str
    bundle_dir: str
    accepted: bool
    local_integrity_seal: str
    bundle_manifest: dict[str, Any]
    verifier_failure_codes: tuple[str, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _export_result_is_data_only(self) -> "MissionArtifactBundleExportResult":
        assert_data_not_authority(
            context="mission_artifact_bundle_export_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class MissionArtifactBundleVerifierResult(SentinelModel):
    bundle_id: str
    accepted: bool
    failure_codes: tuple[str, ...] = Field(default_factory=tuple)
    local_integrity_seal: str = ""
    replay_no_react: bool = False
    checked_from_exported_bundle_only: bool = True
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _verifier_result_is_data_only(self) -> "MissionArtifactBundleVerifierResult":
        assert_data_not_authority(
            context="mission_artifact_bundle_verifier_result",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MissionArtifactBundleExporter:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def export_product_loop(
        self,
        *,
        loop_result: ProductActionKernelTaskLoopResult,
        mission_objective: str,
        model_visible_skills: tuple[str, ...],
        hard_boundary_events: Iterable[dict[str, Any]] = (),
    ) -> MissionArtifactBundleExportResult:
        if not loop_result.mission_ids:
            raise ValueError("mission_artifact_bundle_requires_material_mission")
        owner_mission_id = _owner_mission_with_artifact_export(self._store, loop_result.mission_ids)
        owner_mission_dir = self._store.mission_dir(owner_mission_id)
        workspace_manifest = _load_json(owner_mission_dir / "mission_workspace" / "manifest.json")
        artifact_export = _handle(workspace_manifest, "artifact_export")
        bundle_id = f"mission_artifact_bundle_{stable_hash({'loop_id': loop_result.loop_id, 'mission_ids': loop_result.mission_ids})[:16]}"
        bundle_dir = owner_mission_dir / str(artifact_export["relative_path"]) / bundle_id
        bundle_dir.mkdir(parents=True, exist_ok=True)

        payloads = self._payloads(
            bundle_id=bundle_id,
            loop_result=loop_result,
            owner_mission_id=owner_mission_id,
            mission_objective=mission_objective,
            model_visible_skills=model_visible_skills,
            workspace_manifest=workspace_manifest,
            artifact_export=artifact_export,
            hard_boundary_events=tuple(hard_boundary_events),
        )
        seal = _local_integrity_seal(payloads)
        payloads["mission_manifest"]["local_integrity_seal"] = seal
        payloads["artifact_hashes"] = _artifact_hash_payload(payloads)

        for name, payload in payloads.items():
            self._store.atomic_write_json(bundle_dir / f"{name}.json", payload)

        verifier_result = MissionArtifactBundleVerifier.verify_bundle(bundle_dir)
        self._store.atomic_write_json(bundle_dir / "verifier_result.json", verifier_result.safe_model_dump())
        manifest = payloads["mission_manifest"]
        return MissionArtifactBundleExportResult(
            bundle_id=bundle_id,
            bundle_dir=str(bundle_dir),
            accepted=verifier_result.accepted,
            local_integrity_seal=seal,
            bundle_manifest=manifest,
            verifier_failure_codes=verifier_result.failure_codes,
        )

    def _payloads(
        self,
        *,
        bundle_id: str,
        loop_result: ProductActionKernelTaskLoopResult,
        owner_mission_id: str,
        mission_objective: str,
        model_visible_skills: tuple[str, ...],
        workspace_manifest: dict[str, Any],
        artifact_export: dict[str, Any],
        hard_boundary_events: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        product_receipts = _collect_product_receipts(self._store, loop_result.mission_ids)
        finalgate = _collect_product_finalgate(self._store, loop_result.mission_ids)
        skill_receipts = _collect_skill_receipts(self._store, loop_result.mission_ids)
        worker_receipts = _collect_worker_receipts(self._store, loop_result.mission_ids)
        replay = ProductActionKernelTaskLoopReplay.from_store(self._store, mission_ids=loop_result.mission_ids)
        replay_payload = {
            **replay.model_dump(mode="json"),
            "no_code_rerun": replay.command_executions_delta == 0,
            "no_channel_resend": replay.channel_transport_sends_delta == 0,
            "no_workspace_patch_reapply": replay.reexecuted_actions is False,
            "no_browser_reopen_research_reextract": replay.reexecuted_actions is False,
            "no_worker_respawn": replay.reexecuted_actions is False and replay.receipt_writes_delta == 0,
            "no_new_receipts": replay.receipt_writes_delta == 0,
            "no_new_finalgate": replay.finalgate_writes_delta == 0,
        }
        mission_objective_hash = stable_hash({"mission_objective": mission_objective})
        return {
            "mission_manifest": {
                "schema_version": BUNDLE_SCHEMA_VERSION,
                "bundle_id": bundle_id,
                "owner_mission_id": owner_mission_id,
                "mission_ids": list(loop_result.mission_ids),
                "mission_objective_hash": mission_objective_hash,
                "mission_workspace_ref": workspace_manifest["manifest_id"],
                "mission_workspace_hash": workspace_manifest["manifest_hash"],
                "artifact_export_ref": artifact_export["safe_ref"],
                "artifact_export_hash": stable_hash(artifact_export),
                "integrity_model": "local_hash_chain",
                "external_signature": "not_claimed",
                "local_integrity_seal": "",
                "data_not_authority": True,
                "can_execute": False,
            },
            "authority_envelope": {
                "mission_ids": list(loop_result.mission_ids),
                "records": [_record_summary(self._store, mission_id) for mission_id in loop_result.mission_ids],
            },
            "model_visible_skills": {
                "primary_model_surface": "model_visible_skills",
                "skills": sorted(set(model_visible_skills)),
                "action_envelope_language": "internal_runtime_only",
            },
            "decision_summaries": {
                "model_call_count": loop_result.model_call_count,
                "dispatch_results": [_dispatch_summary(result) for result in loop_result.dispatch_results],
            },
            "skill_action_trace": {
                "loop_id": loop_result.loop_id,
                "status": loop_result.status.value,
                "final_reason": loop_result.final_reason,
                "capability_sequence": list(loop_result.capability_sequence),
                "material_action_count": loop_result.material_action_count,
                "product_receipt_refs": list(loop_result.product_receipt_refs),
                "product_finalgate_refs": list(loop_result.product_finalgate_refs),
                "certificate_refs": list(loop_result.certificate_refs),
            },
            "product_action_kernel_receipts": {"receipts": product_receipts},
            "skill_specific_receipts": {"receipts": skill_receipts},
            "finalgate_certificates": {"certificates": finalgate},
            "worker_receipts": {"receipts": worker_receipts},
            "replay_proof": replay_payload,
            "hard_boundary_events": {"events": [_safe_boundary_event(event) for event in hard_boundary_events]},
            "mission_summary": {
                "mission_objective_hash": mission_objective_hash,
                "status": loop_result.status.value,
                "material_action_count": loop_result.material_action_count,
                "product_receipt_count": len(product_receipts),
                "skill_specific_receipt_count": len(skill_receipts),
                "worker_receipt_count": len(worker_receipts),
                "finalgate_certificate_count": len(finalgate),
                "summary_hash": stable_hash(
                    {
                        "status": loop_result.status.value,
                        "capability_sequence": list(loop_result.capability_sequence),
                        "product_receipts": loop_result.product_receipt_refs,
                    }
                ),
            },
        }


class MissionArtifactBundleVerifier:
    @classmethod
    def verify_bundle(cls, bundle_dir: Path | str) -> MissionArtifactBundleVerifierResult:
        path = Path(bundle_dir)
        payloads = _load_bundle_payloads(path)
        failures: list[str] = []
        for name in _required_bundle_names():
            if name not in payloads:
                failures.append(f"missing_{name}")
        if failures:
            return MissionArtifactBundleVerifierResult(
                bundle_id="unknown",
                accepted=False,
                failure_codes=tuple(failures),
            )

        manifest = payloads["mission_manifest"]
        bundle_id = str(manifest.get("bundle_id") or "unknown")
        seal = str(manifest.get("local_integrity_seal") or "")
        if not seal or seal != _local_integrity_seal(payloads):
            failures.append("integrity_hash_chain_invalid")

        trace = payloads["skill_action_trace"]
        product_receipts = payloads["product_action_kernel_receipts"].get("receipts", [])
        finalgate = payloads["finalgate_certificates"].get("certificates", [])
        worker_receipts = payloads["worker_receipts"].get("receipts", [])
        replay = payloads["replay_proof"]

        if len(product_receipts) < int(trace.get("material_action_count") or 0):
            failures.append("missing_product_action_kernel_receipt")
        product_receipt_ids = {str(receipt.get("receipt_id")) for receipt in product_receipts}
        for certificate in finalgate:
            refs = {str(ref) for ref in certificate.get("receipt_refs", [])}
            if not refs or not refs.issubset(product_receipt_ids):
                failures.append("finalgate_receipt_mismatch")
                break
        for receipt in worker_receipts:
            child = receipt.get("child_authority") if isinstance(receipt, dict) else None
            if receipt.get("authority_expanded") is True or not isinstance(child, dict) or child.get("strict_subset") is not True:
                failures.append("worker_authority_expansion")
                break
        if int(replay.get("receipt_writes_delta") or 0) != 0 or replay.get("no_new_receipts") is not True:
            failures.append("replay_receipt_write_delta")
        if int(replay.get("finalgate_writes_delta") or 0) != 0 or replay.get("no_new_finalgate") is not True:
            failures.append("replay_finalgate_write_delta")
        if replay.get("no_code_rerun") is not True:
            failures.append("replay_code_rerun")
        if replay.get("no_channel_resend") is not True:
            failures.append("replay_channel_resend")
        if replay.get("no_worker_respawn") is not True:
            failures.append("replay_worker_respawn")
        if _contains_forbidden_raw_material(payloads):
            failures.append("raw_material_persistence")

        unique_failures = tuple(dict.fromkeys(failures))
        return MissionArtifactBundleVerifierResult(
            bundle_id=bundle_id,
            accepted=not unique_failures,
            failure_codes=unique_failures,
            local_integrity_seal=seal,
            replay_no_react=not any(code.startswith("replay_") for code in unique_failures),
        )


def _collect_product_receipts(store: MissionRunStore, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    return _collect_product_action_kernel_artifacts(store, mission_ids, collection="receipts", collection_short="r")


def _collect_product_finalgate(store: MissionRunStore, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    return _collect_product_action_kernel_artifacts(store, mission_ids, collection="finalgate", collection_short="fg")


def _collect_worker_receipts(store: MissionRunStore, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    return _collect_json_files(store, mission_ids, "worker_fleet/receipts/*.json")


def _collect_skill_receipts(store: MissionRunStore, mission_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    excluded_parts = {"product_action_kernel", "worker_fleet"}
    for mission_id in mission_ids:
        mission_dir = store.mission_dir(mission_id)
        if not mission_dir.exists():
            continue
        for path in sorted(mission_dir.rglob("receipts/*.json")):
            if excluded_parts.intersection(path.parts):
                continue
            receipts.append(_load_json(path))
    return receipts


def _collect_json_files(store: MissionRunStore, mission_ids: tuple[str, ...], pattern: str) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for mission_id in mission_ids:
        mission_dir = store.mission_dir(mission_id)
        if not mission_dir.exists():
            continue
        for path in sorted(mission_dir.glob(pattern)):
            payloads.append(_load_json(path))
    return payloads


def _collect_product_action_kernel_artifacts(
    store: MissionRunStore,
    mission_ids: tuple[str, ...],
    *,
    collection: str,
    collection_short: str,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    seen: set[str] = set()
    for mission_id in mission_ids:
        mission_dir = store.mission_dir(mission_id)
        if not mission_dir.exists():
            continue
        index_path = mission_dir / "_pak" / "index" / f"{collection_short}.json"
        if index_path.exists():
            index = _load_json(index_path)
            entries = index.get("entries") if isinstance(index.get("entries"), dict) else {}
            for logical_ref, entry in sorted(entries.items()):
                if not isinstance(entry, dict):
                    continue
                relative_path = _safe_relative_artifact_path(str(entry.get("relative_path") or ""))
                if relative_path is None:
                    continue
                artifact_path = mission_dir / relative_path
                if not _json_path_exists(artifact_path):
                    continue
                payload = _load_json(artifact_path)
                key = str(payload.get("receipt_id") or payload.get("certificate_id") or logical_ref)
                if key in seen:
                    continue
                seen.add(key)
                payloads.append(payload)
        for payload in _collect_json_files(store, (mission_id,), f"product_action_kernel/{collection}/*.json"):
            key = str(payload.get("receipt_id") or payload.get("certificate_id") or stable_hash(payload))
            if key in seen:
                continue
            seen.add(key)
            payloads.append(payload)
    return payloads


def _safe_relative_artifact_path(value: str) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def _record_summary(store: MissionRunStore, mission_id: str) -> dict[str, Any]:
    record = store.load_record(mission_id)
    payload = record.safe_model_dump()
    return {
        "mission_id": payload["mission_id"],
        "status": payload["status"],
        "authority_summary": payload.get("authority_summary"),
        "power_actions_used": payload.get("power_actions_used"),
        "record_hash": payload.get("record_hash"),
    }


def _dispatch_summary(result: Any) -> dict[str, Any]:
    return {
        "dispatch_id": result.dispatch_id,
        "mission_id": result.mission_id,
        "status": result.status.value,
        "capability_id": result.capability_id,
        "operation": result.operation,
        "adapter_id": result.adapter_id,
        "receipt_refs": list(result.receipt_refs),
        "finalgate_refs": list(result.finalgate_refs),
        "blocked_reason": result.blocked_reason,
    }


def _safe_boundary_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "category": str(event.get("category") or "unknown"),
        "status": str(event.get("status") or "unknown"),
        "proof_hash": stable_hash(event),
    }


def _artifact_hash_payload(payloads: dict[str, Any]) -> dict[str, Any]:
    item_hashes = {
        name: stable_hash(payload)
        for name, payload in sorted(payloads.items())
        if name not in {"artifact_hashes", "verifier_result"}
    }
    return {
        "hash_algorithm": "stable_hash",
        "local_integrity_seal": _local_integrity_seal(payloads),
        "item_hashes": item_hashes,
    }


def _local_integrity_seal(payloads: dict[str, Any]) -> str:
    item_hashes = [
        {"name": name, "hash": stable_hash(payload)}
        for name, payload in sorted(payloads.items())
        if name not in _HASH_CHAIN_EXCLUDED
    ]
    return stable_hash({"schema_version": BUNDLE_SCHEMA_VERSION, "items": item_hashes})


def _load_bundle_payloads(bundle_dir: Path) -> dict[str, Any]:
    payloads: dict[str, Any] = {}
    if not bundle_dir.exists():
        return payloads
    for path in sorted(bundle_dir.glob("*.json")):
        payloads[path.stem] = _load_json(path)
    return payloads


def _required_bundle_names() -> tuple[str, ...]:
    return (
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
    )


def _handle(manifest: dict[str, Any], kind: str) -> dict[str, Any]:
    for handle in manifest.get("handles", []):
        if isinstance(handle, dict) and handle.get("kind") == kind:
            return handle
    raise ValueError(f"mission_workspace_{kind}_handle_missing")


def _owner_mission_with_artifact_export(store: MissionRunStore, mission_ids: tuple[str, ...]) -> str:
    for mission_id in mission_ids:
        manifest_path = store.mission_dir(mission_id) / "mission_workspace" / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = _load_json(manifest_path)
        try:
            _handle(manifest, "artifact_export")
        except ValueError:
            continue
        return mission_id
    raise ValueError("mission_artifact_bundle_requires_mission_workspace_artifact_export")


def _contains_forbidden_raw_material(payloads: dict[str, Any]) -> bool:
    rendered = json.dumps(payloads, sort_keys=True).lower()
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
    return any(marker in rendered for marker in forbidden)


def _load_json(path: Path) -> dict[str, Any]:
    with open(_filesystem_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _json_path_exists(path: Path) -> bool:
    if path.exists():
        return True
    if os.name != "nt":
        return False
    return os.path.exists(_filesystem_path(path))


def _filesystem_path(path: Path) -> str:
    rendered = str(path)
    if os.name != "nt" or rendered.startswith("\\\\?\\"):
        return rendered
    if rendered.startswith("\\\\"):
        return "\\\\?\\UNC\\" + rendered[2:]
    return "\\\\?\\" + rendered


__all__ = [
    "MissionArtifactBundleExporter",
    "MissionArtifactBundleExportResult",
    "MissionArtifactBundleVerifier",
    "MissionArtifactBundleVerifierResult",
]
