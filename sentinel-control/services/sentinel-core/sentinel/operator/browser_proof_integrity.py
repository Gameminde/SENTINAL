from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from sentinel.agent.model_execution.redaction import stable_hash


_LEDGER_SCHEMA_VERSION = "browser_completion_ledger_v1"
_GATE_SCHEMA_VERSION = "browser_proof_integrity_gate_v1"
_PROVENANCE_SCHEMA_VERSION = "runtime_provenance_v1"


def browser_completion_ledger_from_index(index: dict[str, Any]) -> dict[str, Any]:
    """Project the canonical completion truth into a compact ledger.

    The ledger is intentionally not a second evaluator. It is a stable,
    machine-readable projection of `completion_truth` so batch reports cannot
    silently drift away from the browser proof index.
    """

    truth = index.get("completion_truth") if isinstance(index.get("completion_truth"), dict) else {}
    truth_hash = stable_hash(truth)
    return {
        "schema_version": _LEDGER_SCHEMA_VERSION,
        "source": "browser_proof_index.completion_truth",
        "source_completion_truth_hash": truth_hash,
        "loop_closed": bool(truth.get("loop_closed")),
        "browser_body_reached": bool(truth.get("browser_body_reached")),
        "material_browser_action_succeeded": bool(truth.get("material_browser_action_succeeded")),
        "evidence_acquired": bool(truth.get("evidence_acquired")),
        "final_answer_present": bool(truth.get("final_answer_present")),
        "honest_blocker_present": bool(truth.get("honest_blocker_present")),
        "mission_objective_satisfied": bool(truth.get("mission_objective_satisfied")),
        "technical_completion": bool(truth.get("loop_closed") and truth.get("material_browser_action_succeeded")),
        "useful_answer_completion": bool(truth.get("useful_answer_completion")),
        "human_readable_public_evidence_count": _safe_int(truth.get("human_readable_public_evidence_count")),
        "supported_factual_claim_count": _safe_int(truth.get("supported_factual_claim_count")),
        "unsupported_factual_claim_count": _safe_int(truth.get("unsupported_factual_claim_count")),
        "material_browser_receipt_count": _safe_int(truth.get("material_browser_receipt_count")),
        "browser_receipt_readable_count": _safe_int(truth.get("browser_receipt_readable_count")),
        "browser_receipt_missing_count": _safe_int(truth.get("browser_receipt_missing_count")),
        "data_not_authority": True,
        "can_execute": False,
    }


def build_runtime_provenance(
    *,
    repo_root: Path | str | None = None,
    corpus_manifest_hash: str = "",
    runtime_corpus_hash: str = "",
    git_runner: Callable[[Path, list[str]], str] | None = None,
) -> dict[str, Any]:
    root = _find_git_root(Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve())
    run_git = git_runner or _run_git
    head = _safe_git(run_git, root, ["rev-parse", "HEAD"]) if root else ""
    tree_hash = _safe_git(run_git, root, ["rev-parse", "HEAD^{tree}"]) if root else ""
    status = _safe_git(run_git, root, ["status", "--porcelain=v1", "--untracked-files=all"]) if root else ""
    status_lines = [line for line in status.splitlines() if line.strip()]
    tracked_dirty_count = sum(1 for line in status_lines if not line.startswith("??"))
    untracked_count = sum(1 for line in status_lines if line.startswith("??"))
    provenance = {
        "schema_version": _PROVENANCE_SCHEMA_VERSION,
        "git_head": head or "unknown",
        "runtime_source_tree_hash": tree_hash or "unknown",
        "git_dirty": bool(status_lines),
        "tracked_dirty_file_count": tracked_dirty_count,
        "untracked_file_count": untracked_count,
        "dirty_state_hash": stable_hash(status),
        "corpus_manifest_hash": str(corpus_manifest_hash or ""),
        "runtime_corpus_hash": str(runtime_corpus_hash or ""),
        "raw_paths_persisted": False,
        "data_not_authority": True,
        "can_execute": False,
    }
    provenance["runtime_provenance_hash"] = stable_hash(provenance)
    return provenance


def evaluate_browser_proof_integrity_gate(
    *,
    proof_index: dict[str, Any],
    ledger: dict[str, Any] | None = None,
    evaluator_result: dict[str, Any] | None = None,
    replay_payload: dict[str, Any] | None = None,
    runtime_provenance: dict[str, Any] | None = None,
    safe_bundle_created: bool,
    cleanup_success: bool,
) -> dict[str, Any]:
    canonical_ledger = browser_completion_ledger_from_index(proof_index)
    candidate_ledger = ledger if isinstance(ledger, dict) else canonical_ledger
    evaluator = evaluator_result if isinstance(evaluator_result, dict) else {}
    replay = replay_payload if isinstance(replay_payload, dict) else {}
    provenance = runtime_provenance if isinstance(runtime_provenance, dict) else {}
    failures: list[str] = []

    if not proof_index:
        failures.append("proof_index_missing")
    if not safe_bundle_created:
        failures.append("safe_bundle_missing")
    if not cleanup_success:
        failures.append("cleanup_not_proven")
    if canonical_ledger["browser_receipt_missing_count"] != 0:
        failures.append("material_browser_receipt_missing")

    for field in (
        "technical_completion",
        "useful_answer_completion",
        "mission_objective_satisfied",
        "final_answer_present",
        "evidence_acquired",
        "supported_factual_claim_count",
        "unsupported_factual_claim_count",
        "browser_receipt_missing_count",
    ):
        if field in candidate_ledger and candidate_ledger.get(field) != canonical_ledger.get(field):
            failures.append(f"ledger_mismatch:{field}")

    failures.extend(_evaluator_contradictions(canonical_ledger, evaluator))
    if not _replay_reconstruction_no_react(replay):
        failures.append("replay_reconstruction_not_proven")
    if not _runtime_provenance_valid(provenance):
        failures.append("runtime_provenance_missing_or_unsealed")

    return {
        "schema_version": _GATE_SCHEMA_VERSION,
        "passed": not failures,
        "failure_reasons": sorted(dict.fromkeys(failures)),
        "canonical_completion_ledger": canonical_ledger,
        "ledger_hash": stable_hash(candidate_ledger),
        "evaluator_hash": stable_hash(evaluator),
        "replay_hash": stable_hash(replay),
        "runtime_provenance_hash": str(provenance.get("runtime_provenance_hash") or ""),
        "data_not_authority": True,
        "can_execute": False,
    }


def _evaluator_contradictions(ledger: dict[str, Any], evaluator: dict[str, Any]) -> list[str]:
    if not evaluator:
        return []
    failures: list[str] = []
    if evaluator.get("evaluator_called") is not True:
        failures.append("evaluator_not_called")
        return failures
    if "answer_present" in evaluator and bool(evaluator.get("answer_present")) != bool(ledger.get("final_answer_present")):
        failures.append("evaluator_mismatch:answer_present")
    if "evidence_present" in evaluator and bool(evaluator.get("evidence_present")) != bool(ledger.get("evidence_acquired")):
        failures.append("evaluator_mismatch:evidence_present")
    evaluator_unsupported = _safe_int(evaluator.get("unsupported_claim_count"))
    if evaluator_unsupported > _safe_int(ledger.get("unsupported_factual_claim_count")):
        failures.append("evaluator_mismatch:unsupported_claim_count")
    verdict = str(evaluator.get("evaluator_verdict") or "").upper()
    if "FAIL" in verdict and bool(ledger.get("useful_answer_completion")):
        failures.append("evaluator_mismatch:useful_answer_completion")
    answer_useful = evaluator.get("answer_useful_complete")
    if answer_useful is not None and bool(answer_useful) != bool(ledger.get("useful_answer_completion")):
        failures.append("evaluator_mismatch:answer_useful_complete")
    return failures


def _replay_reconstruction_no_react(payload: dict[str, Any]) -> bool:
    return bool(
        payload
        and payload.get("replay_mode") == "artifact_history_reconstruction"
        and payload.get("history_reconstructed") is True
        and payload.get("effect_reexecution_attempted") is False
        and payload.get("reexecuted_actions") is False
        and _safe_int(payload.get("model_calls_delta")) == 0
        and _safe_int(payload.get("receipt_writes_delta")) == 0
        and _safe_int(payload.get("finalgate_writes_delta")) == 0
        and _safe_int(payload.get("browser_proof_index_writes_delta")) == 0
        and payload.get("browser_proof_index_hashes_stable") is True
    )


def _runtime_provenance_valid(payload: dict[str, Any]) -> bool:
    return bool(
        payload
        and str(payload.get("git_head") or "")
        and str(payload.get("runtime_source_tree_hash") or "")
        and str(payload.get("dirty_state_hash") or "")
        and str(payload.get("runtime_provenance_hash") or "")
    )


def _find_git_root(start: Path) -> Path | None:
    cursor = start if start.is_dir() else start.parent
    for item in (cursor, *cursor.parents):
        if (item / ".git").exists():
            return item
    return None


def _safe_git(run_git: Callable[[Path, list[str]], str], root: Path, args: list[str]) -> str:
    try:
        return run_git(root, args).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(root),
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return completed.stdout


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


__all__ = [
    "browser_completion_ledger_from_index",
    "build_runtime_provenance",
    "evaluate_browser_proof_integrity_gate",
]
