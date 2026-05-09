from __future__ import annotations

from pydantic import Field

from sentinel.shared.models import SentinelModel, new_id


class SidecarKillSwitch(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("dsk"))
    mission_id: str
    sidecar_id: str
    triggered: bool = False
    reason: str | None = None
    authority_expansion: bool = False

    @property
    def execution_allowed(self) -> bool:
        return not self.triggered

    def trigger(self, *, reason: str) -> SidecarKillSwitch:
        return self.model_copy(update={"triggered": True, "reason": reason})
