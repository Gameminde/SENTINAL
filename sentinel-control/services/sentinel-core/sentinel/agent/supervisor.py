from __future__ import annotations

from sentinel.agent.event_bus import EventBus
from sentinel.agent.exceptions import MissionRevokedError
from sentinel.agent.invariants import InvariantChecker, InvariantViolation
from sentinel.agent.models import AgentContext, CapabilityNeed, LearningProposal
from sentinel.agent.state import AgentState
from sentinel.mission.models import MissionAuthorityEnvelope


class Supervisor:
    def __init__(self, invariants: InvariantChecker | None = None) -> None:
        self.invariants = invariants or InvariantChecker()

    def assert_mission_can_run(self, context: AgentContext) -> None:
        if context.mission.revoked_at is not None:
            raise MissionRevokedError("Mission authority has been revoked.")

    def assert_context_did_not_expand_authority(
        self,
        context: AgentContext,
        *,
        envelope: MissionAuthorityEnvelope | None = None,
        original_allowed_actions: tuple[str, ...] | None = None,
        boundary_name: str | None = None,
    ) -> None:
        """Assert that context/memory has not expanded mission authority.

        Requirement 2 — Memory-not-Authority Multi-Phase Enforcement.

        Parameters
        ----------
        context
            The *current* agent context. ``context.available_capabilities`` is
            the thing being validated.
        envelope
            The mission authority envelope to use as the source of truth. When
            omitted (the legacy CONTEXT_BUILDING call site), falls back to
            ``context.mission`` so existing callers keep working.
        original_allowed_actions
            The set of allowed actions captured at run entry. When provided,
            the check enforces that neither the current envelope nor the
            current context capabilities have grown beyond that original set.
            This is what makes the check resistant to mid-run mutation of
            ``context.mission.allowed_actions``.
        boundary_name
            If provided, the boundary label is prepended to any
            ``InvariantViolation`` message so the offending transition is
            identifiable in traces.
        """
        authority = envelope if envelope is not None else context.mission
        original_list = list(original_allowed_actions) if original_allowed_actions is not None else None
        try:
            # Drift check on the authority source: current envelope's
            # allowed_actions must remain a subset of the original authorised
            # set. No-op in the legacy path (original_list is None).
            self.invariants.check_memory_not_authority(
                authority,
                list(authority.allowed_actions),
                original_allowed_actions=original_list,
            )
            # Task 2.4-A Gap 1 fix: drift check on ``context.mission`` itself.
            # When an explicit ``envelope`` is supplied the authority-side
            # check above only inspects the pristine envelope. If
            # ``context.mission.allowed_actions`` has been mutated post
            # context-build (memory/capability-selector contamination,
            # reviewer side-channels, etc.), the envelope check alone cannot
            # see the drift. This second check makes the boundary re-check
            # detect context.mission widening even when the supplied
            # envelope stays clean. Only runs in drift-mode
            # (original_list is not None); legacy single-arg callers are
            # unaffected.
            if original_list is not None and context.mission is not authority:
                self.invariants.check_memory_not_authority(
                    context.mission,
                    list(context.mission.allowed_actions),
                    original_allowed_actions=original_list,
                )
            # Derivation check: current available capabilities must derive from
            # the original (not possibly-mutated) authority.
            self.invariants.check_capabilities_derive_from_authority(
                authority,
                context.available_capabilities,
                original_allowed_actions=original_list,
            )
        except InvariantViolation as exc:
            if boundary_name is not None:
                raise InvariantViolation(f"{boundary_name}: {exc}") from exc
            raise

    def assert_capabilities_are_declared(self, needs: list[CapabilityNeed]) -> None:
        self.invariants.check_capability_declarations(needs)

    def assert_learning_is_safe(self, proposals: list[LearningProposal]) -> None:
        self.invariants.check_learning_proposals(proposals)

    def assert_completion(self, state: AgentState, mission_result) -> None:
        self.invariants.check_completion(state, mission_result)

    def assert_state_bounds(self, state: AgentState) -> None:
        self.invariants.check_bounded_repair(state)

    def assert_trace_integrity(self, event_bus: EventBus) -> None:
        self.invariants.check_trace_chain(event_bus)
