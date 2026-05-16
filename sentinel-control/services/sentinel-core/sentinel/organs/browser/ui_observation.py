from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import Field

from sentinel.organs.browser.models import BrowserAccessibilitySnapshot
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserUIObservationSource(StrEnum):
    ACCESSIBILITY_SNAPSHOT = "accessibility_snapshot"
    CDP_AX_TREE = "cdp_ax_tree"
    DOM_SNAPSHOT = "dom_snapshot"
    SCREENSHOT_REGION = "screenshot_region"
    ZOOM_REGION = "zoom_region"
    NETWORK_DELTA = "network_delta"


class BrowserUIObservationStatus(StrEnum):
    CAPTURED = "captured"
    REJECTED = "rejected"


class BrowserBoundingBox(SentinelModel):
    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(ge=0)
    height: float = Field(ge=0)


class BrowserUIObservation(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bui"))
    mission_id: str
    source: BrowserUIObservationSource
    url: str
    tab_id: str | None = None
    frame_id: str | None = None
    ref_id: str | None = None
    role: str | None = None
    name: str | None = None
    text: str | None = None
    bbox: BrowserBoundingBox | None = None
    visible: bool | None = None
    interactable: bool | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    dom_path: str | None = None
    ax_path: str | None = None
    network_delta_refs: list[str] = Field(default_factory=list)
    screenshot_sha256: str | None = None
    page_sha256: str | None = None
    snapshot_sha256: str | None = None
    uncertainty_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserUIObservationSet(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("buiset"))
    mission_id: str
    url: str
    observations: list[BrowserUIObservation] = Field(default_factory=list)
    observation_sha256: str
    source_count: int = Field(ge=0)
    trace_refs: list[str] = Field(default_factory=list)


class BrowserUIObservationBuilder:
    """Builds a unified UI observation layer from certified browser perception sources."""

    def from_accessibility_snapshot(
        self,
        *,
        mission_id: str,
        url: str,
        snapshot: BrowserAccessibilitySnapshot,
        event_bus: EventBus | None = None,
        tab_id: str | None = None,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserUIObservationSet:
        observations = [
            BrowserUIObservation(
                mission_id=mission_id,
                source=BrowserUIObservationSource.ACCESSIBILITY_SNAPSHOT,
                url=url,
                tab_id=tab_id,
                ref_id=ref_id,
                role=ref.role,
                name=ref.name,
                visible=True,
                interactable=ref.role
                in {
                    "button",
                    "link",
                    "textbox",
                    "checkbox",
                    "radio",
                    "combobox",
                    "listbox",
                    "option",
                    "searchbox",
                    "slider",
                    "spinbutton",
                    "switch",
                    "tab",
                },
                attrs={"nth": ref.nth} if ref.nth is not None else {},
                ax_path=f"accessibility_snapshot.refs.{ref_id}",
                page_sha256=snapshot.page_sha256,
                snapshot_sha256=snapshot.snapshot_sha256,
                uncertainty_score=0.15,
                trace_refs=list(trace_refs or []),
            )
            for ref_id, ref in sorted(snapshot.refs.items())
        ]
        return self._finalize(
            mission_id=mission_id,
            url=url,
            observations=observations,
            event_bus=event_bus,
            source=BrowserUIObservationSource.ACCESSIBILITY_SNAPSHOT,
            trace_refs=list(trace_refs or []),
            phase=phase,
        )

    def from_cdp_ax_nodes(
        self,
        *,
        mission_id: str,
        url: str,
        nodes: list[dict[str, Any]],
        tree_sha256: str,
        page_sha256: str | None = None,
        event_bus: EventBus | None = None,
        tab_id: str | None = None,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserUIObservationSet:
        observations: list[BrowserUIObservation] = []
        for index, node in enumerate(nodes):
            ref_id = str(node.get("ref_id") or node.get("backend_node_id") or node.get("node_id") or f"ax{index + 1}")
            observations.append(
                BrowserUIObservation(
                    mission_id=mission_id,
                    source=BrowserUIObservationSource.CDP_AX_TREE,
                    url=url,
                    tab_id=tab_id,
                    ref_id=ref_id,
                    role=_optional_str(node.get("role")),
                    name=_optional_str(node.get("name")),
                    text=_optional_str(node.get("value")),
                    visible=_optional_bool(node.get("visible")),
                    interactable=_optional_bool(node.get("interactable")),
                    attrs=dict(node.get("attrs") or {}),
                    ax_path=str(node.get("ax_path") or f"cdp_ax.nodes.{index}"),
                    page_sha256=page_sha256,
                    snapshot_sha256=tree_sha256,
                    uncertainty_score=0.05,
                    trace_refs=list(trace_refs or []),
                )
            )
        return self._finalize(
            mission_id=mission_id,
            url=url,
            observations=observations,
            event_bus=event_bus,
            source=BrowserUIObservationSource.CDP_AX_TREE,
            trace_refs=list(trace_refs or []),
            phase=phase,
        )

    def from_dom_nodes(
        self,
        *,
        mission_id: str,
        url: str,
        nodes: list[dict[str, Any]],
        snapshot_sha256: str,
        event_bus: EventBus | None = None,
        tab_id: str | None = None,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserUIObservationSet:
        observations: list[BrowserUIObservation] = []
        for index, node in enumerate(nodes):
            bbox_raw = node.get("bbox")
            observations.append(
                BrowserUIObservation(
                    mission_id=mission_id,
                    source=BrowserUIObservationSource.DOM_SNAPSHOT,
                    url=url,
                    tab_id=tab_id,
                    ref_id=_optional_str(node.get("ref_id")),
                    role=_optional_str(node.get("role")),
                    name=_optional_str(node.get("name")),
                    text=_optional_str(node.get("text")),
                    bbox=BrowserBoundingBox(**bbox_raw) if isinstance(bbox_raw, dict) else None,
                    visible=_optional_bool(node.get("visible")),
                    interactable=_optional_bool(node.get("interactable")),
                    attrs=dict(node.get("attrs") or {}),
                    dom_path=str(node.get("dom_path") or f"dom_snapshot.nodes.{index}"),
                    snapshot_sha256=snapshot_sha256,
                    uncertainty_score=0.1,
                    trace_refs=list(trace_refs or []),
                )
            )
        return self._finalize(
            mission_id=mission_id,
            url=url,
            observations=observations,
            event_bus=event_bus,
            source=BrowserUIObservationSource.DOM_SNAPSHOT,
            trace_refs=list(trace_refs or []),
            phase=phase,
        )

    @staticmethod
    def _finalize(
        *,
        mission_id: str,
        url: str,
        observations: list[BrowserUIObservation],
        event_bus: EventBus | None,
        source: BrowserUIObservationSource,
        trace_refs: list[str],
        phase: AgentPhase,
    ) -> BrowserUIObservationSet:
        payload = {
            "mission_id": mission_id,
            "url": url,
            "observations": [observation.model_dump(mode="json") for observation in observations],
            "source_count": len({observation.source.value for observation in observations}),
        }
        observation_set = BrowserUIObservationSet(
            mission_id=mission_id,
            url=url,
            observations=observations,
            source_count=payload["source_count"],
            observation_sha256=hash_ui_observation_payload(payload),
            trace_refs=trace_refs,
        )
        if event_bus is not None:
            if event_bus.mission_id != mission_id:
                raise ValueError("UI observation event bus mission_id must match mission_id.")
            event = event_bus.append(
                AgentEventType.BROWSER_UI_OBSERVATION_CAPTURED,
                "Browser V2.5 UI observation set captured from certified perception source.",
                phase_before=phase,
                phase_after=phase,
                payload={
                    "observation_set_id": observation_set.id,
                    "observation_sha256": observation_set.observation_sha256,
                    "observation_set": observation_set.model_dump(mode="json"),
                    "source": source.value,
                    "source_count": observation_set.source_count,
                    "observation_count": len(observation_set.observations),
                    "url": url,
                    "stateless_public": True,
                    "cookies_enabled": False,
                    "storage_enabled": False,
                    "js_enabled": False,
                    "downloads_enabled": False,
                },
                trace_refs=trace_refs,
            )
            observation_set = observation_set.model_copy(update={"trace_refs": [*trace_refs, event.id]})
        return observation_set


def hash_ui_observation_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_ui_observation_hash(observation_set: dict[str, Any], expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    payload = {
        "mission_id": observation_set.get("mission_id"),
        "url": observation_set.get("url"),
        "observations": observation_set.get("observations", []),
        "source_count": observation_set.get("source_count", 0),
    }
    return hash_ui_observation_payload(payload) == expected_hash


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
