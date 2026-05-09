from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sentinel.organs import (
    AutonomyRiskLane,
    ClipboardSanitizer,
    DesktopActionReceipt,
    DesktopFinalGateAdapter,
    DesktopHighPowerSurface,
    DesktopMisuseClassifier,
    ExternalOrganRegistry,
    FakeSidecarProvider,
    PermissionedSidecarManifest,
    ScreenContextSanitizer,
    SidecarEnrollmentGrant,
    SidecarKillSwitch,
    SidecarRPCDryRun,
    build_desktop_sidecar_organ_contract,
)
from sentinel.organs.contracts import OrganPromotionLevel, OrganType


def fresh_manifest() -> PermissionedSidecarManifest:
    return PermissionedSidecarManifest(
        sidecar_id="sidecar_local_1",
        sidecar_name="local fake desktop sidecar",
        capabilities=[
            "terminal",
            "filesystem",
            "desktop",
            "browser",
            "clipboard",
            "screenshot",
            "system_info",
            "awareness",
        ],
        allowed_roots=["workspace", "C:/Users/youcefcheriet/sentinal"],
        policy_hash="policy_hash_desktop_v1",
        evidence_refs=["p6k_desktop_harvest"],
    )


def fresh_grant(*, revoked: bool = False, expires_at: datetime | None = None) -> SidecarEnrollmentGrant:
    return SidecarEnrollmentGrant(
        sidecar_id="sidecar_local_1",
        sidecar_identity="jarvis_harvested_fake_sidecar",
        signed_enrollment="signed.enrollment.jwt",
        policy_hash="policy_hash_desktop_v1",
        issued_at=datetime.now(UTC) - timedelta(minutes=5),
        expires_at=expires_at or datetime.now(UTC) + timedelta(minutes=30),
        revoked=revoked,
        evidence_refs=["p6k_desktop_harvest"],
    )


def provider() -> FakeSidecarProvider:
    return FakeSidecarProvider(manifest=fresh_manifest(), enrollment=fresh_grant())


def test_desktop_contract_registers_with_foundry():
    contract = build_desktop_sidecar_organ_contract()
    registry = ExternalOrganRegistry().register(contract)

    assert registry.get("desktop_sidecar").id == contract.id
    assert contract.organ_type == OrganType.DESKTOP_SIDECAR
    assert contract.promotion_level == OrganPromotionLevel.L3_FAKE_EVAL
    assert contract.execution_enabled is False
    assert contract.dry_run_required is True
    assert contract.kill_switch_required is True
    assert contract.final_gate_required is True
    assert "desktop_rpc_dry_run" in contract.supported_actions


def test_manifest_declares_jarvis_backed_capabilities():
    manifest = fresh_manifest()

    assert {
        "terminal",
        "filesystem",
        "desktop",
        "browser",
        "clipboard",
        "screenshot",
        "system_info",
        "awareness",
    } <= set(manifest.capabilities)
    assert manifest.live_host_control_enabled is False
    assert manifest.vendor_runtime_bridge is False
    assert manifest.vendor_code_copied is False


def test_enrollment_requires_signed_identity_and_policy_hash():
    grant = fresh_grant()

    assert grant.is_active() is True
    assert grant.revoked is False
    with pytest.raises(ValueError, match="signed enrollment"):
        SidecarEnrollmentGrant(
            sidecar_id="sidecar_local_1",
            sidecar_identity="jarvis_harvested_fake_sidecar",
            signed_enrollment="",
            policy_hash="policy_hash_desktop_v1",
            issued_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            evidence_refs=["p6k_desktop_harvest"],
        )


def test_revoked_or_stale_sidecar_rejected():
    stale = FakeSidecarProvider(
        manifest=fresh_manifest(),
        enrollment=fresh_grant(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
    )
    revoked = FakeSidecarProvider(manifest=fresh_manifest(), enrollment=fresh_grant(revoked=True))
    request = SidecarRPCDryRun(method="desktop_list_windows", action_family="observation", evidence_refs=["fixture"])

    with pytest.raises(ValueError, match="stale or revoked"):
        stale.preview(request)
    with pytest.raises(ValueError, match="stale or revoked"):
        revoked.preview(request)


def test_fake_sidecar_dry_run_only_no_live_host_control():
    result = provider().preview(
        SidecarRPCDryRun(method="desktop_click", action_family="mutation", target={"window_id": "win_1"}, evidence_refs=["fixture"])
    )

    assert result.preview.execution_started is False
    assert result.preview.live_host_control_enabled is False
    assert result.receipt.action_family == "mutation"
    assert result.receipt.dry_run_only is True
    with pytest.raises(ValueError, match="does not execute live host actions"):
        provider().execute_live(result.preview)


def test_screen_sanitizer_redacts_secret_like_content():
    sanitized = ScreenContextSanitizer().sanitize(
        {
            "window_title": "Vault token sk_live_abc123",
            "ocr_text": "password=hunter2 api_key=abc123 SECRET_ACCESS_TOKEN",
        }
    )

    assert "sk_live" not in sanitized.text
    assert "hunter2" not in sanitized.text
    assert sanitized.redaction_count >= 3


def test_clipboard_sanitizer_redacts_secret_like_content():
    sanitized = ClipboardSanitizer().sanitize("copy password=hunter2 and bearer_token=abc.def.ghi")

    assert "hunter2" not in sanitized.text
    assert "bearer_token" not in sanitized.text
    assert sanitized.redaction_count >= 2


def test_wrong_target_mutation_rejected():
    request = SidecarRPCDryRun(
        method="desktop_type",
        action_family="mutation",
        target={"window_id": "win_actual", "expected_window_id": "win_expected"},
        text="hello",
        evidence_refs=["fixture"],
    )

    with pytest.raises(ValueError, match="wrong target"):
        provider().preview(request)


def test_path_traversal_and_symlink_escape_rejected():
    bad_traversal = SidecarRPCDryRun(method="read_file", action_family="filesystem", target={"path": "../secret.txt"}, evidence_refs=["fixture"])
    bad_symlink = SidecarRPCDryRun(
        method="write_file",
        action_family="filesystem",
        target={"path": "workspace/report.md", "symlink_target": "C:/Users/youcefcheriet/.ssh/id_rsa"},
        evidence_refs=["fixture"],
    )

    with pytest.raises(ValueError, match="path traversal"):
        provider().preview(bad_traversal)
    with pytest.raises(ValueError, match="symlink escape"):
        provider().preview(bad_symlink)


def test_sidecar_admin_mutation_preview_only():
    result = provider().preview(
        SidecarRPCDryRun(
            method="update_config",
            action_family="sidecar_admin",
            target={"config_key": "capabilities.desktop"},
            special_authority=True,
            evidence_refs=["fixture"],
        )
    )

    assert result.preview.preview_only is True
    assert result.preview.requires_special_authority is True
    assert result.receipt.dry_run_only is True
    assert result.receipt.action_family == "sidecar_admin"


def test_kill_switch_blocks_fake_sidecar_execution_shape():
    kill_switch = SidecarKillSwitch(mission_id="mission_desktop", sidecar_id="sidecar_local_1").trigger(reason="operator stop")
    request = SidecarRPCDryRun(method="desktop_focus_window", action_family="mutation", target={"window_id": "win_1"}, evidence_refs=["fixture"])

    with pytest.raises(ValueError, match="kill switch"):
        provider().preview(request, kill_switch=kill_switch)


def test_receipt_is_deterministic_and_redacted():
    request = SidecarRPCDryRun(
        mission_id="mission_desktop",
        method="set_clipboard",
        action_family="clipboard",
        text="password=hunter2",
        evidence_refs=["fixture"],
    )

    first = provider().preview(request)
    second = provider().preview(request)

    assert isinstance(first.receipt, DesktopActionReceipt)
    assert first.receipt.receipt_hash == second.receipt.receipt_hash
    assert "hunter2" not in first.receipt.sanitized_summary
    assert first.receipt.authority_expansion is False


def test_black_lane_host_misuse_blocked():
    classifier = DesktopMisuseClassifier()

    for objective in ["hidden keystrokes", "credential theft", "secret capture", "authority bypass", "vendor runtime bridge"]:
        decision = classifier.classify(objective)
        assert decision.lane == AutonomyRiskLane.BLACK
        assert decision.blocked is True


def test_high_power_surfaces_have_promotion_paths():
    surfaces = DesktopHighPowerSurface.defaults()
    by_name = {surface.surface_name: surface for surface in surfaces}

    assert by_name["window_metadata_system_info_awareness"].lane == AutonomyRiskLane.BLUE
    assert by_name["screenshot_clipboard_filesystem_preview"].lane == AutonomyRiskLane.RED
    assert by_name["click_type_keys_launch_focus"].requires_special_authority is True
    assert by_name["sidecar_admin_config"].requires_special_authority is True
    assert all(surface.promotion_path for surface in surfaces)
    assert DesktopFinalGateAdapter().required_fields == [
        "mission_id",
        "sidecar_id",
        "action_family",
        "authority_refs",
        "evidence_refs",
        "receipt_hash",
    ]
