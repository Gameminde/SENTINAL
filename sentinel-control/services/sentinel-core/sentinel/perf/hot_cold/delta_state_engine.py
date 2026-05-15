"""``DeltaStateEngine`` — validated delta application on ``HotMissionCache``.

Applies validated deltas on top of ``HotMissionCache``, never a full rebuild.
Each delta is bounds-checked against the ``MissionAuthorityEnvelope`` and
structural capacity constants before mutation. On rejection the prior state
is preserved (no partial application) and an ``AUTHORITY_VIOLATION`` event
is emitted.

Requirements: 12.7 (authority-bounds enforcement).
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict

from sentinel.mission.models import MissionAuthorityEnvelope
from sentinel.perf.hot_cold.hot_mission_cache import (
    ActionSummary,
    HotMissionCache,
    MAX_BLOCKERS,
    MAX_CONSTRAINTS,
    MAX_ORGAN_STATES,
)
from sentinel.shared.events import AgentEventType, EventBus
from sentinel.shared.models import SentinelModel


# ---------------------------------------------------------------------------
# StateDelta — frozen, validated delta descriptor.
# ---------------------------------------------------------------------------


class StateDelta(SentinelModel):
    """Frozen descriptor for a single state mutation against a mission's hot view.

    Fields
    ------
    delta_type : str
        One of ``"set_objective"``, ``"add_constraint"``, ``"add_blocker"``,
        ``"push_action_summary"``, ``"set_organ_state"``.
    payload : dict[str, Any]
        Delta-specific data. Examples:
        - ``{"objective": "..."}`` for ``set_objective``
        - ``{"constraint": "..."}`` for ``add_constraint``
        - ``{"blocker": "..."}`` for ``add_blocker``
        - ``{"summary": <ActionSummary.model_dump()>}`` for ``push_action_summary``
        - ``{"key": "...", "value": "..."}`` for ``set_organ_state``
    """

    delta_type: str
    payload: dict[str, Any]

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------------------
# Valid delta types (used for dispatch and validation).
# ---------------------------------------------------------------------------

_VALID_DELTA_TYPES: frozenset[str] = frozenset(
    {
        "set_objective",
        "add_constraint",
        "add_blocker",
        "push_action_summary",
        "set_organ_state",
    }
)


# ---------------------------------------------------------------------------
# DeltaStateEngine
# ---------------------------------------------------------------------------


class DeltaStateEngine:
    """Applies validated deltas on top of HotMissionCache, never a full rebuild.

    Requirements: 12.7 (authority-bounds enforcement).

    Prior state is preserved on rejection: bounds checks run BEFORE any
    mutation, so a rejected delta leaves the hot cache unchanged.
    """

    def __init__(self, hot_cache: HotMissionCache, *, event_bus: EventBus) -> None:
        self._hot_cache = hot_cache
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(
        self,
        mission_id: str,
        delta: StateDelta,
        envelope: MissionAuthorityEnvelope,
    ) -> None:
        """Apply *delta* to the hot cache for *mission_id*.

        Rejects deltas that would exceed envelope bounds or structural
        capacity constants. On rejection:
        - Emits ``AUTHORITY_VIOLATION`` with payload describing the
          violation.
        - Raises ``ValueError`` with a descriptive message.
        - Prior state is preserved (no partial application).

        On acceptance, dispatches to the appropriate ``HotMissionCache``
        method to mutate the view.
        """
        if delta.delta_type not in _VALID_DELTA_TYPES:
            raise ValueError(f"Unknown delta_type: {delta.delta_type}")

        # --- Bounds checks (before applying) ---
        self._check_bounds(mission_id, delta, envelope)

        # --- Dispatch to the appropriate cache method ---
        self._dispatch(mission_id, delta)

    # ------------------------------------------------------------------
    # Bounds checking
    # ------------------------------------------------------------------

    def _check_bounds(
        self,
        mission_id: str,
        delta: StateDelta,
        envelope: MissionAuthorityEnvelope,
    ) -> None:
        """Reject deltas that would exceed structural or authority-envelope bounds.

        Raises ``ValueError`` and emits ``AUTHORITY_VIOLATION`` on rejection.
        """
        view = self._hot_cache.get(mission_id)

        if delta.delta_type == "add_constraint":
            current_count = len(view.constraints) if view else 0
            if current_count >= MAX_CONSTRAINTS:
                self._reject(mission_id, delta)

        elif delta.delta_type == "push_action_summary":
            # Authority-envelope bounds check: mission cannot exceed its
            # authorized action count.
            action_count = self._hot_cache._action_count.get(mission_id, 0)
            if action_count >= envelope.max_actions:
                self._reject(mission_id, delta)

        elif delta.delta_type == "set_organ_state":
            current_count = len(view.organ_states) if view else 0
            # Only reject if we're adding a NEW key (not updating existing)
            if view and delta.payload.get("key") in view.organ_states:
                # Updating an existing key — always allowed.
                pass
            elif current_count >= MAX_ORGAN_STATES:
                self._reject(mission_id, delta)

        elif delta.delta_type == "add_blocker":
            current_count = len(view.blockers) if view else 0
            if current_count >= MAX_BLOCKERS:
                self._reject(mission_id, delta)

    def _reject(self, mission_id: str, delta: StateDelta) -> None:
        """Emit AUTHORITY_VIOLATION and raise ValueError."""
        self._event_bus.append(
            event_type=AgentEventType.AUTHORITY_VIOLATION,
            summary=(
                f"Delta rejected: {delta.delta_type} exceeds authority bounds "
                f"for mission {mission_id}"
            ),
            payload={
                "mission_id": mission_id,
                "delta_type": delta.delta_type,
                "reason": "exceeds_envelope_bounds",
            },
        )
        raise ValueError(
            f"Delta rejected: {delta.delta_type} exceeds authority bounds"
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, mission_id: str, delta: StateDelta) -> None:
        """Route the accepted delta to the correct HotMissionCache method."""
        if delta.delta_type == "set_objective":
            self._hot_cache.set_objective(mission_id, delta.payload["objective"])

        elif delta.delta_type == "add_constraint":
            view = self._hot_cache.get(mission_id)
            if view is None:
                # Ensure view exists before appending.
                self._hot_cache.set_constraints(mission_id, [delta.payload["constraint"]])
            else:
                updated = list(view.constraints)
                updated.append(delta.payload["constraint"])
                self._hot_cache.set_constraints(mission_id, updated)

        elif delta.delta_type == "add_blocker":
            # Ensure view exists, then append blocker directly.
            view = self._hot_cache.get(mission_id)
            if view is None:
                self._hot_cache.set_objective(mission_id, "")
                view = self._hot_cache.get(mission_id)
            assert view is not None
            view.blockers.append(delta.payload["blocker"])

        elif delta.delta_type == "push_action_summary":
            summary = ActionSummary(**delta.payload["summary"])
            self._hot_cache.push_action_summary(mission_id, summary)

        elif delta.delta_type == "set_organ_state":
            key = delta.payload["key"]
            value = delta.payload["value"]
            view = self._hot_cache.get(mission_id)
            if view is None:
                self._hot_cache.set_objective(mission_id, "")
                view = self._hot_cache.get(mission_id)
            assert view is not None
            view.organ_states[key] = value


__all__ = [
    "DeltaStateEngine",
    "StateDelta",
]
