from __future__ import annotations

from sentinel.operator.replay import MissionReplayBuilder
from sentinel.operator.workflow_models import WorkflowReplayView
from sentinel.operator.workflow_store import DurableWorkflowStore


class DurableWorkflowReplayBuilder:
    def __init__(self, store: DurableWorkflowStore) -> None:
        self._store = store

    def build(self, workflow_id: str) -> WorkflowReplayView:
        try:
            record = self._store.load(workflow_id)
            checkpoints = self._store.list_checkpoints(workflow_id)
            verified = self._store.verify(workflow_id)
        except (OSError, ValueError, KeyError):
            return WorkflowReplayView(
                workflow_id=workflow_id,
                mission_id="unknown",
                record=None,
                checkpoints=[],
                tampered=True,
                reexecuted_actions=False,
        )
        mission_replay = MissionReplayBuilder(self._store.mission_store).build(record.mission_id)
        replay = WorkflowReplayView(
            workflow_id=workflow_id,
            mission_id=record.mission_id,
            record=record,
            checkpoints=checkpoints,
            tampered=not verified or mission_replay.tampered,
            reexecuted_actions=False,
        )
        telemetry_sink = getattr(self._store.mission_store, "telemetry_sink", None)
        if telemetry_sink is not None and hasattr(telemetry_sink, "record_replay_view"):
            telemetry_sink.record_replay_view(replay)
        return replay
