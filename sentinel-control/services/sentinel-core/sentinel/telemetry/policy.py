from __future__ import annotations

from enum import StrEnum
from typing import Any

from sentinel.shared.models import SentinelModel


class TelemetryOperationalState(StrEnum):
    CERTIFIED = "certified"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    TAMPER_DETECTED = "tamper_detected"
    READ_ONLY_SAFE_MODE = "read_only_safe_mode"


class TelemetryExecutionClass(StrEnum):
    MATERIAL_MUTATION = "material_mutation"
    READ_ONLY_OBSERVATION = "read_only_observation"
    KILL_OR_REVOCATION = "kill_or_revocation"


class TelemetryDegradationPolicy(SentinelModel):
    allow_read_only_when_degraded: bool = False
    operator_visible: bool = True
    data_not_authority: bool = True
    authority_effect: str = "none"


class TelemetryPolicyDecision(SentinelModel):
    operation_class: TelemetryExecutionClass
    state: TelemetryOperationalState
    evidence_ready: bool
    reasons: list[str]
    operator_visible: bool = True
    kill_and_revocation_available: bool = True
    data_not_authority: bool = True
    authority_effect: str = "none"
    can_grant_authority: bool = False
    can_execute: bool = False


def evaluate_telemetry_operation(
    sink: Any | None,
    operation_class: TelemetryExecutionClass,
    *,
    policy: TelemetryDegradationPolicy | None = None,
) -> TelemetryPolicyDecision:
    policy = policy or TelemetryDegradationPolicy()
    snapshot = _safe_snapshot(sink)
    state = _state_from_snapshot(snapshot)
    reasons = list(getattr(snapshot, "reasons", []) or ["telemetry_unavailable"])

    if operation_class is TelemetryExecutionClass.KILL_OR_REVOCATION:
        return TelemetryPolicyDecision(
            operation_class=operation_class,
            state=state,
            evidence_ready=True,
            reasons=reasons,
            operator_visible=policy.operator_visible,
        )

    if bool(getattr(snapshot, "certified_mode", False)):
        return TelemetryPolicyDecision(
            operation_class=operation_class,
            state=TelemetryOperationalState.CERTIFIED,
            evidence_ready=True,
            reasons=reasons,
            operator_visible=policy.operator_visible,
        )

    if (
        operation_class is TelemetryExecutionClass.READ_ONLY_OBSERVATION
        and policy.allow_read_only_when_degraded
    ):
        return TelemetryPolicyDecision(
            operation_class=operation_class,
            state=TelemetryOperationalState.READ_ONLY_SAFE_MODE,
            evidence_ready=True,
            reasons=reasons,
            operator_visible=policy.operator_visible,
        )

    return TelemetryPolicyDecision(
        operation_class=operation_class,
        state=state,
        evidence_ready=False,
        reasons=reasons,
        operator_visible=policy.operator_visible,
    )


def _safe_snapshot(sink: Any | None) -> Any:
    if sink is None or not hasattr(sink, "certified_mode_status"):
        return None
    try:
        return sink.certified_mode_status()
    except Exception:
        return None


def _state_from_snapshot(snapshot: Any | None) -> TelemetryOperationalState:
    if snapshot is None or not bool(getattr(snapshot, "telemetry_available", False)):
        return TelemetryOperationalState.UNAVAILABLE
    if bool(getattr(snapshot, "tampered", False)):
        return TelemetryOperationalState.TAMPER_DETECTED
    if bool(getattr(snapshot, "certified_mode", False)):
        return TelemetryOperationalState.CERTIFIED
    return TelemetryOperationalState.DEGRADED
