from __future__ import annotations

from sentinel.mission.cancellation import CancellationToken
from sentinel.mission.models import MissionAuthorityEnvelope, MissionState, utc_now
from sentinel.mission.trace_timeline import MissionTraceTimeline
from sentinel.shared.enums import MissionStatus, MissionTraceEventType


class MissionKillSwitch:
    def pause(self, state: MissionState, timeline: MissionTraceTimeline | None = None) -> MissionState:
        updated = state.model_copy(update={"status": MissionStatus.PAUSED, "updated_at": utc_now()})
        if timeline:
            timeline.emit(MissionTraceEventType.MISSION_PAUSED, "Mission paused after current safe step.")
        return updated

    def stop(self, state: MissionState, timeline: MissionTraceTimeline | None = None) -> MissionState:
        updated = state.model_copy(update={"status": MissionStatus.STOPPED, "updated_at": utc_now(), "ended_at": utc_now()})
        if timeline:
            timeline.emit(MissionTraceEventType.MISSION_STOPPED, "Mission stopped and queued work interrupted.")
        return updated

    def revoke(
        self,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
        timeline: MissionTraceTimeline | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> tuple[MissionAuthorityEnvelope, MissionState]:
        """Revoke mission authority.

        Task 4 / Requirement 4 (F-A3.10) — reactive kill-switch.

        Stamps ``envelope.revoked_at`` (declarative signal polled by
        :meth:`sentinel.mission.runner.MissionRunner._check_revocation`)
        AND cancels the optional shared
        :class:`sentinel.mission.cancellation.CancellationToken` so organ
        adapters performing network I/O can interrupt within one event-loop
        tick (CP-4.2 Bounded Latency).
        """
        revoked_at = utc_now()
        updated_envelope = envelope.model_copy(update={"revoked_at": revoked_at})
        updated_state = state.model_copy(update={"status": MissionStatus.REVOKED, "updated_at": revoked_at, "ended_at": revoked_at})
        if cancellation_token is not None:
            cancellation_token.cancel()
        if timeline:
            timeline.emit(MissionTraceEventType.MISSION_REVOKED, "Mission authority revoked; all future actions are blocked.")
        return updated_envelope, updated_state
