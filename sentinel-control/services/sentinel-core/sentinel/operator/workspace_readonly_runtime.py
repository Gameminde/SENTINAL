from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sentinel.agent.model_execution.redaction import stable_hash, text_hash
from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.operator.action_kernel import ActionEnvelope, ActionResult
from sentinel.operator.redaction import redact_operator_text, redact_operator_value


class WorkspaceReadOnlyRuntimeError(RuntimeError):
    pass


class WorkspaceReadOnlyRuntime:
    """Read-only workspace backend for ProductActionKernel workspace skills."""

    def __init__(self, *, workspace_root: Path | str) -> None:
        self.workspace_root = Path(workspace_root).resolve()

    def execute(
        self,
        envelope: ActionEnvelope,
        *,
        authority: MissionAuthorityEnvelope,
        context: dict[str, Any],
    ) -> ActionResult:
        _assert_workspace_authority(authority, self.workspace_root)
        operation = envelope.operation
        if operation == "list":
            status, observation, summary = self._list(envelope.params)
        elif operation == "read":
            status, observation, summary = self._read(envelope.params)
        elif operation == "search":
            status, observation, summary = self._search(envelope.params)
        else:
            raise WorkspaceReadOnlyRuntimeError(f"workspace_operation_unsupported:{operation}")
        observation = redact_operator_value(observation)
        evidence_ref = f"workspace_evidence:{stable_hash(observation)[:24]}"
        return ActionResult(
            action_id=envelope.action_id,
            capability_id=envelope.capability_id,
            operation=envelope.operation,
            status=status,
            evidence_refs=(evidence_ref,),
            material_action=True,
            observation_summary=summary,
            context_cards={
                "workspace_readonly_observation": observation,
                "workspace_readonly_evidence_ref": evidence_ref,
                "workspace_readonly_backend": {
                    "backend_id": "workspace_read_only",
                    "authority": "workspace_read",
                    "root_hash": stable_hash(str(self.workspace_root)),
                    "data_not_authority": True,
                    "can_execute": False,
                    "can_grant_authority": False,
                },
            },
        )

    def _list(self, arguments: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        target = _resolve_workspace_path(self.workspace_root, str(arguments.get("path") or "."), must_exist=True)
        if not target.is_dir():
            raise WorkspaceReadOnlyRuntimeError("workspace_list_target_not_directory")
        entries = tuple(
            f"{child.name}/" if child.is_dir() else child.name
            for child in sorted(target.iterdir(), key=lambda item: item.name.lower())
        )
        relative = _relative_workspace_path(self.workspace_root, target)
        return (
            "completed",
            {"path": relative, "entries": entries, "entry_count": len(entries)},
            f"workspace list observed {len(entries)} entries at {relative}.",
        )

    def _read(self, arguments: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        target = _resolve_workspace_path(self.workspace_root, str(arguments.get("path") or ""), must_exist=True)
        if not target.is_file():
            raise WorkspaceReadOnlyRuntimeError("workspace_read_target_not_file")
        max_chars = _bounded_int(arguments.get("max_chars"), default=1200, minimum=1, maximum=4000)
        max_bytes = _bounded_int(arguments.get("max_bytes"), default=1_000_000, minimum=1, maximum=4_000_000)
        try:
            byte_count = target.stat().st_size
        except OSError as exc:
            raise WorkspaceReadOnlyRuntimeError("workspace_read_stat_failed") from exc
        if byte_count > max_bytes:
            raise WorkspaceReadOnlyRuntimeError("workspace_read_target_too_large")
        data = target.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceReadOnlyRuntimeError("workspace_read_binary_target_blocked") from exc
        relative = _relative_workspace_path(self.workspace_root, target)
        excerpt = redact_operator_text(text[:max_chars])
        return (
            "completed",
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "byte_count": len(data),
                "content_excerpt": excerpt,
                "truncated": len(text) > max_chars,
            },
            f"workspace file observed at {relative}.",
        )

    def _search(self, arguments: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise WorkspaceReadOnlyRuntimeError("workspace_search_query_required")
        root = _resolve_workspace_path(self.workspace_root, str(arguments.get("path") or "."), must_exist=True)
        if not root.is_dir():
            raise WorkspaceReadOnlyRuntimeError("workspace_search_root_not_directory")
        lowered_query = query.lower()
        normalized_query_terms = _normalized_search_terms(query)
        max_files = _bounded_int(arguments.get("max_files"), default=1000, minimum=1, maximum=5000)
        max_bytes_per_file = _bounded_int(arguments.get("max_bytes_per_file"), default=256_000, minimum=1, maximum=1_000_000)
        matches: list[dict[str, Any]] = []
        files_examined_count = 0
        skipped_outside_root_count = 0
        skipped_max_files_count = 0
        skipped_too_large_count = 0
        skipped_io_error_count = 0
        skipped_binary_count = 0
        for path in sorted(root.rglob("*"), key=lambda item: str(item).lower()):
            try:
                resolved = path.resolve()
            except OSError:
                skipped_io_error_count += 1
                continue
            if resolved != self.workspace_root and self.workspace_root not in resolved.parents:
                skipped_outside_root_count += 1
                continue
            try:
                if not resolved.is_file():
                    continue
                byte_count = resolved.stat().st_size
            except OSError:
                skipped_io_error_count += 1
                continue
            if files_examined_count >= max_files:
                skipped_max_files_count += 1
                continue
            files_examined_count += 1
            if byte_count > max_bytes_per_file:
                skipped_too_large_count += 1
                continue
            try:
                text = resolved.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped_binary_count += 1
                continue
            except OSError:
                skipped_io_error_count += 1
                continue
            relative_path = _relative_workspace_path(self.workspace_root, resolved)
            path_channels = _match_channels(query=lowered_query, terms=normalized_query_terms, haystack=relative_path)
            content_channels = _match_channels(query=lowered_query, terms=normalized_query_terms, haystack=text)
            match_channels = tuple(
                dict.fromkeys(
                    [
                        *("filename_path" for _ in path_channels),
                        *("content" for _ in content_channels),
                        *(["normalized_terms"] if "normalized_terms" in {*path_channels, *content_channels} else []),
                    ]
                )
            )
            if not match_channels:
                continue
            matches.append(
                {
                    "path": relative_path,
                    "content_hash": text_hash(text),
                    "path_match": bool(path_channels),
                    "content_match": bool(content_channels),
                    "normalized_term_match": "normalized_terms" in {*path_channels, *content_channels},
                    "match_channels": match_channels,
                }
            )
        path_match_count = sum(1 for match in matches if match["path_match"])
        content_match_count = sum(1 for match in matches if match["content_match"])
        normalized_match_count = sum(1 for match in matches if match["normalized_term_match"])
        return (
            "completed",
            {
                "root": _relative_workspace_path(self.workspace_root, root),
                "query_hash": text_hash(query),
                "search_scope": {
                    "path": _relative_workspace_path(self.workspace_root, root),
                    "channels": ("filename_path", "content", "normalized_terms"),
                },
                "match_count": len(matches),
                "matches": tuple(matches[:20]),
                "path_match_count": path_match_count,
                "content_match_count": content_match_count,
                "normalized_term_match_count": normalized_match_count,
                "files_examined_count": files_examined_count,
                "skipped_outside_root_count": skipped_outside_root_count,
                "skipped_max_files_count": skipped_max_files_count,
                "skipped_too_large_count": skipped_too_large_count,
                "skipped_io_error_count": skipped_io_error_count,
                "skipped_binary_count": skipped_binary_count,
            },
            f"workspace search observed {len(matches)} matching files.",
        )


def _assert_workspace_authority(authority: MissionAuthorityEnvelope, workspace_root: Path) -> None:
    if "workspace" not in set(authority.allowed_tools):
        raise WorkspaceReadOnlyRuntimeError("workspace_tool_not_authorized")
    allowed_actions = set(authority.allowed_actions)
    if not {"workspace.list", "workspace.read", "workspace.search", "list", "read", "search"} & allowed_actions:
        raise WorkspaceReadOnlyRuntimeError("workspace_action_not_authorized")
    allowed_roots = []
    for item in authority.allowed_paths:
        try:
            allowed_roots.append(Path(item).resolve())
        except OSError:
            continue
    if workspace_root not in allowed_roots:
        raise WorkspaceReadOnlyRuntimeError("workspace_root_not_authorized")


def _resolve_workspace_path(root: Path, requested: str, *, must_exist: bool) -> Path:
    if not requested:
        raise WorkspaceReadOnlyRuntimeError("workspace_path_required")
    path = (root / requested).resolve()
    if path != root and root not in path.parents:
        raise WorkspaceReadOnlyRuntimeError("workspace_path_outside_root")
    if must_exist and not path.exists():
        raise WorkspaceReadOnlyRuntimeError("workspace_path_not_found")
    return path


def _relative_workspace_path(root: Path, path: Path) -> str:
    if path == root:
        return "."
    return path.relative_to(root).as_posix()


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _normalized_search_terms(text: str) -> tuple[str, ...]:
    normalized = _normalize_search_text(text)
    terms = [term for term in normalized.split(" ") if term]
    expanded = list(terms)
    for left, right in zip(terms, terms[1:], strict=False):
        if len(left) > 2 and len(right) > 2:
            expanded.append(f"{left[0]}{right[0]}")
    return tuple(dict.fromkeys(expanded))


def _normalize_search_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-.\\/]+", " ", text).lower()).strip()


def _match_channels(*, query: str, terms: tuple[str, ...], haystack: str) -> tuple[str, ...]:
    normalized_haystack = _normalize_search_text(haystack)
    haystack_terms = set(term for term in normalized_haystack.split(" ") if term)
    haystack_terms.update(_normalized_search_terms(normalized_haystack))
    channels: list[str] = []
    if query and query in haystack.lower():
        channels.append("exact")
    if terms and all(term in haystack_terms for term in terms):
        channels.append("normalized_terms")
    return tuple(channels)


__all__ = ["WorkspaceReadOnlyRuntime", "WorkspaceReadOnlyRuntimeError"]
