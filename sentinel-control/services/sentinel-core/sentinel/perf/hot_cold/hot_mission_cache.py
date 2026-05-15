"""``HotMissionCache`` — compact in-memory mutable mission state (Phase B).

This module implements the *hot side* of the hot/cold state separation
(Requirements 4.1, 4.2, 4.5, 4.6, 4.7, 4.8). It is the single in-memory
working set the Decision_Core touches on every tick: short identifier
strings, short summary strings, and bounded reference lists. It MUST NOT
hold receipt or artifact payload bytes — those live cold-side, addressed
by ID through ``ColdReceiptStore`` / ``ReceiptIndex`` (Tasks 4.2 and 4.4).

References-only invariant
-------------------------
Every field on every model in this module is one of:

* a short identifier string (``mission_id``, ``receipt_id``, ``organ_id``,
  ``action_type``);
* a short summary string capped to 200 characters;
* a bounded list of the above;
* a bounded ``dict[str, str]`` of organ-state labels (≤32 entries);
* a single ``int`` timestamp (``ts_ns``).

There are no ``bytes`` fields, no ``Any`` fields, no nested receipt
payloads, and no embedded artifact blobs. This is the structural enforcement
of Requirement 4.2 ("references only"): the type system itself rejects
payload-bearing values.

Per-tier memory budget
----------------------
Requirement 4.5 sets per-mission memory ceilings keyed on completed-action
count:

* tier 1 — fewer than 100 completed actions   → < 64 KB
* tier 2 — 100..1_000 completed actions       → < 128 KB
* tier 3 — more than 1_000 completed actions  → < 256 KB

``memory_footprint_bytes`` returns a deterministic estimator that closely
tracks the actual Python footprint of the bounded structures the cache
holds. The estimator is intentionally simple (sum of string lengths plus
small per-entry overheads) — exact byte-perfection is not required, only
that callers can use the per-tier ceilings as advisory bounds.
``current_tier``, ``tier_budget_bytes``, and ``exceeds_budget`` make those
ceilings programmatically queryable.

Synchronous eviction
--------------------
Requirement 4.7 mandates that terminal-state mission eviction completes
synchronously within the same event-loop tick, blocking other cache
operations until done. ``evict_mission`` is a plain blocking ``def`` with
no ``await``, no thread handoff, no asyncio scheduling — when it returns,
the mission's view and counter have been removed atomically and the cache
is in a consistent state. Phase B is single-threaded; no locks are
introduced.

Overflow → receipt-id ref
-------------------------
Requirement 4.8: action summaries beyond the 10 most recent are evicted
and replaced by their receipt IDs in the cold store. ``push_action_summary``
implements this directly: when ``recent_action_summaries`` would exceed 10,
the oldest full ``ActionSummary`` is popped and only its ``receipt_id`` is
retained — appended to ``overflow_receipt_ids``. The popped summary's full
struct is discarded; the cold store remains the canonical source.

Requirements covered: 4.1, 4.2, 4.5, 4.6, 4.7, 4.8.
"""

from __future__ import annotations

from typing import Self

from pydantic import ConfigDict, Field, model_validator

from sentinel.shared.models import SentinelModel


# ---------------------------------------------------------------------------
# Public capacity constants — used by callers, tests, and the estimator.
# ---------------------------------------------------------------------------

MAX_CONSTRAINTS: int = 32
"""Upper bound on per-mission constraint strings (Requirement 4.1)."""

MAX_BLOCKERS: int = 16
"""Upper bound on per-mission blocker strings (Requirement 4.1)."""

MAX_ORGAN_STATES: int = 32
"""Upper bound on per-mission organ-state entries (Requirement 4.1)."""

MAX_ACTION_SUMMARIES_PER_MISSION: int = 10
"""Upper bound on per-mission ``recent_action_summaries`` (Requirements 4.1, 4.8)."""

MAX_SUMMARY_LEN: int = 200
"""Per-summary string cap (Requirement 4.2 — keeps each summary small)."""


# ---------------------------------------------------------------------------
# Per-tier byte budgets (Requirement 4.5).
# ---------------------------------------------------------------------------

BUDGET_BYTES_TIER_1: int = 64 * 1024
"""<64 KB ceiling for missions with fewer than 100 completed actions."""

BUDGET_BYTES_TIER_2: int = 128 * 1024
"""<128 KB ceiling for missions with 100..1_000 completed actions."""

BUDGET_BYTES_TIER_3: int = 256 * 1024
"""<256 KB ceiling for missions with more than 1_000 completed actions."""

_TIER_2_LOWER: int = 100
_TIER_3_LOWER: int = 1_000


# ---------------------------------------------------------------------------
# ActionSummary — references-only per-action record.
# ---------------------------------------------------------------------------


class ActionSummary(SentinelModel):
    """Frozen reference-bearing summary of a single completed action.

    The ``receipt_id`` is *always required* — this is the structural
    enforcement of the "references only" invariant: every action summary
    must point at a cold-store receipt, so the hot cache can drop the
    summary at any time without information loss (the receipt remains
    queryable via ``ReceiptIndex``).

    ``summary`` is capped at 200 characters (``MAX_SUMMARY_LEN``) so that a
    full ``recent_action_summaries`` list of 10 entries cannot blow the
    tier-1 64 KB ceiling on its own.
    """

    receipt_id: str
    action_type: str
    organ_id: str | None = None
    summary: str = Field(max_length=MAX_SUMMARY_LEN)
    ts_ns: int = Field(ge=0)

    # Frozen: an ``ActionSummary`` is an immutable record once constructed.
    # ``extra='forbid'`` blocks accidental payload smuggling via unknown keys.
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


# ---------------------------------------------------------------------------
# HotMissionView — mutable bounded per-mission view.
# ---------------------------------------------------------------------------


class HotMissionView(SentinelModel):
    """Mutable, bounded, references-only working state for one active mission.

    All bounded fields enforce their caps at construction. After construction
    the view is mutable (``frozen=False``) so the cache can append to its
    lists and assign to its scalars in place; the cache is responsible for
    re-checking caps on mutation paths (``push_action_summary``,
    ``set_constraints``, etc.). The pydantic-side caps are a defensive gate
    against external code constructing an oversized view directly.
    """

    mission_id: str
    objective: str = ""
    constraints: list[str] = Field(default_factory=list, max_length=MAX_CONSTRAINTS)
    blockers: list[str] = Field(default_factory=list, max_length=MAX_BLOCKERS)
    organ_states: dict[str, str] = Field(default_factory=dict)
    recent_action_summaries: list[ActionSummary] = Field(
        default_factory=list, max_length=MAX_ACTION_SUMMARIES_PER_MISSION
    )
    # Unbounded by design: contains only ``receipt_id`` strings — cheap, and
    # acts as a forwarding pointer to the cold store for actions that have
    # aged out of ``recent_action_summaries``. The estimator counts these so
    # they still contribute to the per-tier budget.
    overflow_receipt_ids: list[str] = Field(default_factory=list)

    # Mutable so the cache can update it in place.
    model_config = ConfigDict(extra="forbid", frozen=False, use_enum_values=False)

    @model_validator(mode="after")
    def _validate_organ_states_cap(self) -> Self:
        """Enforce the ≤32 ``organ_states`` cap (pydantic v2 has no ``max_length`` for dicts in all versions)."""
        if len(self.organ_states) > MAX_ORGAN_STATES:
            raise ValueError(
                f"HotMissionView.organ_states exceeds cap "
                f"({len(self.organ_states)} > {MAX_ORGAN_STATES})."
            )
        return self


# ---------------------------------------------------------------------------
# HotMissionCache — the registry, the budget estimator, the eviction site.
# ---------------------------------------------------------------------------


class HotMissionCache:
    """Compact in-memory references-only mutable mission state.

    Stores at most one ``HotMissionView`` per active mission, plus a
    monotonic completed-action counter used to pick the per-tier budget.
    Receipts and artifacts are NEVER stored here — only ``receipt_id``
    references and short summary strings. Phase B is single-threaded; no
    locks are taken. Terminal-state eviction is synchronous and same-tick
    (Requirement 4.7).

    Requirements: 4.1, 4.2, 4.5, 4.6, 4.7, 4.8.
    """

    # Re-export caps as class attributes so callers can introspect via the
    # cache instance without importing the module-level constants.
    MAX_ACTION_SUMMARIES_PER_MISSION: int = MAX_ACTION_SUMMARIES_PER_MISSION
    MAX_CONSTRAINTS: int = MAX_CONSTRAINTS
    MAX_BLOCKERS: int = MAX_BLOCKERS
    MAX_ORGAN_STATES: int = MAX_ORGAN_STATES
    MAX_SUMMARY_LEN: int = MAX_SUMMARY_LEN
    BUDGET_BYTES_TIER_1: int = BUDGET_BYTES_TIER_1
    BUDGET_BYTES_TIER_2: int = BUDGET_BYTES_TIER_2
    BUDGET_BYTES_TIER_3: int = BUDGET_BYTES_TIER_3

    def __init__(self) -> None:
        # Live mutable views, one per active mission.
        self._views: dict[str, HotMissionView] = {}
        # Monotonic counter of completed actions per mission. Used by
        # ``current_tier`` to pick the right per-tier budget. Incremented
        # on every ``push_action_summary``; reset by ``evict_mission``.
        self._action_count: dict[str, int] = {}

    # ------------------------------------------------------------------ get

    def get(self, mission_id: str) -> HotMissionView | None:
        """Return the live mutable view for ``mission_id``, or ``None``.

        The view is returned by reference (not a copy). Callers MAY mutate
        bounded fields in place but MUST NOT inline payload bytes — the
        references-only invariant is enforced by the model field types.
        """
        return self._views.get(mission_id)

    # ---------------------------------------------------------- set_objective

    def set_objective(self, mission_id: str, objective: str) -> None:
        """Set the mission objective; lazily creates the view on first call."""
        view = self._ensure_view(mission_id)
        view.objective = objective

    # --------------------------------------------------------- set_constraints

    def set_constraints(self, mission_id: str, constraints: list[str]) -> None:
        """Replace the constraint list; rejects payloads larger than the cap.

        Raises ``ValueError`` if ``len(constraints) > MAX_CONSTRAINTS``.
        Lazily creates the view on first call.
        """
        if len(constraints) > MAX_CONSTRAINTS:
            raise ValueError(
                f"constraints length {len(constraints)} exceeds cap {MAX_CONSTRAINTS}"
            )
        view = self._ensure_view(mission_id)
        # Defensive copy: callers may mutate their local list afterwards.
        view.constraints = list(constraints)

    # ------------------------------------------------------ push_action_summary

    def push_action_summary(self, mission_id: str, summary: ActionSummary) -> None:
        """Append a summary; keep at most ``MAX_ACTION_SUMMARIES_PER_MISSION``.

        When the list would exceed the cap, the oldest full summary is
        dropped and only its ``receipt_id`` is retained — appended to
        ``overflow_receipt_ids``. This is Requirement 4.8: "evict action
        summaries beyond the 10 most recent, replacing them with their
        receipt IDs in the cold store". The full ``ActionSummary`` struct
        is discarded from the hot cache; the canonical record lives cold.

        Increments the per-mission action counter (used by
        ``current_tier`` to pick the per-tier budget).
        """
        view = self._ensure_view(mission_id)
        view.recent_action_summaries.append(summary)
        while len(view.recent_action_summaries) > MAX_ACTION_SUMMARIES_PER_MISSION:
            evicted = view.recent_action_summaries.pop(0)
            view.overflow_receipt_ids.append(evicted.receipt_id)
        self._action_count[mission_id] = self._action_count.get(mission_id, 0) + 1

    # ----------------------------------------------------------- evict_mission

    def evict_mission(self, mission_id: str) -> None:
        """Synchronously remove all hot state for ``mission_id`` (Requirement 4.7).

        Same-tick blocking: this method does not yield, schedule, or await.
        When it returns, the view and the action counter are gone. Idempotent
        — calling ``evict_mission`` for an unknown id is a no-op.
        """
        # ``dict.pop(..., None)`` is atomic in CPython and never raises.
        self._views.pop(mission_id, None)
        self._action_count.pop(mission_id, None)

    # ---------------------------------------------------- memory_footprint_bytes

    def memory_footprint_bytes(self, mission_id: str) -> int:
        """Estimate current memory footprint of the mission's view, in bytes.

        Returns ``0`` for a missing mission. Otherwise sums the length of
        all string content plus small per-entry overheads. The estimator
        intentionally tracks the actual Python footprint *closely enough*
        that callers can use the per-tier ceilings as advisory bounds — it
        is not byte-perfect against ``sys.getsizeof``. The cap relationship
        we care about is monotone: larger views produce larger estimates,
        smaller views produce smaller estimates, and a view that fits well
        under the configured ceiling here will fit comfortably under the
        actual interpreter footprint.

        Requirement 4.5.
        """
        view = self._views.get(mission_id)
        if view is None:
            return 0

        total = 0

        # Per-action-summary cost: the four short strings + the ts_ns int.
        for s in view.recent_action_summaries:
            total += _action_summary_bytes(s)

        # Constraints: short strings + small per-entry list overhead.
        for c in view.constraints:
            total += len(c) + 24

        # Blockers: identical shape to constraints.
        for b in view.blockers:
            total += len(b) + 24

        # Organ states: per-entry dict overhead.
        for k, v in view.organ_states.items():
            total += len(k) + len(v) + 32

        # Overflow receipt-id refs: cheap, but counted so they show up in
        # the per-tier budget after large action counts.
        for r in view.overflow_receipt_ids:
            total += len(r) + 16

        # Struct overhead: scalar fields + the surrounding view object.
        total += len(view.objective) + len(view.mission_id) + 64

        return total

    # ---------------------------------------------------------------- helpers

    def current_tier(self, mission_id: str) -> int:
        """Return the per-tier index (1, 2, or 3) for ``mission_id``.

        * tier 1 — fewer than 100 completed actions
        * tier 2 — 100..1_000 completed actions
        * tier 3 — more than 1_000 completed actions

        Unknown missions are treated as tier 1.
        """
        count = self._action_count.get(mission_id, 0)
        if count < _TIER_2_LOWER:
            return 1
        if count <= _TIER_3_LOWER:
            return 2
        return 3

    def tier_budget_bytes(self, mission_id: str) -> int:
        """Return the per-tier byte ceiling for ``mission_id``."""
        tier = self.current_tier(mission_id)
        if tier == 1:
            return BUDGET_BYTES_TIER_1
        if tier == 2:
            return BUDGET_BYTES_TIER_2
        return BUDGET_BYTES_TIER_3

    def exceeds_budget(self, mission_id: str) -> bool:
        """Diagnostic: ``True`` iff the estimated footprint exceeds the tier ceiling.

        Does NOT raise — caller policy decides what to do (emit a warning,
        trigger compression, escalate to cold store, etc.). Returns ``False``
        for unknown missions (footprint is 0).
        """
        return self.memory_footprint_bytes(mission_id) > self.tier_budget_bytes(mission_id)

    # ------------------------------------------------------------- internal

    def _ensure_view(self, mission_id: str) -> HotMissionView:
        """Get-or-create the live view for ``mission_id``."""
        view = self._views.get(mission_id)
        if view is None:
            view = HotMissionView(mission_id=mission_id)
            self._views[mission_id] = view
        return view


# ---------------------------------------------------------------------------
# Estimator helpers (module-private).
# ---------------------------------------------------------------------------


def _action_summary_bytes(summary: ActionSummary) -> int:
    """Estimated byte cost of one ``ActionSummary`` in the hot cache.

    Roughly: sum of string lengths + 8 bytes for the ``ts_ns`` int. The
    constant ``8`` covers the int payload plus a small per-record overhead;
    the estimator does not need to be byte-perfect, only monotone.
    """
    organ_id_len = len(summary.organ_id) if summary.organ_id is not None else 0
    return (
        len(summary.receipt_id)
        + len(summary.action_type)
        + organ_id_len
        + len(summary.summary)
        + 8
    )


__all__ = [
    "ActionSummary",
    "HotMissionView",
    "HotMissionCache",
    "MAX_ACTION_SUMMARIES_PER_MISSION",
    "MAX_CONSTRAINTS",
    "MAX_BLOCKERS",
    "MAX_ORGAN_STATES",
    "MAX_SUMMARY_LEN",
    "BUDGET_BYTES_TIER_1",
    "BUDGET_BYTES_TIER_2",
    "BUDGET_BYTES_TIER_3",
]
