from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.kernel import MissionKernel
from sentinel.operator.store import _mkdir_path
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


class MissionWorkspaceHandleKind(StrEnum):
    WORKSPACE_FILES = "workspace_files"
    SCRATCH_MEMORY = "scratch_memory"
    CODE_SANDBOX = "code_sandbox"
    BROWSER_SESSION = "browser_session"
    CHANNEL_DESTINATION_GRANTS = "channel_destination_grants"
    WORKER_POOL = "worker_pool"
    RECEIPT_LEDGER = "receipt_ledger"
    REPLAY_LEDGER = "replay_ledger"
    ARTIFACT_EXPORT = "artifact_export"


MISSION_WORKSPACE_HANDLE_ORDER: tuple[MissionWorkspaceHandleKind, ...] = (
    MissionWorkspaceHandleKind.WORKSPACE_FILES,
    MissionWorkspaceHandleKind.SCRATCH_MEMORY,
    MissionWorkspaceHandleKind.CODE_SANDBOX,
    MissionWorkspaceHandleKind.BROWSER_SESSION,
    MissionWorkspaceHandleKind.CHANNEL_DESTINATION_GRANTS,
    MissionWorkspaceHandleKind.WORKER_POOL,
    MissionWorkspaceHandleKind.RECEIPT_LEDGER,
    MissionWorkspaceHandleKind.REPLAY_LEDGER,
    MissionWorkspaceHandleKind.ARTIFACT_EXPORT,
)


_HANDLE_BACKEND_BINDINGS: dict[MissionWorkspaceHandleKind, str] = {
    MissionWorkspaceHandleKind.WORKSPACE_FILES: "workspace_root",
    MissionWorkspaceHandleKind.SCRATCH_MEMORY: "operator_memory_candidate",
    MissionWorkspaceHandleKind.CODE_SANDBOX: "code_execution_sandbox",
    MissionWorkspaceHandleKind.BROWSER_SESSION: "browser_control",
    MissionWorkspaceHandleKind.CHANNEL_DESTINATION_GRANTS: "bounded_channel",
    MissionWorkspaceHandleKind.WORKER_POOL: "worker_fleet",
    MissionWorkspaceHandleKind.RECEIPT_LEDGER: "receipt_ledger",
    MissionWorkspaceHandleKind.REPLAY_LEDGER: "replay_ledger",
    MissionWorkspaceHandleKind.ARTIFACT_EXPORT: "artifact_export",
}


class MissionWorkspaceHandle(SentinelModel):
    handle_id: str
    kind: MissionWorkspaceHandleKind
    safe_ref: str
    relative_path: str
    product_body_role: str
    backend_binding: str
    backend_status: str = "reserved"
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _handle_is_data_only(self) -> "MissionWorkspaceHandle":
        assert_data_not_authority(
            context="mission_workspace_handle",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class MissionWorkspaceManifest(SentinelModel):
    manifest_id: str
    mission_id: str
    workspace_root_ref: str
    workspace_root_hash: str
    allowed_domain_hashes: tuple[str, ...] = ()
    channel_destination_ref_hashes: tuple[str, ...] = ()
    handles: tuple[MissionWorkspaceHandle, ...]
    product_spine_entrypoint: str = "RuntimeHost -> MissionWorkspaceRuntime -> ProductActionKernel"
    registered_new_dispatch_adapter: bool = False
    live_external_power_enabled: bool = False
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False
    manifest_hash: str = ""
    manifest_path: str | None = Field(default=None, exclude=True)

    @model_validator(mode="after")
    def _manifest_is_data_only(self) -> "MissionWorkspaceManifest":
        assert_data_not_authority(
            context="mission_workspace_manifest",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        kinds = [handle.kind for handle in self.handles]
        if kinds != list(MISSION_WORKSPACE_HANDLE_ORDER):
            raise ValueError("mission_workspace_handles_must_match_product_body_order")
        if self.registered_new_dispatch_adapter is not False or self.live_external_power_enabled is not False:
            raise ValueError("mission_workspace_manifest_cannot_enable_live_power")
        self.manifest_hash = stable_hash(self.safe_model_dump(include_hash=False))
        return self

    def safe_model_dump(self, *, include_hash: bool = True, include_manifest_path: bool = False) -> dict[str, Any]:
        payload = self.model_dump(mode="json", exclude={"manifest_path"})
        payload["handles"] = [handle.safe_model_dump() for handle in self.handles]
        if not include_hash:
            payload["manifest_hash"] = ""
        if include_manifest_path and self.manifest_path:
            payload["manifest_path"] = self.manifest_path
        return payload


class MissionWorkspaceRuntime:
    """Data-only product body registry for a mission run.

    Pack 3 intentionally does not execute these handles. It gives the product
    spine one stable place to find the workspace body that later skills use.
    """

    def __init__(self, kernel: MissionKernel) -> None:
        self._kernel = kernel

    def prepare(
        self,
        *,
        mission_id: str,
        workspace_root: Path | str,
        allowed_domains: tuple[str, ...] = (),
        channel_destination_refs: tuple[str, ...] = (),
    ) -> MissionWorkspaceManifest:
        workspace = Path(workspace_root)
        if not workspace.exists():
            raise ValueError("mission_workspace_root_not_found")
        if not workspace.is_dir():
            raise ValueError("mission_workspace_root_not_directory")
        resolved_workspace = workspace.resolve()
        workspace_hash = stable_hash({"workspace_root": str(resolved_workspace)})

        mission_dir = self._kernel.store.mission_dir(mission_id, create=True)
        workspace_dir = mission_dir / "mission_workspace"
        _mkdir_path(workspace_dir)

        handles = tuple(
            self._handle_for(
                mission_id=mission_id,
                workspace_dir=workspace_dir,
                kind=kind,
            )
            for kind in MISSION_WORKSPACE_HANDLE_ORDER
        )
        manifest_path = workspace_dir / "manifest.json"
        manifest = MissionWorkspaceManifest(
            manifest_id=f"mission_workspace_{stable_hash({'mission_id': mission_id})[:16]}",
            mission_id=mission_id,
            workspace_root_ref=f"workspace_root_hash:{workspace_hash}",
            workspace_root_hash=workspace_hash,
            allowed_domain_hashes=tuple(
                stable_hash({"allowed_domain": domain}) for domain in sorted(set(allowed_domains))
            ),
            channel_destination_ref_hashes=tuple(
                stable_hash({"channel_destination_ref": ref}) for ref in sorted(set(channel_destination_refs))
            ),
            handles=handles,
            manifest_path=str(manifest_path),
        )
        self._kernel.store.atomic_write_json(manifest_path, manifest.safe_model_dump())
        self._kernel.store.append_event(
            mission_id,
            event_type="mission_workspace_prepared",
            safe_summary="Mission workspace product body prepared.",
            metadata={
                "manifest_id": manifest.manifest_id,
                "manifest_hash": manifest.manifest_hash,
                "handle_count": len(manifest.handles),
                "workspace_root_ref": manifest.workspace_root_ref,
                "allowed_domain_count": len(manifest.allowed_domain_hashes),
                "channel_destination_ref_count": len(manifest.channel_destination_ref_hashes),
            },
        )
        return manifest

    def _handle_for(
        self,
        *,
        mission_id: str,
        workspace_dir: Path,
        kind: MissionWorkspaceHandleKind,
    ) -> MissionWorkspaceHandle:
        directory_name = "artifact_exports" if kind is MissionWorkspaceHandleKind.ARTIFACT_EXPORT else kind.value
        handle_dir = workspace_dir / directory_name
        _mkdir_path(handle_dir)
        relative_path = f"mission_workspace/{directory_name}"
        handle_hash = stable_hash({"mission_id": mission_id, "kind": kind.value, "relative_path": relative_path})
        return MissionWorkspaceHandle(
            handle_id=f"mission_workspace_handle_{kind.value}_{handle_hash[:12]}",
            kind=kind,
            safe_ref=f"mission_workspace:{kind.value}:{handle_hash[:16]}",
            relative_path=relative_path,
            product_body_role=kind.value,
            backend_binding=_HANDLE_BACKEND_BINDINGS[kind],
        )


def mission_workspace_product_body_frame() -> dict[str, Any]:
    return {
        "entrypoint_id": "mission_workspace_runtime",
        "enabled": True,
        "primary_role": "product_body",
        "runtime_owner": "RuntimeHost -> MissionWorkspaceRuntime",
        "owned_handles": [kind.value for kind in MISSION_WORKSPACE_HANDLE_ORDER],
        "handle_backend_bindings": {kind.value: _HANDLE_BACKEND_BINDINGS[kind] for kind in MISSION_WORKSPACE_HANDLE_ORDER},
        "product_spine_entrypoint": "RuntimeHost -> MissionWorkspaceRuntime -> ProductActionKernel",
        "action_envelope_language": "internal_runtime_only",
        "data_not_authority": True,
        "authority_effect": "none",
        "can_grant_authority": False,
        "can_execute": False,
        "hard_boundaries": [
            "payment",
            "credential_access",
            "login_or_account_mutation",
            "contact_supplier_outside_grant",
            "workspace_escape",
            "destructive_write_outside_authority",
            "provider_native_tools",
            "fallback_auto",
            "replay_side_effects",
            "raw_session_or_cookie_persistence",
        ],
    }
