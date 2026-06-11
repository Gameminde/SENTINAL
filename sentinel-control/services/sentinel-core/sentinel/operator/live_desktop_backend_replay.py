from __future__ import annotations

from pathlib import Path
from typing import Any

from sentinel.operator.desktop_sidecar_models import DesktopMonitoringResult
from sentinel.operator.live_desktop_backend_models import (
    DesktopActionExecutionPlan,
    DesktopActionExecutionResult,
    DesktopBenchmarkRun,
    DesktopMonitoringTick,
    DesktopOperatorSession,
    LiveDesktopBackendConfig,
    LiveDesktopBackendReplayView,
)
from sentinel.operator.store import MissionRunStore


class LiveDesktopBackendReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str) -> LiveDesktopBackendReplayView:
        root = self._root(mission_id)
        configs = _load_many(root / "configs", LiveDesktopBackendConfig)
        sessions = _load_many(root / "sessions", DesktopOperatorSession)
        monitoring_results = _load_many(root / "monitoring", DesktopMonitoringResult)
        monitoring_ticks = _load_many(root / "monitoring_ticks", DesktopMonitoringTick)
        action_plans = _load_many(root / "action_plans", DesktopActionExecutionPlan)
        action_results = _load_many(root / "action_results", DesktopActionExecutionResult)
        benchmark_runs = _load_many(root / "benchmarks", DesktopBenchmarkRun)
        tampered = not self._store.verify_timeline(mission_id)
        for collection in (configs, sessions, monitoring_results, monitoring_ticks, action_plans, action_results, benchmark_runs):
            for item in collection:
                if hasattr(item, "verify_hash") and not item.verify_hash():
                    tampered = True
        events = [
            event
            for event in self._store.load_events(mission_id)
            if event.event_type.startswith("desktop_") or event.event_type.startswith("live_desktop_")
        ]
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        for item in action_results:
            if item.action_receipt is not None:
                receipt_refs.append(item.action_receipt.receipt_id)
            if item.finalgate_certificate is not None:
                finalgate_refs.append(item.finalgate_certificate.certificate_id)
        for item in monitoring_results:
            if item.monitoring_receipt is not None:
                receipt_refs.append(item.monitoring_receipt.receipt_id)
        for run in benchmark_runs:
            receipt_refs.extend(run.receipt_refs)
            finalgate_refs.extend(run.finalgate_refs)
        return LiveDesktopBackendReplayView(
            mission_id=mission_id,
            configs=configs,
            sessions=sessions,
            monitoring_results=monitoring_results,
            monitoring_ticks=monitoring_ticks,
            action_plans=action_plans,
            action_results=action_results,
            benchmark_runs=benchmark_runs,
            receipt_refs=list(dict.fromkeys(receipt_refs)),
            finalgate_refs=list(dict.fromkeys(finalgate_refs)),
            telemetry_refs=list(dict.fromkeys(event.event_hash for event in events)),
            tampered=tampered,
            recollected_system_metrics=False,
            reexecuted_actions=False,
        )

    def _root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id) / "desktop_sidecar" / "live_backend"


def _load_many(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]
