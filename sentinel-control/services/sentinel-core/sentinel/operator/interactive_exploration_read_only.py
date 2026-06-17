"""Interactive read-only repository exploration with observable decision journal.

This module extends the batch self-exploration harness with an interactive loop
where the model independently selects read-only actions against a frozen
repository snapshot. Each turn produces a structured decision journal for
full trajectory monitoring.

Classification: AUTONOMOUS_REPOSITORY_EXPLORATION
Sentinel binding: EXPERIMENTAL_HARNESS_WITH_PARTIAL_SENTINEL_BINDING
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import Field

from sentinel.agent.model_execution.credentials import ProviderCredentialHandle
from sentinel.agent.model_execution.models import RealModelRequest
from sentinel.agent.model_execution.policy import ModelTimeoutPolicy
from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.operator.real_model_certification import (
    CERT_BASE_URL_ENV,
    CERT_CREDENTIAL_ENV,
    CERT_PROVIDER_ID,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ID,
)
from sentinel.operator.self_exploration_read_only import (
    OpenAICompatibleSelfExplorationModelClient,
    ReadOnlyOperation,
    ReadOnlyPolicyViolation,
    ReadOnlyRepositorySnapshot,
    SelfExplorationModelCall,
    SelfExplorationPolicy,
    _backend_profile,
    _bounded_excerpt,
    _safe_read_text,
    _snapshot_identity,
)
from sentinel.shared.models import SentinelModel, new_id
from sentinel.shared.safety_scanner import OrganSafetyScanCategory, scan_forbidden_payload_categorized


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INTERACTIVE_EXPERIMENT_VERSION = "REAL_MODEL_SENTINEL_INTERACTIVE_EXPLORATION_READ_ONLY_V1"

# Adaptive budget tiers
EXPLORATION_BASE_TURNS = 12
EXPLORATION_EXTENSION_TURNS = 8
EXPLORATION_RESERVE_TURNS = 4
MAX_EXPLORATION_TURNS = EXPLORATION_BASE_TURNS + EXPLORATION_EXTENSION_TURNS + EXPLORATION_RESERVE_TURNS

# Per-lane token limits
SMOKE_OUTPUT_TOKENS = 500
SMOKE_INPUT_TOKENS = 2_000
ACTION_SMOKE_OUTPUT_TOKENS = 1_500
ACTION_SMOKE_INPUT_TOKENS = 3_000
EXPLORATION_OUTPUT_TOKENS = 1_500
EXPLORATION_MAX_INPUT_TOKENS = 10_000
REPORT_A_OUTPUT_TOKENS = 10_000
REPORT_A_MAX_INPUT_TOKENS = 20_000
REPORT_B_OUTPUT_TOKENS = 8_000
REPORT_B_MAX_INPUT_TOKENS = 25_000

# Aggregate limits
MAX_CUMULATIVE_INPUT_TOKENS = 350_000
MAX_CUMULATIVE_OUTPUT_TOKENS = 60_000
MAX_TOTAL_MODEL_CALLS = 28
MAX_TOTAL_FILES_READ = 120
MAX_TOTAL_BYTES_READ = 500_000
MAX_OBSERVATION_BYTES = 6_144
MAX_EVIDENCE_CATALOG_ENTRIES = 60
MAX_HISTORY_CHARS = 12_000
MAX_EXPERIMENT_DURATION_SECONDS = 900.0
MAX_DUPLICATE_FILE_READS = 3
MAX_SEARCH_RESULTS = 30
MAX_LIST_ENTRIES = 120

# Nonproductive turn threshold for adaptive budget
NONPRODUCTIVE_TURN_LIMIT = 3

DEPTH_GATE_REQUIRED_CATEGORIES = frozenset({
    "entrypoint",
    "mission_lifecycle",
    "authority_path",
    "execution_runtime",
    "telemetry_path",
    "proof_path",
    "replay_persistence_path",
    "capability_path",
})

DEPTH_GATE_MARKERS: dict[str, tuple[str, ...]] = {
    "entrypoint": ("__main__", "cli", "entrypoint", "main("),
    "mission_lifecycle": ("missionkernel", "mission lifecycle", "mission state", "kernel.py"),
    "authority_path": ("authority", "missionauthorityenvelope", "gate", "permission"),
    "execution_runtime": ("agentruntime", "powerruntime", "runtime", "execute"),
    "telemetry_path": ("telemetry", "certified mode", "eventbus"),
    "proof_path": ("receipt", "finalgate", "final gate", "certificate"),
    "replay_persistence_path": ("replay", "store", "durable", "checkpoint", "missionrunstore"),
    "capability_path": ("organ", "browser", "capability", "channel", "desktop"),
}


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExplorationTool(StrEnum):
    LIST_DIRECTORY = "list_directory"
    SEARCH_TEXT = "search_text"
    SEARCH_SYMBOL = "search_symbol"
    READ_FILE_SEGMENT = "read_file_segment"
    FIND_REFERENCES = "find_references"
    INSPECT_TEST = "inspect_test"
    INSPECT_GIT_METADATA = "inspect_git_metadata"
    FINISH_EXPLORATION = "finish_exploration"


VALID_TOOLS = frozenset(ExplorationTool)
CRITICAL_FIELDS = frozenset({"action", "target", "parameters"})
ALLOWED_DECISION_FIELDS = frozenset({
    "action",
    "target",
    "parameters",
    "decision_summary",
    "evidence_refs",
    "current_state",
    "facts_confirmed",
    "active_hypotheses",
    "hypotheses_rejected",
    "alternatives_considered",
    "expected_result",
    "confidence",
    "uncertainties",
    "remaining_questions",
})


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ExplorationDecisionJournal(SentinelModel):
    """Observable decision trace — NOT raw chain-of-thought."""
    decision_summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    current_state: str = ""
    facts_confirmed: list[str] = Field(default_factory=list)
    active_hypotheses: list[str] = Field(default_factory=list)
    hypotheses_rejected: list[str] = Field(default_factory=list)
    alternatives_considered: list[str] = Field(default_factory=list)
    expected_result: str = ""
    confidence: float = 0.5
    uncertainties: list[str] = Field(default_factory=list)
    remaining_questions: list[str] = Field(default_factory=list)

    @property
    def journal_quality(self) -> str:
        filled = sum([
            bool(self.decision_summary),
            bool(self.current_state),
            len(self.facts_confirmed) > 0,
            len(self.active_hypotheses) > 0,
            bool(self.expected_result),
        ])
        if filled >= 4:
            return "COMPLETE"
        if filled >= 2:
            return "PARTIAL"
        return "MINIMAL"


class EvidenceCatalogEntry(SentinelModel):
    ref: str
    turn: int
    action: str
    target: str
    summary: str
    bytes_size: int = 0
    match_count: int | None = None
    content_hash: str | None = None
    novelty_status: str = "NOVEL"


class ExplorationBudgetStatus(SentinelModel):
    turns_used: int = 0
    turns_remaining: int = MAX_EXPLORATION_TURNS
    files_read: int = 0
    files_remaining: int = MAX_TOTAL_FILES_READ
    bytes_read: int = 0
    bytes_remaining: int = MAX_TOTAL_BYTES_READ
    evidence_catalog_size: int = 0
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    output_tokens_remaining: int = MAX_CUMULATIVE_OUTPUT_TOKENS
    elapsed_seconds: float = 0.0
    time_remaining_seconds: float = MAX_EXPERIMENT_DURATION_SECONDS
    model_calls_used: int = 0
    model_calls_remaining: int = MAX_TOTAL_MODEL_CALLS


class ExplorationTurnRecord(SentinelModel):
    turn: int
    timestamp_utc: str
    phase: str = "exploration"
    action: str
    target: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    decision_journal: dict[str, Any] = Field(default_factory=dict)
    journal_quality: str = "MINIMAL"
    observation_summary: str = ""
    observation_bytes: int = 0
    observation_matches: int | None = None
    evidence_ref: str | None = None
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    cumulative_files_read: int = 0
    cumulative_bytes_read: int = 0
    parse_success: bool = False
    validation_success: bool = False
    action_blocked_reason: str | None = None
    reasoning_metadata: dict[str, Any] = Field(default_factory=dict)
    productive: bool = False


class ExplorationState(SentinelModel):
    """Accumulated exploration state managed by the harness."""
    facts_confirmed: list[str] = Field(default_factory=list)
    active_hypotheses: list[str] = Field(default_factory=list)
    hypotheses_rejected: list[str] = Field(default_factory=list)
    evidence_catalog: list[EvidenceCatalogEntry] = Field(default_factory=list)
    files_read_set: set[str] = Field(default_factory=set)
    file_segment_reads: dict[str, int] = Field(default_factory=dict)
    search_queries: list[str] = Field(default_factory=list)
    evidence_content_hashes: set[str] = Field(default_factory=set)
    evidence_target_hashes: set[str] = Field(default_factory=set)
    nonproductive_streak: int = 0

    def next_evidence_ref(self) -> str:
        return f"E{len(self.evidence_catalog) + 1}"

    def add_evidence(self, *, turn: int, action: str, target: str,
                     summary: str, content: str, match_count: int | None = None) -> str:
        ref = self.next_evidence_ref()
        content_hash = text_hash(content)
        target_hash = text_hash(f"{action}:{target}:{content_hash}")
        if content_hash in self.evidence_content_hashes:
            novelty_status = "DUPLICATE_EVIDENCE"
        elif target_hash in self.evidence_target_hashes:
            novelty_status = "DUPLICATE_TARGET"
        else:
            novelty_status = "NOVEL"
            self.evidence_content_hashes.add(content_hash)
            self.evidence_target_hashes.add(target_hash)
        entry = EvidenceCatalogEntry(
            ref=ref, turn=turn, action=action, target=target,
            summary=summary[:300], bytes_size=len(content.encode("utf-8")),
            match_count=match_count, content_hash=content_hash,
            novelty_status=novelty_status,
        )
        if len(self.evidence_catalog) >= MAX_EVIDENCE_CATALOG_ENTRIES:
            self.evidence_catalog = self.evidence_catalog[1:]
        self.evidence_catalog.append(entry)
        return ref

    def coverage_categories(self) -> set[str]:
        categories: set[str] = set()
        searchable_parts: list[str] = []
        for entry in self.evidence_catalog:
            searchable_parts.extend([entry.action, entry.target, entry.summary])
        corpus = "\n".join(searchable_parts).lower()
        for category, markers in DEPTH_GATE_MARKERS.items():
            if any(marker.lower() in corpus for marker in markers):
                categories.add(category)
        return categories

    def finish_depth_gate(self) -> tuple[bool, list[str]]:
        covered = self.coverage_categories()
        missing = sorted(DEPTH_GATE_REQUIRED_CATEGORIES - covered)
        return not missing, missing

    def update_from_journal(self, journal: ExplorationDecisionJournal) -> bool:
        """Update state from the model's decision journal. Returns True if productive."""
        changed = False
        for fact in journal.facts_confirmed:
            trimmed = fact.strip()[:200]
            if trimmed and trimmed not in self.facts_confirmed:
                self.facts_confirmed.append(trimmed)
                changed = True
        new_hyps = []
        for hyp in journal.active_hypotheses:
            trimmed = hyp.strip()[:300]
            if trimmed:
                new_hyps.append(trimmed)
        if new_hyps != self.active_hypotheses:
            changed = True
        self.active_hypotheses = new_hyps
        for hyp in journal.hypotheses_rejected:
            trimmed = hyp.strip()[:300]
            if trimmed and trimmed not in self.hypotheses_rejected:
                self.hypotheses_rejected.append(trimmed)
                changed = True
        if changed:
            self.nonproductive_streak = 0
        else:
            self.nonproductive_streak += 1
        return changed

    def check_duplicate_read(self, file_path: str, start: int, end: int) -> bool:
        key = f"{file_path}:{start}-{end}"
        count = self.file_segment_reads.get(key, 0)
        if count >= MAX_DUPLICATE_FILE_READS:
            return True
        self.file_segment_reads[key] = count + 1
        return False


class InteractiveExplorationReport(SentinelModel):
    status: str
    verdict: str
    experiment_version: str = INTERACTIVE_EXPERIMENT_VERSION
    policy_hash: str = ""
    snapshot_identity: dict[str, Any] = Field(default_factory=dict)
    provider_id: str = ""
    model_id: str = ""
    mission_id: str = ""
    run_id: str = ""
    output_root: str = ""
    smoke_a_passed: bool = False
    smoke_b_passed: bool = False
    total_exploration_turns: int = 0
    total_model_calls: int = 0
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    duration_seconds: float = 0.0
    exploration_state_final: dict[str, Any] = Field(default_factory=dict)
    evidence_catalog: list[dict[str, Any]] = Field(default_factory=list)
    trajectory_file: str = ""
    stage_a_report_hash: str | None = None
    stage_b_report_hash: str | None = None
    early_termination: bool = False
    early_termination_reason: str | None = None
    findings_count: int = 0
    sentinel_binding: dict[str, str] = Field(default_factory=lambda: {
        "SelfExplorationPolicy": "DIRECT",
        "ReadOnlyRepositorySnapshot": "DIRECT",
        "OpenAICompatibleChatProvider": "DIRECT",
        "ProviderCredentialHandle": "DIRECT",
        "ReasoningRedaction": "DIRECT",
        "SafetyScanner": "DIRECT",
        "MissionKernel": "PARTIAL_ID_ONLY",
        "AuthorityEnvelope": "MINIMAL_READ_ONLY_POLICY",
        "Telemetry": "EXTERNAL_JSONL",
        "Receipts": "BYPASSED",
        "FinalGate": "BYPASSED",
        "OrganDispatch": "BYPASSED",
        "ContextCompiler": "PARTIAL_EVIDENCE_CATALOG",
        "MemoryBridge": "BYPASSED",
    })


def interactive_safe_policy(policy: SelfExplorationPolicy) -> dict[str, Any]:
    payload = policy.safe_policy()
    payload["experiment_version"] = policy.experiment_version
    payload["interactive_experiment_version"] = INTERACTIVE_EXPERIMENT_VERSION
    payload["interactive_budgets"] = {
        "max_exploration_turns": MAX_EXPLORATION_TURNS,
        "exploration_base_turns": EXPLORATION_BASE_TURNS,
        "exploration_extension_turns": EXPLORATION_EXTENSION_TURNS,
        "exploration_reserve_turns": EXPLORATION_RESERVE_TURNS,
        "smoke_output_tokens": SMOKE_OUTPUT_TOKENS,
        "smoke_input_tokens": SMOKE_INPUT_TOKENS,
        "action_smoke_output_tokens": ACTION_SMOKE_OUTPUT_TOKENS,
        "action_smoke_input_tokens": ACTION_SMOKE_INPUT_TOKENS,
        "exploration_output_tokens": EXPLORATION_OUTPUT_TOKENS,
        "exploration_max_input_tokens": EXPLORATION_MAX_INPUT_TOKENS,
        "report_a_output_tokens": REPORT_A_OUTPUT_TOKENS,
        "report_a_max_input_tokens": REPORT_A_MAX_INPUT_TOKENS,
        "report_b_output_tokens": REPORT_B_OUTPUT_TOKENS,
        "report_b_max_input_tokens": REPORT_B_MAX_INPUT_TOKENS,
        "max_cumulative_input_tokens": MAX_CUMULATIVE_INPUT_TOKENS,
        "max_cumulative_output_tokens": MAX_CUMULATIVE_OUTPUT_TOKENS,
        "max_total_model_calls": MAX_TOTAL_MODEL_CALLS,
        "max_total_files_read": MAX_TOTAL_FILES_READ,
        "max_total_bytes_read": MAX_TOTAL_BYTES_READ,
        "max_observation_bytes": MAX_OBSERVATION_BYTES,
        "max_evidence_catalog_entries": MAX_EVIDENCE_CATALOG_ENTRIES,
        "max_history_chars": MAX_HISTORY_CHARS,
        "max_experiment_duration_seconds": MAX_EXPERIMENT_DURATION_SECONDS,
        "max_duplicate_file_reads": MAX_DUPLICATE_FILE_READS,
        "max_search_results": MAX_SEARCH_RESULTS,
        "max_list_entries": MAX_LIST_ENTRIES,
        "nonproductive_turn_limit": NONPRODUCTIVE_TURN_LIMIT,
    }
    return payload


def interactive_policy_hash(policy: SelfExplorationPolicy) -> str:
    return stable_hash(interactive_safe_policy(policy))


# ---------------------------------------------------------------------------
# Full-text search index (snapshot-only)
# ---------------------------------------------------------------------------

class SnapshotSearchIndex:
    """In-memory full-text index over all accessible files in the frozen snapshot."""

    def __init__(self, snapshot: ReadOnlyRepositorySnapshot) -> None:
        self._index: dict[str, str] = {}
        self._symbols: dict[str, list[str]] = {}
        for item in snapshot.inventory:
            if not item.stage_a_accessible:
                continue
            try:
                text = snapshot.read_file(item.path, stage="A")
                if _unsafe_model_visible_text(text, path=f"$.snapshot.{item.path}"):
                    continue
                self._index[item.path] = text
            except (ReadOnlyPolicyViolation, OSError):
                continue
            for sym in item.symbol_refs:
                self._symbols.setdefault(sym, []).append(item.path)

    def search_text(self, query: str, *, scope: str = "") -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if not query.strip():
            return results
        for path, content in self._index.items():
            if scope and not path.startswith(scope):
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if query in line:
                    results.append({
                        "file": path, "line": i,
                        "content": line.strip()[:200],
                    })
                    if len(results) >= MAX_SEARCH_RESULTS:
                        return results
        return results

    def search_symbol(self, symbol: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if not symbol.strip():
            return results
        pattern = re.compile(r'\b' + re.escape(symbol) + r'\b')
        for path, content in self._index.items():
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    results.append({
                        "file": path, "line": i,
                        "content": line.strip()[:200],
                    })
                    if len(results) >= MAX_SEARCH_RESULTS:
                        return results
        return results

    def find_references(self, symbol: str, *, scope: str = "") -> list[dict[str, Any]]:
        return self.search_symbol(symbol) if not scope else [
            r for r in self.search_symbol(symbol) if r["file"].startswith(scope)
        ][:MAX_SEARCH_RESULTS]

    def list_directory(self, prefix: str) -> list[dict[str, Any]]:
        normalized = prefix.strip().rstrip("/")
        if normalized in (".", "", "/"):
            normalized = ""
        results: list[dict[str, Any]] = []
        seen_dirs: set[str] = set()
        for path in sorted(self._index.keys()):
            if normalized and not path.startswith(normalized + "/") and path != normalized:
                continue
            remainder = path[len(normalized):].lstrip("/") if normalized else path
            parts = remainder.split("/")
            if len(parts) == 1:
                results.append({"path": path, "type": "file"})
            else:
                dir_path = (normalized + "/" + parts[0]) if normalized else parts[0]
                if dir_path not in seen_dirs:
                    seen_dirs.add(dir_path)
                    results.append({"path": dir_path, "type": "directory"})
            if len(results) >= MAX_LIST_ENTRIES:
                break
        return results

    def read_file_segment(self, path: str, start_line: int, end_line: int) -> str | None:
        content = self._index.get(path)
        if content is None:
            return None
        lines = content.splitlines()
        start = max(0, start_line - 1)
        end = min(len(lines), end_line)
        if end - start > 200:
            end = start + 200
        return "\n".join(lines[start:end])

    def get_file_content(self, path: str) -> str | None:
        return self._index.get(path)

    @property
    def file_count(self) -> int:
        return len(self._index)

    @property
    def total_bytes(self) -> int:
        return sum(len(v.encode("utf-8")) for v in self._index.values())


# ---------------------------------------------------------------------------
# Tool execution (snapshot-only)
# ---------------------------------------------------------------------------

def execute_snapshot_tool(
    action: ExplorationTool,
    target: str,
    parameters: dict[str, Any],
    *,
    policy: SelfExplorationPolicy | None = None,
    search_index: SnapshotSearchIndex,
    snapshot: ReadOnlyRepositorySnapshot,
    state: ExplorationState,
    budget: ExplorationBudgetStatus,
) -> tuple[str, int, int | None]:
    """Execute a read-only tool against the frozen snapshot.

    Returns (observation_text, observation_bytes, match_count_or_none).
    Raises ReadOnlyPolicyViolation on forbidden operations.
    """
    _validate_policy_operation(policy, action, target)

    if action == ExplorationTool.FINISH_EXPLORATION:
        return "EXPLORATION_COMPLETE", 0, None

    if action == ExplorationTool.LIST_DIRECTORY:
        entries = search_index.list_directory(target)
        text = "\n".join(f"{'[DIR]' if e['type'] == 'directory' else '[FILE]'} {e['path']}" for e in entries)
        text = text[:MAX_OBSERVATION_BYTES]
        return text, len(text.encode("utf-8")), len(entries)

    if action == ExplorationTool.SEARCH_TEXT:
        scope = parameters.get("scope", "")
        results = search_index.search_text(target, scope=scope)
        state.search_queries.append(target)
        lines = [f"{r['file']}:{r['line']}: {r['content']}" for r in results]
        text = "\n".join(lines)[:MAX_OBSERVATION_BYTES]
        return text, len(text.encode("utf-8")), len(results)

    if action == ExplorationTool.SEARCH_SYMBOL:
        results = search_index.search_symbol(target)
        state.search_queries.append(f"symbol:{target}")
        lines = [f"{r['file']}:{r['line']}: {r['content']}" for r in results]
        text = "\n".join(lines)[:MAX_OBSERVATION_BYTES]
        return text, len(text.encode("utf-8")), len(results)

    if action == ExplorationTool.READ_FILE_SEGMENT:
        start = int(parameters.get("start_line", 1))
        end = int(parameters.get("end_line", 200))
        if state.check_duplicate_read(target, start, end):
            return f"DUPLICATE_READ_LIMIT: {target}:{start}-{end} already read {MAX_DUPLICATE_FILE_READS} times", 0, None
        content = search_index.read_file_segment(target, start, end)
        if content is None:
            return f"FILE_NOT_ACCESSIBLE: {target}", 0, None
        state.files_read_set.add(target)
        text = f"[{target} lines {start}-{end}]\n{content}"[:MAX_OBSERVATION_BYTES]
        return text, len(text.encode("utf-8")), None

    if action == ExplorationTool.INSPECT_TEST:
        content = search_index.read_file_segment(target, 1, 200)
        if content is None:
            return f"TEST_FILE_NOT_ACCESSIBLE: {target}", 0, None
        state.files_read_set.add(target)
        text = f"[TEST: {target}]\n{content}"[:MAX_OBSERVATION_BYTES]
        return text, len(text.encode("utf-8")), None

    if action == ExplorationTool.FIND_REFERENCES:
        scope = parameters.get("scope", "")
        results = search_index.find_references(target, scope=scope)
        state.search_queries.append(f"refs:{target}")
        lines = [f"{r['file']}:{r['line']}: {r['content']}" for r in results]
        text = "\n".join(lines)[:MAX_OBSERVATION_BYTES]
        return text, len(text.encode("utf-8")), len(results)

    if action == ExplorationTool.INSPECT_GIT_METADATA:
        meta = {
            "head": snapshot.head,
            "origin_main": snapshot.origin_main,
            "dirty_worktree_fingerprint": snapshot.dirty_worktree_fingerprint,
            "inventory_count": len(snapshot.inventory),
            "inventory_hash": snapshot.inventory_hash,
        }
        text = json.dumps(meta, indent=2)
        return text, len(text.encode("utf-8")), None

    raise ReadOnlyPolicyViolation(f"unknown_tool:{action}")


def _validate_policy_operation(
    policy: SelfExplorationPolicy | None,
    action: ExplorationTool,
    target: str,
) -> None:
    operation_kind_by_action = {
        ExplorationTool.LIST_DIRECTORY: "list_dir",
        ExplorationTool.SEARCH_TEXT: "search",
        ExplorationTool.SEARCH_SYMBOL: "symbol_scan",
        ExplorationTool.READ_FILE_SEGMENT: "read_file",
        ExplorationTool.FIND_REFERENCES: "symbol_scan",
        ExplorationTool.INSPECT_TEST: "read_file",
        ExplorationTool.INSPECT_GIT_METADATA: "git_metadata",
        ExplorationTool.FINISH_EXPLORATION: "finish_exploration",
    }
    if action not in operation_kind_by_action:
        raise ReadOnlyPolicyViolation(f"unknown_tool:{action}")
    effective_policy = policy or SelfExplorationPolicy()
    effective_policy.validate_operation(
        ReadOnlyOperation(kind=operation_kind_by_action[action], target=target)
    )


# ---------------------------------------------------------------------------
# Action JSON parsing
# ---------------------------------------------------------------------------

def parse_action_json(visible_text: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse structured action JSON from model visible output.

    Returns (parsed_dict, error_message).
    Separates critical fields (action/target/parameters) from diagnostic journal.
    """
    text = visible_text.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None, "JSON_MUST_BE_EXACT_OBJECT"
    parsed = _try_parse_json(text)
    if parsed is not None:
        return parsed, None
    return None, "INVALID_JSON"


def _try_parse_json(text: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def validate_action(parsed: dict[str, Any]) -> tuple[str | None, ExplorationDecisionJournal]:
    """Validate critical action fields. Returns (error_or_none, journal).

    Critical: action, target must be valid for execution.
    Journal: diagnostic fields are best-effort — partial journal doesn't block safe action.
    """
    unknown = sorted(set(parsed) - ALLOWED_DECISION_FIELDS)
    if unknown:
        return "UNKNOWN_FIELDS:" + ",".join(unknown), ExplorationDecisionJournal()

    action_str = parsed.get("action", "")
    if not action_str or action_str not in VALID_TOOLS:
        return f"INVALID_ACTION:{action_str}", ExplorationDecisionJournal()

    target = parsed.get("target")
    if target is None:
        target = ""
    if not isinstance(target, str):
        return "INVALID_TARGET_TYPE", ExplorationDecisionJournal()
    if len(target) > 500:
        return "TARGET_TOO_LONG", ExplorationDecisionJournal()

    # Path traversal check, including Windows drive/UNC and mixed separators.
    normalized_target = target.replace("\\", "/")
    has_drive_prefix = bool(re.match(r"^[A-Za-z]:/", normalized_target))
    has_unc_prefix = normalized_target.startswith("//")
    if (
        ".." in normalized_target.split("/")
        or has_drive_prefix
        or has_unc_prefix
        or (normalized_target.startswith("/") and normalized_target != "/" and not normalized_target.startswith("sentinel"))
    ):
        return "PATH_TRAVERSAL_BLOCKED", ExplorationDecisionJournal()

    params = parsed.get("parameters", {})
    if not isinstance(params, dict):
        params = {}

    journal_payload = {
        key: parsed.get(key)
        for key in ALLOWED_DECISION_FIELDS
        if key not in CRITICAL_FIELDS and key in parsed
    }
    if _unsafe_model_visible_text(journal_payload, path="$.decision_journal"):
        return "UNSAFE_JOURNAL_FIELD", ExplorationDecisionJournal()

    # Build journal from diagnostic fields (best-effort, never blocks action)
    journal = ExplorationDecisionJournal(
        decision_summary=str(parsed.get("decision_summary", ""))[:1500],
        evidence_refs=_safe_string_list(parsed.get("evidence_refs"), max_items=20),
        current_state=str(parsed.get("current_state", ""))[:300],
        facts_confirmed=_safe_string_list(parsed.get("facts_confirmed"), max_items=10, max_len=200),
        active_hypotheses=_safe_string_list(parsed.get("active_hypotheses"), max_items=5, max_len=300),
        hypotheses_rejected=_safe_string_list(parsed.get("hypotheses_rejected"), max_items=10, max_len=300),
        alternatives_considered=_safe_string_list(parsed.get("alternatives_considered"), max_items=5, max_len=200),
        expected_result=str(parsed.get("expected_result", ""))[:300],
        confidence=_safe_float(parsed.get("confidence"), default=0.5),
        uncertainties=_safe_string_list(parsed.get("uncertainties"), max_items=5, max_len=200),
        remaining_questions=_safe_string_list(parsed.get("remaining_questions"), max_items=5, max_len=200),
    )
    return None, journal


def _safe_string_list(val: Any, *, max_items: int = 10, max_len: int = 300) -> list[str]:
    if not isinstance(val, list):
        return []
    return [str(item)[:max_len] for item in val[:max_items] if isinstance(item, (str, int, float))]


def _safe_float(val: Any, *, default: float = 0.5) -> float:
    try:
        f = float(val)
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return default


def _unsafe_model_visible_text(payload: Any, *, path: str) -> bool:
    scan = scan_forbidden_payload_categorized(payload, path=path)
    return bool(scan[OrganSafetyScanCategory.ALL.value])


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

EXPLORATION_SYSTEM_PROMPT = """You are a read-only repository exploration agent for the Sentinel project.

Your mission: Explore the Sentinel repository to produce an evidence-backed architecture map with maturity labels and findings.

RULES:
- You can ONLY use read-only tools. No writes, patches, commits, or mutations.
- Each turn, respond with exactly one JSON object (no prose before or after).
- Your JSON must contain the critical fields: action, target, parameters.
- Include the diagnostic journal fields for monitoring (decision_summary, facts_confirmed, active_hypotheses, etc.)
- Evidence references (E1, E2...) refer to observations from previous turns.
- You may finish exploration early with action "finish_exploration".
- Build towards: architecture map, maturity labels, evidence-backed findings.

AVAILABLE TOOLS:
- list_directory: target=path, parameters={}
- search_text: target=query_string, parameters={scope: "optional/path/prefix"}
- search_symbol: target=class_or_function_name, parameters={}
- read_file_segment: target=file_path, parameters={start_line: N, end_line: M} (max 200 lines)
- find_references: target=symbol_name, parameters={scope: "optional/path/prefix"}
- inspect_test: target=test_file_path, parameters={}
- inspect_git_metadata: target=".", parameters={}
- finish_exploration: target="done", parameters={}

JSON FORMAT:
{
  "action": "tool_name",
  "target": "path_or_query",
  "parameters": {},
  "decision_summary": "Why this action (1-2 sentences)",
  "evidence_refs": ["E1", "E3"],
  "current_state": "What exploration phase",
  "facts_confirmed": ["fact1"],
  "active_hypotheses": ["H1: hypothesis"],
  "hypotheses_rejected": ["H0: rejected because..."],
  "alternatives_considered": ["Could have done X instead"],
  "expected_result": "What I expect to find",
  "confidence": 0.65,
  "uncertainties": ["Open question"],
  "remaining_questions": ["What still needs answering"]
}"""


def build_exploration_turn_prompt(
    *,
    mission_id: str,
    turn: int,
    state: ExplorationState,
    budget: ExplorationBudgetStatus,
    recent_turns: list[ExplorationTurnRecord],
) -> str:
    sections = [
        EXPLORATION_SYSTEM_PROMPT,
        f"\nMission ID: {mission_id}",
        f"Turn: {turn}",
        "",
        "=== EXPLORATION STATE ===",
    ]

    if state.facts_confirmed:
        sections.append("Confirmed facts:")
        for fact in state.facts_confirmed[-15:]:
            sections.append(f"  - {fact}")

    if state.active_hypotheses:
        sections.append("Active hypotheses:")
        for hyp in state.active_hypotheses:
            sections.append(f"  - {hyp}")

    if state.hypotheses_rejected:
        sections.append("Rejected hypotheses:")
        for hyp in state.hypotheses_rejected[-10:]:
            sections.append(f"  - {hyp}")

    sections.append("")
    sections.append("=== EVIDENCE CATALOG ===")
    if state.evidence_catalog:
        for entry in state.evidence_catalog:
            sections.append(f"  {entry.ref}: [{entry.action}] {entry.target} — {entry.summary} ({entry.bytes_size}B)")
    else:
        sections.append("  (empty — this is your first turn)")

    sections.append("")
    sections.append("=== RECENT TURNS ===")
    for rec in recent_turns[-3:]:
        sections.append(f"Turn {rec.turn}: {rec.action}({rec.target})")
        if rec.observation_summary:
            sections.append(f"  Observation: {rec.observation_summary[:500]}")
        if rec.evidence_ref:
            sections.append(f"  Evidence ref: {rec.evidence_ref}")

    sections.append("")
    sections.append("=== BUDGET ===")
    sections.append(json.dumps(budget.model_dump(), indent=2))

    sections.append("")
    sections.append("Choose your next action as a single JSON object.")

    return "\n".join(sections)


REPORT_PROMPT_TEMPLATE = """You are producing the {stage_name} for a read-only Sentinel repository exploration.

Mission ID: {mission_id}

IMPORTANT: Your entire report must be in your visible response. Do NOT place analysis in a thinking block.
The visible response must contain the complete Markdown report.

{stage_instructions}

=== EVIDENCE CATALOG ===
{evidence_catalog}

=== CONFIRMED FACTS ===
{facts}

=== ACTIVE HYPOTHESES ===
{hypotheses}

=== REJECTED HYPOTHESES ===
{rejected}

=== TRAJECTORY SUMMARY ===
{trajectory_summary}

=== TOP EVIDENCE EXCERPTS ===
{top_evidence}

{extra_context}

Produce your complete Markdown report now. Every claim must cite evidence references (E1, E2...).
Claims without evidence are classified as EVIDENCE_LINKED_CLAIM (not INDEPENDENTLY_VERIFIED)."""


def build_stage_a_report_prompt(
    *,
    mission_id: str,
    state: ExplorationState,
    trajectory_records: list[ExplorationTurnRecord],
    search_index: SnapshotSearchIndex,
) -> str:
    evidence_catalog = "\n".join(
        f"{e.ref}: [{e.action}] {e.target} — {e.summary} ({e.bytes_size}B)"
        for e in state.evidence_catalog
    )
    facts = "\n".join(f"- {f}" for f in state.facts_confirmed) or "(none)"
    hypotheses = "\n".join(f"- {h}" for h in state.active_hypotheses) or "(none)"
    rejected = "\n".join(f"- {h}" for h in state.hypotheses_rejected) or "(none)"
    trajectory_summary = (
        f"Total exploration turns: {len(trajectory_records)}\n"
        f"Files read: {len(state.files_read_set)}\n"
        f"Searches: {len(state.search_queries)}\n"
        f"Evidence entries: {len(state.evidence_catalog)}\n"
        f"Facts confirmed: {len(state.facts_confirmed)}\n"
        f"Hypotheses formed: {len(state.active_hypotheses) + len(state.hypotheses_rejected)}\n"
        f"Hypotheses rejected: {len(state.hypotheses_rejected)}"
    )

    # Top evidence excerpts: most-referenced entries
    ref_counts: dict[str, int] = {}
    for rec in trajectory_records:
        for ref in rec.decision_journal.get("evidence_refs", []):
            ref_counts[ref] = ref_counts.get(ref, 0) + 1
    top_refs = sorted(ref_counts.keys(), key=lambda r: ref_counts.get(r, 0), reverse=True)[:10]
    top_evidence_parts = []
    for ref in top_refs:
        entry = next((e for e in state.evidence_catalog if e.ref == ref), None)
        if entry:
            content = search_index.get_file_content(entry.target)
            if content:
                excerpt = _bounded_excerpt(content, 2000)
                top_evidence_parts.append(f"### {ref}: {entry.target}\n```\n{excerpt}\n```")
    top_evidence = "\n\n".join(top_evidence_parts) or "(no frequently-cited evidence)"

    return REPORT_PROMPT_TEMPLATE.format(
        stage_name="Stage A Architecture Report",
        mission_id=mission_id,
        stage_instructions=(
            "Stage A: Blind code-first reconstruction.\n"
            "Build an architecture map with maturity labels: "
            "LIVE_PROVEN, LIVE_BOUNDED, LOCAL_ONLY, INJECTED, SANDBOX, PAPER, FOUNDATION, "
            "CONTRACT_ONLY, BLOCKED, ABSENT, UNKNOWN.\n"
            "For every claim, cite evidence references from your exploration.\n"
            "List your strongest evidence-backed findings.\n"
            "Mark unsupported claims as EVIDENCE_LINKED_CLAIM (not verified)."
        ),
        evidence_catalog=evidence_catalog,
        facts=facts,
        hypotheses=hypotheses,
        rejected=rejected,
        trajectory_summary=trajectory_summary,
        top_evidence=top_evidence,
        extra_context="",
    )


def build_stage_b_report_prompt(
    *,
    mission_id: str,
    state: ExplorationState,
    trajectory_records: list[ExplorationTurnRecord],
    stage_a_report: str,
    snapshot: ReadOnlyRepositorySnapshot,
    policy: SelfExplorationPolicy,
) -> str:
    evidence_catalog = "\n".join(
        f"{e.ref}: [{e.action}] {e.target} — {e.summary} ({e.bytes_size}B)"
        for e in state.evidence_catalog
    )
    facts = "\n".join(f"- {f}" for f in state.facts_confirmed) or "(none)"
    hypotheses = "\n".join(f"- {h}" for h in state.active_hypotheses) or "(none)"
    rejected = "\n".join(f"- {h}" for h in state.hypotheses_rejected) or "(none)"
    trajectory_summary = f"Total turns: {len(trajectory_records)}, Facts: {len(state.facts_confirmed)}"

    # Truth documents
    truth_parts = []
    for doc_path in policy.stage_b_truth_docs:
        if snapshot.can_read(doc_path, stage="B"):
            text = snapshot.read_file(doc_path, stage="B")
            truth_parts.append(f"### {doc_path}\n```\n{_bounded_excerpt(text, 4000)}\n```")
        else:
            truth_parts.append(f"### {doc_path}\nUNAVAILABLE")
    truth_text = "\n\n".join(truth_parts)

    stage_a_excerpt = _bounded_excerpt(stage_a_report, 6000)

    return REPORT_PROMPT_TEMPLATE.format(
        stage_name="Stage B Truth Reconciliation Report",
        mission_id=mission_id,
        stage_instructions=(
            "Stage B: Truth reconciliation.\n"
            "Compare your Stage A code-derived findings against these canonical truth documents.\n"
            "Classify each claim: CONFIRMED, LIKELY, EVIDENCE_LINKED_CLAIM, NOT_SUPPORTED.\n"
            "Identify: confirmed claims, optimistic claims, stale claims, missing claims, contradictions.\n"
            "Each finding must include: id, title, severity, confidence, evidence refs, impact."
        ),
        evidence_catalog=evidence_catalog,
        facts=facts,
        hypotheses=hypotheses,
        rejected=rejected,
        trajectory_summary=trajectory_summary,
        top_evidence=f"=== STAGE A REPORT ===\n{stage_a_excerpt}",
        extra_context=f"=== CANONICAL TRUTH DOCUMENTS ===\n{truth_text}",
    )


# ---------------------------------------------------------------------------
# Visible report safety
# ---------------------------------------------------------------------------

def reject_unsafe_visible_report(text: str, *, stage: str) -> None:
    if not text.strip():
        raise RuntimeError(f"unsafe_visible_report:{stage}:empty")
    scan = scan_forbidden_payload_categorized(
        {"visible_report": text},
        path=f"$.{stage}.visible_report",
    )
    if scan[OrganSafetyScanCategory.ALL.value]:
        raise RuntimeError(
            f"unsafe_visible_report:{stage}:"
            + ",".join(scan[OrganSafetyScanCategory.ALL.value])
        )


def safe_model_call_result(call: SelfExplorationModelCall, *, stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "visible_text_hash": text_hash(call.visible_text) if call.visible_text else None,
        "visible_text_length": len(call.visible_text),
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "latency_seconds": call.latency_seconds,
        "finish_reason": call.finish_reason,
        "output_truncated": call.output_truncated,
        "reasoning_present": call.reasoning_present,
        "reasoning_hash": call.reasoning_hash,
        "reasoning_char_count": call.reasoning_char_count,
        "reasoning_token_count": call.reasoning_token_count,
        "provider_error": call.provider_error,
    }


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

def run_smoke_a(model_client: OpenAICompatibleSelfExplorationModelClient,
                policy: SelfExplorationPolicy, mission_id: str) -> tuple[bool, dict[str, Any]]:
    """Visible-report smoke test. Returns (passed, result_dict)."""
    prompt = (
        "You are a model evaluation smoke test.\n"
        "Produce exactly five lines of visible text assessing the repository name \"Sentinel\".\n"
        "Line 1: The project name.\n"
        "Line 2: What the name suggests.\n"
        "Line 3: A one-word assessment.\n"
        "Line 4: Your model identifier.\n"
        "Line 5: The word \"SMOKE_COMPLETE\".\n"
    )
    call = model_client.complete(prompt=prompt, policy=policy, mission_id=mission_id, stage="smoke_a")
    passed = (
        bool(call.visible_text.strip())
        and len(call.visible_text) >= 50
        and "SMOKE_COMPLETE" in call.visible_text
        and call.provider_error is None
    )
    return passed, {
        "passed": passed,
        "visible_text_length": len(call.visible_text),
        "contains_marker": "SMOKE_COMPLETE" in call.visible_text,
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "latency_seconds": call.latency_seconds,
        "reasoning_present": call.reasoning_present,
        "reasoning_hash": call.reasoning_hash,
        "provider_error": call.provider_error,
    }


def run_smoke_b(model_client: OpenAICompatibleSelfExplorationModelClient,
                policy: SelfExplorationPolicy, mission_id: str,
                search_index: SnapshotSearchIndex, snapshot: ReadOnlyRepositorySnapshot,
                state: ExplorationState, budget: ExplorationBudgetStatus) -> tuple[bool, dict[str, Any]]:
    """Action-protocol smoke test. Returns (passed, result_dict)."""
    prompt = (
        "You are a repository exploration agent. You have been given access to read-only tools.\n"
        "Your first task: list the root directory of the repository.\n\n"
        "Respond with exactly one JSON object. No prose before or after. No markdown code fences.\n\n"
        "Required fields:\n"
        '{\n'
        '  "action": "list_directory",\n'
        '  "target": ".",\n'
        '  "parameters": {},\n'
        '  "decision_summary": "Initial scan of root directory to understand project structure.",\n'
        '  "evidence_refs": [],\n'
        '  "current_state": "initial exploration",\n'
        '  "facts_confirmed": [],\n'
        '  "active_hypotheses": [],\n'
        '  "confidence": 0.5\n'
        '}\n'
    )
    call = model_client.complete(prompt=prompt, policy=policy, mission_id=mission_id, stage="smoke_b")
    parsed, parse_error = parse_action_json(call.visible_text)
    json_valid = parsed is not None
    action_error: str | None = None
    action_valid = False
    tool_result = ""
    tool_success = False
    if json_valid:
        action_error, journal = validate_action(parsed)
        if action_error is None:
            if parsed.get("action") != ExplorationTool.LIST_DIRECTORY:
                action_error = "SMOKE_B_WRONG_ACTION"
            elif str(parsed.get("target", ".")).strip() not in {"", ".", "/"}:
                action_error = "SMOKE_B_WRONG_TARGET"
            else:
                action_valid = True
        if action_valid:
            try:
                obs, obs_bytes, match_count = execute_snapshot_tool(
                    ExplorationTool(parsed["action"]),
                    str(parsed.get("target", ".")),
                    parsed.get("parameters", {}),
                    policy=policy,
                    search_index=search_index,
                    snapshot=snapshot,
                    state=state,
                    budget=budget,
                )
                tool_result = obs[:500]
                tool_success = bool(obs.strip())
            except ReadOnlyPolicyViolation as exc:
                tool_result = str(exc)
    passed = json_valid and action_valid and tool_success and call.provider_error is None
    return passed, {
        "passed": passed,
        "json_valid": json_valid,
        "parse_error": parse_error,
        "action_valid": action_valid,
        "action_error": action_error,
        "tool_success": tool_success,
        "tool_result_preview": tool_result[:200],
        "visible_text_length": len(call.visible_text),
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "latency_seconds": call.latency_seconds,
        "reasoning_present": call.reasoning_present,
        "reasoning_hash": call.reasoning_hash,
        "provider_error": call.provider_error,
    }


# ---------------------------------------------------------------------------
# Interactive exploration loop
# ---------------------------------------------------------------------------

class ReadOnlyExplorationLoop:
    """Interactive read-only exploration loop with adaptive budget."""

    def __init__(
        self,
        *,
        model_client: OpenAICompatibleSelfExplorationModelClient,
        policy: SelfExplorationPolicy,
        snapshot: ReadOnlyRepositorySnapshot,
        search_index: SnapshotSearchIndex,
        mission_id: str,
        output_root: Path,
    ) -> None:
        self.model_client = model_client
        self.policy = policy
        self.snapshot = snapshot
        self.search_index = search_index
        self.mission_id = mission_id
        self.output_root = output_root
        self.state = ExplorationState()
        self.budget = ExplorationBudgetStatus()
        self.trajectory: list[ExplorationTurnRecord] = []
        self._started = time.perf_counter()

    def run(self) -> tuple[ExplorationState, list[ExplorationTurnRecord]]:
        """Run the interactive exploration loop. Returns (final_state, trajectory)."""
        trajectory_path = self.output_root / "exploration_trajectory.jsonl"

        for turn_num in range(1, MAX_EXPLORATION_TURNS + 1):
            elapsed = time.perf_counter() - self._started
            if elapsed > MAX_EXPERIMENT_DURATION_SECONDS:
                self._record_early_stop("TIME_BUDGET_EXHAUSTED", turn_num, trajectory_path)
                break
            if self.budget.cumulative_input_tokens >= MAX_CUMULATIVE_INPUT_TOKENS:
                self._record_early_stop("INPUT_TOKEN_BUDGET_EXHAUSTED", turn_num, trajectory_path)
                break
            if self.budget.cumulative_output_tokens >= MAX_CUMULATIVE_OUTPUT_TOKENS:
                self._record_early_stop("OUTPUT_TOKEN_BUDGET_EXHAUSTED", turn_num, trajectory_path)
                break

            # Adaptive budget: if past base turns and nonproductive, suggest finishing
            if (turn_num > EXPLORATION_BASE_TURNS
                    and self.state.nonproductive_streak >= NONPRODUCTIVE_TURN_LIMIT):
                self._record_early_stop("NONPRODUCTIVE_STREAK", turn_num, trajectory_path)
                break

            self._update_budget(turn_num, elapsed)
            prompt = build_exploration_turn_prompt(
                mission_id=self.mission_id,
                turn=turn_num,
                state=self.state,
                budget=self.budget,
                recent_turns=self.trajectory,
            )

            call = self.model_client.complete(
                prompt=prompt, policy=self.policy,
                mission_id=self.mission_id, stage=f"exploration_turn_{turn_num}",
            )
            latency = call.latency_seconds

            self.budget.cumulative_input_tokens += call.input_tokens
            self.budget.cumulative_output_tokens += call.output_tokens
            self.budget.model_calls_used += 1

            # Parse action
            parsed, parse_error = parse_action_json(call.visible_text)
            if parsed is None:
                record = self._make_turn_record(
                    turn_num, "PARSE_FAILED", "", {}, ExplorationDecisionJournal(),
                    "", 0, None, None, latency, call, parse_success=False,
                )
                self._append_trajectory(record, trajectory_path)
                continue

            # Validate action
            action_error, journal = validate_action(parsed)
            action_str = parsed.get("action", "UNKNOWN")
            target_str = str(parsed.get("target", ""))
            params = parsed.get("parameters", {}) if isinstance(parsed.get("parameters"), dict) else {}

            if action_error:
                record = self._make_turn_record(
                    turn_num, action_str, target_str, params, journal,
                    "", 0, None, None, latency, call,
                    parse_success=True, validation_success=False,
                    blocked_reason=action_error,
                )
                self._append_trajectory(record, trajectory_path)
                continue

            # Check for finish
            if action_str == ExplorationTool.FINISH_EXPLORATION:
                depth_ready, missing_depth = self.state.finish_depth_gate()
                if not depth_ready:
                    blocked = "DEPTH_GATE_BLOCKED:" + ",".join(missing_depth)
                    record = self._make_turn_record(
                        turn_num, action_str, target_str, params, journal,
                        blocked, 0, None, None, latency, call,
                        parse_success=True, validation_success=False,
                        blocked_reason=blocked,
                    )
                    self._append_trajectory(record, trajectory_path)
                    continue
                productive = self.state.update_from_journal(journal)
                record = self._make_turn_record(
                    turn_num, action_str, target_str, params, journal,
                    "EXPLORATION_COMPLETE", 0, None, None, latency, call,
                    parse_success=True, validation_success=True, productive=productive,
                )
                self._append_trajectory(record, trajectory_path)
                break

            # Execute tool
            try:
                obs_text, obs_bytes, match_count = execute_snapshot_tool(
                    ExplorationTool(action_str), target_str, params,
                    policy=self.policy,
                    search_index=self.search_index,
                    snapshot=self.snapshot,
                    state=self.state,
                    budget=self.budget,
                )
            except ReadOnlyPolicyViolation as exc:
                record = self._make_turn_record(
                    turn_num, action_str, target_str, params, journal,
                    "", 0, None, None, latency, call,
                    parse_success=True, validation_success=False,
                    blocked_reason=str(exc),
                )
                self._append_trajectory(record, trajectory_path)
                continue

            # Update budget
            self.budget.bytes_read += obs_bytes
            if action_str in {ExplorationTool.READ_FILE_SEGMENT, ExplorationTool.INSPECT_TEST}:
                self.budget.files_read += 1

            # Add evidence
            obs_summary = obs_text[:300] if obs_text else ""
            evidence_ref = self.state.add_evidence(
                turn=turn_num, action=action_str, target=target_str,
                summary=obs_summary, content=obs_text, match_count=match_count,
            )

            # Update state from journal
            productive = self.state.update_from_journal(journal)
            latest = self.state.evidence_catalog[-1] if self.state.evidence_catalog else None
            evidence_is_novel = latest is not None and latest.novelty_status == "NOVEL"
            if obs_bytes > 0 and evidence_is_novel:
                productive = True
                self.state.nonproductive_streak = 0
            elif latest is not None and latest.novelty_status != "NOVEL" and not productive:
                self.state.nonproductive_streak += 1

            record = self._make_turn_record(
                turn_num, action_str, target_str, params, journal,
                obs_summary, obs_bytes, match_count, evidence_ref,
                latency, call,
                parse_success=True, validation_success=True, productive=productive,
            )
            self._append_trajectory(record, trajectory_path)

        return self.state, self.trajectory

    def _update_budget(self, turn: int, elapsed: float) -> None:
        self.budget.turns_used = turn - 1
        self.budget.turns_remaining = MAX_EXPLORATION_TURNS - turn + 1
        self.budget.files_remaining = MAX_TOTAL_FILES_READ - self.budget.files_read
        self.budget.bytes_remaining = MAX_TOTAL_BYTES_READ - self.budget.bytes_read
        self.budget.evidence_catalog_size = len(self.state.evidence_catalog)
        self.budget.output_tokens_remaining = MAX_CUMULATIVE_OUTPUT_TOKENS - self.budget.cumulative_output_tokens
        self.budget.elapsed_seconds = round(elapsed, 2)
        self.budget.time_remaining_seconds = round(MAX_EXPERIMENT_DURATION_SECONDS - elapsed, 2)
        self.budget.model_calls_remaining = MAX_TOTAL_MODEL_CALLS - self.budget.model_calls_used

    def _make_turn_record(
        self, turn: int, action: str, target: str, params: dict,
        journal: ExplorationDecisionJournal,
        obs_summary: str, obs_bytes: int, match_count: int | None,
        evidence_ref: str | None, latency: float,
        call: SelfExplorationModelCall,
        *, parse_success: bool = False, validation_success: bool = False,
        blocked_reason: str | None = None, productive: bool = False,
    ) -> ExplorationTurnRecord:
        return ExplorationTurnRecord(
            turn=turn,
            timestamp_utc=datetime.now(UTC).isoformat(),
            action=action,
            target=target,
            parameters=params,
            decision_journal=journal.model_dump(mode="json"),
            journal_quality=journal.journal_quality,
            observation_summary=obs_summary,
            observation_bytes=obs_bytes,
            observation_matches=match_count,
            evidence_ref=evidence_ref,
            latency_seconds=round(latency, 4),
            input_tokens=call.input_tokens,
            output_tokens=call.output_tokens,
            cumulative_input_tokens=self.budget.cumulative_input_tokens,
            cumulative_output_tokens=self.budget.cumulative_output_tokens,
            cumulative_files_read=self.budget.files_read,
            cumulative_bytes_read=self.budget.bytes_read,
            parse_success=parse_success,
            validation_success=validation_success,
            action_blocked_reason=blocked_reason,
            reasoning_metadata={
                "reasoning_present": call.reasoning_present,
                "reasoning_hash": call.reasoning_hash,
                "reasoning_token_count": call.reasoning_token_count,
            },
            productive=productive,
        )

    def _append_trajectory(self, record: ExplorationTurnRecord, path: Path) -> None:
        self.trajectory.append(record)
        with open(path, "a", encoding="utf-8") as f:
            f.write(record.model_dump_json() + "\n")

    def _record_early_stop(self, reason: str, turn: int, path: Path) -> None:
        record = ExplorationTurnRecord(
            turn=turn,
            timestamp_utc=datetime.now(UTC).isoformat(),
            action="EARLY_STOP",
            target=reason,
            observation_summary=f"Exploration stopped: {reason}",
        )
        self._append_trajectory(record, path)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

class InteractiveExplorationRunner:
    """Orchestrates: smoke → exploration → Stage A → Stage B."""

    def __init__(
        self,
        *,
        policy: SelfExplorationPolicy,
        model_client: OpenAICompatibleSelfExplorationModelClient,
    ) -> None:
        self.policy = policy
        self.model_client = model_client

    def run(
        self,
        *,
        repo_root: Path,
        output_root: Path,
        expected_policy_hash: str,
    ) -> InteractiveExplorationReport:
        policy_hash = interactive_policy_hash(self.policy)
        if policy_hash != expected_policy_hash:
            raise RuntimeError(f"policy_hash_mismatch: expected={expected_policy_hash} got={policy_hash}")

        if output_root.exists():
            raise RuntimeError("output_root_already_exists")
        output_root.mkdir(parents=True)

        started = time.perf_counter()
        mission_id = new_id("interactive_exploration")
        run_id = new_id("interactive_run")

        # Freeze snapshot
        print(f"[{_ts()}] Freezing repository snapshot...", flush=True)
        snapshot = ReadOnlyRepositorySnapshot.freeze(repo_root=repo_root, policy=self.policy)
        snapshot_id = _snapshot_identity(snapshot)
        _write_json(output_root / "snapshot_identity.json", snapshot_id)
        _write_json(output_root / "policy_freeze.json", {
            "policy_hash": policy_hash,
            "safe_policy": interactive_safe_policy(self.policy),
        })

        # Build full-text search index
        print(f"[{_ts()}] Building full-text search index ({len(snapshot.inventory)} files)...", flush=True)
        search_index = SnapshotSearchIndex(snapshot)
        print(f"[{_ts()}] Index ready: {search_index.file_count} files, {search_index.total_bytes} bytes.", flush=True)

        base_report = InteractiveExplorationReport(
            status="failed", verdict="NOT_STARTED",
            policy_hash=policy_hash, snapshot_identity=snapshot_id,
            provider_id=self.policy.provider_id, model_id=self.policy.model_id,
            mission_id=mission_id, run_id=run_id, output_root=str(output_root),
        )

        # Smoke A
        print(f"[{_ts()}] Running Smoke A (visible report)...", flush=True)
        smoke_a_passed, smoke_a_result = run_smoke_a(self.model_client, self.policy, mission_id)
        _write_json(output_root / "smoke_a_result.json", smoke_a_result)
        print(f"[{_ts()}] Smoke A: {'PASSED' if smoke_a_passed else 'FAILED'}", flush=True)
        if not smoke_a_passed:
            base_report.smoke_a_passed = False
            base_report.status = "failed"
            base_report.verdict = "SMOKE_A_FAILED"
            base_report.duration_seconds = round(time.perf_counter() - started, 4)
            _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
            return base_report

        # Smoke B
        print(f"[{_ts()}] Running Smoke B (action protocol)...", flush=True)
        temp_state = ExplorationState()
        temp_budget = ExplorationBudgetStatus()
        smoke_b_passed, smoke_b_result = run_smoke_b(
            self.model_client, self.policy, mission_id,
            search_index, snapshot, temp_state, temp_budget,
        )
        _write_json(output_root / "smoke_b_result.json", smoke_b_result)
        print(f"[{_ts()}] Smoke B: {'PASSED' if smoke_b_passed else 'FAILED'}", flush=True)
        if not smoke_b_passed:
            base_report.smoke_a_passed = True
            base_report.smoke_b_passed = False
            base_report.status = "failed"
            base_report.verdict = "SMOKE_B_FAILED"
            base_report.duration_seconds = round(time.perf_counter() - started, 4)
            _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
            return base_report

        base_report.smoke_a_passed = True
        base_report.smoke_b_passed = True
        base_report.status = "partial"
        base_report.verdict = "SMOKES_PASSED_EXPLORATION_PENDING"
        base_report.duration_seconds = round(time.perf_counter() - started, 4)
        _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))

        # Interactive exploration
        print(f"[{_ts()}] Starting interactive exploration loop...", flush=True)
        loop = ReadOnlyExplorationLoop(
            model_client=self.model_client,
            policy=self.policy,
            snapshot=snapshot,
            search_index=search_index,
            mission_id=mission_id,
            output_root=output_root,
        )
        final_state, trajectory = loop.run()
        print(f"[{_ts()}] Exploration complete: {len(trajectory)} turns.", flush=True)

        _write_json(output_root / "exploration_state_final.json", final_state.model_dump(mode="json"))
        _write_json(output_root / "evidence_catalog.json",
                     [e.model_dump(mode="json") for e in final_state.evidence_catalog])

        base_report.total_exploration_turns = len(trajectory)
        base_report.exploration_state_final = final_state.model_dump(mode="json")
        base_report.evidence_catalog = [e.model_dump(mode="json") for e in final_state.evidence_catalog]
        base_report.trajectory_file = str(output_root / "exploration_trajectory.jsonl")
        base_report.cumulative_input_tokens = loop.budget.cumulative_input_tokens
        base_report.cumulative_output_tokens = loop.budget.cumulative_output_tokens
        base_report.total_model_calls = loop.budget.model_calls_used + 2  # +2 for smokes
        base_report.status = "partial"
        base_report.verdict = "EXPLORATION_COMPLETED_STAGE_A_PENDING"
        base_report.duration_seconds = round(time.perf_counter() - started, 4)
        _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))

        # Stage A report
        print(f"[{_ts()}] Generating Stage A report...", flush=True)
        stage_a_prompt = build_stage_a_report_prompt(
            mission_id=mission_id, state=final_state,
            trajectory_records=trajectory, search_index=search_index,
        )
        (output_root / "stage_a_prompt_hash.txt").write_text(text_hash(stage_a_prompt) + "\n", encoding="utf-8")
        stage_a_call = self.model_client.complete(
            prompt=stage_a_prompt, policy=self.policy,
            mission_id=mission_id, stage="stage_a_report",
        )
        _write_json(output_root / "stage_a_call_result.json", safe_model_call_result(stage_a_call, stage="stage_a_report"))
        base_report.cumulative_input_tokens += stage_a_call.input_tokens
        base_report.cumulative_output_tokens += stage_a_call.output_tokens
        stage_a_report = stage_a_call.visible_text
        if stage_a_report.strip():
            try:
                reject_unsafe_visible_report(stage_a_report, stage="stage_a")
            except RuntimeError:
                base_report.status = "failed"
                base_report.verdict = "STAGE_A_UNSAFE_VISIBLE_REPORT"
                base_report.duration_seconds = round(time.perf_counter() - started, 4)
                _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
                return base_report
            (output_root / "stage_a_report.md").write_text(stage_a_report, encoding="utf-8")
            base_report.stage_a_report_hash = text_hash(stage_a_report)
            print(f"[{_ts()}] Stage A report: {len(stage_a_report)} chars.", flush=True)
        else:
            base_report.status = "failed"
            base_report.verdict = "STAGE_A_EMPTY"
            base_report.duration_seconds = round(time.perf_counter() - started, 4)
            _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
            return base_report

        base_report.total_model_calls += 1
        base_report.status = "partial"
        base_report.verdict = "STAGE_A_COMPLETED_STAGE_B_PENDING"
        base_report.duration_seconds = round(time.perf_counter() - started, 4)
        _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))

        # Stage B report
        print(f"[{_ts()}] Generating Stage B reconciliation report...", flush=True)
        stage_b_prompt = build_stage_b_report_prompt(
            mission_id=mission_id, state=final_state,
            trajectory_records=trajectory, stage_a_report=stage_a_report,
            snapshot=snapshot, policy=self.policy,
        )
        (output_root / "stage_b_prompt_hash.txt").write_text(text_hash(stage_b_prompt) + "\n", encoding="utf-8")
        stage_b_call = self.model_client.complete(
            prompt=stage_b_prompt, policy=self.policy,
            mission_id=mission_id, stage="stage_b_report",
        )
        _write_json(output_root / "stage_b_call_result.json", safe_model_call_result(stage_b_call, stage="stage_b_report"))
        base_report.total_model_calls += 1
        base_report.cumulative_input_tokens += stage_b_call.input_tokens
        base_report.cumulative_output_tokens += stage_b_call.output_tokens
        stage_b_report = stage_b_call.visible_text
        if stage_b_report.strip():
            try:
                reject_unsafe_visible_report(stage_b_report, stage="stage_b")
            except RuntimeError:
                base_report.status = "failed"
                base_report.verdict = "STAGE_B_UNSAFE_VISIBLE_REPORT"
                base_report.duration_seconds = round(time.perf_counter() - started, 4)
                _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
                return base_report
            (output_root / "stage_b_report.md").write_text(stage_b_report, encoding="utf-8")
            base_report.stage_b_report_hash = text_hash(stage_b_report)
            print(f"[{_ts()}] Stage B report: {len(stage_b_report)} chars.", flush=True)
        else:
            base_report.status = "failed"
            base_report.verdict = "STAGE_B_EMPTY"
            base_report.duration_seconds = round(time.perf_counter() - started, 4)
            _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
            return base_report

        # Verify snapshot unchanged
        if not snapshot.verify_unchanged():
            raise RuntimeError("repository_changed_during_run")

        # Write trajectory summary
        _write_trajectory_summary(output_root / "trajectory_summary.md", trajectory, final_state)

        # Final report
        base_report.status = "completed"
        base_report.verdict = "INTERACTIVE_EXPLORATION_COMPLETED"
        base_report.duration_seconds = round(time.perf_counter() - started, 4)
        early = any(r.action == "EARLY_STOP" for r in trajectory)
        if early:
            base_report.early_termination = True
            stop_rec = next(r for r in trajectory if r.action == "EARLY_STOP")
            base_report.early_termination_reason = stop_rec.target
        finished = any(r.action == ExplorationTool.FINISH_EXPLORATION for r in trajectory)
        if finished:
            base_report.early_termination = True
            base_report.early_termination_reason = "MODEL_CHOSE_FINISH"

        _write_json(output_root / "final_report.json", base_report.model_dump(mode="json"))
        print(f"[{_ts()}] Run complete. Verdict: {base_report.verdict}", flush=True)
        return base_report


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _ts() -> str:
    return datetime.now(UTC).strftime("%H:%M:%S")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _write_trajectory_summary(path: Path, trajectory: list[ExplorationTurnRecord],
                               state: ExplorationState) -> None:
    lines = ["# Exploration Trajectory Summary\n"]
    for rec in trajectory:
        marker = "✅" if rec.productive else "⬜"
        lines.append(
            f"{marker} **Turn {rec.turn}**: `{rec.action}({rec.target})`"
            f" — {rec.observation_bytes}B"
            f" [{rec.journal_quality}]"
            f" {rec.latency_seconds:.1f}s"
        )
        if rec.evidence_ref:
            lines.append(f"  → {rec.evidence_ref}: {rec.observation_summary[:120]}")
        if rec.action_blocked_reason:
            lines.append(f"  ⛔ Blocked: {rec.action_blocked_reason}")
    lines.append(f"\n## Final State")
    lines.append(f"- Facts: {len(state.facts_confirmed)}")
    lines.append(f"- Active hypotheses: {len(state.active_hypotheses)}")
    lines.append(f"- Rejected hypotheses: {len(state.hypotheses_rejected)}")
    lines.append(f"- Evidence entries: {len(state.evidence_catalog)}")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Sentinel interactive read-only exploration V1."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path.cwd().parents[2] if Path.cwd().name == "sentinel-core" else Path.cwd()),
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--expected-policy-hash")
    parser.add_argument("--print-policy-and-exit", action="store_true")
    parser.add_argument(
        "--base-url",
        default=os.environ.get(CERT_BASE_URL_ENV, DEFAULT_BASE_URL),
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    args = parser.parse_args(argv)

    policy = SelfExplorationPolicy(
        experiment_version=INTERACTIVE_EXPERIMENT_VERSION,
        base_url=args.base_url,
        model_id=args.model_id,
        max_model_calls=MAX_TOTAL_MODEL_CALLS,
        max_files_read=MAX_TOTAL_FILES_READ,
        max_bytes_read=MAX_TOTAL_BYTES_READ,
        max_output_tokens_per_call=REPORT_A_OUTPUT_TOKENS,
        max_total_tokens=MAX_CUMULATIVE_INPUT_TOKENS,
        max_duration_seconds=MAX_EXPERIMENT_DURATION_SECONDS,
        max_report_chars=80_000,
    )

    if args.print_policy_and_exit:
        snapshot = ReadOnlyRepositorySnapshot.freeze(
            repo_root=Path(args.repo_root), policy=policy,
        )
        print(json.dumps({
            "experiment_version": INTERACTIVE_EXPERIMENT_VERSION,
            "safe_policy": interactive_safe_policy(policy),
            "policy_hash": interactive_policy_hash(policy),
            "snapshot": _snapshot_identity(snapshot),
            "budgets": {
                "max_exploration_turns": MAX_EXPLORATION_TURNS,
                "exploration_output_tokens": EXPLORATION_OUTPUT_TOKENS,
                "report_a_output_tokens": REPORT_A_OUTPUT_TOKENS,
                "report_b_output_tokens": REPORT_B_OUTPUT_TOKENS,
                "max_cumulative_input_tokens": MAX_CUMULATIVE_INPUT_TOKENS,
                "max_cumulative_output_tokens": MAX_CUMULATIVE_OUTPUT_TOKENS,
                "max_total_model_calls": MAX_TOTAL_MODEL_CALLS,
                "max_experiment_duration_seconds": MAX_EXPERIMENT_DURATION_SECONDS,
            },
        }, indent=2, sort_keys=True))
        return 0

    if not args.expected_policy_hash:
        raise RuntimeError("--expected-policy-hash is required for execution")

    model_client = OpenAICompatibleSelfExplorationModelClient(policy=policy)
    runner = InteractiveExplorationRunner(policy=policy, model_client=model_client)
    report = runner.run(
        repo_root=Path(args.repo_root),
        output_root=Path(args.output_root),
        expected_policy_hash=args.expected_policy_hash,
    )
    print(json.dumps({
        "verdict": report.verdict,
        "status": report.status,
        "exploration_turns": report.total_exploration_turns,
        "model_calls": report.total_model_calls,
        "duration_seconds": report.duration_seconds,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
