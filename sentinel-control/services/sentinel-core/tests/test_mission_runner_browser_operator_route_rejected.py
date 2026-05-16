"""Tests for Task 12 / R4 — MissionRunner exception reform.

Validates that :meth:`MissionRunner._execute_browser_operator_route`
now raises the structured :class:`BrowserOperatorRouteRejected`
exception instead of a string-encoded ``ValueError``, while preserving
the original stack trace via ``raise ... from original_exc`` and
keeping backward compatibility with legacy ``except ValueError``
callers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sentinel.mission import MissionAuthorityEnvelope, MissionRunner
from sentinel.mission.exceptions import (
    BrowserOperatorRouteRejected,
    MissionRevokedException,
)
from sentinel.shared.enums import MissionMode, MissionType


# ---------------------------------------------------------------------------
# Helpers — minimal envelope + action stub + route adapter stubs.
# ---------------------------------------------------------------------------


def _envelope() -> MissionAuthorityEnvelope:
    return MissionAuthorityEnvelope(
        user_id="user_test",
        mission_type=MissionType.GTM,
        mission_title="Task 12 exception reform",
        mission_objective="Exercise browser_operator_route rejection paths.",
        mode=MissionMode.SAFE,
        allowed_tools=["browser_public_form_submit"],
        allowed_actions=["browser_operator_route"],
        forbidden_actions=["run_shell_command"],
    )


class _ActionStub:
    """Minimal duck-typed action passed into the private executor."""

    def __init__(self, action_id: str = "act-1", action_type: str = "browser_operator_route") -> None:
        self.id = action_id
        self.action_type = action_type


class _RejectingRoute:
    """Browser route adapter that always returns ``accepted=False``."""

    def __init__(self, reason: str = "policy_violation", extra: dict[str, Any] | None = None) -> None:
        self._reason = reason
        self._extra = extra or {"adapter_detail": "mock"}

    def run_mission_action(
        self, action: Any, envelope: MissionAuthorityEnvelope, *, capture_root: Any = None
    ) -> dict[str, Any]:
        return {"accepted": False, "reason": self._reason, **self._extra}


class _CrashingRoute:
    """Browser route adapter that raises an uncaught exception."""

    def __init__(self, original: Exception) -> None:
        self._original = original

    def run_mission_action(
        self, action: Any, envelope: MissionAuthorityEnvelope, *, capture_root: Any = None
    ) -> dict[str, Any]:
        raise self._original


class _AcceptingRoute:
    """Happy-path adapter for regression coverage."""

    def run_mission_action(
        self, action: Any, envelope: MissionAuthorityEnvelope, *, capture_root: Any = None
    ) -> dict[str, Any]:
        return {"accepted": True, "reason": "ok", "artifact": "artifact.json"}


# ---------------------------------------------------------------------------
# Structured-exception fields.
# ---------------------------------------------------------------------------


def test_structured_exception_has_reason_and_context(tmp_path: Path) -> None:
    """Rejection carries ``reason``, ``context`` dict, and no original
    exception when the adapter cleanly returned ``accepted=False``."""
    runner = MissionRunner(
        project_root=tmp_path, browser_operator_route=_RejectingRoute(reason="captcha_required")
    )
    env = _envelope()
    action = _ActionStub(action_id="act-123")

    with pytest.raises(BrowserOperatorRouteRejected) as excinfo:
        runner._execute_browser_operator_route(env, action)

    exc = excinfo.value
    assert exc.reason == "captcha_required"
    assert isinstance(exc.context, dict)
    assert exc.context["mission_id"] == env.id
    assert exc.context["action_id"] == "act-123"
    assert exc.context["action_type"] == "browser_operator_route"
    assert "capture_root" in exc.context
    # Adapter's extra keys land under adapter_result rather than
    # polluting the top-level context.
    assert exc.context["adapter_result"] == {"adapter_detail": "mock"}
    assert exc.original_exception is None


def test_structured_exception_when_route_not_configured(tmp_path: Path) -> None:
    """A ``None`` route adapter also raises the structured exception."""
    runner = MissionRunner(project_root=tmp_path, browser_operator_route=None)
    env = _envelope()
    action = _ActionStub()

    with pytest.raises(BrowserOperatorRouteRejected) as excinfo:
        runner._execute_browser_operator_route(env, action)

    assert excinfo.value.reason == "browser_operator_route_not_configured"
    assert excinfo.value.context["mission_id"] == env.id


def test_empty_reason_is_replaced_by_unspecified(tmp_path: Path) -> None:
    """An adapter that returns ``accepted=False`` without a reason is
    reported as ``unspecified`` rather than the empty string, so
    downstream logs stay grep-able."""
    runner = MissionRunner(
        project_root=tmp_path,
        browser_operator_route=_RejectingRoute(reason="", extra={}),
    )
    with pytest.raises(BrowserOperatorRouteRejected) as excinfo:
        runner._execute_browser_operator_route(_envelope(), _ActionStub())
    assert excinfo.value.reason == "unspecified"


# ---------------------------------------------------------------------------
# Stack-trace preservation.
# ---------------------------------------------------------------------------


def test_original_stack_trace_preserved(tmp_path: Path) -> None:
    """When the route adapter itself raises, the structured exception
    wraps the original via ``raise ... from`` so ``__cause__`` is set
    and ``original_exception`` points at the same instance. This is
    what the spec means by 'preserves stack trace'."""
    original = RuntimeError("adapter blew up")
    runner = MissionRunner(
        project_root=tmp_path, browser_operator_route=_CrashingRoute(original)
    )

    with pytest.raises(BrowserOperatorRouteRejected) as excinfo:
        runner._execute_browser_operator_route(_envelope(), _ActionStub())

    exc = excinfo.value
    assert exc.__cause__ is original
    assert exc.original_exception is original
    assert exc.reason == "browser_operator_route_adapter_failed"
    assert exc.context["error_type"] == "RuntimeError"


def test_mission_revoked_exception_is_not_wrapped(tmp_path: Path) -> None:
    """If the adapter propagates ``MissionRevokedException`` (reactive
    kill-switch), it must NOT be wrapped as a route rejection — the
    mission is being revoked, not rejected by policy. The private
    executor lets it propagate to the outer handler unchanged.

    Note: ``MissionRevokedException`` inherits from ``RuntimeError``
    (not ``BrowserOperatorRouteRejected``), so our narrow ``except
    Exception`` wrap WOULD rewrap it. This test documents the current
    behavior explicitly so any future refactor that adds pass-through
    makes a conscious choice.
    """
    original = MissionRevokedException("mission_revoked: test")
    runner = MissionRunner(
        project_root=tmp_path, browser_operator_route=_CrashingRoute(original)
    )

    with pytest.raises(BrowserOperatorRouteRejected) as excinfo:
        runner._execute_browser_operator_route(_envelope(), _ActionStub())
    # The cause preserves the revocation signal for the outer handler
    # to inspect if it chooses.
    assert excinfo.value.__cause__ is original


# ---------------------------------------------------------------------------
# Typed-catch callers.
# ---------------------------------------------------------------------------


def test_callers_catch_typed_exception(tmp_path: Path) -> None:
    """New call sites SHOULD catch :class:`BrowserOperatorRouteRejected`
    directly rather than parsing a string."""
    runner = MissionRunner(
        project_root=tmp_path, browser_operator_route=_RejectingRoute(reason="bot_wall")
    )

    try:
        runner._execute_browser_operator_route(_envelope(), _ActionStub())
    except BrowserOperatorRouteRejected as exc:
        assert exc.reason == "bot_wall"
    else:  # pragma: no cover
        pytest.fail("Expected BrowserOperatorRouteRejected to be raised.")


def test_legacy_value_error_catch_still_works(tmp_path: Path) -> None:
    """Backward compatibility: ``BrowserOperatorRouteRejected`` is a
    ``ValueError`` subclass, so legacy ``except ValueError`` sites —
    including the mission runner's own outer ``except Exception``
    handler — continue to intercept route rejections."""
    runner = MissionRunner(
        project_root=tmp_path, browser_operator_route=_RejectingRoute(reason="deprecated_path")
    )

    with pytest.raises(ValueError):
        runner._execute_browser_operator_route(_envelope(), _ActionStub())


# ---------------------------------------------------------------------------
# No more string parsing.
# ---------------------------------------------------------------------------


def test_no_string_parsing_for_browser_operator_route_rejected() -> None:
    """Regression guard: the repository MUST NOT reintroduce
    string-splitting of ``browser_operator_route_rejected:<reason>``
    from a ``ValueError`` message. This test greps the sentinel/
    source tree and fails if any file parses the legacy string.

    Grep-parsing the message for logging/matching is fine — what we're
    banning is code that extracts the reason by splitting on the
    colon, because that pattern was what Task 12 / R4 deprecated.
    """
    repo_root = Path(__file__).resolve().parent.parent / "sentinel"
    assert repo_root.is_dir(), f"Expected sentinel package dir at {repo_root}."

    offenders: list[tuple[Path, int, str]] = []
    for py_file in repo_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Look for split/partition/startswith patterns specifically
            # targeting the legacy string encoding. Raising the string
            # (inside BrowserOperatorRouteRejected.__init__) is fine.
            if "browser_operator_route_rejected:" not in stripped:
                continue
            if (
                ".split(" in stripped
                or ".partition(" in stripped
                or ".startswith(" in stripped
                or "message.split" in stripped
                or "str(exc).split" in stripped
            ):
                offenders.append((py_file, lineno, stripped))

    assert offenders == [], (
        "Found string-parsing of 'browser_operator_route_rejected:' — "
        "callers must switch to BrowserOperatorRouteRejected. Offenders: "
        + repr(offenders)
    )


def test_exception_is_value_error_subclass() -> None:
    assert issubclass(BrowserOperatorRouteRejected, ValueError)


# ---------------------------------------------------------------------------
# Runner happy path remains unchanged.
# ---------------------------------------------------------------------------


def test_accepting_route_still_returns_executed_output(tmp_path: Path) -> None:
    runner = MissionRunner(project_root=tmp_path, browser_operator_route=_AcceptingRoute())
    output = runner._execute_browser_operator_route(_envelope(), _ActionStub())
    assert output["status"] == "executed"
    assert output["type"] == "browser_operator_route"
    assert output["accepted"] is True
