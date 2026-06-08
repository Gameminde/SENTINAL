from __future__ import annotations

from pathlib import Path

from sentinel.operator.store import MissionRunStore
from sentinel.operator.worker_models import WorkerFleetReplayView, WorkerFleetRun
from sentinel.telemetry import TelemetryMetricKind


class WorkerFleetReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str, worker_fleet_run_id: str) -> WorkerFleetReplayView:
        run = self._load_run(mission_id, worker_fleet_run_id)
        events = self._store.load_events(mission_id)
        telemetry_refs = [event.event_hash for event in events if event.event_type.startswith("worker_")]
        replay = WorkerFleetReplayView(
            mission_id=mission_id,
            worker_fleet_run_id=worker_fleet_run_id,
            run=run,
            child_authority_envelopes=run.child_authority_envelopes,
            worker_results=run.worker_results,
            merge_decisions=run.merge_decisions,
            conflict_records=run.conflict_records,
            receipt_refs=_dedupe(ref for result in run.worker_results for ref in result.evidence_packet.receipt_refs),
            finalgate_certificate_refs=_dedupe(
                ref for result in run.worker_results for ref in result.evidence_packet.finalgate_certificate_refs
            ),
            memory_feedback_refs=_dedupe(
                ref for result in run.worker_results for ref in result.evidence_packet.memory_feedback_refs
            ),
            telemetry_refs=_dedupe(telemetry_refs),
            tampered=not run.verify_hash() or not self._store.verify_timeline(mission_id),
            reexecuted_actions=False,
        )
        telemetry_sink = getattr(self._store, "telemetry_sink", None)
        if telemetry_sink is not None and hasattr(telemetry_sink, "record_worker_metric"):
            telemetry_sink.record_worker_metric(
                mission_id,
                metric_kind=TelemetryMetricKind.WORKER_PARALLEL_EFFICIENCY,
                value=0.0,
                safe_summary="Worker fleet replay reconstructed.",
                metadata={"worker_fleet_run_id": worker_fleet_run_id},
            )
        return replay

    def _load_run(self, mission_id: str, worker_fleet_run_id: str) -> WorkerFleetRun:
        path = self._store.mission_dir(mission_id, create=True) / "worker_fleet" / f"{worker_fleet_run_id}.json"
        return WorkerFleetRun.model_validate_json(path.read_text(encoding="utf-8"))


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
