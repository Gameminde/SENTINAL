from __future__ import annotations

import pytest

from sentinel.agent import EventBus
from sentinel.agent.events import AgentEventType
from sentinel.organs import (
    DesktopActionLifecycle,
    DesktopCapabilityMap,
    DesktopFailureMode,
    DesktopHarvestIntegrator,
    DesktopPermissionSurface,
    DesktopSidecarBlueprint,
    DesktopVendorPattern,
    OrganPromotionLevel,
)


def build_map() -> DesktopCapabilityMap:
    return DesktopHarvestIntegrator().build_capability_map()


def build_blueprint() -> DesktopSidecarBlueprint:
    return DesktopHarvestIntegrator().build_sidecar_blueprint()


def test_desktop_harvest_is_source_backed_by_jarvis_openclaw_and_openjarvis():
    capability_map = build_map()

    assert capability_map.phase == "P6K_DESKTOP_AGENTLAB_HARVEST_AND_BLUEPRINT"
    assert capability_map.primary_source == "JARVIS"
    assert {"JARVIS", "OpenClaw", "OpenJarvis"} <= set(capability_map.source_systems)
    assert capability_map.current_promotion_level == OrganPromotionLevel.L1_EXTRACTION_MATRIX
    assert capability_map.target_promotion_level == OrganPromotionLevel.L2_SENTINEL_CONTRACT
    assert capability_map.runtime_powers_added == 0
    assert capability_map.live_desktop_execution_enabled is False
    assert capability_map.vendor_code_copied is False
    assert capability_map.vendor_runtime_bridge is False
    assert capability_map.authority_expansion is False
    assert all(pattern.evidence_refs for pattern in capability_map.vendor_patterns)
    assert all(pattern.source_files for pattern in capability_map.vendor_patterns)


def test_jarvis_capability_manifest_and_rpc_surface_are_harvested_not_copied():
    capability_map = build_map()

    assert {
        "terminal",
        "filesystem",
        "desktop",
        "browser",
        "clipboard",
        "screenshot",
        "system_info",
        "awareness",
    } <= set(capability_map.vendor_capabilities)
    assert {
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
    } <= set(capability_map.rpc_methods)
    assert "PermissionedSidecarManifest" in capability_map.sentinel_rewrites
    assert "DesktopActionLifecycle" in capability_map.sentinel_rewrites


def test_sidecar_blueprint_models_power_without_live_execution():
    blueprint = build_blueprint()

    assert isinstance(blueprint, DesktopSidecarBlueprint)
    assert blueprint.live_desktop_execution_enabled is False
    assert blueprint.host_control_enabled is False
    assert blueprint.vendor_runtime_bridge is False
    assert blueprint.vendor_code_copied is False
    assert blueprint.authority_expansion is False
    assert "signed_enrollment" in blueprint.enrollment_model
    assert "revocation" in blueprint.enrollment_model
    assert "rpc_dry_run_preview" in blueprint.rpc_model
    assert "screen_context_sanitizer" in blueprint.observation_model
    assert "approval_gate" in blueprint.approval_model
    assert "sidecar_kill_switch" in blueprint.kill_switch_model
    assert "trace_replay_record" in blueprint.trace_schema


def test_permission_surfaces_separate_observation_from_critical_host_actions():
    capability_map = build_map()
    surfaces = {surface.surface_name: surface for surface in capability_map.permission_surfaces}

    assert surfaces["window_metadata_observation"].execution_enabled is False
    assert "Blue" in surfaces["window_metadata_observation"].autonomy_lane
    assert surfaces["sanitized_screenshot_observation"].requires_sanitizer is True
    assert "desktop_click_type_keys_launch" in surfaces
    assert surfaces["desktop_click_type_keys_launch"].requires_approval is True
    assert "desktop_action_preview" in surfaces["desktop_click_type_keys_launch"].required_controls
    assert "sidecar_admin_config_mutation" in surfaces
    assert surfaces["sidecar_admin_config_mutation"].requires_special_authority is True


def test_critical_action_lifecycle_requires_preview_approval_trace_and_finalgate():
    capability_map = build_map()
    lifecycles = {lifecycle.action_class: lifecycle for lifecycle in capability_map.action_lifecycles}

    critical = lifecycles["desktop_mutation"]
    assert isinstance(critical, DesktopActionLifecycle)
    assert critical.execution_enabled is False
    assert critical.lifecycle_steps == [
        "classify_authority",
        "prepare_preview",
        "sanitize_context",
        "risk_score",
        "approval_gate",
        "dry_run_receipt",
        "kill_switch_check",
        "FinalGate",
        "trace_record",
    ]


def test_failure_modes_cover_real_desktop_sidecar_edge_cases():
    capability_map = build_map()
    failures = {failure.failure_mode for failure in capability_map.failure_modes}

    assert {
        "path_traversal_or_blocklist_bypass",
        "shell_string_execution_bypass",
        "screenshot_or_clipboard_secret_leak",
        "sidecar_admin_config_escalation",
        "stale_or_revoked_sidecar_token",
        "desktop_keystroke_wrong_target",
    } <= failures
    assert all(isinstance(failure, DesktopFailureMode) for failure in capability_map.failure_modes)
    assert all(failure.required_test for failure in capability_map.failure_modes)


def test_desktop_harvest_rejects_vendor_runtime_code_copy_authority_expansion_and_live_execution():
    pattern = build_map().vendor_patterns[0]

    with pytest.raises(ValueError, match="vendor runtime"):
        DesktopVendorPattern(**pattern.model_dump(exclude={"vendor_runtime_bridge"}), vendor_runtime_bridge=True)
    with pytest.raises(ValueError, match="vendor code"):
        DesktopVendorPattern(**pattern.model_dump(exclude={"vendor_code_copied"}), vendor_code_copied=True)

    surface = build_map().permission_surfaces[0]
    with pytest.raises(ValueError, match="expand authority"):
        DesktopPermissionSurface(**surface.model_dump(exclude={"authority_expansion"}), authority_expansion=True)

    lifecycle = build_map().action_lifecycles[0]
    with pytest.raises(ValueError, match="live desktop execution"):
        DesktopActionLifecycle(**lifecycle.model_dump(exclude={"execution_enabled"}), execution_enabled=True)

    blueprint = build_blueprint()
    with pytest.raises(ValueError, match="host control"):
        DesktopSidecarBlueprint(**blueprint.model_dump(exclude={"host_control_enabled"}), host_control_enabled=True)


def test_desktop_harvest_records_trace_without_execution():
    bus = EventBus("mission_p6k_desktop")

    capability_map = DesktopHarvestIntegrator().build_capability_map(event_bus=bus)
    blueprint = DesktopHarvestIntegrator().build_sidecar_blueprint(event_bus=bus)

    assert capability_map.trace_refs
    assert blueprint.trace_refs
    assert bus.verify_chain() is True
    assert bus.events()[0].event_type == AgentEventType.DESKTOP_AGENTLAB_HARVEST_BUILT.value
    assert bus.events()[-1].event_type == AgentEventType.DESKTOP_SIDECAR_BLUEPRINT_BUILT.value
    assert all(event.payload["runtime_powers_added"] == 0 for event in bus.events())
    assert all(event.payload["authority_expansion"] is False for event in bus.events())
