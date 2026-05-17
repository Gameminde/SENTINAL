"""U12 Boundary-Detection Gate — sentinel-context-cache-runtime-closure (Task 0.2).

This module is **test-only**. It implements an in-process boundary-detection
scanner that the spec uses as a hard scope guardrail before any production
source is created or modified by waves >= 1.

Purpose
-------
The scanner enumerates the categories of diff that this closure spec is
forbidden from introducing. It runs over either:

  (a) a synthetic in-memory diff dict (each test below builds one), or
  (b) actual file contents under the working tree (the
      `test_no_denylist_terms_in_files_added_or_modified_by_this_spec`
      function below).

It is example-based only (no Hypothesis import) and lives ONLY inside this
test file — it is NOT added to any production package. See spec
`.kiro/specs/sentinel-context-cache-runtime-closure/`:

  - tasks.md §0.2
  - design.md §Boundary-Detection Gate Ordering (Pre-Production), §Final
    Review Checkpoint §3 (allowed file set)
  - requirements.md §Requirement 8 (hard scope guardrails)

Forbidden categories enumerated below
-------------------------------------
    p6u_namespace
    brain_science_namespace
    new_organ_subpackage
    mission_authority_field_change
    organ_authority_field_change
    regex_denylist_term
    new_agent_event_type_member
    new_required_build_parameter

Constraints honoured
--------------------
- No Hypothesis import.
- No `pytest.mark.slow`.
- No production import; the scanner is pure (no I/O outside the explicit
  working-tree test, no network, deterministic).
- No raw secrets, prompts, or payloads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pytest


# ---------------------------------------------------------------------------
# Constants — foundation-lock organ allow-list and reserved namespaces
# ---------------------------------------------------------------------------

# Foundation-lock organ subpackage set at commit
# 378d862310bc1b5939b210a49c04026cd99a860d. New subpackages outside this
# set are forbidden by Requirement 8.3.
_FOUNDATION_ORGAN_SUBPACKAGES: frozenset[str] = frozenset(
    {
        "browser",
        "channels",
        "desktop",
        "capital",
        "trading",
        "spend",
        "credentials",
        "external_api",
    }
)

# Existing flat module files under sentinel/organs/ at the foundation lock.
# Files of these names are NOT new subpackages.
_FOUNDATION_ORGAN_FLAT_MODULES: frozenset[str] = frozenset(
    {
        "__init__.py",
        "authority.py",
        "receipts.py",
        "contracts.py",
        "kill_switch.py",
        "dry_run.py",
        "replay.py",
        "risk.py",
        "promotion_gate.py",
        "real_world_gauntlet.py",
        "vendor_harvest.py",
        "registry.py",
        "exceptions.py",
        "lanes.py",
        "capability_frontier.py",
        "implementation_alignment.py",
        "reality_activation.py",
        "runtime_promotion.py",
    }
)

# Path prefix that anchors all reserved-namespace checks. Using a constant
# keeps the scanner POSIX-style and avoids OS-dependent separators.
_SENTINEL_CORE_ROOT = "sentinel-control/services/sentinel-core/sentinel"

# P6U-reserved namespace prefixes / patterns. Requirement 8.1.
_P6U_PATH_PREFIXES: tuple[str, ...] = (
    f"{_SENTINEL_CORE_ROOT}/p6u/",
)
_P6U_PATH_SUBSTRINGS: tuple[str, ...] = (
    "/p6u/",
    "/p6u_",
)
# Module-name prefix denylist (POSIX basename starts with `p6u_`).
_P6U_MODULE_PREFIX: str = "p6u_"

# Brain / Science reserved namespaces. Requirement 8.2.
_BRAIN_SCIENCE_PATH_PREFIXES: tuple[str, ...] = (
    f"{_SENTINEL_CORE_ROOT}/brain/",
    f"{_SENTINEL_CORE_ROOT}/science/",
)
_BRAIN_SCIENCE_PATH_SUBSTRINGS: tuple[str, ...] = (
    f"{_SENTINEL_CORE_ROOT}/brain/",
    f"{_SENTINEL_CORE_ROOT}/science/",
)

# Regex denylist tokens. Requirement 8.6 (case-insensitive substring).
_REGEX_DENYLIST_TOKENS: tuple[str, ...] = (
    "payment",
    "spend",
    "trading",
    "channel_send",
    "channel-send",
    "credential_secret",
    "credential-secret",
    "pay_invoice",
    "transfer_funds",
    "send_message_external",
)

# Foundation-lock authority-relevant field names on
# `MissionAuthorityEnvelope`. Requirement 8.5.
_MISSION_AUTHORITY_FIELD_NAMES: tuple[str, ...] = (
    "mission_type",
    "allowed_actions",
    "allowed_tools",
    "max_actions",
    "max_cost_usd",
    "mode",
    "expires_at",
    "revoked_at",
    "original_allowed_actions",
)

# Regex matching a Pydantic Field assignment inside a model class body.
_FIELD_ASSIGNMENT_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*:\s*.+=\s*Field\(")
# Regex matching a StrEnum-style member assignment.
_ENUM_MEMBER_RE = re.compile(r'^\s+[A-Z_][A-Z0-9_]*\s*=\s*["\']')
# Regex matching `def build(` and capturing the parameter list up to the
# matching `)`.
_DEF_BUILD_RE = re.compile(r"def\s+build\s*\(([^)]*)\)")

# Allow-list for organ files whose existing names already match a denylist
# token (per Requirement 8.6 allow-list). Only EXISTING files at the
# foundation lock are exempt; new files under these directories are not
# exempt by this allow-list (the new-organ-subpackage rule still applies).
_ORGAN_DENYLIST_ALLOWLIST_DIRS: tuple[str, ...] = (
    f"{_SENTINEL_CORE_ROOT}/organs/spend/",
    f"{_SENTINEL_CORE_ROOT}/organs/trading/",
    f"{_SENTINEL_CORE_ROOT}/organs/channels/",
    f"{_SENTINEL_CORE_ROOT}/organs/capital/",
    f"{_SENTINEL_CORE_ROOT}/organs/credentials/",
)

# Path of THIS test file relative to repo root. The test file references
# the literal denylist tokens (intentionally) and is allow-listed from the
# regex denylist scan so it does not self-trip.
_THIS_TEST_FILE_REL = (
    "sentinel-control/services/sentinel-core/tests/perf/test_scope_guardrails.py"
)


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileDiff:
    """Synthetic or working-tree-derived diff input for the scanner."""

    path: str
    is_new_file: bool
    added_text: str
    removed_text: str = ""


@dataclass(frozen=True)
class BoundaryViolation:
    """A single boundary crossing detected by `detect_boundary_crossings`."""

    path: str
    category: str
    detail: str


# ---------------------------------------------------------------------------
# Pure scanner — no I/O, deterministic
# ---------------------------------------------------------------------------


def _is_path_under(path: str, prefixes: Iterable[str]) -> bool:
    """Return True when ``path`` starts with any of ``prefixes``."""

    return any(path.startswith(p) for p in prefixes)


def _basename(path: str) -> str:
    """POSIX basename — last segment after the final ``/``."""

    return path.rsplit("/", 1)[-1]


def _detect_p6u_namespace(diff: FileDiff) -> BoundaryViolation | None:
    path = diff.path
    if _is_path_under(path, _P6U_PATH_PREFIXES):
        return BoundaryViolation(
            path=path,
            category="p6u_namespace",
            detail="path under reserved P6U prefix",
        )
    for sub in _P6U_PATH_SUBSTRINGS:
        if sub in path:
            return BoundaryViolation(
                path=path,
                category="p6u_namespace",
                detail=f"path contains reserved P6U segment {sub!r}",
            )
    if _basename(path).startswith(_P6U_MODULE_PREFIX) and path.endswith(".py"):
        return BoundaryViolation(
            path=path,
            category="p6u_namespace",
            detail="python module name starts with reserved P6U prefix",
        )
    return None


def _detect_brain_science_namespace(diff: FileDiff) -> BoundaryViolation | None:
    path = diff.path
    if _is_path_under(path, _BRAIN_SCIENCE_PATH_PREFIXES):
        return BoundaryViolation(
            path=path,
            category="brain_science_namespace",
            detail="path under reserved Brain/Science namespace",
        )
    for sub in _BRAIN_SCIENCE_PATH_SUBSTRINGS:
        if sub in path:
            return BoundaryViolation(
                path=path,
                category="brain_science_namespace",
                detail=f"path contains reserved Brain/Science segment {sub!r}",
            )
    return None


def _detect_new_organ_subpackage(diff: FileDiff) -> BoundaryViolation | None:
    path = diff.path
    organs_root = f"{_SENTINEL_CORE_ROOT}/organs/"
    if not path.startswith(organs_root):
        return None
    if not diff.is_new_file:
        return None
    remainder = path[len(organs_root) :]
    # A flat module file at organs/<file>.py is not a new subpackage.
    if "/" not in remainder:
        # Only flag if the flat file name is not one of the foundation
        # flat modules. New flat modules at organs/ are also forbidden by
        # this spec (no new module under organs/). Treat them as a new
        # subpackage-class violation for purposes of U12.
        if remainder not in _FOUNDATION_ORGAN_FLAT_MODULES:
            return BoundaryViolation(
                path=path,
                category="new_organ_subpackage",
                detail="new flat module under sentinel/organs/",
            )
        return None
    # remainder has the shape "<subdir>/..."; <subdir> must be in the
    # foundation organ set.
    subdir = remainder.split("/", 1)[0]
    if subdir not in _FOUNDATION_ORGAN_SUBPACKAGES:
        return BoundaryViolation(
            path=path,
            category="new_organ_subpackage",
            detail=f"new subpackage {subdir!r} not in foundation-lock organ set",
        )
    return None


def _diff_touches_authority_file(diff: FileDiff, authority_file: str) -> bool:
    """True when the diff path matches the given authority module."""

    return diff.path.endswith(authority_file)


def _detect_authority_field_change(
    diff: FileDiff, authority_file: str, category: str, field_names: Iterable[str]
) -> BoundaryViolation | None:
    if not _diff_touches_authority_file(diff, authority_file):
        return None
    text_blocks = (("added_text", diff.added_text), ("removed_text", diff.removed_text))
    for which, text in text_blocks:
        if not text:
            continue
        # Direct mention of a known authority field name in any added or
        # removed line.
        for name in field_names:
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(f"{name}:") or stripped.startswith(f"{name} =") or stripped.startswith(f"{name}="):
                    return BoundaryViolation(
                        path=diff.path,
                        category=category,
                        detail=f"{which} touches authority field {name!r}",
                    )
        # Any new Field(...) assignment line inside the diff is treated as
        # a structural change.
        for line in text.splitlines():
            if _FIELD_ASSIGNMENT_RE.match(line):
                return BoundaryViolation(
                    path=diff.path,
                    category=category,
                    detail=f"{which} introduces a Pydantic Field(...) assignment",
                )
    return None


def _detect_mission_authority_field_change(diff: FileDiff) -> BoundaryViolation | None:
    return _detect_authority_field_change(
        diff,
        authority_file="sentinel/mission/models.py",
        category="mission_authority_field_change",
        field_names=_MISSION_AUTHORITY_FIELD_NAMES,
    )


def _detect_organ_authority_field_change(diff: FileDiff) -> BoundaryViolation | None:
    if not _diff_touches_authority_file(diff, "sentinel/organs/authority.py"):
        return None
    # OrganAuthorityEnvelope field names are not enumerated here; any
    # field-shaped addition or removal in this module is treated as a
    # change.
    for which, text in (("added_text", diff.added_text), ("removed_text", diff.removed_text)):
        if not text:
            continue
        for line in text.splitlines():
            if _FIELD_ASSIGNMENT_RE.match(line):
                return BoundaryViolation(
                    path=diff.path,
                    category="organ_authority_field_change",
                    detail=f"{which} introduces a Pydantic Field(...) assignment",
                )
    return None


def _is_path_allowlisted_for_denylist(path: str) -> bool:
    """True when this path is allow-listed from the regex-denylist scan."""

    if path.endswith(_THIS_TEST_FILE_REL):
        return True
    if path == _THIS_TEST_FILE_REL:
        return True
    return False


def _is_existing_organ_file_allowlisted(diff: FileDiff) -> bool:
    """True when the diff is on an EXISTING file under an allow-listed organ
    directory. New files under those directories are NOT exempt."""

    if diff.is_new_file:
        return False
    return _is_path_under(diff.path, _ORGAN_DENYLIST_ALLOWLIST_DIRS)


def _detect_regex_denylist_term(diff: FileDiff) -> BoundaryViolation | None:
    if _is_path_allowlisted_for_denylist(diff.path):
        return None
    if _is_existing_organ_file_allowlisted(diff):
        return None
    haystack = diff.added_text.lower()
    if not haystack:
        return None
    for token in _REGEX_DENYLIST_TOKENS:
        if token.lower() in haystack:
            return BoundaryViolation(
                path=diff.path,
                category="regex_denylist_term",
                detail=f"added_text contains denylist token {token!r}",
            )
    return None


def _detect_new_agent_event_type_member(diff: FileDiff) -> BoundaryViolation | None:
    if not diff.path.endswith("sentinel/shared/events.py"):
        return None
    if not diff.added_text:
        return None
    for line in diff.added_text.splitlines():
        if _ENUM_MEMBER_RE.match(line):
            return BoundaryViolation(
                path=diff.path,
                category="new_agent_event_type_member",
                detail="added enum-style member assignment in events.py",
            )
    return None


def _extract_def_build_param_list(text: str) -> str | None:
    """Return the `def build(` parameter list from the first match in
    ``text``, or None when no `def build(` line is present."""

    match = _DEF_BUILD_RE.search(text)
    if match is None:
        return None
    # Normalize whitespace so cosmetic reformatting does not trip.
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _detect_new_required_build_parameter(diff: FileDiff) -> BoundaryViolation | None:
    if not diff.path.endswith("sentinel/agent/context_builder.py"):
        return None
    added_params = _extract_def_build_param_list(diff.added_text)
    removed_params = _extract_def_build_param_list(diff.removed_text)
    if added_params is None and removed_params is None:
        return None
    if added_params != removed_params:
        return BoundaryViolation(
            path=diff.path,
            category="new_required_build_parameter",
            detail="def build(...) parameter list changed",
        )
    return None


_DETECTORS = (
    _detect_p6u_namespace,
    _detect_brain_science_namespace,
    _detect_new_organ_subpackage,
    _detect_mission_authority_field_change,
    _detect_organ_authority_field_change,
    _detect_regex_denylist_term,
    _detect_new_agent_event_type_member,
    _detect_new_required_build_parameter,
)


def detect_boundary_crossings(diffs: list[FileDiff]) -> list[BoundaryViolation]:
    """Return the list of boundary violations across all input diffs.

    Pure: no I/O, no network, deterministic. Each detector inspects one
    diff at a time and returns at most one violation for that diff. The
    output preserves input order.
    """

    violations: list[BoundaryViolation] = []
    for diff in diffs:
        for detector in _DETECTORS:
            v = detector(diff)
            if v is not None:
                violations.append(v)
                # One detector per diff is sufficient — first match wins
                # so the gate halts deterministically on the most specific
                # category.
                break
    return violations


# ---------------------------------------------------------------------------
# Synthetic-diff tests — every test asserts `detect_boundary_crossings`
# returns at least one violation of the expected category.
# ---------------------------------------------------------------------------


def _categories(violations: list[BoundaryViolation]) -> set[str]:
    return {v.category for v in violations}


def test_gate_halts_on_p6u_namespace() -> None:
    diff = FileDiff(
        path=f"{_SENTINEL_CORE_ROOT}/p6u/scanner.py",
        is_new_file=True,
        added_text="def scan() -> None:\n    return None\n",
    )
    violations = detect_boundary_crossings([diff])
    assert "p6u_namespace" in _categories(violations), violations


def test_gate_halts_on_brain_namespace() -> None:
    diff = FileDiff(
        path=f"{_SENTINEL_CORE_ROOT}/brain/cortex.py",
        is_new_file=True,
        added_text="class Cortex:\n    pass\n",
    )
    violations = detect_boundary_crossings([diff])
    assert "brain_science_namespace" in _categories(violations), violations


def test_gate_halts_on_science_namespace() -> None:
    diff = FileDiff(
        path=f"{_SENTINEL_CORE_ROOT}/science/lab.py",
        is_new_file=True,
        added_text="class Lab:\n    pass\n",
    )
    violations = detect_boundary_crossings([diff])
    assert "brain_science_namespace" in _categories(violations), violations


def test_gate_halts_on_new_organ_subpackage() -> None:
    diff = FileDiff(
        path=f"{_SENTINEL_CORE_ROOT}/organs/wallet/__init__.py",
        is_new_file=True,
        added_text='"""wallet organ."""\n',
    )
    violations = detect_boundary_crossings([diff])
    assert "new_organ_subpackage" in _categories(violations), violations


def test_gate_halts_on_mission_authority_field_default_change() -> None:
    # Synthetic attempt to alter `allowed_actions` default on
    # MissionAuthorityEnvelope.
    diff = FileDiff(
        path="sentinel-control/services/sentinel-core/sentinel/mission/models.py",
        is_new_file=False,
        added_text="    allowed_actions: list[str] = Field(default_factory=lambda: [\"x\"])\n",
        removed_text="    allowed_actions: list[str] = Field(default_factory=list)\n",
    )
    violations = detect_boundary_crossings([diff])
    assert "mission_authority_field_change" in _categories(violations), violations


def test_gate_halts_on_organ_authority_field_change() -> None:
    diff = FileDiff(
        path="sentinel-control/services/sentinel-core/sentinel/organs/authority.py",
        is_new_file=False,
        added_text="    new_field: list[str] = Field(default_factory=list)\n",
        removed_text="",
    )
    violations = detect_boundary_crossings([diff])
    assert "organ_authority_field_change" in _categories(violations), violations


@pytest.mark.parametrize("token", _REGEX_DENYLIST_TOKENS)
def test_gate_halts_on_each_regex_denylist_term(token: str) -> None:
    # Synthetic diff against a runtime file (not the test file, not an
    # existing organ allow-listed directory) that adds a line containing
    # the denylist token. The added line is benign-looking source — the
    # gate fires solely on the literal substring.
    diff = FileDiff(
        path="sentinel-control/services/sentinel-core/sentinel/agent/runtime.py",
        is_new_file=False,
        added_text=f"# adding a forbidden term: {token} should be flagged\n",
        removed_text="",
    )
    violations = detect_boundary_crossings([diff])
    assert "regex_denylist_term" in _categories(violations), (token, violations)


def test_gate_halts_on_new_agent_event_type_member() -> None:
    # Synthetic addition of a fictional new member to AgentEventType.
    added = (
        "class AgentEventType(StrEnum):\n"
        '    NEW_FICTIONAL_EVENT = "new_fictional_event"\n'
    )
    diff = FileDiff(
        path="sentinel-control/services/sentinel-core/sentinel/shared/events.py",
        is_new_file=False,
        added_text=added,
        removed_text="",
    )
    violations = detect_boundary_crossings([diff])
    assert "new_agent_event_type_member" in _categories(violations), violations


def test_gate_halts_on_new_required_build_parameter() -> None:
    removed = (
        "    def build(self, envelope, *, user_input=None, evidence_refs=None,"
        " memory_items=None) -> AgentContext:\n"
    )
    added = (
        "    def build(self, envelope, *, user_input=None, evidence_refs=None,"
        " memory_items=None, cache_key_provider=None) -> AgentContext:\n"
    )
    diff = FileDiff(
        path="sentinel-control/services/sentinel-core/sentinel/agent/context_builder.py",
        is_new_file=False,
        added_text=added,
        removed_text=removed,
    )
    violations = detect_boundary_crossings([diff])
    assert "new_required_build_parameter" in _categories(violations), violations


def test_gate_does_not_halt_on_clean_diff() -> None:
    # Control case: a benign addition to the new module this spec creates
    # under sentinel/perf/caches/. Must produce zero violations.
    diff = FileDiff(
        path="sentinel-control/services/sentinel-core/sentinel/perf/caches/context_cache_key.py",
        is_new_file=True,
        added_text=(
            '"""ContextCacheKey module — closure spec, additive only."""\n'
            "from __future__ import annotations\n"
            "\n"
            "def _ok() -> bool:\n"
            "    return True\n"
        ),
        removed_text="",
    )
    violations = detect_boundary_crossings([diff])
    assert violations == [], violations


# ---------------------------------------------------------------------------
# Working-tree test — protects future waves
# ---------------------------------------------------------------------------


# The hard-coded list of paths THIS SPEC is allowed to touch, matching the
# allowed-file-set in design.md §Final Review Checkpoint §3.
_SPEC_ALLOWED_PATHS: tuple[str, ...] = (
    "sentinel-control/services/sentinel-core/sentinel/perf/caches/context_cache_key.py",
    "sentinel-control/services/sentinel-core/sentinel/perf/caches/__init__.py",
    "sentinel-control/services/sentinel-core/sentinel/agent/runtime.py",
    "sentinel-control/services/sentinel-core/tests/perf/test_scope_guardrails.py",
    "sentinel-control/docs/CURRENT_STATE_LOCK.md",
    "sentinel-control/docs/P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md",
)

# Paths inside the allowed set that legitimately reference the denylist
# tokens by name (this test file, the historical state-lock doc that
# enumerates the locked organs, and the implementation log that quotes
# the boundary rules verbatim). They are exempt from the working-tree
# regex scan; production source files in `_SPEC_ALLOWED_PATHS` are NOT
# exempt.
_WORKING_TREE_DENYLIST_ALLOWLIST: frozenset[str] = frozenset(
    {
        "sentinel-control/services/sentinel-core/tests/perf/test_scope_guardrails.py",
        "sentinel-control/docs/CURRENT_STATE_LOCK.md",
        "sentinel-control/docs/P_C_KEY_RUNTIME_CLOSURE_IMPLEMENTATION_LOG.md",
    }
)


def _repo_root() -> Path:
    """Resolve the repo root (the parent of `sentinel-control/`).

    This file lives at
        <repo>/sentinel-control/services/sentinel-core/tests/perf/test_scope_guardrails.py
    so the repo root is six parents up.
    """

    return Path(__file__).resolve().parents[5]


def _read_text_or_none(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return None
    except OSError:
        return None


def test_no_denylist_terms_in_files_added_or_modified_by_this_spec() -> None:
    """Working-tree gate: scan files this spec is allowed to touch and
    assert no denylist token appears in any of them (with allow-listed
    documentation/test files exempt).

    At Wave 0 the only files this spec has added are the implementation
    log doc and this test file itself — both allow-listed, so the
    assertion is trivially empty. As later waves add `context_cache_key.py`
    and edit `runtime.py` and `__init__.py`, this test will protect the
    closure work from accidentally introducing a denylist term.
    """

    root = _repo_root()
    diffs: list[FileDiff] = []
    for rel in _SPEC_ALLOWED_PATHS:
        if rel in _WORKING_TREE_DENYLIST_ALLOWLIST:
            continue
        path = root / rel
        text = _read_text_or_none(path)
        if text is None:
            # File does not exist yet at the current wave — that is fine.
            continue
        diffs.append(
            FileDiff(
                path=rel,
                is_new_file=False,
                added_text=text,
                removed_text="",
            )
        )

    violations = [
        v
        for v in detect_boundary_crossings(diffs)
        if v.category == "regex_denylist_term"
    ]
    assert violations == [], violations
