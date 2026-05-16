"""Mission-layer exceptions.

Task 4 / Requirement 4 (F-A3.10) — reactive kill-switch interruption.

``MissionRevokedException`` is raised inside :meth:`MissionRunner.run_mission`
when the authority envelope's ``revoked_at`` stamp appears or when a shared
:class:`sentinel.mission.cancellation.CancellationToken` has been cancelled.
The runner catches it and returns a structured :class:`MissionRunResult`
with ``state.status = MissionStatus.REVOKED`` so the doctrine property
holds:

    ∀ revoke event R at time T:
        no plan step initiated after T completes successfully.

Task 12 / Requirement 12 (R4) — MissionRunner exception reform.

``BrowserOperatorRouteRejected`` replaces the previous string-encoded
``ValueError(f"browser_operator_route_rejected:{reason}")`` in
:meth:`MissionRunner._execute_browser_operator_route`. The structured
exception carries three fields (``reason``, ``context``, and
``original_exception``) so callers can reason about the rejection
without regex-parsing a message, while still preserving the original
stack trace via ``raise ... from original_exc``. Subclasses
:class:`ValueError` so any legacy ``except ValueError`` site continues
to intercept the rejection untouched.
"""

from __future__ import annotations

from typing import Any


class MissionRevokedException(RuntimeError):
    """Raised when a mission run is interrupted by authority revocation.

    The canonical code surfaced in the error message is ``mission_revoked``.
    """


class BrowserOperatorRouteRejected(ValueError):
    """Raised when the browser operator route rejects a mission action.

    Task 12 / R4 / F-A2.7-adjacent — structured replacement for the
    previous ``ValueError(f"browser_operator_route_rejected:{reason}")``
    string encoding. Carries three structured fields:

    * ``reason`` (str) — the machine-readable rejection code surfaced by
      :meth:`BrowserOperatorMissionRouteProtocol.run_mission_action`
      via its ``result["reason"]`` key. Never the empty string; a
      caller that omits the reason gets a synthetic ``"unspecified"``.
    * ``context`` (dict) — structured metadata attached to the
      rejection (mission id, action id, capture root, etc.). Never
      ``None``; a caller that omits context gets an empty dict so
      downstream code can do ``exc.context.get(...)`` unconditionally.
    * ``original_exception`` (Exception | None) — the upstream
      exception, if this rejection was triggered by a nested failure.
      The canonical way to preserve the stack trace is also
      ``raise BrowserOperatorRouteRejected(...) from original_exc``;
      ``original_exception`` mirrors the same value for programmatic
      access without walking ``__cause__``.

    Subclasses :class:`ValueError` so legacy ``except ValueError`` sites
    (if any exist outside the mission runner) continue to work; new
    code SHOULD catch :class:`BrowserOperatorRouteRejected` explicitly
    to distinguish route rejections from other validation failures.
    """

    def __init__(
        self,
        *,
        reason: str,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ) -> None:
        self.reason = reason if reason else "unspecified"
        self.context: dict[str, Any] = dict(context) if context else {}
        self.original_exception = original_exception
        # The message preserves the legacy grep token
        # ``browser_operator_route_rejected`` so log dashboards/regexes
        # keyed on the old surface continue to find the event. Callers
        # that want structured access should read ``.reason`` /
        # ``.context`` instead of parsing the string.
        super().__init__(f"browser_operator_route_rejected:{self.reason}")
