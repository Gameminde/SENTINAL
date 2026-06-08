from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash
from sentinel.operator.harness_models import (
    AmplificationSession,
    AnalysisKernelResult,
    ContentAddressedArtifact,
    HarnessReplayView,
    HarnessWorkerResult,
    HashAnchoredEditVerification,
    MinimizedToolResult,
)
from sentinel.operator.store import MissionRunStore


class HarnessReplayBuilder:
    def __init__(self, store: MissionRunStore) -> None:
        self._store = store

    def build(self, mission_id: str, session_id: str) -> HarnessReplayView:
        root = self._harness_root(mission_id)
        session = AmplificationSession.model_validate_json(
            (root / _HARNESS_DIR_ALIASES["sessions"] / f"{_short_component(session_id)}.json").read_text(encoding="utf-8")
        )
        tampered = not session.verify_hash() or not self._store.verify_timeline(mission_id)

        artifact_refs: list[str] = []
        edit_refs: list[str] = []
        kernel_result_refs: list[str] = []
        tool_result_refs: list[str] = []
        worker_result_refs: list[str] = []
        merge_decision_refs: list[str] = []
        receipt_refs: list[str] = []
        finalgate_refs: list[str] = []
        memory_refs: list[str] = []

        for artifact in _load_models(_session_dir(root, "artifacts", session_id), ContentAddressedArtifact):
            artifact_refs.append(artifact.artifact_ref)
            tampered = tampered or not artifact.verify_hash()
        for edit in _load_models(_session_dir(root, "edit_verifications", session_id), HashAnchoredEditVerification):
            edit_refs.append(edit.verification_id)
            tampered = tampered or not edit.verify_hash()
        for kernel_result in _load_models(_session_dir(root, "kernel_results", session_id), AnalysisKernelResult):
            kernel_result_refs.append(kernel_result.kernel_result_id)
            tampered = tampered or not kernel_result.verify_hash()
        for tool_result in _load_models(_session_dir(root, "tool_results", session_id), MinimizedToolResult):
            tool_result_refs.append(tool_result.tool_result_ref)
            receipt_refs.extend(tool_result.receipt_refs)
            finalgate_refs.extend(tool_result.finalgate_certificate_refs)
            memory_refs.extend(tool_result.memory_feedback_refs)
            tampered = tampered or not tool_result.verify_hash()
        for worker_result in _load_models(_session_dir(root, "worker_results", session_id), HarnessWorkerResult):
            worker_result_refs.append(worker_result.worker_result_ref)
            receipt_refs.extend(worker_result.receipt_refs)
            finalgate_refs.extend(worker_result.finalgate_certificate_refs)
            memory_refs.extend(worker_result.memory_feedback_refs)
            tampered = tampered or not worker_result.verify_hash()
        merge_root = _session_dir(root, "merges", session_id)
        for merge_path in sorted(merge_root.glob("*.json")) if merge_root.exists() else []:
            payload = json.loads(merge_path.read_text(encoding="utf-8"))
            merge_decision_refs.append(str(payload.get("merge_decision_id", merge_path.stem)))

        telemetry_refs = [
            event.event_hash
            for event in self._store.load_events(mission_id)
            if event.event_type.startswith("harness_")
        ]
        return HarnessReplayView(
            mission_id=mission_id,
            session_id=session_id,
            session=session,
            artifact_refs=_dedupe(artifact_refs),
            edit_refs=_dedupe(edit_refs),
            kernel_result_refs=_dedupe(kernel_result_refs),
            tool_result_refs=_dedupe(tool_result_refs),
            worker_result_refs=_dedupe(worker_result_refs),
            merge_decision_refs=_dedupe(merge_decision_refs),
            telemetry_refs=_dedupe(telemetry_refs),
            memory_feedback_refs=_dedupe(memory_refs),
            receipt_refs=_dedupe(receipt_refs),
            finalgate_certificate_refs=_dedupe(finalgate_refs),
            tampered=tampered,
            reexecuted_actions=False,
        )

    def _harness_root(self, mission_id: str) -> Path:
        return self._store.mission_dir(mission_id, create=True) / "harness"


def _load_models(path: Path, model: Any) -> list[Any]:
    if not path.exists():
        return []
    return [model.model_validate_json(item.read_text(encoding="utf-8")) for item in sorted(path.glob("*.json"))]


def _dedupe(values) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


_HARNESS_DIR_ALIASES = {
    "sessions": "s",
    "artifacts": "a",
    "edit_verifications": "ev",
    "kernel_results": "kr",
    "tool_results": "t",
    "worker_results": "wrs",
    "merges": "m",
}


def _session_dir(root: Path, subdir: str, session_id: str) -> Path:
    return root / _HARNESS_DIR_ALIASES[subdir] / _short_component(session_id)


def _short_component(value: str) -> str:
    return stable_hash(value)[:20]
