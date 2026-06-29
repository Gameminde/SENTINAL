from __future__ import annotations

import json
from pathlib import Path

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel


class BrowserWorldModelReplayView(SentinelModel):
    mission_id: str
    world_model_writes_delta: int
    decision_frame_writes_delta: int
    artifact_hashes_stable: bool

    @classmethod
    def from_store(cls, store: object, *, mission_id: str) -> "BrowserWorldModelReplayView":
        mission_dir = store.mission_dir(mission_id)
        before_counts = _artifact_counts(mission_dir)
        before_hashes = _artifact_hashes(mission_dir)
        after_counts = _artifact_counts(mission_dir)
        after_hashes = _artifact_hashes(mission_dir)
        return cls(
            mission_id=mission_id,
            world_model_writes_delta=after_counts["world_models"] - before_counts["world_models"],
            decision_frame_writes_delta=after_counts["decision_frames"] - before_counts["decision_frames"],
            artifact_hashes_stable=before_hashes == after_hashes,
        )


def _artifact_counts(mission_dir: Path) -> dict[str, int]:
    root = mission_dir / "real_browser_control"
    return {
        "world_models": len(list((root / "world_models").glob("*.json"))) if (root / "world_models").exists() else 0,
        "decision_frames": len(list((root / "decision_frames").glob("*.json"))) if (root / "decision_frames").exists() else 0,
    }


def _artifact_hashes(mission_dir: Path) -> tuple[str, ...]:
    root = mission_dir / "real_browser_control"
    hashes: list[str] = []
    for collection in ("world_models", "decision_frames"):
        folder = root / collection
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            hashes.append(stable_hash(json.loads(path.read_text(encoding="utf-8"))))
    return tuple(hashes)


__all__ = ["BrowserWorldModelReplayView"]
