"""Cognitive phase state-machine rules.

Task 13 / Requirement 13 — ``AgentPhase`` (the enum) now lives in
:mod:`sentinel.shared.events`. This module keeps the cognitive-cycle
helpers (``ALLOWED_PHASE_TRANSITIONS``, ``ABSORBING_PHASES``, and
``can_transition``) which encode Sentinel's cognitive state machine.

``AgentPhase`` is re-exported here for backward compatibility.
"""

from __future__ import annotations

from sentinel.shared.events import AgentPhase


ALLOWED_PHASE_TRANSITIONS: dict[AgentPhase, frozenset[AgentPhase]] = {
    AgentPhase.CREATED: frozenset({AgentPhase.INITIALIZED, AgentPhase.STOPPED, AgentPhase.BLOCKED}),
    AgentPhase.INITIALIZED: frozenset({AgentPhase.CONTEXT_BUILDING, AgentPhase.REVOKED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.CONTEXT_BUILDING: frozenset({AgentPhase.ORIENTING, AgentPhase.REVOKED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.ORIENTING: frozenset({AgentPhase.METHOD_SELECTING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.METHOD_SELECTING: frozenset({AgentPhase.CAPABILITY_SELECTING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.CAPABILITY_SELECTING: frozenset({AgentPhase.TOOL_SELECTING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.TOOL_SELECTING: frozenset({AgentPhase.HYPOTHESIS_VERIFYING, AgentPhase.LEARNING_PROPOSING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.HYPOTHESIS_VERIFYING: frozenset({AgentPhase.ACTION_SCORING, AgentPhase.LEARNING_PROPOSING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.ACTION_SCORING: frozenset({AgentPhase.EFFORT_ROUTING, AgentPhase.LEARNING_PROPOSING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.EFFORT_ROUTING: frozenset({AgentPhase.PLANNING, AgentPhase.LEARNING_PROPOSING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.PLANNING: frozenset({AgentPhase.PLAN_REVIEWING, AgentPhase.LEARNING_PROPOSING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.PLAN_REVIEWING: frozenset({AgentPhase.EXECUTING, AgentPhase.LEARNING_PROPOSING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.EXECUTING: frozenset({AgentPhase.ORGAN_DISPATCHING, AgentPhase.ARTIFACT_REVIEWING, AgentPhase.LEARNING_PROPOSING, AgentPhase.ESCALATED, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.ORGAN_DISPATCHING: frozenset({AgentPhase.ARTIFACT_REVIEWING, AgentPhase.LEARNING_PROPOSING, AgentPhase.ESCALATED, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.ARTIFACT_REVIEWING: frozenset({AgentPhase.SUCCESS_EVALUATING, AgentPhase.REPAIRING, AgentPhase.ESCALATED, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.REPAIRING: frozenset({AgentPhase.EXECUTING, AgentPhase.SUCCESS_EVALUATING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.SUCCESS_EVALUATING: frozenset({AgentPhase.LEARNING_PROPOSING, AgentPhase.REPAIRING, AgentPhase.PAUSED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
    AgentPhase.LEARNING_PROPOSING: frozenset({AgentPhase.COMPLETED, AgentPhase.ESCALATED, AgentPhase.STOPPED, AgentPhase.BLOCKED, AgentPhase.FAILED}),
}


ABSORBING_PHASES = {
    AgentPhase.COMPLETED,
    AgentPhase.ESCALATED,
    AgentPhase.PAUSED,
    AgentPhase.STOPPED,
    AgentPhase.REVOKED,
    AgentPhase.BLOCKED,
    AgentPhase.FAILED,
}


def can_transition(phase: AgentPhase, next_phase: AgentPhase) -> bool:
    if phase == next_phase:
        # Task 15 / F-A3.2: absorbing phases must not self-transition.
        # A terminal phase (COMPLETED/FAILED/BLOCKED/REVOKED/...) is a
        # dead end in the cognitive state machine by doctrine; allowing
        # a self-loop would mask that invariant and let runtime code
        # "re-complete" an already-completed mission or "re-block" an
        # already-blocked one, losing the distinction between a first
        # transition into the absorbing state and a spurious later one.
        if phase in ABSORBING_PHASES:
            return False
        return True
    if phase in ABSORBING_PHASES:
        return False
    return next_phase in ALLOWED_PHASE_TRANSITIONS.get(phase, frozenset())


__all__ = ["AgentPhase", "ALLOWED_PHASE_TRANSITIONS", "ABSORBING_PHASES", "can_transition"]
