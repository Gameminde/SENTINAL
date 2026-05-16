from __future__ import annotations

from pydantic import Field

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel, new_id


class OrganKillSwitch(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("okill"))
    mission_id: str
    organ_id: str
    enabled: bool = True
    triggered: bool = False
    reason: str | None = None
    execution_allowed: bool = True
    authority_expansion: bool = False
    trace_refs: list[str] = Field(default_factory=list)

    def trigger(self, *, reason: str, event_bus: EventBus | None = None) -> OrganKillSwitch:
        updated = self.model_copy(update={"triggered": True, "reason": reason, "execution_allowed": False})
        if event_bus is None:
            return updated
        event = event_bus.append(
            AgentEventType.ORGAN_KILL_SWITCH_TRIGGERED,
            "External organ kill switch triggered.",
            payload={
                "kill_switch_id": self.id,
                "organ_id": self.organ_id,
                "reason": reason,
                "execution_allowed": False,
                "authority_expansion": False,
            },
        )
        return updated.model_copy(update={"trace_refs": [*self.trace_refs, event.id]})
