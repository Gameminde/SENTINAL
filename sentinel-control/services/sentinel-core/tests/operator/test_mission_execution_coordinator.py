from __future__ import annotations

from sentinel.operator.mission_execution_coordinator import (
    MissionExecutionCoordinator,
    MissionExecutionDecisionStatus,
    MissionExecutionRequest,
)
from sentinel.operator.runtime_connections import (
    RuntimeConnectionRoute,
    build_default_runtime_connection_registry,
)


def test_coordinator_selects_read_only_research_product_route() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(_request("mission_connection_1"))

    assert decision.status is MissionExecutionDecisionStatus.ROUTED
    assert decision.connection_id == "read_only_research"
    assert decision.authoritative_route is RuntimeConnectionRoute.AGENT_RUNTIME
    assert decision.bridge_id == "agent_runtime_bridge"
    assert decision.adapter_id == "read_only_research_adapter"
    assert decision.data_not_authority is True
    assert decision.can_execute is False


def test_coordinator_rejects_experimental_only_route() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(_request("mission_connection_2", capability_id="interactive_exploration"))

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "experimental_route_not_product_reachable"
    assert decision.authoritative_route is RuntimeConnectionRoute.EXPERIMENTAL_ONLY


def test_coordinator_rejects_operation_not_declared_by_connection() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(_request("mission_connection_3", operation="search_text"))

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.connection_id == "read_only_research"
    assert decision.authoritative_route is RuntimeConnectionRoute.AGENT_RUNTIME
    assert decision.rejection_reason == "operation_not_supported"


def test_coordinator_routes_workspace_patch_product_adapter() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(
        _request(
            "mission_connection_skill_native_1",
            capability_id="workspace_patch",
            operation="apply_patch",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.ROUTED
    assert decision.connection_id == "workspace_patch"
    assert decision.adapter_id == "product_action_kernel_adapter"
    assert decision.skill_id == "workspace_patch"
    assert decision.model_visible_backend_id == "workspace_patch_skill"
    assert decision.task_loop_reachable is True
    assert decision.product_reachable is True
    assert decision.dispatch_enabled is False
    assert decision.can_execute is False


def test_coordinator_recognizes_known_skill_without_product_adapter() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(
        _request(
            "mission_connection_skill_native_2",
            capability_id="bounded_channel",
            operation="send_message",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "skill_not_product_dispatchable"
    assert decision.skill_id == "bounded_channel"
    assert decision.model_visible_backend_id == "bounded_channel_skill"
    assert decision.task_loop_reachable is True
    assert decision.product_reachable is False
    assert decision.dispatch_enabled is False
    assert decision.adapter_id is None
    assert decision.can_execute is False


def test_coordinator_rejects_mutating_operation_not_declared_by_connection() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(_request("mission_connection_3b", operation="write_file"))

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "operation_not_supported"


def test_coordinator_rejects_when_health_gate_fails() -> None:
    registry = build_default_runtime_connection_registry()
    broken = registry.get("read_only_research").model_copy(update={"finalgate_contract": ""})
    coordinator = MissionExecutionCoordinator(registry.with_connection(broken))

    decision = coordinator.decide(_request("mission_connection_4"))

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "runtime_connection_health_failed"


def _request(
    mission_id: str,
    *,
    capability_id: str = "read_only_research",
    operation: str = "inspect_repository",
) -> MissionExecutionRequest:
    return MissionExecutionRequest(
        mission_id=mission_id,
        capability_id=capability_id,
        operation=operation,
        parameter_hash="param_hash",
        workspace_ref="workspace:C:/sentinel/fixture",
        model_contract_ref="model_contract:fake",
        authority_envelope_ref="mission_authority_envelope_ref",
    ).with_hash()
