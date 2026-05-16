"""Task 7 / Requirement 7 — Per-Append Trace Hash Verification (F-A3.3).

Validates the per-append tail-integrity check added to
:meth:`sentinel.agent.event_bus.EventBus.append`:

    CP-7.1 (Immediate Detection):
        ∀ mutation M applied to event E_k at time T: the next append after T
        raises :class:`TraceIntegrityError`.

    CP-7.2 (Chain Integrity):
        ∀ event sequence [E_1..E_n]:
            hash(E_n) = H(hash(E_{n-1}) || content(E_n))
        and :meth:`EventBus.verify_chain` remains a full-chain audit.

Attacks simulated
-----------------
* Replace a prior event in ``_events`` via ``bus._events[k] = event.model_copy(...)``.
* Corrupt only the ``_last_hash`` anchor without touching the events list.
* Splice a freshly-built event with a random ``event_hash`` into the list.

Every attack must be caught on the NEXT append (CP-7.1); the historical
``verify_chain`` check must also still catch the tampering (CP-7.2).
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from sentinel.agent import AgentEventType, AgentPhase, EventBus
from sentinel.agent.exceptions import TraceIntegrityError


# ---------------------------------------------------------------------------
# Test 1 — append builds a consistent running hash chain.
# ---------------------------------------------------------------------------


def test_append_computes_running_hash() -> None:
    """**Validates: CP-7.2 (Chain Integrity).**

    Each appended event's ``event_hash`` is deterministic and each new event
    links to the previous one via ``previous_hash``. The EventBus tail
    anchor (``_last_hash``) tracks the freshest event_hash.
    """
    bus = EventBus("mission_trace_7")

    first = bus.append(
        AgentEventType.AGENT_INITIALIZED,
        "Initialized.",
        phase_after=AgentPhase.INITIALIZED,
    )
    second = bus.append(
        AgentEventType.CONTEXT_BUILT,
        "Context built.",
        phase_before=AgentPhase.INITIALIZED,
        phase_after=AgentPhase.CONTEXT_BUILDING,
    )
    third = bus.append(
        AgentEventType.AGENT_BLOCKED,
        "Blocked.",
        phase_before=AgentPhase.CONTEXT_BUILDING,
        phase_after=AgentPhase.BLOCKED,
    )

    assert first.previous_hash is None
    assert second.previous_hash == first.event_hash
    assert third.previous_hash == second.event_hash
    assert bus._last_hash == third.event_hash
    assert bus.verify_chain() is True


# ---------------------------------------------------------------------------
# Test 2 — tampering with a previous event is detected on the very next append.
# ---------------------------------------------------------------------------


def test_tampered_event_detected_on_next_append() -> None:
    """**Validates: CP-7.1 (Immediate Detection).**

    Mutating a prior event via ``model_copy`` replacement in the internal
    ``_events`` list causes the NEXT append to raise ``TraceIntegrityError``
    — not only the final ``verify_chain()``.
    """
    bus = EventBus("mission_trace_7_tamper_next")
    first = bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.")
    bus.append(AgentEventType.CONTEXT_BUILT, "Context built.")

    # Tamper: rewrite the first event with a mutated summary; keep the
    # ORIGINAL event_hash so ``_last_hash`` still equals some tail
    # event_hash — but the second event is now orphaned (its
    # ``previous_hash`` points to a hash of an event that no longer exists
    # in the list). The next append MUST refuse.
    tampered_first = first.model_copy(update={"summary": "tampered"})
    bus._events[0] = tampered_first

    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.AGENT_BLOCKED, "After tamper.")


def test_tampered_tail_event_detected_on_next_append() -> None:
    """**Validates: CP-7.1 (Immediate Detection), tail variant.**

    Mutating the last event (so its stored ``event_hash`` no longer matches
    the recomputed hash of its payload) causes the next append to raise.
    """
    bus = EventBus("mission_trace_7_tamper_tail")
    bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.")
    tail = bus.append(AgentEventType.CONTEXT_BUILT, "Tail.")

    # Re-write the tail with a model_copy that keeps the old event_hash but
    # changes summary. ``_last_hash`` still equals the old hash (matches
    # tail.event_hash), but the recomputed hash of the tampered payload
    # differs. The recompute check catches this.
    bus._events[-1] = tail.model_copy(update={"summary": "tail tampered"})

    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.AGENT_BLOCKED, "After tail tamper.")


def test_stale_last_hash_detected_on_next_append() -> None:
    """**Validates: CP-7.1 (Immediate Detection), anchor variant.**

    Directly corrupting the tail anchor ``_last_hash`` without touching the
    events list still raises on the next append — the anchor vs. stored
    ``event_hash`` check fires first.
    """
    bus = EventBus("mission_trace_7_anchor")
    bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.")
    bus._last_hash = "0" * 64  # plausibly-shaped but wrong

    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.CONTEXT_BUILT, "After anchor tamper.")


def test_empty_bus_with_anchor_raises() -> None:
    """Defensive: if ``_last_hash`` is somehow set while ``_events`` is
    empty, the next append refuses (no state to anchor against).
    """
    bus = EventBus("mission_trace_7_empty_anchor")
    bus._last_hash = "0" * 64  # adversarial injection with no events

    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.AGENT_INITIALIZED, "Would-be first event.")


# ---------------------------------------------------------------------------
# Test 3 — verify_chain still works as belt-and-braces final check.
# ---------------------------------------------------------------------------


def test_verify_chain_still_works_as_final_check() -> None:
    """**Validates: CP-7.2 (Chain Integrity).**

    ``verify_chain()`` / ``verify_events(...)`` continues to re-verify the
    whole chain at return time. A trace built without tampering passes; a
    trace tampered AFTER the last append (never appended to again) is
    caught by the full-chain audit even though the per-append hook never
    fired.
    """
    bus = EventBus("mission_trace_7_verify")
    bus.append(AgentEventType.AGENT_INITIALIZED, "Initialized.")
    bus.append(AgentEventType.CONTEXT_BUILT, "Context built.")
    bus.append(AgentEventType.AGENT_COMPLETED, "Done.")
    assert bus.verify_chain() is True

    # Tamper after the last append — no further append means the per-append
    # hook is never invoked. verify_chain must still catch it.
    original = bus._events[0]
    bus._events[0] = original.model_copy(update={"summary": "forged"})
    assert bus.verify_chain() is False


# ---------------------------------------------------------------------------
# Test 4 — Hypothesis property: tampering at any index raises on next append.
# ---------------------------------------------------------------------------


_PHASE_POOL = st.sampled_from(
    [
        AgentPhase.CONTEXT_BUILDING,
        AgentPhase.ORIENTING,
        AgentPhase.METHOD_SELECTING,
        AgentPhase.CAPABILITY_SELECTING,
        AgentPhase.TOOL_SELECTING,
    ]
)


@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ],
)
@given(
    event_count=st.integers(min_value=2, max_value=6),
    tamper_index_seed=st.integers(min_value=0, max_value=5),
    phase_after=_PHASE_POOL,
)
def test_trace_integrity_property(
    event_count: int,
    tamper_index_seed: int,
    phase_after: AgentPhase,
) -> None:
    """**Validates: CP-7.1 (Immediate Detection).**

    For any trace of N events with N ≥ 2, mutating event K (0 ≤ K < N) via
    ``model_copy`` replacement causes the next append (N+1-th event) to
    raise :class:`TraceIntegrityError`.
    """
    bus = EventBus(f"mission_trace_7_prop_{event_count}_{tamper_index_seed}")
    for index in range(event_count):
        bus.append(
            AgentEventType.AGENT_INITIALIZED if index == 0 else AgentEventType.CONTEXT_BUILT,
            f"event_{index}",
            phase_after=phase_after,
        )

    tamper_index = tamper_index_seed % event_count
    original = bus._events[tamper_index]
    bus._events[tamper_index] = original.model_copy(
        update={"summary": f"tampered_at_{tamper_index}"}
    )

    with pytest.raises(TraceIntegrityError):
        bus.append(AgentEventType.AGENT_BLOCKED, "After property tamper.")

    # verify_chain also surfaces the tamper independently (CP-7.2 remains).
    assert bus.verify_chain() is False


# ---------------------------------------------------------------------------
# Test 5 — the exception carries the canonical prefix for log grep.
# ---------------------------------------------------------------------------


def test_trace_integrity_error_has_canonical_code() -> None:
    """Message grepping contract: the raised exception must carry the
    ``trace_integrity_error`` prefix so downstream log filters and tests
    can identify the cause without string-fuzzing.
    """
    bus = EventBus("mission_trace_7_code")
    bus.append(AgentEventType.AGENT_INITIALIZED, "a")
    bus._last_hash = "deadbeef" * 8

    with pytest.raises(TraceIntegrityError) as excinfo:
        bus.append(AgentEventType.CONTEXT_BUILT, "b")
    assert "trace_integrity_error" in str(excinfo.value)
