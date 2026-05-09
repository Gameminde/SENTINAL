from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.models import SentinelModel, new_id


SUPPORTED_DRY_RUN_METHODS = {
    "desktop_list_windows",
    "get_window_metadata",
    "capture_screen",
    "desktop_screenshot",
    "get_clipboard",
    "set_clipboard",
    "read_file",
    "write_file",
    "desktop_click",
    "desktop_type",
    "desktop_press_keys",
    "desktop_launch_app",
    "desktop_focus_window",
    "get_config",
    "update_config",
}


class SidecarRPCDryRun(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("drpc"))
    mission_id: str = "mission_desktop"
    method: str
    action_family: str
    target: dict[str, Any] = Field(default_factory=dict)
    text: str | None = None
    special_authority: bool = False
    authority_refs: list[str] = Field(default_factory=lambda: ["p6l_fake_sidecar_authority"])
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=lambda: ["p6l_fake_sidecar_trace"])
    live_host_control_requested: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> SidecarRPCDryRun:
        if self.method not in SUPPORTED_DRY_RUN_METHODS:
            raise ValueError(f"unsupported desktop dry-run method:{self.method}")
        if not self.action_family:
            raise ValueError("SidecarRPCDryRun requires action family.")
        if not self.authority_refs:
            raise ValueError("SidecarRPCDryRun requires authority refs.")
        if not self.evidence_refs:
            raise ValueError("SidecarRPCDryRun requires evidence refs.")
        if self.live_host_control_requested:
            raise ValueError("SidecarRPCDryRun cannot request live host control in P6L.")
        if self.authority_expansion:
            raise ValueError("SidecarRPCDryRun cannot expand authority.")
        return self
