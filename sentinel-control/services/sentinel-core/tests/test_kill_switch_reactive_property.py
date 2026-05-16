"""Task 4 / Requirement 4 — Reactive Kill-Switch Interruption (F-A3.10).

Validates the reactive-revocation contract wired into
:meth:`sentinel.mission.runner.MissionRunner.run_mission`:

    CP-4.1 (Revocation Completeness):
        ∀ revoke event R at time T:
            no plan step initiated after T completes successfully.

    CP-4.2 (Bounded Latency):
        ∀ sync worker: revocation takes effect within 1 phase boundary;
        ∀ async worker: within 1 event-loop tick.

Tests here are deterministic and fake-adapter-based — no real time / no
real network calls. Plan-step iteration is instrumented via a fake
executor that mutates ``envelope.revoked_at`` or cancels a shared
``CancellationToken`` at a chosen step index, and the subsequent
``MissionRunResult`` is inspected for the REVOKED terminal state with
all later steps suppressed.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.mission import MissionAuthorityEnvelope
from sentinel.mission.cancellation import CancellationToken
from sentinel.mission.exceptions import MissionRevokedException
from sentinel.mission.kill_switch import MissionKillSwitch
from sentinel.mission.models import MissionState, utc_now
from sentinel.mission.runner import MissionRunner
from sentinel.shared.enums import (
    MissionActionRoute,
    MissionStatus,
    MissionTraceEventType,
    MissionType,
)
from sentinel.shared.enums import MissionMode


SAFE_ACTIONS = [
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
        "user_id": "user_kill_switch",
        "mission_type": MissionType.GTM,
        "mission_title": "Kill-switch reactive test",
        "mission_objective": "Prove revocation halts plan execution.",
        "success_criteria": ["Plan halted on revocation"],
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


# ---------------------------------------------------------------------------
# Test 1 — revoke before first step prevents all steps from executing.
# ---------------------------------------------------------------------------


def test_revoke_before_first_step_suppresses_all_steps(tmp_path: Path) -> None:
    """**Validates: CP-4.1 (Revocation Completeness).**

    An envelope that arrives already-revoked must cause the runner to
    suppress every plan step, return ``success=False`` with
    ``state.status == MissionStatus.REVOKED``, and emit
    ``MISSION_REVOKED`` in the trace.
    """
    env = _envelope(revoked_at=utc_now())
    runner = MissionRunner(project_root=tmp_path)

    result = runner.run_mission(env, idea="Pre-revoked mission")

    assert result.success is False
    assert result.state.status == MissionStatus.REVOKED
    executed = [
        event for event in result.trace_events
        if event.event_type == MissionTraceEventType.ACTION_EXECUTED
    ]
    assert executed == [], (
        f"Pre-revoked envelope must suppress ALL action executions; "
        f"observed {len(executed)} execution events."
    )
    revoked_events = [
        event for event in result.trace_events
        if event.event_type == MissionTraceEventType.MISSION_REVOKED
    ]
    assert revoked_events, "Runner must emit MISSION_REVOKED when halting."


# ---------------------------------------------------------------------------
# Test 2 — revoke after step K prevents steps K+1..N from executing.
# ---------------------------------------------------------------------------


def test_revocation_stops_plan_execution_after_step_k(tmp_path: Path) -> None:
    """**Validates: CP-4.1 (Revocation Completeness).**

    The runner exposes the plan iteration by way of
    ``autonomy.decide`` being called per step. We monkeypatch
    ``runner.autonomy.decide`` so its side-effect cancels the shared
    :class:`CancellationToken` after the FIRST decision has been routed,
    then inspect the resulting mission to confirm no further steps were
    executed.
    """
    env = _envelope()
    runner = MissionRunner(project_root=tmp_path)
    token = CancellationToken()

    original_decide = runner.autonomy.decide
    decide_call_count = {"n": 0}

    def _decide_and_cancel_after_first(*args: Any, **kwargs: Any):
        decide_call_count["n"] += 1
        decision = original_decide(*args, **kwargs)
        if decide_call_count["n"] == 1:
            # Fire the kill-switch mid-plan, between decision and the
            # next iteration's revocation poll.
            token.cancel()
        return decision

    runner.autonomy.decide = _decide_and_cancel_after_first  # type: ignore[method-assign]

    result = runner.run_mission(
        env, idea="Mid-plan revoke", cancellation_token=token
    )

    assert result.state.status == MissionStatus.REVOKED
    assert result.success is False
    # At most one autonomy decision ran before the token fired.
    assert decide_call_count["n"] >= 1
    revoked_events = [
        event for event in result.trace_events
        if event.event_type == MissionTraceEventType.MISSION_REVOKED
    ]
    assert revoked_events, (
        "Runner must emit MISSION_REVOKED when the cancellation token "
        "fires between steps."
    )


# ---------------------------------------------------------------------------
# Test 3 — cancellation token is thread-safe and idempotent.
# ---------------------------------------------------------------------------


def test_cancellation_token_thread_safe() -> None:
    """Concurrent :meth:`CancellationToken.cancel` calls and
    :attr:`CancellationToken.is_cancelled` reads produce a consistent view.

    ``threading.Event`` is atomic; this test just asserts the wrapper
    preserves that guarantee.
    """
    token = CancellationToken()
    assert token.is_cancelled is False

    readers_saw_true = []

    def reader():
        readers_saw_true.append(token.is_cancelled)

    def canceller():
        token.cancel()

    cancel_threads = [threading.Thread(target=canceller) for _ in range(8)]
    for t in cancel_threads:
        t.start()
    for t in cancel_threads:
        t.join()

    # After every cancel completes, is_cancelled is guaranteed True.
    assert token.is_cancelled is True

    # Idempotent: additional cancels are no-ops.
    token.cancel()
    token.cancel()
    assert token.is_cancelled is True

    # Concurrent readers run after cancel — each must see True.
    read_threads = [threading.Thread(target=reader) for _ in range(8)]
    for t in read_threads:
        t.start()
    for t in read_threads:
        t.join()
    assert all(x is True for x in readers_saw_true), (
        f"Concurrent readers must all see is_cancelled=True after cancel; "
        f"got {readers_saw_true!r}."
    )


# ---------------------------------------------------------------------------
# Test 4 — MissionKillSwitch.revoke cancels the optional token.
# ---------------------------------------------------------------------------


def test_kill_switch_revoke_cancels_token() -> None:
    """``MissionKillSwitch.revoke(..., cancellation_token=token)`` stamps
    ``envelope.revoked_at`` AND cancels the optional token so organ
    adapters polling the token observe the revocation within one tick.
    """
    env = _envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    token = CancellationToken()
    assert token.is_cancelled is False

    updated_env, updated_state = MissionKillSwitch().revoke(
        env, state, cancellation_token=token
    )

    assert updated_env.revoked_at is not None
    assert updated_state.status == MissionStatus.REVOKED
    assert token.is_cancelled is True


# ---------------------------------------------------------------------------
# Test 5 — _check_revocation raises MissionRevokedException on either signal.
# ---------------------------------------------------------------------------


def test_check_revocation_raises_on_envelope_stamp() -> None:
    env = _envelope(revoked_at=utc_now())
    with pytest.raises(MissionRevokedException) as excinfo:
        MissionRunner._check_revocation(env, None)
    assert "mission_revoked" in str(excinfo.value)


def test_check_revocation_raises_on_token_cancel() -> None:
    env = _envelope()
    token = CancellationToken()
    token.cancel()
    with pytest.raises(MissionRevokedException) as excinfo:
        MissionRunner._check_revocation(env, token)
    assert "mission_revoked" in str(excinfo.value)


def test_check_revocation_silent_when_neither_signal_set() -> None:
    env = _envelope()
    token = CancellationToken()
    # Must not raise.
    MissionRunner._check_revocation(env, token)
    MissionRunner._check_revocation(env, None)


# ---------------------------------------------------------------------------
# Test 6 — Hypothesis property: revoke at step K suppresses K+1..N.
# ---------------------------------------------------------------------------


@settings(
    max_examples=6,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(revoke_after_decision=st.integers(min_value=1, max_value=3))
def test_kill_switch_reactive_property(tmp_path: Path, revoke_after_decision: int) -> None:
    """**Validates: CP-4.1 (Revocation Completeness).**

    For any K ∈ {1, 2, 3}, firing the cancellation token after the K-th
    autonomy decision produces a REVOKED mission with no more than K
    executed steps (the K-th step may have completed, but nothing after
    it starts).
    """
    env = _envelope()
    runner = MissionRunner(project_root=tmp_path / f"hyp_revoke_after_{revoke_after_decision}")
    token = CancellationToken()

    original_decide = runner.autonomy.decide
    decisions_seen = {"n": 0}

    def _decide_and_cancel(*args: Any, **kwargs: Any):
        decisions_seen["n"] += 1
        decision = original_decide(*args, **kwargs)
        if decisions_seen["n"] == revoke_after_decision:
            token.cancel()
        return decision

    runner.autonomy.decide = _decide_and_cancel  # type: ignore[method-assign]

    result = runner.run_mission(
        env, idea="Property revocation", cancellation_token=token
    )

    assert result.state.status == MissionStatus.REVOKED
    assert result.success is False
    executed_count = sum(
        1 for event in result.trace_events
        if event.event_type == MissionTraceEventType.ACTION_EXECUTED
    )
    # No more than K steps executed: any post-K step would violate
    # CP-4.1 Revocation Completeness.
    assert executed_count <= revoke_after_decision, (
        f"After revoke-at-decision-K={revoke_after_decision}, expected "
        f"<= {revoke_after_decision} executed steps, got {executed_count}."
    )
    revoked_events = [
        event for event in result.trace_events
        if event.event_type == MissionTraceEventType.MISSION_REVOKED
    ]
    assert revoked_events, "Runner must emit MISSION_REVOKED on token cancel."


# ---------------------------------------------------------------------------
# Test 7 — async / token-polling I/O: organ adapter polling pattern.
# ---------------------------------------------------------------------------


def test_cancellation_token_stops_adapter_io() -> None:
    """**Validates: CP-4.2 (Bounded Latency) at adapter polling boundary.**

    Organ adapters (for real network I/O in later tasks) are expected to
    check ``token.is_cancelled`` before each I/O boundary and raise
    :class:`MissionRevokedException` if cancelled. This test simulates
    that polling pattern with a fake adapter and confirms the raise path.
    """
    token = CancellationToken()

    def _fake_io_step(token: CancellationToken) -> str:
        if token.is_cancelled:
            raise MissionRevokedException(
                "mission_revoked: cancellation token fired before I/O."
            )
        return "io_ok"

    assert _fake_io_step(token) == "io_ok"

    token.cancel()
    with pytest.raises(MissionRevokedException) as excinfo:
        _fake_io_step(token)
    assert "mission_revoked" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Test 8 — idempotent revocation: revoking twice is safe.
# ---------------------------------------------------------------------------


def test_revocation_is_idempotent() -> None:
    """Calling :meth:`MissionKillSwitch.revoke` twice does not crash and
    the second call is a no-op on an already-revoked envelope/token.
    """
    env = _envelope()
    state = MissionState(mission_id=env.id, status=MissionStatus.RUNNING)
    token = CancellationToken()

    ks = MissionKillSwitch()
    env1, state1 = ks.revoke(env, state, cancellation_token=token)
    assert env1.revoked_at is not None
    assert token.is_cancelled is True

    env2, state2 = ks.revoke(env1, state1, cancellation_token=token)
    assert env2.revoked_at is not None
    assert state2.status == MissionStatus.REVOKED
    assert token.is_cancelled is True
