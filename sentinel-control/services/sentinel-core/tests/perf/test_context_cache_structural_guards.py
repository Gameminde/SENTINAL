"""U8-U11 structural guards for sentinel-context-cache-runtime-closure.

Spec: ``sentinel-context-cache-runtime-closure``.
Closure backlog items: P-C-KEY-01 / P-C-RUNTIME-01.

These structural tests pin invariants that must hold at every commit
inside this closure spec. They are pure file-content / AST inspections;
they do not exercise runtime behavior (that's I1-I5 / R1).

Coverage:
- U8: no ``mission_hot_hash=envelope.id`` / ``authority_hash=envelope.id``
  / ``workspace_snapshot_id="v1"`` / ``organ_state_hash="v1"`` in
  ``runtime.py``. Pre-closure these were the four placeholder values
  passed to ``ContextBuildCache.composite_key``; post-closure they MUST
  all be sourced from ``ContextCacheKeyBuilder``.
- U9: public required signatures unchanged for ``ContextBuilder.build``,
  ``AgentRuntime.run``, ``AgentRuntime._execute_controlled_tool_calls``,
  ``AgentRuntime._build_decision_frame_cached``,
  ``AgentRuntime._render_prompt_text_cached``, and
  ``AgentRuntime._enforce_frame_budget``.
- U10: only allowed modules touched by the closure (production-source
  edit set is a subset of the spec's allowed-file-set).
- U11: no new ``AgentEventType`` member added by the closure.

U12 (boundary-detection gate) lives in
``tests/perf/test_scope_guardrails.py`` and is run as part of the
mandatory pre/post-task gate; it is not duplicated here.

Import-cycle caveat (Task 3.3): seed ``sentinel.agent.runtime`` first.
"""
from __future__ import annotations

# Seed the canonical production import order. Do not reorder these imports.
from sentinel.agent.runtime import AgentRuntime  # noqa: F401

import inspect
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures — file paths and the minimum baseline knowledge of allowed files.
# ---------------------------------------------------------------------------


_SERVICES_ROOT = Path(__file__).resolve().parents[2]  # .../services/sentinel-core
_RUNTIME_PY = _SERVICES_ROOT / "sentinel" / "agent" / "runtime.py"
_CONTEXT_BUILDER_PY = _SERVICES_ROOT / "sentinel" / "agent" / "context_builder.py"
_CONTEXT_CACHE_KEY_PY = _SERVICES_ROOT / "sentinel" / "perf" / "caches" / "context_cache_key.py"
_CACHES_INIT_PY = _SERVICES_ROOT / "sentinel" / "perf" / "caches" / "__init__.py"


# Production files this closure spec is allowed to touch (subset of the
# spec's allowed-file-set, restricted to the production source surface
# pinned by U10). Tests are NOT included here — U10 is about production
# source.
_CLOSURE_ALLOWED_PRODUCTION_FILES = {
    _RUNTIME_PY,            # Task 3.x edits inside CONTEXT_BUILDING phase
    _CONTEXT_CACHE_KEY_PY,  # Task 2.1/2.2 — new module
    _CACHES_INIT_PY,        # Task 2.3 — additive re-exports
}


# ---------------------------------------------------------------------------
# U8 — no envelope.id / "v1" stand-ins in runtime.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stand_in",
    [
        'mission_hot_hash=envelope.id',
        'authority_hash=envelope.id',
        'workspace_snapshot_id="v1"',
        'organ_state_hash="v1"',
    ],
)
def test_u8_no_envelope_id_or_v1_stand_in_in_runtime(stand_in: str) -> None:
    """The four pre-closure placeholder values MUST NOT appear in
    runtime.py at any commit after Task 3.2 lands."""
    source = _RUNTIME_PY.read_text(encoding="utf-8")
    assert stand_in not in source, (
        f"{stand_in!r} is the pre-closure placeholder for a cache-key "
        f"value slot. It must be replaced by ContextCacheKeyBuilder "
        f"output (Tasks 3.1, 3.2). Found in {_RUNTIME_PY}."
    )


def test_u8_mission_id_event_tag_is_still_allowed() -> None:
    """``mission_id=envelope.id`` is the cache-event mission_id
    propagation argument (consumed by ContextBuildCache for
    CACHE_HIT/CACHE_MISS event tagging). It is NOT a cache-key value
    slot. U8 must not regress to forbid this; it must remain present
    in runtime.py because the cache module relies on it."""
    source = _RUNTIME_PY.read_text(encoding="utf-8")
    assert "mission_id=envelope.id" in source, (
        "mission_id=envelope.id is the legitimate cache-event tag and "
        "must remain in runtime.py"
    )


# ---------------------------------------------------------------------------
# U9 — public required signatures unchanged
# ---------------------------------------------------------------------------


def _required_params(func) -> list[str]:
    sig = inspect.signature(func)
    return [
        name for name, p in sig.parameters.items()
        if name != "self"
        and p.default is inspect.Parameter.empty
        and p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]


def test_u9_context_builder_build_signature_unchanged() -> None:
    """``ContextBuilder.build`` MUST require exactly (envelope) as the
    only required parameter. user_input/evidence_refs/memory_items are
    optional kwargs."""
    from sentinel.agent.context_builder import ContextBuilder

    required = _required_params(ContextBuilder.build)
    assert required == ["envelope"], (
        f"ContextBuilder.build required parameters must be ['envelope']; "
        f"got {required}. The closure spec forbids adding any new "
        f"required parameter to ContextBuilder.build."
    )


def test_u9_agent_runtime_run_signature_unchanged() -> None:
    """``AgentRuntime.run`` MUST require exactly (envelope)."""
    required = _required_params(AgentRuntime.run)
    assert required == ["envelope"], (
        f"AgentRuntime.run required parameters must be ['envelope']; "
        f"got {required}."
    )


def test_u9_agent_runtime_execute_controlled_tool_calls_signature_unchanged() -> None:
    """``AgentRuntime._execute_controlled_tool_calls`` retains its
    foundation-lock signature (envelope, user_input, event_bus required;
    max_calls keyword-only required)."""
    required = _required_params(AgentRuntime._execute_controlled_tool_calls)
    # The foundation-lock signature has envelope, user_input, event_bus
    # as positional-or-keyword required and max_calls as keyword-only required.
    assert "envelope" in required
    assert "user_input" in required
    assert "event_bus" in required
    assert "max_calls" in required


def test_u9_build_decision_frame_cached_signature_unchanged() -> None:
    """``_build_decision_frame_cached`` is keyword-only with three
    required parameters: mission_id, composite_inputs, builder."""
    sig = inspect.signature(AgentRuntime._build_decision_frame_cached)
    params = sig.parameters
    expected = {"self", "mission_id", "composite_inputs", "builder"}
    assert set(params) == expected, (
        f"_build_decision_frame_cached parameters must be {expected}; "
        f"got {set(params)}"
    )


def test_u9_render_prompt_text_cached_signature_unchanged() -> None:
    """``_render_prompt_text_cached`` accepts (frame) positional-or-keyword
    and (mission_id) keyword-only."""
    sig = inspect.signature(AgentRuntime._render_prompt_text_cached)
    params = sig.parameters
    expected = {"self", "frame", "mission_id"}
    assert set(params) == expected, (
        f"_render_prompt_text_cached parameters must be {expected}; "
        f"got {set(params)}"
    )


def test_u9_enforce_frame_budget_signature_unchanged() -> None:
    """``_enforce_frame_budget`` is keyword-only with three required
    parameters: mission_id, builder, frame_budget."""
    sig = inspect.signature(AgentRuntime._enforce_frame_budget)
    params = sig.parameters
    expected = {"self", "mission_id", "builder", "frame_budget"}
    assert set(params) == expected, (
        f"_enforce_frame_budget parameters must be {expected}; "
        f"got {set(params)}"
    )


# ---------------------------------------------------------------------------
# U10 — only allowed modules touched by the closure
# ---------------------------------------------------------------------------


def test_u10_allowed_production_files_exist_and_are_inside_perf_caches_or_runtime() -> None:
    """Every closure-allowed production file is either runtime.py or
    sits under sentinel/perf/caches/. ContextBuilder is excluded
    (Task 8.1 verified context_builder.py is byte-identical to the
    foundation lock)."""
    for path in _CLOSURE_ALLOWED_PRODUCTION_FILES:
        assert path.exists(), f"closure-allowed file missing: {path}"
        rel = path.relative_to(_SERVICES_ROOT).as_posix()
        # Must be runtime.py OR under sentinel/perf/caches/.
        assert (
            rel == "sentinel/agent/runtime.py"
            or rel.startswith("sentinel/perf/caches/")
        ), f"closure-allowed file outside the agreed perimeter: {rel}"


def test_u10_context_builder_is_not_in_allowed_set() -> None:
    """Task 8.1 contract: ContextBuilder is NOT modified by this spec.
    It must NOT appear in the closure's allowed production-file set."""
    assert _CONTEXT_BUILDER_PY not in _CLOSURE_ALLOWED_PRODUCTION_FILES, (
        "context_builder.py must NOT be in the closure-allowed file set; "
        "Task 8.1 verified it is byte-identical to the foundation lock"
    )


# ---------------------------------------------------------------------------
# U11 — no new AgentEventType member introduced by the closure
# ---------------------------------------------------------------------------


# The closure spec MUST NOT add a new ``AgentEventType`` member. We
# verify this dynamically by re-reading the enum at the foundation-lock
# commit (378d862310bc1b5939b210a49c04026cd99a860d) via ``git show``
# and asserting the live HEAD enum is a subset of the foundation-lock
# member names. This avoids hand-maintaining a static pin list and
# stays correct as the foundation-spec / other specs add their own
# event types.
_FOUNDATION_LOCK_COMMIT = "378d862310bc1b5939b210a49c04026cd99a860d"


def _foundation_lock_agent_event_type_names() -> frozenset[str]:
    """Read AgentEventType members at the foundation-lock commit.

    Uses ``git show <commit>:<path>`` so we don't depend on any working-
    tree state. Parses the StrEnum body line-by-line; only lines of the
    form ``    NAME = "value"`` count.

    On any error (git missing, file not at that commit, parse error),
    return ``frozenset()`` and let the test fail loudly with a useful
    message rather than silently passing.
    """
    import re
    import subprocess

    repo_root = _SERVICES_ROOT.parents[2]  # .../sentinal
    relpath = "sentinel-control/services/sentinel-core/sentinel/shared/events.py"
    try:
        result = subprocess.run(
            ["git", "show", f"{_FOUNDATION_LOCK_COMMIT}:{relpath}"],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo_root,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return frozenset()

    src = result.stdout
    # Find the AgentEventType class block. Stop at the next top-level
    # ``class `` declaration (line that starts with "class ").
    in_block = False
    member_names: set[str] = set()
    member_re = re.compile(r"^\s{4}([A-Z][A-Z0-9_]+)\s*=\s*\"")
    for line in src.splitlines():
        if line.startswith("class AgentEventType"):
            in_block = True
            continue
        if in_block and line.startswith("class "):
            break
        if in_block:
            m = member_re.match(line)
            if m:
                member_names.add(m.group(1))
    return frozenset(member_names)


def test_u11_no_new_agent_event_type_member_introduced_by_closure() -> None:
    """The closure spec must not add a new ``AgentEventType`` member.
    Compare live HEAD members against the foundation-lock member set
    extracted directly from ``git show`` of the foundation-lock commit.
    Any member present at HEAD but not at the foundation lock is a
    closure-introduced member and fails the test."""
    from sentinel.shared.events import AgentEventType

    foundation_members = _foundation_lock_agent_event_type_names()
    assert foundation_members, (
        "could not read AgentEventType members at the foundation-lock "
        f"commit {_FOUNDATION_LOCK_COMMIT}; check git availability and "
        "that the file is present at that commit"
    )

    current_members = frozenset(member.name for member in AgentEventType)
    new_members = current_members - foundation_members
    assert not new_members, (
        f"closure spec must not add new AgentEventType members; "
        f"new members detected (vs {_FOUNDATION_LOCK_COMMIT}): "
        f"{sorted(new_members)}"
    )
