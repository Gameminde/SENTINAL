from __future__ import annotations

from sentinel.organs.contracts import (
    REQUIRED_TRACE_EVENTS,
    ExternalOrganContract,
    OrganCapability,
    OrganPromotionLevel,
    OrganType,
    VendorHarvestReference,
)


def build_desktop_sidecar_organ_contract() -> ExternalOrganContract:
    authority_fields = [
        "allowed_sidecars",
        "allowed_actions",
        "allowed_paths",
        "allowed_apps",
        "allowed_windows",
        "special_authority_refs",
    ]
    supported_actions = [
        "desktop_rpc_dry_run",
        "desktop_observe_window_metadata",
        "desktop_screenshot_preview",
        "desktop_clipboard_preview",
        "desktop_filesystem_preview",
        "desktop_action_preview",
        "desktop_sidecar_config_preview",
    ]
    return ExternalOrganContract(
        organ_name="desktop_sidecar",
        organ_type=OrganType.DESKTOP_SIDECAR,
        version="0.1.0",
        description="Sentinel-native Desktop Sidecar Organ contract built from P6K JARVIS-first harvest.",
        promotion_level=OrganPromotionLevel.L3_FAKE_EVAL,
        capabilities=[
            OrganCapability(
                name="jarvis_backed_sidecar_manifest",
                description="Permissioned manifest for JARVIS-backed sidecar capability families.",
                actions=["desktop_rpc_dry_run"],
                authority_fields=["allowed_sidecars", "allowed_actions"],
                promotion_required=OrganPromotionLevel.L3_FAKE_EVAL,
                evidence_refs=["p6k_desktop_harvest"],
            ),
            OrganCapability(
                name="desktop_observation_preview",
                description="Window metadata, screenshot, clipboard, and filesystem previews with sanitizers.",
                actions=["desktop_observe_window_metadata", "desktop_screenshot_preview", "desktop_clipboard_preview", "desktop_filesystem_preview"],
                authority_fields=["allowed_sidecars", "allowed_actions", "allowed_paths", "allowed_apps", "allowed_windows"],
                promotion_required=OrganPromotionLevel.L3_FAKE_EVAL,
                evidence_refs=["p6k_desktop_harvest"],
            ),
            OrganCapability(
                name="desktop_mutation_preview",
                description="Preview-only click/type/key/launch/focus and sidecar admin mutations.",
                actions=["desktop_action_preview", "desktop_sidecar_config_preview"],
                authority_fields=["allowed_sidecars", "allowed_actions", "allowed_apps", "allowed_windows", "special_authority_refs"],
                promotion_required=OrganPromotionLevel.L3_FAKE_EVAL,
                evidence_refs=["p6k_desktop_harvest"],
            ),
        ],
        supported_actions=supported_actions,
        authority_fields=authority_fields,
        required_trace_events=sorted(REQUIRED_TRACE_EVENTS),
        source_refs=[
            VendorHarvestReference(
                source_system="JARVIS",
                source_path="agent-lab/audits/jarvis_desktop_static_audit.md",
                mechanism="Sidecar capability manifest, enrollment, desktop awareness, and RPC registry.",
                sentinel_rewrite="PermissionedSidecarManifest",
                evidence_refs=["p6k_desktop_harvest", "jarvis_desktop_static_audit"],
            ),
            VendorHarvestReference(
                source_system="OpenClaw",
                source_path="agent-lab/audits/final/openclaw_final_forensic_report.md",
                mechanism="Action preview and approval lifecycle for high-power execution surfaces.",
                sentinel_rewrite="DesktopActionPreview",
                evidence_refs=["p6k_desktop_harvest", "openclaw_final"],
            ),
            VendorHarvestReference(
                source_system="OpenJarvis",
                source_path="agent-lab/audits/final/openjarvis_final_forensic_report.md",
                mechanism="Cost, sandbox, timeout, and local execution policy discipline.",
                sentinel_rewrite="DesktopCostAndSandboxPolicy",
                evidence_refs=["p6k_desktop_harvest", "openjarvis_final"],
            ),
        ],
    )
