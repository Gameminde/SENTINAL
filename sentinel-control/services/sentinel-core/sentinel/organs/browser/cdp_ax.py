from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import Field

from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserCdpAxNode(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bax"))
    node_id: str
    backend_node_id: str | None = None
    role: str | None = None
    name: str | None = None
    value: str | None = None
    description: str | None = None
    states: list[str] = Field(default_factory=list)
    child_ids: list[str] = Field(default_factory=list)
    ignored: bool = False
    ref_id: str | None = None


class BrowserCdpAxTree(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("baxtree"))
    mission_id: str
    url: str
    nodes: list[BrowserCdpAxNode] = Field(default_factory=list)
    root_id: str | None = None
    node_count: int = Field(default=0, ge=0)
    backend_node_count: int = Field(default=0, ge=0)
    tree_sha256: str
    page_sha256: str | None = None
    trace_refs: list[str] = Field(default_factory=list)


class BrowserCdpAxCaptureResult(SentinelModel):
    accepted: bool
    reason: str
    tree: BrowserCdpAxTree | None = None
    trace_event_id: str | None = None
    errors: list[str] = Field(default_factory=list)


class BrowserCdpAccessibilityAdapter:
    """Normalizes runtime-provided CDP AX tree payloads into proof-bound Sentinel records."""

    def capture(
        self,
        *,
        mission_id: str,
        url: str,
        raw_tree: dict[str, Any],
        event_bus: EventBus | None = None,
        page_sha256: str | None = None,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserCdpAxCaptureResult:
        if event_bus is not None and event_bus.mission_id != mission_id:
            raise ValueError("CDP AX event bus mission_id must match mission_id.")
        try:
            nodes = [_normalize_ax_node(node, index) for index, node in enumerate(raw_tree.get("nodes", []))]
        except Exception as exc:
            return BrowserCdpAxCaptureResult(
                accepted=False,
                reason="cdp_ax_tree_normalization_failed",
                errors=[f"{type(exc).__name__}:{str(exc)[:300]}"],
            )
        if not nodes:
            return BrowserCdpAxCaptureResult(
                accepted=False,
                reason="cdp_ax_tree_empty",
                errors=["nodes_empty"],
            )

        payload = {
            "mission_id": mission_id,
            "url": url,
            "nodes": [node.model_dump(mode="json") for node in nodes],
            "root_id": str(raw_tree.get("root_id") or nodes[0].node_id),
            "node_count": len(nodes),
            "backend_node_count": sum(1 for node in nodes if node.backend_node_id),
            "page_sha256": page_sha256,
        }
        tree = BrowserCdpAxTree(**payload, tree_sha256=hash_cdp_ax_tree_payload(payload), trace_refs=list(trace_refs or []))
        if event_bus is not None:
            event = event_bus.append(
                AgentEventType.BROWSER_CDP_AX_TREE_CAPTURED,
                "CDP-native accessibility tree captured as Browser V2.5 perception proof.",
                phase_before=phase,
                phase_after=phase,
                payload={
                    "tree_id": tree.id,
                    "tree_sha256": tree.tree_sha256,
                    "tree": tree.model_dump(mode="json"),
                    "url": url,
                    "node_count": tree.node_count,
                    "backend_node_count": tree.backend_node_count,
                    "root_id": tree.root_id,
                    "stateless_public": True,
                    "cookies_enabled": False,
                    "storage_enabled": False,
                    "js_enabled": False,
                    "downloads_enabled": False,
                },
                trace_refs=list(trace_refs or []),
            )
            tree = tree.model_copy(update={"trace_refs": [*list(trace_refs or []), event.id]})
            return BrowserCdpAxCaptureResult(
                accepted=True,
                reason="cdp_ax_tree_captured",
                tree=tree,
                trace_event_id=event.id,
            )
        return BrowserCdpAxCaptureResult(accepted=True, reason="cdp_ax_tree_captured", tree=tree)


def hash_cdp_ax_tree_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_cdp_ax_tree_hash(tree: dict[str, Any], expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    payload = {
        "mission_id": tree.get("mission_id"),
        "url": tree.get("url"),
        "nodes": tree.get("nodes", []),
        "root_id": tree.get("root_id"),
        "node_count": tree.get("node_count"),
        "backend_node_count": tree.get("backend_node_count"),
        "page_sha256": tree.get("page_sha256"),
    }
    return hash_cdp_ax_tree_payload(payload) == expected_hash


def _normalize_ax_node(raw: dict[str, Any], index: int) -> BrowserCdpAxNode:
    node_id = _ax_value(raw.get("nodeId") or raw.get("node_id") or raw.get("id") or f"node_{index + 1}")
    backend_node_id = _ax_optional(raw.get("backendDOMNodeId") or raw.get("backend_node_id"))
    role = _ax_optional(raw.get("role"))
    name = _ax_optional(raw.get("name"))
    value = _ax_optional(raw.get("value"))
    description = _ax_optional(raw.get("description"))
    child_ids_raw = raw.get("childIds") or raw.get("child_ids") or []
    states_raw = raw.get("states") or raw.get("properties") or []
    return BrowserCdpAxNode(
        node_id=node_id,
        backend_node_id=backend_node_id,
        role=role,
        name=name,
        value=value,
        description=description,
        states=sorted({_ax_value(item) for item in states_raw if _ax_value(item)}),
        child_ids=[_ax_value(item) for item in child_ids_raw if _ax_value(item)],
        ignored=bool(raw.get("ignored", False)),
        ref_id=f"ax_{backend_node_id or node_id}",
    )


def _ax_value(value: Any) -> str:
    if isinstance(value, dict):
        if "value" in value:
            return _ax_value(value["value"])
        if "name" in value:
            return _ax_value(value["name"])
    if value is None:
        return ""
    return str(value).strip()


def _ax_optional(value: Any) -> str | None:
    text = _ax_value(value)
    return text or None
