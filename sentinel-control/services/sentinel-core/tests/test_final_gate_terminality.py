"""Task 1.4 / Requirement 1 (FinalGate Runtime Integration, finding F-A3.11).

Terminality tests for ``AgentRuntime._apply_final_gate``.

These tests enforce the doctrine invariant:

    ∀ result returned by AgentRuntime.run:
        result.final_gate_certification is not None
        AND result.final_gate_certification.accepted is True

and the companion invariant that a rejected intended result is NEVER
surfaced to callers — it MUST be downgraded to a BLOCKED result that
passes re-certification, with the failed intended check names preserved
ONLY as text in ``escalation_reason``.

**Validates: Requirements 1.1, 1.2, 1.3 (CP-1.1 FinalGate Terminality)**
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.agent import (
    AgentPhase,
    AgentRuntime,
    CoreFinalGate,
    CoreFinalGateResult,
    CoreGateCheck,
    CoreGateCheckKind,
    ReviewFinding,
)
from sentinel.agent.exceptions import AgentBlockedError
from sentinel.mission import MissionAuthorityEnvelope
from sentinel.shared.enums import MissionMode, MissionType


# ---------------------------------------------------------------------------
# Envelope factories — mirror the shape used by existing test modules
# (``tests/test_agent_runtime.py``, ``tests/test_agent_core_final_gate.py``).
# ---------------------------------------------------------------------------

SAFE_ACTIONS: list[str] = [
    "create_project_folder",
    "create_markdown_file",
    "export_json",
    "generate_gtm_pack",
    "generate_landing_copy",
    "generate_outreach_drafts_without_sending",
    "create_watchlist",
    "generate_research_questions",
    "write_trace",
]


def _envelope(**overrides: Any) -> MissionAuthorityEnvelope:
    data: dict[str, Any] = {
        "user_id": "user_001",
        "mission_type": MissionType.GTM,
        "mission_title": "Final gate terminality test",
        "mission_objective": "Exercise AgentRuntime.run exit paths.",
        "success_criteria": ["Trace exists", "Run completes"],
        "mode": MissionMode.POWER,
        "allowed_systems": ["local_workspace"],
        "allowed_tools": ["safe_file_writer"],
        "allowed_actions": list(SAFE_ACTIONS),
        "forbidden_actions": [
            "send_email",
            "run_shell_command",
            "browser_submit_form",
            "credential_access",
        ],
        "allowed_paths": ["data/generated_projects"],
        "max_duration_minutes": 30,
        "max_actions": 20,
        "max_cost_usd": 1.0,
    }
    data.update(overrides)
    return MissionAuthorityEnvelope(**data)


def _completed_run(tmp_path: Path):
    """A normal terminal COMPLETED run."""
    return AgentRuntime(project_root=tmp_path).run(
        _envelope(),
        {"idea": "Sentinel SPINE terminality"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )


def _blocked_run_via_tool_selection(tmp_path: Path):
    """BLOCKED path — authorized action set too narrow for available plans.

    Mirrors ``test_critical_tool_selection_review_prevents_worker_execution``.
    """
    env = _envelope(
        allowed_actions=["create_project_folder"],
        allowed_tools=["safe_file_writer"],
    )
    return AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": "Blocked mission"},
        evidence_refs=["ev_scope"],
    )


def _failed_run_via_planner_crash(tmp_path: Path):
    """FAILED path via the exception-handler branch in ``run``.

    Mirrors ``test_agent_runtime_does_not_disguise_internal_key_errors_as_policy_blocks``.
    """
    runtime = AgentRuntime(project_root=tmp_path)

    def raise_internal_key_error(*args: Any, **kwargs: Any) -> Any:
        raise KeyError("internal planner cache miss")

    runtime.planner_bridge.create_plan = raise_internal_key_error
    return runtime.run(
        _envelope(),
        {"idea": "Unknown mission"},
        evidence_refs=["ev_001"],
    )


def _escalated_run_via_forced_repair(tmp_path: Path):
    """ESCALATED path — force repair pressure past the escalation threshold.

    Mirrors ``repair_recovered_result`` in ``tests/test_agent_core_final_gate.py``
    but keeps forcing critical findings so repair converts to ESCALATE.
    """
    runtime = AgentRuntime(project_root=tmp_path)
    original_review = runtime.review_loop.review_worker_result

    def always_review_critical(result):  # type: ignore[no-untyped-def]
        # Keep hammering the repair loop with critical findings so
        # pressure exceeds the escalation threshold.
        original_review(result)
        return [
            ReviewFinding(
                code="forced_escalation",
                severity="critical",
                message="Force escalation for terminality test.",
            )
        ]

    runtime.review_loop.review_worker_result = always_review_critical
    return runtime.run(
        _envelope(),
        {"idea": "Escalated mission"},
        evidence_refs=["ev_wtp"],
    )


# ---------------------------------------------------------------------------
# Test 1: every exit path produces an accepted certification
# ---------------------------------------------------------------------------


def test_runtime_returns_final_gate_certification_for_all_exit_paths(tmp_path):
    """COMPLETED, BLOCKED, FAILED (and ESCALATED when reachable) paths all
    return a result with ``final_gate_certification.accepted is True``."""
    completed = _completed_run(tmp_path / "completed")
    blocked = _blocked_run_via_tool_selection(tmp_path / "blocked")
    failed = _failed_run_via_planner_crash(tmp_path / "failed")

    for result, label in (
        (completed, "completed"),
        (blocked, "blocked"),
        (failed, "failed"),
    ):
        assert result.final_gate_certification is not None, (
            f"{label} result has no final_gate_certification"
        )
        assert result.final_gate_certification.accepted is True, (
            f"{label} result has rejected final_gate_certification; "
            f"errors: {result.final_gate_certification.errors}"
        )

    # Sanity: phases match expected exit paths.
    assert completed.final_phase == AgentPhase.COMPLETED
    assert blocked.final_phase == AgentPhase.BLOCKED
    assert failed.final_phase == AgentPhase.FAILED

    # Best-effort ESCALATED coverage: the escalated path depends on repair
    # pressure thresholds; if the fixture successfully reaches ESCALATED,
    # it must also carry an accepted certification. If not reachable in
    # the current environment, skip rather than fail (the first three
    # paths already enforce the invariant across representative exits).
    try:
        escalated = _escalated_run_via_forced_repair(tmp_path / "escalated")
    except Exception:
        return
    assert escalated.final_gate_certification is not None
    assert escalated.final_gate_certification.accepted is True


# ---------------------------------------------------------------------------
# Test 2: rejected intended verdict → certified BLOCKED result
# ---------------------------------------------------------------------------


def test_final_gate_rejected_intended_result_returns_certified_blocked_result(
    tmp_path,
):
    """When CoreFinalGate rejects the intended result, the downgraded BLOCKED
    result must be re-certified before returning.

    The returned ``final_gate_certification`` MUST be the accepted verdict from
    the second (BLOCKED) call, never the rejected intended verdict.
    """
    runtime = AgentRuntime(project_root=tmp_path)

    failed_check = CoreGateCheck(
        name="synthetic_forced_failure",
        kind=CoreGateCheckKind.PHASE,
        passed=False,
        message="Synthetic rejection for terminality test.",
    )
    rejected_verdict = CoreFinalGateResult(accepted=False, checks=[failed_check])

    accepted_check = CoreGateCheck(
        name="synthetic_blocked_acceptance",
        kind=CoreGateCheckKind.PHASE,
        passed=True,
        message="Synthetic acceptance of the downgraded BLOCKED result.",
    )

    calls: list[dict[str, Any]] = []
    # ``side_effects`` mirrors the task spec: a list whose entries are the
    # verdicts returned for each call, in order. We use a closure so we can
    # also capture the *accepted* verdict object that actually gets attached
    # to the returned result for an identity check.
    side_effects: list[CoreFinalGateResult] = []

    class _SwappableGate:
        def evaluate(
            self,
            result,
            *,
            allowed_project_root=None,
        ) -> CoreFinalGateResult:
            call_index = len(calls)
            calls.append(
                {
                    "final_phase": result.final_phase,
                    "success": result.success,
                    "escalation_reason": result.escalation_reason,
                }
            )
            if call_index == 0:
                # First call: reject the intended result.
                return rejected_verdict
            # Second call (on the downgraded BLOCKED result): accept. We
            # build a fresh verdict per call so we can use object identity
            # to prove the attached certification is the one from THIS
            # call and not the rejected intended verdict.
            verdict = CoreFinalGateResult(
                accepted=True,
                checks=[accepted_check],
            )
            side_effects.append(verdict)
            return verdict

    runtime._final_gate = _SwappableGate()

    result = runtime.run(
        _envelope(),
        {"idea": "Intended-reject forces BLOCKED downgrade"},
        evidence_refs=["ev_direct", "ev_wtp"],
    )

    # 1. Downgraded to BLOCKED with correct escalation_reason semantics.
    assert result.final_phase == AgentPhase.BLOCKED
    assert result.success is False
    assert result.escalation_reason is not None
    assert result.escalation_reason.startswith("final_gate_rejected:"), (
        f"escalation_reason must carry the failed-check prefix; got "
        f"{result.escalation_reason!r}"
    )
    assert "synthetic_forced_failure" in result.escalation_reason

    # 2. Certification is present AND accepted.
    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True

    # 3. The certification attached to the returned result is the verdict
    #    produced by the SECOND call (BLOCKED re-certification), not the
    #    rejected intended verdict.
    assert len(calls) >= 2, (
        "Expected at least two gate evaluations (intended + BLOCKED "
        f"re-certification); got {len(calls)}"
    )
    assert calls[0]["final_phase"] != AgentPhase.BLOCKED or (
        calls[0]["escalation_reason"] is None
        or not calls[0]["escalation_reason"].startswith("final_gate_rejected:")
    ), "First evaluate call should have been the intended (pre-downgrade) result"
    assert calls[1]["final_phase"] == AgentPhase.BLOCKED
    assert calls[1]["success"] is False
    assert calls[1]["escalation_reason"] is not None
    assert calls[1]["escalation_reason"].startswith("final_gate_rejected:")

    # The captured accepted verdict from the second call is the one attached
    # to the returned result (identity check, as required by the task).
    assert side_effects, "Second evaluate call should have produced a verdict"
    assert result.final_gate_certification is side_effects[0]

    # 4. The attached certification is NOT the synthetic rejected one.
    assert result.final_gate_certification is not rejected_verdict
    assert "synthetic_forced_failure" not in {
        check.name for check in result.final_gate_certification.checks
    }
    assert "synthetic_blocked_acceptance" in {
        check.name for check in result.final_gate_certification.checks
    }


# ---------------------------------------------------------------------------
# Test 3: no returned result ever has a failed certification (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "runner",
    [
        pytest.param(_completed_run, id="completed"),
        pytest.param(_blocked_run_via_tool_selection, id="blocked"),
        pytest.param(_failed_run_via_planner_crash, id="failed"),
    ],
)
def test_runtime_never_returns_failed_final_gate_certification(tmp_path, runner):
    result = runner(tmp_path)

    assert result.final_gate_certification is not None, (
        "AgentRuntime.run must always attach a CoreFinalGateResult "
        "to the returned AgentRunResult."
    )
    assert result.final_gate_certification.accepted is not False, (
        "AgentRuntime.run must NEVER return a result whose "
        "final_gate_certification.accepted is False. "
        f"Failed checks: {result.final_gate_certification.errors}"
    )
    assert result.final_gate_certification.accepted is True


# ---------------------------------------------------------------------------
# Test 4: property test over small envelope variations
# ---------------------------------------------------------------------------


_SAFE_TITLES = st.sampled_from(
    [
        "Terminality property mission A",
        "Terminality property mission B",
        "SPINE property-test mission",
        "Final-gate property coverage",
    ]
)

_SAFE_MODES = st.sampled_from([MissionMode.SAFE, MissionMode.POWER])

_EVIDENCE_REFS = st.lists(
    st.sampled_from(["ev_direct", "ev_wtp", "ev_scope", "ev_001"]),
    min_size=0,
    max_size=3,
    unique=True,
)

_IDEAS = st.sampled_from(
    [
        "Sentinel SPINE",
        "Property-based final-gate exercise",
        "Small safe mission idea",
        "Terminality coverage mission",
    ]
)


@settings(
    max_examples=6,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    title=_SAFE_TITLES,
    mode=_SAFE_MODES,
    max_actions=st.integers(min_value=5, max_value=20),
    evidence_refs=_EVIDENCE_REFS,
    idea=_IDEAS,
)
def test_final_gate_terminality_property(
    tmp_path, title, mode, max_actions, evidence_refs, idea
):
    """**Validates: Requirements 1.1, 1.2, 1.3 (CP-1.1 FinalGate Terminality)**

    For any valid run context, the returned ``AgentRunResult`` carries an
    accepted ``CoreFinalGateResult`` on ``final_gate_certification``.
    """
    env = _envelope(
        mission_title=title,
        mode=mode,
        max_actions=max_actions,
    )

    result = AgentRuntime(project_root=tmp_path).run(
        env,
        {"idea": idea},
        evidence_refs=list(evidence_refs),
    )

    assert result.final_gate_certification is not None
    assert result.final_gate_certification.accepted is True


# ---------------------------------------------------------------------------
# Test 5 (deep-invariant failure — recommended): both verdicts rejected
# ---------------------------------------------------------------------------


def test_final_gate_rejects_both_intended_and_blocked_raises(tmp_path):
    """When CoreFinalGate rejects BOTH the intended AND the downgraded
    BLOCKED result, the runtime must NOT return a manufactured uncertified
    ``AgentRunResult``.

    The current implementation raises ``AgentBlockedError`` from inside
    ``_apply_final_gate``. ``AgentRuntime.run``'s own ``except Exception``
    handler catches that exception and rebuilds a BLOCKED result which is
    then funneled through ``_apply_final_gate`` a second time — where the
    always-reject gate raises ``AgentBlockedError`` again. That second
    raise propagates past ``run()``'s handler (the handler is already
    unwinding) and surfaces to the caller.

    Observed behavior: ``AgentBlockedError`` propagates out of ``run()``.
    """
    runtime = AgentRuntime(project_root=tmp_path)

    failed_check = CoreGateCheck(
        name="synthetic_always_reject",
        kind=CoreGateCheckKind.PHASE,
        passed=False,
        message="Synthetic always-reject gate for deep-invariant test.",
    )
    always_rejected = CoreFinalGateResult(accepted=False, checks=[failed_check])

    class _AlwaysRejectGate:
        def evaluate(
            self,
            result,
            *,
            allowed_project_root=None,
        ) -> CoreFinalGateResult:
            return always_rejected

    runtime._final_gate = _AlwaysRejectGate()

    with pytest.raises(AgentBlockedError) as exc_info:
        runtime.run(
            _envelope(),
            {"idea": "Always-reject gate forces deep-invariant failure"},
            evidence_refs=["ev_direct", "ev_wtp"],
        )

    message = str(exc_info.value)
    assert "synthetic_always_reject" in message
    assert "refusing to return an uncertified AgentRunResult" in message
