"""Tests for Task 15 / F-A3.2 — Phase Self-Transition Guard.

These tests freeze the doctrine that absorbing phases (COMPLETED,
FAILED, BLOCKED, ESCALATED, PAUSED, STOPPED, REVOKED) are terminal and
cannot self-transition. Non-absorbing phases retain the pre-existing
doctrine of permitting self-transition (idempotent re-entry into a
mid-cycle phase is legal; the state-machine's ``ALLOWED_PHASE_TRANSITIONS``
mapping enumerates only forward transitions, so self-transition on a
non-absorbing phase is a default-allow by ``can_transition``).

AgentState.transition now raises :class:`InvalidPhaseTransition` rather
than a bare ``ValueError``. The exception subclasses ``ValueError`` so
any pre-Task-15 caller that did ``except ValueError`` continues to work
untouched.
"""

from __future__ import annotations

import pytest

from sentinel.agent.exceptions import InvalidPhaseTransition
from sentinel.agent.phases import ABSORBING_PHASES, AgentPhase, can_transition
from sentinel.agent.state import AgentState


# ---------------------------------------------------------------------------
# Absorbing self-transition is rejected.
# ---------------------------------------------------------------------------


def test_completed_to_completed_rejected():
    assert can_transition(AgentPhase.COMPLETED, AgentPhase.COMPLETED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.COMPLETED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.COMPLETED)


def test_failed_to_failed_rejected():
    assert can_transition(AgentPhase.FAILED, AgentPhase.FAILED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.FAILED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.FAILED)


def test_blocked_to_blocked_rejected():
    assert can_transition(AgentPhase.BLOCKED, AgentPhase.BLOCKED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.BLOCKED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.BLOCKED)


def test_escalated_to_escalated_rejected():
    assert can_transition(AgentPhase.ESCALATED, AgentPhase.ESCALATED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.ESCALATED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.ESCALATED)


def test_paused_to_paused_rejected():
    assert can_transition(AgentPhase.PAUSED, AgentPhase.PAUSED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.PAUSED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.PAUSED)


def test_stopped_to_stopped_rejected():
    assert can_transition(AgentPhase.STOPPED, AgentPhase.STOPPED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.STOPPED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.STOPPED)


def test_revoked_to_revoked_rejected():
    assert can_transition(AgentPhase.REVOKED, AgentPhase.REVOKED) is False

    state = AgentState(mission_id="mission_001", phase=AgentPhase.REVOKED)
    with pytest.raises(InvalidPhaseTransition):
        state.transition(AgentPhase.REVOKED)


def test_absorbing_self_transition_rejected_for_every_absorbing_phase():
    """Guard against future additions to ABSORBING_PHASES silently
    becoming self-transition-eligible. If a maintainer adds a new
    absorbing phase, this loop enforces the doctrine without requiring
    a new hand-written test."""
    for phase in ABSORBING_PHASES:
        assert can_transition(phase, phase) is False, (
            f"Absorbing phase {phase} must not self-transition."
        )
        state = AgentState(mission_id="mission_001", phase=phase)
        with pytest.raises(InvalidPhaseTransition):
            state.transition(phase)


# ---------------------------------------------------------------------------
# Non-absorbing self-transition is still allowed (doctrine preserved).
# ---------------------------------------------------------------------------


def test_non_absorbing_self_transition_allowed():
    """Non-absorbing phases may self-transition. This is the pre-Task-15
    doctrine and is explicitly preserved: Task 15's scope is to reject
    *absorbing* self-transitions only."""
    assert can_transition(AgentPhase.CONTEXT_BUILDING, AgentPhase.CONTEXT_BUILDING) is True

    state = AgentState(mission_id="mission_001", phase=AgentPhase.CONTEXT_BUILDING)
    transitioned = state.transition(AgentPhase.CONTEXT_BUILDING)
    assert transitioned.phase == AgentPhase.CONTEXT_BUILDING


def test_every_non_absorbing_phase_permits_self_transition():
    """Declarative sweep: the complement of ABSORBING_PHASES must
    permit self-transition on both ``can_transition`` and
    ``AgentState.transition`` paths. This ensures the guard narrowly
    targets absorbing phases and does not bleed into the cognitive
    cycle."""
    non_absorbing = [phase for phase in AgentPhase if phase not in ABSORBING_PHASES]
    assert non_absorbing, "Sanity: there must be at least one non-absorbing phase."

    for phase in non_absorbing:
        assert can_transition(phase, phase) is True, (
            f"Non-absorbing phase {phase} must permit self-transition."
        )
        state = AgentState(mission_id="mission_001", phase=phase)
        transitioned = state.transition(phase)
        assert transitioned.phase == phase


# ---------------------------------------------------------------------------
# Exception hierarchy — backward compatibility.
# ---------------------------------------------------------------------------


def test_invalid_phase_transition_is_value_error_subclass():
    """Pre-Task-15 callers that do ``except ValueError`` around
    ``state.transition(...)`` MUST keep working. Subclassing
    ``ValueError`` is the non-regressive design choice."""
    assert issubclass(InvalidPhaseTransition, ValueError)


def test_invalid_phase_transition_caught_by_value_error_clause():
    """Integration check for the backward-compat contract: catching
    ``ValueError`` still intercepts the new exception type."""
    state = AgentState(mission_id="mission_001", phase=AgentPhase.COMPLETED)
    with pytest.raises(ValueError) as excinfo:
        state.transition(AgentPhase.COMPLETED)
    assert isinstance(excinfo.value, InvalidPhaseTransition)


def test_invalid_phase_transition_message_names_both_phases():
    """The diagnostic carries both source and destination phase so
    ``state.transition`` failures remain grep-able in logs."""
    state = AgentState(mission_id="mission_001", phase=AgentPhase.COMPLETED)
    with pytest.raises(InvalidPhaseTransition) as excinfo:
        state.transition(AgentPhase.COMPLETED)
    message = str(excinfo.value)
    assert "completed" in message.lower()
