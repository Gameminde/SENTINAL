"""Tests for Task 6 / F-A3.8 / Requirement 6 — Execution Gate Ordering.

Locks in two correctness properties:

* **CP-6.1 (Gate Ordering):** For every action reaching the sequence,
  the gates execute in strict order 1→2→3→4→5→6→7.
* **CP-6.2 (Short-Circuit):** When any gate returns a non-PASS
  verdict, no downstream gate is evaluated.

The tests exercise both (a) the canonical default sequence constructed
from production checkers and (b) synthetic gate lists that make
ordering and short-circuit failures observable at the call-counter
level.
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from sentinel.mission.gate_sequence import (
    Gate,
    GateResult,
    GateSequence,
    GateVerdict,
    SequenceResult,
    TERMINAL_VERDICTS,
)
from sentinel.mission.models import (
    MissionAction,
    MissionAuthorityEnvelope,
    MissionState,
)
from sentinel.shared.enums import (
    ConfidenceLevel,
    ExternalityLevel,
    MissionMode,
    MissionStatus,
    MissionType,
    ReversibilityLevel,
    SensitivityLevel,
)


# ---------------------------------------------------------------------------
# Fixtures — small, explicit, reusable.
# ---------------------------------------------------------------------------


def _envelope(**overrides) -> MissionAuthorityEnvelope:
    data = {
        "user_id": "user_test",
        "mission_type": MissionType.GTM,
        "mission_title": "Task 6 gate sequence",
        "mission_objective": "Exercise gate ordering.",
        "mode": MissionMode.SAFE,
        "allowed_tools": ["safe_file_writer"],
        # ``benign_in_memory_computation`` is NOT in
        # ``PATH_SCOPED_LOCAL_ACTIONS`` so the scope checker treats it
        # as path-free; this keeps the happy-path test focused on the
        # seven gates rather than on path-scope plumbing.
        "allowed_actions": ["benign_in_memory_computation"],
        "forbidden_actions": ["run_shell_command"],
        "max_cost_usd": 5.0,
        "max_actions": 10,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _action(env: MissionAuthorityEnvelope, **overrides) -> MissionAction:
    data = {
        "mission_id": env.id,
        "action_type": "benign_in_memory_computation",
        "tool": "safe_file_writer",
        "intent": "smoke",
        "expected_output": "result",
        "reversibility": ReversibilityLevel.LOCAL_WRITE_REVERSIBLE,
        "externality": ExternalityLevel.INTERNAL_LOCAL,
        "sensitivity": SensitivityLevel.INTERNAL,
        "confidence": ConfidenceLevel.HIGH,
        "estimated_cost": 0.1,
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
# Synthetic gate infrastructure — lets tests observe call ordering.
# ---------------------------------------------------------------------------


@dataclass
class _Recorder:
    """Shared buffer for synthetic gates to record their call order."""

    calls: list[str] = field(default_factory=list)


def _fake_gate(name: str, verdict: GateVerdict, recorder: _Recorder):
    """Return a callable that records its name and emits a fixed verdict."""

    def gate(action, envelope, state):
        recorder.calls.append(name)
        return GateResult(
            gate_name=name,
            verdict=verdict,
            reason=f"fake gate {name}",
        )

    gate.name = name  # type: ignore[attr-defined]
    return gate


# ---------------------------------------------------------------------------
# CP-6.1 — gates execute in SPINE order on the default sequence.
# ---------------------------------------------------------------------------


SPINE_ORDER = (
    "forbidden",
    "out_of_scope",
    "black_zone",
    "cost_exceeds_budget",
    "external_or_irreversible_or_sensitive",
    "unknown_tool_or_capability",
    "local_reversible_in_scope",
)


def test_default_sequence_has_exactly_seven_gates_in_spine_order():
    """CP-6.1: the canonical default sequence has the seven gates
    named and ordered exactly as SPINE_01 §5 specifies."""
    sequence = GateSequence.default()
    gate_names = tuple(g.name for g in sequence.gates)  # type: ignore[attr-defined]
    assert gate_names == SPINE_ORDER


def test_gates_execute_in_spine_order_on_clean_action(tmp_path):
    """CP-6.1: a fully-compliant action walks all seven gates in order
    and reaches PASS."""
    env = _envelope()
    action = _action(env)
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path)
    # Tell gate 6 the tool is known so we observe the happy path.
    sequence = GateSequence.default(
        project_root=tmp_path, known_tools={"safe_file_writer"}
    )

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.PASS
    gate_names = tuple(gr.gate_name for gr in result.evaluated)
    assert gate_names == SPINE_ORDER
    assert all(gr.verdict == GateVerdict.PASS for gr in result.evaluated)


# ---------------------------------------------------------------------------
# CP-6.2 — short-circuit on terminal verdicts.
# ---------------------------------------------------------------------------


def test_block_short_circuits_stops_further_gates():
    """CP-6.2: a BLOCK verdict is terminal — no downstream gate runs."""
    recorder = _Recorder()
    sequence = GateSequence(
        gates=[
            _fake_gate("gate_1", GateVerdict.PASS, recorder),
            _fake_gate("gate_2", GateVerdict.PASS, recorder),
            _fake_gate("gate_3", GateVerdict.BLOCK, recorder),
            _fake_gate("gate_4", GateVerdict.PASS, recorder),
            _fake_gate("gate_5", GateVerdict.PASS, recorder),
        ]
    )

    env = _envelope()
    result = sequence.evaluate(_action(env), env, _state(env))

    assert result.terminal_verdict == GateVerdict.BLOCK
    assert recorder.calls == ["gate_1", "gate_2", "gate_3"]
    assert tuple(gr.gate_name for gr in result.evaluated) == (
        "gate_1",
        "gate_2",
        "gate_3",
    )
    # blocking_gate convenience property.
    assert result.blocking_gate is not None
    assert result.blocking_gate.gate_name == "gate_3"
    assert result.blocking_gate.verdict == GateVerdict.BLOCK


def test_escalate_short_circuits_like_block():
    """ESCALATE terminates the sequence too — SPINE_01 treats gates
    as a single decision, so "ESCALATE at gate 2" is the mission's
    answer and gates 3..7 are not asked."""
    recorder = _Recorder()
    sequence = GateSequence(
        gates=[
            _fake_gate("g1", GateVerdict.PASS, recorder),
            _fake_gate("g2", GateVerdict.ESCALATE, recorder),
            _fake_gate("g3", GateVerdict.PASS, recorder),
        ]
    )
    env = _envelope()
    result = sequence.evaluate(_action(env), env, _state(env))

    assert result.terminal_verdict == GateVerdict.ESCALATE
    assert recorder.calls == ["g1", "g2"]


def test_report_missing_short_circuits_like_block():
    recorder = _Recorder()
    sequence = GateSequence(
        gates=[
            _fake_gate("g1", GateVerdict.REPORT_MISSING, recorder),
            _fake_gate("g2", GateVerdict.PASS, recorder),
        ]
    )
    env = _envelope()
    result = sequence.evaluate(_action(env), env, _state(env))

    assert result.terminal_verdict == GateVerdict.REPORT_MISSING
    assert recorder.calls == ["g1"]


def test_all_pass_reports_no_blocking_gate():
    recorder = _Recorder()
    sequence = GateSequence(
        gates=[
            _fake_gate("g1", GateVerdict.PASS, recorder),
            _fake_gate("g2", GateVerdict.PASS, recorder),
        ]
    )
    env = _envelope()
    result = sequence.evaluate(_action(env), env, _state(env))

    assert result.terminal_verdict == GateVerdict.PASS
    assert recorder.calls == ["g1", "g2"]
    assert result.blocking_gate is None


# ---------------------------------------------------------------------------
# CP-6.1 + CP-6.2 — Hypothesis property test.
# ---------------------------------------------------------------------------


_VERDICT = st.sampled_from(
    [
        GateVerdict.PASS,
        GateVerdict.BLOCK,
        GateVerdict.ESCALATE,
        GateVerdict.REPORT_MISSING,
    ]
)

_GATE_NAME = st.text(
    alphabet=string.ascii_lowercase + "_", min_size=3, max_size=20
).filter(lambda s: s[0] in string.ascii_lowercase)


@given(
    verdicts=st.lists(_VERDICT, min_size=1, max_size=10),
)
@settings(deadline=None, max_examples=100)
def test_gate_ordering_property_short_circuits_on_first_non_pass(
    verdicts: list[GateVerdict],
) -> None:
    """CP-6.2 property: if any gate returns a non-PASS verdict, no
    downstream gate is called, and the sequence's terminal verdict is
    the first non-PASS verdict. If all gates PASS, the sequence's
    terminal verdict is PASS and every gate was called exactly once."""
    recorder = _Recorder()
    gates = [
        _fake_gate(f"g{i}", verdict, recorder)
        for i, verdict in enumerate(verdicts)
    ]
    sequence = GateSequence(gates=gates)

    env = _envelope()
    result = sequence.evaluate(_action(env), env, _state(env))

    # Find the first non-PASS verdict (if any).
    first_non_pass_idx = next(
        (i for i, v in enumerate(verdicts) if v != GateVerdict.PASS),
        None,
    )

    if first_non_pass_idx is None:
        # All gates PASS.
        assert result.terminal_verdict == GateVerdict.PASS
        assert len(recorder.calls) == len(verdicts)
        assert recorder.calls == [f"g{i}" for i in range(len(verdicts))]
    else:
        # Short-circuit.
        expected_verdict = verdicts[first_non_pass_idx]
        assert result.terminal_verdict == expected_verdict
        assert expected_verdict in TERMINAL_VERDICTS
        # Exactly first_non_pass_idx + 1 gates were called.
        assert len(recorder.calls) == first_non_pass_idx + 1
        assert recorder.calls == [f"g{i}" for i in range(first_non_pass_idx + 1)]
        # The evaluated tuple includes all called gates, in order.
        assert tuple(gr.gate_name for gr in result.evaluated) == tuple(
            f"g{i}" for i in range(first_non_pass_idx + 1)
        )


@given(
    prefix_len=st.integers(min_value=0, max_value=6),
    block_at=st.sampled_from([GateVerdict.BLOCK, GateVerdict.ESCALATE, GateVerdict.REPORT_MISSING]),
    suffix_len=st.integers(min_value=0, max_value=6),
)
@settings(deadline=None, max_examples=50)
def test_gates_after_short_circuit_are_never_called(
    prefix_len: int, block_at: GateVerdict, suffix_len: int
) -> None:
    """CP-6.2 strong form: construct a sequence with N PASS gates
    followed by one non-PASS gate followed by K gates, assert the K
    suffix gates are never invoked."""
    recorder = _Recorder()
    gates: list = []
    for i in range(prefix_len):
        gates.append(_fake_gate(f"pass_{i}", GateVerdict.PASS, recorder))
    gates.append(_fake_gate("terminal", block_at, recorder))
    for i in range(suffix_len):
        gates.append(_fake_gate(f"never_{i}", GateVerdict.PASS, recorder))

    sequence = GateSequence(gates=gates)
    env = _envelope()
    result = sequence.evaluate(_action(env), env, _state(env))

    assert result.terminal_verdict == block_at
    assert "terminal" in recorder.calls
    # No gate with "never_" prefix was called.
    assert not any(name.startswith("never_") for name in recorder.calls)


# ---------------------------------------------------------------------------
# Integration — default sequence against representative actions.
# ---------------------------------------------------------------------------


def test_forbidden_action_blocks_at_gate_1(tmp_path):
    env = _envelope(
        allowed_actions=["run_shell_command", "benign_in_memory_computation"],
        allowed_tools=["safe_file_writer", "shell"],
        forbidden_actions=["run_shell_command"],
    )
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)
    sequence = GateSequence.default(
        project_root=tmp_path, known_tools={"safe_file_writer", "shell"}
    )

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.BLOCK
    assert result.evaluated[-1].gate_name == "forbidden"
    # Only gate 1 ran — gates 2..7 did not.
    assert len(result.evaluated) == 1


def test_out_of_scope_action_escalates_at_gate_2(tmp_path):
    env = _envelope()
    action = _action(env, action_type="send_email", tool="safe_file_writer")
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.ESCALATE
    assert result.evaluated[-1].gate_name == "out_of_scope"
    assert len(result.evaluated) == 2  # forbidden passed, out_of_scope escalated


def test_black_zone_action_blocks_at_gate_3_even_if_mission_allowed_it(
    tmp_path,
):
    """If a mission author accidentally allows ``run_shell_command``
    and doesn't list it in ``forbidden_actions``, the system-wide
    black-zone still catches it."""
    env = _envelope(
        allowed_actions=["run_shell_command"],
        allowed_tools=["shell", "safe_file_writer"],
        forbidden_actions=[],  # no explicit forbidden list
    )
    action = _action(env, action_type="run_shell_command", tool="shell")
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.BLOCK
    assert result.evaluated[-1].gate_name == "black_zone"
    # Gate 1 and 2 passed; gate 3 blocked.
    assert tuple(gr.gate_name for gr in result.evaluated) == (
        "forbidden",
        "out_of_scope",
        "black_zone",
    )


def test_budget_exceeded_escalates_at_gate_4(tmp_path):
    env = _envelope(max_cost_usd=1.0, max_actions=10)
    action = _action(env, estimated_cost=2.0)
    state = _state(env, cost_used=0.0)
    sequence = GateSequence.default(project_root=tmp_path)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.ESCALATE
    assert result.evaluated[-1].gate_name == "cost_exceeds_budget"


def test_external_action_escalates_at_gate_5(tmp_path):
    env = _envelope()
    action = _action(
        env,
        externality=ExternalityLevel.EXTERNAL_PUBLIC,
    )
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.ESCALATE
    assert result.evaluated[-1].gate_name == "external_or_irreversible_or_sensitive"


def test_irreversible_action_escalates_at_gate_5(tmp_path):
    env = _envelope()
    action = _action(env, reversibility=ReversibilityLevel.IRREVERSIBLE)
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.ESCALATE
    assert result.evaluated[-1].gate_name == "external_or_irreversible_or_sensitive"


def test_sensitive_action_escalates_at_gate_5(tmp_path):
    env = _envelope()
    action = _action(env, sensitivity=SensitivityLevel.FINANCIAL)
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.ESCALATE
    assert result.evaluated[-1].gate_name == "external_or_irreversible_or_sensitive"


def test_unknown_tool_reports_missing_at_gate_6(tmp_path):
    env = _envelope()
    action = _action(env)  # tool == "safe_file_writer"
    state = _state(env)
    sequence = GateSequence.default(
        project_root=tmp_path,
        known_tools={"some_other_tool"},  # safe_file_writer absent
    )

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.REPORT_MISSING
    assert result.evaluated[-1].gate_name == "unknown_tool_or_capability"


def test_known_tool_reaches_gate_7_pass(tmp_path):
    env = _envelope()
    action = _action(env)
    state = _state(env)
    sequence = GateSequence.default(
        project_root=tmp_path, known_tools={"safe_file_writer"}
    )

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.PASS
    # All 7 gates ran and passed.
    assert len(result.evaluated) == 7
    assert tuple(gr.gate_name for gr in result.evaluated) == SPINE_ORDER


def test_none_known_tools_makes_gate_6_a_noop(tmp_path):
    """Production callers SHOULD pass ``known_tools``; the ``None``
    default turns gate 6 into a PASS so the sequence still completes,
    rather than silently reporting every action as missing."""
    env = _envelope()
    action = _action(env)
    state = _state(env)
    sequence = GateSequence.default(project_root=tmp_path, known_tools=None)

    result = sequence.evaluate(action, env, state)

    assert result.terminal_verdict == GateVerdict.PASS


# ---------------------------------------------------------------------------
# All risk lanes traverse expected sequence.
# ---------------------------------------------------------------------------


def test_all_risk_lanes_traverse_expected_sequence(tmp_path):
    """For GREEN (happy), ORANGE (escalate at gate 5), RED (block at
    gate 3), and a BLACK-zone-specifically action, check the number
    of gates traversed matches SPINE ordering."""
    env = _envelope()
    sequence = GateSequence.default(
        project_root=tmp_path, known_tools={"safe_file_writer", "shell"}
    )

    # GREEN — all 7 gates.
    green_action = _action(env)
    green = sequence.evaluate(green_action, env, _state(env))
    assert green.terminal_verdict == GateVerdict.PASS
    assert len(green.evaluated) == 7

    # ORANGE — escalates at gate 5.
    orange_action = _action(env, reversibility=ReversibilityLevel.IRREVERSIBLE)
    orange = sequence.evaluate(orange_action, env, _state(env))
    assert orange.terminal_verdict == GateVerdict.ESCALATE
    assert orange.evaluated[-1].gate_name == "external_or_irreversible_or_sensitive"
    assert len(orange.evaluated) == 5

    # RED / black — blocks at gate 3.
    red_env = _envelope(
        allowed_actions=["run_shell_command"],
        allowed_tools=["shell"],
        forbidden_actions=[],
    )
    red_action = _action(red_env, action_type="run_shell_command", tool="shell")
    red = sequence.evaluate(red_action, red_env, _state(red_env))
    assert red.terminal_verdict == GateVerdict.BLOCK
    assert red.evaluated[-1].gate_name == "black_zone"
    assert len(red.evaluated) == 3


# ---------------------------------------------------------------------------
# Determinism.
# ---------------------------------------------------------------------------


def test_sequence_is_deterministic_across_repeated_evaluations(tmp_path):
    """Same inputs → same :class:`SequenceResult`. Gates must not
    carry hidden mutable state."""
    env = _envelope()
    action = _action(env)
    state = _state(env)
    sequence = GateSequence.default(
        project_root=tmp_path, known_tools={"safe_file_writer"}
    )

    r1 = sequence.evaluate(action, env, state)
    r2 = sequence.evaluate(action, env, state)

    assert r1.terminal_verdict == r2.terminal_verdict
    assert tuple(gr.gate_name for gr in r1.evaluated) == tuple(
        gr.gate_name for gr in r2.evaluated
    )
    assert tuple(gr.verdict for gr in r1.evaluated) == tuple(
        gr.verdict for gr in r2.evaluated
    )


def test_gates_tuple_is_immutable():
    """``GateSequence.gates`` returns a tuple — a caller cannot append
    or pop to mutate the sequence in place."""
    sequence = GateSequence.default()
    assert isinstance(sequence.gates, tuple)
    with pytest.raises(AttributeError):
        sequence.gates.append(lambda a, e, s: GateResult("x", GateVerdict.PASS))  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public API surface.
# ---------------------------------------------------------------------------


def test_public_api_exports_all_required_symbols():
    from sentinel.mission import gate_sequence as module

    for name in (
        "Gate",
        "GateCallable",
        "GateResult",
        "GateSequence",
        "GateVerdict",
        "SequenceResult",
        "TERMINAL_VERDICTS",
    ):
        assert hasattr(module, name), f"{name} missing from gate_sequence public API"
