from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any

from pydantic import Field

from sentinel.organs.browser.ui_observation import BrowserBoundingBox
from sentinel.shared.events import AgentEventType, AgentPhase, EventBus
from sentinel.shared.models import SentinelModel, new_id


class BrowserVisualObservationKind(StrEnum):
    SCREENSHOT_CROP = "screenshot_crop"
    ZOOM_REGION = "zoom_region"
    OCR_STUB = "ocr_stub"


class BrowserScreenshotRegion(SentinelModel):
    bbox: BrowserBoundingBox
    source_screenshot_sha256: str
    source_width: int | None = Field(default=None, ge=0)
    source_height: int | None = Field(default=None, ge=0)
    ref_id: str | None = None
    reason: str = ""


class BrowserVisualObservation(SentinelModel):
    id: str = Field(default_factory=lambda: new_id("bvis"))
    mission_id: str
    url: str
    kind: BrowserVisualObservationKind
    region: BrowserScreenshotRegion
    page_sha256: str | None = None
    snapshot_sha256: str | None = None
    viewport: dict[str, Any] = Field(default_factory=dict)
    ui_observation_ref_ids: list[str] = Field(default_factory=list)
    zoom_factor: float = Field(default=1.0, ge=1.0, le=8.0)
    artifact_id: str | None = None
    artifact_sha256: str | None = None
    bytes_observed: int = Field(default=0, ge=0)
    max_bytes: int = Field(default=1_000_000, ge=1)
    ocr_text: str | None = None
    observation_sha256: str
    trace_refs: list[str] = Field(default_factory=list)


class BrowserVisualObservationBuilder:
    """Creates bounded visual observation metadata without adding heavyweight OCR/runtime powers."""

    def create(
        self,
        *,
        mission_id: str,
        url: str,
        region: BrowserScreenshotRegion,
        kind: BrowserVisualObservationKind = BrowserVisualObservationKind.SCREENSHOT_CROP,
        event_bus: EventBus | None = None,
        crop_bytes: bytes | None = None,
        artifact_id: str | None = None,
        artifact_sha256: str | None = None,
        page_sha256: str | None = None,
        snapshot_sha256: str | None = None,
        viewport: dict[str, Any] | None = None,
        ui_observation_ref_ids: list[str] | None = None,
        zoom_factor: float = 1.0,
        max_bytes: int = 1_000_000,
        trace_refs: list[str] | None = None,
        phase: AgentPhase = AgentPhase.EXECUTING,
    ) -> BrowserVisualObservation:
        if event_bus is not None and event_bus.mission_id != mission_id:
            raise ValueError("Visual observation event bus mission_id must match mission_id.")
        observed_len = len(crop_bytes or b"")
        if observed_len > max_bytes:
            raise ValueError("visual_observation_bytes_exceed_max")
        if crop_bytes is not None and artifact_sha256 is None:
            artifact_sha256 = hashlib.sha256(crop_bytes).hexdigest()
        zoom_value = float(zoom_factor)
        payload = {
            "mission_id": mission_id,
            "url": url,
            "kind": kind.value,
            "region": region.model_dump(mode="json"),
            "page_sha256": page_sha256,
            "snapshot_sha256": snapshot_sha256,
            "viewport": dict(viewport or {}),
            "ui_observation_ref_ids": list(ui_observation_ref_ids or []),
            "zoom_factor": zoom_value,
            "artifact_id": artifact_id,
            "artifact_sha256": artifact_sha256,
            "bytes_observed": observed_len,
            "max_bytes": max_bytes,
            "ocr_text": None,
        }
        observation = BrowserVisualObservation(
            **payload,
            observation_sha256=hash_visual_observation_payload(payload),
            trace_refs=list(trace_refs or []),
        )
        if event_bus is not None:
            event = event_bus.append(
                AgentEventType.BROWSER_VISUAL_OBSERVATION_CAPTURED,
                "Browser V2.5 visual crop or zoom observation metadata captured.",
                phase_before=phase,
                phase_after=phase,
                payload={
                    "visual_observation_id": observation.id,
                    "observation_sha256": observation.observation_sha256,
                    "observation": observation.model_dump(mode="json"),
                    "kind": observation.kind.value,
                    "url": url,
                    "source_screenshot_sha256": region.source_screenshot_sha256,
                    "page_sha256": page_sha256,
                    "snapshot_sha256": snapshot_sha256,
                    "viewport": dict(viewport or {}),
                    "ui_observation_ref_ids": list(ui_observation_ref_ids or []),
                    "artifact_id": artifact_id,
                    "artifact_sha256": artifact_sha256,
                    "bytes_observed": observed_len,
                    "max_bytes": max_bytes,
                    "zoom_factor": zoom_value,
                    "ocr_dependency": "stub",
                    "stateless_public": True,
                    "cookies_enabled": False,
                    "storage_enabled": False,
                    "js_enabled": False,
                    "downloads_enabled": False,
                },
                trace_refs=list(trace_refs or []),
            )
            observation = observation.model_copy(update={"trace_refs": [*list(trace_refs or []), event.id]})
        return observation


def hash_visual_observation_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_visual_observation_hash(observation: dict[str, Any], expected_hash: str | None) -> bool:
    if not expected_hash:
        return False
    payload = {
        "mission_id": observation.get("mission_id"),
        "url": observation.get("url"),
        "kind": observation.get("kind"),
        "region": observation.get("region"),
        "page_sha256": observation.get("page_sha256"),
        "snapshot_sha256": observation.get("snapshot_sha256"),
        "viewport": observation.get("viewport") or {},
        "ui_observation_ref_ids": observation.get("ui_observation_ref_ids") or [],
        "zoom_factor": observation.get("zoom_factor"),
        "artifact_id": observation.get("artifact_id"),
        "artifact_sha256": observation.get("artifact_sha256"),
        "bytes_observed": observation.get("bytes_observed"),
        "max_bytes": observation.get("max_bytes"),
        "ocr_text": observation.get("ocr_text"),
    }
    return hash_visual_observation_payload(payload) == expected_hash
