from __future__ import annotations

"""Runtime invariants for the Sentinel cognitive agent.

This module owns the executable form of the SPINE_01 invariants enforced by
:class:`InvariantChecker`. Each method here encodes one named invariant:

* ``check_trace_chain`` — the agent event hash chain on
  :class:`~sentinel.agent.event_bus.EventBus` verifies.
* ``check_memory_not_authority`` — memory, context, and any in-flight
  envelope mutation cannot expand mission authority past the set captured at
  run entry (see the multi-phase contract below).
* ``check_capabilities_derive_from_authority`` — any capability surfaced to
  the agent is derivable from the *original* authorised actions, not from a
  (possibly mutated) live envelope.
* ``check_capability_declarations`` — missing capabilities must declare a
  reason.
* ``check_completion`` — the agent may only enter ``COMPLETED`` with a
  successful :class:`~sentinel.mission.models.MissionRunResult`.
* ``check_learning_proposals`` — learning proposals always require human
  approval before being applied.
* ``check_improvement_proposals`` — self-improvement proposals with
  ``status == "approved"`` must carry a non-empty
  ``approved_by_human_id`` (Task 14 / F-A3.7 approval-token).
* ``check_bounded_repair`` — repair cycles are bounded by the agent state.

Where authority is enforced — canonical chokepoints
----------------------------------------------------

Task 10 / F-A3.1 — a previous ``check_authority`` method on this class has
been removed as dead safety code. The real enforcement of "is this
action/tool pair inside the mission authority envelope?" lives in two
layers that are both always-on in production:

1. :meth:`sentinel.mission.risk.RiskRouter.route` (called by
   :meth:`sentinel.mission.autonomy.AutonomyEngine.decide`) checks the
   exact pair via :meth:`sentinel.mission.scope_checker.MissionScopeChecker.is_in_scope`
   plus a strictly stronger set of rules (forbidden-action matching,
   black-zone action terms, path scope, revocation / expiry, budget,
   posture). Out-of-scope actions route to ``ESCALATE``; forbidden /
   black-zone / revoked / expired actions route to ``BLOCK``.
2. :class:`sentinel.organs.authority.OrganAuthorityEvaluator` applies an
   organ-scoped authority envelope with matching requested-action
   semantics for organ adapters.

Additionally, :meth:`check_memory_not_authority` and
:meth:`check_capabilities_derive_from_authority` run at every cognitive
phase boundary (Task 2) to block drift against
``original_allowed_actions`` captured at run entry. A separate naive
``check_authority`` on this class would duplicate the router's check
one function-call earlier, use a weaker authority source (live envelope
instead of originals), and risk creating a false sense that authority
is enforced here rather than at the router.

Multi-phase enforcement contract — Memory-not-Authority
--------------------------------------------------------

Requirement 2 (Memory-not-Authority Multi-Phase Enforcement) specifies that
``check_memory_not_authority`` and ``check_capabilities_derive_from_authority``
are **not** one-shot checks at context-building time. They are re-invoked at
each cognitive phase boundary inside
:meth:`sentinel.agent.runtime.AgentRuntime.run` through the helper
``AgentRuntime._assert_memory_not_authority_boundary``, which delegates to
:meth:`sentinel.agent.supervisor.Supervisor.assert_context_did_not_expand_authority`.

The nine boundaries currently wired are:

1. ``context_building → orienting``
2. ``orienting → method_selecting``
3. ``method_selecting → capability_selecting``
4. ``capability_selecting → tool_selecting``
5. ``tool_selecting → hypothesis_verifying``
6. ``hypothesis_verifying → action_scoring``
7. ``effort_routing → planning``
8. ``plan_reviewing → executing``
9. ``repairing → executing``

At each boundary the supervisor compares both ``envelope.allowed_actions`` and
``context.mission.allowed_actions`` against the ``original_allowed_actions``
snapshot captured at run entry, and then verifies that
``context.available_capabilities`` is still derivable from that original
authority via ``capabilities_from_actions``. Any drift raises
:class:`InvariantViolation` prefixed with the boundary name (e.g.
``"context_building→orienting: ..."``).

Violations propagate out of the phase handler and are caught by the
``except Exception`` path in :meth:`AgentRuntime.run`, which hands the run to
the final-gate helper ``_apply_final_gate`` (Requirement 1) so the run exits
as a certified BLOCKED result rather than an uncertified error.
"""

from sentinel.agent.capability_selector import capabilities_from_actions
from sentinel.agent.event_bus import EventBus
from sentinel.agent.models import CapabilityNeed, LearningProposal
from sentinel.agent.phases import AgentPhase
from sentinel.agent.state import AgentState
from sentinel.mission.models import MissionAction, MissionAuthorityEnvelope, MissionRunResult

# Task 14 / F-A3.7: ImprovementProposal lives in the learning layer.
# Use a string annotation + runtime-imported type for the invariant
# method signature so the agent layer does not eagerly import from the
# learning layer at module load. The invariant body only reads the
# ``status`` and ``approved_by_human_id`` attributes, so duck-typing on
# the pydantic model works without a hard import.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel.learning.self_improvement import ImprovementProposal


class InvariantViolation(ValueError):
    """Raised when a Sentinel agent invariant is violated."""


class InvariantChecker:
    """Executable SPINE_01 invariants for the cognitive runtime.

    Methods on this class encode one invariant each (see module docstring for
    the full list). The Memory-not-Authority pair
    (:meth:`check_memory_not_authority` + :meth:`check_capabilities_derive_from_authority`)
    operates in two modes — **drift mode** (multi-phase, keyed on
    ``original_allowed_actions`` captured at run entry) and **legacy mode**
    (one-shot at CONTEXT_BUILDING, kept for backward compatibility).

    Production call sites:

    * :meth:`sentinel.agent.supervisor.Supervisor.assert_context_did_not_expand_authority`
      invokes both Memory-not-Authority methods on every phase boundary.
    * :meth:`sentinel.agent.runtime.AgentRuntime._assert_memory_not_authority_boundary`
      is the thin wrapper that threads ``original_allowed_actions`` and
      ``boundary_name`` through to the supervisor.

    Violation semantics: each method raises :class:`InvariantViolation` on
    breach. The supervisor prefixes boundary-originated violations with the
    boundary name; the ``except Exception`` handler in
    :meth:`AgentRuntime.run` converts the violation into a certified BLOCKED
    result via Task 1's ``_apply_final_gate``.
    """

    def check_authority(self, envelope: MissionAuthorityEnvelope, action: MissionAction) -> None:
        # Task 10 / F-A3.1 — intentionally retained as an error stub.
        #
        # The original implementation duplicated
        # :meth:`sentinel.mission.scope_checker.MissionScopeChecker.is_in_scope`
        # and had zero production call sites. Removing the method name
        # would be more aggressive; we keep the name so that any older
        # integration that still imports or calls it fails loudly with
        # a diagnostic pointing at the canonical chokepoint. The method
        # MUST NOT be reintroduced as a live check without a clear
        # statement of what class of bugs it catches that the router,
        # the organ authority evaluator, and the Memory-not-Authority
        # multi-phase checks do not already catch.
        raise NotImplementedError(
            "InvariantChecker.check_authority has been removed "
            "(Task 10 / F-A3.1). Authority enforcement lives in "
            "sentinel.mission.risk.RiskRouter.route (via "
            "MissionScopeChecker.is_in_scope) and "
            "sentinel.organs.authority.OrganAuthorityEvaluator. "
            "Use MissionScopeChecker.is_in_scope if a standalone "
            "check is needed."
        )

    def check_trace_chain(self, event_bus: EventBus) -> None:
        if not event_bus.verify_chain():
            raise InvariantViolation("Agent event hash chain verification failed.")

    def check_memory_not_authority(
        self,
        envelope: MissionAuthorityEnvelope,
        context_allowed_actions: list[str] | None = None,
        *,
        original_allowed_actions: list[str] | None = None,
    ) -> None:
        """Verify that mission authority has not been expanded by context/memory.

        Requirement 2 — Memory-not-Authority Multi-Phase Enforcement.

        Two modes:

        1. **Drift mode** (``original_allowed_actions`` provided): compares the
           ``envelope.allowed_actions`` captured at re-check time against the
           ``original_allowed_actions`` captured at run entry. If the current
           envelope has grown past the original set, the context or memory has
           mutated the envelope in-flight and we must block. This is the
           multi-phase enforcement path wired at every phase boundary by
           :class:`sentinel.agent.supervisor.Supervisor`.

        2. **Legacy mode** (``original_allowed_actions`` is ``None``): compares
           the provided ``context_allowed_actions`` against
           ``envelope.allowed_actions``. Preserved for backward compatibility
           with existing callers and tests.
        """
        if original_allowed_actions is not None:
            current = set(envelope.allowed_actions)
            original = set(original_allowed_actions)
            if not current.issubset(original):
                raise InvariantViolation(
                    "Context or memory attempted to expand mission authority "
                    "beyond the actions authorised at run entry."
                )
            return

        proposed = set(context_allowed_actions or [])
        allowed = set(envelope.allowed_actions)
        if not proposed.issubset(allowed):
            raise InvariantViolation("Context or memory attempted to expand mission authority.")

    def check_capabilities_derive_from_authority(
        self,
        envelope: MissionAuthorityEnvelope,
        context_capabilities: list[str] | None = None,
        *,
        original_allowed_actions: list[str] | None = None,
    ) -> None:
        """Verify that ``context_capabilities`` derive from mission authority.

        When ``original_allowed_actions`` is provided the capability set is
        derived from those (captured at run entry) rather than from the
        possibly-mutated ``envelope.allowed_actions``. This ensures the check
        cannot be bypassed by mutating the envelope mid-run.
        """
        proposed = set(context_capabilities or [])
        authority_actions = (
            list(original_allowed_actions)
            if original_allowed_actions is not None
            else list(envelope.allowed_actions)
        )
        allowed = set(capabilities_from_actions(authority_actions))
        if not proposed.issubset(allowed):
            raise InvariantViolation("Context or memory attempted to add capabilities outside mission authority.")

    def check_capability_declarations(self, needs: list[CapabilityNeed]) -> None:
        for need in needs:
            if not need.available and not need.missing_reason:
                raise InvariantViolation(f"Missing capability `{need.name}` must explain why it is unavailable.")

    def check_completion(self, state: AgentState, mission_result: MissionRunResult | None) -> None:
        if state.phase == AgentPhase.COMPLETED and (mission_result is None or not mission_result.success):
            raise InvariantViolation("Agent cannot complete without a successful mission result.")

    def check_learning_proposals(self, proposals: list[LearningProposal]) -> None:
        for proposal in proposals:
            if not proposal.requires_human_approval:
                raise InvariantViolation("Learning proposals must require human approval.")

    def check_improvement_proposals(
        self,
        proposals: "list[ImprovementProposal]",
    ) -> None:
        """Enforce Task 14 / F-A3.7 approval-token invariant.

        An :class:`ImprovementProposal` with ``status == "approved"`` MUST
        carry a non-empty ``approved_by_human_id``. While the pydantic
        ``@model_validator`` on the model already rejects invalid
        constructions at the schema layer, this invariant is called from
        the runtime's supervisor path (as a belt-and-braces check) so
        that if a proposal is ever reconstituted from a persistence
        store or a non-validated dict-style path, the doctrine still
        holds. ``requires_human_approval`` semantics for
        :class:`LearningProposal` are kept separate in
        :meth:`check_learning_proposals` — the two proposal types carry
        different contracts and must not be conflated.
        """
        for proposal in proposals:
            if proposal.status != "approved":
                continue
            token = proposal.approved_by_human_id
            if token is None or (isinstance(token, str) and not token.strip()):
                raise InvariantViolation(
                    "ImprovementProposal with status='approved' must carry "
                    "a non-empty approved_by_human_id."
                )

    def check_bounded_repair(self, state: AgentState) -> None:
        if state.repair_cycles > state.max_repair_cycles:
            raise InvariantViolation("Repair cycles exceeded the configured bound.")
