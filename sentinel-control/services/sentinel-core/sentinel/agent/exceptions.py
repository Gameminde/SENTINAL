class MissionRevokedError(RuntimeError):
    """Raised when a run is attempted after mission authority was revoked."""


class AgentBlockedError(RuntimeError):
    """Raised when the agent core blocks execution before worker dispatch."""


class InvalidPhaseTransition(ValueError):
    """Raised when :meth:`AgentState.transition` rejects a phase change.

    Task 15 / F-A3.2 — Phase Self-Transition Guard. Subclasses
    :class:`ValueError` to preserve backward compatibility with existing
    callers that catch ``ValueError`` from ``state.transition(...)`` (the
    doctrine before Task 15 was to raise a plain ``ValueError`` with a
    human-readable message). New code SHOULD catch
    :class:`InvalidPhaseTransition` to distinguish phase-machine
    violations from other validation errors.
    """


# Task 13 / Requirement 13 — ``TraceIntegrityError`` now lives in
# ``sentinel.shared.events`` as a platform primitive. Re-exported here for
# backward compatibility with callers that do
# ``from sentinel.agent.exceptions import TraceIntegrityError``.
from sentinel.shared.events import TraceIntegrityError  # noqa: E402  (re-export)

__all__ = [
    "AgentBlockedError",
    "InvalidPhaseTransition",
    "MissionRevokedError",
    "TraceIntegrityError",
]
