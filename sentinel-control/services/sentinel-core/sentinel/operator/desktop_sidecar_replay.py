from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.desktop_sidecar_models import (
    DesktopActionApproval,
    DesktopActionPreview,
    DesktopActionResult,
    DesktopMonitoringResult,
    DesktopObservationResult,
    DesktopSidecarConfig,
    DesktopSidecarReceipt,
    DesktopSidecarReplayView,
    DesktopVisualGroundingResult,
)
from sentinel.operator.store import MissionRunStore


class DesktopSidecarReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str) -> DesktopSidecarReplayView:
        root = self._root(mission_id)
        configs = _load_many(root / "configs", DesktopSidecarConfig)
        observations = _load_many(root / "observations", DesktopObservationResult)
        monitoring = _load_many(root / "monitoring", DesktopMonitoringResult)
        grounding = _load_many(root / "grounding", DesktopVisualGroundingResult)
        previews = _load_many(root / "previews", DesktopActionPreview)
        approvals = _load_many(root / "approvals", DesktopActionApproval)
        action_results = _load_many(root / "action_results", DesktopActionResult)
        receipts = _load_many(root / "receipts", DesktopSidecarReceipt)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (configs, observations, monitoring, grounding, previews, approvals, action_results, receipts):
            for item in collection:
                if hasattr(item, "verify_hash") and not item.verify_hash():
                    tampered = True
        events = [
            event
            for event in self._store.load_events(mission_id)
            if event.event_type.startswith("desktop_")
        ]
        finalgate_refs = []
        for item in [*observations, *grounding, *action_results]:
            cert = getattr(item, "finalgate_certificate", None)
            if cert is not None:
                finalgate_refs.append(cert.certificate_id)
        return DesktopSidecarReplayView(
            mission_id=mission_id,
            configs=configs,
            observations=observations,
            monitoring_results=monitoring,
            grounding_results=grounding,
            action_previews=previews,
            approvals=approvals,
            action_results=action_results,
            receipts=receipts,
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            memory_feedback_refs=[],
            tampered=tampered,
            recaptured_screenshots=False,
            reexecuted_actions=False,
        )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id) / "desktop_sidecar"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]
