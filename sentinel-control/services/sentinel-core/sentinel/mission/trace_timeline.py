from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from sentinel.mission.models import MissionTraceEvent
from sentinel.shared.enums import MissionTraceEventType, ReversibilityLevel
from sentinel.shared.models import new_id


MISSION_TRACE_PROJECTION_FAILED = "MISSION_TRACE_PROJECTION_FAILED"


class MissionTraceProjectionError(RuntimeError):
    def __init__(self, code: str = MISSION_TRACE_PROJECTION_FAILED, safe_message: str = "Mission trace projection failed.") -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class MissionTraceEventSink(Protocol):
    def emit_mission_trace_event(self, event: MissionTraceEvent) -> None:
        ...


class MissionTraceTimeline:
    def __init__(
        self,
        mission_id: str,
        project_dir: str | Path | None = None,
        *,
        event_sink: MissionTraceEventSink | None = None,
    ) -> None:
        self.mission_id = mission_id
        self.project_dir = Path(project_dir).resolve() if project_dir else None
        self.events: list[MissionTraceEvent] = []
        self._last_hash: str | None = None
        self._event_sink = event_sink
        self._projection_failed_code: str | None = None

    @property
    def timeline_path(self) -> Path | None:
        if self.project_dir is None:
            return None
        return self.project_dir / "mission_timeline.json"

    def bind_project_dir(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir).resolve()
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.persist()

    def emit(
        self,
        event_type: MissionTraceEventType,
        summary: str,
        *,
        actor: str = "sentinel",
        action_id: str | None = None,
        target: str | None = None,
        result: dict[str, Any] | None = None,
        impact: str | None = None,
        reversible: bool = True,
        cost: float = 0.0,
    ) -> MissionTraceEvent:
        if self._projection_failed_code is not None:
            raise MissionTraceProjectionError(
                self._projection_failed_code,
                "Mission trace timeline is closed after projection failure.",
            )
        sequence = len(self.events)
        event_data = {
            "id": new_id("mev"),
            "mission_id": self.mission_id,
            "sequence": sequence,
            "logical_time": sequence,
            "event_type": event_type,
            "actor": actor,
            "action_id": action_id,
            "summary": summary,
            "target": target,
            "result": deepcopy(result) if result is not None else {},
            "impact": impact,
            "reversible": reversible,
            "cost": cost,
            "timestamp": datetime.now(UTC),
            "previous_hash": self._last_hash,
            "event_hash": "",
        }
        event_hash = self._hash_payload(event_data)
        event = MissionTraceEvent(**{**event_data, "event_hash": event_hash})
        self.events.append(event)
        self._last_hash = event_hash
        if self.project_dir is not None:
            self.persist()
        if self._event_sink is not None:
            try:
                self._event_sink.emit_mission_trace_event(event)
            except Exception as exc:  # noqa: BLE001
                self._projection_failed_code = MISSION_TRACE_PROJECTION_FAILED
                raise MissionTraceProjectionError() from exc
        return event

    def emit_action_planned(self, action_id: str, summary: str, target: str | None = None) -> MissionTraceEvent:
        return self.emit(
            MissionTraceEventType.ACTION_PLANNED,
            summary,
            action_id=action_id,
            target=target,
        )

    def emit_route(self, action_id: str, route: str, risk_score: float, reasons: list[str]) -> MissionTraceEvent:
        return self.emit(
            MissionTraceEventType.ACTION_ROUTED,
            f"Action routed to {route}.",
            action_id=action_id,
            result={"route": route, "risk_score": risk_score, "reasons": list(reasons)},
            impact="Mission authority boundary evaluated.",
        )

    def emit_executed(self, action_id: str, summary: str, result: dict[str, Any], reversibility: ReversibilityLevel) -> MissionTraceEvent:
        return self.emit(
            MissionTraceEventType.ACTION_EXECUTED,
            summary,
            action_id=action_id,
            target=str(result.get("path") or result.get("folder_path") or result.get("type") or ""),
            result=result,
            reversible=reversibility != ReversibilityLevel.IRREVERSIBLE,
            cost=float(result.get("cost", 0.0) or 0.0),
        )

    def persist(self) -> None:
        path = self.timeline_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps([event.model_dump(mode="json") for event in self.events], indent=2),
            encoding="utf-8",
        )

    def verify_chain(self) -> bool:
        return self.verify_events(self.events)

    @classmethod
    def verify_events(cls, events: Iterable[MissionTraceEvent]) -> bool:
        previous_hash: str | None = None
        seen_ids: set[str] = set()
        for index, event in enumerate(events):
            if event.id in seen_ids:
                return False
            seen_ids.add(event.id)
            if event.sequence != index or event.logical_time != index:
                return False
            if event.previous_hash != previous_hash:
                return False
            event_data = event.model_dump()
            event_hash = event_data.pop("event_hash")
            if cls._hash_payload(event_data) != event_hash:
                return False
            previous_hash = event_hash
        return True

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        serializable = dict(payload)
        serializable.pop("event_hash", None)
        canonical = json.dumps(serializable, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
