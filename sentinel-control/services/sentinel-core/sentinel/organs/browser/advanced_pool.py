from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserPublicPoolInstanceStatus(StrEnum):
    IDLE = "idle"
    LEASED = "leased"
    DEGRADED = "degraded"


class BrowserAdvancedPoolLeaseStatus(StrEnum):
    LEASED = "leased"
    RELEASED = "released"
    REJECTED = "rejected"


class BrowserPublicPoolInstance(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bpinst"))
    backend_kind: str = "playwright_public"
    status: BrowserPublicPoolInstanceStatus = BrowserPublicPoolInstanceStatus.IDLE
    mission_id: str | None = None
    lease_id: str | None = None
    stateless_public: bool = True
    cookies_enabled: bool = False
    storage_enabled: bool = False
    js_enabled: bool = False
    downloads_enabled: bool = False
    health_notes: list[str] = Field(default_factory=list)


class BrowserAdvancedPoolLease(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("baplease"))
    mission_id: str
    instance_id: str
    purpose: str
    status: BrowserAdvancedPoolLeaseStatus = BrowserAdvancedPoolLeaseStatus.LEASED
    trace_refs: list[str] = Field(default_factory=list)


class BrowserAdvancedPoolResult(SentinelModel):
    accepted: bool
    status: BrowserAdvancedPoolLeaseStatus
    reason: str
    lease: BrowserAdvancedPoolLease | None = None
    instance: BrowserPublicPoolInstance | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserPublicPoolManager:
    """Manages warm public/stateless browser instance leases without private profile state."""

    def __init__(self, *, capacity: int = 2, backend_kind: str = "playwright_public") -> None:
        if capacity < 1:
            raise ValueError("browser_public_pool_capacity_must_be_positive")
        self.capacity = capacity
        self.backend_kind = backend_kind
        self.instances = {
            instance.id: instance
            for instance in [
                BrowserPublicPoolInstance(backend_kind=backend_kind)
                for _ in range(capacity)
            ]
        }
        self.leases: dict[str, BrowserAdvancedPoolLease] = {}

    def start(
        self,
        *,
        mission_id: str,
        event_bus: EventBus,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> None:
        self._require_mission(event_bus, mission_id)
        event_bus.append(
            AgentEventType.BROWSER_ADVANCED_POOL_STARTED,
            "Browser V2.5 public stateless pool started with warm instance ledger.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "capacity": self.capacity,
                "backend_kind": self.backend_kind,
                "instance_ids": sorted(self.instances),
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
        )

    def lease(
        self,
        *,
        mission_id: str,
        purpose: str,
        event_bus: EventBus,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserAdvancedPoolResult:
        self._require_mission(event_bus, mission_id)
        instance = next((item for item in self.instances.values() if item.status == BrowserPublicPoolInstanceStatus.IDLE), None)
        if instance is None:
            return self._reject(
                mission_id=mission_id,
                reason="browser_public_pool_capacity_exhausted",
                event_bus=event_bus,
                phase=phase,
            )
        lease = BrowserAdvancedPoolLease(mission_id=mission_id, instance_id=instance.id, purpose=purpose)
        event = event_bus.append(
            AgentEventType.BROWSER_ADVANCED_POOL_LEASED,
            "Browser V2.5 public stateless pool instance leased.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "lease_id": lease.id,
                "instance_id": instance.id,
                "purpose": purpose,
                "backend_kind": instance.backend_kind,
                "status": BrowserAdvancedPoolLeaseStatus.LEASED.value,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
        )
        lease = lease.model_copy(update={"trace_refs": [event.id]})
        instance = instance.model_copy(
            update={
                "status": BrowserPublicPoolInstanceStatus.LEASED,
                "mission_id": mission_id,
                "lease_id": lease.id,
            }
        )
        self.instances[instance.id] = instance
        self.leases[lease.id] = lease
        return BrowserAdvancedPoolResult(
            accepted=True,
            status=BrowserAdvancedPoolLeaseStatus.LEASED,
            reason="browser_public_pool_instance_leased",
            lease=lease,
            instance=instance,
            trace_event_id=event.id,
        )

    def release(
        self,
        *,
        lease_id: str,
        event_bus: EventBus,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserAdvancedPoolResult:
        lease = self.leases.get(lease_id)
        if lease is None:
            return self._reject(
                mission_id=event_bus.mission_id,
                reason="browser_public_pool_lease_missing",
                event_bus=event_bus,
                phase=phase,
                lease_id=lease_id,
            )
        self._require_mission(event_bus, lease.mission_id)
        instance = self.instances.get(lease.instance_id)
        if instance is None or instance.lease_id != lease.id:
            return self._reject(
                mission_id=lease.mission_id,
                reason="browser_public_pool_instance_mismatch",
                event_bus=event_bus,
                phase=phase,
                lease_id=lease_id,
            )
        event = event_bus.append(
            AgentEventType.BROWSER_ADVANCED_POOL_RELEASED,
            "Browser V2.5 public stateless pool instance released.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "lease_id": lease.id,
                "instance_id": instance.id,
                "backend_kind": instance.backend_kind,
                "status": BrowserAdvancedPoolLeaseStatus.RELEASED.value,
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
            },
            trace_refs=lease.trace_refs,
        )
        released_lease = lease.model_copy(update={"status": BrowserAdvancedPoolLeaseStatus.RELEASED, "trace_refs": [*lease.trace_refs, event.id]})
        released_instance = instance.model_copy(
            update={"status": BrowserPublicPoolInstanceStatus.IDLE, "mission_id": None, "lease_id": None}
        )
        self.leases[lease.id] = released_lease
        self.instances[instance.id] = released_instance
        return BrowserAdvancedPoolResult(
            accepted=True,
            status=BrowserAdvancedPoolLeaseStatus.RELEASED,
            reason="browser_public_pool_instance_released",
            lease=released_lease,
            instance=released_instance,
            trace_event_id=event.id,
        )

    @staticmethod
    def _require_mission(event_bus: EventBus, mission_id: str) -> None:
        if event_bus.mission_id != mission_id:
            raise ValueError("Browser public pool event bus mission_id must match mission_id.")

    @staticmethod
    def _reject(
        *,
        mission_id: str,
        reason: str,
        event_bus: EventBus,
        phase: AgentPhase,
        lease_id: str | None = None,
    ) -> BrowserAdvancedPoolResult:
        event = event_bus.append(
            AgentEventType.BROWSER_SUPERVISOR_REJECTED,
            "Browser V2.5 public stateless pool request rejected.",
            phase_before=phase,
            phase_after=phase,
            payload={
                "action": "advanced_pool",
                "operation_name": "advanced_pool",
                "lease_id": lease_id,
                "reason": reason,
                "errors": [reason],
                "stateless_public": True,
                "cookies_enabled": False,
                "storage_enabled": False,
                "js_enabled": False,
                "downloads_enabled": False,
                "status": BrowserAdvancedPoolLeaseStatus.REJECTED.value,
            },
        )
        return BrowserAdvancedPoolResult(
            accepted=False,
            status=BrowserAdvancedPoolLeaseStatus.REJECTED,
            reason=reason,
            trace_event_id=event.id,
            errors=[reason],
        )
