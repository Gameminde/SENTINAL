"""Task 13 / Requirement 13 — Event Bus Primitives Layer Extraction.

Structural tests that enforce the layering contract independent of any
individual test. These catch regressions where a future change to
``sentinel/shared/events.py`` or to an organ adapter would re-introduce
an upward dependency from organs to the cognitive layer.

CP-13.1 (Clean Layering):
    ∀ module M in sentinel/organs/: M does not import from sentinel/agent/
    (for EventBus / AgentEventType specifically; other legitimate cases
    such as ``sanitize_context_payload`` are allowed).

CP-13.2 (Backward Compat):
    ∀ existing import path: import still resolves during deprecation period.

This module also asserts that ``sentinel.shared.events`` itself does not
import from ``sentinel.agent.*`` anywhere in its transitive graph at
module-load time.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

import pytest


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SENTINEL_ROOT = _REPO_ROOT / "sentinel"
_ORGANS_ROOT = _SENTINEL_ROOT / "organs"
_SHARED_EVENTS = _SENTINEL_ROOT / "shared" / "events.py"


# ---------------------------------------------------------------------------
# CP-13.2 — old import paths still resolve
# ---------------------------------------------------------------------------


def test_old_event_import_paths_still_resolve() -> None:
    """Existing callers that do ``from sentinel.agent.event_bus import EventBus``
    or ``from sentinel.agent.events import AgentEventType`` must continue
    to work. Also the shims re-export the same class object as the new
    canonical location.
    """
    from sentinel.agent.event_bus import EventBus as LegacyEventBus
    from sentinel.agent.events import AgentEventType as LegacyAgentEventType
    from sentinel.agent.exceptions import TraceIntegrityError as LegacyTraceError
    from sentinel.agent.models import AgentEvent as LegacyAgentEvent
    from sentinel.agent.phases import AgentPhase as LegacyAgentPhase

    from sentinel.shared.events import (
        AgentEvent,
        AgentEventType,
        AgentPhase,
        EventBus,
        TraceIntegrityError,
    )

    # Same class object — no parallel implementations.
    assert LegacyEventBus is EventBus
    assert LegacyAgentEventType is AgentEventType
    assert LegacyTraceError is TraceIntegrityError
    assert LegacyAgentEvent is AgentEvent
    assert LegacyAgentPhase is AgentPhase


# ---------------------------------------------------------------------------
# CP-13.1 — no organ module imports EventBus / AgentEventType from
# ``sentinel.agent.event_bus`` or ``sentinel.agent.events``.
# ---------------------------------------------------------------------------


_FORBIDDEN_PATTERN = re.compile(
    r"^\s*from\s+sentinel\.agent\.(event_bus|events)\s+import", re.MULTILINE
)


def test_organs_do_not_import_agent_event_paths() -> None:
    """Static-import scan: every ``.py`` under ``sentinel/organs/`` is
    inspected for forbidden ``from sentinel.agent.event_bus`` or
    ``from sentinel.agent.events`` imports. If any adapter slips back
    into the legacy path, this test flags it and the layering contract
    is violated.
    """
    offenders: list[tuple[pathlib.Path, list[str]]] = []
    for source in _ORGANS_ROOT.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        bad_lines = _FORBIDDEN_PATTERN.findall(text)
        if bad_lines:
            offenders.append(
                (source.relative_to(_SENTINEL_ROOT), bad_lines)
            )
    assert offenders == [], (
        "Organs must import event primitives from sentinel.shared.events. "
        "Forbidden imports found in:\n"
        + "\n".join(f"  {path}: {matches!r}" for path, matches in offenders)
    )


# ---------------------------------------------------------------------------
# Shared events module isolation: shared/events.py must not statically
# import anything from sentinel.agent.*, sentinel.mission.*, or
# sentinel.organs.*.
# ---------------------------------------------------------------------------


def test_shared_events_does_not_import_agent_layer() -> None:
    """``sentinel.shared.events`` is the canonical downward-facing layer.
    It MUST NOT import from ``sentinel.agent``, ``sentinel.mission``, or
    ``sentinel.organs`` — those are upward-facing layers.

    Parses the module AST so the check is robust to comments and
    conditional imports.
    """
    source = _SHARED_EVENTS.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(_SHARED_EVENTS))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            if (
                node.module.startswith("sentinel.agent")
                or node.module.startswith("sentinel.mission")
                or node.module.startswith("sentinel.organs")
            ):
                offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (
                    alias.name.startswith("sentinel.agent")
                    or alias.name.startswith("sentinel.mission")
                    or alias.name.startswith("sentinel.organs")
                ):
                    offenders.append(f"line {node.lineno}: import {alias.name}")
    assert offenders == [], (
        "sentinel.shared.events must not import from sentinel.agent/"
        "sentinel.mission/sentinel.organs. Offending imports:\n"
        + "\n".join(f"  {x}" for x in offenders)
    )


# ---------------------------------------------------------------------------
# Import the shared events module under a fresh module cache slot and
# confirm no upward module was loaded transitively as a side effect.
# ---------------------------------------------------------------------------


def test_shared_events_import_does_not_pull_agent_or_mission_or_organs() -> None:
    """Importing ``sentinel.shared.events`` in isolation must not load
    any ``sentinel.agent.*``, ``sentinel.mission.*``, or
    ``sentinel.organs.*`` module.

    This goes beyond the AST check — it also guards against transitive
    imports (e.g. if ``shared/events.py`` imported a module that itself
    imported an agent module).
    """
    # Snapshot modules that happen to be loaded from prior tests, then
    # re-import shared.events fresh and check that it did not add any
    # upward-layer modules.
    upward_prefixes = ("sentinel.agent.", "sentinel.mission.", "sentinel.organs.")
    before = {
        name for name in sys.modules
        if any(name.startswith(pref) for pref in upward_prefixes)
    }

    # Ensure a clean reload path for shared.events without touching the
    # upward modules pytest has already loaded.
    sys.modules.pop("sentinel.shared.events", None)
    import importlib

    importlib.import_module("sentinel.shared.events")

    after = {
        name for name in sys.modules
        if any(name.startswith(pref) for pref in upward_prefixes)
    }
    # Only modules that were already loaded before the re-import may be
    # present. If shared.events transitively imported an upward module
    # that was not already loaded, ``after - before`` would be non-empty.
    newly_loaded = after - before
    assert newly_loaded == set(), (
        "Importing sentinel.shared.events should not transitively load any "
        f"upward layer module; it loaded: {sorted(newly_loaded)!r}"
    )


# ---------------------------------------------------------------------------
# Shim sanity: an organ that uses only the new shared import path can
# construct and exercise EventBus end-to-end with Task 7 semantics intact.
# ---------------------------------------------------------------------------


def test_shared_events_bus_append_and_chain_after_extraction() -> None:
    """End-to-end: the moved EventBus still builds a hash-chain and still
    raises ``TraceIntegrityError`` on per-append tampering.
    """
    from sentinel.shared.events import (
        AgentEventType,
        AgentPhase,
        EventBus,
        TraceIntegrityError,
    )

    bus = EventBus("mission_layer_extract")
    first = bus.append(
        AgentEventType.AGENT_INITIALIZED,
        "Initialized.",
        phase_after=AgentPhase.INITIALIZED,
    )
    second = bus.append(AgentEventType.CONTEXT_BUILT, "Context.")
    assert second.previous_hash == first.event_hash
    assert bus.verify_chain() is True

    # Tamper a prior event; next append must raise.
    bus._events[0] = first.model_copy(update={"summary": "tampered"})
    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.AGENT_BLOCKED, "after tamper")
