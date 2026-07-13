from __future__ import annotations

from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel, new_id


class BrowserObservationBundle(SentinelModel):
    bundle_id: str = Field(default_factory=lambda: new_id("browser_observation_bundle"))
    source: str = "real_browser_control_runtime"
    page_state_hash: str
    devtools_sensor_consumed: bool = False
    network_events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    console_events: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    raw_material_persisted: bool = False
    data_not_authority: bool = True
    can_execute: bool = False
    can_grant_authority: bool = False

    def safe_model_dump(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def build_browser_observation_bundle(
    *,
    page_state_hash: str,
    devtools_context: dict[str, Any] | None = None,
) -> BrowserObservationBundle:
    safe_metadata = devtools_context.get("safe_metadata") if isinstance(devtools_context, dict) else None
    safe_metadata = safe_metadata if isinstance(safe_metadata, dict) else {}
    network_count = _safe_int(safe_metadata.get("network_event_count"))
    console_error_count = _safe_int(safe_metadata.get("console_error_count"))
    network_events: list[dict[str, Any]] = []
    if network_count:
        network_events.append(
            {
                "event_class": "network_activity",
                "count": network_count,
                "request_classes_hash": stable_hash(safe_metadata.get("request_classes") or {}),
                "response_status_classes_hash": stable_hash(safe_metadata.get("response_status_classes") or {}),
                "query_linked_request_evidence": bool(safe_metadata.get("query_linked_request_evidence")),
            }
        )
    console_events: list[dict[str, Any]] = []
    if console_error_count:
        console_events.append({"event_class": "console_error", "count": console_error_count})
    evidence_refs = []
    if network_events:
        evidence_refs.append(f"network:{stable_hash(network_events)}")
    if console_events:
        evidence_refs.append(f"console:{stable_hash(console_events)}")
    return BrowserObservationBundle(
        page_state_hash=page_state_hash,
        devtools_sensor_consumed=bool(devtools_context),
        network_events=tuple(network_events),
        console_events=tuple(console_events),
        evidence_refs=tuple(evidence_refs),
        raw_material_persisted=False,
    )


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


__all__ = ["BrowserObservationBundle", "build_browser_observation_bundle"]
