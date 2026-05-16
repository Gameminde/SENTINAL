from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field, model_validator

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.organs.contracts import OrganPromotionLevel
from sentinel.shared.models import SentinelModel


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


class DesktopVendorPattern(SentinelModel):
    id: str = ""
    source_system: str
    pattern_name: str
    source_files: list[str]
    mechanism: str
    sentinel_rewrite: str
    extracted_power: str
    high_power_surfaces: list[str]
    black_lane_misuse_objectives: list[str] = Field(default_factory=list)
    required_controls: list[str]
    evidence_refs: list[str]
    vendor_runtime_bridge: bool = False
    vendor_code_copied: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> DesktopVendorPattern:
        if not self.source_files:
            raise ValueError("DesktopVendorPattern requires source files.")
        if not self.high_power_surfaces:
            raise ValueError("DesktopVendorPattern requires high-power surfaces.")
        if not self.required_controls:
            raise ValueError("DesktopVendorPattern requires controls.")
        if not self.evidence_refs:
            raise ValueError("DesktopVendorPattern requires evidence refs.")
        if self.vendor_runtime_bridge:
            raise ValueError("DesktopVendorPattern cannot bridge vendor runtime.")
        if self.vendor_code_copied:
            raise ValueError("DesktopVendorPattern cannot copy vendor code.")
        if self.authority_expansion:
            raise ValueError("DesktopVendorPattern cannot expand authority.")
        if not self.id:
            self.id = _stable_id(
                "dpattern",
                {
                    "source_system": self.source_system,
                    "pattern_name": self.pattern_name,
                    "sentinel_rewrite": self.sentinel_rewrite,
                    "evidence_refs": self.evidence_refs,
                },
            )
        return self


class DesktopPermissionSurface(SentinelModel):
    id: str = ""
    surface_name: str
    capability: str
    actions: list[str]
    autonomy_lane: str
    required_authority_fields: list[str]
    required_controls: list[str]
    promotion_path: OrganPromotionLevel
    requires_sanitizer: bool = False
    requires_approval: bool = False
    requires_special_authority: bool = False
    execution_enabled: bool = False
    evidence_refs: list[str]
    source_refs: list[str]
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> DesktopPermissionSurface:
        if not self.actions:
            raise ValueError("DesktopPermissionSurface requires actions.")
        if not self.required_authority_fields:
            raise ValueError("DesktopPermissionSurface requires authority fields.")
        if not self.required_controls:
            raise ValueError("DesktopPermissionSurface requires controls.")
        if not self.evidence_refs:
            raise ValueError("DesktopPermissionSurface requires evidence refs.")
        if not self.source_refs:
            raise ValueError("DesktopPermissionSurface requires source refs.")
        if self.execution_enabled:
            raise ValueError("DesktopPermissionSurface cannot enable live desktop execution in P6K.")
        if self.authority_expansion:
            raise ValueError("DesktopPermissionSurface cannot expand authority.")
        if self.requires_special_authority and "special_authority" not in self.required_controls:
            raise ValueError("DesktopPermissionSurface special authority surfaces must declare special_authority control.")
        if not self.id:
            self.id = _stable_id(
                "dsurface",
                {
                    "surface_name": self.surface_name,
                    "capability": self.capability,
                    "actions": self.actions,
                    "promotion_path": self.promotion_path.value,
                },
            )
        return self


class DesktopActionLifecycle(SentinelModel):
    id: str = ""
    action_class: str
    source_pattern: str
    lifecycle_steps: list[str]
    receipt_requirements: list[str]
    trace_requirements: list[str]
    evidence_refs: list[str]
    source_refs: list[str]
    execution_enabled: bool = False
    authority_expansion: bool = False

    @model_validator(mode="after")
    def _validate(self) -> DesktopActionLifecycle:
        if not self.lifecycle_steps:
            raise ValueError("DesktopActionLifecycle requires lifecycle steps.")
        if not self.receipt_requirements:
            raise ValueError("DesktopActionLifecycle requires receipt requirements.")
        if not self.trace_requirements:
            raise ValueError("DesktopActionLifecycle requires trace requirements.")
        if not self.evidence_refs:
            raise ValueError("DesktopActionLifecycle requires evidence refs.")
        if not self.source_refs:
            raise ValueError("DesktopActionLifecycle requires source refs.")
        if self.execution_enabled:
            raise ValueError("DesktopActionLifecycle cannot enable live desktop execution in P6K.")
        if self.authority_expansion:
            raise ValueError("DesktopActionLifecycle cannot expand authority.")
        if self.action_class in {"desktop_mutation", "sidecar_admin"}:
            needed = {"approval_gate", "dry_run_receipt", "kill_switch_check", "FinalGate", "trace_record"}
            if not needed.issubset(set(self.lifecycle_steps)):
                raise ValueError("DesktopActionLifecycle critical actions require preview approval trace and FinalGate.")
        if not self.id:
            self.id = _stable_id("dlifecycle", {"action_class": self.action_class, "source_pattern": self.source_pattern})
        return self


class DesktopFailureMode(SentinelModel):
    id: str = ""
    failure_mode: str
    source_pattern: str
    sentinel_prevention: str
    required_test: str
    evidence_refs: list[str]
    source_refs: list[str]

    @model_validator(mode="after")
    def _validate(self) -> DesktopFailureMode:
        if not self.sentinel_prevention:
            raise ValueError("DesktopFailureMode requires Sentinel prevention.")
        if not self.required_test:
            raise ValueError("DesktopFailureMode requires required test.")
        if not self.evidence_refs:
            raise ValueError("DesktopFailureMode requires evidence refs.")
        if not self.source_refs:
            raise ValueError("DesktopFailureMode requires source refs.")
        if not self.id:
            self.id = _stable_id("dfail", {"failure_mode": self.failure_mode, "source_pattern": self.source_pattern})
        return self


class DesktopCapabilityMap(SentinelModel):
    id: str = ""
    phase: str = "P6K_DESKTOP_AGENTLAB_HARVEST_AND_BLUEPRINT"
    primary_source: str = "JARVIS"
    source_systems: list[str]
    source_paths: list[str]
    vendor_capabilities: list[str]
    rpc_methods: list[str]
    sentinel_rewrites: list[str]
    vendor_patterns: list[DesktopVendorPattern]
    permission_surfaces: list[DesktopPermissionSurface]
    action_lifecycles: list[DesktopActionLifecycle]
    failure_modes: list[DesktopFailureMode]
    current_promotion_level: OrganPromotionLevel = OrganPromotionLevel.L1_EXTRACTION_MATRIX
    target_promotion_level: OrganPromotionLevel = OrganPromotionLevel.L2_SENTINEL_CONTRACT
    runtime_powers_added: int = 0
    live_desktop_execution_enabled: bool = False
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> DesktopCapabilityMap:
        if self.primary_source != "JARVIS":
            raise ValueError("DesktopCapabilityMap primary source must be JARVIS.")
        if not {"JARVIS", "OpenClaw", "OpenJarvis"}.issubset(set(self.source_systems)):
            raise ValueError("DesktopCapabilityMap requires JARVIS, OpenClaw, and OpenJarvis sources.")
        if not self.source_paths:
            raise ValueError("DesktopCapabilityMap requires source paths.")
        if not self.vendor_patterns:
            raise ValueError("DesktopCapabilityMap requires vendor patterns.")
        if not self.permission_surfaces:
            raise ValueError("DesktopCapabilityMap requires permission surfaces.")
        if not self.action_lifecycles:
            raise ValueError("DesktopCapabilityMap requires action lifecycles.")
        if not self.failure_modes:
            raise ValueError("DesktopCapabilityMap requires failure modes.")
        if self.runtime_powers_added != 0:
            raise ValueError("DesktopCapabilityMap cannot add runtime powers.")
        if self.live_desktop_execution_enabled:
            raise ValueError("DesktopCapabilityMap cannot enable live desktop execution in P6K.")
        if self.vendor_code_copied:
            raise ValueError("DesktopCapabilityMap cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("DesktopCapabilityMap cannot bridge vendor runtime.")
        if self.authority_expansion:
            raise ValueError("DesktopCapabilityMap cannot expand authority.")
        if not self.id:
            self.id = _stable_id(
                "dcapmap",
                {
                    "phase": self.phase,
                    "source_systems": self.source_systems,
                    "sentinel_rewrites": self.sentinel_rewrites,
                    "pattern_ids": [pattern.id for pattern in self.vendor_patterns],
                },
            )
        return self

    def record(self, event_bus: EventBus | None = None) -> DesktopCapabilityMap:
        if event_bus is None:
            return self
        event = event_bus.append(
            AgentEventType.DESKTOP_AGENTLAB_HARVEST_BUILT,
            "Desktop AgentLab harvest built from source-backed vendor patterns without host execution.",
            payload={
                "capability_map_id": self.id,
                "phase": self.phase,
                "primary_source": self.primary_source,
                "source_systems": self.source_systems,
                "runtime_powers_added": 0,
                "live_desktop_execution_enabled": False,
                "vendor_code_copied": False,
                "vendor_runtime_bridge": False,
                "authority_expansion": False,
            },
        )
        return self.model_copy(update={"trace_refs": [*self.trace_refs, event.id]})


class DesktopSidecarBlueprint(SentinelModel):
    id: str = ""
    phase: str = "P6K_DESKTOP_AGENTLAB_HARVEST_AND_BLUEPRINT"
    blueprint_name: str = "SentinelPermissionedSidecarBlueprint"
    source_systems: list[str]
    enrollment_model: list[str]
    capability_manifest_model: list[str]
    rpc_model: list[str]
    observation_model: list[str]
    filesystem_model: list[str]
    clipboard_model: list[str]
    desktop_action_model: list[str]
    approval_model: list[str]
    kill_switch_model: list[str]
    trace_schema: list[str]
    required_evals: list[str]
    source_refs: list[str]
    evidence_refs: list[str]
    current_promotion_level: OrganPromotionLevel = OrganPromotionLevel.L2_SENTINEL_CONTRACT
    target_promotion_level: OrganPromotionLevel = OrganPromotionLevel.L3_FAKE_EVAL
    live_desktop_execution_enabled: bool = False
    host_control_enabled: bool = False
    vendor_code_copied: bool = False
    vendor_runtime_bridge: bool = False
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> DesktopSidecarBlueprint:
        required_lists = [
            self.enrollment_model,
            self.capability_manifest_model,
            self.rpc_model,
            self.observation_model,
            self.filesystem_model,
            self.clipboard_model,
            self.desktop_action_model,
            self.approval_model,
            self.kill_switch_model,
            self.trace_schema,
            self.required_evals,
            self.source_refs,
            self.evidence_refs,
        ]
        if any(not item for item in required_lists):
            raise ValueError("DesktopSidecarBlueprint requires complete blueprint sections.")
        if self.live_desktop_execution_enabled:
            raise ValueError("DesktopSidecarBlueprint cannot enable live desktop execution in P6K.")
        if self.host_control_enabled:
            raise ValueError("DesktopSidecarBlueprint cannot enable host control in P6K.")
        if self.vendor_code_copied:
            raise ValueError("DesktopSidecarBlueprint cannot copy vendor code.")
        if self.vendor_runtime_bridge:
            raise ValueError("DesktopSidecarBlueprint cannot bridge vendor runtime.")
        if self.authority_expansion:
            raise ValueError("DesktopSidecarBlueprint cannot expand authority.")
        if not self.id:
            self.id = _stable_id(
                "dblueprint",
                {
                    "blueprint_name": self.blueprint_name,
                    "source_systems": self.source_systems,
                    "source_refs": self.source_refs,
                    "evidence_refs": self.evidence_refs,
                },
            )
        return self

    def record(self, event_bus: EventBus | None = None) -> DesktopSidecarBlueprint:
        if event_bus is None:
            return self
        event = event_bus.append(
            AgentEventType.DESKTOP_SIDECAR_BLUEPRINT_BUILT,
            "Desktop sidecar blueprint built without vendor runtime bridge or host control.",
            payload={
                "blueprint_id": self.id,
                "phase": self.phase,
                "source_systems": self.source_systems,
                "runtime_powers_added": 0,
                "live_desktop_execution_enabled": False,
                "host_control_enabled": False,
                "vendor_code_copied": False,
                "vendor_runtime_bridge": False,
                "authority_expansion": False,
            },
        )
        return self.model_copy(update={"trace_refs": [*self.trace_refs, event.id]})


class DesktopHarvestIntegrator:
    def build_capability_map(self, *, event_bus: EventBus | None = None) -> DesktopCapabilityMap:
        capability_map = DesktopCapabilityMap(
            source_systems=["JARVIS", "OpenClaw", "OpenJarvis"],
            source_paths=[
                "agent-lab/audits/final/jarvis_final_forensic_report.md",
                "agent-lab/audits/jarvis_sidecar_map.md",
                "agent-lab/audits/jarvis_desktop_awareness_map.md",
                "agent-lab/audits/jarvis_permission_map.md",
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/audits/final/openjarvis_final_forensic_report.md",
            ],
            vendor_capabilities=["terminal", "filesystem", "desktop", "browser", "clipboard", "screenshot", "system_info", "awareness"],
            rpc_methods=[
                "run_command",
                "read_file",
                "write_file",
                "list_directory",
                "get_clipboard",
                "set_clipboard",
                "capture_screen",
                "get_window_tree",
                "click_element",
                "type_text",
                "press_keys",
                "launch_app",
                "focus_window",
                "find_element",
                "get_config",
                "update_config",
            ],
            sentinel_rewrites=[
                "PermissionedSidecarManifest",
                "DesktopCapabilityMap",
                "DesktopActionLifecycle",
                "ScreenContextSanitizer",
                "ClipboardSanitizer",
                "SidecarEnrollmentGrant",
                "SidecarRPCDryRun",
                "DesktopActionPreview",
                "SidecarKillSwitch",
            ],
            vendor_patterns=_default_vendor_patterns(),
            permission_surfaces=_default_permission_surfaces(),
            action_lifecycles=_default_action_lifecycles(),
            failure_modes=_default_failure_modes(),
        )
        return capability_map.record(event_bus)

    def build_sidecar_blueprint(self, *, event_bus: EventBus | None = None) -> DesktopSidecarBlueprint:
        blueprint = DesktopSidecarBlueprint(
            source_systems=["JARVIS", "OpenClaw", "OpenJarvis"],
            enrollment_model=["signed_enrollment", "one_time_token_display", "token_expiry", "revocation", "device_manifest_review"],
            capability_manifest_model=["deny_by_default", "exact_capability_list", "allowed_roots", "allowed_apps", "clipboard_policy", "screenshot_policy", "policy_hash"],
            rpc_model=["rpc_dry_run_preview", "method_allowlist", "argument_hash", "detached_timeout", "result_classification", "replay_record"],
            observation_model=["window_metadata", "screen_context_sanitizer", "clipboard_sanitizer", "sensitivity_label", "retention_tier"],
            filesystem_model=["allow_roots_only", "canonical_path_resolution", "symlink_escape_check", "generated_workspace_write_scope"],
            clipboard_model=["opt_in_read", "redact_before_model", "no_raw_clipboard_persistence", "write_requires_preview"],
            desktop_action_model=["target_app_scope", "target_window_scope", "desktop_action_preview", "no_hidden_keystrokes", "approval_before_mutation"],
            approval_model=["authority_fit", "risk_score", "evidence_refs", "approval_gate", "one_time_nonce", "expiry"],
            kill_switch_model=["sidecar_kill_switch", "revoke_grants", "fail_pending_rpcs", "disable_capability"],
            trace_schema=["trace_replay_record", "sidecar_id", "capability", "method", "args_hash", "sanitizer_hash", "approval_id", "result_hash"],
            required_evals=[
                "fake_sidecar_capability_escalation",
                "path_traversal_and_symlink_escape",
                "shell_blocklist_bypass",
                "screen_secret_redaction",
                "clipboard_secret_redaction",
                "stale_token_rejection",
                "wrong_target_desktop_action",
            ],
            source_refs=[
                "agent-lab/vendors/jarvis/source/src/sidecar/types.ts",
                "agent-lab/vendors/jarvis/source/src/sidecar/manager.ts",
                "agent-lab/vendors/jarvis/source/sidecar/handlers.go",
                "agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts",
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/audits/final/openjarvis_final_forensic_report.md",
            ],
            evidence_refs=["jarvis_sidecar_map", "jarvis_desktop_awareness_map", "jarvis_permission_map", "openclaw_final", "openjarvis_final"],
        )
        return blueprint.record(event_bus)


def _default_vendor_patterns() -> list[DesktopVendorPattern]:
    return [
        DesktopVendorPattern(
            source_system="JARVIS",
            pattern_name="permissioned_sidecar_capability_manifest",
            source_files=[
                "agent-lab/vendors/jarvis/source/src/sidecar/types.ts",
                "agent-lab/vendors/jarvis/source/sidecar/handlers.go",
            ],
            mechanism="Sidecar advertises terminal/filesystem/desktop/browser/clipboard/screenshot/system_info/awareness and exposes RPC handlers by capability.",
            sentinel_rewrite="PermissionedSidecarManifest",
            extracted_power="multi-machine host-control capability routing",
            high_power_surfaces=["sidecar_capability_manifest", "sidecar_rpc_registry", "sidecar_admin_config"],
            black_lane_misuse_objectives=["capability_escalation_without_approval", "vendor_runtime_bridge"],
            required_controls=["signed_manifest", "capability_scope", "policy_hash", "revocation", "trace"],
            evidence_refs=["jarvis_sidecar_map", "jarvis_final"],
        ),
        DesktopVendorPattern(
            source_system="JARVIS",
            pattern_name="desktop_awareness_and_action_tools",
            source_files=[
                "agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts",
                "agent-lab/vendors/jarvis/source/sidecar/desktop_windows.go",
            ],
            mechanism="Desktop tools list windows, snapshot UI trees, find elements, screenshot, click, type, press keys, launch apps, and focus windows.",
            sentinel_rewrite="DesktopActionLifecycle",
            extracted_power="visual and structural desktop operation through UI element IDs",
            high_power_surfaces=["window_metadata", "ui_tree_snapshot", "screenshot_capture", "desktop_click_type_keys_launch"],
            black_lane_misuse_objectives=["hidden_keystrokes", "wrong_target_mutation", "secret_capture"],
            required_controls=["screen_context_sanitizer", "desktop_action_preview", "approval_gate", "FinalGate", "trace"],
            evidence_refs=["jarvis_desktop_awareness_map", "jarvis_final"],
        ),
        DesktopVendorPattern(
            source_system="OpenClaw",
            pattern_name="action_kernel_and_exec_approval_pattern",
            source_files=[
                "agent-lab/audits/final/openclaw_final_forensic_report.md",
                "agent-lab/vendors/openclaw/source/src/infra/exec-approvals.ts",
            ],
            mechanism="Gateway-centered action control and approval UX for high-impact exec/browser/channel surfaces.",
            sentinel_rewrite="DesktopActionPreview",
            extracted_power="action preview and approval loop that can be reused for desktop mutation",
            high_power_surfaces=["approval_ui", "action_preview", "exec_style_permission_prompt"],
            black_lane_misuse_objectives=["allow_always_for_high_impact_actions"],
            required_controls=["one_time_approval", "action_hash_binding", "expiry", "trace"],
            evidence_refs=["openclaw_final", "g9_synthesis"],
        ),
        DesktopVendorPattern(
            source_system="OpenJarvis",
            pattern_name="cost_and_sandbox_policy_for_local_execution",
            source_files=[
                "agent-lab/audits/final/openjarvis_final_forensic_report.md",
                "agent-lab/vendors/openjarvis/source/src/openjarvis/sandbox/runner.py",
            ],
            mechanism="Local execution and sandbox surfaces need budget, timeout, mount, telemetry, and policy routing before use.",
            sentinel_rewrite="DesktopCostAndSandboxPolicy",
            extracted_power="budget-aware local operation and sandbox gating for future desktop/code execution",
            high_power_surfaces=["local_execution_budget", "sandbox_mount_scope", "timeout_policy"],
            black_lane_misuse_objectives=["open_by_default_mounts", "host_shell_execution"],
            required_controls=["budget_cap", "mount_allowlist", "timeout", "telemetry_trace"],
            evidence_refs=["openjarvis_final", "g9_synthesis"],
        ),
    ]


def _default_permission_surfaces() -> list[DesktopPermissionSurface]:
    common_source = ["agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts", "agent-lab/audits/jarvis_desktop_awareness_map.md"]
    return [
        DesktopPermissionSurface(
            surface_name="window_metadata_observation",
            capability="desktop",
            actions=["desktop_list_windows"],
            autonomy_lane="Blue",
            required_authority_fields=["allowed_sidecar", "allowed_app_scope", "read_only"],
            required_controls=["authority_mapping", "trace", "context_minimization"],
            promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
            evidence_refs=["jarvis_desktop_awareness_map"],
            source_refs=common_source,
        ),
        DesktopPermissionSurface(
            surface_name="sanitized_screenshot_observation",
            capability="screenshot",
            actions=["desktop_screenshot", "capture_screen"],
            autonomy_lane="Red",
            required_authority_fields=["allowed_sidecar", "allowed_app_scope", "screenshot_policy", "retention_tier"],
            required_controls=["screen_context_sanitizer", "secret_redaction", "trace", "preview"],
            promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
            requires_sanitizer=True,
            requires_approval=True,
            evidence_refs=["jarvis_desktop_awareness_map", "jarvis_final"],
            source_refs=common_source,
        ),
        DesktopPermissionSurface(
            surface_name="clipboard_observation_and_write",
            capability="clipboard",
            actions=["get_clipboard", "set_clipboard"],
            autonomy_lane="Red",
            required_authority_fields=["allowed_sidecar", "clipboard_policy", "data_retention"],
            required_controls=["clipboard_sanitizer", "preview", "approval_gate", "trace"],
            promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
            requires_sanitizer=True,
            requires_approval=True,
            evidence_refs=["jarvis_sidecar_map", "jarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/sidecar/handlers.go", "agent-lab/audits/jarvis_sidecar_map.md"],
        ),
        DesktopPermissionSurface(
            surface_name="desktop_click_type_keys_launch",
            capability="desktop",
            actions=["desktop_click", "desktop_type", "desktop_press_keys", "desktop_launch_app", "desktop_focus_window"],
            autonomy_lane="Red",
            required_authority_fields=["allowed_sidecar", "allowed_app_scope", "target_window", "action_class", "approval_id"],
            required_controls=["special_authority", "desktop_action_preview", "approval_gate", "kill_switch", "FinalGate", "trace"],
            promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
            requires_approval=True,
            requires_special_authority=True,
            evidence_refs=["jarvis_desktop_awareness_map", "jarvis_permission_map", "jarvis_final"],
            source_refs=common_source,
        ),
        DesktopPermissionSurface(
            surface_name="sidecar_admin_config_mutation",
            capability="sidecar_admin",
            actions=["get_config", "update_config"],
            autonomy_lane="Red",
            required_authority_fields=["allowed_sidecar", "capability_manifest_hash", "admin_approval_id"],
            required_controls=["special_authority", "signed_manifest", "approval_gate", "revocation", "trace"],
            promotion_path=OrganPromotionLevel.L3_FAKE_EVAL,
            requires_approval=True,
            requires_special_authority=True,
            evidence_refs=["jarvis_sidecar_map", "jarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/sidecar/handlers.go", "agent-lab/vendors/jarvis/source/src/sidecar/manager.ts"],
        ),
    ]


def _default_action_lifecycles() -> list[DesktopActionLifecycle]:
    return [
        DesktopActionLifecycle(
            action_class="desktop_observation",
            source_pattern="window metadata and UI tree observation",
            lifecycle_steps=["classify_authority", "sanitize_context", "minimize_context", "trace_record"],
            receipt_requirements=["source_ref", "sanitizer_hash", "retention_tier"],
            trace_requirements=["sidecar_id", "capability", "method", "result_hash"],
            evidence_refs=["jarvis_desktop_awareness_map"],
            source_refs=["agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts"],
        ),
        DesktopActionLifecycle(
            action_class="desktop_mutation",
            source_pattern="click/type/keys/launch/focus host action",
            lifecycle_steps=[
                "classify_authority",
                "prepare_preview",
                "sanitize_context",
                "risk_score",
                "approval_gate",
                "dry_run_receipt",
                "kill_switch_check",
                "FinalGate",
                "trace_record",
            ],
            receipt_requirements=["preview_hash", "approval_id", "target_window", "expected_effect", "rollback_note"],
            trace_requirements=["mission_id", "sidecar_id", "action_hash", "policy_version", "result_hash"],
            evidence_refs=["jarvis_desktop_awareness_map", "jarvis_permission_map"],
            source_refs=["agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts", "agent-lab/vendors/jarvis/source/sidecar/handlers.go"],
        ),
        DesktopActionLifecycle(
            action_class="sidecar_admin",
            source_pattern="get_config/update_config administrative RPC",
            lifecycle_steps=[
                "classify_authority",
                "prepare_preview",
                "sanitize_context",
                "risk_score",
                "approval_gate",
                "dry_run_receipt",
                "kill_switch_check",
                "FinalGate",
                "trace_record",
            ],
            receipt_requirements=["manifest_before_hash", "manifest_after_hash", "approval_id", "revocation_plan"],
            trace_requirements=["sidecar_id", "admin_method", "args_hash", "policy_version", "result_hash"],
            evidence_refs=["jarvis_sidecar_map", "jarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/sidecar/handlers.go", "agent-lab/vendors/jarvis/source/src/sidecar/manager.ts"],
        ),
    ]


def _default_failure_modes() -> list[DesktopFailureMode]:
    return [
        DesktopFailureMode(
            failure_mode="path_traversal_or_blocklist_bypass",
            source_pattern="JARVIS filesystem RPC uses blocked path checks; OpenClaw/OpenJarvis show filesystem escape risks.",
            sentinel_prevention="canonical allow-root containment with symlink resolution before any future file action",
            required_test="fake_sidecar_path_traversal_and_symlink_escape",
            evidence_refs=["jarvis_sidecar_map", "openclaw_final", "openjarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/sidecar/handlers.go"],
        ),
        DesktopFailureMode(
            failure_mode="shell_string_execution_bypass",
            source_pattern="JARVIS run_command and OpenClaw/OpenJarvis shell surfaces accept shell-shaped execution.",
            sentinel_prevention="shell remains absent from desktop organ; future shell requires typed executor sandbox",
            required_test="shell_string_execution_is_not_part_of_desktop_blueprint",
            evidence_refs=["jarvis_sidecar_map", "openclaw_final", "openjarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/sidecar/handlers.go"],
        ),
        DesktopFailureMode(
            failure_mode="screenshot_or_clipboard_secret_leak",
            source_pattern="JARVIS screenshot and clipboard observers can deliver raw sensitive context.",
            sentinel_prevention="ScreenContextSanitizer and ClipboardSanitizer before storage or model ingestion",
            required_test="screen_and_clipboard_secret_redaction_fixture",
            evidence_refs=["jarvis_desktop_awareness_map", "jarvis_sidecar_map"],
            source_refs=["agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts", "agent-lab/vendors/jarvis/source/sidecar/handlers.go"],
        ),
        DesktopFailureMode(
            failure_mode="sidecar_admin_config_escalation",
            source_pattern="JARVIS registers update_config as an administrative sidecar RPC.",
            sentinel_prevention="admin config mutation becomes special-authority manifest change with signed approval",
            required_test="sidecar_config_mutation_requires_special_authority",
            evidence_refs=["jarvis_sidecar_map", "jarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/sidecar/handlers.go"],
        ),
        DesktopFailureMode(
            failure_mode="stale_or_revoked_sidecar_token",
            source_pattern="JARVIS validates JWT and enrolled sidecar status before connection.",
            sentinel_prevention="token expiry, one-time display, revocation ledger, and stale token rejection",
            required_test="stale_or_revoked_sidecar_token_rejected",
            evidence_refs=["jarvis_sidecar_map", "jarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/src/sidecar/manager.ts"],
        ),
        DesktopFailureMode(
            failure_mode="desktop_keystroke_wrong_target",
            source_pattern="Desktop tools can type or press keys into the focused app or cached element.",
            sentinel_prevention="target app/window binding, visible preview, one-time approval, and wrong-target fixture",
            required_test="desktop_keystroke_wrong_target_blocked",
            evidence_refs=["jarvis_desktop_awareness_map", "jarvis_final"],
            source_refs=["agent-lab/vendors/jarvis/source/src/actions/tools/desktop.ts"],
        ),
    ]
