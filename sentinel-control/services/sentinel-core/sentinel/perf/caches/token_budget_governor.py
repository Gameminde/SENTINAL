"""TokenBudgetGovernor — hard token limits at frame, action, and mission scope.

Task 6.4 / sentinel-performance-runtime-foundation.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9.

Scope summary
-------------

This module provides :class:`TokenBudgetGovernor`, the cognitive cycle's
single source of truth for token-budget enforcement. The governor is
deliberately stateless about the *contents* of frames or actions — it
only tracks integer token counters per mission, decides accept/reject,
and emits budget events on the existing :class:`EventBus`. The concrete
:class:`ContextCompressor` and :class:`LLMDecisionFrame` types are
*never* imported here; both arrive as parameters so the governor stays
decoupled from the cognitive layer it governs (Task 6.11 wires the
real types in at the call site).

Three enforcement scopes
------------------------

* **Per-frame** (Requirements 10.1, 10.2, 10.3): :meth:`enforce_frame`
  builds the candidate frame and re-estimates token count after each
  ``compressor.compress`` pass. The compressor is invoked **at most**
  :attr:`max_compression_passes` times (default ``3``). If the frame
  still exceeds ``frame_budget`` after the configured number of
  passes, the frame is rejected and ``BUDGET_EXCEEDED`` is emitted
  with ``scope="frame"``.

* **Per-action** (Requirements 10.4, 10.5): :meth:`enforce_action`
  performs a pre-execution check. If the action's estimated token
  count exceeds ``action_budget``, the call is rejected before any
  organ-side work runs and ``BUDGET_EXCEEDED`` is emitted with
  ``scope="action"``. If the mission is already exhausted, the call
  is rejected with ``BUDGET_EXHAUSTED`` and ``reason="mission_exhausted"``.

* **Per-mission** (Requirements 10.6, 10.7, 10.8): :meth:`enforce_mission`
  records ``tokens_just_spent`` against the mission's cumulative
  counter and decides:

    - if cumulative crosses the warning threshold (default ``0.9``)
      for the first time — emit ``BUDGET_WARNING`` exactly once;
    - if cumulative reaches or exceeds ``mission_budget`` — mark the
      mission exhausted and emit ``BUDGET_EXHAUSTED`` exactly once.

  In-flight calls (tracked by :meth:`begin_call` / :meth:`end_call`)
  are allowed to finish; only **new** calls are blocked, by the
  ``mission_exhausted`` short-circuit in :meth:`enforce_action`
  (Requirement 10.7 explicit wording: "block new model calls for
  that mission … allow in-flight model calls to complete without
  cancellation").

Edge case — exactly 90 %
------------------------

The warning fires when ``tokens_spent >= warning_threshold * mission_budget``
(default ``0.9``) **AND** the mission's previous cumulative spent was
``< warning_threshold * mission_budget``. A mission that lands exactly
on the threshold (``cumulative == 0.9 * mission_budget``) **does** cross
the threshold; the comparison is ``>=``, not ``>``. The "exactly once"
guarantee is enforced via :attr:`_mission_warning_emitted` — once a
mission appears in that set, no further ``BUDGET_WARNING`` events are
emitted for it for the lifetime of the governor instance.

Hard-constraint event payload schema (Requirement 12.1, 12.8)
-------------------------------------------------------------

Events emitted by this governor **never** carry frame bodies, evidence
content, prompt text, raw user input, action input payloads, organ
outputs, or secret values. Every payload is restricted to the
whitelist:

* ``scope``         — one of ``"frame"``, ``"action"``, ``"mission"``;
* ``mission_id``    — caller-supplied identifier;
* ``tokens_used``   — integer counter only;
* ``tokens_budget`` — integer counter only;
* ``reason``        — short, static, machine-readable tag (one of
                      :data:`REASON_FRAME_REJECTED`,
                      :data:`REASON_ACTION_REJECTED`,
                      :data:`REASON_MISSION_EXHAUSTED`,
                      :data:`REASON_WARNING_THRESHOLD_CROSSED`).

These five keys are the entire contract surface of the governor's
event payloads. Any future addition must extend the whitelist
explicitly (and would require a corresponding spec update).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import ConfigDict, Field

from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel

__all__ = [
    "BudgetDecision",
    "DEFAULT_MAX_COMPRESSION_PASSES",
    "DEFAULT_WARNING_THRESHOLD",
    "REASON_ACTION_REJECTED",
    "REASON_FRAME_COMPRESSED",
    "REASON_FRAME_REJECTED",
    "REASON_MISSION_EXHAUSTED",
    "REASON_WARNING_THRESHOLD_CROSSED",
    "REASON_WITHIN_BUDGET",
    "SCOPE_ACTION",
    "SCOPE_FRAME",
    "SCOPE_MISSION",
    "TokenBudgetGovernor",
]


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


DEFAULT_MAX_COMPRESSION_PASSES: int = 3
"""Maximum number of ``ContextCompressor.compress`` passes per frame
(Requirement 10.3 — "after a maximum of 3 compression passes")."""


DEFAULT_WARNING_THRESHOLD: float = 0.9
"""Mission-budget warning threshold (Requirement 10.8 — 90 %)."""


# Scope tags (whitelisted in every event payload)
SCOPE_FRAME: str = "frame"
SCOPE_ACTION: str = "action"
SCOPE_MISSION: str = "mission"


# Reason tags carried on :class:`BudgetDecision` and on event payloads
REASON_WITHIN_BUDGET: str = "within_budget"
REASON_FRAME_COMPRESSED: str = "frame_compressed"
REASON_FRAME_REJECTED: str = "frame_rejected_after_compression"
REASON_ACTION_REJECTED: str = "action_rejected_pre_execution"
REASON_MISSION_EXHAUSTED: str = "mission_exhausted"
REASON_WARNING_THRESHOLD_CROSSED: str = "warning_threshold_crossed"


# ---------------------------------------------------------------------------
# Token estimation helper
# ---------------------------------------------------------------------------


def _estimate_frame_tokens(frame: Any) -> int:
    """Return a non-negative integer estimate of the frame's token count.

    Resolution order
    ----------------

    1. If ``frame`` exposes a ``prompt_tokens`` attribute that is an
       ``int`` (or ``int``-coercible), return ``int(prompt_tokens)``.
    2. Else if ``frame`` exposes a ``token_count`` attribute that is an
       ``int`` (or ``int``-coercible), return ``int(token_count)``.
       :class:`sentinel.agent.decision_frame.LLMDecisionFrame` carries
       this field, populated by ``PromptBudgetAllocator.estimate_frame_tokens``.
    3. Else if ``frame`` exposes ``model_dump``, hash the canonical JSON
       form (sorted keys, ASCII escapes) and return ``len(json) // 4``.
       The 4-bytes-per-token heuristic matches GPT-family tokenizer
       averages and is used by ``token_ledger.estimate_tokens`` so the
       two estimators stay roughly aligned.
    4. Else fall back to ``len(str(frame)) // 4``.

    Resolution is deliberately tolerant: the governor is decoupled from
    :class:`LLMDecisionFrame` and ``ContextCompressor`` so it can govern
    any frame-shaped object that exposes either a token counter or a
    serialisable form. The estimate is always non-negative — a value
    below zero (e.g., from a buggy upstream counter) is clamped to ``0``.
    """

    # Path 1: explicit prompt_tokens attribute.
    candidate = getattr(frame, "prompt_tokens", None)
    if candidate is not None:
        try:
            value = int(candidate)
        except (TypeError, ValueError):
            value = None
        if value is not None:
            return max(0, value)

    # Path 2: token_count attribute (LLMDecisionFrame).
    candidate = getattr(frame, "token_count", None)
    if candidate is not None:
        try:
            value = int(candidate)
        except (TypeError, ValueError):
            value = None
        if value is not None:
            return max(0, value)

    # Path 3: pydantic-style model_dump → canonical JSON length / 4.
    model_dump = getattr(frame, "model_dump", None)
    if callable(model_dump):
        try:
            payload = model_dump(mode="json")
        except TypeError:
            # ``model_dump`` may not accept ``mode="json"`` on plain
            # dataclasses; fall back to the no-arg form.
            payload = model_dump()
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
        return max(0, len(canonical) // 4)

    # Path 4: stringification fallback.
    return max(0, len(str(frame)) // 4)


# ---------------------------------------------------------------------------
# BudgetDecision
# ---------------------------------------------------------------------------


class BudgetDecision(SentinelModel):
    """Immutable verdict returned by every ``enforce_*`` method.

    Carries integer counters and a short reason tag only — never any
    frame body, action payload, or secret. Frozen so downstream
    subscribers cannot mutate counters in flight.

    Fields
    ------

    * ``accepted``: ``True`` iff the call may proceed.
    * ``tokens_used``: actual or estimated token count for the
      enforcement scope (post-compression for frames, estimated for
      actions, cumulative for missions). Always ``>= 0``.
    * ``tokens_budget``: the configured budget for the enforcement
      scope. Always ``>= 0``.
    * ``reason``: one of the ``REASON_*`` constants exported by this
      module.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    accepted: bool
    tokens_used: int = Field(ge=0)
    tokens_budget: int = Field(ge=0)
    reason: str


# ---------------------------------------------------------------------------
# TokenBudgetGovernor
# ---------------------------------------------------------------------------


class TokenBudgetGovernor:
    """Hard token limits at frame, action, and mission scope.

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9.

    The governor is decoupled from :class:`ContextCompressor` and
    :class:`LLMDecisionFrame` — both are passed in as parameters. The
    only hard dependency is :class:`EventBus` (for budget events) and
    :class:`AgentEventType` (the event-type enum extended in Task 1.2).

    Per-mission state
    -----------------

    * :attr:`_mission_spent` — cumulative tokens spent per mission.
    * :attr:`_mission_warning_emitted` — set of missions that have
      already received a ``BUDGET_WARNING`` (enforces "exactly once").
    * :attr:`_mission_exhausted` — set of missions whose budget is
      depleted; new calls are rejected via :meth:`enforce_action`.
    * :attr:`_mission_in_flight` — count of in-flight calls per
      mission, managed by :meth:`begin_call` / :meth:`end_call`.

    The governor never tracks individual call IDs — that is the
    caller's responsibility (typically the scheduler or runtime).
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        max_compression_passes: int = DEFAULT_MAX_COMPRESSION_PASSES,
        warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
    ) -> None:
        if max_compression_passes < 0:
            raise ValueError("TokenBudgetGovernor.max_compression_passes must be >= 0")
        if not (0.0 < warning_threshold <= 1.0):
            raise ValueError(
                "TokenBudgetGovernor.warning_threshold must be in (0.0, 1.0]"
            )

        self._event_bus = event_bus
        self._max_compression_passes = max_compression_passes
        self._warning_threshold = warning_threshold

        self._mission_spent: dict[str, int] = {}
        self._mission_warning_emitted: set[str] = set()
        self._mission_exhausted: set[str] = set()
        self._mission_in_flight: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Read-only accessors (for tests + diagnostics)
    # ------------------------------------------------------------------

    @property
    def max_compression_passes(self) -> int:
        return self._max_compression_passes

    @property
    def warning_threshold(self) -> float:
        return self._warning_threshold

    def mission_spent(self, mission_id: str) -> int:
        """Cumulative tokens recorded for ``mission_id`` (``0`` if unseen)."""

        return self._mission_spent.get(mission_id, 0)

    def is_mission_exhausted(self, mission_id: str) -> bool:
        return mission_id in self._mission_exhausted

    def in_flight(self, mission_id: str) -> int:
        """Current in-flight call count for ``mission_id`` (``0`` if unseen)."""

        return self._mission_in_flight.get(mission_id, 0)

    # ------------------------------------------------------------------
    # In-flight bookkeeping (Requirement 10.7)
    # ------------------------------------------------------------------

    def begin_call(self, mission_id: str) -> None:
        """Record that a new call for ``mission_id`` has started executing.

        Call this immediately *after* :meth:`enforce_action` returns
        ``accepted=True`` and *before* the model/organ work begins.
        Pairs with :meth:`end_call`.
        """

        self._mission_in_flight[mission_id] = self._mission_in_flight.get(mission_id, 0) + 1

    def end_call(self, mission_id: str) -> None:
        """Record that an in-flight call for ``mission_id`` has finished.

        Tolerant of double-end and end-without-begin: the in-flight
        counter is clamped at zero rather than raising. The governor
        does not own call lifecycle, only its accounting.
        """

        current = self._mission_in_flight.get(mission_id, 0)
        if current <= 1:
            self._mission_in_flight.pop(mission_id, None)
        else:
            self._mission_in_flight[mission_id] = current - 1

    # ------------------------------------------------------------------
    # Per-frame enforcement (Requirements 10.1, 10.2, 10.3)
    # ------------------------------------------------------------------

    def enforce_frame(
        self,
        mission_id: str,
        frame_builder: Callable[[], Any],
        compressor: Any,
        frame_budget: int,
    ) -> tuple[Any, BudgetDecision]:
        """Build a decision frame and enforce the per-frame token budget.

        The frame is built via ``frame_builder()``. Its token count is
        estimated; if it exceeds ``frame_budget``, ``compressor.compress``
        is invoked at most :attr:`max_compression_passes` times, with
        the frame re-estimated after each pass.

        * If the frame fits on the first estimate (no compression
          needed) — returns ``(frame, BudgetDecision(accepted=True,
          reason=REASON_WITHIN_BUDGET))``.

        * If the frame fits after one or more compression passes —
          returns ``(frame, BudgetDecision(accepted=True,
          reason=REASON_FRAME_COMPRESSED))``.

        * If the frame still exceeds ``frame_budget`` after the
          configured number of passes — emits ``BUDGET_EXCEEDED``
          with ``scope="frame"`` and returns ``(frame,
          BudgetDecision(accepted=False,
          reason=REASON_FRAME_REJECTED))``. The frame body is NOT
          included in the event payload.

        The ``compressor`` parameter is duck-typed: any object that
        exposes a ``compress(frame) -> frame`` method works. The
        governor never imports the concrete
        :class:`ContextCompressor` class.

        ``frame_budget`` is validated to be ``> 0`` (Requirement 10.1).
        """

        if frame_budget <= 0:
            raise ValueError("TokenBudgetGovernor.enforce_frame: frame_budget must be > 0")

        frame = frame_builder()
        tokens = _estimate_frame_tokens(frame)

        if tokens <= frame_budget:
            return frame, BudgetDecision(
                accepted=True,
                tokens_used=tokens,
                tokens_budget=frame_budget,
                reason=REASON_WITHIN_BUDGET,
            )

        # Over budget — invoke the compressor up to ``max_compression_passes``
        # times, re-estimating after each pass.
        passes = 0
        while passes < self._max_compression_passes and tokens > frame_budget:
            frame = compressor.compress(frame)
            tokens = _estimate_frame_tokens(frame)
            passes += 1

        if tokens <= frame_budget:
            return frame, BudgetDecision(
                accepted=True,
                tokens_used=tokens,
                tokens_budget=frame_budget,
                reason=REASON_FRAME_COMPRESSED,
            )

        # Still over budget after the configured number of passes —
        # reject and emit BUDGET_EXCEEDED with scope="frame". The frame
        # body itself is intentionally omitted from the payload.
        self._emit_budget_exceeded(
            scope=SCOPE_FRAME,
            mission_id=mission_id,
            tokens_used=tokens,
            tokens_budget=frame_budget,
            reason=REASON_FRAME_REJECTED,
        )
        return frame, BudgetDecision(
            accepted=False,
            tokens_used=tokens,
            tokens_budget=frame_budget,
            reason=REASON_FRAME_REJECTED,
        )

    # ------------------------------------------------------------------
    # Per-action enforcement (Requirements 10.4, 10.5, 10.7)
    # ------------------------------------------------------------------

    def enforce_action(
        self,
        mission_id: str,
        estimated_tokens: int,
        action_budget: int,
    ) -> BudgetDecision:
        """Pre-execution token check for an individual action.

        Returns a rejected :class:`BudgetDecision` (and emits the
        matching event) when:

        * the mission is already exhausted — emits ``BUDGET_EXHAUSTED``
          with ``scope="action"`` and ``reason=REASON_MISSION_EXHAUSTED``;
          this is what blocks **new** calls per Requirement 10.7
          (in-flight calls are unaffected).
        * the action's estimated token count exceeds ``action_budget``
          — emits ``BUDGET_EXCEEDED`` with ``scope="action"`` and
          ``reason=REASON_ACTION_REJECTED`` (Requirement 10.5).

        Otherwise returns an accepted decision with
        ``reason=REASON_WITHIN_BUDGET``.

        ``action_budget`` is validated to be ``> 0`` (Requirement 10.4).
        ``estimated_tokens`` is clamped to ``>= 0``; a negative input
        from a buggy upstream counter is treated as zero rather than
        propagated.
        """

        if action_budget <= 0:
            raise ValueError(
                "TokenBudgetGovernor.enforce_action: action_budget must be > 0"
            )
        tokens = max(0, int(estimated_tokens))

        if mission_id in self._mission_exhausted:
            self._emit_budget_exhausted(
                scope=SCOPE_ACTION,
                mission_id=mission_id,
                tokens_used=self._mission_spent.get(mission_id, 0),
                tokens_budget=action_budget,
                reason=REASON_MISSION_EXHAUSTED,
            )
            return BudgetDecision(
                accepted=False,
                tokens_used=tokens,
                tokens_budget=action_budget,
                reason=REASON_MISSION_EXHAUSTED,
            )

        if tokens > action_budget:
            self._emit_budget_exceeded(
                scope=SCOPE_ACTION,
                mission_id=mission_id,
                tokens_used=tokens,
                tokens_budget=action_budget,
                reason=REASON_ACTION_REJECTED,
            )
            return BudgetDecision(
                accepted=False,
                tokens_used=tokens,
                tokens_budget=action_budget,
                reason=REASON_ACTION_REJECTED,
            )

        return BudgetDecision(
            accepted=True,
            tokens_used=tokens,
            tokens_budget=action_budget,
            reason=REASON_WITHIN_BUDGET,
        )

    # ------------------------------------------------------------------
    # Per-mission enforcement (Requirements 10.6, 10.7, 10.8)
    # ------------------------------------------------------------------

    def enforce_mission(
        self,
        mission_id: str,
        tokens_just_spent: int,
        mission_budget: int,
    ) -> BudgetDecision:
        """Record post-call token spend and decide warning/exhaustion.

        Behavior
        --------

        * Adds ``tokens_just_spent`` to the mission's cumulative
          counter (clamped at ``>= 0``).
        * If the cumulative counter crosses
          ``warning_threshold * mission_budget`` for the first time,
          emits ``BUDGET_WARNING`` with ``scope="mission"`` exactly
          once (subsequent crossings for the same mission are silent).
        * If the cumulative counter reaches or exceeds
          ``mission_budget``, marks the mission exhausted and emits
          ``BUDGET_EXHAUSTED`` with ``scope="mission"`` exactly once;
          returns a rejected decision with
          ``reason=REASON_MISSION_EXHAUSTED``.
        * Otherwise returns an accepted decision with
          ``reason=REASON_WITHIN_BUDGET``.

        Edge case — exactly 90 %
        ------------------------

        The crossing predicate is::

            previous_spent < threshold * mission_budget <= new_spent

        i.e. the comparison on the *new* cumulative is ``>=``, not
        ``>``. A mission that lands exactly at ``0.9 * mission_budget``
        does cross the threshold. The "exactly once" guarantee is
        enforced via :attr:`_mission_warning_emitted`; the warning
        fires once per mission per governor lifetime.

        Note: the governor does **not** cancel in-flight calls on
        exhaustion. Per Requirement 10.7 ("allow in-flight model
        calls to complete without cancellation"), callers continue
        running their in-flight work; only **new** calls are blocked,
        via :meth:`enforce_action`.

        ``mission_budget`` is validated to be ``> 0`` (Requirement 10.6).
        """

        if mission_budget <= 0:
            raise ValueError(
                "TokenBudgetGovernor.enforce_mission: mission_budget must be > 0"
            )
        delta = max(0, int(tokens_just_spent))

        previous = self._mission_spent.get(mission_id, 0)
        cumulative = previous + delta
        self._mission_spent[mission_id] = cumulative

        # Warning-threshold crossing — exactly once per mission.
        warning_floor = self._warning_threshold * mission_budget
        if (
            cumulative >= warning_floor
            and previous < warning_floor
            and mission_id not in self._mission_warning_emitted
        ):
            self._mission_warning_emitted.add(mission_id)
            self._emit_budget_warning(
                scope=SCOPE_MISSION,
                mission_id=mission_id,
                tokens_used=cumulative,
                tokens_budget=mission_budget,
                reason=REASON_WARNING_THRESHOLD_CROSSED,
            )

        # Exhaustion — exactly once per mission.
        if cumulative >= mission_budget:
            newly_exhausted = mission_id not in self._mission_exhausted
            self._mission_exhausted.add(mission_id)
            if newly_exhausted:
                self._emit_budget_exhausted(
                    scope=SCOPE_MISSION,
                    mission_id=mission_id,
                    tokens_used=cumulative,
                    tokens_budget=mission_budget,
                    reason=REASON_MISSION_EXHAUSTED,
                )
            return BudgetDecision(
                accepted=False,
                tokens_used=cumulative,
                tokens_budget=mission_budget,
                reason=REASON_MISSION_EXHAUSTED,
            )

        return BudgetDecision(
            accepted=True,
            tokens_used=cumulative,
            tokens_budget=mission_budget,
            reason=REASON_WITHIN_BUDGET,
        )

    # ------------------------------------------------------------------
    # Event emission helpers — payload whitelist enforced here
    # ------------------------------------------------------------------

    def _emit_budget_warning(
        self,
        *,
        scope: str,
        mission_id: str,
        tokens_used: int,
        tokens_budget: int,
        reason: str,
    ) -> None:
        self._event_bus.append(
            AgentEventType.BUDGET_WARNING,
            "token_budget_governor warning threshold crossed",
            payload=self._whitelisted_payload(
                scope=scope,
                mission_id=mission_id,
                tokens_used=tokens_used,
                tokens_budget=tokens_budget,
                reason=reason,
            ),
        )

    def _emit_budget_exceeded(
        self,
        *,
        scope: str,
        mission_id: str,
        tokens_used: int,
        tokens_budget: int,
        reason: str,
    ) -> None:
        self._event_bus.append(
            AgentEventType.BUDGET_EXCEEDED,
            "token_budget_governor budget exceeded",
            payload=self._whitelisted_payload(
                scope=scope,
                mission_id=mission_id,
                tokens_used=tokens_used,
                tokens_budget=tokens_budget,
                reason=reason,
            ),
        )

    def _emit_budget_exhausted(
        self,
        *,
        scope: str,
        mission_id: str,
        tokens_used: int,
        tokens_budget: int,
        reason: str,
    ) -> None:
        self._event_bus.append(
            AgentEventType.BUDGET_EXHAUSTED,
            "token_budget_governor mission exhausted",
            payload=self._whitelisted_payload(
                scope=scope,
                mission_id=mission_id,
                tokens_used=tokens_used,
                tokens_budget=tokens_budget,
                reason=reason,
            ),
        )

    @staticmethod
    def _whitelisted_payload(
        *,
        scope: str,
        mission_id: str,
        tokens_used: int,
        tokens_budget: int,
        reason: str,
    ) -> dict[str, Any]:
        """Return the strict event payload — only whitelisted keys.

        This single chokepoint is the only place ``TokenBudgetGovernor``
        constructs an event payload dict. Any future call site that
        bypasses this helper would also bypass the payload-shape
        contract; tests assert on the exact key set returned here.
        """

        return {
            "scope": scope,
            "mission_id": mission_id,
            "tokens_used": int(tokens_used),
            "tokens_budget": int(tokens_budget),
            "reason": reason,
        }
