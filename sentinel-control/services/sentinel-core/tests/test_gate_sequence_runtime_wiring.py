"""Tests for Task 6.5-A — GateSequence production-runtime wiring.

Validates that:

* :meth:`RiskRouter.route_via_sequence` now runs
  :meth:`GateSequence.evaluate` before the legacy
  :meth:`RiskRouter.route` path, and records the
  :class:`SequenceResult` on ``router.last_sequence_result`` so tests
  and audit tooling can observe the ordered gate trace.
* :class:`AutonomyEngine.decide` routes through the sequence by
  default — every production call site that went through
  ``autonomy.decide`` now traverses the 1→7 gate order first.
* The legacy ``RISK_ROUTE_DECIDED`` timeline event payload is
  preserved byte-for-byte (same fields, same values) so existing
  tests and FinalGate assertions continue to hold.
* A happy-path GREEN action still auto-executes — the wiring does not
  over-block.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.mission import (
    AutonomyEngine,
    MissionAction,
    MissionAuthorityEnvelope,
    MissionState,
    MissionTraceTimeline,
)
from sentinel.mission.gate_sequence import GateVerdict, SequenceResult
from sentinel.mission.risk import (
    GateSequenceRoutingError,
    RiskRouter,
    RouteDecision,
)
from sentinel.shared.enums import (
    ConfidenceLevel,
    ExternalityLevel,
    MissionActionRoute,
    MissionMode,
    MissionStatus,
    MissionTraceEventType,
    MissionType,
    ReversibilityLevel,
    SensitivityLevel,
)


# ---------------------------------------------------------------------------
# Shared fixtures.
# ---------------------------------------------------------------------------


SAFE_ACTIONS = [
    "create_project_folder",
    "create_markdown_file",
    "export_json",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_research_questions",
    "create_watchlist",
    "write_trace",
]


def _envelope(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "Task 6.5-A gate wiring",
        "mission_objective": "Exercise production gate wiring.",
        "success_criteria": ["smoke"],
        "mode": MissionMode.SAFE,
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": SAFE_ACTIONS,
        "forbidden_actions": ["send_email", "run_shell_command"],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _action(env: MissionAuthorityEnvelope, **overrides) -> MissionAction:
    data = {
        "mission_id": env.id,
        "action_type": "create_project_folder",
        "tool": "safe_file_writer",
        "intent": "wiring-smoke",
        "input": {},
        "expected_output": "folder",
        "target": "data/generated_projects/proj_test",
        "reversibility": ReversibilityLevel.LOCAL_WRITE_REVERSIBLE,
        "externality": ExternalityLevel.INTERNAL_LOCAL,
        "sensitivity": SensitivityLevel.INTERNAL,
        "confidence": ConfidenceLevel.HIGH,
        "estimated_cost": 0.05,
    }
    data.update(overrides)
    return MissionAction(**data)


def _state(env: MissionAuthorityEnvelope, **overrides) -> MissionState:
    data = {
        "mission_id": env.id,
        "status": MissionStatus.RUNNING,
        "cost_used": 0.0,
        "action_count": 0,
    }
    data.update(overrides)
    return MissionState(**data)


# ---------------------------------------------------------------------------
# 1. Router uses the gate sequence.
# ---------------------------------------------------------------------------


def test_risk_router_uses_gate_sequence_order(tmp_path: Path) -> None:
    """After ``route_via_sequence`` runs, the router exposes a
    :class:`SequenceResult` whose ``evaluated`` tuple is a prefix of
    the canonical SPINE order. For a GREEN action that reaches gate
    7, the full seven gates are recorded in order."""
    router = RiskRouter(project_root=tmp_path)
    env = _envelope()
    action = _action(env)
    state = _state(env)

    decision = router.route_via_sequence(env, state, action)

    assert router.last_sequence_result is not None
    result = router.last_sequence_result
    assert isinstance(result, SequenceResult)
    gate_names = tuple(gr.gate_name for gr in result.evaluated)
    # First two gates always run.
    assert gate_names[0] == "forbidden"
    assert gate_names[1] == "out_of_scope"
    # A clean GREEN action traverses all seven gates.
    assert result.terminal_verdict == GateVerdict.PASS
    assert gate_names == (
        "forbidden",
        "out_of_scope",
        "black_zone",
        "cost_exceeds_budget",
        "external_or_irreversible_or_sensitive",
        "unknown_tool_or_capability",
        "local_reversible_in_scope",
    )
    # Router still returned a legacy RouteDecision.
    assert isinstance(decision, RouteDecision)
    assert decision.route == MissionActionRoute.AUTO_EXECUTE


def test_autonomy_engine_decide_is_wired_through_sequence(tmp_path: Path) -> None:
    """``AutonomyEngine.decide`` — the canonical production call site
    in ``MissionRunner.run_mission`` — now routes through the
    sequence by default."""
    engine = AutonomyEngine(project_root=tmp_path)
    env = _envelope()
    action = _action(env)
    state = _state(env)

    engine.decide(env, state, action)

    assert engine.router.last_sequence_result is not None
    # The sequence observed gate 1 (forbidden) first.
    assert engine.router.last_sequence_result.evaluated[0].gate_name == "forbidden"


# ---------------------------------------------------------------------------
# 2. Short-circuit before later gates.
# ---------------------------------------------------------------------------


def test_runtime_route_short_circuits_before_later_gates(tmp_path: Path) -> None:
    """CP-6.2 at the production-runtime layer: if gate 1 (forbidden)
    BLOCKs, gates 2..7 do NOT run inside the sequence. The router's
    legacy BLOCK path is still emitted (preserving the timeline
    contract)."""
    env = _envelope()  # forbidden_actions includes "run_shell_command"
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)
    router = RiskRouter(project_root=tmp_path)

    decision = router.route_via_sequence(env, state, action)

    result = router.last_sequence_result
    assert result is not None
    assert result.terminal_verdict == GateVerdict.BLOCK
    assert tuple(gr.gate_name for gr in result.evaluated) == ("forbidden",)
    # Legacy router also returned BLOCK — consistency check passes.
    assert decision.route == MissionActionRoute.BLOCK


def test_black_zone_short_circuits_before_gate_4(tmp_path: Path) -> None:
    """Black-zone BLOCK at gate 3 prevents gates 4 (budget), 5
    (external/irreversible/sensitive), 6 (unknown tool), and 7 from
    running."""
    env = _envelope(
        forbidden_actions=[],  # bypass gate 1
        allowed_actions=["run_shell_command"],
        allowed_tools=["shell"],
    )
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)
    router = RiskRouter(project_root=tmp_path)

    router.route_via_sequence(env, state, action)

    result = router.last_sequence_result
    assert result is not None
    gate_names = tuple(gr.gate_name for gr in result.evaluated)
    # Gates 1, 2, 3 ran; 4..7 did not.
    assert gate_names == ("forbidden", "out_of_scope", "black_zone")
    assert result.terminal_verdict == GateVerdict.BLOCK


# ---------------------------------------------------------------------------
# 3. RISK_ROUTE_DECIDED timeline payload preserved.
# ---------------------------------------------------------------------------


def test_existing_risk_route_decided_event_preserved(tmp_path: Path) -> None:
    """The ``RISK_ROUTE_DECIDED`` event payload must carry the same
    fields the legacy :meth:`RiskRouter.route` has always emitted:
    ``route``, ``posture``, ``posture_level``, ``risk_score``,
    ``applied_threshold``, ``blocking_rule``, ``reasons``. Task 6.5-A
    wiring is additive — no field is removed, renamed, or reordered."""
    env = _envelope()  # forbidden_actions includes run_shell_command
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "trace")
    router = RiskRouter(project_root=tmp_path)

    router.route_via_sequence(env, state, action, timeline=timeline)

    risk_events = [
        e
        for e in timeline.events
        if e.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED
    ]
    assert risk_events, "RISK_ROUTE_DECIDED event missing after wiring."
    event = risk_events[-1]
    for required_field in (
        "route",
        "posture",
        "posture_level",
        "risk_score",
        "applied_threshold",
        "blocking_rule",
        "reasons",
    ):
        assert required_field in event.result, (
            f"RISK_ROUTE_DECIDED payload missing `{required_field}` after wiring."
        )
    # The blocking rule for a forbidden action is the existing
    # ``forbidden_or_black_zone`` label — unchanged by the wiring.
    assert event.result["blocking_rule"] == "forbidden_or_black_zone"
    assert event.result["route"] == MissionActionRoute.BLOCK.value


def test_risk_route_decided_is_emitted_exactly_once_per_decision(
    tmp_path: Path,
) -> None:
    """The wiring must not duplicate timeline events. One routing
    decision → one ``RISK_ROUTE_DECIDED`` event."""
    env = _envelope()
    action = _action(env)
    state = _state(env)
    timeline = MissionTraceTimeline(env.id, tmp_path / "data" / "trace2")
    router = RiskRouter(project_root=tmp_path)

    router.route_via_sequence(env, state, action, timeline=timeline)

    risk_events = [
        e
        for e in timeline.events
        if e.event_type == MissionTraceEventType.RISK_ROUTE_DECIDED
    ]
    assert len(risk_events) == 1, (
        f"Expected exactly one RISK_ROUTE_DECIDED event; got {len(risk_events)}."
    )


# ---------------------------------------------------------------------------
# 4. AutonomyEngine.decide still blocks black-zone action.
# ---------------------------------------------------------------------------


def test_autonomy_engine_decide_still_blocks_black_zone_action(
    tmp_path: Path,
) -> None:
    """Legacy contract preserved: an authority-forged mission that
    allows ``run_shell_command`` still BLOCKs at the autonomy layer
    because the black-zone set is terminal."""
    env = _envelope(
        forbidden_actions=[],
        allowed_actions=["run_shell_command"],
        allowed_tools=["shell"],
    )
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)

    engine = AutonomyEngine(project_root=tmp_path)
    decision = engine.decide(env, state, action)

    assert decision.route == MissionActionRoute.BLOCK
    assert decision.risk_score == 100.0
    assert decision.blocking_rule in {
        "forbidden_or_black_zone",
        "mission_identity_mismatch",  # never expected for this fixture
    }
    # Sequence also observed the BLOCK.
    result = engine.router.last_sequence_result
    assert result is not None
    assert result.terminal_verdict == GateVerdict.BLOCK


# ---------------------------------------------------------------------------
# 5. Green-path actions are not over-blocked by the wiring.
# ---------------------------------------------------------------------------


def test_gate_sequence_wiring_does_not_change_existing_route_for_green_action(
    tmp_path: Path,
) -> None:
    """A fully-compliant action that auto-executed pre-wiring still
    auto-executes post-wiring. The sequence is additive audit
    evidence; it does not over-block."""
    env = _envelope()
    action = _action(env)  # create_project_folder with valid target path
    state = _state(env)

    # Pre-wiring baseline: call `route` directly.
    baseline_router = RiskRouter(project_root=tmp_path)
    baseline_decision = baseline_router.route(env, state, action)

    # Post-wiring: call via sequence.
    wired_router = RiskRouter(project_root=tmp_path)
    wired_decision = wired_router.route_via_sequence(env, state, action)

    # The route/risk_score/reasons/blocking_rule must be identical.
    assert baseline_decision.route == wired_decision.route
    assert baseline_decision.risk_score == wired_decision.risk_score
    assert baseline_decision.blocking_rule == wired_decision.blocking_rule
    assert baseline_decision.reasons == wired_decision.reasons
    # Sanity: both routes are AUTO_EXECUTE.
    assert wired_decision.route == MissionActionRoute.AUTO_EXECUTE


def test_gate_sequence_wiring_preserves_route_for_out_of_scope_action(
    tmp_path: Path,
) -> None:
    """An out-of-scope action still ESCALATEs with the same
    :class:`RouteDecision` shape the legacy router produced."""
    env = _envelope()
    action = _action(env, action_type="not_in_allowed_actions")
    state = _state(env)

    baseline_router = RiskRouter(project_root=tmp_path)
    baseline_decision = baseline_router.route(env, state, action)

    wired_router = RiskRouter(project_root=tmp_path)
    wired_decision = wired_router.route_via_sequence(env, state, action)

    assert baseline_decision.route == wired_decision.route == MissionActionRoute.ESCALATE
    assert baseline_decision.blocking_rule == wired_decision.blocking_rule


def test_gate_sequence_wiring_preserves_budget_boundary_escalation(
    tmp_path: Path,
) -> None:
    """Budget-boundary ESCALATE behavior is preserved."""
    env = _envelope(max_cost_usd=1.0, max_actions=1)
    action = _action(env, estimated_cost=1.1)
    state = _state(env, cost_used=0.0)

    baseline_router = RiskRouter(project_root=tmp_path)
    baseline_decision = baseline_router.route(env, state, action)

    wired_router = RiskRouter(project_root=tmp_path)
    wired_decision = wired_router.route_via_sequence(env, state, action)

    assert baseline_decision.route == wired_decision.route == MissionActionRoute.ESCALATE
    assert baseline_decision.blocking_rule == wired_decision.blocking_rule


# ---------------------------------------------------------------------------
# 6. Consistency invariant — sequence/router verdicts agree.
# ---------------------------------------------------------------------------


def test_sequence_block_and_router_block_agree_on_forbidden(tmp_path: Path) -> None:
    env = _envelope()
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)
    router = RiskRouter(project_root=tmp_path)

    decision = router.route_via_sequence(env, state, action)

    assert router.last_sequence_result is not None
    assert router.last_sequence_result.terminal_verdict == GateVerdict.BLOCK
    assert decision.route == MissionActionRoute.BLOCK


def test_consistency_error_raised_on_manufactured_sequence_router_drift(
    tmp_path: Path,
) -> None:
    """If a caller forces a GateSequence BLOCK verdict while the
    router returns AUTO_EXECUTE, the consistency check raises
    :class:`GateSequenceRoutingError`. This is the failure mode the
    invariant catches at runtime."""
    from sentinel.mission.gate_sequence import GateResult, GateSequence

    env = _envelope()
    action = _action(env)
    state = _state(env)

    # Construct a single-gate sequence that returns BLOCK
    # unconditionally, but let the router believe the action is fine.
    def always_block(a, e, s):
        return GateResult(gate_name="synthetic", verdict=GateVerdict.BLOCK, reason="test")

    always_block.name = "synthetic"

    router = RiskRouter(project_root=tmp_path)
    router._gate_sequence = GateSequence(gates=[always_block])

    with pytest.raises(GateSequenceRoutingError) as excinfo:
        router.route_via_sequence(env, state, action)
    assert "BLOCK" in str(excinfo.value)
    assert "synthetic" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 7. last_sequence_result exposure.
# ---------------------------------------------------------------------------


def test_last_sequence_result_is_none_before_first_route_via_sequence_call(
    tmp_path: Path,
) -> None:
    router = RiskRouter(project_root=tmp_path)
    assert router.last_sequence_result is None


def test_last_sequence_result_persists_latest_call_only(tmp_path: Path) -> None:
    """Each ``route_via_sequence`` call overwrites the previous
    :class:`SequenceResult` — the property is "latest", not a buffer."""
    router = RiskRouter(project_root=tmp_path)
    env = _envelope()
    state = _state(env)

    router.route_via_sequence(env, state, _action(env))
    first = router.last_sequence_result
    assert first is not None
    assert first.terminal_verdict == GateVerdict.PASS

    router.route_via_sequence(
        env, state, _action(env, action_type="run_shell_command", tool="shell")
    )
    second = router.last_sequence_result
    assert second is not None
    assert second is not first
    assert second.terminal_verdict == GateVerdict.BLOCK
