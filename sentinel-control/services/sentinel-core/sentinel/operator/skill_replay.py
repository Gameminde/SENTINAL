from __future__ import annotations

from sentinel.operator.skill_models import ProcedureReplayView
from sentinel.operator.store import MissionRunStore


class ProcedureReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self.store = store

    def build(self, mission_id: str, *, procedure_run_id: str | None = None) -> ProcedureReplayView:
        timeline_valid = self.store.verify_timeline(mission_id)
        lifecycle_events: list[str] = []
        procedure_step_events: list[str] = []
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        memory_refs: list[str] = []
        telemetry_refs: list[str] = []
        skill_id: str | None = None
        version: str | None = None
        rollback_posture: str | None = None
        scan_refs: list[str] = []

        for event in self.store.load_events(mission_id):
            if event.event_type.startswith("skill_"):
                lifecycle_events.append(event.event_type)
            if event.event_type.startswith("procedure_step_"):
                procedure_step_events.append(event.event_type)
            if event.event_hash:
                telemetry_refs.append(event.event_hash)
            metadata = event.metadata or {}
            if metadata.get("skill_id"):
                skill_id = str(metadata["skill_id"])
            if metadata.get("version"):
                version = str(metadata["version"])
            if metadata.get("scanner_result_id"):
                scan_refs.append(str(metadata["scanner_result_id"]))
            if metadata.get("rollback_posture"):
                rollback_posture = str(metadata["rollback_posture"])
            receipt_refs.extend(event.receipt_refs)
            finalgate_refs.extend(event.finalgate_certificate_refs)
            memory_refs.extend(event.memory_feedback_refs)

        if rollback_posture is None:
            rollback_posture = _load_run_rollback_posture(self.store, mission_id, procedure_run_id)

        return ProcedureReplayView(
            mission_id=mission_id,
            skill_id=skill_id,
            version=version,
            procedure_run_id=procedure_run_id,
            manifest_version=version,
            scan_result_refs=list(dict.fromkeys(scan_refs)),
            lifecycle_events=lifecycle_events,
            procedure_step_events=procedure_step_events,
            receipt_refs=list(dict.fromkeys(receipt_refs)),
            finalgate_certificate_refs=list(dict.fromkeys(finalgate_refs)),
            memory_feedback_refs=list(dict.fromkeys(memory_refs)),
            telemetry_refs=list(dict.fromkeys(telemetry_refs)),
            rollback_posture=rollback_posture,
            timeline_valid=timeline_valid,
            reexecuted_actions=False,
        )


def _load_run_rollback_posture(
    store: MissionRunStore,
    mission_id: str,
    procedure_run_id: str | None,
) -> str | None:
    if procedure_run_id is None:
        return None
    root = store.mission_dir(mission_id) / "skill_fabric" / "procedure_runs"
    if not root.exists():
        return None
    for path in root.glob("*.json"):
        try:
            payload = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if procedure_run_id not in payload:
            continue
        if "no_external_side_effects" in payload:
            return "no_external_side_effects"
        return "recorded"
    return None
