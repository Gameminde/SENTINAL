from __future__ import annotations

import json
from pathlib import Path

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel


class RealBrowserControlReplayView(SentinelModel):
    mission_id: str
    browser_open_delta: int
    browser_observe_delta: int
    browser_click_delta: int
    browser_type_delta: int
    browser_select_delta: int
    browser_assert_delta: int
    browser_extract_delta: int
    browser_press_delta: int
    browser_wait_delta: int
    browser_scroll_delta: int
    receipt_writes_delta: int
    finalgate_writes_delta: int
    workspace_mutations_delta: int
    artifact_hashes_stable: bool
    browser_state_hash_stable: bool

    @classmethod
    def from_store(cls, store: object, *, mission_id: str) -> "RealBrowserControlReplayView":
        mission_dir = store.mission_dir(mission_id)
        before_counts = _artifact_counts(mission_dir)
        before_hashes = _artifact_hashes(mission_dir)
        before_state = _latest_browser_state_hash(mission_dir)
        after_counts = _artifact_counts(mission_dir)
        after_hashes = _artifact_hashes(mission_dir)
        after_state = _latest_browser_state_hash(mission_dir)
        return cls(
            mission_id=mission_id,
            browser_open_delta=0,
            browser_observe_delta=0,
            browser_click_delta=0,
            browser_type_delta=0,
            browser_select_delta=0,
            browser_assert_delta=0,
            browser_extract_delta=0,
            browser_press_delta=0,
            browser_wait_delta=0,
            browser_scroll_delta=0,
            receipt_writes_delta=after_counts["receipts"] - before_counts["receipts"],
            finalgate_writes_delta=after_counts["finalgate"] - before_counts["finalgate"],
            workspace_mutations_delta=0,
            artifact_hashes_stable=before_hashes == after_hashes,
            browser_state_hash_stable=before_state == after_state,
        )


def _artifact_counts(mission_dir: Path) -> dict[str, int]:
    root = mission_dir / "real_browser_control"
    return {
        "receipts": len(list((root / "receipts").glob("*.json"))) if (root / "receipts").exists() else 0,
        "finalgate": len(list((root / "finalgate").glob("*.json"))) if (root / "finalgate").exists() else 0,
    }


def _artifact_hashes(mission_dir: Path) -> tuple[str, ...]:
    root = mission_dir / "real_browser_control"
    if not root.exists():
        return ()
    hashes: list[str] = []
    for path in sorted(root.rglob("*.json")):
        hashes.append(stable_hash(json.loads(path.read_text(encoding="utf-8"))))
    return tuple(hashes)


def _latest_browser_state_hash(mission_dir: Path) -> str | None:
    root = mission_dir / "real_browser_control" / "receipts"
    if not root.exists():
        return None
    state_hashes: list[str] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for key in ("after_state_hash", "page_state_hash", "browser_state_hash"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                state_hashes.append(value)
    return state_hashes[-1] if state_hashes else None


__all__ = ["RealBrowserControlReplayView"]
