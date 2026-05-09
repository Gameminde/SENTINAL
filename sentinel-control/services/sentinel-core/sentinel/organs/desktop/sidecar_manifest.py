from __future__ import annotations

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel


JARVIS_BACKED_CAPABILITIES = {
    "terminal",
    "filesystem",
    "desktop",
    "browser",
    "clipboard",
    "screenshot",
    "system_info",
    "awareness",
}


class PermissionedSidecarManifest(SentinelModel):
    sidecar_id: str
    sidecar_name: str
    capabilities: list[str]
    allowed_roots: list[str] = Field(default_factory=list)
    policy_hash: str
    evidence_refs: list[str]
    live_host_control_enabled: bool = False
    vendor_runtime_bridge: bool = False
    vendor_code_copied: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> PermissionedSidecarManifest:
        if not self.sidecar_id:
            raise ValueError("PermissionedSidecarManifest requires sidecar id.")
        if not JARVIS_BACKED_CAPABILITIES.issubset(set(self.capabilities)):
            raise ValueError("PermissionedSidecarManifest must declare JARVIS-backed capability families.")
        if not self.allowed_roots:
            raise ValueError("PermissionedSidecarManifest requires allowed roots.")
        if not self.policy_hash:
            raise ValueError("PermissionedSidecarManifest requires policy hash.")
        if not self.evidence_refs:
            raise ValueError("PermissionedSidecarManifest requires evidence refs.")
        if self.live_host_control_enabled:
            raise ValueError("PermissionedSidecarManifest cannot enable live host control in P6L.")
        if self.vendor_runtime_bridge:
            raise ValueError("PermissionedSidecarManifest cannot bridge vendor runtime.")
        if self.vendor_code_copied:
            raise ValueError("PermissionedSidecarManifest cannot copy vendor code.")
        if self.authority_expansion:
            raise ValueError("PermissionedSidecarManifest cannot expand authority.")
        return self
