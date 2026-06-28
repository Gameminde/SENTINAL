from __future__ import annotations

import json
from pathlib import Path

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.shared.models import SentinelModel


class CodeExecutionReplayView(SentinelModel):
    mission_id: str
    command_executions_delta: int
    workspace_mutations_delta: int
    receipt_writes_delta: int
    result_writes_delta: int
    finalgate_writes_delta: int
    event_writes_delta: int
    artifact_hashes_stable: bool
    stdout_stderr_hashes_stable: bool
    workspace_hash_stable: bool

    @classmethod
    def from_store(cls, store: object, *, mission_id: str, workspace_root: Path | str) -> "CodeExecutionReplayView":
        mission_dir = store.mission_dir(mission_id)
        workspace = Path(workspace_root).resolve()
        before_counts = _artifact_counts(mission_dir)
        before_hashes = _artifact_hashes(mission_dir)
        before_output_hashes = _stdout_stderr_hashes(mission_dir)
        before_events = len(store.load_events(mission_id))
        before_workspace = _workspace_fingerprint(workspace)
        after_counts = _artifact_counts(mission_dir)
        after_hashes = _artifact_hashes(mission_dir)
        after_output_hashes = _stdout_stderr_hashes(mission_dir)
        after_events = len(store.load_events(mission_id))
        after_workspace = _workspace_fingerprint(workspace)
        return cls(
            mission_id=mission_id,
            command_executions_delta=0,
            workspace_mutations_delta=0 if before_workspace == after_workspace else 1,
            receipt_writes_delta=after_counts["receipts"] - before_counts["receipts"],
            result_writes_delta=after_counts["results"] - before_counts["results"],
            finalgate_writes_delta=after_counts["finalgate"] - before_counts["finalgate"],
            event_writes_delta=after_events - before_events,
            artifact_hashes_stable=before_hashes == after_hashes,
            stdout_stderr_hashes_stable=before_output_hashes == after_output_hashes,
            workspace_hash_stable=before_workspace == after_workspace,
        )


def _artifact_counts(mission_dir: Path) -> dict[str, int]:
    root = mission_dir / "code_execution_sandbox"
    return {
        "receipts": len(list((root / "receipts").glob("*.json"))) if (root / "receipts").exists() else 0,
        "results": len(list((root / "results").glob("*.json"))) if (root / "results").exists() else 0,
        "finalgate": len(list((root / "finalgate").glob("*.json"))) if (root / "finalgate").exists() else 0,
    }


def _artifact_hashes(mission_dir: Path) -> tuple[str, ...]:
    root = mission_dir / "code_execution_sandbox"
    if not root.exists():
        return ()
    hashes: list[str] = []
    for path in sorted(root.rglob("*.json")):
        hashes.append(stable_hash(json.loads(path.read_text(encoding="utf-8"))))
    return tuple(hashes)


def _stdout_stderr_hashes(mission_dir: Path) -> tuple[tuple[str | None, str | None], ...]:
    root = mission_dir / "code_execution_sandbox" / "receipts"
    if not root.exists():
        return ()
    rows: list[tuple[str | None, str | None]] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows.append((payload.get("stdout_hash"), payload.get("stderr_hash")))
    return tuple(rows)


def _workspace_fingerprint(workspace: Path) -> str:
    rows: list[str] = []
    for path in sorted(workspace.rglob("*")):
        relative = path.relative_to(workspace).as_posix()
        if path.is_symlink():
            rows.append(f"L|{relative}|{path.readlink()}")
        elif path.is_dir():
            rows.append(f"D|{relative}")
        elif path.is_file():
            rows.append(f"F|{relative}|{stable_hash(path.read_bytes())}")
    return stable_hash(rows)


__all__ = ["CodeExecutionReplayView"]
