from __future__ import annotations

import inspect

import pytest

from sentinel.operator.connection_manifest_models import (
    ConnectionDirection,
    ConnectionManifest,
    ConnectionRiskClass,
    ConnectionSurfaceStatus,
)
from sentinel.operator.connection_manifest_registry import build_default_connection_manifest_registry
from sentinel.operator.runtime_host import SentinelRuntimeHost


def _minimal_manifest(**overrides: object) -> ConnectionManifest:
    values: dict[str, object] = {
        "connection_id": "test_surface",
        "surface_id": "surface:test",
        "surface_kind": "test_metadata",
        "owner_module": "sentinel.operator.runtime_connections",
        "runtime_class_name": None,
        "adapter_id": None,
        "current_status": ConnectionSurfaceStatus.PLANNED,
        "production_reachable": False,
        "product_dispatchable": False,
        "direction": ConnectionDirection.INTERNAL,
        "risk_class": ConnectionRiskClass.C0,
        "data_types": ("metadata",),
        "credential_env_names": (),
        "credential_required": False,
        "authority_required": "none_manifest_only",
        "capability_id": None,
        "operation": None,
        "can_read": False,
        "can_write": False,
        "can_send": False,
        "can_execute": False,
        "external_side_effects_possible": False,
        "requires_gate": False,
        "requires_finalgate": False,
        "requires_receipts": False,
        "requires_replay": False,
        "requires_kill_or_revocation": False,
        "prompt_injection_exposure": "none",
        "secret_exfiltration_exposure": "none",
        "receipt_schema_ref": None,
        "replay_schema_ref": None,
        "approval_policy_ref": "policy:none",
        "status_reason": "test manifest only",
        "missing_to_dispatchable": ("not_a_product_surface",),
    }
    values.update(overrides)
    return ConnectionManifest(**values)


def test_default_connection_manifests_are_data_only_and_registry_cannot_execute() -> None:
    registry = build_default_connection_manifest_registry()

    assert not hasattr(registry, "execute")
    validation = registry.validate_all()
    assert validation.ok is True
    assert validation.manifest_count == len(registry.list_manifests())
    assert validation.findings == ()

    for manifest in registry.list_manifests():
        assert manifest.data_not_authority is True
        assert manifest.authority_granting is False
        assert manifest.can_grant_authority is False
        assert manifest.registry_can_execute is False
        assert manifest.can_execute is False
        assert manifest.fallback_auto_allowed is False
        assert manifest.provider_native_tools_allowed is False


def test_manifest_rejects_authority_execution_fallback_and_provider_native_tools() -> None:
    with pytest.raises(ValueError, match="authority"):
        _minimal_manifest(authority_granting=True)
    with pytest.raises(ValueError, match="grant authority"):
        _minimal_manifest(can_grant_authority=True)
    with pytest.raises(ValueError, match="execute"):
        _minimal_manifest(registry_can_execute=True)
    with pytest.raises(ValueError, match="execute"):
        _minimal_manifest(can_execute=True)
    with pytest.raises(ValueError, match="fallback"):
        _minimal_manifest(fallback_auto_allowed=True)
    with pytest.raises(ValueError, match="provider-native"):
        _minimal_manifest(provider_native_tools_allowed=True)


def test_manifest_rejects_credential_values_raw_endpoints_and_provider_payloads() -> None:
    assert _minimal_manifest(credential_env_names=("SENTINEL_CERT_MODEL_API_KEY",)).credential_env_names == (
        "SENTINEL_CERT_MODEL_API_KEY",
    )

    with pytest.raises(ValueError, match="credential"):
        _minimal_manifest(credential_env_names=("sk-live-secret-value",))
    with pytest.raises(ValueError, match="endpoint"):
        _minimal_manifest(allowed_destinations_policy_ref="https://example.invalid/compatible-mode/v1")
    with pytest.raises(ValueError, match="provider payload"):
        _minimal_manifest(status_reason="contains raw_provider_payload wrapper")


def test_read_only_research_is_the_only_product_dispatchable_manifest() -> None:
    registry = build_default_connection_manifest_registry()

    dispatchable_ids = [
        manifest.connection_id
        for manifest in registry.list_manifests()
        if manifest.product_dispatchable
    ]

    assert dispatchable_ids == ["read_only_research"]
    read_only = registry.get("read_only_research")
    assert read_only.production_reachable is True
    assert read_only.adapter_id == "read_only_research_adapter"
    assert read_only.capability_id == "read_only_research"
    assert read_only.operation == "inspect_repository"


def test_c4_c5_surfaces_are_locked_and_cannot_be_dispatchable_by_default() -> None:
    registry = build_default_connection_manifest_registry()
    high_risk = [
        manifest
        for manifest in registry.list_manifests()
        if manifest.risk_class in {ConnectionRiskClass.C4, ConnectionRiskClass.C5}
    ]

    assert high_risk
    assert all(not manifest.product_dispatchable for manifest in high_risk)
    assert all(not manifest.production_reachable for manifest in high_risk)
    assert all(manifest.adapter_id is None for manifest in high_risk)

    with pytest.raises(ValueError, match="high-risk"):
        _minimal_manifest(
            risk_class=ConnectionRiskClass.C4,
            production_reachable=True,
            product_dispatchable=True,
            adapter_id="future_external_adapter",
        )


def test_runtime_connection_comparison_reports_manifest_coverage_without_dispatching() -> None:
    registry = build_default_connection_manifest_registry()

    comparison = registry.compare_runtime_connections()

    assert "read_only_research" not in comparison.missing_runtime_connection_profiles
    assert "browser_live_operator" not in comparison.missing_manifests_for_runtime_connections
    assert "interactive_exploration" not in comparison.missing_manifests_for_runtime_connections
    assert "model_router_runtime" in comparison.missing_runtime_connection_profiles
    assert "channel_connector_runtime" in comparison.missing_runtime_connection_profiles


def test_adapter_readiness_report_keeps_only_read_only_product_ready() -> None:
    registry = build_default_connection_manifest_registry()

    report = registry.adapter_readiness_report()
    by_id = {item.connection_id: item for item in report.entries}

    read_only = by_id["read_only_research"]
    assert read_only.manifest_exists is True
    assert read_only.runtime_connection_profile_exists is True
    assert read_only.unified_execution_adapter_exists is True
    assert read_only.runtime_host_registered is True
    assert read_only.product_dispatchable is True
    assert read_only.missing_to_dispatchable == ()

    channel = by_id["channel_connector_runtime"]
    assert channel.product_dispatchable is False
    assert "runtime_connection_profile_missing" in channel.missing_to_dispatchable
    assert "unified_execution_adapter_missing" in channel.missing_to_dispatchable


def test_safe_export_exposes_names_and_hashes_without_values_or_endpoints() -> None:
    registry = build_default_connection_manifest_registry()

    exported = registry.export_safe_summaries()
    exported_text = repr(exported)

    assert "sk-" not in exported_text
    assert "https://" not in exported_text
    assert "Authorization" not in exported_text
    assert "raw_provider_payload" not in exported_text

    provider = next(item for item in exported if item["connection_id"] == "model_provider_catalog")
    assert "SENTINEL_CERT_MODEL_API_KEY" in provider["credential_env_names"]
    assert provider["credential_env_name_hashes"]
    assert provider["safe_export_hash"]


def test_pack2_does_not_wire_manifest_registry_into_runtimehost_dispatch() -> None:
    source = inspect.getsource(SentinelRuntimeHost.__init__)

    assert '"read_only_research_adapter"' in source
    assert "connection_manifest" not in source.lower()
