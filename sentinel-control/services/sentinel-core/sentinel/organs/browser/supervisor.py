from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any

from sentinel.organs.browser.models import (
    BrowserHealthCheck,
    BrowserHealthStatus,
    BrowserOperationAttempt,
    BrowserOperationStatus,
    BrowserPoolLease,
    BrowserPoolLeaseReceipt,
    BrowserPoolLeaseResult,
    BrowserPoolLeaseStatus,
    BrowserRetryPolicy,
    BrowserSupervisedOperationResult,
)
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus


BrowserOperation = Callable[[], dict[str, Any]]
BrowserHealthProbe = Callable[[], BrowserHealthStatus | str | dict[str, Any]]


class BrowserOperationError(RuntimeError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


class BrowserReliabilitySupervisor:
    """Supervises public browser leases, health checks, and bounded retries."""

    def __init__(self) -> None:
        self.leases: dict[str, BrowserPoolLease] = {}
        self._consecutive_failures: int = 0

    def lease(
        self,
        *,
        mission_id: str,
        purpose: str,
        event_bus: EventBus,
        backend_kind: str = "playwright_public",
        max_operations: int = 10,
        stateless_public: bool = True,
        cookies_enabled: bool = False,
        storage_enabled: bool = False,
        js_enabled: bool = False,
        downloads_enabled: bool = False,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPoolLeaseResult:
        self._require_mission(event_bus, mission_id)
        boundary_errors = _boundary_errors(
            stateless_public=stateless_public,
            cookies_enabled=cookies_enabled,
            storage_enabled=storage_enabled,
            js_enabled=js_enabled,
            downloads_enabled=downloads_enabled,
        )
        if boundary_errors:
            return self._reject_lease(
                mission_id=mission_id,
                action="lease",
                reason="browser_pool_lease_boundary_rejected",
                errors=boundary_errors,
                event_bus=event_bus,
                phase=phase,
            )

        lease = BrowserPoolLease(
            mission_id=mission_id,
            purpose=purpose,
            backend_kind=backend_kind,
            max_operations=max_operations,
        )
        receipt = BrowserPoolLeaseReceipt(
            mission_id=mission_id,
            lease_id=lease.id,
            action="lease",
            backend_kind=backend_kind,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_POOL_LEASED,
            "Public browser pool lease created under stateless execution boundaries.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "lease_id": lease.id,
                "purpose": purpose,
                "backend_kind": backend_kind,
                "max_operations": lease.max_operations,
                "operation_count": lease.operation_count,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
                "status": BrowserPoolLeaseStatus.LEASED.value,
            },
        )
        trace_refs = [event.id]
        lease = lease.model_copy(update={"trace_refs": trace_refs})
        receipt = receipt.model_copy(update={"trace_refs": trace_refs})
        self.leases[lease.id] = lease
        return BrowserPoolLeaseResult(
            accepted=True,
            status=BrowserPoolLeaseStatus.LEASED,
            reason="browser_pool_lease_created",
            mission_id=mission_id,
            lease=lease,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def release(
        self,
        *,
        lease_id: str,
        event_bus: EventBus,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserPoolLeaseResult:
        lease = self.leases.get(lease_id)
        if lease is None:
            return self._reject_lease(
                mission_id=event_bus.mission_id,
                action="release",
                reason="browser_pool_lease_missing",
                lease_id=lease_id,
                event_bus=event_bus,
                phase=phase,
            )
        self._require_mission(event_bus, lease.mission_id)
        if lease.status != BrowserPoolLeaseStatus.LEASED:
            return self._reject_lease(
                mission_id=lease.mission_id,
                action="release",
                reason="browser_pool_lease_not_active",
                lease_id=lease_id,
                event_bus=event_bus,
                phase=phase,
            )

        receipt = BrowserPoolLeaseReceipt(
            mission_id=lease.mission_id,
            lease_id=lease.id,
            action="release",
            backend_kind=lease.backend_kind,
            trace_refs=lease.trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_POOL_RELEASED,
            "Public browser pool lease released.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "receipt_id": receipt.id,
                "lease_id": lease.id,
                "backend_kind": lease.backend_kind,
                "max_operations": lease.max_operations,
                "operation_count": lease.operation_count,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
                "status": BrowserPoolLeaseStatus.RELEASED.value,
            },
            trace_refs=lease.trace_refs,
        )
        trace_refs = [*lease.trace_refs, event.id]
        closed_lease = lease.model_copy(update={"status": BrowserPoolLeaseStatus.RELEASED, "trace_refs": trace_refs})
        receipt = receipt.model_copy(update={"trace_refs": trace_refs})
        self.leases[lease.id] = closed_lease
        return BrowserPoolLeaseResult(
            accepted=True,
            status=BrowserPoolLeaseStatus.RELEASED,
            reason="browser_pool_lease_released",
            mission_id=lease.mission_id,
            lease=closed_lease,
            receipt=receipt,
            trace_event_id=event.id,
        )

    def health_check(
        self,
        *,
        mission_id: str,
        event_bus: EventBus,
        lease_id: str | None = None,
        probe: BrowserHealthProbe | None = None,
        backend_kind: str = "playwright_public",
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserHealthCheck:
        self._require_mission(event_bus, mission_id)
        lease = self.leases.get(lease_id) if lease_id else None
        if lease_id and lease is None:
            return self._rejected_health(
                mission_id=mission_id,
                lease_id=lease_id,
                reason="browser_pool_lease_missing",
                event_bus=event_bus,
                phase=phase,
            )
        if lease and lease.status != BrowserPoolLeaseStatus.LEASED:
            return self._rejected_health(
                mission_id=mission_id,
                lease_id=lease_id,
                reason="browser_pool_lease_not_active",
                event_bus=event_bus,
                phase=phase,
            )

        started = perf_counter()
        notes: list[str] = []
        errors: list[str] = []
        status = BrowserHealthStatus.HEALTHY
        try:
            observed = probe() if probe else BrowserHealthStatus.HEALTHY
            status, notes = _coerce_health_probe(observed)
            self._consecutive_failures = 0 if status == BrowserHealthStatus.HEALTHY else self._consecutive_failures + 1
        except Exception as exc:
            status = BrowserHealthStatus.UNAVAILABLE
            self._consecutive_failures += 1
            errors = [f"{type(exc).__name__}:{str(exc)[:300]}"]
        latency_ms = max(0, int((perf_counter() - started) * 1000))
        trace_refs = list(lease.trace_refs) if lease else []
        check = BrowserHealthCheck(
            mission_id=mission_id,
            lease_id=lease_id,
            status=status,
            backend_kind=lease.backend_kind if lease else backend_kind,
            latency_ms=latency_ms,
            consecutive_failures=self._consecutive_failures,
            notes=notes,
            errors=errors,
            trace_refs=trace_refs,
        )
        event = event_bus.append(
            AgentEventType.BROWSER_HEALTH_CHECKED,
            "Public browser backend health checked through supervisor.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "health_check_id": check.id,
                "lease_id": lease_id,
                "status": check.status.value,
                "backend_kind": check.backend_kind,
                "latency_ms": check.latency_ms,
                "consecutive_failures": check.consecutive_failures,
                "notes": check.notes,
                "errors": check.errors,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
            trace_refs=trace_refs,
        )
        return check.model_copy(update={"trace_refs": [*trace_refs, event.id]})

    def run_with_retries(
        self,
        operation: BrowserOperation,
        *,
        mission_id: str,
        operation_name: str,
        event_bus: EventBus,
        retry_policy: BrowserRetryPolicy | None = None,
        lease_id: str | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserSupervisedOperationResult:
        self._require_mission(event_bus, mission_id)
        policy = retry_policy or BrowserRetryPolicy()
        lease = self.leases.get(lease_id) if lease_id else None
        if lease_id:
            lease_error = self._active_lease_error(lease, mission_id=mission_id)
            if lease_error is not None:
                return self._rejected_operation(
                    mission_id=mission_id,
                    operation_name=operation_name,
                    reason=lease_error,
                    event_bus=event_bus,
                    lease_id=lease_id,
                    phase=phase,
                )
            assert lease is not None
            if lease.operation_count >= lease.max_operations:
                return self._rejected_operation(
                    mission_id=mission_id,
                    operation_name=operation_name,
                    reason="browser_pool_lease_operation_limit_reached",
                    event_bus=event_bus,
                    lease_id=lease_id,
                    phase=phase,
                )
            self.leases[lease.id] = lease.model_copy(update={"operation_count": lease.operation_count + 1})
            lease = self.leases[lease.id]

        attempts: list[BrowserOperationAttempt] = []
        for attempt_number in range(1, policy.max_attempts + 1):
            try:
                result = operation()
                return BrowserSupervisedOperationResult(
                    accepted=True,
                    status=BrowserOperationStatus.COMPLETED,
                    mission_id=mission_id,
                    operation_name=operation_name,
                    reason="browser_operation_completed",
                    lease_id=lease_id,
                    attempts=[
                        *attempts,
                        BrowserOperationAttempt(
                            attempt_number=attempt_number,
                            reason="completed",
                            retryable=False,
                        ),
                    ],
                    result=dict(result),
                )
            except Exception as exc:
                reason = _operation_failure_reason(exc)
                retryable = reason in set(policy.retryable_reasons) and attempt_number < policy.max_attempts
                attempt = BrowserOperationAttempt(
                    attempt_number=attempt_number,
                    reason=reason,
                    retryable=retryable,
                )
                if retryable:
                    event = event_bus.append(
                        AgentEventType.BROWSER_OPERATION_RETRIED,
                        "Browser operation retry authorized by bounded supervisor policy.",
                        phase_before=phase,
                        phase_after=phase,
                        payload={
                            "operation_name": operation_name,
                            "lease_id": lease_id,
                            "attempt_number": attempt_number,
                            "max_attempts": policy.max_attempts,
                            "reason": reason,
                            "retryable": True,
                            "status": BrowserOperationStatus.RETRYING.value,
                            "stateless_public": True,
                            "cookies_enabled": False,
                            "storage_enabled": False,
                            "js_enabled": False,
                            "downloads_enabled": False,
                        },
                        trace_refs=list(lease.trace_refs) if lease else [],
                    )
                    attempts.append(attempt.model_copy(update={"trace_event_id": event.id}))
                    continue
                attempts.append(attempt)
                rejection = self._rejected_operation(
                    mission_id=mission_id,
                    operation_name=operation_name,
                    reason=reason,
                    event_bus=event_bus,
                    lease_id=lease_id,
                    phase=phase,
                    errors=[f"{type(exc).__name__}:{str(exc)[:300]}"],
                )
                return rejection.model_copy(update={"attempts": attempts})

        return self._rejected_operation(
            mission_id=mission_id,
            operation_name=operation_name,
            reason="browser_retry_policy_exhausted",
            event_bus=event_bus,
            lease_id=lease_id,
            phase=phase,
            errors=["max_attempts_exhausted"],
        )

    @staticmethod
    def _require_mission(event_bus: EventBus, mission_id: str) -> None:
        if event_bus.mission_id != mission_id:
            raise ValueError("Browser supervisor event bus mission_id must match request mission_id.")

    @staticmethod
    def _active_lease_error(lease: BrowserPoolLease | None, *, mission_id: str) -> str | None:
        if lease is None:
            return "browser_pool_lease_missing"
        if lease.mission_id != mission_id:
            return "browser_pool_lease_mission_mismatch"
        if lease.status != BrowserPoolLeaseStatus.LEASED:
            return "browser_pool_lease_not_active"
        return None

    @staticmethod
    def _reject_lease(
        *,
        mission_id: str,
        action: str,
        reason: str,
        event_bus: EventBus,
        phase: AgentPhase,
        lease_id: str | None = None,
        errors: list[str] | None = None,
    ) -> BrowserPoolLeaseResult:
        event = event_bus.append(
            AgentEventType.BROWSER_SUPERVISOR_REJECTED,
            "Browser supervisor rejected a pool lease operation.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "action": action,
                "operation_name": action,
                "lease_id": lease_id,
                "reason": reason,
                "errors": errors or [],
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
                "status": BrowserPoolLeaseStatus.REJECTED.value,
            },
        )
        return BrowserPoolLeaseResult(
            accepted=False,
            status=BrowserPoolLeaseStatus.REJECTED,
            reason=reason,
            mission_id=mission_id,
            trace_event_id=event.id,
            errors=errors or [],
        )

    def _rejected_health(
        self,
        *,
        mission_id: str,
        lease_id: str | None,
        reason: str,
        event_bus: EventBus,
        phase: AgentPhase,
    ) -> BrowserHealthCheck:
        event = event_bus.append(
            AgentEventType.BROWSER_SUPERVISOR_REJECTED,
            "Browser supervisor rejected a health check before probing.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "action": "health_check",
                "operation_name": "health_check",
                "lease_id": lease_id,
                "reason": reason,
                "errors": [reason],
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
                "status": BrowserOperationStatus.REJECTED.value,
            },
        )
        return BrowserHealthCheck(
            mission_id=mission_id,
            lease_id=lease_id,
            status=BrowserHealthStatus.UNAVAILABLE,
            errors=[reason],
            trace_refs=[event.id],
        )

    def _rejected_operation(
        self,
        *,
        mission_id: str,
        operation_name: str,
        reason: str,
        event_bus: EventBus,
        phase: AgentPhase,
        lease_id: str | None = None,
        errors: list[str] | None = None,
    ) -> BrowserSupervisedOperationResult:
        trace_refs: list[str] = []
        if lease_id and lease_id in self.leases:
            trace_refs = list(self.leases[lease_id].trace_refs)
        event = event_bus.append(
            AgentEventType.BROWSER_SUPERVISOR_REJECTED,
            "Browser supervisor rejected a bounded browser operation.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "action": "run_with_retries",
                "operation_name": operation_name,
                "lease_id": lease_id,
                "reason": reason,
                "errors": errors or [],
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
                "status": BrowserOperationStatus.REJECTED.value,
            },
            trace_refs=trace_refs,
        )
        return BrowserSupervisedOperationResult(
            accepted=False,
            status=BrowserOperationStatus.REJECTED,
            mission_id=mission_id,
            operation_name=operation_name,
            reason=reason,
            lease_id=lease_id,
            trace_event_id=event.id,
            errors=errors or [reason],
        )


def _boundary_errors(
    *,
    stateless_public: bool,
    cookies_enabled: bool,
    storage_enabled: bool,
    js_enabled: bool,
    downloads_enabled: bool,
) -> list[str]:
    errors: list[str] = []
    if not stateless_public:
        errors.append("stateless_public_required")
    if cookies_enabled:
        errors.append("cookies_not_granted")
    if storage_enabled:
        errors.append("storage_not_granted")
    if js_enabled:
        errors.append("javascript_not_granted")
    if downloads_enabled:
        errors.append("downloads_not_granted")
    return errors


def _coerce_health_probe(observed: BrowserHealthStatus | str | dict[str, Any]) -> tuple[BrowserHealthStatus, list[str]]:
    if isinstance(observed, dict):
        status = BrowserHealthStatus(str(observed.get("status", BrowserHealthStatus.HEALTHY.value)))
        notes = observed.get("notes", [])
        return status, [str(note) for note in notes] if isinstance(notes, list) else [str(notes)]
    if isinstance(observed, BrowserHealthStatus):
        return observed, []
    return BrowserHealthStatus(str(observed)), []


def _operation_failure_reason(exc: Exception) -> str:
    if isinstance(exc, BrowserOperationError):
        return exc.reason
    return "browser_operation_failed"
