from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.telemetry.models import (
    TelemetryEventRecord,
    TelemetryEventKind,
    TelemetryMetricSample,
    TelemetryMetricKind,
    TelemetrySnapshot,
)


class TelemetryIntegrityError(RuntimeError):
    pass


_TELEMETRY_LOCKS: dict[str, threading.RLock] = {}
_TELEMETRY_LOCKS_GUARD = threading.Lock()


def _filesystem_path(path: Path) -> str:
    rendered = str(path)
    if os.name != "nt" or rendered.startswith("\\\\?\\"):
        return rendered
    if rendered.startswith("\\\\"):
        return "\\\\?\\UNC\\" + rendered[2:]
    return "\\\\?\\" + rendered


def _mkdir_path(path: Path) -> None:
    os.makedirs(_filesystem_path(path), exist_ok=True)


def _path_exists(path: Path) -> bool:
    return os.path.exists(_filesystem_path(path))


def _read_text_file(path: Path) -> str:
    with open(_filesystem_path(path), encoding="utf-8") as handle:
        return handle.read()


class TelemetryStore:
    def __init__(self, root: Path | str, *, enabled: bool = True) -> None:
        self.root = Path(root).resolve()
        _mkdir_path(self.root)
        self.enabled = enabled
        self.events_path = self.root / "events.jsonl"
        self.metrics_path = self.root / "metrics.jsonl"
        self._degradation_reasons: set[str] = set()
        with _TELEMETRY_LOCKS_GUARD:
            self._lock = _TELEMETRY_LOCKS.setdefault(str(self.root), threading.RLock())

    def record_event(self, record: TelemetryEventRecord) -> TelemetryEventRecord:
        if not self.enabled:
            raise TelemetryIntegrityError("telemetry_store_disabled")
        try:
            with self._lock:
                events = self.load_events()
                previous_hash = events[-1].event_hash if events else None
                event = record.model_copy(update={"previous_hash": previous_hash}).with_hash()
                self._append_jsonl(self.events_path, event.safe_model_dump())
                return event
        except Exception as exc:
            self.mark_degraded("telemetry_write_failed")
            raise TelemetryIntegrityError("telemetry_write_failed") from exc

    def record_metric(self, sample: TelemetryMetricSample) -> TelemetryMetricSample:
        if not self.enabled:
            raise TelemetryIntegrityError("telemetry_store_disabled")
        try:
            with self._lock:
                metrics = self.load_metrics()
                previous_hash = metrics[-1].metric_hash if metrics else None
                metric = sample.model_copy(update={"previous_hash": previous_hash}).with_hash()
                self._append_jsonl(self.metrics_path, metric.safe_model_dump())
                return metric
        except Exception as exc:
            self.mark_degraded("telemetry_write_failed")
            raise TelemetryIntegrityError("telemetry_write_failed") from exc

    def mark_degraded(self, reason: str) -> None:
        self._degradation_reasons.add(str(reason))

    def load_events(self) -> list[TelemetryEventRecord]:
        if not _path_exists(self.events_path):
            return []
        return [
            TelemetryEventRecord.model_validate(json.loads(line))
            for line in _read_text_file(self.events_path).splitlines()
            if line.strip()
        ]

    def load_metrics(self) -> list[TelemetryMetricSample]:
        if not _path_exists(self.metrics_path):
            return []
        return [
            TelemetryMetricSample.model_validate(json.loads(line))
            for line in _read_text_file(self.metrics_path).splitlines()
            if line.strip()
        ]

    def verify_events(self) -> bool:
        previous_hash: str | None = None
        for event in self.load_events():
            if event.mission_id is None and event.workflow_id is None and event.session_id is None:
                # Some telemetry events are global, but every record must still chain cleanly.
                pass
            if event.previous_hash != previous_hash:
                return False
            if event.event_hash != _event_hash(event):
                return False
            if event.created_at.tzinfo is None:
                return False
            previous_hash = event.event_hash
        return True

    def verify_metrics(self) -> bool:
        previous_hash: str | None = None
        for metric in self.load_metrics():
            if metric.previous_hash != previous_hash:
                return False
            if metric.metric_hash != _metric_hash(metric):
                return False
            if metric.created_at.tzinfo is None:
                return False
            previous_hash = metric.metric_hash
        return True

    def snapshot(self) -> TelemetrySnapshot:
        reasons: list[str] = sorted(self._degradation_reasons)
        try:
            events = self.load_events()
            event_chain_ok = self.verify_events()
        except Exception:
            events = []
            event_chain_ok = False
            reasons.append("event_chain_unreadable")
        try:
            metrics = self.load_metrics()
            metric_chain_ok = self.verify_metrics()
        except Exception:
            metrics = []
            metric_chain_ok = False
            reasons.append("metric_chain_unreadable")
        if not self.enabled:
            reasons.append("telemetry_disabled")
        if not event_chain_ok:
            reasons.append("event_chain_tampered")
        if not metric_chain_ok:
            reasons.append("metric_chain_tampered")
        if not _path_exists(self.events_path) and not _path_exists(self.metrics_path):
            reasons.append("telemetry_empty")
        reasons = list(dict.fromkeys(reasons))
        event_counts_by_kind: dict[str, int] = {}
        metric_counts_by_kind: dict[str, int] = {}
        domain_counts: dict[str, int] = {}
        latest_provider_backend_model: dict[str, str] | None = None
        for event in events:
            event_counts_by_kind[event.event_kind.value] = event_counts_by_kind.get(event.event_kind.value, 0) + 1
            domain_counts[event.domain.value] = domain_counts.get(event.domain.value, 0) + 1
            if event.event_kind.value == "model_call_started" and event.metadata:
                latest_provider_backend_model = {
                    key: str(event.metadata.get(key, ""))
                    for key in ("provider_id", "backend_id", "model_id")
                    if event.metadata.get(key) is not None
                }
        for metric in metrics:
            metric_counts_by_kind[metric.metric_kind.value] = metric_counts_by_kind.get(metric.metric_kind.value, 0) + 1
            if metric.metric_kind.value == "provider_backend_model_selected" and isinstance(metric.value, dict):
                latest_provider_backend_model = {
                    key: str(metric.value.get(key, ""))
                    for key in ("provider_id", "backend_id", "model_id")
                    if metric.value.get(key) is not None
                }
        for event_kind in TelemetryEventKind:
            event_counts_by_kind.setdefault(event_kind.value, 0)
        for metric_kind in TelemetryMetricKind:
            metric_counts_by_kind.setdefault(metric_kind.value, 0)
        return TelemetrySnapshot(
            root_path=str(self.root),
            telemetry_available=self.enabled,
            event_chain_ok=event_chain_ok,
            metric_chain_ok=metric_chain_ok,
            tampered=not event_chain_ok or not metric_chain_ok,
            certified_mode=self.enabled and event_chain_ok and metric_chain_ok and not self._degradation_reasons,
            reasons=reasons,
            event_count=len(events),
            metric_count=len(metrics),
            event_counts_by_kind=event_counts_by_kind,
            metric_counts_by_kind=metric_counts_by_kind,
            domain_counts=domain_counts,
            latest_event_hash=events[-1].event_hash if events else None,
            latest_metric_hash=metrics[-1].metric_hash if metrics else None,
            latest_provider_backend_model=latest_provider_backend_model,
            product_power_score=_product_power_score(
                events,
                metrics,
                certified=self.enabled and event_chain_ok and metric_chain_ok and not self._degradation_reasons,
            ),
        )

    def certified_mode_status(self) -> TelemetrySnapshot:
        return self.snapshot()

    def _append_jsonl(self, path: Path, payload: Any) -> None:
        rendered = json.dumps(payload, sort_keys=True, default=str)
        with self._lock:
            _mkdir_path(path.parent)
            with open(_filesystem_path(path), "a", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())


def _event_hash(event: TelemetryEventRecord) -> str:
    payload = event.safe_model_dump()
    payload["event_hash"] = ""
    return stable_hash(payload)


def _metric_hash(metric: TelemetryMetricSample) -> str:
    payload = metric.safe_model_dump()
    payload["metric_hash"] = ""
    return stable_hash(payload)


def _product_power_score(events: list[TelemetryEventRecord], metrics: list[TelemetryMetricSample], *, certified: bool) -> float:
    if not events and not metrics:
        return 0.0
    terminal_events = sum(1 for event in events if event.event_kind.value in {"mission_completed", "mission_failed", "mission_killed"})
    useful_metrics = sum(
        1
        for metric in metrics
        if metric.metric_kind.value
        in {
            "mission_completion_rate",
            "time_to_useful_result",
            "timeline_replay_completeness",
            "receipt_completeness",
        }
    )
    score = min(100.0, terminal_events * 10.0 + useful_metrics * 5.0)
    if certified:
        score = min(100.0, score + 25.0)
    return round(score, 2)
