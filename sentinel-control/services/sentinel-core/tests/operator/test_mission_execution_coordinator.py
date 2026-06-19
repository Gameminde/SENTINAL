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

    decision = coordinator.decide(
        MissionExecutionRequest(
            mission_id="mission_connection_1",
            capability_id="read_only_research",
            requested_action="read_file_segment",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.ROUTED
    assert decision.connection_id == "read_only_research"
    assert decision.authoritative_route is RuntimeConnectionRoute.AGENT_RUNTIME
    assert decision.bridge_id == "agent_runtime_bridge"
    assert decision.data_not_authority is True
    assert decision.can_execute is False


def test_coordinator_rejects_experimental_only_route() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(
        MissionExecutionRequest(
            mission_id="mission_connection_2",
            capability_id="interactive_exploration",
            requested_action="search_text",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "experimental_route_not_product_reachable"
    assert decision.authoritative_route is RuntimeConnectionRoute.EXPERIMENTAL_ONLY


def test_coordinator_rejects_search_text_until_read_only_adapter_is_product_scoped() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(
        MissionExecutionRequest(
            mission_id="mission_connection_3",
            capability_id="read_only_research",
            requested_action="search_text",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.connection_id == "read_only_research"
    assert decision.authoritative_route is RuntimeConnectionRoute.AGENT_RUNTIME
    assert decision.rejection_reason == "action_not_declared_for_connection"


def test_coordinator_rejects_action_not_declared_by_connection() -> None:
    coordinator = MissionExecutionCoordinator(build_default_runtime_connection_registry())

    decision = coordinator.decide(
        MissionExecutionRequest(
            mission_id="mission_connection_3b",
            capability_id="read_only_research",
            requested_action="write_file",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "action_not_declared_for_connection"


def test_coordinator_rejects_when_health_gate_fails() -> None:
    registry = build_default_runtime_connection_registry()
    broken = registry.get("read_only_research").model_copy(update={"finalgate_contract": ""})
    coordinator = MissionExecutionCoordinator(registry.with_connection(broken))

    decision = coordinator.decide(
        MissionExecutionRequest(
            mission_id="mission_connection_4",
            capability_id="read_only_research",
            requested_action="read_file_segment",
        )
    )

    assert decision.status is MissionExecutionDecisionStatus.REJECTED
    assert decision.rejection_reason == "runtime_connection_health_failed"
