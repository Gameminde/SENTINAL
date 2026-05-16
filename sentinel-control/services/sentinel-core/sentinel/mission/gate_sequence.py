"""Execution-gate sequence enforcer (Task 6 / F-A3.8 / Requirement 6).

SPINE_01 §5 mandates seven execution gates in a strict order. Today the
gates are correct individually but distributed across several
components (:class:`sentinel.organs.authority.OrganAuthorityEvaluator`,
:class:`sentinel.mission.scope_checker.MissionScopeChecker`,
:class:`sentinel.mission.budget.MissionBudgetController`,
:class:`sentinel.mission.risk.RiskRouter`,
:class:`sentinel.agent.capability_selector.CapabilitySelector`). There
is no single code location that proves a given action traversed them in
the specified 1→7 order — which is exactly what Requirement 6 asks for.

Module contract
---------------

This module introduces :class:`GateSequence` as the **single auditable
enforcer** for the seven-gate order. It is designed for both
integration wiring and property-level testing:

* **Deterministic ordering.** Gates are stored as an immutable tuple;
  :meth:`GateSequence.evaluate` iterates in order.
* **Short-circuit on BLOCK.** :data:`GateVerdict.BLOCK` is terminal —
  no later gate is evaluated, and the first BLOCK verdict is returned
  as the sequence verdict. :data:`GateVerdict.ESCALATE` and
  :data:`GateVerdict.REPORT_MISSING` are also terminal in the sense
  that they return the *first* non-PASS verdict, preserving SPINE_01's
  doctrine that "ESCALATE at gate N" is the mission's answer and
  downstream gates do not run.
* **No enforcement weakening.** Default gates delegate to existing
  production checkers (:class:`MissionScopeChecker`,
  :class:`MissionBudgetController`, etc.) — the sequence does not
  redefine what a black-zone action is; it only orders the calls.
* **Staged wiring.** The sequence is self-contained. Production
  runtime call sites (:meth:`MissionRunner.run_mission`,
  :meth:`AgentRuntime.run`) still route actions through
  :class:`RiskRouter` as today. A future sub-task may replace the
  distributed call-graph with :meth:`GateSequence.evaluate`; this
  module makes that possible without making it mandatory.

CP-6.1 (Gate Ordering):
    ∀ action A reaching execution:
        A traversed gates 1→2→3→4→5→6→7 in strict order.

CP-6.2 (Short-Circuit):
    ∀ gate G returning BLOCK:
        no subsequent gate is evaluated.

Canonical gate order (SPINE_01 §5)
----------------------------------

1. ``forbidden`` — ``action ∈ envelope.forbidden_actions`` → BLOCK
2. ``out_of_scope`` — ``action ∉ envelope.allowed_actions`` OR
   ``tool ∉ envelope.allowed_tools`` OR path outside
   ``envelope.allowed_paths`` → ESCALATE
3. ``black_zone`` — action/tool matches `BLACK_ZONE_ACTIONS` →
   BLOCK (terminal deny-of-last-resort, even if forbidden list was
   incomplete)
4. ``cost_exceeds_budget`` — ``MissionBudgetController`` reports
   exceeded → ESCALATE
5. ``external_or_irreversible_or_sensitive`` — action touches external
   systems, is irreversible, or carries sensitive data → ESCALATE
6. ``unknown_tool_or_capability`` — tool/capability is not in the
   registry → REPORT_MISSING
7. ``local_reversible_in_scope`` — the happy path → PASS, routes to
   AUTO_EXECUTE downstream
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Callable, Protocol

from sentinel.mission.budget import MissionBudgetController
from sentinel.mission.models import (
    MissionAction,
    MissionAuthorityEnvelope,
    MissionState,
)
from sentinel.mission.scope_checker import BLACK_ZONE_ACTIONS, MissionScopeChecker
from sentinel.shared.enums import (
    ConfidenceLevel,
    ExternalityLevel,
    ReversibilityLevel,
    SensitivityLevel,
)


# ---------------------------------------------------------------------------
# Verdict types.
# ---------------------------------------------------------------------------


class GateVerdict(StrEnum):
    """Outcome of a single gate evaluation.

    SPINE_01 §5 defines four verdicts:

    * ``PASS`` — the gate has no objection; continue to the next gate.
    * ``BLOCK`` — terminal deny. No later gate runs; the action is
      refused. This is the verdict for gates 1 (forbidden) and 3
      (black_zone).
    * ``ESCALATE`` — route to human or higher-authority review. No
      later gate runs. This is the verdict for gates 2 (out_of_scope),
      4 (budget), and 5 (external/irreversible/sensitive).
    * ``REPORT_MISSING`` — the tool or capability required by the
      action is not in the registry. No later gate runs. This is the
      verdict for gate 6.
    """

    PASS = "pass"
    BLOCK = "block"
    ESCALATE = "escalate"
    REPORT_MISSING = "report_missing"


TERMINAL_VERDICTS: frozenset[GateVerdict] = frozenset(
    {GateVerdict.BLOCK, GateVerdict.ESCALATE, GateVerdict.REPORT_MISSING}
)


@dataclass(frozen=True)
class GateResult:
    """Per-gate evaluation outcome.

    ``gate_name`` is the canonical gate identifier (e.g. ``"forbidden"``,
    ``"out_of_scope"``). ``verdict`` is the returned :class:`GateVerdict`.
    ``reason`` is a human-readable explanation; ``details`` is a
    structured payload for trace emission.
    """

    gate_name: str
    verdict: GateVerdict
    reason: str = ""
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SequenceResult:
    """Outcome of a full gate-sequence run.

    ``terminal_verdict`` is the verdict returned by the sequence (either
    ``PASS`` if every gate passed, or the first non-PASS verdict).
    ``evaluated`` lists every gate that actually ran, in order —
    including the terminating gate. Gates downstream of the
    short-circuit are NOT in this list.
    """

    terminal_verdict: GateVerdict
    evaluated: tuple[GateResult, ...]

    @property
    def blocking_gate(self) -> GateResult | None:
        """The gate that terminated the sequence, if any."""
        if self.terminal_verdict == GateVerdict.PASS:
            return None
        return self.evaluated[-1] if self.evaluated else None


# ---------------------------------------------------------------------------
# Gate protocol and callable type.
# ---------------------------------------------------------------------------


class Gate(Protocol):
    """Callable contract for a single gate.

    A gate receives the action, envelope, and mission state and returns
    a :class:`GateResult`. Gates MUST be pure with respect to the
    inputs (no global state mutation) so
    :meth:`GateSequence.evaluate` is deterministic.
    """

    name: str

    def __call__(
        self,
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        ...


GateCallable = Callable[
    [MissionAction, MissionAuthorityEnvelope, MissionState],
    GateResult,
]


# ---------------------------------------------------------------------------
# The sequence itself.
# ---------------------------------------------------------------------------


class GateSequence:
    """Ordered enforcer for the seven SPINE_01 execution gates.

    Usage::

        sequence = GateSequence.default(project_root=...)
        result = sequence.evaluate(action, envelope, state)
        if result.terminal_verdict == GateVerdict.PASS:
            ...  # auto-execute
        elif result.terminal_verdict == GateVerdict.BLOCK:
            ...  # refuse
        ...

    Custom gate lists are permitted for targeted tests; production
    call sites SHOULD always use :meth:`default` to ensure the
    canonical seven gates run.
    """

    def __init__(self, gates: list[GateCallable]) -> None:
        self._gates: tuple[GateCallable, ...] = tuple(gates)

    @property
    def gates(self) -> tuple[GateCallable, ...]:
        return self._gates

    def evaluate(
        self,
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> SequenceResult:
        """Run gates in order. Short-circuit on any non-PASS verdict.

        Returns a :class:`SequenceResult` whose ``evaluated`` tuple
        records every gate that actually ran (including the
        terminating gate). Gates downstream of the short-circuit are
        not in the list — that absence is what ``CP-6.2`` requires.
        """
        evaluated: list[GateResult] = []
        for gate in self._gates:
            outcome = gate(action, envelope, state)
            evaluated.append(outcome)
            if outcome.verdict != GateVerdict.PASS:
                return SequenceResult(
                    terminal_verdict=outcome.verdict,
                    evaluated=tuple(evaluated),
                )
        return SequenceResult(
            terminal_verdict=GateVerdict.PASS,
            evaluated=tuple(evaluated),
        )

    @classmethod
    def default(
        cls,
        *,
        project_root: str | Path | None = None,
        known_tools: set[str] | None = None,
    ) -> "GateSequence":
        """Construct the canonical seven-gate sequence.

        ``project_root`` is threaded into :class:`MissionScopeChecker`
        so path-scope checks resolve relative to the mission's
        project directory. ``known_tools``, if provided, is the
        registry used by gate 6 to detect unknown tools; if ``None``,
        gate 6 skips the unknown-tool check (it cannot invent a
        registry out of thin air and SHOULD NOT silently report every
        tool as missing).
        """
        scope_checker = MissionScopeChecker(project_root)
        budget_controller = MissionBudgetController()
        return cls(
            gates=[
                _forbidden_gate(scope_checker),
                _out_of_scope_gate(scope_checker),
                _black_zone_gate(scope_checker),
                _cost_exceeds_budget_gate(budget_controller),
                _external_or_irreversible_or_sensitive_gate(),
                _unknown_tool_or_capability_gate(known_tools),
                _local_reversible_in_scope_gate(),
            ]
        )


# ---------------------------------------------------------------------------
# Default gate implementations.
# ---------------------------------------------------------------------------
#
# Each default gate is a small closure over the production checker it
# delegates to. Closures carry ``.__name__`` for introspection; the
# module-level factories below assign ``gate.name`` explicitly so the
# sequence is auditable at runtime.


def _forbidden_gate(scope_checker: MissionScopeChecker) -> GateCallable:
    """Gate 1: explicit forbidden-action matching.

    ``envelope.forbidden_actions`` is a user-provided deny list. Any
    action in it is blocked with a terminal verdict — this is the
    mission-level deny-list, distinct from the system-wide
    black-zone set handled by gate 3.
    """

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        forbidden = {item.lower() for item in envelope.forbidden_actions}
        if action.action_type.lower() in forbidden or action.tool.lower() in forbidden:
            return GateResult(
                gate_name="forbidden",
                verdict=GateVerdict.BLOCK,
                reason="Action or tool is in envelope.forbidden_actions.",
                details={
                    "action_type": action.action_type,
                    "tool": action.tool,
                },
            )
        return GateResult(gate_name="forbidden", verdict=GateVerdict.PASS)

    gate.name = "forbidden"  # type: ignore[attr-defined]
    return gate


def _out_of_scope_gate(scope_checker: MissionScopeChecker) -> GateCallable:
    """Gate 2: action/tool/path within envelope scope.

    Out-of-scope actions escalate — they are not forbidden, merely
    not authorised for this mission, and a human reviewer may extend
    authority.
    """

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        if not scope_checker.is_in_scope(envelope, action):
            missing_reasons: list[str] = []
            if action.action_type not in envelope.allowed_actions:
                missing_reasons.append("action_type_not_allowed")
            if action.tool not in envelope.allowed_tools:
                missing_reasons.append("tool_not_allowed")
            if not scope_checker.is_path_in_scope(envelope, action):
                missing_reasons.append("path_not_in_scope")
            return GateResult(
                gate_name="out_of_scope",
                verdict=GateVerdict.ESCALATE,
                reason="Action is outside the mission authority envelope.",
                details={"reasons": missing_reasons},
            )
        return GateResult(gate_name="out_of_scope", verdict=GateVerdict.PASS)

    gate.name = "out_of_scope"  # type: ignore[attr-defined]
    return gate


def _black_zone_gate(scope_checker: MissionScopeChecker) -> GateCallable:
    """Gate 3: system-wide deny-of-last-resort for dangerous actions.

    This gate fires AFTER out_of_scope so that even if a mission
    author accidentally added ``run_shell_command`` to
    ``allowed_actions``, the black-zone set still catches it. The
    canonical set lives in
    :data:`sentinel.mission.scope_checker.BLACK_ZONE_ACTIONS`.
    """

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        if scope_checker.is_black_zone(action):
            return GateResult(
                gate_name="black_zone",
                verdict=GateVerdict.BLOCK,
                reason="Action or tool is in the system-wide black zone.",
                details={
                    "action_type": action.action_type,
                    "tool": action.tool,
                    "matching_term": next(
                        (
                            term
                            for term in BLACK_ZONE_ACTIONS
                            if term == action.action_type.lower()
                            or term == action.tool.lower()
                        ),
                        None,
                    ),
                },
            )
        return GateResult(gate_name="black_zone", verdict=GateVerdict.PASS)

    gate.name = "black_zone"  # type: ignore[attr-defined]
    return gate


def _cost_exceeds_budget_gate(
    budget: MissionBudgetController,
) -> GateCallable:
    """Gate 4: mission budget controller.

    Delegates to :meth:`MissionBudgetController.evaluate`. If the
    controller reports ``allowed=False``, the action escalates.
    """

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        decision = budget.evaluate(envelope, state, action)
        if not decision.allowed:
            return GateResult(
                gate_name="cost_exceeds_budget",
                verdict=GateVerdict.ESCALATE,
                reason="; ".join(decision.reasons)
                or "Mission budget would be exceeded.",
                details={
                    "exceeded": decision.exceeded,
                    "estimated_cost": action.estimated_cost,
                    "cost_used": state.cost_used,
                    "max_cost_usd": envelope.max_cost_usd,
                    "action_count": state.action_count,
                    "max_actions": envelope.max_actions,
                },
            )
        return GateResult(
            gate_name="cost_exceeds_budget", verdict=GateVerdict.PASS
        )

    gate.name = "cost_exceeds_budget"  # type: ignore[attr-defined]
    return gate


def _external_or_irreversible_or_sensitive_gate() -> GateCallable:
    """Gate 5: escalate actions with high blast-radius properties.

    An action escalates if ANY of:

    * externality is EXTERNAL_PRIVATE or EXTERNAL_PUBLIC,
    * reversibility is IRREVERSIBLE,
    * sensitivity is PERSONAL, SECRET, FINANCIAL, or IDENTITY.

    Missions that need to send external traffic or mutate
    irreversible state are not forbidden — they are merely required
    to pass through human review instead of auto-executing.
    """

    external_levels = {ExternalityLevel.EXTERNAL_PRIVATE, ExternalityLevel.EXTERNAL_PUBLIC}
    sensitive_levels = {
        SensitivityLevel.PERSONAL,
        SensitivityLevel.SECRET,
        SensitivityLevel.FINANCIAL,
        SensitivityLevel.IDENTITY,
    }

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        triggers: list[str] = []
        if action.externality in external_levels:
            triggers.append(f"externality:{action.externality.value}")
        if action.reversibility == ReversibilityLevel.IRREVERSIBLE:
            triggers.append("reversibility:irreversible")
        if action.sensitivity in sensitive_levels:
            triggers.append(f"sensitivity:{action.sensitivity.value}")
        if triggers:
            return GateResult(
                gate_name="external_or_irreversible_or_sensitive",
                verdict=GateVerdict.ESCALATE,
                reason="Action carries high blast-radius properties requiring review.",
                details={"triggers": triggers},
            )
        return GateResult(
            gate_name="external_or_irreversible_or_sensitive",
            verdict=GateVerdict.PASS,
        )

    gate.name = "external_or_irreversible_or_sensitive"  # type: ignore[attr-defined]
    return gate


def _unknown_tool_or_capability_gate(
    known_tools: set[str] | None,
) -> GateCallable:
    """Gate 6: reject actions that reference unknown tools.

    If ``known_tools`` is ``None`` the gate PASSes — the sequence
    cannot invent a tool registry, and silently REPORT_MISSING on
    every action would defeat the rest of the sequence. Production
    call sites SHOULD supply a known-tools set built from the
    capability registry.
    """

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        if known_tools is None:
            return GateResult(
                gate_name="unknown_tool_or_capability",
                verdict=GateVerdict.PASS,
                reason="known_tools registry not supplied; gate is a no-op.",
            )
        if action.tool not in known_tools:
            return GateResult(
                gate_name="unknown_tool_or_capability",
                verdict=GateVerdict.REPORT_MISSING,
                reason=f"Tool `{action.tool}` is not in the capability registry.",
                details={"tool": action.tool, "known_tools_count": len(known_tools)},
            )
        return GateResult(
            gate_name="unknown_tool_or_capability", verdict=GateVerdict.PASS
        )

    gate.name = "unknown_tool_or_capability"  # type: ignore[attr-defined]
    return gate


def _local_reversible_in_scope_gate() -> GateCallable:
    """Gate 7: the happy path.

    By the time an action reaches gate 7, every safety gate has
    passed. This gate PASSes unconditionally — its role is to exist
    at the correct position so the sequence always has seven gates,
    and so future hardening (e.g. an "idempotency check") has a
    natural slot.
    """

    def gate(
        action: MissionAction,
        envelope: MissionAuthorityEnvelope,
        state: MissionState,
    ) -> GateResult:
        return GateResult(
            gate_name="local_reversible_in_scope",
            verdict=GateVerdict.PASS,
            reason="Action cleared all six prior gates.",
        )

    gate.name = "local_reversible_in_scope"  # type: ignore[attr-defined]
    return gate


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

__all__ = [
    "Gate",
    "GateCallable",
    "GateResult",
    "GateSequence",
    "GateVerdict",
    "SequenceResult",
    "TERMINAL_VERDICTS",
]
