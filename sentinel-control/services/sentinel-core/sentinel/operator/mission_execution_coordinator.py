from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.mission_lifecycle_service import MissionExecutionRequest
from sentinel.operator.redaction import redact_operator_text, redact_operator_value
from sentinel.operator.runtime_connections import (
    ConnectionHealthStatus,
    RuntimeConnectionRegistry,
    RuntimeConnectionRoute,
    build_default_runtime_connection_registry,
    run_runtime_connection_health_gate,
)
from sentinel.operator.safety import assert_data_not_authority
from sentinel.shared.models import SentinelModel, new_id


class MissionExecutionDecisionStatus(StrEnum):
    ROUTED = "routed"
    REJECTED = "rejected"


class MissionExecutionDecision(SentinelModel):
    decision_id: str = Field(default_factory=lambda: new_id("mission_exec_decision"))
    status: MissionExecutionDecisionStatus
    mission_id: str
    execution_request_id: str
    capability_id: str
    operation: str
    connection_id: str | None = None
    route: RuntimeConnectionRoute | None = None
    bridge_id: str | None = None
    adapter_id: str | None = None
    authority_envelope_ref: str | None = None
    connection_profile_hash: str | None = None
    rejection_reason: str | None = None
    health_status: ConnectionHealthStatus
    connection_finding_codes: tuple[str, ...] = Field(default_factory=tuple)
    decision_hash: str = ""
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

    @property
    def authoritative_route(self) -> RuntimeConnectionRoute | None:
        return self.route

    @property
    def requested_action(self) -> str:
        return self.operation

    def safe_model_dump(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "status": self.status.value,
            "mission_id": self.mission_id,
            "execution_request_id": self.execution_request_id,
            "capability_id": redact_operator_text(self.capability_id),
            "operation": redact_operator_text(self.operation),
            "route": self.route.value if self.route else None,
            "adapter_id": redact_operator_text(self.adapter_id or "") or None,
            "connection_id": redact_operator_text(self.connection_id or "") or None,
            "bridge_id": redact_operator_text(self.bridge_id or "") or None,
            "authority_envelope_ref": self.authority_envelope_ref,
            "connection_profile_hash": self.connection_profile_hash,
            "rejection_reason": redact_operator_text(self.rejection_reason or "") or None,
            "health_status": self.health_status.value,
            "connection_finding_codes": list(self.connection_finding_codes),
            "decision_hash": self.decision_hash,
            "data_not_authority": self.data_not_authority,
            "authority_effect": self.authority_effect,
            "can_grant_authority": self.can_grant_authority,
            "can_execute": self.can_execute,
        }

    def with_hash(self) -> "MissionExecutionDecision":
        payload = self.safe_model_dump()
        payload["decision_hash"] = ""
        return self.model_copy(update={"decision_hash": stable_hash(redact_operator_value(payload))})

    def verify_hash(self) -> bool:
        payload = self.safe_model_dump()
        stored = payload["decision_hash"]
        payload["decision_hash"] = ""
        return bool(stored) and stored == stable_hash(redact_operator_value(payload))


class MissionExecutionCoordinator:
    """Selects the official route for a mission capability without executing it."""

    def __init__(self, registry: RuntimeConnectionRegistry | None = None) -> None:
        self._registry = registry or build_default_runtime_connection_registry()

    def decide(self, request: MissionExecutionRequest) -> MissionExecutionDecision:
        if not request.verify_hash():
            return self._reject(
                request,
                reason="mission_execution_request_hash_mismatch",
                health_status=ConnectionHealthStatus.FAILED,
            )
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
        if request.operation not in connection.supported_operations:
            return self._reject(
                request,
                reason="operation_not_supported",
                health_status=health.status,
                connection_id=connection.connection_id,
                authoritative_route=connection.authoritative_route,
                adapter_id=connection.adapter_id,
                connection_profile_hash=connection.profile_hash,
            )
        return MissionExecutionDecision(
            status=MissionExecutionDecisionStatus.ROUTED,
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            capability_id=request.capability_id,
            operation=request.operation,
            connection_id=connection.connection_id,
            route=connection.authoritative_route,
            bridge_id=_bridge_id_for_route(connection.authoritative_route),
            adapter_id=connection.adapter_id,
            authority_envelope_ref=request.authority_envelope_ref,
            connection_profile_hash=connection.profile_hash,
            health_status=health.status,
        ).with_hash()

    @staticmethod
    def _reject(
        request: MissionExecutionRequest,
        *,
        reason: str,
        health_status: ConnectionHealthStatus,
        connection_id: str | None = None,
        authoritative_route: RuntimeConnectionRoute | None = None,
        adapter_id: str | None = None,
        connection_profile_hash: str | None = None,
        finding_codes: tuple[str, ...] = (),
    ) -> MissionExecutionDecision:
        return MissionExecutionDecision(
            status=MissionExecutionDecisionStatus.REJECTED,
            mission_id=request.mission_id,
            execution_request_id=request.request_id,
            capability_id=request.capability_id,
            operation=request.operation,
            connection_id=connection_id,
            route=authoritative_route,
            adapter_id=adapter_id,
            authority_envelope_ref=request.authority_envelope_ref,
            connection_profile_hash=connection_profile_hash,
            rejection_reason=reason,
            health_status=health_status,
            connection_finding_codes=finding_codes,
        ).with_hash()


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
