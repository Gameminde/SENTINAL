from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from sentinel.operator.runtime_connections import (
    ConnectionHealthStatus,
    RuntimeConnectionRegistry,
    RuntimeConnectionRoute,
    build_default_runtime_connection_registry,
    run_runtime_connection_health_gate,
)
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel


class MissionExecutionDecisionStatus(StrEnum):
    ROUTED = "routed"
    REJECTED = "rejected"


class MissionExecutionRequest(SentinelModel):
    mission_id: str
    capability_id: str
    requested_action: str
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _request_is_data_only(self) -> "MissionExecutionRequest":
        assert_data_not_authority(
            context="mission_execution_request",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        if not self.mission_id.strip():
            raise ValueError("MissionExecutionRequest.mission_id is required.")
        if not self.capability_id.strip():
            raise ValueError("MissionExecutionRequest.capability_id is required.")
        if not self.requested_action.strip():
            raise ValueError("MissionExecutionRequest.requested_action is required.")
        return self


class MissionExecutionDecision(SentinelModel):
    status: MissionExecutionDecisionStatus
    mission_id: str
    capability_id: str
    requested_action: str
    connection_id: str | None = None
    authoritative_route: RuntimeConnectionRoute | None = None
    bridge_id: str | None = None
    rejection_reason: str | None = None
    health_status: ConnectionHealthStatus
    connection_finding_codes: tuple[str, ...] = Field(default_factory=tuple)
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False

    @model_validator(mode="after")
    def _decision_is_data_only(self) -> "MissionExecutionDecision":
        assert_data_not_authority(
            context="mission_execution_decision",
            authority_effect=self.authority_effect,
            data_not_authority=self.data_not_authority,
            can_grant_authority=self.can_grant_authority,
            can_execute=self.can_execute,
        )
        return self


class MissionExecutionCoordinator:
    """Selects the official route for a mission capability without executing it."""

    def __init__(self, registry: RuntimeConnectionRegistry | None = None) -> None:
        self._registry = registry or build_default_runtime_connection_registry()

    def decide(self, request: MissionExecutionRequest) -> MissionExecutionDecision:
        health = run_runtime_connection_health_gate(self._registry)
        if health.status is ConnectionHealthStatus.FAILED:
            return self._reject(
                request,
                reason="runtime_connection_health_failed",
                health_status=health.status,
                finding_codes=tuple(finding.code for finding in health.findings if finding.severity in {"P0", "P1"}),
            )
        try:
            connection = self._registry.get(request.capability_id)
        except KeyError:
            return self._reject(
                request,
                reason="unknown_capability_connection",
                health_status=health.status,
            )
        if connection.authoritative_route is RuntimeConnectionRoute.EXPERIMENTAL_ONLY:
            return self._reject(
                request,
                reason="experimental_route_not_product_reachable",
                health_status=health.status,
                connection_id=connection.connection_id,
                authoritative_route=connection.authoritative_route,
            )
        if connection.authoritative_route is RuntimeConnectionRoute.BLOCKED:
            return self._reject(
                request,
                reason="connection_blocked",
                health_status=health.status,
                connection_id=connection.connection_id,
                authoritative_route=connection.authoritative_route,
            )
        if not connection.production_reachable:
            return self._reject(
                request,
                reason="connection_not_product_reachable",
                health_status=health.status,
                connection_id=connection.connection_id,
                authoritative_route=connection.authoritative_route,
            )
        if request.requested_action not in connection.authority_actions:
            return self._reject(
                request,
                reason="action_not_declared_for_connection",
                health_status=health.status,
                connection_id=connection.connection_id,
                authoritative_route=connection.authoritative_route,
            )
        return MissionExecutionDecision(
            status=MissionExecutionDecisionStatus.ROUTED,
            mission_id=request.mission_id,
            capability_id=request.capability_id,
            requested_action=request.requested_action,
            connection_id=connection.connection_id,
            authoritative_route=connection.authoritative_route,
            bridge_id=_bridge_id_for_route(connection.authoritative_route),
            health_status=health.status,
        )

    @staticmethod
    def _reject(
        request: MissionExecutionRequest,
        *,
        reason: str,
        health_status: ConnectionHealthStatus,
        connection_id: str | None = None,
        authoritative_route: RuntimeConnectionRoute | None = None,
        finding_codes: tuple[str, ...] = (),
    ) -> MissionExecutionDecision:
        return MissionExecutionDecision(
            status=MissionExecutionDecisionStatus.REJECTED,
            mission_id=request.mission_id,
            capability_id=request.capability_id,
            requested_action=request.requested_action,
            connection_id=connection_id,
            authoritative_route=authoritative_route,
            rejection_reason=reason,
            health_status=health_status,
            connection_finding_codes=finding_codes,
        )


def _bridge_id_for_route(route: RuntimeConnectionRoute) -> str | None:
    if route is RuntimeConnectionRoute.AGENT_RUNTIME:
        return "agent_runtime_bridge"
    if route is RuntimeConnectionRoute.POWER_RUNTIME:
        return "power_runtime_bridge"
    if route is RuntimeConnectionRoute.LOCAL_GOVERNED_SURFACE:
        return "mission_kernel"
    return None


__all__ = [
    "MissionExecutionCoordinator",
    "MissionExecutionDecision",
    "MissionExecutionDecisionStatus",
    "MissionExecutionRequest",
]
