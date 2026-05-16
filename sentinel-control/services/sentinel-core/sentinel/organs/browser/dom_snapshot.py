from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field

from sentinel.organs.browser.ui_observation import BrowserBoundingBox
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserDomSnapshotNode(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bdom"))
    node_index: int = Field(ge=0)
    tag: str
    role: str | None = None
    name: str | None = None
    text: str | None = None
    attrs: dict[str, str] = Field(default_factory=dict)
    dom_path: str
    parent_index: int | None = Field(default=None, ge=0)
    visible: bool = True
    interactable: bool = False
    bbox: BrowserBoundingBox | None = None
    ref_id: str | None = None


class BrowserDomSnapshot(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bdomsnap"))
    mission_id: str
    url: str
    nodes: list[BrowserDomSnapshotNode] = Field(default_factory=list)
    node_count: int = Field(default=0, ge=0)
    layout_count: int = Field(default=0, ge=0)
    snapshot_sha256: str
    trace_refs: list[str] = Field(default_factory=list)


class BrowserDomSnapshotCaptureResult(SentinelModel):
    accepted: bool
    reason: str
    snapshot: BrowserDomSnapshot | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserDomSnapshotAdapter:
    """Normalizes runtime-provided DOMSnapshot/layout payloads into Sentinel records."""

    def capture(
        self,
        *,
        mission_id: str,
        url: str,
        raw_snapshot: dict[str, Any],
        event_bus: EventBus | None = None,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserDomSnapshotCaptureResult:
        if event_bus is not None and event_bus.mission_id != mission_id:
            raise ValueError("DOMSnapshot event bus mission_id must match mission_id.")
        try:
            nodes = [_normalize_dom_node(node, index) for index, node in enumerate(raw_snapshot.get("nodes", []))]
        except Exception as exc:
            return BrowserDomSnapshotCaptureResult(
                accepted=False,
                reason="dom_snapshot_normalization_failed",
                errors=[f"{type(exc).__name__}:{str(exc)[:300]}"],
            )
        if not nodes:
            return BrowserDomSnapshotCaptureResult(
                accepted=False,
                reason="dom_snapshot_empty",
                errors=["nodes_empty"],
            )
        payload = {
            "mission_id": mission_id,
            "url": url,
            "nodes": [node.model_dump(mode="json") for node in nodes],
            "node_count": len(nodes),
            "layout_count": sum(1 for node in nodes if node.bbox is not None),
        }
        snapshot = BrowserDomSnapshot(
            **payload,
            snapshot_sha256=hash_dom_snapshot_payload(payload),
            trace_refs=list(trace_refs or []),
        )
        if event_bus is not None:
            event = event_bus.append(
                AgentEventType.BROWSER_DOM_SNAPSHOT_CAPTURED,
                "DOMSnapshot and layout model captured as Browser V2.5 perception proof.",
                phase_before=phase,
                phase_after=phase,
                payload={
                    "snapshot_id": snapshot.id,
                    "snapshot_sha256": snapshot.snapshot_sha256,
                    "snapshot": snapshot.model_dump(mode="json"),
                    "url": url,
                    "node_count": snapshot.node_count,
                    "layout_count": snapshot.layout_count,
                    "stateless_public": True,
                    "cookies_enabled": False,
                    "storage_enabled": False,
                    "js_enabled": False,
                    "downloads_enabled": False,
                },
                trace_refs=list(trace_refs or []),
            )
            snapshot = snapshot.model_copy(update={"trace_refs": [*list(trace_refs or []), event.id]})
            return BrowserDomSnapshotCaptureResult(
                accepted=True,
                reason="dom_snapshot_captured",
                snapshot=snapshot,
                trace_event_id=event.id,
            )
        return BrowserDomSnapshotCaptureResult(accepted=True, reason="dom_snapshot_captured", snapshot=snapshot)


def hash_dom_snapshot_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_dom_snapshot_hash(snapshot: dict[str, Any], expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    payload = {
        "mission_id": snapshot.get("mission_id"),
        "url": snapshot.get("url"),
        "nodes": snapshot.get("nodes", []),
        "node_count": snapshot.get("node_count"),
        "layout_count": snapshot.get("layout_count"),
    }
    return hash_dom_snapshot_payload(payload) == expected_hash


def _normalize_dom_node(raw: dict[str, Any], index: int) -> BrowserDomSnapshotNode:
    attrs = {str(key): str(value) for key, value in dict(raw.get("attrs") or {}).items()}
    bbox_raw = raw.get("bbox")
    bbox = BrowserBoundingBox(**bbox_raw) if isinstance(bbox_raw, dict) else None
    role = _optional(raw.get("role")) or _role_for_tag(str(raw.get("tag") or "").lower(), attrs)
    name = _optional(raw.get("name")) or attrs.get("aria-label") or attrs.get("title") or attrs.get("alt")
    tag = str(raw.get("tag") or "node").lower()
    return BrowserDomSnapshotNode(
        node_index=int(raw.get("node_index", index)),
        tag=tag,
        role=role,
        name=name,
        text=_optional(raw.get("text")),
        attrs=attrs,
        dom_path=str(raw.get("dom_path") or f"/document/{tag}[{index}]"),
        parent_index=raw.get("parent_index"),
        visible=bool(raw.get("visible", True)),
        interactable=bool(raw.get("interactable", role in {"button", "link", "textbox", "combobox"})),
        bbox=bbox,
        ref_id=_optional(raw.get("ref_id")),
    )


def _role_for_tag(tag: str, attrs: dict[str, str]) -> str | None:
    if attrs.get("role"):
        return attrs["role"].lower()
    if tag == "a" and attrs.get("href"):
        return "link"
    if tag == "button":
        return "button"
    if tag in {"input", "textarea"}:
        return "textbox"
    if tag == "select":
        return "combobox"
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return "heading"
    return None


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
