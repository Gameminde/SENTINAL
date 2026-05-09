from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Any

from pydantic import model_validator

from sentinel.organs.desktop.action_lifecycle import SidecarRPCDryRun
from sentinel.organs.desktop.action_preview import DesktopActionPreview
from sentinel.organs.desktop.clipboard_sanitizer import ClipboardSanitizer
from sentinel.organs.desktop.enrollment import SidecarEnrollmentGrant
from sentinel.organs.desktop.kill_switch import SidecarKillSwitch
from sentinel.organs.desktop.receipts import DesktopActionReceipt
from sentinel.organs.desktop.screen_sanitizer import ScreenContextSanitizer
from sentinel.organs.desktop.sidecar_manifest import PermissionedSidecarManifest
from sentinel.organs.lanes import AutonomyRiskLane
from sentinel.shared.models import SentinelModel


OBSERVATION_METHODS = {"desktop_list_windows", "get_window_metadata"}
SCREEN_METHODS = {"capture_screen", "desktop_screenshot"}
CLIPBOARD_METHODS = {"get_clipboard", "set_clipboard"}
FILESYSTEM_METHODS = {"read_file", "write_file"}
MUTATION_METHODS = {"desktop_click", "desktop_type", "desktop_press_keys", "desktop_launch_app", "desktop_focus_window"}
ADMIN_METHODS = {"get_config", "update_config"}


class FakeSidecarDryRunResult(SentinelModel):
    preview: DesktopActionPreview
    receipt: DesktopActionReceipt


class FakeSidecarProvider(SentinelModel):
    manifest: PermissionedSidecarManifest
    enrollment: SidecarEnrollmentGrant
    live_host_control_enabled: bool = False
    vendor_runtime_bridge: bool = False

    @model_validator(mode="after")
    def _validate(self) -> FakeSidecarProvider:
        if self.live_host_control_enabled:
            raise ValueError("FakeSidecarProvider cannot enable live host control in P6L.")
        if self.vendor_runtime_bridge:
            raise ValueError("FakeSidecarProvider cannot bridge vendor runtime.")
        if self.manifest.sidecar_id != self.enrollment.sidecar_id:
            raise ValueError("FakeSidecarProvider sidecar id mismatch.")
        if self.manifest.policy_hash != self.enrollment.policy_hash:
            raise ValueError("FakeSidecarProvider policy hash mismatch.")
        return self

    def preview(self, request: SidecarRPCDryRun, *, kill_switch: SidecarKillSwitch | None = None) -> FakeSidecarDryRunResult:
        self._validate_operational_state(kill_switch)
        self._validate_target(request)
        lane = self._lane_for(request.method)
        requires_special_authority = request.method in {"update_config", "desktop_click", "desktop_type", "desktop_press_keys", "desktop_launch_app", "desktop_focus_window"}
        if request.method == "update_config" and not request.special_authority:
            raise ValueError("sidecar admin config mutation requires special authority")
        sanitized_summary = self._sanitized_summary(request)
        preview = DesktopActionPreview(
            mission_id=request.mission_id,
            sidecar_id=self.manifest.sidecar_id,
            method=request.method,
            action_family=request.action_family,
            target=request.target,
            lane=lane,
            sanitized_summary=sanitized_summary,
            authority_refs=request.authority_refs,
            evidence_refs=request.evidence_refs,
            trace_refs=request.trace_refs,
            requires_special_authority=requires_special_authority,
        )
        receipt = DesktopActionReceipt(
            mission_id=request.mission_id,
            sidecar_id=self.manifest.sidecar_id,
            action_family=request.action_family,
            method=request.method,
            target=request.target,
            lane=lane,
            authority_refs=request.authority_refs,
            evidence_refs=request.evidence_refs,
            trace_refs=request.trace_refs,
            sanitized_summary=sanitized_summary,
        )
        return FakeSidecarDryRunResult(preview=preview, receipt=receipt)

    def execute_live(self, preview: DesktopActionPreview) -> None:
        raise ValueError("P6L fake sidecar does not execute live host actions.")

    def _validate_operational_state(self, kill_switch: SidecarKillSwitch | None) -> None:
        if not self.enrollment.is_active():
            raise ValueError("stale or revoked sidecar enrollment")
        if kill_switch is not None:
            if kill_switch.sidecar_id != self.manifest.sidecar_id:
                raise ValueError("kill switch sidecar mismatch")
            if kill_switch.triggered or not kill_switch.execution_allowed:
                raise ValueError("fake sidecar blocked by kill switch")

    def _validate_target(self, request: SidecarRPCDryRun) -> None:
        expected = request.target.get("expected_window_id")
        actual = request.target.get("window_id")
        if expected and actual and expected != actual:
            raise ValueError("wrong target desktop mutation rejected")
        if request.method in FILESYSTEM_METHODS:
            path = str(request.target.get("path", ""))
            if ".." in PureWindowsPath(path).parts:
                raise ValueError("path traversal rejected")
            if path.startswith("/") or ":" in path:
                if not any(path.lower().startswith(root.lower()) for root in self.manifest.allowed_roots):
                    raise ValueError("path outside allowed roots")
            symlink_target = request.target.get("symlink_target")
            if symlink_target and not any(str(symlink_target).lower().startswith(root.lower()) for root in self.manifest.allowed_roots):
                raise ValueError("symlink escape rejected")

    def _sanitized_summary(self, request: SidecarRPCDryRun) -> str:
        payload: dict[str, Any] = {"method": request.method, "target": request.target}
        if request.text:
            payload["text"] = request.text
        if request.method in CLIPBOARD_METHODS:
            return ClipboardSanitizer().sanitize(str(payload)).text
        return ScreenContextSanitizer().sanitize(payload).text

    def _lane_for(self, method: str) -> AutonomyRiskLane:
        if method in OBSERVATION_METHODS:
            return AutonomyRiskLane.BLUE
        if method in SCREEN_METHODS | CLIPBOARD_METHODS | FILESYSTEM_METHODS | MUTATION_METHODS | ADMIN_METHODS:
            return AutonomyRiskLane.RED
        return AutonomyRiskLane.BLACK
