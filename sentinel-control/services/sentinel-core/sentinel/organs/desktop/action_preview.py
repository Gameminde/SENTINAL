from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from sentinel.organs.contracts import OrganPromotionLevel
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel, new_id


class DesktopActionPreview(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("dprev"))
    mission_id: str
    sidecar_id: str
    method: str
    action_family: str
    target: dict[str, Any] = Field(default_factory=dict)
    lane: AutonomyRiskLane
    sanitized_summary: str
    authority_refs: list[str]
    evidence_refs: list[str]
    trace_refs: list[str] = Field(default_factory=list)
    preview_only: bool = True
    requires_special_authority: bool = False
    execution_started: bool = False
    live_host_control_enabled: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> DesktopActionPreview:
        if not self.authority_refs:
            raise ValueError("DesktopActionPreview requires authority refs.")
        if not self.evidence_refs:
            raise ValueError("DesktopActionPreview requires evidence refs.")
        if not self.preview_only:
            raise ValueError("DesktopActionPreview must remain preview-only in P6L.")
        if self.execution_started:
            raise ValueError("DesktopActionPreview cannot start host execution in P6L.")
        if self.live_host_control_enabled:
            raise ValueError("DesktopActionPreview cannot enable live host control in P6L.")
        if self.authority_expansion:
            raise ValueError("DesktopActionPreview cannot expand authority.")
        return self


class DesktopHighPowerSurface(SentinelModel):
    surface_name: str
    lane: AutonomyRiskLane
    promotion_path: OrganPromotionLevel
    requires_special_authority: bool = False
    description: str
    evidence_refs: list[str]

    @classmethod
    def defaults(cls) -> list[DesktopHighPowerSurface]:
        return [
            cls(
                surface_name="window_metadata_system_info_awareness",
                lane=AutonomyRiskLane.BLUE,
                promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
                description="Read-only window metadata, system info, and awareness observation.",
                evidence_refs=["p6k_desktop_harvest"],
            ),
            cls(
                surface_name="screenshot_clipboard_filesystem_preview",
                lane=AutonomyRiskLane.RED,
                promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
                description="Sanitized screenshot, clipboard, and filesystem preview surfaces.",
                evidence_refs=["p6k_desktop_harvest"],
            ),
            cls(
                surface_name="click_type_keys_launch_focus",
                lane=AutonomyRiskLane.RED,
                promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
                requires_special_authority=True,
                description="Desktop mutation previews for click, type, keypress, launch, and focus.",
                evidence_refs=["p6k_desktop_harvest"],
            ),
            cls(
                surface_name="sidecar_admin_config",
                lane=AutonomyRiskLane.RED,
                promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
                requires_special_authority=True,
                description="Sidecar administrative configuration mutation preview.",
                evidence_refs=["p6k_desktop_harvest"],
            ),
        ]
