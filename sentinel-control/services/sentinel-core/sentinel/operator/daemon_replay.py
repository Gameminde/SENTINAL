from __future__ import annotations

from sentinel.operator.daemon_models import DaemonReplayView
from sentinel.operator.daemon_store import MissionDaemonStore
from sentinel.operator.store import MissionRunStore


class DaemonReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store
        self._daemon_store = MissionDaemonStore(store)

    def build(self, mission_id: str) -> DaemonReplayView:
        events = self._store.load_events(mission_id)
        telemetry_refs = [event.event_hash for event in events if event.event_type.startswith(("daemon_", "scheduler_", "operator_"))]
        return DaemonReplayView(
            mission_id=mission_id,
            queue=[record for record in self._daemon_store.list_queue() if record.mission_id == mission_id],
            leases=[record for record in self._daemon_store.list_leases() if record.mission_id == mission_id],
            heartbeats=[record for record in self._daemon_store.list_heartbeats() if record.mission_id == mission_id],
            dead_letters=self._daemon_store.list_dead_letters_for_mission(mission_id),
            telemetry_refs=list(dict.fromkeys(telemetry_refs)),
            tampered=not self._daemon_store.verify(mission_id),
            reexecuted_actions=False,
        )
