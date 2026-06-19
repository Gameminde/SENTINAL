from __future__ import annotations

from sentinel.operator.runtime_connections import (
    ConnectionHealthStatus,
    RuntimeConnectionMaturity,
    RuntimeConnectionRoute,
    build_default_runtime_connection_registry,
    run_runtime_connection_health_gate,
)


def test_default_runtime_connection_registry_declares_core_product_routes() -> None:
    registry = build_default_runtime_connection_registry()

    assert registry.get("mission_kernel").authoritative_route is RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE
    assert registry.get("agent_runtime_bridge").authoritative_route is RuntimeConnectionRoute.AGENT_RUNTIME
    assert registry.get("power_runtime_bridge").authoritative_route is RuntimeConnectionRoute.POWER_RUNTIME
    assert registry.get("read_only_research").authoritative_route is RuntimeConnectionRoute.AGENT_RUNTIME

    read_only = registry.get("read_only_research")
    assert read_only.maturity is RuntimeConnectionMaturity.LIVE_BOUNDED
    assert read_only.tool_registry_refs == ("read_only_observation",)
    assert read_only.authority_actions == (
        "list_directory",
        "read_file_segment",
        "finish_report",
    )
    assert read_only.telemetry_required is True
    assert read_only.receipt_contract == "ReadOnlyActionReceipt"
    assert read_only.finalgate_contract == "ReadOnlyFinalGateCertificate"
    assert read_only.replay_adapter == "ReadOnlyReplayView"


def test_connection_health_gate_rejects_missing_product_proof_contract() -> None:
    registry = build_default_runtime_connection_registry()
    broken = registry.get("read_only_research").model_copy(update={"receipt_contract": ""})
    registry = registry.with_connection(broken)

    result = run_runtime_connection_health_gate(registry)

    assert result.status is ConnectionHealthStatus.FAILED
    assert any(
        finding.connection_id == "read_only_research"
        and finding.code == "receipt_contract_missing"
        for finding in result.findings
    )


def test_connection_health_gate_marks_experimental_routes_but_does_not_fail_them() -> None:
    result = run_runtime_connection_health_gate(build_default_runtime_connection_registry())

    assert result.status is ConnectionHealthStatus.PASSED_WITH_LIMITS
    assert any(
        finding.connection_id == "interactive_exploration"
        and finding.code == "experimental_not_product_route"
        for finding in result.findings
    )
    assert not any(finding.severity == "P0" for finding in result.findings)


def test_registry_keeps_tool_and_organ_registry_references_data_only() -> None:
    registry = build_default_runtime_connection_registry()

    browser = registry.get("browser_live_operator")
    assert browser.organ_registry_refs == ("browser",)
    assert browser.execution_enabled_by_registry is False
    assert browser.authority_effect == "none"
    assert browser.data_not_authority is True

    exported = registry.export_json()
    assert all("provider_key" not in str(item).lower() for item in exported)
    assert all("raw_prompt" not in str(item).lower() for item in exported)
